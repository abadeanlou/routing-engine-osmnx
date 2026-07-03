# tests/test_route_dummy.py
from app.services.graph_manager import GraphManager
from tests.conftest import build_dummy_graph, make_dummy_service

ORIGIN = {"lat": 45.4642, "lon": 9.19}
DESTINATION = {"lat": 45.48, "lon": 9.25}


def test_route_on_dummy_graph(client):
    payload = {"origin": ORIGIN, "destination": DESTINATION, "departure_time": None}
    response = client.post("/route/", json=payload)
    assert response.status_code == 200

    data = response.json()
    summary = data["summary"]
    assert summary["distance_m"] > 0
    assert summary["duration_s"] > 0
    assert isinstance(summary["geometry"], list)
    assert len(summary["geometry"]) >= 2
    assert len(data["steps"]) >= 1
    # Shortest path should take the 1->2->3 chain (2500 m), not the 2600 m edge
    assert abs(summary["distance_m"] - 2500.0) < 1.0


def test_no_path_returns_422(client):
    # Reversed OD: the dummy graph's edges are one-way, so no path exists.
    payload = {"origin": DESTINATION, "destination": ORIGIN, "departure_time": None}
    response = client.post("/route/", json=payload)
    assert response.status_code == 422
    assert "path" in response.json()["detail"].lower()


def test_frozen_instance_rejects_out_of_area(client):
    service = make_dummy_service()
    # Preload with the dummy builder, then freeze.
    service.graph_manager.preload(45.4642, 9.19, 5000.0, cache_dir=None)
    assert service.graph_manager.frozen

    from app.api.v1.routes_routing import get_routing_service
    from app.main import app
    app.dependency_overrides[get_routing_service] = lambda: service
    payload = {"origin": {"lat": 48.85, "lon": 2.35},  # Paris: far outside
               "destination": ORIGIN, "departure_time": None}
    response = client.post("/route/", json=payload)
    assert response.status_code == 422
    assert "area" in response.json()["detail"].lower()


def test_dynamic_mode_rebuilds_for_new_area():
    gm_calls = []

    def counting_builder(lat, lon, radius):
        gm_calls.append((round(lat, 3), round(lon, 3)))
        return build_dummy_graph(lat, lon, radius)

    gm = GraphManager(graph_builder=counting_builder,
                      nearest_fn=GraphManager.nearest_node_euclidean)
    from app.models.routing import Coordinate
    gm.ensure_graph_for_points(Coordinate(lat=45.4642, lon=9.19),
                               Coordinate(lat=45.48, lon=9.25))
    assert len(gm_calls) == 1
    # Same area again: no rebuild
    gm.ensure_graph_for_points(Coordinate(lat=45.47, lon=9.20),
                               Coordinate(lat=45.475, lon=9.24))
    assert len(gm_calls) == 1
