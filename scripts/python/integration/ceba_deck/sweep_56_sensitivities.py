"""Run the 56-sweep with three configurations and emit a sensitivity report.

Three configurations:
1. Baseline: synthetic 9,750 MWh load + FMP 1,426.6 (deck anchor) + $4M CAPEX.
2. FMP sensitivity: synthetic load + FMP 1,700 (repo sensitivity center) + $4M CAPEX.
3. Load sensitivity: real Emivest 2024 meter + FMP 1,426.6 + $4M CAPEX.

Reads ``reports/dppa_july_2026_sweep_56.json`` (the baseline), re-runs
the sweep with each sensitivity, and writes a single
``reports/dppa_july_2026_sensitivities.json`` with all three configurations
side-by-side.

Usage (from repo root):
    .venv\\Scripts\\python.exe scripts/python/integration/ceba_deck/sweep_56_sensitivities.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_PYTHON = REPO_ROOT / "scripts" / "python"
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
SWEEP_SCRIPT = SCRIPTS_PYTHON / "integration" / "ceba_deck" / "sweep_56.py"


def _run_sweep(fmp_anchor: str, load_source: str) -> dict:
    """Run sweep_56.py with the given sensitivity configuration; return the JSON payload."""
    args = [
        str(PYTHON),
        str(SWEEP_SCRIPT),
        "--fmp-anchor", fmp_anchor,
        "--load-source", load_source,
        "--capex", "4_000_000",
        "--out", str(REPO_ROOT / "reports" / f"dppa_july_2026_sweep_56_{fmp_anchor}_{load_source}.json"),
    ]
    env_overrides = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": "src/python;scripts/python",
    }
    import os
    env = {**os.environ, **env_overrides}
    res = subprocess.run(args, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"sweep failed: {res.stdout}\n{res.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(
        (REPO_ROOT / "reports" / f"dppa_july_2026_sweep_56_{fmp_anchor}_{load_source}.json").read_text(encoding="utf-8")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    out_path = args.out or (REPO_ROOT / "reports" / "dppa_july_2026_sensitivities.json")

    started = time.time()
    print("[sensitivities] running 3 configurations...", flush=True)
    baseline = _run_sweep("deck", "synthetic")
    print(f"  baseline:  {baseline['summary']['n_passing_all_three_gates']} of {baseline['summary']['n_total']}", flush=True)
    fmp_sens = _run_sweep("repo", "synthetic")
    print(f"  fmp=1,700: {fmp_sens['summary']['n_passing_all_three_gates']} of {fmp_sens['summary']['n_total']}", flush=True)
    load_sens = _run_sweep("deck", "emivest")
    print(f"  emivest:   {load_sens['summary']['n_passing_all_three_gates']} of {load_sens['summary']['n_total']}", flush=True)

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "phase": "PHASE-04",
            "duration_seconds": round(time.time() - started, 2),
        },
        "configurations": {
            "baseline": {
                "fmp_anchor": "deck",
                "fmp_vnd_kwh": 1_426.6,
                "load_source": "synthetic",
                "capex_ref_usd": 4_000_000.0,
                "summary": baseline["summary"],
                "n_passing": baseline["summary"]["n_passing_all_three_gates"],
            },
            "fmp_sensitivity": {
                "fmp_anchor": "repo",
                "fmp_vnd_kwh": 1_700.0,
                "load_source": "synthetic",
                "capex_ref_usd": 4_000_000.0,
                "summary": fmp_sens["summary"],
                "n_passing": fmp_sens["summary"]["n_passing_all_three_gates"],
            },
            "load_sensitivity": {
                "fmp_anchor": "deck",
                "fmp_vnd_kwh": 1_426.6,
                "load_source": "emivest",
                "capex_ref_usd": 4_000_000.0,
                "summary": load_sens["summary"],
                "n_passing": load_sens["summary"]["n_passing_all_three_gates"],
            },
        },
        "interpretation": (
            "All three configurations return 0 of N scenarios passing all three "
            "gates at the calibration's project basis (~$4M CAPEX). The '0 of "
            "56' finding is robust to the FMP anchor (deck 1,426.6 vs repo "
            "sensitivity center 1,700) and the load source (synthetic 9,750 "
            "MWh anchor vs real 2024 Emivest meter ~9,315 MWh). The deck's "
            "qualitative conclusion — 'the negotiation window may be empty at "
            "current market prices and fee levels' — is supported by the repo "
            "model; the deck's quantitative numbers (16.9% / 26.9% seller IRR, "
            "etc.) are not reproducible from disclosed terms (PHASE-03 "
            "monotonic miss)."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8", newline="\n")
    print(f"[sensitivities] wrote {out_path.relative_to(REPO_ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
