# app/api/v1/routes_routing.py
from functools import lru_cache

import networkx as nx
from fastapi import APIRouter, Depends, HTTPException

from app.core.errors import GraphAreaError
from app.models.routing import RouteRequest, RouteResponse
from app.services.routing_service import RoutingService

router = APIRouter(
    prefix="/route",
    tags=["routing"],
)


@lru_cache(maxsize=1)
def get_routing_service() -> RoutingService:
    """Process-wide RoutingService. Tests override this dependency."""
    return RoutingService()


@router.post(
    "/",
    response_model=RouteResponse,
    summary="Compute a route between origin and destination",
)
def compute_route(
    request: RouteRequest,
    service: RoutingService = Depends(get_routing_service),
) -> RouteResponse:
    """
    Compute a route between origin and destination on the OSM road network.

    Declared sync on purpose: graph building and pathfinding are blocking
    CPU/network work, so FastAPI runs this handler in its threadpool
    instead of stalling the event loop.
    """
    try:
        return service.compute_route(request)
    except GraphAreaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except nx.NetworkXNoPath as exc:
        raise HTTPException(
            status_code=422,
            detail="No drivable path found between these points.",
        ) from exc
