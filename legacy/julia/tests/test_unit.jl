"""
Layer 2: Unit Tests for REoptVietnam.jl

Tests the preprocessing logic in isolation — fast, no API keys or solver needed.
Each function is tested for correct behavior, edge cases, and non-destructive merging.

Run: julia --project tests/julia/test_unit.jl
"""

using Test
using JSON

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", ".."))
include(joinpath(REPO_ROOT, "legacy", "julia", "src", "REoptVietnam.jl"))
using .REoptVietnam

# Load Vietnam data once for all tests
const VN = load_vietnam_data()

# ---------------------------------------------------------------------------
# Helper: create a minimal scenario dict with common tech blocks
# ---------------------------------------------------------------------------
function make_base_dict(; pv=true, wind=false, storage=true, generator=false)
    d = Dict{String,Any}(
        "Site" => Dict{String,Any}("latitude" => 10.8, "longitude" => 106.6),
        "ElectricLoad" => Dict{String,Any}(
            "doe_reference_name" => "Hospital",
            "annual_kwh" => 1_000_000
        ),
    )
    if pv
        d["PV"] = Dict{String,Any}("max_kw" => 500)
    end
    if wind
        d["Wind"] = Dict{String,Any}("max_kw" => 200)
    end
    if storage
        d["ElectricStorage"] = Dict{String,Any}("max_kw" => 200, "max_kwh" => 800)
    end
    if generator
        d["Generator"] = Dict{String,Any}("max_kw" => 100)
    end
    return d
end

@testset "Layer 2: REoptVietnam Unit Tests" begin

    # ===================================================================
    # 1. load_vietnam_data
    # ===================================================================
    @testset "load_vietnam_data" begin
        @test VN isa VNData
        @test VN.exchange_rate == 26400.0
        @test VN.tariff isa Dict
        @test VN.tech_costs isa Dict
        @test VN.financials isa Dict
        @test VN.emissions isa Dict
        @test VN.export_rules isa Dict
        @test VN.regimes isa Dict
        @test haskey(VN.tariff, "base_avg_price_vnd_per_kwh")
        @test haskey(VN.tech_costs, "PV")
        @test haskey(VN.financials, "standard")
        @test haskey(VN.emissions, "grid_emission_factor_lb_CO2_per_kwh")
        @test haskey(VN.export_rules, "rooftop_solar")
        @test haskey(VN.regimes, "regimes")
        @test haskey(VN.regimes["regimes"], "decision_963_2026_current")
    end

    @testset "load_vietnam_data — bad manifest path" begin
        @test_throws Exception load_vietnam_data(manifest_path="nonexistent.json")
    end

    # ===================================================================
    # 2. Currency conversion
    # ===================================================================
    @testset "convert_vnd_to_usd" begin
        @test convert_vnd_to_usd(26400; exchange_rate=26400) ≈ 1.0
        @test convert_vnd_to_usd(0; exchange_rate=26400) ≈ 0.0
        @test convert_vnd_to_usd(52800; exchange_rate=26400) ≈ 2.0
        @test convert_vnd_to_usd(2204.07; exchange_rate=26400) ≈ 2204.07 / 26400 atol=1e-10
    end

    @testset "convert_usd_to_vnd" begin
        @test convert_usd_to_vnd(1.0; exchange_rate=26400) ≈ 26400.0
        @test convert_usd_to_vnd(0.0; exchange_rate=26400) ≈ 0.0
        @test convert_usd_to_vnd(0.0834875; exchange_rate=26400) ≈ 0.0834875 * 26400 atol=1e-6
    end

    @testset "Currency round-trip" begin
        original_vnd = 50_000.0
        usd = convert_vnd_to_usd(original_vnd; exchange_rate=26400)
        back_to_vnd = convert_usd_to_vnd(usd; exchange_rate=26400)
        @test back_to_vnd ≈ original_vnd atol=1e-8
    end

    @testset "Currency — invalid exchange rate" begin
        @test_throws Exception convert_vnd_to_usd(100; exchange_rate=0)
        @test_throws Exception convert_vnd_to_usd(100; exchange_rate=-1)
        @test_throws Exception convert_usd_to_vnd(100; exchange_rate=0)
    end

    # ===================================================================
    # 3. zero_us_incentives!
    # ===================================================================
    @testset "zero_us_incentives! — PV" begin
        d = make_base_dict()
        d["PV"]["federal_itc_fraction"] = 0.30  # US default
        d["PV"]["macrs_option_years"] = 5
        zero_us_incentives!(d)

        @test d["PV"]["federal_itc_fraction"] == 0
        @test d["PV"]["macrs_option_years"] == 0
        @test d["PV"]["macrs_bonus_fraction"] == 0
        @test d["PV"]["state_ibi_fraction"] == 0
        @test d["PV"]["utility_ibi_fraction"] == 0
        @test d["PV"]["production_incentive_per_kwh"] == 0
    end

    @testset "zero_us_incentives! — ElectricStorage" begin
        d = make_base_dict()
        d["ElectricStorage"]["total_itc_fraction"] = 0.30
        zero_us_incentives!(d)

        @test d["ElectricStorage"]["total_itc_fraction"] == 0
        @test d["ElectricStorage"]["macrs_option_years"] == 0
        @test d["ElectricStorage"]["total_rebate_per_kw"] == 0
    end

    @testset "zero_us_incentives! — Wind" begin
        d = make_base_dict(wind=true)
        zero_us_incentives!(d)

        @test d["Wind"]["federal_itc_fraction"] == 0
        @test d["Wind"]["macrs_option_years"] == 0
        @test d["Wind"]["production_incentive_per_kwh"] == 0
    end

    @testset "zero_us_incentives! — Generator" begin
        d = make_base_dict(generator=true)
        zero_us_incentives!(d)

        @test d["Generator"]["federal_itc_fraction"] == 0
        @test d["Generator"]["macrs_option_years"] == 0
        @test d["Generator"]["federal_rebate_per_kw"] == 0
    end

    @testset "zero_us_incentives! — PV as Vector" begin
        d = make_base_dict()
        d["PV"] = [
            Dict{String,Any}("name" => "roof_east", "max_kw" => 200, "federal_itc_fraction" => 0.30),
            Dict{String,Any}("name" => "roof_west", "max_kw" => 300, "federal_itc_fraction" => 0.26),
        ]
        zero_us_incentives!(d)

        for pv in d["PV"]
            @test pv["federal_itc_fraction"] == 0
            @test pv["macrs_option_years"] == 0
        end
    end

    @testset "zero_us_incentives! — missing tech blocks (no error)" begin
        d = Dict{String,Any}("Site" => Dict{String,Any}("latitude" => 10.0))
        @test_nowarn zero_us_incentives!(d)
    end

    # ===================================================================
    # 4. apply_vietnam_financials!
    # ===================================================================
    @testset "apply_vietnam_financials! — standard profile" begin
        d = make_base_dict()
        apply_vietnam_financials!(d, VN; financial_profile="standard")

        fin = d["Financial"]
        @test fin["offtaker_tax_rate_fraction"] == 0.20
        @test fin["owner_tax_rate_fraction"] == 0.20
        @test fin["offtaker_discount_rate_fraction"] == 0.10
        @test fin["owner_discount_rate_fraction"] == 0.08
        @test fin["elec_cost_escalation_rate_fraction"] == 0.04
        @test fin["om_cost_escalation_rate_fraction"] == 0.03
        @test fin["analysis_years"] == 25
    end

    @testset "apply_vietnam_financials! — RE preferential profile" begin
        d = make_base_dict()
        apply_vietnam_financials!(d, VN; financial_profile="renewable_energy_preferential")

        fin = d["Financial"]
        @test fin["offtaker_tax_rate_fraction"] == 0.10
        # Blended rate should be applied for owner
        @test fin["owner_tax_rate_fraction"] == 0.066
    end

    @testset "apply_vietnam_financials! — user value preserved" begin
        d = make_base_dict()
        d["Financial"] = Dict{String,Any}("offtaker_tax_rate_fraction" => 0.15)
        apply_vietnam_financials!(d, VN; financial_profile="standard")

        @test d["Financial"]["offtaker_tax_rate_fraction"] == 0.15  # user value wins
        @test d["Financial"]["owner_discount_rate_fraction"] == 0.08  # default injected
    end

    @testset "apply_vietnam_financials! — invalid profile" begin
        d = make_base_dict()
        @test_throws Exception apply_vietnam_financials!(d, VN; financial_profile="nonexistent")
    end

    # ===================================================================
    # 5. build_vietnam_tariff
    # ===================================================================
    @testset "build_vietnam_tariff — industrial, medium voltage" begin
        tariff = build_vietnam_tariff(VN, "industrial", "medium_voltage_22kv_to_110kv"; year=2025)

        @test haskey(tariff, "tou_energy_rates_per_kwh")
        rates = tariff["tou_energy_rates_per_kwh"]
        @test length(rates) == 8760
        @test all(r -> r > 0, rates)

        # Peak rate should be highest, off-peak lowest
        base_vnd = VN.tariff["base_avg_price_vnd_per_kwh"]
        mults = VN.tariff["rate_multipliers"]["industrial"]["medium_voltage_22kv_to_110kv"]
        expected_peak = base_vnd * mults["peak"] / VN.exchange_rate
        expected_offpeak = base_vnd * mults["offpeak"] / VN.exchange_rate

        @test maximum(rates) ≈ expected_peak atol=1e-8
        @test minimum(rates) ≈ expected_offpeak atol=1e-8
    end

    @testset "build_vietnam_tariff — Decision 963 removes morning peak" begin
        tariff = build_vietnam_tariff(VN, "industrial", "medium_voltage_22kv_to_110kv";
                                      regime_id="decision_963_2026_current", year=2025)
        monday_rates = tariff["tou_energy_rates_per_kwh"][1:24]
        @test monday_rates[10] ≈ monday_rates[9] atol=1e-10
        @test monday_rates[18] > monday_rates[17]
    end

    @testset "build_vietnam_tariff — commercial, low voltage" begin
        tariff = build_vietnam_tariff(VN, "commercial", "low_voltage_1kv_and_below"; year=2025)
        rates = tariff["tou_energy_rates_per_kwh"]
        @test length(rates) == 8760
        @test maximum(rates) > minimum(rates)
    end

    @testset "build_vietnam_tariff — household (flat)" begin
        tariff = build_vietnam_tariff(VN, "household", ""; year=2025)
        rates = tariff["tou_energy_rates_per_kwh"]
        @test length(rates) == 8760
        # Household is flat — all values should be identical
        @test all(r -> r ≈ rates[1], rates)
        @test rates[1] > 0
    end

    @testset "build_vietnam_tariff — Sunday vs weekday pattern" begin
        tariff = build_vietnam_tariff(VN, "industrial", "medium_voltage_22kv_to_110kv"; year=2025)
        rates = tariff["tou_energy_rates_per_kwh"]

        # 2025-01-01 is a Wednesday. Find first Sunday = Jan 5 (day index 4, 0-based)
        # Sunday hours: index 4*24+1 to 4*24+24 = 97 to 120
        sunday_rates = rates[97:120]
        # Sunday has no peak hours — max should be standard rate
        base_vnd = VN.tariff["base_avg_price_vnd_per_kwh"]
        mults = VN.tariff["rate_multipliers"]["industrial"]["medium_voltage_22kv_to_110kv"]
        expected_standard = base_vnd * mults["standard"] / VN.exchange_rate
        expected_peak = base_vnd * mults["peak"] / VN.exchange_rate

        # Sunday should NOT have peak rate
        sunday_key = haskey(VN.tariff["tou_schedule"], "sunday") ? "sunday" : "sunday_and_public_holidays"
        @test !(expected_peak in sunday_rates) || isempty(VN.tariff["tou_schedule"][sunday_key]["peak_hours"])
        # Sunday max should be standard
        @test maximum(sunday_rates) ≈ expected_standard atol=1e-8
    end

    @testset "build_vietnam_tariff — demand charges" begin
        tariff = build_vietnam_tariff(VN, "industrial", "medium_voltage_22kv_to_110kv")
        @test haskey(tariff, "monthly_demand_rates")
        @test length(tariff["monthly_demand_rates"]) == 12
        # Currently 0 for Vietnam
        @test all(r -> r == 0, tariff["monthly_demand_rates"])
    end

    @testset "build_vietnam_tariff — invalid customer type" begin
        @test_throws Exception build_vietnam_tariff(VN, "government", "medium_voltage_22kv_to_110kv")
    end

    @testset "build_vietnam_tariff — invalid voltage level" begin
        @test_throws Exception build_vietnam_tariff(VN, "industrial", "ultra_high_voltage")
    end

    # ===================================================================
    # 6. apply_vietnam_emissions!
    # ===================================================================
    @testset "apply_vietnam_emissions!" begin
        d = make_base_dict()
        apply_vietnam_emissions!(d, VN)

        @test haskey(d, "ElectricUtility")
        eu = d["ElectricUtility"]
        @test haskey(eu, "emissions_factor_series_lb_CO2_per_kwh")
        ef = eu["emissions_factor_series_lb_CO2_per_kwh"]
        @test length(ef) == 8760
        @test ef[1] ≈ 1.5013 atol=1e-4
        @test all(v -> v ≈ ef[1], ef)  # constant series
    end

    @testset "apply_vietnam_emissions! — user value preserved" begin
        d = make_base_dict()
        custom_series = fill(2.0, 8760)
        d["ElectricUtility"] = Dict{String,Any}("emissions_factor_series_lb_CO2_per_kwh" => custom_series)
        apply_vietnam_emissions!(d, VN)

        @test d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"][1] ≈ 2.0  # user value preserved
    end

    # ===================================================================
    # 7. apply_vietnam_tech_costs!
    # ===================================================================
    @testset "apply_vietnam_tech_costs! — PV rooftop south" begin
        d = make_base_dict()
        apply_vietnam_tech_costs!(d, VN; region="south", pv_type="rooftop")

        @test d["PV"]["installed_cost_per_kw"] == 600
        @test d["PV"]["om_cost_per_kw"] == 8
        @test d["PV"]["dc_ac_ratio"] == 1.2  # common default
        @test d["PV"]["losses"] == 0.14
    end

    @testset "apply_vietnam_tech_costs! — PV ground north" begin
        d = make_base_dict()
        apply_vietnam_tech_costs!(d, VN; region="north", pv_type="ground")

        @test d["PV"]["installed_cost_per_kw"] == 550
        @test d["PV"]["om_cost_per_kw"] == 9
    end

    @testset "apply_vietnam_tech_costs! — ElectricStorage south" begin
        d = make_base_dict()
        apply_vietnam_tech_costs!(d, VN; region="south")

        @test d["ElectricStorage"]["installed_cost_per_kw"] == 370
        @test d["ElectricStorage"]["installed_cost_per_kwh"] == 270
        @test d["ElectricStorage"]["installed_cost_constant"] == 0
        @test d["ElectricStorage"]["replace_cost_per_kw"] == 200
        @test d["ElectricStorage"]["replace_cost_per_kwh"] == 150
    end

    @testset "apply_vietnam_tech_costs! — Wind onshore central" begin
        d = make_base_dict(wind=true)
        apply_vietnam_tech_costs!(d, VN; region="central", wind_type="onshore")

        @test d["Wind"]["installed_cost_per_kw"] == 1300
        @test d["Wind"]["om_cost_per_kw"] == 26
    end

    @testset "apply_vietnam_tech_costs! — Generator diesel" begin
        d = make_base_dict(generator=true)
        apply_vietnam_tech_costs!(d, VN; region="south")

        @test d["Generator"]["installed_cost_per_kw"] == 500
        @test d["Generator"]["fuel_cost_per_gallon"] == 4.50
    end

    @testset "apply_vietnam_tech_costs! — user cost preserved" begin
        d = make_base_dict()
        d["PV"]["installed_cost_per_kw"] = 800  # user override
        apply_vietnam_tech_costs!(d, VN; region="south")

        @test d["PV"]["installed_cost_per_kw"] == 800  # user value wins
        @test d["PV"]["om_cost_per_kw"] == 8  # default injected
    end

    @testset "apply_vietnam_tech_costs! — invalid region" begin
        d = make_base_dict()
        @test_throws Exception apply_vietnam_tech_costs!(d, VN; region="west")
    end

    @testset "apply_vietnam_tech_costs! — PV as Vector" begin
        d = make_base_dict()
        d["PV"] = [
            Dict{String,Any}("name" => "roof_east", "max_kw" => 200),
            Dict{String,Any}("name" => "roof_west", "max_kw" => 300),
        ]
        apply_vietnam_tech_costs!(d, VN; region="south", pv_type="rooftop")

        # First PV gets regional costs
        @test d["PV"][1]["installed_cost_per_kw"] == 600
        # Both get common defaults
        for pv in d["PV"]
            @test pv["dc_ac_ratio"] == 1.2
            @test pv["federal_itc_fraction"] == 0
        end
    end

    # ===================================================================
    # 8. apply_decree57_export!
    # ===================================================================
    @testset "apply_decree57_export!" begin
        d = make_base_dict()
        apply_decree57_export!(d, VN)

        et = d["ElectricTariff"]
        @test et["wholesale_rate"] ≈ 0.0254 atol=1e-4
        @test et["export_rate_beyond_net_metering_limit"] == 0

        pv = d["PV"]
        @test pv["can_net_meter"] == false
        @test pv["can_wholesale"] == true
        @test pv["can_export_beyond_nem_limit"] == false
        @test pv["can_curtail"] == true
        @test d["_meta"]["decree57_max_export_fraction"] == 0.50
    end

    @testset "apply_decree57_export! — regime-specific export fraction" begin
        d = make_base_dict()
        apply_decree57_export!(d, VN; regime_id="decree57_rooftop_50pct_draft")

        @test d["_meta"]["decree57_max_export_fraction"] == 0.50
        @test d["_meta"]["resolved_regime_id"] == "decree57_rooftop_50pct_draft"
    end

    @testset "apply_decree57_export! — user wholesale rate preserved" begin
        d = make_base_dict()
        d["ElectricTariff"] = Dict{String,Any}("wholesale_rate" => 0.05)
        apply_decree57_export!(d, VN)

        @test d["ElectricTariff"]["wholesale_rate"] == 0.05  # user value wins
    end

    @testset "apply_decree57_export! — non-default max_export_fraction emits warning" begin
        d = make_base_dict()
        @test_logs (:warn, r"max_export_fraction=.*stored for Vietnam custom solve wrappers") apply_decree57_export!(d, VN; max_export_fraction=0.10)
        @test d["_meta"]["decree57_max_export_fraction"] == 0.10
    end

    @testset "apply_decree57_export! — default max_export_fraction emits no warning" begin
        d = make_base_dict()
        @test_nowarn apply_decree57_export!(d, VN; max_export_fraction=0.50)
    end

    @testset "apply_decree57_export! — invalid max_export_fraction errors" begin
        d = make_base_dict()
        @test_throws Exception apply_decree57_export!(d, VN; max_export_fraction=1.1)
    end

    @testset "apply_decree57_export! — explicit legacy 0.20 now warns" begin
        d = make_base_dict()
        @test_logs (:warn, r"max_export_fraction=.*stored for Vietnam custom solve wrappers") apply_decree57_export!(d, VN; max_export_fraction=0.20)
        @test d["_meta"]["decree57_max_export_fraction"] == 0.20
    end

    @testset "apply_decree57_export! — decree_57_2025_legacy regime restores 20 percent" begin
        d = make_base_dict()
        @test_nowarn apply_decree57_export!(d, VN; regime_id="decree_57_2025_legacy")
        @test d["_meta"]["decree57_max_export_fraction"] == 0.20
    end

    # ===================================================================
    # 9. apply_vietnam_defaults! — master function
    # ===================================================================
    @testset "apply_vietnam_defaults! — full pipeline" begin
        d = make_base_dict(wind=true, generator=true)
        apply_vietnam_defaults!(d, VN;
            customer_type="industrial",
            voltage_level="medium_voltage_22kv_to_110kv",
            region="south"
        )

        # Financial injected
        @test haskey(d, "Financial")
        @test d["Financial"]["offtaker_tax_rate_fraction"] == 0.20

        # Tariff injected
        @test haskey(d, "ElectricTariff")
        @test haskey(d["ElectricTariff"], "tou_energy_rates_per_kwh")
        @test length(d["ElectricTariff"]["tou_energy_rates_per_kwh"]) == 8760

        # Emissions injected
        @test haskey(d, "ElectricUtility")
        @test length(d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]) == 8760

        # Tech costs injected
        @test d["PV"]["installed_cost_per_kw"] == 600
        @test d["Wind"]["installed_cost_per_kw"] == 1350
        @test d["ElectricStorage"]["installed_cost_constant"] == 0
        @test d["Generator"]["installed_cost_per_kw"] == 500

        # Incentives zeroed
        @test d["PV"]["federal_itc_fraction"] == 0
        @test d["Wind"]["federal_itc_fraction"] == 0
        @test d["ElectricStorage"]["total_itc_fraction"] == 0
        @test d["Generator"]["federal_itc_fraction"] == 0

        # Export rules
        @test d["PV"]["can_net_meter"] == false
        @test d["ElectricTariff"]["wholesale_rate"] ≈ 0.0254 atol=1e-4
        @test d["_meta"]["decree57_max_export_fraction"] == 0.50
        @test d["_meta"]["resolved_regime_id"] == "decision_963_2026_current"
    end

    @testset "apply_vietnam_defaults! — explicit baseline matches implicit default" begin
        explicit = make_base_dict()
        implicit = make_base_dict()

        apply_vietnam_defaults!(explicit, VN; regime_id="decision_963_2026_current")
        apply_vietnam_defaults!(implicit, VN)

        @test implicit["_meta"]["resolved_regime_id"] == "decision_963_2026_current"
        @test implicit["ElectricTariff"]["tou_energy_rates_per_kwh"] == explicit["ElectricTariff"]["tou_energy_rates_per_kwh"]
        @test implicit["_meta"]["decree57_max_export_fraction"] == explicit["_meta"]["decree57_max_export_fraction"]
    end

    @testset "apply_vietnam_defaults! — two-part tariff trial injects demand rate" begin
        d = make_base_dict()
        apply_vietnam_defaults!(d, VN; regime_id="decree146_two_part_trial_2026")

        @test d["ElectricTariff"]["monthly_demand_rates"] ≈ fill(235414 / VN.exchange_rate, 12)
        @test d["_meta"]["resolved_regime_id"] == "decree146_two_part_trial_2026"
        @test d["_meta"]["bess_capacity_payment_vnd_per_kw_month"] == 0
    end

    @testset "apply_vietnam_defaults! — Decision 14 legacy changes tariff shape" begin
        baseline = make_base_dict()
        shifted = make_base_dict()

        apply_vietnam_defaults!(baseline, VN)
        apply_vietnam_defaults!(shifted, VN; regime_id="decision_14_2025_legacy")

        @test baseline["ElectricTariff"]["tou_energy_rates_per_kwh"] != shifted["ElectricTariff"]["tou_energy_rates_per_kwh"]
        @test shifted["_meta"]["resolved_regime_id"] == "decision_14_2025_legacy"
    end

    @testset "apply_vietnam_defaults! — selective disable" begin
        d = make_base_dict()
        apply_vietnam_defaults!(d, VN;
            apply_tariff=false,
            apply_emissions=false,
            apply_export_rules=false
        )

        # Financial and tech costs should still be applied
        @test haskey(d, "Financial")
        @test d["PV"]["installed_cost_per_kw"] == 600

        # Tariff, emissions, export should NOT be applied
        @test !haskey(d, "ElectricUtility")
        et = get(d, "ElectricTariff", Dict())
        @test !haskey(et, "tou_energy_rates_per_kwh")
        @test !haskey(et, "wholesale_rate")
    end

    @testset "apply_vietnam_defaults! — non-destructive (comprehensive)" begin
        d = Dict{String,Any}(
            "Site" => Dict{String,Any}("latitude" => 10.8, "longitude" => 106.6),
            "ElectricLoad" => Dict{String,Any}("doe_reference_name" => "Hospital", "annual_kwh" => 500_000),
            "PV" => Dict{String,Any}(
                "installed_cost_per_kw" => 800,
                "max_kw" => 1000,
                "can_net_meter" => true,  # user explicitly wants net metering
            ),
            "ElectricStorage" => Dict{String,Any}(
                "installed_cost_per_kwh" => 350,
                "max_kwh" => 2000,
            ),
            "Financial" => Dict{String,Any}(
                "offtaker_tax_rate_fraction" => 0.15,
            ),
            "ElectricTariff" => Dict{String,Any}(
                "wholesale_rate" => 0.05,
            ),
            "ElectricUtility" => Dict{String,Any}(
                "emissions_factor_series_lb_CO2_per_kwh" => fill(2.0, 8760),
            ),
        )

        apply_vietnam_defaults!(d, VN; region="south")

        # All user values preserved
        @test d["PV"]["installed_cost_per_kw"] == 800
        @test d["PV"]["max_kw"] == 1000
        @test d["PV"]["can_net_meter"] == true
        @test d["ElectricStorage"]["installed_cost_per_kwh"] == 350
        @test d["ElectricStorage"]["max_kwh"] == 2000
        @test d["Financial"]["offtaker_tax_rate_fraction"] == 0.15
        @test d["ElectricTariff"]["wholesale_rate"] == 0.05
        @test d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"][1] ≈ 2.0

        # Defaults still injected where user didn't specify
        @test d["PV"]["om_cost_per_kw"] == 8
        @test d["ElectricStorage"]["installed_cost_constant"] == 0
        @test d["Financial"]["owner_discount_rate_fraction"] == 0.08
    end

    @testset "resolve_vietnam_regime" begin
        resolved = resolve_vietnam_regime(VN; regime_id="decree57_rooftop_50pct_draft")
        @test resolved["regime_id"] == "decree57_rooftop_50pct_draft"
        @test resolved["export_rules"]["rooftop_solar"]["max_export_fraction"] == 0.5
        @test resolved["tariff"]["base_avg_price_vnd_per_kwh"] == VN.tariff["base_avg_price_vnd_per_kwh"]
        @test_throws Exception resolve_vietnam_regime(VN; regime_id="missing_regime")
    end

end # top-level testset

println("\n✓ Layer 2: All unit tests completed.")
