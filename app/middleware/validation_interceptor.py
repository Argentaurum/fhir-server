from app.middleware.base import FHIRInterceptor
from app.fhir.validator import validate_resource


class ValidationInterceptor(FHIRInterceptor):
    def before_create(self, resource_type, resource_data):
        validate_resource(resource_type, resource_data)

    def before_update(self, resource_type, fhir_id, resource_data):
        validate_resource(resource_type, resource_data)
