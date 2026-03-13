#!/usr/bin/env python3
"""Seed the FHIR server with sample data."""

from app import create_app
from app.dao.resource_dao import resource_dao

app = create_app()

PATIENTS = [
    {
        "resourceType": "Patient",
        "name": [{"family": "Smith", "given": ["John", "Michael"]}],
        "gender": "male",
        "birthDate": "1990-01-15",
        "identifier": [{"system": "http://example.com/mrn", "value": "MRN001"}],
        "address": [{"line": ["123 Main St"], "city": "Springfield", "state": "IL", "postalCode": "62704"}],
        "telecom": [{"system": "phone", "value": "555-0101"}],
    },
    {
        "resourceType": "Patient",
        "name": [{"family": "Johnson", "given": ["Jane"]}],
        "gender": "female",
        "birthDate": "1985-06-22",
        "identifier": [{"system": "http://example.com/mrn", "value": "MRN002"}],
        "address": [{"line": ["456 Oak Ave"], "city": "Chicago", "state": "IL", "postalCode": "60601"}],
    },
    {
        "resourceType": "Patient",
        "name": [{"family": "Williams", "given": ["Robert"]}],
        "gender": "male",
        "birthDate": "1975-11-03",
        "identifier": [{"system": "http://example.com/mrn", "value": "MRN003"}],
    },
]


def seed():
    with app.app_context():
        patient_ids = []
        for p in PATIENTS:
            data, fhir_id, _ = resource_dao.create("Patient", p.copy())
            patient_ids.append(fhir_id)
            print(f"Created Patient/{fhir_id}: {p['name'][0]['family']}")

        # Create some observations
        for pid in patient_ids:
            obs = {
                "resourceType": "Observation",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
                "subject": {"reference": f"Patient/{pid}"},
                "valueQuantity": {"value": 72, "unit": "beats/min", "system": "http://unitsofmeasure.org", "code": "/min"},
                "effectiveDateTime": "2024-06-15T10:30:00Z",
            }
            data, obs_id, _ = resource_dao.create("Observation", obs)
            print(f"Created Observation/{obs_id} for Patient/{pid}")

        print(f"\nSeeded {len(patient_ids)} patients with observations.")


if __name__ == "__main__":
    seed()
