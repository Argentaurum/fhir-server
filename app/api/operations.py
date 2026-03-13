"""FHIR operation endpoints: $lookup, $validate-code."""

from flask import Blueprint, request
from app.api.content_negotiation import fhir_response
from app.api.errors import BadRequestError
from app.fhir.terminology import terminology_service

operations_bp = Blueprint("operations", __name__, url_prefix="/fhir")


@operations_bp.route("/CodeSystem/$lookup", methods=["GET", "POST"])
def codesystem_lookup():
    """CodeSystem/$lookup operation.

    GET  /fhir/CodeSystem/$lookup?system=...&code=...&version=...
    POST /fhir/CodeSystem/$lookup  (Parameters in body)
    """
    if request.method == "GET":
        system = request.args.get("system")
        code = request.args.get("code")
        version = request.args.get("version")
    else:
        data = request.get_json(force=True) or {}
        system, code, version = _extract_params(data, "system", "code", "version")

    if not code:
        raise BadRequestError("Parameter 'code' is required for $lookup")

    result = terminology_service.lookup(system=system, code=code, version=version)

    if result is None:
        raise BadRequestError(f"Code '{code}' not found in system '{system}'")

    return fhir_response(result)


@operations_bp.route("/ValueSet/$validate-code", methods=["GET", "POST"])
def valueset_validate_code():
    """ValueSet/$validate-code operation.

    GET  /fhir/ValueSet/$validate-code?url=...&system=...&code=...
    POST /fhir/ValueSet/$validate-code  (Parameters in body)
    """
    if request.method == "GET":
        url = request.args.get("url")
        system = request.args.get("system")
        code = request.args.get("code")
        display = request.args.get("display")
    else:
        data = request.get_json(force=True) or {}
        url, system, code, display = _extract_params(
            data, "url", "system", "code", "display"
        )

    if not code:
        raise BadRequestError("Parameter 'code' is required for $validate-code")

    result = terminology_service.validate_code(
        url=url, system=system, code=code, display=display
    )

    return fhir_response(result)


def _extract_params(data, *param_names):
    """Extract named parameters from a FHIR Parameters resource."""
    values = []
    params = data.get("parameter", [])
    for name in param_names:
        value = None
        for p in params:
            if p.get("name") == name:
                # Try common value types
                value = (
                    p.get("valueString") or p.get("valueUri") or
                    p.get("valueCode") or p.get("valueBoolean")
                )
                break
        values.append(value)
    return values
