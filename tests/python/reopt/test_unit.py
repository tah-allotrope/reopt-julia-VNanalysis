"""
Layer 2: Unit Tests for reopt_pysam_vn.reopt.preprocess (Python)

Tests the preprocessing logic in isolation â€” fast, no API keys or solver needed.
Each function is tested for correct behavior, edge cases, and non-destructive merging.
Mirror of legacy/julia/tests/test_unit.jl â€” identical checks, same data files.

Run: pytest tests/python/reopt/test_unit.py -v
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

from reopt_pysam_vn.reopt.preprocess import (
    VNData,
    apply_decree57_export,
    apply_vietnam_defaults,
    apply_vietnam_emissions,
    apply_vietnam_financials,
    apply_vietnam_tech_costs,
    build_vietnam_tariff,
    convert_usd_to_vnd,
    convert_vnd_to_usd,
    load_vietnam_data,
    resolve_vietnam_regime,
    zero_us_incentives,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vn():
    return load_vietnam_data()


def make_base_dict(pv=True, wind=False, storage=True, generator=False):
    """Create a minimal scenario dict with common tech blocks."""
    d = {
        "Site": {"latitude": 10.8, "longitude": 106.6},
        "ElectricLoad": {"doe_reference_name": "Hospital", "annual_kwh": 1_000_000},
    }
    if pv:
        d["PV"] = {"max_kw": 500}
    if wind:
        d["Wind"] = {"max_kw": 200}
    if storage:
        d["ElectricStorage"] = {"max_kw": 200, "max_kwh": 800}
    if generator:
        d["Generator"] = {"max_kw": 100}
    return d


# ===================================================================
# 1. load_vietnam_data
# ===================================================================


class TestLoadVietnamData:
    def test_returns_vndata(self, vn):
        assert isinstance(vn, VNData)

    def test_exchange_rate(self, vn):
        assert vn.exchange_rate == 26400.0

    def test_tariff_is_dict(self, vn):
        assert isinstance(vn.tariff, dict)
        assert "base_avg_price_vnd_per_kwh" in vn.tariff

    def test_tech_costs_is_dict(self, vn):
        assert isinstance(vn.tech_costs, dict)
        assert "PV" in vn.tech_costs

    def test_financials_is_dict(self, vn):
        assert isinstance(vn.financials, dict)
        assert "standard" in vn.financials

    def test_emissions_is_dict(self, vn):
        assert isinstance(vn.emissions, dict)
        assert "grid_emission_factor_lb_CO2_per_kwh" in vn.emissions

    def test_export_rules_is_dict(self, vn):
        assert isinstance(vn.export_rules, dict)
        assert "rooftop_solar" in vn.export_rules

    def test_regimes_is_dict(self, vn):
        assert isinstance(vn.regimes, dict)
        assert "regimes" in vn.regimes
        assert "decision_963_2026_current" in vn.regimes["regimes"]

    def test_bad_manifest_path(self):
        with pytest.raises((FileNotFoundError, OSError)):
            load_vietnam_data(manifest_path="nonexistent.json")


# ===================================================================
# 2. Currency conversion
# ===================================================================


class TestCurrencyConversion:
    def test_vnd_to_usd_identity(self):
        assert convert_vnd_to_usd(26400, exchange_rate=26400) == pytest.approx(1.0)

    def test_vnd_to_usd_zero(self):
        assert convert_vnd_to_usd(0, exchange_rate=26400) == pytest.approx(0.0)

    def test_vnd_to_usd_double(self):
        assert convert_vnd_to_usd(52800, exchange_rate=26400) == pytest.approx(2.0)

    def test_vnd_to_usd_precise(self):
        assert convert_vnd_to_usd(2204.07, exchange_rate=26400) == pytest.approx(
            2204.07 / 26400, abs=1e-10
        )

    def test_usd_to_vnd_identity(self):
        assert convert_usd_to_vnd(1.0, exchange_rate=26400) == pytest.approx(26400.0)

    def test_usd_to_vnd_zero(self):
        assert convert_usd_to_vnd(0.0, exchange_rate=26400) == pytest.approx(0.0)

    def test_usd_to_vnd_precise(self):
        assert convert_usd_to_vnd(0.0834875, exchange_rate=26400) == pytest.approx(
            0.0834875 * 26400, abs=1e-6
        )

    def test_round_trip(self):
        original_vnd = 50_000.0
        usd = convert_vnd_to_usd(original_vnd, exchange_rate=26400)
        back_to_vnd = convert_usd_to_vnd(usd, exchange_rate=26400)
        assert back_to_vnd == pytest.approx(original_vnd, abs=1e-8)

    def test_invalid_exchange_rate_zero(self):
        with pytest.raises(ValueError):
            convert_vnd_to_usd(100, exchange_rate=0)

    def test_invalid_exchange_rate_negative(self):
        with pytest.raises(ValueError):
            convert_vnd_to_usd(100, exchange_rate=-1)

    def test_invalid_exchange_rate_usd_to_vnd(self):
        with pytest.raises(ValueError):
            convert_usd_to_vnd(100, exchange_rate=0)


# ===================================================================
# 3. zero_us_incentives
# ===================================================================


class TestZeroUSIncentives:
    def test_pv(self):
        d = make_base_dict()
        d["PV"]["federal_itc_fraction"] = 0.30
        d["PV"]["macrs_option_years"] = 5
        zero_us_incentives(d)

        assert d["PV"]["federal_itc_fraction"] == 0
        assert d["PV"]["macrs_option_years"] == 0
        assert d["PV"]["macrs_bonus_fraction"] == 0
        assert d["PV"]["state_ibi_fraction"] == 0
        assert d["PV"]["utility_ibi_fraction"] == 0
        assert d["PV"]["production_incentive_per_kwh"] == 0

    def test_electric_storage(self):
        d = make_base_dict()
        d["ElectricStorage"]["total_itc_fraction"] = 0.30
        zero_us_incentives(d)

        assert d["ElectricStorage"]["total_itc_fraction"] == 0
        assert d["ElectricStorage"]["macrs_option_years"] == 0
        assert d["ElectricStorage"]["total_rebate_per_kw"] == 0

    def test_wind(self):
        d = make_base_dict(wind=True)
        zero_us_incentives(d)

        assert d["Wind"]["federal_itc_fraction"] == 0
        assert d["Wind"]["macrs_option_years"] == 0
        assert d["Wind"]["production_incentive_per_kwh"] == 0

    def test_generator(self):
        d = make_base_dict(generator=True)
        zero_us_incentives(d)

        assert d["Generator"]["federal_itc_fraction"] == 0
        assert d["Generator"]["macrs_option_years"] == 0
        assert d["Generator"]["federal_rebate_per_kw"] == 0

    def test_pv_as_list(self):
        d = make_base_dict()
        d["PV"] = [
            {"name": "roof_east", "max_kw": 200, "federal_itc_fraction": 0.30},
            {"name": "roof_west", "max_kw": 300, "federal_itc_fraction": 0.26},
        ]
        zero_us_incentives(d)

        for pv in d["PV"]:
            assert pv["federal_itc_fraction"] == 0
            assert pv["macrs_option_years"] == 0

    def test_missing_tech_blocks_no_error(self):
        d = {"Site": {"latitude": 10.0}}
        zero_us_incentives(d)  # should not raise


# ===================================================================
# 4. apply_vietnam_financials
# ===================================================================


class TestApplyVietnamFinancials:
    def test_standard_profile(self, vn):
        d = make_base_dict()
        apply_vietnam_financials(d, vn, financial_profile="standard")

        fin = d["Financial"]
        assert fin["offtaker_tax_rate_fraction"] == 0.20
        assert fin["owner_tax_rate_fraction"] == 0.20
        assert fin["offtaker_discount_rate_fraction"] == 0.10
        assert fin["owner_discount_rate_fraction"] == 0.08
        assert fin["elec_cost_escalation_rate_fraction"] == 0.04
        assert fin["om_cost_escalation_rate_fraction"] == 0.03
        assert fin["analysis_years"] == 25

    def test_re_preferential_profile(self, vn):
        d = make_base_dict()
        apply_vietnam_financials(
            d, vn, financial_profile="renewable_energy_preferential"
        )

        fin = d["Financial"]
        assert fin["offtaker_tax_rate_fraction"] == 0.10
        # Blended rate should be applied for owner
        assert fin["owner_tax_rate_fraction"] == 0.066

    def test_user_value_preserved(self, vn):
        d = make_base_dict()
        d["Financial"] = {"offtaker_tax_rate_fraction": 0.15}
        apply_vietnam_financials(d, vn, financial_profile="standard")

        assert d["Financial"]["offtaker_tax_rate_fraction"] == 0.15  # user value wins
        assert (
            d["Financial"]["owner_discount_rate_fraction"] == 0.08
        )  # default injected

    def test_invalid_profile(self, vn):
        d = make_base_dict()
        with pytest.raises(ValueError):
            apply_vietnam_financials(d, vn, financial_profile="nonexistent")


# ===================================================================
# 5. build_vietnam_tariff
# ===================================================================


class TestBuildVietnamTariff:
    def test_decision_963_window_shift_removes_morning_peak(self, vn):
        tariff = build_vietnam_tariff(
            vn,
            "industrial",
            "medium_voltage_22kv_to_110kv",
            regime_id="decision_963_2026_current",
            year=2025,
        )

        monday_rates = tariff["tou_energy_rates_per_kwh"][0:24]
        assert monday_rates[9] == pytest.approx(monday_rates[8], abs=1e-10)
        assert monday_rates[17] > monday_rates[16]

    def test_default_tariff_uses_decision_963_windows(self, vn):
        tariff = build_vietnam_tariff(
            vn, "industrial", "medium_voltage_22kv_to_110kv", year=2025
        )

        rates = tariff["tou_energy_rates_per_kwh"]
        assert len(rates) == 8760

        base_vnd = vn.tariff["base_avg_price_vnd_per_kwh"]
        mults = vn.tariff["rate_multipliers"]["industrial"][
            "medium_voltage_22kv_to_110kv"
        ]
        peak_rate = base_vnd * mults["peak"] / vn.exchange_rate
        standard_rate = base_vnd * mults["standard"] / vn.exchange_rate

        monday_rates = rates[0:24]
        for h in [17, 18, 19, 20, 21, 22]:
            assert monday_rates[h] == pytest.approx(peak_rate, abs=1e-8), f"Hour {h} should be peak"
        for h in [9, 10]:
            assert monday_rates[h] == pytest.approx(standard_rate, abs=1e-8), f"Hour {h} should be standard (not peak)"

    def test_legacy_decision_14_still_works(self, vn):
        tariff = build_vietnam_tariff(
            vn,
            "industrial",
            "medium_voltage_22kv_to_110kv",
            regime_id="decision_14_2025_legacy",
            year=2025,
        )

        rates = tariff["tou_energy_rates_per_kwh"]
        base_vnd = vn.tariff["base_avg_price_vnd_per_kwh"]
        mults = vn.tariff["rate_multipliers"]["industrial"]["medium_voltage_22kv_to_110kv"]
        peak_rate = base_vnd * mults["peak"] / vn.exchange_rate
        standard_rate = base_vnd * mults["standard"] / vn.exchange_rate

        monday_rates = rates[0:24]
        for h in [9, 10, 17, 18, 19]:
            assert monday_rates[h] == pytest.approx(peak_rate, abs=1e-8), f"Hour {h} should be peak under Decision 14"
        for h in [20, 21]:
            assert monday_rates[h] == pytest.approx(standard_rate, abs=1e-8), f"Hour {h} should be standard under Decision 14"

    def test_alias_resolves_to_legacy(self, vn):
        tariff_alias = build_vietnam_tariff(
            vn,
            "industrial",
            "medium_voltage_22kv_to_110kv",
            regime_id="decision_14_2025_current",
            year=2025,
        )
        tariff_legacy = build_vietnam_tariff(
            vn,
            "industrial",
            "medium_voltage_22kv_to_110kv",
            regime_id="decision_14_2025_legacy",
            year=2025,
        )

        assert tariff_alias["tou_energy_rates_per_kwh"] == tariff_legacy["tou_energy_rates_per_kwh"]

    def test_industrial_medium_voltage(self, vn):
        tariff = build_vietnam_tariff(
            vn, "industrial", "medium_voltage_22kv_to_110kv", year=2025
        )

        assert "tou_energy_rates_per_kwh" in tariff
        rates = tariff["tou_energy_rates_per_kwh"]
        assert len(rates) == 8760
        assert all(r > 0 for r in rates)

        # Decision 963 default: peak hours 17-22, standard includes 9 and 10
        base_vnd = vn.tariff["base_avg_price_vnd_per_kwh"]
        mults = vn.tariff["rate_multipliers"]["industrial"][
            "medium_voltage_22kv_to_110kv"
        ]
        expected_peak = base_vnd * mults["peak"] / vn.exchange_rate
        expected_offpeak = base_vnd * mults["offpeak"] / vn.exchange_rate

        assert max(rates) == pytest.approx(expected_peak, abs=1e-8)
        assert min(rates) == pytest.approx(expected_offpeak, abs=1e-8)

    def test_commercial_low_voltage(self, vn):
        tariff = build_vietnam_tariff(
            vn, "commercial", "low_voltage_1kv_and_below", year=2025
        )
        rates = tariff["tou_energy_rates_per_kwh"]
        assert len(rates) == 8760
        assert max(rates) > min(rates)

    def test_household_flat(self, vn):
        tariff = build_vietnam_tariff(vn, "household", "", year=2025)
        rates = tariff["tou_energy_rates_per_kwh"]
        assert len(rates) == 8760
        # Household is flat â€” all values should be identical
        assert all(r == pytest.approx(rates[0]) for r in rates)
        assert rates[0] > 0

    def test_sunday_vs_weekday_pattern(self, vn):
        tariff = build_vietnam_tariff(
            vn, "industrial", "medium_voltage_22kv_to_110kv", year=2025
        )
        rates = tariff["tou_energy_rates_per_kwh"]

        # 2025-01-01 is a Wednesday. First Sunday = Jan 5 (day index 4, 0-based)
        # Sunday hours: index 4*24 to 4*24+23 = 96 to 119
        sunday_rates = rates[96:120]
        # Sunday has no peak hours â€” max should be standard rate
        base_vnd = vn.tariff["base_avg_price_vnd_per_kwh"]
        mults = vn.tariff["rate_multipliers"]["industrial"][
            "medium_voltage_22kv_to_110kv"
        ]
        expected_standard = base_vnd * mults["standard"] / vn.exchange_rate
        expected_peak = base_vnd * mults["peak"] / vn.exchange_rate

        # Sunday should NOT have peak rate
        sunday_key = (
            "sunday"
            if "sunday" in vn.tariff["tou_schedule"]
            else "sunday_and_public_holidays"
        )
        sunday_peak_hours = vn.tariff["tou_schedule"][sunday_key]["peak_hours"]
        if len(sunday_peak_hours) == 0:
            assert expected_peak not in sunday_rates
        # Sunday max should be standard
        assert max(sunday_rates) == pytest.approx(expected_standard, abs=1e-8)

        # Decision 963: off-peak hours are 0-5, not 22-23
        # Monday (weekday) hour 22 should be peak, not off-peak
        monday_rates = rates[0:24]
        assert monday_rates[22] == pytest.approx(expected_peak, abs=1e-8)
        # Monday hour 5 should be off-peak
        expected_offpeak = base_vnd * mults["offpeak"] / vn.exchange_rate
        assert monday_rates[5] == pytest.approx(expected_offpeak, abs=1e-8)

    def test_demand_charges(self, vn):
        tariff = build_vietnam_tariff(vn, "industrial", "medium_voltage_22kv_to_110kv")
        assert "monthly_demand_rates" in tariff
        assert len(tariff["monthly_demand_rates"]) == 12
        # Currently 0 for Vietnam
        assert all(r == 0 for r in tariff["monthly_demand_rates"])

    def test_invalid_customer_type(self, vn):
        with pytest.raises(ValueError):
            build_vietnam_tariff(vn, "government", "medium_voltage_22kv_to_110kv")

    def test_invalid_voltage_level(self, vn):
        with pytest.raises(ValueError):
            build_vietnam_tariff(vn, "industrial", "ultra_high_voltage")


# ===================================================================
# 6. apply_vietnam_emissions
# ===================================================================


class TestApplyVietnamEmissions:
    def test_emissions_injected(self, vn):
        d = make_base_dict()
        apply_vietnam_emissions(d, vn)

        assert "ElectricUtility" in d
        eu = d["ElectricUtility"]
        assert "emissions_factor_series_lb_CO2_per_kwh" in eu
        ef = eu["emissions_factor_series_lb_CO2_per_kwh"]
        assert len(ef) == 8760
        assert ef[0] == pytest.approx(1.5013, abs=1e-4)
        assert all(v == pytest.approx(ef[0]) for v in ef)  # constant series

    def test_user_value_preserved(self, vn):
        d = make_base_dict()
        custom_series = [2.0] * 8760
        d["ElectricUtility"] = {"emissions_factor_series_lb_CO2_per_kwh": custom_series}
        apply_vietnam_emissions(d, vn)

        assert d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"][
            0
        ] == pytest.approx(2.0)


# ===================================================================
# 7. apply_vietnam_tech_costs
# ===================================================================


class TestApplyVietnamTechCosts:
    def test_pv_rooftop_south(self, vn):
        d = make_base_dict()
        apply_vietnam_tech_costs(d, vn, region="south", pv_type="rooftop")

        assert d["PV"]["installed_cost_per_kw"] == 600
        assert d["PV"]["om_cost_per_kw"] == 8
        assert d["PV"]["dc_ac_ratio"] == 1.2  # common default
        assert d["PV"]["losses"] == 0.14

    def test_pv_ground_north(self, vn):
        d = make_base_dict()
        apply_vietnam_tech_costs(d, vn, region="north", pv_type="ground")

        assert d["PV"]["installed_cost_per_kw"] == 550
        assert d["PV"]["om_cost_per_kw"] == 9

    def test_electric_storage_south(self, vn):
        d = make_base_dict()
        apply_vietnam_tech_costs(d, vn, region="south")

        assert d["ElectricStorage"]["installed_cost_per_kw"] == 370
        assert d["ElectricStorage"]["installed_cost_per_kwh"] == 270
        assert d["ElectricStorage"]["installed_cost_constant"] == 0
        assert d["ElectricStorage"]["replace_cost_per_kw"] == 200
        assert d["ElectricStorage"]["replace_cost_per_kwh"] == 150

    def test_wind_onshore_central(self, vn):
        d = make_base_dict(wind=True)
        apply_vietnam_tech_costs(d, vn, region="central", wind_type="onshore")

        assert d["Wind"]["installed_cost_per_kw"] == 1300
        assert d["Wind"]["om_cost_per_kw"] == 26

    def test_generator_diesel(self, vn):
        d = make_base_dict(generator=True)
        apply_vietnam_tech_costs(d, vn, region="south")

        assert d["Generator"]["installed_cost_per_kw"] == 500
        assert d["Generator"]["fuel_cost_per_gallon"] == 4.50

    def test_user_cost_preserved(self, vn):
        d = make_base_dict()
        d["PV"]["installed_cost_per_kw"] = 800  # user override
        apply_vietnam_tech_costs(d, vn, region="south")

        assert d["PV"]["installed_cost_per_kw"] == 800  # user value wins
        assert d["PV"]["om_cost_per_kw"] == 8  # default injected

    def test_invalid_region(self, vn):
        d = make_base_dict()
        with pytest.raises(ValueError):
            apply_vietnam_tech_costs(d, vn, region="west")

    def test_pv_as_list(self, vn):
        d = make_base_dict()
        d["PV"] = [
            {"name": "roof_east", "max_kw": 200},
            {"name": "roof_west", "max_kw": 300},
        ]
        apply_vietnam_tech_costs(d, vn, region="south", pv_type="rooftop")

        # First PV gets regional costs
        assert d["PV"][0]["installed_cost_per_kw"] == 600
        # Both get common defaults
        for pv in d["PV"]:
            assert pv["dc_ac_ratio"] == 1.2
            assert pv["federal_itc_fraction"] == 0


# ===================================================================
# 8. apply_decree57_export
# ===================================================================


class TestApplyDecree57Export:
    def test_regime_specific_export_fraction(self, vn):
        d = make_base_dict()
        apply_decree57_export(d, vn, regime_id="decree57_rooftop_50pct_draft")

        assert d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.50)
        assert d["_meta"]["resolved_regime_id"] == "decree57_rooftop_50pct_draft"

    def test_export_rules_applied(self, vn):
        d = make_base_dict()
        apply_decree57_export(d, vn)

        et = d["ElectricTariff"]
        assert et["wholesale_rate"] == pytest.approx(0.0254, abs=1e-4)
        assert et["export_rate_beyond_net_metering_limit"] == 0

        pv = d["PV"]
        assert pv["can_net_meter"] is False
        assert pv["can_wholesale"] is True
        assert pv["can_export_beyond_nem_limit"] is False
        assert pv["can_curtail"] is True
        assert d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.50)

    def test_user_wholesale_rate_preserved(self, vn):
        d = make_base_dict()
        d["ElectricTariff"] = {"wholesale_rate": 0.05}
        apply_decree57_export(d, vn)

        assert d["ElectricTariff"]["wholesale_rate"] == 0.05  # user value wins

    def test_non_default_max_export_fraction_warns(self, vn):
        d = make_base_dict()
        with pytest.warns(
            UserWarning,
            match=r"max_export_fraction=.*stored for Vietnam custom solve wrappers",
        ):
            apply_decree57_export(d, vn, max_export_fraction=0.10)
        assert d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.10)

    def test_default_max_export_fraction_no_warning(self, vn):
        d = make_base_dict()
        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error", UserWarning)
            apply_decree57_export(d, vn, max_export_fraction=0.50)  # must not raise

    def test_invalid_max_export_fraction_errors(self, vn):
        d = make_base_dict()
        with pytest.raises(ValueError):
            apply_decree57_export(d, vn, max_export_fraction=1.1)

    def test_explicit_legacy_fraction_now_warns(self, vn):
        """Decree 243/2026 raised the enacted cap to 50%; explicitly passing
        the pre-243 20% value is now a caller override of the active
        regulatory default and must warn, not the reverse."""
        d = make_base_dict()
        with pytest.warns(
            UserWarning,
            match=r"max_export_fraction=.*stored for Vietnam custom solve wrappers",
        ):
            apply_decree57_export(d, vn, max_export_fraction=0.20)
        assert d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.20)

    def test_legacy_regime_restores_20pct_without_warning(self, vn):
        d = make_base_dict()
        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error", UserWarning)
            apply_decree57_export(d, vn, regime_id="decree_57_2025_legacy")
        assert d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.20)


# ===================================================================
# 9. apply_vietnam_defaults â€” master function
# ===================================================================


class TestApplyVietnamDefaults:
    def test_default_regime_preserves_baseline_behavior(self, vn):
        explicit = make_base_dict()
        implicit = make_base_dict()

        apply_vietnam_defaults(explicit, vn, regime_id="decision_963_2026_current")
        apply_vietnam_defaults(implicit, vn)

        assert implicit["_meta"]["resolved_regime_id"] == "decision_963_2026_current"
        assert implicit["ElectricTariff"]["tou_energy_rates_per_kwh"] == explicit["ElectricTariff"]["tou_energy_rates_per_kwh"]
        assert implicit["_meta"]["decree57_max_export_fraction"] == explicit["_meta"]["decree57_max_export_fraction"]

    def test_two_part_tariff_trial_injects_monthly_demand_rate(self, vn):
        d = make_base_dict()
        apply_vietnam_defaults(d, vn, regime_id="decree146_two_part_trial_2026")

        assert d["ElectricTariff"]["monthly_demand_rates"] == pytest.approx([235414 / vn.exchange_rate] * 12)
        assert d["_meta"]["resolved_regime_id"] == "decree146_two_part_trial_2026"
        assert d["_meta"]["bess_capacity_payment_vnd_per_kw_month"] == 0

    def test_decision_14_legacy_changes_tariff_shape(self, vn):
        baseline = make_base_dict()
        shifted = make_base_dict()

        apply_vietnam_defaults(baseline, vn)
        apply_vietnam_defaults(
            shifted,
            vn,
            regime_id="decision_14_2025_legacy",
        )

        assert baseline["ElectricTariff"]["tou_energy_rates_per_kwh"] != shifted["ElectricTariff"]["tou_energy_rates_per_kwh"]
        assert shifted["_meta"]["resolved_regime_id"] == "decision_14_2025_legacy"

    def test_full_pipeline(self, vn):
        d = make_base_dict(wind=True, generator=True)
        apply_vietnam_defaults(
            d,
            vn,
            customer_type="industrial",
            voltage_level="medium_voltage_22kv_to_110kv",
            region="south",
        )

        # Financial injected
        assert "Financial" in d
        assert d["Financial"]["offtaker_tax_rate_fraction"] == 0.20

        # Tariff injected
        assert "ElectricTariff" in d
        assert "tou_energy_rates_per_kwh" in d["ElectricTariff"]
        assert len(d["ElectricTariff"]["tou_energy_rates_per_kwh"]) == 8760

        # Emissions injected
        assert "ElectricUtility" in d
        assert (
            len(d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]) == 8760
        )

        # Tech costs injected
        assert d["PV"]["installed_cost_per_kw"] == 600
        assert d["Wind"]["installed_cost_per_kw"] == 1350
        assert d["ElectricStorage"]["installed_cost_constant"] == 0
        assert d["Generator"]["installed_cost_per_kw"] == 500

        # Incentives zeroed
        assert d["PV"]["federal_itc_fraction"] == 0
        assert d["Wind"]["federal_itc_fraction"] == 0
        assert d["ElectricStorage"]["total_itc_fraction"] == 0
        assert d["Generator"]["federal_itc_fraction"] == 0

        # Export rules
        assert d["PV"]["can_net_meter"] is False
        assert d["ElectricTariff"]["wholesale_rate"] == pytest.approx(0.0254, abs=1e-4)
        assert d["_meta"]["decree57_max_export_fraction"] == pytest.approx(0.50)
        assert d["_meta"]["resolved_regime_id"] == "decision_963_2026_current"


class TestResolveVietnamRegime:
    def test_resolves_tariff_and_export_overrides(self, vn):
        resolved = resolve_vietnam_regime(vn, "decree57_rooftop_50pct_draft")

        assert resolved["regime_id"] == "decree57_rooftop_50pct_draft"
        assert resolved["export_rules"]["rooftop_solar"]["max_export_fraction"] == pytest.approx(0.5)
        assert resolved["tariff"]["base_avg_price_vnd_per_kwh"] == vn.tariff["base_avg_price_vnd_per_kwh"]

    def test_unknown_regime_errors(self, vn):
        with pytest.raises(ValueError):
            resolve_vietnam_regime(vn, "missing_regime")

    def test_selective_disable(self, vn):
        d = make_base_dict()
        apply_vietnam_defaults(
            d,
            vn,
            apply_tariff=False,
            apply_emissions=False,
            apply_export_rules=False,
        )

        # Financial and tech costs should still be applied
        assert "Financial" in d
        assert d["PV"]["installed_cost_per_kw"] == 600

        # Tariff, emissions, export should NOT be applied
        assert "ElectricUtility" not in d
        et = d.get("ElectricTariff", {})
        assert "tou_energy_rates_per_kwh" not in et
        assert "wholesale_rate" not in et

    def test_non_destructive_comprehensive(self, vn):
        d = {
            "Site": {"latitude": 10.8, "longitude": 106.6},
            "ElectricLoad": {"doe_reference_name": "Hospital", "annual_kwh": 500_000},
            "PV": {
                "installed_cost_per_kw": 800,
                "max_kw": 1000,
                "can_net_meter": True,  # user explicitly wants net metering
            },
            "ElectricStorage": {
                "installed_cost_per_kwh": 350,
                "max_kwh": 2000,
            },
            "Financial": {
                "offtaker_tax_rate_fraction": 0.15,
            },
            "ElectricTariff": {
                "wholesale_rate": 0.05,
            },
            "ElectricUtility": {
                "emissions_factor_series_lb_CO2_per_kwh": [2.0] * 8760,
            },
        }

        apply_vietnam_defaults(d, vn, region="south")

        # All user values preserved
        assert d["PV"]["installed_cost_per_kw"] == 800
        assert d["PV"]["max_kw"] == 1000
        assert d["PV"]["can_net_meter"] is True
        assert d["ElectricStorage"]["installed_cost_per_kwh"] == 350
        assert d["ElectricStorage"]["max_kwh"] == 2000
        assert d["Financial"]["offtaker_tax_rate_fraction"] == 0.15
        assert d["ElectricTariff"]["wholesale_rate"] == 0.05
        assert d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"][
            0
        ] == pytest.approx(2.0)

        # Defaults still injected where user didn't specify
        assert d["PV"]["om_cost_per_kw"] == 8
        assert d["ElectricStorage"]["installed_cost_constant"] == 0
        assert d["Financial"]["owner_discount_rate_fraction"] == 0.08


class TestDealDefaultsConfig:
    def test_config_file_exists(self):
        config_path = REPO_ROOT / "data" / "vietnam" / "vn_deal_defaults_2026.json"
        assert config_path.exists(), "vn_deal_defaults_2026.json not found"

    def test_config_file_is_valid_json(self):
        config_path = REPO_ROOT / "data" / "vietnam" / "vn_deal_defaults_2026.json"
        import json
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        assert "_meta" in raw
        cfg = raw["data"]
        assert "exchange_rate" in cfg
        assert "debt_terms" in cfg
        assert "analysis" in cfg
        assert "dppa" in cfg
        assert "bess" in cfg
        assert "sensitivity_ranges" in cfg

    def test_config_debt_terms_are_reasonable(self):
        import json
        config_path = REPO_ROOT / "data" / "vietnam" / "vn_deal_defaults_2026.json"
        cfg = json.loads(config_path.read_text(encoding="utf-8"))["data"]
        debt = cfg["debt_terms"]
        assert 0.0 < debt["debt_fraction"] < 1.0
        assert 0.0 < debt["interest_rate"] < 0.20
        assert debt["debt_tenor_years"] >= 1

    def test_config_exchange_rate_is_reasonable(self):
        import json
        config_path = REPO_ROOT / "data" / "vietnam" / "vn_deal_defaults_2026.json"
        cfg = json.loads(config_path.read_text(encoding="utf-8"))["data"]
        rate = cfg["exchange_rate"]["vnd_per_usd"]
        assert 20_000 <= rate <= 30_000

    def test_manifest_registers_deal_defaults(self):
        manifest_path = REPO_ROOT / "data" / "vietnam" / "manifest.json"
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "deal_defaults" in manifest
        assert manifest["deal_defaults"] == "vn_deal_defaults_2026.json"


class TestSensitivitySweep:
    def test_range_f_utility(self):
        from reopt_pysam_vn.reopt.preprocess import load_vietnam_data
        vn = load_vietnam_data()
        cfg = vn.financials
        assert cfg is not None
        assert "standard" in cfg
        assert "owner_discount_rate_fraction" in cfg["standard"]

    def test_extract_ebitda_from_minimal_results(self):
        minimal_results = {
            "Financial": {
                "lcc": 1_000_000,
                "npv": 200_000,
                "initial_capital_costs": 500_000,
            },
            "ElectricTariff": {
                "year_one_energy_cost_before": 100_000,
                "year_one_energy_cost_after": 80_000,
            },
        }
        from scripts.python.reopt.sensitivity_sweep import extract_base_ebitda
        ebitda = extract_base_ebitda(minimal_results, analysis_years=20)
        assert len(ebitda) == 20
        assert ebitda[0] > 0

    def test_compute_equity_irr_returns_dict(self):
        from scripts.python.reopt.sensitivity_sweep import compute_equity_irr
        result = compute_equity_irr(
            ebitda_series=[1_000_000] * 20,
            total_capex=49_510_000,
            debt_fraction=0.70,
            interest_rate=0.085,
            debt_tenor_years=10,
            analysis_years=20,
        )
        assert "equity_irr" in result
        assert "equity_npv" in result
        assert result["equity_investment"] > 0

