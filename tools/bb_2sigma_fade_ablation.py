#!/usr/bin/env python3
"""Regenerate the BB 2-sigma fade ablation report."""
from __future__ import annotations

from tools.bb_2sigma_fade_bt import REPORT_DIR, run_backtest


def main() -> int:
    result = run_backtest(report_dir=REPORT_DIR)
    print(f"wrote {REPORT_DIR / 'ablation.md'} with {len(result['family_b'])} Family B cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
