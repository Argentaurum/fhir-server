from flask import request, jsonify
from functools import wraps

from app.utils.fhir_types import FHIR_MIME_TYPES


def fhir_response(data, status_code=200, headers=None):
    """Create a FHIR JSON response with proper content type."""
    resp = jsonify(data)
    resp.status_code = status_code
    resp.content_type = "application/fhir+json"
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp


PATCH_MIME_TYPES = {
    "application/json-patch+json",
}


def require_fhir_json(f):
    """Decorator that validates Content-Type on requests with a body."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ("POST", "PUT") and request.content_length:
            ct = request.content_type or ""
            base_ct = ct.split(";")[0].strip()
            if base_ct and base_ct not in FHIR_MIME_TYPES:
                from app.api.errors import BadRequestError
                raise BadRequestError(
                    f"Unsupported Content-Type: {ct}. "
                    "Use application/fhir+json or application/json"
                )
        return f(*args, **kwargs)
    return wrapper


def require_patch_json(f):
    """Decorator that validates Content-Type for PATCH requests."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.content_length:
            ct = request.content_type or ""
            base_ct = ct.split(";")[0].strip()
            if base_ct and base_ct not in (PATCH_MIME_TYPES | FHIR_MIME_TYPES):
                from app.api.errors import BadRequestError
                raise BadRequestError(
                    f"Unsupported Content-Type: {ct}. "
                    "Use application/json-patch+json for PATCH"
                )
        return f(*args, **kwargs)
    return wrapper
