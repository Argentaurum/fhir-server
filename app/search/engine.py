"""Orchestrates FHIR search."""

import json
from app.search.query_builder import SearchQueryBuilder
from app.search.param_parser import parse_search_params
from app.search.includes import resolve_includes, resolve_revincludes
from app.fhir.summary import apply_summary, apply_elements


class SearchEngine:
    """High-level search orchestrator."""

    def search(self, resource_type, raw_params, count=20, offset=0, sort_params=None):
        """Execute a search and return (resource_dicts, total_count, include_entries, entities).

        Args:
            resource_type: FHIR resource type
            raw_params: Flask request.args (ImmutableMultiDict)
            count: max results
            offset: pagination offset
            sort_params: _sort value (can also come from raw_params)

        Returns:
            (results, total, include_entries, entities)
        """
        parsed, control = parse_search_params(resource_type, raw_params)

        effective_count = control.get("_count", count)
        effective_offset = control.get("_offset", offset)
        effective_sort = control.get("_sort", sort_params)
        summary_mode = control.get("_summary")
        elements = control.get("_elements")

        # Filter out _has params for special handling
        has_params = [p for p in parsed if p.type == "_has"]
        regular_params = [p for p in parsed if p.type not in ("_has",)]

        builder = SearchQueryBuilder(resource_type)
        query, count_query = builder.build(
            regular_params, effective_count, effective_offset, effective_sort,
            has_params=has_params,
        )

        total = count_query.scalar()

        # For _summary=count, return only the total
        if summary_mode == "count":
            return [], total, [], []

        entities = query.all()

        # Resolve includes
        base_url = ""  # Will be set by caller
        include_entries = resolve_includes(
            entities, control.get("_include", []), base_url
        )
        include_entries.extend(
            resolve_revincludes(
                entities, control.get("_revinclude", []), base_url
            )
        )

        # Convert entities to resource dicts
        results = [json.loads(e.res_text) for e in entities]

        # Apply _summary / _elements filtering
        if summary_mode and summary_mode != "false":
            results = [apply_summary(r, summary_mode) for r in results]
        elif elements:
            results = [apply_elements(r, elements) for r in results]

        return results, total, include_entries, entities
