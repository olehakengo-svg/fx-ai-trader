#!/usr/bin/env python3
"""Regime-gate Phase B2.5 full-family BT artifact generator."""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("BT_REQUIRE_MASSIVE_CACHE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.regime_classifier import classify_regime


PAIRS = ("USDJPY=X", "EURUSD=X", "GBPUSD=X")
LOOKBACK = 365
INTERVAL = "15m"
REGIMES = ("TRENDING", "RANGING", "CHOP")
CONDITIONS = ("baseline", "gated_TRENDING", "gated_RANGING", "gated_CHOP")
OUT_DIR = ROOT / "reports" / "regime_gate_phase_b2"

ALL_FAMILIES = (
    "sr_fib_confluence",
    "ema_cross",
    "htf_false_breakout",
    "london_session_breakout",
    "tokyo_nakane_momentum",
    "adx_trend_continuation",
    "sr_break_retest",
    "lin_reg_channel",
    "orb_trap",
    "london_close_reversal",
    "london_close_reversal_v2",
    "gbp_deep_pullback",
    "turtle_soup",
    "trendline_sweep",
    "inducement_ob",
    "dual_sr_bounce",
    "london_ny_swing",
    "gold_vol_break",
    "jpy_basket_trend",
    "squeeze_release_momentum",
    "eurgbp_daily_mr",
    "dt_bb_rsi_mr",
    "gold_trend_momentum",
    "liquidity_sweep",
    "session_time_bias",
    "gotobi_fix",
    "london_fix_reversal",
    "vix_carry_unwind",
    "xs_momentum",
    "hmm_regime_filter",
    "vol_spike_mr",
    "doji_breakout",
    "dt_fib_reversal",
    "dt_sr_channel_reversal",
    "ema200_trend_reversal",
    "post_news_vol",
    "ny_close_reversal",
    "streak_reversal",
    "vwap_mean_reversion",
    "intraday_seasonality",
    "wick_imbalance_reversion",
    "atr_regime_break",
    "tokyo_range_breakout_up",
    "pullback_to_liquidity_v1",
    "asia_range_fade_v1",
    "sr_anti_hunt_bounce",
    "sr_liquidity_grab",
    "cpd_divergence",
    "vdr_jpy",
    "vsg_jpy_reversal",
    "rsk_gbpjpy_reversion",
    "mqe_gbpusd_fix",
    "pd_eurjpy_h20_bbpb3_sell",
    "bb_rsi_reversion",
    "bb_rsi_ema_aligned",
    "bb_squeeze_breakout",
    "engulfing_bb",
    "london_breakout",
    "ma_regime_switch",
    "mtf_reversal_confluence",
    "mtf_regime_trend_cascade_scalp",
    "mtf_regime_range_cascade_scalp",
    "stoch_trend_pullback",
    "three_bar_reversal",
    "trend_rebound",
    "vol_momentum_scalp",
)


@dataclass
class OutputTables:
    kpi_rows: list[dict]
    sanity_rows: list[dict]
    shadow_proposals: list[dict]
    zero_trade_families: list[dict]


def pair_key(symbol: str) -> str:
    value = symbol.upper().replace("/", "_").replace("-", "_")
    if value.endswith("=X"):
        value = value[:-2]
    value = value.replace("_", "")
    if len(value) == 6:
        return f"{value[:3]}{value[3:]}"
    return value


def pair_cache_key(symbol: str) -> str:
    value = pair_key(symbol)
    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def _parse_time(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def trade_pnl(trade: dict) -> float:
    for key in ("pnl_m", "pnl", "r_multiple"):
        if key in trade and trade[key] is not None:
            return float(trade[key])
    friction = float(trade.get("exit_friction_m", 0) or 0)
    if trade.get("outcome") == "WIN":
        return float(trade.get("tp_m", 0) or 0) - friction
    if trade.get("outcome") == "LOSS":
        loss = trade.get("actual_sl_m", trade.get("sl_m", 0))
        return -(float(loss or 0) + friction)
    return 0.0


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def _profit_factor(pnls: list[float]) -> float:
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _kelly(pnls: list[float]) -> float:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    n = len(pnls)
    if n == 0 or not wins or not losses:
        return 0.0
    p = len(wins) / n
    b = (sum(wins) / len(wins)) / max(sum(losses) / len(losses), 1e-12)
    return p - ((1 - p) / b)


def _finite(value: float) -> str | float:
    if math.isinf(value):
        return "inf"
    if math.isnan(value):
        return "nan"
    return round(value, 6)


def compute_kpi(trades: Iterable[dict]) -> dict:
    rows = list(trades)
    pnls = [trade_pnl(t) for t in rows]
    n = len(rows)
    wins = sum(1 for p in pnls if p > 0)
    pnl = sum(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 6) if n else 0.0,
        "EV_pip": round(pnl / n, 6) if n else 0.0,
        "PnL": round(pnl, 6),
        "PF": _finite(_profit_factor(pnls)),
        "Wilson_lo": round(_wilson_lower(wins, n), 6),
        "Kelly": round(_kelly(pnls), 6),
    }


def _pf_as_float(value) -> float:
    if value == "inf":
        return float("inf")
    return float(value)


def catastrophic_verdict(baseline: dict, gate: dict) -> tuple[str, str]:
    if baseline["PnL"] <= 0:
        return "CATASTROPHIC", "baseline_negative_no_edge"
    if (baseline["PnL"] > 0 and gate["PnL"] < 0) or (baseline["PnL"] < 0 and gate["PnL"] > 0):
        return "CATASTROPHIC", "pnl_sign_flip"
    if gate["N"] < 30:
        return "CATASTROPHIC", "gate_N_lt_30"
    if _pf_as_float(gate["PF"]) < 0.50 and _pf_as_float(baseline["PF"]) > 0.80:
        return "CATASTROPHIC", "pf_extreme_drop"
    return "NOT_CATASTROPHIC", "not_catastrophic"


def run_pair_bt(symbol: str, lookback_days: int = LOOKBACK) -> dict:
    import app

    if hasattr(app, "_dt_bt_cache"):
        app._dt_bt_cache.clear()
    try:
        import modules.data as data_mod

        if hasattr(data_mod, "_data_cache"):
            data_mod._data_cache.clear()
    except Exception:
        pass
    return app.run_daytrade_backtest(symbol, lookback_days=lookback_days, interval=INTERVAL)


def tag_trades(
    symbol: str,
    trades: Iterable[dict],
    classifier: Callable[[str, pd.Timestamp], str | None] = classify_regime,
) -> list[dict]:
    pair = pair_key(symbol)
    tagged = []
    for idx, trade in enumerate(trades):
        instrument = trade.get("instrument") or trade.get("symbol") or trade.get("pair") or symbol
        if "XAU" in str(instrument).upper():
            continue
        row = dict(trade)
        row["pair"] = pair
        row["source_symbol"] = symbol
        row["trade_id"] = f"{pair}-{idx}"
        entry_time = row.get("entry_time")
        regime = None
        if entry_time:
            regime = classifier(symbol, _parse_time(entry_time))
        row["regime"] = regime or "UNKNOWN"
        row["pnl_m"] = round(trade_pnl(row), 6)
        tagged.append(row)
    return tagged


def _trades_for(trades: list[dict], family: str, regime: str | None = None) -> list[dict]:
    rows = [t for t in trades if t.get("entry_type") == family]
    if regime is not None:
        rows = [t for t in rows if t.get("regime") == regime]
    return rows


def build_output_tables(trades: list[dict], family_universe: Iterable[str] = ALL_FAMILIES) -> OutputTables:
    observed = {str(t.get("entry_type")) for t in trades if t.get("entry_type")}
    families = sorted(set(family_universe) | observed)
    kpi_rows: list[dict] = []
    sanity_rows: list[dict] = []
    proposals: list[dict] = []
    zero_rows: list[dict] = []

    for family in families:
        baseline_trades = _trades_for(trades, family)
        baseline = compute_kpi(baseline_trades)
        if baseline["N"] == 0:
            zero_rows.append({"entry_type": family, "N": 0})
        kpi_rows.append({"entry_type": family, "condition": "baseline", **baseline})

        for regime in REGIMES:
            gated = compute_kpi(_trades_for(trades, family, regime))
            condition = f"gated_{regime}"
            kpi_rows.append({"entry_type": family, "condition": condition, **gated})
            verdict, reason = catastrophic_verdict(baseline, gated)
            sanity_rows.append(
                {
                    "entry_type": family,
                    "gate": regime,
                    "verdict": verdict,
                    "reason": reason,
                    "baseline_N": baseline["N"],
                    "baseline_PnL": baseline["PnL"],
                    "baseline_PF": baseline["PF"],
                    "gate_N": gated["N"],
                    "gate_PnL": gated["PnL"],
                    "gate_PF": gated["PF"],
                }
            )
            if verdict == "NOT_CATASTROPHIC":
                proposals.append(
                    {
                        "proposal": f"{family}__regime_{regime}",
                        "entry_type": family,
                        "gate": regime,
                        "N": gated["N"],
                        "WR": gated["WR"],
                        "EV_pip": gated["EV_pip"],
                        "PF": gated["PF"],
                        "Wilson_lo": gated["Wilson_lo"],
                        "Kelly": gated["Kelly"],
                    }
                )

    return OutputTables(kpi_rows, sanity_rows, proposals, zero_rows)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    if not fieldnames:
        fieldnames = ["empty"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_artifacts(
    pair_results: dict[str, dict],
    tagged_trades: list[dict],
    outputs: OutputTables,
    out_dir: Path = OUT_DIR,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for symbol, result in pair_results.items():
        name = pair_key(symbol)
        path = out_dir / f"trade_log_baseline_{name}.csv"
        _write_csv(path, result.get("trade_log", []))
        written.append(path)

    tables = {
        "trade_log_tagged.csv": tagged_trades,
        "kpi_per_family_gate.csv": outputs.kpi_rows,
        "sanity_verdict.csv": outputs.sanity_rows,
        "shadow_proposals.csv": outputs.shadow_proposals,
        "zero_trade_families.csv": outputs.zero_trade_families,
    }
    for filename, rows in tables.items():
        path = out_dir / filename
        _write_csv(path, rows)
        written.append(path)

    summary = out_dir / "SUMMARY.md"
    summary.write_text(build_summary(pair_results, tagged_trades, outputs), encoding="utf-8")
    written.append(summary)
    return written


def _kpi_lookup(outputs: OutputTables, family: str, condition: str) -> dict | None:
    for row in outputs.kpi_rows:
        if row["entry_type"] == family and row["condition"] == condition:
            return row
    return None


def build_summary(pair_results: dict[str, dict], tagged_trades: list[dict], outputs: OutputTables) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    pair_counts = {pair_key(symbol): len(result.get("trade_log", [])) for symbol, result in pair_results.items()}
    family_count = len({row["entry_type"] for row in outputs.kpi_rows})
    observed_count = len({t.get("entry_type") for t in tagged_trades if t.get("entry_type")})
    zero_names = [row["entry_type"] for row in outputs.zero_trade_families]
    proposal_count = len(outputs.shadow_proposals)
    top = sorted(outputs.shadow_proposals, key=lambda r: (float(r["EV_pip"]), int(r["N"])), reverse=True)[:10]

    stoch_rows = {
        condition: _kpi_lookup(outputs, "stoch_trend_pullback", condition)
        for condition in CONDITIONS
    }
    stoch_lines = []
    for condition, row in stoch_rows.items():
        if row:
            stoch_lines.append(
                f"| {condition} | {row['N']} | {row['WR']:.3f} | {row['EV_pip']:+.3f} |"
            )
        else:
            stoch_lines.append(f"| {condition} | missing | missing | missing |")

    top_lines = [
        f"| {r['proposal']} | {r['N']} | {float(r['WR']):.3f} | {float(r['EV_pip']):+.3f} | {r['PF']} |"
        for r in top
    ]
    if not top_lines:
        top_lines = ["| none | 0 | 0.000 | +0.000 | 0 |"]

    zero_text = ", ".join(zero_names) if zero_names else "none"
    return "\n".join(
        [
            "# Regime-Gate Phase B2.5 Summary",
            "",
            f"- generated_at: {generated_at}",
            f"- data_source_required: MASSIVE parquet (`BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`)",
            f"- pair baseline trades: USDJPY={pair_counts.get('USDJPY', 0)}, EURUSD={pair_counts.get('EURUSD', 0)}, GBPUSD={pair_counts.get('GBPUSD', 0)}",
            f"- all family universe: {family_count}; observed BT families: {observed_count}",
            f"- zero-trade families: {zero_text}",
            f"- NOT_CATASTROPHIC proposals: {proposal_count}",
            "",
            "## Tier A Reproduction Benchmark",
            "",
            "| condition | N | WR | EV |",
            "|---|---:|---:|---:|",
            *stoch_lines,
            "",
            "Expected reference: baseline ~316 / WR ~60% / EV ~+0.01; TRENDING ~104 / WR ~64% / EV ~+0.11; RANGING ~51 / WR ~47% / EV ~-0.39; CHOP ~161 / WR ~62% / EV ~+0.07.",
            "",
            "## Top 10 Shadow Proposals",
            "",
            "| proposal | N | WR | EV | PF |",
            "|---|---:|---:|---:|---:|",
            *top_lines,
            "",
            "## Next Action",
            "",
            "司令塔側で artifacts と Tier A 再現ベンチマークを確認し、commit する。BT 結果は Shadow 候補生成のみで、Live 昇格判定には使わない。",
            "",
        ]
    )


def run_full(out_dir: Path = OUT_DIR, lookback_days: int = LOOKBACK) -> dict:
    pair_results: dict[str, dict] = {}
    tagged: list[dict] = []
    for symbol in PAIRS:
        started = time.time()
        result = run_pair_bt(symbol, lookback_days=lookback_days)
        result["elapsed_s"] = round(time.time() - started, 3)
        if result.get("error") and not result.get("trade_log"):
            raise RuntimeError(f"{symbol} BT failed: {result.get('error')}")
        pair_results[symbol] = result
        tagged.extend(tag_trades(symbol, result.get("trade_log", [])))

    outputs = build_output_tables(tagged, family_universe=ALL_FAMILIES)
    written = write_artifacts(pair_results, tagged, outputs, out_dir=out_dir)
    return {
        "pair_results": pair_results,
        "tagged_trades": tagged,
        "outputs": outputs,
        "written": written,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--lookback-days", type=int, default=LOOKBACK)
    args = parser.parse_args(argv)

    result = run_full(out_dir=args.out_dir, lookback_days=args.lookback_days)
    print(f"wrote {len(result['written'])} files to {args.out_dir}")
    print(f"tagged_trades={len(result['tagged_trades'])}")
    print(f"shadow_proposals={len(result['outputs'].shadow_proposals)}")
    print(f"zero_trade_families={len(result['outputs'].zero_trade_families)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
