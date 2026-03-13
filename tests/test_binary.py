"""Tests for FHIR Binary resource support."""

import base64
import json


SAMPLE_PDF_BYTES = b"%PDF-1.4 fake pdf content for testing"
SAMPLE_PDF_B64 = base64.b64encode(SAMPLE_PDF_BYTES).decode("ascii")


# ---------------------------------------------------------------------------
# JSON mode
# ---------------------------------------------------------------------------

def test_create_binary_json(client):
    """Create a Binary via FHIR JSON with base64 data."""
    payload = {
        "resourceType": "Binary",
        "contentType": "application/pdf",
        "data": SAMPLE_PDF_B64,
    }
    resp = client.post(
        "/fhir/Binary",
        data=json.dumps(payload),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["resourceType"] == "Binary"
    assert data["id"]
    assert data["contentType"] == "application/pdf"
    assert data["data"] == SAMPLE_PDF_B64
    assert data["meta"]["versionId"] == "1"
    assert "Location" in resp.headers


def test_read_binary_json(client):
    """Read a Binary resource; default response is FHIR JSON."""
    fhir_id = _create_binary_json(client)["id"]

    resp = client.get(f"/fhir/Binary/{fhir_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == fhir_id
    assert data["data"] == SAMPLE_PDF_B64


def test_read_binary_native(client):
    """GET with Accept matching stored contentType returns raw bytes."""
    fhir_id = _create_binary_json(client)["id"]

    resp = client.get(
        f"/fhir/Binary/{fhir_id}",
        headers={"Accept": "application/pdf"},
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data == SAMPLE_PDF_BYTES


def test_read_binary_json_explicit_accept(client):
    """GET with Accept: application/fhir+json returns FHIR JSON even if native would match."""
    fhir_id = _create_binary_json(client)["id"]

    resp = client.get(
        f"/fhir/Binary/{fhir_id}",
        headers={"Accept": "application/fhir+json"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["resourceType"] == "Binary"


def test_update_binary_json(client):
    """PUT updates Binary via JSON mode."""
    fhir_id = _create_binary_json(client)["id"]

    new_bytes = b"updated content"
    new_b64 = base64.b64encode(new_bytes).decode("ascii")
    payload = {
        "resourceType": "Binary",
        "id": fhir_id,
        "contentType": "application/pdf",
        "data": new_b64,
    }
    resp = client.put(
        f"/fhir/Binary/{fhir_id}",
        data=json.dumps(payload),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["data"] == new_b64
    assert data["meta"]["versionId"] == "2"


def test_delete_binary(client):
    """DELETE removes the Binary resource."""
    fhir_id = _create_binary_json(client)["id"]

    resp = client.delete(f"/fhir/Binary/{fhir_id}")
    assert resp.status_code == 204

    resp = client.get(f"/fhir/Binary/{fhir_id}")
    assert resp.status_code == 410  # Gone


def test_binary_history(client):
    """Instance history tracks versions."""
    data = _create_binary_json(client)
    fhir_id = data["id"]

    # Update to create a second version
    payload = {**data, "data": base64.b64encode(b"v2").decode("ascii")}
    client.put(
        f"/fhir/Binary/{fhir_id}",
        data=json.dumps(payload),
        content_type="application/fhir+json",
    )

    resp = client.get(f"/fhir/Binary/{fhir_id}/_history")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "history"
    assert len(bundle["entry"]) == 2


def test_binary_vread(client):
    """Version-read returns a specific version."""
    data = _create_binary_json(client)
    fhir_id = data["id"]

    payload = {**data, "data": base64.b64encode(b"v2 content").decode("ascii")}
    client.put(
        f"/fhir/Binary/{fhir_id}",
        data=json.dumps(payload),
        content_type="application/fhir+json",
    )

    resp = client.get(f"/fhir/Binary/{fhir_id}/_history/1")
    assert resp.status_code == 200
    assert resp.get_json()["data"] == SAMPLE_PDF_B64


# ---------------------------------------------------------------------------
# Native binary mode
# ---------------------------------------------------------------------------

def test_create_binary_native(client):
    """POST with raw bytes and non-FHIR Content-Type creates a Binary resource."""
    resp = client.post(
        "/fhir/Binary",
        data=SAMPLE_PDF_BYTES,
        content_type="application/pdf",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["resourceType"] == "Binary"
    assert data["contentType"] == "application/pdf"
    assert data["data"] == SAMPLE_PDF_B64


def test_update_binary_native(client):
    """PUT with raw bytes updates contentType and data."""
    fhir_id = _create_binary_json(client)["id"]

    new_bytes = b"\x89PNG\r\nfake png"
    resp = client.put(
        f"/fhir/Binary/{fhir_id}",
        data=new_bytes,
        content_type="image/png",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["contentType"] == "image/png"
    assert data["data"] == base64.b64encode(new_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_binary_search_by_contenttype(client):
    """Search by contenttype token parameter."""
    _create_binary_json(client)  # application/pdf

    # Create a second with a different content type
    client.post(
        "/fhir/Binary",
        data=b"<html/>",
        content_type="text/html",
    )

    resp = client.get("/fhir/Binary?contenttype=application/pdf")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["contentType"] == "application/pdf"


def test_binary_in_capability_statement(client):
    """Binary appears in the CapabilityStatement."""
    resp = client.get("/fhir/metadata")
    types = {r["type"] for r in resp.get_json()["rest"][0]["resource"]}
    assert "Binary" in types


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_binary_json(client):
    resp = client.post(
        "/fhir/Binary",
        data=json.dumps({
            "resourceType": "Binary",
            "contentType": "application/pdf",
            "data": SAMPLE_PDF_B64,
        }),
        content_type="application/fhir+json",
    )
    assert resp.status_code == 201
    return resp.get_json()
