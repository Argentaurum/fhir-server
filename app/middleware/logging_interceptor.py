import logging
from app.middleware.base import FHIRInterceptor

logger = logging.getLogger("fhir.interceptor.logging")


class LoggingInterceptor(FHIRInterceptor):
    def before_create(self, resource_type, resource_data):
        logger.info("CREATE %s", resource_type)

    def after_create(self, resource_type, resource_data, fhir_id):
        logger.info("CREATED %s/%s", resource_type, fhir_id)

    def before_update(self, resource_type, fhir_id, resource_data):
        logger.info("UPDATE %s/%s", resource_type, fhir_id)

    def after_update(self, resource_type, fhir_id, resource_data):
        logger.info("UPDATED %s/%s", resource_type, fhir_id)

    def before_delete(self, resource_type, fhir_id):
        logger.info("DELETE %s/%s", resource_type, fhir_id)

    def after_delete(self, resource_type, fhir_id):
        logger.info("DELETED %s/%s", resource_type, fhir_id)

    def before_read(self, resource_type, fhir_id):
        logger.debug("READ %s/%s", resource_type, fhir_id)

    def after_read(self, resource_type, fhir_id, resource_data):
        logger.debug("READ complete %s/%s", resource_type, fhir_id)

    def before_search(self, resource_type, params):
        logger.debug("SEARCH %s", resource_type)

    def after_search(self, resource_type, results, total):
        logger.debug("SEARCH %s returned %d results", resource_type, total)
