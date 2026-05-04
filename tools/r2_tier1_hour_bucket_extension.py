#!/usr/bin/env python3
"""R2 Tier 1 + hour-bucket extension counterfactual.

Read-only proposal generator. It starts from the prior TRUE_LIVE
strategy x instrument R2 demote set, then searches additional N>=3
Tier 1 and strategy x instrument x UTC-hour cells.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.edge_discovery.significance import binomial_one_sided_p
from tools.gate_progression_audit import _hour_bucket, _metrics, summarize_trades
from tools.r2_strategy_instrument_counterfactual import (
    DEFAULT_TRADES as R2_DEFAULT_TRADES,
    SSOT_PROTECTED_KEEP_CELLS,
    apply_lot_multipliers,
    build_strategy_instrument_cells,
    greedy_counterfactual,
    load_trade_payload,
    split_buckets,
    summarize_buckets,
)

DEFAULT_TRADES = Path("/tmp/live-trades-20260503.json") if Path("/tmp/live-trades-20260503.json").exists() else R2_DEFAULT_TRADES
DEFAULT_BASE_DEMOTE_SET = Path("knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md")
DEFAULT_OUTPUT = Path("knowledge-base/wiki/decisions/r2-tier1-hour-bucket-extension-2026-05-03.md")
POST_CUTOFF = "2026-04-08"
MIN_ADD_N = 3
TIER1_STRATEGIES = {"session_time_bias", "gbp_deep_pullback", "trendline_sweep"}
BASE_DEMOTE_RE = re.compile(r"^\|\s*\d+\s*\|\s*STOP_OANDA\s*\|\s*0\.0\s*\|\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def _trade_id(row: dict) -> str:
    return str(row.get("trade_id") or row.get("id"))


def _cell_id(*parts: str) -> str:
    return "|".join(parts)


def _upper_tail_binomial_p(wins: int, n: int, p0: float = 0.50) -> float:
    if n <= 0:
        return 1.0
    return max(0.0, min(1.0, binomial_one_sided_p(wins, n, p0)))


def _parse_base_demote_set(path: str | Path | None) -> list[tuple[str, str]]:
    if not path:
        return []
    source = Path(path)
    if not source.exists():
        return []
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in source.read_text().splitlines():
        match = BASE_DEMOTE_RE.match(line)
        if match:
            key = (match.group(1).strip(), match.group(2).strip())
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def _base_demote_cells_from_doc_or_greedy(rows: list[dict], path: str | Path | None) -> list[dict]:
    doc_cells = _parse_base_demote_set(path)
    cells = build_strategy_instrument_cells(rows)
    selected, _post = greedy_counterfactual(rows, cells, mc_iterations=1000, mc_horizon_days=60)
    by_pair = {(cell["entry_type"], cell["instrument"]): cell for cell in selected}
    wanted = doc_cells or [
        (cell["entry_type"], cell["instrument"])
        for cell in selected
        if cell.get("action") == "STOP_OANDA" and float(cell.get("lot_multiplier", 1.0)) <= 0
    ]
    return [
        {**by_pair[key], "action": "BASE_STOP", "lot_multiplier": 0.0, "base_rank": idx + 1}
        for idx, key in enumerate(key for key in wanted if key in by_pair)
    ]


def apply_stop_ids(rows: list[dict], stop_ids: set[str]) -> list[dict]:
    return [row for row in rows if _trade_id(row) not in stop_ids]


def _candidate_record(
    *,
    dimension: str,
    key: tuple[str, ...],
    sub_rows: list[dict],
    m_add: int,
    mc_horizon_days: int,
) -> dict:
    metrics = _metrics(sub_rows, mc_iterations=100, mc_horizon_days=mc_horizon_days, n_trials=m_add)
    upper_raw = _upper_tail_binomial_p(metrics["wins"], metrics["n"])
    alpha_prime = 0.05 / max(1, m_add)
    strategy = key[0]
    instrument = key[1]
    hour = key[2] if len(key) > 2 else ""
    significant_positive = metrics["wr"] > 0.50 and metrics["ev_pips"] > 0 and upper_raw <= alpha_prime
    protected_pair = (strategy, instrument) in SSOT_PROTECTED_KEEP_CELLS
    return {
        "dimension": dimension,
        "cell_id": _cell_id(*key),
        "entry_type": strategy,
        "instrument": instrument,
        "hour_bucket": hour,
        "trade_ids": sorted(_trade_id(row) for row in sub_rows),
        "bonferroni_upper_p": min(1.0, upper_raw * max(1, m_add)),
        "binomial_upper_raw_p": upper_raw,
        "alpha_prime": alpha_prime,
        "significant_positive_keep": significant_positive,
        "protected_pair_keep": protected_pair,
        **metrics,
    }


def build_extension_candidates(rows: list[dict], *, mc_horizon_days: int = 60) -> tuple[list[dict], int]:
    grouped: dict[tuple[str, tuple[str, ...]], list[dict]] = defaultdict(list)
    for row in rows:
        strategy = str(row.get("entry_type") or row.get("strategy") or "unknown")
        instrument = str(row.get("instrument") or row.get("pair") or "unknown")
        hour = _hour_bucket(row)
        if strategy in TIER1_STRATEGIES:
            grouped[("tier1_pair", (strategy, instrument))].append(row)
        grouped[("hour_overlay", (strategy, instrument, hour))].append(row)

    qualified = {
        key: sub_rows
        for key, sub_rows in grouped.items()
        if len(sub_rows) >= MIN_ADD_N
    }
    m_add = len(qualified)
    records = [
        _candidate_record(dimension=dimension, key=key, sub_rows=sub_rows, m_add=m_add, mc_horizon_days=mc_horizon_days)
        for (dimension, key), sub_rows in qualified.items()
    ]
    records.sort(key=lambda row: (row["total_pnl_pips"], row["ev_pips"], row["kelly_raw"], -row["n"]))
    return records, m_add


def greedy_extension(
    base_remaining_rows: list[dict],
    candidates: list[dict],
    *,
    mc_iterations: int,
    mc_horizon_days: int,
) -> tuple[list[dict], dict]:
    selected: list[dict] = []
    stop_ids: set[str] = set()
    current = summarize_trades(base_remaining_rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days)["aggregate"]
    rank = 0
    for candidate in candidates:
        row = {**candidate, "action": "KEEP", "extension_rank": None, "reason": "initial keep"}
        if candidate["protected_pair_keep"]:
            row["reason"] = "SSOT protected pair keep"
        elif candidate["significant_positive_keep"]:
            row["reason"] = "Bonferroni-significant positive edge keep"
        elif candidate["total_pnl_pips"] < 0 and candidate["ev_pips"] < 0:
            remaining_ids = set(candidate["trade_ids"]) - stop_ids
            if remaining_ids:
                trial_rows = apply_stop_ids(base_remaining_rows, stop_ids | remaining_ids)
                trial = summarize_trades(trial_rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days)["aggregate"]
                if trial["kelly_raw"] > current["kelly_raw"]:
                    rank += 1
                    row["action"] = "STOP_OANDA"
                    row["extension_rank"] = rank
                    row["reason"] = "greedy worst-first extension"
                    stop_ids |= remaining_ids
                    current = trial
        selected.append(row)
        if current["kelly_raw"] >= 0 and current["mc_ruin_60d"] <= 0.90:
            break
    for cell in candidates[len(selected):]:
        if cell["protected_pair_keep"]:
            reason = "SSOT protected pair keep"
        elif cell["significant_positive_keep"]:
            reason = "Bonferroni-significant positive edge keep"
        else:
            reason = "not needed after recovery"
        selected.append({**cell, "action": "KEEP", "extension_rank": None, "reason": reason})
    selected.sort(key=lambda row: ((row["extension_rank"] is None), row["extension_rank"] or 9999, row["dimension"], row["cell_id"]))
    return selected, current


def verdict_for(post: dict, selected: list[dict]) -> str:
    protected_demoted = any(
        cell["action"] == "STOP_OANDA" and (cell["protected_pair_keep"] or cell["significant_positive_keep"])
        for cell in selected
    )
    if post["kelly_raw"] >= 0 and post["mc_ruin_60d"] <= 0.90 and not protected_demoted:
        return "ACCEPT"
    if -0.001 <= post["kelly_raw"] < 0 and post["mc_ruin_60d"] <= 0.90 and not protected_demoted:
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
        f"Wilson_lo={agg['wilson_lo']:.4f}, PF={agg['pf']:.3f}, total={agg['total_pnl_pips']:+.1f}p"
    )


def _bucket_row(name: str, metrics: dict) -> str:
    return (
        f"| {name} | {metrics['n']} | {metrics['wins']} | {metrics['losses']} | {metrics['breakevens']} | "
        f"{_fmt_pct(metrics['wr'])} | {metrics['ev_pips']:+.3f} | {metrics['total_pnl_pips']:+.1f} |"
    )


def _base_row(cell: dict) -> str:
    return f"| {cell['base_rank']} | {cell['entry_type']} | {cell['instrument']} | {cell['n']} | {cell['ev_pips']:+.2f} | {cell['total_pnl_pips']:+.1f} |"


def _ext_row(cell: dict) -> str:
    rank = "" if cell.get("extension_rank") is None else str(cell["extension_rank"])
    keep = "KEEP_SIG" if cell["significant_positive_keep"] else ("SSOT_KEEP" if cell["protected_pair_keep"] else "")
    return (
        f"| {rank} | {cell['action']} | {keep} | {cell['dimension']} | {cell['entry_type']} | {cell['instrument']} | "
        f"{cell['hour_bucket'] or '-'} | {cell['n']} | {_fmt_pct(cell['wr'])} | {cell['ev_pips']:+.2f} | "
        f"{cell['total_pnl_pips']:+.1f} | {cell['kelly_raw']:+.4f} | {_fmt_num(cell['binomial_upper_raw_p'])} | "
        f"{_fmt_num(cell['bonferroni_upper_p'])} | {cell['reason']} |"
    )


def _extension_table(cells: list[dict]) -> list[str]:
    lines = [
        "| rank | action | keep | dimension | strategy | instrument | hour_utc | N | WR | EV pip | total pip | raw Kelly | p(edge) | Bonf p(edge) | reason |",
        "|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    lines.extend(_ext_row(cell) for cell in cells)
    return lines


def render_report(
    *,
    source_trades: str,
    source_base_demote_set: str,
    bucket_summary: dict[str, dict],
    live_rows: list[dict],
    baseline: dict,
    base_post: dict,
    extension_post: dict,
    base_cells: list[dict],
    extension_cells: list[dict],
    m_add: int,
    mc_iterations: int,
    mc_horizon_days: int,
) -> str:
    verdict = verdict_for(extension_post, extension_cells)
    extension_stops = [cell for cell in extension_cells if cell["action"] == "STOP_OANDA"]
    keep_sig = [cell for cell in extension_cells if cell["significant_positive_keep"] or cell["protected_pair_keep"]]
    lines = [
        "# R2 Tier 1 + hour-bucket extension - 2026-05-03",
        "",
        f"Verdict: {verdict}",
        f"Aggregate post-extension: raw Kelly={extension_post['kelly_raw']:+.4f}, MC60d={extension_post['mc_ruin_60d']:.4f}, EV={extension_post['ev_pips']:+.2f}p, PF={extension_post['pf']:.3f}, N={extension_post['n']}",
        "Min extension demote set: "
        + (", ".join(f"{cell['dimension']}:{cell['cell_id']}" for cell in extension_stops) if extension_stops else "none"),
        f"Bonferroni m_add: {m_add}; alpha'_add={0.05 / max(1, m_add):.6f}; keep_sig={len(keep_sig)}",
        "",
        "## Source / separation",
        "",
        f"- 一次ソース: `{source_trades}`",
        f"- base demote source: `{source_base_demote_set}`",
        f"- TRUE_LIVE抽出: `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN (...) AND pnl_pips IS NOT NULL AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '{POST_CUTOFF}'`。",
        f"- TRUE_LIVE N: {len(live_rows)} / Live期間: {baseline.get('live_start') or 'unknown'} -> {baseline.get('live_end') or 'unknown'}。",
        f"- MC仕様: iterations={mc_iterations}, horizon={mc_horizon_days}d, bootstrap=Live PnL分布。",
        "- 本レポートは LOCK proposal。OANDA転送停止・lot変更・本番DB書き込みは未実施。",
        "",
        "## Bucket 3-split",
        "",
        "| bucket | N | wins | losses | breakevens | WR | EV pip | PnL pip |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *[_bucket_row(name, bucket_summary[name]) for name in ("TRUE_LIVE", "FLAG_DRIFT", "SHADOW")],
        "",
        "## Aggregate counterfactual",
        "",
        _aggregate_line("Baseline TRUE_LIVE", baseline),
        _aggregate_line("Base 14-cell post-cut", base_post),
        _aggregate_line("Aggregate post-extension", extension_post),
        f"Kelly improvement: {baseline['kelly_raw']:+.4f} -> {base_post['kelly_raw']:+.4f} -> {extension_post['kelly_raw']:+.4f}",
        f"MC60d improvement: {baseline['mc_ruin_60d']:.4f} -> {base_post['mc_ruin_60d']:.4f} -> {extension_post['mc_ruin_60d']:.4f}",
        "",
        "## Existing 14-cell base demote",
        "",
        "| rank | strategy | instrument | N | EV pip | total pip |",
        "|---:|---|---|---:|---:|---:|",
        *[_base_row(cell) for cell in base_cells],
        "",
        "## Extension candidates / actions",
        "",
        *_extension_table(extension_cells),
        "",
        "## Bonferroni-significant keep protection",
        "",
        f"- Bonferroni-significant positive or SSOT protected keep cell数: {len(keep_sig)}",
        "- SSOT protected pair (`fib_reversal x USD_JPY/EUR_USD` 等) は hour-bucket overlay でも STOP 対象外。",
        "",
        *(_extension_table(keep_sig) if keep_sig else ["_該当なし_"]),
        "",
        "## Verdict rationale",
        "",
    ]
    if verdict == "ACCEPT":
        lines.append("- 既存14-cell + 最小拡張STOPで raw Kelly >= 0 かつ MC60d <= 90% を達成。")
    elif verdict == "NEEDS_MORE_EVIDENCE":
        lines.append("- raw Kelly は -0.001 以内まで接近したが ACCEPT 未達。hour bucket 細分化または追加軸が必要。")
    else:
        lines.append("- Tier 1 + hour-bucket追加STOPでも raw Kelly < -0.001。H3: portfolio構造見直しが必要。")
    lines += [
        "- Bonferroni-significant positive / SSOT protected keep cell は demote していない。",
        "- `app.py` / `modules` / `strategies` は本タスクでは編集しない。",
        "",
    ]
    return "\n".join(lines)


def run_audit(
    *,
    trades_path: str | Path,
    base_demote_set_path: str | Path | None,
    output_path: str | Path | None,
    mc_iterations: int,
    mc_horizon_days: int,
) -> dict:
    payload = load_trade_payload(trades_path)
    buckets = split_buckets(payload)
    bucket_summary = summarize_buckets(buckets)
    live_rows = buckets["TRUE_LIVE"]
    baseline = summarize_trades(live_rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days)["aggregate"]
    base_cells = _base_demote_cells_from_doc_or_greedy(live_rows, base_demote_set_path)
    base_stop_ids = {trade_id for cell in base_cells for trade_id in cell.get("trade_ids", [])}
    base_remaining_rows = apply_stop_ids(live_rows, base_stop_ids)
    base_post = summarize_trades(base_remaining_rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days)["aggregate"]
    candidates, m_add = build_extension_candidates(base_remaining_rows, mc_horizon_days=mc_horizon_days)
    extension_cells, extension_post = greedy_extension(
        base_remaining_rows,
        candidates,
        mc_iterations=mc_iterations,
        mc_horizon_days=mc_horizon_days,
    )
    report = render_report(
        source_trades=str(trades_path),
        source_base_demote_set=str(base_demote_set_path or ""),
        bucket_summary=bucket_summary,
        live_rows=live_rows,
        baseline=baseline,
        base_post=base_post,
        extension_post=extension_post,
        base_cells=base_cells,
        extension_cells=extension_cells,
        m_add=m_add,
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
        "base_post": base_post,
        "extension_post": extension_post,
        "base_cells": base_cells,
        "extension_cells": extension_cells,
        "m_add": m_add,
        "report": report,
        "verdict": verdict_for(extension_post, extension_cells),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", default=str(DEFAULT_TRADES))
    parser.add_argument("--base-demote-set", default=str(DEFAULT_BASE_DEMOTE_SET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mc-iterations", type=int, default=1000)
    parser.add_argument("--mc-horizon", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    trades_path = Path(args.trades)
    if not trades_path.exists():
        print(f"trades file not found: {trades_path}", file=sys.stderr)
        return 2
    if args.mc_iterations < 1000 and not args.dry_run:
        print("MC iterations must be >= 1000", file=sys.stderr)
        return 2

    mc_iterations = 1000 if not args.dry_run else max(100, min(args.mc_iterations, 1000))
    result = run_audit(
        trades_path=trades_path,
        base_demote_set_path=args.base_demote_set,
        output_path=None if args.dry_run else args.output,
        mc_iterations=mc_iterations,
        mc_horizon_days=args.mc_horizon,
    )
    buckets = ", ".join(
        f"{name}={metrics['n']}({metrics['total_pnl_pips']:+.1f}p)"
        for name, metrics in result["bucket_summary"].items()
    )
    stops = [cell for cell in result["extension_cells"] if cell["action"] == "STOP_OANDA"]
    print(f"Bucket 3-split: {buckets}")
    print(f"Base demote cells={len(result['base_cells'])}, extension candidates={len(result['extension_cells'])}, m_add={result['m_add']}")
    print(
        "Counterfactual: "
        f"raw Kelly={result['baseline']['kelly_raw']:+.4f}->{result['base_post']['kelly_raw']:+.4f}->{result['extension_post']['kelly_raw']:+.4f}, "
        f"MC60d={result['baseline']['mc_ruin_60d']:.4f}->{result['base_post']['mc_ruin_60d']:.4f}->{result['extension_post']['mc_ruin_60d']:.4f}, "
        f"extension_stops={len(stops)}"
    )
    print(f"Verdict: {result['verdict']}")
    if args.dry_run:
        for cell in result["base_cells"]:
            print(f"BASE_STOP {cell['entry_type']} {cell['instrument']} N={cell['n']} PnL={cell['total_pnl_pips']:+.1f}")
        for cell in result["extension_cells"]:
            if cell["action"] == "STOP_OANDA" or cell["significant_positive_keep"] or cell["protected_pair_keep"]:
                print(
                    f"{cell['action']} {cell['dimension']} {cell['cell_id']} "
                    f"N={cell['n']} EV={cell['ev_pips']:+.2f} PnL={cell['total_pnl_pips']:+.1f} "
                    f"rawKelly={cell['kelly_raw']:+.4f} reason={cell['reason']}"
                )
    elif args.output:
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
