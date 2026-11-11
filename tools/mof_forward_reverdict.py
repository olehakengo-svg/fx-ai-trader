#!/usr/bin/env python3
"""MoF forward pre-reg (台帳 #4) — §5.5 PARTIAL 分岐の「次の円買いエピソード 1 回限り同一仕様再判定」。

Spec (凍結、変更禁止): knowledge-base/wiki/decisions/mof-intervention-forward-prereg-2026-07-24.md
  §2.2 estimand / §5.1-5.4 ゲート / §5.5 固定分岐 / §8 ナイフエッジ 3 点検査 / §10 verdict (2026-08-18 PARTIAL)。
本 tool は tools/mof_forward_verdict.py (2026-08-18 執行) と同一の計算を、エピソード固有の凍結入力
(窓 / 開示 D) だけ差し替えて 1 回適用する。識別 rule (X,Y)、h*、予測符号、band、α、k 規約は
2026-07-24 LOCK 値をそのまま使う (新自由度ゼロ)。

エピソード固有入力 (観測前に外部一次情報で確定した順序を注記):
  - 窓 WIN = 月次開示 (mof.go.jp data/monthly/20260828.html、公表 2026-08-28) の対象窓 2026-07-30〜08-26
    (15兆3,993億円)。日次ラベル観測 (11-09) より **前** に KB に記録済み (mof-monthly-total-verdict-2026-08-31)。
  - 開示 D = 四半期開示 (data/quarter/2026_3Q.html、公表 2026-11-09): 07-30 ¥7兆9,756億 / 07-31 ¥5兆5,523億 /
    08-03 ¥1兆8,714億、全て米ドル売り・日本円買い。
  - candidate list S は本 tool 内で凍結 rule を窓に 1 回適用して生成する (初回 verdict と異なり LOCK 時点の
    事前凍結 S は存在しない — rule と窓が決定論的に S を定めるため裁量はないが、D 観測後の計算である事実を
    §11 peek 会計に明記する)。

Usage: python3 tools/mof_forward_reverdict.py [--parquet PATH] [--out-dir DIR] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from math import comb
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DEFAULT_P15 = Path("/Users/jg-n-012/test/fx-ai-trader/data/cache/massive/USD_JPY_15m.parquet")

# ── 凍結 (2026-07-24 LOCK、変更禁止) ────────────────────────────────────────
X_FROZEN, Y_FROZEN = 2.0, 0.25            # §2.2 identification rule
RANGE_MED_LOOKBACK = 20                   # trailing-20d median range
ALPHA = 0.10                              # §5.2 one-shot
S_CAP = 5                                 # |S| ≤ 5 事前上限
H_STAR = 10                               # §5.3 h*
HORIZONS = (1, 2, 5, 10)
PRED_SIGN = -1                            # §5.3 予測符号 = 負 (SELL)
BAND = (-319.8, -43.6)                    # §5.3 記述 band [P25, P75]
ED_K_RANGE = (2, 5)                       # §5.4 E-D
ED_MAX_SINGLE_BN = 3000.0                 # §5.4 最大単日 ≥ ¥3.0T (十億円)
PIP = 0.01
PERTURB = (("X-20%", 1.6, 0.25), ("X+20%", 2.4, 0.25), ("Y-20%", 2.0, 0.20), ("Y+20%", 2.0, 0.30))

# ── エピソード固有の凍結入力 (再判定 2026-11-11) ───────────────────────────
EPISODE_ID = "2026Q3"
WIN = (date(2026, 7, 30), date(2026, 8, 26))      # 月次開示 20260828.html (公表 08-28、D 観測前)
D_DISCLOSED = {                                     # 四半期開示 2026_3Q.html (公表 2026-11-09)、十億円
    date(2026, 7, 30): 7975.6,
    date(2026, 7, 31): 5552.3,
    date(2026, 8, 3): 1871.4,
}
D_PAIR, D_DIRECTION = "USD/JPY", "sell_USD_buy_JPY"
EB_PRED_PAIR, EB_PRED_DIRECTION = "USD/JPY", "sell_USD_buy_JPY"   # §5.1 凍結予測


# ── 純粋関数 (test pin 対象) ──────────────────────────────────────────────
def hyper_p_ge(ov: int, M: int, s: int, k: int) -> float:
    """P(|S ∩ D| ≥ ov) — D は M 日から一様 k 日抽出、S は固定 s 日。"""
    tot = comb(M, k)
    return sum(comb(s, j) * comb(M - s, k - j) for j in range(ov, min(s, k) + 1)) / tot


def ea_pass(overlap: int, k_eff: int, p: float) -> bool:
    """§5.2: k_eff=1 → overlap≥1、k_eff≥2 → overlap≥2 かつ p≤α。"""
    if k_eff <= 0:
        return False
    if k_eff == 1:
        return overlap >= 1 and p <= ALPHA
    return overlap >= 2 and p <= ALPHA


def rule_candidate(co_ret_pct: float, range_ratio: float, x: float = X_FROZEN, y: float = Y_FROZEN) -> bool:
    return co_ret_pct <= -y and range_ratio >= x


def daily_from_15m(df: pd.DataFrame) -> pd.DataFrame:
    """UTC-day 集計 (§2.2 凍結: 09:00 JST 境界 = 東京営業日)、週末除外、range/co_ret/trailing median。"""
    d = df[["Open", "High", "Low", "Close"]].copy()
    d["day"] = [t.date() for t in d.index]
    day = d.groupby("day").agg(Open=("Open", "first"), High=("High", "max"),
                               Low=("Low", "min"), Close=("Close", "last"))
    day = day[[x.weekday() < 5 for x in day.index]]
    day["range"] = day.High - day.Low
    day["co_ret"] = day.Close / day.Open - 1.0
    day["trail_med_range"] = day["range"].rolling(RANGE_MED_LOOKBACK).median().shift(1)
    return day


def candidates(day: pd.DataFrame, pop: list[date], x: float, y: float) -> list[date]:
    out = []
    for dd in pop:
        r = day.loc[dd]
        if pd.isna(r.trail_med_range):
            continue
        if rule_candidate(r.co_ret * 100.0, r.range / r.trail_med_range, x, y):
            out.append(dd)
    return out


def verdict_branch(g0: bool, eb: bool, ea: bool, ec: bool) -> str:
    """§5.5 固定分岐。"""
    if not (g0 and eb):
        return "NO-TEST"
    if ea and ec:
        return "PASS"
    if ea or ec:
        return "PARTIAL"
    return "FAIL"


# ── 計算本体 ──────────────────────────────────────────────────────────────
def run(p15: Path) -> dict:
    bars = pd.read_parquet(p15)
    bars = bars[["Open", "High", "Low", "Close"]].copy()
    bars["day"] = [t.date() for t in bars.index]
    day = daily_from_15m(bars)
    days = list(day.index)

    # population M = 窓内のデータ存在営業日 (§5.2 k 規約: 欠損日は母集団外)
    pop = [dd for dd in days if WIN[0] <= dd <= WIN[1]]
    missing_bd = []
    cur = WIN[0]
    while cur <= WIN[1]:
        if cur.weekday() < 5 and cur not in day.index:
            missing_bd.append(cur)
        cur += timedelta(days=1)
    M = len(pop)

    # S = 凍結 rule の 1 回適用
    S = candidates(day, pop, X_FROZEN, Y_FROZEN)
    s_cap_ok = len(S) <= S_CAP

    # G0 / E-B
    D = sorted(D_DISCLOSED)
    g0 = any(WIN[0] <= dd <= WIN[1] for dd in D)
    eb = (D_PAIR == EB_PRED_PAIR) and (D_DIRECTION == EB_PRED_DIRECTION)

    # E-A
    D_in_pop = [dd for dd in D if dd in pop]
    k_eff = len(D_in_pop)
    overlap = len(set(S) & set(D))
    pA = hyper_p_ge(overlap, M, len(S), k_eff) if (len(S) > 0 and k_eff > 0) else 1.0
    ea = ea_pass(overlap, k_eff, pA) and s_cap_ok
    # 閾値脆弱性 (§8.3): overlap ±1 で α を跨ぐか
    p_minus1 = hyper_p_ge(max(overlap - 1, 0), M, len(S), k_eff) if (len(S) > 0 and k_eff > 0) else 1.0

    # E-C
    def next_bd(dd: date) -> date:
        later = [x for x in days if x > dd]
        return later[0]

    def bd_offset(dd: date, h: int) -> date:
        return days[days.index(dd) + h]

    def first_bar_open(dd: date):
        sub = bars[bars["day"] == dd]
        return float(sub["Open"].iloc[0]), sub.index[0]

    def forward_row(anchor_day: date) -> dict:
        p0, t0 = first_bar_open(anchor_day)
        row = {"anchor": str(anchor_day), "p0": p0}
        for h in HORIZONS:
            ph, _ = first_bar_open(bd_offset(anchor_day, h))
            row[f"net_h{h}"] = round((ph - p0) / PIP, 1)       # SELL 有利 = 負
        dend = bd_offset(anchor_day, H_STAR)
        seg = bars[(bars.index >= t0) & (bars["day"] < dend)]
        row["mfe_sell_h10"] = round((p0 - float(seg["Low"].min())) / PIP, 1)
        row["mae_sell_h10"] = round((float(seg["High"].max()) - p0) / PIP, 1)
        return row

    rows = []
    for ev in D:
        r = forward_row(next_bd(ev))
        r = {"event": str(ev), **r}
        rows.append(r)

    def median(xs):
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0

    med = {f"h{h}": median([r[f"net_h{h}"] for r in rows]) for h in HORIZONS}
    med_hstar = med[f"h{H_STAR}"]
    ec = (med_hstar < 0) if PRED_SIGN < 0 else (med_hstar > 0)
    in_band = BAND[0] <= med_hstar <= BAND[1]
    # episode-初日 anchor 変種 (§8.2 感度、判定不使用)
    ep_first = forward_row(next_bd(D[0]))

    # E-D (記述)
    k = len(D)
    max_single = max(D_DISCLOSED.values())
    ed_k_ok = ED_K_RANGE[0] <= k <= ED_K_RANGE[1]
    ed_max_ok = max_single >= ED_MAX_SINGLE_BN

    # §8.1 機構分解
    decomp = {}
    for dd in sorted(set(S) | set(D)):
        r = day.loc[dd]
        decomp[str(dd)] = {
            "co_ret_pct": round(r.co_ret * 100.0, 3),
            "co_ret_hit": bool(r.co_ret * 100.0 <= -Y_FROZEN),
            "range_p": round(r.range / PIP, 1),
            "x_trail_med_p": round(X_FROZEN * r.trail_med_range / PIP, 1),
            "range_ratio": round(r.range / r.trail_med_range, 2),
            "range_hit": bool(r.range >= X_FROZEN * r.trail_med_range),
            "in_S": dd in S, "in_D": dd in D,
        }
    # §8.3 摂動
    perturb = {lbl: [str(x) for x in candidates(day, pop, x, y)] for lbl, x, y in PERTURB}
    # §8.2 擬似反復: gap≥30d クラスタ
    clusters = 1
    for a, b in zip(D, D[1:]):
        if (b - a).days >= 30:
            clusters += 1

    v = verdict_branch(g0, eb, ea, ec)
    return {
        "episode": EPISODE_ID, "spec": "mof-intervention-forward-prereg-2026-07-24 §5 (LOCK 2026-07-24) / §5.5 PARTIAL 1 回限り再判定",
        "parquet": str(p15), "parquet_end": str(bars.index.max()),
        "window": [str(WIN[0]), str(WIN[1])], "M": M, "missing_business_days": [str(x) for x in missing_bd],
        "rule": {"X": X_FROZEN, "Y_pct": Y_FROZEN, "lookback": RANGE_MED_LOOKBACK},
        "S": [str(x) for x in S], "S_cap_ok": s_cap_ok,
        "D": {str(k_): v_ for k_, v_ in D_DISCLOSED.items()}, "D_pair": D_PAIR, "D_direction": D_DIRECTION,
        "G0": g0, "E_B": eb,
        "E_A": {"k_eff": k_eff, "overlap": overlap, "p": round(pA, 4), "alpha": ALPHA, "pass": ea,
                "p_if_overlap_minus1": round(p_minus1, 4)},
        "E_C": {"h_star": H_STAR, "pred_sign": "neg(SELL)", "band": list(BAND), "rows": rows,
                "median": med, "median_hstar": med_hstar, "in_band": in_band, "pass": ec,
                "episode_first_day_anchor": ep_first},
        "E_D": {"k": k, "k_range": list(ED_K_RANGE), "k_ok": ed_k_ok, "max_single_bn": max_single,
                "max_single_ok": ed_max_ok},
        "knife_edge": {"mechanism": decomp, "clusters_gap30d": clusters, "effective_episodes": clusters,
                       "perturb": perturb},
        "verdict": v,
    }


def render(res: dict) -> str:
    L = []
    L.append(f"# MoF forward pre-reg 再判定 (§5.5 PARTIAL → 1 回限り同一仕様) — episode {res['episode']}")
    L.append(f"parquet = {res['parquet']} (end {res['parquet_end']})")
    L.append(f"window = {res['window'][0]}..{res['window'][1]} | M = {res['M']} | missing bd = {res['missing_business_days']}")
    L.append(f"rule (frozen) = (X,Y)=({res['rule']['X']},{res['rule']['Y_pct']}%) | S = {res['S']} | |S|<=5: {res['S_cap_ok']}")
    L.append(f"D = {res['D']} ({res['D_pair']} {res['D_direction']})")
    L.append(f"G0 = {res['G0']} | E-B = {res['E_B']}")
    ea = res["E_A"]
    L.append(f"E-A: k_eff={ea['k_eff']} overlap={ea['overlap']} p={ea['p']} (alpha {ea['alpha']}) -> {'PASS' if ea['pass'] else 'FAIL'} | p if overlap-1 = {ea['p_if_overlap_minus1']}")
    ec = res["E_C"]
    for r in ec["rows"]:
        L.append(f"  {r['event']} anchor {r['anchor']} p0 {r['p0']:.3f}: h1 {r['net_h1']} h2 {r['net_h2']} h5 {r['net_h5']} h10 {r['net_h10']} | MFE_sell {r['mfe_sell_h10']} MAE_sell {r['mae_sell_h10']}")
    L.append(f"E-C: median net_h{ec['h_star']} = {ec['median_hstar']}p (pred {ec['pred_sign']}, band {ec['band']}, in_band={ec['in_band']}) -> {'PASS' if ec['pass'] else 'FAIL'} | medians {ec['median']}")
    ef = ec["episode_first_day_anchor"]
    L.append(f"  episode-first-day anchor {ef['anchor']}: h10 {ef['net_h10']} (MFE {ef['mfe_sell_h10']} / MAE {ef['mae_sell_h10']})")
    ed = res["E_D"]
    L.append(f"E-D: k={ed['k']} in {ed['k_range']}: {ed['k_ok']} | max single ¥{ed['max_single_bn']}bn >= 3000: {ed['max_single_ok']}")
    ke = res["knife_edge"]
    L.append("§8.1 mechanism:")
    for dd, m in ke["mechanism"].items():
        L.append(f"  {dd}: co_ret {m['co_ret_pct']}% hit={m['co_ret_hit']} | range {m['range_p']}p vs {m['x_trail_med_p']}p (ratio {m['range_ratio']}) hit={m['range_hit']} | S={m['in_S']} D={m['in_D']}")
    L.append(f"§8.2 clusters (gap>=30d) = {ke['clusters_gap30d']} -> effective N = {ke['effective_episodes']} episode")
    L.append(f"§8.3 perturb: {ke['perturb']}")
    L.append(f"VERDICT = {res['verdict']}")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parquet", type=Path, default=DEFAULT_P15)
    ap.add_argument("--out-dir", type=Path, default=REPO / "knowledge-base" / "raw" / "bt-results")
    ap.add_argument("--stamp", default="2026-11-11")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    res = run(a.parquet)
    txt = render(res)
    print(txt)
    if not a.no_write:
        a.out_dir.mkdir(parents=True, exist_ok=True)
        (a.out_dir / f"mof-forward-reverdict-{a.stamp}.txt").write_text(txt + "\n", encoding="utf-8")
        (a.out_dir / f"mof-forward-reverdict-{a.stamp}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
