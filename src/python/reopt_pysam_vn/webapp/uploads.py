"""Load ingestion via the mature ingestion library (PHASE-05)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

__all__ = ["UploadError", "parse_load_upload", "screen_load_plausibility"]

_HOURS = 8760
_SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xlsm", ".xls", ".json"}


class UploadError(ValueError):
    pass


def screen_load_plausibility(loads_kw: list[float]) -> list[str]:
    """Return advisory strings for unusual load shapes (never raises)."""
    adv: list[str] = []
    if not loads_kw:
        return adv
    zero_frac = sum(1 for v in loads_kw if v == 0.0) / len(loads_kw)
    if zero_frac > 0.20:
        pct = round(zero_frac * 100, 1)
        adv.append(f"{pct}% of hours are zero")
    mx = max(loads_kw) if loads_kw else 0.0
    if mx > 0:
        mean = sum(loads_kw) / len(loads_kw)
        lf = mean / mx if mx else 0.0
        if lf < 0.10:
            adv.append(f"load factor {lf:.3f} is unusually low")
        if mx > 1_000_000:
            adv.append(f"peak {mx:.0f} kW is unusually large; check the units are kW, not W")
    return adv


def parse_load_upload(content: bytes, filename: str) -> tuple[list[float], dict[str, Any]]:
    """Parse an uploaded load file via :func:`ingestion.loader.ingest_factory_load`.

    Returns ``(series_8760, cleaning_summary)`` where the summary includes the
    loader's cleaning metrics plus any ``plausibility_warnings``.
    Raises :class:`UploadError` on unsupported suffix, unreadable file, or a
    series length the loader cannot resolve to 8760.
    """
    if not content or not content.strip():
        raise UploadError("upload is empty; expected an 8760-row hourly kW column")
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise UploadError(f"unsupported file type {suffix!r}; accepted: csv, xlsx, xls, xlsm, json")

    from reopt_pysam_vn.ingestion.loader import LoadLengthError, ingest_factory_load

    tmp_path: Path | None = None
    try:
        # Windows: close handle before second reader opens the path.
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)  # noqa: SIM115
        tmp_path = Path(tmp.name)
        tmp.write(content)
        tmp.close()
        try:
            result = ingest_factory_load(tmp_path)
        except LoadLengthError as exc:
            raise UploadError(str(exc)) from exc
        except (ValueError, KeyError, OSError) as exc:
            raise UploadError(str(exc)) from exc
        except Exception as exc:
            raise UploadError(str(exc)) from exc

        summary: dict[str, Any] = dict(result.cleaning_summary)
        # Ensure keys expected by tests/spec are present.
        summary.setdefault("original_row_count", len(result.loads_kw))
        # Add plausibility advisories
        plaus = screen_load_plausibility(result.loads_kw)
        if plaus:
            summary["plausibility_warnings"] = plaus
        # Include detected column when available for timestamped CSV test.
        summary.setdefault("detected_column", result.detected_column)
        return result.loads_kw, summary
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
