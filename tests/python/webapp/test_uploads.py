"""PHASE-03: hourly load-profile upload parsing (CSV / basic .xlsx)."""

import io

import pytest
from reopt_pysam_vn.webapp.uploads import UploadError, parse_load_csv, parse_load_xlsx

_HOURS = 8760


def test_parse_csv_single_column_no_header():
    text = "\n".join(str(100.0 + i * 0.001) for i in range(_HOURS))
    loads = parse_load_csv(text.encode("utf-8"))
    assert len(loads) == _HOURS
    assert loads[0] == pytest.approx(100.0)


def test_parse_csv_with_header():
    text = "kw\n" + "\n".join("50.5" for _ in range(_HOURS))
    loads = parse_load_csv(text.encode("utf-8"))
    assert len(loads) == _HOURS
    assert all(v == 50.5 for v in loads)


def test_parse_csv_rejects_wrong_length():
    text = "\n".join("1.0" for _ in range(100))
    with pytest.raises(UploadError, match="8760"):
        parse_load_csv(text.encode("utf-8"))


def test_parse_csv_rejects_non_numeric():
    text = "\n".join(["abc"] + ["1.0"] * (_HOURS - 1))
    with pytest.raises(UploadError, match="numeric"):
        parse_load_csv(text.encode("utf-8"))


def test_parse_csv_rejects_empty_file():
    with pytest.raises(UploadError, match="empty"):
        parse_load_csv(b"")


def test_parse_xlsx_single_column():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["kw"])
    for i in range(_HOURS):
        ws.append([200.0 + i * 0.01])
    buf = io.BytesIO()
    wb.save(buf)
    loads = parse_load_xlsx(buf.getvalue())
    assert len(loads) == _HOURS
    assert loads[0] == pytest.approx(200.0)
