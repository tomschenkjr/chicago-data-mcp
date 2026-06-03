"""
Chicago Open Data MCP Server
Provides search and query tools for data.cityofchicago.org (Socrata SoDA API).
No API key required for basic access; set SOCRATA_APP_TOKEN for higher rate limits.
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "Chicago Open Data",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

DOMAIN = "data.cityofchicago.org"
HEADERS = {"User-Agent": "chicago-data-mcp/1.0 (opengrid deployment)"}

_app_token = os.getenv("SOCRATA_APP_TOKEN", "").strip()
_secret_token = os.getenv("SOCRATA_SECRET_TOKEN", "").strip()

# Basic Auth uses app_token as username and secret_token as password.
# If only the app token is present it is sent as a query param for rate-limit
# headroom without requiring authentication.
_auth = (_app_token, _secret_token) if (_app_token and _secret_token) else None
_token_param = _app_token if (_app_token and not _secret_token) else None


async def _get(url: str, params: dict = None) -> dict | list:
    if params is None:
        params = {}
    if _token_param:
        params["$$app_token"] = _token_param
    async with httpx.AsyncClient(headers=HEADERS, auth=_auth, timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def search_chicago_datasets(query: str, limit: int = 10) -> list[dict]:
    """
    Search data.cityofchicago.org catalog for datasets matching a keyword.
    Returns dataset names, IDs, descriptions, and categories.

    Args:
        query: Search terms (e.g. "crime", "food inspection", "building permits")
        limit: Maximum number of results to return (default 10)
    """
    url = f"https://{DOMAIN}/api/catalog/v1"
    params = {"q": query, "limit": limit, "domains": DOMAIN}
    data = await _get(url, params)
    results = data.get("results", [])
    return [
        {
            "id": r.get("resource", {}).get("id"),
            "name": r.get("resource", {}).get("name"),
            "description": r.get("resource", {}).get("description"),
            "category": r.get("classification", {}).get("categories", [None])[0],
            "type": r.get("resource", {}).get("type"),
            "permalink": r.get("permalink"),
            "updated_at": r.get("resource", {}).get("updatedAt"),
        }
        for r in results
        if r.get("resource", {}).get("type") in ("dataset", "map")
    ]


@mcp.tool()
async def get_dataset_columns(dataset_id: str) -> list[dict]:
    """
    Get column names, field types, and descriptions for a Chicago open data dataset.
    Call this before querying to understand the available fields and their names.

    Args:
        dataset_id: The 4x4 Socrata dataset identifier (e.g. "ijzp-q8t2" for crimes)
    """
    url = f"https://{DOMAIN}/api/views/{dataset_id}.json"
    data = await _get(url)
    columns = data.get("columns", [])
    return [
        {
            "field_name": col.get("fieldName"),
            "display_name": col.get("name"),
            "data_type": col.get("dataTypeName"),
            "description": col.get("description"),
        }
        for col in columns
        if not col.get("fieldName", "").startswith(":")
    ]


@mcp.tool()
async def query_chicago_dataset(
    dataset_id: str,
    soql_where: str = None,
    limit: int = 500,
    order_by: str = None,
    select: str = None,
) -> list[dict]:
    """
    Execute a SOQL query against a Chicago open data dataset.
    Returns matching rows as a list of dicts. Use get_dataset_columns first to know field names.

    Args:
        dataset_id: The 4x4 Socrata dataset identifier (e.g. "ijzp-q8t2")
        soql_where: SOQL WHERE clause (e.g. "primary_type = 'BURGLARY' AND date > '2024-01-01'")
        limit: Maximum rows to return (default 500, max 50000)
        order_by: ORDER BY clause (e.g. "date DESC")
        select: Comma-separated column names to return (default: all columns)
    """
    url = f"https://{DOMAIN}/resource/{dataset_id}.json"
    params: dict = {"$limit": min(limit, 50000)}
    if soql_where:
        params["$where"] = soql_where
    if order_by:
        params["$order"] = order_by
    if select:
        params["$select"] = select
    return await _get(url, params)


@mcp.tool()
async def geocode_chicago_location(location: str) -> dict:
    """
    Convert a Chicago neighborhood, address, or landmark name to coordinates.
    Use this to find lat/lon for location-based SOQL queries
    (e.g. within_circle, within_box).

    Args:
        location: Chicago location name, neighborhood, or address
                  (e.g. "Wicker Park", "Lincoln Park", "600 W Chicago Ave")
    """
    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/find"
    params = {
        "text": f"{location}, Chicago, IL",
        "bbox": "-88.02864,41.56614,-87.30011,42.06663",
        "f": "json",
        "maxLocations": 1,
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    locations = data.get("locations", [])
    if not locations:
        return {"error": f"Could not geocode: {location}"}
    loc = locations[0]
    return {
        "name": loc.get("name"),
        "latitude": loc["feature"]["geometry"]["y"],
        "longitude": loc["feature"]["geometry"]["x"],
        "score": loc.get("score"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
