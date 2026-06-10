#!/usr/bin/env python3
"""R2 cell-level demotion lock audit.

This is a read-only audit. It proposes STOP_OANDA / LOT_HALF actions at
(entry_type, instrument, UTC hour_bucket) cell level and simulates the aggregate
counterfactual without changing OANDA routing or lot settings.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.edge_discovery.significance import binomial_one_sided_p
from tools.gate_progression_audit import (
    _hour_bucket,
    _metrics,
    _parse_dt,
    filter_closed_live_trades,
    summarize_trades,
)

DECIDED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}
STOP_MIN_N = 5
LOT_HALF_MIN_N = 10
MAX_REPORT_CELLS_PER_SECTION = 120


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


def filter_closed_shadow_rows(payload: Any) -> list[dict]:
    rows = []
    for row in _trade_rows(payload):
        if not _as_bool(row.get("is_shadow", False)):
            continue
        # dedup_violation=1 は per-bar dedup gate leak の二重記録 → 統計から除外
        # (2026-06-08 Claude 検証、shadow_promote_r2_alert と整合)
        if int(row.get("dedup_violation", 0) or 0) == 1:
            continue
        clone = dict(row)
        clone["is_shadow"] = 0
        rows.extend(filter_closed_live_trades({"trades": [clone]}))
    return rows


def _cell_id(strategy: str, instrument: str, hour_bucket: str) -> str:
    return f"{strategy}|{instrument}|{hour_bucket}"


def _lower_tail_binomial_p(wins: int, n: int, p0: float = 0.50) -> float:
    if n <= 0:
        return 1.0
    if wins >= n:
        return 1.0
    return max(0.0, min(1.0, 1.0 - binomial_one_sided_p(wins + 1, n, p0)))


def _upper_tail_binomial_p(wins: int, n: int, p0: float = 0.50) -> float:
    if n <= 0:
        return 1.0
    return max(0.0, min(1.0, binomial_one_sided_p(wins, n, p0)))


def build_cell_records(rows: list[dict], *, mc_horizon_days: int = 60) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        strategy = str(row.get("entry_type") or row.get("strategy") or "unknown")
        instrument = str(row.get("instrument") or row.get("pair") or "unknown")
        hour = _hour_bucket(row)
        grouped[(strategy, instrument, hour)].append(row)

    records = []
    m = len(grouped)
    for (strategy, instrument, hour), sub_rows in grouped.items():
        metrics = _metrics(sub_rows, mc_iterations=100, mc_horizon_days=mc_horizon_days, n_trials=m)
        lower_raw = _lower_tail_binomial_p(metrics["wins"], metrics["n"])
        upper_raw = _upper_tail_binomial_p(metrics["wins"], metrics["n"])
        records.append(
            {
                "cell_id": _cell_id(strategy, instrument, hour),
                "entry_type": strategy,
                "instrument": instrument,
                "hour_bucket": hour,
                "trade_ids": sorted(str(row.get("trade_id") or row.get("id")) for row in sub_rows),
                "binomial_lower_raw_p": lower_raw,
                "binomial_upper_raw_p": upper_raw,
                "bonferroni_p": min(1.0, lower_raw * max(1, m)),
                "bonferroni_upper_p": min(1.0, upper_raw * max(1, m)),
                **metrics,
            }
        )
    records.sort(key=lambda row: (row["ev_pips"], row["kelly_raw"], row["total_pnl_pips"], -row["n"]))
    return records


def _is_keep(cell: dict) -> bool:
    return cell["ev_pips"] > 0 or cell["wilson_lo"] > 0.50 or cell["kelly_raw"] > 0


def _is_stop(cell: dict) -> bool:
    return (
        cell["n"] >= STOP_MIN_N
        and cell["ev_pips"] < -2.0
        and cell["wilson_lo"] < 0.30
        and cell["kelly_raw"] < -0.5
        and cell["total_pnl_pips"] < -15.0
    )


def _is_lot_half(cell: dict) -> bool:
    return (
        cell["n"] >= LOT_HALF_MIN_N
        and cell["ev_pips"] < -0.5
        and cell["wilson_lo"] < 0.40
        and cell["kelly_raw"] < -0.1
        and cell["total_pnl_pips"] < -5.0
    )


def classify_cells(cells: list[dict], *, max_cuts: int) -> list[dict]:
    cut_count = 0
    classified = []
    for cell in cells:
        row = dict(cell)
        row["extension_rank"] = None
        if _is_keep(cell):
            row["action"] = "KEEP"
            row["reason"] = "EV>0 or Wilson_lo>0.50 or raw Kelly>0"
        elif _is_stop(cell) and cut_count < max_cuts:
            cut_count += 1
            row["action"] = "STOP_OANDA"
            row["reason"] = "LOCK threshold"
        elif _is_lot_half(cell):
            row["action"] = "LOT_HALF"
            row["reason"] = "LOCK threshold"
        else:
            row["action"] = "WATCH"
            row["reason"] = "N<5, boundary, or threshold not met"
        classified.append(row)
    return classified


def apply_actions(rows: list[dict], cells: list[dict]) -> list[dict]:
    stop_ids: set[str] = set()
    half_ids: set[str] = set()
    for cell in cells:
        if cell["action"] == "STOP_OANDA":
            stop_ids.update(str(trade_id) for trade_id in cell.get("trade_ids", []))
        elif cell["action"] == "LOT_HALF":
            half_ids.update(str(trade_id) for trade_id in cell.get("trade_ids", []))

    adjusted = []
    for row in rows:
        trade_id = str(row.get("trade_id") or row.get("id"))
        if trade_id in stop_ids:
            continue
        clone = dict(row)
        if trade_id in half_ids:
            clone["pnl_pips"] = float(clone["pnl_pips"]) * 0.5
        adjusted.append(clone)
    return adjusted


def extend_cuts_until_recovery(
    rows: list[dict],
    cells: list[dict],
    *,
    max_cuts: int,
    mc_iterations: int,
    mc_horizon_days: int,
) -> tuple[list[dict], dict]:
    selected = [dict(cell) for cell in cells]
    rank = 0
    while True:
        adjusted = apply_actions(rows, selected)
        aggregate = summarize_trades(
            adjusted, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days
        )["aggregate"]
        stop_count = sum(1 for cell in selected if cell["action"] == "STOP_OANDA")
        if aggregate["kelly_raw"] >= 0 or stop_count >= max_cuts:
            return selected, aggregate

        candidate = next(
            (
                cell
                for cell in selected
                if cell["action"] == "WATCH" and cell["n"] >= 5 and cell["ev_pips"] < 0
            ),
            None,
        )
        if candidate is None:
            return selected, aggregate
        rank += 1
        candidate["action"] = "STOP_OANDA"
        candidate["reason"] = "counterfactual extension; LOCK threshold not fully met"
        candidate["extension_rank"] = rank


def pgrep_app_py_status() -> str:
    try:
        result = subprocess.run(
            ["pgrep", "-f", "app.py"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
    except Exception as exc:
        return f"sandbox-restricted-fallback ({type(exc).__name__}: {exc})"
    output = (result.stdout or "").strip()
    if result.returncode == 0 and output:
        return f"FOUND pid(s): {output.replace(chr(10), ', ')}"
    err = (result.stderr or "").strip()
    if err:
        return f"sandbox-restricted-fallback ({err.replace(chr(10), '; ')})"
    return "none"


def _fmt_pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _fmt_num(value: float, digits: int = 4) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def _row(cell: dict) -> str:
    ext = "" if cell.get("extension_rank") is None else f"ext#{cell['extension_rank']}"
    return (
        f"| {cell['action']} | {cell['entry_type']} | {cell['instrument']} | {cell['hour_bucket']} | "
        f"{cell['n']} | {_fmt_pct(cell['wr'])} | {_fmt_pct(cell['wilson_lo'])} | "
        f"{cell['ev_pips']:+.2f} | {cell['kelly_raw']:+.4f} | {cell['total_pnl_pips']:+.1f} | "
        f"{_fmt_num(cell['pf'], 3)} | {_fmt_num(cell['bonferroni_p'])} | "
        f"{_fmt_pct(cell['max_dd_pct'])} | {cell['reason']} {ext} |"
    )


def _table(cells: list[dict], *, limit: int = MAX_REPORT_CELLS_PER_SECTION) -> list[str]:
    lines = [
        "| action | entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | raw Kelly | total pip | PF | Bonf p(lower) | max DD | reason |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for cell in cells[:limit]:
        lines.append(_row(cell))
    if len(cells) > limit:
        lines.append(f"| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | {len(cells) - limit} rows omitted |")
    return lines


def _aggregate_line(label: str, agg: dict) -> str:
    return (
        f"{label}: N={agg['n']}, raw Kelly={agg['kelly_raw']:+.4f}, clipped Kelly={agg['kelly']:.4f}, "
        f"MC60d={agg['mc_ruin_60d']:.4f}, EV={agg['ev_pips']:+.2f}p, "
        f"Wilson_lo={agg['wilson_lo']:.4f}, PF={agg['pf']:.3f}, "
        f"maxDD={agg['max_dd_pct']:.4f}, total={agg['total_pnl_pips']:+.1f}p"
    )


def verdict_for(post: dict) -> str:
    if post["kelly_raw"] >= 0:
        return "ACCEPT_GATE_0_RECOVERY"
    if post["kelly_raw"] >= -0.05:
        return "NEEDS_MORE_CUTS"
    return "REJECT_INSUFFICIENT"


def render_report(
    *,
    source_trades: str,
    live_rows: list[dict],
    shadow_rows: list[dict],
    baseline: dict,
    post: dict,
    cells: list[dict],
    m: int,
    mc_iterations: int,
    mc_horizon_days: int,
    max_cuts: int,
    pgrep_status: str,
) -> str:
    stop = [cell for cell in cells if cell["action"] == "STOP_OANDA"]
    lot_half = [cell for cell in cells if cell["action"] == "LOT_HALF"]
    watch = [cell for cell in cells if cell["action"] == "WATCH"]
    keep = [cell for cell in cells if cell["action"] == "KEEP"]
    keep_sig = [
        cell
        for cell in keep
        if cell["bonferroni_upper_p"] <= (0.05 / max(1, m)) or cell["ev_pips"] > 0
    ]
    verdict = verdict_for(post)
    lines = [
        "# R2 cell-level 降格候補 LOCK list - 2026-05-03",
        "",
        f"Counterfactual: aggregate raw Kelly={baseline['kelly_raw']:+.4f}→{post['kelly_raw']:+.4f}, MC60d={baseline['mc_ruin_60d']:.4f}→{post['mc_ruin_60d']:.4f}, STOP_OANDA={len(stop)}件, LOT_HALF={len(lot_half)}件, KEEP={len(keep)}件",
        f"Verdict: {verdict}",
        "",
        "## Source / pre-reg LOCK",
        "",
        f"- 一次ソース: `{source_trades}`",
        "- Live抽出: `is_shadow=0`, `status=CLOSED`, `outcome in (WIN, LOSS, BREAKEVEN)`, `pnl_pips != null`。",
        "- XAU除外: `instrument NOT LIKE 'XAU%'`。",
        f"- Shadow行: {len(shadow_rows)} 件。R2判定・counterfactual集計には混入なし。",
        f"- Live N: {len(live_rows)} / Live期間: {baseline.get('live_start') or 'unknown'} -> {baseline.get('live_end') or 'unknown'}。",
        f"- Bonferroni母数 m pre-reg LOCK: **{m} cell**。alpha'=0.05/{m}={0.05 / max(1, m):.6f}。事後変更なし。",
        f"- MC仕様: iterations={mc_iterations}, horizon={mc_horizon_days}d, bootstrap=Live PnL分布, ruin=peak DD 50% of 1000 pips。",
        f"- `pgrep -f app.py`: {pgrep_status}",
        "- OANDA転送停止・lot変更・本番DB書き込みは未実施。",
        "",
        "## Aggregate counterfactual",
        "",
        _aggregate_line("Aggregate baseline", baseline),
        _aggregate_line("Aggregate post-cut", post),
        "",
        "## STOP_OANDA",
        "",
        *_table(stop),
        "",
        "## LOT_HALF",
        "",
        *_table(lot_half),
        "",
        "## WATCH",
        "",
        *_table(watch),
        "",
        "## KEEP",
        "",
        *_table(keep),
        "",
        "## KEEP protection / feedback_ma_filter_breaks_mr",
        "",
        f"- KEEP cell数: {len(keep)}。EV>0 / Wilson_lo>0.50 / raw Kelly>0 の cell は R2対象外として明示維持。",
        f"- Bonferroni-significant候補またはEV>0のKEEP表示対象: {len(keep_sig)}。",
        "- STOP_OANDA / LOT_HALF の選定は cell 単位で、entry_type 全体停止は提案していない。",
        "",
        *_table(keep_sig, limit=80),
        "",
        "## PR template (司令塔承認後の別PR)",
        "",
        "- branch: `feat/r2-cell-demotion-2026-05-03`",
        "- scope: R2 cell-level OANDA routing override only; no strategy-wide demotion.",
        "- proposed STOP_OANDA: 上表 `STOP_OANDA` cell を `entry_type + instrument + UTC hour_bucket` 条件で lot=0。",
        "- proposed LOT_HALF: 上表 `LOT_HALF` cell を現在 lot x 0.5。",
        "- shadow logging: 継続。Live/OANDA転送のみ停止または半減。",
        "- pre-merge evidence: 本レポート、前段 Gate Progression Audit、司令塔承認コメント。",
        "",
        "## Risks / blockers",
        "",
    ]
    if post["kelly_raw"] < 0:
        lines.append(f"- max_cuts={max_cuts} 適用後も raw Kelly は負。R2 cell cut だけでは Gate 0 復帰不足。")
    if stop and any(cell.get("extension_rank") is not None for cell in stop):
        lines.append("- 一部 STOP_OANDA は counterfactual 復帰用の拡張候補で、LOCK STOP閾値を全て満たすわけではない。司令塔レビュー必須。")
    lines += [
        "- hour_bucket は UTC hour。実装PRでは注文生成時の timestamp 基準と同じ UTC に固定する必要がある。",
        "- LOT_HALF counterfactual は該当 cell の実測 pnl_pips を 0.5 倍して近似。約定品質やスリッページ非線形性は未反映。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mc-iterations", type=int, default=1000)
    parser.add_argument("--mc-horizon", type=int, default=60)
    parser.add_argument("--max-cuts", type=int, default=30)
    args = parser.parse_args()

    if args.mc_iterations < 1000:
        print("MC iterations must be >= 1000", file=sys.stderr)
        return 2
    if args.max_cuts < 1:
        print("max-cuts must be >= 1", file=sys.stderr)
        return 2

    payload = json.loads(Path(args.trades).read_text())
    live_rows = filter_closed_live_trades(payload)
    shadow_rows = filter_closed_shadow_rows(payload)
    baseline = summarize_trades(
        live_rows, mc_iterations=args.mc_iterations, mc_horizon_days=args.mc_horizon
    )["aggregate"]
    cells = build_cell_records(live_rows, mc_horizon_days=args.mc_horizon)
    classified = classify_cells(cells, max_cuts=args.max_cuts)
    selected, post = extend_cuts_until_recovery(
        live_rows,
        classified,
        max_cuts=args.max_cuts,
        mc_iterations=args.mc_iterations,
        mc_horizon_days=args.mc_horizon,
    )
    report = render_report(
        source_trades=args.trades,
        live_rows=live_rows,
        shadow_rows=shadow_rows,
        baseline=baseline,
        post=post,
        cells=selected,
        m=len(cells),
        mc_iterations=args.mc_iterations,
        mc_horizon_days=args.mc_horizon,
        max_cuts=args.max_cuts,
        pgrep_status=pgrep_app_py_status(),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report)

    stop_count = sum(1 for cell in selected if cell["action"] == "STOP_OANDA")
    half_count = sum(1 for cell in selected if cell["action"] == "LOT_HALF")
    keep_count = sum(1 for cell in selected if cell["action"] == "KEEP")
    print(
        f"Counterfactual: aggregate raw Kelly={baseline['kelly_raw']:+.4f}->{post['kelly_raw']:+.4f}, "
        f"MC60d={baseline['mc_ruin_60d']:.4f}->{post['mc_ruin_60d']:.4f}, "
        f"STOP_OANDA={stop_count}, LOT_HALF={half_count}, KEEP={keep_count}"
    )
    print(f"Verdict: {verdict_for(post)}")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
