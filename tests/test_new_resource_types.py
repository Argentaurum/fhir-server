"""Tests for the 6 new resource types added in Phase 1."""

import json

FHIR_JSON = "application/fhir+json"


def test_create_practitioner(client):
    data = {
        "resourceType": "Practitioner",
        "name": [{"family": "Jones", "given": ["Alice"]}],
        "gender": "female",
        "identifier": [{"system": "http://npi.org", "value": "1234567890"}],
    }
    resp = client.post("/fhir/Practitioner", data=json.dumps(data), content_type=FHIR_JSON)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["resourceType"] == "Practitioner"
    assert body["name"][0]["family"] == "Jones"


def test_create_organization(client):
    data = {
        "resourceType": "Organization",
        "name": "General Hospital",
        "active": True,
        "type": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "prov"}]}],
    }
    resp = client.post("/fhir/Organization", data=json.dumps(data), content_type=FHIR_JSON)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "General Hospital"


def test_create_location(client):
    data = {
        "resourceType": "Location",
        "name": "South Wing",
        "status": "active",
        "address": {"line": ["123 Main St"], "city": "Anytown", "state": "CA"},
    }
    resp = client.post("/fhir/Location", data=json.dumps(data), content_type=FHIR_JSON)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "South Wing"


def test_create_practitioner_role(client):
    data = {
        "resourceType": "PractitionerRole",
        "active": True,
        "code": [{"coding": [{"system": "http://snomed.info/sct", "code": "59058001", "display": "General physician"}]}],
        "specialty": [{"coding": [{"system": "http://snomed.info/sct", "code": "394814009"}]}],
    }
    resp = client.post("/fhir/PractitionerRole", data=json.dumps(data), content_type=FHIR_JSON)
    assert resp.status_code == 201
    assert resp.get_json()["resourceType"] == "PractitionerRole"


def test_create_service_request(client):
    data = {
        "resourceType": "ServiceRequest",
        "status": "active",
        "intent": "order",
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
    }
    resp = client.post("/fhir/ServiceRequest", data=json.dumps(data), content_type=FHIR_JSON)
    assert resp.status_code == 201
    assert resp.get_json()["resourceType"] == "ServiceRequest"


def test_create_immunization(client):
    data = {
        "resourceType": "Immunization",
        "status": "completed",
        "vaccineCode": {"coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": "207", "display": "COVID-19"}]},
        "occurrenceDateTime": "2024-03-15",
    }
    resp = client.post("/fhir/Immunization", data=json.dumps(data), content_type=FHIR_JSON)
    assert resp.status_code == 201
    assert resp.get_json()["resourceType"] == "Immunization"


def test_search_practitioner_by_name(client):
    data = {
        "resourceType": "Practitioner",
        "name": [{"family": "Watson", "given": ["John"]}],
    }
    client.post("/fhir/Practitioner", data=json.dumps(data), content_type=FHIR_JSON)

    resp = client.get("/fhir/Practitioner?family=Watson")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Watson"


def test_search_organization_by_name(client):
    data = {
        "resourceType": "Organization",
        "name": "Springfield Medical Center",
    }
    client.post("/fhir/Organization", data=json.dumps(data), content_type=FHIR_JSON)

    resp = client.get("/fhir/Organization?name=Springfield")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1


def test_search_immunization_by_date(client):
    data = {
        "resourceType": "Immunization",
        "status": "completed",
        "vaccineCode": {"coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": "207"}]},
        "occurrenceDateTime": "2024-06-01",
    }
    client.post("/fhir/Immunization", data=json.dumps(data), content_type=FHIR_JSON)

    resp = client.get("/fhir/Immunization?date=ge2024-01-01")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1


def test_capability_statement_includes_new_types(client):
    resp = client.get("/fhir/metadata")
    assert resp.status_code == 200
    cs = resp.get_json()
    resource_types = {r["type"] for r in cs["rest"][0]["resource"]}
    for rt in ("Practitioner", "Organization", "Location", "PractitionerRole", "ServiceRequest", "Immunization"):
        assert rt in resource_types, f"{rt} missing from CapabilityStatement"
