"""Tests for JSON Patch, _has (reverse chaining), and composite search."""

import json

FHIR_JSON = "application/fhir+json"
PATCH_JSON = "application/json-patch+json"


# --- JSON Patch ---

def test_patch_replace(client, sample_patient):
    resp = client.post("/fhir/Patient", data=json.dumps(sample_patient), content_type=FHIR_JSON)
    fhir_id = resp.get_json()["id"]

    patch_ops = [
        {"op": "replace", "path": "/gender", "value": "female"},
    ]
    resp = client.patch(
        f"/fhir/Patient/{fhir_id}",
        data=json.dumps(patch_ops),
        content_type=PATCH_JSON,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["gender"] == "female"
    assert body["meta"]["versionId"] == "2"


def test_patch_add(client, sample_patient):
    resp = client.post("/fhir/Patient", data=json.dumps(sample_patient), content_type=FHIR_JSON)
    fhir_id = resp.get_json()["id"]

    patch_ops = [
        {"op": "add", "path": "/active", "value": True},
    ]
    resp = client.patch(
        f"/fhir/Patient/{fhir_id}",
        data=json.dumps(patch_ops),
        content_type=PATCH_JSON,
    )
    assert resp.status_code == 200
    assert resp.get_json()["active"] is True


def test_patch_remove(client, sample_patient):
    resp = client.post("/fhir/Patient", data=json.dumps(sample_patient), content_type=FHIR_JSON)
    fhir_id = resp.get_json()["id"]

    patch_ops = [
        {"op": "remove", "path": "/gender"},
    ]
    resp = client.patch(
        f"/fhir/Patient/{fhir_id}",
        data=json.dumps(patch_ops),
        content_type=PATCH_JSON,
    )
    assert resp.status_code == 200
    assert "gender" not in resp.get_json()


def test_patch_not_found(client):
    patch_ops = [{"op": "replace", "path": "/gender", "value": "female"}]
    resp = client.patch(
        "/fhir/Patient/nonexistent",
        data=json.dumps(patch_ops),
        content_type=PATCH_JSON,
    )
    assert resp.status_code == 404


# --- _has (Reverse Chaining) ---

def test_has_basic(client):
    """Test _has:Observation:patient:code=8867-4 finds patients with matching observations."""
    # Create a patient
    patient_data = {
        "resourceType": "Patient",
        "name": [{"family": "HasTest"}],
    }
    resp = client.post("/fhir/Patient", data=json.dumps(patient_data), content_type=FHIR_JSON)
    patient_id = resp.get_json()["id"]

    # Create another patient (no observations)
    patient2_data = {
        "resourceType": "Patient",
        "name": [{"family": "NoObs"}],
    }
    client.post("/fhir/Patient", data=json.dumps(patient2_data), content_type=FHIR_JSON)

    # Create an observation referencing the first patient
    obs_data = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
    }
    client.post("/fhir/Observation", data=json.dumps(obs_data), content_type=FHIR_JSON)

    # Use _has to find patients that have observations with code 8867-4
    resp = client.get("/fhir/Patient?_has:Observation:patient:code=8867-4")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1
    found_ids = {e["resource"]["id"] for e in bundle["entry"]}
    assert patient_id in found_ids


# --- Composite Search ---

def test_composite_code_value_quantity(client):
    """Test code-value-quantity composite search on Observation."""
    obs_data = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "valueQuantity": {"value": 72, "unit": "beats/min", "system": "http://unitsofmeasure.org"},
    }
    resp = client.post("/fhir/Observation", data=json.dumps(obs_data), content_type=FHIR_JSON)
    assert resp.status_code == 201

    # Composite search: code-value-quantity=http://loinc.org|8867-4$72.0
    resp = client.get("/fhir/Observation?code-value-quantity=http://loinc.org|8867-4$72.0")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1


def test_composite_no_match(client):
    """Composite search should not match when components don't align."""
    obs_data = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "valueQuantity": {"value": 72, "unit": "beats/min"},
    }
    client.post("/fhir/Observation", data=json.dumps(obs_data), content_type=FHIR_JSON)

    # Wrong code + right value should not match
    resp = client.get("/fhir/Observation?code-value-quantity=http://loinc.org|WRONG$72.0")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] == 0
