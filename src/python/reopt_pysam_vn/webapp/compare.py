"""Two-run side-by-side comparison view-model (PHASE-05, DEC-018).

Reuses ``results_view`` metric extraction so a metric only needs to be taught
to one place; aligns on shared metric labels and computes a numeric delta
when both sides are numbers. Mixed modes degrade to the (possibly empty)
intersection of metrics rather than erroring.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from reopt_pysam_vn.webapp.results_view import build_view_model

__all__ = ["build_compare_model"]


def build_compare_model(
    mode_a: str, result_a: Optional[Dict[str, Any]], mode_b: str, result_b: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    view_a = build_view_model(mode_a, result_a)
    view_b = build_view_model(mode_b, result_b)

    metrics_a = {m["label"]: m["value"] for m in view_a.get("metrics", [])}
    metrics_b = {m["label"]: m["value"] for m in view_b.get("metrics", [])}

    rows = []
    for label in metrics_a:
        if label not in metrics_b:
            continue
        a_val, b_val = metrics_a[label], metrics_b[label]
        delta = None
        if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
            delta = b_val - a_val
        rows.append({"label": label, "a": a_val, "b": b_val, "delta": delta})

    return {"mode_a": mode_a, "mode_b": mode_b, "rows": rows}
