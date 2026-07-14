"""Maps internal exceptions to analyst-facing error fields (PHASE-01, DEC-105).

``to_user_error`` never returns the raw exception message for genuinely
unexpected errors (programming bugs like ``KeyError``/``TypeError``) — those
get a generic message plus a hint to check the server log (which still gets
the full traceback via ``logger.exception``). Known, actionable exceptions
(missing inputs, no orchestrator, no API key, and REopt solve-pipeline
failures such as ``RuntimeError("REopt job failed with status: infeasible")``
or a poll ``TimeoutError``) keep their specific message since it already
names what to fix.
"""

from __future__ import annotations

from typing import Any, Dict

from reopt_pysam_vn.webapp.service import (
    AnalysisError,
    MissingInputsError,
    OrchestratorNotRegisteredError,
)

__all__ = ["to_user_error"]

_MISSING_INPUTS_HINT = (
    "Upload the required pre-solved inputs, or submit an onsite deal for a live solve."
)
_NO_ORCHESTRATOR_HINT = (
    "This deal case has no offsite model yet; use a registered case or the generic runner."
)
_NO_API_KEY_HINT = "Set NREL_DEVELOPER_API_KEY or run in offline mode."
_SOLVER_HTTP_HINT = "Check site coordinates and load profile; retry, or run offline."
_SOLVER_ERROR_HINT = "Check site coordinates and load profile; retry, or run offline."
_INTERNAL_HINT = "See the server log for the full traceback (run_id is logged)."


def to_user_error(exc: Exception) -> Dict[str, Any]:
    """Return ``{"code", "message", "hint"}`` for ``exc``, suitable for display."""
    message = str(exc)

    if isinstance(exc, MissingInputsError):
        return {"code": "MISSING_INPUTS", "message": message, "hint": _MISSING_INPUTS_HINT}

    if isinstance(exc, OrchestratorNotRegisteredError):
        return {"code": "NO_ORCHESTRATOR", "message": message, "hint": _NO_ORCHESTRATOR_HINT}

    if isinstance(exc, AnalysisError):
        return {"code": "MISSING_INPUTS", "message": message, "hint": _MISSING_INPUTS_HINT}

    if isinstance(exc, RuntimeError) and "NREL API key not found" in message:
        return {
            "code": "NO_API_KEY",
            "message": "No NREL API key configured.",
            "hint": _NO_API_KEY_HINT,
        }

    try:
        import requests

        if isinstance(exc, requests.RequestException):
            return {
                "code": "SOLVER_HTTP_ERROR",
                "message": "The NREL REopt solver rejected or could not process this request.",
                "hint": _SOLVER_HTTP_HINT,
            }
    except ImportError:
        pass

    # Known REopt solve-pipeline failures (job rejected, infeasible, timed out)
    # raise plain RuntimeError/TimeoutError with an already-actionable message
    # (see reopt/preprocess.py:run_vietnam_reopt) — keep it, don't genericize.
    if isinstance(exc, (RuntimeError, TimeoutError)):
        return {"code": "SOLVER_ERROR", "message": message, "hint": _SOLVER_ERROR_HINT}

    return {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred while processing this run.",
        "hint": _INTERNAL_HINT,
    }
