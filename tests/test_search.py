"""Tests for FHIR search operations."""

import json


def _create_patient(client, family="Smith", given="John", gender="male",
                    birth_date="1990-01-15", city="Springfield"):
    patient = {
        "resourceType": "Patient",
        "name": [{"family": family, "given": [given]}],
        "gender": gender,
        "birthDate": birth_date,
        "address": [{"city": city, "state": "IL"}],
        "identifier": [{"system": "http://example.com/mrn", "value": f"MRN-{family}"}],
    }
    resp = client.post(
        "/fhir/Patient",
        data=json.dumps(patient),
        content_type="application/fhir+json",
    )
    return resp.get_json()


def _create_observation(client, patient_id, code="8867-4", value=72.0,
                        date="2024-06-15T10:30:00Z"):
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": code}]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {
            "value": value,
            "unit": "beats/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min",
        },
        "effectiveDateTime": date,
    }
    resp = client.post(
        "/fhir/Observation",
        data=json.dumps(obs),
        content_type="application/fhir+json",
    )
    return resp.get_json()


def test_search_by_name(client):
    _create_patient(client, family="Smith")
    _create_patient(client, family="Jones")

    resp = client.get("/fhir/Patient?family=Smith")
    bundle = resp.get_json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Smith"


def test_search_by_name_exact(client):
    _create_patient(client, family="Smith")
    _create_patient(client, family="Smithson")

    resp = client.get("/fhir/Patient?family:exact=Smith")
    bundle = resp.get_json()
    assert bundle["total"] == 1


def test_search_by_token(client):
    _create_patient(client, gender="male")
    _create_patient(client, gender="female")

    resp = client.get("/fhir/Patient?gender=male")
    bundle = resp.get_json()
    assert bundle["total"] == 1


def test_search_by_identifier_system_value(client):
    _create_patient(client, family="Smith")

    resp = client.get("/fhir/Patient?identifier=http://example.com/mrn|MRN-Smith")
    bundle = resp.get_json()
    assert bundle["total"] == 1


def test_search_by_date(client):
    _create_patient(client, family="Young", birth_date="2000-05-20")
    _create_patient(client, family="Old", birth_date="1950-03-10")

    resp = client.get("/fhir/Patient?birthdate=ge2000-01-01")
    bundle = resp.get_json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Young"


def test_search_by_reference(client):
    patient = _create_patient(client)
    patient_id = patient["id"]
    _create_observation(client, patient_id)
    _create_observation(client, patient_id, code="29463-7", value=70)

    resp = client.get(f"/fhir/Observation?patient=Patient/{patient_id}")
    bundle = resp.get_json()
    assert bundle["total"] == 2


def test_search_by_code_token(client):
    patient = _create_patient(client)
    _create_observation(client, patient["id"], code="8867-4")
    _create_observation(client, patient["id"], code="29463-7")

    resp = client.get("/fhir/Observation?code=http://loinc.org|8867-4")
    bundle = resp.get_json()
    assert bundle["total"] == 1


def test_search_pagination(client):
    for i in range(5):
        _create_patient(client, family=f"Patient{i}")

    resp = client.get("/fhir/Patient?_count=2&_offset=0")
    bundle = resp.get_json()
    assert bundle["total"] == 5
    assert len(bundle["entry"]) == 2

    resp = client.get("/fhir/Patient?_count=2&_offset=2")
    bundle = resp.get_json()
    assert len(bundle["entry"]) == 2


def test_search_sort(client):
    _create_patient(client, family="Alpha", birth_date="2000-01-01")
    _create_patient(client, family="Beta", birth_date="1990-01-01")

    resp = client.get("/fhir/Patient?_sort=birthdate")
    bundle = resp.get_json()
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Beta"

    resp = client.get("/fhir/Patient?_sort=-birthdate")
    bundle = resp.get_json()
    assert bundle["entry"][0]["resource"]["name"][0]["family"] == "Alpha"


def test_search_include(client):
    patient = _create_patient(client)
    _create_observation(client, patient["id"])

    resp = client.get(
        f"/fhir/Observation?patient=Patient/{patient['id']}&_include=Observation:patient"
    )
    bundle = resp.get_json()
    # Should have observation + included patient
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Observation" in types
    assert "Patient" in types


def test_search_chain(client):
    patient = _create_patient(client, family="ChainTest")
    _create_observation(client, patient["id"])

    resp = client.get("/fhir/Observation?patient.family=ChainTest")
    bundle = resp.get_json()
    assert bundle["total"] == 1
