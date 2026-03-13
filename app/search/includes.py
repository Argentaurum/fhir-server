"""_include / _revinclude support."""

import json
from app.extensions import db
from app.models.resource import ResourceEntity
from app.models.resource_link import ResourceLink


def resolve_includes(resource_entities, include_params, base_url):
    """Resolve _include parameters and return additional Bundle entries.

    include_params: list of strings like "Observation:patient" or "Observation:encounter:Encounter"
    """
    if not include_params:
        return []

    resource_ids = [e.id for e in resource_entities]
    if not resource_ids:
        return []

    included = []
    seen = set()

    for inc in include_params:
        parts = inc.split(":")
        if len(parts) < 2:
            continue

        src_type = parts[0]
        param_name = parts[1]
        target_type = parts[2] if len(parts) > 2 else None

        # Find links from these resources
        link_query = (
            db.session.query(ResourceLink)
            .filter(ResourceLink.src_resource_id.in_(resource_ids))
        )

        if target_type:
            link_query = link_query.filter(
                ResourceLink.target_resource_type == target_type
            )

        for link in link_query.all():
            key = (link.target_resource_type, link.target_fhir_id)
            if key in seen:
                continue
            seen.add(key)

            target = ResourceEntity.query.filter_by(
                res_type=link.target_resource_type,
                fhir_id=link.target_fhir_id,
                is_deleted=False,
            ).first()

            if target:
                resource_data = json.loads(target.res_text)
                included.append({
                    "fullUrl": f"{base_url}/{link.target_resource_type}/{link.target_fhir_id}",
                    "resource": resource_data,
                    "search": {"mode": "include"},
                })

    return included


def resolve_revincludes(resource_entities, revinclude_params, base_url):
    """Resolve _revinclude parameters.

    revinclude_params: list of strings like "Observation:patient"
    """
    if not revinclude_params:
        return []

    # Build a set of (type, id) for the main results
    target_keys = set()
    for e in resource_entities:
        target_keys.add((e.res_type, e.fhir_id))

    if not target_keys:
        return []

    included = []
    seen = set()

    for revinc in revinclude_params:
        parts = revinc.split(":")
        if len(parts) < 2:
            continue

        src_type = parts[0]
        param_name = parts[1]

        for target_type, target_id in target_keys:
            links = (
                db.session.query(ResourceLink)
                .join(ResourceEntity, ResourceLink.src_resource_id == ResourceEntity.id)
                .filter(
                    ResourceEntity.res_type == src_type,
                    ResourceEntity.is_deleted == False,  # noqa: E712
                    ResourceLink.target_resource_type == target_type,
                    ResourceLink.target_fhir_id == target_id,
                )
                .all()
            )

            for link in links:
                if link.src_resource_id in seen:
                    continue
                seen.add(link.src_resource_id)

                src = ResourceEntity.query.get(link.src_resource_id)
                if src and not src.is_deleted:
                    resource_data = json.loads(src.res_text)
                    included.append({
                        "fullUrl": f"{base_url}/{src.res_type}/{src.fhir_id}",
                        "resource": resource_data,
                        "search": {"mode": "include"},
                    })

    return included
