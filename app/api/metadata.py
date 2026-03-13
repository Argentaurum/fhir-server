from flask import Blueprint
from app.fhir.capability import build_capability_statement
from app.api.content_negotiation import fhir_response

metadata_bp = Blueprint("metadata", __name__, url_prefix="/fhir")


@metadata_bp.route("/metadata", methods=["GET"])
def capability_statement():
    return fhir_response(build_capability_statement())
