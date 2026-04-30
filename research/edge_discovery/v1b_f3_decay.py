"""v1b f3 decay forensic — どこで何が劣化したかの構造解析

LOCK Failure Condition #3 ("WR 連続 12d 下落") の判断基準を defensible に
するため、f3 (2026-02-09〜04-13) の劣化が:
  (a) どのセッションに集中しているか
  (b) WR drop / avg_win 縮小 / avg_loss 拡大 / hold time 変化のどれか
  (c) 月次 / 半月次でどう推移しているか
を実測する。

Phase B Shadow 期間 (2026-04-30〜05-14) の判断基準を出力。
"""
from __future__ import annotations
import sys
from pathlib import Path
import math

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

V1B_TRADES = "knowledge-base/raw/audits/ma_family_v1/USD_JPY_trades_20260430_064233.csv"


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / den) * 100.0


def cell_stats(sub: pd.DataFrame) -> dict:
    n = len(sub)
    if n == 0:
        return {"n": 0}
    w = int((sub["outcome"] == "WIN").sum())
    pnls = sub["pnl_pips"].values
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    avg_w = float(wins.mean()) if len(wins) else 0.0
    avg_l = float(losses.mean()) if len(losses) else 0.0
    pf = (wins.sum() / -losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    if pf == float("inf"):
        pf = 99.9
    return {
        "n": n, "w": w, "wr": w/n*100,
        "wilson_lo": wilson_lower(w, n),
        "ev": float(pnls.mean()),
        "pf": pf,
        "avg_win": avg_w, "avg_loss": avg_l,
        "avg_exit_bars": float(sub["exit_bars"].mean()),
        "median_exit_bars": float(sub["exit_bars"].median()),
    }


def hr(t):
    print()
    print("═" * 78); print(t); print("═" * 78)


def section(t):
    print()
    print("─" * 78); print(t); print("─" * 78)


def main():
    df = pd.read_csv(V1B_TRADES)
    df["ts"] = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date
    df["win"] = (df["outcome"] == "WIN").astype(int)

    n_all = len(df)
    fold_size = n_all // 3
    df_sorted = df.sort_values("ts").reset_index(drop=True)
    folds = {
        "f1": df_sorted.iloc[0:fold_size],
        "f2": df_sorted.iloc[fold_size:2*fold_size],
        "f3": df_sorted.iloc[2*fold_size:n_all],
    }

    hr("v1b f3 DECAY FORENSIC — どこで何が劣化したか")
    print(f"Source: {V1B_TRADES}")
    print(f"f1: {folds['f1']['date'].min()} → {folds['f1']['date'].max()}  (N={len(folds['f1'])})")
    print(f"f2: {folds['f2']['date'].min()} → {folds['f2']['date'].max()}  (N={len(folds['f2'])})")
    print(f"f3: {folds['f3']['date'].min()} → {folds['f3']['date'].max()}  (N={len(folds['f3'])})")

    # ───────── (a) Session × fold cell decomposition ─────────
    section("(a) Session × Fold cell — どのセッションが decay の主因か")
    rows = []
    for sess in ("Tokyo", "London", "NY"):
        for fname, fsub in folds.items():
            cell = fsub[fsub["session"] == sess]
            s = cell_stats(cell)
            s["session"] = sess
            s["fold"] = fname
            rows.append(s)
    cells = pd.DataFrame(rows)
    cells = cells[["session", "fold", "n", "wr", "wilson_lo", "ev", "pf", "avg_win", "avg_loss", "avg_exit_bars"]]
    print(cells.to_string(index=False))

    print()
    print("Δ (f3 - f1) per session:")
    for sess in ("Tokyo", "London", "NY"):
        f1 = cells[(cells["session"]==sess) & (cells["fold"]=="f1")].iloc[0]
        f3 = cells[(cells["session"]==sess) & (cells["fold"]=="f3")].iloc[0]
        d_wr = f3["wr"] - f1["wr"]
        d_wilson = f3["wilson_lo"] - f1["wilson_lo"]
        d_pf = f3["pf"] - f1["pf"]
        d_ev = f3["ev"] - f1["ev"]
        d_aw = f3["avg_win"] - f1["avg_win"]
        d_al = f3["avg_loss"] - f1["avg_loss"]
        verdict = "🔴 大幅劣化" if d_wr < -10 else ("🟡 軽度劣化" if d_wr < -3 else "✅ 維持/改善")
        print(f"  {sess:<8} ΔWR={d_wr:+6.2f}%  ΔWilson={d_wilson:+6.2f}  ΔPF={d_pf:+5.2f}  ΔEV={d_ev:+5.3f}  Δavg_win={d_aw:+5.2f}  Δavg_loss={d_al:+5.2f}  {verdict}")

    # ───────── (b) Decay driver attribution ─────────
    section("(b) 劣化要因の分解 (Tokyo に絞り、最重要 cell)")
    tk_f1 = folds["f1"][folds["f1"]["session"]=="Tokyo"]
    tk_f3 = folds["f3"][folds["f3"]["session"]=="Tokyo"]
    s_f1 = cell_stats(tk_f1)
    s_f3 = cell_stats(tk_f3)
    print(f"  {'metric':<20} {'f1':<14} {'f3':<14} {'Δ':<10} {'解釈'}")
    print(f"  {'-'*68}")
    print(f"  {'N':<20} {s_f1['n']:<14} {s_f3['n']:<14} {s_f3['n']-s_f1['n']:<+10}")
    print(f"  {'WR%':<20} {s_f1['wr']:<14.2f} {s_f3['wr']:<14.2f} {s_f3['wr']-s_f1['wr']:<+10.2f}")
    print(f"  {'Wilson95下限%':<20} {s_f1['wilson_lo']:<14.2f} {s_f3['wilson_lo']:<14.2f} {s_f3['wilson_lo']-s_f1['wilson_lo']:<+10.2f}")
    print(f"  {'PF':<20} {s_f1['pf']:<14.3f} {s_f3['pf']:<14.3f} {s_f3['pf']-s_f1['pf']:<+10.3f}")
    print(f"  {'EV pip':<20} {s_f1['ev']:<14.3f} {s_f3['ev']:<14.3f} {s_f3['ev']-s_f1['ev']:<+10.3f}")
    print(f"  {'avg_win pip':<20} {s_f1['avg_win']:<14.3f} {s_f3['avg_win']:<14.3f} {s_f3['avg_win']-s_f1['avg_win']:<+10.3f}")
    print(f"  {'avg_loss pip':<20} {s_f1['avg_loss']:<14.3f} {s_f3['avg_loss']:<14.3f} {s_f3['avg_loss']-s_f1['avg_loss']:<+10.3f}")
    print(f"  {'avg_exit_bars':<20} {s_f1['avg_exit_bars']:<14.2f} {s_f3['avg_exit_bars']:<14.2f} {s_f3['avg_exit_bars']-s_f1['avg_exit_bars']:<+10.2f}")
    print(f"  {'median_exit_bars':<20} {s_f1['median_exit_bars']:<14.0f} {s_f3['median_exit_bars']:<14.0f} {s_f3['median_exit_bars']-s_f1['median_exit_bars']:<+10.0f}")

    # ───────── (c) 半月単位の WR 推移 ─────────
    section("(c) 半月次 WR 推移 — decay の時系列")
    df_sorted["half_month"] = df_sorted["ts"].dt.to_period("M").astype(str) + "_" + df_sorted["ts"].dt.day.apply(lambda d: "H1" if d<=15 else "H2")
    hm = df_sorted.groupby("half_month").agg(
        n=("win","size"), w=("win","sum"), pnl=("pnl_pips","sum"))
    hm["wr"] = hm["w"]/hm["n"]*100
    hm["wilson_lo"] = [round(wilson_lower(int(r["w"]), int(r["n"])), 2) for _, r in hm.iterrows()]
    hm["ev"] = hm["pnl"]/hm["n"]
    print(hm.to_string())

    # Trend slope
    if len(hm) >= 4:
        x = np.arange(len(hm))
        y = hm["wr"].values
        slope, intercept = np.polyfit(x, y, 1)
        print(f"\n  WR linear trend slope = {slope:+.2f}%/half-month  (n={len(hm)} half-months)")
        recent_3 = hm["wr"].iloc[-3:].mean()
        early_3 = hm["wr"].iloc[:3].mean()
        print(f"  早期 3 半月平均 WR: {early_3:.1f}%  →  直近 3 半月平均 WR: {recent_3:.1f}%  (Δ={recent_3-early_3:+.1f}%)")

    # ───────── (d) Phase B 監視指標 ─────────
    section("(d) Phase B Shadow 監視メトリクス (decay early warning)")

    # f3 baseline for comparison
    f3_tk = cell_stats(folds["f3"][folds["f3"]["session"]=="Tokyo"])
    f3_ny = cell_stats(folds["f3"][folds["f3"]["session"]=="NY"])

    print("Phase B Shadow LIVE (2026-04-30〜05-14) では以下を毎日監視:")
    print()
    print("Tokyo cell (f3 baseline):")
    print(f"  - N expected: {f3_tk['n']*14/62:.0f} trades / 14d (f3 N={f3_tk['n']}/62d 比例)")
    print(f"  - WR baseline (f3): {f3_tk['wr']:.1f}%  → 警報: WR < {f3_tk['wr']-10:.0f}%")
    print(f"  - Wilson95下限 baseline (f3): {f3_tk['wilson_lo']:.1f}%  → 必須: > 30% (LOCK Failure #1)")
    print(f"  - avg_exit_bars baseline (f3): {f3_tk['avg_exit_bars']:.1f}  → 警報: > {f3_tk['avg_exit_bars']*1.5:.1f} (delayed exit)")
    print()
    print("NY cell (f3 baseline):")
    print(f"  - N expected: {f3_ny['n']*14/62:.0f} trades / 14d")
    print(f"  - WR baseline (f3): {f3_ny['wr']:.1f}%  → 警報: WR < {f3_ny['wr']-10:.0f}%")
    print(f"  - Wilson95下限 baseline (f3): {f3_ny['wilson_lo']:.1f}%  → 必須: > 25% (LOCK Failure #2)")

    # ───────── (e) Conclusion ─────────
    hr("総合判定")
    print()

    tk_drop = cells[(cells["session"]=="Tokyo") & (cells["fold"]=="f3")]["wr"].iloc[0] - cells[(cells["session"]=="Tokyo") & (cells["fold"]=="f1")]["wr"].iloc[0]
    ny_drop = cells[(cells["session"]=="NY") & (cells["fold"]=="f3")]["wr"].iloc[0] - cells[(cells["session"]=="NY") & (cells["fold"]=="f1")]["wr"].iloc[0]
    london_drop = cells[(cells["session"]=="London") & (cells["fold"]=="f3")]["wr"].iloc[0] - cells[(cells["session"]=="London") & (cells["fold"]=="f1")]["wr"].iloc[0]

    print(f"Decay 集中度:")
    print(f"  Tokyo  f1→f3 ΔWR = {tk_drop:+.1f}%")
    print(f"  London f1→f3 ΔWR = {london_drop:+.1f}%")
    print(f"  NY     f1→f3 ΔWR = {ny_drop:+.1f}%")
    print()
    if abs(tk_drop) > 10 and abs(ny_drop) < 5:
        print("→ Tokyo 限定の decay (NY は維持) — 戦略全体の decay ではなく Tokyo 局所的レジーム変化")
    elif abs(tk_drop) > 5 and abs(ny_drop) > 5:
        print("→ 全セッション decay — 戦略全体のエッジ消耗 / マクロ regime shift の可能性")
    elif abs(tk_drop) < 3 and abs(ny_drop) < 3:
        print("→ Decay 限定的 — 全体ノイズ範囲、エッジ維持")
    else:
        print(f"→ 部分的 decay (Tokyo Δ={tk_drop:+.1f}%, NY Δ={ny_drop:+.1f}%, London Δ={london_drop:+.1f}%)")


if __name__ == "__main__":
    main()
