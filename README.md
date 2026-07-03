# routing-engine-osmnx

[![ci](https://github.com/abadeanlou/routing-engine-osmnx/actions/workflows/ci.yml/badge.svg)](https://github.com/abadeanlou/routing-engine-osmnx/actions/workflows/ci.yml)

A small, production-shaped routing engine: **FastAPI** REST API, street
networks from **OSMnx** (OpenStreetMap), shortest paths with **NetworkX**,
and a **Leaflet** map frontend — click origin and destination, get the
routed path with distance and duration.

**Live demo: <https://abadeanlou.com/routing-engine/>** — central Milan,
preloaded-graph mode, self-hosted on GCP behind Caddy.

## How it works

```
Leaflet map (/map)  ->  POST /route/  ->  RoutingService
                                            |- GraphManager: OSM graph (dynamic or preloaded+frozen)
                                            |- nearest-node snap (OSMnx)
                                            |- Dijkstra shortest path (weight = metres)
                                            '- geometry from edge shapes -> [lat, lon] polyline
```

Two graph modes:

- **Dynamic** (default, local development): the graph is built on demand
  around each origin/destination pair (radius capped at 15 km). Every new
  area triggers a live Overpass download — convenient locally, unsuitable
  for a public instance.
- **Preloaded** (`PRELOAD_GRAPH=true`, what the Docker image defaults to):
  one fixed-area graph is downloaded once at startup, cached to disk as
  GraphML, and **frozen** — requests outside the covered area get a clean
  HTTP 422 instead of triggering downloads. This is the mode a public
  deployment runs in.

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000/map     (interactive docs at /docs)
```

Or containerised (preloaded-Milan mode by default; first start downloads
and caches the graph, later starts reuse the cache volume):

```bash
docker build -t routing-engine .
docker run -p 8000:8000 -v routing-cache:/app/cache routing-engine
```

Configuration (env vars or `.env`): `PRELOAD_GRAPH`, `PRELOAD_LAT`,
`PRELOAD_LON`, `PRELOAD_RADIUS_M`, `GRAPH_CACHE_DIR`.

## API

`POST /route/` with:

```json
{
  "origin":      {"lat": 45.4642, "lon": 9.19},
  "destination": {"lat": 45.48,   "lon": 9.25}
}
```

Returns distance (m), duration (s, constant 40 km/h assumption), per-edge
steps, and the route polyline. **Note:** coordinates are returned as
`[lat, lon]` pairs (Leaflet ordering), not GeoJSON `[lon, lat]`.

Errors are explicit: out-of-coverage points and unreachable destinations
both return HTTP 422 with a human-readable reason.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests -v
```

The suite runs entirely offline: a tiny in-memory street network is
injected through `GraphManager`'s pluggable graph-builder and
nearest-node strategies — production code contains no test-mode branches.
Covered: routing on the dummy network (including the shortest-vs-direct
choice), one-way no-path handling, frozen-instance area rejection, and
dynamic-mode rebuild behaviour.

## Design notes & limits

- Handlers that do blocking graph work are deliberately **sync** so
  FastAPI runs them in its threadpool instead of stalling the event loop.
- Duration is distance / 40 km/h — a placeholder, not a traffic model.
- One graph per process: concurrent requests in *dynamic* mode can thrash
  the graph; preloaded mode is immutable and therefore concurrency-safe.
- Built by [Amirhesam Badeanlou](https://abadeanlou.com) — see also
  [bikeflow](https://abadeanlou.com/bikeflow/), a live data pipeline and
  forecasting project.
