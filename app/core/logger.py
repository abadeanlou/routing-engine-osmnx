# app/core/logger.py
from loguru import logger
import sys

# Configure logger format
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "{message}",
    level="INFO",
)

__all__ = ["logger"]
