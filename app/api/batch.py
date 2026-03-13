"""POST /fhir — Bundle (transaction/batch) endpoint."""

from flask import Blueprint, request

from app.api.content_negotiation import fhir_response, require_fhir_json
from app.api.errors import BadRequestError
from app.fhir.bundle_processor import bundle_processor

batch_bp = Blueprint("batch", __name__, url_prefix="/fhir")


@batch_bp.route("", methods=["POST"])
@require_fhir_json
def process_bundle():
    """Process a transaction or batch Bundle."""
    data = request.get_json(force=True)

    if not isinstance(data, dict):
        raise BadRequestError("Request body must be a JSON object")

    if data.get("resourceType") != "Bundle":
        raise BadRequestError("Expected a Bundle resource")

    result = bundle_processor.process(data)
    return fhir_response(result)
