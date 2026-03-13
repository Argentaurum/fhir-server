"""Tests for _summary, _elements, and meta search params."""

import json

FHIR_JSON = "application/fhir+json"


def _create_patient(client, family="Smith", tags=None, profile=None):
    data = {
        "resourceType": "Patient",
        "name": [{"family": family, "given": ["John"]}],
        "gender": "male",
        "birthDate": "1990-01-15",
        "text": {"status": "generated", "div": "<div>Patient summary</div>"},
        "address": [{"city": "Springfield", "state": "IL"}],
    }
    if tags or profile:
        data["meta"] = {}
        if tags:
            data["meta"]["tag"] = tags
        if profile:
            data["meta"]["profile"] = profile
    resp = client.post("/fhir/Patient", data=json.dumps(data), content_type=FHIR_JSON)
    return resp.get_json()


def test_summary_true_on_search(client):
    _create_patient(client)
    resp = client.get("/fhir/Patient?_summary=true")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1
    resource = bundle["entry"][0]["resource"]
    # Summary should keep name, gender, birthDate but drop address text
    assert "name" in resource
    assert "gender" in resource
    assert "text" not in resource
    # Should have SUBSETTED tag
    tags = resource.get("meta", {}).get("tag", [])
    assert any(t["code"] == "SUBSETTED" for t in tags)


def test_summary_count(client):
    _create_patient(client)
    _create_patient(client, family="Jones")
    resp = client.get("/fhir/Patient?_summary=count")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 2
    assert "entry" not in bundle


def test_summary_text(client):
    patient = _create_patient(client)
    fhir_id = patient["id"]
    resp = client.get(f"/fhir/Patient/{fhir_id}?_summary=text")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "text" in data
    assert "name" not in data
    assert "gender" not in data


def test_summary_data(client):
    patient = _create_patient(client)
    fhir_id = patient["id"]
    resp = client.get(f"/fhir/Patient/{fhir_id}?_summary=data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "text" not in data
    assert "name" in data


def test_elements_on_read(client):
    patient = _create_patient(client)
    fhir_id = patient["id"]
    resp = client.get(f"/fhir/Patient/{fhir_id}?_elements=name,gender")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "name" in data
    assert "gender" in data
    assert "birthDate" not in data
    assert "address" not in data
    # SUBSETTED tag
    tags = data.get("meta", {}).get("tag", [])
    assert any(t["code"] == "SUBSETTED" for t in tags)


def test_elements_on_search(client):
    _create_patient(client)
    resp = client.get("/fhir/Patient?_elements=name,gender")
    assert resp.status_code == 200
    bundle = resp.get_json()
    resource = bundle["entry"][0]["resource"]
    assert "name" in resource
    assert "gender" in resource
    assert "birthDate" not in resource


def test_search_by_tag(client):
    _create_patient(client, family="Tagged", tags=[
        {"system": "http://example.com/tags", "code": "research"}
    ])
    _create_patient(client, family="Untagged")

    resp = client.get("/fhir/Patient?_tag=research")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Tagged"


def test_search_by_tag_system_code(client):
    _create_patient(client, family="Tagged2", tags=[
        {"system": "http://example.com/tags", "code": "vip"}
    ])

    resp = client.get("/fhir/Patient?_tag=http://example.com/tags|vip")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] == 1


def test_search_by_profile(client):
    _create_patient(client, family="Profiled", profile=[
        "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
    ])
    _create_patient(client, family="NoProfile")

    resp = client.get("/fhir/Patient?_profile=http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Profiled"
