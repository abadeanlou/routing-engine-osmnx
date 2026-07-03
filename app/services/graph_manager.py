# app/services/graph_manager.py
"""Routing-graph lifecycle.

Two modes:

- **Dynamic** (default): a graph is (re)built on demand around each
  origin/destination pair, capped at MAX_GRAPH_RADIUS_M. Good for local
  experimentation; unsuitable for a public deployment (every new area
  triggers a live Overpass download).
- **Preloaded** (``preload()``): one fixed-area graph is built at startup
  (and cached to disk as GraphML), after which the manager is *frozen* —
  requests outside the covered area fail fast with GraphAreaError instead
  of triggering downloads. This is the mode a public instance runs in.

The OSMnx download and nearest-node strategies are injectable so tests can
supply a tiny in-memory graph without patching environment variables.
"""
import math
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import networkx as nx

from app.core.errors import GraphAreaError
from app.core.logger import logger
from app.models.routing import Coordinate

Bbox = Tuple[float, float, float, float]  # (north, south, east, west)
GraphBuilder = Callable[[float, float, float], nx.MultiDiGraph]
NearestFn = Callable[[nx.MultiDiGraph, Coordinate], Any]


class GraphManager:
    """Manages the routing graph and nearest-node lookups."""

    MAX_GRAPH_RADIUS_M = 15_000.0  # cap for any downloaded graph

    def __init__(
        self,
        graph_builder: Optional[GraphBuilder] = None,
        nearest_fn: Optional[NearestFn] = None,
    ) -> None:
        self.graph: Optional[nx.MultiDiGraph] = None
        self.bbox: Optional[Bbox] = None
        self.frozen: bool = False
        self._graph_builder = graph_builder or self._build_osmnx_graph
        self._nearest_fn = nearest_fn or self._nearest_node_osmnx
        logger.info("GraphManager initialised (graph will be built on demand).")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def preload(self, center_lat: float, center_lon: float, radius_m: float,
                cache_dir: str | None = None) -> None:
        """Build (or load from disk cache) one fixed-area graph and freeze.

        After preloading, requests outside the covered area raise
        GraphAreaError instead of triggering a rebuild.
        """
        radius_m = min(radius_m, self.MAX_GRAPH_RADIUS_M)
        G: Optional[nx.MultiDiGraph] = None
        cache_file = None
        if cache_dir:
            cache_file = (Path(cache_dir) /
                          f"graph_{center_lat:.4f}_{center_lon:.4f}_{int(radius_m)}.graphml")
            if cache_file.exists():
                import osmnx as ox
                logger.info(f"Loading preloaded graph from cache: {cache_file}")
                G = ox.load_graphml(cache_file)

        if G is None:
            logger.info(f"Preloading graph around ({center_lat:.4f}, {center_lon:.4f}), "
                        f"radius {radius_m:.0f} m")
            G = self._graph_builder(center_lat, center_lon, radius_m)
            if cache_file:
                import osmnx as ox
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                ox.save_graphml(G, cache_file)
                logger.info(f"Preloaded graph cached to {cache_file}")

        G = self._ensure_numeric_weights(G)
        self.graph = G
        self.bbox = self._bbox_from_graph(G, center_lat, center_lon)
        self.frozen = True
        logger.info(f"Preloaded graph ready and FROZEN: "
                    f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    def ensure_graph_for_points(self, origin: Coordinate, destination: Coordinate) -> None:
        """Ensure the graph covers both points; rebuild only in dynamic mode."""
        if self.graph is not None and self._bbox_contains_points(origin, destination):
            return
        if self.frozen:
            raise GraphAreaError(
                "This instance serves a fixed area and one of the requested "
                "points lies outside it. Pick origin and destination inside "
                "the highlighted coverage area."
            )
        self._build_graph_for_points(origin, destination)

    def find_nearest_node(self, coord: Coordinate) -> Any:
        if self.graph is None:
            raise RuntimeError("Graph not initialised. Call ensure_graph_for_points() first.")
        node_id = self._nearest_fn(self.graph, coord)
        logger.info(f"Nearest node for ({coord.lat:.6f}, {coord.lon:.6f}) -> node {node_id}")
        return node_id

    # ------------------------------------------------------------------ #
    # Strategies (injectable)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_osmnx_graph(center_lat: float, center_lon: float,
                           radius_m: float) -> nx.MultiDiGraph:
        import osmnx as ox
        return ox.graph_from_point(
            center_point=(center_lat, center_lon),
            dist=radius_m,
            network_type="drive",
            simplify=True,
        )

    @staticmethod
    def _nearest_node_osmnx(G: nx.MultiDiGraph, coord: Coordinate) -> Any:
        import osmnx as ox
        return ox.distance.nearest_nodes(G, X=coord.lon, Y=coord.lat)

    @staticmethod
    def nearest_node_euclidean(G: nx.MultiDiGraph, coord: Coordinate) -> Any:
        """Plain Euclidean nearest-node search in degree space.

        Exact enough for small test graphs and CRS-free fixtures; used by the
        test-suite as the injected nearest_fn.
        """
        nearest, best = None, float("inf")
        for node_id, data in G.nodes(data=True):
            x, y = data.get("x"), data.get("y")
            if x is None or y is None:
                continue
            d2 = (x - coord.lon) ** 2 + (y - coord.lat) ** 2
            if d2 < best:
                best, nearest = d2, node_id
        if nearest is None:
            raise RuntimeError("No node with coordinates found in graph.")
        return nearest

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _bbox_contains_points(self, origin: Coordinate, destination: Coordinate) -> bool:
        if self.bbox is None:
            return False
        north, south, east, west = self.bbox
        return all(south <= c.lat <= north and west <= c.lon <= east
                   for c in (origin, destination))

    def _build_graph_for_points(self, origin: Coordinate, destination: Coordinate) -> None:
        """Dynamic mode: build a graph around the OD midpoint (radius capped)."""
        distance_m = self._haversine_distance_m(origin, destination)
        if distance_m > 2.0 * self.MAX_GRAPH_RADIUS_M:
            logger.warning(
                f"OD distance ~{distance_m:.0f} m exceeds "
                f"2×MAX_GRAPH_RADIUS_M={2.0 * self.MAX_GRAPH_RADIUS_M:.0f} m; "
                "the graph cannot fully cover both endpoints."
            )

        radius_m = min(1.5 * distance_m + 2_000.0, self.MAX_GRAPH_RADIUS_M)
        center_lat = (origin.lat + destination.lat) / 2.0
        center_lon = (origin.lon + destination.lon) / 2.0

        logger.info(f"Building OSM graph around ({center_lat:.6f}, {center_lon:.6f}), "
                    f"radius {radius_m:.0f} m (OD distance ~{distance_m:.0f} m)")
        G = self._graph_builder(center_lat, center_lon, radius_m)
        G = self._ensure_numeric_weights(G)
        self.graph = G
        self.bbox = self._bbox_from_graph(G, center_lat, center_lon)
        logger.info(f"Graph ready: {G.number_of_nodes()} nodes, "
                    f"{G.number_of_edges()} edges; bbox {self.bbox}")

    @staticmethod
    def _bbox_from_graph(G: nx.MultiDiGraph, center_lat: float, center_lon: float) -> Bbox:
        xs = [d.get("x") for _, d in G.nodes(data=True) if d.get("x") is not None]
        ys = [d.get("y") for _, d in G.nodes(data=True) if d.get("y") is not None]
        if xs and ys:
            return (max(ys), min(ys), max(xs), min(xs))
        return (center_lat + 1.0, center_lat - 1.0, center_lon + 1.0, center_lon - 1.0)

    def _ensure_numeric_weights(self, G: nx.MultiDiGraph) -> nx.MultiDiGraph:
        """Guarantee every edge has a numeric 'weight' attribute (metres)."""
        num_fixed = num_missing = 0
        for u, v, _k, data in G.edges(keys=True, data=True):
            length = data.get("length")
            if isinstance(length, str):
                try:
                    length = float(length)
                except ValueError:
                    length = None
            if length is None:
                lat_u, lon_u = G.nodes[u].get("y"), G.nodes[u].get("x")
                lat_v, lon_v = G.nodes[v].get("y"), G.nodes[v].get("x")
                if None in (lat_u, lon_u, lat_v, lon_v):
                    num_missing += 1
                    continue
                length = self._haversine_distance_m(
                    Coordinate(lat=lat_u, lon=lon_u),
                    Coordinate(lat=lat_v, lon=lon_v),
                )
            try:
                data["weight"] = float(length)
                num_fixed += 1
            except (TypeError, ValueError):
                num_missing += 1
        logger.info(f"Edge weights normalised: {num_fixed} ok, "
                    f"{num_missing} without valid length/coords.")
        return G

    @staticmethod
    def _haversine_distance_m(a: Coordinate, b: Coordinate) -> float:
        """Great-circle distance between two lat/lon points, in metres."""
        R = 6_371_000.0
        lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
        lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))
