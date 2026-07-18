"""
    REoptVietnam

Julia module for preprocessing REopt input dicts with Vietnam-specific assumptions.
All Vietnam-specific values are loaded at runtime from versioned JSON files in `data/vietnam/`,
driven by `manifest.json`. This module contains logic only — no hardcoded policy values.

# Usage
```julia
using REopt, JuMP, HiGHS, JSON
include("src/julia/REoptVietnam.jl")
using .REoptVietnam

vn = load_vietnam_data()
d = JSON.parsefile("my_project.json")
apply_vietnam_defaults!(d, vn; customer_type="industrial", voltage_level="medium_voltage_22kv_to_110kv", region="south")
results = run_reopt([Model(HiGHS.Optimizer), Model(HiGHS.Optimizer)], d)
```
"""
module REoptVietnam

using JSON
using Dates
using REopt
using JuMP

const MOI = JuMP.MOI

export VNData,
       load_vietnam_data,
       resolve_vietnam_regime,
       apply_vietnam_defaults!,
       zero_us_incentives!,
       apply_vietnam_financials!,
       build_vietnam_tariff,
       apply_vietnam_emissions!,
       apply_vietnam_tech_costs!,
       apply_decree57_export!,
       add_decree57_export_cap_constraint!,
       run_vietnam_reopt,
       convert_vnd_to_usd,
       convert_usd_to_vnd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

const REPO_ROOT = abspath(joinpath(@__DIR__, "..", ".."))
const DEFAULT_DATA_DIR = joinpath(REPO_ROOT, "data", "vietnam")
const DEFAULT_MANIFEST = joinpath(DEFAULT_DATA_DIR, "manifest.json")
const DEFAULT_EXCHANGE_RATE = 26_400.0  # VND per USD fallback

const VALID_CUSTOMER_TYPES = ("industrial", "commercial")
const VALID_REGIONS = ("north", "central", "south")

const HOURS_PER_YEAR = 8760
const DECREE57_META_KEY = "decree57_max_export_fraction"
const DEFAULT_REGIME_ID = "decision_963_2026_current"
const DECREE57_CONSTRAINT_NAME = :Decree57AnnualExportCapCon

# US incentive fields to zero out, grouped by tech
const PV_WIND_INCENTIVE_FIELDS = [
    "macrs_option_years", "macrs_bonus_fraction",
    "federal_itc_fraction", "federal_rebate_per_kw",
    "state_ibi_fraction", "state_ibi_max", "state_rebate_per_kw",
    "utility_ibi_fraction", "utility_ibi_max", "utility_rebate_per_kw",
    "production_incentive_per_kwh", "production_incentive_max_benefit",
    "production_incentive_years"
]

const STORAGE_INCENTIVE_FIELDS = [
    "macrs_option_years", "macrs_bonus_fraction",
    "total_itc_fraction", "total_rebate_per_kw"
]

const GENERATOR_INCENTIVE_FIELDS = [
    "macrs_option_years", "macrs_bonus_fraction",
    "federal_itc_fraction", "federal_rebate_per_kw"
]

# ---------------------------------------------------------------------------
# VNData struct — holds all loaded Vietnam data
# ---------------------------------------------------------------------------

"""
    VNData

Immutable struct holding all Vietnam assumption data loaded from the manifest-driven JSON files.
Created once via `load_vietnam_data()` and passed to all preprocessing functions.
"""
struct VNData
    tariff::Dict{String,Any}
    tech_costs::Dict{String,Any}
    financials::Dict{String,Any}
    emissions::Dict{String,Any}
    export_rules::Dict{String,Any}
    regimes::Dict{String,Any}
    exchange_rate::Float64
    data_dir::String
end

# ---------------------------------------------------------------------------
# load_vietnam_data — reads manifest, loads all active data files
# ---------------------------------------------------------------------------

"""
    load_vietnam_data(; manifest_path=DEFAULT_MANIFEST) -> VNData

Read `manifest.json`, load all active versioned data files, and return a `VNData` struct.
Call once at startup; the returned struct is immutable and can be reused across scenarios.
"""
function load_vietnam_data(; manifest_path::String=DEFAULT_MANIFEST)
    data_dir = dirname(manifest_path)
    manifest = JSON.parsefile(manifest_path)

    required_keys = ("tariff", "tech_costs", "financials", "emissions", "export_rules", "regimes")
    for k in required_keys
        haskey(manifest, k) || error("manifest.json missing required key: \"$k\"")
    end

    function _load(key::String)
        filename = manifest[key]
        filepath = joinpath(data_dir, filename)
        isfile(filepath) || error("Data file not found: $filepath (referenced by manifest key \"$key\")")
        raw = JSON.parsefile(filepath)
        haskey(raw, "data") || error("Data file $filename missing \"data\" block")
        return raw
    end

    tariff_raw       = _load("tariff")
    tech_costs_raw   = _load("tech_costs")
    financials_raw   = _load("financials")
    emissions_raw    = _load("emissions")
    export_rules_raw = _load("export_rules")
    regimes_raw      = _load("regimes")

    # Extract exchange rate from tariff _meta (VND-denominated file), with fallback
    exchange_rate = get(get(tariff_raw, "_meta", Dict()), "exchange_rate_vnd_per_usd", DEFAULT_EXCHANGE_RATE)

    return VNData(
        tariff_raw["data"],
        tech_costs_raw["data"],
        financials_raw["data"],
        emissions_raw["data"],
        export_rules_raw["data"],
        merge(regimes_raw["data"], Dict("_meta" => get(regimes_raw, "_meta", Dict{String,Any}()))),
        Float64(exchange_rate),
        data_dir
    )
end

# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------

"""
    convert_vnd_to_usd(value; exchange_rate=DEFAULT_EXCHANGE_RATE) -> Float64

Convert a value from VND to USD using the given exchange rate (VND per USD).
"""
function convert_vnd_to_usd(value::Real; exchange_rate::Real=DEFAULT_EXCHANGE_RATE)
    exchange_rate > 0 || error("exchange_rate must be positive, got $exchange_rate")
    return Float64(value) / Float64(exchange_rate)
end

"""
    convert_usd_to_vnd(value; exchange_rate=DEFAULT_EXCHANGE_RATE) -> Float64

Convert a value from USD to VND using the given exchange rate (VND per USD).
"""
function convert_usd_to_vnd(value::Real; exchange_rate::Real=DEFAULT_EXCHANGE_RATE)
    exchange_rate > 0 || error("exchange_rate must be positive, got $exchange_rate")
    return Float64(value) * Float64(exchange_rate)
end

# ---------------------------------------------------------------------------
# Helper: non-destructive set (user values always win)
# ---------------------------------------------------------------------------

"""
    _set_default!(d::Dict, key::String, value)

Set `d[key] = value` only if `key` is not already present in `d`. User-provided values are preserved.
"""
function _set_default!(d::Dict, key::String, value)
    if !haskey(d, key)
        d[key] = value
    end
    return d
end

"""
    _ensure_block!(d::Dict, key::String) -> Dict

Ensure `d[key]` exists as a Dict; create it if missing. Returns the sub-dict.
"""
function _ensure_block!(d::Dict, key::String)
    if !haskey(d, key)
        d[key] = Dict{String,Any}()
    end
    return d[key]
end

function _deep_merge_dicts(base::Dict, overrides::Dict)
    merged = deepcopy(base)
    for (key, value) in overrides
        if haskey(merged, key) && merged[key] isa Dict && value isa Dict
            merged[key] = _deep_merge_dicts(merged[key], value)
        else
            merged[key] = deepcopy(value)
        end
    end
    return merged
end

function resolve_vietnam_regime(vn::VNData; regime_id::String=DEFAULT_REGIME_ID)
    regimes = get(vn.regimes, "regimes", Dict{String,Any}())
    haskey(regimes, regime_id) || error("Unknown regime_id \"$regime_id\". Available: $(join(sort(collect(keys(regimes))), ", "))")

    entry = regimes[regime_id]

    # Follow alias_of redirects (e.g. decision_14_2025_current -> decision_14_2025_legacy)
    if haskey(entry, "alias_of")
        target_id = entry["alias_of"]
        haskey(regimes, target_id) || error("Alias target \"$target_id\" not found in regime registry.")
        bundle = deepcopy(regimes[target_id])
    else
        bundle = deepcopy(entry)
    end

    tariff_overrides = get(bundle, "tariff_overrides", Dict{String,Any}())
    export_overrides = get(bundle, "export_rule_overrides", Dict{String,Any}())
    postprocess_overrides = get(bundle, "postprocess_overrides", Dict{String,Any}())

    resolved_tariff = _deep_merge_dicts(vn.tariff, tariff_overrides)
    resolved_export_rules = _deep_merge_dicts(vn.export_rules, export_overrides)

    return Dict{String,Any}(
        "regime_id" => regime_id,
        "registry_version" => get(get(vn.regimes, "_meta", Dict{String,Any}()), "version", nothing),
        "label" => get(bundle, "label", regime_id),
        "effective_date" => get(bundle, "effective_date", nothing),
        "status" => get(bundle, "status", nothing),
        "source_refs" => deepcopy(get(bundle, "source_refs", Any[])),
        "notes" => get(bundle, "notes", nothing),
        "tariff" => resolved_tariff,
        "export_rules" => resolved_export_rules,
        "postprocess_overrides" => deepcopy(postprocess_overrides),
    )
end

function _scenario_input_dict(d::Dict)
    clean = deepcopy(d)
    for key in ("_meta", "_template")
        if haskey(clean, key)
            delete!(clean, key)
        end
    end
    return clean
end

function _decree57_export_fraction(d::Dict)
    meta = get(d, "_meta", nothing)
    if meta isa Dict && haskey(meta, DECREE57_META_KEY)
        return Float64(meta[DECREE57_META_KEY])
    end
    return nothing
end

function _validate_export_fraction(max_export_fraction::Real)
    0 <= max_export_fraction <= 1 || error("max_export_fraction must be between 0 and 1, got $max_export_fraction")
    return Float64(max_export_fraction)
end

function _finalize_reopt_results(m::JuMP.AbstractModel, p; organize_pvs::Bool=true)
    opt_time = 0.0
    start_time = time()
    optimize!(m)
    opt_time = round(time() - start_time, digits=3)

    if termination_status(m) == MOI.TIME_LIMIT
        status = "timed-out"
    elseif termination_status(m) == MOI.OPTIMAL
        status = "optimal"
    else
        @warn "REopt solved with $(termination_status(m)); returning the model instead of results."
        return m
    end

    results = REopt.reopt_results(m, p)
    results["status"] = status
    results["solver_seconds"] = opt_time
    results["Messages"] = REopt.logger_to_dict()

    if organize_pvs && !isempty(p.techs.pv)
        REopt.organize_multiple_pv_results(p, results)
    end

    return results
end

function _run_reopt_with_optional_constraint(m::JuMP.AbstractModel, p;
                                             organize_pvs::Bool=true,
                                             max_export_fraction::Union{Nothing,Float64}=nothing)
    REopt.build_reopt!(m, p)
    if max_export_fraction !== nothing
        add_decree57_export_cap_constraint!(m, p; max_export_fraction=max_export_fraction)
    end
    return _finalize_reopt_results(m, p; organize_pvs=organize_pvs)
end

# ---------------------------------------------------------------------------
# zero_us_incentives!(d)
# ---------------------------------------------------------------------------

"""
    zero_us_incentives!(d::Dict)

Zero out all US-specific incentive fields (ITC, MACRS, rebates, IBI, production incentives)
on every tech block present in the dict. This prevents REopt's US defaults from inflating
Vietnam project economics.
"""
function zero_us_incentives!(d::Dict)
    # PV — may appear as "PV" (single) or in a list
    if haskey(d, "PV")
        pv = d["PV"]
        if pv isa Dict
            _zero_fields!(pv, PV_WIND_INCENTIVE_FIELDS)
        elseif pv isa Vector
            for p in pv
                p isa Dict && _zero_fields!(p, PV_WIND_INCENTIVE_FIELDS)
            end
        end
    end

    # Wind
    if haskey(d, "Wind")
        _zero_fields!(d["Wind"], PV_WIND_INCENTIVE_FIELDS)
    end

    # ElectricStorage
    if haskey(d, "ElectricStorage")
        _zero_fields!(d["ElectricStorage"], STORAGE_INCENTIVE_FIELDS)
    end

    # Generator
    if haskey(d, "Generator")
        _zero_fields!(d["Generator"], GENERATOR_INCENTIVE_FIELDS)
    end

    return d
end

function _zero_fields!(block::Dict, fields::Vector{String})
    for f in fields
        block[f] = 0
    end
end

# ---------------------------------------------------------------------------
# apply_vietnam_financials!(d, vn)
# ---------------------------------------------------------------------------

"""
    apply_vietnam_financials!(d::Dict, vn::VNData;
                              financial_profile::String="standard",
                              kwargs...)

Inject Vietnam financial defaults into the `Financial` block of `d`.
Uses the specified `financial_profile` from the financials data file
("standard", "renewable_energy_preferential", or "high_tech_zone").

Keyword arguments matching Financial field names (e.g., `offtaker_tax_rate_fraction=0.15`)
override the data file values. User values already in `d["Financial"]` are never overwritten.
"""
function apply_vietnam_financials!(d::Dict, vn::VNData;
                                   financial_profile::String="standard",
                                   kwargs...)
    haskey(vn.financials, financial_profile) ||
        error("Unknown financial_profile \"$financial_profile\". Available: $(join(filter(k -> k != "reference_rates", collect(keys(vn.financials))), ", "))")

    profile = vn.financials[financial_profile]
    fin = _ensure_block!(d, "Financial")

    # Track which keys the user already set (before we inject anything)
    user_keys = Set(keys(fin))

    # Fields to inject from the profile
    fin_fields = [
        "offtaker_tax_rate_fraction",
        "offtaker_discount_rate_fraction",
        "owner_tax_rate_fraction",
        "owner_discount_rate_fraction",
        "elec_cost_escalation_rate_fraction",
        "om_cost_escalation_rate_fraction",
        "analysis_years"
    ]

    for field in fin_fields
        if haskey(profile, field)
            # Keyword overrides take priority over data file
            kw_sym = Symbol(field)
            if haskey(kwargs, kw_sym)
                _set_default!(fin, field, kwargs[kw_sym])
            else
                _set_default!(fin, field, profile[field])
            end
        end
    end

    # If using RE preferential profile with blended tax rate, apply it.
    # Overwrite the profile's raw rate with the blended rate — but only if
    # the user didn't explicitly set owner_tax_rate_fraction themselves.
    if financial_profile == "renewable_energy_preferential" && haskey(profile, "tax_holiday")
        blended = get(profile["tax_holiday"], "effective_blended_rate_25yr", nothing)
        if blended !== nothing && !("owner_tax_rate_fraction" in user_keys)
            fin["owner_tax_rate_fraction"] = blended
        end
    end

    return d
end

# ---------------------------------------------------------------------------
# build_vietnam_tariff
# ---------------------------------------------------------------------------

"""
    build_vietnam_tariff(vn::VNData, customer_type::String, voltage_level::String;
                         exchange_rate::Real=vn.exchange_rate,
                         year::Int=Dates.year(Dates.today())) -> Dict

Generate an 8760-hour TOU energy rate array from the tariff data file and return a Dict
suitable for merging into `d["ElectricTariff"]`.

Returns:
```julia
Dict(
    "urdb_label" => "",
    "blended_annual_energy_rate" => 0,
    "tou_energy_rates_per_kwh" => Float64[...],  # 8760 USD/kWh
    "monthly_demand_rates" => zeros(12),
)
```

Only `"industrial"` and `"commercial"` customer types support TOU. Household uses tiered
block pricing which cannot be represented as an 8760 series — use a flat average instead.
"""
function build_vietnam_tariff(vn::VNData, customer_type::String, voltage_level::String;
                              regime_id::String=DEFAULT_REGIME_ID,
                              exchange_rate::Real=vn.exchange_rate,
                              year::Int=Dates.year(Dates.today()))
    tariff = resolve_vietnam_regime(vn; regime_id=regime_id)["tariff"]
    base_vnd = tariff["base_avg_price_vnd_per_kwh"]
    schedule = tariff["tou_schedule"]
    multipliers = tariff["rate_multipliers"]

    if customer_type == "household"
        # Household: flat average (tier 2 multiplier as representative)
        avg_mult = get(multipliers["household"], "tier_2_101_to_200kwh", 1.0)
        rate_usd = convert_vnd_to_usd(base_vnd * avg_mult; exchange_rate=exchange_rate)
        rates = fill(rate_usd, HOURS_PER_YEAR)
    else
        customer_type in VALID_CUSTOMER_TYPES ||
            error("Unknown customer_type \"$customer_type\". Valid: $(join(VALID_CUSTOMER_TYPES, ", ")), household")

        haskey(multipliers, customer_type) ||
            error("No rate multipliers for customer_type \"$customer_type\"")
        cust_mults = multipliers[customer_type]

        vl = _resolve_tariff_multiplier_block(customer_type, cust_mults, voltage_level)

        peak_rate_usd     = convert_vnd_to_usd(base_vnd * vl["peak"];     exchange_rate=exchange_rate)
        standard_rate_usd = convert_vnd_to_usd(base_vnd * vl["standard"]; exchange_rate=exchange_rate)
        offpeak_rate_usd  = convert_vnd_to_usd(base_vnd * vl["offpeak"];  exchange_rate=exchange_rate)

        # Build hour-of-day → rate lookup for weekday and Sunday/holiday
        weekday_rates = _build_hourly_rates(schedule["weekday"], peak_rate_usd, standard_rate_usd, offpeak_rate_usd)
        sunday_key = haskey(schedule, "sunday") ? "sunday" : "sunday_and_public_holidays"
        sunday_rates  = _build_hourly_rates(schedule[sunday_key],  peak_rate_usd, standard_rate_usd, offpeak_rate_usd)

        rates = _build_8760_rates(weekday_rates, sunday_rates, year)
    end

    demand_vnd = get(get(tariff, "demand_charge", Dict()), "monthly_demand_rate_vnd_per_kw", 0)
    demand_usd = convert_vnd_to_usd(demand_vnd; exchange_rate=exchange_rate)

    return Dict{String,Any}(
        "urdb_label" => "",
        "blended_annual_energy_rate" => 0,
        "tou_energy_rates_per_kwh" => rates,
        "monthly_demand_rates" => fill(demand_usd, 12),
    )
end

"""
Build a 24-element vector mapping hour index (0-23) to the appropriate rate.
"""
function _build_hourly_rates(schedule_block::Dict, peak::Float64, standard::Float64, offpeak::Float64)
    rates = fill(standard, 24)  # default to standard
    for h in get(schedule_block, "peak_hours", [])
        rates[Int(h) + 1] = peak
    end
    for h in get(schedule_block, "offpeak_hours", [])
        rates[Int(h) + 1] = offpeak
    end
    for h in get(schedule_block, "standard_hours", [])
        rates[Int(h) + 1] = standard
    end
    return rates
end

function _resolve_commercial_voltage(vl::String)
    if vl in ("medium_voltage_22kv_to_110kv", "medium_voltage_above_1kv_to_35kv", "medium_voltage_and_above_1kv")
        return "medium_voltage_and_above_1kv"
    elseif vl in ("low_voltage_below_22kv", "low_voltage_1kv_and_below", "low_voltage")
        return "low_voltage_1kv_and_below"
    end
    return vl
end

function _resolve_industrial_voltage(vl::String)
    if vl == "low_voltage_below_22kv"
        return "low_voltage_1kv_and_below"
    elseif vl == "medium_voltage_above_1kv_to_35kv"
        return "medium_voltage_22kv_to_110kv"
    end
    return vl
end

function _resolve_tariff_multiplier_block(customer_type::String, customer_mults::Dict, voltage_level::String)
    if customer_type != "commercial"
        normalized_vl = customer_type == "industrial" ? _resolve_industrial_voltage(voltage_level) : voltage_level
        haskey(customer_mults, normalized_vl) ||
            error("Unknown voltage_level \"$voltage_level\" for $customer_type. Available: $(join(keys(customer_mults), ", "))")
        return customer_mults[normalized_vl]
    end

    if haskey(customer_mults, voltage_level)
        return customer_mults[voltage_level]
    end

    normalized_vl = _resolve_commercial_voltage(voltage_level)
    subcategories = filter(k -> customer_mults[k] isa Dict && haskey(customer_mults[k], normalized_vl), collect(keys(customer_mults)))
    isempty(subcategories) && error("Unknown voltage_level \"$voltage_level\" for commercial. Available subcategories: $(join(filter(k -> customer_mults[k] isa Dict, collect(keys(customer_mults))), ", "))")

    preferred = "other_commercial"
    selected = preferred in subcategories ? preferred : first(subcategories)
    return customer_mults[selected][normalized_vl]
end

"""
Build 8760-length rate array from weekday/Sunday hourly rates for a given year.
Weekday schedule applies Mon-Sat; Sunday schedule applies Sun.
"""
function _build_8760_rates(weekday_rates::Vector{Float64}, sunday_rates::Vector{Float64}, year::Int)
    rates = Vector{Float64}(undef, HOURS_PER_YEAR)
    # Jan 1 of the given year
    start_date = Date(year, 1, 1)
    idx = 1
    for day_offset in 0:364
        d = start_date + Day(day_offset)
        dow = dayofweek(d)  # 1=Monday ... 7=Sunday
        hourly = (dow == 7) ? sunday_rates : weekday_rates
        for h in 1:24
            rates[idx] = hourly[h]
            idx += 1
        end
    end
    # Handle leap year: if year has 366 days, we only fill 8760 (REopt standard)
    # If year has 365 days, idx should be exactly 8761
    return rates
end

# ---------------------------------------------------------------------------
# apply_vietnam_emissions!(d, vn)
# ---------------------------------------------------------------------------

"""
    apply_vietnam_emissions!(d::Dict, vn::VNData)

Set `ElectricUtility.emissions_factor_series_lb_CO2_per_kwh` from the emissions data file.
This overrides REopt's US-centric AVERT/Cambium lookups which fail for non-US locations.
"""
function apply_vietnam_emissions!(d::Dict, vn::VNData)
    eu = _ensure_block!(d, "ElectricUtility")
    ef = vn.emissions["grid_emission_factor_lb_CO2_per_kwh"]
    series_type = get(vn.emissions, "series_type", "constant")

    if series_type == "constant"
        _set_default!(eu, "emissions_factor_series_lb_CO2_per_kwh", fill(Float64(ef), HOURS_PER_YEAR))
    else
        # Future: support hourly series from data file
        _set_default!(eu, "emissions_factor_series_lb_CO2_per_kwh", fill(Float64(ef), HOURS_PER_YEAR))
    end

    return d
end

# ---------------------------------------------------------------------------
# apply_vietnam_tech_costs!(d, vn; region)
# ---------------------------------------------------------------------------

"""
    apply_vietnam_tech_costs!(d::Dict, vn::VNData;
                              region::String="south",
                              pv_type::String="rooftop",
                              wind_type::String="onshore",
                              exchange_rate::Real=vn.exchange_rate,
                              currency::String="USD")

Inject PV, Wind, Battery, and Generator costs from the tech costs data file.
Regional costs are selected by `region` ("north", "central", "south").
Common defaults (zero incentives, DC/AC ratio, etc.) are also applied.

If `currency="VND"`, cost values in the data file are assumed VND and converted to USD.
The data file is natively in USD, so this is only needed if you override with VND values.
"""
function apply_vietnam_tech_costs!(d::Dict, vn::VNData;
                                   region::String="south",
                                   pv_type::String="rooftop",
                                   wind_type::String="onshore",
                                   exchange_rate::Real=vn.exchange_rate,
                                   currency::String="USD")
    region in VALID_REGIONS ||
        error("Unknown region \"$region\". Valid: $(join(VALID_REGIONS, ", "))")

    tc = vn.tech_costs
    conv = currency == "VND" ? (v -> convert_vnd_to_usd(v; exchange_rate=exchange_rate)) : identity

    # --- PV ---
    if haskey(d, "PV")
        pv_data = tc["PV"]
        pv_block = d["PV"] isa Dict ? d["PV"] : (d["PV"] isa Vector && length(d["PV"]) > 0 ? d["PV"][1] : nothing)

        if pv_block !== nothing && haskey(pv_data, pv_type) && haskey(pv_data[pv_type], region)
            regional = pv_data[pv_type][region]
            _set_default!(pv_block, "installed_cost_per_kw", conv(regional["installed_cost_per_kw"]))
            _set_default!(pv_block, "om_cost_per_kw", conv(regional["om_cost_per_kw"]))
        end

        # Apply common defaults
        if haskey(pv_data, "common_defaults")
            targets = d["PV"] isa Vector ? d["PV"] : [d["PV"]]
            for t in targets
                t isa Dict || continue
                for (k, v) in pv_data["common_defaults"]
                    k == "tilt_rule" && continue
                    _set_default!(t, k, v)
                end
            end
        end
    end

    # --- Wind ---
    if haskey(d, "Wind")
        wind_data = tc["Wind"]
        wind_block = d["Wind"]

        if haskey(wind_data, wind_type) && haskey(wind_data[wind_type], region)
            regional = wind_data[wind_type][region]
            _set_default!(wind_block, "installed_cost_per_kw", conv(regional["installed_cost_per_kw"]))
            _set_default!(wind_block, "om_cost_per_kw", conv(regional["om_cost_per_kw"]))
        end

        if haskey(wind_data, "common_defaults")
            for (k, v) in wind_data["common_defaults"]
                _set_default!(wind_block, k, v)
            end
        end
    end

    # --- ElectricStorage ---
    if haskey(d, "ElectricStorage")
        es_data = tc["ElectricStorage"]
        es_block = d["ElectricStorage"]

        if haskey(es_data, "li_ion") && haskey(es_data["li_ion"], region)
            regional = es_data["li_ion"][region]
            _set_default!(es_block, "installed_cost_per_kw", conv(regional["installed_cost_per_kw"]))
            _set_default!(es_block, "installed_cost_per_kwh", conv(regional["installed_cost_per_kwh"]))
        end

        if haskey(es_data, "common_defaults")
            for (k, v) in es_data["common_defaults"]
                _set_default!(es_block, k, v)
            end
        end
    end

    # --- Generator ---
    if haskey(d, "Generator")
        gen_data = tc["Generator"]
        gen_block = d["Generator"]

        if haskey(gen_data, "diesel")
            diesel = gen_data["diesel"]
            for (k, v) in diesel
                _set_default!(gen_block, k, conv(v))
            end
        end

        if haskey(gen_data, "common_defaults")
            for (k, v) in gen_data["common_defaults"]
                _set_default!(gen_block, k, v)
            end
        end
    end

    return d
end

# ---------------------------------------------------------------------------
# apply_decree57_export!(d, vn)
# ---------------------------------------------------------------------------

"""
    apply_decree57_export!(d::Dict, vn::VNData;
                           max_export_fraction::Real=0.20,
                           exchange_rate::Real=vn.exchange_rate)

Configure export rules per Decree 57/2025 as amended by Decree 243/2026
(surplus cap 50% from 2026-06-26; resolved from the active export-rules data
file):
 - `can_net_meter = false`
 - `can_wholesale = true` at the surplus purchase rate
 - `can_export_beyond_nem_limit = false`
 - `can_curtail = true`

The wholesale rate is set to the rooftop solar surplus purchase rate from the export rules data file.
`max_export_fraction` is stored in `_meta` so Vietnam solve wrappers can add a hard JuMP
constraint before optimization. Plain `REopt.run_reopt(...)` does not read this metadata.
"""
function apply_decree57_export!(d::Dict, vn::VNData;
                                regime_id::String=DEFAULT_REGIME_ID,
                                max_export_fraction::Union{Nothing,Real}=nothing,
                                exchange_rate::Real=vn.exchange_rate)
    resolved_regime = resolve_vietnam_regime(vn; regime_id=regime_id)
    er = resolved_regime["export_rules"]
    rooftop = get(er, "rooftop_solar", Dict())
    data_default = get(rooftop, "max_export_fraction", 0.20)
    if max_export_fraction === nothing
        max_export_fraction = data_default
    end

    max_export_fraction = _validate_export_fraction(max_export_fraction)
    if max_export_fraction != data_default
        @warn "max_export_fraction=$max_export_fraction is stored for Vietnam custom solve wrappers, " *
              "but plain REopt.run_reopt(...) will NOT enforce it automatically."
    end

    et = _ensure_block!(d, "ElectricTariff")

    # Wholesale rate from surplus purchase price
    surplus_usd = get(rooftop, "surplus_purchase_rate_usd_per_kwh", nothing)
    if surplus_usd === nothing
        surplus_vnd = get(rooftop, "surplus_purchase_rate_vnd_per_kwh", 671)
        surplus_usd = convert_vnd_to_usd(surplus_vnd; exchange_rate=exchange_rate)
    end
    _set_default!(et, "wholesale_rate", surplus_usd)

    # Export beyond NEM limit off — this keeps Decree 57 exports on the wholesale bin only
    _set_default!(et, "export_rate_beyond_net_metering_limit", 0)

    # PV-specific export settings
    if haskey(d, "PV")
        targets = d["PV"] isa Vector ? d["PV"] : [d["PV"]]
        for pv in targets
            pv isa Dict || continue
            _set_default!(pv, "can_net_meter", false)
            _set_default!(pv, "can_wholesale", true)
            _set_default!(pv, "can_export_beyond_nem_limit", false)
            _set_default!(pv, "can_curtail", true)
        end
    end

    meta = _ensure_block!(d, "_meta")
    _set_default!(meta, DECREE57_META_KEY, max_export_fraction)
    _set_default!(meta, "resolved_regime_id", regime_id)
    _set_default!(meta, "regime_registry_version", resolved_regime["registry_version"])
    for (k, v) in resolved_regime["postprocess_overrides"]
        _set_default!(meta, k, deepcopy(v))
    end

    return d
end

"""
    add_decree57_export_cap_constraint!(m::JuMP.AbstractModel, p::REopt.REoptInputs;
                                        max_export_fraction::Real=0.20)

Add the Decree 57 hard annual export cap for PV technologies:

`annual PV export <= max_export_fraction * annual PV production`

Both sides use REopt's average-annual production convention (`levelization_factor`) so the
constraint aligns with `annual_energy_exported_kwh` and `annual_energy_produced_kwh` results.
"""
function add_decree57_export_cap_constraint!(m::JuMP.AbstractModel, p::REopt.REoptInputs;
                                             max_export_fraction::Real=0.20)
    max_export_fraction = _validate_export_fraction(max_export_fraction)

    if isempty(p.techs.pv) || isempty(p.s.electric_tariff.export_bins)
        return m
    end

    export_expr = @expression(m,
        p.hours_per_time_step * sum(
            m[:dvProductionToGrid][t, u, ts]
            for t in p.techs.pv, u in p.export_bins_by_tech[t], ts in p.time_steps
        )
    )

    production_expr = @expression(m,
        p.hours_per_time_step * sum(
            m[:dvRatedProduction][t, ts] * p.production_factor[t, ts] * p.levelization_factor[t]
            for t in p.techs.pv, ts in p.time_steps
        )
    )

    m[DECREE57_CONSTRAINT_NAME] = @constraint(m, export_expr <= max_export_fraction * production_expr)
    return m
end

"""
    run_vietnam_reopt(m::JuMP.AbstractModel, d::Dict)
    run_vietnam_reopt(ms::AbstractVector{<:JuMP.AbstractModel}, d::Dict)

Solve a Vietnam scenario while honoring the Decree 57 export-cap metadata written by
`apply_decree57_export!`. For scenarios without the metadata, this falls back to REopt's
standard solve path.
"""
function run_vietnam_reopt(m::JuMP.AbstractModel, d::Dict)
    max_export_fraction = _decree57_export_fraction(d)
    clean = _scenario_input_dict(d)

    if max_export_fraction === nothing
        return REopt.run_reopt(m, clean)
    end

    s = Scenario(clean)
    p = REoptInputs(s)
    return _run_reopt_with_optional_constraint(m, p; max_export_fraction=max_export_fraction)
end

function run_vietnam_reopt(ms::AbstractVector{T}, d::Dict) where {T <: JuMP.AbstractModel}
    max_export_fraction = _decree57_export_fraction(d)
    clean = _scenario_input_dict(d)

    if max_export_fraction === nothing
        return REopt.run_reopt(ms, clean)
    end

    s = Scenario(clean)
    if s.settings.off_grid_flag
        @warn "Only using first Model and not running BAU case because `off_grid_flag` is true. The BAU scenario is not applicable for off-grid microgrids."
        return run_vietnam_reopt(ms[1], d)
    end

    p = REoptInputs(s)
    bau_inputs = REopt.BAUInputs(p)
    bau_results = REopt.run_reopt(ms[1], bau_inputs; organize_pvs=false)
    opt_results = _run_reopt_with_optional_constraint(ms[2], p; organize_pvs=false, max_export_fraction=max_export_fraction)

    if !(bau_results isa Dict) || !(opt_results isa Dict) || bau_results["status"] == "error" || opt_results["status"] == "error"
        error("REopt scenarios solved either with errors or non-optimal solutions.")
    end

    results = REopt.combine_results(p, bau_results, opt_results, bau_inputs.s)
    results["Financial"] = merge(results["Financial"], REopt.proforma_results(p, results))

    if !isempty(p.techs.pv)
        REopt.organize_multiple_pv_results(p, results)
    end

    return results
end

# ---------------------------------------------------------------------------
# apply_vietnam_defaults! — master function
# ---------------------------------------------------------------------------

"""
    apply_vietnam_defaults!(d::Dict, vn::VNData;
                            customer_type::String="industrial",
                            voltage_level::String="medium_voltage_22kv_to_110kv",
                            region::String="south",
                            pv_type::String="rooftop",
                            wind_type::String="onshore",
                            financial_profile::String="standard",
                            currency::String="USD",
                            exchange_rate::Real=vn.exchange_rate,
                            apply_tariff::Bool=true,
                            apply_emissions::Bool=true,
                            apply_tech_costs::Bool=true,
                            apply_export_rules::Bool=true,
                            apply_financials::Bool=true,
                            apply_zero_incentives::Bool=true,
                            kwargs...)

Master preprocessing function. Calls all sub-functions in sequence using data from `vn`.
All settings are non-destructive: user-provided values in `d` are never overwritten.

Set any `apply_*` flag to `false` to skip that preprocessing step.
Additional keyword arguments are forwarded to `apply_vietnam_financials!`.
"""
function apply_vietnam_defaults!(d::Dict, vn::VNData;
                                 customer_type::String="industrial",
                                 voltage_level::String="medium_voltage_22kv_to_110kv",
                                 region::String="south",
                                 pv_type::String="rooftop",
                                 wind_type::String="onshore",
                                 financial_profile::String="standard",
                                 regime_id::String=DEFAULT_REGIME_ID,
                                 currency::String="USD",
                                 exchange_rate::Real=vn.exchange_rate,
                                 apply_tariff::Bool=true,
                                 apply_emissions::Bool=true,
                                 apply_tech_costs::Bool=true,
                                 apply_export_rules::Bool=true,
                                 apply_financials::Bool=true,
                                 apply_zero_incentives::Bool=true,
                                 kwargs...)

    # 1. Zero US incentives first (before tech costs, so common_defaults don't conflict)
    if apply_zero_incentives
        zero_us_incentives!(d)
    end

    # 2. Financial defaults
    if apply_financials
        apply_vietnam_financials!(d, vn;
                                  financial_profile=financial_profile,
                                  kwargs...)
    end

    # 3. TOU tariff
    if apply_tariff
        tariff_dict = build_vietnam_tariff(vn, customer_type, voltage_level;
                                           regime_id=regime_id,
                                           exchange_rate=exchange_rate)
        et = _ensure_block!(d, "ElectricTariff")
        for (k, v) in tariff_dict
            _set_default!(et, k, v)
        end
    end

    # 4. Emissions
    if apply_emissions
        apply_vietnam_emissions!(d, vn)
    end

    # 5. Tech costs
    if apply_tech_costs
        apply_vietnam_tech_costs!(d, vn;
                                  region=region,
                                  pv_type=pv_type,
                                  wind_type=wind_type,
                                  exchange_rate=exchange_rate,
                                  currency=currency)
    end

    # 6. Decree 57 export rules
    if apply_export_rules
        apply_decree57_export!(d, vn; regime_id=regime_id, exchange_rate=exchange_rate)
    end

    if apply_tariff || apply_export_rules
        meta = _ensure_block!(d, "_meta")
        resolved_regime = resolve_vietnam_regime(vn; regime_id=regime_id)
        _set_default!(meta, "resolved_regime_id", regime_id)
        _set_default!(meta, "regime_registry_version", resolved_regime["registry_version"])
        for (k, v) in resolved_regime["postprocess_overrides"]
            _set_default!(meta, k, deepcopy(v))
        end
    end

    return d
end

end # module REoptVietnam
