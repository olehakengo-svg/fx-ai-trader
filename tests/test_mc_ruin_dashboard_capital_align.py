"""Regression pin: /api/risk/dashboard MC capital is JPY-aligned (rule:R3, 2026-08-05).

Track C D-b (2026-07-28) aligned the ruin *gate* capital
(demo_trader._get_ruin_probability の _ruin_capital_pips) to real NAV, but the
dashboard call site kept compute_risk_dashboard's default initial_capital=1000
pips. One wide-stop JPY-cross fill (oanda 549250, −123.2p = ¥1,232 = 0.34% NAV)
then flipped the *display* ruin 0%→100% while the gate measured 0.0 — the
classic 「同じ事実を表す複数値は同じ statement で更新する」 lesson.

References:
- knowledge-base/wiki/analyses/mc-ruin-dashboard-artifact-2026-08-05.md
- knowledge-base/raw/trade-logs/2026-08-04.md (incident daily, Key Obs #5/#6)
"""
from __future__ import annotations

import re
from pathlib import Path

from modules.risk_analytics import monte_carlo_ruin

ROOT = Path(__file__).resolve().parents[1]

# The exact 30d window that produced the ruin=100% artifact (2026-08-04 daily).
INCIDENT_30D_PNL = [-123.2, -30.1, -7.9, -7.8, -6.8, -2.4, 0.1, 0.6, 1.8, 1.8]
JPY_ALIGNED_CAPITAL_PIPS = max(359109.0 / 61.9, 1000.0)


def test_incident_series_ruin_resolves_under_aligned_capital():
    """同一系列でも資本を実 NAV の pip 換算に揃えれば ruin は非破局値に戻る。"""
    legacy = monte_carlo_ruin(
        INCIDENT_30D_PNL, initial_capital=1000.0,
        n_simulations=2000, n_trades_forward=300, lot_multiplier=0.2)
    aligned = monte_carlo_ruin(
        INCIDENT_30D_PNL, initial_capital=JPY_ALIGNED_CAPITAL_PIPS,
        n_simulations=2000, n_trades_forward=300, lot_multiplier=0.2)
    assert legacy["ruin_probability"] > 0.9, (
        "sanity: the artifact must reproduce under the legacy 1000-pip base")
    assert aligned["ruin_probability"] < 0.7, (
        "JPY-aligned capital must keep the same series below the 0.7 gate "
        "threshold — mirrors the gate-path measurement (ruin=0.0, 2026-08-05)")


def test_dashboard_route_passes_aligned_capital():
    """app.py /api/risk/dashboard が gate 側と同一式の資本を MC に渡すことを pin。"""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    m = re.search(
        r"def api_risk_dashboard\(\):(.*?)\n@app\.route", src, re.DOTALL)
    assert m, "api_risk_dashboard route not found"
    body = m.group(1)
    assert "OANDA_EQ_BASE_JPY" in body and "OANDA_JPY_PER_PIP_AVG" in body, (
        "dashboard MC capital must be derived from the same env pair as the "
        "gate path (_get_ruin_probability) — do not regress to the bare "
        "compute_risk_dashboard(closed, lot_multiplier=...) call")
    assert re.search(
        r"compute_risk_dashboard\(\s*closed,\s*initial_capital=_ruin_capital_pips",
        body), "initial_capital=_ruin_capital_pips must be passed"
