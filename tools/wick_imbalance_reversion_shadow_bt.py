#!/usr/bin/env python3
"""Compatibility entrypoint for wick_imbalance_reversion V2 shadow BT."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.alpha_wick_imbalance_shadow_bt import main


if __name__ == "__main__":
    raise SystemExit(main())
