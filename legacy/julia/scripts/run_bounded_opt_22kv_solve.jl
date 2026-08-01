"""Run bounded-opt REopt solve for 22kV two-part tariff branch."""

using JSON
using JuMP
using HiGHS
using REopt

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", ".."))
include(joinpath(REPO_ROOT, "legacy", "julia", "src", "REoptVietnam.jl"))
using .REoptVietnam

let env_path = joinpath(REPO_ROOT, "NREL_API.env")
    if isfile(env_path)
        for line in eachline(env_path)
            stripped = strip(line)
            (isempty(stripped) || startswith(stripped, "#")) && continue
            !occursin('=', stripped) && continue
            k, v = split(stripped, "=", limit=2)
            k = strip(k); v = strip(replace(strip(v), "\"" => ""))
            k == "API_KEY_NAME"  && (ENV["NREL_DEVELOPER_API_KEY"] = v)
            k == "API_KEY_EMAIL" && (ENV["NREL_DEVELOPER_EMAIL"] = v)
        end
        println("API keys loaded")
    end
end

scenario_path = joinpath(REPO_ROOT, "scenarios", "case_studies", "saigon18",
    "2026-04-21_saigon18_dppa-case-3_bounded-opt_22kv.json")

println("\nLoading scenario: $scenario_path")
d = JSON.parsefile(scenario_path)
delete!(d, "_meta")
delete!(d, "_template")

ef = d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"]
if ef isa Number
    d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"] = fill(Float64(ef), 8760)
elseif length(ef) == 1
    d["ElectricUtility"]["emissions_factor_series_lb_CO2_per_kwh"] = fill(Float64(ef[1]), 8760)
end

println("\nConstructing Scenario()...")
s = Scenario(d)
println("Scenario() OK. Site: lat=$(s.site.latitude), lon=$(s.site.longitude)")

println("\nRunning REopt optimization (time limit: 3600s)...")
m1 = Model(HiGHS.Optimizer)
m2 = Model(HiGHS.Optimizer)
set_time_limit_sec(m1, 3600)
set_time_limit_sec(m2, 3600)

results = run_vietnam_reopt([m1, m2], d)

status = get(results, "status", "unknown")
println("\n--- Results ---")
println("Status: $status")

if haskey(results, "PV")
    pv = results["PV"]
    println("PV size_kw:              $(get(pv, "size_kw", "N/A"))")
    println("PV year_one_energy:      $(get(pv, "year_one_energy_produced_kwh", "N/A")) kWh")
end
if haskey(results, "ElectricStorage")
    es = results["ElectricStorage"]
    println("BESS size_kw:           $(get(es, "size_kw", "N/A"))")
    println("BESS size_kwh:          $(get(es, "size_kwh", "N/A"))")
end

out_path = joinpath(REPO_ROOT, "artifacts", "results", "saigon18",
    "2026-04-21_saigon18_dppa-case-3_bounded-opt_22kv_reopt-results.json")
mkpath(dirname(out_path))
open(out_path, "w") do f
    JSON.print(f, results, 2)
end
println("\nResults saved to: $out_path")