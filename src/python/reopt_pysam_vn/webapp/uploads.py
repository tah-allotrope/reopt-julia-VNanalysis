"""Parse an hourly load-profile upload into ``loads_kw`` (DEC-016: simple
single-column CSV/xlsx only — no full workbook extraction)."""

from __future__ import annotations

import csv
import io
from typing import List

__all__ = ["UploadError", "parse_load_csv", "parse_load_xlsx"]

_HOURS = 8760


class UploadError(ValueError):
    pass


def _first_numeric_column(rows: List[List[str]]) -> List[float]:
    cells = [row[0].strip() for row in rows if row and row[0].strip()]
    if not cells:
        return []

    # A one-line text header is only distinguishable from a genuine bad value
    # by row count: an 8761-row file whose first cell doesn't parse is a
    # header; an 8760-row file with a bad first cell is a real data error.
    has_header = len(cells) == _HOURS + 1
    if has_header:
        try:
            float(cells[0])
            has_header = False  # first cell is numeric; not a header after all
        except ValueError:
            pass

    data_cells = cells[1:] if has_header else cells
    values: List[float] = []
    for cell in data_cells:
        try:
            values.append(float(cell))
        except ValueError:
            raise UploadError(f"non-numeric value in load column: {cell!r}") from None
    return values


def _validate_length(values: List[float]) -> List[float]:
    if not values:
        raise UploadError("upload is empty; expected an 8760-row hourly kW column")
    if len(values) != _HOURS:
        raise UploadError(
            f"expected {_HOURS} hourly kW values, got {len(values)}"
        )
    return values


def parse_load_csv(content: bytes) -> List[float]:
    if not content.strip():
        raise UploadError("upload is empty; expected an 8760-row hourly kW column")
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    values = _first_numeric_column(rows)
    return _validate_length(values)


def parse_load_xlsx(content: bytes) -> List[float]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = [[str(cell) if cell is not None else "" for cell in (row[0],)] for row in ws.iter_rows(values_only=True)]
    values = _first_numeric_column(rows)
    return _validate_length(values)
