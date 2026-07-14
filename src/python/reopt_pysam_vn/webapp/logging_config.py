"""Structured logging setup for the web app (PHASE-01, strategic-lens DEC-105).

Installs one stream handler on the ``reopt_pysam_vn`` package logger so every
module's ``logging.getLogger(__name__)`` calls reach stdout with a consistent
format, instead of the prior mix of bare ``print()`` calls and unconfigured
loggers.
"""

from __future__ import annotations

import logging

__all__ = ["configure_logging"]

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_CONFIGURED_ATTR = "_reopt_pysam_vn_configured"


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotently install a stream handler on the ``reopt_pysam_vn`` logger."""
    logger = logging.getLogger("reopt_pysam_vn")
    if getattr(logger, _CONFIGURED_ATTR, False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(level)
    setattr(logger, _CONFIGURED_ATTR, True)
