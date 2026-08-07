import pytest

PySAM = pytest.importorskip("PySAM")


def test_pysam_import_available():
    assert PySAM is not None
