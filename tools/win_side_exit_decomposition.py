#!/usr/bin/env python3
"""Win-side exit decomposition — なぜ avg_win が縮んだのかを実測で分解する。

背景: 2026-09-13 cell deepdive (`knowledge-base/raw/cell_deepdive/2026-09-13/`) が
`sr_anti_hunt_bounce` の R:R 反転 (2.30 → 0.25) を検出し、その主因が「負け拡大」ではなく
**avg_win の 1/5 への縮小** (19.03p → 3.5〜5.9p) であることを特定した。本ツールはその
avg_win 縮小を close_reason / MFE capture / pair mix の3軸へ帰属させる。

estimand (宣言):
  対象 = 指定 entry_type の **closed trade** のうち XAU 除外 / dedup_violation=1 除外 /
  outcome ∈ {WIN, LOSS}。avg_win = outcome=WIN 行の pnl_pips 平均 (pips)。
  「勝ち側 capture」= WIN 行の pnl_pips / mafe_favorable_pips。
  ⚠️ close_reason="SL_HIT" は BE/トレール利確も含む混成ラベル
  (MEMORY project_sl_hit_label_collision)。よって全ての close_reason 分解は
  **outcome で必ず分割**して読む。close_reason 単独での集計は行わない。

出力は stdout の Markdown。副作用なし。

Usage:
  curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000" -o /tmp/prod_trades.json
  python3 tools/win_side_exit_decomposition.py /tmp/prod_trades.json --strategy sr_anti_hunt_bounce
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime

# ── shadow exit regime break ──────────────────────────────────────────────
# commit ab7a4931 "fix(exit): persist shadow SL changes directly to DB" が
# 2026-06-03 16:58 JST (= 07:58 UTC) にデプロイされるまで、shadow trade の SL 変更は
# OandaBridge.modify_sl_sync の False 戻りにより毎 iteration ロールバックされていた。
# すなわち BE-lock / SMC BE+0.1 / ATR×0.8 BE / ATR×1.5 trail / v6.4 TP extender の
# **全てが shadow 上で dead code** だった (lesson-shadow-sl-rollback-bug-2026-06-03)。
#
# 帰結: この時刻の前後で shadow の payoff 統計 (avg_win / R:R / WR / hold time) は
# **別の estimand** になる。境界をまたぐ shadow 集計は比較不能。
# 実測 (全戦略 shadow, XAU除外/dedup除外): WR 26.3%→51.5% / avg_win 11.72→4.35p /
# R:R 1.90→0.55 / WIN 行の close_reason=SL_HIT 比率 0.3%→88.3%。
SHADOW_EXIT_REGIME_BREAK = "2026-06-03T07:58"


def month_of(iso: str | None) -> str:
    return (iso or "")[:7] or "unknown"


def _hold_hours(entry_iso: str | None, exit_iso: str | None) -> float | None:
    if not entry_iso or not exit_iso:
        return None
    try:
        a = datetime.fromisoformat(entry_iso.replace("Z", "+00:00"))
        b = datetime.fromisoformat(exit_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (b - a).total_seconds() / 3600.0


def load_clean(path: str, strategy: str | None) -> list[dict]:
    with open(path) as f:
        payload = json.load(f)
    out = []
    for t in payload.get("trades", []):
        if strategy and t.get("entry_type") != strategy:
            continue
        if "XAU" in (t.get("instrument") or ""):
            continue
        if t.get("dedup_violation") == 1:
            continue
        if t.get("outcome") not in ("WIN", "LOSS"):
            continue
        out.append({
            "entry_type": t.get("entry_type"),
            "instrument": t.get("instrument"),
            "direction": t.get("direction"),
            "win": t.get("outcome") == "WIN",
            "pnl": float(t.get("pnl_pips") or 0.0),
            "mfe": float(t.get("mafe_favorable_pips") or 0.0),
            "mae": float(t.get("mafe_adverse_pips") or 0.0),
            "reason": t.get("close_reason") or "(null)",
            "entry_time": t.get("entry_time"),
            "hold_h": _hold_hours(t.get("entry_time"), t.get("exit_time")),
            "month": month_of(t.get("entry_time")),
            "is_shadow": bool(t.get("is_shadow")),
        })
    return out


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def fmt(x: float | None, nd: int = 2) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def monthly_table(rows: list[dict]) -> str:
    by_m = defaultdict(list)
    for r in rows:
        by_m[r["month"]].append(r)
    lines = ["| month | N | WR | avg_win | avg_loss | R:R | EV_net |",
             "|---|---|---|---|---|---|---|"]
    for m in sorted(by_m):
        rs = by_m[m]
        w = [r["pnl"] for r in rs if r["win"]]
        l = [-r["pnl"] for r in rs if not r["win"]]
        aw, al = mean(w), mean(l)
        rr = (aw / al) if al > 0 else None
        lines.append(f"| {m} | {len(rs)} | {len(w)/len(rs):.1%} | {fmt(aw) if w else '—'} | "
                     f"{fmt(al) if l else '—'} | {fmt(rr)} | {mean([r['pnl'] for r in rs]):+.2f} |")
    return "\n".join(lines)


def reason_outcome_table(rows: list[dict], label: str) -> str:
    """close_reason × outcome。SL_HIT ラベル衝突があるため outcome 分割は必須。"""
    g = defaultdict(list)
    for r in rows:
        g[(r["reason"], "WIN" if r["win"] else "LOSS")].append(r)
    reasons = sorted({k[0] for k in g})
    lines = [f"**{label}**", "",
             "| close_reason | N_win | avg_win | N_loss | avg_loss | win_share |",
             "|---|---|---|---|---|---|"]
    tot_w = sum(1 for r in rows if r["win"])
    for rsn in reasons:
        w = [x["pnl"] for x in g.get((rsn, "WIN"), [])]
        l = [-x["pnl"] for x in g.get((rsn, "LOSS"), [])]
        share = (len(w) / tot_w) if tot_w else 0.0
        lines.append(f"| {rsn} | {len(w)} | {fmt(mean(w)) if w else '—'} | {len(l)} | "
                     f"{fmt(mean(l)) if l else '—'} | {share:.1%} |")
    return "\n".join(lines)


def shift_share(rows_a: list[dict], rows_b: list[dict], key: str) -> tuple[str, float, float]:
    """avg_win の A→B 変化を mix 効果 / within 効果へ分解 (Oaxaca 型)。

    avg_win = Σ_k s_k * m_k  (s = 構成比, m = 群内 avg_win)
    Δ = Σ_k (s_k^B - s_k^A) * m_k^A   [mix]
      + Σ_k s_k^B * (m_k^B - m_k^A)   [within]
    群が片側にしか無い場合、その群の欠側 m は反対側の全体 avg_win で代用 (保守的)。
    """
    wa = [r for r in rows_a if r["win"]]
    wb = [r for r in rows_b if r["win"]]
    if not wa or not wb:
        return "(片側に WIN 行が無く分解不能)", 0.0, 0.0
    ga, gb = defaultdict(list), defaultdict(list)
    for r in wa:
        ga[r[key]].append(r["pnl"])
    for r in wb:
        gb[r[key]].append(r["pnl"])
    base_a, base_b = mean([r["pnl"] for r in wa]), mean([r["pnl"] for r in wb])
    keys = sorted(set(ga) | set(gb))
    mix = within = 0.0
    lines = ["| " + key + " | share_A | avg_win_A | share_B | avg_win_B | mix寄与 | within寄与 |",
             "|---|---|---|---|---|---|---|"]
    for k in keys:
        sa = len(ga.get(k, [])) / len(wa)
        sb = len(gb.get(k, [])) / len(wb)
        ma = mean(ga[k]) if k in ga else base_a
        mb = mean(gb[k]) if k in gb else base_b
        c_mix = (sb - sa) * ma
        c_within = sb * (mb - ma)
        mix += c_mix
        within += c_within
        lines.append(f"| {k} | {sa:.1%} | {fmt(ma)} | {sb:.1%} | {fmt(mb)} | {c_mix:+.2f} | {c_within:+.2f} |")
    lines.append(f"| **合計** | | **{fmt(base_a)}** | | **{fmt(base_b)}** | **{mix:+.2f}** | **{within:+.2f}** |")
    return "\n".join(lines), mix, within


def capture_table(rows: list[dict]) -> str:
    """勝ち側 capture = realized / MFE。roadmap v2.3 T3 の capture 0.0944 と同じ軸。"""
    by_m = defaultdict(list)
    for r in rows:
        if r["win"] and r["mfe"] > 0:
            by_m[r["month"]].append(r)
    lines = ["| month | N_win(MFE>0) | avg_MFE | avg_win | capture | 取り残し |",
             "|---|---|---|---|---|---|"]
    for m in sorted(by_m):
        rs = by_m[m]
        amfe, apnl = mean([r["mfe"] for r in rs]), mean([r["pnl"] for r in rs])
        lines.append(f"| {m} | {len(rs)} | {fmt(amfe)} | {fmt(apnl)} | "
                     f"{fmt(apnl/amfe, 3) if amfe > 0 else '—'} | {fmt(amfe-apnl)} |")
    return "\n".join(lines)


def hold_hours(rows: list[dict]) -> str:
    """WIN 行の保有時間。BE/trail が効くと中央値が短縮するため regime break の直接指標。"""
    by_m = defaultdict(list)
    for r in rows:
        if r["win"] and r["hold_h"] is not None:
            by_m[r["month"]].append(r["hold_h"])
    lines = ["| month | N_win | median_hold_h | avg_hold_h |", "|---|---|---|---|"]
    for m in sorted(by_m):
        h = sorted(by_m[m])
        lines.append(f"| {m} | {len(h)} | {fmt(h[len(h)//2])} | {fmt(mean(h))} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("trades_json")
    ap.add_argument("--strategy", default="sr_anti_hunt_bounce",
                    help="entry_type。'ALL' で全戦略横断")
    ap.add_argument("--split-at", default=SHADOW_EXIT_REGIME_BREAK,
                    help="この entry_time 以降を期間 B、それ未満を期間 A とする "
                         f"(既定 = shadow exit regime break {SHADOW_EXIT_REGIME_BREAK})")
    args = ap.parse_args()

    strat = None if args.strategy == "ALL" else args.strategy
    rows = load_clean(args.trades_json, strat)
    if not rows:
        raise SystemExit(f"no clean rows for {args.strategy}")

    split = args.split_at
    a = [r for r in rows if (r["entry_time"] or "") < split]
    b = [r for r in rows if (r["entry_time"] or "") >= split]

    print(f"# Win-side exit decomposition — {args.strategy}\n")
    print(f"- clean N = **{len(rows)}** (XAU除外 / dedup除外 / outcome∈{{WIN,LOSS}})")
    print(f"- span: {min(r['entry_time'] or '' for r in rows)} → {max(r['entry_time'] or '' for r in rows)}")
    print(f"- 期間 A = < {split} (N={len(a)}) / 期間 B = ≥ {split} (N={len(b)})")
    if split == SHADOW_EXIT_REGIME_BREAK:
        print("- ⚠️ 既定の split は **shadow exit regime break** (commit ab7a4931)。"
              "境界をまたぐ shadow の payoff 集計は estimand が異なるため比較不能")
    print(f"- shadow 比率 {sum(1 for r in rows if r['is_shadow'])/len(rows):.1%}\n")

    print("## 1. 月次ペイオフ (再現)\n")
    print(monthly_table(rows), "\n")

    print("## 2. close_reason × outcome (SL_HIT ラベル衝突対応)\n")
    print(reason_outcome_table(a, f"期間 A (< {split})"), "\n")
    print(reason_outcome_table(b, f"期間 B (≥ {split})"), "\n")

    print("## 3. avg_win 変化の帰属 — shift-share 分解\n")
    for key, label in (("reason", "close_reason 軸"), ("instrument", "pair 軸")):
        tbl, mix, within = shift_share(a, b, key)
        d = mix + within
        print(f"### {label}\n")
        print(tbl, "\n")
        if d:
            print(f"→ Δavg_win = {d:+.2f}p のうち mix {mix:+.2f}p ({mix/d:.0%}) / "
                  f"within {within:+.2f}p ({within/d:.0%})\n")

    print("## 4. 勝ち側 capture (realized / MFE)\n")
    print("> ⚠️ MFE は exit 時点までしか観測されない。exit を早めると測定 MFE は"
          "機械的に縮むため、capture 単独で「相場が走らなくなった」と読んではいけない。"
          "§5 の保有時間と併せて読むこと。\n")
    print(capture_table(rows), "\n")

    print("## 5. WIN 行の保有時間 (exit mechanism の直接指標)\n")
    print(hold_hours(rows), "\n")


if __name__ == "__main__":
    main()
