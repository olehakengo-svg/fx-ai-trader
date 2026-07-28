"""gotobi_tokyo_fix_usdjpy frozen explore — calibration-primary + single tail cell.

Protocol (frozen BEFORE observation):
  knowledge-base/wiki/analyses/gotobi-calibration-explore-prereg-2026-07-28.md

Legs (all exit-free, USD_JPY, explore 2014-01-01..2021-12-31):
  C1 (calibration, m=0): fix-window drift 00:00 UTC open -> 00:55 UTC close,
      gotobi(Conv A) vs non-gotobi JP business days, month-block permutation.
  C2 (calibration, m=0): post-fix 00:55 -> 06:00 UTC close, same contrast.
  P1 (promotion tail cell, m=1): last JP business day of month, D1
      00:00 open -> 21:00 UTC close, one-sided (+), vs non-gotobi days.
      Kill: drift < 13.0p or p >= 0.05 -> family close, no OOS touch.

Data: FULL parquet from the main checkout (worktree copies are partial).
No module-level side effects (tools/*.py dual script/library rule).
"""

import argparse
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SEED = 20260728
N_PERM = 10000
PIP = 0.01
EXPLORE_START = date(2014, 1, 1)
EXPLORE_END = date(2021, 12, 31)  # inclusive


def load_calendar(cal_path):
    """Return (dict date -> jp_business_day(bool), set of month_end_jp dates)."""
    import pandas as pd
    df = pd.read_parquet(cal_path)
    cols = {c.lower(): c for c in df.columns}
    dcol = next(cols[k] for k in ("date_utc", "date", "day", "session_date") if k in cols)
    out, me = {}, set()
    for _, r in df.iterrows():
        d = pd.Timestamp(r[dcol]).date()
        out[d] = bool(r[cols["jp_business_day"]])
        if bool(r[cols["month_end_jp"]]):
            me.add(d)
    return out, me


def gotobi_calendar_days(y, m):
    """Calendar gotobi days for a month: 5,10,15,20,25,30 (Feb: last day)."""
    days = [5, 10, 15, 20, 25]
    if m == 2:
        last = (date(y, 3, 1) - timedelta(days=1)).day
        days.append(last)
    else:
        days.append(30)
    return [date(y, m, d) for d in days]


def roll(d, jp_bday, direction, limit=10):
    for i in range(limit + 1):
        cand = d + timedelta(days=direction * i)
        if jp_bday.get(cand, False):
            return cand
    return None


def classify_days(jp_bday, d0, d1):
    """Return (gotobi_A, gotobi_B, eom) sets of dates within [d0, d1]."""
    got_a, got_b, eom = set(), set(), set()
    y, m = d0.year, d0.month
    while (y, m) <= (d1.year, d1.month):
        for g in gotobi_calendar_days(y, m):
            a = roll(g, jp_bday, +1)
            b = roll(g, jp_bday, -1)
            if a and d0 <= a <= d1:
                got_a.add(a)
            if b and d0 <= b <= d1:
                got_b.add(b)
        # last JP business day of month
        last_cal = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1))
        e = roll(last_cal, jp_bday, -1)
        if e and d0 <= e <= d1:
            eom.add(e)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return got_a, got_b, eom


def day_metrics(df5):
    """Per calendar-date UTC metrics from 5m bars.

    Returns dict date -> {fix, postfix, d1} in pips (None if bars missing).
    """
    import pandas as pd
    idx = df5.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
        df5 = df5.set_axis(idx)
    out = {}
    for d, g in df5.groupby(idx.date):
        bars = {ts.strftime("%H:%M"): (o, c) for ts, o, c in
                zip(g.index, g["Open"] if "Open" in g else g["open"],
                    g["Close"] if "Close" in g else g["close"])}
        # bars are period-start labeled: bar "00:50" closes at 00:55 (= fix time),
        # bar "05:55" closes at 06:00, bar "20:55" closes at 21:00.
        o0 = bars.get("00:00")
        cfix = bars.get("00:50")
        c0600 = bars.get("05:55")
        c2100 = bars.get("20:55")
        rec = {}
        rec["fix"] = (cfix[1] - o0[0]) / PIP if (o0 and cfix) else None
        rec["postfix"] = (c0600[1] - cfix[1]) / PIP if (cfix and c0600) else None
        rec["d1"] = (c2100[1] - o0[0]) / PIP if (o0 and c2100) else None
        out[d] = rec
    return out


def mean(xs):
    return sum(xs) / len(xs)


def month_block_perm(day_vals, labels, rng, one_sided=False, n_perm=N_PERM):
    """day_vals: list[(date, value)], labels: set of 'treatment' dates.

    Diff-in-means treatment - control, permuting labels within month blocks.
    """
    obs_t = [v for d, v in day_vals if d in labels]
    obs_c = [v for d, v in day_vals if d not in labels]
    obs = mean(obs_t) - mean(obs_c)
    by_month = defaultdict(list)
    for d, v in day_vals:
        by_month[(d.year, d.month)].append((d, v))
    hits = 0
    for _ in range(n_perm):
        t_vals, c_vals = [], []
        for mo, rows in by_month.items():
            k = sum(1 for d, _ in rows if d in labels)
            vals = [v for _, v in rows]
            rng.shuffle(vals)
            t_vals.extend(vals[:k])
            c_vals.extend(vals[k:])
        stat = mean(t_vals) - mean(c_vals) if t_vals and c_vals else 0.0
        if one_sided:
            if stat >= obs:
                hits += 1
        else:
            if abs(stat) >= abs(obs):
                hits += 1
    return obs, (hits + 1) / (n_perm + 1), len(obs_t), len(obs_c)


def run(data_root, cal_path, out_json):
    import pandas as pd
    df5 = pd.read_parquet(Path(data_root) / "USD_JPY_5m_2014_2026.parquet")
    jp_bday, cal_me = load_calendar(cal_path)
    got_a, got_b, eom = classify_days(jp_bday, EXPLORE_START, EXPLORE_END)
    # cross-check derived EOM vs calendar month_end_jp column
    cal_me_win = {d for d in cal_me if EXPLORE_START <= d <= EXPLORE_END}
    eom_mismatch = sorted(eom.symmetric_difference(cal_me_win))
    metrics = day_metrics(df5)

    days = [d for d in sorted(metrics) if EXPLORE_START <= d <= EXPLORE_END
            and jp_bday.get(d, False)]
    non_gotobi = [d for d in days if d not in got_a]

    rng = random.Random(SEED)
    res = {"seed": SEED, "n_perm": N_PERM,
           "counts": {"jp_bdays_with_fx": len(days), "gotobi_A": len(got_a & set(days)),
                      "gotobi_B": len(got_b & set(days)), "eom": len(eom & set(days)),
                      "eom_calendar_mismatch": [str(d) for d in eom_mismatch]}}

    def leg(metric, labels, one_sided):
        vals = [(d, metrics[d][metric]) for d in days if metrics[d][metric] is not None]
        return month_block_perm(vals, labels, rng, one_sided=one_sided)

    for name, metric, labels, oneside in (
            ("C1_fix_convA", "fix", got_a, False),
            ("C1_fix_convB_diag", "fix", got_b, False),
            ("C2_postfix_convA", "postfix", got_a, False),
            ("P1_eom_d1", "d1", eom, True)):
        obs, p, n_t, n_c = leg(metric, labels, oneside)
        res[name] = {"diff_pips": round(obs, 3), "p": round(p, 5),
                     "n_treat": n_t, "n_control": n_c,
                     "one_sided": oneside}

    # diagnostics: yearly means of C1 conv A (decay curve)
    yearly = {}
    for y in range(2014, 2022):
        vals_t = [metrics[d]["fix"] for d in days
                  if d.year == y and d in got_a and metrics[d]["fix"] is not None]
        vals_c = [metrics[d]["fix"] for d in days
                  if d.year == y and d not in got_a and metrics[d]["fix"] is not None]
        if vals_t and vals_c:
            yearly[y] = round(mean(vals_t) - mean(vals_c), 3)
    res["C1_yearly_diff"] = yearly

    # weekday-matched sensitivity for C1 (reweight control to treatment DOW mix)
    dow_t = defaultdict(list)
    dow_c = defaultdict(list)
    for d in days:
        v = metrics[d]["fix"]
        if v is None:
            continue
        (dow_t if d in got_a else dow_c)[d.weekday()].append(v)
    wsum, wtot = 0.0, 0
    for wd, tv in dow_t.items():
        if dow_c.get(wd):
            wsum += (mean(tv) - mean(dow_c[wd])) * len(tv)
            wtot += len(tv)
    res["C1_dow_matched_diff"] = round(wsum / wtot, 3) if wtot else None

    Path(out_json).write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=2, default=str))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data/cache/massive")
    ap.add_argument("--calendar", default="data/calendar/structural_events.parquet")
    ap.add_argument("--out", default="knowledge-base/raw/bt-results/gotobi-calibration-explore-2026-07-28.json")
    args = ap.parse_args()
    run(args.data_root, args.calendar, args.out)


if __name__ == "__main__":
    main()
