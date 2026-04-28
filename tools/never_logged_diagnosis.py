"""
G1: NEVER_LOGGED 7 戦略の root-cause 診断 (Phase 10).

7 戦略 (Apr 28 audit で production NEVER_LOGGED 確認済) を 365d × 5 majors
の 15m 履歴で replay し、BT 上での発火回数を数える。Live で 0 trade な戦略が
BT でも 0 trade なら **entry 条件が真に発火不能** (廃止候補)。BT で N>0 だが
Live で 0 なら **production 配線 / SR levels / runtime context** の問題
(G2 で env var override で緩和しつつ Sentinel data 蓄積開始)。

Plan: /Users/jg-n-012/.claude/plans/memoized-snuggling-eclipse.md (Phase 10 G1)

Usage:
    python3 tools/never_logged_diagnosis.py [--days 365] [--sample-every 4]
        [--out raw/audits/never_logged_diagnosis_<date>.md]

Output: BT 発火回数 × 7 戦略 × 5 pair マトリクス + per-strategy 集計。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

import pandas as pd

from modules.indicators import add_indicators
from strategies.context import SignalContext
from strategies.daytrade.cpd_divergence import CpdDivergence
from strategies.daytrade.mqe_gbpusd_fix import MqeGbpusdFix
from strategies.daytrade.rsk_gbpjpy_reversion import RskGbpjpyReversion
from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce
from strategies.daytrade.sr_liquidity_grab import SrLiquidityGrab
from strategies.daytrade.vdr_jpy import VdrJpy
from strategies.daytrade.vsg_jpy_reversal import VsgJpyReversal
from tools.bt_data_cache import BTDataCache


NEVER_LOGGED_STRATEGIES = [
    SrAntiHuntBounce,
    SrLiquidityGrab,
    CpdDivergence,
    VdrJpy,
    VsgJpyReversal,
    RskGbpjpyReversion,
    MqeGbpusdFix,
]

PAIRS_FOR_DIAGNOSIS = [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("GBPUSD=X", "GBP_USD"),
    ("EURJPY=X", "EUR_JPY"),
    ("GBPJPY=X", "GBP_JPY"),
]

MIN_WARMUP_BARS = 200


def _build_minimal_context(
    df: pd.DataFrame,
    bar_idx: int,
    symbol: str,
    tf: str,
) -> "SignalContext | None":
    """Build SignalContext for the bar at ``bar_idx`` using prefix slice.

    Uses empty sr_levels and empty layer dicts — diagnostic only. Strategies
    that gate on these (e.g. sr_anti_hunt_bounce requires sr_levels) will
    register as zero-signal, which is itself a useful diagnosis output.
    """
    if bar_idx < MIN_WARMUP_BARS or bar_idx >= len(df):
        return None
    sub = df.iloc[: bar_idx + 1]
    row = sub.iloc[-1]
    try:
        return SignalContext.from_df(
            sub, row, symbol=symbol, tf=tf,
            sr_levels=[], layer0={}, layer1={}, regime={},
            layer2={}, layer3={}, htf={}, session={},
            backtest_mode=True, bar_time=row.name,
        )
    except Exception:
        return None


def diagnose_strategy(strategy_cls, pairs, days, sample_every, cache):
    strat = strategy_cls()
    per_pair: dict = {}
    for sym_yf, pair_canon in pairs:
        try:
            df = cache.get(pair_canon, "15m", days=days)
        except Exception as e:
            per_pair[pair_canon] = {
                "n_evals": 0, "n_signals": 0, "n_buy": 0, "n_sell": 0,
                "error": str(e)[:120],
            }
            continue
        try:
            df = add_indicators(df)
        except Exception as e:
            per_pair[pair_canon] = {
                "n_evals": 0, "n_signals": 0, "n_buy": 0, "n_sell": 0,
                "error": f"indicators_err: {str(e)[:100]}",
            }
            continue

        n_evals = n_signals = n_buy = n_sell = 0
        for i in range(MIN_WARMUP_BARS, len(df), max(1, sample_every)):
            ctx = _build_minimal_context(df, i, sym_yf, "15m")
            if ctx is None:
                continue
            n_evals += 1
            try:
                cand = strat.evaluate(ctx)
            except Exception:
                cand = None
            if cand is not None:
                n_signals += 1
                if cand.signal == "BUY":
                    n_buy += 1
                elif cand.signal == "SELL":
                    n_sell += 1
        per_pair[pair_canon] = {
            "n_evals": n_evals, "n_signals": n_signals,
            "n_buy": n_buy, "n_sell": n_sell,
        }

    totals = {
        "n_evals": sum(p.get("n_evals", 0) for p in per_pair.values()),
        "n_signals": sum(p.get("n_signals", 0) for p in per_pair.values()),
        "n_buy": sum(p.get("n_buy", 0) for p in per_pair.values()),
        "n_sell": sum(p.get("n_sell", 0) for p in per_pair.values()),
    }
    return {
        "name": strat.name,
        "pairs": per_pair,
        "totals": totals,
        "signal_rate_pct": (
            100.0 * totals["n_signals"] / totals["n_evals"]
            if totals["n_evals"] > 0 else 0.0
        ),
    }


def render_markdown(reports, days, sample_every):
    lines = []
    lines.append(f"# G1: NEVER_LOGGED 7 戦略 BT 発火診断 ({date.today().isoformat()})")
    lines.append("")
    lines.append(f"- {days}d 履歴, 15m, 5 majors, sample_every={sample_every}")
    lines.append(f"- Plan: Phase 10 G1")
    lines.append("")
    lines.append("## サマリー")
    lines.append("")
    lines.append("| Strategy | n_evals | n_signals | rate% | n_BUY | n_SELL | 判定 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in reports:
        t = r["totals"]
        rate = r["signal_rate_pct"]
        if t["n_signals"] == 0:
            verdict = "🔴 真に 0 firing — 廃止 or G2 緩和必須"
        elif rate < 0.05:
            verdict = "🟡 BT で稀 — production 環境差 or 緩和"
        elif rate < 0.5:
            verdict = "🟢 BT で動く — production 配線/data 問題"
        else:
            verdict = "✅ BT で頻発 — 別要因"
        lines.append(
            f"| {r['name']} | {t['n_evals']} | {t['n_signals']} | {rate:.3f} "
            f"| {t['n_buy']} | {t['n_sell']} | {verdict} |"
        )
    lines.append("")
    lines.append("## Pair 別")
    lines.append("")
    pair_keys = sorted(reports[0]["pairs"].keys()) if reports else []
    lines.append("| Strategy | " + " | ".join(pair_keys) + " | total |")
    lines.append("|" + "---|" * (len(pair_keys) + 2))
    for r in reports:
        cells = []
        for pk in pair_keys:
            p = r["pairs"].get(pk, {})
            cells.append("ERR" if "error" in p
                         else f"{p.get('n_signals', 0)}/{p.get('n_evals', 0)}")
        cells.append(f"{r['totals']['n_signals']}/{r['totals']['n_evals']}")
        lines.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## 解釈ガイド")
    lines.append("")
    lines.append("- **0 signals**: BT も発火しない → entry 真に困難。G2 で sub-clause 緩和。")
    lines.append("- **n>0 だが production NEVER_LOGGED**: BT で動くが Live で動かない。")
    lines.append("  SignalContext 組み立て差 (sr_levels / regime), or DT_QUALIFIED / pair scope 不整合。")
    lines.append("- **rate% < 0.05**: 稀すぎ → 廃止候補。")
    lines.append("")
    lines.append("## 注意 (本診断の限界)")
    lines.append("")
    lines.append("- SR levels / layer dicts は **empty** で渡している。これに依存する戦略")
    lines.append("  (sr_anti_hunt_bounce, sr_liquidity_grab) は本 audit で過小評価される。")
    lines.append("- sample_every で sub-sample しているため絶対数は近似値、比較用のみ。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--sample-every", type=int, default=4)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    out = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "raw", "audits",
        f"never_logged_diagnosis_{date.today().isoformat()}.md",
    )

    cache = BTDataCache()
    reports = []
    for cls in NEVER_LOGGED_STRATEGIES:
        print(f"Diagnosing {cls.__name__}...", flush=True)
        r = diagnose_strategy(
            cls, PAIRS_FOR_DIAGNOSIS,
            days=args.days, sample_every=args.sample_every, cache=cache,
        )
        print(f"  {r['name']}: signals={r['totals']['n_signals']}/"
              f"{r['totals']['n_evals']} rate={r['signal_rate_pct']:.3f}%", flush=True)
        reports.append(r)

    md = render_markdown(reports, args.days, args.sample_every)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(md)
    print(f"\nWrote {out}")
    n_zero = sum(1 for r in reports if r["totals"]["n_signals"] == 0)
    print(f"Strategies with 0 BT signals: {n_zero}/{len(reports)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
