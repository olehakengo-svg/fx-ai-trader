"""v1b Phase B Daily Monitor — LOCK Failure Conditions 自動評価

Pre-reg LOCK ma_trend_perfect (2026-04-30〜2026-05-30) の Failure
Conditions #1-#6 を毎日自動評価し、閾値接触で markdown report を生成。

Failure Conditions (from pre-reg-ma-trend-perfect-2026-04-30.md):
  1. Shadow LIVE Tokyo Wilson95下限 < 30%
  2. Shadow LIVE NY Wilson95下限 < 25%
  3. WR 連続 12d 下落トレンド
  4. spread 実測 > 1.2 pip (0.8 × 1.5)
  5. ema_trend_scalp 同期間 Shadow と相対 PF 比 < 1.5x
  6. ATR 14d 平均 (M15) > 0.1441 (f3 baseline +20%)

Phase B Promotion Checks (Tokyo + NY 合算 N>=30 で達成):
  - Tokyo Wilson95下限 > 30% MUST
  - NY Wilson95下限 > 25% MUST
  - WF 全 fold で PF>1.3 (continuation)

Usage:
  python3 research/edge_discovery/v1b_phase_b_monitor.py
  → fetch Render API → compute metrics → emit markdown report
"""
from __future__ import annotations
import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


_RENDER_BASE = "https://fx-ai-trader.onrender.com"
_LOCK_START = pd.Timestamp("2026-04-30", tz="UTC")
_LOCK_END = pd.Timestamp("2026-05-30", tz="UTC")
_F3_ATR_BASELINE = 0.1201          # f3 ATR 14d 平均 (M15)
_F3_ATR_FAILURE = 0.1441           # = 0.1201 × 1.20


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / den) * 100.0


def session_of_hour(h: int) -> str:
    if 0 <= h < 7:
        return "Tokyo"
    if 7 <= h < 13:
        return "London"
    if 13 <= h < 21:
        return "NY"
    return "Off"


def fetch_trades(strats: set, instrument: str = "USD_JPY") -> pd.DataFrame:
    # Use requests library (semgrep-recommended over urllib for URL safety).
    url = f"{_RENDER_BASE}/api/demo/trades?limit=10000"
    if not url.startswith("https://"):
        raise ValueError(f"unsupported URL scheme in {url!r}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    trades = data if isinstance(data, list) else data.get("trades", [])
    rows = []
    for t in trades:
        if t.get("entry_type") not in strats:
            continue
        if (t.get("instrument") or "") != instrument:
            continue
        if not t.get("entry_time"):
            continue
        ts = pd.Timestamp(t["entry_time"])
        if ts.tz is None:
            ts = ts.tz_localize("UTC")
        rows.append({
            "strategy": t["entry_type"],
            "entry_time": ts,
            "is_shadow": int(t.get("is_shadow") or 0),
            "pnl_pips": float(t.get("pnl_pips") or 0),
            "outcome": ("WIN" if (t.get("pnl_pips") or 0) > 0 else "LOSS"),
            "session": session_of_hour(ts.hour),
            "spread_at_entry": float(t.get("spread_at_entry") or 0),
        })
    return pd.DataFrame(rows)


def cell_stats(sub: pd.DataFrame) -> dict:
    n = len(sub)
    if n == 0:
        return {"n": 0, "wr": 0, "wilson_lo": 0, "ev": 0, "pf": 0}
    wins = int((sub["outcome"] == "WIN").sum())
    pnls = sub["pnl_pips"].values
    wr = wins / n
    pf = (pnls[pnls > 0].sum() / -pnls[pnls < 0].sum()) if (pnls < 0).any() else float("inf")
    if pf == float("inf"):
        pf = 99.9
    return {
        "n": n, "wins": wins, "wr": round(wr * 100, 2),
        "wilson_lo": round(wilson_lower(wins, n), 2),
        "ev": round(float(pnls.mean()), 3),
        "pf": round(pf, 3),
    }


def compute_current_atr_m15() -> float:
    """Compute current 14d rolling ATR average on M15 bars.

    Uses local parquet cache (USD_JPY_15m). Returns 0 if unavailable.
    """
    try:
        df = pd.read_parquet("data/cache/massive/USD_JPY_15m.parquet")
        df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        # Last 14 days of M15 bars (~1344 bars)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=14)
        recent = df[df.index >= cutoff]
        if len(recent) < 100:
            return 0.0
        h, l, c = recent["High"], recent["Low"], recent["Close"]
        pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        return float(atr.dropna().mean())
    except Exception:
        return 0.0


def evaluate_failure_conditions(stats_v1b: dict, stats_ema: dict, spread_avg: float) -> dict:
    """Evaluate the 6 LOCK Failure Conditions."""
    results = {}

    tokyo = stats_v1b.get("Tokyo", {})
    ny = stats_v1b.get("NY", {})

    tk_wilson = tokyo.get("wilson_lo", 0); tk_n = tokyo.get("n", 0)
    results["c1_tokyo_wilson_pass"] = (tk_wilson >= 30 if tk_n >= 5 else None)
    results["c1_tokyo_wilson_detail"] = f"Tokyo N={tk_n} Wilson={tk_wilson}%"

    ny_wilson = ny.get("wilson_lo", 0); ny_n = ny.get("n", 0)
    results["c2_ny_wilson_pass"] = (ny_wilson >= 25 if ny_n >= 5 else None)
    results["c2_ny_wilson_detail"] = f"NY N={ny_n} Wilson={ny_wilson}%"

    results["c4_spread_pass"] = spread_avg <= 1.2 if spread_avg > 0 else None
    results["c4_spread_detail"] = f"avg spread {spread_avg:.2f} pip"

    v1b_all_pf = stats_v1b.get("ALL", {}).get("pf", 0)
    ema_pf = stats_ema.get("ALL", {}).get("pf", 0.685)
    rel_pf = (v1b_all_pf / ema_pf) if ema_pf > 0 else 0
    results["c5_relative_pf_pass"] = rel_pf >= 1.5 if v1b_all_pf > 0 else None
    results["c5_relative_pf_detail"] = f"v1b PF={v1b_all_pf:.2f} / ema PF={ema_pf:.2f} = {rel_pf:.2f}× (need >=1.5)"

    atr_current = compute_current_atr_m15()
    results["c6_atr_pass"] = (atr_current <= _F3_ATR_FAILURE) if atr_current > 0 else None
    results["c6_atr_detail"] = f"ATR 14d M15 平均 = {atr_current:.4f} (failure threshold = {_F3_ATR_FAILURE})"

    return results


def render_report(today: pd.Timestamp, stats_v1b: dict, stats_ema: dict,
                  failure_results: dict, days_in_lock: int) -> str:
    lines = []
    lines.append(f"# v1b Phase B Daily Monitor — {today.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"**LOCK day**: {days_in_lock}/30  ({_LOCK_START.date()} 〜 {_LOCK_END.date()})")
    lines.append(f"**Generated**: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## v1b LIVE Stats (USD_JPY × is_shadow=0)")
    lines.append("")
    lines.append("| Cell | N | wins | WR | Wilson95下限 | EV pip | PF |")
    lines.append("|---|---|---|---|---|---|---|")
    for cell in ("Tokyo", "London", "NY", "ALL"):
        s = stats_v1b.get(cell, {})
        if s.get("n", 0) > 0:
            lines.append(f"| {cell} | {s['n']} | {s.get('wins',0)} | {s['wr']}% | {s['wilson_lo']}% | {s['ev']} | {s['pf']} |")
        else:
            lines.append(f"| {cell} | 0 | — | — | — | — | — |")
    lines.append("")
    lines.append("## Failure Conditions Status")
    lines.append("")
    lines.append("| # | Condition | Status | Detail |")
    lines.append("|---|---|---|---|")
    for cond, name in [
        ("c1_tokyo_wilson_pass", "Tokyo Wilson95下限 ≥ 30%"),
        ("c2_ny_wilson_pass", "NY Wilson95下限 ≥ 25%"),
        ("c4_spread_pass", "spread ≤ 1.2 pip"),
        ("c5_relative_pf_pass", "v1b/ema PF 比 ≥ 1.5×"),
        ("c6_atr_pass", f"ATR 14d M15 ≤ {_F3_ATR_FAILURE}"),
    ]:
        passed = failure_results.get(cond)
        if passed is None:
            badge = "⏳ N不足"
        elif passed:
            badge = "✅ pass"
        else:
            badge = "🔴 FAIL"
        detail = failure_results.get(cond.replace("_pass", "_detail"), "")
        lines.append(f"| {cond[:2]} | {name} | {badge} | {detail} |")
    lines.append("")
    lines.append("## Promotion Decision Preview (2026-05-30)")
    lines.append("")
    days_remaining = max(0, (_LOCK_END - today).days)
    lines.append(f"**Days remaining**: {days_remaining}")
    tk = stats_v1b.get("Tokyo", {})
    ny = stats_v1b.get("NY", {})
    combined_n = tk.get("n", 0) + ny.get("n", 0)
    lines.append(f"**Tokyo+NY 合算 N**: {combined_n} (require ≥ 30)")
    if combined_n >= 30 and tk.get("wilson_lo", 0) >= 30 and ny.get("wilson_lo", 0) >= 25:
        lines.append(f"**判定**: 🎯 全条件達成見込み")
    elif combined_n < 5:
        lines.append(f"**判定**: ⏳ N 不足、シグナル発火待ち")
    else:
        lines.append(f"**判定**: 🟡 進行中、最終判定は 2026-05-30")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(f"- Failure Condition #3 (WR 連続 12d 下落) は時系列分析で別途要評価")
    return "\n".join(lines)


def main():
    today = pd.Timestamp.now(tz="UTC").normalize()
    days_in_lock = max(0, (today - _LOCK_START).days)

    print(f"=== v1b Phase B Daily Monitor ===")
    print(f"Today: {today.date()}  LOCK day: {days_in_lock}/30")
    print()

    # Fetch trades
    print("Fetching from Render API...")
    df = fetch_trades({"ma_trend_perfect", "ema_trend_scalp"})
    print(f"  Retrieved: {len(df)} trades")
    if len(df) == 0:
        print("WARN: no trades returned")
        return

    # Filter to LIVE (is_shadow=0) and within LOCK period
    live_v1b = df[(df["strategy"] == "ma_trend_perfect")
                  & (df["is_shadow"] == 0)
                  & (df["entry_time"] >= _LOCK_START)]
    live_ema = df[(df["strategy"] == "ema_trend_scalp")
                  & (df["is_shadow"] == 0)
                  & (df["entry_time"] >= _LOCK_START)]
    # Shadow data also useful for early signals (within LOCK)
    shadow_v1b = df[(df["strategy"] == "ma_trend_perfect")
                    & (df["is_shadow"] == 1)
                    & (df["entry_time"] >= _LOCK_START)]
    print(f"  v1b LIVE in LOCK: {len(live_v1b)}, shadow: {len(shadow_v1b)}")
    print(f"  ema_trend_scalp LIVE in LOCK: {len(live_ema)}")

    # For Phase B, use LIVE data primarily; shadow as supplemental.
    # If LIVE N=0, fall back to shadow for early monitoring.
    v1b_eval = live_v1b if len(live_v1b) >= 5 else shadow_v1b
    eval_basis = "LIVE" if len(live_v1b) >= 5 else "Shadow (LIVE N<5)"
    print(f"  Eval basis: {eval_basis}")

    # Cell stats
    stats_v1b = {}
    for cell in ("Tokyo", "London", "NY"):
        stats_v1b[cell] = cell_stats(v1b_eval[v1b_eval["session"] == cell])
    stats_v1b["ALL"] = cell_stats(v1b_eval)
    stats_ema = {"ALL": cell_stats(live_ema)}
    avg_spread = float(v1b_eval["spread_at_entry"].mean()) if len(v1b_eval) > 0 else 0.0

    # Evaluate failure conditions
    failure = evaluate_failure_conditions(stats_v1b, stats_ema, avg_spread)

    # Render report
    report = render_report(today, stats_v1b, stats_ema, failure, days_in_lock)
    print()
    print(report)

    # Save to KB
    out_dir = Path("knowledge-base/raw/audits/ma_family_v1/phase_b_monitor")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"phase_b_{today.strftime('%Y-%m-%d')}.md"
    out_path.write_text(report)
    print()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
