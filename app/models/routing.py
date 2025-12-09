# app/models/routing.py

from typing import List, Optional

from pydantic import BaseModel


class Coordinate(BaseModel):
    """
    Simple latitude/longitude coordinate.
    """
    lat: float
    lon: float


class RouteRequest(BaseModel):
    """
    Request body for the /route endpoint.
    """
    origin: Coordinate
    destination: Coordinate
    # For future use (e.g. time-dependent routing).
    departure_time: Optional[str] = None


class RouteGeometry(BaseModel):
    """
    Geometry of the computed route as a GeoJSON-like LineString.

    coordinates is a list of [lat, lon] pairs, e.g.:
    [
        [45.4642, 9.1900],
        [45.4700, 9.2000],
        ...
    ]
    """
    type: str = "LineString"
    coordinates: List[List[float]]


class RouteSummary(BaseModel):
    """
    Summary object for convenience and backward compatibility.

    IMPORTANT: tests expect `summary["geometry"]` to be a **list** of [lat, lon]
    coordinates, not a nested object. So here we store plain coordinates.
    """
    distance_m: float
    duration_s: float
    geometry: List[List[float]]  # plain list of [lat, lon]


class RouteStep(BaseModel):
    """
    One leg of the route, typically corresponding to a single edge
    between two graph nodes.
    """
    from_node: int
    to_node: int
    distance_m: float
    duration_s: float


class RouteResponse(BaseModel):
    """
    Response for the /route endpoint.

    - Top-level `geometry` is a proper GeoJSON-like object (type + coordinates),
      ideal for map visualisation.
    - `summary.geometry` is a plain list of [lat, lon] pairs, as tests expect.
    """
    distance_m: float
    duration_s: float
    geometry: RouteGeometry
    summary: RouteSummary
    steps: List[RouteStep]
    warnings: Optional[List[str]] = []