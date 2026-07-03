# tests/conftest.py
import os
import sys

import networkx as nx
import pytest
from fastapi.testclient import TestClient

# Make "import app" work when pytest runs from the repo root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.api.v1.routes_routing import get_routing_service  # noqa: E402
from app.main import app  # noqa: E402
from app.services.graph_manager import GraphManager  # noqa: E402
from app.services.routing_service import RoutingService  # noqa: E402


def build_dummy_graph(center_lat: float, center_lon: float,
                      radius_m: float) -> nx.MultiDiGraph:
    """Tiny in-memory street network near Milan; no network calls.

    Chain 1 -> 2 -> 3 plus a longer direct edge 1 -> 3 (directed, so the
    reverse direction has no path at all -- used by the no-path test).
    """
    G = nx.MultiDiGraph()
    G.add_node(1, x=9.19, y=45.4642)
    G.add_node(2, x=9.22, y=45.4720)
    G.add_node(3, x=9.25, y=45.4800)
    G.add_edge(1, 2, length=1000.0)
    G.add_edge(2, 3, length=1500.0)
    G.add_edge(1, 3, length=2600.0)
    return G


def make_dummy_service() -> RoutingService:
    gm = GraphManager(
        graph_builder=build_dummy_graph,
        nearest_fn=GraphManager.nearest_node_euclidean,
    )
    return RoutingService(graph_manager=gm)


@pytest.fixture()
def client():
    """TestClient whose RoutingService routes on the dummy graph."""
    service = make_dummy_service()
    app.dependency_overrides[get_routing_service] = lambda: service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
