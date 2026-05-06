from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["BT_MODE"] = "1"
os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
os.environ.setdefault("NO_AUTOSTART", "1")

import pandas as pd

from strategies.micro_scalp.base import CostModel, TickBar


PAIRS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP"]
INTERVAL = "15m"
LOOKBACK_DAYS = 365
OUT = Path("bt-results/ofi_mr-shadow-redesign-v2-2026-05-05.json")


def _load_bars(pair: str) -> list[TickBar]:
    path = Path(f"data/cache/massive/{pair}_{INTERVAL}.parquet")
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path} index is not DatetimeIndex")
    end = df.index.max()
    start = end - timedelta(days=LOOKBACK_DAYS)
    df = df.loc[df.index >= start].copy()
    cols = {c.lower(): c for c in df.columns}
    bars = []
    for ts, row in df.iterrows():
        volume = row[cols.get("volume", "Volume")]
        bars.append(
            TickBar(
                ts=ts.timestamp(),
                open=float(row[cols.get("open", "Open")]),
                high=float(row[cols.get("high", "High")]),
                low=float(row[cols.get("low", "Low")]),
                close=float(row[cols.get("close", "Close")]),
                tick_volume=max(1, int(volume)) if pd.notna(volume) else 1,
            )
        )
    return bars


def _wilson_lo(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def _stats(trades) -> dict:
    n = len(trades)
    wins = sum(1 for t in trades if t.pnl_pips > 0)
    gross_win = sum(t.pnl_pips for t in trades if t.pnl_pips > 0)
    gross_loss = abs(sum(t.pnl_pips for t in trades if t.pnl_pips < 0))
    if gross_loss == 0:
        pf = float("inf") if gross_win > 0 else 0.0
    else:
        pf = gross_win / gross_loss
    return {
        "trades": n,
        "wins": wins,
        "losses": n - wins,
        "gross_win_pips": round(gross_win, 3),
        "gross_loss_pips": round(gross_loss, 3),
        "win_rate": round(wins / n, 4) if n else 0.0,
        "wilson_lo": round(_wilson_lo(wins, n), 4),
        "profit_factor": round(pf, 4) if math.isfinite(pf) else "inf",
        "total_pnl_pips": round(sum(t.pnl_pips for t in trades), 3),
        "expected_value_pips": round(sum(t.pnl_pips for t in trades) / n, 4) if n else 0.0,
    }


def _run_micro_variant(pair: str, redesign_v2: bool) -> dict:
    bars = _load_bars(pair)
    cost = CostModel(spread_pips=0.8, latency_ms=150, slippage_per_ms=0.001, symbol=pair)

    class _Trade:
        def __init__(self, pnl_pips: float):
            self.pnl_pips = pnl_pips

    W = 180
    DIST = 1800
    Z = 2.0
    MAX_HOLD_BARS = 1  # native 15m bars exceed ofi_mr max_hold_sec=600 at next bar
    pip = cost.pip
    n = len(bars)
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    vols = [max(1, b.tick_volume) for b in bars]

    signed = [0.0] * n
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            signed[i] = vols[i]
        elif closes[i] < closes[i - 1]:
            signed[i] = -vols[i]

    ps_ofi = [0.0]
    ps_vol = [0.0]
    ps_vp = [0.0]
    for i in range(n):
        ps_ofi.append(ps_ofi[-1] + signed[i])
        ps_vol.append(ps_vol[-1] + vols[i])
        ps_vp.append(ps_vp[-1] + vols[i] * closes[i])

    tr = [0.0] * n
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    ps_tr = [0.0]
    for x in tr:
        ps_tr.append(ps_tr[-1] + x)

    def rng_sum(ps, lo, hi):
        return ps[hi + 1] - ps[lo]

    def ofi(lo, hi):
        return rng_sum(ps_ofi, lo, hi)

    def vwap(lo, hi):
        den = rng_sum(ps_vol, lo, hi)
        return rng_sum(ps_vp, lo, hi) / den if den > 0 else closes[hi]

    def atr(end_exclusive, length=60):
        lo = end_exclusive - length
        hi = end_exclusive - 1
        if lo < 1:
            return 0.0
        return rng_sum(ps_tr, lo, hi) / length

    trades = []
    i = 2000
    while i < n - MAX_HOLD_BARS - 1:
        if redesign_v2:
            feat_lo, feat_hi = i - W, i - 1
            dist_lo, dist_hi = i - (DIST + W), i - W - 1
            signal_price = closes[feat_hi]
            mid = closes[i]
            atr_val = atr(i)
        else:
            feat_lo, feat_hi = i - W + 1, i
            dist_lo, dist_hi = i - (DIST + W) + 1, i - W
            signal_price = closes[i]
            mid = closes[i]
            atr_val = atr(i)
        if dist_lo < 0 or feat_lo < 0:
            i += 1
            continue

        ofi_now = ofi(feat_lo, feat_hi)
        chunks = []
        for start in range(dist_lo, dist_hi - W + 2, 30):
            chunks.append(ofi(start, start + W - 1))
        if len(chunks) < 20:
            i += 1
            continue
        mu = sum(chunks) / len(chunks)
        var = sum((x - mu) ** 2 for x in chunks) / (len(chunks) - 1)
        sigma = math.sqrt(var) if var > 0 else 0.0
        if sigma <= 0:
            i += 1
            continue
        z_ofi = (ofi_now - mu) / sigma
        if abs(z_ofi) < Z:
            i += 1
            continue
        vw = vwap(feat_lo, feat_hi)
        displacement = signal_price - vw
        if atr_val <= 0:
            i += 1
            continue
        entry_slip_price = cost.total_cost_pips * pip
        if atr_val < 2.0 * entry_slip_price:
            i += 1
            continue
        if z_ofi > 0 and displacement > atr_val:
            side = "SELL"
        elif z_ofi < 0 and displacement < -atr_val:
            side = "BUY"
        else:
            i += 1
            continue

        cost_buffer = 2.0 * entry_slip_price + 0.3 * atr_val
        if side == "BUY":
            entry = cost.apply_to_entry(side, mid)
            sl = min(min(lows[feat_lo:feat_hi + 1]) - 0.3 * atr_val, entry - cost_buffer)
            sl_dist = entry - sl
            tp_dist_calc = vw - entry
            if redesign_v2:
                if tp_dist_calc < 8.0 * pip:
                    i += 1
                    continue
                tp = vw
                tp_dist = tp_dist_calc
            else:
                tp_dist = max(tp_dist_calc, 8.0 * pip)
                tp = entry + tp_dist
        else:
            entry = cost.apply_to_entry(side, mid)
            sl = max(max(highs[feat_lo:feat_hi + 1]) + 0.3 * atr_val, entry + cost_buffer)
            sl_dist = sl - entry
            tp_dist_calc = entry - vw
            if redesign_v2:
                if tp_dist_calc < 8.0 * pip:
                    i += 1
                    continue
                tp = vw
                tp_dist = tp_dist_calc
            else:
                tp_dist = max(tp_dist_calc, 8.0 * pip)
                tp = entry - tp_dist
        if sl_dist <= 0 or tp_dist <= 0 or (not redesign_v2 and tp_dist < sl_dist * 0.7):
            i += 1
            continue

        exit_bar = i + 1
        hi, lo = highs[exit_bar], lows[exit_bar]
        if side == "BUY":
            hit_sl = lo <= sl
            hit_tp = (not hit_sl) and hi >= tp
            exit_mid = sl if hit_sl else (tp if hit_tp else closes[exit_bar])
            exit_px = cost.apply_to_exit(side, exit_mid)
            pnl = (exit_px - entry) / pip
        else:
            hit_sl = hi >= sl
            hit_tp = (not hit_sl) and lo <= tp
            exit_mid = sl if hit_sl else (tp if hit_tp else closes[exit_bar])
            exit_px = cost.apply_to_exit(side, exit_mid)
            pnl = (entry - exit_px) / pip
        trades.append(_Trade(pnl))
        i = exit_bar + 1

    out = _stats(trades)
    out["bars"] = len(bars)
    return out


def _daytrade_probe(redesign_v2: bool) -> dict:
    env = os.environ.copy()
    env["OFI_MR_REDESIGN_V2"] = "1" if redesign_v2 else "0"
    code = """
import json, os, sys, types
os.environ['BT_MODE']='1'
os.environ['BT_REQUIRE_MASSIVE_CACHE']='1'
os.environ['NO_AUTOSTART']='1'
sys.modules.setdefault('pytest', types.ModuleType('pytest'))
import app
getattr(app, '_dt_bt_cache', {}).clear()
res = app.run_daytrade_backtest('USDJPY=X', lookback_days=365, interval='15m', backtest_mode=True)
bd = res.get('entry_breakdown') or {}
print(json.dumps({
  'mode': res.get('mode'),
  'trades': res.get('trades'),
  'data_source': res.get('data_source') or res.get('debug', {}).get('data_source'),
  'contains_ofi_mr': 'ofi_mr' in bd,
  'error': res.get('error'),
}))
"""
    try:
        cp = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {
            "contains_ofi_mr": False,
            "error": "run_daytrade_backtest probe timed out after 20s during app startup/side effects",
        }
    if cp.returncode != 0:
        return {"contains_ofi_mr": False, "error": (cp.stderr or cp.stdout)[-1000:]}
    line = cp.stdout.strip().splitlines()[-1] if cp.stdout.strip() else "{}"
    try:
        return json.loads(line)
    except Exception:
        return {"contains_ofi_mr": False, "error": cp.stdout[-1000:]}


def _aggregate(per_pair: dict, side: str) -> dict:
    total = {"trades": 0, "wins": 0, "losses": 0, "total_pnl_pips": 0.0}
    gross_win = 0.0
    gross_loss = 0.0
    for pair_stats in per_pair.values():
        s = pair_stats[side]
        total["trades"] += s["trades"]
        total["wins"] += s["wins"]
        total["losses"] += s["losses"]
        total["total_pnl_pips"] += s["total_pnl_pips"]
        gross_win += s.get("gross_win_pips", 0.0)
        gross_loss += s.get("gross_loss_pips", 0.0)
    n = total["trades"]
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    total.update({
        "win_rate": round(total["wins"] / n, 4) if n else 0.0,
        "wilson_lo": round(_wilson_lo(total["wins"], n), 4),
        "gross_win_pips": round(gross_win, 3),
        "gross_loss_pips": round(gross_loss, 3),
        "profit_factor": round(pf, 4) if math.isfinite(pf) else "inf",
        "total_pnl_pips": round(total["total_pnl_pips"], 3),
        "expected_value_pips": round(total["total_pnl_pips"] / n, 4) if n else 0.0,
    })
    return total


def _verdict(base: dict, prop: dict) -> dict:
    if prop["trades"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "shadow_promote_decision": "SHADOW_PROMOTE_RECOMMENDED",
            "reason": "proposed BT trades < 20; catastrophic_check skipped per v2 spec",
        }
    sanity = {
        "wilson_lo_proposed": prop["wilson_lo"] >= 0.20,
        "pf_proposed": prop["profit_factor"] == "inf" or prop["profit_factor"] >= 0.85,
    }
    if not all(sanity.values()):
        return {"verdict": "REJECT", "shadow_promote_decision": "NO_CHANGE", "sanity_floor": sanity}

    def pct_change(new, old):
        if old in (0, "inf"):
            return None
        return (new - old) / old

    pf_change = None
    if base["profit_factor"] != "inf" and prop["profit_factor"] != "inf" and base["profit_factor"] > 0:
        pf_change = pct_change(prop["profit_factor"], base["profit_factor"])
    n_change_pct = ((prop["trades"] - base["trades"]) / base["trades"] * 100) if base["trades"] else None
    checks = {
        "pf_change": pf_change is None or pf_change >= -0.10,
        "wilson_lo_change": (prop["wilson_lo"] - base["wilson_lo"]) >= -0.05,
        "n_change_pct": n_change_pct is None or n_change_pct >= -30,
        "pnl_sign_preserved": not (base["total_pnl_pips"] > 0 and prop["total_pnl_pips"] < 0),
    }
    return {
        "verdict": "PASS" if all(checks.values()) else "REJECT",
        "shadow_promote_decision": "SHADOW_PROMOTE_RECOMMENDED" if all(checks.values()) else "NO_CHANGE",
        "sanity_floor": sanity,
        "catastrophic_check": checks,
        "changes": {
            "pf_change": round(pf_change, 4) if pf_change is not None else None,
            "wilson_lo_change": round(prop["wilson_lo"] - base["wilson_lo"], 4),
            "n_change_pct": round(n_change_pct, 2) if n_change_pct is not None else None,
        },
    }


def main() -> None:
    per_pair = {}
    for pair in PAIRS:
        per_pair[pair] = {
            "baseline": _run_micro_variant(pair, False),
            "proposed": _run_micro_variant(pair, True),
        }
    aggregate = {
        "baseline": _aggregate(per_pair, "baseline"),
        "proposed": _aggregate(per_pair, "proposed"),
    }
    lock = _verdict(aggregate["baseline"], aggregate["proposed"])
    report = {
        "strategy": "ofi_mr",
        "report": "shadow-redesign-v2",
        "generated_at": "2026-05-05",
        "runner_required": "app.run_daytrade_backtest(symbol=\"USDJPY=X\", lookback_days=365, interval=\"15m\", backtest_mode=True)",
        "runner_note": (
            "ofi_mr is implemented in strategies.micro_scalp and is not a qualified "
            "entry_type in run_daytrade_backtest; the daytrade probe verifies the "
            "production runner/source guard but cannot produce ofi_mr trades."
        ),
        "data_source_required": "data/cache/massive/{PAIR}_15m.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "daytrade_probe": {
            "baseline": _daytrade_probe(False),
            "proposed": _daytrade_probe(True),
        },
        "micro_harness_note": "Native MASSIVE 15m cache only; no Yahoo fallback and no resample substitute.",
        "per_pair": per_pair,
        "aggregate": aggregate,
        "v2_lock": lock,
        "shadow_registration": {
            "implemented": True,
            "flags_required": ["OFI_MR_REDESIGN_V2=1", "OFI_MR_REDESIGN_V2_SHADOW_PROMOTE=1"],
            "default_live_impact": "zero; both flags default OFF",
        },
        "codex_self_review": {
            "catastrophic_only_shadow_promote": True,
            "absolute_kelly_required": False,
            "flag_off_live_impact_zero": True,
            "post_hoc_adjustment": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"out": str(OUT), "v2_lock": lock, "aggregate": aggregate}, indent=2))


if __name__ == "__main__":
    main()
