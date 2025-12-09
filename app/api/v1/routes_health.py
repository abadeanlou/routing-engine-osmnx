# app/api/v1/routes_health.py
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/", summary="Health check")
async def health_check():
    """
    Simple health check endpoint to verify that the API is running.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
