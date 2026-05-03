#!/usr/bin/env python3
"""R2 strategy x instrument demotion counterfactual.

Read-only proposal generator. It evaluates TRUE_LIVE trades only:
is_shadow=0, non-empty oanda_trade_id, post-cutoff, closed decided outcomes,
non-null pnl_pips, excluding XAU_USD and EUR_GBP.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.edge_discovery.significance import binomial_one_sided_p
from tools.gate_progression_audit import _metrics, summarize_trades

POST_CUTOFF = "2026-04-08"
DECIDED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}
EXCLUDED_INSTRUMENTS = {"XAU_USD", "EUR_GBP"}
MIN_CELL_N = 5
DEFAULT_TRADES = Path("/tmp/live-trades-r2si.json")
ELITE_FLAG_CELL = ("session_time_bias", "GBP_USD")
SSOT_PROTECTED_KEEP_CELLS = {
    ("fib_reversal", "EUR_USD"),
    ("fib_reversal", "USD_JPY"),
    ("vol_surge_detector", "EUR_USD"),
    ("vol_momentum_scalp", "USD_JPY"),
    ("dt_bb_rsi_mr", "USD_JPY"),
    ("ema_trend_scalp", "EUR_USD"),
    ("bb_squeeze_breakout", "EUR_USD"),
    ("bb_rsi_reversion", "GBP_USD"),
    ("trend_rebound", "EUR_USD"),
    ("stoch_trend_pullback", "EUR_USD"),
}


def _trade_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        rows = payload.get("trades", [])
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("trade payload must be a list or {'trades': [...]}")
    return [row for row in rows if isinstance(row, dict)]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _has_oanda_trade_id(row: dict) -> bool:
    return bool(str(row.get("oanda_trade_id") or "").strip())


def _trade_id(row: dict) -> str:
    return str(row.get("trade_id") or row.get("id"))


def _cell_id(strategy: str, instrument: str) -> str:
    return f"{strategy}|{instrument}"


def _base_closed_row(row: dict, *, cutoff: str = POST_CUTOFF) -> dict | None:
    outcome = str(row.get("outcome") or "").upper()
    status = str(row.get("status") or "").upper()
    if status and status != "CLOSED":
        return None
    if outcome not in DECIDED_OUTCOMES:
        return None
    instrument = str(row.get("instrument") or row.get("pair") or "")
    if instrument in EXCLUDED_INSTRUMENTS or instrument.startswith("XAU"):
        return None
    entry_dt = _parse_dt(row.get("entry_time") or row.get("created_at"))
    cutoff_dt = _parse_dt(cutoff)
    if entry_dt is None or cutoff_dt is None or entry_dt < cutoff_dt:
        return None
    if row.get("pnl_pips") is None:
        return None
    try:
        pnl = float(row.get("pnl_pips"))
    except (TypeError, ValueError):
        return None
    clean = dict(row)
    clean["outcome"] = outcome
    clean["status"] = "CLOSED"
    clean["pnl_pips"] = pnl
    clean["entry_type"] = clean.get("entry_type") or clean.get("strategy") or "unknown"
    clean["instrument"] = instrument or "unknown"
    return clean


def bucket_for(row: dict) -> str:
    if _as_bool(row.get("is_shadow", False)):
        return "SHADOW"
    if _has_oanda_trade_id(row):
        return "TRUE_LIVE"
    return "FLAG_DRIFT"


def split_buckets(payload: Any, *, cutoff: str = POST_CUTOFF) -> dict[str, list[dict]]:
    buckets = {"TRUE_LIVE": [], "FLAG_DRIFT": [], "SHADOW": []}
    for row in _trade_rows(payload):
        clean = _base_closed_row(row, cutoff=cutoff)
        if clean is None:
            continue
        buckets[bucket_for(clean)].append(clean)
    return buckets


def filter_true_live_rows(payload: Any, *, cutoff: str = POST_CUTOFF) -> list[dict]:
    return split_buckets(payload, cutoff=cutoff)["TRUE_LIVE"]


def _bucket_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "wins": 0, "losses": 0, "breakevens": 0, "wr": 0.0, "ev_pips": 0.0, "total_pnl_pips": 0.0}
    wins = sum(1 for row in rows if float(row["pnl_pips"]) > 0)
    losses = sum(1 for row in rows if float(row["pnl_pips"]) < 0)
    total = sum(float(row["pnl_pips"]) for row in rows)
    n = len(rows)
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "breakevens": n - wins - losses,
        "wr": wins / n,
        "ev_pips": total / n,
        "total_pnl_pips": total,
    }


def summarize_buckets(buckets: dict[str, list[dict]]) -> dict[str, dict]:
    return {name: _bucket_metrics(rows) for name, rows in buckets.items()}


def _lower_tail_binomial_p(wins: int, n: int, p0: float = 0.50) -> float:
    if n <= 0 or wins >= n:
        return 1.0
    return max(0.0, min(1.0, 1.0 - binomial_one_sided_p(wins + 1, n, p0)))


def _upper_tail_binomial_p(wins: int, n: int, p0: float = 0.50) -> float:
    if n <= 0:
        return 1.0
    return max(0.0, min(1.0, binomial_one_sided_p(wins, n, p0)))


def build_strategy_instrument_cells(
    rows: list[dict],
    *,
    min_n: int = MIN_CELL_N,
    mc_horizon_days: int = 60,
) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("entry_type") or "unknown"), str(row.get("instrument") or "unknown"))].append(row)

    qualified = {key: sub_rows for key, sub_rows in grouped.items() if len(sub_rows) >= min_n}
    m = len(qualified)
    records: list[dict] = []
    for (strategy, instrument), sub_rows in qualified.items():
        metrics = _metrics(sub_rows, mc_iterations=100, mc_horizon_days=mc_horizon_days, n_trials=m)
        lower_raw = _lower_tail_binomial_p(metrics["wins"], metrics["n"])
        upper_raw = _upper_tail_binomial_p(metrics["wins"], metrics["n"])
        cell = {
            "cell_id": _cell_id(strategy, instrument),
            "entry_type": strategy,
            "instrument": instrument,
            "trade_ids": sorted(_trade_id(row) for row in sub_rows),
            "binomial_lower_raw_p": lower_raw,
            "binomial_upper_raw_p": upper_raw,
            "bonferroni_lower_p": min(1.0, lower_raw * max(1, m)),
            "bonferroni_upper_p": min(1.0, upper_raw * max(1, m)),
            "alpha_prime": 0.05 / max(1, m),
            **metrics,
        }
        cell["significant_keep"] = is_significant_keep(cell, m=m)
        records.append(cell)
    records.sort(key=lambda row: (row["total_pnl_pips"], row["ev_pips"], row["kelly_raw"], -row["n"]))
    return records


def is_significant_keep(cell: dict, *, m: int) -> bool:
    if (cell["entry_type"], cell["instrument"]) in SSOT_PROTECTED_KEEP_CELLS:
        return True
    return (
        cell["n"] >= MIN_CELL_N
        and cell["ev_pips"] > 0
        and cell["bonferroni_upper_p"] <= (0.05 / max(1, m))
    )


def apply_lot_multipliers(rows: list[dict], cells: list[dict]) -> list[dict]:
    multipliers: dict[str, float] = {}
    for cell in cells:
        multiplier = float(cell.get("lot_multiplier", 1.0))
        for trade_id in cell.get("trade_ids", []):
            multipliers[str(trade_id)] = multiplier

    adjusted: list[dict] = []
    for row in rows:
        multiplier = multipliers.get(_trade_id(row), 1.0)
        if multiplier <= 0:
            continue
        clone = dict(row)
        clone["pnl_pips"] = float(clone["pnl_pips"]) * multiplier
        adjusted.append(clone)
    return adjusted


def _kelly_raw_from_rows(rows: list[dict]) -> float:
    pnls = [float(row["pnl_pips"]) for row in rows]
    if not pnls:
        return 0.0
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    n = len(pnls)
    win_rate = len(wins) / n
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    return (win_rate * b - (1 - win_rate)) / b


def full_negative_stop_counterfactual(
    rows: list[dict],
    cells: list[dict],
    *,
    mc_iterations: int,
    mc_horizon_days: int,
) -> dict:
    stopped = [
        {**cell, "action": "STOP_OANDA", "lot_multiplier": 0.0}
        for cell in cells
        if cell["total_pnl_pips"] < 0 and not cell.get("significant_keep")
    ]
    adjusted = apply_lot_multipliers(rows, stopped)
    return summarize_trades(
        adjusted, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days
    )["aggregate"]


def greedy_counterfactual(
    rows: list[dict],
    cells: list[dict],
    *,
    mc_iterations: int,
    mc_horizon_days: int,
) -> tuple[list[dict], dict]:
    selected = [
        {
            **cell,
            "action": "KEEP",
            "lot_multiplier": 1.0,
            "greedy_rank": None,
            "reason": (
                "SSOT/Bonferroni positive edge; protected keep"
                if cell.get("significant_keep")
                else "initial keep"
            ),
        }
        for cell in cells
    ]
    candidates = [
        cell for cell in selected if not cell.get("significant_keep") and cell["total_pnl_pips"] < 0
    ]
    candidates.sort(key=lambda row: (row["total_pnl_pips"], row["ev_pips"], row["kelly_raw"], -row["n"]))

    current_kelly_raw = _kelly_raw_from_rows(apply_lot_multipliers(rows, selected))
    rank = 0
    for candidate in candidates:
        if current_kelly_raw >= 0:
            break
        rank += 1
        candidate["action"] = "LOT_HALF"
        candidate["lot_multiplier"] = 0.5
        candidate["greedy_rank"] = rank
        candidate["reason"] = "worst-first trial at 0.5x"
        half_kelly_raw = _kelly_raw_from_rows(apply_lot_multipliers(rows, selected))
        if half_kelly_raw >= 0:
            current_kelly_raw = half_kelly_raw
            break
        candidate["action"] = "STOP_OANDA"
        candidate["lot_multiplier"] = 0.0
        candidate["reason"] = "worst-first 0.5x insufficient; stop"
        current_kelly_raw = _kelly_raw_from_rows(apply_lot_multipliers(rows, selected))
    selected.sort(key=lambda row: ((row["greedy_rank"] is None), row["greedy_rank"] or 9999, row["cell_id"]))
    aggregate = summarize_trades(
        apply_lot_multipliers(rows, selected),
        mc_iterations=mc_iterations,
        mc_horizon_days=mc_horizon_days,
    )["aggregate"]
    return selected, aggregate


def verdict_for(post: dict, full_stop: dict, cells: list[dict]) -> str:
    protected_demoted = any(
        cell.get("significant_keep") and float(cell.get("lot_multiplier", 1.0)) < 1.0 for cell in cells
    )
    if post["kelly_raw"] >= 0 and post["mc_ruin_60d"] <= 0.90 and not protected_demoted:
        return "ACCEPT"
    if post["kelly_raw"] >= -0.05 or full_stop["kelly_raw"] >= -0.05:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def _fmt_pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _fmt_num(value: float, digits: int = 4) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def _aggregate_line(label: str, agg: dict) -> str:
    return (
        f"{label}: N={agg['n']}, raw Kelly={agg['kelly_raw']:+.4f}, clipped Kelly={agg['kelly']:.4f}, "
        f"MC60d={agg['mc_ruin_60d']:.4f}, EV={agg['ev_pips']:+.2f}p, "
        f"Wilson_lo={agg['wilson_lo']:.4f}, PF={agg['pf']:.3f}, "
        f"maxDD={agg['max_dd_pct']:.4f}, total={agg['total_pnl_pips']:+.1f}p"
    )


def _bucket_row(name: str, metrics: dict) -> str:
    return (
        f"| {name} | {metrics['n']} | {metrics['wins']} | {metrics['losses']} | "
        f"{metrics['breakevens']} | {_fmt_pct(metrics['wr'])} | "
        f"{metrics['ev_pips']:+.3f} | {metrics['total_pnl_pips']:+.1f} |"
    )


def _cell_row(cell: dict) -> str:
    keep_mark = "KEEP_SIG" if cell.get("significant_keep") else ""
    rank = "" if cell.get("greedy_rank") is None else str(cell["greedy_rank"])
    return (
        f"| {rank} | {cell.get('action', 'KEEP')} | {cell.get('lot_multiplier', 1.0):.1f} | "
        f"{keep_mark} | {cell['entry_type']} | {cell['instrument']} | {cell['n']} | "
        f"{_fmt_pct(cell['wr'])} | {_fmt_pct(cell['wilson_lo'])} | {cell['ev_pips']:+.2f} | "
        f"{cell['total_pnl_pips']:+.1f} | {_fmt_num(cell['pf'], 3)} | {cell['kelly_raw']:+.4f} | "
        f"{_fmt_num(cell['binomial_upper_raw_p'])} | {_fmt_num(cell['bonferroni_upper_p'])} | "
        f"{_fmt_pct(cell['max_dd_pct'])} | {cell.get('reason', '')} |"
    )


def _cell_table(cells: list[dict]) -> list[str]:
    lines = [
        "| rank | action | lot | keep | strategy | instrument | N | WR | Wilson lo | EV pip | total pip | PF | raw Kelly | p(edge) | Bonf p(edge) | max DD | reason |",
        "|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    lines.extend(_cell_row(cell) for cell in cells)
    return lines


def render_report(
    *,
    source_trades: str,
    bucket_summary: dict[str, dict],
    live_rows: list[dict],
    baseline: dict,
    greedy_post: dict,
    full_stop: dict,
    cells: list[dict],
    m: int,
    mc_iterations: int,
    mc_horizon_days: int,
) -> str:
    verdict = verdict_for(greedy_post, full_stop, cells)
    actions = [cell for cell in cells if cell.get("action") in {"LOT_HALF", "STOP_OANDA"}]
    protected = [cell for cell in cells if cell.get("significant_keep")]
    elite = next((cell for cell in cells if (cell["entry_type"], cell["instrument"]) == ELITE_FLAG_CELL), None)
    elite_text = "present" if elite else "not_in_N>=5_grid"
    if elite:
        elite_text = (
            f"N={elite['n']}, EV={elite['ev_pips']:+.2f}, PnL={elite['total_pnl_pips']:+.1f}, "
            f"action={elite.get('action', 'KEEP')}"
        )

    lines = [
        "# R2 strategy x instrument counterfactual - 2026-05-03",
        "",
        f"Verdict: {verdict}",
        f"Aggregate post-cut: raw Kelly={greedy_post['kelly_raw']:+.4f}, MC60d={greedy_post['mc_ruin_60d']:.4f}, N={greedy_post['n']}",
        "Min demote set: "
        + (
            ", ".join(
                f"{cell['entry_type']} x {cell['instrument']} x{cell['lot_multiplier']:.1f}"
                for cell in actions
            )
            if verdict == "ACCEPT" and actions
            else "none; no strategy x instrument demote set reached aggregate raw Kelly >= 0 and MC60d <= 90%"
        ),
        "Greedy tested set: "
        + (
            ", ".join(
                f"{cell['entry_type']} x {cell['instrument']} x{cell['lot_multiplier']:.1f}"
                for cell in actions
            )
            if actions
            else "none"
        ),
        f"ELITE_FLAG: session_time_bias x GBP_USD -> {elite_text}; recommend immediate WATCH escalation as separate action.",
        "",
        "## Bucket 3-split (post-cutoff, excluding XAU_USD/EUR_GBP)",
        "",
        "| bucket | N | wins | losses | breakevens | WR | EV pip | PnL pip |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *[_bucket_row(name, bucket_summary[name]) for name in ("TRUE_LIVE", "FLAG_DRIFT", "SHADOW")],
        "",
        "## Source / separation",
        "",
        f"- 一次ソース: `{source_trades}`",
        f"- Live抽出: `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN (...) AND pnl_pips IS NOT NULL AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '{POST_CUTOFF}'`。",
        "- modeフィルタは未使用。",
        f"- TRUE_LIVE N: {len(live_rows)} / Live期間: {baseline.get('live_start') or 'unknown'} -> {baseline.get('live_end') or 'unknown'}。",
        f"- Bonferroni母数 m: **{m} TRUE_LIVE N>=5 strategy x instrument cells**。alpha'=0.05/{m}={0.05 / max(1, m):.6f}。",
        f"- MC仕様: iterations={mc_iterations}, horizon={mc_horizon_days}d, bootstrap=Live PnL分布。",
        "- OANDA転送停止・lot変更・本番DB書き込みは未実施。",
        "",
        "## Aggregate counterfactual",
        "",
        _aggregate_line("Baseline TRUE_LIVE", baseline),
        _aggregate_line("Greedy post-cut", greedy_post),
        _aggregate_line("All negative N>=5 STOP", full_stop),
        "",
        "## Strategy x instrument cells",
        "",
        *_cell_table(cells),
        "",
        "## Bonferroni-significant keep protection",
        "",
        f"- protected keep cell数: {len(protected)}",
        "- `KEEP_SIG` は SSOTのLive黒字/keep指定、または N>=5, EV>0, one-sided binomial positive-edge p <= alpha' の cell。該当 cell は demote 候補から除外。",
        "",
        *(_cell_table(protected) if protected else ["_該当なし_"]),
        "",
        "## ELITE_FLAG",
        "",
        "- `session_time_bias x GBP_USD` は ELITE_LIVE 出血セルとして別アクションで WATCH 格上げを推奨。",
        f"- Current grid evidence: {elite_text}",
        "",
        "## Verdict rationale",
        "",
    ]
    if verdict == "ACCEPT":
        lines.append("- 最小 demote 集合で aggregate raw Kelly >= 0 かつ MC60d <= 90% を達成。")
    elif verdict == "NEEDS_MORE_EVIDENCE":
        lines.append("- raw Kelly は -0.05 以上まで近づいた、または全N>=5出血cell STOPで -0.05 以上に入った。Gate 0救済には拡張範囲が必要。")
    else:
        lines.append("- 全N>=5出血cellをSTOPしても aggregate raw Kelly < -0.05。H5: strategy x instrument demote だけでは不十分。")
    lines += [
        "- Live黒字cellは greedy demote 候補から除外。",
        "- 本レポートは LOCK proposal。実装PRや `app.py` 変更は別タスク。",
        "",
    ]
    return "\n".join(lines)


def load_trade_payload(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def run_audit(
    *,
    trades_path: str | Path,
    output_path: str | Path | None,
    mc_iterations: int,
    mc_horizon_days: int,
) -> dict:
    payload = load_trade_payload(trades_path)
    buckets = split_buckets(payload)
    bucket_summary = summarize_buckets(buckets)
    live_rows = buckets["TRUE_LIVE"]
    baseline = summarize_trades(
        live_rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days
    )["aggregate"]
    cells = build_strategy_instrument_cells(live_rows, mc_horizon_days=mc_horizon_days)
    selected, greedy_post = greedy_counterfactual(
        live_rows,
        cells,
        mc_iterations=mc_iterations,
        mc_horizon_days=mc_horizon_days,
    )
    full_stop = full_negative_stop_counterfactual(
        live_rows,
        cells,
        mc_iterations=mc_iterations,
        mc_horizon_days=mc_horizon_days,
    )
    report = render_report(
        source_trades=str(trades_path),
        bucket_summary=bucket_summary,
        live_rows=live_rows,
        baseline=baseline,
        greedy_post=greedy_post,
        full_stop=full_stop,
        cells=selected,
        m=len(cells),
        mc_iterations=mc_iterations,
        mc_horizon_days=mc_horizon_days,
    )
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report)
    return {
        "bucket_summary": bucket_summary,
        "baseline": baseline,
        "greedy_post": greedy_post,
        "full_stop": full_stop,
        "cells": selected,
        "report": report,
        "verdict": verdict_for(greedy_post, full_stop, selected),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", default=str(DEFAULT_TRADES))
    parser.add_argument("--output")
    parser.add_argument("--mc-iterations", type=int, default=1000)
    parser.add_argument("--mc-horizon", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.mc_iterations < 1000 and not args.dry_run:
        print("MC iterations must be >= 1000", file=sys.stderr)
        return 2
    trades_path = Path(args.trades)
    if not trades_path.exists():
        print(f"trades file not found: {trades_path}", file=sys.stderr)
        return 2

    mc_iterations = 1000 if not args.dry_run else max(100, min(args.mc_iterations, 1000))
    result = run_audit(
        trades_path=trades_path,
        output_path=None if args.dry_run else args.output,
        mc_iterations=mc_iterations,
        mc_horizon_days=args.mc_horizon,
    )
    cells = result["cells"]
    actions = [cell for cell in cells if cell.get("action") in {"LOT_HALF", "STOP_OANDA"}]
    bucket_bits = ", ".join(
        f"{name}={metrics['n']}({metrics['total_pnl_pips']:+.1f}p)"
        for name, metrics in result["bucket_summary"].items()
    )
    print(f"Bucket 3-split: {bucket_bits}")
    print(
        f"Grid: qualified_cells={len(cells)}, qualified_trades={sum(cell['n'] for cell in cells)}, "
        f"protected_keep={sum(1 for cell in cells if cell.get('significant_keep'))}"
    )
    print(
        f"Counterfactual: aggregate raw Kelly={result['baseline']['kelly_raw']:+.4f}->{result['greedy_post']['kelly_raw']:+.4f}, "
        f"MC60d={result['baseline']['mc_ruin_60d']:.4f}->{result['greedy_post']['mc_ruin_60d']:.4f}, "
        f"actions={len(actions)}"
    )
    print(f"All negative N>=5 STOP raw Kelly={result['full_stop']['kelly_raw']:+.4f}, MC60d={result['full_stop']['mc_ruin_60d']:.4f}")
    print(f"Verdict: {result['verdict']}")
    if args.dry_run:
        for cell in cells:
            print(
                f"{cell['entry_type']} {cell['instrument']} N={cell['n']} "
                f"EV={cell['ev_pips']:+.2f} PnL={cell['total_pnl_pips']:+.1f} "
                f"rawKelly={cell['kelly_raw']:+.4f} action={cell.get('action')} "
                f"lot={cell.get('lot_multiplier', 1.0):.1f}"
            )
    elif args.output:
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
