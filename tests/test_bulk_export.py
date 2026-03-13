"""Tests for Bulk Data Export ($export)."""

import json

FHIR_JSON = "application/fhir+json"


def _seed_data(client):
    """Create some test resources for export."""
    patient = {
        "resourceType": "Patient",
        "name": [{"family": "Export", "given": ["Test"]}],
        "gender": "male",
    }
    resp = client.post("/fhir/Patient", data=json.dumps(patient), content_type=FHIR_JSON)
    patient_id = resp.get_json()["id"]

    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": 72, "unit": "bpm"},
    }
    client.post("/fhir/Observation", data=json.dumps(obs), content_type=FHIR_JSON)

    return patient_id


def test_system_export_kickoff(client):
    """System $export returns 202 with Content-Location."""
    _seed_data(client)

    resp = client.get("/fhir/$export")
    assert resp.status_code == 202
    assert "Content-Location" in resp.headers
    poll_url = resp.headers["Content-Location"]
    assert "$export-poll-status" in poll_url
    assert "job=" in poll_url


def test_system_export_poll_and_download(client):
    """Full export flow: kick-off → poll → download."""
    _seed_data(client)

    # Kick-off
    resp = client.get("/fhir/$export")
    assert resp.status_code == 202
    poll_url = resp.headers["Content-Location"]

    # Extract relative path for test client
    poll_path = "/" + poll_url.split("/", 3)[-1]

    # Poll — should be complete (synchronous processing)
    resp = client.get(poll_path)
    assert resp.status_code == 200
    manifest = resp.get_json()
    assert "output" in manifest
    assert len(manifest["output"]) > 0

    # Find Patient output
    patient_output = None
    for out in manifest["output"]:
        if out["type"] == "Patient":
            patient_output = out
            break
    assert patient_output is not None
    assert patient_output["count"] >= 1

    # Download
    download_url = patient_output["url"]
    download_path = "/" + download_url.split("/", 3)[-1]
    resp = client.get(download_path)
    assert resp.status_code == 200
    assert "ndjson" in resp.content_type

    # Parse ndjson — each line is a JSON resource
    lines = resp.data.decode().strip().split("\n")
    assert len(lines) >= 1
    resource = json.loads(lines[0])
    assert resource["resourceType"] == "Patient"


def test_system_export_with_type_filter(client):
    """$export with _type filter returns only requested types."""
    _seed_data(client)

    resp = client.get("/fhir/$export?_type=Patient")
    assert resp.status_code == 202
    poll_path = "/" + resp.headers["Content-Location"].split("/", 3)[-1]

    resp = client.get(poll_path)
    manifest = resp.get_json()
    types = {out["type"] for out in manifest["output"]}
    assert types == {"Patient"}


def test_patient_export(client):
    """Patient-level $export."""
    patient_id = _seed_data(client)

    resp = client.get(f"/fhir/Patient/$export?patient={patient_id}")
    assert resp.status_code == 202
    poll_path = "/" + resp.headers["Content-Location"].split("/", 3)[-1]

    resp = client.get(poll_path)
    assert resp.status_code == 200
    manifest = resp.get_json()
    assert len(manifest["output"]) > 0

    # Should include both Patient and Observation
    types = {out["type"] for out in manifest["output"]}
    assert "Patient" in types
    assert "Observation" in types


def test_export_delete(client):
    """DELETE /fhir/$export-poll-status?job=<id> cancels the job."""
    _seed_data(client)

    resp = client.get("/fhir/$export")
    poll_url = resp.headers["Content-Location"]
    poll_path = "/" + poll_url.split("/", 3)[-1]

    # Delete the job
    resp = client.delete(poll_path)
    assert resp.status_code == 202

    # Poll again — should be 404
    resp = client.get(poll_path)
    assert resp.status_code == 404


def test_export_nonexistent_job(client):
    resp = client.get("/fhir/$export-poll-status?job=nonexistent")
    assert resp.status_code == 404
