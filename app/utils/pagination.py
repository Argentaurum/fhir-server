"""Bundle pagination helpers."""

from flask import request


def build_search_bundle(entries, total, base_url=None):
    """Build a FHIR searchset Bundle from a list of resource entries."""
    if base_url is None:
        base_url = request.base_url

    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": total,
        "link": [
            {"relation": "self", "url": request.url},
        ],
        "entry": entries,
    }

    # Add next/prev links if pagination params present
    count = request.args.get("_count", type=int)
    offset = request.args.get("_offset", 0, type=int)
    if count and total > offset + count:
        next_offset = offset + count
        next_url = _replace_param(request.url, "_offset", str(next_offset))
        bundle["link"].append({"relation": "next", "url": next_url})

    if offset > 0:
        prev_offset = max(0, offset - (count or 20))
        prev_url = _replace_param(request.url, "_offset", str(prev_offset))
        bundle["link"].append({"relation": "previous", "url": prev_url})

    return bundle


def build_history_bundle(entries, base_url=None, total=None):
    """Build a FHIR history Bundle."""
    return {
        "resourceType": "Bundle",
        "type": "history",
        "total": total if total is not None else len(entries),
        "entry": entries,
    }


def make_entry(resource, base_url, search_mode="match"):
    """Create a Bundle entry for a resource."""
    res_type = resource.get("resourceType", "")
    res_id = resource.get("id", "")
    return {
        "fullUrl": f"{base_url}/{res_type}/{res_id}",
        "resource": resource,
        "search": {"mode": search_mode},
    }


def _replace_param(url, param, value):
    """Replace or add a query parameter in a URL."""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params[param] = [value]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
