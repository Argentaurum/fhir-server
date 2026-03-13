"""Binary resource blueprint.

Handles FHIR Binary resources with dual-mode content negotiation:
  - JSON mode: standard FHIR JSON with base64-encoded `data` field
  - Native mode: raw bytes in/out when Content-Type / Accept is a non-FHIR MIME type
"""

import base64

from flask import Blueprint, request, make_response

from app.api.content_negotiation import fhir_response
from app.api.errors import BadRequestError
from app.dao.resource_dao import resource_dao
from app.utils.fhir_types import FHIR_MIME_TYPES
from app.utils.pagination import build_search_bundle, make_entry, build_history_bundle

binary_bp = Blueprint("binary", __name__, url_prefix="/fhir")


def _is_native_content_type(content_type):
    """Return True if Content-Type is a non-FHIR MIME type (native binary upload)."""
    if not content_type:
        return False
    base_ct = content_type.split(";")[0].strip()
    return base_ct not in FHIR_MIME_TYPES


def _prefers_native(accept_header, stored_content_type):
    """Return True if Accept explicitly includes the stored content type.

    Per FHIR spec: client must request the native MIME type explicitly.
    Default (no Accept or */*) returns JSON.
    """
    if not accept_header or not stored_content_type:
        return False
    for part in accept_header.split(","):
        mime = part.split(";")[0].strip()
        if mime == stored_content_type:
            return True
    return False


# --- Search ---

@binary_bp.route("/Binary", methods=["GET"])
def binary_search():
    results, total, include_entries, _ = resource_dao.search("Binary", request.args)
    base_url = request.host_url.rstrip("/") + "/fhir"
    entries = [make_entry(r, base_url) for r in results]
    entries.extend(include_entries)
    bundle = build_search_bundle(entries, total, base_url)
    return fhir_response(bundle)


# --- Create ---

@binary_bp.route("/Binary", methods=["POST"])
def binary_create():
    ct = request.content_type or ""
    if _is_native_content_type(ct):
        content_type = ct.split(";")[0].strip()
        raw_bytes = request.get_data()
        if not raw_bytes:
            raise BadRequestError("Request body is empty")
        resource_data = {
            "resourceType": "Binary",
            "contentType": content_type,
            "data": base64.b64encode(raw_bytes).decode("ascii"),
        }
    else:
        resource_data = request.get_json(force=True)
        if not isinstance(resource_data, dict):
            raise BadRequestError("Request body must be a JSON object")
        resource_data["resourceType"] = "Binary"

    result, fhir_id, version_id = resource_dao.create("Binary", resource_data)
    base_url = request.host_url.rstrip("/") + "/fhir"
    return fhir_response(
        result,
        status_code=201,
        headers={
            "Location": f"{base_url}/Binary/{fhir_id}",
            "ETag": f'W/"{version_id}"',
        },
    )


# --- Read ---

@binary_bp.route("/Binary/<fhir_id>", methods=["GET"])
def binary_read(fhir_id):
    resource_data = resource_dao.read("Binary", fhir_id)
    version_id = resource_data.get("meta", {}).get("versionId", "1")
    stored_ct = resource_data.get("contentType", "application/octet-stream")

    if _prefers_native(request.headers.get("Accept", ""), stored_ct):
        raw_b64 = resource_data.get("data", "")
        try:
            raw_bytes = base64.b64decode(raw_b64)
        except Exception:
            raise BadRequestError("Binary data is not valid base64")
        resp = make_response(raw_bytes)
        resp.content_type = stored_ct
        resp.headers["ETag"] = f'W/"{version_id}"'
        return resp

    return fhir_response(resource_data, headers={"ETag": f'W/"{version_id}"'})


# --- Update ---

@binary_bp.route("/Binary/<fhir_id>", methods=["PUT"])
def binary_update(fhir_id):
    ct = request.content_type or ""
    if _is_native_content_type(ct):
        content_type = ct.split(";")[0].strip()
        raw_bytes = request.get_data()
        if not raw_bytes:
            raise BadRequestError("Request body is empty")
        resource_data = {
            "resourceType": "Binary",
            "id": fhir_id,
            "contentType": content_type,
            "data": base64.b64encode(raw_bytes).decode("ascii"),
        }
    else:
        resource_data = request.get_json(force=True)
        if not isinstance(resource_data, dict):
            raise BadRequestError("Request body must be a JSON object")
        resource_data["resourceType"] = "Binary"
        if resource_data.get("id") and resource_data["id"] != fhir_id:
            raise BadRequestError(
                f"Resource id in body ({resource_data['id']}) does not match URL ({fhir_id})"
            )
        resource_data["id"] = fhir_id

    result, version_id = resource_dao.update("Binary", fhir_id, resource_data)
    return fhir_response(result, headers={"ETag": f'W/"{version_id}"'})


# --- Delete ---

@binary_bp.route("/Binary/<fhir_id>", methods=["DELETE"])
def binary_delete(fhir_id):
    resource_dao.delete("Binary", fhir_id)
    return fhir_response(
        {"resourceType": "OperationOutcome", "issue": [{
            "severity": "information",
            "code": "informational",
            "diagnostics": f"Successfully deleted Binary/{fhir_id}",
        }]},
        status_code=204,
    )


# --- Instance History ---

@binary_bp.route("/Binary/<fhir_id>/_history", methods=["GET"])
def binary_instance_history(fhir_id):
    entries = resource_dao.history("Binary", fhir_id)
    bundle = build_history_bundle(entries)
    return fhir_response(bundle)


# --- Version Read ---

@binary_bp.route("/Binary/<fhir_id>/_history/<int:version_id>", methods=["GET"])
def binary_vread(fhir_id, version_id):
    resource_data = resource_dao.vread("Binary", fhir_id, version_id)
    return fhir_response(resource_data, headers={"ETag": f'W/"{version_id}"'})
