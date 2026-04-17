#!/usr/bin/env python3
"""
Portfolio BUY/SELL Balance Audit
═════════════════════════════════

Simpson's paradox / regime imbalance の一次診断ツール.

目的:
- 戦略ポートフォリオ全体が BUY に偏っていないか (構造的 long-bias)
- 各 instrument / entry_type で direction 比率が 50:50 から有意に乖離しているか
- direction × regime で marginal PnL がどう分解されるか
- (もし分解すると) 「戦略そのものの edge」と「方向 × regime exposure」を分離できる

Usage:
    python3 tools/portfolio_balance.py
    python3 tools/portfolio_balance.py --date-from 2026-04-08
    python3 tools/portfolio_balance.py --exclude-shadow

根拠: knowledge-base/wiki/analyses/conditional-edge-estimand-2026-04-17.md
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import os
from pathlib import Path

# プロジェクトルートを sys.path に追加
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# .env 読み込み
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def _parse_regime_label(regime_json: str) -> str:
    """Production の regime JSON 列から top-level regime を抽出.

    Returns: "TREND_BULL" | "TREND_BEAR" | "RANGE" | "UNKNOWN"
    """
    if not regime_json or not isinstance(regime_json, str):
        return "UNKNOWN"
    try:
        obj = json.loads(regime_json)
    except (json.JSONDecodeError, ValueError):
        return "UNKNOWN"
    if not isinstance(obj, dict):
        return "UNKNOWN"
    r = obj.get("regime", "UNKNOWN")
    if r in ("TREND_BULL", "TREND_BEAR", "RANGE"):
        return r
    return "UNKNOWN"


def _chi2_2way(n_buy: int, n_sell: int, p_null: float = 0.5) -> tuple[float, float]:
    """2-way chi-square goodness-of-fit against 50:50.

    Returns: (chi2_stat, p_value_approx)
    p_value は正規近似 (df=1) — scipy 非依存.
    """
    n = n_buy + n_sell
    if n == 0:
        return 0.0, 1.0
    exp_buy = n * p_null
    exp_sell = n * (1 - p_null)
    chi2 = ((n_buy - exp_buy) ** 2) / exp_buy + ((n_sell - exp_sell) ** 2) / exp_sell
    # df=1 の chi-square → |z| = sqrt(chi2), 両側 p 値は 2*(1-Phi(|z|))
    z = math.sqrt(chi2)
    p = math.erfc(z / math.sqrt(2))  # 2 * (1 - Phi(z))
    return chi2, p


def _fmt_ratio(n_buy: int, n_sell: int) -> str:
    n = n_buy + n_sell
    if n == 0:
        return "0:0 (N=0)"
    pct_buy = 100 * n_buy / n
    return f"{n_buy}:{n_sell} ({pct_buy:.0f}%B / {100-pct_buy:.0f}%S, N={n})"


def _fmt_pnl(s) -> str:
    import pandas as pd
    if len(s) == 0:
        return "N=0"
    return (
        f"N={len(s):3d} WR={100*(s>0).mean():4.1f}% "
        f"Avg={s.mean():+6.2f}p Med={s.median():+6.2f}p"
    )


def run_audit(date_from: str, include_shadow: bool = True,
              min_n_display: int = 10) -> None:
    import pandas as pd
    from research.edge_discovery.production_fetcher import fetch_closed_trades

    print("═" * 78)
    print("PORTFOLIO BUY/SELL BALANCE AUDIT")
    print(f"date_from={date_from}  include_shadow={include_shadow}")
    print("═" * 78)

    df = fetch_closed_trades(
        date_from=date_from,
        include_shadow=include_shadow,
    )
    if df.empty:
        print("no trades fetched; abort")
        return

    print(f"\nFetched {len(df)} trades "
          f"({df['entry_time'].min().date()} → {df['entry_time'].max().date()})")

    # ── 1. Overall direction balance ───────────────────────────────────
    print("\n" + "─" * 78)
    print("1. OVERALL DIRECTION BALANCE")
    print("─" * 78)
    n_buy = int((df["direction"] == "BUY").sum())
    n_sell = int((df["direction"] == "SELL").sum())
    chi2, p = _chi2_2way(n_buy, n_sell)
    print(f"  {_fmt_ratio(n_buy, n_sell)}")
    print(f"  χ² vs 50:50 = {chi2:.2f}  p = {p:.4f}"
          f"  {'← 有意' if p < 0.05 else ''}")

    # ── 2. Per-instrument balance ──────────────────────────────────────
    print("\n" + "─" * 78)
    print("2. PER-INSTRUMENT DIRECTION BALANCE")
    print("─" * 78)
    print(f"  {'instrument':12s} {'BUY:SELL':28s} {'χ² p-val':>10s}  flag")
    for inst, grp in df.groupby("instrument"):
        nb = int((grp["direction"] == "BUY").sum())
        ns = int((grp["direction"] == "SELL").sum())
        if nb + ns < min_n_display:
            continue
        _, p = _chi2_2way(nb, ns)
        flag = "⚠ skewed" if p < 0.05 else ""
        print(f"  {inst:12s} {_fmt_ratio(nb, ns):28s} {p:10.4f}  {flag}")

    # ── 3. Per-entry_type balance ──────────────────────────────────────
    print("\n" + "─" * 78)
    print("3. PER-ENTRY_TYPE DIRECTION BALANCE (top 15 by N)")
    print("─" * 78)
    print(f"  {'entry_type':25s} {'BUY:SELL':28s} {'χ² p-val':>10s}  flag")
    top_types = df["entry_type"].value_counts().head(15).index
    for et in top_types:
        grp = df[df["entry_type"] == et]
        nb = int((grp["direction"] == "BUY").sum())
        ns = int((grp["direction"] == "SELL").sum())
        if nb + ns < min_n_display:
            continue
        _, p = _chi2_2way(nb, ns)
        flag = "⚠ directional" if p < 0.05 else ""
        print(f"  {et:25s} {_fmt_ratio(nb, ns):28s} {p:10.4f}  {flag}")

    # ── 4. Direction × PnL (marginal edge per direction) ───────────────
    print("\n" + "─" * 78)
    print("4. DIRECTION × PNL (marginal edge per direction, LIVE only)")
    print("─" * 78)
    live_df = df[df.get("is_shadow", 0) != 1]
    for d in ["BUY", "SELL"]:
        s = live_df[live_df["direction"] == d]["pnl_pips"]
        print(f"  {d:5s}: {_fmt_pnl(s)}")

    # ── 5. Instrument × Direction PnL (conditional edge) ───────────────
    print("\n" + "─" * 78)
    print("5. INSTRUMENT × DIRECTION × PNL (LIVE only)")
    print("─" * 78)
    print(f"  {'instrument':12s} {'dir':5s} {'stats':50s}")
    for inst in sorted(live_df["instrument"].unique()):
        for d in ["BUY", "SELL"]:
            s = live_df[(live_df["instrument"] == inst)
                        & (live_df["direction"] == d)]["pnl_pips"]
            if len(s) < min_n_display:
                continue
            print(f"  {inst:12s} {d:5s} {_fmt_pnl(s)}")

    # ── 6. Regime (production-tagged) × Direction × PnL ────────────────
    print("\n" + "─" * 78)
    print("6. REGIME(prod-tag) × DIRECTION × PNL (LIVE only)")
    print("─" * 78)
    print("  Note: regime は entry時に production が自己申告したタグ.")
    print("        OANDA 独立 OHLC での検証はまだ未実施 (regime_labeler 予定).")
    live_df = live_df.copy()
    live_df["regime_parsed"] = live_df["regime"].apply(_parse_regime_label)
    n_unknown = int((live_df["regime_parsed"] == "UNKNOWN").sum())
    print(f"  (UNKNOWN regime count: {n_unknown} / {len(live_df)})")
    print(f"  {'regime':12s} {'dir':5s} {'stats':50s}")
    for r in ["TREND_BULL", "TREND_BEAR", "RANGE", "UNKNOWN"]:
        for d in ["BUY", "SELL"]:
            s = live_df[(live_df["regime_parsed"] == r)
                        & (live_df["direction"] == d)]["pnl_pips"]
            if len(s) < min_n_display:
                continue
            print(f"  {r:12s} {d:5s} {_fmt_pnl(s)}")

    # ── 7. π_sample (regime distribution in sample) ────────────────────
    print("\n" + "─" * 78)
    print("7. π_sample: REGIME DISTRIBUTION IN SAMPLE (LIVE only)")
    print("─" * 78)
    total = len(live_df)
    for r in ["TREND_BULL", "TREND_BEAR", "RANGE", "UNKNOWN"]:
        n = int((live_df["regime_parsed"] == r).sum())
        pct = 100 * n / total if total > 0 else 0
        print(f"  {r:12s} n={n:4d}  π_sample={pct:5.1f}%")
    print()
    print("  これが π_long_run から乖離していれば、marginal edge は bias あり.")
    print("  π_long_run の推定は OANDA OHLC を使った regime_labeler 待ち.")

    # ── 8. Key takeaways ───────────────────────────────────────────────
    print("\n" + "─" * 78)
    print("8. KEY TAKEAWAYS")
    print("─" * 78)

    # (a) overall long bias?
    if (n_buy + n_sell) > 0:
        buy_pct = 100 * n_buy / (n_buy + n_sell)
        if abs(buy_pct - 50) < 5:
            print(f"  ✅ Overall BUY:SELL = {buy_pct:.0f}%:{100-buy_pct:.0f}%  "
                  f"— 構造的 direction bias は軽微")
        else:
            print(f"  ⚠  Overall BUY:SELL = {buy_pct:.0f}%:{100-buy_pct:.0f}%  "
                  f"— 構造的 {'long' if buy_pct > 50 else 'short'}-bias の疑い")

    # (b) regime × direction: 特定の組み合わせで大きな edge/drag があるか
    worst_cell = None
    worst_avg = 0
    best_cell = None
    best_avg = 0
    for r in ["TREND_BULL", "TREND_BEAR", "RANGE"]:
        for d in ["BUY", "SELL"]:
            s = live_df[(live_df["regime_parsed"] == r)
                        & (live_df["direction"] == d)]["pnl_pips"]
            if len(s) < 30:  # 判定に十分な N
                continue
            avg = s.mean()
            if avg < worst_avg:
                worst_avg = avg
                worst_cell = (r, d, len(s))
            if avg > best_avg:
                best_avg = avg
                best_cell = (r, d, len(s))
    if best_cell:
        print(f"  🔵 Best cell:  {best_cell[0]:12s} × {best_cell[1]:5s} "
              f"(N={best_cell[2]})  Avg={best_avg:+.2f}p")
    if worst_cell:
        print(f"  🔴 Worst cell: {worst_cell[0]:12s} × {worst_cell[1]:5s} "
              f"(N={worst_cell[2]})  Avg={worst_avg:+.2f}p")

    # (c) Simpson's paradox risk check: direction の marginal と conditional が一致?
    for d in ["BUY", "SELL"]:
        s_all = live_df[live_df["direction"] == d]["pnl_pips"]
        if len(s_all) < 30:
            continue
        marginal = s_all.mean()
        # 条件付き期待値 (over regime, π_sample weighted — 実は marginal と一致するので参考値)
        cond_by_regime = {}
        for r in ["TREND_BULL", "TREND_BEAR", "RANGE"]:
            s_r = live_df[(live_df["regime_parsed"] == r)
                          & (live_df["direction"] == d)]["pnl_pips"]
            if len(s_r) >= 10:
                cond_by_regime[r] = (s_r.mean(), len(s_r))
        if cond_by_regime:
            span = max(v[0] for v in cond_by_regime.values()) - min(v[0] for v in cond_by_regime.values())
            print(f"  📊 {d}: marginal={marginal:+.2f}p, "
                  f"regime条件付け span={span:.2f}p "
                  f"{'⚠ regime感応度高い' if span > 3 else ''}")

    print("\n" + "═" * 78)
    print("完了. 詳細解釈は conditional-edge-estimand-2026-04-17.md 参照.")
    print("═" * 78)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", default="2026-04-08",
                        help="取得開始日 (YYYY-MM-DD)")
    parser.add_argument("--exclude-shadow", action="store_true",
                        help="shadow trades を除外")
    parser.add_argument("--min-n", type=int, default=10,
                        help="表示閾値 (cell N)")
    args = parser.parse_args()

    run_audit(
        date_from=args.date_from,
        include_shadow=not args.exclude_shadow,
        min_n_display=args.min_n,
    )


if __name__ == "__main__":
    main()
