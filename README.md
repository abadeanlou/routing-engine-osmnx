# Routing Engine with FastAPI + OSMnx

This project is a lightweight routing engine built on:

-   **FastAPI** for the backend REST API
-   **OSMnx + NetworkX** for dynamic street-network extraction and
    routing
-   **Leaflet** for the frontend map UI (`/map` endpoint)

It allows you to click an origin and destination on a map and get a
routed path with distance and duration.

## Features

-   Dynamic OSM graph extraction around the selected OD pair
-   Shortest-path routing with NetworkX
-   GeoJSON-like polyline geometry returned by the API
-   Interactive Leaflet map (`static/index.html`)
-   Clean separation of backend (`app/`) and frontend (`static/`)

## Project structure

    .
    ├─ app/           # FastAPI app (main.py, routers, services, models)
    ├─ static/        # Frontend (index.html and assets)
    ├─ tests/         # Unit tests (pytest)
    ├─ cache/         # Local cache (ignored in .gitignore)
    └─ requirements.txt

## How to run

    # 1. Create and activate a virtual environment (optional but recommended)
    python -m venv .venv
    .\.venv\Scripts\activate      # Windows
    # source .venv/bin/activate   # Linux / macOS

    # 2. Install dependencies
    pip install -r requirements.txt

    # 3. Start the API
    uvicorn app.main:app --reload

Then open:

-   API docs: http://127.0.0.1:8000/docs
-   Map UI: http://127.0.0.1:8000/map


