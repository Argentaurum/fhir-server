"""Tests for Subscription resource and subscription evaluation."""

import json
from unittest.mock import patch, MagicMock

FHIR_JSON = "application/fhir+json"


def test_create_subscription(client):
    sub = {
        "resourceType": "Subscription",
        "status": "active",
        "criteria": "Observation",
        "channel": {
            "type": "rest-hook",
            "endpoint": "http://example.com/notify",
            "payload": "application/fhir+json",
        },
        "reason": "Monitor observations",
    }
    resp = client.post("/fhir/Subscription", data=json.dumps(sub), content_type=FHIR_JSON)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["resourceType"] == "Subscription"
    assert body["status"] == "active"


def test_search_subscription(client):
    sub = {
        "resourceType": "Subscription",
        "status": "active",
        "criteria": "Observation",
        "channel": {"type": "rest-hook", "endpoint": "http://example.com/notify"},
    }
    client.post("/fhir/Subscription", data=json.dumps(sub), content_type=FHIR_JSON)

    resp = client.get("/fhir/Subscription?status=active")
    assert resp.status_code == 200
    bundle = resp.get_json()
    assert bundle["total"] >= 1


def test_subscription_criteria_matching():
    """Test SubscriptionManager criteria matching logic."""
    from app.fhir.subscriptions import SubscriptionManager

    mgr = SubscriptionManager()

    # Simple type match
    assert mgr._matches_criteria("Observation", "Observation", {"resourceType": "Observation"})
    assert not mgr._matches_criteria("Observation", "Patient", {"resourceType": "Patient"})

    # Type + param match
    assert mgr._matches_criteria(
        "Observation?status=final", "Observation", {"resourceType": "Observation", "status": "final"}
    )
    assert not mgr._matches_criteria(
        "Observation?status=final", "Observation", {"resourceType": "Observation", "status": "preliminary"}
    )


@patch("app.fhir.subscriptions.SubscriptionManager._send_notification")
def test_subscription_triggers_on_create(mock_send, client):
    """Creating a matching resource triggers subscription notification."""
    # Create a subscription for Observations
    sub = {
        "resourceType": "Subscription",
        "status": "active",
        "criteria": "Observation",
        "channel": {"type": "rest-hook", "endpoint": "http://example.com/hook"},
    }
    client.post("/fhir/Subscription", data=json.dumps(sub), content_type=FHIR_JSON)

    # Create an observation — should trigger the subscription
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
    }
    client.post("/fhir/Observation", data=json.dumps(obs), content_type=FHIR_JSON)

    # Verify notification was sent
    assert mock_send.called
    call_args = mock_send.call_args
    assert call_args[0][0] == "http://example.com/hook"


@patch("app.fhir.subscriptions.SubscriptionManager._send_notification")
def test_subscription_does_not_trigger_for_non_matching(mock_send, client):
    """Non-matching resource type should not trigger subscription."""
    sub = {
        "resourceType": "Subscription",
        "status": "active",
        "criteria": "Observation",
        "channel": {"type": "rest-hook", "endpoint": "http://example.com/hook"},
    }
    client.post("/fhir/Subscription", data=json.dumps(sub), content_type=FHIR_JSON)

    # Create a Patient — should NOT trigger the Observation subscription
    patient = {
        "resourceType": "Patient",
        "name": [{"family": "Test"}],
    }
    client.post("/fhir/Patient", data=json.dumps(patient), content_type=FHIR_JSON)

    assert not mock_send.called


@patch("app.fhir.subscriptions.SubscriptionManager._send_notification")
def test_inactive_subscription_does_not_trigger(mock_send, client):
    """Inactive subscription should not trigger."""
    sub = {
        "resourceType": "Subscription",
        "status": "off",
        "criteria": "Observation",
        "channel": {"type": "rest-hook", "endpoint": "http://example.com/hook"},
    }
    client.post("/fhir/Subscription", data=json.dumps(sub), content_type=FHIR_JSON)

    obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
    }
    client.post("/fhir/Observation", data=json.dumps(obs), content_type=FHIR_JSON)

    assert not mock_send.called
