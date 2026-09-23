# MCP tool catalog

The server is independently runnable from the submission root:

```bash
uv run python mcp-servers/alarm-management/server.py
```

The client first calls MCP `tools/list`, checks that the requested tool is
available, and then invokes it with schema-aware arguments. Pydantic models
validate inputs and outputs. Each invocation carries a correlation `trace_id`
to the source API as `x-trace-id`. The bearer token is read from
`ALARM_API_TOKEN` and is never returned or logged.

## Common behavior

- **Authentication:** the connector sends `Authorization: Bearer $ALARM_API_TOKEN`.
- **Timeout:** each source API request has an 8-second timeout.
- **Retry:** one retry is attempted for an HTTP or transport failure.
- **Error mapping:** connector failures become `Alarm Management API unavailable:
  ...` MCP tool errors; invalid MCP arguments are rejected before the API call.
- **Trace:** the LangGraph investigation creates a correlation ID. The MCP
  gateway records discovery, invocation, and completion events and the
  connector forwards the ID as `x-trace-id`.
- **Secret handling:** credentials are read from environment configuration and
  are excluded from tool results, citations, and UI traces.

## `search_assets`

- **Purpose:** resolve a natural-language asset name or identifier.
- **Input schema:** `query: string`, 2-120 characters; optional
  `trace_id: string`, 8-80 characters.
- **Output schema:** `{results: Asset[], total: integer}` where an `Asset`
  contains `asset_id`, `name`, `site`, `criticality`, and `related_assets`.
- **Source operation:** `GET /assets/search?query=...`.
- **Example invocation:** `{"query":"Boiler Feed Pump 102","trace_id":"a1b2c3d4"}`.
- **Example response:** `{"results":[{"asset_id":"BFP-102","name":"Boiler Feed Pump 102","site":"EastRefinery","criticality":"critical","related_assets":["COMP-204","MTR-305"]}],"total":1}`.
- **Errors:** invalid query is rejected; source timeout/unavailability is
  returned as an MCP tool error.

## `get_asset_metadata`

- **Purpose:** retrieve one asset and its related equipment.
- **Input schema:** `asset_id` matching `^[A-Z0-9-]{3,32}$`; optional `trace_id`.
- **Output schema:** one `Asset` object.
- **Source operation:** `GET /assets/{asset_id}/metadata`.
- **Example invocation:** `{"asset_id":"BFP-102","trace_id":"a1b2c3d4"}`.
- **Example response:** `{"asset_id":"BFP-102","name":"Boiler Feed Pump 102","site":"EastRefinery","criticality":"critical","related_assets":["COMP-204","MTR-305"]}`.
- **Errors:** invalid identifier or unavailable source is mapped to a clear MCP error.

## `get_alarms`

- **Purpose:** retrieve active, cleared, or all alarms for an asset.
- **Input schema:** `asset_id` matching `^[A-Z0-9-]{3,32}$`; `status` is
  `active`, `cleared`, or `all`; optional `trace_id`.
- **Output schema:** `{results: Alarm[], total: integer}`. An `Alarm` includes
  `alarm_id`, `asset_id`, `title`, `severity`, `status`, `occurrences`,
  `likely_causes`, and `recommendations`.
- **Source operation:** `GET /alarms?asset_id=...&status=...`.
- **Example invocation:** `{"asset_id":"BFP-102","status":"active","trace_id":"a1b2c3d4"}`.
- **Example response:** `{"results":[{"alarm_id":"ALM-1001","asset_id":"BFP-102","title":"High discharge pressure","severity":"critical","status":"active","occurrences":5,"likely_causes":["Partially closed discharge valve","Suction filter fouling"],"recommendations":["Verify discharge valve position","Check suction strainer differential"]}],"total":1}`.
- **Errors:** invalid status/asset ID is rejected; source failures are mapped to MCP errors.

## `get_alarm_summary`

- **Purpose:** return severity, recurrence, causes, and recommendations.
- **Input schema:** `alarm_id` matching `^ALM-[0-9]{4,}$`; optional `trace_id`.
- **Output schema:** one `Alarm` object.
- **Source operation:** `GET /alarms/{alarm_id}/summary`.
- **Example invocation:** `{"alarm_id":"ALM-1001","trace_id":"a1b2c3d4"}`.
- **Example response:** `{"alarm_id":"ALM-1001","asset_id":"BFP-102","title":"High discharge pressure","severity":"critical","status":"active","occurrences":5,"likely_causes":["Partially closed discharge valve","Suction filter fouling"],"recommendations":["Verify discharge valve position","Check suction strainer differential"]}`.
- **Errors:** invalid alarm ID or unavailable source is mapped to an MCP error.

## `get_alarm_correlation`

- **Purpose:** identify related assets and likely causes.
- **Input schema:** `alarm_id` matching `^ALM-[0-9]{4,}$`; optional `trace_id`.
- **Output schema:** `{alarm_id: string, related_assets: string[], likely_causes: string[]}`.
- **Source operation:** `GET /alarms/{alarm_id}/correlation`.
- **Example invocation:** `{"alarm_id":"ALM-1001","trace_id":"a1b2c3d4"}`.
- **Example response:** `{"alarm_id":"ALM-1001","related_assets":["COMP-204","MTR-305"],"likely_causes":["Partially closed discharge valve","Suction filter fouling"]}`.
- **Errors:** invalid alarm ID or unavailable source is mapped to an MCP error.

## `get_operator_recommendations`

- **Purpose:** return immediate operator actions for an alarm.
- **Input schema:** `alarm_id` matching `^ALM-[0-9]{4,}$`; optional `trace_id`.
- **Output schema:** `{alarm_id: string, recommendations: string[]}`.
- **Source operation:** `GET /alarms/{alarm_id}/recommendations`.
- **Example invocation:** `{"alarm_id":"ALM-1001","trace_id":"a1b2c3d4"}`.
- **Example response:** `{"alarm_id":"ALM-1001","recommendations":["Verify discharge valve position","Check suction strainer differential"]}`.
- **Errors:** invalid alarm ID or unavailable source is mapped to an MCP error.

## Combined workflow

For a question about a named asset, the LLM can chain
`search_assets -> get_alarms -> get_alarm_summary` and optionally
`get_alarm_correlation` or `get_operator_recommendations`. In parallel, the
application retrieves procedure evidence from RAG. The Streamlit UI displays
the grounded answer, document sources, and MCP execution trace.
