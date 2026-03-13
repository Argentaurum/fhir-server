"""Tests for type/system history and conditional operations."""

import json

FHIR_JSON = "application/fhir+json"


def _create_patient(client, family="Smith", identifier=None):
    data = {
        "resourceType": "Patient",
        "name": [{"family": family, "given": ["John"]}],
        "gender": "male",
    }
    if identifier:
        data["identifier"] = [{"system": "http://example.com/mrn", "value": identifier}]
    resp = client.post("/fhir/Patient", data=json.dumps(data), content_type=FHIR_JSON)
    return resp.get_json()


# --- Type-level and System-level History ---

def test_type_history(client):
    _create_patient(client, family="One")
    _create_patient(client, family="Two")

    resp = client.get("/fhir/Patient/_history")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["type"] == "history"
    assert bundle["total"] >= 2


def test_type_history_pagination(client):
    for i in range(5):
        _create_patient(client, family=f"Hist{i}")

    resp = client.get("/fhir/Patient/_history?_count=2&_offset=0")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert len(bundle["entry"]) == 2
    assert bundle["total"] >= 5


def test_system_history(client):
    _create_patient(client, family="SysHist")

    # Also create a different resource type
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
    }
    client.post("/fhir/Observation", data=json.dumps(obs), content_type=FHIR_JSON)

    resp = client.get("/fhir/_history")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["type"] == "history"
    assert bundle["total"] >= 2

    # Should contain both resource types
    res_types = {e["resource"]["resourceType"] for e in bundle["entry"]}
    assert "Patient" in res_types
    assert "Observation" in res_types


# --- Conditional Update ---

def test_conditional_update_create(client):
    """Conditional update with 0 matches → create."""
    data = {
        "resourceType": "Patient",
        "name": [{"family": "NewCond"}],
        "identifier": [{"system": "http://example.com/mrn", "value": "COND001"}],
    }

    resp = client.put(
        "/fhir/Patient?identifier=http://example.com/mrn|COND001",
        data=json.dumps(data),
        content_type=FHIR_JSON,
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"][0]["family"] == "NewCond"
    assert "Location" in resp.headers


def test_conditional_update_match(client):
    """Conditional update with 1 match → update."""
    patient = _create_patient(client, family="CondUpd", identifier="COND002")

    updated_data = {
        "resourceType": "Patient",
        "name": [{"family": "Updated"}],
        "identifier": [{"system": "http://example.com/mrn", "value": "COND002"}],
    }

    resp = client.put(
        "/fhir/Patient?identifier=http://example.com/mrn|COND002",
        data=json.dumps(updated_data),
        content_type=FHIR_JSON,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"][0]["family"] == "Updated"
    assert body["id"] == patient["id"]  # Same resource


def test_conditional_update_multiple_matches_412(client):
    """Conditional update with 2+ matches → 412."""
    _create_patient(client, family="Dup1")
    _create_patient(client, family="Dup2")

    data = {
        "resourceType": "Patient",
        "name": [{"family": "WontWork"}],
    }

    # Both patients have gender=male
    resp = client.put(
        "/fhir/Patient?gender=male",
        data=json.dumps(data),
        content_type=FHIR_JSON,
    )
    assert resp.status_code == 412


# --- Conditional Delete ---

def test_conditional_delete(client):
    _create_patient(client, family="DelMe", identifier="DEL001")

    resp = client.delete("/fhir/Patient?identifier=http://example.com/mrn|DEL001")
    assert resp.status_code == 200

    # Verify it's gone
    resp = client.get("/fhir/Patient?identifier=http://example.com/mrn|DEL001")
    bundle = resp.get_json()
    assert bundle["total"] == 0


def test_conditional_delete_no_params_rejected(client):
    resp = client.delete("/fhir/Patient")
    assert resp.status_code == 400


def test_conditional_update_no_params_rejected(client):
    data = {"resourceType": "Patient", "name": [{"family": "Foo"}]}
    resp = client.put(
        "/fhir/Patient",
        data=json.dumps(data),
        content_type=FHIR_JSON,
    )
    assert resp.status_code == 400
