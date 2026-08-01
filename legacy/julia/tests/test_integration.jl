"""
Layer 4: Integration / Regression Tests for REoptVietnam.jl

End-to-end tests that verify the full pipeline produces reasonable optimization results.
Requires: REopt.jl, HiGHS solver, NREL API key (for resource data).

Tests:
  1. Template smoke tests — Scenario() construction (no solve) for all 4 templates
  2. Incentive verification — after solve, capital costs == capital costs after incentives
  3. Industrial PV+Storage regression — compare key metrics against saved baseline (±5%)

Run: julia --project tests/julia/test_integration.jl
  or: julia --project tests/julia/test_integration.jl --smoke-only   (skip solver tests)
"""

using Test
using JSON
using JuMP
using HiGHS
using REopt
using DelimitedFiles

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", ".."))
include(joinpath(REPO_ROOT, "legacy", "julia", "src", "REoptVietnam.jl"))
using .REoptVietnam

const TEMPLATES_DIR = joinpath(REPO_ROOT, "scenarios", "templates")
const BASELINES_DIR = joinpath(REPO_ROOT, "tests", "baselines")
const ENV_PATH = joinpath(REPO_ROOT, "NREL_API.env")

const SMOKE_ONLY = "--smoke-only" in ARGS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function load_nrel_env(env_path::AbstractString)
    if !isfile(env_path)
        @warn "NREL_API.env not found; PV/Wind resource lookups may fail." env_path
        return false
    end
    for line in eachline(env_path)
        stripped = strip(line)
        (isempty(stripped) || startswith(stripped, "#")) && continue
        !occursin('=', stripped) && continue
        key, value = split(stripped, "=", limit=2)
        key = strip(key)
        value = strip(replace(strip(value), "\"" => ""))
        if key == "API_KEY_NAME"
            ENV["NREL_DEVELOPER_API_KEY"] = value
        elseif key == "API_KEY_EMAIL"
            ENV["NREL_DEVELOPER_EMAIL"] = value
        end
    end
    return true
end

function safe_get(dict::Dict, keys::Vector{String}, default=nothing)
    current = dict
    for key in keys
        if !(current isa Dict) || !haskey(current, key)
            return default
        end
        current = current[key]
    end
    return current
end

"""
Strip the `_template` metadata key from a scenario dict before passing to REopt.
REopt's Scenario() constructor does not recognize `_template` and will error.
"""
function strip_template_meta!(d::Dict)
    delete!(d, "_template")
    return d
end

"""
Convert scalar emissions factor to 8760 array if needed.
REopt requires an array, not a scalar, for emissions_factor_series_lb_CO2_per_kwh.
"""
function ensure_emissions_array!(d::Dict)
    if haskey(d, "ElectricUtility") && haskey(d["ElectricUtility"], "emissions_factor_series_lb_CO2_per_kwh")
        ef = d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]
        if ef isa Number
            d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"] = fill(Float64(ef), 8760)
        end
    end
    return d
end

"""
Check if a metric deviates from baseline by more than `tolerance` fraction.
Returns (passed::Bool, actual, baseline, pct_diff).
"""
function check_regression(actual, baseline, tolerance::Float64=0.05)
    if baseline == 0
        return (actual == 0, actual, baseline, 0.0)
    end
    pct_diff = abs(actual - baseline) / abs(baseline)
    return (pct_diff <= tolerance, actual, baseline, pct_diff)
end

function make_export_cap_scenario()
    return Dict{String,Any}(
        "Site" => Dict{String,Any}(
            "latitude" => 10.8,
            "longitude" => 106.6,
        ),
        "ElectricLoad" => Dict{String,Any}(
            "loads_kw" => fill(0.05, 8760),
            "year" => 2025,
        ),
        "PV" => Dict{String,Any}(
            "min_kw" => 100.0,
            "max_kw" => 100.0,
            "production_factor_series" => fill(1.0, 8760),
            "installed_cost_per_kw" => 0.0,
            "om_cost_per_kw" => 0.0,
        ),
        "Financial" => Dict{String,Any}(
            "analysis_years" => 1,
            "owner_discount_rate_fraction" => 0.0,
            "offtaker_discount_rate_fraction" => 0.0,
            "owner_tax_rate_fraction" => 0.0,
            "offtaker_tax_rate_fraction" => 0.0,
            "elec_cost_escalation_rate_fraction" => 0.0,
            "om_cost_escalation_rate_fraction" => 0.0,
        ),
        "ElectricTariff" => Dict{String,Any}(
            "tou_energy_rates_per_kwh" => fill(0.01, 8760),
            "wholesale_rate" => 0.2,
            "export_rate_beyond_net_metering_limit" => 0.0,
        ),
        "ElectricUtility" => Dict{String,Any}(
            "emissions_factor_series_lb_CO2_per_kwh" => fill(0.0, 8760),
        ),
        "_meta" => Dict{String,Any}(),
    )
end

# ---------------------------------------------------------------------------
# Load API keys
# ---------------------------------------------------------------------------
has_api_key = load_nrel_env(ENV_PATH)

# Load Vietnam data once
const VN = load_vietnam_data()

@testset "Layer 4: Integration Tests" begin

    # ===================================================================
    # 1. Template Smoke Tests — Scenario() construction, no solve
    # ===================================================================
    @testset "Template smoke tests — Scenario() construction" begin
        template_files = [
            "vn_commercial_rooftop_pv.json",
            "vn_industrial_pv_storage.json",
            "vn_hospital_resilience.json",
        ]

        for filename in template_files
            @testset "$filename" begin
                filepath = joinpath(TEMPLATES_DIR, filename)
                @test isfile(filepath)

                d = JSON.parsefile(filepath)
                strip_template_meta!(d)
                ensure_emissions_array!(d)

                # Verify key blocks exist
                @test haskey(d, "Site")
                @test haskey(d, "ElectricLoad")
                @test haskey(d, "PV")
                @test haskey(d, "Financial")

                # Attempt Scenario() construction — this validates the input dict
                # against REopt's schema without running the solver
                try
                    s = Scenario(d)
                    @test true  # construction succeeded
                    println("  ✓ $filename — Scenario() construction OK")
                catch e
                    # Print the error for debugging but don't hard-fail on
                    # non-US location warnings (AVERT/Cambium/EASIUR)
                    err_str = string(e)
                    if occursin("AVERT", err_str) || occursin("Cambium", err_str) || occursin("EASIUR", err_str)
                        @warn "Non-US location warning (expected for Vietnam)" filename exception=e
                        @test_broken false  # mark as known issue
                    else
                        @test false  # unexpected error
                        println("  ✗ $filename — Scenario() failed: $e")
                    end
                end
            end
        end
    end

    @testset "Off-grid template smoke test" begin
        filepath = joinpath(TEMPLATES_DIR, "vn_offgrid_microgrid.json")
        @test isfile(filepath)

        d = JSON.parsefile(filepath)
        strip_template_meta!(d)
        ensure_emissions_array!(d)

        @test haskey(d, "Settings")
        @test d["Settings"]["off_grid_flag"] == true
        @test haskey(d, "Generator")
        @test haskey(d, "ElectricStorage")

        try
            s = Scenario(d)
            @test true
            println("  ✓ vn_offgrid_microgrid.json — Scenario() construction OK")
        catch e
            err_str = string(e)
            if occursin("AVERT", err_str) || occursin("Cambium", err_str) || occursin("EASIUR", err_str)
                @warn "Non-US location warning (expected for Vietnam)" exception=e
                @test_broken false
            else
                @test false
                println("  ✗ vn_offgrid_microgrid.json — Scenario() failed: $e")
            end
        end
    end

    # ===================================================================
    # 2. Template values validation — verify Vietnam defaults are correct
    # ===================================================================
    @testset "Template values validation" begin
        @testset "All templates have zero US incentives" begin
            for filename in readdir(TEMPLATES_DIR)
                endswith(filename, ".json") || continue
                d = JSON.parsefile(joinpath(TEMPLATES_DIR, filename))

                @testset "$filename" begin
                    if haskey(d, "PV") && d["PV"] isa Dict
                        @test get(d["PV"], "federal_itc_fraction", 0) == 0
                        @test get(d["PV"], "macrs_option_years", 0) == 0
                        @test get(d["PV"], "macrs_bonus_fraction", 0) == 0
                    end
                    if haskey(d, "Wind") && d["Wind"] isa Dict
                        @test get(d["Wind"], "federal_itc_fraction", 0) == 0
                        @test get(d["Wind"], "macrs_option_years", 0) == 0
                    end
                    if haskey(d, "ElectricStorage") && d["ElectricStorage"] isa Dict
                        @test get(d["ElectricStorage"], "total_itc_fraction", 0) == 0
                        @test get(d["ElectricStorage"], "installed_cost_constant", 0) == 0
                    end
                    if haskey(d, "Generator") && d["Generator"] isa Dict
                        @test get(d["Generator"], "federal_itc_fraction", 0) == 0
                    end
                end
            end
        end

        @testset "All templates have Vietnam financial defaults" begin
            for filename in readdir(TEMPLATES_DIR)
                endswith(filename, ".json") || continue
                d = JSON.parsefile(joinpath(TEMPLATES_DIR, filename))

                @testset "$filename" begin
                    @test haskey(d, "Financial")
                    fin = d["Financial"]
                    @test fin["offtaker_tax_rate_fraction"] == 0.20
                    @test fin["analysis_years"] == 25
                end
            end
        end

        @testset "All templates have Vietnam emissions factor" begin
            for filename in readdir(TEMPLATES_DIR)
                endswith(filename, ".json") || continue
                d = JSON.parsefile(joinpath(TEMPLATES_DIR, filename))

                @testset "$filename" begin
                    @test haskey(d, "ElectricUtility")
                    ef = d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]
                    if ef isa Number
                        @test ef ≈ 1.5013 atol=1e-3
                    elseif ef isa Vector
                        @test length(ef) == 8760
                        @test ef[1] ≈ 1.5013 atol=1e-3
                    end
                end
            end
        end
    end

    # ===================================================================
    # 3. Solver-dependent tests (skip with --smoke-only)
    # ===================================================================
    if SMOKE_ONLY
        println("\n⚠ Skipping solver-dependent tests (--smoke-only flag)")
    else

        # ---------------------------------------------------------------
        # 3a. Incentive verification — capital costs must match
        # ---------------------------------------------------------------
        @testset "Incentive verification — zero incentives" begin
            # Use the commercial rooftop PV template (simplest, no outages)
            d = JSON.parsefile(joinpath(TEMPLATES_DIR, "vn_commercial_rooftop_pv.json"))
            strip_template_meta!(d)
            ensure_emissions_array!(d)

            # Apply Vietnam defaults to get TOU tariff series
            apply_vietnam_defaults!(d, VN;
                customer_type="commercial",
                voltage_level="medium_voltage_22kv_to_110kv",
                region="south",
                apply_zero_incentives=true,
            )

            println("\n  Running incentive verification solve (commercial rooftop PV)...")
            m1 = Model(HiGHS.Optimizer)
            m2 = Model(HiGHS.Optimizer)
            results = run_reopt([m1, m2], d)

            status = safe_get(results, ["status"], "error")
            @test status == "optimal"

            if status == "optimal"
                capital = safe_get(results, ["Financial", "initial_capital_costs"], 0.0)
                capital_after = safe_get(results, ["Financial", "initial_capital_costs_after_incentives"], 0.0)

                # With all US incentives zeroed, these must be equal
                @test capital ≈ capital_after atol=1.0
                if abs(capital - capital_after) > 1.0
                    println("  ✗ Capital mismatch: before=$capital, after=$capital_after")
                else
                    println("  ✓ Capital costs match (no incentives applied): \$$capital")
                end
            else
                println("  ✗ Solve did not reach optimal status: $status")
            end
        end

        # ---------------------------------------------------------------
        # 3b. Industrial PV+Storage template regression test
        # ---------------------------------------------------------------
        @testset "Industrial PV+Storage template regression" begin
            baseline_path = joinpath(BASELINES_DIR, "industrial_vietnam_baseline.json")

            if !isfile(baseline_path)
                @warn "Baseline file not found — running Industrial template to generate it." baseline_path
                println("  Generating baseline: $baseline_path")
            end

            d = JSON.parsefile(joinpath(TEMPLATES_DIR, "vn_industrial_pv_storage.json"))
            strip_template_meta!(d)
            ensure_emissions_array!(d)

            apply_vietnam_defaults!(d, VN;
                customer_type="industrial",
                voltage_level="medium_voltage_22kv_to_110kv",
                region="south",
            )

            println("\n  Running Industrial PV+Storage regression solve...")
            m1 = Model(HiGHS.Optimizer)
            m2 = Model(HiGHS.Optimizer)
            results = run_reopt([m1, m2], d)

            status = safe_get(results, ["status"], "error")
            @test status == "optimal"

            if status == "optimal"
                actual = Dict{String,Any}(
                    "pv_size_kw"       => safe_get(results, ["PV", "size_kw"], 0.0),
                    "storage_size_kw"  => safe_get(results, ["ElectricStorage", "size_kw"], 0.0),
                    "storage_size_kwh" => safe_get(results, ["ElectricStorage", "size_kwh"], 0.0),
                    "lcc"              => safe_get(results, ["Financial", "lcc"], 0.0),
                    "npv"              => safe_get(results, ["Financial", "npv"], 0.0),
                    "initial_capital_costs" => safe_get(results, ["Financial", "initial_capital_costs"], 0.0),
                    "initial_capital_costs_after_incentives" => safe_get(results, ["Financial", "initial_capital_costs_after_incentives"], 0.0),
                    "pv_year_one_energy_kwh" => safe_get(results, ["PV", "year_one_energy_produced_kwh"], 0.0),
                )

                println("    PV size: $(actual["pv_size_kw"]) kW")
                println("    Storage size: $(actual["storage_size_kw"]) kW / $(actual["storage_size_kwh"]) kWh")
                println("    LCC: \$$(actual["lcc"])")

                # Incentive verification: with Vietnam defaults, capital == capital_after_incentives
                @test actual["initial_capital_costs"] ≈ actual["initial_capital_costs_after_incentives"] atol=1.0

                # Sanity checks
                @test actual["lcc"] > 0
                @test actual["pv_size_kw"] >= 0

                if isfile(baseline_path)
                    baseline = JSON.parsefile(baseline_path)

                    println("  Comparing against baseline:")
                    all_passed = true
                    for (metric, act_val) in actual
                        base_val = get(baseline, metric, nothing)
                        base_val === nothing && continue

                        passed, _, _, pct = check_regression(Float64(act_val), Float64(base_val), 0.05)
                        status_str = passed ? "✓" : "✗"
                        println("    $status_str $metric: actual=$(round(act_val, digits=2)), baseline=$(round(base_val, digits=2)), diff=$(round(pct*100, digits=1))%")
                        @test passed
                        if !passed
                            all_passed = false
                        end
                    end

                    if all_passed
                        println("  ✓ All metrics within 5% of baseline")
                    end
                else
                    mkpath(BASELINES_DIR)
                    open(baseline_path, "w") do f
                        JSON.print(f, actual, 2)
                    end
                    println("  ✓ Baseline saved to: $baseline_path")
                    println("  Metrics:")
                    for (k, v) in sort(collect(actual))
                        println("    $k: $v")
                    end
                    @test true  # baseline generation is a pass
                end
            else
                println("  ✗ Industrial solve did not reach optimal status: $status")
            end
        end

        @testset "Decree 57 hard export cap" begin
            d = make_export_cap_scenario()
            apply_decree57_export!(d, VN; max_export_fraction=0.20)

            println("\n  Running Decree 57 export-cap solve...")
            results = run_vietnam_reopt([Model(HiGHS.Optimizer), Model(HiGHS.Optimizer)], d)

            status = safe_get(results, ["status"], "error")
            @test status == "optimal"

            if status == "optimal"
                pv = results["PV"]
                exported = Float64(pv["annual_energy_exported_kwh"])
                produced = Float64(pv["annual_energy_produced_kwh"])
                ratio = produced > 0 ? exported / produced : 0.0

                println("    Annual PV production: $(round(produced, digits=2)) kWh")
                println("    Annual PV export: $(round(exported, digits=2)) kWh")
                println("    Export ratio: $(round(ratio * 100, digits=2))%")

                @test produced > 0
                @test ratio <= 0.20 + 1e-6
                @test ratio >= 0.19
            end
        end

    end  # if !SMOKE_ONLY

end  # top-level testset

if SMOKE_ONLY
    println("\n✓ Layer 4: Smoke tests completed (solver tests skipped).")
else
    println("\n✓ Layer 4: All integration tests completed.")
end
