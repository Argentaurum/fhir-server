"""Parses FHIR search query strings into structured param objects."""

import re
from app.fhir.search_params import get_search_param, get_composite_params
from app.utils.fhir_types import DATE_PREFIXES

# Special parameters that are not resource-specific search params
CONTROL_PARAMS = {
    "_count", "_offset", "_sort", "_include", "_revinclude",
    "_total", "_format", "_summary", "_elements",
}

# Meta search params that apply to all resource types
META_SEARCH_PARAMS = {
    "_tag": {"name": "_tag", "type": "token", "paths": ["meta.tag"]},
    "_security": {"name": "_security", "type": "token", "paths": ["meta.security"]},
    "_profile": {"name": "_profile", "type": "token", "paths": ["meta.profile"]},
}


class ParsedParam:
    """A single parsed search parameter."""

    __slots__ = ("name", "modifier", "type", "values", "prefix", "chain", "param_def")

    def __init__(self, name, modifier, param_type, values, prefix=None, chain=None, param_def=None):
        self.name = name
        self.modifier = modifier
        self.type = param_type
        self.values = values  # list of raw value strings (OR semantics)
        self.prefix = prefix  # date/quantity prefix (eq, ne, gt, lt, ge, le, sa, eb)
        self.chain = chain    # chained param e.g. ("name",) for patient.name
        self.param_def = param_def


def parse_search_params(resource_type, query_args):
    """Parse Flask request.args into a list of ParsedParam objects.

    Returns (parsed_params, control_params) where control_params is a dict
    of _count, _offset, _sort, _include, _revinclude, _summary, _elements values.
    """
    parsed = []
    control = {
        "_count": 20,
        "_offset": 0,
        "_sort": None,
        "_include": [],
        "_revinclude": [],
        "_summary": None,
        "_elements": None,
    }

    for key, value in query_args.items(multi=True):
        if key in ("_format",):
            continue

        if key == "_count":
            control["_count"] = min(int(value), 1000)
            continue
        if key == "_offset":
            control["_offset"] = int(value)
            continue
        if key == "_sort":
            control["_sort"] = value
            continue
        if key == "_include":
            control["_include"].append(value)
            continue
        if key == "_revinclude":
            control["_revinclude"].append(value)
            continue
        if key == "_summary":
            control["_summary"] = value
            continue
        if key == "_elements":
            control["_elements"] = value
            continue

        # Handle meta search params before skipping _ prefixed params
        base_key = key.split(":")[0]  # strip modifier
        if base_key in META_SEARCH_PARAMS:
            meta_def = META_SEARCH_PARAMS[base_key]
            modifier = None
            if ":" in key:
                _, modifier = key.split(":", 1)
            values = value.split(",")
            parsed.append(ParsedParam(
                name=base_key,
                modifier=modifier,
                param_type=meta_def["type"],
                values=values,
                param_def=meta_def,
            ))
            continue

        # Handle _has parameter
        if key.startswith("_has:"):
            parsed.append(_parse_has_param(key, value))
            continue

        if key.startswith("_"):
            continue

        # Parse param name, modifier, and possible chain
        modifier = None
        chain = None
        param_name = key

        # Check for modifier (e.g., name:exact)
        if ":" in key:
            param_name, modifier = key.split(":", 1)

        # Check for chaining (e.g., patient.name)
        if "." in param_name:
            parts = param_name.split(".", 1)
            param_name = parts[0]
            chain = parts[1]

        # Look up the param definition
        param_def = get_search_param(resource_type, param_name)
        if param_def is None:
            # Check if it's a composite param
            comp_def = _find_composite(resource_type, param_name)
            if comp_def:
                # Composite values use $ separator: code$value
                values = value.split(",")
                parsed.append(ParsedParam(
                    name=param_name,
                    modifier=modifier,
                    param_type="composite",
                    values=values,
                    param_def=comp_def,
                ))
            continue  # Skip unknown params

        param_type = param_def["type"]

        # Split comma-separated values (OR semantics)
        values = value.split(",")

        # Extract date/quantity prefix
        prefix = None
        if param_type in ("date", "quantity"):
            processed_values = []
            prefixes = []
            for v in values:
                p, val = _extract_prefix(v)
                prefixes.append(p)
                processed_values.append(val)
            values = processed_values
            prefix = prefixes[0] if prefixes else "eq"

        parsed.append(ParsedParam(
            name=param_name,
            modifier=modifier,
            param_type=param_type,
            values=values,
            prefix=prefix,
            chain=chain,
            param_def=param_def,
        ))

    return parsed, control


def _parse_has_param(key, value):
    """Parse _has:TargetType:refParam:searchParam=value.

    Returns a ParsedParam with type='_has' and special structure.
    """
    # key is like "_has:Observation:patient:code"
    parts = key.split(":")
    # parts[0] = "_has", parts[1] = target_type, parts[2] = ref_param, parts[3] = search_param
    target_type = parts[1] if len(parts) > 1 else None
    ref_param = parts[2] if len(parts) > 2 else None
    search_param = parts[3] if len(parts) > 3 else None

    return ParsedParam(
        name="_has",
        modifier=None,
        param_type="_has",
        values=value.split(","),
        param_def={
            "target_type": target_type,
            "ref_param": ref_param,
            "search_param": search_param,
        },
    )


def _find_composite(resource_type, param_name):
    """Look up a composite search parameter definition."""
    for comp in get_composite_params(resource_type):
        if comp["name"] == param_name:
            return comp
    return None


def _extract_prefix(value):
    """Extract a comparison prefix from a date/quantity value.

    Returns (prefix, value_without_prefix). Default prefix is 'eq'.
    """
    if len(value) >= 2 and value[:2] in DATE_PREFIXES:
        return value[:2], value[2:]
    return "eq", value
