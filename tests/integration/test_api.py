from fastapi.testclient import TestClient

from apps.backend.main import app


def test_asset_search():
    response = TestClient(app).get("/assets/search", params={"query": "Boiler Feed Pump 102"})
    assert response.status_code == 200
    assert response.json()["results"][0]["asset_id"] == "BFP-102"
