"""Subscription evaluation and notification (REST-hook channel type)."""

import json
import logging
import threading

from app.models.resource import ResourceEntity

logger = logging.getLogger("fhir.subscriptions")


class SubscriptionManager:
    """Evaluates active subscriptions against resource changes and sends REST-hook POST."""

    def evaluate(self, resource_type, resource_data, fhir_id):
        """Check all active subscriptions and notify matching ones.

        Called after create/update events.
        """
        from app.extensions import db

        subscriptions = ResourceEntity.query.filter_by(
            res_type="Subscription", is_deleted=False
        ).all()

        for sub_entity in subscriptions:
            sub = json.loads(sub_entity.res_text)
            if sub.get("status") != "active":
                continue

            criteria = sub.get("criteria", "")
            channel = sub.get("channel", {})
            channel_type = channel.get("type", "")

            if channel_type != "rest-hook":
                continue

            endpoint = channel.get("endpoint")
            if not endpoint:
                continue

            # Evaluate criteria: simple format "ResourceType?param=value"
            if not self._matches_criteria(criteria, resource_type, resource_data):
                continue

            # Send notification in a background thread to avoid blocking
            payload = json.dumps(resource_data)
            headers = {"Content-Type": "application/fhir+json"}

            # Add custom headers from channel
            for header_str in channel.get("header", []):
                if ":" in header_str:
                    key, val = header_str.split(":", 1)
                    headers[key.strip()] = val.strip()

            self._send_notification(endpoint, payload, headers, sub.get("id", ""))

    def _matches_criteria(self, criteria, resource_type, resource_data):
        """Check if a resource matches subscription criteria.

        Supports simple criteria format: "ResourceType" or "ResourceType?param=value"
        """
        if not criteria:
            return False

        # Parse criteria
        if "?" in criteria:
            crit_type, crit_params = criteria.split("?", 1)
        else:
            crit_type = criteria
            crit_params = ""

        if crit_type != resource_type:
            return False

        # If no additional params, type match is sufficient
        if not crit_params:
            return True

        # Simple parameter matching (basic implementation)
        for param_str in crit_params.split("&"):
            if "=" not in param_str:
                continue
            param_name, param_value = param_str.split("=", 1)

            # Check common patterns
            actual_value = self._get_resource_value(resource_data, param_name)
            if actual_value is None:
                return False
            if str(actual_value) != param_value:
                return False

        return True

    def _get_resource_value(self, resource_data, param_name):
        """Get a simple value from a resource for criteria matching."""
        # Direct field access for simple cases
        if param_name in resource_data:
            val = resource_data[param_name]
            if isinstance(val, str):
                return val
            return val

        # Check nested paths (e.g., code.coding[0].code)
        return None

    def _send_notification(self, endpoint, payload, headers, sub_id):
        """Send REST-hook notification. Non-blocking."""
        def _do_send():
            try:
                import requests as req_lib
                resp = req_lib.post(
                    endpoint,
                    data=payload,
                    headers=headers,
                    timeout=10,
                )
                logger.info(
                    "Subscription %s notification to %s: %d",
                    sub_id, endpoint, resp.status_code,
                )
            except Exception as e:
                logger.warning(
                    "Subscription %s notification to %s failed: %s",
                    sub_id, endpoint, str(e),
                )

        thread = threading.Thread(target=_do_send, daemon=True)
        thread.start()


subscription_manager = SubscriptionManager()
