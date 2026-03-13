"""Abstract DAO interface for FHIR resources."""

from abc import ABC, abstractmethod


class BaseResourceDAO(ABC):
    @abstractmethod
    def create(self, resource_type, resource_data, fhir_id=None):
        """Create a new resource. Returns (resource_data_with_meta, fhir_id, version_id)."""

    @abstractmethod
    def read(self, resource_type, fhir_id):
        """Read a resource by type and id. Returns resource_data dict."""

    @abstractmethod
    def update(self, resource_type, fhir_id, resource_data):
        """Update an existing resource. Returns (resource_data_with_meta, version_id)."""

    @abstractmethod
    def delete(self, resource_type, fhir_id):
        """Soft-delete a resource."""

    @abstractmethod
    def search(self, resource_type, params, count=20, offset=0, sort_params=None):
        """Search for resources. Returns (list_of_resource_dicts, total_count)."""

    @abstractmethod
    def vread(self, resource_type, fhir_id, version_id):
        """Read a specific version of a resource."""

    @abstractmethod
    def history(self, resource_type, fhir_id):
        """Get version history for a resource."""
