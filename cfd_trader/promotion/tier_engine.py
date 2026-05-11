"""Shadow tier engine — report-only stat aggregator.

Phase 2 reports the 7-axis stats with Bonferroni-corrected Wilson_lo.
It does NOT promote to Live (that is Phase 4 with MT5 integration).

Bonferroni `m` is read from each trade's extra_json. If multiple m values
appear, use the MAX (most conservative). If no m is recorded, default to 1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from cfd_trader.audit.queries import shadow_trades_for
from cfd_trader.engine.stats import (
    wilson_lo, profit_factor, kelly_fraction, max_drawdown,
)
from cfd_trader.promotion.gates import H1_N_MIN


@dataclass(frozen=True)
class TierReport:
    strategy_name: str
    n: int
    wr: float
    ev_point: float
    pf: float
    wilson_lo_raw: float        # z = 1.96 (95% one-sided)
    wilson_lo_bonferroni: float # z adjusted for m comparisons
    kelly_fraction: float
    max_dd_point: float
    bonferroni_m: int
    h1_gate_distance: int       # N_min - N (positive = not ready)


def _z_for_bonferroni(m: int, alpha: float = 0.05) -> float:
    """One-sided z for alpha / m."""
    if m <= 1:
        return 1.96
    table = {1: 1.96, 2: 2.241, 3: 2.394, 4: 2.498, 5: 2.576, 10: 2.807}
    if m in table:
        return table[m]
    try:
        from statistics import NormalDist
        return NormalDist().inv_cdf(1.0 - alpha / m)
    except Exception:
        return 2.576  # conservative


def evaluate(db_path: str, *, strategy_name: str) -> TierReport:
    trades = shadow_trades_for(db_path, strategy_name=strategy_name)
    n = len(trades)
    if n == 0:
        return TierReport(
            strategy_name=strategy_name, n=0, wr=0.0, ev_point=0.0, pf=0.0,
            wilson_lo_raw=0.0, wilson_lo_bonferroni=0.0,
            kelly_fraction=0.0, max_dd_point=0.0,
            bonferroni_m=1, h1_gate_distance=H1_N_MIN,
        )

    df = pd.DataFrame([
        {"pnl_point": t.pnl_point if t.pnl_point is not None else 0.0,
         "extra_json": t.extra_json}
        for t in trades
    ])
    wins = int((df["pnl_point"] > 0).sum())
    wr = wins / n
    ev = float(df["pnl_point"].mean())
    pf = profit_factor(df)
    win_pnl = df.loc[df["pnl_point"] > 0, "pnl_point"]
    loss_pnl = df.loc[df["pnl_point"] < 0, "pnl_point"]
    avg_win = float(win_pnl.mean()) if len(win_pnl) else 0.0
    avg_loss = float(-loss_pnl.mean()) if len(loss_pnl) else 0.0
    kelly = kelly_fraction(wr=wr, avg_win_point=avg_win, avg_loss_point=avg_loss)
    eq = df["pnl_point"].cumsum()
    dd = max_drawdown(eq)

    # Bonferroni m: max across rows (most conservative).
    ms: list[int] = []
    for js in df["extra_json"].dropna():
        try:
            d = json.loads(js)
            ms.append(int(d.get("bonferroni_m", 1)))
        except (ValueError, TypeError):
            continue
    m = max(ms) if ms else 1

    wlo_raw = wilson_lo(wins=wins, n=n, z=1.96)
    wlo_bonf = wilson_lo(wins=wins, n=n, z=_z_for_bonferroni(m))

    distance = max(0, H1_N_MIN - n)

    return TierReport(
        strategy_name=strategy_name, n=n, wr=wr, ev_point=ev, pf=pf,
        wilson_lo_raw=wlo_raw, wilson_lo_bonferroni=wlo_bonf,
        kelly_fraction=kelly, max_dd_point=dd,
        bonferroni_m=m, h1_gate_distance=distance,
    )
