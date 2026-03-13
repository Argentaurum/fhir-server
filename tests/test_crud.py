"""Tests for FHIR CRUD operations."""

import json


def test_metadata(client):
    resp = client.get("/fhir/metadata")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["resourceType"] == "CapabilityStatement"
    assert data["fhirVersion"] == "4.0.1"
    # Should list all 19 resource types
    types = {r["type"] for r in data["rest"][0]["resource"]}
    assert "Patient" in types
    assert "Observation" in types
    assert len(types) == 19


def test_create_patient(client, sample_patient):
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["resourceType"] == "Patient"
    assert data["id"]
    assert data["meta"]["versionId"] == "1"
    assert "Location" in resp.headers


def test_read_patient(client, sample_patient):
    # Create
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    fhir_id = resp.get_json()["id"]

    # Read
    resp = client.get(f"/fhir/Patient/{fhir_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == fhir_id
    assert data["name"][0]["family"] == "Smith"


def test_update_patient(client, sample_patient):
    # Create
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    fhir_id = resp.get_json()["id"]

    # Update
    sample_patient["name"][0]["family"] = "Jones"
    resp = client.put(
        f"/fhir/Patient/{fhir_id}",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["meta"]["versionId"] == "2"
    assert data["name"][0]["family"] == "Jones"


def test_delete_patient(client, sample_patient):
    # Create
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    fhir_id = resp.get_json()["id"]

    # Delete
    resp = client.delete(f"/fhir/Patient/{fhir_id}")
    assert resp.status_code == 204

    # Read should be gone
    resp = client.get(f"/fhir/Patient/{fhir_id}")
    assert resp.status_code == 410


def test_read_not_found(client):
    resp = client.get("/fhir/Patient/nonexistent")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["resourceType"] == "OperationOutcome"


def test_unsupported_resource_type(client):
    resp = client.get("/fhir/FakeResource/123")
    assert resp.status_code == 404


def test_vread(client, sample_patient):
    # Create
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    fhir_id = resp.get_json()["id"]

    # Update
    sample_patient["name"][0]["family"] = "Updated"
    client.put(
        f"/fhir/Patient/{fhir_id}",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )

    # vread version 1
    resp = client.get(f"/fhir/Patient/{fhir_id}/_history/1")
    assert resp.status_code == 200
    assert resp.get_json()["name"][0]["family"] == "Smith"

    # vread version 2
    resp = client.get(f"/fhir/Patient/{fhir_id}/_history/2")
    assert resp.status_code == 200
    assert resp.get_json()["name"][0]["family"] == "Updated"


def test_history(client, sample_patient):
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )
    fhir_id = resp.get_json()["id"]

    # Update once
    sample_patient["gender"] = "female"
    client.put(
        f"/fhir/Patient/{fhir_id}",
        data=json.dumps(sample_patient),
        content_type="application/fhir+json",
    )

    resp = client.get(f"/fhir/Patient/{fhir_id}/_history")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["type"] == "history"
    assert bundle["total"] == 2
