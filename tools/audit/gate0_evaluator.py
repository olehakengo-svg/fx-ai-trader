#!/usr/bin/env python3
"""Gate 0 evaluator harness.

This file is intentionally a small harness. Existing Gate 0 verdict logic is
outside the NSG-1 task scope; the only integrated behavior here is optional
Neighborhood Stability Gate evaluation when explicit grid inputs are provided.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_grid(path: Path) -> Any:
    import pandas as pd

    if path.suffix.lower() == ".json":
        return pd.read_json(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported grid format: {path.suffix}")


def _load_primary_cell(raw: str | None) -> dict[str, Any]:
    if raw is None:
        raise ValueError("--primary-cell-json is required with --require-nsg1")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("--primary-cell-json must decode to an object")
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Gate 0 checks, optionally requiring NSG-1.",
    )
    parser.add_argument(
        "--require-nsg1",
        action="store_true",
        help="Require NSG-1 neighborhood stability in the emitted JSON verdict.",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        help="CSV or JSON grid with parameter axes plus N, wilson_lo, kelly.",
    )
    parser.add_argument(
        "--primary-cell-json",
        help='Primary cell as JSON, e.g. \'{"rsi":10,"exit":"trail"}\'.',
    )
    parser.add_argument(
        "--bev-wr",
        type=float,
        default=0.50,
        help="Break-even win rate used for NSG-1 sign agreement.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. Defaults to stdout.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    result: dict[str, Any] = {
        "gate0": {
            "implemented": False,
            "notes": ["skeleton_only_existing_gate0_logic_out_of_scope"],
        },
        "nsg1": None,
    }

    if args.require_nsg1:
        if args.grid is None:
            result["nsg1"] = {
                "evaluated": False,
                "pass_overall": False,
                "notes": ["grid_required_for_nsg1"],
            }
        else:
            from tools.audit.neighborhood_stability import (
                compute_neighborhood_stability,
            )

            verdict = compute_neighborhood_stability(
                _load_grid(args.grid),
                _load_primary_cell(args.primary_cell_json),
                args.bev_wr,
            )
            result["nsg1"] = {"evaluated": True, **asdict(verdict)}

    encoded = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
