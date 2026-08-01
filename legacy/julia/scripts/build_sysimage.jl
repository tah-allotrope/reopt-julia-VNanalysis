"""
Build a PackageCompiler sysimage for REopt.jl + HiGHS + JuMP.

Usage:
    julia --project scripts/julia/build_sysimage.jl

Output:
    artifacts/sysimage/reopt_sysimage.dll  (Windows)
    artifacts/sysimage/reopt_sysimage.so   (Linux/macOS)

The sysimage precompiles REopt, JuMP, HiGHS, JSON, and ArchGDAL so that
subsequent Julia invocations skip JIT compilation (cold-start drops from
~3-8 min to <3s). Solver binaries (HiGHS JLL artifact) are loaded at runtime
and are NOT baked into the sysimage.

Set SKIP_PRECOMPILE=true in the environment to skip the representative
precompile workload (faster build, less warm coverage).
"""

using PackageCompiler

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", "..", ".."))
const SYSLIB = joinpath(REPO_ROOT, "artifacts", "sysimage")

mkpath(SYSLIB)

# Packages to compile into the sysimage.
# Keep lean — only what's needed for run_vietnam_scenario.jl.
pkgs = [
    "REopt",
    "JuMP",
    "HiGHS",
    "JSON",
    "ArchGDAL",
]

# Optional precompile execution file: runs a representative workload
# to warm-compile the solver code paths.
precompile_file = nothing
if !haskey(ENV, "SKIP_PRECOMPILE")
    precompile_file = joinpath(@__DIR__, "precompile_workload.jl")
    # Generate a minimal precompile script
    write(precompile_file, """
    using REopt, JuMP, HiGHS, JSON

    # Minimal REopt scenario to warm solver paths
    d = Dict{String,Any}(
        "Site" => Dict("latitude" => 10.8, "longitude" => 106.6),
        "ElectricLoad" => Dict(
            "doe_reference_name" => "Hospital",
            "annual_kwh" => 1_000_000,
        ),
        "ElectricTariff" => Dict(
            "urdb_label" => "Commercial",
            "tou_energy_rates_per_kwh" => [0.12],
        ),
        "Financial" => Dict(
            "analysis_years" => 25,
            "offtaker_discount_rate_fraction" => 0.068,
        ),
        "PV" => Dict("max_kw" => 1000),
        "ElectricStorage" => Dict("max_kw" => 500, "max_kwh" => 1000),
    )

    m1 = Model(HiGHS.Optimizer)
    m2 = Model(HiGHS.Optimizer)
    set_silent(m1)
    set_silent(m2)

    try
        results = REopt.run_reopt(m1, m2, d)
        println("Precompile solve status: ", get(results, "status", "unknown"))
    catch e
        @warn "Precompile solve skipped (expected for minimal scenario)" exception = e
    end
    """)
end

println("Building sysimage with packages: $(join(pkgs, ", "))")
println("Output directory: $SYSLIB")

if precompile_file !== nothing
    create_sysimage(
        pkgs;
        sysimage_path = joinpath(SYSLIB, "reopt_sysimage"),
        precompile_execution_file = precompile_file,
        filter_stdlibs = Sys.iswindows() ? false : true,
        cpu_target = "native",
    )
else
    create_sysimage(
        pkgs;
        sysimage_path = joinpath(SYSLIB, "reopt_sysimage"),
        filter_stdlibs = Sys.iswindows() ? false : true,
        cpu_target = "native",
    )
end

if precompile_file !== nothing && isfile(precompile_file)
    rm(precompile_file)
end

println("\nSysimage built successfully at: $SYSLIB")
println("Run with: julia --sysimage=$(joinpath(SYSLIB, "reopt_sysimage")) --project ...")
