"""Tests for transaction and batch bundle processing."""

import json


def test_transaction_bundle(client):
    """Test a transaction bundle with urn:uuid references."""
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-1",
                "resource": {
                    "resourceType": "Patient",
                    "name": [{"family": "Bundle", "given": ["Test"]}],
                    "gender": "male",
                },
                "request": {"method": "POST", "url": "Patient"},
            },
            {
                "fullUrl": "urn:uuid:encounter-1",
                "resource": {
                    "resourceType": "Encounter",
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "subject": {"reference": "urn:uuid:patient-1"},
                },
                "request": {"method": "POST", "url": "Encounter"},
            },
            {
                "fullUrl": "urn:uuid:obs-1",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {
                        "coding": [
                            {"system": "http://loinc.org", "code": "8867-4"}
                        ]
                    },
                    "subject": {"reference": "urn:uuid:patient-1"},
                    "encounter": {"reference": "urn:uuid:encounter-1"},
                    "valueQuantity": {"value": 72, "unit": "bpm"},
                },
                "request": {"method": "POST", "url": "Observation"},
            },
        ],
    }

    resp = client.post(
        "/fhir",
        data=json.dumps(bundle),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["type"] == "transaction-response"
    assert len(result["entry"]) == 3

    # All should be 201
    for entry in result["entry"]:
        assert "201" in entry["response"]["status"]

    # Verify the observation's subject reference was resolved
    obs_entry = [e for e in result["entry"] if e["resource"]["resourceType"] == "Observation"][0]
    obs_subject = obs_entry["resource"]["subject"]["reference"]
    assert obs_subject.startswith("Patient/")
    assert "urn:uuid" not in obs_subject


def test_batch_bundle(client):
    """Test a batch bundle with independent entries."""
    bundle = {
        "resourceType": "Bundle",
        "type": "batch",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "name": [{"family": "Batch1"}],
                },
                "request": {"method": "POST", "url": "Patient"},
            },
            {
                "resource": {
                    "resourceType": "Patient",
                    "name": [{"family": "Batch2"}],
                },
                "request": {"method": "POST", "url": "Patient"},
            },
        ],
    }

    resp = client.post(
        "/fhir",
        data=json.dumps(bundle),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["type"] == "batch-response"
    assert len(result["entry"]) == 2


def test_batch_partial_failure(client):
    """Batch should allow partial success."""
    bundle = {
        "resourceType": "Bundle",
        "type": "batch",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "name": [{"family": "Good"}],
                },
                "request": {"method": "POST", "url": "Patient"},
            },
            {
                "request": {"method": "GET", "url": "Patient/nonexistent-id-xyz"},
            },
        ],
    }

    resp = client.post(
        "/fhir",
        data=json.dumps(bundle),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 200
    result = resp.get_json()
    statuses = [e["response"]["status"] for e in result["entry"]]
    assert "201 Created" in statuses
    assert "404" in statuses


def test_conditional_create(client):
    """Test ifNoneExist conditional create."""
    # First create
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "identifier": [{"system": "http://example.com", "value": "COND1"}],
                    "name": [{"family": "Conditional"}],
                },
                "request": {
                    "method": "POST",
                    "url": "Patient",
                    "ifNoneExist": "identifier=http://example.com|COND1",
                },
            },
        ],
    }

    resp = client.post(
        "/fhir",
        data=json.dumps(bundle),
        content_type="application/fhir+json",
    )
    result = resp.get_json()
    first_status = result["entry"][0]["response"]["status"]
    assert "201" in first_status

    # Second create with same ifNoneExist should return existing
    resp = client.post(
        "/fhir",
        data=json.dumps(bundle),
        content_type="application/fhir+json",
    )
    result = resp.get_json()
    second_status = result["entry"][0]["response"]["status"]
    assert "200" in second_status
