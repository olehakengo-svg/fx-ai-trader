#!/usr/bin/env python3
"""Walk-Forward Stability Scanner — 既存 BT の時間窓別安定性評価

目的:
  365d BT を 1 回実行し、trade_log を月単位で bin して戦略×ペア別の
  窓間一貫性 (CV of EV) を測定する。pybroker の walk-forward 概念を
  FX AI Trader の「パラメータ凍結 + データ蓄積フェーズ」に合わせて簡略化。

非侵襲:
  - 既存 `app.run_daytrade_backtest` をそのまま呼ぶ (BT ロジック無変更)
  - 結果を post-hoc で時間窓分解するだけ
  - live path / BT signal 関数は一切変更しない

判断プロトコル (CLAUDE.md):
  - 不安定戦略の FORCE_DEMOTE 実装は 別セッションで 365d 再検証後に決定
  - ここでは観測のみ

Usage:
    python3 tools/bt_walkforward.py [--pairs USD_JPY,EUR_USD]
                                     [--lookback 365]
                                     [--interval 15m]
                                     [--window-days 30]
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

DEFAULT_PAIRS = [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("GBPUSD=X", "GBP_USD"),
    ("EURJPY=X", "EUR_JPY"),
    ("GBPJPY=X", "GBP_JPY"),
]


def parse_entry_time(et_str: str):
    """Tolerant parser — trade_log stores entry_time as str(Timestamp)."""
    try:
        ts = datetime.fromisoformat(et_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except Exception:
        try:
            return datetime.strptime(et_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def compute_pnl_pip(trade: dict) -> float:
    """Reproduce _dt_pnl-like pip P&L with friction subtraction.

    outcome=WIN → +tp_m × atr_rel_factor (simplified: +tp_m - exit_friction_m)
    outcome=LOSS → -sl_m - exit_friction_m
    """
    outcome = trade.get("outcome")
    tp_m = float(trade.get("tp_m") or 0.0)
    sl_m = float(trade.get("sl_m") or 0.0)
    friction = float(trade.get("exit_friction_m") or 0.0)
    if outcome == "WIN":
        return tp_m - friction
    else:
        actual_sl = trade.get("actual_sl_m")
        base = float(actual_sl) if actual_sl is not None else sl_m
        return -(base + friction)


def bin_trades(trades: list[dict], window_days: int) -> dict:
    """Bin trades by rolling window_days, keyed by window index (month)."""
    if not trades:
        return {}
    parsed = []
    for t in trades:
        ts = parse_entry_time(t.get("entry_time", ""))
        if ts is None:
            continue
        parsed.append((ts, t))
    if not parsed:
        return {}
    parsed.sort(key=lambda x: x[0])
    start = parsed[0][0]

    bins = defaultdict(list)
    for ts, t in parsed:
        wi = int((ts - start).total_seconds() / 86400 // window_days)
        bins[wi].append(t)
    return dict(bins)


def window_stats(trades: list[dict]) -> dict:
    """N, WR, EV, PF per window."""
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    pnls = [compute_pnl_pip(t) for t in trades]
    pos = sum(p for p in pnls if p > 0)
    neg = sum(-p for p in pnls if p < 0)
    pf = (pos / neg) if neg > 0.0 else float("inf")
    return {
        "n": n,
        "wr": round(wins / n * 100, 1),
        "ev": round(sum(pnls) / n, 3),
        "pnl": round(sum(pnls), 2),
        "pf": round(pf, 2) if pf != float("inf") else None,
    }


def stability_metrics(per_window: list[dict]) -> dict:
    """CV(EV), positive-window ratio, min/max EV."""
    active = [w for w in per_window if w["n"] >= 5]
    if len(active) < 2:
        return {
            "active_windows": len(active),
            "positive_ratio": None,
            "cv_ev": None,
            "min_ev": None,
            "max_ev": None,
            "verdict": "N_windows<2",
        }
    evs = [w["ev"] for w in active]
    pos = sum(1 for e in evs if e > 0)
    mu = mean(evs)
    sigma = pstdev(evs)
    cv = (sigma / abs(mu)) if abs(mu) > 1e-6 else None
    # Verdict: positive_ratio ≥ 0.67 and cv < 1.0 → stable
    if pos / len(active) >= 0.67 and cv is not None and cv < 1.0:
        verdict = "stable"
    elif pos / len(active) >= 0.5:
        verdict = "borderline"
    else:
        verdict = "unstable"
    return {
        "active_windows": len(active),
        "positive_ratio": round(pos / len(active), 3),
        "cv_ev": round(cv, 3) if cv is not None else None,
        "min_ev": round(min(evs), 3),
        "max_ev": round(max(evs), 3),
        "verdict": verdict,
    }


def scan_symbol(yf_symbol: str, pair: str, lookback: int, interval: str,
                window_days: int) -> dict:
    """Run 1x BT, bin trades, compute per-strategy stability."""
    print(f"\n[bt] {pair} ({yf_symbol}) × {lookback}d {interval}...")
    import app
    app._dt_bt_cache.clear()

    try:
        result = app.run_daytrade_backtest(yf_symbol, lookback_days=lookback,
                                            interval=interval)
    except Exception as e:
        return {"pair": pair, "error": f"BT failed: {e}"}

    if result.get("error"):
        return {"pair": pair, "error": result["error"]}

    trades = result.get("trade_log", [])
    if not trades:
        return {"pair": pair, "error": "no trades"}

    # Group by strategy (entry_type)
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        et = t.get("entry_type") or "unknown"
        by_strategy[et].append(t)

    strategies = {}
    for strat, st_trades in by_strategy.items():
        if len(st_trades) < 10:
            continue  # skip low-N strategies
        bins = bin_trades(st_trades, window_days)
        per_window = []
        for wi in sorted(bins.keys()):
            ws = window_stats(bins[wi])
            ws["window"] = wi
            per_window.append(ws)
        agg = window_stats(st_trades)
        stab = stability_metrics(per_window)
        strategies[strat] = {
            "aggregate": agg,
            "per_window": per_window,
            "stability": stab,
        }

    print(f"  {len(trades)} trades, {len(strategies)} strategies (N≥10)")
    return {
        "pair": pair,
        "symbol": yf_symbol,
        "lookback_days": lookback,
        "interval": interval,
        "window_days": window_days,
        "total_trades": len(trades),
        "overall_wr": result.get("win_rate"),
        "overall_ev": result.get("expected_value"),
        "strategies": strategies,
    }


def render_markdown(all_results: list[dict], window_days: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Walk-Forward Stability Scan",
        "",
        f"- **Generated**: {now}",
        f"- **Window size**: {window_days} days (rolling)",
        f"- **Verdict thresholds**:",
        f"  - **stable**: positive_ratio ≥ 0.67 AND CV(EV) < 1.0",
        f"  - **borderline**: positive_ratio ≥ 0.5",
        f"  - **unstable**: 上記どちらも満たさない",
        "",
        "## Cross-Pair Strategy Stability",
        "| Pair | Strategy | N | Overall EV | Windows | Pos.ratio | CV(EV) | Min/Max EV | Verdict |",
        "|------|----------|--:|-----------:|--------:|----------:|-------:|:-----------|:-------:|",
    ]

    rows = []
    for r in all_results:
        if "error" in r:
            lines.append(f"| {r['pair']} | — | — | — | — | — | — | — | ❌ {r['error']} |")
            continue
        for strat, st in r["strategies"].items():
            agg = st["aggregate"]
            stab = st["stability"]
            rows.append({
                "pair": r["pair"],
                "strategy": strat,
                "n": agg["n"],
                "ev": agg["ev"],
                "windows": stab["active_windows"],
                "pos_ratio": stab["positive_ratio"],
                "cv": stab["cv_ev"],
                "min_ev": stab["min_ev"],
                "max_ev": stab["max_ev"],
                "verdict": stab["verdict"],
            })

    # Sort: unstable first (priority), then borderline, stable
    verdict_order = {"unstable": 0, "borderline": 1, "stable": 2, "N_windows<2": 3}
    rows.sort(key=lambda x: (verdict_order.get(x["verdict"], 99), -x["n"]))

    for row in rows:
        verdict_icon = {"stable": "✅", "borderline": "🟡",
                        "unstable": "🔴", "N_windows<2": "⚪"}.get(row["verdict"], "?")
        pr = f"{row['pos_ratio']:.2f}" if row["pos_ratio"] is not None else "—"
        cv = f"{row['cv']:.2f}" if row["cv"] is not None else "—"
        mn = f"{row['min_ev']:+.2f}" if row["min_ev"] is not None else "—"
        mx = f"{row['max_ev']:+.2f}" if row["max_ev"] is not None else "—"
        lines.append(
            f"| {row['pair']} | {row['strategy']} | {row['n']} | {row['ev']:+.3f} "
            f"| {row['windows']} | {pr} | {cv} | {mn}/{mx} | {verdict_icon} {row['verdict']} |"
        )

    # Unstable strategies section
    unstable = [r for r in rows if r["verdict"] == "unstable"]
    lines += [
        "",
        f"## 🔴 Unstable Strategies ({len(unstable)} cells)",
    ]
    if unstable:
        lines.append("これらは Overall EV が正でも窓間分散が大きい、")
        lines.append("または勝ち窓が半数未満。Kelly Half 到達前の FORCE_DEMOTE 検討候補。")
        lines.append("")
        lines.append("| Pair × Strategy | Overall EV | CV(EV) | Min EV | Max EV |")
        lines.append("|-----------------|-----------:|-------:|-------:|-------:|")
        for r in unstable:
            lines.append(
                f"| {r['pair']} × {r['strategy']} | {r['ev']:+.3f} | "
                f"{(r['cv'] if r['cv'] is not None else 0):.2f} | "
                f"{(r['min_ev'] if r['min_ev'] is not None else 0):+.2f} | "
                f"{(r['max_ev'] if r['max_ev'] is not None else 0):+.2f} |"
            )
    else:
        lines.append("該当なし ✨")

    lines += [
        "",
        "## 判断プロトコル遵守 (CLAUDE.md)",
        "- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)",
        "- `unstable` 判定戦略も、post-hoc 分解のみで因果なし",
        "- 次ステップ: Live N≥30 を経るか、別 BT 期間 (例 730d) で再検証",
        "",
        "## Source",
        "- pybroker walk-forward concept adapted for parameter-frozen regime",
        "- Generated by: `tools/bt_walkforward.py`",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="BT walk-forward stability scanner")
    parser.add_argument("--pairs", default=None,
                        help="Comma-separated pairs (default: all 5 FX majors)")
    parser.add_argument("--lookback", type=int, default=365)
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--window-days", type=int, default=30,
                        help="Rolling window size in days (default 30)")
    parser.add_argument("--output", default=None)
    parser.add_argument("--save-json", action="store_true",
                        help="Also save raw results as JSON")
    args = parser.parse_args()

    if args.pairs:
        user_pairs = set(p.strip() for p in args.pairs.split(","))
        pairs = [(yf, p) for yf, p in DEFAULT_PAIRS if p in user_pairs]
    else:
        pairs = DEFAULT_PAIRS

    print("=" * 60)
    print(f"  Walk-Forward Stability Scanner")
    print(f"  Pairs: {[p for _, p in pairs]}")
    print(f"  Lookback={args.lookback}d, Interval={args.interval}, Window={args.window_days}d")
    print("=" * 60)

    all_results = []
    for yf_symbol, pair in pairs:
        try:
            r = scan_symbol(yf_symbol, pair, args.lookback, args.interval,
                           args.window_days)
            all_results.append(r)
        except Exception as e:
            print(f"  ❌ {pair}: {e}")
            all_results.append({"pair": pair, "error": str(e)})

    md = render_markdown(all_results, args.window_days)
    if args.output is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results" / f"walkforward-{date_str}.md"
    else:
        out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"\n✅ Report written: {out_path}")

    if args.save_json:
        json_path = out_path.with_suffix(".json")
        json_path.write_text(json.dumps(all_results, indent=2, default=str),
                             encoding="utf-8")
        print(f"   Raw JSON: {json_path}")


if __name__ == "__main__":
    main()
