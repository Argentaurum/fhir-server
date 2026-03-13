"""Interceptor that triggers subscription evaluation after create/update."""

import logging
from app.middleware.base import FHIRInterceptor

logger = logging.getLogger("fhir.interceptor.subscription")


class SubscriptionInterceptor(FHIRInterceptor):
    """Hooks into after_create and after_update to evaluate subscriptions."""

    def after_create(self, resource_type, resource_data, fhir_id):
        if resource_type == "Subscription":
            return  # Don't trigger subscriptions for Subscription resources themselves
        self._evaluate(resource_type, resource_data, fhir_id)

    def after_update(self, resource_type, fhir_id, resource_data):
        if resource_type == "Subscription":
            return
        self._evaluate(resource_type, resource_data, fhir_id)

    def _evaluate(self, resource_type, resource_data, fhir_id):
        try:
            from app.fhir.subscriptions import subscription_manager
            subscription_manager.evaluate(resource_type, resource_data, fhir_id)
        except Exception as e:
            logger.warning("Subscription evaluation failed: %s", str(e))
