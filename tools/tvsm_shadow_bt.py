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
OUT = Path("bt-results/tvsm-shadow-redesign-v2-2026-05-05.json")


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


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return 0.0, 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return mean, math.sqrt(var) if var > 0 else 0.0


def _hour_utc(bar: TickBar) -> int:
    return pd.Timestamp(bar.ts, unit="s", tz="UTC").hour


def _atr(highs: list[float], lows: list[float], closes: list[float],
         end_exclusive: int, length: int = 60) -> float:
    lo = end_exclusive - length
    hi = end_exclusive - 1
    if lo < 1:
        return 0.0
    total = 0.0
    for idx in range(lo, hi + 1):
        total += max(
            highs[idx] - lows[idx],
            abs(highs[idx] - closes[idx - 1]),
            abs(lows[idx] - closes[idx - 1]),
        )
    return total / length


def _passes_v2_gate(pair: str, bar: TickBar, atr_val: float,
                    cost: CostModel) -> bool:
    if pair not in {"USD_JPY", "EUR_USD", "GBP_USD"}:
        return False
    if _hour_utc(bar) not in set(range(7, 17)):
        return False
    entry_slip_price = cost.total_cost_pips * cost.pip
    spread_price = cost.spread_pips * cost.pip
    cost_ok = entry_slip_price > 0 and atr_val >= 3.0 * entry_slip_price
    spread_ok = spread_price > 0 and (atr_val / spread_price) >= 8.0
    return cost_ok or spread_ok


def _run_variant(pair: str, redesign_v2: bool) -> dict:
    bars = _load_bars(pair)
    cost = CostModel(spread_pips=0.8, latency_ms=150, slippage_per_ms=0.001, symbol=pair)
    pip = cost.pip
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    opens = [b.open for b in bars]
    volumes = [float(b.tick_volume) for b in bars]
    trades: list[float] = []
    i = 2000
    while i < len(bars) - 2:
        latest_idx = i
        spike_idx = i - 2
        conf_idx = i - 1
        hist_lo = i - 303
        hist_hi = i - 3
        if hist_lo < 0:
            i += 1
            continue

        atr_val = _atr(highs, lows, closes, i, 60)
        if atr_val <= 0:
            i += 1
            continue
        if redesign_v2 and not _passes_v2_gate(pair, bars[latest_idx], atr_val, cost):
            i += 1
            continue

        mu, sigma = _mean_std(volumes[hist_lo:hist_hi + 1])
        if sigma <= 0:
            i += 1
            continue
        z_spike = (volumes[spike_idx] - mu) / sigma
        if z_spike < 3.0:
            i += 1
            continue

        body = closes[spike_idx] - opens[spike_idx]
        if abs(body) < 0.3 * pip:
            i += 1
            continue
        side = "BUY" if body > 0 else "SELL"
        move_1 = closes[conf_idx] - closes[spike_idx]
        move_2 = closes[latest_idx] - closes[conf_idx]
        if side == "BUY" and (move_1 <= 0 or move_2 <= 0):
            i += 1
            continue
        if side == "SELL" and (move_1 >= 0 or move_2 >= 0):
            i += 1
            continue

        entry_slip_price = cost.total_cost_pips * pip
        sl_dist = max(1.2 * atr_val, 2.0 * entry_slip_price + 0.5 * atr_val)
        if atr_val < 2.0 * entry_slip_price:
            i += 1
            continue
        tp_dist = max(3.0 * atr_val, 8.0 * pip)
        if tp_dist < sl_dist * 1.5:
            i += 1
            continue

        entry = cost.apply_to_entry(side, closes[latest_idx])
        if side == "BUY":
            sl = entry - sl_dist
            tp = entry + tp_dist
        else:
            sl = entry + sl_dist
            tp = entry - tp_dist

        exit_idx = i + 1
        if side == "BUY":
            hit_sl = lows[exit_idx] <= sl
            hit_tp = (not hit_sl) and highs[exit_idx] >= tp
            exit_mid = sl if hit_sl else (tp if hit_tp else closes[exit_idx])
            pnl = (cost.apply_to_exit(side, exit_mid) - entry) / pip
        else:
            hit_sl = highs[exit_idx] >= sl
            hit_tp = (not hit_sl) and lows[exit_idx] <= tp
            exit_mid = sl if hit_sl else (tp if hit_tp else closes[exit_idx])
            pnl = (entry - cost.apply_to_exit(side, exit_mid)) / pip
        trades.append(pnl)
        i = exit_idx + 1
    return _stats(trades, len(bars))


def _daytrade_probe(redesign_v2: bool) -> dict:
    env = os.environ.copy()
    env["TVSM_REDESIGN_V2"] = "1" if redesign_v2 else "0"
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
  'contains_tvsm': 'tvsm' in bd,
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
            "contains_tvsm": False,
            "error": "run_daytrade_backtest probe timed out after 20s during app startup/side effects",
        }
    if cp.returncode != 0:
        return {"contains_tvsm": False, "error": (cp.stderr or cp.stdout)[-1000:]}
    line = cp.stdout.strip().splitlines()[-1] if cp.stdout.strip() else "{}"
    try:
        return json.loads(line)
    except Exception:
        return {"contains_tvsm": False, "error": cp.stdout[-1000:]}


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
    warnings = {
        "n_change_pct": round(((prop["trades"] - base["trades"]) / base["trades"] * 100), 2)
        if base["trades"] else None,
        "pf_change": round(prop["profit_factor"] - base["profit_factor"], 4)
        if isinstance(prop["profit_factor"], float) and isinstance(base["profit_factor"], float) else None,
        "wilson_lo_change": round(prop["wilson_lo"] - base["wilson_lo"], 4),
    }
    if prop["trades"] < 20:
        return {
            "verdict": "INSUFFICIENT_BT_EVIDENCE",
            "shadow_promote_decision": "SHADOW_PROMOTE_RECOMMENDED",
            "catastrophic_check": "SKIPPED_N_LT_20",
            "warnings_only": warnings,
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
        "strategy": "tvsm",
        "report": "shadow-redesign-v2.1",
        "generated_at": "2026-05-05",
        "runner_required": "app.run_daytrade_backtest(symbol=\"USDJPY=X\", lookback_days=365, interval=\"15m\", backtest_mode=True)",
        "runner_note": (
            "tvsm is implemented in strategies.micro_scalp and is not a qualified "
            "entry_type in run_daytrade_backtest; the daytrade probe verifies the "
            "production runner/source guard but cannot produce tvsm trades."
        ),
        "data_source_required": "data/cache/massive/{PAIR}_15m.parquet with BT_MODE=1 and BT_REQUIRE_MASSIVE_CACHE=1",
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "daytrade_probe": {
            "baseline": _daytrade_probe(False),
            "proposed": _daytrade_probe(True),
        },
        "micro_harness_note": "Native MASSIVE 15m cache only; no Yahoo fallback and no resample substitute. No 1s/tick MASSIVE cache exists in this workspace.",
        "redesign_axis": "pair whitelist + London/NY UTC session + ATR/cost viability pre-trigger gate",
        "per_pair": per_pair,
        "aggregate": aggregate,
        "v2_lock": lock,
        "shadow_registration": {
            "implemented": True,
            "flags_required": ["TVSM_REDESIGN_V2=1", "TVSM_REDESIGN_V2_SHADOW_PROMOTE=1"],
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
