# app/services/routing_service.py

from time import perf_counter
from typing import List, Tuple

import networkx as nx

from app.core.logger import logger
from app.models.routing import (
    Coordinate,
    RouteRequest,
    RouteResponse,
    RouteGeometry,
    RouteSummary,
    RouteStep,
)
from app.services.graph_manager import GraphManager


class RoutingService:
    """
    High-level routing service:
    - ensures a suitable graph is available
    - finds nearest graph nodes for origin/destination
    - computes shortest path
    - builds geometry using edge shapes where available
    """

    # Simple constant speed in km/h for converting distance -> duration.
    DEFAULT_SPEED_KMH: float = 40.0

    def __init__(self, graph_manager: GraphManager | None = None) -> None:
        self.graph_manager = graph_manager or GraphManager()
        logger.info("RoutingService initialised (graph will be built on demand).")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def compute_route(self, request: RouteRequest) -> RouteResponse:
        """
        Main entry point for the /route endpoint.

        1. Ensure graph covers origin + destination.
        2. Find nearest graph nodes.
        3. Compute shortest path (by 'weight' = metres).
        4. Build geometry using full edge shapes (when available).
        5. Aggregate distance and compute duration.
        6. Build per-edge steps list.
        """
        t0 = perf_counter()

        origin: Coordinate = request.origin
        destination: Coordinate = request.destination

        logger.info(
            "Received routing request from (%.6f, %.6f) -> (%.6f, %.6f)",
            origin.lat,
            origin.lon,
            destination.lat,
            destination.lon,
        )

        # 1) Ensure graph
        t_graph0 = perf_counter()
        self.graph_manager.ensure_graph_for_points(origin, destination)
        t_graph1 = perf_counter()
        logger.info(
            "Graph ensured for request in %.2f ms",
            (t_graph1 - t_graph0) * 1000.0,
        )

        G = self.graph_manager.graph
        if G is None:
            raise RuntimeError("Graph is not initialised after ensure_graph_for_points().")

        # 2) Nearest-node lookups
        t_nn0 = perf_counter()
        origin_node = self.graph_manager.find_nearest_node(origin)
        destination_node = self.graph_manager.find_nearest_node(destination)
        t_nn1 = perf_counter()
        logger.info(
            "Nearest-node lookup: origin_node=%s, destination_node=%s, time=%.2f ms",
            origin_node,
            destination_node,
            (t_nn1 - t_nn0) * 1000.0,
        )

        # 3) Shortest path (by distance)
        t_sp0 = perf_counter()
        path: List[int] = nx.shortest_path(
            G,
            source=origin_node,
            target=destination_node,
            weight="weight",
        )
        t_sp1 = perf_counter()
        logger.info(
            "Shortest path found with %d nodes in %.2f ms",
            len(path),
            (t_sp1 - t_sp0) * 1000.0,
        )

        # 4) Geometry from edge shapes
        coords: List[List[float]] = self._build_coordinates_from_path(G, path)

        # 5) Steps and total distance
        steps, distance_m = self._build_steps_from_path(G, path)

        # 6) Total duration from distance
        duration_s: float = self._compute_duration_from_distance(distance_m)

        logger.info(
            "Route summary: distance=%.1f m, duration=%.1f s",
            distance_m,
            duration_s,
        )

        t1 = perf_counter()
        logger.info("Total routing time: %.2f ms", (t1 - t0) * 1000.0)

        # Top-level GeoJSON-like geometry object
        geometry = RouteGeometry(
            type="LineString",
            coordinates=coords,  # [ [lat, lon], ... ]
        )

        # Summary: tests expect geometry to be a plain list of [lat, lon]
        summary = RouteSummary(
            distance_m=distance_m,
            duration_s=duration_s,
            geometry=coords,
        )
        
        warnings = []

        if distance_m > 2.0 * self.graph_manager.MAX_GRAPH_RADIUS_M:
            warnings.append(
                f"Route distance ({distance_m:.0f} m) exceeds 2×max graph radius "
                f"({2 * self.graph_manager.MAX_GRAPH_RADIUS_M:.0f} m). "
                "Routing may fail or be incomplete."
            )

        
        return RouteResponse(
            distance_m=distance_m,
            duration_s=duration_s,
            geometry=geometry,
            summary=summary,
            steps=steps,
            warnings=warnings,
        )


    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_coordinates_from_path(
        self,
        G: nx.MultiDiGraph,
        path: List[int],
    ) -> List[List[float]]:
        """
        Build polyline coordinates for the route using **edge geometries**.

        - If an edge has a 'geometry' attribute (shapely LineString), we take all
          its points.
        - If not, we fall back to straight segments between node coordinates.
        - Output format is [ [lat, lon], ... ] which is what the Leaflet map uses.
        """
        if not path:
            return []

        # Trivial single-node path (edge case)
        if len(path) == 1:
            node_id = path[0]
            nd = G.nodes[node_id]
            return [[nd.get("y"), nd.get("x")]]

        coords: List[List[float]] = []

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]

            edge_dict = G.get_edge_data(u, v, default=None)
            geom = None

            if edge_dict:
                # MultiDiGraph: pick the first edge key
                first_key = next(iter(edge_dict))
                data = edge_dict[first_key]
                geom = data.get("geometry")

            if geom is not None:
                # Use the shapely LineString geometry: coords are (x, y) = (lon, lat)
                segment_points = list(geom.coords)
                for j, (x, y) in enumerate(segment_points):
                    # Avoid repeating the first point of each segment
                    # except for the very first segment.
                    if i > 0 and j == 0:
                        continue
                    coords.append([y, x])  # [lat, lon]
            else:
                # Fallback: use node coordinates (straight segment)
                node_u = G.nodes[u]
                node_v = G.nodes[v]

                lat_u, lon_u = node_u.get("y"), node_u.get("x")
                lat_v, lon_v = node_v.get("y"), node_v.get("x")

                if i == 0:
                    coords.append([lat_u, lon_u])  # starting point
                coords.append([lat_v, lon_v])

        return coords

    def _build_steps_from_path(
        self,
        G: nx.MultiDiGraph,
        path: List[int],
    ) -> Tuple[List[RouteStep], float]:
        """
        Build per-edge steps and compute total distance.

        Each step corresponds to one edge (u, v) in the path.
        """
        steps: List[RouteStep] = []
        total_distance = 0.0

        if len(path) < 2:
            return steps, total_distance

        speed_mps = self.DEFAULT_SPEED_KMH * 1000.0 / 3600.0
        if speed_mps <= 0:
            speed_mps = 1.0  # just to avoid division by zero

        for u, v in zip(path[:-1], path[1:]):
            edge_dict = G.get_edge_data(u, v, default=None)
            if not edge_dict:
                continue

            first_key = next(iter(edge_dict))
            data = edge_dict[first_key]
            w = data.get("weight")

            if not isinstance(w, (int, float)):
                continue

            dist = float(w)
            total_distance += dist
            dur = dist / speed_mps

            steps.append(
                RouteStep(
                    from_node=int(u),
                    to_node=int(v),
                    distance_m=dist,
                    duration_s=dur,
                )
            )

        return steps, total_distance

    def _compute_duration_from_distance(self, distance_m: float) -> float:
        """
        Convert distance in metres to duration in seconds using a simple constant speed.
        """
        if distance_m <= 0:
            return 0.0

        speed_mps = self.DEFAULT_SPEED_KMH * 1000.0 / 3600.0
        if speed_mps <= 0:
            return 0.0

        return distance_m / speed_mps
