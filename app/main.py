# app/main.py

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import routes_health, routes_routing
from app.core.logger import logger

# BASE_DIR = .../app
BASE_DIR = Path(__file__).resolve().parent
# PROJECT_ROOT = parent of app → .../
PROJECT_ROOT = BASE_DIR.parent
# STATIC_DIR = .../static
STATIC_DIR = PROJECT_ROOT / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Routing API",
        version="0.1.0",
        description="Routing API with a Leaflet frontend served from /map.",
    )

    # Routers
    app.include_router(routes_health.router, prefix="", tags=["health"])
    app.include_router(routes_routing.router, prefix="", tags=["routing"])

    # Serve /static/* from the static folder at project root
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/map")
    async def map_page() -> FileResponse:
        """
        Serve the frontend map page from static/index.html
        """
        logger.info("Serving /map from %s", INDEX_FILE)

        if not INDEX_FILE.exists():
            logger.error("index.html not found at %s", INDEX_FILE)
            raise HTTPException(status_code=404, detail="index.html not found")

        return FileResponse(INDEX_FILE)

    return app


app = create_app()
