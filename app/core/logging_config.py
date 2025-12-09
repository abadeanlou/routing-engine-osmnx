# app/core/logging_config.py
from loguru import logger
import sys


def setup_logging() -> None:
    """
    Configure application-wide logging using loguru.
    """
    # Remove default handler added by loguru
    logger.remove()

    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
