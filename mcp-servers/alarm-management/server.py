from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from mcp.server.fastmcp import FastMCP

from connectors.alarm_api import AlarmApiClient

mcp = FastMCP("alarm-management")
client = AlarmApiClient()


@mcp.tool()
def search_assets(query: str) -> dict:
    """Resolve a natural-language asset name to asset identifiers."""
    return client.get("/assets/search", {"query": query})


@mcp.tool()
def get_asset_metadata(asset_id: str) -> dict:
    """Return asset metadata and related assets."""
    return client.get(f"/assets/{asset_id}/metadata")


@mcp.tool()
def get_alarms(asset_id: str, status: str = "active") -> dict:
    """Retrieve active or historical alarms for an asset."""
    return client.get("/alarms", {"asset_id": asset_id, "status": status})


@mcp.tool()
def get_alarm_summary(alarm_id: str) -> dict:
    """Return severity, causes, recurrence, and recommendations."""
    return client.get(f"/alarms/{alarm_id}/summary")


@mcp.tool()
def get_alarm_correlation(alarm_id: str) -> dict:
    """Return related assets and likely causes."""
    return client.get(f"/alarms/{alarm_id}/correlation")


@mcp.tool()
def get_operator_recommendations(alarm_id: str) -> dict:
    """Return immediate operator recommendations."""
    return client.get(f"/alarms/{alarm_id}/recommendations")


if __name__ == "__main__":
    mcp.run(transport="stdio")
