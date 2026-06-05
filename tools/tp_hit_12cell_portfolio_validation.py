#!/usr/bin/env python3
"""TP-HIT 12-cell pre-registered portfolio validation.

Primary estimator is Render Production demo_trades.db. The script can either
fetch via Render SSH or consume an exported CSV with the required columns.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import shutil
import statistics
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


FROZEN_CELLS: Tuple[Tuple[str, str, str], ...] = (
    ("dt_bb_rsi_mr", "EUR_USD", "SELL"),
    ("dt_sr_channel_reversal", "USD_JPY", "BUY"),
    ("dt_bb_rsi_mr", "GBP_USD", "SELL"),
    ("wick_imbalance_reversion", "EUR_USD", "BUY"),
    ("sr_fib_confluence", "EUR_USD", "BUY"),
    ("orb_trap", "GBP_USD", "SELL"),
    ("wick_imbalance_reversion", "GBP_USD", "BUY"),
    ("trendline_sweep", "EUR_USD", "SELL"),
    ("dual_sr_bounce", "EUR_JPY", "SELL"),
    ("sr_anti_hunt_bounce", "EUR_JPY", "BUY"),
    ("dt_sr_channel_reversal", "EUR_JPY", "BUY"),
    ("rsk_gbpjpy_reversion", "GBP_JPY", "BUY"),
)

DEFAULT_JSON = Path("bt-results/tp-hit-12cell-portfolio-2026-06-05.json")
DEFAULT_RUN_REPORT = Path("final.md")
COHORT_CUT = "2026-05-16"
BONFERRONI_Z = 3.52
PROD_API = "https://fx-ai-trader.onrender.com/api/demo/trades"
MASSIVE_TFS = ("5m", "15m", "1h")


def cell_id(entry_type: str, instrument: str, direction: str) -> str:
    return f"{entry_type}|{instrument}|{direction}"


def _safe_float(value) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _day(value: str) -> str:
    return str(value or "")[:10]


def _wilson_lower(wins: int, n: int, z: float) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    adj = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n)
    return max(0.0, (centre - adj) / denom)


def _profit_factor(pnls: Sequence[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _bootstrap_ci(pnls: Sequence[float], n_boot: int, seed: int) -> Dict[str, float | None]:
    if not pnls:
        return {"low": None, "high": None}
    rng = random.Random(seed)
    n = len(pnls)
    means = []
    for _ in range(n_boot):
        sample = [pnls[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    low_i = int(0.025 * n_boot)
    high_i = min(n_boot - 1, int(0.975 * n_boot))
    return {"low": round(means[low_i], 6), "high": round(means[high_i], 6)}


def _max_drawdown(values: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def _cohort_stats(rows: Sequence[Mapping[str, object]]) -> Dict[str, float | int | None]:
    pnls = [_safe_float(r.get("pnl_pips")) for r in rows]
    wins = sum(1 for p in pnls if p > 0)
    return {
        "n": len(pnls),
        "wins": wins,
        "wr": round(wins / len(pnls), 6) if pnls else None,
        "ev": round(sum(pnls) / len(pnls), 6) if pnls else None,
    }


def _walk_forward(rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    ordered = sorted(rows, key=lambda r: str(r.get("exit_time") or ""))
    n = len(ordered)
    folds = []
    if n == 0:
        return {"fold_count": 0, "positive_ev_folds": 0, "folds": [], "sign_test_p": None, "sign_consistent": False}
    for i in range(3):
        start = (n * i) // 3
        end = (n * (i + 1)) // 3
        fold_rows = ordered[start:end]
        pnls = [_safe_float(r.get("pnl_pips")) for r in fold_rows]
        ev = sum(pnls) / len(pnls) if pnls else 0.0
        folds.append({"fold": i + 1, "n": len(pnls), "ev": round(ev, 6), "positive_ev": ev > 0})
    positive = sum(1 for f in folds if f["positive_ev"])
    # One-sided sign test under p=0.5 for at least observed positives in 3 folds.
    sign_p = sum(math.comb(3, k) * (0.5 ** 3) for k in range(positive, 4))
    return {
        "fold_count": 3,
        "positive_ev_folds": positive,
        "folds": folds,
        "sign_test_p": round(sign_p, 6),
        "sign_consistent": positive == 3,
    }


def compute_cell_stats(
    entry_type: str,
    instrument: str,
    direction: str,
    rows: Sequence[Mapping[str, object]],
    n_boot: int = 10000,
    seed: int = 20260605,
) -> Dict[str, object]:
    pnls = [_safe_float(r.get("pnl_pips")) for r in rows]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [abs(p) for p in pnls if p < 0]
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
    wr = wins / n if n else 0.0
    rr = avg_win / avg_loss if avg_loss > 0 else math.inf
    kelly = wr - ((1 - wr) / rr) if math.isfinite(rr) and rr > 0 else (wr if avg_win > 0 else 0.0)
    ev = sum(pnls) / n if n else 0.0
    wilson_lo = _wilson_lower(wins, n, 1.96)
    wilson_bonf_lo = _wilson_lower(wins, n, BONFERRONI_Z)
    before = [r for r in rows if _day(str(r.get("exit_time") or "")) < COHORT_CUT]
    after = [r for r in rows if _day(str(r.get("exit_time") or "")) >= COHORT_CUT]
    tp_wins = sum(
        1
        for r in rows
        if str(r.get("close_reason")) == "TP_HIT"
        or (str(r.get("close_reason")) == "OANDA_SL_TP" and str(r.get("outcome")) == "WIN")
    )
    h1_pass = n >= 30 and wilson_lo >= 0.40 and ev >= 0
    return {
        "cell": cell_id(entry_type, instrument, direction),
        "entry_type": entry_type,
        "instrument": instrument,
        "direction": direction,
        "n": n,
        "wins": wins,
        "tp_wins": tp_wins,
        "wr": round(wr, 6),
        "profit_factor": round(_profit_factor(pnls), 6) if math.isfinite(_profit_factor(pnls)) else "Infinity",
        "wilson_95_lower": round(wilson_lo, 6),
        "wilson_bonferroni_lower_m116": round(wilson_bonf_lo, 6),
        "ev_pips": round(ev, 6),
        "bootstrap_ev_95ci": _bootstrap_ci(pnls, n_boot=n_boot, seed=seed),
        "avg_win_pips": round(avg_win, 6),
        "avg_loss_pips": round(avg_loss, 6),
        "rr": round(rr, 6) if math.isfinite(rr) else "Infinity",
        "kelly_fraction": round(kelly, 6),
        "walk_forward": _walk_forward(rows),
        "cohorts": {
            "before_2026_05_16": _cohort_stats(before),
            "from_2026_05_16": _cohort_stats(after),
        },
        "h1_gate": {
            "pass": h1_pass,
            "checks": {
                "n_ge_30": n >= 30,
                "wilson_lo_ge_0_40": wilson_lo >= 0.40,
                "ev_ge_0": ev >= 0,
            },
        },
        "bonferroni_survives": wilson_bonf_lo >= 0.40,
    }


def compute_portfolio_stats(daily_by_cell: Mapping[str, Mapping[str, float]]) -> Dict[str, object]:
    active = {k: dict(v) for k, v in daily_by_cell.items() if v}
    all_days = sorted({day for values in active.values() for day in values})
    if not active or not all_days:
        return {
            "status": "INSUFFICIENT_DATA",
            "cells": len(active),
            "days": len(all_days),
            "weights": {},
            "daily_pnl": {},
            "max_drawdown_pips": None,
            "calmar": None,
            "monthly_sharpe": None,
            "daily_correlation": {},
        }

    vols = {}
    for cid, values in active.items():
        series = [values.get(day, 0.0) for day in all_days]
        vol = statistics.pstdev(series) if len(series) > 1 else 0.0
        vols[cid] = vol if vol > 0 else 1.0
    inv = {cid: 1.0 / vol for cid, vol in vols.items()}
    inv_sum = sum(inv.values())
    weights = {cid: inv_v / inv_sum for cid, inv_v in inv.items()}
    daily = {
        day: sum(weights[cid] * active[cid].get(day, 0.0) for cid in active)
        for day in all_days
    }
    daily_values = [daily[day] for day in all_days]
    mdd = _max_drawdown(daily_values)
    mean_daily = sum(daily_values) / len(daily_values)
    calmar = (mean_daily * 252 / mdd) if mdd > 0 else None
    monthly = defaultdict(float)
    for day, value in daily.items():
        monthly[day[:7]] += value
    monthly_values = list(monthly.values())
    if len(monthly_values) > 1 and statistics.pstdev(monthly_values) > 0:
        monthly_sharpe = statistics.mean(monthly_values) / statistics.pstdev(monthly_values) * math.sqrt(12)
    else:
        monthly_sharpe = None
    corr = _correlation_matrix(active, all_days)
    raw_monthly_expectancy = mean_daily * 21
    return {
        "status": "OK",
        "cells": len(active),
        "days": len(all_days),
        "weights": {k: round(v, 8) for k, v in weights.items()},
        "daily_pnl": {k: round(v, 6) for k, v in daily.items()},
        "max_drawdown_pips": round(mdd, 6),
        "calmar": round(calmar, 6) if calmar is not None else None,
        "monthly_sharpe": round(monthly_sharpe, 6) if monthly_sharpe is not None else None,
        "daily_correlation": corr,
        "dd20_sizing_monthly_return_expectancy": {
            "raw_pips": round(raw_monthly_expectancy, 6),
            "bonferroni_conservative_0_5_pips": round(raw_monthly_expectancy * 0.5, 6),
        },
    }


def _correlation_matrix(active: Mapping[str, Mapping[str, float]], days: Sequence[str]) -> Dict[str, Dict[str, float | None]]:
    matrix: Dict[str, Dict[str, float | None]] = {}
    keys = sorted(active)
    for a in keys:
        matrix[a] = {}
        av = [active[a].get(day, 0.0) for day in days]
        for b in keys:
            bv = [active[b].get(day, 0.0) for day in days]
            matrix[a][b] = _corr(av, bv)
    return matrix


def _corr(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    denom = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    if denom == 0:
        return None
    return round(sum(x * y for x, y in zip(da, db)) / denom, 6)


def load_rows_csv(path: Path) -> List[Dict[str, object]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def fetch_rows_via_ssh() -> List[Dict[str, object]]:
    if shutil.which("ssh") is None:
        raise RuntimeError("ssh binary not found in PATH")
    where_cells = " OR ".join(
        f"(entry_type='{e}' AND instrument='{i}' AND direction='{d}')"
        for e, i, d in FROZEN_CELLS
    )
    sql = f"""
.headers on
.mode csv
SELECT
  id, trade_id, status, direction, entry_time, exit_time, pnl_pips, pnl_r,
  outcome, entry_type, close_reason, mode, oanda_trade_id, instrument,
  is_shadow, edge_cell_id
FROM demo_trades
WHERE status='CLOSED'
  AND is_shadow=1
  AND instrument != 'XAU_USD'
  AND ({where_cells})
ORDER BY exit_time, id;
"""
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "srv-d6va1of5r7bs73en10vg@ssh.oregon.render.com",
        f"sqlite3 /var/data/demo_trades.db {json.dumps(sql)}",
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    stderr = "\n".join(line for line in proc.stderr.splitlines() if "global_hostkeys" not in line)
    if proc.returncode != 0:
        raise RuntimeError(f"Render SSH sqlite query failed rc={proc.returncode}: {stderr or proc.stdout}")
    return list(csv.DictReader(proc.stdout.splitlines()))


def fetch_rows_via_api(limit: int = 10000) -> List[Dict[str, object]]:
    query = urllib.parse.urlencode({"status": "closed", "limit": int(limit)})
    url = f"{PROD_API}?{query}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    rows = payload.get("trades", []) if isinstance(payload, dict) else payload
    frozen = set(FROZEN_CELLS)
    out = []
    for row in rows:
        key = (
            str(row.get("entry_type")),
            str(row.get("instrument")),
            str(row.get("direction")),
        )
        if key not in frozen:
            continue
        if str(row.get("status", "")).upper() != "CLOSED":
            continue
        if str(row.get("instrument")) == "XAU_USD":
            continue
        if int(row.get("is_shadow") or 0) != 1:
            continue
        out.append(row)
    return out


def fetch_rows_production() -> tuple[List[Dict[str, object]], str]:
    try:
        return fetch_rows_via_ssh(), "Render Production demo_trades.db via SSH sqlite"
    except Exception as ssh_exc:
        try:
            rows = fetch_rows_via_api()
            return rows, f"Render Production /api/demo/trades fallback; SSH unavailable: {ssh_exc}"
        except Exception as api_exc:
            raise RuntimeError(f"SSH failed ({ssh_exc}); API fallback failed ({api_exc})") from api_exc


def massive_cache_manifest() -> Dict[str, object]:
    pairs = sorted({instrument for _entry_type, instrument, _direction in FROZEN_CELLS})
    base = Path("data/cache/massive")
    files = {}
    missing = []
    for pair in pairs:
        for tf in MASSIVE_TFS:
            path = base / f"{pair}_{tf}.parquet"
            key = f"{pair}_{tf}"
            if path.exists():
                files[key] = {"path": str(path), "bytes": path.stat().st_size}
            else:
                missing.append(str(path))
    return {
        "role": "BT sanity data availability only; exact per-strategy BT is substituted by shadow realized daily PnL when no unified frozen-cell runner exists.",
        "required_pairs": pairs,
        "timeframes_checked": list(MASSIVE_TFS),
        "files": files,
        "missing": missing,
        "all_required_pair_tf_available": not missing,
    }


def build_result(
    rows: Sequence[Mapping[str, object]],
    n_boot: int,
    seed: int,
    source: str = "Render Production demo_trades.db shadow CLOSED rows",
) -> Dict[str, object]:
    grouped: Dict[str, List[Mapping[str, object]]] = {cell_id(*c): [] for c in FROZEN_CELLS}
    daily_by_cell: Dict[str, Dict[str, float]] = {cell_id(*c): defaultdict(float) for c in FROZEN_CELLS}
    for row in rows:
        cid = cell_id(str(row.get("entry_type")), str(row.get("instrument")), str(row.get("direction")))
        if cid not in grouped:
            continue
        grouped[cid].append(row)
        day = _day(str(row.get("exit_time") or ""))
        if day:
            daily_by_cell[cid][day] += _safe_float(row.get("pnl_pips"))
    cell_stats = [
        compute_cell_stats(e, i, d, grouped[cell_id(e, i, d)], n_boot=n_boot, seed=seed + idx)
        for idx, (e, i, d) in enumerate(FROZEN_CELLS)
    ]
    promote = [
        s["cell"]
        for s in cell_stats
        if s["h1_gate"]["pass"] and s["walk_forward"]["sign_consistent"] and s["bonferroni_survives"]
    ]
    rejected = [
        {
            "cell": s["cell"],
            "reasons": _reject_reasons(s),
        }
        for s in cell_stats
        if s["cell"] not in promote
    ]
    return {
        "task_id": "20260605-tp-hit-12cell-portfolio-validation",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": source,
        "tp_definition": "close_reason='TP_HIT' OR (close_reason='OANDA_SL_TP' AND outcome='WIN')",
        "frozen_cells": [cell_id(*c) for c in FROZEN_CELLS],
        "cell_stats": cell_stats,
        "portfolio": compute_portfolio_stats(daily_by_cell),
        "bt_sanity": massive_cache_manifest(),
        "promotion_recommended_cells": promote,
        "rejected_cells": rejected,
    }


def _reject_reasons(stats: Mapping[str, object]) -> List[str]:
    reasons = []
    h1 = stats["h1_gate"]["checks"]
    if not h1["n_ge_30"]:
        reasons.append("N<30")
    if not h1["wilson_lo_ge_0_40"]:
        reasons.append("Wilson95 lower <0.40")
    if not h1["ev_ge_0"]:
        reasons.append("EV<0")
    if not stats["walk_forward"]["sign_consistent"]:
        reasons.append("WF 3-fold sign not all positive")
    if not stats["bonferroni_survives"]:
        reasons.append("Bonferroni Wilson lower <0.40")
    return reasons


def write_markdown(result: Mapping[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = result.get("cell_stats", [])
    promote = result.get("promotion_recommended_cells", [])
    portfolio = result.get("portfolio", {})
    bt_sanity = result.get("bt_sanity", {})
    lines = [
        "# TP-HIT 12-cell portfolio validation",
        "",
        f"- status: {result.get('status', 'OK')}",
        f"- source: {result.get('source')}",
        f"- generated_at: {result.get('generated_at')}",
        f"- promote_recommended: {', '.join(promote) if promote else 'none'}",
    ]
    if result.get("rerun_access_note"):
        lines.append(f"- rerun_access_note: {result.get('rerun_access_note')}")
    if bt_sanity:
        lines.append(f"- bt_sanity_role: {bt_sanity.get('role')}")
        lines.append(f"- massive_all_required_pair_tf_available: {bt_sanity.get('all_required_pair_tf_available')}")
        if bt_sanity.get("missing"):
            lines.append(f"- massive_missing: {', '.join(bt_sanity.get('missing', []))}")
    lines.extend(
        [
            "",
            "## Gate table",
            "",
            "| cell | N | WR | PF | Wilson95 lo | Bonf lo | EV | Kelly | WF +folds | H1 | verdict |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for s in rows:
        verdict = "PROMOTE" if s["cell"] in promote else "REJECT"
        lines.append(
            "| {cell} | {n} | {wr:.3f} | {pf} | {wlo:.3f} | {bf:.3f} | {ev:.3f} | {kelly:.3f} | {wf}/3 | {h1} | {verdict} |".format(
                cell=str(s["cell"]).replace("|", r"\|"),
                n=s["n"],
                wr=s["wr"],
                pf=s["profit_factor"],
                wlo=s["wilson_95_lower"],
                bf=s["wilson_bonferroni_lower_m116"],
                ev=s["ev_pips"],
                kelly=s["kelly_fraction"],
                wf=s["walk_forward"]["positive_ev_folds"],
                h1="PASS" if s["h1_gate"]["pass"] else "FAIL",
                verdict=verdict,
            )
        )
    lines.extend(
        [
            "",
            "## Portfolio",
            "",
            f"- status: {portfolio.get('status')}",
            f"- cells: {portfolio.get('cells')}",
            f"- days: {portfolio.get('days')}",
            f"- maxDD_pips: {portfolio.get('max_drawdown_pips')}",
            f"- calmar: {portfolio.get('calmar')}",
            f"- monthly_sharpe: {portfolio.get('monthly_sharpe')}",
            f"- dd20_monthly_expectancy_raw_pips: {portfolio.get('dd20_sizing_monthly_return_expectancy', {}).get('raw_pips')}",
            f"- dd20_monthly_expectancy_bonf_0_5_pips: {portfolio.get('dd20_sizing_monthly_return_expectancy', {}).get('bonferroni_conservative_0_5_pips')}",
            "",
            "## Rejections",
            "",
        ]
    )
    for item in result.get("rejected_cells", []):
        lines.append(f"- `{item['cell']}`: {', '.join(item['reasons'])}")
    path.write_text("\n".join(lines) + "\n")


def write_blocked_report(error: str, json_path: Path, md_path: Path) -> Dict[str, object]:
    result = {
        "task_id": "20260605-tp-hit-12cell-portfolio-validation",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "status": "BLOCKED_PRIMARY_DATA_UNREACHABLE",
        "source": "Render Production demo_trades.db via SSH",
        "error": error,
        "frozen_cells": [cell_id(*c) for c in FROZEN_CELLS],
        "cell_stats": [],
        "portfolio": {"status": "NOT_COMPUTED_PRIMARY_DATA_BLOCKED"},
        "promotion_recommended_cells": [],
        "rejected_cells": [],
        "required_next_evidence": [
            "Successful SSH sqlite export from /var/data/demo_trades.db for the frozen 12 cells",
            "CLOSED shadow rows with entry_type, instrument, direction, exit_time, pnl_pips, outcome, close_reason",
        ],
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        "\n".join(
            [
                "# TP-HIT 12-cell portfolio validation",
                "",
                "- status: BLOCKED_PRIMARY_DATA_UNREACHABLE",
                "- source: Render Production demo_trades.db via SSH",
                f"- error: {error}",
                "",
                "## Gate table",
                "",
                "Not computed. Mock-only PASS is prohibited by the task; local demo_trades.db is stale and Render SSH did not resolve.",
                "",
                "## Required next evidence",
                "",
                "- Successful SSH sqlite export from `/var/data/demo_trades.db` for the frozen 12 cells.",
                "- CLOSED shadow rows containing `entry_type`, `instrument`, `direction`, `exit_time`, `pnl_pips`, `outcome`, and `close_reason`.",
            ]
        )
        + "\n"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", type=Path, help="Use pre-exported Render CSV instead of SSH.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--run-report", type=Path, default=DEFAULT_RUN_REPORT)
    parser.add_argument("--n-boot", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260605)
    parser.add_argument("--write-blocked-report", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.input_csv:
            rows = load_rows_csv(args.input_csv)
            source = f"pre-exported Render CSV: {args.input_csv}"
        else:
            rows, source = fetch_rows_production()
        result = build_result(rows, n_boot=args.n_boot, seed=args.seed, source=source)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        write_markdown(result, args.run_report)
        return 0
    except Exception as exc:
        if args.write_blocked_report:
            write_blocked_report(str(exc), args.output_json, args.run_report)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
