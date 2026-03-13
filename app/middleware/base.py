from app.api.errors import FHIRError


class FHIRInterceptor:
    """Base class for FHIR server interceptors with no-op defaults."""

    def before_create(self, resource_type, resource_data):
        """Called before a resource is created. Can modify or reject."""
        pass

    def after_create(self, resource_type, resource_data, fhir_id):
        """Called after a resource is created."""
        pass

    def before_update(self, resource_type, fhir_id, resource_data):
        """Called before a resource is updated."""
        pass

    def after_update(self, resource_type, fhir_id, resource_data):
        """Called after a resource is updated."""
        pass

    def before_delete(self, resource_type, fhir_id):
        """Called before a resource is deleted."""
        pass

    def after_delete(self, resource_type, fhir_id):
        """Called after a resource is deleted."""
        pass

    def before_read(self, resource_type, fhir_id):
        """Called before a resource is read."""
        pass

    def after_read(self, resource_type, fhir_id, resource_data):
        """Called after a resource is read."""
        pass

    def before_search(self, resource_type, params):
        """Called before a search is executed."""
        pass

    def after_search(self, resource_type, results, total):
        """Called after a search is executed."""
        pass


def _check_rejection(result):
    """Check if an interceptor hook returned a FHIRError to short-circuit."""
    if isinstance(result, FHIRError):
        raise result


class InterceptorChain:
    """Manages ordered list of interceptors."""

    def __init__(self):
        self._interceptors: list[FHIRInterceptor] = []

    def register(self, interceptor: FHIRInterceptor):
        self._interceptors.append(interceptor)

    def fire_before_create(self, resource_type, resource_data):
        for i in self._interceptors:
            result = i.before_create(resource_type, resource_data)
            _check_rejection(result)

    def fire_after_create(self, resource_type, resource_data, fhir_id):
        for i in self._interceptors:
            i.after_create(resource_type, resource_data, fhir_id)

    def fire_before_update(self, resource_type, fhir_id, resource_data):
        for i in self._interceptors:
            result = i.before_update(resource_type, fhir_id, resource_data)
            _check_rejection(result)

    def fire_after_update(self, resource_type, fhir_id, resource_data):
        for i in self._interceptors:
            i.after_update(resource_type, fhir_id, resource_data)

    def fire_before_delete(self, resource_type, fhir_id):
        for i in self._interceptors:
            result = i.before_delete(resource_type, fhir_id)
            _check_rejection(result)

    def fire_after_delete(self, resource_type, fhir_id):
        for i in self._interceptors:
            i.after_delete(resource_type, fhir_id)

    def fire_before_read(self, resource_type, fhir_id):
        for i in self._interceptors:
            result = i.before_read(resource_type, fhir_id)
            _check_rejection(result)

    def fire_after_read(self, resource_type, fhir_id, resource_data):
        for i in self._interceptors:
            i.after_read(resource_type, fhir_id, resource_data)

    def fire_before_search(self, resource_type, params):
        for i in self._interceptors:
            result = i.before_search(resource_type, params)
            _check_rejection(result)

    def fire_after_search(self, resource_type, results, total):
        for i in self._interceptors:
            i.after_search(resource_type, results, total)


# Singleton chain — registered in create_app()
interceptor_chain = InterceptorChain()
