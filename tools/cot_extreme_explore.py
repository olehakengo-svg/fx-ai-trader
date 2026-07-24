#!/usr/bin/env python3
"""
Family #5: cot_spec_positioning_extreme_weekly — EXPLORE ONLY (pre-2022).

Hypothesis (two-sided, both counted in m):
  REVERSION   : crowded speculative positioning (net_pct_oi at a rolling-3y
                extreme) marks a saturated trade -> the currency mean-reverts
                over the following weeks (fade the crowd).
  CONTINUATION: extremes mark informed institutional flow -> the move
                continues (follow the crowd).

Population: CFTC legacy non-commercial (institutional speculators) — distinct
from E1's Myfxbook retail population. E1 data is NOT touched here.

Design (exit-free, no TP/SL/BE/Trail):
  - Signal    : net_pct_oi rolling 3y (156-week) percentile per currency.
                Extreme zone = pct >= 0.90 (crowded long) or <= 0.10
                (crowded short). p5/p95 kept as a labelled diagnostic band.
  - Episodes  : consecutive extreme weeks are ONE event. Event = episode
                ONSET (first week entering the zone after being outside).
                Prevents pseudo-replication from persistent positioning.
  - Release-lag (FROZEN): COT report_date is Tuesday (as-of). Publication is
                Friday 15:30 ET = report_date + 3 BUSINESS DAYS. Signal is
                usable only after publication. Entry = OPEN of the first
                trading day of the NEXT week (first Monday strictly after
                publish date; <=3d holiday guard). Lookahead asserted:
                entry_date > publish_date AND entry_date - report_date >= 6d.
  - Pairs     : currency -> USD pair. JPY/CAD/CHF are QUOTE currencies:
                BUY currency == SELL pair (direction sign asserted in map).
  - Measurement: forward net/MFE/MAE in pips at horizons {1w,2w,4w} =
                {5,10,20} daily bars from entry Monday open (weekend rows
                dropped; entry bar included — entry price is its Open, all
                bar extremes occur after the open; no lookahead).
                Net is signed in the REVERSION direction (+ = reversion wins);
                continuation stats are the mirror image.
  - Friction  : RT subtraction + adverse swap stress 2.5%/yr (p95 of G6-USD
                short-rate differentials in-window; sign of true carry depends
                on position, so adverse-case is the honest explore treatment).
                Multi-week clause: swap shown for 1w/2w/4w (7/14/28 swap-days).
  - Stats     : one-sided episode bootstrap per (currency, horizon,
                direction); pooled bootstrap blocked by ENTRY DATE (same-week
                cross-currency correlation). BH-FDR q=0.10 over the primary
                family m = 6 ccy x 3 horizons x 2 directions = 36; pooled
                family m = 6 handled separately. Headroom = MFE_p50 / RT
                vs the 10x catalog entry condition.

OOS LOCK: COT report_date AND price index hard-filtered < 2022-01-01 with
asserts. 2022-01-01..2026-06-30 is never analyzed (joint COT x price contact
with OOS is forbidden until a pre-registered confirm).

No module-top side effects: everything runs under main().
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ── Frozen constants ─────────────────────────────────────────────────────
REPO = "/Users/jg-n-012/test/fx-ai-trader"
COT_PARQUET = f"{REPO}/data/external/cot_fx_panel.parquet"

# currency -> (pair, base_sign). base_sign=+1: currency is BASE (BUY ccy = BUY
# pair). base_sign=-1: currency is QUOTE (BUY ccy = SELL pair).
CCY_MAP = {
    "EUR": ("EUR_USD", +1),
    "GBP": ("GBP_USD", +1),
    "AUD": ("AUD_USD", +1),
    "JPY": ("USD_JPY", -1),
    "CAD": ("USD_CAD", -1),
    "CHF": ("USD_CHF", -1),
}
PRICE_TMPL = f"{REPO}/data/cache/massive/{{pair}}_1d_2014_2026.parquet"

PIP_SIZE = {"EUR_USD": 1e-4, "GBP_USD": 1e-4, "AUD_USD": 1e-4,
            "USD_JPY": 1e-2, "USD_CAD": 1e-4, "USD_CHF": 1e-4}
# RT friction (pips): EUR/JPY/GBP from KB friction table. AUD_USD 2.5p is the
# same theoretical assumption used by weekend_gap explore (not in KB table).
# USD_CAD/USD_CHF are NOT in the KB table: 3.0p theoretical (OANDA typical
# spread ~1.4-1.5p + 0.5-1.0p slippage) — flagged in report.
RT_PIPS = {"EUR_USD": 2.0, "USD_JPY": 2.14, "GBP_USD": 4.53,
           "AUD_USD": 2.5, "USD_CAD": 3.0, "USD_CHF": 3.0}
RT_THEORETICAL = {"AUD_USD", "USD_CAD", "USD_CHF"}

OOS_LOCK = pd.Timestamp("2022-01-01", tz="UTC")   # never analyze >= this
COT_OOS_LOCK = pd.Timestamp("2022-01-01")          # naive (COT is tz-naive)

ROLL_WINDOW = 156          # 3y of weekly reports
PCT_LO, PCT_HI = 0.10, 0.90            # primary extreme thresholds
PCT_LO_DIAG, PCT_HI_DIAG = 0.05, 0.95  # diagnostic band (NOT primary family)
RELEASE_LAG_BDAYS = 3      # FROZEN: Tue as-of -> Fri 15:30 ET publication
MIN_LAG_DAYS = 6           # lookahead assert: entry - report_date >= 6 cal days
HOLIDAY_GUARD_D = 3        # entry Monday missing -> allow Tue-Thu, else skip
HORIZON_BARS = {"1w": 5, "2w": 10, "4w": 20}   # trading bars incl. entry bar
SPAN_GUARD_4W_D = 35       # 20 bars normally span ~26 cal days; data holes skip
SWAP_STRESS_ANNUAL = 0.025  # adverse carry stress (see docstring)
SWAP_DAYS = {"1w": 7, "2w": 14, "4w": 28}
N_BOOT = 10_000
SEED = 20260724
BH_Q = 0.10

JSON_OUT = f"{REPO}/bt-results/cot_extreme_explore-2026-07-24.json"


# ── Loading ──────────────────────────────────────────────────────────────
def load_cot() -> pd.DataFrame:
    df = pd.read_parquet(COT_PARQUET)
    df = df[df["report_date"] < COT_OOS_LOCK].copy()
    assert len(df) > 0
    assert df["report_date"].max() < COT_OOS_LOCK, "COT OOS LOCK VIOLATED"
    assert not df["net_pct_oi"].isna().any(), "net_pct_oi NaN in explore window"
    # weekly cadence sanity per currency (holiday shifts 6/8d allowed)
    for ccy, g in df.groupby("currency"):
        d = g.sort_values("report_date")["report_date"].diff().dropna().dt.days
        assert d.isin([6, 7, 8]).all(), f"{ccy}: non-weekly cadence {sorted(set(d))}"
    return df


def load_price(pair: str) -> pd.DataFrame:
    df = pd.read_parquet(PRICE_TMPL.format(pair=pair))
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    df = df[df.index < OOS_LOCK]
    assert len(df) > 0, f"{pair}: empty after OOS filter"
    assert df.index.max() < OOS_LOCK, f"{pair}: OOS LOCK VIOLATED ({df.index.max()})"
    # Drop weekend rows (MASSIVE feed artifact: Saturday rows + partial Sunday
    # session bars — see price_shock audit 2026-07-24). Entry/horizons are
    # defined on Mon-Fri daily bars only.
    df = df[df.index.weekday < 5]
    assert df.index.is_monotonic_increasing
    return df[["Open", "High", "Low", "Close"]].astype(float)


# ── Signal ───────────────────────────────────────────────────────────────
def rolling_pct(vals: np.ndarray, window: int) -> np.ndarray:
    """Percentile rank of current value within trailing full window
    (inclusive; backward-looking only — no leakage)."""
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        w = vals[i - window + 1: i + 1]
        x = vals[i]
        out[i] = ((w < x).sum() + 0.5 * (w == x).sum()) / window
    return out


def episodes_for_ccy(g: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    """Episode onsets: first week entering an extreme zone after being outside.
    Consecutive in-zone weeks = one event (pseudo-replication control)."""
    s = g.sort_values("report_date").reset_index(drop=True)
    pct = rolling_pct(s["net_pct_oi"].to_numpy(), ROLL_WINDOW)
    zone = np.zeros(len(s), dtype=int)
    zone[pct >= hi] = 1     # crowded long
    zone[pct <= lo] = -1    # crowded short
    zone[np.isnan(pct)] = 0
    prev = np.concatenate([[0], zone[:-1]])
    onset = (zone != 0) & (zone != prev)
    s["pct"], s["zone"], s["onset"] = pct, zone, onset

    # episode duration (weeks in zone from each onset)
    dur = np.zeros(len(s), dtype=int)
    i = 0
    while i < len(s):
        if onset[i]:
            j = i
            while j + 1 < len(s) and zone[j + 1] == zone[i]:
                j += 1
            dur[i] = j - i + 1
            i = j + 1
        else:
            i += 1
    s["episode_weeks"] = dur
    return s


# ── Entry timing (release-lag, FROZEN) ───────────────────────────────────
def publish_date(report_d: date) -> date:
    """report_date + 3 business days (Tue -> Fri). COT as-of dates are always
    Mon/Tue (business days) — asserted."""
    assert report_d.weekday() in (0, 1), f"unexpected report weekday {report_d}"
    return np.busday_offset(np.datetime64(report_d, "D"),
                            RELEASE_LAG_BDAYS).astype("datetime64[D]").astype(object)


def next_monday_after(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


# ── Forward measurement (exit-free) ─────────────────────────────────────
def measure_event(px: pd.DataFrame, i0: int, pair_dir: int, pip: float) -> dict:
    o = float(px["Open"].iloc[i0])
    out = {}
    for hname, nb in HORIZON_BARS.items():
        hi = px["High"].iloc[i0:i0 + nb].to_numpy()
        lo = px["Low"].iloc[i0:i0 + nb].to_numpy()
        c = float(px["Close"].iloc[i0 + nb - 1])
        if pair_dir > 0:   # long pair in reversion direction
            net = (c - o) / pip
            mfe = (hi.max() - o) / pip
            mae = (o - lo.min()) / pip
        else:              # short pair
            net = (o - c) / pip
            mfe = (o - lo.min()) / pip
            mae = (hi.max() - o) / pip
        out[hname] = {"net": net, "mfe": mfe, "mae": mae}
    return out


def extract_events(ccy: str, sig: pd.DataFrame, px: pd.DataFrame,
                   base_sign: int, pip: float) -> tuple[list[dict], dict]:
    idx_dates = px.index.normalize()
    last_i = len(px) - 1
    skip = {"pre_price_history": 0, "no_entry_bar": 0,
            "incomplete_4w": 0, "span_guard": 0}
    events = []
    for _, row in sig[sig["onset"]].iterrows():
        rep_d = row["report_date"].date()
        pub_d = publish_date(rep_d)
        tgt = next_monday_after(pub_d)
        if pd.Timestamp(tgt, tz="UTC") < px.index[0]:
            skip["pre_price_history"] += 1
            continue
        i0 = int(idx_dates.searchsorted(pd.Timestamp(tgt, tz="UTC")))
        if i0 > last_i or (idx_dates[i0].date() - tgt).days > HOLIDAY_GUARD_D:
            skip["no_entry_bar"] += 1
            continue
        entry_d = idx_dates[i0].date()
        # ── lookahead asserts (release-lag discipline) ──
        assert entry_d > pub_d, f"{ccy} {rep_d}: entry {entry_d} <= publish {pub_d}"
        assert (entry_d - rep_d).days >= MIN_LAG_DAYS, \
            f"{ccy} {rep_d}: entry lag {(entry_d - rep_d).days}d < {MIN_LAG_DAYS}d"
        if i0 + HORIZON_BARS["4w"] - 1 > last_i:
            skip["incomplete_4w"] += 1
            continue
        span = (idx_dates[i0 + HORIZON_BARS["4w"] - 1].date() - entry_d).days
        if span > SPAN_GUARD_4W_D:
            skip["span_guard"] += 1
            continue
        zone = int(row["zone"])
        # reversion: fade the crowd. crowded long (zone=+1) -> SELL ccy.
        ccy_dir_rev = -zone
        pair_dir = ccy_dir_rev * base_sign
        m = measure_event(px, i0, pair_dir, pip)
        events.append({
            "report_date": str(rep_d), "publish_date": str(pub_d),
            "entry_date": str(entry_d), "zone": zone,
            "pct": float(row["pct"]), "episode_weeks": int(row["episode_weeks"]),
            "entry_open": float(px["Open"].iloc[i0]),
            "pair_dir_reversion": pair_dir, "m": m,
        })
    return events, skip


# ── Stats ────────────────────────────────────────────────────────────────
def pctile_block(a: np.ndarray) -> dict:
    return {"p25": float(np.percentile(a, 25)),
            "p50": float(np.percentile(a, 50)),
            "p75": float(np.percentile(a, 75))}


def bootstrap_p_mean_gt0(vals: np.ndarray, rng: np.random.Generator,
                         blocks: np.ndarray | None = None) -> float:
    """One-sided event/episode-block bootstrap p (H1: mean > 0)."""
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


def swap_stress_pips(pair: str, med_price: float, hname: str) -> float:
    return med_price * SWAP_STRESS_ANNUAL * SWAP_DAYS[hname] / 365.0 / PIP_SIZE[pair]


def cell_stats(evs: list[dict], pair: str, med_price: float,
               rng: np.random.Generator) -> dict:
    """Per-horizon reversion + continuation stats for one currency."""
    rt = RT_PIPS[pair]
    out = {}
    for hname in HORIZON_BARS:
        net = np.array([e["m"][hname]["net"] for e in evs])
        mfe = np.array([e["m"][hname]["mfe"] for e in evs])
        mae = np.array([e["m"][hname]["mae"] for e in evs])
        sw = swap_stress_pips(pair, med_price, hname)
        p_rev = bootstrap_p_mean_gt0(net, rng)
        p_cont = bootstrap_p_mean_gt0(-net, rng)
        out[hname] = {
            "n": len(net),
            "net_mean": float(net.mean()), "net_median": float(np.median(net)),
            "net_sd": float(net.std(ddof=1)) if len(net) > 1 else None,
            "mfe_rev": pctile_block(mfe), "mae_rev": pctile_block(mae),
            "boot_p_reversion": p_rev, "boot_p_continuation": p_cont,
            "rt_pips": rt, "swap_stress_pips": float(sw),
            "stressed_net_rev": float(net.mean() - rt - sw),
            "stressed_net_cont": float(-net.mean() - rt - sw),
            "headroom_rev": float(np.percentile(mfe, 50) / rt),
            "headroom_cont": float(np.percentile(mae, 50) / rt),
        }
    return out


def bh_fdr(pvals: list[tuple[str, float]], q: float) -> dict:
    """Benjamini-Hochberg step-up. Returns threshold + survivors."""
    m = len(pvals)
    srt = sorted(pvals, key=lambda kv: kv[1])
    k_star = 0
    for k, (_, p) in enumerate(srt, start=1):
        if p <= k * q / m:
            k_star = k
    surv = [kv for kv in srt[:k_star]]
    return {"m": m, "q": q, "k_star": k_star,
            "survivors": [{"cell": c, "p": p} for c, p in surv],
            "min_p": srt[0][1] if m else None,
            "min_cell": srt[0][0] if m else None}


# ── Main ─────────────────────────────────────────────────────────────────
def main() -> None:
    rng = np.random.default_rng(SEED)
    cot = load_cot()
    print(f"COT explore rows: {len(cot)}  span "
          f"{cot['report_date'].min().date()} .. {cot['report_date'].max().date()}")

    per_ccy = {}
    pooled_events = []          # (ccy, entry_date, event)
    diag_band_events = {}       # p5/p95 diagnostic
    primary_pvals = []

    for ccy, (pair, base_sign) in CCY_MAP.items():
        g = cot[cot["currency"] == ccy]
        px = load_price(pair)
        med_price = float(px["Close"].median())
        pip = PIP_SIZE[pair]

        sig = episodes_for_ccy(g, PCT_LO, PCT_HI)
        n_sig_weeks = int(sig["pct"].notna().sum())
        n_zone_weeks = int((sig["zone"] != 0).sum())
        events, skip = extract_events(ccy, sig, px, base_sign, pip)
        print(f"[{ccy}->{pair}] signal_weeks={n_sig_weeks} zone_weeks={n_zone_weeks} "
              f"onsets={int(sig['onset'].sum())} measured={len(events)} skips={skip}")
        assert len(events) >= 8, f"{ccy}: too few measured episodes ({len(events)})"

        stats = cell_stats(events, pair, med_price, rng)
        for hname, st in stats.items():
            primary_pvals.append((f"{ccy}|{hname}|reversion", st["boot_p_reversion"]))
            primary_pvals.append((f"{ccy}|{hname}|continuation", st["boot_p_continuation"]))

        # diagnostics: side split + extremity terciles + spacing
        long_evs = [e for e in events if e["zone"] == 1]
        short_evs = [e for e in events if e["zone"] == -1]
        side = {}
        for label, evs in (("crowded_long_fade", long_evs),
                           ("crowded_short_fade", short_evs)):
            if len(evs) >= 3:
                side[label] = {h: {"n": len(evs),
                                   "net_mean": float(np.mean([e["m"][h]["net"] for e in evs])),
                                   "net_median": float(np.median([e["m"][h]["net"] for e in evs]))}
                               for h in HORIZON_BARS}
        ext = np.array([max(e["pct"], 1 - e["pct"]) for e in events])
        net2 = np.array([e["m"]["2w"]["net"] for e in events])
        terc = None
        if len(events) >= 9:
            q1, q2 = np.percentile(ext, [33.34, 66.67])
            lab = np.where(ext <= q1, 0, np.where(ext <= q2, 1, 2))
            rows = [{"tercile": t + 1, "n": int((lab == t).sum()),
                     "extremity_median": float(np.median(ext[lab == t])),
                     "net2w_median": float(np.median(net2[lab == t])),
                     "net2w_mean": float(net2[lab == t].mean())}
                    for t in (0, 1, 2)]
            meds = [r["net2w_median"] for r in rows]
            terc = {"rows": rows,
                    "monotone_increasing": bool(meds[0] < meds[1] < meds[2]),
                    "monotone_decreasing": bool(meds[0] > meds[1] > meds[2])}
        entry_ts = pd.to_datetime([e["entry_date"] for e in events])
        spacing = np.diff(entry_ts.values).astype("timedelta64[D]").astype(int) \
            if len(events) > 1 else np.array([])

        per_ccy[ccy] = {
            "pair": pair, "base_sign": base_sign,
            "rt_pips": RT_PIPS[pair], "rt_theoretical": pair in RT_THEORETICAL,
            "median_price": med_price,
            "signal_weeks": n_sig_weeks, "zone_weeks": n_zone_weeks,
            "n_onsets": int(sig["onset"].sum()), "n_measured": len(events),
            "skips": skip,
            "episode_weeks": pctile_block(np.array([e["episode_weeks"] for e in events])),
            "inter_onset_spacing_days": pctile_block(spacing) if len(spacing) else None,
            "events_per_year": round(len(events) / 8.0, 2),
            "horizons": stats, "side_split": side, "extremity_terciles": terc,
            "events": [{k: e[k] for k in ("report_date", "publish_date", "entry_date",
                                          "zone", "pct", "episode_weeks")}
                       | {"net_1w": round(e["m"]["1w"]["net"], 1),
                          "net_2w": round(e["m"]["2w"]["net"], 1),
                          "net_4w": round(e["m"]["4w"]["net"], 1)}
                       for e in events],
        }
        for e in events:
            pooled_events.append((ccy, e))

        # diagnostic band p5/p95 (labelled, NOT in primary family)
        sig_d = episodes_for_ccy(g, PCT_LO_DIAG, PCT_HI_DIAG)
        ev_d, _ = extract_events(ccy, sig_d, px, base_sign, pip)
        diag_band_events[ccy] = {
            "n": len(ev_d),
            "horizons": {h: {"net_mean": float(np.mean([e["m"][h]["net"] for e in ev_d])),
                             "net_median": float(np.median([e["m"][h]["net"] for e in ev_d])),
                             "boot_p_reversion": bootstrap_p_mean_gt0(
                                 np.array([e["m"][h]["net"] for e in ev_d]), rng),
                             "boot_p_continuation": bootstrap_p_mean_gt0(
                                 -np.array([e["m"][h]["net"] for e in ev_d]), rng)}
                        for h in HORIZON_BARS} if ev_d else None,
        }

    # ── pooled (blocks = entry date; same-week cross-ccy correlation) ────
    blocks = np.array([e["entry_date"] for _, e in pooled_events])
    pooled = {"n": len(pooled_events),
              "n_distinct_entry_dates": int(len(np.unique(blocks))),
              "horizons": {}}
    pooled_pvals = []
    for hname in HORIZON_BARS:
        net = np.array([e["m"][hname]["net"] for _, e in pooled_events])
        bp = np.array([e["m"][hname]["net"] * PIP_SIZE[CCY_MAP[c][0]]
                       / e["entry_open"] * 1e4 for c, e in pooled_events])
        p_rev = bootstrap_p_mean_gt0(net, rng, blocks)
        p_cont = bootstrap_p_mean_gt0(-net, rng, blocks)
        pooled["horizons"][hname] = {
            "net_mean_pips": float(net.mean()), "net_median_pips": float(np.median(net)),
            "net_mean_bp": float(bp.mean()), "net_median_bp": float(np.median(bp)),
            "boot_p_reversion_entrydate_block": p_rev,
            "boot_p_continuation_entrydate_block": p_cont,
        }
        pooled_pvals.append((f"pooled|{hname}|reversion", p_rev))
        pooled_pvals.append((f"pooled|{hname}|continuation", p_cont))

    # yearly diagnostic (pooled reversion net 2w)
    yr = {}
    for c, e in pooled_events:
        y = e["entry_date"][:4]
        yr.setdefault(y, []).append(e["m"]["2w"]["net"])
    yearly = {y: {"n": len(v), "net2w_mean": float(np.mean(v))}
              for y, v in sorted(yr.items())}

    bh_primary = bh_fdr(primary_pvals, BH_Q)
    bh_pooled = bh_fdr(pooled_pvals, BH_Q)

    result = {
        "task": "family #5 cot_spec_positioning_extreme_weekly EXPLORE",
        "run_date": "2026-07-24",
        "explore_window": {
            "cot_signal": "2010-01-05 .. 2021-12-28 (2010-2012 burned as rolling-3y warmup)",
            "price_events": "2014-01 .. 2021-11 (12y parquet starts 2013-12-30; 4w-forward completeness)",
        },
        "oos_lock": "COT report_date AND price index hard-filtered < 2022-01-01 + asserts; joint COT x price OOS contact forbidden",
        "frozen_definitions": {
            "signal": f"net_pct_oi rolling {ROLL_WINDOW}w percentile (backward-looking, inclusive)",
            "extreme_primary": f"pct >= {PCT_HI} (crowded long) / <= {PCT_LO} (crowded short)",
            "extreme_diagnostic": f"pct >= {PCT_HI_DIAG} / <= {PCT_LO_DIAG} (labelled band, not in m)",
            "episode": "consecutive in-zone weeks = 1 event; event = zone onset",
            "release_lag": f"publish = report_date + {RELEASE_LAG_BDAYS} business days (Fri 15:30 ET); entry = next Monday open strictly after publish; asserts entry>publish and entry-report>= {MIN_LAG_DAYS}d",
            "horizons": {k: f"{v} daily bars incl. entry bar" for k, v in HORIZON_BARS.items()},
            "direction_convention": "net signed in REVERSION (fade-the-crowd) direction; continuation = mirror",
            "swap_stress": f"adverse {SWAP_STRESS_ANNUAL:.1%}/yr x {SWAP_DAYS} swap-days (multi-week clause)",
            "bootstrap": f"one-sided, B={N_BOOT}, seed {SEED}; per-ccy = episode bootstrap; pooled = entry-date block",
            "bh_fdr": f"q={BH_Q}; primary family m={len(primary_pvals)} (6 ccy x 3 h x 2 dir); pooled family m={len(pooled_pvals)}",
            "rt_note": "AUD_USD 2.5p / USD_CAD 3.0p / USD_CHF 3.0p are theoretical (not in KB friction table)",
        },
        "currencies": per_ccy,
        "pooled": pooled,
        "yearly_pooled_net2w": yearly,
        "bh_primary_family": bh_primary,
        "bh_pooled_family": bh_pooled,
        "diagnostic_band_p5_p95": diag_band_events,
    }
    with open(JSON_OUT, "w") as f:
        json.dump(result, f, indent=1, default=str)
    print(f"\nwrote {JSON_OUT}")

    # console summary
    print("\n=== PRIMARY FAMILY BH-FDR (q=0.10, m=%d) ===" % bh_primary["m"])
    print(f"min p = {bh_primary['min_p']} @ {bh_primary['min_cell']}  "
          f"survivors = {len(bh_primary['survivors'])}")
    for s in bh_primary["survivors"]:
        print("  SURVIVES:", s)
    print("=== POOLED FAMILY BH-FDR (q=0.10, m=%d) ===" % bh_pooled["m"])
    print(f"min p = {bh_pooled['min_p']} @ {bh_pooled['min_cell']}  "
          f"survivors = {len(bh_pooled['survivors'])}")
    for s in bh_pooled["survivors"]:
        print("  SURVIVES:", s)


if __name__ == "__main__":
    sys.exit(main())
