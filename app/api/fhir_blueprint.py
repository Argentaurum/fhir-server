"""Single generic Blueprint for all FHIR resource CRUD + search."""

import json
from flask import Blueprint, request

from app.api.content_negotiation import fhir_response, require_fhir_json, require_patch_json
from app.api.errors import UnsupportedResourceError, BadRequestError
from app.dao.resource_dao import resource_dao
from app.utils.fhir_types import SUPPORTED_RESOURCE_TYPES
from app.utils.pagination import build_search_bundle, make_entry, build_history_bundle
from app.fhir.summary import apply_summary, apply_elements

fhir_bp = Blueprint("fhir", __name__, url_prefix="/fhir")


def _validate_resource_type(resource_type):
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise UnsupportedResourceError(resource_type)


# --- System-level history (must be registered before /<resource_type> routes) ---

@fhir_bp.route("/_history", methods=["GET"])
def system_history():
    """System-level history: GET /fhir/_history"""
    count = request.args.get("_count", 20, type=int)
    offset = request.args.get("_offset", 0, type=int)
    entries, total = resource_dao.system_history(count=count, offset=offset)
    bundle = build_history_bundle(entries, total=total)
    return fhir_response(bundle)


# --- Type-level history (must be registered before /<resource_type>/<id>) ---

@fhir_bp.route("/<resource_type>/_history", methods=["GET"])
def type_history(resource_type):
    """Type-level history: GET /fhir/<ResourceType>/_history"""
    _validate_resource_type(resource_type)
    count = request.args.get("_count", 20, type=int)
    offset = request.args.get("_offset", 0, type=int)
    entries, total = resource_dao.type_history(resource_type, count=count, offset=offset)
    bundle = build_history_bundle(entries, total=total)
    return fhir_response(bundle)


# --- Search ---

@fhir_bp.route("/<resource_type>", methods=["GET"])
def search(resource_type):
    """Search for resources: GET /fhir/<ResourceType>?params"""
    _validate_resource_type(resource_type)

    results, total, include_entries, entities = resource_dao.search(
        resource_type, request.args
    )

    summary_mode = request.args.get("_summary")

    # _summary=count returns Bundle with total only
    if summary_mode == "count":
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
        }
        return fhir_response(bundle)

    base_url = request.host_url.rstrip("/") + "/fhir"
    entries = [make_entry(r, base_url) for r in results]
    entries.extend(include_entries)

    bundle = build_search_bundle(entries, total, base_url)
    return fhir_response(bundle)


# --- Create ---

@fhir_bp.route("/<resource_type>", methods=["POST"])
@require_fhir_json
def create(resource_type):
    """Create a resource: POST /fhir/<ResourceType>"""
    _validate_resource_type(resource_type)

    data = request.get_json(force=True)
    if not isinstance(data, dict):
        raise BadRequestError("Request body must be a JSON object")

    data["resourceType"] = resource_type

    resource_data, fhir_id, version_id = resource_dao.create(resource_type, data)

    base_url = request.host_url.rstrip("/") + "/fhir"
    location = f"{base_url}/{resource_type}/{fhir_id}"

    return fhir_response(
        resource_data,
        status_code=201,
        headers={
            "Location": location,
            "ETag": f'W/"{version_id}"',
        },
    )


# --- Conditional Update: PUT /<type>?search_params ---

@fhir_bp.route("/<resource_type>", methods=["PUT"])
@require_fhir_json
def conditional_update(resource_type):
    """Conditional update: PUT /fhir/<ResourceType>?search_params"""
    _validate_resource_type(resource_type)

    if not request.args:
        raise BadRequestError("Conditional update requires search parameters in the URL")

    data = request.get_json(force=True)
    if not isinstance(data, dict):
        raise BadRequestError("Request body must be a JSON object")

    data["resourceType"] = resource_type

    resource_data, version_id, created = resource_dao.conditional_update(
        resource_type, data, request.args
    )

    base_url = request.host_url.rstrip("/") + "/fhir"
    fhir_id = resource_data["id"]
    location = f"{base_url}/{resource_type}/{fhir_id}"

    status_code = 201 if created else 200
    headers = {"ETag": f'W/"{version_id}"'}
    if created:
        headers["Location"] = location

    return fhir_response(resource_data, status_code=status_code, headers=headers)


# --- Conditional Delete: DELETE /<type>?search_params ---

@fhir_bp.route("/<resource_type>", methods=["DELETE"])
def conditional_delete(resource_type):
    """Conditional delete: DELETE /fhir/<ResourceType>?search_params"""
    _validate_resource_type(resource_type)

    if not request.args:
        raise BadRequestError("Conditional delete requires search parameters in the URL")

    count = resource_dao.conditional_delete(resource_type, request.args)

    return fhir_response(
        {"resourceType": "OperationOutcome", "issue": [
            {"severity": "information", "code": "informational",
             "diagnostics": f"Conditionally deleted {count} {resource_type} resource(s)"}
        ]},
        status_code=200 if count > 0 else 204,
    )


# --- Read ---

@fhir_bp.route("/<resource_type>/<fhir_id>", methods=["GET"])
def read(resource_type, fhir_id):
    """Read a resource: GET /fhir/<ResourceType>/<id>"""
    _validate_resource_type(resource_type)
    resource_data = resource_dao.read(resource_type, fhir_id)

    # Apply _summary / _elements
    summary_mode = request.args.get("_summary")
    elements = request.args.get("_elements")
    if summary_mode:
        resource_data = apply_summary(resource_data, summary_mode)
    elif elements:
        resource_data = apply_elements(resource_data, elements)

    version_id = resource_data.get("meta", {}).get("versionId", "1")
    return fhir_response(
        resource_data,
        headers={"ETag": f'W/"{version_id}"'},
    )


# --- PATCH ---

@fhir_bp.route("/<resource_type>/<fhir_id>", methods=["PATCH"])
@require_patch_json
def patch(resource_type, fhir_id):
    """Patch a resource: PATCH /fhir/<ResourceType>/<id>"""
    _validate_resource_type(resource_type)

    data = request.get_json(force=True)
    if not isinstance(data, list):
        raise BadRequestError("PATCH body must be a JSON array of patch operations")

    resource_data, version_id = resource_dao.patch(resource_type, fhir_id, data)

    return fhir_response(
        resource_data,
        headers={"ETag": f'W/"{version_id}"'},
    )


# --- Update ---

@fhir_bp.route("/<resource_type>/<fhir_id>", methods=["PUT"])
@require_fhir_json
def update(resource_type, fhir_id):
    """Update a resource: PUT /fhir/<ResourceType>/<id>"""
    _validate_resource_type(resource_type)

    data = request.get_json(force=True)
    if not isinstance(data, dict):
        raise BadRequestError("Request body must be a JSON object")

    # Ensure resource type and id match
    data["resourceType"] = resource_type
    if data.get("id") and data["id"] != fhir_id:
        raise BadRequestError(
            f"Resource id in body ({data['id']}) does not match URL ({fhir_id})"
        )
    data["id"] = fhir_id

    resource_data, version_id = resource_dao.update(resource_type, fhir_id, data)

    return fhir_response(
        resource_data,
        headers={"ETag": f'W/"{version_id}"'},
    )


# --- Delete ---

@fhir_bp.route("/<resource_type>/<fhir_id>", methods=["DELETE"])
def delete(resource_type, fhir_id):
    """Delete a resource: DELETE /fhir/<ResourceType>/<id>"""
    _validate_resource_type(resource_type)
    resource_dao.delete(resource_type, fhir_id)
    return fhir_response(
        {"resourceType": "OperationOutcome", "issue": [
            {"severity": "information", "code": "informational",
             "diagnostics": f"Successfully deleted {resource_type}/{fhir_id}"}
        ]},
        status_code=204,
    )


# --- Instance History ---

@fhir_bp.route("/<resource_type>/<fhir_id>/_history", methods=["GET"])
def instance_history(resource_type, fhir_id):
    """Instance history: GET /fhir/<ResourceType>/<id>/_history"""
    _validate_resource_type(resource_type)
    entries = resource_dao.history(resource_type, fhir_id)
    bundle = build_history_bundle(entries)
    return fhir_response(bundle)


# --- Version Read ---

@fhir_bp.route("/<resource_type>/<fhir_id>/_history/<int:version_id>", methods=["GET"])
def vread(resource_type, fhir_id, version_id):
    """Version read: GET /fhir/<ResourceType>/<id>/_history/<vid>"""
    _validate_resource_type(resource_type)
    resource_data = resource_dao.vread(resource_type, fhir_id, version_id)
    return fhir_response(
        resource_data,
        headers={"ETag": f'W/"{version_id}"'},
    )
