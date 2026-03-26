"""
Logger centralisé avec Loguru.
Colore la sortie en dev, format JSON structuré en prod.
"""

import sys
from pathlib import Path

from loguru import logger

from src.common.config import settings

# Supprime le handler par défaut
logger.remove()

if settings.is_production:
    # Format JSON structuré → compatible avec les log aggregators (CloudWatch, etc.)
    logger.add(
        sys.stdout,
        format='{"time": "{time:YYYY-MM-DDTHH:mm:ss.SSS}Z", "level": "{level}", "module": "{module}", "message": "{message}"}',
        level=settings.log_level,
        serialize=False,
    )
    # Fichier rotatif (30 jours de rétention)
    logger.add(
        "logs/devlife.log",
        rotation="00:00",
        retention="30 days",
        level="WARNING",
        compression="gz",
    )
else:
    # Format coloré pour le développement
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan> — {message}",
        level=settings.log_level,
    )

__all__ = ["logger"]
