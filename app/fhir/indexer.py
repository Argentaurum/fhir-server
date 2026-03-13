"""Search parameter indexer.

Extracts values from FHIR JSON and writes typed index rows.
Handles complex FHIR types: CodeableConcept → token, HumanName → string,
Period → date range, Quantity → quantity, Reference → resource link.
"""

import logging

from app.extensions import db
from app.models.search_index import StringIndex, TokenIndex, DateIndex, QuantityIndex, CompositeIndex
from app.models.resource_link import ResourceLink
from app.fhir.search_params import get_search_params, get_composite_params
from app.utils.datetime_utils import parse_fhir_date_to_range

logger = logging.getLogger("fhir.indexer")


class SearchParamIndexer:
    """Extracts search parameter values from a FHIR resource and creates index rows."""

    def reindex(self, resource_entity):
        """Delete existing indexes and recreate from current resource JSON."""
        import json

        resource_data = json.loads(resource_entity.res_text)
        res_type = resource_entity.res_type
        res_id = resource_entity.id

        # Delete existing indexes
        StringIndex.query.filter_by(resource_id=res_id).delete()
        TokenIndex.query.filter_by(resource_id=res_id).delete()
        DateIndex.query.filter_by(resource_id=res_id).delete()
        QuantityIndex.query.filter_by(resource_id=res_id).delete()
        CompositeIndex.query.filter_by(resource_id=res_id).delete()
        ResourceLink.query.filter_by(src_resource_id=res_id).delete()

        params = get_search_params(res_type)
        for param_def in params:
            param_name = param_def["name"]
            param_type = param_def["type"]
            paths = param_def["paths"]

            for path in paths:
                values = self._extract_values(resource_data, path)
                for val in values:
                    if param_type == "string":
                        self._index_string(res_id, res_type, param_name, val)
                    elif param_type == "token":
                        self._index_token(res_id, res_type, param_name, val)
                    elif param_type == "date":
                        self._index_date(res_id, res_type, param_name, val)
                    elif param_type == "quantity":
                        self._index_quantity(res_id, res_type, param_name, val)
                    elif param_type == "reference":
                        self._index_reference(
                            res_id, res_type, param_name, val,
                            path, param_def.get("target", []),
                        )

        # Index meta.tag, meta.security, meta.profile
        self._index_meta(res_id, res_type, resource_data)

        # Index composite search parameters
        self._index_composites(res_id, res_type, resource_data)

    def _extract_values(self, data, path):
        """Walk a dotted path through FHIR JSON, returning all leaf values.

        Handles arrays at any level. E.g., "name.family" on Patient returns
        all family names.
        """
        parts = path.split(".")
        current = [data]

        for part in parts:
            next_level = []
            for item in current:
                if isinstance(item, dict):
                    val = item.get(part)
                    if val is not None:
                        if isinstance(val, list):
                            next_level.extend(val)
                        else:
                            next_level.append(val)
                elif isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, dict):
                            val = sub.get(part)
                            if val is not None:
                                if isinstance(val, list):
                                    next_level.extend(val)
                                else:
                                    next_level.append(val)
            current = next_level

        return current

    def _index_string(self, resource_id, res_type, param_name, value):
        """Index a string value. Handles plain strings and HumanName-like objects."""
        strings = self._to_string_values(value)
        for s in strings:
            if s:
                db.session.add(StringIndex(
                    resource_id=resource_id,
                    res_type=res_type,
                    param_name=param_name,
                    value_normalized=s.lower(),
                    value_exact=s,
                ))

    def _to_string_values(self, value):
        """Convert a value to a list of indexable strings."""
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            # Could be a HumanName, Address, or similar complex type
            results = []
            for key in ("text", "family", "given", "prefix", "suffix",
                        "line", "city", "state", "postalCode", "country"):
                v = value.get(key)
                if v:
                    if isinstance(v, list):
                        results.extend(str(x) for x in v)
                    else:
                        results.append(str(v))
            if not results:
                # Generic: try "value" or "display"
                for key in ("value", "display"):
                    v = value.get(key)
                    if v:
                        results.append(str(v))
            return results
        if isinstance(value, (int, float, bool)):
            return [str(value)]
        return []

    def _index_token(self, resource_id, res_type, param_name, value):
        """Index a token value. Handles code strings, CodeableConcept, Coding,
        Identifier, booleans, and ContactPoint.
        """
        tokens = self._to_token_values(value)
        for system, code in tokens:
            db.session.add(TokenIndex(
                resource_id=resource_id,
                res_type=res_type,
                param_name=param_name,
                system=system,
                value=code,
            ))

    def _to_token_values(self, value):
        """Convert a value to (system, code) tuples."""
        if isinstance(value, str):
            return [(None, value)]
        if isinstance(value, bool):
            return [(None, str(value).lower())]
        if isinstance(value, dict):
            # CodeableConcept
            if "coding" in value:
                results = []
                for coding in value["coding"]:
                    results.append((coding.get("system"), coding.get("code")))
                # Also index the text
                if value.get("text"):
                    results.append((None, value["text"]))
                return results
            # Coding
            if "system" in value and "code" in value:
                return [(value.get("system"), value.get("code"))]
            # Identifier
            if "value" in value:
                return [(value.get("system"), value.get("value"))]
            # ContactPoint (telecom)
            if "system" in value and "value" in value:
                return [(value.get("system"), value.get("value"))]
        if isinstance(value, list):
            results = []
            for item in value:
                results.extend(self._to_token_values(item))
            return results
        return []

    def _index_date(self, resource_id, res_type, param_name, value):
        """Index a date/dateTime/Period value."""
        if isinstance(value, str):
            low, high = parse_fhir_date_to_range(value)
            if low:
                db.session.add(DateIndex(
                    resource_id=resource_id,
                    res_type=res_type,
                    param_name=param_name,
                    value_low=low,
                    value_high=high,
                ))
        elif isinstance(value, dict):
            # Period
            start = value.get("start")
            end = value.get("end")
            if start:
                low, _ = parse_fhir_date_to_range(start)
                _, high = parse_fhir_date_to_range(end) if end else (None, None)
                if not high:
                    _, high = parse_fhir_date_to_range(start)
                if low:
                    db.session.add(DateIndex(
                        resource_id=resource_id,
                        res_type=res_type,
                        param_name=param_name,
                        value_low=low,
                        value_high=high,
                    ))

    def _index_quantity(self, resource_id, res_type, param_name, value):
        """Index a Quantity value."""
        if isinstance(value, dict) and "value" in value:
            try:
                num_value = float(value["value"])
            except (ValueError, TypeError):
                return
            db.session.add(QuantityIndex(
                resource_id=resource_id,
                res_type=res_type,
                param_name=param_name,
                system=value.get("system"),
                units=value.get("unit") or value.get("code"),
                value=num_value,
            ))

    def _index_reference(self, resource_id, res_type, param_name, value,
                         path, target_types):
        """Index a Reference value and create a ResourceLink."""
        ref_str = None
        if isinstance(value, dict):
            ref_str = value.get("reference")
        elif isinstance(value, str):
            ref_str = value

        if not ref_str:
            return

        # Parse "ResourceType/id" format
        target_type, target_id = self._parse_reference(ref_str)
        if not target_type or not target_id:
            return

        # Create the resource link
        src_path = f"{res_type}.{path}" if "." not in path else f"{res_type}.{path.split('.')[0]}"
        db.session.add(ResourceLink(
            src_resource_id=resource_id,
            src_path=src_path,
            target_resource_type=target_type,
            target_fhir_id=target_id,
        ))

        # Also create a token index entry for the reference param
        db.session.add(TokenIndex(
            resource_id=resource_id,
            res_type=res_type,
            param_name=param_name,
            system=None,
            value=f"{target_type}/{target_id}",
        ))

    def _index_composites(self, resource_id, res_type, resource_data):
        """Index composite search parameters."""
        composite_defs = get_composite_params(res_type)
        for comp_def in composite_defs:
            comp_name = comp_def["name"]
            components = comp_def["components"]
            if len(components) < 2:
                continue

            comp1_def = components[0]
            comp2_def = components[1]

            # Extract values for each component
            comp1_values = []
            for path in comp1_def["paths"]:
                raw = self._extract_values(resource_data, path)
                for val in raw:
                    tokens = self._to_token_values(val)
                    comp1_values.extend(tokens)

            comp2_values = []
            for path in comp2_def["paths"]:
                raw = self._extract_values(resource_data, path)
                for val in raw:
                    if comp2_def["type"] == "token":
                        tokens = self._to_token_values(val)
                        comp2_values.extend(tokens)
                    elif comp2_def["type"] == "quantity":
                        if isinstance(val, dict) and "value" in val:
                            try:
                                num = str(float(val["value"]))
                            except (ValueError, TypeError):
                                continue
                            comp2_values.append((val.get("system"), num))

            # Create cross-product of comp1 x comp2
            for sys1, val1 in comp1_values:
                for sys2, val2 in comp2_values:
                    if val1 and val2:
                        db.session.add(CompositeIndex(
                            resource_id=resource_id,
                            res_type=res_type,
                            param_name=comp_name,
                            comp1_system=sys1,
                            comp1_value=val1,
                            comp2_system=sys2,
                            comp2_value=val2,
                        ))

    def _index_meta(self, resource_id, res_type, resource_data):
        """Index meta.tag, meta.security, meta.profile as tokens."""
        meta = resource_data.get("meta", {})

        # meta.tag — array of Coding
        for tag in meta.get("tag", []):
            if isinstance(tag, dict):
                system = tag.get("system")
                code = tag.get("code")
                if code:
                    db.session.add(TokenIndex(
                        resource_id=resource_id, res_type=res_type,
                        param_name="_tag", system=system, value=code,
                    ))

        # meta.security — array of Coding
        for sec in meta.get("security", []):
            if isinstance(sec, dict):
                system = sec.get("system")
                code = sec.get("code")
                if code:
                    db.session.add(TokenIndex(
                        resource_id=resource_id, res_type=res_type,
                        param_name="_security", system=system, value=code,
                    ))

        # meta.profile — array of canonical URLs (strings)
        for profile in meta.get("profile", []):
            if isinstance(profile, str):
                db.session.add(TokenIndex(
                    resource_id=resource_id, res_type=res_type,
                    param_name="_profile", system=None, value=profile,
                ))

    def _parse_reference(self, ref_str):
        """Parse a FHIR reference string into (type, id)."""
        if "/" in ref_str:
            # Could be "Patient/123" or "http://example.com/fhir/Patient/123"
            parts = ref_str.rstrip("/").rsplit("/", 2)
            if len(parts) >= 2:
                return parts[-2], parts[-1]
        return None, None


# Module-level singleton
indexer = SearchParamIndexer()
