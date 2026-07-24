#!/usr/bin/env python3
"""
weekend_gap_fill_oos_confirm.py — OOS confirm executor for the LOCKED pre-reg
knowledge-base/wiki/decisions/weekend-gap-oos-prereg-2026-07-24.md (rule:R1
stage-1, LOCKED 2026-07-24). Implements the frozen design EXACTLY — arms,
gates (a)-(e), BH step-up decision table, stressed-net, headroom, N floors,
DST re-anchor sensitivity, qualify-threshold perturbation (8x/12x RT),
spike-revert artifact flag rule (prereg section 3.1), flagged-event-excluded
recomputation, completeness audit, diagnostics (section 5), knife-edge
downgrades (sections 2.1/3.1/7-3) and the family verdict priority rules
(section 4.2). Everything is computed IN A SINGLE RUN (section 3).

Modes (mutually exclusive, required):
  --dry-run  explore window 2014-01-01 .. 2021-12-31. Free to run/re-run.
             Must reproduce the frozen explore stats (prereg section 3
             dry-run protocol): arm A 4h +12.3p / 12h +15.6p (N=57, p<1e-4
             both), arm B 4h +8.92p (N=169, 117 weekends, weekend-block
             p<1e-4, MFE p50 24.6p). Exits non-zero on reproduction failure.
  --oos      OOS window 2022-01-01 .. 2026-06-30. SINGLE-SHOT: the script
             refuses to run if an OOS output file already exists (prereg
             section 3 — re-execution after first look is prohibited).
             GBP_USD is never loaded in this mode (asserted + removed from
             the pair map so any accidental load raises).

Estimand identity (prereg section 2.1 / task requirement):
  tools/weekend_gap_fill_explore.py is imported (never modified) and its
  load_pair / extract_events / measure_event / bootstrap_p_mean_gt0 /
  summarize / tercile_monotonicity / pctile_block / fridays are reused
  verbatim. The explore module's window constants (EXPLORE_START, OOS_LOCK)
  are re-pointed at runtime to the selected mode window; in --dry-run they
  are set to values identical to the explore originals (asserted), so the
  dry-run code path is bit-identical to the explore estimand.

RNG discipline: one np.random.default_rng(20260724), B=10,000, one-sided,
consumed in a FIXED documented order (see RNG_ORDER below). p floor is
1/(B+1) and is reported as 'p<1e-4' (prereg section 3).

No module-top side effects (constants only). No silent except (no
try/except anywhere — any failure aborts loudly before output is written).
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

# ── Frozen constants (all values copied verbatim from the LOCKED prereg) ──
REPO = "/Users/jg-n-012/test/fx-ai-trader"
EXPLORE_SCRIPT = f"{REPO}/tools/weekend_gap_fill_explore.py"
PREREG_DOC = "knowledge-base/wiki/decisions/weekend-gap-oos-prereg-2026-07-24.md"

# GBP_USD excluded from BOTH arms (prereg section 2) and never loaded here.
PAIRS_CONFIRM = ("EUR_USD", "USD_JPY", "AUD_USD")

WINDOWS = {
    # mode: (start inclusive, end exclusive)
    "dry-run": (pd.Timestamp("2014-01-01", tz="UTC"), pd.Timestamp("2022-01-01", tz="UTC")),
    "oos": (pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC")),
}

QUALIFY_MULT = 10.0                                   # |gap| >= 10x normal RT
QUALIFY_PIPS_FROZEN = {"EUR_USD": 20.0, "USD_JPY": 21.4, "AUD_USD": 25.0}
STRESSED_RT_PAIR = {"EUR_USD": 6.0, "USD_JPY": 6.42, "AUD_USD": 7.5}  # 3x RT
STRESSED_RT_ARM_B = 6.56      # frozen explore-N-weighted; NO OOS reweighting
HEADROOM_REQ_A = 20.0         # gate (d): MFE p50 >= 10x normal RT (EUR_USD)
HEADROOM_REQ_B = 21.9         # frozen explore-N-weighted constant for arm B
N_FLOOR = {"A": 25, "B": 60}  # gate (e); below floor -> UNDERPOWERED
ARM_A_HORIZONS = (4, 12)      # co-primary, IUT max-p (both required)
ARM_B_HORIZON = 4
PERTURB_MULTS = (8.0, 12.0)   # section 7-3 (ii): qualify threshold +/-20%
SPIKE_REVERT_FRAC = 0.20      # section 3.1: event-bar close within 20% of gap
NY_TZ = "America/New_York"    # section 2.1 DST sensitivity anchor (17:00 NY)
SEED = 20260724
N_BOOT = 10_000
P_FLOOR = 1.0 / (N_BOOT + 1)

RNG_ORDER = [
    "1. per-pair summarize (EUR_USD, USD_JPY, AUD_USD) x 5 horizons each",
    "2. pooled weekend-block bootstrap per horizon (4,12,24,72,120)",
    "3. spike-revert-excluded recompute: armA p4h, p12h; armB p4h (only if flags>0)",
    "(DST re-anchor and 8x/12x perturbation are sign checks on means: no RNG)",
]

# Frozen explore stats the dry-run must reproduce (prereg section 3).
FROZEN_EXPLORE = {
    "armA_n": 57,
    "armA_net4": 12.3, "armA_net12": 15.6,
    "armA_p4": "p<1e-4", "armA_p12": "p<1e-4",
    "armB_n": 169, "armB_weekends": 117,
    "armB_net4": 8.92, "armB_p4": "p<1e-4",
    "armB_mfe_p50_4h": 24.6,
}

NOTES = [
    "swap: ignored — holding <=12h, multi-week clause N/A (prereg section 2)",
    "AUD_USD RT 2.5p is a theoretical placeholder outside the KB friction "
    "table (prereg section 2 requires restating this in the verdict)",
    "GBP_USD is excluded from both arms and never loaded in --oos mode "
    "(prereg section 2 — protects a potential future GBP-continuation family)",
    "qualify thresholds frozen in pips (no RT recomputation on 2022+ spreads)",
    "measurement is exit-free fixed-horizon (no TP/SL/BE/Trail — MEMORY "
    "project_be_trail_inflates_python_bt_wr)",
    "bootstrap p floor = 1/(B+1); reported as 'p<1e-4'",
]


# ── Explore module reuse (imported, never modified) ─────────────────────
def load_explore_module():
    spec = importlib.util.spec_from_file_location(
        "weekend_gap_fill_explore", EXPLORE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # explore module has no top-level side effects
    return mod


def assert_explore_frozen(wg) -> None:
    """Guard: the imported explore module still carries the frozen design."""
    assert wg.SEED == SEED, "explore SEED drifted"
    assert wg.N_BOOT == N_BOOT, "explore N_BOOT drifted"
    assert wg.HORIZONS_H == [4, 12, 24, 72, 120], "explore horizons drifted"
    assert wg.RT_PIPS == {"EUR_USD": 2.0, "USD_JPY": 2.14,
                          "GBP_USD": 4.53, "AUD_USD": 2.5}, "explore RT drifted"
    assert wg.QUALIFY_MULT_PRIMARY == QUALIFY_MULT, "explore qualify mult drifted"
    assert wg.EXPLORE_START == pd.Timestamp("2014-01-01", tz="UTC")
    assert wg.OOS_LOCK == pd.Timestamp("2022-01-01", tz="UTC")
    for p in PAIRS_CONFIRM:
        assert abs(QUALIFY_PIPS_FROZEN[p] - QUALIFY_MULT * wg.RT_PIPS[p]) < 1e-9, \
            f"{p}: frozen qualify pips != 10x RT"
        assert abs(STRESSED_RT_PAIR[p] - 3.0 * wg.RT_PIPS[p]) < 1e-9, \
            f"{p}: frozen stressed RT != 3x RT"


# ── Small helpers ────────────────────────────────────────────────────────
def fmt_p(p) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "NA"
    if p <= P_FLOOR + 1e-12:
        return "p<1e-4"
    return f"p={p:.4g}"


def nets(evs, h) -> np.ndarray:
    return np.array([e["m"]["horizons"][h]["net"] for e in evs], dtype=float)


def mfes(evs, h) -> np.ndarray:
    return np.array([e["m"]["horizons"][h]["mfe"] for e in evs], dtype=float)


def endpoint_stats(evs, h, stressed_rt) -> dict:
    """Gross / stressed-net means + MFE p50 at one horizon (no RNG)."""
    if not evs:
        return {"n": 0, "gross_mean": None, "stressed_mean": None,
                "net_median": None, "mfe_p50": None}
    net = nets(evs, h)
    return {"n": len(evs),
            "gross_mean": float(net.mean()),
            "stressed_mean": float((net - stressed_rt).mean()),
            "net_median": float(np.median(net)),
            "mfe_p50": float(np.percentile(mfes(evs, h), 50))}


def ensure_measured(wg, pair, df, evs) -> None:
    for e in evs:
        if "m" not in e:
            e["m"] = wg.measure_event(pair, df, e)


def qualified(evs, rt, mult):
    return [e for e in evs if abs(e["gap_pips"]) >= mult * rt]


def annotate_spike_revert(df, evs) -> None:
    """Section 3.1 flag: event-bar Close back within 20% of |gap| from Friday
    close (>80% of the gap reversed inside the event bar — spike-revert print).
    """
    closes = df["Close"].to_numpy()
    for e in evs:
        c0 = float(closes[e["event_idx"]])
        gap_abs = abs(e["mon_open"] - e["fri_close"])
        e["event_bar_close"] = c0
        e["spike_revert_flag"] = bool(abs(c0 - e["fri_close"]) <= SPIKE_REVERT_FRAC * gap_abs)


def data_holes(idx, min_days: float = 7.0) -> list[dict]:
    """Section 3.1 (c): gaps in the bar index longer than one week."""
    if len(idx) < 2:
        return []
    d = idx[1:] - idx[:-1]
    out = []
    for i in np.where(d > pd.Timedelta(days=min_days))[0]:
        out.append({"from": str(idx[i]), "to": str(idx[i + 1]),
                    "days": round(float(d[i].total_seconds()) / 86400.0, 1)})
    return out


def extract_events_ny17(wg, pair, df, start, end):
    """Section 2.1 DST sensitivity: weekend boundary re-anchored to 17:00
    America/New_York (tz-aware, DST-following). Mirrors wg.extract_events
    exactly except for the two cutoffs; measurement reuses wg.measure_event.
    """
    idx = df.index
    last_ts = idx[-1]
    pip = wg.PIP_SIZE[pair]
    skip = {"no_friday_close": 0, "no_sunday_open": 0, "incomplete_120h": 0}
    events = []
    for fri in wg.fridays(start, end - timedelta(days=1)):
        fri_cut = pd.Timestamp(f"{fri.date()} 17:00", tz=NY_TZ).tz_convert("UTC")
        sun_cut = pd.Timestamp(f"{(fri + timedelta(days=2)).date()} 17:00",
                               tz=NY_TZ).tz_convert("UTC")

        i_fri = idx.searchsorted(fri_cut) - 1  # last bar strictly < fri_cut
        if i_fri < 0 or (fri_cut - idx[i_fri]) > timedelta(hours=wg.FRI_CLOSE_GUARD_H):
            skip["no_friday_close"] += 1
            continue
        i_sun = idx.searchsorted(sun_cut)      # first bar >= sun_cut
        if i_sun >= len(idx) or (idx[i_sun] - sun_cut) > timedelta(hours=wg.SUN_OPEN_GUARD_H):
            skip["no_sunday_open"] += 1
            continue

        event_ts = idx[i_sun]
        if event_ts + timedelta(hours=wg.HORIZONS_H[-1]) > last_ts:
            skip["incomplete_120h"] += 1
            continue

        fri_close = float(df["Close"].iloc[i_fri])
        mon_open = float(df["Open"].iloc[i_sun])
        events.append({
            "weekend": str(fri.date()),
            "event_ts": event_ts,
            "event_idx": int(i_sun),
            "fri_close": fri_close,
            "mon_open": mon_open,
            "gap_pips": (mon_open - fri_close) / pip,
        })
    return events, skip


def bh_step_up(arm_ps: dict, tested: list) -> tuple[dict, dict]:
    """Gate (b): frozen BH-FDR q=0.10 step-up decision table (prereg 4(b)).
    m = number of arms that met the N floor (= tested arms).
    """
    passes = {a: False for a in arm_ps}
    m = len(tested)
    if m == 2:
        (a1, p1), (a2, p2) = sorted(((a, arm_ps[a]) for a in tested),
                                    key=lambda t: t[1])
        if p2 <= 0.10:
            passes[a1] = passes[a2] = True
            branch = "(i) p(2)<=0.10 -> both arms pass"
        elif p1 <= 0.05:
            passes[a1] = True
            branch = f"(ii) p(1)<=0.05 -> arm {a1} only"
        else:
            branch = "(iii) no arm passes"
    elif m == 1:
        a = tested[0]
        passes[a] = bool(arm_ps[a] <= 0.10)
        branch = f"m=1 -> arm {a} single test at alpha=0.10"
    else:
        branch = "m=0 -> no arm tested (all UNDERPOWERED)"
    return passes, {"m": m, "branch": branch, "q": 0.10}


def sign_flip(endpoints) -> bool | None:
    """Knife-edge criterion (sections 2.1/3.1/7-3, strict side per 10-4):
    positive sign of BOTH gross mean AND stressed-net mean must hold at every
    frozen endpoint; any non-positive value = flip. None = not evaluable (N=0).
    """
    if not endpoints:
        return None
    for ep in endpoints.values():
        if ep["n"] == 0:
            return None
    return bool(any(ep["gross_mean"] <= 0.0 or ep["stressed_mean"] <= 0.0
                    for ep in endpoints.values()))


def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


# ── Core run (single pass: gates + sensitivities + diagnostics) ─────────
def run(mode: str) -> int:
    start, end = WINDOWS[mode]
    run_date = datetime.now(timezone.utc).date().isoformat()

    wg = load_explore_module()
    assert_explore_frozen(wg)

    # Re-point the explore module's window constants to the mode window.
    # The explore FILE is never modified; in dry-run the values are identical
    # to the originals (asserted) => bit-identical estimand code path.
    if mode == "dry-run":
        assert start == wg.EXPLORE_START and end == wg.OOS_LOCK, \
            "dry-run window must equal the explore window"
    wg.EXPLORE_START = start
    wg.OOS_LOCK = end

    if mode == "oos":
        # GBP_USD must never be loaded in OOS mode (prereg section 2).
        wg.PAIRS = {k: v for k, v in wg.PAIRS.items() if k != "GBP_USD"}
        assert "GBP_USD" not in wg.PAIRS
        out_json = (f"{REPO}/knowledge-base/raw/bt-results/"
                    f"weekend_gap_oos_confirm-{run_date}.json")
        prior = glob.glob(f"{REPO}/knowledge-base/raw/bt-results/"
                          f"weekend_gap_oos_confirm-*.json")
        if prior:
            print("REFUSING TO RUN: OOS output already exists (single-shot "
                  f"rule, prereg section 3): {prior}", file=sys.stderr)
            return 2
        print("=== SINGLE-SHOT OOS RUN — re-execution after this run is "
              "prohibited (prereg section 3). Dry-run reproduction must have "
              "passed before this point. ===")
    else:
        out_json = f"{REPO}/bt-results/weekend_gap_oos_confirm_dryrun-{run_date}.json"

    assert "GBP_USD" not in PAIRS_CONFIRM
    rng = np.random.default_rng(SEED)
    cal_weekends = sum(1 for _ in wg.fridays(start, end - timedelta(days=1)))

    # ── Load + extract (estimand functions reused from explore) ─────────
    frames, base_events, completeness = {}, {}, {}
    for pair in PAIRS_CONFIRM:
        assert pair != "GBP_USD", "GBP_USD must never be loaded"
        df = wg.load_pair(pair)  # window filter + max<end assert inside
        # Hard per-mode asserts (task requirement / prereg section 3):
        assert df.index.min() >= start, f"{pair}: rows before window start"
        assert df.index.max() < end, f"{pair}: rows at/after window end"
        if mode == "oos":
            assert df.index.min() >= pd.Timestamp("2022-01-01", tz="UTC"), \
                f"{pair}: explore-window contamination in OOS run"
        events, skips = wg.extract_events(pair, df)
        annotate_spike_revert(df, events)
        frames[pair] = df
        base_events[pair] = events
        holes = data_holes(df.index)
        missing_frac = 1.0 - len(events) / cal_weekends
        completeness[pair] = {
            "rows": int(len(df)),
            "span": [str(df.index[0]), str(df.index[-1])],
            "calendar_weekends": int(cal_weekends),
            "weekends_measured": int(len(events)),
            "missing_frac": round(float(missing_frac), 4),
            "missing_gt_10pct": bool(missing_frac > 0.10),
            "skips": skips,
            "holes_gt_1w": holes,
        }
        print(f"[{pair}] rows={len(df)} span={df.index[0]}..{df.index[-1]} "
              f"weekends={len(events)}/{cal_weekends} skips={skips} "
              f"holes>{7}d={len(holes)}")

    # ── Qualification sets (10x primary; 8x/12x for perturbation) ───────
    qual = {}
    for pair in PAIRS_CONFIRM:
        rt = wg.RT_PIPS[pair]
        qual[pair] = {}
        for mult in (min(PERTURB_MULTS), QUALIFY_MULT, max(PERTURB_MULTS)):
            q = qualified(base_events[pair], rt, mult)
            ensure_measured(wg, pair, frames[pair], q)
            qual[pair][mult] = q
        print(f"[{pair}] qualify N: 8x={len(qual[pair][8.0])} "
              f"10x={len(qual[pair][QUALIFY_MULT])} 12x={len(qual[pair][12.0])} "
              f"(10x threshold {QUALIFY_PIPS_FROZEN[pair]}p frozen)")

    qual10_eur = qual["EUR_USD"][QUALIFY_MULT]
    pooled10 = [(pair, e) for pair in PAIRS_CONFIRM
                for e in qual[pair][QUALIFY_MULT]]

    # Section 7-2: arm A weekends must not overlap at the frozen horizons.
    ts_sorted = sorted(e["event_ts"] for e in qual10_eur)
    for a, b in zip(ts_sorted, ts_sorted[1:]):
        assert (b - a) > timedelta(hours=max(ARM_A_HORIZONS)), \
            "arm A event overlap at frozen horizons"

    # ── RNG step 1: per-pair diagnostics (explore-format, all horizons) ──
    pair_diag = {}
    for pair in PAIRS_CONFIRM:
        q10 = qual[pair][QUALIFY_MULT]
        summ = wg.summarize(pair, q10, rng)
        summ["threshold_pips"] = QUALIFY_PIPS_FROZEN[pair]
        summ["tercile_monotonicity_net24"] = wg.tercile_monotonicity(pair, q10)
        if summ.get("horizons"):
            for h in wg.HORIZONS_H:
                summ["horizons"][h]["p_display"] = fmt_p(
                    summ["horizons"][h]["boot_p_one_sided"])
        summ["events"] = [{
            "weekend": e["weekend"], "event_ts": e["event_ts"].isoformat(),
            "gap_pips": round(e["gap_pips"], 1),
            "net4": round(e["m"]["horizons"][4]["net"], 1),
            "net12": round(e["m"]["horizons"][12]["net"], 1),
            "net24": round(e["m"]["horizons"][24]["net"], 1),
            "net120": round(e["m"]["horizons"][120]["net"], 1),
            "t_full_fill_h": e["m"]["t_full_fill_h"],
            "spike_revert_flag": bool(e["spike_revert_flag"]),
        } for e in q10]
        pair_diag[pair] = summ

    # ── RNG step 2: pooled diagnostics (weekend-block, all horizons) ─────
    pooled_diag = {"n": len(pooled10)}
    if pooled10:
        blocks = np.array([e["weekend"] for _, e in pooled10])
        pooled_diag["n_distinct_weekends"] = int(len(np.unique(blocks)))
        pooled_diag["horizons"] = {}
        for h in wg.HORIZONS_H:
            net = np.array([e["m"]["horizons"][h]["net"] for _, e in pooled10])
            mfe = np.array([e["m"]["horizons"][h]["mfe"] for _, e in pooled10])
            mae = np.array([e["m"]["horizons"][h]["mae"] for _, e in pooled10])
            p = wg.bootstrap_p_mean_gt0(net, rng, blocks)
            pooled_diag["horizons"][h] = {
                "mfe": wg.pctile_block(mfe), "mae": wg.pctile_block(mae),
                "net_mean": float(net.mean()),
                "net_median": float(np.median(net)),
                "boot_p_one_sided_weekend_block": p,
                "p_display": fmt_p(p),
            }

    # ── Arms + gates (a)(c)(d)(e); p values reused from steps 1-2 ────────
    def arm_a_block(evs, p4, p12):
        eps = {}
        for h in ARM_A_HORIZONS:
            eps[h] = endpoint_stats(evs, h, STRESSED_RT_PAIR["EUR_USD"])
            eps[h]["headroom_req_pips"] = HEADROOM_REQ_A
            eps[h]["boot_p"] = p4 if h == 4 else p12
            eps[h]["p_display"] = fmt_p(eps[h]["boot_p"])
        n = len(evs)
        arm_p = max(p4, p12) if n else float("nan")  # IUT (intersection-union)
        return {"n": n, "endpoints": eps, "arm_p": arm_p,
                "arm_p_display": fmt_p(arm_p) if n else "NA"}

    def arm_b_block(tagged, p4):
        evs = [e for _, e in tagged]
        ep = endpoint_stats(evs, ARM_B_HORIZON, STRESSED_RT_ARM_B)
        ep["headroom_req_pips"] = HEADROOM_REQ_B
        ep["boot_p"] = p4
        ep["p_display"] = fmt_p(p4)
        wks = len({e["weekend"] for e in evs})
        return {"n": len(evs), "n_distinct_weekends": int(wks),
                "endpoints": {ARM_B_HORIZON: ep},
                "arm_p": p4 if evs else float("nan"),
                "arm_p_display": fmt_p(p4) if evs else "NA"}

    pA4 = pair_diag["EUR_USD"]["horizons"][4]["boot_p_one_sided"] \
        if pair_diag["EUR_USD"].get("horizons") else float("nan")
    pA12 = pair_diag["EUR_USD"]["horizons"][12]["boot_p_one_sided"] \
        if pair_diag["EUR_USD"].get("horizons") else float("nan")
    pB4 = pooled_diag["horizons"][4]["boot_p_one_sided_weekend_block"] \
        if pooled10 else float("nan")

    arms = {"A": arm_a_block(qual10_eur, pA4, pA12),
            "B": arm_b_block(pooled10, pB4)}

    def eval_gates(kind, arm):
        g = {"e_n_floor": bool(arm["n"] >= N_FLOOR[kind])}
        eps = arm["endpoints"]
        if arm["n"] == 0:
            g.update({"a_direction": False, "c_stressed_net": False,
                      "d_headroom": False})
            return g
        g["a_direction"] = bool(all(ep["gross_mean"] > 0 for ep in eps.values()))
        g["c_stressed_net"] = bool(all(ep["stressed_mean"] > 0 for ep in eps.values()))
        g["d_headroom"] = bool(all(ep["mfe_p50"] >= ep["headroom_req_pips"]
                                   for ep in eps.values()))
        return g

    for kind in arms:
        arms[kind]["gates"] = eval_gates(kind, arms[kind])
        arms[kind]["n_floor"] = N_FLOOR[kind]

    # Gate (b): BH step-up over the arms that met the N floor.
    tested = [k for k in arms if arms[k]["gates"]["e_n_floor"]]
    arm_ps = {k: arms[k]["arm_p"] for k in arms}
    b_passes, bh_detail = bh_step_up(arm_ps, tested)
    for kind in arms:
        arms[kind]["gates"]["b_multiplicity_bh"] = bool(b_passes[kind])

    # Pre-knife-edge status.
    for kind in arms:
        g = arms[kind]["gates"]
        if not g["e_n_floor"]:
            arms[kind]["status_pre_knife_edge"] = "UNDERPOWERED"
        elif all((g["a_direction"], g["b_multiplicity_bh"],
                  g["c_stressed_net"], g["d_headroom"])):
            arms[kind]["status_pre_knife_edge"] = "PASS"
        else:
            arms[kind]["status_pre_knife_edge"] = "FAIL"

    # ── Sensitivity 1 (section 2.1 / 7-3(i)): NY17:00 DST re-anchor ──────
    dst = {}
    dst_qual = {}
    for pair in PAIRS_CONFIRM:
        evs, skips = extract_events_ny17(wg, pair, frames[pair], start, end)
        q10 = qualified(evs, wg.RT_PIPS[pair], QUALIFY_MULT)
        ensure_measured(wg, pair, frames[pair], q10)
        dst_qual[pair] = q10
        dst[pair] = {"weekends_measured": len(evs), "skips": skips,
                     "qualify_n_10x": len(q10)}
    dst_a_eps = {h: {**endpoint_stats(dst_qual["EUR_USD"], h,
                                      STRESSED_RT_PAIR["EUR_USD"]),
                     "headroom_req_pips": HEADROOM_REQ_A}
                 for h in ARM_A_HORIZONS}
    dst_b_evs = [e for p in PAIRS_CONFIRM for e in dst_qual[p]]
    dst_b_eps = {ARM_B_HORIZON: {**endpoint_stats(dst_b_evs, ARM_B_HORIZON,
                                                  STRESSED_RT_ARM_B),
                                 "headroom_req_pips": HEADROOM_REQ_B}}
    dst_block = {
        "definition": "Friday close < Fri 17:00 America/New_York; Monday open"
                      " >= Sun 17:00 America/New_York (DST-following)",
        "per_pair": dst,
        "armA": {"n": len(dst_qual["EUR_USD"]), "endpoints": dst_a_eps,
                 "sign_flip": sign_flip(dst_a_eps)},
        "armB": {"n": len(dst_b_evs),
                 "n_distinct_weekends": len({e["weekend"] for e in dst_b_evs}),
                 "endpoints": dst_b_eps, "sign_flip": sign_flip(dst_b_eps)},
    }

    # ── Sensitivity 2 (section 7-3(ii)): qualify threshold 8x / 12x RT ───
    perturb = {}
    for mult in PERTURB_MULTS:
        a_evs = qual["EUR_USD"][mult]
        a_eps = {h: {**endpoint_stats(a_evs, h, STRESSED_RT_PAIR["EUR_USD"]),
                     "headroom_req_pips": HEADROOM_REQ_A}
                 for h in ARM_A_HORIZONS}
        b_evs = [e for p in PAIRS_CONFIRM for e in qual[p][mult]]
        b_eps = {ARM_B_HORIZON: {**endpoint_stats(b_evs, ARM_B_HORIZON,
                                                  STRESSED_RT_ARM_B),
                                 "headroom_req_pips": HEADROOM_REQ_B}}
        perturb[f"{mult:.0f}x"] = {
            "thresholds_pips": {p: round(mult * wg.RT_PIPS[p], 2)
                                for p in PAIRS_CONFIRM},
            "armA": {"n": len(a_evs), "endpoints": a_eps,
                     "sign_flip": sign_flip(a_eps)},
            "armB": {"n": len(b_evs), "endpoints": b_eps,
                     "sign_flip": sign_flip(b_eps)},
        }

    # ── Sensitivity 3 (section 3.1): spike-revert flags + excluded rerun ─
    flags_a = [e for e in qual10_eur if e["spike_revert_flag"]]
    flags_b = [(p, e) for p, e in pooled10 if e["spike_revert_flag"]]
    flag_list = [{"pair": p, "weekend": e["weekend"],
                  "gap_pips": round(e["gap_pips"], 1),
                  "event_bar_close": e["event_bar_close"],
                  "fri_close": e["fri_close"]} for p, e in pooled10
                 if e["spike_revert_flag"]]

    # RNG step 3 (consumed only when flags exist -> deterministic given data)
    def spike_excluded_arm_a():
        if not flags_a:
            return {"n_flagged": 0,
                    "note": "no flagged events — identical to primary",
                    "sign_flip": False}
        keep = [e for e in qual10_eur if not e["spike_revert_flag"]]
        p4 = wg.bootstrap_p_mean_gt0(nets(keep, 4), rng) if keep else float("nan")
        p12 = wg.bootstrap_p_mean_gt0(nets(keep, 12), rng) if keep else float("nan")
        blk = arm_a_block(keep, p4, p12)
        blk["gates_recomputed"] = eval_gates("A", blk)
        blk["n_flagged"] = len(flags_a)
        blk["sign_flip"] = sign_flip(blk["endpoints"])
        return blk

    def spike_excluded_arm_b():
        if not flags_b:
            return {"n_flagged": 0,
                    "note": "no flagged events — identical to primary",
                    "sign_flip": False}
        keep = [(p, e) for p, e in pooled10 if not e["spike_revert_flag"]]
        if keep:
            net = np.array([e["m"]["horizons"][ARM_B_HORIZON]["net"]
                            for _, e in keep])
            blocks = np.array([e["weekend"] for _, e in keep])
            p4 = wg.bootstrap_p_mean_gt0(net, rng, blocks)
        else:
            p4 = float("nan")
        blk = arm_b_block(keep, p4)
        blk["gates_recomputed"] = eval_gates("B", blk)
        blk["n_flagged"] = len(flags_b)
        blk["sign_flip"] = sign_flip(blk["endpoints"])
        return blk

    spike_block = {
        "rule": "flag if |event_bar_close - fri_close| <= 0.20 x |gap| "
                "(>80% of gap reversed inside the excluded event bar)",
        "n_flagged_armA": len(flags_a),
        "n_flagged_armB_pooled": len(flags_b),
        "flagged_events": flag_list,
        "armA_excluded_recompute": spike_excluded_arm_a(),
        "armB_excluded_recompute": spike_excluded_arm_b(),
    }

    # ── Knife-edge downgrades (applied to PASS arms only; recorded always) ─
    for kind in arms:
        flips = {
            "dst_ny17": dst_block[f"arm{kind}"]["sign_flip"],
            "perturb_8x": perturb["8x"][f"arm{kind}"]["sign_flip"],
            "perturb_12x": perturb["12x"][f"arm{kind}"]["sign_flip"],
            "spike_revert_excluded":
                spike_block[f"arm{kind}_excluded_recompute"]["sign_flip"],
        }
        arms[kind]["knife_edge_flips"] = flips
        status = arms[kind]["status_pre_knife_edge"]
        if status == "PASS":
            fired = [k for k, v in flips.items() if v is True]
            not_eval = [k for k, v in flips.items() if v is None]
            if fired:
                status = f"FAIL (knife-edge: {','.join(fired)})"
            if not_eval:
                arms[kind]["knife_edge_warning"] = \
                    f"not evaluable (n=0): {not_eval}"
        arms[kind]["status_final"] = status

    # ── Family verdict (section 4.2 priority rules, frozen) ─────────────
    finals = {k: arms[k]["status_final"] for k in arms}
    if any(s == "PASS" for s in finals.values()):
        family = ("PASS-candidate — family #3 proceeds to section 9 R1 "
                  "procedure (no live change; user approval required)")
    elif any(s.startswith("FAIL") for s in finals.values()):
        family = ("PERMANENT CLOSE — no PASS and >=1 tested FAIL (retry "
                  "prohibited; news-type variants only as a new family with "
                  "new pre-2022 explore)")
    else:
        family = ("CLOSE (UNDERPOWERED) — all arms below N floor; reopen "
                  "only on data-source update")

    # ── Section 5 diagnostics: annual counts / |gap| percentiles ────────
    def annual(evs_tagged):
        by_year = {}
        for pair, e in evs_tagged:
            y = int(e["event_ts"].year)
            by_year.setdefault(y, []).append(abs(e["gap_pips"]))
        return {y: {"n": len(v),
                    "abs_gap_p50": round(float(np.percentile(v, 50)), 1),
                    "abs_gap_p90": round(float(np.percentile(v, 90)), 1)}
                for y, v in sorted(by_year.items())}

    annual_diag = {"pooled": annual(pooled10)}
    for pair in PAIRS_CONFIRM:
        annual_diag[pair] = annual([(pair, e)
                                    for e in qual[pair][QUALIFY_MULT]])

    # Section 7-2: same-weekend cross-pair overlap + weekend-level lag-1 rho.
    wk_counts = Counter(e["weekend"] for _, e in pooled10)
    overlap_dist = Counter(v for v in wk_counts.values())
    wk_sorted = sorted(wk_counts)
    wk_net4 = [float(np.mean([e["m"]["horizons"][4]["net"]
                              for _, e in pooled10 if e["weekend"] == w]))
               for w in wk_sorted]
    if len(wk_net4) >= 3 and np.std(wk_net4[:-1]) > 0 and np.std(wk_net4[1:]) > 0:
        lag1_rho = float(np.corrcoef(wk_net4[:-1], wk_net4[1:])[0, 1])
    else:
        lag1_rho = None
    pseudo_rep = {
        "weekends_with_multiple_pairs_qualifying":
            int(sum(1 for v in wk_counts.values() if v >= 2)),
        "overlap_distribution": {str(k): int(v)
                                 for k, v in sorted(overlap_dist.items())},
        "weekend_level_net4_lag1_rho": lag1_rho,
        "armA_no_overlap_assert": "passed (all gaps > 12h)",
    }

    # Section 7-1 mechanism record (non-gating; explore reference shape:
    # t-half median 1-2h, full-fill median ~9-15h, MFE-dominant).
    mech = {}
    for pair in PAIRS_CONFIRM:
        d = pair_diag[pair]
        if d.get("horizons"):
            mech[pair] = {
                "t_half_h_p50": d["fill"]["t_half_h"]["p50"]
                    if d["fill"]["t_half_h"] else None,
                "t_full_h_p50": d["fill"]["t_full_h"]["p50"]
                    if d["fill"]["t_full_h"] else None,
                "full_fill_rate_120h": d["fill"]["full_fill_rate_120h"],
                "mfe_p50_4h": d["horizons"][4]["mfe"]["p50"],
                "mae_p50_4h": d["horizons"][4]["mae"]["p50"],
            }

    # ── Assemble result ──────────────────────────────────────────────────
    result = {
        "task": "weekend_gap short-horizon fade — OOS confirm (prereg-locked)",
        "prereg": PREREG_DOC,
        "mode": mode,
        "run_date": run_date,
        "window": [str(start.date()), str((end - timedelta(days=1)).date())],
        "seed": SEED, "n_boot": N_BOOT,
        "rng_consumption_order": RNG_ORDER,
        "pairs": list(PAIRS_CONFIRM),
        "frozen_constants": {
            "qualify_pips_10x": QUALIFY_PIPS_FROZEN,
            "stressed_rt_3x": STRESSED_RT_PAIR,
            "stressed_rt_arm_b_fixed": STRESSED_RT_ARM_B,
            "headroom_req_pips": {"armA": HEADROOM_REQ_A, "armB": HEADROOM_REQ_B},
            "n_floor": N_FLOOR,
            "arm_a_horizons": list(ARM_A_HORIZONS),
            "arm_b_horizon": ARM_B_HORIZON,
        },
        "notes": NOTES,
        "completeness_audit": completeness,
        "arms": arms,
        "bh_step_up": bh_detail,
        "family_verdict": family if mode == "oos" else
            f"[DRY-RUN — non-binding, explore window] {family}",
        "sensitivity_dst_ny17": dst_block,
        "sensitivity_qualify_perturbation": perturb,
        "sensitivity_spike_revert": spike_block,
        "diagnostics": {
            "per_pair_10x": pair_diag,
            "pooled_10x_weekend_block": pooled_diag,
            "annual_qualifying": annual_diag,
            "pseudo_replication": pseudo_rep,
            "mechanism_fill_dynamics": mech,
        },
    }

    # ── Dry-run reproduction check (prereg section 3 dry-run protocol) ───
    ok_all = True
    if mode == "dry-run":
        A, B = arms["A"], arms["B"]
        gA4 = A["endpoints"][4]["gross_mean"]
        gA12 = A["endpoints"][12]["gross_mean"]
        gB = B["endpoints"][4]["gross_mean"]
        mB = B["endpoints"][4]["mfe_p50"]
        rows = [
            ("arm A (EUR_USD) N", str(FROZEN_EXPLORE["armA_n"]), str(A["n"]),
             A["n"] == FROZEN_EXPLORE["armA_n"]),
            ("arm A 4h net mean (p)", f"+{FROZEN_EXPLORE['armA_net4']}",
             f"{gA4:+.3f}", abs(gA4 - FROZEN_EXPLORE["armA_net4"]) <= 0.05),
            ("arm A 12h net mean (p)", f"+{FROZEN_EXPLORE['armA_net12']}",
             f"{gA12:+.3f}", abs(gA12 - FROZEN_EXPLORE["armA_net12"]) <= 0.05),
            ("arm A 4h bootstrap p", FROZEN_EXPLORE["armA_p4"],
             fmt_p(pA4), fmt_p(pA4) == FROZEN_EXPLORE["armA_p4"]),
            ("arm A 12h bootstrap p", FROZEN_EXPLORE["armA_p12"],
             fmt_p(pA12), fmt_p(pA12) == FROZEN_EXPLORE["armA_p12"]),
            ("arm B pooled N", str(FROZEN_EXPLORE["armB_n"]), str(B["n"]),
             B["n"] == FROZEN_EXPLORE["armB_n"]),
            ("arm B distinct weekends", str(FROZEN_EXPLORE["armB_weekends"]),
             str(B["n_distinct_weekends"]),
             B["n_distinct_weekends"] == FROZEN_EXPLORE["armB_weekends"]),
            ("arm B 4h net mean (p)", f"+{FROZEN_EXPLORE['armB_net4']}",
             f"{gB:+.4f}", abs(gB - FROZEN_EXPLORE["armB_net4"]) <= 0.005),
            ("arm B 4h weekend-block p", FROZEN_EXPLORE["armB_p4"],
             fmt_p(pB4), fmt_p(pB4) == FROZEN_EXPLORE["armB_p4"]),
            ("arm B 4h MFE p50 (p)", str(FROZEN_EXPLORE["armB_mfe_p50_4h"]),
             f"{mB:.2f}", abs(mB - FROZEN_EXPLORE["armB_mfe_p50_4h"]) <= 0.05),
        ]
        ok_all = all(r[3] for r in rows)
        result["dry_run_reproduction"] = {
            "frozen_source": "prereg section 2 table / section 3 dry-run protocol",
            "rows": [{"metric": m, "frozen": f, "computed": c, "match": bool(k)}
                     for m, f, c, k in rows],
            "verdict": "DRY_RUN_PASS" if ok_all else "DRY_RUN_FAIL",
        }
        print("\n== DRY-RUN REPRODUCTION vs FROZEN EXPLORE STATS ==")
        print(f"{'metric':<28} {'frozen':>12} {'computed':>12}  match")
        for m, f, c, k in rows:
            print(f"{m:<28} {f:>12} {c:>12}  {'OK' if k else 'MISMATCH'}")
        print(f"OVERALL: {'DRY_RUN_PASS' if ok_all else 'DRY_RUN_FAIL'}")

    # ── Write output + stdout summary ────────────────────────────────────
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(result, f, indent=1, default=_json_default)
    print(f"\nwrote {out_json}")

    print("\n== ARM SUMMARY ==")
    for kind in ("A", "B"):
        a = arms[kind]
        print(f"arm {kind}: N={a['n']} (floor {a['n_floor']}) "
              f"arm_p={a['arm_p_display']} gates={a['gates']} "
              f"flips={a['knife_edge_flips']} -> {a['status_final']}")
    print(f"BH: {bh_detail}")
    print(f"FAMILY VERDICT: {result['family_verdict']}")

    return 0 if ok_all else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="weekend_gap OOS confirm (prereg-locked, single-shot OOS)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true",
                   help="explore window 2014-01-01..2021-12-31 (reproduction check)")
    g.add_argument("--oos", action="store_true",
                   help="OOS window 2022-01-01..2026-06-30 (SINGLE-SHOT verdict run)")
    args = ap.parse_args()
    return run("oos" if args.oos else "dry-run")


if __name__ == "__main__":
    sys.exit(main())
