"""Sanitization helpers for REopt API payloads and results.

Relocated from the (now removed) ``archive/colab`` colab reference script during the
2026-06-12 repo de-bloat so the canonical package owns the logic its tests exercise.
"""

from __future__ import annotations

from typing import Any

__all__ = ["redact_sensitive_fields"]


def redact_sensitive_fields(payload: Any) -> Any:
    """Recursively drop ``api_key`` entries from a nested dict/list payload.

    Used before persisting or logging REopt API request/response bodies so secrets
    never land in tracked artifacts. Non-container values pass through unchanged;
    the comparison is case-insensitive on the key name.
    """
    if isinstance(payload, dict):
        return {
            key: redact_sensitive_fields(value)
            for key, value in payload.items()
            if not (isinstance(key, str) and key.lower() == "api_key")
        }
    if isinstance(payload, list):
        return [redact_sensitive_fields(item) for item in payload]
    return payload
