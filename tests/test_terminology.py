"""Tests for terminology service: CodeSystem/$lookup and ValueSet/$validate-code."""

import json

FHIR_JSON = "application/fhir+json"


def _load_code_system(client):
    cs = {
        "resourceType": "CodeSystem",
        "url": "http://loinc.org",
        "name": "LOINC",
        "status": "active",
        "content": "fragment",
        "concept": [
            {"code": "8867-4", "display": "Heart rate"},
            {"code": "8310-5", "display": "Body temperature"},
            {"code": "85354-9", "display": "Blood pressure panel"},
        ],
    }
    resp = client.post("/fhir/CodeSystem", data=json.dumps(cs), content_type=FHIR_JSON)
    assert resp.status_code == 201
    return resp.get_json()


def _load_value_set(client):
    vs = {
        "resourceType": "ValueSet",
        "url": "http://hl7.org/fhir/ValueSet/observation-vitalsignresult",
        "name": "VitalSigns",
        "status": "active",
        "compose": {
            "include": [
                {
                    "system": "http://loinc.org",
                    "concept": [
                        {"code": "8867-4", "display": "Heart rate"},
                        {"code": "8310-5", "display": "Body temperature"},
                    ],
                }
            ]
        },
    }
    resp = client.post("/fhir/ValueSet", data=json.dumps(vs), content_type=FHIR_JSON)
    assert resp.status_code == 201
    return resp.get_json()


def test_codesystem_lookup_get(client):
    _load_code_system(client)

    resp = client.get("/fhir/CodeSystem/$lookup?system=http://loinc.org&code=8867-4")
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["resourceType"] == "Parameters"
    params = {p["name"]: p for p in result["parameter"]}
    assert params["display"]["valueString"] == "Heart rate"
    assert params["code"]["valueCode"] == "8867-4"


def test_codesystem_lookup_not_found(client):
    _load_code_system(client)

    resp = client.get("/fhir/CodeSystem/$lookup?system=http://loinc.org&code=NONEXISTENT")
    assert resp.status_code == 400


def test_codesystem_lookup_post(client):
    _load_code_system(client)

    params = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "system", "valueUri": "http://loinc.org"},
            {"name": "code", "valueCode": "8310-5"},
        ],
    }
    resp = client.post(
        "/fhir/CodeSystem/$lookup",
        data=json.dumps(params),
        content_type=FHIR_JSON,
    )
    assert resp.status_code == 200
    result = resp.get_json()
    params_dict = {p["name"]: p for p in result["parameter"]}
    assert params_dict["display"]["valueString"] == "Body temperature"


def test_valueset_validate_code_found(client):
    _load_code_system(client)
    _load_value_set(client)

    resp = client.get(
        "/fhir/ValueSet/$validate-code?"
        "url=http://hl7.org/fhir/ValueSet/observation-vitalsignresult"
        "&system=http://loinc.org&code=8867-4"
    )
    assert resp.status_code == 200
    result = resp.get_json()
    params = {p["name"]: p for p in result["parameter"]}
    assert params["result"]["valueBoolean"] is True


def test_valueset_validate_code_not_found(client):
    _load_code_system(client)
    _load_value_set(client)

    resp = client.get(
        "/fhir/ValueSet/$validate-code?"
        "url=http://hl7.org/fhir/ValueSet/observation-vitalsignresult"
        "&system=http://loinc.org&code=WRONG"
    )
    assert resp.status_code == 200
    result = resp.get_json()
    params = {p["name"]: p for p in result["parameter"]}
    assert params["result"]["valueBoolean"] is False


def test_search_codesystem(client):
    _load_code_system(client)

    resp = client.get("/fhir/CodeSystem?name=LOINC")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1


def test_search_valueset(client):
    _load_value_set(client)

    resp = client.get("/fhir/ValueSet?name=VitalSigns")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1
