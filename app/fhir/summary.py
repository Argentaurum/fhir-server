"""_summary and _elements support for FHIR search and read."""

import copy

# Per-type definitions of which fields appear in _summary=true
# Includes mandatory fields per FHIR spec (resourceType, id, meta) plus key summary fields
SUMMARY_ELEMENTS = {
    "Patient": {"resourceType", "id", "meta", "identifier", "active", "name", "telecom", "gender", "birthDate", "address", "managingOrganization", "link"},
    "Encounter": {"resourceType", "id", "meta", "identifier", "status", "class", "type", "subject", "period"},
    "Observation": {"resourceType", "id", "meta", "identifier", "status", "code", "subject", "effectiveDateTime", "effectivePeriod", "valueQuantity", "valueCodeableConcept", "valueString", "dataAbsentReason", "interpretation"},
    "Condition": {"resourceType", "id", "meta", "identifier", "clinicalStatus", "verificationStatus", "category", "code", "subject"},
    "Procedure": {"resourceType", "id", "meta", "identifier", "status", "code", "subject", "performedDateTime", "performedPeriod"},
    "Medication": {"resourceType", "id", "meta", "identifier", "code", "status"},
    "MedicationRequest": {"resourceType", "id", "meta", "identifier", "status", "intent", "medicationCodeableConcept", "medicationReference", "subject"},
    "AllergyIntolerance": {"resourceType", "id", "meta", "identifier", "clinicalStatus", "verificationStatus", "type", "code", "patient"},
    "DiagnosticReport": {"resourceType", "id", "meta", "identifier", "status", "code", "subject", "effectiveDateTime", "issued"},
    "DocumentReference": {"resourceType", "id", "meta", "identifier", "status", "type", "subject", "date"},
    "Practitioner": {"resourceType", "id", "meta", "identifier", "active", "name", "telecom", "gender"},
    "Organization": {"resourceType", "id", "meta", "identifier", "active", "name", "type", "telecom", "address"},
    "Location": {"resourceType", "id", "meta", "identifier", "status", "name", "type", "telecom", "address"},
    "PractitionerRole": {"resourceType", "id", "meta", "identifier", "active", "practitioner", "organization", "code", "specialty"},
    "ServiceRequest": {"resourceType", "id", "meta", "identifier", "status", "intent", "code", "subject"},
    "Immunization": {"resourceType", "id", "meta", "identifier", "status", "vaccineCode", "patient", "occurrenceDateTime"},
}

# Mandatory FHIR fields that must never be removed
MANDATORY_FIELDS = {"resourceType", "id", "meta"}

# Text-only fields for _summary=text
TEXT_FIELDS = {"resourceType", "id", "meta", "text"}


def apply_summary(resource, mode):
    """Apply _summary filtering to a resource.

    Modes:
        true  - return only summary elements
        text  - return only text, id, meta
        data  - remove text element
        false - return everything (no-op)
        count - handled at bundle level (caller should not include resource)
    """
    if mode == "false" or mode is None:
        return resource

    result = copy.deepcopy(resource)
    res_type = result.get("resourceType", "")

    if mode == "true":
        summary_fields = SUMMARY_ELEMENTS.get(res_type, MANDATORY_FIELDS)
        keys_to_remove = [k for k in result if k not in summary_fields]
        for k in keys_to_remove:
            del result[k]
        _add_subsetted_tag(result)

    elif mode == "text":
        keys_to_remove = [k for k in result if k not in TEXT_FIELDS]
        for k in keys_to_remove:
            del result[k]
        _add_subsetted_tag(result)

    elif mode == "data":
        result.pop("text", None)
        _add_subsetted_tag(result)

    return result


def apply_elements(resource, fields):
    """Apply _elements filtering — keep only specified fields plus mandatory ones.

    Args:
        resource: FHIR resource dict
        fields: comma-separated string of element names
    """
    if not fields:
        return resource

    keep = set(fields.split(",")) | MANDATORY_FIELDS
    result = copy.deepcopy(resource)
    keys_to_remove = [k for k in result if k not in keep]
    for k in keys_to_remove:
        del result[k]
    _add_subsetted_tag(result)
    return result


def _add_subsetted_tag(resource):
    """Add SUBSETTED tag to meta to indicate partial content."""
    resource.setdefault("meta", {})
    resource["meta"].setdefault("tag", [])
    subsetted = {
        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationValue",
        "code": "SUBSETTED",
        "display": "subsetted",
    }
    # Don't duplicate
    for tag in resource["meta"]["tag"]:
        if tag.get("code") == "SUBSETTED":
            return
    resource["meta"]["tag"].append(subsetted)
