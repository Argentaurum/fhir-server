"""Load terminology resources (CodeSystem, ValueSet) into the FHIR server.

Usage:
    python scripts/load_terminology.py [--base-url http://localhost:5000/fhir]
"""

import json
import sys
import argparse

try:
    import requests
except ImportError:
    print("requests library required: pip install requests")
    sys.exit(1)

FHIR_JSON = "application/fhir+json"


def load_resource(base_url, resource):
    """POST a resource to the FHIR server."""
    res_type = resource["resourceType"]
    url = f"{base_url}/{res_type}"
    resp = requests.post(url, json=resource, headers={"Content-Type": FHIR_JSON})
    if resp.status_code == 201:
        fhir_id = resp.json().get("id")
        print(f"  Created {res_type}/{fhir_id}")
    else:
        print(f"  Failed to create {res_type}: {resp.status_code} {resp.text[:200]}")


def load_sample_terminology(base_url):
    """Load a sample CodeSystem and ValueSet for testing."""

    # Sample LOINC-like CodeSystem (subset)
    code_system = {
        "resourceType": "CodeSystem",
        "url": "http://loinc.org",
        "name": "LOINC",
        "title": "Logical Observation Identifiers, Names and Codes (LOINC)",
        "status": "active",
        "content": "fragment",
        "concept": [
            {"code": "8867-4", "display": "Heart rate"},
            {"code": "8310-5", "display": "Body temperature"},
            {"code": "85354-9", "display": "Blood pressure panel"},
            {"code": "8480-6", "display": "Systolic blood pressure"},
            {"code": "8462-4", "display": "Diastolic blood pressure"},
            {"code": "29463-7", "display": "Body weight"},
            {"code": "8302-2", "display": "Body height"},
        ],
    }

    # Sample ValueSet referencing LOINC vital signs
    value_set = {
        "resourceType": "ValueSet",
        "url": "http://hl7.org/fhir/ValueSet/observation-vitalsignresult",
        "name": "VitalSigns",
        "title": "Vital Signs",
        "status": "active",
        "compose": {
            "include": [
                {
                    "system": "http://loinc.org",
                    "concept": [
                        {"code": "8867-4", "display": "Heart rate"},
                        {"code": "8310-5", "display": "Body temperature"},
                        {"code": "85354-9", "display": "Blood pressure panel"},
                        {"code": "29463-7", "display": "Body weight"},
                        {"code": "8302-2", "display": "Body height"},
                    ],
                }
            ]
        },
    }

    print("Loading CodeSystem...")
    load_resource(base_url, code_system)
    print("Loading ValueSet...")
    load_resource(base_url, value_set)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load terminology resources")
    parser.add_argument(
        "--base-url", default="http://localhost:5000/fhir",
        help="FHIR server base URL",
    )
    args = parser.parse_args()
    load_sample_terminology(args.base_url)
