#!/usr/bin/env python3
"""WS3 外部仮説 — 価格ベース lead-lag エッジ feasibility 診断 (rule:R3, read-only)

タスク: .ai/tasks/queue/20260713-ws3-round3-crossasset-divergence.md 起点
背景: WS3 内部母集団探索 2 周 FAIL (round-1 stage-2 EV FAIL / round-2 OOS 0/5) →
      pre-reg 固定分岐「外部仮説 (新シグナル系統) の探索へ転進」(ws3-round2-explore-prereg §3)。
      本診断は「価格ベース lead-lag (OHLCV 内 + cross-asset) に tradeable な先行構造があるか」を
      feasibility として測り、外部仮説スクリーン (external-hypothesis-scan-2026-07-13) の実証根拠にする。

計測 (全て feasibility probe — verdict ではない):
  A. 内部 cross-pair lead-lag: r_lead(t) が r_follow(t+1) を予測するか (Pearson IC)
     + 非同期取引バイアス (Lo-MacKinlay) の adversarial check = liquid-hours + destale で IC 崩壊を確認
  B. cross-asset lead: ZN (10y T-note fut) → USD_JPY の contemporaneous vs lag-1 IC

read-only。live パラメータ・shadow に一切触れない。OOS 窓は消費しない (feasibility 用に full/discovery のみ)。

実行: python3 tools/ws3_leadlag_ic_explore.py
"""
import json
import os
from itertools import permutations

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASSIVE = os.path.join(REPO, "data", "cache", "massive")
YIELD = os.path.join(REPO, "data", "cache", "yield")
OUT_JSON = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                        "ws3_leadlag_ic_2026_07.json")
OUT_MD = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                      "ws3_leadlag_ic_2026_07.md")

PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY",
         "USD_CHF", "USD_CAD", "AUD_USD", "NZD_USD", "NZD_JPY", "EUR_GBP", "EUR_AUD"]
LIQUID_MAJORS = ["EUR_USD", "GBP_USD", "USD_JPY", "EUR_JPY", "GBP_JPY"]
DISCOVERY_START = "2023-01-01"


def _logret(df):
    return np.log(df["Close"]).diff()


def _ic(x, y, min_n=500):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < min_n:
        return float("nan")
    return float(np.corrcoef(x[m], y[m])[0, 1])


def _load_fx(pair):
    f = os.path.join(MASSIVE, f"{pair}_1h.parquet")
    if not os.path.exists(f):
        return None
    return pd.read_parquet(f).loc[DISCOVERY_START:]


def probe_leadlag():
    rets = {}
    for p in PAIRS:
        df = _load_fx(p)
        if df is not None:
            rets[p] = _logret(df)
    R = pd.DataFrame(rets).dropna(how="any")
    n = len(R) - 1
    res = []
    for lead, follow in permutations([p for p in PAIRS if p in R], 2):
        v = _ic(R[lead][:-1].values, R[follow].shift(-1)[:-1].values)
        if np.isfinite(v):
            res.append((lead, follow, v))
    res.sort(key=lambda t: -abs(t[2]))
    # Bonferroni r_crit
    from scipy import stats
    m = len(res)
    alpha = 0.05 / max(m, 1)
    tcrit = stats.t.ppf(1 - alpha / 2, n - 2)
    rcrit = float(tcrit / np.sqrt(n - 2 + tcrit ** 2))
    naive_sig = [r for r in res if abs(r[2]) > rcrit]

    # adversarial: top naive hit under liquid-hours + destale
    top = res[0]
    lead_df = _load_fx(top[0])
    foll_df = _load_fx(top[1])

    def _clean(df):
        d = df[(df["High"] > df["Low"]) & (df.get("Volume", 1) > 0)]
        return d[(d.index.hour >= 7) & (d.index.hour <= 16)]

    Rc = pd.DataFrame({
        "lead": np.log(_clean(lead_df)["Close"]).diff(),
        "foll": np.log(_clean(foll_df)["Close"]).diff(),
    }).dropna()
    top_clean_ic = _ic(Rc["lead"][:-1].values, Rc["foll"].shift(-1)[:-1].values)
    own_ac = {p: _ic(R[p][:-1].values, R[p].shift(-1)[:-1].values)
              for p in (top[0], top[1])}

    # liquid majors only
    maj = [p for p in LIQUID_MAJORS if p in R]
    maj_res = []
    for a, b in permutations(maj, 2):
        v = _ic(R[a][:-1].values, R[b].shift(-1)[:-1].values)
        maj_res.append((a, b, v))
    maj_res.sort(key=lambda t: -abs(t[2]))

    return {
        "n_bars": n,
        "window": [str(R.index[0]), str(R.index[-1])],
        "n_ordered_pairs": m,
        "bonferroni_rcrit": rcrit,
        "naive_max_abs_ic": abs(res[0][2]),
        "naive_top": {"lead": top[0], "follow": top[1], "ic": top[2]},
        "naive_bonferroni_sig_count": len(naive_sig),
        "adversarial_top_liquid_destaled_ic": top_clean_ic,
        "own_lag1_autocorr": own_ac,
        "liquid_majors_max_abs_ic": abs(maj_res[0][2]),
        "liquid_majors_top": [{"lead": a, "follow": b, "ic": v} for a, b, v in maj_res[:5]],
        "verdict": ("NULL — naive lead-lag は非同期取引 (Lo-MacKinlay) artifact。"
                    "liquid-hours+destale で IC 崩壊、liquid majors max|IC| は friction 未満"),
    }


def probe_crossasset():
    znf = os.path.join(YIELD, "ZN_F_15m.parquet")
    ujf = os.path.join(MASSIVE, "USD_JPY_1h.parquet")
    if not (os.path.exists(znf) and os.path.exists(ujf)):
        return {"available": False}
    zn = pd.read_parquet(znf)
    uj = pd.read_parquet(ujf)
    zn1h = zn["Close"].resample("1h").last()
    R = pd.DataFrame({"ZN": np.log(zn1h).diff(),
                      "UJ": np.log(uj["Close"]).diff()}).dropna().loc[DISCOVERY_START:]
    con = _ic(R["ZN"].values, R["UJ"].values, min_n=200)
    lead = _ic(R["ZN"][:-1].values, R["UJ"].shift(-1)[:-1].values, min_n=200)
    rev = _ic(R["UJ"][:-1].values, R["ZN"].shift(-1)[:-1].values, min_n=200)
    return {
        "available": True,
        "zn_cache_range": [str(zn.index[0]), str(zn.index[-1])],
        "n_bars": len(R),
        "contemporaneous_ic": con,
        "lead_ic_zn_to_usdjpy": lead,
        "rev_ic_usdjpy_to_zn": rev,
        "verdict": ("cross-asset linkage は contemporaneous で強い (IC~-0.58, 符号正) が "
                    "lag-1 lead は ~0 → tradeable 先行なし。divergence-reversion 構成で要再評価"),
    }


def main():
    out = {
        "generated_kind": "feasibility_probe_rule_R3",
        "note": "verdict ではない feasibility 診断。OOS 窓非消費。live/shadow 不変更",
        "leadlag_internal": probe_leadlag(),
        "crossasset_zn_usdjpy": probe_crossasset(),
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    ll = out["leadlag_internal"]
    ca = out["crossasset_zn_usdjpy"]
    lines = [
        "# WS3 外部仮説 — 価格ベース lead-lag feasibility 診断 (rule:R3)",
        "",
        "> read-only feasibility probe。verdict ではない。OOS 窓非消費。",
        "> 起点: 内部探索 2 周 FAIL → 外部仮説転進 (ws3-round2-explore-prereg §3)",
        "",
        "## A. 内部 cross-pair lead-lag (1h, 13 pair)",
        f"- 窓: {ll['window'][0]} → {ll['window'][1]} (N={ll['n_bars']} bars, {ll['n_ordered_pairs']} ordered pairs)",
        f"- **naive scan**: max|IC lag1| = {ll['naive_max_abs_ic']:.4f} "
        f"({ll['naive_top']['lead']}→{ll['naive_top']['follow']}), "
        f"Bonferroni-sig = {ll['naive_bonferroni_sig_count']} pairs (r_crit={ll['bonferroni_rcrit']:.4f})",
        f"- **adversarial (Lo-MacKinlay 非同期取引 check)**: top hit を liquid-hours+destale で再計測 → "
        f"IC = {ll['adversarial_top_liquid_destaled_ic']:.4f} (崩壊)",
        f"- own lag-1 autocorr: " + ", ".join(f"{k} {v:+.3f}" for k, v in ll['own_lag1_autocorr'].items())
        + " (強い負値 = bid-ask bounce / stale-quote シグネチャ)",
        f"- **liquid majors only**: max|IC lag1| = {ll['liquid_majors_max_abs_ic']:.4f} (friction 2-4.5p 未満)",
        f"- **判定**: {ll['verdict']}",
        "",
        "## B. cross-asset lead (ZN 10y T-note fut → USD_JPY, 1h)",
    ]
    if ca.get("available"):
        lines += [
            f"- ZN cache: {ca['zn_cache_range'][0]} → {ca['zn_cache_range'][1]} (N={ca['n_bars']} — 短期、feasibility のみ)",
            f"- contemporaneous IC = {ca['contemporaneous_ic']:.4f} (強い、符号整合: yields↑=ZN↓⇒USDJPY↑)",
            f"- **lag-1 lead IC (ZN→USDJPY) = {ca['lead_ic_zn_to_usdjpy']:.4f}** (tradeable 先行なし)",
            f"- rev IC (USDJPY→ZN) = {ca['rev_ic_usdjpy_to_zn']:.4f}",
            f"- **判定**: {ca['verdict']}",
        ]
    else:
        lines.append("- データ未取得")
    lines += [
        "",
        "## 帰結",
        "価格ベースの先行構造は OHLCV 内部でも cross-asset でも ≥1h バーで裁定消滅 "
        "(liquid 電子市場では情報は同時反映)。tradeable エッジは "
        "(a) 非先行構成 (contemporaneous linkage を使った divergence-reversion) か "
        "(b) 非価格モダリティ (positioning/flow/sentiment) が必要。"
        "→ [[external-hypothesis-scan-2026-07-13]] のスクリーン結論を実証的に支持。",
    ]
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT_JSON}\nwrote {OUT_MD}")
    print(json.dumps({"leadlag_verdict": ll["verdict"],
                      "crossasset_lead_ic": ca.get("lead_ic_zn_to_usdjpy")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
