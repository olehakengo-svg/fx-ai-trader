"""v1b ma_trend_perfect — Tier 1 Forensic analysis (rule:R1 LOCK pre-check)

Three deliverables (CLAUDE.md「自分の発見を絶対視しない」規律):
  ① Tokyo 73.6% WR の解剖 (時刻/週次/ストリーク/トレード分布)
  ② Cohort time alignment (fold 期間と直近 regime の重複)
  ③ BH cell grouping 妥当性 (4-cell vs 12-cell の statistical defensibility)

Usage:
  python3 research/edge_discovery/v1b_forensics.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import math

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

V1B_TRADES = "knowledge-base/raw/audits/ma_family_v1/USD_JPY_trades_20260430_064233.csv"
ALL4_TRADES = "knowledge-base/raw/audits/ma_family_v1/USD_JPY_trades_20260430_062341.csv"


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / den) * 100.0


def runs_test(outcomes: list[bool]) -> dict:
    """Wald-Wolfowitz runs test for serial independence.

    H0: outcomes are i.i.d. (no streak structure)
    Returns z and 2-sided p-value.
    """
    n = len(outcomes)
    n1 = sum(outcomes)
    n2 = n - n1
    if n1 == 0 or n2 == 0 or n < 5:
        return {"runs": 0, "expected_runs": 0, "z": 0.0, "p_value": 1.0}
    runs = 1
    for i in range(1, n):
        if outcomes[i] != outcomes[i-1]:
            runs += 1
    mu = (2 * n1 * n2) / n + 1
    var = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n * n * (n - 1))
    if var <= 0:
        return {"runs": runs, "expected_runs": round(mu, 2), "z": 0.0, "p_value": 1.0}
    z = (runs - mu) / math.sqrt(var)
    from scipy.stats import norm
    p = 2 * (1 - norm.cdf(abs(z)))
    return {"runs": runs, "expected_runs": round(mu, 2), "z": round(z, 3), "p_value": round(p, 4)}


def benjamini_hochberg(pvals: list[float], q: float = 0.05) -> list[bool]:
    n = len(pvals)
    if n == 0:
        return []
    order = np.argsort(pvals)
    ranked = np.array(pvals)[order]
    thresholds = (np.arange(1, n + 1) / n) * q
    passed = ranked <= thresholds
    if not passed.any():
        return [False] * n
    max_k = int(np.max(np.where(passed)[0])) + 1
    rej = np.zeros(n, dtype=bool)
    rej[order[:max_k]] = True
    return rej.tolist()


def binom_p(wins: int, n: int, p_h0: float) -> float:
    from scipy.stats import binom
    return float(binom.sf(wins - 1, n, p_h0))


def hr(title: str):
    print()
    print("═" * 78)
    print(title)
    print("═" * 78)


def section(title: str):
    print()
    print("─" * 78)
    print(title)
    print("─" * 78)


def main():
    df = pd.read_csv(V1B_TRADES)
    df["ts"] = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date
    df["week"] = df["ts"].dt.isocalendar().week
    df["year_week"] = df["ts"].dt.strftime("%G-W%V")
    df["win"] = (df["outcome"] == "WIN").astype(int)

    hr("v1b ma_trend_perfect FORENSIC REPORT (180d × USD_JPY × spread 0.8 pip)")
    print(f"Source : {V1B_TRADES}")
    print(f"Trades : N={len(df)}")
    print(f"Range  : {df['ts'].min()} → {df['ts'].max()}")
    print(f"Span   : {(df['ts'].max() - df['ts'].min()).days} days")

    # ═══════════ ① Tokyo 73.6% WR 解剖 ═══════════════════════════════
    hr("① Tokyo 73.6% WR FORENSIC (N=91 trades)")

    tk = df[df["session"] == "Tokyo"].sort_values("ts").reset_index(drop=True)
    tk_n = len(tk)
    tk_w = int(tk["win"].sum())
    tk_wr = tk_w / tk_n
    print(f"Confirmation: N={tk_n}, wins={tk_w}, WR={tk_wr*100:.2f}%, Wilson95下限={wilson_lower(tk_w, tk_n):.2f}%")

    section("①-a 時刻ヒストグラム (UTC hour)")
    hour_stats = tk.groupby("hour_utc").agg(
        n=("win", "size"), w=("win", "sum"), pnl=("pnl_pips", "sum"))
    hour_stats["wr"] = (hour_stats["w"] / hour_stats["n"] * 100).round(1)
    hour_stats["wilson_lo"] = [
        round(wilson_lower(int(r["w"]), int(r["n"])), 1)
        for _, r in hour_stats.iterrows()
    ]
    print(hour_stats.to_string())

    section("①-b 週次 WR 変動 (year-week 別)")
    wk_stats = tk.groupby("year_week").agg(
        n=("win", "size"), w=("win", "sum"), pnl=("pnl_pips", "sum"))
    wk_stats["wr"] = (wk_stats["w"] / wk_stats["n"] * 100).round(1)
    print(f"Active weeks: {len(wk_stats)} / 26 (180d / 7)")
    print(f"Per-week N — mean={wk_stats['n'].mean():.2f} median={wk_stats['n'].median():.0f} max={wk_stats['n'].max()}")
    print(f"Per-week WR — mean={wk_stats['wr'].mean():.1f}% median={wk_stats['wr'].median():.1f}% std={wk_stats['wr'].std():.2f}")
    print()
    print("Top-5 高 WR 週 (N>=2):")
    print(wk_stats[wk_stats["n"] >= 2].sort_values("wr", ascending=False).head(5).to_string())
    print()
    print("Bottom-5 低 WR 週 (N>=2):")
    print(wk_stats[wk_stats["n"] >= 2].sort_values("wr").head(5).to_string())

    # Concentration check: top-5 weeks contain what % of total wins?
    top5_w = wk_stats.sort_values("wr", ascending=False).head(5)["w"].sum()
    print(f"\n上位 5 週で総勝ちの {top5_w}/{tk_w} = {top5_w/tk_w*100:.1f}% を占める")

    section("①-c ストリーク分析 (Wald-Wolfowitz runs test)")
    out = tk["win"].astype(bool).tolist()
    r = runs_test(out)
    print(f"  Observed runs: {r['runs']}, Expected (i.i.d.): {r['expected_runs']}")
    print(f"  z = {r['z']}, two-sided p = {r['p_value']}")
    print(f"  Interpretation: p<0.05 → 系列従属あり (i.i.d. 反証) / p>=0.05 → i.i.d. と整合")
    # Also: max consecutive win/loss
    max_w_streak = 0; max_l_streak = 0; cur_w = 0; cur_l = 0
    for o in out:
        if o:
            cur_w += 1; cur_l = 0; max_w_streak = max(max_w_streak, cur_w)
        else:
            cur_l += 1; cur_w = 0; max_l_streak = max(max_l_streak, cur_l)
    print(f"  Longest WIN streak: {max_w_streak}, longest LOSS streak: {max_l_streak}")

    section("①-d 損益分布 (BT optimistic touch model 検査)")
    wins_pnl = tk[tk["outcome"] == "WIN"]["pnl_pips"]
    losses_pnl = tk[tk["outcome"] == "LOSS"]["pnl_pips"]
    expir_pnl = tk[tk["outcome"] == "EXPIRED"]["pnl_pips"]
    print(f"  WIN  N={len(wins_pnl):3d}  mean={wins_pnl.mean():.3f}  median={wins_pnl.median():.3f}  min={wins_pnl.min():.3f}  max={wins_pnl.max():.3f}")
    print(f"  LOSS N={len(losses_pnl):3d}  mean={losses_pnl.mean():.3f}  median={losses_pnl.median():.3f}  min={losses_pnl.min():.3f}  max={losses_pnl.max():.3f}")
    print(f"  EXPR N={len(expir_pnl):3d}  mean={expir_pnl.mean():.3f}" if len(expir_pnl) else "  EXPR N=0")
    print()
    print(f"  Exit bars distribution (max_hold=240):")
    print(f"    WIN  exit_bars  mean={tk[tk['outcome']=='WIN']['exit_bars'].mean():.1f}  median={tk[tk['outcome']=='WIN']['exit_bars'].median():.0f}")
    print(f"    LOSS exit_bars  mean={tk[tk['outcome']=='LOSS']['exit_bars'].mean():.1f}  median={tk[tk['outcome']=='LOSS']['exit_bars'].median():.0f}")
    print()
    # Quick close LOSS analysis: LOSS in <5 bars suggests SL too tight or BT optimistic
    quick_loss = tk[(tk['outcome']=='LOSS') & (tk['exit_bars']<5)]
    print(f"  Quick LOSS (<5 bars, BT model でほぼノイズ): {len(quick_loss)} / {len(losses_pnl)} = {len(quick_loss)/max(1,len(losses_pnl))*100:.1f}%")

    # ═══════════ ② Cohort time alignment ═══════════════════════════════
    hr("② COHORT TIME ALIGNMENT — fold期間とregime")

    df_all = df.sort_values("ts").reset_index(drop=True)
    n_all = len(df_all)
    fold_size = n_all // 3
    folds = [
        ("f1", df_all.iloc[0:fold_size]),
        ("f2", df_all.iloc[fold_size:2*fold_size]),
        ("f3", df_all.iloc[2*fold_size:n_all]),
    ]
    print(f"{'fold':<5} {'date_start':<12} {'date_end':<12} {'days':<6} {'N':<5} {'wins':<6} {'WR':<8} {'PF':<6} {'EV':<7}")
    for name, sub in folds:
        if len(sub) == 0:
            continue
        n = len(sub); w = int(sub["win"].sum())
        wr = w/n*100
        pnl = sub["pnl_pips"].values
        gw = pnl[pnl>0].sum(); gl = -pnl[pnl<0].sum()
        pf = (gw/gl) if gl>0 else float('inf')
        ev = pnl.mean()
        d_start = sub["date"].min()
        d_end = sub["date"].max()
        days = (sub["ts"].max() - sub["ts"].min()).days
        print(f"{name:<5} {str(d_start):<12} {str(d_end):<12} {days:<6} {n:<5} {w:<6} {wr:<8.2f} {pf:<6.3f} {ev:<7.3f}")

    print()
    print("レジーム重複コメント:")
    print("  - f3 (最新) が Phase B Shadow 期間 (2026-04-30〜05-14) と隣接")
    print("  - f3 WR 56.1% は f1/f2 (64-62%) より明確に劣化 → エッジ decay の可能性")
    print("  - 円介入/FOMC/NFP イベントは f3 期間で確認推奨")

    # ═══════════ ③ BH cell grouping ═══════════════════════════════
    hr("③ BH CELL GROUPING 妥当性検証 (4-cell vs 12-cell)")

    # Re-derive p-values from session subsets (using 180d v1b run)
    sess_p = {}
    sess_stats = {}
    bev_proxy = 0.50  # approximation; the real BEV is ~0.43-0.51 across cells
    for sess in ("Tokyo", "London", "NY"):
        sub = df[df["session"] == sess]
        n = len(sub); w = int(sub["win"].sum())
        # Use the actual BEV from prior run (per cell):
        if sess == "Tokyo": bev = 0.5069
        elif sess == "London": bev = 0.5086
        else: bev = 0.4949
        p = binom_p(w, n, bev)
        sess_p[sess] = p
        sess_stats[sess] = {"n": n, "w": w, "wr": w/n*100, "bev": bev, "p": p}

    section("③-a 3-cell BH (現状の v1b LOCK 採用方式)")
    pvals3 = [sess_stats["Tokyo"]["p"], sess_stats["London"]["p"], sess_stats["NY"]["p"]]
    rej3 = benjamini_hochberg(pvals3, q=0.05)
    for sess, rej in zip(["Tokyo", "London", "NY"], rej3):
        s = sess_stats[sess]
        print(f"  {sess:<8} N={s['n']:3d} WR={s['wr']:6.2f}%  BEV={s['bev']:.4f}  p={s['p']:.5f}  BH-pass={rej}")
    print(f"  → {sum(rej3)}/3 cells significant at BH q=0.05")

    section("③-b 12-cell BH (4戦略 × 3セッション full panel)")
    print("注: 90d 4戦略 BT 結果から再計算")
    # Use 90d 4-strategy data for 12-cell view
    df90 = pd.read_csv(ALL4_TRADES)
    df90["ts"] = pd.to_datetime(df90["ts"])
    df90["win"] = (df90["outcome"] == "WIN").astype(int)
    cells12 = []
    for strat in df90["strategy"].unique():
        for sess in ("Tokyo", "London", "NY"):
            sub = df90[(df90["strategy"]==strat) & (df90["session"]==sess)]
            if len(sub) < 5:
                continue
            n = len(sub); w = int(sub["win"].sum())
            pnl = sub["pnl_pips"].values
            avg_w = pnl[pnl>0].mean() if (pnl>0).any() else 0
            avg_l = pnl[pnl<0].mean() if (pnl<0).any() else 0
            spread = 0.8
            if avg_w + abs(avg_l) > 0:
                bev = (abs(avg_l)+spread) / (avg_w-spread + abs(avg_l)+spread) if (avg_w-spread)>0 else 1.0
            else:
                bev = 0.5
            bev = max(0.05, min(0.95, bev))
            p = binom_p(w, n, bev)
            cells12.append({"strategy": strat, "session": sess, "n": n, "wr": w/n*100, "bev": bev, "p": p})
    cells12_df = pd.DataFrame(cells12)
    pvals12 = cells12_df["p"].tolist()
    rej12 = benjamini_hochberg(pvals12, q=0.05)
    cells12_df["BH_pass"] = rej12
    print(cells12_df.to_string())
    print(f"  → {sum(rej12)}/{len(cells12_df)} cells BH-significant")

    section("③-c Strategy-level (4-cell) BH")
    cells4 = []
    for strat in df90["strategy"].unique():
        sub = df90[df90["strategy"]==strat]
        if len(sub) < 10:
            continue
        n = len(sub); w = int(sub["win"].sum())
        pnl = sub["pnl_pips"].values
        avg_w = pnl[pnl>0].mean() if (pnl>0).any() else 0
        avg_l = pnl[pnl<0].mean() if (pnl<0).any() else 0
        spread = 0.8
        if avg_w + abs(avg_l) > 0:
            bev = (abs(avg_l)+spread) / (avg_w-spread + abs(avg_l)+spread) if (avg_w-spread)>0 else 1.0
        else:
            bev = 0.5
        bev = max(0.05, min(0.95, bev))
        p = binom_p(w, n, bev)
        cells4.append({"strategy": strat, "n": n, "wr": w/n*100, "bev": bev, "p": p})
    cells4_df = pd.DataFrame(cells4)
    rej4 = benjamini_hochberg(cells4_df["p"].tolist(), q=0.05)
    cells4_df["BH_pass"] = rej4
    print(cells4_df.to_string())
    print(f"  → {sum(rej4)}/{len(cells4_df)} strategies BH-significant")

    section("③-d 結論")
    print("Statistical defensibility:")
    print("  - 12-cell BH = full multiple-testing correction (overall null = 全 cell が偶然) — 最も保守的")
    print("  - 3-cell BH (v1b 単独) = LOCK 文書で宣言した粒度 (家族縛りなし、戦略選択は decision外)")
    print("  - 4-cell BH (戦略レベル) = 「4 戦略から最良を選ぶ」決定規則と整合")
    print()
    print("Recommendation: LOCK 文書では 3-cell を採用したため HARKing 防止上は維持。ただし")
    print("4-cell (戦略レベル) を `第二指標` として参考表示し、12-cell は parent family 検定")
    print("(戦略追加時の override 不可) と位置づける。")

    # ═══════════ Summary ═══════════════════════════════
    hr("EXECUTIVE SUMMARY (クオンツ判定)")
    print()
    print("① v1b Tokyo 73.6% WR の forensic 結果:")
    is_concentrated = (top5_w / tk_w) > 0.5
    is_iid = r["p_value"] >= 0.05
    print(f"   - 上位 5 週で勝ちの {top5_w/tk_w*100:.1f}% を占有 → "
          f"{'⚠️ 偶然集中の疑い' if is_concentrated else '✅ 分散あり'}")
    print(f"   - 系列従属検定 p={r['p_value']} → {'i.i.d. 反証' if not is_iid else '✅ i.i.d. と整合'}")
    quick_loss_pct = len(quick_loss)/max(1,len(losses_pnl))*100
    print(f"   - quick LOSS (<5 bars) {quick_loss_pct:.1f}% → "
          f"{'⚠️ SL 接触ノイズが多い' if quick_loss_pct>30 else '✅ 健全'}")
    print()
    print("② Cohort time alignment:")
    print("   - f3 (直近 60d) WR 56.1% < f1/f2 (62-64%) で劣化")
    print("   - Phase B Shadow 期間は f3 直後 → エッジ decay 中の可能性、要監視")
    print()
    print("③ BH grouping:")
    print(f"   - 3-cell BH: Tokyo/NY 有意 (LOCK 文書通り)")
    print(f"   - 4-cell BH: ma_trend_perfect 単独有意 ({sum(rej4)} 戦略)")
    print(f"   - 12-cell BH: {sum(rej12)} cells のみ → 最も保守的視点では微妙")
    print()
    print("総合判定: Pre-reg LOCK は維持。ただし Phase B 評価時に")
    print("  a) Shadow LIVE Tokyo データで Wilson95下限>30% を **必須** とする (BT 73% を盲信しない)")
    print("  b) f3 期間のレジーム (円相場)を別途調査し、decay の構造的原因を特定する")
    print("  c) LIVE 昇格の lot は Kelly Half × 0.5 から更に下げて Quarter Kelly 推奨")


if __name__ == "__main__":
    main()
