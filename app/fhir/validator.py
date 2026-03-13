import logging

from pydantic import ValidationError as PydanticValidationError

from app.api.errors import ValidationError

logger = logging.getLogger("fhir.validator")

try:
    from fhir.resources import construct_fhir_element as _construct_fhir
    _FHIR_RESOURCES_AVAILABLE = True
except ImportError:
    _FHIR_RESOURCES_AVAILABLE = False

# Resource types whose models couldn't be found — warn once, then skip silently.
_no_model: set = set()


def validate_resource(resource_type, data):
    """Validate a FHIR resource dict using fhir.resources.

    Raises ValidationError with OperationOutcome diagnostics on failure.
    Silently skips if no model is available for the resource type.
    """
    if not _FHIR_RESOURCES_AVAILABLE or resource_type in _no_model:
        return

    try:
        _construct_fhir(resource_type, data)
    except PydanticValidationError as e:
        errors = [
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in e.errors()
        ]
        raise ValidationError("; ".join(errors))
    except Exception:
        _no_model.add(resource_type)
        logger.warning("No fhir.resources model found for %s — validation skipped", resource_type)
