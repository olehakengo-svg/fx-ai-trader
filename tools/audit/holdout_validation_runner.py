#!/usr/bin/env python3
"""HIP-1 v2 holdout validation runner skeleton."""

from __future__ import annotations

import os

os.environ["FX_HOLDOUT_GUARD"] = "1"

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run explicit holdout validation with FX_HOLDOUT_GUARD enabled."
    )
    parser.add_argument(
        "--validation-mode",
        action="store_true",
        help="Also set FX_HOLDOUT_VALIDATION=1 to bypass cuts for audit-only runs.",
    )
    parser.add_argument(
        "--symbol",
        default="USDJPY=X",
        help="Symbol to validate when implementation is expanded.",
    )
    parser.add_argument(
        "--interval",
        default="5m",
        help="Interval to validate when implementation is expanded.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=400,
        help="Lookback window for future validation implementation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.validation_mode:
        os.environ["FX_HOLDOUT_VALIDATION"] = "1"
    print(
        "HIP-1 v2 validation skeleton: "
        f"guard={os.environ.get('FX_HOLDOUT_GUARD')} "
        f"validation={os.environ.get('FX_HOLDOUT_VALIDATION', '0')} "
        f"symbol={args.symbol} interval={args.interval} days={args.days}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
