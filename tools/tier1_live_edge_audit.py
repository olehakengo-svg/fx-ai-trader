#!/usr/bin/env python3
"""Tier 1 LIVE strategy x instrument edge audit.

Read-only Gate 0 rescue audit. It checks the five locked Tier 1 LIVE cells
against production Live/OANDA-filled trades and reports BT-vs-Live deltas.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.edge_discovery.significance import binomial_one_sided_p
from tools.gate_progression_audit import _metrics, _trade_rows, filter_closed_shadow_trades

DEFAULT_TRADES = Path("/tmp/live-trades-20260503.json")
ALT_DEFAULT_TRADES = Path("/tmp/live-trades-tier1.json")
ALPHA0 = 0.05
BONFERRONI_M = 5
ALPHA_PRIME = ALPHA0 / BONFERRONI_M
DECIDED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}

BEV_WR = {
    "USD_JPY": 0.344,
    "EUR_USD": 0.397,
    "GBP_USD": 0.379,
    "EUR_JPY": 0.337,
}

TARGET_CELLS = [
    {
        "strategy": "gbp_deep_pullback",
        "instrument": "GBP_USD",
        "bt_n": 77,
        "bt_wr": 0.75,
        "bt_ev": 1.064,
        "bt_pf": 2.00,
    },
    {
        "strategy": "trendline_sweep",
        "instrument": "GBP_USD",
        "bt_n": 134,
        "bt_wr": 0.73,
        "bt_ev": 0.599,
        "bt_pf": 1.68,
    },
    {
        "strategy": "session_time_bias",
        "instrument": "USD_JPY",
        "bt_n": 157,
        "bt_wr": 0.79,
        "bt_ev": 0.580,
        "bt_pf": 2.46,
    },
    {
        "strategy": "session_time_bias",
        "instrument": "EUR_USD",
        "bt_n": 566,
        "bt_wr": 0.70,
        "bt_ev": 0.215,
        "bt_pf": 1.34,
    },
    {
        "strategy": "xs_momentum",
        "instrument": "USD_JPY",
        "bt_n": 342,
        "bt_wr": 0.69,
        "bt_ev": 0.270,
        "bt_pf": 1.43,
    },
]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _trade_id(row: dict) -> str:
    return str(row.get("trade_id") or row.get("id") or "")


def _cell_key(strategy: str, instrument: str) -> str:
    return f"{strategy}|{instrument}"


def _target_lookup() -> dict[tuple[str, str], dict]:
    return {(row["strategy"], row["instrument"]): row for row in TARGET_CELLS}


def _clean_closed_trade(row: dict) -> dict | None:
    outcome = str(row.get("outcome") or "").upper()
    status = str(row.get("status") or "").upper()
    if status and status != "CLOSED":
        return None
    if outcome not in DECIDED_OUTCOMES:
        return None
    if row.get("pnl_pips") is None:
        return None
    try:
        pnl = float(row.get("pnl_pips"))
    except (TypeError, ValueError):
        return None
    instrument = str(row.get("instrument") or row.get("pair") or "")
    if instrument.startswith("XAU"):
        return None
    clean = dict(row)
    clean["outcome"] = outcome
    clean["status"] = "CLOSED"
    clean["pnl_pips"] = pnl
    clean["entry_type"] = clean.get("entry_type") or clean.get("strategy") or "unknown"
    clean["instrument"] = instrument or "unknown"
    return clean


def has_oanda_fill(row: dict) -> bool:
    return bool(str(row.get("oanda_trade_id") or "").strip())


def filter_closed_oanda_live_trades(payload: Any) -> list[dict]:
    out: list[dict] = []
    for row in _trade_rows(payload):
        if _as_bool(row.get("is_shadow", False)):
            continue
        if not has_oanda_fill(row):
            continue
        clean = _clean_closed_trade(row)
        if clean is not None:
            out.append(clean)
    return out


def oanda_shadow_drift_rows(payload: Any) -> list[dict]:
    out: list[dict] = []
    for row in _trade_rows(payload):
        if not _as_bool(row.get("is_shadow", False)):
            continue
        if not has_oanda_fill(row):
            continue
        clean = _clean_closed_trade(row)
        if clean is not None:
            out.append(clean)
    return out


def load_trade_payload(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def _fmt_pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _fmt_num(value: float, digits: int = 4) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def build_cell_records(live_rows: list[dict], *, mc_horizon_days: int = 60) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    targets = _target_lookup()
    for row in live_rows:
        key = (str(row.get("entry_type") or "unknown"), str(row.get("instrument") or "unknown"))
        if key in targets:
            grouped[key].append(row)

    records: list[dict] = []
    for target in TARGET_CELLS:
        key = (target["strategy"], target["instrument"])
        rows = grouped.get(key, [])
        metrics = _metrics(rows, mc_iterations=100, mc_horizon_days=mc_horizon_days, n_trials=BONFERRONI_M)
        bev_wr = BEV_WR[target["instrument"]]
        raw_p = binomial_one_sided_p(metrics["wins"], metrics["n"], bev_wr) if metrics["n"] else 1.0
        bonf_p = min(1.0, raw_p * BONFERRONI_M)
        accept = (
            metrics["n"] >= 30
            and metrics["wilson_lo"] > bev_wr
            and bonf_p < ALPHA_PRIME
            and metrics["pf"] >= 1.10
        )
        if accept:
            cell_verdict = "ACCEPT_CELL"
        elif 0 < metrics["n"] < 30:
            cell_verdict = "NEEDS_MORE_EVIDENCE"
        elif 30 <= metrics["n"] < 100:
            cell_verdict = "NEEDS_MORE_EVIDENCE"
        else:
            cell_verdict = "REJECT_CELL"
        records.append(
            {
                **target,
                **metrics,
                "cell_id": _cell_key(target["strategy"], target["instrument"]),
                "bev_wr": bev_wr,
                "binomial_raw_p": raw_p,
                "bonferroni_p": bonf_p,
                "alpha_prime": ALPHA_PRIME,
                "delta_wr": metrics["wr"] - target["bt_wr"],
                "delta_ev": metrics["ev_pips"] - target["bt_ev"],
                "delta_pf": metrics["pf"] - target["bt_pf"],
                "accept_cell": accept,
                "cell_verdict": cell_verdict,
                "trade_ids": sorted(_trade_id(row) for row in rows),
            }
        )
    return records


def verdict_for_cells(cells: list[dict]) -> tuple[str, list[str]]:
    accept_cells = [cell for cell in cells if cell["accept_cell"]]
    no_evidence_cells = [cell for cell in cells if cell["n"] < 30]
    n30_cells = [cell for cell in cells if cell["n"] >= 30]
    h3_fired = all(
        cell["wilson_lo"] < cell["bev_wr"]
        or (cell["n"] >= 30 and cell["bonferroni_p"] >= ALPHA_PRIME)
        for cell in cells
    )
    if len(accept_cells) >= 2:
        return "ACCEPT", [f"{len(accept_cells)} cells met Wilson/Bonferroni/PF/N gates"]
    if len(accept_cells) == 1:
        return "NEEDS_MORE_EVIDENCE", ["only 1 cell met ACCEPT_CELL gate; task requires 2"]
    if len(no_evidence_cells) >= 3:
        return "NEEDS_MORE_EVIDENCE", [f"{len(no_evidence_cells)} cells have N<30"]
    if h3_fired and n30_cells:
        return "REJECT", ["H3 fired: no N>=30 cell cleared Wilson/Bonferroni edge gate"]
    return "REJECT", ["no Tier 1 LIVE target cell cleared the required edge gate"]


def aggregate_impact(cells: list[dict], live_rows: list[dict]) -> dict:
    target_ids = {trade_id for cell in cells for trade_id in cell["trade_ids"]}
    target_rows = [row for row in live_rows if _trade_id(row) in target_ids]
    non_target_rows = [row for row in live_rows if _trade_id(row) not in target_ids]
    return {
        "target": _metrics(target_rows, mc_iterations=100, mc_horizon_days=60, n_trials=BONFERRONI_M),
        "non_target": _metrics(non_target_rows, mc_iterations=100, mc_horizon_days=60, n_trials=BONFERRONI_M),
        "all_live": _metrics(live_rows, mc_iterations=100, mc_horizon_days=60, n_trials=BONFERRONI_M),
    }


def _cell_table(cells: list[dict]) -> list[str]:
    lines = [
        "| strategy | instrument | N | WR | BEV_WR | Wilson lo | EV pip | PF | total pip | max DD | raw Kelly | p(edge) | Bonferroni p | delta-from-BT WR | delta-from-BT EV | delta-from-BT PF | verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for cell in cells:
        lines.append(
            f"| {cell['strategy']} | {cell['instrument']} | {cell['n']} | {_fmt_pct(cell['wr'])} | "
            f"{_fmt_pct(cell['bev_wr'])} | {_fmt_pct(cell['wilson_lo'])} | {cell['ev_pips']:+.2f} | "
            f"{_fmt_num(cell['pf'], 3)} | {cell['total_pnl_pips']:+.1f} | {_fmt_pct(cell['max_dd_pct'])} | "
            f"{cell['kelly_raw']:+.4f} | {_fmt_num(cell['binomial_raw_p'])} | {_fmt_num(cell['bonferroni_p'])} | "
            f"{cell['delta_wr']:+.2%} | {cell['delta_ev']:+.2f} | {cell['delta_pf']:+.2f} | {cell['cell_verdict']} |"
        )
    return lines


def _impact_line(name: str, m: dict) -> str:
    return (
        f"| {name} | {m['n']} | {_fmt_pct(m['wr'])} | {m['ev_pips']:+.2f} | "
        f"{m['total_pnl_pips']:+.1f} | {_fmt_num(m['pf'], 3)} | {m['kelly_raw']:+.4f} | "
        f"{_fmt_pct(m['max_dd_pct'])} |"
    )


def render_report(
    *,
    source_trades: str,
    live_rows: list[dict],
    shadow_rows: list[dict],
    drift_rows: list[dict],
    cells: list[dict],
    verdict: str,
    reasons: list[str],
    impact: dict,
) -> str:
    accept_cells = [cell for cell in cells if cell["accept_cell"]]
    lines = [
        "# Tier 1 LIVE edge audit - 2026-05-03",
        "",
        f"Verdict: {verdict}",
        f"ACCEPT cell count: {len(accept_cells)} / {BONFERRONI_M}",
        f"ACCEPT cell list: {', '.join(cell['cell_id'] for cell in accept_cells) if accept_cells else 'none'}",
        "",
        "## Source / separation",
        "",
        f"- 一次ソース: `{source_trades}`",
        "- Live集計: `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status=CLOSED`。",
        "- XAU除外、outcome は WIN/LOSS/BREAKEVEN、`pnl_pips != null`。",
        f"- Live/OANDA closed rows: {len(live_rows)}",
        f"- Shadow rows (closed, FX): {len(shadow_rows)}。Live統計には混入なし。",
        f"- Drift warning rows (`is_shadow=1` and `oanda_trade_id!=''`): {len(drift_rows)}。本タスクのLive集計からは除外。",
        f"- Bonferroni: m={BONFERRONI_M}, alpha'=0.05/5={ALPHA_PRIME:.3f}。本レポートの ACCEPT_CELL は Bonferroni p < {ALPHA_PRIME:.3f} を要求。",
        "",
        "## Verdict rationale",
        "",
        f"- 判定: **{verdict}**",
        f"- 根拠: {'; '.join(reasons)}",
        "- 本監査は LOCK proposal。`app.py` / `modules` / `strategies` / 本番DB / OANDA設定は変更していない。",
        "",
        "## 5 cell delta-from-BT",
        "",
        *_cell_table(cells),
        "",
        "## Aggregate impact estimate",
        "",
        "| bucket | N | WR | EV pip | total pip | PF | raw Kelly | max DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        _impact_line("all Live/OANDA rows", impact["all_live"]),
        _impact_line("Tier 1 target 5 cells only", impact["target"]),
        _impact_line("non-target Live/OANDA rows", impact["non_target"]),
        "",
        "## Next task",
        "",
    ]
    if verdict == "ACCEPT":
        lines.append("- 次タスク: ACCEPT_CELL の lot promotion / routing LOCK proposal。BT-Live delta が大きい cell は lot据え置き。")
    elif verdict == "NEEDS_MORE_EVIDENCE":
        lines.append("- 次タスク: N<30 / N<100 cell の蓄積待ち、または Shadow→Live 通路と `is_shadow` drift の再点検。")
    else:
        lines.append("- 次タスク: Path B `bt-live-divergence.md` 6構造的楽観バイアス audit。Tier 1 LIVE のBT期待がLiveで保持されていない前提で原因分解する。")
    lines.append("")
    return "\n".join(lines)


def run_audit(*, trades_path: str | Path, output_path: str | Path | None = None) -> dict:
    payload = load_trade_payload(trades_path)
    live_rows = filter_closed_oanda_live_trades(payload)
    shadow_rows = filter_closed_shadow_trades(payload)
    drift_rows = oanda_shadow_drift_rows(payload)
    cells = build_cell_records(live_rows)
    verdict, reasons = verdict_for_cells(cells)
    impact = aggregate_impact(cells, live_rows)
    report = render_report(
        source_trades=str(trades_path),
        live_rows=live_rows,
        shadow_rows=shadow_rows,
        drift_rows=drift_rows,
        cells=cells,
        verdict=verdict,
        reasons=reasons,
        impact=impact,
    )
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report)
    return {
        "verdict": verdict,
        "reasons": reasons,
        "cells": cells,
        "impact": impact,
        "report": report,
        "live_rows": live_rows,
        "drift_rows": drift_rows,
    }


def _resolve_default_trades() -> Path:
    if DEFAULT_TRADES.exists():
        return DEFAULT_TRADES
    return ALT_DEFAULT_TRADES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", default=str(_resolve_default_trades()))
    parser.add_argument("--output")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    trades_path = Path(args.trades)
    if not trades_path.exists():
        print(f"trades file not found: {trades_path}", file=sys.stderr)
        return 2

    result = run_audit(trades_path=trades_path, output_path=None if args.dry_run else args.output)
    print(
        f"Grid: target_cells={BONFERRONI_M}, BEV_WR="
        + ", ".join(f"{pair}={_fmt_pct(wr)}" for pair, wr in sorted(BEV_WR.items()))
        + f", alpha_prime={ALPHA_PRIME:.3f}, live_oanda_n={len(result['live_rows'])}"
    )
    print(f"Verdict: {result['verdict']}")
    print(
        "ACCEPT cell list: "
        + (
            ", ".join(cell["cell_id"] for cell in result["cells"] if cell["accept_cell"])
            if any(cell["accept_cell"] for cell in result["cells"])
            else "none"
        )
    )
    for cell in result["cells"]:
        print(
            f"{cell['strategy']} {cell['instrument']} N={cell['n']} WR={_fmt_pct(cell['wr'])} "
            f"Wilson_lo={_fmt_pct(cell['wilson_lo'])} BEV_WR={_fmt_pct(cell['bev_wr'])} "
            f"EV={cell['ev_pips']:+.2f} PF={_fmt_num(cell['pf'], 3)} "
            f"Bonferroni_p={_fmt_num(cell['bonferroni_p'])} "
            f"delta-from-BT WR={cell['delta_wr']:+.2%} EV={cell['delta_ev']:+.2f} PF={cell['delta_pf']:+.2f} "
            f"verdict={cell['cell_verdict']}"
        )
    if args.output and not args.dry_run:
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
