"""Transaction/batch bundle processing.

Implements FHIR spec:
  - Transaction: atomic (all-or-nothing), resolves urn:uuid: references,
    orders operations per spec (DELETE → POST → PUT → GET)
  - Batch: independent entries, partial success allowed
  - Conditional create: via ifNoneExist search before creating
"""

import json
import re
import uuid

from app.extensions import db
from app.dao.resource_dao import resource_dao
from app.fhir.references import resolve_references_in_resource
from app.api.errors import BadRequestError, FHIRError, make_operation_outcome
from app.utils.fhir_types import (
    SUPPORTED_RESOURCE_TYPES,
    BUNDLE_TRANSACTION,
    BUNDLE_BATCH,
    BUNDLE_TRANSACTION_RESPONSE,
    BUNDLE_BATCH_RESPONSE,
    TRANSACTION_ORDER,
)

# Match "ResourceType" or "ResourceType?search" from request.url
_URL_PATTERN = re.compile(r"^([A-Z][a-zA-Z]+)(?:/(.+))?$")


class BundleProcessor:
    """Process transaction and batch bundles."""

    def process(self, bundle_data):
        """Process a Bundle and return a response Bundle."""
        bundle_type = bundle_data.get("type")
        entries = bundle_data.get("entry", [])

        if bundle_type == BUNDLE_TRANSACTION:
            return self._process_transaction(entries)
        elif bundle_type == BUNDLE_BATCH:
            return self._process_batch(entries)
        else:
            raise BadRequestError(
                f"Unsupported bundle type: {bundle_type}. "
                "Expected 'transaction' or 'batch'."
            )

    def _process_transaction(self, entries):
        """Process a transaction bundle atomically."""
        # Sort entries by FHIR-specified order: DELETE → POST → PUT → GET
        sorted_entries = sorted(
            entries,
            key=lambda e: TRANSACTION_ORDER.get(
                e.get("request", {}).get("method", "GET"), 99
            ),
        )

        # Build uuid map for urn:uuid: references
        uuid_map = {}
        for entry in sorted_entries:
            full_url = entry.get("fullUrl", "")
            if full_url.startswith("urn:uuid:"):
                # Pre-assign a real id
                resource = entry.get("resource", {})
                res_type = resource.get("resourceType", "")
                new_id = str(uuid.uuid4())
                uuid_map[full_url] = f"{res_type}/{new_id}"
                resource["_assigned_id"] = new_id

        # Resolve urn:uuid references in all resources
        for entry in sorted_entries:
            resource = entry.get("resource")
            if resource:
                resolve_references_in_resource(resource, uuid_map)

        # Execute all entries
        response_entries = []
        try:
            for entry in sorted_entries:
                resp = self._execute_entry(entry)
                response_entries.append(resp)
            db.session.flush()
        except Exception:
            db.session.rollback()
            raise

        return {
            "resourceType": "Bundle",
            "type": BUNDLE_TRANSACTION_RESPONSE,
            "entry": response_entries,
        }

    def _process_batch(self, entries):
        """Process a batch bundle — each entry independently."""
        response_entries = []
        for entry in entries:
            try:
                resp = self._execute_entry(entry)
                response_entries.append(resp)
            except FHIRError as e:
                response_entries.append({
                    "response": {
                        "status": str(e.status_code),
                        "outcome": make_operation_outcome(
                            e.severity, e.code, e.diagnostics
                        ),
                    }
                })
            except Exception as e:
                response_entries.append({
                    "response": {
                        "status": "500",
                        "outcome": make_operation_outcome(
                            "fatal", "exception", str(e)
                        ),
                    }
                })

        return {
            "resourceType": "Bundle",
            "type": BUNDLE_BATCH_RESPONSE,
            "entry": response_entries,
        }

    def _execute_entry(self, entry):
        """Execute a single bundle entry."""
        req = entry.get("request", {})
        method = req.get("method", "").upper()
        url = req.get("url", "")
        resource = entry.get("resource")

        if method == "POST":
            return self._handle_post(entry, url, resource, req)
        elif method == "PUT":
            return self._handle_put(url, resource)
        elif method == "DELETE":
            return self._handle_delete(url)
        elif method == "GET":
            return self._handle_get(url)
        else:
            raise BadRequestError(f"Unsupported method: {method}")

    def _handle_post(self, entry, url, resource, req):
        """Handle POST (create) in a bundle."""
        res_type = url.split("?")[0] if "?" in url else url
        if res_type not in SUPPORTED_RESOURCE_TYPES:
            raise BadRequestError(f"Unsupported resource type: {res_type}")

        resource["resourceType"] = res_type

        # Check for conditional create (ifNoneExist)
        if_none_exist = req.get("ifNoneExist")
        if if_none_exist:
            from werkzeug.datastructures import ImmutableMultiDict
            from urllib.parse import parse_qs
            search_params = parse_qs(if_none_exist)
            flat_params = ImmutableMultiDict(
                [(k, v[0]) for k, v in search_params.items()]
            )
            results, total, _, _ = resource_dao.search(res_type, flat_params)
            if total > 0:
                return {
                    "response": {"status": "200 OK"},
                    "resource": results[0],
                }

        # Use pre-assigned id if available (from urn:uuid resolution)
        assigned_id = resource.pop("_assigned_id", None)
        data, fhir_id, version_id = resource_dao.create(
            res_type, resource, fhir_id=assigned_id
        )

        return {
            "response": {
                "status": "201 Created",
                "location": f"{res_type}/{fhir_id}/_history/{version_id}",
                "etag": f'W/"{version_id}"',
            },
            "resource": data,
        }

    def _handle_put(self, url, resource):
        """Handle PUT (update) in a bundle."""
        m = _URL_PATTERN.match(url)
        if not m or not m.group(2):
            raise BadRequestError(f"Invalid PUT URL: {url}")

        res_type = m.group(1)
        fhir_id = m.group(2)

        if res_type not in SUPPORTED_RESOURCE_TYPES:
            raise BadRequestError(f"Unsupported resource type: {res_type}")

        resource["resourceType"] = res_type
        resource["id"] = fhir_id

        # Try update, fall back to create if not found
        try:
            data, version_id = resource_dao.update(res_type, fhir_id, resource)
            status = "200 OK"
        except Exception:
            data, fhir_id, version_id = resource_dao.create(
                res_type, resource, fhir_id=fhir_id
            )
            status = "201 Created"

        return {
            "response": {
                "status": status,
                "location": f"{res_type}/{fhir_id}/_history/{version_id}",
                "etag": f'W/"{version_id}"',
            },
            "resource": data,
        }

    def _handle_delete(self, url):
        """Handle DELETE in a bundle."""
        m = _URL_PATTERN.match(url)
        if not m or not m.group(2):
            raise BadRequestError(f"Invalid DELETE URL: {url}")

        res_type = m.group(1)
        fhir_id = m.group(2)

        try:
            resource_dao.delete(res_type, fhir_id)
            return {"response": {"status": "204 No Content"}}
        except FHIRError:
            # Already deleted or not found — still success in transaction
            return {"response": {"status": "204 No Content"}}

    def _handle_get(self, url):
        """Handle GET (read) in a bundle."""
        m = _URL_PATTERN.match(url)
        if not m:
            raise BadRequestError(f"Invalid GET URL: {url}")

        res_type = m.group(1)
        fhir_id = m.group(2)

        if fhir_id:
            data = resource_dao.read(res_type, fhir_id)
            return {
                "response": {"status": "200 OK"},
                "resource": data,
            }
        else:
            # Search not supported inside bundles for now
            raise BadRequestError("Search inside bundles not supported")


bundle_processor = BundleProcessor()
