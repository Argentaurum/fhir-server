"""SQLAlchemy implementation of the FHIR Resource DAO."""

import json
import uuid
from datetime import datetime, timezone

from app.extensions import db
from app.models.resource import ResourceEntity
from app.models.resource_history import ResourceHistory
from app.fhir.indexer import indexer
from app.api.errors import (
    ResourceNotFoundError, ResourceGoneError, PreconditionFailedError, BadRequestError,
)
from app.middleware.base import interceptor_chain


class ResourceDAO:
    """SQLAlchemy-based FHIR resource DAO."""

    def create(self, resource_type, resource_data, fhir_id=None):
        """Create a new resource."""
        interceptor_chain.fire_before_create(resource_type, resource_data)

        if fhir_id is None:
            fhir_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc)

        # Set meta fields
        resource_data["id"] = fhir_id
        resource_data["resourceType"] = resource_type
        resource_data.setdefault("meta", {})
        resource_data["meta"]["versionId"] = "1"
        resource_data["meta"]["lastUpdated"] = now.isoformat()

        entity = ResourceEntity(
            fhir_id=fhir_id,
            res_type=resource_type,
            version_id=1,
            res_text=json.dumps(resource_data),
            last_updated=now,
            is_deleted=False,
        )
        db.session.add(entity)
        db.session.flush()  # Get the entity.id

        # Create initial history record
        history = ResourceHistory(
            resource_id=entity.id,
            fhir_id=fhir_id,
            res_type=resource_type,
            version_id=1,
            res_text=entity.res_text,
            timestamp=now,
        )
        db.session.add(history)

        # Index search parameters
        indexer.reindex(entity)

        db.session.commit()

        interceptor_chain.fire_after_create(resource_type, resource_data, fhir_id)
        return resource_data, fhir_id, 1

    def read(self, resource_type, fhir_id):
        """Read a resource by type and id."""
        interceptor_chain.fire_before_read(resource_type, fhir_id)

        entity = ResourceEntity.query.filter_by(
            res_type=resource_type, fhir_id=fhir_id
        ).first()

        if entity is None:
            raise ResourceNotFoundError(resource_type, fhir_id)

        if entity.is_deleted:
            raise ResourceGoneError(resource_type, fhir_id)

        resource_data = json.loads(entity.res_text)
        interceptor_chain.fire_after_read(resource_type, fhir_id, resource_data)
        return resource_data

    def update(self, resource_type, fhir_id, resource_data):
        """Update an existing resource."""
        entity = ResourceEntity.query.filter_by(
            res_type=resource_type, fhir_id=fhir_id
        ).first()

        if entity is None:
            raise ResourceNotFoundError(resource_type, fhir_id)

        interceptor_chain.fire_before_update(resource_type, fhir_id, resource_data)

        now = datetime.now(timezone.utc)
        new_version = entity.version_id + 1

        # Update meta
        resource_data["id"] = fhir_id
        resource_data["resourceType"] = resource_type
        resource_data.setdefault("meta", {})
        resource_data["meta"]["versionId"] = str(new_version)
        resource_data["meta"]["lastUpdated"] = now.isoformat()

        entity.version_id = new_version
        entity.res_text = json.dumps(resource_data)
        entity.last_updated = now
        entity.is_deleted = False

        # Save history
        history = ResourceHistory(
            resource_id=entity.id,
            fhir_id=fhir_id,
            res_type=resource_type,
            version_id=new_version,
            res_text=entity.res_text,
            timestamp=now,
        )
        db.session.add(history)

        # Re-index
        indexer.reindex(entity)

        db.session.commit()

        interceptor_chain.fire_after_update(resource_type, fhir_id, resource_data)
        return resource_data, new_version

    def delete(self, resource_type, fhir_id):
        """Soft-delete a resource."""
        entity = ResourceEntity.query.filter_by(
            res_type=resource_type, fhir_id=fhir_id
        ).first()

        if entity is None:
            raise ResourceNotFoundError(resource_type, fhir_id)

        interceptor_chain.fire_before_delete(resource_type, fhir_id)

        now = datetime.now(timezone.utc)
        new_version = entity.version_id + 1

        entity.is_deleted = True
        entity.version_id = new_version
        entity.last_updated = now

        # Save deletion in history
        history = ResourceHistory(
            resource_id=entity.id,
            fhir_id=fhir_id,
            res_type=resource_type,
            version_id=new_version,
            res_text=entity.res_text,
            timestamp=now,
        )
        db.session.add(history)

        # Remove indexes
        from app.models.search_index import StringIndex, TokenIndex, DateIndex, QuantityIndex, CompositeIndex
        from app.models.resource_link import ResourceLink
        StringIndex.query.filter_by(resource_id=entity.id).delete()
        TokenIndex.query.filter_by(resource_id=entity.id).delete()
        DateIndex.query.filter_by(resource_id=entity.id).delete()
        QuantityIndex.query.filter_by(resource_id=entity.id).delete()
        CompositeIndex.query.filter_by(resource_id=entity.id).delete()
        ResourceLink.query.filter_by(src_resource_id=entity.id).delete()

        db.session.commit()

        interceptor_chain.fire_after_delete(resource_type, fhir_id)

    def vread(self, resource_type, fhir_id, version_id):
        """Read a specific version of a resource."""
        history = ResourceHistory.query.filter_by(
            res_type=resource_type,
            fhir_id=fhir_id,
            version_id=version_id,
        ).first()

        if history is None:
            raise ResourceNotFoundError(
                resource_type, f"{fhir_id}/_history/{version_id}"
            )

        return json.loads(history.res_text)

    def history(self, resource_type, fhir_id):
        """Get version history for a resource."""
        entity = ResourceEntity.query.filter_by(
            res_type=resource_type, fhir_id=fhir_id
        ).first()

        if entity is None:
            raise ResourceNotFoundError(resource_type, fhir_id)

        versions = (
            ResourceHistory.query
            .filter_by(resource_id=entity.id)
            .order_by(ResourceHistory.version_id.desc())
            .all()
        )

        return self._build_history_entries(versions, resource_type)

    def type_history(self, resource_type, count=20, offset=0):
        """Get history for all resources of a given type."""
        query = (
            ResourceHistory.query
            .filter_by(res_type=resource_type)
            .order_by(ResourceHistory.timestamp.desc())
        )
        total = query.count()
        versions = query.offset(offset).limit(count).all()
        entries = self._build_history_entries(versions, resource_type)
        return entries, total

    def system_history(self, count=20, offset=0):
        """Get history for all resources in the system."""
        query = (
            ResourceHistory.query
            .order_by(ResourceHistory.timestamp.desc())
        )
        total = query.count()
        versions = query.offset(offset).limit(count).all()
        entries = self._build_history_entries(versions)
        return entries, total

    def _build_history_entries(self, versions, resource_type=None):
        """Build bundle entries from a list of ResourceHistory records."""
        entries = []
        for v in versions:
            rt = resource_type or v.res_type
            resource_data = json.loads(v.res_text)
            method = "POST" if v.version_id == 1 else "PUT"
            entries.append({
                "fullUrl": f"{rt}/{v.fhir_id}",
                "resource": resource_data,
                "request": {
                    "method": method,
                    "url": f"{rt}/{v.fhir_id}",
                },
                "response": {
                    "status": "200",
                    "lastModified": v.timestamp.isoformat(),
                },
            })
        return entries

    def search(self, resource_type, search_params, count=20, offset=0, sort_params=None):
        """Search for resources using the search engine."""
        from app.search.engine import SearchEngine
        engine = SearchEngine()
        return engine.search(resource_type, search_params, count, offset, sort_params)

    def conditional_create(self, resource_type, resource_data, search_params):
        """Create only if no existing match (ifNoneExist)."""
        results, total = self.search(resource_type, search_params, count=1)
        if total > 0:
            # Already exists — return existing
            return json.loads(results[0].res_text) if hasattr(results[0], 'res_text') else results[0], False
        data, fhir_id, vid = self.create(resource_type, resource_data)
        return data, True

    def conditional_update(self, resource_type, resource_data, search_params):
        """Conditional update: PUT /<type>?search_params.

        0 matches → create, 1 match → update, 2+ matches → 412.
        Returns (resource_data, version_id, created: bool).
        """
        from app.search.engine import SearchEngine
        engine = SearchEngine()
        results, total, _, entities = engine.search(resource_type, search_params, count=2)

        if total == 0:
            data, fhir_id, vid = self.create(resource_type, resource_data)
            return data, vid, True
        elif total == 1:
            fhir_id = results[0]["id"]
            resource_data["id"] = fhir_id
            data, vid = self.update(resource_type, fhir_id, resource_data)
            return data, vid, False
        else:
            raise PreconditionFailedError(
                f"Conditional update matched {total} resources for {resource_type}"
            )

    def conditional_delete(self, resource_type, search_params):
        """Conditional delete: DELETE /<type>?search_params.

        Deletes all matching resources. Requires at least one search param.
        Returns number of deleted resources.
        """
        from app.search.engine import SearchEngine
        engine = SearchEngine()
        results, total, _, entities = engine.search(resource_type, search_params, count=1000)

        count = 0
        for resource in results:
            fhir_id = resource["id"]
            try:
                self.delete(resource_type, fhir_id)
                count += 1
            except (ResourceNotFoundError, ResourceGoneError):
                pass
        return count

    def patch(self, resource_type, fhir_id, patch_operations):
        """Apply a JSON Patch (RFC 6902) to a resource.

        Args:
            resource_type: FHIR resource type
            fhir_id: resource id
            patch_operations: list of patch operations (RFC 6902)

        Returns:
            (resource_data, version_id)
        """
        import jsonpatch

        current = self.read(resource_type, fhir_id)
        patch = jsonpatch.JsonPatch(patch_operations)
        patched = patch.apply(current)

        # Preserve resourceType and id
        patched["resourceType"] = resource_type
        patched["id"] = fhir_id

        return self.update(resource_type, fhir_id, patched)


# Module-level singleton
resource_dao = ResourceDAO()
