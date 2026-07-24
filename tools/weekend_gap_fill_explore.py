#!/usr/bin/env python3
"""
W0-3: weekend_gap_fill_multiday — EXPLORE ONLY (2014-01-01 .. 2021-12-31).

Hypothesis: large weekend gaps (Monday open vs Friday close) tend to fill
back toward the Friday close ("fade the gap").

Design (exit-free, no TP/SL/BE/Trail simulation):
  - Friday close  = Close of last 15m bar with ts <  Friday 21:00 UTC
                    (guard: bar must lie within 6h before the cutoff)
  - Monday open   = Open  of first 15m bar with ts >= Sunday 21:00 UTC
                    (guard: bar must lie within 24h after the cutoff)
  - gap           = monday_open - friday_close  (price units)
  - Qualify       : |gap_pips| >= 10 x pair RT friction (primary),
                    5x RT kept as a clearly-labelled diagnostic band.
  - Signal        : fade the gap. gap>0 -> SHORT toward fill, gap<0 -> LONG.
  - Measurement   : forward MFE/MAE/net move TOWARD FILL at fixed horizons
                    h in {4h, 12h, 24h, 72h, 120h}, event bar excluded from
                    every forward window (asserted). Entry ref = Monday open.
  - Fill timing   : time-to-50%-fill and time-to-full-fill within 120h.
  - Stats         : per-pair N, MFE/MAE p25/p50/p75, net mean/median,
                    one-sided event-block bootstrap p (H1: mean net toward
                    fill > 0), headroom = MFE_p50 / RT, gap-size tercile
                    monotonicity. Pooled bootstrap blocks by weekend date
                    (same-weekend cross-pair correlation).

OOS LOCK: hard date filter keeps data strictly < 2022-01-01 and the script
asserts max(loaded index) < 2022-01-01 for every pair.

No module-top side effects: everything runs under main().
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

# ── Constants (data, no side effects) ───────────────────────────────────
REPO = "/Users/jg-n-012/test/fx-ai-trader"

PAIRS = {
    "EUR_USD": f"{REPO}/data/cache/massive/EUR_USD_15m_2014_2026.parquet",
    "USD_JPY": f"{REPO}/data/cache/massive/USD_JPY_15m_2014_2026.parquet",
    "GBP_USD": f"{REPO}/data/cache/massive/GBP_USD_15m_2014_2026.parquet",
    # AUD_JPY has no 12y parquet (starts 2021-12-24) -> substituted by the
    # 4th USD major with full 12y history:
    "AUD_USD": f"{REPO}/data/cache/massive/AUD_USD_15m_2014_2026.parquet",
}

# Round-turn theoretical friction (pips). EUR/JPY/GBP from task brief (KB
# friction table). AUD_USD absent from KB -> 2.5p theoretical assumption
# (spread slightly wider than EUR_USD), flagged in report.
RT_PIPS = {"EUR_USD": 2.0, "USD_JPY": 2.14, "GBP_USD": 4.53, "AUD_USD": 2.5}
PIP_SIZE = {"EUR_USD": 1e-4, "USD_JPY": 1e-2, "GBP_USD": 1e-4, "AUD_USD": 1e-4}

EXPLORE_START = pd.Timestamp("2014-01-01", tz="UTC")
OOS_LOCK = pd.Timestamp("2022-01-01", tz="UTC")   # never touch >= this

HORIZONS_H = [4, 12, 24, 72, 120]
QUALIFY_MULT_PRIMARY = 10.0
QUALIFY_MULT_DIAG = 5.0
FRI_CLOSE_GUARD_H = 6     # Friday-close bar must be within 6h before cutoff
SUN_OPEN_GUARD_H = 24     # Monday-open bar must be within 24h after cutoff
N_BOOT = 10_000
SEED = 20260724

JSON_OUT = f"{REPO}/bt-results/weekend_gap_fill_multiday-2026-07-24.json"
MD_OUT = f"{REPO}/reports/weekend_gap_fill_multiday-2026-07-24.md"


# ── Data loading ─────────────────────────────────────────────────────────
def load_pair(pair: str) -> pd.DataFrame:
    df = pd.read_parquet(PAIRS[pair])
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    df = df[(df.index >= EXPLORE_START) & (df.index < OOS_LOCK)]
    assert len(df) > 0, f"{pair}: empty after explore-window filter"
    assert df.index.max() < OOS_LOCK, f"{pair}: OOS LOCK VIOLATED ({df.index.max()})"
    assert df.index.is_monotonic_increasing
    return df[["Open", "High", "Low", "Close"]].astype(float)


# ── Event extraction ─────────────────────────────────────────────────────
def fridays(start: pd.Timestamp, end: pd.Timestamp):
    d = start
    while d.weekday() != 4:  # Friday
        d += timedelta(days=1)
    while d <= end:
        yield d
        d += timedelta(days=7)


def extract_events(pair: str, df: pd.DataFrame) -> tuple[list[dict], dict]:
    """All weekend gap events (before qualification). Returns (events, skip_counts)."""
    pip = PIP_SIZE[pair]
    idx = df.index
    last_ts = idx[-1]
    skip = {"no_friday_close": 0, "no_sunday_open": 0, "incomplete_120h": 0}
    events = []
    for fri in fridays(EXPLORE_START, OOS_LOCK - timedelta(days=1)):
        fri_cut = fri.replace(hour=21, minute=0)
        sun_cut = fri_cut + timedelta(hours=48)

        i_fri = idx.searchsorted(fri_cut) - 1  # last bar strictly < fri_cut
        if i_fri < 0 or (fri_cut - idx[i_fri]) > timedelta(hours=FRI_CLOSE_GUARD_H):
            skip["no_friday_close"] += 1
            continue
        i_sun = idx.searchsorted(sun_cut)      # first bar >= sun_cut
        if i_sun >= len(idx) or (idx[i_sun] - sun_cut) > timedelta(hours=SUN_OPEN_GUARD_H):
            skip["no_sunday_open"] += 1
            continue

        event_ts = idx[i_sun]
        if event_ts + timedelta(hours=HORIZONS_H[-1]) > last_ts:
            skip["incomplete_120h"] += 1
            continue

        fri_close = float(df["Close"].iloc[i_fri])
        mon_open = float(df["Open"].iloc[i_sun])
        gap = mon_open - fri_close
        events.append({
            "weekend": str(fri.date()),
            "event_ts": event_ts,
            "event_idx": int(i_sun),
            "fri_close": fri_close,
            "mon_open": mon_open,
            "gap_pips": gap / pip,
        })
    return events, skip


# ── Forward measurement (exit-free) ─────────────────────────────────────
def measure_event(pair: str, df: pd.DataFrame, ev: dict) -> dict:
    """Toward-fill MFE/MAE/net at fixed horizons + fill timing. Event bar excluded."""
    pip = PIP_SIZE[pair]
    idx = df.index
    ts0 = ev["event_ts"]
    entry = ev["mon_open"]
    gap = ev["gap_pips"] * pip
    short = gap > 0  # fade: gap-up -> short toward Friday close

    i0 = ev["event_idx"] + 1  # forward window starts strictly AFTER event bar
    out = {"horizons": {}}
    highs = df["High"].to_numpy()
    lows = df["Low"].to_numpy()
    closes = df["Close"].to_numpy()

    for h in HORIZONS_H:
        i1 = idx.searchsorted(ts0 + timedelta(hours=h), side="right")
        assert i1 > i0, f"{pair} {ts0}: empty {h}h window"
        assert idx[i0] > ts0, "lookahead: event bar inside forward window"
        w_hi, w_lo, c_h = highs[i0:i1], lows[i0:i1], closes[i1 - 1]
        if short:
            mfe = (entry - w_lo.min()) / pip
            mae = (w_hi.max() - entry) / pip
            net = (entry - c_h) / pip
        else:
            mfe = (w_hi.max() - entry) / pip
            mae = (entry - w_lo.min()) / pip
            net = (c_h - entry) / pip
        out["horizons"][h] = {"mfe": mfe, "mae": mae, "net": net,
                              "n_bars": int(i1 - i0)}

    # fill timing within 120h
    i1 = idx.searchsorted(ts0 + timedelta(hours=120), side="right")
    w_hi, w_lo = highs[i0:i1], lows[i0:i1]
    half_lvl = entry - 0.5 * gap
    full_lvl = ev["fri_close"]
    hit_half = (w_lo <= half_lvl) if short else (w_hi >= half_lvl)
    hit_full = (w_lo <= full_lvl) if short else (w_hi >= full_lvl)

    def first_hit_hours(mask: np.ndarray):
        j = int(np.argmax(mask)) if mask.any() else -1
        if j < 0:
            return None
        return float((idx[i0 + j] - ts0).total_seconds() / 3600.0)

    out["t_half_fill_h"] = first_hit_hours(hit_half)
    out["t_full_fill_h"] = first_hit_hours(hit_full)
    return out


# ── Stats helpers ────────────────────────────────────────────────────────
def pctile_block(a: np.ndarray) -> dict:
    return {"p25": float(np.percentile(a, 25)),
            "p50": float(np.percentile(a, 50)),
            "p75": float(np.percentile(a, 75))}


def bootstrap_p_mean_gt0(vals: np.ndarray, rng: np.random.Generator,
                         blocks: np.ndarray | None = None) -> float:
    """One-sided event-block bootstrap p (H1: mean > 0).

    blocks=None -> each value is its own block. Otherwise values sharing a
    block label (weekend date) are resampled together.
    """
    if len(vals) == 0:
        return float("nan")
    if blocks is None:
        n = len(vals)
        samp = rng.integers(0, n, size=(N_BOOT, n))
        means = vals[samp].mean(axis=1)
    else:
        uniq = np.unique(blocks)
        groups = [vals[blocks == b] for b in uniq]
        nb = len(groups)
        means = np.empty(N_BOOT)
        for k in range(N_BOOT):
            pick = rng.integers(0, nb, size=nb)
            means[k] = np.concatenate([groups[j] for j in pick]).mean()
    return float((np.sum(means <= 0.0) + 1) / (N_BOOT + 1))


def summarize(pair: str, evs: list[dict], rng: np.random.Generator) -> dict:
    rt = RT_PIPS[pair]
    res = {"n": len(evs), "horizons": {}}
    if not evs:
        return res
    for h in HORIZONS_H:
        mfe = np.array([e["m"]["horizons"][h]["mfe"] for e in evs])
        mae = np.array([e["m"]["horizons"][h]["mae"] for e in evs])
        net = np.array([e["m"]["horizons"][h]["net"] for e in evs])
        res["horizons"][h] = {
            "mfe": pctile_block(mfe), "mae": pctile_block(mae),
            "net_mean": float(net.mean()), "net_median": float(np.median(net)),
            "boot_p_one_sided": bootstrap_p_mean_gt0(net, rng),
            "headroom_mult": float(np.percentile(mfe, 50) / rt),
        }
    t_half = [e["m"]["t_half_fill_h"] for e in evs]
    t_full = [e["m"]["t_full_fill_h"] for e in evs]
    got_h = np.array([t for t in t_half if t is not None])
    got_f = np.array([t for t in t_full if t is not None])
    res["fill"] = {
        "half_fill_rate_120h": float(len(got_h) / len(evs)),
        "full_fill_rate_120h": float(len(got_f) / len(evs)),
        "half_fill_rate_24h": float(np.mean([(t is not None and t <= 24) for t in t_half])),
        "full_fill_rate_24h": float(np.mean([(t is not None and t <= 24) for t in t_full])),
        "full_fill_rate_72h": float(np.mean([(t is not None and t <= 72) for t in t_full])),
        "t_half_h": pctile_block(got_h) if len(got_h) else None,
        "t_full_h": pctile_block(got_f) if len(got_f) else None,
    }
    return res


def tercile_monotonicity(pair: str, evs: list[dict]) -> dict | None:
    """Median net@24h + full-fill rate by |gap|/RT tercile."""
    if len(evs) < 6:
        return None
    ratios = np.array([abs(e["gap_pips"]) / RT_PIPS[pair] for e in evs])
    net24 = np.array([e["m"]["horizons"][24]["net"] for e in evs])
    full = np.array([e["m"]["t_full_fill_h"] is not None for e in evs])
    q1, q2 = np.percentile(ratios, [33.34, 66.67])
    terc = np.where(ratios <= q1, 0, np.where(ratios <= q2, 1, 2))
    rows = []
    for t in (0, 1, 2):
        m = terc == t
        rows.append({"tercile": t + 1, "n": int(m.sum()),
                     "gap_rt_ratio_median": float(np.median(ratios[m])),
                     "net24_median": float(np.median(net24[m])),
                     "net24_mean": float(net24[m].mean()),
                     "full_fill_rate": float(full[m].mean())})
    meds = [r["net24_median"] for r in rows]
    return {"rows": rows,
            "monotone_increasing": bool(meds[0] < meds[1] < meds[2]),
            "monotone_decreasing": bool(meds[0] > meds[1] > meds[2])}


# ── Main ─────────────────────────────────────────────────────────────────
def main() -> None:
    rng = np.random.default_rng(SEED)
    all_pair_out = {}
    pooled = {QUALIFY_MULT_PRIMARY: [], QUALIFY_MULT_DIAG: []}

    for pair in PAIRS:
        df = load_pair(pair)
        print(f"[{pair}] rows={len(df)}  span={df.index[0]} .. {df.index[-1]}")
        events, skip = extract_events(pair, df)
        print(f"[{pair}] weekends_with_gap_measured={len(events)}  skips={skip}")
        assert len(events) > 300, f"{pair}: suspiciously few weekends ({len(events)}) — bug?"

        gaps = np.array([abs(e["gap_pips"]) for e in events])
        rt = RT_PIPS[pair]
        print(f"[{pair}] |gap| pips: p50={np.median(gaps):.1f} p90={np.percentile(gaps,90):.1f} "
              f"p99={np.percentile(gaps,99):.1f} max={gaps.max():.1f}  "
              f"RT={rt}p  10xRT={10*rt:.1f}p")

        pair_out = {"rt_pips": rt, "weekends_measured": len(events), "skips": skip,
                    "abs_gap_pips": {"p50": float(np.median(gaps)),
                                     "p90": float(np.percentile(gaps, 90)),
                                     "p99": float(np.percentile(gaps, 99)),
                                     "max": float(gaps.max())},
                    "thresholds": {}}

        for mult in (QUALIFY_MULT_PRIMARY, QUALIFY_MULT_DIAG):
            qual = [e for e in events if abs(e["gap_pips"]) >= mult * rt]
            for e in qual:
                if "m" not in e:
                    e["m"] = measure_event(pair, df, e)
            print(f"[{pair}] qualify >= {mult:.0f}x RT ({mult*rt:.1f}p): N={len(qual)}")
            summ = summarize(pair, qual, rng)
            summ["threshold_pips"] = mult * rt
            summ["tercile_monotonicity"] = tercile_monotonicity(pair, qual)
            summ["events"] = [{
                "weekend": e["weekend"], "event_ts": e["event_ts"].isoformat(),
                "gap_pips": round(e["gap_pips"], 1),
                "net24": round(e["m"]["horizons"][24]["net"], 1),
                "net120": round(e["m"]["horizons"][120]["net"], 1),
                "t_full_fill_h": e["m"]["t_full_fill_h"],
            } for e in qual]
            pair_out["thresholds"][f"{mult:.0f}x"] = summ
            for e in qual:
                pooled[mult].append((pair, e))
        all_pair_out[pair] = pair_out

    # pooled stats: bootstrap blocked by weekend date (cross-pair correlation)
    pooled_out = {}
    for mult, tagged in pooled.items():
        if not tagged:
            pooled_out[f"{mult:.0f}x"] = {"n": 0}
            continue
        blocks = np.array([e["weekend"] for _, e in tagged])
        entry = {"n": len(tagged),
                 "n_distinct_weekends": int(len(np.unique(blocks))),
                 "horizons": {}}
        for h in HORIZONS_H:
            net = np.array([e["m"]["horizons"][h]["net"] for _, e in tagged])
            mfe = np.array([e["m"]["horizons"][h]["mfe"] for _, e in tagged])
            mae = np.array([e["m"]["horizons"][h]["mae"] for _, e in tagged])
            entry["horizons"][h] = {
                "mfe": pctile_block(mfe), "mae": pctile_block(mae),
                "net_mean": float(net.mean()), "net_median": float(np.median(net)),
                "boot_p_one_sided_weekend_block": bootstrap_p_mean_gt0(net, rng, blocks),
            }
        pooled_out[f"{mult:.0f}x"] = entry

    result = {
        "task": "W0-3 weekend_gap_fill_multiday EXPLORE",
        "run_date": "2026-07-24",
        "explore_window": [str(EXPLORE_START.date()), str((OOS_LOCK - timedelta(days=1)).date())],
        "oos_lock": "data >= 2022-01-01 never loaded (hard filter + assert)",
        "definitions": {
            "friday_close": "Close of last 15m bar < Fri 21:00 UTC (<=6h guard)",
            "monday_open": "Open of first 15m bar >= Sun 21:00 UTC (<=24h guard)",
            "signal": "fade gap toward Friday close; event bar excluded from forward windows",
            "qualify_primary": "|gap| >= 10x RT", "qualify_diagnostic": "|gap| >= 5x RT",
            "horizons_h": HORIZONS_H, "bootstrap": f"one-sided, {N_BOOT} resamples, seed {SEED}",
            "aud_note": "AUD_JPY has no 12y parquet (starts 2021-12); AUD_USD substituted, RT 2.5p assumed (not in KB)",
        },
        "pairs": all_pair_out,
        "pooled": pooled_out,
    }
    with open(JSON_OUT, "w") as f:
        json.dump(result, f, indent=1, default=str)
    print(f"\nwrote {JSON_OUT}")


if __name__ == "__main__":
    sys.exit(main())
