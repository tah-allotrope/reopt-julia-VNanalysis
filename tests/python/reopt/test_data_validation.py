"""
Layer 1: Data File Validation Tests (Python)

Pure schema and sanity checks on the Vietnam JSON data files.
Runs WITHOUT a solver â€” only reads and validates the data layer.
Mirror of tests/julia/test_data_validation.jl â€” identical checks, same data files.

Run: pytest tests/python/reopt/test_data_validation.py -v
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "vietnam"
MANIFEST_PATH = DATA_DIR / "manifest.json"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_data_file(manifest: dict, key: str):
    filename = manifest[key]
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f), filename


# ===================================================================
# 1. Manifest structure
# ===================================================================


class TestManifestStructure:
    REQUIRED_KEYS = [
        "tariff",
        "tech_costs",
        "financials",
        "emissions",
        "export_rules",
        "regimes",
    ]

    def test_required_keys_present(self, manifest):
        for k in self.REQUIRED_KEYS:
            assert k in manifest, f"manifest.json missing required key: {k}"

    def test_referenced_files_exist(self, manifest):
        for k in self.REQUIRED_KEYS:
            filename = manifest[k]
            filepath = DATA_DIR / filename
            assert filepath.is_file(), f"File not found: {filepath}"


# ===================================================================
# 2. Schema compliance â€” every file has _meta + data
# ===================================================================


class TestSchemaCompliance:
    REQUIRED_META_FIELDS = ["version", "effective_date", "source", "last_updated"]

    @pytest.mark.parametrize(
        "key",
        ["tariff", "tech_costs", "financials", "emissions", "export_rules", "regimes"],
    )
    def test_meta_and_data_blocks(self, manifest, key):
        raw, filename = _load_data_file(manifest, key)
        assert "_meta" in raw, f"{filename} missing _meta block"
        assert "data" in raw, f"{filename} missing data block"

        meta = raw["_meta"]
        for field in self.REQUIRED_META_FIELDS:
            assert field in meta, f"{filename}._meta missing field: {field}"


# ===================================================================
# 3. Tariff sanity
# ===================================================================


class TestTariffSanity:
    @pytest.fixture(scope="class")
    def tariff_data(self, manifest):
        raw, _ = _load_data_file(manifest, "tariff")
        return raw["data"]

    def test_base_price_positive(self, tariff_data):
        assert "base_avg_price_vnd_per_kwh" in tariff_data
        base = tariff_data["base_avg_price_vnd_per_kwh"]
        assert base > 0
        assert base < 100_000

    @pytest.mark.parametrize("day_type", ["weekday", "sunday_and_public_holidays"])
    def test_tou_schedule_completeness(self, tariff_data, day_type):
        schedule = tariff_data["tou_schedule"]
        assert day_type in schedule
        block = schedule[day_type]

        all_hours = []
        for period in ["peak_hours", "standard_hours", "offpeak_hours"]:
            assert period in block, f"{day_type} missing {period}"
            all_hours.extend(int(h) for h in block[period])

        assert sorted(set(all_hours)) == list(range(24)), (
            f"{day_type} TOU hours don't cover 0-23: got {sorted(set(all_hours))}"
        )

    def test_industrial_multipliers(self, tariff_data):
        mults = tariff_data["rate_multipliers"]
        assert "industrial" in mults

        for vl_name, vl in mults["industrial"].items():
            if not isinstance(vl, dict):
                continue
            assert "peak" in vl, f"industrial.{vl_name} missing peak"
            assert "standard" in vl, f"industrial.{vl_name} missing standard"
            assert "offpeak" in vl, f"industrial.{vl_name} missing offpeak"
            assert vl["peak"] > vl["standard"] > vl["offpeak"], (
                f"industrial.{vl_name}: peak > standard > offpeak violated"
            )
            assert vl["peak"] > 0
            assert vl["offpeak"] > 0

    def test_commercial_multipliers(self, tariff_data):
        mults = tariff_data["rate_multipliers"]
        assert "commercial" in mults

        for subcategory, subcat_rates in mults["commercial"].items():
            if not isinstance(subcat_rates, dict):
                continue
            for vl_name, vl in subcat_rates.items():
                if not isinstance(vl, dict):
                    continue
                assert "peak" in vl, f"commercial.{subcategory}.{vl_name} missing peak"
                assert "standard" in vl, (
                    f"commercial.{subcategory}.{vl_name} missing standard"
                )
                assert "offpeak" in vl, (
                    f"commercial.{subcategory}.{vl_name} missing offpeak"
                )
                assert vl["peak"] > vl["standard"] > vl["offpeak"]

    def test_household_tiers(self, tariff_data):
        mults = tariff_data["rate_multipliers"]
        assert "household" in mults
        hh = mults["household"]
        tier_keys = [k for k in hh if k.startswith("tier_")]
        assert len(tier_keys) >= 2
        for tk in tier_keys:
            assert hh[tk] > 0
            assert hh[tk] < 5.0


# ===================================================================
# 3b. Regime registry sanity
# ===================================================================


class TestRegimeRegistrySanity:
    VALID_STATUS = {"active", "legacy", "draft", "preview", "archived"}

    @pytest.fixture(scope="class")
    def regime_data(self, manifest):
        raw, _ = _load_data_file(manifest, "regimes")
        return raw["data"]

    def test_regimes_block_present(self, regime_data):
        assert "regimes" in regime_data
        assert isinstance(regime_data["regimes"], dict)
        assert regime_data["regimes"]

    def test_baseline_regime_present(self, regime_data):
        assert "decision_963_2026_current" in regime_data["regimes"]

    def test_regime_structure(self, regime_data):
        for regime_id, regime in regime_data["regimes"].items():
            if "alias_of" in regime:
                continue
            assert regime_id == regime_id.strip()
            assert regime["label"]
            assert regime["effective_date"]
            assert regime["status"] in self.VALID_STATUS
            assert isinstance(regime.get("source_refs", []), list)
            assert isinstance(regime.get("notes", ""), str)

    def test_non_baseline_regimes_have_sources(self, regime_data):
        for regime_id, regime in regime_data["regimes"].items():
            if "alias_of" in regime:
                continue
            if regime_id == "decision_963_2026_current":
                continue
            assert regime.get("source_refs"), (
                f"{regime_id} must include at least one source reference"
            )

    def test_tariff_override_schedule_completeness(self, regime_data):
        for regime in regime_data["regimes"].values():
            schedule = regime.get("tariff_overrides", {}).get("tou_schedule")
            if not schedule:
                continue
            for day_type, block in schedule.items():
                if not isinstance(block, dict):
                    continue
                all_hours = []
                for period in ["peak_hours", "standard_hours", "offpeak_hours"]:
                    assert period in block, f"{day_type} missing {period}"
                    all_hours.extend(int(h) for h in block[period])
                assert sorted(set(all_hours)) == list(range(24)), (
                    f"{day_type} TOU hours don't cover 0-23: got {sorted(set(all_hours))}"
                )

    def test_export_cap_bounds(self, regime_data):
        for regime in regime_data["regimes"].values():
            rooftop = regime.get("export_rule_overrides", {}).get("rooftop_solar", {})
            if "max_export_fraction" in rooftop:
                assert 0 <= rooftop["max_export_fraction"] <= 1


# ===================================================================
# 4. Tech cost bounds
# ===================================================================


class TestTechCostBounds:
    @pytest.fixture(scope="class")
    def tech_data(self, manifest):
        raw, _ = _load_data_file(manifest, "tech_costs")
        return raw["data"]

    def test_pv_costs(self, tech_data):
        assert "PV" in tech_data
        for pv_type in ["rooftop", "ground"]:
            if pv_type not in tech_data["PV"]:
                continue
            for region in ["north", "central", "south"]:
                if region not in tech_data["PV"][pv_type]:
                    continue
                cost = tech_data["PV"][pv_type][region]["installed_cost_per_kw"]
                assert 200 <= cost <= 2000, (
                    f"PV {pv_type}/{region} cost {cost} out of range"
                )
                om = tech_data["PV"][pv_type][region]["om_cost_per_kw"]
                assert om >= 0

    def test_wind_costs(self, tech_data):
        if "Wind" not in tech_data:
            pytest.skip("No Wind data")
        for wind_type in ["onshore"]:
            if wind_type not in tech_data["Wind"]:
                continue
            for region in ["north", "central", "south"]:
                if region not in tech_data["Wind"][wind_type]:
                    continue
                cost = tech_data["Wind"][wind_type][region]["installed_cost_per_kw"]
                assert 500 <= cost <= 5000, (
                    f"Wind {wind_type}/{region} cost {cost} out of range"
                )

    def test_battery_costs(self, tech_data):
        if "ElectricStorage" not in tech_data:
            pytest.skip("No ElectricStorage data")
        es = tech_data["ElectricStorage"]
        if "li_ion" in es:
            for region in ["north", "central", "south"]:
                if region not in es["li_ion"]:
                    continue
                cost_kw = es["li_ion"][region]["installed_cost_per_kw"]
                cost_kwh = es["li_ion"][region]["installed_cost_per_kwh"]
                assert cost_kw > 0
                assert 50 <= cost_kwh <= 1000, (
                    f"Battery {region} cost_kwh {cost_kwh} out of range"
                )
        if "common_defaults" in es:
            assert es["common_defaults"]["installed_cost_constant"] == 0

    def test_pv_common_defaults_zero_incentives(self, tech_data):
        if "common_defaults" not in tech_data["PV"]:
            pytest.skip("No PV common_defaults")
        cd = tech_data["PV"]["common_defaults"]
        assert cd["federal_itc_fraction"] == 0
        assert cd["macrs_option_years"] == 0
        assert cd["macrs_bonus_fraction"] == 0
        assert cd["state_ibi_fraction"] == 0
        assert cd["utility_ibi_fraction"] == 0


# ===================================================================
# 5. Emissions factor range
# ===================================================================


class TestEmissionsFactor:
    @pytest.fixture(scope="class")
    def emissions_data(self, manifest):
        raw, _ = _load_data_file(manifest, "emissions")
        return raw["data"]

    def test_lb_co2_per_kwh_range(self, emissions_data):
        assert "grid_emission_factor_lb_CO2_per_kwh" in emissions_data
        ef = emissions_data["grid_emission_factor_lb_CO2_per_kwh"]
        assert 0.0 < ef <= 3.0

    def test_tco2e_per_mwh_range(self, emissions_data):
        assert "grid_emission_factor_tCO2e_per_mwh" in emissions_data
        ef_t = emissions_data["grid_emission_factor_tCO2e_per_mwh"]
        assert 0.0 < ef_t <= 2.0

    def test_unit_cross_check(self, emissions_data):
        ef = emissions_data["grid_emission_factor_lb_CO2_per_kwh"]
        ef_t = emissions_data["grid_emission_factor_tCO2e_per_mwh"]
        expected_lb = ef_t * 2204.62 / 1000
        assert abs(ef - expected_lb) < 0.01

    def test_series_type(self, emissions_data):
        assert "series_type" in emissions_data
        if emissions_data["series_type"] == "constant":
            assert "series_length" in emissions_data
            assert emissions_data["series_length"] == 8760


# ===================================================================
# 6. Financial bounds
# ===================================================================


class TestFinancialBounds:
    @pytest.fixture(scope="class")
    def financial_data(self, manifest):
        raw, _ = _load_data_file(manifest, "financials")
        return raw["data"]

    @pytest.mark.parametrize(
        "profile_name", ["standard", "renewable_energy_preferential", "high_tech_zone"]
    )
    def test_profile_bounds(self, financial_data, profile_name):
        if profile_name not in financial_data:
            pytest.skip(f"Profile {profile_name} not in data")
        p = financial_data[profile_name]

        if "offtaker_tax_rate_fraction" in p:
            assert 0 <= p["offtaker_tax_rate_fraction"] <= 1
        if "owner_tax_rate_fraction" in p:
            assert 0 <= p["owner_tax_rate_fraction"] <= 1
        if "offtaker_discount_rate_fraction" in p:
            assert 0 < p["offtaker_discount_rate_fraction"] <= 1
        if "owner_discount_rate_fraction" in p:
            assert 0 < p["owner_discount_rate_fraction"] <= 1
        if "elec_cost_escalation_rate_fraction" in p:
            assert -0.1 <= p["elec_cost_escalation_rate_fraction"] <= 0.2
        if "om_cost_escalation_rate_fraction" in p:
            assert -0.1 <= p["om_cost_escalation_rate_fraction"] <= 0.2
        if "analysis_years" in p:
            assert 1 <= p["analysis_years"] <= 50


# ===================================================================
# 7. Export rules
# ===================================================================


class TestExportRules:
    @pytest.fixture(scope="class")
    def export_data(self, manifest):
        raw, _ = _load_data_file(manifest, "export_rules")
        return raw["data"]

    def test_rooftop_solar(self, export_data):
        assert "rooftop_solar" in export_data
        rs = export_data["rooftop_solar"]
        assert "max_export_fraction" in rs
        assert 0 < rs["max_export_fraction"] <= 1
        assert "surplus_purchase_rate_vnd_per_kwh" in rs
        assert rs["surplus_purchase_rate_vnd_per_kwh"] > 0
        assert "surplus_purchase_rate_usd_per_kwh" in rs
        assert rs["surplus_purchase_rate_usd_per_kwh"] > 0

    def test_reopt_mapping(self, export_data):
        assert "reopt_mapping" in export_data
        rm = export_data["reopt_mapping"]
        assert rm["can_net_meter"] is False
        assert rm["can_wholesale"] is True
        assert rm["can_export_beyond_nem_limit"] is False

    def test_dppa_ceiling_tariffs(self, export_data):
        if "dppa_ceiling_tariffs_vnd_per_kwh" not in export_data:
            pytest.skip("No DPPA ceiling tariffs")
        dppa = export_data["dppa_ceiling_tariffs_vnd_per_kwh"]
        for tech, regions in dppa.items():
            if tech == "notes" or not isinstance(regions, dict):
                continue
            for region, rate in regions.items():
                assert rate > 0, f"DPPA {tech}/{region} rate must be > 0"

    def test_active_export_rules_encode_decree_243(self, manifest):
        raw, filename = _load_data_file(manifest, "export_rules")
        assert raw["data"]["rooftop_solar"]["max_export_fraction"] == 0.50
        assert "243" in raw["_meta"]["source"], (
            f"active export_rules file {filename!r} does not cite Decree 243/2026 in _meta.source"
        )

