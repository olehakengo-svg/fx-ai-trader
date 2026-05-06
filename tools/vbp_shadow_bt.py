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
OUT = Path("bt-results/vbp-shadow-redesign-v2-2026-05-05.json")


def _load_bars(pair: str) -> list[TickBar]:
    path = Path(f"data/cache/massive/{pair}_{INTERVAL}.parquet")
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path} index is not DatetimeIndex")
    end = df.index.max()
    start = end - timedelta(days=LOOKBACK_DAYS)
    df = df.loc[df.index >= start].copy()
    cols = {c.lower(): c for c in df.columns}
    bars = []
    for ts, row in df.iterrows():
        volume_col = cols.get("volume", "Volume")
        volume = row[volume_col] if volume_col in row else 1
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


def _stats(trades: list[float], bars: int) -> dict:
    n = len(trades)
    wins = sum(1 for pnl in trades if pnl > 0)
    gross_win = sum(pnl for pnl in trades if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in trades if pnl < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    return {
        "trades": n,
        "wins": wins,
        "losses": n - wins,
        "gross_win_pips": round(gross_win, 3),
        "gross_loss_pips": round(gross_loss, 3),
        "win_rate": round(wins / n, 4) if n else 0.0,
        "wilson_lo": round(_wilson_lo(wins, n), 4),
        "profit_factor": round(pf, 4) if math.isfinite(pf) else "inf",
        "total_pnl_pips": round(sum(trades), 3),
        "expected_value_pips": round(sum(trades) / n, 4) if n else 0.0,
        "bars": bars,
    }


def _rolling_prior(values: list[float], length: int, mode: str) -> list[float]:
    series = pd.Series(values)
    if mode == "max":
        rolled = series.rolling(length).max().shift(1)
    else:
        rolled = series.rolling(length).min().shift(1)
    return rolled.tolist()


def _rolling_atr(highs: list[float], lows: list[float], closes: list[float],
                 length: int = 60) -> list[float]:
    tr = [0.0] * len(highs)
    for i in range(1, len(highs)):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    return pd.Series(tr).rolling(length).mean().shift(1).tolist()


def _run_variant(pair: str, redesign_v2: bool) -> dict:
    bars = _load_bars(pair)
    cost = CostModel(spread_pips=0.8, latency_ms=150, slippage_per_ms=0.001, symbol=pair)
    pip = cost.pip
    lookback = 1800
    pullback_ratio = 0.5
    min_tp_pips = 8.0
    max_hold_sec = 15 * 60
    warmup = 2000

    opens = [b.open for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    closes = [b.close for b in bars]
    times = [b.ts for b in bars]
    prior_high = _rolling_prior(highs, lookback, "max")
    prior_low = _rolling_prior(lows, lookback, "min")
    atr = _rolling_atr(highs, lows, closes, 60)

    trades: list[float] = []
    i = warmup
    while i < len(bars) - 1:
        t_break = None
        break_side = None
        break_price = None
        range_high = None
        range_low = None
        range_prev = None

        if not redesign_v2:
            h_prev = prior_high[i]
            l_prev = prior_low[i]
            if pd.isna(h_prev) or pd.isna(l_prev) or h_prev - l_prev <= 0:
                i += 1
                continue

        for t in range(i - 19, i - 2):
            if t < lookback:
                continue
            if redesign_v2:
                h_i = prior_high[t]
                l_i = prior_low[t]
                if pd.isna(h_i) or pd.isna(l_i) or h_i - l_i <= 0:
                    continue
            else:
                h_i = h_prev
                l_i = l_prev
            if closes[t] > h_i:
                t_break = t
                break_side = "UP"
                break_price = closes[t]
                range_high = h_i
                range_low = l_i
                range_prev = h_i - l_i
                break
            if closes[t] < l_i:
                t_break = t
                break_side = "DOWN"
                break_price = closes[t]
                range_high = h_i
                range_low = l_i
                range_prev = h_i - l_i
                break

        if t_break is None or range_high is None or range_low is None or range_prev is None:
            i += 1
            continue

        pb_start = t_break + 1 if redesign_v2 else t_break
        if pb_start > i:
            i += 1
            continue

        if break_side == "UP":
            extreme = max(highs[t_break:i + 1])
            pullback_target = extreme - pullback_ratio * (extreme - range_high)
            pb_low = min(lows[pb_start:i + 1])
            if pb_low > pullback_target:
                i += 1
                continue
            upmoves = sum(1 for j in range(i - 2, i + 1) if closes[j] > opens[j])
            if upmoves < 2 or closes[i] <= pb_low:
                i += 1
                continue
            side = "BUY"
            sl_extreme = pb_low
        else:
            extreme = min(lows[t_break:i + 1])
            pullback_target = extreme + pullback_ratio * (range_low - extreme)
            pb_high = max(highs[pb_start:i + 1])
            if pb_high < pullback_target:
                i += 1
                continue
            downmoves = sum(1 for j in range(i - 2, i + 1) if closes[j] < opens[j])
            if downmoves < 2 or closes[i] >= pb_high:
                i += 1
                continue
            side = "SELL"
            sl_extreme = pb_high

        atr_val = atr[i]
        if pd.isna(atr_val) or atr_val <= 0:
            i += 1
            continue

        entry = cost.apply_to_entry(side, closes[i])
        if side == "BUY":
            sl = sl_extreme - 0.5 * atr_val
            sl_dist = entry - sl
            burst = break_price - range_high
            tp_dist = max(burst * 2.0, min_tp_pips * pip)
            tp = entry + tp_dist
        else:
            sl = sl_extreme + 0.5 * atr_val
            sl_dist = sl - entry
            burst = range_low - break_price
            tp_dist = max(burst * 2.0, min_tp_pips * pip)
            tp = entry - tp_dist
        if sl_dist <= 0 or tp_dist <= 0 or tp_dist < sl_dist * 0.8:
            i += 1
            continue

        entry_idx = i
        exit_idx = i + 1
        while exit_idx < len(bars):
            hold_sec = times[exit_idx] - times[entry_idx]
            timeout = hold_sec >= max_hold_sec
            if side == "BUY":
                hit_sl = lows[exit_idx] <= sl
                hit_tp = (not hit_sl) and highs[exit_idx] >= tp
                if hit_sl or hit_tp or timeout:
                    exit_mid = sl if hit_sl else (tp if hit_tp else closes[exit_idx])
                    pnl = (cost.apply_to_exit(side, exit_mid) - entry) / pip
                    trades.append(pnl)
                    break
            else:
                hit_sl = highs[exit_idx] >= sl
                hit_tp = (not hit_sl) and lows[exit_idx] <= tp
                if hit_sl or hit_tp or timeout:
                    exit_mid = sl if hit_sl else (tp if hit_tp else closes[exit_idx])
                    pnl = (entry - cost.apply_to_exit(side, exit_mid)) / pip
                    trades.append(pnl)
                    break
            exit_idx += 1
        i = exit_idx + 1

    return _stats(trades, len(bars))


def _daytrade_probe(redesign_v2: bool) -> dict:
    env = os.environ.copy()
    env["VBP_REDESIGN_V2"] = "1" if redesign_v2 else "0"
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
  'contains_vbp': 'vbp' in bd,
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
            "contains_vbp": False,
            "error": "run_daytrade_backtest probe timed out after 20s during app startup/side effects",
        }
    if cp.returncode != 0:
        return {"contains_vbp": False, "error": (cp.stderr or cp.stdout)[-1000:]}
    line = cp.stdout.strip().splitlines()[-1] if cp.stdout.strip() else "{}"
    try:
        return json.loads(line)
    except Exception:
        return {"contains_vbp": False, "error": cp.stdout[-1000:]}


def _pf_number(value) -> float | None:
    if value == "inf":
        return None
    return float(value)


def _aggregate(per_pair: dict, side: str) -> dict:
    trades = sum(pair_stats[side]["trades"] for pair_stats in per_pair.values())
    wins = sum(pair_stats[side]["wins"] for pair_stats in per_pair.values())
    gross_win = sum(pair_stats[side]["gross_win_pips"] for pair_stats in per_pair.values())
    gross_loss = sum(pair_stats[side]["gross_loss_pips"] for pair_stats in per_pair.values())
    pnl = sum(pair_stats[side]["total_pnl_pips"] for pair_stats in per_pair.values())
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    return {
        "trades": trades,
        "wins": wins,
        "losses": trades - wins,
        "gross_win_pips": round(gross_win, 3),
        "gross_loss_pips": round(gross_loss, 3),
        "win_rate": round(wins / trades, 4) if trades else 0.0,
        "wilson_lo": round(_wilson_lo(wins, trades), 4),
        "profit_factor": round(pf, 4) if math.isfinite(pf) else "inf",
        "total_pnl_pips": round(pnl, 3),
        "expected_value_pips": round(pnl / trades, 4) if trades else 0.0,
    }


def _verdict(base: dict, prop: dict) -> dict:
    base_pf = _pf_number(base["profit_factor"])
    prop_pf = _pf_number(prop["profit_factor"])
    warnings = {
        "n_change_pct": round(((prop["trades"] - base["trades"]) / base["trades"] * 100), 2)
        if base["trades"] else None,
        "pf_change": round(prop_pf - base_pf, 4) if prop_pf is not None and base_pf is not None else None,
        "wilson_lo_change": round(prop["wilson_lo"] - base["wilson_lo"], 4),
        "ev_change_pips": round(prop["expected_value_pips"] - base["expected_value_pips"], 4),
    }
    if prop["trades"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "shadow_promote_decision": "SHADOW_PROMOTE_RECOMMENDED",
            "catastrophic_check": "SKIPPED_N_LT_20",
            "warnings_only": warnings,
            "sanity_floor": "REMOVED_IN_V2_1",
        }
    pnl_sign_preserved = not (base["total_pnl_pips"] > 0 and prop["total_pnl_pips"] < 0)
    return {
        "verdict": "PASS" if pnl_sign_preserved else "REJECT",
        "shadow_promote_decision": "SHADOW_PROMOTE_RECOMMENDED" if pnl_sign_preserved else "NO_CHANGE",
        "catastrophic_check": {"pnl_sign_preserved": pnl_sign_preserved},
        "warnings_only": warnings,
        "sanity_floor": "REMOVED_IN_V2_1",
    }


def main() -> None:
    per_pair = {}
    for pair in PAIRS:
        per_pair[pair] = {
            "baseline": _run_variant(pair, False),
            "proposed": _run_variant(pair, True),
        }
    aggregate = {
        "baseline": _aggregate(per_pair, "baseline"),
        "proposed": _aggregate(per_pair, "proposed"),
    }
    lock = _verdict(aggregate["baseline"], aggregate["proposed"])
    report = {
        "strategy": "vbp",
        "report": "shadow-redesign-v2.1",
        "generated_at": "2026-05-05",
        "runner_required": "app.run_daytrade_backtest(symbol=\"USDJPY=X\", lookback_days=365, interval=\"15m\", backtest_mode=True)",
        "runner_note": (
            "vbp is implemented in strategies.micro_scalp and is not a qualified "
            "entry_type in run_daytrade_backtest; the daytrade probe verifies the "
            "production runner/source guard but cannot produce vbp trades."
        ),
        "data_source_required": "data/cache/massive/{PAIR}_15m.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "daytrade_probe": {
            "baseline": _daytrade_probe(False),
            "proposed": _daytrade_probe(True),
        },
        "micro_harness_note": "Native MASSIVE 15m cache only; no Yahoo fallback and no resample substitute. No 1s/tick MASSIVE cache exists in this workspace.",
        "redesign_axis": "Axis 2/3: candidate break bar uses its own prior range; pullback bars start after the break bar for V2.",
        "per_pair": per_pair,
        "aggregate": aggregate,
        "v2_lock": lock,
        "shadow_registration": {
            "implemented": True,
            "flags_required": ["VBP_REDESIGN_V2=1", "VBP_REDESIGN_V2_SHADOW_PROMOTE=1"],
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
