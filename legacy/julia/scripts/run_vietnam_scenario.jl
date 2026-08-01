"""
Run a Vietnam scenario end-to-end using a pre-filled template or a scenario JSON.

Usage:
    julia --project --compile=min scripts/julia/run_vietnam_scenario.jl
    julia --project --compile=min scripts/julia/run_vietnam_scenario.jl --no-solve
    julia --project --compile=min scripts/julia/run_vietnam_scenario.jl \\
        --scenario scenarios/case_studies/saigon18/2026-03-20_scenario-a_fixed-sizing_evntou.json --no-solve
    julia --sysimage=artifacts/sysimage/reopt_sysimage.dll --project \\
        scripts/julia/run_vietnam_scenario.jl --scenario <path>

Flags:
    --no-solve            Build and validate Scenario() but skip the HiGHS solver.
                          Useful for quick input validation without a full optimization run.
    --scenario <path>     Load a specific scenario JSON directly (already has Vietnam
                          defaults applied by build_saigon18_reopt_input.py). If omitted,
                          uses the default vn_commercial_rooftop_pv.json template with
                          Vietnam preprocessing applied at runtime.
    --output-dir <path>   Write results into the provided directory instead of the legacy
                          case-study routing logic.
    --sysimage <path>     Path to a PackageCompiler sysimage for faster startup.
                          Note: this flag must come BEFORE --project or be passed via
                          the Julia CLI: julia --sysimage=<path> --project ...

Environment (required for resource data fetch from NREL):
    NREL_DEVELOPER_API_KEY   your NREL developer API key
    NREL_DEVELOPER_EMAIL     your registered email

    Or put them in NREL_API.env at the repo root:
        API_KEY_NAME=<key>
        API_KEY_EMAIL=<email>
"""

using JSON
using JuMP
using HiGHS
using REopt

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", ".."))
include(joinpath(REPO_ROOT, "legacy", "julia", "src", "REoptVietnam.jl"))
using .REoptVietnam

const NO_SOLVE = "--no-solve" in ARGS

# Parse --scenario flag
const SCENARIO_IDX = findfirst(==("--scenario"), ARGS)
const SCENARIO_PATH = SCENARIO_IDX !== nothing ? ARGS[SCENARIO_IDX + 1] : nothing
const OUTPUT_DIR_IDX = findfirst(==("--output-dir"), ARGS)
const OUTPUT_DIR = OUTPUT_DIR_IDX !== nothing ? ARGS[OUTPUT_DIR_IDX + 1] : nothing
const SAIGON18_SCENARIO_MARKER = joinpath("scenarios", "case_studies", "saigon18")
const NORTH_THUAN_SCENARIO_MARKER = joinpath("scenarios", "case_studies", "north_thuan")
const NINHSIM_SCENARIO_MARKER = joinpath("scenarios", "case_studies", "ninhsim")

# ---------------------------------------------------------------------------
# Load NREL API keys from NREL_API.env if present
# ---------------------------------------------------------------------------
let env_path = joinpath(REPO_ROOT, "NREL_API.env")
    if isfile(env_path)
        for line in eachline(env_path)
            stripped = strip(line)
            (isempty(stripped) || startswith(stripped, "#")) && continue
            !occursin('=', stripped) && continue
            k, v = split(stripped, "=", limit=2)
            k = strip(k); v = strip(replace(strip(v), "\"" => ""))
            k == "API_KEY_NAME"  && (ENV["NREL_DEVELOPER_API_KEY"] = v)
            k == "API_KEY_EMAIL" && (ENV["NREL_DEVELOPER_EMAIL"]    = v)
        end
        println("API keys loaded from NREL_API.env")
    else
        @warn "NREL_API.env not found — set NREL_DEVELOPER_API_KEY and NREL_DEVELOPER_EMAIL manually."
    end
end

# ---------------------------------------------------------------------------
# Load scenario: either a direct JSON (--scenario) or the default template
# ---------------------------------------------------------------------------
if SCENARIO_PATH !== nothing
    # Direct scenario JSON — already has Vietnam defaults applied by build_saigon18_reopt_input.py
    println("\nLoading scenario: $SCENARIO_PATH")
    d = JSON.parsefile(SCENARIO_PATH)
    delete!(d, "_meta")   # remove builder metadata REopt doesn't accept
    delete!(d, "_template")
    # Expand scalar emissions factor to 8760 array (REopt requires array)
    if haskey(d, "ElectricUtility")
        ef = get(d["ElectricUtility"], "emissions_factor_series_lb_CO2_per_kwh", nothing)
        if ef isa Number
            d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"] = fill(Float64(ef), 8760)
        end
    end
else
    # Default: use the commercial rooftop template with Vietnam preprocessing
    println("\nLoading Vietnam data...")
    vn = load_vietnam_data()

    template = joinpath(REPO_ROOT, "scenarios", "templates", "vn_commercial_rooftop_pv.json")
    println("Loading template: $template")
    d = JSON.parsefile(template)

    # Strip _template metadata block — REopt does not accept it
    delete!(d, "_template")

    # Expand scalar emissions factor to 8760 array (REopt requires array)
    if haskey(d, "ElectricUtility")
        ef = get(d["ElectricUtility"], "emissions_factor_series_lb_CO2_per_kwh", nothing)
        if ef isa Number
            d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"] = fill(Float64(ef), 8760)
        end
    end

    println("Applying Vietnam defaults (customer_type=commercial, region=south)...")
    apply_vietnam_defaults!(d, vn;
        customer_type = "commercial",
        voltage_level = "medium_voltage_22kv_to_110kv",
        region        = "south",
    )
end

# ---------------------------------------------------------------------------
# Construct Scenario (validates inputs — catches schema errors before solve)
# ---------------------------------------------------------------------------
println("\nConstructing Scenario()...")
s = Scenario(d)
println("Scenario() constructed successfully.")
println("  Site:     lat=$(s.site.latitude), lon=$(s.site.longitude)")
println("  Analysis: $(s.financial.analysis_years) years, discount=$(s.financial.offtaker_discount_rate_fraction)")

if NO_SOLVE
    println("\nSkipping solver (--no-solve). Done.")
else
    # -------------------------------------------------------------------------
    # Run REopt optimization with HiGHS
    # -------------------------------------------------------------------------
    println("\nRunning REopt optimization (HiGHS)...")
    m1 = Model(HiGHS.Optimizer)
    m2 = Model(HiGHS.Optimizer)
    results = run_vietnam_reopt([m1, m2], d)

    status = "unknown"
    if results isa Dict && haskey(results, "status")
        status = results["status"]
    end

    println("\n--- Results ---")
    println("Status: $status")

    if haskey(results, "PV")
        pv = results["PV"]
        println("PV size:              $(get(pv, "size_kw", "N/A")) kW")
        println("PV year-1 energy:     $(get(pv, "year_one_energy_produced_kwh", "N/A")) kWh")
    end
    if haskey(results, "ElectricStorage")
        es = results["ElectricStorage"]
        println("Battery power:        $(get(es, "size_kw", "N/A")) kW")
        println("Battery capacity:     $(get(es, "size_kwh", "N/A")) kWh")
    end
    if haskey(results, "Financial")
        fin = results["Financial"]
        println("LCC:                  \$$(get(fin, "lcc", "N/A"))")
        println("NPV:                  \$$(get(fin, "npv", "N/A"))")
        println("Capital cost:         \$$(get(fin, "initial_capital_costs", "N/A"))")
        println("Capital after incent: \$$(get(fin, "initial_capital_costs_after_incentives", "N/A"))")
    end

    # Save results to artifacts/results/ directory
    if OUTPUT_DIR !== nothing
        out_dir = abspath(OUTPUT_DIR)
        mkpath(out_dir)
        basename_noext = SCENARIO_PATH !== nothing ? replace(basename(SCENARIO_PATH), r"\.json$" => "") : "scenario"
        out_path = joinpath(out_dir, "reopt-results.json")
    elseif SCENARIO_PATH !== nothing
        basename_noext = replace(basename(SCENARIO_PATH), r"\.json$" => "")
        normalized_scenario_path = replace(normpath(SCENARIO_PATH), '/' => Base.Filesystem.path_separator)
        if occursin(SAIGON18_SCENARIO_MARKER, normalized_scenario_path)
            out_dir = joinpath(REPO_ROOT, "artifacts", "results", "saigon18")
        elseif occursin(NORTH_THUAN_SCENARIO_MARKER, normalized_scenario_path)
            out_dir = joinpath(REPO_ROOT, "artifacts", "results", "north_thuan")
        elseif occursin(NINHSIM_SCENARIO_MARKER, normalized_scenario_path)
            out_dir = joinpath(REPO_ROOT, "artifacts", "results", "ninhsim")
        else
            out_dir = joinpath(REPO_ROOT, "artifacts", "results")
        end
        mkpath(out_dir)
        out_path = joinpath(out_dir, "$(basename_noext)_reopt-results.json")
    else
        mkpath(joinpath(REPO_ROOT, "artifacts", "results", "examples"))
        out_path = joinpath(REPO_ROOT, "artifacts", "results", "examples", "commercial-rooftop_reopt-results.json")
    end
    open(out_path, "w") do f
        JSON.print(f, results, 2)
    end
    println("\nResults saved to: $out_path")
end
