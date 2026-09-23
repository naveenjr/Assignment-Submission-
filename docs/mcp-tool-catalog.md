# MCP tool catalog

The server is independently runnable:

```powershell
python mcp-servers/alarm-management/server.py
```

Tools are discovered with MCP `tools/list`; calls are schema-aware and use the typed Python signatures.

| Tool | Input | Output | API operation |
|---|---|---|---|
| `search_assets` | `query: str` | matching assets | `GET /assets/search` |
| `get_asset_metadata` | `asset_id: str` | asset metadata | `GET /assets/{id}/metadata` |
| `get_alarms` | `asset_id: str, status: str` | alarm list | `GET /alarms` |
| `get_alarm_summary` | `alarm_id: str` | causes and severity | `GET /alarms/{id}/summary` |
| `get_alarm_correlation` | `alarm_id: str` | related assets/causes | `GET /alarms/{id}/correlation` |
| `get_operator_recommendations` | `alarm_id: str` | recommended actions | `GET /alarms/{id}/recommendations` |

The connector propagates bearer authentication, uses an 8-second timeout, retries once, and maps failures to explicit exceptions. API keys are never returned in tool output.
