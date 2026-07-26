"""Deterministic multi-regime scenario materialization and execution helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .preprocess import apply_vietnam_defaults, load_vietnam_data, resolve_vietnam_regime


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_ASSUMPTION_SET_DIR = REPO_ROOT / "scenarios" / "regime_engine" / "assumption_sets"
DEFAULT_GENERATED_SCENARIO_DIR = REPO_ROOT / "scenarios" / "generated" / "regime_engine"
DEFAULT_RESULT_STORE_DIR = REPO_ROOT / "artifacts" / "results" / "regime_engine"
JULIA_RUNNER = REPO_ROOT / "scripts" / "julia" / "run_vietnam_scenario.jl"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _slugify(value: str) -> str:
    chars = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        else:
            if not previous_dash:
                chars.append("-")
                previous_dash = True
    slug = "".join(chars).strip("-")
    return slug or "project"


def canonicalize_for_hash(payload: Dict[str, Any]) -> str:
    """Return canonical JSON text for stable scenario hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def scenario_hash(canonical_json: str) -> str:
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]


def load_assumption_set(assumption_set_id: str, assumption_set_dir: Path = DEFAULT_ASSUMPTION_SET_DIR) -> Dict[str, Any]:
    path = assumption_set_dir / f"{assumption_set_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Assumption set not found: {path}")
    payload = _read_json(path)
    payload.setdefault("scenario_overrides", {})
    payload.setdefault("meta_overrides", {})
    payload.setdefault("notes", [])
    payload.setdefault("_meta", {})
    payload["_meta"].setdefault("id", assumption_set_id)
    payload["_path"] = str(path)
    return payload


def _template_context(base_scenario: Dict[str, Any], fallback_name: str) -> Dict[str, Any]:
    template = base_scenario.get("_template", {})
    return {
        "customer_type": template.get("customer_type", "industrial"),
        "voltage_level": template.get("voltage_level", "medium_voltage_22kv_to_110kv"),
        "region": template.get("region", "south"),
        "pv_type": "ground" if base_scenario.get("PV", {}).get("location") == "ground" else "rooftop",
        "wind_type": "onshore",
        "financial_profile": "standard",
        "project_slug": _slugify(template.get("name", fallback_name)),
    }


def materialize_regime_scenario(
    scenario_path: Path,
    regime_id: str,
    assumption_set_id: str,
    *,
    generated_root: Path = DEFAULT_GENERATED_SCENARIO_DIR,
    result_store_root: Path = DEFAULT_RESULT_STORE_DIR,
) -> Dict[str, Any]:
    vn = load_vietnam_data()
    base_scenario = _read_json(scenario_path)
    context = _template_context(base_scenario, scenario_path.stem)
    assumption_set = load_assumption_set(assumption_set_id)

    scenario = deepcopy(base_scenario)
    scenario = _deep_merge(scenario, assumption_set["scenario_overrides"])
    apply_vietnam_defaults(
        scenario,
        vn,
        customer_type=context["customer_type"],
        voltage_level=context["voltage_level"],
        region=context["region"],
        pv_type=context["pv_type"],
        wind_type=context["wind_type"],
        financial_profile=context["financial_profile"],
        regime_id=regime_id,
    )

    scenario_meta = scenario.setdefault("_meta", {})
    scenario_meta["source_scenario_path"] = str(scenario_path)
    scenario_meta["assumption_set_id"] = assumption_set_id
    scenario_meta["assumption_set_path"] = assumption_set["_path"]
    scenario_meta["regime_runner_version"] = "phase3"
    for key, value in assumption_set.get("meta_overrides", {}).items():
        scenario_meta[key] = deepcopy(value)

    resolved_regime = resolve_vietnam_regime(vn, regime_id)
    hash_payload = {
        "scenario": scenario,
        "regime_id": regime_id,
        "assumption_set_id": assumption_set_id,
        "registry_version": resolved_regime.get("registry_version"),
    }
    canonical = canonicalize_for_hash(hash_payload)
    run_hash = scenario_hash(canonical)
    scenario_meta["scenario_hash"] = run_hash

    project_slug = context["project_slug"]
    generated_dir = generated_root / project_slug
    generated_path = generated_dir / f"{run_hash}_{regime_id}_{assumption_set_id}.json"

    result_dir = result_store_root / project_slug / run_hash
    manifest_path = result_dir / "run_manifest.json"
    cached_manifest = _read_json(manifest_path) if manifest_path.is_file() else None
    cache_hit = bool(cached_manifest and cached_manifest.get("status") in {"scenario_built_no_solve", "optimal", "cached"})

    _write_json(generated_path, scenario)
    input_path = _write_json(result_dir / "input.json", scenario)
    resolved_regime_path = _write_json(result_dir / "resolved_regime.json", resolved_regime)

    manifest = {
        "project_slug": project_slug,
        "scenario_hash": run_hash,
        "regime_id": regime_id,
        "assumption_set_id": assumption_set_id,
        "registry_version": resolved_regime.get("registry_version"),
        "source_scenario_path": str(scenario_path),
        "generated_scenario_path": str(generated_path),
        "result_dir": str(result_dir),
        "input_path": str(input_path),
        "resolved_regime_path": str(resolved_regime_path),
        "status": "materialized",
        "cache_hit": cache_hit,
        "generated_at_epoch": int(time.time()),
    }

    summary = {
        "project_slug": project_slug,
        "scenario_hash": run_hash,
        "regime_id": regime_id,
        "assumption_set_id": assumption_set_id,
        "status": "materialized",
        "resolved_regime_id": scenario_meta.get("resolved_regime_id"),
        "monthly_demand_rate_usd_per_kw": scenario.get("ElectricTariff", {}).get("monthly_demand_rates", [0])[0],
        "decree57_max_export_fraction": scenario_meta.get("decree57_max_export_fraction"),
    }

    return {
        "project_slug": project_slug,
        "scenario": scenario,
        "resolved_regime": resolved_regime,
        "assumption_set": assumption_set,
        "scenario_hash": run_hash,
        "generated_scenario_path": str(generated_path),
        "result_dir": str(result_dir),
        "input_path": str(input_path),
        "resolved_regime_path": str(resolved_regime_path),
        "manifest_path": str(manifest_path),
        "summary_path": str(result_dir / "summary.json"),
        "manifest": manifest,
        "summary": summary,
    }


def _run_julia_scenario(generated_scenario_path: str, result_dir: str, solve: bool) -> subprocess.CompletedProcess[str]:
    command = ["julia", "--project", "--compile=min", str(JULIA_RUNNER), "--scenario", generated_scenario_path, "--output-dir", result_dir]
    if not solve:
        command.append("--no-solve")
    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )


def build_regime_matrix(
    *,
    scenario_path: Path,
    regime_ids: Iterable[str],
    assumption_set_ids: Iterable[str],
    generated_root: Path = DEFAULT_GENERATED_SCENARIO_DIR,
    result_store_root: Path = DEFAULT_RESULT_STORE_DIR,
    solve: bool = False,
    force: bool = False,
) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    for regime_id in regime_ids:
        for assumption_set_id in assumption_set_ids:
            run = materialize_regime_scenario(
                scenario_path=Path(scenario_path),
                regime_id=regime_id,
                assumption_set_id=assumption_set_id,
                generated_root=generated_root,
                result_store_root=result_store_root,
            )

            manifest = run["manifest"]
            summary = run["summary"]
            result_dir = Path(run["result_dir"])
            reopt_results_path = result_dir / "reopt-results.json"

            if manifest["cache_hit"] and not force:
                manifest["status"] = "cached"
                summary["status"] = "cached"
            elif solve:
                completed = _run_julia_scenario(run["generated_scenario_path"], run["result_dir"], solve=True)
                manifest["stdout"] = completed.stdout
                manifest["stderr"] = completed.stderr
                if completed.returncode != 0:
                    manifest["status"] = "error"
                    summary["status"] = "error"
                    manifest["returncode"] = completed.returncode
                else:
                    manifest["status"] = "optimal" if reopt_results_path.is_file() else "completed_without_results"
                    summary["status"] = manifest["status"]
            else:
                completed = _run_julia_scenario(run["generated_scenario_path"], run["result_dir"], solve=False)
                manifest["stdout"] = completed.stdout
                manifest["stderr"] = completed.stderr
                manifest["returncode"] = completed.returncode
                manifest["status"] = "scenario_built_no_solve" if completed.returncode == 0 else "error"
                summary["status"] = manifest["status"]

            _write_json(Path(run["manifest_path"]), manifest)
            _write_json(Path(run["summary_path"]), summary)
            runs.append(run)

    return runs


def build_regime_scenarios(
    *,
    scenario_path: Path,
    regime_ids: Iterable[str],
    assumption_set_ids: Iterable[str],
    generated_root: Path = DEFAULT_GENERATED_SCENARIO_DIR,
    result_store_root: Path = DEFAULT_RESULT_STORE_DIR,
) -> List[Dict[str, Any]]:
    outputs = []
    for regime_id in regime_ids:
        for assumption_set_id in assumption_set_ids:
            outputs.append(
                materialize_regime_scenario(
                    scenario_path=Path(scenario_path),
                    regime_id=regime_id,
                    assumption_set_id=assumption_set_id,
                    generated_root=generated_root,
                    result_store_root=result_store_root,
                )
            )
    return outputs
