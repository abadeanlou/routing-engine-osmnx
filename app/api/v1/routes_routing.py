# app/api/v1/routes_routing.py
from fastapi import APIRouter

from app.models.routing import RouteRequest, RouteResponse
from app.services.graph_manager import GraphManager
from app.services.routing_service import RoutingService

router = APIRouter(
    prefix="/route",
    tags=["routing"],
)

# Single shared instances
graph_manager = GraphManager()
routing_service = RoutingService(graph_manager=graph_manager)


@router.post(
    "/",
    response_model=RouteResponse,
    summary="Compute a route between origin and destination",
)
async def compute_route(request: RouteRequest) -> RouteResponse:
    """
    Compute a route between origin and destination using the OSM-based graph.

    - Snaps origin/destination to nearest OSM road nodes.
    - Uses shortest path (Dijkstra) on the drivable road network.
    """
    return routing_service.compute_route(request)
