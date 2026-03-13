from datetime import datetime, timezone

from app.utils.fhir_types import (
    SUPPORTED_RESOURCE_TYPES,
    INTERACTION_READ,
    INTERACTION_VREAD,
    INTERACTION_UPDATE,
    INTERACTION_DELETE,
    INTERACTION_HISTORY_INSTANCE,
    INTERACTION_CREATE,
    INTERACTION_SEARCH_TYPE,
    INTERACTION_HISTORY_TYPE,
    INTERACTION_PATCH,
)
from app.fhir.search_params import SEARCH_PARAMS


def build_capability_statement():
    resources = []
    for res_type in sorted(SUPPORTED_RESOURCE_TYPES):
        search_params = []
        for param in SEARCH_PARAMS.get(res_type, []):
            search_params.append({
                "name": param["name"],
                "type": param["type"],
            })

        resources.append({
            "type": res_type,
            "interaction": [
                {"code": INTERACTION_READ},
                {"code": INTERACTION_VREAD},
                {"code": INTERACTION_CREATE},
                {"code": INTERACTION_UPDATE},
                {"code": INTERACTION_PATCH},
                {"code": INTERACTION_DELETE},
                {"code": INTERACTION_HISTORY_INSTANCE},
                {"code": INTERACTION_HISTORY_TYPE},
                {"code": INTERACTION_SEARCH_TYPE},
            ],
            "versioning": "versioned",
            "readHistory": True,
            "conditionalCreate": True,
            "conditionalUpdate": True,
            "conditionalDelete": "multiple",
            "searchParam": search_params,
        })

    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.now(timezone.utc).isoformat(),
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "implementation": {
            "description": "Python/Flask FHIR R4 Server",
        },
        "rest": [
            {
                "mode": "server",
                "resource": resources,
                "interaction": [
                    {"code": "transaction"},
                    {"code": "batch"},
                    {"code": "history-system"},
                ],
                "searchParam": [
                    {"name": "_tag", "type": "token"},
                    {"name": "_security", "type": "token"},
                    {"name": "_profile", "type": "token"},
                    {"name": "_summary", "type": "string"},
                    {"name": "_elements", "type": "string"},
                ],
            }
        ],
    }
