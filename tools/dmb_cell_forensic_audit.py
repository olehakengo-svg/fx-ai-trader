#!/usr/bin/env python3
"""Read-only DMB Shadow cell forensic audit.

This tool implements the SQL/metric contract from
.ai/tasks/queue/20260528-0454-donchian-momentum-breakout-cell-forensic.md.
It never writes to SQLite; the only write target is the requested Markdown
report path.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STRATEGY = "donchian_momentum_breakout"
DEFAULT_DB = "/var/data/demo_trades.db"


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def pf(pnls: list[float]) -> float | None:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss <= 0:
        return math.inf if gross_profit > 0 else None
    return gross_profit / gross_loss


def kelly(wins: int, pnls: list[float]) -> float | None:
    n = len(pnls)
    losses = [-p for p in pnls if p < 0]
    gains = [p for p in pnls if p > 0]
    if n == 0 or not losses or not gains:
        return None
    wr = wins / n
    payoff = (sum(gains) / len(gains)) / (sum(losses) / len(losses))
    if payoff <= 0:
        return None
    return wr - ((1 - wr) / payoff)


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    return f"{float(value):.{digits}f}"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def day_name(value: str | None) -> str:
    ts = parse_time(value)
    return "unknown" if ts is None else str(ts.weekday())


def hour(value: str | None) -> str:
    ts = parse_time(value)
    return "unknown" if ts is None else f"{ts.hour:02d}"


def pip_mult(instrument: str | None) -> int:
    return 100 if (instrument or "").upper().endswith("_JPY") else 10000


def tp_sl_distance(row: sqlite3.Row) -> tuple[float | None, float | None]:
    entry = row["entry_price"]
    tp_v = row["tp"]
    sl_v = row["sl"]
    mult = pip_mult(row["instrument"])
    tp_dist = abs(float(tp_v) - float(entry)) * mult if entry is not None and tp_v is not None else None
    sl_dist = abs(float(sl_v) - float(entry)) * mult if entry is not None and sl_v is not None else None
    return tp_dist, sl_dist


def connect_ro(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    uri = f"file:{path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT trade_id, status, direction, entry_price, entry_time, exit_price,
               exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
               confidence, tf, reasons, regime, dow_regime, v2_regime,
               edge_cell_id, close_reason, mode, instrument, signal_price,
               spread_at_entry, spread_at_exit, slippage_pips, close_analysis,
               mafe_adverse_pips, mafe_favorable_pips, is_shadow, created_at
        FROM demo_trades
        WHERE entry_type = ? AND status = 'CLOSED'
        ORDER BY entry_time, trade_id
        """,
        (STRATEGY,),
    ).fetchall()


def fetch_audit_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT bridge_status, is_live, COUNT(*) AS n
        FROM oanda_audit
        WHERE entry_type = ?
        GROUP BY bridge_status, is_live
        ORDER BY bridge_status, is_live
        """,
        (STRATEGY,),
    ).fetchall()


def summarize(rows: list[sqlite3.Row]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "by_shadow": {},
        "shadow_period": {},
        "cells": {},
        "live_cells": {},
    }
    for shadow in (0, 1):
        cohort = [r for r in rows if int(r["is_shadow"] or 0) == shadow]
        pnls = [float(r["pnl_pips"] or 0.0) for r in cohort]
        wins = sum(1 for p in pnls if p > 0)
        out["by_shadow"][shadow] = {
            "n": len(cohort),
            "wins": wins,
            "wr": wins / len(cohort) if cohort else None,
            "ev": sum(pnls) / len(pnls) if pnls else None,
            "total": sum(pnls),
        }

    shadow_rows = [r for r in rows if int(r["is_shadow"] or 0) == 1]
    times = [parse_time(r["entry_time"]) for r in shadow_rows]
    times = [t for t in times if t is not None]
    now = datetime.now(timezone.utc)
    out["shadow_period"] = {
        "first": min(times).isoformat() if times else None,
        "last": max(times).isoformat() if times else None,
        "n_30d": sum(1 for t in times if (now - t).days < 30),
        "n_7d": sum(1 for t in times if (now - t).days < 7),
        "n_24h": sum(1 for t in times if (now - t).total_seconds() < 86400),
    }

    def add_cells(target: dict, cohort: list[sqlite3.Row]) -> None:
        grouped: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
        for row in cohort:
            grouped[(row["instrument"] or "UNKNOWN", (row["direction"] or "?").upper())].append(row)
        m = len(grouped)
        z_bf = 1.959963984540054 if m <= 1 else normal_quantile(1 - (0.05 / m) / 2)
        for key, cell_rows in grouped.items():
            pnls = [float(r["pnl_pips"] or 0.0) for r in cell_rows]
            wins = sum(1 for p in pnls if p > 0)
            close_counts = Counter((r["close_reason"] or "UNKNOWN") for r in cell_rows)
            target[key] = {
                "rows": cell_rows,
                "n": len(cell_rows),
                "wins": wins,
                "wr": wins / len(cell_rows) if cell_rows else 0.0,
                "ev": sum(pnls) / len(pnls) if pnls else 0.0,
                "total": sum(pnls),
                "pf": pf(pnls),
                "kelly": kelly(wins, pnls),
                "wilson_lo": wilson_lower(wins, len(cell_rows)),
                "wilson_bf_lo": wilson_lower(wins, len(cell_rows), z=z_bf),
                "close_counts": close_counts,
                "tp_ratio": close_counts.get("TAKE_PROFIT", 0) / len(cell_rows) if cell_rows else 0.0,
            }
        target["_m"] = m

    add_cells(out["cells"], shadow_rows)
    add_cells(out["live_cells"], [r for r in rows if int(r["is_shadow"] or 0) == 0])
    return out


def normal_quantile(p: float) -> float:
    """Acklam inverse-normal approximation."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687,
         138.3577518672690, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866,
         66.80131188771972, -13.28068155288572]
    c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996,
         3.754408661907416]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def cohort_split(cell_rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    ordered = sorted(cell_rows, key=lambda r: (r["entry_time"] or "", r["trade_id"] or ""))
    half_point = len(ordered) // 2
    parts = [("first_half", ordered[:half_point]), ("second_half", ordered[half_point:])]
    out = []
    for label, rows in parts:
        pnls = [float(r["pnl_pips"] or 0.0) for r in rows]
        wins = sum(1 for p in pnls if p > 0)
        out.append({
            "half": label,
            "n": len(rows),
            "wins": wins,
            "wr": wins / len(rows) if rows else None,
            "ev": sum(pnls) / len(pnls) if pnls else None,
            "total": sum(pnls),
        })
    return out


def structural_distance(cell_rows: list[sqlite3.Row]) -> dict[str, Any]:
    rows = []
    for row in cell_rows:
        tp_dist, sl_dist = tp_sl_distance(row)
        rows.append((row, tp_dist, sl_dist))
    valid_tp = [tp_dist for _, tp_dist, _ in rows if tp_dist is not None]
    mfes = [float(r["mafe_favorable_pips"] or 0.0) for r, _, _ in rows]
    maes = [abs(float(r["mafe_adverse_pips"] or 0.0)) for r, _, _ in rows]
    avg_tp = sum(valid_tp) / len(valid_tp) if valid_tp else None
    avg_mfe = sum(mfes) / len(mfes) if mfes else None
    avg_mae = sum(maes) / len(maes) if maes else None
    ratio = (avg_mfe / avg_tp) if avg_tp and avg_mfe is not None else None
    return {
        "rows": rows,
        "avg_tp_dist": avg_tp,
        "avg_mfe": avg_mfe,
        "avg_mae": avg_mae,
        "mfe_tp_ratio": ratio,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return lines


def reason_key_scan(rows: list[sqlite3.Row]) -> tuple[list[str], dict[str, Counter]]:
    keys: Counter[str] = Counter()
    bucket_counts: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        raw = row["reasons"]
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(parsed, dict):
            continue
        for key, value in parsed.items():
            keys[key] += 1
            if key in {"adx", "adx_at_entry", "range_width_atr", "htf_agreement"}:
                bucket_counts[key][str(value)] += 1
    return [k for k, _ in keys.most_common()], bucket_counts


def build_report(db_path: str, rows: list[sqlite3.Row], audit_rows: list[sqlite3.Row]) -> str:
    s = summarize(rows)
    shadow_n = s["by_shadow"][1]["n"]
    lines = [
        f"# {STRATEGY} cell-level Win/Loss forensic audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"DB: `{db_path}` opened with `mode=ro`",
        "",
        "## Result",
        "",
    ]
    if shadow_n < 30:
        lines.append(f"- Shadow N={shadow_n} < 30: cell分解は試行のみ。判定は蓄積不足として扱う。")
    period = s["shadow_period"]
    if period["n_7d"] == 0 and period["n_30d"] > 10:
        lines.append("- Rule 4: 直近7d Shadow N=0 かつ 30d N>10。silent block疑い。")
    lines.extend(["", "## Phase A reconciliation matrix", ""])
    rows_a = []
    for shadow in (1, 0):
        item = s["by_shadow"][shadow]
        rows_a.append([shadow, item["n"], item["wins"], pct(item["wr"]), num(item["ev"], 3), num(item["total"], 1)])
    lines.extend(markdown_table(["is_shadow", "N", "wins", "WR", "EV pips", "total pips"], rows_a))
    lines.extend(["", f"- Shadow first_t: `{period['first']}`", f"- Shadow last_t: `{period['last']}`"])
    lines.append(f"- Shadow recent N: 30d={period['n_30d']}, 7d={period['n_7d']}, 24h={period['n_24h']}")
    lines.extend(["", "### oanda_audit bridge_status", ""])
    lines.extend(markdown_table(["bridge_status", "is_live", "N"], [[r["bridge_status"], r["is_live"], r["n"]] for r in audit_rows] or [["none", "n/a", 0]]))

    lines.extend(["", "## Phase B per-cell stats table", ""])
    cell_items = [(k, v) for k, v in s["cells"].items() if k != "_m"]
    cell_items.sort(key=lambda kv: kv[1]["total"], reverse=True)
    rows_b = []
    for (instrument, direction), item in cell_items:
        rows_b.append([
            instrument, direction, item["n"], item["wins"], pct(item["wr"]), num(item["ev"]),
            num(item["total"], 1), num(item["pf"]), pct(item["kelly"]), pct(item["wilson_lo"]),
            pct(item["wilson_bf_lo"]), ", ".join(f"{k}:{v}" for k, v in item["close_counts"].items()),
        ])
    lines.append(f"Bonferroni m={s['cells'].get('_m', 0)}")
    lines.extend(markdown_table(
        ["instrument", "direction", "N", "wins", "WR", "EV", "total", "PF", "Kelly", "Wilson_lo", "Wilson_bf_lo", "close_reason"],
        rows_b or [["none", "n/a", 0, 0, "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
    ))

    if cell_items:
        top = max(cell_items, key=lambda kv: kv[1]["ev"] * kv[1]["n"])
        lose = min(cell_items, key=lambda kv: kv[1]["ev"] * kv[1]["n"])
        lines.extend(deep_dive_winning(top, s["cells"].get("_m", 0)))
        lines.extend(deep_dive_losing(lose))
    else:
        lines.extend(["", "## Phase C top-winning cell deep-dive", "", "SKIP: Shadow cell rows not available."])
        lines.extend(["", "## Phase D top-losing cell deep-dive", "", "SKIP: Shadow cell rows not available."])

    lines.extend(["", "## Phase E Shadow vs Live divergence", ""])
    live_rows = []
    live_map = {k: v for k, v in s["live_cells"].items() if k != "_m"}
    for key, live in sorted(live_map.items()):
        if live["n"] < 5:
            continue
        shadow = s["cells"].get(key)
        wr_diff = None if not shadow else abs(live["wr"] - shadow["wr"])
        live_rows.append([key[0], key[1], live["n"], pct(live["wr"]), num(live["ev"]), pct(wr_diff)])
    if live_rows:
        lines.extend(markdown_table(["instrument", "direction", "Live N", "Live WR", "Live EV", "WR diff vs shadow"], live_rows))
        if any((float(str(r[5]).strip("%")) if r[5] != "n/a" else 0.0) >= 20.0 for r in live_rows):
            lines.append("- Rule 3: WR diff >= 20pt の cell あり。R3 simulator divergence hot-fix候補。")
    else:
        lines.append("SKIP: Live N>=5/cell の cohortなし。ShadowとLiveは混合していない。")

    lines.extend(["", "## Phase F reasons/regime label split", ""])
    reason_keys, bucket_counts = reason_key_scan([r for r in rows if int(r["is_shadow"] or 0) == 1])
    if reason_keys:
        lines.append(f"- reasons JSON keys observed: `{', '.join(reason_keys[:20])}`")
        for key, counts in bucket_counts.items():
            lines.append(f"- {key}: " + ", ".join(f"{k}={v}" for k, v in counts.most_common(10)))
    else:
        lines.append("SKIP: reasons JSONが空またはparse不可。")

    lines.extend(recommendation(s, cell_items))
    lines.extend(memory_draft(s, cell_items))
    return "\n".join(lines) + "\n"


def deep_dive_winning(top: tuple[tuple[str, str], dict[str, Any]], m: int) -> list[str]:
    (instrument, direction), item = top
    lines = ["", "## Phase C top-winning cell deep-dive", ""]
    lines.append(f"Top cell by EV*N: `{instrument}/{direction}` (m={m})")
    lines.extend(markdown_table(
        ["trade_id", "entry_time", "exit_time", "pnl", "close_reason", "MFE", "MAE", "spread", "slip", "regime", "dow", "v2"],
        [[
            r["trade_id"], r["entry_time"], r["exit_time"], num(r["pnl_pips"]), r["close_reason"],
            num(r["mafe_favorable_pips"]), num(r["mafe_adverse_pips"]), num(r["spread_at_entry"], 3),
            num(r["slippage_pips"], 3), r["regime"] or "", r["dow_regime"] or "", r["v2_regime"] or "",
        ] for r in item["rows"]],
    ))
    by_hour: dict[str, list[float]] = defaultdict(list)
    by_dow: dict[str, list[float]] = defaultdict(list)
    for r in item["rows"]:
        pnl = float(r["pnl_pips"] or 0.0)
        by_hour[hour(r["entry_time"])].append(pnl)
        by_dow[day_name(r["entry_time"])].append(pnl)
    lines.extend(["", "### Hour split"])
    lines.extend(metric_table_for_groups(by_hour))
    lines.extend(["", "### Day-of-week split"])
    lines.extend(metric_table_for_groups(by_dow))
    cohorts = cohort_split(item["rows"])
    lines.extend(["", "### Time cohort split"])
    lines.extend(markdown_table(["half", "N", "wins", "WR", "EV", "total"], [
        [c["half"], c["n"], c["wins"], pct(c["wr"]), num(c["ev"]), num(c["total"], 1)] for c in cohorts
    ]))
    same_sign = all(c["ev"] is not None and c["ev"] >= 0 for c in cohorts) or all(c["ev"] is not None and c["ev"] <= 0 for c in cohorts)
    criteria = [
        ("N >= 30", item["n"] >= 30),
        ("Wilson_bf_lo >= 0.50", item["wilson_bf_lo"] >= 0.50),
        ("avg_pips >= +1.0", item["ev"] >= 1.0),
        ("time cohort WR>=45% and EV same sign", all((c["wr"] or 0) >= 0.45 for c in cohorts) and same_sign),
        ("TAKE_PROFIT ratio >= 20%", item["tp_ratio"] >= 0.20),
    ]
    passed = sum(1 for _, ok in criteria if ok)
    verdict = "ACCEPT" if passed == 5 else "NEEDS_MORE_EVIDENCE" if passed >= 3 else "REJECT"
    lines.extend(["", f"Rule 1 verdict: **{verdict}** ({passed}/5)"])
    lines.extend([f"- {name}: {'PASS' if ok else 'FAIL'}" for name, ok in criteria])
    return lines


def metric_table_for_groups(groups: dict[str, list[float]]) -> list[str]:
    rows = []
    for key, pnls in sorted(groups.items()):
        wins = sum(1 for p in pnls if p > 0)
        rows.append([key, len(pnls), wins, pct(wins / len(pnls) if pnls else None), num(sum(pnls) / len(pnls) if pnls else None)])
    return markdown_table(["bucket", "N", "wins", "WR", "EV"], rows or [["none", 0, 0, "n/a", "n/a"]])


def deep_dive_losing(lose: tuple[tuple[str, str], dict[str, Any]]) -> list[str]:
    (instrument, direction), item = lose
    sd = structural_distance(item["rows"])
    lines = ["", "## Phase D top-losing cell deep-dive", ""]
    lines.append(f"Worst cell by EV*N: `{instrument}/{direction}`")
    lines.extend(markdown_table(
        ["trade_id", "dir", "tp_dist", "sl_dist", "pnl", "close_reason", "MFE", "MAE", "spread", "slip"],
        [[
            r["trade_id"], r["direction"], num(tp_dist, 1), num(sl_dist, 1), num(r["pnl_pips"]),
            r["close_reason"], num(r["mafe_favorable_pips"]), num(r["mafe_adverse_pips"]),
            num(r["spread_at_entry"], 3), num(r["slippage_pips"], 3),
        ] for r, tp_dist, sl_dist in sd["rows"]],
    ))
    lines.append(f"- avg_mfe / avg_tp_dist_pip = {num(sd['mfe_tp_ratio'], 3)}")
    if sd["mfe_tp_ratio"] is not None and sd["mfe_tp_ratio"] < 0.5:
        lines.append("- 判定: そもそも順行しないタイプ。signal方向またはfilter不足疑い。")
    elif sd["mfe_tp_ratio"] is not None and sd["mfe_tp_ratio"] >= 0.7 and item["tp_ratio"] < 0.2:
        lines.append("- 判定: 近づくが届かないタイプ。TP距離またはtrail設計疑い。")
    else:
        lines.append("- 判定: N/分布確認が必要。単独で設計欠陥確定までは不可。")
    if item["wr"] < 0.30 and sd["avg_mae"] is not None and sd["avg_mfe"] is not None and sd["avg_mae"] > sd["avg_mfe"] * 2:
        lines.append("- 方向判定崩壊条件: PASS (WR<30% and MAE>MFE*2)")
    return lines


def recommendation(s: dict[str, Any], cell_items: list[tuple[tuple[str, str], dict[str, Any]]]) -> list[str]:
    lines = ["", "## Recommend", ""]
    qualified = []
    for key, item in cell_items:
        cohorts = cohort_split(item["rows"])
        same_sign = all(c["ev"] is not None and c["ev"] >= 0 for c in cohorts) or all(c["ev"] is not None and c["ev"] <= 0 for c in cohorts)
        passed = [
            item["n"] >= 30,
            item["wilson_bf_lo"] >= 0.50,
            item["ev"] >= 1.0,
            all((c["wr"] or 0) >= 0.45 for c in cohorts) and same_sign,
            item["tp_ratio"] >= 0.20,
        ]
        if sum(passed) == 5:
            qualified.append((key, item))
    if qualified:
        for (instrument, direction), item in qualified:
            lines.append(f"- single-cell shadow promote候補: `{instrument}/{direction}` N={item['n']} EV={num(item['ev'])} Wilson_bf_lo={pct(item['wilson_bf_lo'])}")
        lines.append("- config変更は本タスク外。別PRで strategy cell gate を追加すること。")
    else:
        max_bf = max((item["wilson_bf_lo"] for _, item in cell_items), default=0.0)
        if max_bf <= 0.40:
            lines.append("- FORCE_DEMOTED維持。全cellで Wilson_bf_lo > 0.40 が未確認。")
        else:
            lines.append("- single-cell promote候補なし。Shadow継続またはredesign queue投入。")
    lines.append("- Live tier/config変更は未実施。")
    return lines


def memory_draft(s: dict[str, Any], cell_items: list[tuple[tuple[str, str], dict[str, Any]]]) -> list[str]:
    lines = ["", "## MEMORY 更新提案 draft", ""]
    lines.append("project_donchian_momentum_breakout_cell_audit_2026_05_28.md:")
    lines.append(f"- DMB Shadow forensic audit: Shadow N={s['by_shadow'][1]['n']}, Live N={s['by_shadow'][0]['n']}, cells={s['cells'].get('_m', 0)}.")
    if cell_items:
        best = max(cell_items, key=lambda kv: kv[1]["ev"] * kv[1]["n"])
        worst = min(cell_items, key=lambda kv: kv[1]["ev"] * kv[1]["n"])
        lines.append(f"- Best EV*N cell: {best[0][0]}/{best[0][1]} EV={num(best[1]['ev'])}, N={best[1]['n']}, Wilson_bf_lo={pct(best[1]['wilson_bf_lo'])}.")
        lines.append(f"- Worst EV*N cell: {worst[0][0]}/{worst[0][1]} EV={num(worst[1]['ev'])}, N={worst[1]['n']}.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        conn = connect_ro(args.db)
    except FileNotFoundError as exc:
        print(f"BLOCKED: {exc}")
        print("Required evidence: read-only access to /var/data/demo_trades.db or an explicit production snapshot path.")
        return 2
    try:
        rows = fetch_rows(conn)
        audit_rows = fetch_audit_rows(conn)
    finally:
        conn.close()
    report = build_report(args.db, rows, audit_rows)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"wrote {out} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
