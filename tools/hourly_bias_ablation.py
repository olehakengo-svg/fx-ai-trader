#!/usr/bin/env python3
"""Regenerate the hourly bias ablation report."""
from __future__ import annotations

from tools.hourly_bias_bt import REPORT_DIR, run_backtest


def main() -> int:
    result = run_backtest(report_dir=REPORT_DIR)
    print(f"wrote {REPORT_DIR / 'ablation.md'} with {len(result['family_b'])} ablation cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
