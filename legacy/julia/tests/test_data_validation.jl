"""
Layer 1: Data File Validation Tests

Pure schema and sanity checks on the Vietnam JSON data files.
Runs WITHOUT a solver — only reads and validates the data layer.

Run: julia --project tests/julia/test_data_validation.jl
"""

using Test
using JSON

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", ".."))
const DATA_DIR = joinpath(REPO_ROOT, "data", "vietnam")
const MANIFEST_PATH = joinpath(DATA_DIR, "manifest.json")

# ---------------------------------------------------------------------------
# Helper: load a data file by manifest key
# ---------------------------------------------------------------------------
function load_data_file(manifest::Dict, key::String)
    filename = manifest[key]
    filepath = joinpath(DATA_DIR, filename)
    return JSON.parsefile(filepath), filename
end

# ---------------------------------------------------------------------------
# Load manifest once
# ---------------------------------------------------------------------------
const MANIFEST = JSON.parsefile(MANIFEST_PATH)

@testset "Layer 1: Vietnam Data File Validation" begin

    # ===================================================================
    # 1. Manifest structure
    # ===================================================================
    @testset "Manifest structure" begin
        required_keys = ["tariff", "tech_costs", "financials", "emissions", "export_rules", "regimes"]
        for k in required_keys
            @test haskey(MANIFEST, k)
        end

        for k in required_keys
            filename = MANIFEST[k]
            filepath = joinpath(DATA_DIR, filename)
            @test isfile(filepath)
        end
    end

    # ===================================================================
    # 2. Schema compliance — every file has _meta + data
    # ===================================================================
    @testset "Schema compliance (_meta + data)" begin
        required_meta_fields = ["version", "effective_date", "source", "last_updated"]

        for key in ["tariff", "tech_costs", "financials", "emissions", "export_rules"]
            raw, filename = load_data_file(MANIFEST, key)

            @testset "$filename" begin
                @test haskey(raw, "_meta")
                @test haskey(raw, "data")

                if haskey(raw, "_meta")
                    meta = raw["_meta"]
                    for field in required_meta_fields
                        @test haskey(meta, field)
                    end
                end
            end
        end

        raw, filename = load_data_file(MANIFEST, "regimes")
        @testset "$filename" begin
            @test haskey(raw, "_meta")
            @test haskey(raw, "data")

            if haskey(raw, "_meta")
                meta = raw["_meta"]
                for field in required_meta_fields
                    @test haskey(meta, field)
                end
            end
        end
    end

    # ===================================================================
    # 3. Tariff sanity
    # ===================================================================
    @testset "Tariff sanity" begin
        raw, _ = load_data_file(MANIFEST, "tariff")
        data = raw["data"]

        @testset "Base price" begin
            @test haskey(data, "base_avg_price_vnd_per_kwh")
            base = data["base_avg_price_vnd_per_kwh"]
            @test base > 0
            @test base < 100_000
        end

        @testset "TOU schedule completeness" begin
            schedule = data["tou_schedule"]
            @test haskey(schedule, "weekday")
            sunday_key = haskey(schedule, "sunday") ? "sunday" : "sunday_and_public_holidays"
            @test haskey(schedule, sunday_key)

            for (day_type, block) in [("weekday", schedule["weekday"]), (sunday_key, schedule[sunday_key])]
                all_hours = Int[]
                for period in ["peak_hours", "standard_hours", "offpeak_hours"]
                    @test haskey(block, period)
                    append!(all_hours, Int.(block[period]))
                end
                sorted = sort(unique(all_hours))
                @test sorted == collect(0:23)
            end
        end

        @testset "Rate multipliers — industrial" begin
            mults = data["rate_multipliers"]
            @test haskey(mults, "industrial")

            for (vl_name, vl) in mults["industrial"]
                vl isa Dict || continue
                @testset "$vl_name" begin
                    @test haskey(vl, "peak")
                    @test haskey(vl, "standard")
                    @test haskey(vl, "offpeak")
                    @test vl["peak"] > vl["standard"] > vl["offpeak"]
                    @test vl["peak"] > 0
                    @test vl["offpeak"] > 0
                end
            end
        end

        @testset "Rate multipliers — commercial" begin
            mults = data["rate_multipliers"]
            @test haskey(mults, "commercial")

            for (subcategory, subcat_rates) in mults["commercial"]
                subcat_rates isa Dict || continue
                for (vl_name, vl) in subcat_rates
                    vl isa Dict || continue
                    @testset "$subcategory/$vl_name" begin
                        @test haskey(vl, "peak")
                        @test haskey(vl, "standard")
                        @test haskey(vl, "offpeak")
                        @test vl["peak"] > vl["standard"] > vl["offpeak"]
                    end
                end
            end
        end

        @testset "Rate multipliers — household tiers" begin
            mults = data["rate_multipliers"]
            @test haskey(mults, "household")
            hh = mults["household"]
            tier_keys = filter(k -> startswith(k, "tier_"), collect(keys(hh)))
            @test length(tier_keys) >= 2
            for tk in tier_keys
                @test hh[tk] > 0
                @test hh[tk] < 5.0
            end
        end
    end

    # ===================================================================
    # 3b. Regime registry sanity
    # ===================================================================
    @testset "Regime registry sanity" begin
        raw, _ = load_data_file(MANIFEST, "regimes")
        data = raw["data"]
        valid_status = Set(["active", "legacy", "draft", "preview", "archived"])

        @test haskey(data, "regimes")
        @test data["regimes"] isa Dict
        @test !isempty(data["regimes"])
        @test haskey(data["regimes"], "decision_963_2026_current")

        for (regime_id, regime) in data["regimes"]
            # Skip alias entries (they don't have full structure)
            haskey(regime, "alias_of") && continue
            @test regime_id == strip(regime_id)
            @test haskey(regime, "label")
            @test !isempty(regime["label"])
            @test haskey(regime, "effective_date")
            @test haskey(regime, "status")
            @test regime["status"] in valid_status
            @test get(regime, "source_refs", String[]) isa Vector
            @test get(regime, "notes", "") isa AbstractString

            if regime_id != "decision_963_2026_current"
                @test !isempty(get(regime, "source_refs", Any[]))
            end

            schedule = get(get(regime, "tariff_overrides", Dict{String,Any}()), "tou_schedule", nothing)
            if schedule !== nothing
                for (day_type, block) in schedule
                    block isa Dict || continue
                    all_hours = Int[]
                    for period in ["peak_hours", "standard_hours", "offpeak_hours"]
                        @test haskey(block, period)
                        append!(all_hours, Int.(block[period]))
                    end
                    @test sort(unique(all_hours)) == collect(0:23)
                end
            end

            rooftop = get(get(regime, "export_rule_overrides", Dict{String,Any}()), "rooftop_solar", Dict{String,Any}())
            if haskey(rooftop, "max_export_fraction")
                @test 0 <= rooftop["max_export_fraction"] <= 1
            end
        end
    end

    # ===================================================================
    # 4. Tech cost bounds
    # ===================================================================
    @testset "Tech cost bounds" begin
        raw, _ = load_data_file(MANIFEST, "tech_costs")
        data = raw["data"]

        @testset "PV costs" begin
            @test haskey(data, "PV")
            for pv_type in ["rooftop", "ground"]
                if haskey(data["PV"], pv_type)
                    for region in ["north", "central", "south"]
                        if haskey(data["PV"][pv_type], region)
                            cost = data["PV"][pv_type][region]["installed_cost_per_kw"]
                            @test 200 <= cost <= 2000
                            om = data["PV"][pv_type][region]["om_cost_per_kw"]
                            @test om >= 0
                        end
                    end
                end
            end
        end

        @testset "Wind costs" begin
            if haskey(data, "Wind")
                for wind_type in ["onshore"]
                    if haskey(data["Wind"], wind_type)
                        for region in ["north", "central", "south"]
                            if haskey(data["Wind"][wind_type], region)
                                cost = data["Wind"][wind_type][region]["installed_cost_per_kw"]
                                @test 500 <= cost <= 5000
                            end
                        end
                    end
                end
            end
        end

        @testset "Battery costs" begin
            if haskey(data, "ElectricStorage")
                es = data["ElectricStorage"]
                if haskey(es, "li_ion")
                    for region in ["north", "central", "south"]
                        if haskey(es["li_ion"], region)
                            cost_kw = es["li_ion"][region]["installed_cost_per_kw"]
                            cost_kwh = es["li_ion"][region]["installed_cost_per_kwh"]
                            @test cost_kw > 0
                            @test 50 <= cost_kwh <= 1000
                        end
                    end
                end
                if haskey(es, "common_defaults")
                    @test es["common_defaults"]["installed_cost_constant"] == 0
                end
            end
        end

        @testset "PV common defaults — zero incentives" begin
            if haskey(data["PV"], "common_defaults")
                cd = data["PV"]["common_defaults"]
                @test cd["federal_itc_fraction"] == 0
                @test cd["macrs_option_years"] == 0
                @test cd["macrs_bonus_fraction"] == 0
                @test cd["state_ibi_fraction"] == 0
                @test cd["utility_ibi_fraction"] == 0
            end
        end
    end

    # ===================================================================
    # 5. Emissions factor range
    # ===================================================================
    @testset "Emissions factor" begin
        raw, _ = load_data_file(MANIFEST, "emissions")
        data = raw["data"]

        @test haskey(data, "grid_emission_factor_lb_CO2_per_kwh")
        ef = data["grid_emission_factor_lb_CO2_per_kwh"]
        @test 0.0 < ef <= 3.0

        @test haskey(data, "grid_emission_factor_tCO2e_per_mwh")
        ef_t = data["grid_emission_factor_tCO2e_per_mwh"]
        @test 0.0 < ef_t <= 2.0

        # Cross-check: lb/kWh ≈ tCO2e/MWh × 2204.62 / 1000
        expected_lb = ef_t * 2204.62 / 1000
        @test abs(ef - expected_lb) < 0.01

        @test haskey(data, "series_type")
        if data["series_type"] == "constant"
            @test haskey(data, "series_length")
            @test data["series_length"] == 8760
        end
    end

    # ===================================================================
    # 6. Financial bounds
    # ===================================================================
    @testset "Financial bounds" begin
        raw, _ = load_data_file(MANIFEST, "financials")
        data = raw["data"]

        for profile_name in ["standard", "renewable_energy_preferential", "high_tech_zone"]
            if haskey(data, profile_name)
                @testset "$profile_name" begin
                    p = data[profile_name]

                    if haskey(p, "offtaker_tax_rate_fraction")
                        @test 0 <= p["offtaker_tax_rate_fraction"] <= 1
                    end
                    if haskey(p, "owner_tax_rate_fraction")
                        @test 0 <= p["owner_tax_rate_fraction"] <= 1
                    end
                    if haskey(p, "offtaker_discount_rate_fraction")
                        @test 0 < p["offtaker_discount_rate_fraction"] <= 1
                    end
                    if haskey(p, "owner_discount_rate_fraction")
                        @test 0 < p["owner_discount_rate_fraction"] <= 1
                    end
                    if haskey(p, "elec_cost_escalation_rate_fraction")
                        @test -0.1 <= p["elec_cost_escalation_rate_fraction"] <= 0.2
                    end
                    if haskey(p, "om_cost_escalation_rate_fraction")
                        @test -0.1 <= p["om_cost_escalation_rate_fraction"] <= 0.2
                    end
                    if haskey(p, "analysis_years")
                        @test 1 <= p["analysis_years"] <= 50
                    end
                end
            end
        end
    end

    # ===================================================================
    # 7. Export rules
    # ===================================================================
    @testset "Export rules" begin
        raw, _ = load_data_file(MANIFEST, "export_rules")
        data = raw["data"]

        @testset "Rooftop solar" begin
            @test haskey(data, "rooftop_solar")
            rs = data["rooftop_solar"]
            @test haskey(rs, "max_export_fraction")
            @test 0 < rs["max_export_fraction"] <= 1
            @test haskey(rs, "surplus_purchase_rate_vnd_per_kwh")
            @test rs["surplus_purchase_rate_vnd_per_kwh"] > 0
            @test haskey(rs, "surplus_purchase_rate_usd_per_kwh")
            @test rs["surplus_purchase_rate_usd_per_kwh"] > 0
        end

        @testset "REopt mapping" begin
            @test haskey(data, "reopt_mapping")
            rm = data["reopt_mapping"]
            @test rm["can_net_meter"] == false
            @test rm["can_wholesale"] == true
            @test rm["can_export_beyond_nem_limit"] == false
        end

        @testset "DPPA ceiling tariffs" begin
            if haskey(data, "dppa_ceiling_tariffs_vnd_per_kwh")
                dppa = data["dppa_ceiling_tariffs_vnd_per_kwh"]
                for (tech, regions) in dppa
                    tech == "notes" && continue
                    regions isa Dict || continue
                    for (region, rate) in regions
                        @test rate > 0
                    end
                end
            end
        end

        @testset "Active export rules encode Decree 243" begin
            @test data["rooftop_solar"]["max_export_fraction"] == 0.50
            @test occursin("243", raw["_meta"]["source"])
        end
    end

end # top-level testset

println("\n✓ Layer 1: All data validation tests completed.")
