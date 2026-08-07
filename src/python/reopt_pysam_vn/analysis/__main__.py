"""CLI for the generalized analysis pipelines (DEC-004).

    python -m reopt_pysam_vn.analysis onsite       --config deal.json [--results r.json] [--out o.json]
    python -m reopt_pysam_vn.analysis offsite_dppa  --config deal.json [--extracted e.json] [--out o.json]

Loads a DealConfig JSON, runs the requested pipeline, and writes (or prints) the
result JSON. Returns exit code 0 on success, 2 on a usage/runtime error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from reopt_pysam_vn.analysis.types import DealConfig


def _load_json(path: str) -> dict[str, Any]:
    # utf-8-sig tolerates a UTF-8 BOM (common from Windows editors/PowerShell) and
    # plain UTF-8 alike, so user-supplied config/results JSON loads either way.
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _emit(payload: dict[str, Any], out: str | None) -> None:
    text = json.dumps(payload, indent=2)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(text)


def _cmd_onsite(args: argparse.Namespace) -> int:
    from reopt_pysam_vn.analysis.onsite import run_onsite

    deal = DealConfig.from_dict(_load_json(args.config))
    results = _load_json(args.results) if args.results else None
    extracted = _load_json(args.extracted) if args.extracted else None
    result = run_onsite(
        deal,
        results=results,
        extracted=extracted,
        target_fraction=args.target_fraction,
    )
    _emit(result.to_dict(), args.out)
    return 0


def _cmd_offsite_dppa(args: argparse.Namespace) -> int:
    from reopt_pysam_vn.analysis.offsite_dppa import run_offsite_dppa

    deal = DealConfig.from_dict(_load_json(args.config))
    extracted = _load_json(args.extracted) if args.extracted else None
    result = run_offsite_dppa(deal, extracted=extracted, run_developer=args.run_developer)
    _emit(result.to_dict(), args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m reopt_pysam_vn.analysis",
        description="Run onsite (BTM) or offsite/DPPA analysis for a Vietnam deal config.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_on = sub.add_parser("onsite", help="Behind-the-meter REopt PV+BESS analysis.")
    p_on.add_argument("--config", required=True, help="Path to a deal_config JSON.")
    p_on.add_argument("--results", help="Path to a pre-solved REopt results JSON.")
    p_on.add_argument("--extracted", help="Path to an inputs JSON carrying loads_kw.")
    p_on.add_argument("--target-fraction", type=float, default=None, dest="target_fraction")
    p_on.add_argument("--out", help="Write result JSON here instead of stdout.")
    p_on.set_defaults(func=_cmd_onsite)

    p_off = sub.add_parser("offsite_dppa", help="Offsite/DPPA settlement + finance analysis.")
    p_off.add_argument("--config", required=True, help="Path to a deal_config JSON.")
    p_off.add_argument("--extracted", help="Path to an *_extracted_inputs JSON.")
    p_off.add_argument("--out", help="Write result JSON here instead of stdout.")
    p_off.add_argument(
        "--no-developer",
        action="store_false",
        dest="run_developer",
        help="Skip the PySAM developer screen.",
    )
    p_off.set_defaults(func=_cmd_offsite_dppa, run_developer=True)
    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
