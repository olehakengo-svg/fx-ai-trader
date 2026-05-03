#!/usr/bin/env python3
"""Validity checks for C-1 London Open Breakout BT artifacts."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np


def _profit_factor(pnls: list[float]) -> float:
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def null_bootstrap_pf(pnls: list[float], n: int = 1000, seed: int = 20260503) -> dict:
    """Deterministic sign-randomization null for a realized pnl vector."""
    rng = np.random.default_rng(seed)
    abs_pnls = np.abs(np.array(pnls, dtype=float))
    if len(abs_pnls) == 0:
        return {"iterations": n, "p95_pf": 0.0, "actual_pf": 0.0, "actual_gt_p95": False}
    values = []
    for _ in range(n):
        signs = rng.choice([-1.0, 1.0], size=len(abs_pnls))
        values.append(_profit_factor((abs_pnls * signs).tolist()))
    finite = [v for v in values if math.isfinite(v)]
    p95 = float(np.percentile(finite or [0.0], 95))
    actual = _profit_factor(pnls)
    return {
        "iterations": n,
        "p95_pf": round(p95, 6),
        "actual_pf": round(actual, 6) if math.isfinite(actual) else "inf",
        "actual_gt_p95": bool(actual > p95),
    }


def cohort_check(trades: list[dict]) -> dict:
    cohorts = [
        ("2014-2016 pre-Brexit", "2014-01-01", "2016-06-22"),
        ("2016-2017 Brexit Vote", "2016-06-23", "2017-12-31"),
        ("2018-2019 calm", "2018-01-01", "2019-12-31"),
        ("2020 COVID", "2020-01-01", "2020-12-31"),
        ("2021-2022 Truss budget", "2021-01-01", "2022-12-31"),
        ("2023-2024", "2023-01-01", "2024-12-31"),
        ("2025-2026", "2025-01-01", "2026-04-30"),
    ]
    rows = []
    total = sum(float(t["pnl_pip_net"]) for t in trades)
    for name, start, end in cohorts:
        subset = [t for t in trades if start <= t["timestamp"][:10] <= end]
        pnls = [float(t["pnl_pip_net"]) for t in subset]
        wins = sum(1 for p in pnls if p > 0)
        pnl = sum(pnls)
        rows.append(
            {
                "cohort": name,
                "n": len(pnls),
                "wr_pct": round(wins / len(pnls) * 100, 6) if pnls else 0.0,
                "pf": round(_profit_factor(pnls), 6) if math.isfinite(_profit_factor(pnls)) else "inf",
                "pnl_pip_net": round(pnl, 6),
                "share_of_total_pnl": round((pnl / total), 6) if total else 0.0,
            }
        )
    max_share = max((abs(r["share_of_total_pnl"]) for r in rows), default=0.0)
    return {"rows": rows, "accept_no_single_cohort_gt_50pct": max_share < 0.5, "max_abs_share": max_share}


def render_api_rsk_check() -> dict:
    url = "https://fx-ai-trader.onrender.com/api/demo/trades?days=365&limit=5000"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "status": "BLOCKED",
            "source": url,
            "reason": f"Render API fetch failed in this environment: {type(exc).__name__}: {exc}",
        }
    trades = data.get("trades", data if isinstance(data, list) else [])
    rsk = [t for t in trades if t.get("entry_type") == "rsk_gbpjpy_reversion"]
    return {"status": "FETCHED", "source": url, "rsk_trade_count": len(rsk), "note": "correlation not computed without daily aligned pnl schema"}


def render_snapshot_rsk_check(snapshot_path: str) -> dict:
    p = Path(snapshot_path)
    if not p.exists():
        return {"status": "BLOCKED", "source": str(p), "reason": "snapshot not found"}
    try:
        conn = sqlite3.connect(str(p))
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), COALESCE(AVG(pnl_pips),0), COALESCE(SUM(pnl_pips),0), "
            "SUM(CASE WHEN COALESCE(is_shadow,0)=1 THEN 1 ELSE 0 END), "
            "MIN(entry_time), MAX(entry_time) "
            "FROM demo_trades WHERE entry_type='rsk_gbpjpy_reversion'"
        )
        n, avg_pnl, sum_pnl, shadow_n, t_min, t_max = cur.fetchone()
        conn.close()
    except sqlite3.Error as exc:
        return {"status": "BLOCKED", "source": str(p), "reason": f"sqlite error: {type(exc).__name__}: {exc}"}
    return {
        "status": "FETCHED",
        "source": f"render_snapshot:{p.name}",
        "rsk_trade_count": int(n or 0),
        "rsk_shadow_count": int(shadow_n or 0),
        "rsk_avg_pnl_pips": round(float(avg_pnl or 0.0), 6),
        "rsk_sum_pnl_pips": round(float(sum_pnl or 0.0), 6),
        "rsk_first_entry": t_min,
        "rsk_last_entry": t_max,
        "note": "correlation not computed without daily aligned pnl schema; counts only",
    }


def broker_cross_check(source: str) -> dict:
    if source != "yfinance":
        return {"status": "BLOCKED", "reason": f"unsupported broker cross source: {source}"}
    try:
        import yfinance as yf  # type: ignore

        df = yf.download("GBPJPY=X", period="60d", interval="5m", progress=False)
    except Exception as exc:
        return {"status": "BLOCKED", "source": "yfinance", "reason": f"fetch failed: {type(exc).__name__}: {exc}"}
    if df is None or len(df) < 100:
        return {"status": "BLOCKED", "source": "yfinance", "reason": "insufficient intraday bars for 12-year cross-check"}
    return {
        "status": "PARTIAL_ONLY",
        "source": "yfinance",
        "bars": int(len(df)),
        "reason": "yfinance intraday does not provide 2014-2026 M5 coverage",
    }


def scenario_from_checks(bt: dict, checks: dict) -> str:
    if bt["header"].get("limitations"):
        return "BLOCKED_DATA"
    primary_scenario = bt["scenario_verdict"]["scenario"]
    if primary_scenario == "REJECT":
        return "REJECT"
    statuses = [checks["v2_rsk_correlation"]["status"], checks["v3_broker_cross_check"]["status"]]
    if any(s == "BLOCKED" for s in statuses):
        return "NEEDS_MORE_EVIDENCE"
    if not checks["v1_null_bootstrap"]["actual_gt_p95"]:
        return "REJECT"
    if not checks["v4_cohort"]["accept_no_single_cohort_gt_50pct"]:
        return "NEEDS_MORE_EVIDENCE"
    return "ACCEPT" if primary_scenario == "NEEDS_VALIDITY_CHECK" else primary_scenario


def main_args_for_test(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bt-result", required=True)
    ap.add_argument("--rsk-source", default="render_api", choices=["render_api", "render_snapshot", "none"])
    ap.add_argument("--rsk-snapshot", default="")
    ap.add_argument("--broker-cross", default="yfinance")
    ap.add_argument("--bootstrap-n", type=int, default=1000)
    ap.add_argument("--output", required=True)
    ap.add_argument("--orphan-log", default="")
    ap.add_argument("--seed", type=int, default=20260503)
    args = ap.parse_args(argv)
    bt = json.loads(Path(args.bt_result).read_text())
    trades = bt["primary"]["trades"]
    pnls = [float(t["pnl_pip_net"]) for t in trades]
    checks = {
        "header": {
            "data_source": bt["header"]["data_source"],
            "live_separation": "bt_only",
            "pair": bt["header"]["pair"],
            "interval": bt["header"]["interval"],
            "time_window": bt["header"]["time_window"],
            "git_sha": bt["header"]["git_sha"],
        },
        "v1_null_bootstrap": null_bootstrap_pf(pnls, args.bootstrap_n, args.seed),
        "v2_rsk_correlation": (
            render_api_rsk_check() if args.rsk_source == "render_api"
            else render_snapshot_rsk_check(args.rsk_snapshot) if args.rsk_source == "render_snapshot"
            else {"status": "BLOCKED", "reason": f"unsupported rsk-source: {args.rsk_source}"}
        ),
        "v3_broker_cross_check": broker_cross_check(args.broker_cross),
        "v4_cohort": cohort_check(trades),
        "v5_orphan_check": {
            "status": "SEE_RUN_LOG" if args.orphan_log else "NOT_PROVIDED",
            "path": args.orphan_log,
        },
        "v6_spread_profile": {"status": "RECORDED_IN_BT", "basis": "entry hour round-trip spread subtracted from entry_price basis"},
    }
    checks["scenario_verdict"] = scenario_from_checks(bt, checks)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checks, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"scenario={checks['scenario_verdict']}")
    return 0


def main() -> int:
    return main_args_for_test()


if __name__ == "__main__":
    raise SystemExit(main())
