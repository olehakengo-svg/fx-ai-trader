"""Phase A production audit — Agent#3 数値の production API direct read 再検証

Usage:
    python3 tools/phase_a_production_audit.py [--input /tmp/render_trades.json]

Outputs:
    raw/audits/phase_a_production_audit_2026-04-27.{json,md}

目的:
    1. WR<35% AND N>=20 cell リスト (M4 シナリオ C target candidate)
    2. bb_rsi_reversion × USD_JPY × scalp の N/WR/Wlo/ΣR 確定値 (H5 trigger)
    3. aggregate Kelly の production 計測値 (H3 §2 patch 用)
    4. Agent#3 報告との一致率 (一覧表)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def kelly_full(wins: int, losses: int, avg_win_r: float, avg_loss_r: float) -> float:
    n = wins + losses
    if n == 0 or avg_loss_r <= 0:
        return 0.0
    p = wins / n
    b = avg_win_r / avg_loss_r
    if b <= 0:
        return 0.0
    return p - (1 - p) / b


# Agent#3 が報告したと仮定する WR<35% N>=20 cell (大まかな再現)
# 実際の Agent#3 出力ファイル参照可能なら置換
AGENT3_DENY_CELLS_HINT = {
    ("ema_trend_scalp", "USD_JPY", "scalp"),
    ("ema_trend_scalp", "GBP_USD", "scalp"),
    ("ema_trend_scalp", "EUR_USD", "scalp"),
    ("stoch_trend_pullback", "USD_JPY", "scalp"),
    ("sr_channel_reversal", "USD_JPY", "scalp"),
}

AGENT3_BB_RSI_LIVE = {
    "cell": ("bb_rsi_reversion", "USD_JPY", "scalp"),
    "claimed_N": 74,
    "claimed_WR": 0.446,
    "claimed_Wlo": 0.338,
    "claimed_sum_R": 7.21,
}


def parse_dt(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/tmp/render_trades_v2.json")
    parser.add_argument(
        "--cutoff",
        default="2026-04-16",
        help="post-cutoff date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        default="raw/audits",
    )
    args = parser.parse_args()

    cutoff_dt = datetime.strptime(args.cutoff, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    with open(args.input) as f:
        data = json.load(f)
    trades = data.get("trades", [])

    # Cell aggregation: (entry_type, instrument, mode) for closed Live trades
    cells = defaultdict(list)
    for t in trades:
        if t.get("is_shadow") != 0:
            continue
        outcome = (t.get("outcome") or "").upper()
        if outcome not in ("WIN", "LOSS"):
            continue
        ts = parse_dt(t.get("created_at"))
        if not ts or ts < cutoff_dt:
            continue
        key = (t.get("entry_type"), t.get("instrument"), t.get("mode"))
        cells[key].append(t)

    # Compute per-cell metrics
    rows = []
    for key, ts in cells.items():
        wins = sum(1 for t in ts if (t.get("outcome") or "").upper() == "WIN")
        losses = sum(1 for t in ts if (t.get("outcome") or "").upper() == "LOSS")
        n = wins + losses
        sum_pips = sum(float(t.get("pnl_pips") or 0) for t in ts)
        sum_r = sum(float(t.get("pnl_r") or 0) for t in ts)
        wr = wins / n if n else 0
        wlo = wilson_lower(wins, n)
        avg_win_r = (
            sum(float(t.get("pnl_r") or 0) for t in ts if (t.get("outcome") or "").upper() == "WIN")
            / wins
            if wins
            else 0
        )
        avg_loss_abs_r = (
            -sum(float(t.get("pnl_r") or 0) for t in ts if (t.get("outcome") or "").upper() == "LOSS")
            / losses
            if losses
            else 0
        )
        kelly = kelly_full(wins, losses, avg_win_r, avg_loss_abs_r)
        rows.append(
            {
                "cell": list(key),
                "N": n,
                "wins": wins,
                "losses": losses,
                "WR": round(wr, 4),
                "Wilson_lo": round(wlo, 4),
                "sum_pips": round(sum_pips, 2),
                "sum_R": round(sum_r, 4),
                "kelly": round(kelly, 4),
            }
        )

    rows.sort(key=lambda r: -r["N"])

    # Report 1: WR<35% AND N>=20 cells (Live)
    deny_candidates = [r for r in rows if r["WR"] < 0.35 and r["N"] >= 20]

    # Report 2: bb_rsi_reversion × USD_JPY × scalp Live (and scalp_5m)
    bb_rsi_cells = [r for r in rows if r["cell"][0] == "bb_rsi_reversion" and r["cell"][1] == "USD_JPY"]

    # Report 3: aggregate Live Kelly
    total_n = sum(r["N"] for r in rows)
    total_sum_r = sum(r["sum_R"] for r in rows)
    avg_r_per_trade = total_sum_r / total_n if total_n else 0

    # Aggregate Kelly via wins/losses sum
    total_wins = sum(r["wins"] for r in rows)
    total_losses = sum(r["losses"] for r in rows)
    total_avg_win_r = (
        sum(
            float(t.get("pnl_r") or 0)
            for ts in cells.values()
            for t in ts
            if (t.get("outcome") or "").upper() == "WIN"
        )
        / total_wins
        if total_wins
        else 0
    )
    total_avg_loss_r = (
        -sum(
            float(t.get("pnl_r") or 0)
            for ts in cells.values()
            for t in ts
            if (t.get("outcome") or "").upper() == "LOSS"
        )
        / total_losses
        if total_losses
        else 0
    )
    aggregate_kelly = kelly_full(total_wins, total_losses, total_avg_win_r, total_avg_loss_r)

    # Report 4: Agent#3 hinted DENY cells comparison
    deny_compare = []
    for hint_cell in AGENT3_DENY_CELLS_HINT:
        match = next((r for r in rows if tuple(r["cell"]) == hint_cell), None)
        deny_compare.append(
            {
                "cell": list(hint_cell),
                "agent3_hint_present": True,
                "production": match,
            }
        )

    # Output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = output_dir / f"phase_a_production_audit_{today}"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": args.input,
        "cutoff": args.cutoff,
        "total_live_closed_trades": total_n,
        "aggregate_kelly_live": round(aggregate_kelly, 4),
        "aggregate_avg_R_per_trade": round(avg_r_per_trade, 4),
        "aggregate_wins": total_wins,
        "aggregate_losses": total_losses,
        "deny_candidates_WR_lt_35_N_ge_20": deny_candidates,
        "bb_rsi_reversion_USDJPY_cells": bb_rsi_cells,
        "agent3_deny_compare": deny_compare,
        "all_cells_top20_by_N": rows[:20],
    }

    with open(f"{base}.json", "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Markdown report
    md = []
    md.append(f"# Phase A Production Audit — {today}")
    md.append("")
    md.append(f"**Input**: `{args.input}`")
    md.append(f"**Cutoff**: post-{args.cutoff}, is_shadow=0, outcome WIN/LOSS only")
    md.append("")
    md.append("## 1. Aggregate Live Kelly")
    md.append("")
    md.append(f"- N (Live closed) = {total_n}")
    md.append(f"- Wins = {total_wins} / Losses = {total_losses}")
    md.append(f"- Avg R per trade = {avg_r_per_trade:+.4f}")
    md.append(f"- **Aggregate Kelly (full) = {aggregate_kelly:+.4f}**")
    md.append("")
    md.append("**Agent#3 比較**: 報告 Live Kelly = +0.0157 (Gate 1 通過)")
    md.append("- 一致条件: 本数字 >= +0.005 ならば Agent#3 と同方向")
    md.append("")
    md.append("## 2. WR<35% AND N>=20 Live cells (M4 deny candidates)")
    md.append("")
    if deny_candidates:
        md.append("| cell | N | WR | Wilson_lo | sum_R | sum_pips | kelly |")
        md.append("|---|---:|---:|---:|---:|---:|---:|")
        for r in deny_candidates:
            cell = " × ".join(r["cell"])
            md.append(
                f"| {cell} | {r['N']} | {r['WR']*100:.1f}% | {r['Wilson_lo']*100:.1f}% | "
                f"{r['sum_R']:+.2f} | {r['sum_pips']:+.1f} | {r['kelly']:+.3f} |"
            )
    else:
        md.append("**(該当 cell ゼロ)**")
    md.append("")
    md.append("## 3. bb_rsi_reversion × USD_JPY × {scalp, scalp_5m} Live")
    md.append("")
    if bb_rsi_cells:
        md.append("| mode | N | WR | Wilson_lo | sum_R | sum_pips |")
        md.append("|---|---:|---:|---:|---:|---:|")
        for r in bb_rsi_cells:
            md.append(
                f"| {r['cell'][2]} | {r['N']} | {r['WR']*100:.1f}% | {r['Wilson_lo']*100:.1f}% | "
                f"{r['sum_R']:+.2f} | {r['sum_pips']:+.1f} |"
            )
    md.append("")
    md.append(
        f"**Agent#3 報告 (claimed)**: N={AGENT3_BB_RSI_LIVE['claimed_N']}, "
        f"WR={AGENT3_BB_RSI_LIVE['claimed_WR']*100:.1f}%, "
        f"Wlo={AGENT3_BB_RSI_LIVE['claimed_Wlo']*100:.1f}%, "
        f"sum_R={AGENT3_BB_RSI_LIVE['claimed_sum_R']:+.2f}"
    )
    md.append("")
    md.append("## 4. Agent#3 hinted DENY cells comparison")
    md.append("")
    md.append("| cell | production_N | production_WR | matches_hint? |")
    md.append("|---|---:|---:|:-:|")
    for c in deny_compare:
        prod = c["production"]
        if prod:
            cell = " × ".join(c["cell"])
            wr_pt = prod["WR"] * 100
            matches = "✓" if (prod["WR"] < 0.35 and prod["N"] >= 20) else "✗"
            md.append(f"| {cell} | {prod['N']} | {wr_pt:.1f}% | {matches} |")
        else:
            cell = " × ".join(c["cell"])
            md.append(f"| {cell} | (no production data) | — | ✗ |")
    md.append("")
    md.append("## 5. Top 20 Live cells by N")
    md.append("")
    md.append("| cell | N | WR | Wilson_lo | sum_R | kelly |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for r in rows[:20]:
        cell = " × ".join(r["cell"])
        md.append(
            f"| {cell} | {r['N']} | {r['WR']*100:.1f}% | {r['Wilson_lo']*100:.1f}% | "
            f"{r['sum_R']:+.2f} | {r['kelly']:+.3f} |"
        )
    md.append("")
    md.append("---")
    md.append("")
    md.append(
        "本 audit は production /api/demo/trades?limit=2000 直接 read。"
        "Agent#3 の集計が local DB の古い snapshot を使っている可能性ありで、"
        "両方の結果を cell-by-cell 比較するための fact-check 用。"
    )

    with open(f"{base}.md", "w") as f:
        f.write("\n".join(md))

    print(f"WROTE: {base}.json")
    print(f"WROTE: {base}.md")
    print()
    print(f"=== KEY METRICS ===")
    print(f"Total Live closed: N={total_n}")
    print(f"Aggregate Kelly: {aggregate_kelly:+.4f} (Agent#3: +0.0157)")
    print(f"Deny candidates (WR<35%, N>=20): {len(deny_candidates)} cells")
    print(f"bb_rsi USDJPY cells: {len(bb_rsi_cells)}")


if __name__ == "__main__":
    main()
