#!/usr/bin/env python3
"""A/B BT filter for ema200_trend_reversal V2 USD_JPY overlap session gate."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools.ema200_reversal_shadow_bt as base  # noqa: E402

base.FLAG = "EMA200_TREND_REVERSAL_REDESIGN_V2"
base.SHADOW_PROMOTE_FLAG = "EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE"
base.OUTFILE = ROOT / "bt-results" / "ema200_trend_reversal-shadow-redesign-v2-2026-05-05.json"
base.VARIANT = "usd_jpy_overlap_session_gate_v2"


if __name__ == "__main__":
    raise SystemExit(base.main())
