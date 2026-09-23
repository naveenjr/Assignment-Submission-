from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parents[2]))

from connectors.alarm_api import AlarmApiClient

mcp = FastMCP("alarm-management")
client = AlarmApiClient()


class Asset(BaseModel):
    asset_id: str
    name: str
    site: str
    criticality: str
    related_assets: list[str]


class AssetSearchResponse(BaseModel):
    results: list[Asset]
    total: int


class Alarm(BaseModel):
    alarm_id: str
    asset_id: str
    title: str
    severity: str
    status: str
    occurrences: int
    likely_causes: list[str]
    recommendations: list[str]


class AlarmListResponse(BaseModel):
    results: list[Alarm]
    total: int


class RecommendationResponse(BaseModel):
    alarm_id: str
    recommendations: list[str]


class CorrelationResponse(BaseModel):
    alarm_id: str
    related_assets: list[str]
    likely_causes: list[str]


def _trace_id(value: str | None) -> str:
    return value or "mcp-investigation"


def _call(path: str, params: dict | None, trace_id: str | None) -> dict:
    try:
        return client.get(path, params, _trace_id(trace_id))
    except RuntimeError as exc:
        raise ValueError(f"Alarm Management API unavailable: {exc}") from exc


@mcp.tool()
def search_assets(
    query: str = Field(min_length=2, max_length=120),
    trace_id: str | None = Field(default=None, min_length=8, max_length=80),
) -> AssetSearchResponse:
    """Find assets by name or identifier."""
    return AssetSearchResponse.model_validate(_call("/assets/search", {"query": query}, trace_id))


@mcp.tool()
def get_asset_metadata(
    asset_id: str = Field(pattern=r"^[A-Z0-9-]{3,32}$"),
    trace_id: str | None = Field(default=None, min_length=8, max_length=80),
) -> Asset:
    """Return metadata for one asset."""
    return Asset.model_validate(_call(f"/assets/{asset_id}/metadata", None, trace_id))


@mcp.tool()
def get_alarms(
    asset_id: str = Field(pattern=r"^[A-Z0-9-]{3,32}$"),
    status: Literal["active", "cleared", "all"] = "active",
    trace_id: str | None = Field(default=None, min_length=8, max_length=80),
) -> AlarmListResponse:
    """Retrieve active or historical alarms for an asset."""
    return AlarmListResponse.model_validate(
        _call("/alarms", {"asset_id": asset_id, "status": status}, trace_id)
    )


@mcp.tool()
def get_alarm_summary(
    alarm_id: str = Field(pattern=r"^ALM-[0-9]{4,}$"),
    trace_id: str | None = Field(default=None, min_length=8, max_length=80),
) -> Alarm:
    """Return severity, causes, recurrence, and recommendations for one alarm."""
    return Alarm.model_validate(_call(f"/alarms/{alarm_id}/summary", None, trace_id))


@mcp.tool()
def get_alarm_correlation(
    alarm_id: str = Field(pattern=r"^ALM-[0-9]{4,}$"),
    trace_id: str | None = Field(default=None, min_length=8, max_length=80),
) -> CorrelationResponse:
    """Return related assets and likely causes for one alarm."""
    return CorrelationResponse.model_validate(
        _call(f"/alarms/{alarm_id}/correlation", None, trace_id)
    )


@mcp.tool()
def get_operator_recommendations(
    alarm_id: str = Field(pattern=r"^ALM-[0-9]{4,}$"),
    trace_id: str | None = Field(default=None, min_length=8, max_length=80),
) -> RecommendationResponse:
    """Return immediate operator recommendations for one alarm."""
    return RecommendationResponse.model_validate(
        _call(f"/alarms/{alarm_id}/recommendations", None, trace_id)
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
