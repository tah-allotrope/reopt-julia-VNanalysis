"""C2.1: one series semantic, shared by every case module.

``_pad_to_8760`` existed in four case modules and the variants had already
drifted: ``dppa_case_1`` returned the slice uncoerced while ``dppa_case_2`` and
``dppa_case_3`` coerced every element to ``float``. ``_sum_series``,
``_annual_energy_kwh`` and ``_financial_value`` were byte-identical triplicates.

These tests pin the single semantic the shared module must have. The coercing
variant wins: it is what two of the three modules already did, and it makes the
type of a series independent of what the caller happened to pass in.
"""

from __future__ import annotations

import pytest
from reopt_pysam_vn.common.series import (
    HOURS,
    annual_energy_kwh,
    financial_value,
    pad_to_8760,
    sum_series,
)


class TestPadTo8760:
    def test_pads_short_series_with_zeros(self):
        assert pad_to_8760([1.0, 2.0]) == [1.0, 2.0] + [0.0] * (HOURS - 2)

    def test_truncates_long_series(self):
        assert len(pad_to_8760([1.0] * (HOURS + 500))) == HOURS

    def test_exact_length_is_unchanged_in_value(self):
        series = [float(index % 7) for index in range(HOURS)]
        assert pad_to_8760(series) == series

    def test_always_coerces_to_float(self):
        """The drifted dppa_case_1 variant did not. Ints in, floats out."""
        padded = pad_to_8760([1, 2, 3])

        assert padded[:3] == [1.0, 2.0, 3.0]
        assert all(isinstance(value, float) for value in padded[:3])

    def test_coerces_when_truncating_too(self):
        padded = pad_to_8760([2] * (HOURS + 10))
        assert all(isinstance(value, float) for value in padded[:5])


class TestSumSeries:
    def test_adds_elementwise_and_pads_to_8760(self):
        summed = sum_series([1.0, 2.0], [10.0, 20.0, 30.0])

        assert len(summed) == HOURS
        assert summed[:3] == [11.0, 22.0, 30.0]

    def test_a_single_series_is_just_padded(self):
        assert sum_series([5.0])[:2] == [5.0, 0.0]


class TestReoptResultReaders:
    def test_annual_energy_prefers_year_one_key(self):
        assert annual_energy_kwh({"year_one_energy_produced_kwh": 1_234.0}) == 1_234.0

    def test_annual_energy_falls_back_to_annual_key(self):
        assert annual_energy_kwh({"annual_energy_produced_kwh": 99.0}) == 99.0

    def test_annual_energy_defaults_to_zero(self):
        assert annual_energy_kwh({}) == 0.0

    def test_financial_value_reads_the_financial_block(self):
        assert financial_value({"Financial": {"npv": 5.0}}, "npv", 0.0) == 5.0

    def test_financial_value_uses_the_default_when_absent_or_zero(self):
        assert financial_value({}, "npv", 7.0) == 7.0
        # Falsy stored values fall through to the default — the long-standing
        # semantic of the triplicated helper, pinned here deliberately.
        assert financial_value({"Financial": {"npv": 0}}, "npv", 7.0) == 7.0


@pytest.mark.parametrize(
    "module_name",
    [
        "dppa_case_1",
        "dppa_case_2",
        "dppa_case_3",
        "dppa_samsung_ttc",
        "ninhsim_solar_storage_60pct",
    ],
)
def test_case_modules_do_not_redefine_the_series_helpers(module_name):
    """The point of the shared module: no case module keeps its own copy."""
    import inspect
    from importlib import import_module

    module = import_module(f"reopt_pysam_vn.integration.{module_name}")
    source = inspect.getsource(module)

    for helper in ("_pad_to_8760", "_sum_series", "_annual_energy_kwh", "_financial_value"):
        assert f"def {helper}(" not in source, (
            f"{module_name} still defines its own {helper}; it should use common.series"
        )
