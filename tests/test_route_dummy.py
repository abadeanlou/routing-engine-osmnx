# tests/test_route_dummy.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_route_dummy():
    payload = {
        "origin": {"lat": 45.4642, "lon": 9.19},        # near center (Milan)
        "destination": {"lat": 45.48, "lon": 9.25},     # some point nearby
        "departure_time": None,
    }

    response = client.post("/route/", json=payload)
    assert response.status_code == 200

    data = response.json()

    # Basic structure
    assert "summary" in data
    assert "steps" in data

    summary = data["summary"]
    assert "distance_m" in summary
    assert "duration_s" in summary
    assert "geometry" in summary

    # Geometry should have at least 2 points
    assert isinstance(summary["geometry"], list)
    assert len(summary["geometry"]) >= 2

    # Distance and duration should be positive
    assert summary["distance_m"] > 0
    assert summary["duration_s"] > 0

    # Steps should not be empty
    assert len(data["steps"]) >= 1
