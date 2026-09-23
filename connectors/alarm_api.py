from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

ASSETS = {
    "BFP-102": {
        "asset_id": "BFP-102",
        "name": "Boiler Feed Pump 102",
        "site": "EastRefinery",
        "criticality": "critical",
        "related_assets": ["COMP-204", "MTR-305"],
    },
    "COMP-204": {
        "asset_id": "COMP-204",
        "name": "Compressor 204",
        "site": "EastRefinery",
        "criticality": "high",
        "related_assets": ["BFP-102", "MTR-305"],
    },
    "MTR-305": {
        "asset_id": "MTR-305",
        "name": "Motor 305",
        "site": "EastRefinery",
        "criticality": "medium",
        "related_assets": ["COMP-204", "BFP-102"],
    },
}

ALARMS = {
    "ALM-1001": {
        "alarm_id": "ALM-1001",
        "asset_id": "BFP-102",
        "title": "High discharge pressure",
        "severity": "critical",
        "status": "active",
        "occurrences": 5,
        "likely_causes": ["Partially closed discharge valve", "Suction filter fouling"],
        "recommendations": ["Verify discharge valve position", "Check suction strainer differential"],
    },
    "ALM-1002": {
        "alarm_id": "ALM-1002",
        "asset_id": "COMP-204",
        "title": "Compressor discharge pressure high",
        "severity": "high",
        "status": "active",
        "occurrences": 9,
        "likely_causes": ["Filter restriction", "Condensate accumulation"],
        "recommendations": ["Inspect discharge strainer", "Check condensate drains"],
    },
    "ALM-1003": {
        "alarm_id": "ALM-1003",
        "asset_id": "MTR-305",
        "title": "Motor trip",
        "severity": "critical",
        "status": "active",
        "occurrences": 3,
        "likely_causes": ["Overcurrent", "Thermal overload"],
        "recommendations": ["Review motor current trend", "Inspect overload relay"],
    },
}


class AlarmApiClient:
    """Authenticated source-system connector used only by the MCP server."""

    def __init__(self) -> None:
        self.base_url = os.getenv("ALARM_API_BASE_URL", "http://localhost:8000").rstrip("/")
        self.token = os.getenv("ALARM_API_TOKEN", "demo-token")

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Call the alarm API with authentication, timeout, and bounded retry."""
        auth_header = "Bearer " + self.token
        headers = {"authorization": auth_header, "x-trace-id": "mcp-investigation"}
        last_error: Exception | None = None
        for _ in range(2):
            try:
                response = httpx.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers=headers,
                    timeout=8,
                )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
        raise RuntimeError(f"Alarm API request failed: {last_error}") from last_error
