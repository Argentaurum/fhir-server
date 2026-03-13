"""Declarative search parameter definitions per resource type.

Each param has:
  - name: FHIR search parameter name
  - type: string | token | date | quantity | reference
  - paths: list of FHIRPath-like dotted paths into the resource JSON
  - target (reference only): list of target resource types
"""

SEARCH_PARAMS = {
    "Binary": [
        {"name": "contenttype", "type": "token", "paths": ["contentType"]},
    ],
    "Patient": [
        {"name": "family", "type": "string", "paths": ["name.family"]},
        {"name": "given", "type": "string", "paths": ["name.given"]},
        {"name": "name", "type": "string", "paths": ["name.family", "name.given", "name.text"]},
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "gender", "type": "token", "paths": ["gender"]},
        {"name": "birthdate", "type": "date", "paths": ["birthDate"]},
        {"name": "address", "type": "string", "paths": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"]},
        {"name": "address-city", "type": "string", "paths": ["address.city"]},
        {"name": "address-state", "type": "string", "paths": ["address.state"]},
        {"name": "address-postalcode", "type": "string", "paths": ["address.postalCode"]},
        {"name": "telecom", "type": "token", "paths": ["telecom"]},
        {"name": "active", "type": "token", "paths": ["active"]},
        {"name": "deceased", "type": "token", "paths": ["deceasedBoolean"]},
        {"name": "death-date", "type": "date", "paths": ["deceasedDateTime"]},
        {"name": "general-practitioner", "type": "reference", "paths": ["generalPractitioner"], "target": ["Practitioner", "Organization"]},
        {"name": "organization", "type": "reference", "paths": ["managingOrganization"], "target": ["Organization"]},
    ],
    "Encounter": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "class", "type": "token", "paths": ["class"]},
        {"name": "type", "type": "token", "paths": ["type"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "date", "type": "date", "paths": ["period.start", "period.end"]},
        {"name": "reason-code", "type": "token", "paths": ["reasonCode"]},
        {"name": "participant", "type": "reference", "paths": ["participant.individual"], "target": ["Practitioner"]},
        {"name": "service-provider", "type": "reference", "paths": ["serviceProvider"], "target": ["Organization"]},
    ],
    "Observation": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "encounter", "type": "reference", "paths": ["encounter"], "target": ["Encounter"]},
        {"name": "date", "type": "date", "paths": ["effectiveDateTime", "effectivePeriod.start"]},
        {"name": "value-quantity", "type": "quantity", "paths": ["valueQuantity"]},
        {"name": "value-concept", "type": "token", "paths": ["valueCodeableConcept"]},
        {"name": "value-string", "type": "string", "paths": ["valueString"]},
        {"name": "component-code", "type": "token", "paths": ["component.code"]},
        {"name": "combo-code", "type": "token", "paths": ["code", "component.code"]},
    ],
    "Condition": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "clinical-status", "type": "token", "paths": ["clinicalStatus"]},
        {"name": "verification-status", "type": "token", "paths": ["verificationStatus"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "severity", "type": "token", "paths": ["severity"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "encounter", "type": "reference", "paths": ["encounter"], "target": ["Encounter"]},
        {"name": "onset-date", "type": "date", "paths": ["onsetDateTime", "onsetPeriod.start"]},
        {"name": "recorded-date", "type": "date", "paths": ["recordedDate"]},
        {"name": "abatement-date", "type": "date", "paths": ["abatementDateTime", "abatementPeriod.start"]},
    ],
    "Procedure": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "encounter", "type": "reference", "paths": ["encounter"], "target": ["Encounter"]},
        {"name": "date", "type": "date", "paths": ["performedDateTime", "performedPeriod.start"]},
        {"name": "performer", "type": "reference", "paths": ["performer.actor"], "target": ["Practitioner"]},
        {"name": "reason-code", "type": "token", "paths": ["reasonCode"]},
    ],
    "Medication": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "form", "type": "token", "paths": ["form"]},
        {"name": "manufacturer", "type": "reference", "paths": ["manufacturer"], "target": ["Organization"]},
    ],
    "MedicationRequest": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["medicationCodeableConcept"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "intent", "type": "token", "paths": ["intent"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "encounter", "type": "reference", "paths": ["encounter"], "target": ["Encounter"]},
        {"name": "medication", "type": "reference", "paths": ["medicationReference"], "target": ["Medication"]},
        {"name": "requester", "type": "reference", "paths": ["requester"], "target": ["Practitioner"]},
        {"name": "authoredon", "type": "date", "paths": ["authoredOn"]},
    ],
    "AllergyIntolerance": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "clinical-status", "type": "token", "paths": ["clinicalStatus"]},
        {"name": "verification-status", "type": "token", "paths": ["verificationStatus"]},
        {"name": "type", "type": "token", "paths": ["type"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "criticality", "type": "token", "paths": ["criticality"]},
        {"name": "patient", "type": "reference", "paths": ["patient"], "target": ["Patient"]},
        {"name": "recorder", "type": "reference", "paths": ["recorder"], "target": ["Practitioner", "Patient"]},
        {"name": "date", "type": "date", "paths": ["recordedDate"]},
        {"name": "onset", "type": "date", "paths": ["onsetDateTime", "onsetPeriod.start"]},
    ],
    "DiagnosticReport": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "encounter", "type": "reference", "paths": ["encounter"], "target": ["Encounter"]},
        {"name": "date", "type": "date", "paths": ["effectiveDateTime", "effectivePeriod.start"]},
        {"name": "issued", "type": "date", "paths": ["issued"]},
        {"name": "result", "type": "reference", "paths": ["result"], "target": ["Observation"]},
        {"name": "performer", "type": "reference", "paths": ["performer"], "target": ["Practitioner", "Organization"]},
    ],
    "DocumentReference": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "type", "type": "token", "paths": ["type"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "date", "type": "date", "paths": ["date"]},
        {"name": "author", "type": "reference", "paths": ["author"], "target": ["Practitioner", "Organization", "Patient"]},
        {"name": "custodian", "type": "reference", "paths": ["custodian"], "target": ["Organization"]},
        {"name": "content-type", "type": "token", "paths": ["content.attachment.contentType"]},
    ],
    "Practitioner": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "family", "type": "string", "paths": ["name.family"]},
        {"name": "given", "type": "string", "paths": ["name.given"]},
        {"name": "name", "type": "string", "paths": ["name.family", "name.given", "name.text"]},
        {"name": "active", "type": "token", "paths": ["active"]},
        {"name": "telecom", "type": "token", "paths": ["telecom"]},
        {"name": "address", "type": "string", "paths": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"]},
        {"name": "address-city", "type": "string", "paths": ["address.city"]},
        {"name": "address-state", "type": "string", "paths": ["address.state"]},
        {"name": "gender", "type": "token", "paths": ["gender"]},
    ],
    "Organization": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "name", "type": "string", "paths": ["name", "alias"]},
        {"name": "active", "type": "token", "paths": ["active"]},
        {"name": "type", "type": "token", "paths": ["type"]},
        {"name": "address", "type": "string", "paths": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"]},
        {"name": "address-city", "type": "string", "paths": ["address.city"]},
        {"name": "address-state", "type": "string", "paths": ["address.state"]},
        {"name": "telecom", "type": "token", "paths": ["telecom"]},
        {"name": "partof", "type": "reference", "paths": ["partOf"], "target": ["Organization"]},
    ],
    "Location": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "name", "type": "string", "paths": ["name", "alias"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "type", "type": "token", "paths": ["type"]},
        {"name": "address", "type": "string", "paths": ["address.line", "address.city", "address.state", "address.postalCode", "address.country"]},
        {"name": "address-city", "type": "string", "paths": ["address.city"]},
        {"name": "address-state", "type": "string", "paths": ["address.state"]},
        {"name": "organization", "type": "reference", "paths": ["managingOrganization"], "target": ["Organization"]},
        {"name": "operational-status", "type": "token", "paths": ["operationalStatus"]},
    ],
    "PractitionerRole": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "active", "type": "token", "paths": ["active"]},
        {"name": "practitioner", "type": "reference", "paths": ["practitioner"], "target": ["Practitioner"]},
        {"name": "organization", "type": "reference", "paths": ["organization"], "target": ["Organization"]},
        {"name": "role", "type": "token", "paths": ["code"]},
        {"name": "specialty", "type": "token", "paths": ["specialty"]},
        {"name": "location", "type": "reference", "paths": ["location"], "target": ["Location"]},
        {"name": "service", "type": "reference", "paths": ["healthcareService"], "target": ["HealthcareService"]},
        {"name": "telecom", "type": "token", "paths": ["telecom"]},
        {"name": "date", "type": "date", "paths": ["period.start", "period.end"]},
    ],
    "ServiceRequest": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "code", "type": "token", "paths": ["code"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "intent", "type": "token", "paths": ["intent"]},
        {"name": "priority", "type": "token", "paths": ["priority"]},
        {"name": "category", "type": "token", "paths": ["category"]},
        {"name": "subject", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "patient", "type": "reference", "paths": ["subject"], "target": ["Patient"]},
        {"name": "encounter", "type": "reference", "paths": ["encounter"], "target": ["Encounter"]},
        {"name": "requester", "type": "reference", "paths": ["requester"], "target": ["Practitioner", "Organization"]},
        {"name": "performer", "type": "reference", "paths": ["performer"], "target": ["Practitioner", "Organization"]},
        {"name": "authored", "type": "date", "paths": ["authoredOn"]},
        {"name": "occurrence", "type": "date", "paths": ["occurrenceDateTime", "occurrencePeriod.start"]},
    ],
    "CodeSystem": [
        {"name": "url", "type": "token", "paths": ["url"]},
        {"name": "name", "type": "string", "paths": ["name"]},
        {"name": "title", "type": "string", "paths": ["title"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "version", "type": "token", "paths": ["version"]},
        {"name": "code", "type": "token", "paths": ["concept.code"]},
        {"name": "system", "type": "token", "paths": ["url"]},
        {"name": "content-mode", "type": "token", "paths": ["content"]},
    ],
    "ValueSet": [
        {"name": "url", "type": "token", "paths": ["url"]},
        {"name": "name", "type": "string", "paths": ["name"]},
        {"name": "title", "type": "string", "paths": ["title"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "version", "type": "token", "paths": ["version"]},
        {"name": "reference", "type": "token", "paths": ["compose.include.system"]},
    ],
    "Subscription": [
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "type", "type": "token", "paths": ["channel.type"]},
        {"name": "criteria", "type": "string", "paths": ["criteria"]},
        {"name": "url", "type": "token", "paths": ["channel.endpoint"]},
    ],
    "Immunization": [
        {"name": "identifier", "type": "token", "paths": ["identifier"]},
        {"name": "vaccine-code", "type": "token", "paths": ["vaccineCode"]},
        {"name": "status", "type": "token", "paths": ["status"]},
        {"name": "patient", "type": "reference", "paths": ["patient"], "target": ["Patient"]},
        {"name": "date", "type": "date", "paths": ["occurrenceDateTime"]},
        {"name": "lot-number", "type": "string", "paths": ["lotNumber"]},
        {"name": "performer", "type": "reference", "paths": ["performer.actor"], "target": ["Practitioner", "Organization"]},
        {"name": "location", "type": "reference", "paths": ["location"], "target": ["Location"]},
        {"name": "status-reason", "type": "token", "paths": ["statusReason"]},
        {"name": "reason-code", "type": "token", "paths": ["reasonCode"]},
    ],
}


# Composite search parameter definitions
# Each composite has two components referencing other search params
COMPOSITE_PARAMS = {
    "Observation": [
        {
            "name": "code-value-quantity",
            "type": "composite",
            "components": [
                {"name": "code", "type": "token", "paths": ["code"]},
                {"name": "value-quantity", "type": "quantity", "paths": ["valueQuantity"]},
            ],
        },
        {
            "name": "code-value-concept",
            "type": "composite",
            "components": [
                {"name": "code", "type": "token", "paths": ["code"]},
                {"name": "value-concept", "type": "token", "paths": ["valueCodeableConcept"]},
            ],
        },
        {
            "name": "combo-code-value-quantity",
            "type": "composite",
            "components": [
                {"name": "combo-code", "type": "token", "paths": ["code", "component.code"]},
                {"name": "value-quantity", "type": "quantity", "paths": ["valueQuantity"]},
            ],
        },
    ],
}


def get_composite_params(resource_type):
    """Get composite search parameter definitions for a resource type."""
    return COMPOSITE_PARAMS.get(resource_type, [])


def get_search_params(resource_type):
    """Get the search parameter definitions for a resource type."""
    return SEARCH_PARAMS.get(resource_type, [])


def get_search_param(resource_type, param_name):
    """Get a specific search parameter definition."""
    for param in SEARCH_PARAMS.get(resource_type, []):
        if param["name"] == param_name:
            return param
    return None
