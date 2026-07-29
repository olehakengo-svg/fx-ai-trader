#!/usr/bin/env python3
"""cot_commercial_flow_weekly (W3-1, 台帳 #16) — 凍結プロトコルの機械実装。

Frozen spec: knowledge-base/wiki/analyses/cot-commercial-flow-explore-prereg-2026-07-29.md
- Signal: flow = comm_net_pct_oi.diff(4 reports), single design point.
- Primary: pooled Spearman IC(flow, fwd 10bd FC-return), two-sided, alpha=0.05, m=1.
- Null: 26-week moving-block, whole cross-section rows, signal/return blocks
  resampled independently (10,000, seed 20260729).
- Gates: (i) p<0.05 (ii) quintile monotonicity (iii) LOYO + single-year share<=50%
  + SNB-window exclusion (iv) side-split same sign (v) headroom>=10x net-of-swap
  (vi) level-neutralized IC retains >=50% same-sign.

Usage:
    python3 tools/cot_commercial_flow_explore.py --stage explore
    python3 tools/cot_commercial_flow_explore.py --stage oos   # only if explore PASSed

No module-top side effects.
"""

import json
import os
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data/external/cot_fx_panel.parquet")
RATES = os.path.join(ROOT, "knowledge-base/raw/bt-results/e20/e20_carry_level.csv")
BARS_DIR = "/Users/jg-n-012/test/fx-ai-trader/data/cache/massive"
OUT_JSON = os.path.join(ROOT, "knowledge-base/raw/bt-results/cot-commercial-flow-explore-2026-07-29.json")

SEED = 20260729
N_BOOT = 10_000
ALPHA = 0.05
BLOCK_WEEKS = 26
FLOW_LAG = 4          # 4 reports = 4w delta window (frozen single design point)
HORIZON_BD = 10       # 2w primary; 5/20bd diagnostics only
HEADROOM_MIN = 10.0
LEVEL_NEUTRAL_MIN = 0.5

# ccy -> (spot pair, FC-direction multiplier on raw pips, pip size, RT friction)
CCY_MAP = {
    "EUR": ("EUR_USD", +1, 0.0001, 2.00),
    "GBP": ("GBP_USD", +1, 0.0001, 4.53),
    "AUD": ("AUD_USD", +1, 0.0001, 3.00),
    "JPY": ("USD_JPY", -1, 0.01, 2.14),
    "CAD": ("USD_CAD", -1, 0.0001, 3.50),
    "CHF": ("USD_CHF", -1, 0.0001, 3.50),
}
# e20_carry_level.csv columns are (base - quote); rd_fc = FC - US
RD_FC_SIGN = {"EUR_USD": +1, "GBP_USD": +1, "AUD_USD": +1,
              "USD_JPY": -1, "USD_CAD": -1, "USD_CHF": -1}
RT_FLOOR = 1.30

EXPLORE = (date(2014, 1, 1), date(2021, 12, 31))
OOS = (date(2022, 1, 1), date(2026, 6, 30))
SNB_WINDOW = (date(2015, 1, 1), date(2015, 1, 31))


def spearman(x, y):
    from scipy import stats
    return float(stats.spearmanr(x, y).statistic)


def load_bars():
    import pandas as pd
    bars = {}
    for ccy, (pair, sign, pip, rt) in CCY_MAP.items():
        df = pd.read_parquet(os.path.join(BARS_DIR, f"{pair}_1d_2014_2026.parquet"))
        keep = [d.weekday() < 5 for d in df.index.date]  # frozen QA: drop Sat/Sun rows
        df = df.loc[keep]
        bars[ccy] = (list(df.index.date), df["Open"].to_numpy())
    return bars


def load_rates():
    import pandas as pd
    df = pd.read_csv(RATES, parse_dates=["date"]).set_index("date").sort_index()
    return df


def build_obs(stage):
    """Long panel of (report_date, ccy, flow, level, dnoncomm, rets, swap, rt)."""
    import numpy as np
    import pandas as pd
    panel = pd.read_parquet(PANEL).sort_values(["currency", "report_date"])
    g = panel.groupby("currency")
    panel["flow"] = g["comm_net_pct_oi"].diff(FLOW_LAG)
    panel["dnoncomm"] = g["net_pct_oi"].diff(FLOW_LAG)
    panel["nonrep_share"] = (panel["comm_net"] + panel["noncomm_net"]).abs() / panel["open_interest"]

    win = EXPLORE if stage == "explore" else OOS
    panel = panel[(panel["report_date"].dt.date >= win[0])
                  & (panel["report_date"].dt.date <= win[1])]

    bars = load_bars()
    rates = load_rates()
    rates_max = rates.index.max().date()

    rows, skips = [], {"entry_guard": 0, "no_exit_bar": 0, "nan_flow": 0}
    for r in panel.itertuples():
        if r.flow != r.flow:  # NaN
            skips["nan_flow"] += 1
            continue
        ccy = r.currency
        pair, sign, pip, rt = CCY_MAP[ccy]
        rep = r.report_date.date()
        publish = np.busday_offset(rep, 3, roll="forward").astype("datetime64[D]").astype(object)
        dates, opens = bars[ccy]
        # first bar strictly after publish
        import bisect
        i = bisect.bisect_right(dates, publish)
        if i >= len(dates):
            skips["no_exit_bar"] += 1
            continue
        entry = dates[i]
        if not (6 <= (entry - rep).days <= 10):
            skips["entry_guard"] += 1
            continue
        assert entry > publish and (entry - rep).days >= 6  # frozen lookahead asserts
        if i + max(HORIZON_BD, 20) >= len(dates):
            skips["no_exit_bar"] += 1
            continue
        p0 = opens[i]
        ret10 = sign * (opens[i + HORIZON_BD] - p0) / pip
        ret5 = sign * (opens[i + 5] - p0) / pip
        ret20 = sign * (opens[i + 20] - p0) / pip
        # swap for long-FC over 10bd, pips
        ts = pd.Timestamp(entry)
        idx = rates.index.searchsorted(ts, side="right") - 1
        rate_row = rates.iloc[max(idx, 0)]
        rd_fc = RD_FC_SIGN[pair] * float(rate_row[pair])
        swap_long = (rd_fc / 100.0) * (HORIZON_BD / 252.0) * p0 / pip
        rows.append({
            "report": rep, "year": rep.year, "ccy": ccy,
            "flow": float(r.flow), "level": float(r.net_pct_oi),
            "dnoncomm": float(r.dnoncomm) if r.dnoncomm == r.dnoncomm else None,
            "ret": float(ret10), "ret5": float(ret5), "ret20": float(ret20),
            "swap_long": float(swap_long), "rt": rt,
            "rates_ffilled_beyond": entry > rates_max,
        })
    return rows, skips


def moving_block_null_p(rows, n_boot, seed, one_sided_sign=None):
    """26-week moving-block, whole cross-section rows; signal and return block
    sequences resampled independently to build the null IC distribution."""
    import numpy as np
    weeks = sorted({r["report"] for r in rows})
    widx = {w: i for i, w in enumerate(weeks)}
    ccys = sorted(CCY_MAP)
    cidx = {c: i for i, c in enumerate(ccys)}
    nw, nc = len(weeks), len(ccys)
    Z = np.full((nw, nc), np.nan)
    R = np.full((nw, nc), np.nan)
    for r in rows:
        Z[widx[r["report"]], cidx[r["ccy"]]] = r["flow"]
        R[widx[r["report"]], cidx[r["ccy"]]] = r["ret"]

    def pooled_ic(zm, rm):
        m = ~(np.isnan(zm) | np.isnan(rm))
        return spearman(zm[m], rm[m])

    ic_obs = pooled_ic(Z.ravel(), R.ravel())
    rng = np.random.default_rng(seed)
    L = BLOCK_WEEKS
    n_blocks_needed = int(np.ceil(nw / L))
    max_start = nw - L
    null = np.empty(n_boot)
    for b in range(n_boot):
        zs = rng.integers(0, max_start + 1, n_blocks_needed)
        rs = rng.integers(0, max_start + 1, n_blocks_needed)
        zrows = np.concatenate([np.arange(s, s + L) for s in zs])[:nw]
        rrows = np.concatenate([np.arange(s, s + L) for s in rs])[:nw]
        null[b] = pooled_ic(Z[zrows].ravel(), R[rrows].ravel())
    if one_sided_sign is None:
        p = (1 + int(np.count_nonzero(np.abs(null) >= abs(ic_obs)))) / (n_boot + 1)
    else:
        s = one_sided_sign
        p = (1 + int(np.count_nonzero(null * s >= ic_obs * s))) / (n_boot + 1)
    return ic_obs, float(p)


def quintile_gate(rows, ic_sign):
    import numpy as np
    flows = np.array([r["flow"] for r in rows])
    rets = np.array([r["ret"] for r in rows])
    qs = np.quantile(flows, [0.2, 0.4, 0.6, 0.8])
    bins = np.digitize(flows, qs)
    means = [float(rets[bins == k].mean()) for k in range(5)]
    ordered = means if ic_sign > 0 else means[::-1]
    violations = sum(1 for a, b in zip(ordered, ordered[1:]) if b < a)
    spread_ok = (means[4] - means[0]) * ic_sign > 0
    return {"quintile_means": [round(m, 3) for m in means],
            "adjacent_violations": violations,
            "spread_sign_ok": bool(spread_ok),
            "pass": bool(violations <= 1 and spread_ok)}


def loyo_gate(rows, ic_sign):
    import numpy as np
    years = sorted({r["year"] for r in rows})
    out, mass_terms = {}, {}
    for y in years:
        sub = [r for r in rows if r["year"] != y]
        out[str(y)] = round(spearman([r["flow"] for r in sub], [r["ret"] for r in sub]), 4)
        yr = [r for r in rows if r["year"] == y]
        ic_y = spearman([r["flow"] for r in yr], [r["ret"] for r in yr]) if len(yr) > 10 else 0.0
        mass_terms[y] = len(yr) * max(ic_y * ic_sign, 0.0)
    sign_stable = all((v > 0) == (ic_sign > 0) for v in out.values())
    total_mass = sum(mass_terms.values())
    max_share = max(mass_terms.values()) / total_mass if total_mass > 0 else 1.0
    sub_snb = [r for r in rows if not (SNB_WINDOW[0] <= r["report"] <= SNB_WINDOW[1])]
    ic_snb = spearman([r["flow"] for r in sub_snb], [r["ret"] for r in sub_snb])
    snb_ok = (ic_snb > 0) == (ic_sign > 0)
    return {"loyo_ics": out, "sign_stable": bool(sign_stable),
            "max_year_share": round(max_share, 3), "ic_ex_snb": round(ic_snb, 4),
            "pass": bool(sign_stable and max_share <= 0.5 and snb_ok)}


def side_split_gate(rows, ic_sign):
    pos = [r for r in rows if r["flow"] > 0]
    neg = [r for r in rows if r["flow"] < 0]
    ic_pos = spearman([r["flow"] for r in pos], [r["ret"] for r in pos])
    ic_neg = spearman([r["flow"] for r in neg], [r["ret"] for r in neg])
    ok = ((ic_pos > 0) == (ic_sign > 0)) and ((ic_neg > 0) == (ic_sign > 0))
    return {"ic_flow_pos": round(ic_pos, 4), "ic_flow_neg": round(ic_neg, 4), "pass": bool(ok)}


def headroom_gate(rows, ic_sign, rt_floor=False):
    import numpy as np
    flows = np.array([r["flow"] for r in rows])
    qs = np.quantile(flows, [0.2, 0.8])
    ratios = []
    for r in rows:
        if r["flow"] >= qs[1]:
            dirn = ic_sign
        elif r["flow"] <= qs[0]:
            dirn = -ic_sign
        else:
            continue
        net = dirn * r["ret"] + (r["swap_long"] if dirn > 0 else -r["swap_long"])
        rt = RT_FLOOR if rt_floor else r["rt"]
        ratios.append(abs(net) / rt)
    med = float(np.median(ratios))
    return {"headroom_median": round(med, 2), "n_extreme": len(ratios),
            "pass": bool(med >= HEADROOM_MIN)}


def level_neutral_gate(rows, ic_obs):
    import numpy as np
    resid = []
    for ccy in sorted(CCY_MAP):
        sub = [r for r in rows if r["ccy"] == ccy]
        f = np.array([r["flow"] for r in sub])
        lv = np.array([r["level"] for r in sub])
        b = np.polyfit(lv, f, 1)
        e = f - np.polyval(b, lv)
        for r, ei in zip(sub, e):
            resid.append((ei, r["ret"]))
    ic_res = spearman([x for x, _ in resid], [y for _, y in resid])
    ok = ((ic_res > 0) == (ic_obs > 0)) and abs(ic_res) >= LEVEL_NEUTRAL_MIN * abs(ic_obs)
    return {"ic_level_neutral": round(ic_res, 4),
            "retention": round(abs(ic_res) / abs(ic_obs), 3) if ic_obs else None,
            "pass": bool(ok)}


def diagnostics(rows):
    import numpy as np
    d = {}
    for ccy in sorted(CCY_MAP):
        sub = [r for r in rows if r["ccy"] == ccy]
        d[f"ic_{ccy}"] = round(spearman([r["flow"] for r in sub], [r["ret"] for r in sub]), 4)
    for y in sorted({r["year"] for r in rows}):
        sub = [r for r in rows if r["year"] == y]
        d[f"ic_year_{y}"] = round(spearman([r["flow"] for r in sub], [r["ret"] for r in sub]), 4)
    d["ic_5bd"] = round(spearman([r["flow"] for r in rows], [r["ret5"] for r in rows]), 4)
    d["ic_20bd"] = round(spearman([r["flow"] for r in rows], [r["ret20"] for r in rows]), 4)
    mir = [(r["flow"], -r["dnoncomm"]) for r in rows if r["dnoncomm"] is not None]
    d["corr_dcomm_vs_neg_dnoncomm"] = round(float(np.corrcoef(
        [a for a, _ in mir], [b for _, b in mir])[0, 1]), 4)
    d["rates_ffilled_beyond_n"] = sum(1 for r in rows if r["rates_ffilled_beyond"])
    return d


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["explore", "oos"], default="explore")
    args = ap.parse_args()

    one_sided = None
    if args.stage == "oos":
        with open(OUT_JSON) as f:
            prior = json.load(f)
        expl = prior["explore"]
        if expl["verdict"] != "PASS":
            raise SystemExit("Explore did not PASS — OOS must remain untouched.")
        one_sided = 1 if expl["ic"] > 0 else -1

    rows, skips = build_obs(args.stage)
    ic, p = moving_block_null_p(rows, N_BOOT, SEED, one_sided_sign=one_sided)
    sign = 1 if ic > 0 else -1
    if args.stage == "oos":
        sign = one_sided  # direction frozen from explore

    g2 = quintile_gate(rows, sign)
    g3 = loyo_gate(rows, sign)
    g4 = side_split_gate(rows, sign)
    g5 = headroom_gate(rows, sign)
    g5f = headroom_gate(rows, sign, rt_floor=True)
    g6 = level_neutral_gate(rows, ic)

    gates = {"i_pvalue": bool(p < ALPHA), "ii_quintile": g2["pass"], "iii_loyo": g3["pass"],
             "iv_side_split": g4["pass"], "v_headroom": g5["pass"], "vi_level_neutral": g6["pass"]}
    verdict = "PASS" if all(gates.values()) else "FAIL"

    out = {
        "stage": args.stage,
        "frozen_doc": "knowledge-base/wiki/analyses/cot-commercial-flow-explore-prereg-2026-07-29.md",
        "seed": SEED, "n_boot": N_BOOT, "alpha": ALPHA, "m": 1,
        "n_obs": len(rows), "n_weeks": len({r["report"] for r in rows}),
        "skips": skips,
        "ic": round(ic, 4), "p": p if p >= 1e-4 else "<1e-4", "p_raw": p,
        "one_sided_sign": one_sided,
        "gates": gates,
        "gate_detail": {"quintile": g2, "loyo": g3, "side_split": g4,
                        "headroom": g5, "headroom_floor_rt": g5f, "level_neutral": g6},
        "verdict": verdict,
        "diagnostics": diagnostics(rows),
    }

    blob = {}
    if os.path.exists(OUT_JSON):
        with open(OUT_JSON) as f:
            blob = json.load(f)
    blob[args.stage] = out
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(blob, f, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
