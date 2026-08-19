"""PHASE-05: load ingestion via the mature loader."""

import io

import pytest
from reopt_pysam_vn.webapp.uploads import UploadError, parse_load_upload, screen_load_plausibility

_HOURS = 8760


def test_parse_single_column_csv():
    text = "load_kw\n" + "\n".join("1000" for _ in range(_HOURS))
    series, summary = parse_load_upload(text.encode("utf-8"), "load.csv")
    assert len(series) == _HOURS
    assert all(v == 1000.0 for v in series)
    assert summary["original_row_count"] == _HOURS


def test_parse_15min_csv():
    text = "load_kw\n" + "\n".join("1000" for _ in range(35040))
    series, summary = parse_load_upload(text.encode("utf-8"), "load.csv")
    assert len(series) == _HOURS
    assert summary.get("synthesis_method")
    assert summary.get("synthesis_method") != "none"
    assert summary["synthesis_source_rows"] == 35040


def test_parse_timestamped_two_column_csv():
    text = "timestamp,load_kw\n" + "\n".join("2024-01-01 00:00,1000" for _ in range(_HOURS))
    series, summary = parse_load_upload(text.encode("utf-8"), "load.csv")
    assert len(series) == _HOURS
    assert summary.get("detected_column") == "load_kw"


def test_parse_gaps():
    rows = ["1000"] * _HOURS
    rows[100] = ""
    rows[101] = ""
    rows[102] = ""
    text = "load_kw\n" + "\n".join(rows)
    series, summary = parse_load_upload(text.encode("utf-8"), "load.csv")
    assert len(series) == _HOURS
    assert summary["missing_count"] == 3
    # interpolated values between neighbours (both 1000)
    assert series[100] == pytest.approx(1000.0)
    assert series[101] == pytest.approx(1000.0)


def test_parse_negatives():
    rows = ["1000"] * _HOURS
    rows[49] = "-5"
    text = "load_kw\n" + "\n".join(rows)
    series, summary = parse_load_upload(text.encode("utf-8"), "load.csv")
    assert series[49] == 0.0
    assert summary["clipped_negative_count"] == 1


def test_parse_unsupported_suffix():
    with pytest.raises(UploadError, match="csv"):
        parse_load_upload(b"xxx", "load.txt")
    # message should name accepted list
    try:
        parse_load_upload(b"xxx", "load.txt")
    except UploadError as exc:
        msg = str(exc).lower()
        assert "csv" in msg and "xlsx" in msg and "json" in msg


def test_parse_empty():
    with pytest.raises(UploadError, match="empty"):
        parse_load_upload(b"", "load.csv")


def test_screen_load_plausibility():
    assert any("zero" in s.lower() for s in screen_load_plausibility([0.0] * 5000 + [1000.0] * 3760))
    assert screen_load_plausibility([1000.0] * _HOURS) == []
    assert any("kW, not W" in s for s in screen_load_plausibility([2_000_000.0] * _HOURS))


def test_parse_xlsx_single_column():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["load_kw"])
    for _ in range(_HOURS):
        ws.append([200.0])
    buf = io.BytesIO()
    wb.save(buf)
    series, summary = parse_load_upload(buf.getvalue(), "load.xlsx")
    assert len(series) == _HOURS
    assert series[0] == pytest.approx(200.0)


def test_parse_json():
    import json

    data = {"loads_kw": [1000.0] * _HOURS}
    series, summary = parse_load_upload(json.dumps(data).encode("utf-8"), "load.json")
    assert len(series) == _HOURS
