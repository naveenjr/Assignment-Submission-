from fastapi import FastAPI

from connectors.alarm_api import ALARMS, ASSETS

app = FastAPI(title="Alarm Management API Simulator")


@app.get("/health")
def health() -> dict:
    """Return simulator health."""
    return {"status": "ok"}


@app.get("/assets/search")
def search_assets(query: str, limit: int = 10) -> dict:
    """Search assets by name or identifier."""
    q = query.lower()
    matches = [
        asset for asset in ASSETS.values()
        if q in asset["name"].lower() or q in asset["asset_id"].lower()
    ]
    return {"results": matches[:limit], "total": len(matches)}


@app.get("/assets/{asset_id}/metadata")
def asset_metadata(asset_id: str) -> dict:
    """Return asset metadata."""
    return ASSETS[asset_id]


@app.get("/alarms")
def alarms(asset_id: str | None = None, status: str = "active") -> dict:
    """Return alarms filtered by asset and status."""
    values = list(ALARMS.values())
    if asset_id:
        values = [alarm for alarm in values if alarm["asset_id"] == asset_id]
    if status != "all":
        values = [alarm for alarm in values if alarm["status"] == status]
    return {"results": values, "total": len(values)}


@app.get("/alarms/{alarm_id}/summary")
def alarm_summary(alarm_id: str) -> dict:
    """Return one alarm summary."""
    return ALARMS[alarm_id]


@app.get("/alarms/{alarm_id}/recommendations")
def recommendations(alarm_id: str) -> dict:
    """Return operator recommendations for an alarm."""
    return {"alarm_id": alarm_id, "recommendations": ALARMS[alarm_id]["recommendations"]}


@app.get("/alarms/{alarm_id}/correlation")
def correlation(alarm_id: str) -> dict:
    """Return related assets and likely causes."""
    alarm = ALARMS[alarm_id]
    related = ASSETS[alarm["asset_id"]]["related_assets"]
    return {"alarm_id": alarm_id, "related_assets": related, "likely_causes": alarm["likely_causes"]}
