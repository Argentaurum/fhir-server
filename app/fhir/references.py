"""Reference resolution utilities for FHIR bundles."""

import re

_REF_PATTERN = re.compile(r"^([A-Z][a-zA-Z]+)/(.+)$")


def parse_reference(ref_string):
    """Parse a FHIR reference string into (resource_type, id).

    Handles:
      - "Patient/123"
      - "http://example.com/fhir/Patient/123"
      - "urn:uuid:abc-def" (returns ("urn:uuid", "abc-def"))
    """
    if not ref_string:
        return None, None

    if ref_string.startswith("urn:uuid:"):
        return "urn:uuid", ref_string[9:]

    # Absolute URL: extract last two path segments
    if ref_string.startswith("http://") or ref_string.startswith("https://"):
        parts = ref_string.rstrip("/").rsplit("/", 2)
        if len(parts) >= 2:
            return parts[-2], parts[-1]

    # Relative reference
    m = _REF_PATTERN.match(ref_string)
    if m:
        return m.group(1), m.group(2)

    return None, None


def resolve_references_in_resource(resource_data, uuid_map):
    """Replace urn:uuid: references in a resource with resolved references.

    Args:
        resource_data: FHIR resource dict (modified in place)
        uuid_map: dict mapping urn:uuid:xxx → "ResourceType/id"
    """
    _walk_and_replace(resource_data, uuid_map)


def _walk_and_replace(obj, uuid_map):
    """Recursively walk a dict/list and replace urn:uuid references."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "reference" and isinstance(value, str) and value.startswith("urn:uuid:"):
                resolved = uuid_map.get(value)
                if resolved:
                    obj[key] = resolved
            elif isinstance(value, (dict, list)):
                _walk_and_replace(value, uuid_map)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _walk_and_replace(item, uuid_map)
