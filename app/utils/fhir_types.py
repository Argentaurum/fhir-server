SUPPORTED_RESOURCE_TYPES = frozenset([
    "Binary",
    "Patient",
    "Encounter",
    "Observation",
    "Condition",
    "Procedure",
    "Medication",
    "MedicationRequest",
    "AllergyIntolerance",
    "DiagnosticReport",
    "DocumentReference",
    "Practitioner",
    "Organization",
    "Location",
    "PractitionerRole",
    "ServiceRequest",
    "Immunization",
    "Coverage",
    "CodeSystem",
    "ValueSet",
    "Subscription",
])

FHIR_MIME_TYPES = {
    "application/fhir+json",
    "application/json",
}

# FHIR interaction types for CapabilityStatement
INTERACTION_READ = "read"
INTERACTION_VREAD = "vread"
INTERACTION_UPDATE = "update"
INTERACTION_DELETE = "delete"
INTERACTION_HISTORY_INSTANCE = "history-instance"
INTERACTION_CREATE = "create"
INTERACTION_SEARCH_TYPE = "search-type"
INTERACTION_HISTORY_TYPE = "history-type"
INTERACTION_HISTORY_SYSTEM = "history-system"
INTERACTION_PATCH = "patch"

# Search parameter types
SEARCH_PARAM_STRING = "string"
SEARCH_PARAM_TOKEN = "token"
SEARCH_PARAM_DATE = "date"
SEARCH_PARAM_QUANTITY = "quantity"
SEARCH_PARAM_REFERENCE = "reference"
SEARCH_PARAM_COMPOSITE = "composite"

# Date comparison prefixes
DATE_PREFIXES = {"eq", "ne", "gt", "lt", "ge", "le", "sa", "eb"}

# Bundle types
BUNDLE_TRANSACTION = "transaction"
BUNDLE_BATCH = "batch"
BUNDLE_SEARCHSET = "searchset"
BUNDLE_HISTORY = "history"
BUNDLE_TRANSACTION_RESPONSE = "transaction-response"
BUNDLE_BATCH_RESPONSE = "batch-response"

# HTTP method ordering for transaction processing (FHIR spec)
TRANSACTION_ORDER = {"DELETE": 0, "POST": 1, "PUT": 2, "GET": 3}
