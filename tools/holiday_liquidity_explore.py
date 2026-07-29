#!/usr/bin/env python3
"""holiday_liquidity_state_family 縮約版 explore — 凍結プロトコルの機械実装。

Frozen spec: knowledge-base/wiki/analyses/holiday-liquidity-explore-prereg-2026-07-29.md
- Leg (a): pre-holiday risk-tilt basket, eve-day O->C, two-sided.
- Leg (c): US-closure next-business-day reversal, dir = -sign(R_H), one-sided.
- Month-block sign-flip permutation (20,000, seed 20260729), family BH-FDR q=0.10 (m=2).
- Gates: BH pass / |mean| >= 5.0p / headroom median(MFE/RT) >= 10 / LOYO sign-stable.

Usage:
    python3 tools/holiday_liquidity_explore.py --stage explore
    python3 tools/holiday_liquidity_explore.py --stage oos   # only legs that PASSed explore

No module-top side effects (lesson: tools are both scripts and libraries).
"""

import json
import os
from datetime import date, timedelta

DATA_DIR = "/Users/jg-n-012/test/fx-ai-trader/data/cache/massive"
CALENDAR = "/Users/jg-n-012/test/fx-ai-trader/data/calendar/structural_events.parquet"
OUT_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge-base/raw/bt-results/holiday-liquidity-explore-2026-07-29.json",
)

SEED = 20260729
N_PERM = 20_000
BH_Q = 0.10
MIN_EFFECT_PIPS = 5.0
HEADROOM_MIN = 10.0

# NYSE full closures, hardcoded per holiday-calendar-verification-2026-07-29 §5.
# Special mourning closures (2018-12-05, 2025-01-09) intentionally NOT listed.
US_CLOSURES_EXPLORE = """
2014-01-01 2014-01-20 2014-02-17 2014-04-18 2014-05-26 2014-07-04 2014-09-01 2014-11-27 2014-12-25
2015-01-01 2015-01-19 2015-02-16 2015-04-03 2015-05-25 2015-07-03 2015-09-07 2015-11-26 2015-12-25
2016-01-01 2016-01-18 2016-02-15 2016-03-25 2016-05-30 2016-07-04 2016-09-05 2016-11-24 2016-12-26
2017-01-02 2017-01-16 2017-02-20 2017-04-14 2017-05-29 2017-07-04 2017-09-04 2017-11-23 2017-12-25
2018-01-01 2018-01-15 2018-02-19 2018-03-30 2018-05-28 2018-07-04 2018-09-03 2018-11-22 2018-12-25
2019-01-01 2019-01-21 2019-02-18 2019-04-19 2019-05-27 2019-07-04 2019-09-02 2019-11-28 2019-12-25
2020-01-01 2020-01-20 2020-02-17 2020-04-10 2020-05-25 2020-07-03 2020-09-07 2020-11-26 2020-12-25
""".split()
US_CLOSURES_OOS = """
2021-01-01 2021-01-18 2021-02-15 2021-04-02 2021-05-31 2021-07-05 2021-09-06 2021-11-25 2021-12-24
2022-01-17 2022-02-21 2022-04-15 2022-05-30 2022-06-20 2022-07-04 2022-09-05 2022-11-24 2022-12-26
2023-01-02 2023-01-16 2023-02-20 2023-04-07 2023-05-29 2023-06-19 2023-07-04 2023-09-04 2023-11-23 2023-12-25
2024-01-01 2024-01-15 2024-02-19 2024-03-29 2024-05-27 2024-06-19 2024-07-04 2024-09-02 2024-11-28 2024-12-25
2025-01-01 2025-01-20 2025-02-17 2025-04-18 2025-05-26 2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25
2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19
""".split()

PAIRS = {
    "USD_JPY": ("USD_JPY_1d_2014_2026.parquet", 0.01),
    "EUR_USD": ("EUR_USD_1d_2014_2026.parquet", 0.0001),
    "GBP_USD": ("GBP_USD_1d_2014_2026.parquet", 0.0001),
    "AUD_USD": ("AUD_USD_1d_2014_2026.parquet", 0.0001),
    "NZD_USD": ("NZD_USD_1d_2014_2026.parquet", 0.0001),
    "USD_CAD": ("USD_CAD_1d_2014_2026.parquet", 0.0001),
    "USD_CHF": ("USD_CHF_1d_2014_2026.parquet", 0.0001),
    "EUR_JPY": ("EUR_JPY_1d.parquet", 0.01),  # partial: starts 2016-04-18 (ex-ante noted)
}
JPY_PANEL = ["USD_JPY", "EUR_JPY"]  # leg (a) JP-eve panel

# Frozen basket signs: + = safer currency appreciates (JPY > CHF > USD > others)
BASKET_SIGN = {
    "USD_JPY": -1, "EUR_USD": -1, "GBP_USD": -1, "AUD_USD": -1,
    "NZD_USD": -1, "USD_CAD": +1, "USD_CHF": -1, "EUR_JPY": -1,
}
RT_FRICTION = {
    "USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53, "EUR_JPY": 2.50,
    "AUD_USD": 3.00, "NZD_USD": 3.50, "USD_CAD": 3.50, "USD_CHF": 3.50,
}
RT_FLOOR = 1.30  # sensitivity only

BACKFILL_WINDOWS = [(date(2019, 9, 14), date(2019, 10, 5)),
                    (date(2020, 10, 13), date(2020, 11, 14))]

EXPLORE = (date(2014, 1, 1), date(2020, 12, 31))
OOS_US = (date(2021, 1, 1), date(2026, 6, 30))
OOS_JP = (date(2021, 1, 1), date(2026, 4, 30))  # structural_events coverage bound


def _parse_dates(tokens):
    return sorted(date(*map(int, t.split("-"))) for t in tokens)


def load_jp_holidays():
    import pandas as pd
    se = pd.read_parquet(CALENDAR)
    days = se.loc[se["jp_holiday"], "date_utc"].dt.date
    return set(days)


def eve_of(h, holiday_set):
    d = h - timedelta(days=1)
    while d.weekday() >= 5 or d in holiday_set:
        d -= timedelta(days=1)
    return d


def next_bd(h, closure_set):
    d = h + timedelta(days=1)
    while d.weekday() >= 5 or d in closure_set:
        d += timedelta(days=1)
    return d


def load_bars():
    import pandas as pd
    bars = {}
    for pair, (fname, pip) in PAIRS.items():
        df = pd.read_parquet(os.path.join(DATA_DIR, fname))
        df = df[["Open", "High", "Low", "Close"]].copy()
        df.index = df.index.date
        bars[pair] = df
    return bars


def in_backfill(d):
    return any(a <= d <= b for a, b in BACKFILL_WINDOWS)


def build_leg_a_events(stage, jp_holidays):
    """Returns list of (eve_date, holiday_year, population) after overlap exclusion."""
    us_all = _parse_dates(US_CLOSURES_EXPLORE if stage == "explore" else US_CLOSURES_OOS)
    us_set = set(us_all)
    win_us = EXPLORE if stage == "explore" else OOS_US
    win_jp = EXPLORE if stage == "explore" else OOS_JP

    us_events = {}  # eve -> holiday year
    for h in us_all:
        if win_us[0] <= h <= win_us[1]:
            us_events.setdefault(eve_of(h, us_set), h.year)

    jp_weekday_hols = sorted(h for h in jp_holidays
                             if h.weekday() < 5 and win_jp[0] <= h <= win_jp[1])
    jp_events = {}
    for h in jp_weekday_hols:
        jp_events.setdefault(eve_of(h, jp_holidays), h.year)

    overlap = sorted(set(us_events) & set(jp_events))
    for d in overlap:
        us_events.pop(d)
        jp_events.pop(d)
    ev = [(d, y, "US") for d, y in us_events.items()] + \
         [(d, y, "JP") for d, y in jp_events.items()]
    return sorted(ev), overlap


def build_leg_c_events(stage):
    us_all = _parse_dates(US_CLOSURES_EXPLORE if stage == "explore" else US_CLOSURES_OOS)
    us_set = set(us_all)
    win = EXPLORE if stage == "explore" else OOS_US
    return [(h, next_bd(h, us_set)) for h in us_all if win[0] <= h <= win[1]]


def leg_a_panel(stage, bars, jp_holidays):
    events, overlap = build_leg_a_events(stage, jp_holidays)
    pos = {pair: {d: i for i, d in enumerate(bars[pair].index)} for pair in PAIRS}
    rows = []
    for eve, hyear, pop in events:
        panel = list(PAIRS) if pop == "US" else JPY_PANEL
        for pair in panel:
            df = bars[pair]
            if eve not in df.index:
                continue
            b = df.loc[eve]
            i = pos[pair][eve]
            c48 = df.iloc[i + 1].Close if i + 1 < len(df) else b.Close
            pip = PAIRS[pair][1]
            s = BASKET_SIGN[pair]
            rows.append({
                "day": eve, "year": hyear, "pop": pop, "pair": pair,
                "signed": s * (b.Close - b.Open) / pip,
                "signed_48h": s * (c48 - b.Open) / pip,
                "raw": (b.Close - b.Open) / pip,
                "mfe_up": (b.High - b.Open) / pip,
                "mfe_dn": (b.Open - b.Low) / pip,
                "range": (b.High - b.Low) / pip,
                "backfill": in_backfill(eve),
                "halfday": (eve.month == 12 and eve.day == 24),
            })
    return rows, len(events), overlap


def leg_c_panel(stage, bars):
    events = build_leg_c_events(stage)
    pos = {pair: {d: i for i, d in enumerate(bars[pair].index)} for pair in PAIRS}
    rows = []
    for h, d1 in events:
        for pair in PAIRS:
            df = bars[pair]
            if h not in df.index or d1 not in df.index:
                continue
            bh, b1 = df.loc[h], df.loc[d1]
            i1 = pos[pair][d1]
            c48 = df.iloc[i1 + 1].Close if i1 + 1 < len(df) else b1.Close
            pip = PAIRS[pair][1]
            rh = (bh.Close - bh.Open) / pip
            if rh == 0:
                continue
            dirn = -1.0 if rh > 0 else 1.0
            rows.append({
                "day": h, "year": h.year, "pair": pair, "d1": d1,
                "r_h": rh, "dir": dirn,
                "signed": dirn * (b1.Close - b1.Open) / pip,
                "signed_48h": dirn * (c48 - b1.Open) / pip,
                "mfe": ((b1.High - b1.Open) if dirn > 0 else (b1.Open - b1.Low)) / pip,
                "weekend_gap": (d1 - h).days > 1,
                "backfill": in_backfill(h) or in_backfill(d1),
                "halfday_d1": (d1.month == 11 and d1.weekday() == 4 and 23 <= d1.day <= 29),
                "cross_month": (h.year, h.month) != (d1.year, d1.month),
            })
    return rows, len(events)


def perm_pvalue(values, blocks, rng, two_sided):
    """Month-block sign-flip permutation on pooled mean."""
    import numpy as np
    v = np.asarray(values, dtype=float)
    bl = np.asarray(blocks)
    uniq, inv = np.unique(bl, return_inverse=True)
    obs = v.mean()
    flips = rng.choice([-1.0, 1.0], size=(N_PERM, len(uniq)))
    perm_means = (flips[:, inv] * v).mean(axis=1)
    if two_sided:
        cnt = int((np.abs(perm_means) >= abs(obs)).sum())
    else:
        cnt = int((perm_means >= obs).sum())
    return obs, (1 + cnt) / (N_PERM + 1)


def loyo_signs(rows):
    import numpy as np
    years = sorted({r["year"] for r in rows})
    full = float(np.mean([r["signed"] for r in rows]))
    out = {}
    for y in years:
        sub = [r["signed"] for r in rows if r["year"] != y]
        out[str(y)] = float(np.mean(sub))
    stable = all((m > 0) == (full > 0) for m in out.values())
    return full, out, stable


def headroom(rows, mfe_key, rt_map):
    import numpy as np
    ratios = [r[mfe_key] / rt_map[r["pair"]] for r in rows]
    return float(np.median(ratios))


def analyze_leg(name, rows, rng, two_sided, fixed_dir=None):
    """fixed_dir: OOS only — leg (a) direction frozen to the explore sign (+1/-1).
    When set, signed values are pre-flipped so the frozen direction tests as mean>0
    (one-sided), and the MFE side follows the frozen direction, not the OOS sign."""
    import numpy as np
    if fixed_dir is not None:
        rows = [dict(r, signed=fixed_dir * r["signed"]) for r in rows]
    blocks = [r["day"].year * 100 + r["day"].month for r in rows]
    signed = [r["signed"] for r in rows]
    obs, p = perm_pvalue(signed, blocks, rng, two_sided)

    if name == "a":
        # favorable excursion follows the effective basket direction (frozen rule)
        eff_dir = fixed_dir if fixed_dir is not None else (1.0 if obs >= 0 else -1.0)
        for r in rows:
            price_dir = eff_dir * BASKET_SIGN[r["pair"]]
            r["mfe"] = r["mfe_up"] if price_dir > 0 else r["mfe_dn"]
    hr = headroom(rows, "mfe", RT_FRICTION)
    hr_floor = headroom(rows, "mfe", {k: RT_FLOOR for k in RT_FRICTION})
    full, loyo, loyo_ok = loyo_signs(rows)

    res = {
        "n_obs": len(rows),
        "n_blocks": len({b for b in blocks}),
        "pooled_mean_pips": round(obs, 4),
        "perm_p": p if p >= 1e-4 else "<1e-4",
        "perm_p_raw": p,
        "two_sided": two_sided,
        "gate_min_effect": abs(obs) >= MIN_EFFECT_PIPS,
        "headroom_median": round(hr, 2),
        "gate_headroom": hr >= HEADROOM_MIN,
        "headroom_median_floor_rt": round(hr_floor, 2),
        "loyo_means": {k: round(v, 3) for k, v in loyo.items()},
        "gate_loyo": loyo_ok,
    }
    return res


def diagnostics(rows_a, rows_c, bars):
    import numpy as np
    d = {}
    for pop in ("US", "JP"):
        sub = [r["signed"] for r in rows_a if r["pop"] == pop]
        d[f"leg_a_mean_{pop}"] = round(float(np.mean(sub)), 3) if sub else None
        d[f"leg_a_n_{pop}"] = len(sub)
    d["leg_a_per_pair"] = {p: round(float(np.mean([r["signed"] for r in rows_a if r["pair"] == p])), 3)
                           for p in PAIRS if any(r["pair"] == p for r in rows_a)}
    d["leg_a_raw_quote_mean"] = round(float(np.mean([r["raw"] for r in rows_a])), 3)
    # eve-day range vs all-weekday baseline (pooled ratio of medians, per pair then median)
    ratios = []
    for pair in PAIRS:
        df = bars[pair]
        pip = PAIRS[pair][1]
        base = float(np.median((df.High - df.Low) / pip))
        ev = [r["range"] for r in rows_a if r["pair"] == pair]
        if ev:
            ratios.append(float(np.median(ev)) / base)
    d["leg_a_range_ratio_median"] = round(float(np.median(ratios)), 3)
    d["leg_c_abs_rh_median"] = round(float(np.median([abs(r["r_h"]) for r in rows_c])), 2)
    d["leg_c_small_rh_share_lt5p"] = round(float(np.mean([abs(r["r_h"]) < 5 for r in rows_c])), 3)
    for key, rows in (("a", rows_a), ("c", rows_c)):
        nobf = [r["signed"] for r in rows if not r["backfill"]]
        d[f"leg_{key}_mean_ex_backfill"] = round(float(np.mean(nobf)), 3)
        d[f"leg_{key}_n_ex_backfill"] = len(nobf)
    gf = [r["signed"] for r in rows_c if r["weekend_gap"]]
    ngf = [r["signed"] for r in rows_c if not r["weekend_gap"]]
    d["leg_c_weekend_gap_mean"] = round(float(np.mean(gf)), 3) if gf else None
    d["leg_c_no_gap_mean"] = round(float(np.mean(ngf)), 3) if ngf else None
    hd = [r["signed"] for r in rows_c if r["halfday_d1"]]
    d["leg_c_halfday_d1_mean"] = round(float(np.mean(hd)), 3) if hd else None
    d["leg_c_halfday_d1_n"] = len(hd)
    d["leg_a_mean_48h"] = round(float(np.mean([r["signed_48h"] for r in rows_a])), 3)
    d["leg_c_mean_48h"] = round(float(np.mean([r["signed_48h"] for r in rows_c])), 3)
    return d


def bh_verdicts(pvals):
    """BH step-up over {leg: p}, q=0.10, m = number of legs tested this stage."""
    m = len(pvals)
    labeled = sorted(pvals.items(), key=lambda x: x[1])
    k = 0
    for i, (_, p) in enumerate(labeled, start=1):
        if p <= i / m * BH_Q:
            k = i
    return {leg for i, (leg, _) in enumerate(labeled, start=1) if i <= k}


def main():
    import argparse
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["explore", "oos"], default="explore")
    args = ap.parse_args()

    bars = load_bars()
    jp_holidays = load_jp_holidays()
    rng = np.random.default_rng(SEED)

    allowed = ["a", "c"]
    fixed_dir_a = None
    if args.stage == "oos":
        # OOS single touch: only legs that PASSed explore are even built/measured.
        with open(OUT_JSON) as f:
            prior = json.load(f)
        expl = prior["explore"]
        allowed = [leg for leg in ("a", "c") if expl[f"leg_{leg}"]["verdict"] == "PASS"]
        if not allowed:
            raise SystemExit("No leg passed explore — OOS must remain untouched.")
        if "a" in allowed:
            fixed_dir_a = 1.0 if expl["leg_a"]["pooled_mean_pips"] >= 0 else -1.0

    results, counts = {}, {}
    rows_a = rows_c = None
    if "a" in allowed:
        rows_a, n_ev_a, overlap = leg_a_panel(args.stage, bars, jp_holidays)
        counts["leg_a_events"] = n_ev_a
        counts["leg_a_overlap_excluded"] = [str(d) for d in overlap]
        results["leg_a"] = analyze_leg(
            "a", rows_a, rng,
            two_sided=(args.stage == "explore"), fixed_dir=fixed_dir_a)
    if "c" in allowed:
        rows_c, n_ev_c = leg_c_panel(args.stage, bars)
        counts["leg_c_events"] = n_ev_c
        results["leg_c"] = analyze_leg("c", rows_c, rng, two_sided=False)

    passed_bh = bh_verdicts({leg: results[f"leg_{leg}"]["perm_p_raw"] for leg in allowed})
    for leg in allowed:
        res = results[f"leg_{leg}"]
        res["gate_bh"] = leg in passed_bh
        gates = [res["gate_bh"], res["gate_min_effect"], res["gate_headroom"], res["gate_loyo"]]
        res["verdict"] = "PASS" if all(gates) else "FAIL"

    out = {
        "stage": args.stage,
        "frozen_doc": "knowledge-base/wiki/analyses/holiday-liquidity-explore-prereg-2026-07-29.md",
        "seed": SEED, "n_perm": N_PERM, "bh_q": BH_Q, "m": len(allowed),
        "legs_tested": allowed,
        "counts": counts,
        **results,
    }
    if rows_a is not None and rows_c is not None:
        out["diagnostics"] = diagnostics(rows_a, rows_c, bars)

    if os.path.exists(OUT_JSON):
        with open(OUT_JSON) as f:
            blob = json.load(f)
    else:
        blob = {}
    blob[args.stage] = out
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(blob, f, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
