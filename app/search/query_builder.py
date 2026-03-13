"""Builds SQLAlchemy queries from parsed search parameters."""

from sqlalchemy import and_, or_, func

from app.extensions import db
from app.models.resource import ResourceEntity
from app.models.search_index import StringIndex, TokenIndex, DateIndex, QuantityIndex, CompositeIndex
from app.models.resource_link import ResourceLink
from app.utils.datetime_utils import parse_fhir_date_to_range


class SearchQueryBuilder:
    """Builds a SQLAlchemy query for FHIR resource search."""

    def __init__(self, resource_type):
        self.resource_type = resource_type
        self._join_counter = 0

    def build(self, parsed_params, count=20, offset=0, sort_param=None, has_params=None):
        """Build and return (query, count_query) for the given params."""
        query = (
            db.session.query(ResourceEntity)
            .filter(ResourceEntity.res_type == self.resource_type)
            .filter(ResourceEntity.is_deleted == False)  # noqa: E712
        )

        for param in parsed_params:
            if param.chain:
                query = self._apply_chain(query, param)
            elif param.type == "string":
                query = self._apply_string(query, param)
            elif param.type == "token":
                query = self._apply_token(query, param)
            elif param.type == "date":
                query = self._apply_date(query, param)
            elif param.type == "quantity":
                query = self._apply_quantity(query, param)
            elif param.type == "reference":
                query = self._apply_reference(query, param)
            elif param.type == "composite":
                query = self._apply_composite(query, param)

        # Apply _has filters before pagination
        for has_param in (has_params or []):
            query = self._apply_has(query, has_param)

        # Count before pagination
        count_query = query.with_entities(func.count(ResourceEntity.id))

        # Sorting
        if sort_param:
            query = self._apply_sort(query, sort_param)
        else:
            query = query.order_by(ResourceEntity.last_updated.desc())

        # Pagination
        query = query.offset(offset).limit(count)

        return query, count_query

    def _next_alias(self, model):
        """Create a unique alias for joined tables."""
        self._join_counter += 1
        return model.__table__.alias(f"idx_{self._join_counter}")

    def _apply_string(self, query, param):
        """Apply a string search parameter."""
        alias = self._next_alias(StringIndex)

        conditions = [
            alias.c.resource_id == ResourceEntity.id,
            alias.c.res_type == self.resource_type,
            alias.c.param_name == param.name,
        ]

        value_conditions = []
        for value in param.values:
            if param.modifier == "exact":
                value_conditions.append(alias.c.value_exact == value)
            elif param.modifier == "contains":
                value_conditions.append(
                    alias.c.value_normalized.like(f"%{value.lower()}%")
                )
            else:
                # Default: starts-with
                value_conditions.append(
                    alias.c.value_normalized.like(f"{value.lower()}%")
                )

        conditions.append(or_(*value_conditions))
        query = query.filter(
            ResourceEntity.id.in_(
                db.session.query(alias.c.resource_id).filter(and_(*conditions))
            )
        )
        return query

    def _apply_token(self, query, param):
        """Apply a token search parameter."""
        alias = self._next_alias(TokenIndex)

        conditions = [
            alias.c.resource_id == ResourceEntity.id,
            alias.c.res_type == self.resource_type,
            alias.c.param_name == param.name,
        ]

        value_conditions = []
        for value in param.values:
            value_conditions.append(self._parse_token_value(alias, value))

        conditions.append(or_(*value_conditions))
        query = query.filter(
            ResourceEntity.id.in_(
                db.session.query(alias.c.resource_id).filter(and_(*conditions))
            )
        )
        return query

    def _parse_token_value(self, alias, value):
        """Parse a token value pattern: system|code, |code, code, system|"""
        if "|" in value:
            parts = value.split("|", 1)
            system_val, code_val = parts[0], parts[1]
            if system_val and code_val:
                return and_(alias.c.system == system_val, alias.c.value == code_val)
            elif system_val and not code_val:
                return alias.c.system == system_val
            elif not system_val and code_val:
                return alias.c.value == code_val
        # Just a code value
        return alias.c.value == value

    def _apply_date(self, query, param):
        """Apply a date search parameter with prefix-based range semantics."""
        alias = self._next_alias(DateIndex)

        conditions = [
            alias.c.resource_id == ResourceEntity.id,
            alias.c.res_type == self.resource_type,
            alias.c.param_name == param.name,
        ]

        value_conditions = []
        for i, value in enumerate(param.values):
            prefix = param.prefix if isinstance(param.prefix, str) else "eq"
            target_low, target_high = parse_fhir_date_to_range(value)
            if target_low is None:
                continue

            cond = self._build_date_condition(alias, prefix, target_low, target_high)
            if cond is not None:
                value_conditions.append(cond)

        if value_conditions:
            conditions.append(or_(*value_conditions))
            query = query.filter(
                ResourceEntity.id.in_(
                    db.session.query(alias.c.resource_id).filter(and_(*conditions))
                )
            )
        return query

    def _build_date_condition(self, alias, prefix, target_low, target_high):
        """Build date comparison based on FHIR prefix semantics."""
        if prefix == "eq":
            # Resource range overlaps with target range
            return and_(
                alias.c.value_low <= target_high,
                alias.c.value_high >= target_low,
            )
        elif prefix == "ne":
            return or_(
                alias.c.value_low > target_high,
                alias.c.value_high < target_low,
            )
        elif prefix == "gt":
            return alias.c.value_high > target_high
        elif prefix == "lt":
            return alias.c.value_low < target_low
        elif prefix == "ge":
            return alias.c.value_high >= target_low
        elif prefix == "le":
            return alias.c.value_low <= target_high
        elif prefix == "sa":
            # starts after
            return alias.c.value_low > target_high
        elif prefix == "eb":
            # ends before
            return alias.c.value_high < target_low
        return None

    def _apply_quantity(self, query, param):
        """Apply a quantity search parameter."""
        alias = self._next_alias(QuantityIndex)

        conditions = [
            alias.c.resource_id == ResourceEntity.id,
            alias.c.res_type == self.resource_type,
            alias.c.param_name == param.name,
        ]

        value_conditions = []
        for i, value in enumerate(param.values):
            prefix = param.prefix if isinstance(param.prefix, str) else "eq"
            num_val, system, unit = self._parse_quantity_value(value)
            if num_val is None:
                continue

            cond = self._build_quantity_condition(alias, prefix, num_val, system, unit)
            if cond is not None:
                value_conditions.append(cond)

        if value_conditions:
            conditions.append(or_(*value_conditions))
            query = query.filter(
                ResourceEntity.id.in_(
                    db.session.query(alias.c.resource_id).filter(and_(*conditions))
                )
            )
        return query

    def _parse_quantity_value(self, value):
        """Parse quantity value: number|system|unit or just number."""
        parts = value.split("|")
        try:
            num_val = float(parts[0])
        except (ValueError, IndexError):
            return None, None, None
        system = parts[1] if len(parts) > 1 and parts[1] else None
        unit = parts[2] if len(parts) > 2 and parts[2] else None
        return num_val, system, unit

    def _build_quantity_condition(self, alias, prefix, num_val, system, unit):
        """Build quantity comparison condition."""
        parts = []
        if system:
            parts.append(alias.c.system == system)
        if unit:
            parts.append(alias.c.units == unit)

        if prefix == "eq":
            # Within 5% tolerance for implicit precision
            tolerance = abs(num_val * 0.05) if num_val != 0 else 0.5
            parts.append(alias.c.value.between(num_val - tolerance, num_val + tolerance))
        elif prefix == "ne":
            tolerance = abs(num_val * 0.05) if num_val != 0 else 0.5
            parts.append(or_(alias.c.value < num_val - tolerance, alias.c.value > num_val + tolerance))
        elif prefix == "gt":
            parts.append(alias.c.value > num_val)
        elif prefix == "lt":
            parts.append(alias.c.value < num_val)
        elif prefix == "ge":
            parts.append(alias.c.value >= num_val)
        elif prefix == "le":
            parts.append(alias.c.value <= num_val)
        else:
            parts.append(alias.c.value == num_val)

        return and_(*parts) if parts else None

    def _apply_reference(self, query, param):
        """Apply a reference search parameter."""
        alias = self._next_alias(ResourceLink)

        conditions = [
            alias.c.src_resource_id == ResourceEntity.id,
        ]

        value_conditions = []
        for value in param.values:
            if "/" in value:
                # ResourceType/id format
                ref_type, ref_id = value.rsplit("/", 1)
                value_conditions.append(and_(
                    alias.c.target_resource_type == ref_type,
                    alias.c.target_fhir_id == ref_id,
                ))
            else:
                # Just an id — match any target type from param def
                value_conditions.append(alias.c.target_fhir_id == value)

        conditions.append(or_(*value_conditions))
        query = query.filter(
            ResourceEntity.id.in_(
                db.session.query(alias.c.src_resource_id).filter(and_(*conditions))
            )
        )
        return query

    def _apply_composite(self, query, param):
        """Apply a composite search parameter using $ separator.

        e.g., code-value-quantity=http://loinc.org|8867-4$72
        """
        alias = self._next_alias(CompositeIndex)

        conditions = [
            alias.c.resource_id == ResourceEntity.id,
            alias.c.res_type == self.resource_type,
            alias.c.param_name == param.name,
        ]

        value_conditions = []
        for value in param.values:
            parts = value.split("$", 1)
            if len(parts) < 2:
                continue

            comp1_str = parts[0]
            comp2_str = parts[1]

            comp1_conds = []
            # Parse component 1 (token format: system|code or just code)
            if "|" in comp1_str:
                sys_val, code_val = comp1_str.split("|", 1)
                if sys_val:
                    comp1_conds.append(alias.c.comp1_system == sys_val)
                if code_val:
                    comp1_conds.append(alias.c.comp1_value == code_val)
            else:
                comp1_conds.append(alias.c.comp1_value == comp1_str)

            comp2_conds = []
            # Parse component 2
            if "|" in comp2_str:
                sys_val, code_val = comp2_str.split("|", 1)
                if sys_val:
                    comp2_conds.append(alias.c.comp2_system == sys_val)
                if code_val:
                    comp2_conds.append(alias.c.comp2_value == code_val)
            else:
                comp2_conds.append(alias.c.comp2_value == comp2_str)

            combined = comp1_conds + comp2_conds
            if combined:
                value_conditions.append(and_(*combined))

        if value_conditions:
            conditions.append(or_(*value_conditions))
            query = query.filter(
                ResourceEntity.id.in_(
                    db.session.query(alias.c.resource_id).filter(and_(*conditions))
                )
            )
        return query

    def _apply_chain(self, query, param):
        """Apply a chained search parameter (e.g., patient.name=Smith).

        Resolves through ResourceLink to find matching target resources,
        then filters source resources that reference them.
        """
        # Find the reference param definition
        ref_param = param.param_def
        target_types = ref_param.get("target", [])

        if not target_types:
            return query

        # Build subquery: find target resource IDs matching the chained param
        from app.fhir.search_params import get_search_param
        chained_parts = param.chain.split(".", 1)
        chained_name = chained_parts[0]

        target_ids = set()
        for target_type in target_types:
            chained_def = get_search_param(target_type, chained_name)
            if chained_def is None:
                continue

            # Build a sub-query on the target resource type
            sub_builder = SearchQueryBuilder(target_type)
            from app.search.param_parser import ParsedParam
            sub_param = ParsedParam(
                name=chained_name,
                modifier=param.modifier,
                param_type=chained_def["type"],
                values=param.values,
                param_def=chained_def,
            )

            sub_q = (
                db.session.query(ResourceEntity.fhir_id, ResourceEntity.res_type)
                .filter(ResourceEntity.res_type == target_type)
                .filter(ResourceEntity.is_deleted == False)  # noqa: E712
            )

            # Apply the chained param filter
            if chained_def["type"] == "string":
                sub_q = sub_builder._apply_string(sub_q, sub_param)
            elif chained_def["type"] == "token":
                sub_q = sub_builder._apply_token(sub_q, sub_param)
            elif chained_def["type"] == "date":
                sub_q = sub_builder._apply_date(sub_q, sub_param)

            for fhir_id, res_type in sub_q.all():
                target_ids.add((res_type, fhir_id))

        if not target_ids:
            # No matches — return empty
            query = query.filter(ResourceEntity.id == -1)
            return query

        # Now filter: source resources that have a link to any of these targets
        link_alias = self._next_alias(ResourceLink)
        or_conds = []
        for res_type, fhir_id in target_ids:
            or_conds.append(and_(
                link_alias.c.target_resource_type == res_type,
                link_alias.c.target_fhir_id == fhir_id,
            ))

        query = query.filter(
            ResourceEntity.id.in_(
                db.session.query(link_alias.c.src_resource_id).filter(
                    and_(
                        link_alias.c.src_resource_id == ResourceEntity.id,
                        or_(*or_conds),
                    )
                )
            )
        )
        return query

    def _apply_has(self, query, has_param):
        """Apply _has (reverse chaining) filter.

        _has:TargetType:refParam:searchParam=value

        Finds TargetType resources where refParam references the main resources
        and searchParam matches value.
        """
        target_type = has_param.param_def.get("target_type")
        ref_param = has_param.param_def.get("ref_param")
        search_param = has_param.param_def.get("search_param")

        if not all([target_type, ref_param, search_param]):
            return query

        from app.fhir.search_params import get_search_param
        search_def = get_search_param(target_type, search_param)
        if search_def is None:
            return query

        # Build a subquery: find target resources matching search_param=value
        sub_builder = SearchQueryBuilder(target_type)
        from app.search.param_parser import ParsedParam

        prefix = None
        values = has_param.values
        if search_def["type"] in ("date", "quantity"):
            from app.utils.fhir_types import DATE_PREFIXES
            processed_values = []
            for v in values:
                if len(v) >= 2 and v[:2] in DATE_PREFIXES:
                    prefix = v[:2]
                    processed_values.append(v[2:])
                else:
                    prefix = "eq"
                    processed_values.append(v)
            values = processed_values

        sub_param = ParsedParam(
            name=search_param,
            modifier=None,
            param_type=search_def["type"],
            values=values,
            prefix=prefix,
            param_def=search_def,
        )

        sub_q = (
            db.session.query(ResourceEntity.id)
            .filter(ResourceEntity.res_type == target_type)
            .filter(ResourceEntity.is_deleted == False)  # noqa: E712
        )

        if search_def["type"] == "string":
            sub_q = sub_builder._apply_string(sub_q, sub_param)
        elif search_def["type"] == "token":
            sub_q = sub_builder._apply_token(sub_q, sub_param)
        elif search_def["type"] == "date":
            sub_q = sub_builder._apply_date(sub_q, sub_param)
        elif search_def["type"] == "quantity":
            sub_q = sub_builder._apply_quantity(sub_q, sub_param)

        # Targets reference main resources via ResourceLink:
        # ResourceLink.src_resource_id = target resource id
        # ResourceLink.target_fhir_id = main resource fhir_id
        # ResourceLink.target_resource_type = main resource type
        link_alias = self._next_alias(ResourceLink)
        matching_target_ids = sub_q.subquery()

        query = query.filter(
            ResourceEntity.fhir_id.in_(
                db.session.query(link_alias.c.target_fhir_id).filter(
                    and_(
                        link_alias.c.src_resource_id.in_(
                            db.session.query(matching_target_ids.c.id)
                        ),
                        link_alias.c.target_resource_type == self.resource_type,
                    )
                )
            )
        )
        return query

    def _apply_sort(self, query, sort_param):
        """Apply _sort parameter. Supports -field for descending."""
        descending = sort_param.startswith("-")
        field_name = sort_param.lstrip("-")

        if field_name == "_lastUpdated":
            col = ResourceEntity.last_updated
            query = query.order_by(col.desc() if descending else col.asc())
        elif field_name == "_id":
            col = ResourceEntity.fhir_id
            query = query.order_by(col.desc() if descending else col.asc())
        else:
            # Sort by a date index if available
            from app.fhir.search_params import get_search_param
            param_def = get_search_param(self.resource_type, field_name)
            if param_def and param_def["type"] == "date":
                alias = self._next_alias(DateIndex)
                query = query.outerjoin(
                    alias,
                    and_(
                        alias.c.resource_id == ResourceEntity.id,
                        alias.c.param_name == field_name,
                    ),
                )
                col = alias.c.value_low
                query = query.order_by(col.desc() if descending else col.asc())
            else:
                # Fallback to last_updated
                query = query.order_by(
                    ResourceEntity.last_updated.desc() if descending
                    else ResourceEntity.last_updated.asc()
                )

        return query
