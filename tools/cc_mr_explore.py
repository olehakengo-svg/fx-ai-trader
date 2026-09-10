#!/usr/bin/env python3
"""#21 commodity_cross_range_mr — explore harness (variant A, frozen; rule:R1).

Frozen pre-reg: knowledge-base/wiki/decisions/cc-mr-explore-prereg-2026-08-05.md
Adversarial verification (21 conditions, SSOT):
  knowledge-base/raw/analysis/wave6-cc-mr-adversarial-verification-2026-08-05.md

Estimand: exit-free fixed-horizon directional edge of D1 z-score extreme fade on
AUD_NZD / AUD_CAD / NZD_CAD. z(t) = (D1close − SMA200) / std60 on NY17:00-boundary
D1 closes reconstructed from frozen 1h bars. Onset |z|>=2.0 crossing -> fade.
Entry = close of the 19:00 America/New_York 1h bar (evening grid; Friday onsets
carry to the next trading evening). Primary outcome = fade-direction net move at
+5 evening-grid nodes; +10 = diagnostic.

Two-pass (verification §7): pass-1 exports events + MFE5 + unconditional 5d
dispersion ONLY (no net returns). Gate A/B adjudicated and committed before
pass-2 computes net5/net10/mae5 and gates C-G.

Explore window only: onset D1 date in 2014-01-01..2021-12-31. OOS (2022+) signal
measurement is refused by construction (no --window flag exists).

P-10 hygiene: only Open/High/Low/Close are ever read from the parquets
(no Volume / vwap — E12 ban until 2027-02-05); asserted at load.
E20 firewall: rate data is used exclusively for the gate-D swap COST after
outcome join (stats stage); the signal/event builder has no access to it.

Usage:
    python3 tools/cc_mr_explore.py --pass 1
    python3 tools/cc_mr_explore.py --pass 2      # refuses unless pass-1 output exists
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")
PIP = 1e-4
PAIRS = ("AUD_NZD", "AUD_CAD", "NZD_CAD")

# ---- frozen data pins (data_freeze_manifest_2026-08-05.json) ----
MANIFEST = ROOT / "knowledge-base/raw/bt-results/cc-mr/data_freeze_manifest_2026-08-05.json"
DESPIKE_CSV = ROOT / "knowledge-base/raw/bt-results/cc-mr/despike_replacements_2026-08-05.csv"
E20_CSV = ROOT / "knowledge-base/raw/bt-results/e20/e20_carry_level.csv"
OUT_DIR = ROOT / "knowledge-base/raw/bt-results/cc-mr"

# ---- frozen design parameters (NO post-hoc changes) ----
Z_TH = 2.0
SMA_N = 200
STD_N = 60                    # sample std, ddof=1, current bar excluded
ENTRY_NY_HOURS = (19, 20, 21, 22)   # per-evening candidate priority: earliest in range
ENTRY_MAX_DELAY_CAL_DAYS = 4        # entry node date > onset+4 cal days -> void
H_PRIMARY = 5                 # evening-grid nodes
H_SECONDARY = 10
EXPLORE_SIG_START = pd.Timestamp("2014-01-01")
EXPLORE_SIG_END = pd.Timestamp("2021-12-31")
# completion cap for Dec-2021 onsets; tz-naive because grid close_t values are
# UTC-naive datetime64 after DataFrame construction
HORIZON_CAP = pd.Timestamp("2022-01-31")
DESPIKE_MULT = 8.0
DESPIKE_WIN = 49              # centered rolling median, min_periods 25
STD_FLOOR = 1e-6
GAP_VOID_BDAYS = 5            # onset void if z(t-1)->z(t) spans > 5 business days

SEED_PRIMARY = 20260805
SEED_SIDE_L = 20260806
SEED_SIDE_S = 20260807
N_PERM = 10_000

STRESSED_RT = {"AUD_NZD": 3.80, "AUD_CAD": 3.70, "NZD_CAD": 3.90}   # G0 freeze 981ae119
GATE_A_MIN = {p: 10.0 * STRESSED_RT[p] for p in PAIRS}              # 38.0/37.0/39.0p
GATE_B_MIN_EVENTS = 120
GATE_B_MIN_BLOCKS = 50
GATE_G_SIDE_MIN_N = 30
GATE_E_MAX_SHARE = 0.50

# swap (verification §6.3 / condition 18) — e20 columns are base−quote %/yr
E20_FORMULA = {"AUD_NZD": ("AUD_USD", "-", "NZD_USD"),
               "AUD_CAD": ("AUD_USD", "+", "USD_CAD"),
               "NZD_CAD": ("NZD_USD", "+", "USD_CAD")}
# markup %/yr: binding = adverse end max(1.5*m_cal, 1.65) per pair (pre-reg §7)
M_ADVERSE = {"AUD_NZD": 1.65, "AUD_CAD": 1.65, "NZD_CAD": 1.73}
M_POINT = {"AUD_NZD": 1.085, "AUD_CAD": 1.075, "NZD_CAD": 1.155}
M_FAVORABLE = 0.55
# worse-of snapshot legs, %/yr signed (negative = cost); worst across valid
# (non-0/0) cc-g0-rt snapshots 2026-08-03/04
SNAP_LEG_PCT = {"AUD_NZD": {"L": 0.75, "S": -2.92},
                "AUD_CAD": {"L": 1.07, "S": -3.22},
                "NZD_CAD": {"L": -0.82, "S": -1.62}}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_frozen(pair: str, manifest: dict) -> pd.DataFrame:
    rel = f"data/cache/massive/{pair}_1h.parquet"
    fp = ROOT / rel
    assert sha256(fp) == manifest["sha256"][rel], f"sha256 mismatch: {rel}"
    df = pd.read_parquet(fp, columns=["Open", "High", "Low", "Close"])
    assert len(df) == manifest["row_counts_1h"][pair], f"row count mismatch (partial parquet?): {pair}"
    assert not any(c in df.columns for c in ("Volume", "vwap")), "P-10: volume columns must not be loaded"
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df = df.set_axis(idx).sort_index()
    assert df.index.is_monotonic_increasing and not df.index.duplicated().any(), pair
    return df


def despike_flags(df: pd.DataFrame) -> pd.Series:
    rng = df["High"] - df["Low"]
    med = rng.rolling(DESPIKE_WIN, center=True, min_periods=25).median()
    return rng > DESPIKE_MULT * med


def trading_days(df: pd.DataFrame) -> pd.DataFrame:
    """Assign each 1h bar (open-time label) to its NY17:00-boundary trading day."""
    close_t = df.index + pd.Timedelta(hours=1)
    ny = close_t.tz_convert(NY)
    dates = pd.DatetimeIndex(np.where(
        (ny.hour < 17) | ((ny.hour == 17) & (ny.minute == 0)),
        ny.normalize(), (ny + pd.Timedelta(days=1)).normalize())).tz_localize(None)
    out = df.copy()
    out["tday"] = dates
    out["close_t"] = close_t
    return out


def build_d1(bars: pd.DataFrame, flags: pd.Series, repl: dict) -> tuple[pd.DataFrame, dict]:
    """NY17-boundary D1 closes with despike replacement + degraded/void rules."""
    wk = bars["tday"].dt.dayofweek
    weekend_excluded = int((wk >= 5).sum())
    body = bars[wk < 5]
    qa = {"weekend_mapped_bars_excluded": weekend_excluded}

    rows = []
    for d, g in body.groupby("tday"):
        last = g.iloc[-1]
        last_ts = g.index[-1]
        ny_close = last["close_t"].tz_convert(NY)
        degraded = not (ny_close.hour == 17 and ny_close.minute == 0)
        void = ny_close.hour < 14  # last bar closes >3h before boundary
        close = last["Close"]
        replaced = False
        if bool(flags.loc[last_ts]):
            key = last_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            if key in repl:
                close, replaced = repl[key], True
            else:
                nf = g[~flags.reindex(g.index).values]
                if len(nf):
                    close, degraded = nf["Close"].iloc[-1], True
                else:
                    void = True
        rows.append({"tday": d, "close": close, "nbars": len(g),
                     "degraded": degraded, "void": void, "replaced": replaced})
    d1 = pd.DataFrame(rows).set_index("tday").sort_index()
    qa["degraded_close_n"] = int(d1["degraded"].sum())
    qa["void_days_n"] = int(d1["void"].sum())
    qa["despike_replaced_d1close_n"] = int(d1["replaced"].sum())
    d1 = d1[~d1["void"]]
    iso = d1.index.isocalendar()
    qa["bars_per_week_median"] = float(d1.groupby([iso.year, iso.week]).size().median())
    wd = pd.Series(d1.index.dayofweek).value_counts(normalize=True)
    qa["weekday_share_minmax"] = [round(float(wd.min()), 4), round(float(wd.max()), 4)]
    assert qa["bars_per_week_median"] == 5.0, "bars/week median != 5 (#18 trap)"
    assert wd.min() > 0.15, "weekday distribution not ~uniform (#18 trap)"
    return d1, qa


def zscore(d1: pd.DataFrame, sma_n: int = SMA_N, std_n: int = STD_N) -> pd.DataFrame:
    c = d1["close"]
    sma = c.rolling(sma_n).mean().shift(1)          # prior N bars, current excluded
    std = c.rolling(std_n).std(ddof=1).shift(1)
    z = (c - sma) / std
    z[std < STD_FLOOR] = np.nan                     # bar void
    out = d1.copy()
    out["z"] = z
    return out


def onsets(dz: pd.DataFrame, z_th: float = Z_TH) -> tuple[pd.DataFrame, dict]:
    """ONSET crossings with frozen endpoint rules (verification §4.2 / cond 10)."""
    z = dz["z"]
    counters = {"head_z_prev_undefined": 0, "sign_reversal_no_reset": 0,
                "gap_void": 0, "reentry_suppressed": 0}
    ev = []
    in_exc, exc_sign = False, 0
    prev_valid_t = None
    for t, zt in z.items():
        if np.isnan(zt):
            continue
        if prev_valid_t is None:
            counters["head_z_prev_undefined"] += 1
            prev_valid_t = t
            continue
        zp = z.loc[prev_valid_t]
        span_bd = np.busday_count(prev_valid_t.date(), t.date())
        if in_exc and abs(zt) < z_th:
            in_exc = False
        if abs(zt) >= z_th and abs(zp) < z_th:
            if span_bd > GAP_VOID_BDAYS:
                counters["gap_void"] += 1
            elif in_exc:
                counters["reentry_suppressed"] += 1
            else:
                in_exc, exc_sign = True, int(np.sign(zt))
                ev.append({"onset": t, "z": float(zt),
                           "side": "S" if zt >= z_th else "L",
                           "d1_close": float(dz.loc[t, "close"])})
        elif in_exc and abs(zt) >= z_th and int(np.sign(zt)) != exc_sign:
            counters["sign_reversal_no_reset"] += 1   # no new event (expected ~0)
        prev_valid_t = t
    return pd.DataFrame(ev), counters


def evening_grid(bars: pd.DataFrame, flags: pd.Series, repl: dict) -> pd.DataFrame:
    """One node per NY-evening: earliest bar with NY open hour in ENTRY_NY_HOURS."""
    ny_open = bars.index.tz_convert(NY)
    m = pd.Series(ny_open.hour, index=bars.index).isin(ENTRY_NY_HOURS)
    e = bars[m.values].copy()
    e["ny_date"] = pd.DatetimeIndex(ny_open[m.values]).normalize().tz_localize(None)
    e["ny_hour"] = ny_open[m.values].hour
    e = e.groupby("ny_date").head(1)
    close = e["Close"].copy()
    fl = flags.reindex(e.index)
    n_repl = 0
    for ts in e.index[fl.values]:
        key = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        if key in repl:
            close.loc[ts] = repl[key]
            n_repl += 1
        else:
            close.loc[ts] = np.nan                   # flagged, no pinned value -> void
    g = pd.DataFrame({"ts": e.index, "close_t": e["close_t"].values,
                      "price": close.values, "ny_hour": e["ny_hour"].values},
                     index=e["ny_date"].values)
    g.attrs["entry_bar_replaced_n"] = n_repl
    return g


def build_events(bars, flags, repl, dz, z_th=Z_TH, entry_mode="ny19"):
    """Join onsets to entry/exit nodes. Returns event frame WITHOUT net returns."""
    evs, counters = onsets(dz, z_th)
    grid = evening_grid(bars, flags, repl)
    if entry_mode == "utc23_nonfri":
        m = pd.Series(bars.index.hour == 23, index=bars.index)
        e = bars[m.values]
        grid = pd.DataFrame({"ts": e.index, "close_t": e["close_t"].values,
                             "price": e["Close"].values, "ny_hour": -1},
                            index=pd.DatetimeIndex(e.index.date))
    elif entry_mode == "utc0_next":
        m = pd.Series(bars.index.hour == 0, index=bars.index)
        e = bars[m.values]
        grid = pd.DataFrame({"ts": e.index, "close_t": e["close_t"].values,
                             "price": e["Close"].values, "ny_hour": -1},
                            index=pd.DatetimeIndex(e.index.date))
    rows = []
    void_entry, void_horizon = 0, 0
    gd = grid.index
    for _, ev in evs.iterrows():
        t = ev["onset"]
        if not (EXPLORE_SIG_START <= t <= EXPLORE_SIG_END):
            continue
        if entry_mode == "utc23_nonfri" and t.dayofweek == 4:
            continue                                  # knife-edge variant skips Fridays
        target = t if entry_mode != "utc0_next" else t + pd.Timedelta(days=1)
        pos = gd.searchsorted(target)                 # first node date >= onset D1 date
        if pos >= len(gd):
            void_entry += 1
            continue
        node_date = gd[pos]
        if (node_date - t).days > ENTRY_MAX_DELAY_CAL_DAYS:
            void_entry += 1
            continue
        if pos + H_SECONDARY >= len(gd):
            void_horizon += 1
            continue
        en = grid.iloc[pos]
        ex5, ex10 = grid.iloc[pos + H_PRIMARY], grid.iloc[pos + H_SECONDARY]
        if pd.Timestamp(ex5["close_t"]) > HORIZON_CAP:
            void_horizon += 1
            continue
        if np.isnan(en["price"]) or np.isnan(ex5["price"]) or np.isnan(ex10["price"]):
            void_entry += 1
            continue
        rows.append({
            "pair": None, "onset": t, "z": ev["z"], "side": ev["side"],
            "d1_close": ev["d1_close"],
            "entry_ts": en["ts"], "entry_price": float(en["price"]),
            "entry_ny_hour": int(en["ny_hour"]),
            "entry_delay_days": int((node_date - t).days),
            "exit5_ts": ex5["ts"], "exit5_price": float(ex5["price"]),
            "exit10_ts": ex10["ts"], "exit10_price": float(ex10["price"]),
            "h_cal5": (pd.Timestamp(ex5["close_t"]) - pd.Timestamp(en["close_t"])).total_seconds() / 86400.0,
            "h_cal10": (pd.Timestamp(ex10["close_t"]) - pd.Timestamp(en["close_t"])).total_seconds() / 86400.0,
        })
    df = pd.DataFrame(rows)
    counters["void_entry"] = void_entry
    counters["void_horizon"] = void_horizon
    counters["entry_bar_replaced_n"] = grid.attrs.get("entry_bar_replaced_n", 0)
    return df, counters


def add_mfe(events: pd.DataFrame, bars: pd.DataFrame, flags: pd.Series, with_mae=False):
    """Fade-direction MFE (and optionally MAE) on non-flagged 1h H/L within (entry, exit5]."""
    ok = ~flags
    mfe, mae = [], []
    for _, ev in events.iterrows():
        w = bars[(bars["close_t"] > pd.Timestamp(ev["entry_ts"]) + pd.Timedelta(hours=1))
                 & (bars["close_t"] <= pd.Timestamp(ev["exit5_ts"]) + pd.Timedelta(hours=1))]
        w = w[ok.reindex(w.index).values]
        if ev["side"] == "S":
            mfe.append((ev["entry_price"] - w["Low"].min()) / PIP)
            mae.append((w["High"].max() - ev["entry_price"]) / PIP)
        else:
            mfe.append((w["High"].max() - ev["entry_price"]) / PIP)
            mae.append((ev["entry_price"] - w["Low"].min()) / PIP)
    events = events.copy()
    events["mfe5"] = mfe
    if with_mae:
        events["mae5"] = mae
    return events


def block_id(ts: pd.Timestamp) -> str:
    iso = ts.isocalendar()
    return f"{iso.year}-B{(iso.week + 1) // 2:02d}"   # fixed 2-ISO-week [2k-1, 2k]


def block_perm_p(vals: np.ndarray, blocks: np.ndarray, seed: int, against=False):
    """One-sided block sign-flip permutation, p=(1+#{perm>=obs})/(1+B)."""
    obs = vals.mean()
    uniq = np.unique(blocks)
    bidx = {b: i for i, b in enumerate(uniq)}
    bi = np.array([bidx[b] for b in blocks])
    rng = np.random.default_rng(seed)
    flips = rng.choice([-1.0, 1.0], size=(N_PERM, len(uniq)))
    sums = np.zeros((N_PERM,))
    for i in range(len(uniq)):
        sums += flips[:, i] * vals[bi == i].sum()
    perm_means = sums / len(vals)
    if against:
        p = (1 + int((perm_means <= obs).sum())) / (1 + N_PERM)
    else:
        p = (1 + int((perm_means >= obs).sum())) / (1 + N_PERM)
    return float(obs), float(p), len(uniq)


def swap_pips(events: pd.DataFrame, e20: pd.DataFrame, markup: dict) -> np.ndarray:
    """Per-event per-side accrual, worse-of(e20-derived, snapshot leg). Negative = cost."""
    out = np.zeros(len(events))
    for i, (_, ev) in enumerate(events.iterrows()):
        pair = ev["pair"]
        a, op, b = E20_FORMULA[pair]
        row = e20[e20["date"] <= pd.Timestamp(ev["entry_ts"]).tz_localize(None)].iloc[-1]
        d = row[a] - row[b] if op == "-" else row[a] + row[b]
        direction = 1.0 if ev["side"] == "L" else -1.0
        e20_leg = direction * d - markup[pair]
        leg = min(e20_leg, SNAP_LEG_PCT[pair][ev["side"]])
        out[i] = (leg / 100.0) * (ev["h_cal5"] / 365.0) * ev["entry_price"] / PIP
    return out


def load_all():
    manifest = json.loads(MANIFEST.read_text())
    repl_df = pd.read_csv(DESPIKE_CSV)
    repl = {f"{r.pair}|{r.ts_utc}": float(r.oanda_mid_close) for r in repl_df.itertuples()}
    data = {}
    for pair in PAIRS:
        df = load_frozen(pair, manifest)
        bars = trading_days(df)
        flags = despike_flags(df)
        prepl = {k.split("|")[1]: v for k, v in repl.items() if k.startswith(pair)}
        d1, qa = build_d1(bars, flags, prepl)
        dz = zscore(d1)
        data[pair] = {"bars": bars, "flags": flags, "repl": prepl, "d1": d1, "dz": dz, "qa": qa}
    return data


def triangle_qa(data) -> dict:
    c = pd.DataFrame({p: data[p]["d1"]["close"] for p in PAIRS}).dropna()
    c = c.loc["2014-01-01":"2021-12-31"]
    r = (np.log(c["AUD_CAD"]) - np.log(c["AUD_NZD"]) - np.log(c["NZD_CAD"])).abs()
    return {"n": len(r), "p50": float(r.quantile(.5)), "p99": float(r.quantile(.99)),
            "max": float(r.max())}


def run_pass1() -> int:
    data = load_all()
    all_ev, counters, qa = [], {}, {"triangle_residual_d1": triangle_qa(data)}
    disp = {}
    for pair in PAIRS:
        d = data[pair]
        ev, cnt = build_events(d["bars"], d["flags"], d["repl"], d["dz"])
        ev["pair"] = pair
        ev = add_mfe(ev, d["bars"], d["flags"])
        all_ev.append(ev)
        counters[pair] = cnt
        qa[pair] = d["qa"]
        # unconditional 5-node dispersion (event-independent, despiked closes)
        c = d["dz"].loc["2014-01-01":"2021-12-31", "close"]
        d5 = (c.shift(-H_PRIMARY) - c).dropna() / PIP
        disp[pair] = {"robust_sd_5d_pips": float((d5 - d5.median()).abs().median() / 0.6745),
                      "n": len(d5)}
    ev = pd.concat(all_ev, ignore_index=True)
    ev["block"] = [block_id(pd.Timestamp(t)) for t in ev["onset"]]
    ev["year"] = [pd.Timestamp(t).year for t in ev["onset"]]

    gate_a = {}
    for pair in PAIRS:
        m = ev[ev["pair"] == pair]["mfe5"]
        p50 = float(m.median()) if len(m) else float("nan")
        gate_a[pair] = {"n": int(len(m)), "mfe5_p50": round(p50, 2),
                        "min_required": GATE_A_MIN[pair],
                        "pass": bool(len(m) and p50 >= GATE_A_MIN[pair])}
    survivors = [p for p in PAIRS if gate_a[p]["pass"]]
    sv = ev[ev["pair"].isin(survivors)]
    n_events, n_blocks = len(sv), sv["block"].nunique()
    pooled_sd = float(np.mean([disp[p]["robust_sd_5d_pips"] for p in (survivors or PAIRS)]))
    mde = 2.487 * pooled_sd / max(np.sqrt(n_events), 1e-9) if n_events else None
    out = {
        "pass": 1, "date": "2026-08-05", "ledger": 21,
        "gate_A": gate_a, "survivors": survivors,
        "family_kill_lt2_survivors": len(survivors) < 2,
        "gate_B": {"events": n_events, "blocks": n_blocks,
                   "min_events": GATE_B_MIN_EVENTS, "min_blocks": GATE_B_MIN_BLOCKS,
                   "pass": bool(n_events >= GATE_B_MIN_EVENTS and n_blocks >= GATE_B_MIN_BLOCKS)},
        "unconditional_dispersion": disp,
        "mde_recomputed_pips": round(mde, 2) if mde else None,
        "per_pair_side_year": {p: {"by_side": ev[ev["pair"] == p]["side"].value_counts().to_dict(),
                                   "by_year": ev[ev["pair"] == p]["year"].value_counts().sort_index().to_dict()}
                               for p in PAIRS},
        "counters": counters, "qa": qa,
        "entry_hour_dist": ev["entry_ny_hour"].value_counts().to_dict(),
        "entry_delay_dist": ev["entry_delay_days"].value_counts().sort_index().to_dict(),
    }
    cols1 = ["pair", "onset", "side", "z", "d1_close", "entry_ts", "entry_price",
             "entry_ny_hour", "entry_delay_days", "exit5_ts", "exit10_ts",
             "h_cal5", "h_cal10", "mfe5", "block", "year"]
    ev[cols1].to_csv(OUT_DIR / "cc-mr-pass1-events-2026-08-05.csv", index=False)
    (OUT_DIR / "cc-mr-pass1-2026-08-05.json").write_text(
        json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: out[k] for k in ("gate_A", "survivors", "gate_B",
                                          "mde_recomputed_pips")}, indent=1, default=str))
    return 0


def run_pass2() -> int:
    p1p = OUT_DIR / "cc-mr-pass1-2026-08-05.json"
    assert p1p.exists(), "pass-1 output missing — two-pass order violated"
    p1 = json.loads(p1p.read_text())
    assert not p1["family_kill_lt2_survivors"], "family KILLED at gate A"
    survivors = p1["survivors"]

    data = load_all()
    ev = pd.read_csv(OUT_DIR / "cc-mr-pass1-events-2026-08-05.csv",
                     parse_dates=["onset", "entry_ts", "exit5_ts", "exit10_ts"])
    full = []
    for pair in PAIRS:
        d = data[pair]
        e, _ = build_events(d["bars"], d["flags"], d["repl"], d["dz"])
        e["pair"] = pair
        e = add_mfe(e, d["bars"], d["flags"], with_mae=True)
        full.append(e)
    fe = pd.concat(full, ignore_index=True)
    assert len(fe) == len(ev), "pass-2 event set != committed pass-1 set"
    dirn = np.where(fe["side"] == "L", 1.0, -1.0)
    fe["net5"] = dirn * (fe["exit5_price"] - fe["entry_price"]) / PIP
    fe["net10"] = dirn * (fe["exit10_price"] - fe["entry_price"]) / PIP
    fe["block"] = [block_id(pd.Timestamp(t)) for t in fe["onset"]]
    fe["year"] = [pd.Timestamp(t).year for t in fe["onset"]]

    sv = fe[fe["pair"].isin(survivors)].reset_index(drop=True)
    vals, blocks = sv["net5"].to_numpy(), sv["block"].to_numpy()

    obs, p_c, n_blocks = block_perm_p(vals, blocks, SEED_PRIMARY)
    gate_c = {"pooled_mean_net5": round(obs, 3), "p_one_sided": p_c,
              "n_blocks": n_blocks, "pass": bool(obs > 0 and p_c < 0.05)}

    e20 = pd.read_csv(E20_CSV, parse_dates=["date"])
    res_d = {}
    for label, markup in (("adverse", M_ADVERSE), ("point", M_POINT),
                          ("favorable", {p: M_FAVORABLE for p in PAIRS})):
        sp = swap_pips(sv, e20, markup)
        rt = sv["pair"].map(STRESSED_RT).to_numpy()
        res_d[label] = round(float((vals + sp - rt).mean()), 3)
    gate_d = {"net_after_friction_swap": res_d, "pass": bool(res_d["adverse"] > 0)}

    bsum = pd.Series(vals).groupby(pd.Series(blocks)).sum()
    share = float(bsum.abs().max() / bsum.abs().sum()) if bsum.abs().sum() > 0 else 1.0
    gate_e = {"max_block_share": round(share, 4), "pass": bool(share <= GATE_E_MAX_SHARE)}

    yr = sv.groupby("year")["net5"].mean()
    years = list(range(2014, 2022))
    pos_years = int(sum(yr.get(y, np.nan) > 0 for y in years))
    loyo = {y: float(sv[sv["year"] != y]["net5"].mean()) for y in years}
    gate_f = {"yearly_mean": {int(k): round(float(v), 3) for k, v in yr.items()},
              "positive_years": pos_years, "loyo_all_positive": bool(all(v > 0 for v in loyo.values())),
              "loyo": {k: round(v, 3) for k, v in loyo.items()},
              "desync_2014_15_mean": round(float(sv[sv["year"].isin([2014, 2015])]["net5"].mean()), 3)
              if len(sv[sv["year"].isin([2014, 2015])]) else None,
              "pass": bool(pos_years >= 6 and all(v > 0 for v in loyo.values()))}

    per_pair_mean = sv.groupby("pair")["net5"].mean()
    pos_pairs = int((per_pair_mean > 0).sum())
    side_res = {}
    side_kill = False
    for side, seed in (("L", SEED_SIDE_L), ("S", SEED_SIDE_S)):
        ss = sv[sv["side"] == side]
        if len(ss) < GATE_G_SIDE_MIN_N:
            side_res[side] = {"n": int(len(ss)), "binding": False, "flag": "N<30 — kill cannot fire"}
            continue
        so, sp_, sb = block_perm_p(ss["net5"].to_numpy(), ss["block"].to_numpy(), seed, against=True)
        kill = bool(so < 0 and sp_ < 0.10)
        side_res[side] = {"n": int(len(ss)), "mean": round(so, 3),
                          "p_against": sp_, "blocks": sb, "kill": kill}
        side_kill = side_kill or kill
    gate_g = {"per_pair_mean": {k: round(float(v), 3) for k, v in per_pair_mean.items()},
              "positive_pair_share": f"{pos_pairs}/{len(per_pair_mean)}",
              "sides": side_res,
              "pass": bool(pos_pairs / max(len(per_pair_mean), 1) >= 2 / 3 and not side_kill)}

    # diagnostics (non-binding)
    diag = {}
    ic = {}
    for pair in PAIRS:
        dz = data[pair]["dz"].loc["2014-01-01":"2021-12-31"]
        fwd = (dz["close"].shift(-H_PRIMARY) - dz["close"]) / PIP
        m = dz["z"].notna() & fwd.notna()
        ic[pair] = round(float(dz["z"][m].corr(fwd[m], method="spearman")), 4)
    diag["spearman_ic_z_fwd5d"] = ic
    keep, open_until = [], {}
    for i, ev_ in sv.sort_values("onset").iterrows():
        ou = open_until.get(ev_["pair"])
        if ou is not None and pd.Timestamp(ev_["onset"]) <= ou:
            continue
        keep.append(i)
        ex = pd.Timestamp(ev_["exit5_ts"])
        open_until[ev_["pair"]] = ex.tz_localize(None) if ex.tzinfo else ex
    diag["skip_version"] = {"n": len(keep), "mean_net5": round(float(sv.loc[keep, "net5"].mean()), 3)}
    ov = 0
    for pair in survivors:
        pe = sv[sv["pair"] == pair].sort_values("onset")
        ends = pe["exit5_ts"].shift(1)
        ov += int((pd.to_datetime(pe["onset"]).values[1:]
                   <= pd.to_datetime(ends).values[1:]).sum())
    diag["overlap_share"] = round(ov / max(len(sv), 1), 4)
    wk = pd.to_datetime(sv["onset"]).dt.isocalendar()
    wkkey = wk.year.astype(str) + "-" + wk.week.astype(str)
    diag["cofire_week_share"] = round(float((sv.groupby(wkkey)["pair"].nunique() >= 2).mean()), 4)
    d1c = {}
    for pair in survivors:
        dz = data[pair]["dz"]
        pe = sv[sv["pair"] == pair]
        c = dz["close"]
        idxer = c.index.get_indexer(pd.to_datetime(pe["onset"]))
        nxt = np.clip(idxer + H_PRIMARY, 0, len(c) - 1)
        dn = np.where(pe["side"] == "L", 1.0, -1.0)
        d1c[pair] = round(float(np.mean(dn * (c.values[nxt] - c.values[idxer]) / PIP)), 3)
    diag["d1_close_to_close_mean"] = d1c
    diag["mae5_p50"] = round(float(sv["mae5"].median()), 2)

    binding = {"A": True, "B": p1["gate_B"]["pass"], "C": gate_c["pass"],
               "D": gate_d["pass"], "E": gate_e["pass"], "F": gate_f["pass"],
               "G": gate_g["pass"]}
    if not p1["gate_B"]["pass"]:
        verdict = "UNDERPOWERED"
    elif all(binding.values()):
        verdict = "PASS"
    else:
        verdict = "FAIL"

    knife = None
    if verdict == "PASS":
        knife = {}
        for tag, kw in [("z1.75", {"z_th": 1.75}), ("z2.25", {"z_th": 2.25}),
                        ("sma160", {"sma_n": 160}), ("sma240", {"sma_n": 240}),
                        ("std45", {"std_n": 45}), ("std75", {"std_n": 75}),
                        ("entry_utc23_nonfri", {"entry_mode": "utc23_nonfri"}),
                        ("entry_utc0_next", {"entry_mode": "utc0_next"}),
                        ("block_1w", {"block_mode": "1w"})]:
            evs = []
            for pair in survivors:
                d = data[pair]
                dzk = zscore(d["d1"], kw.get("sma_n", SMA_N), kw.get("std_n", STD_N)) \
                    if ("sma_n" in kw or "std_n" in kw) else d["dz"]
                ek, _ = build_events(d["bars"], d["flags"], d["repl"], dzk,
                                     z_th=kw.get("z_th", Z_TH),
                                     entry_mode=kw.get("entry_mode", "ny19"))
                ek["pair"] = pair
                evs.append(ek)
            ke = pd.concat(evs, ignore_index=True)
            dk = np.where(ke["side"] == "L", 1.0, -1.0)
            ke["net5"] = dk * (ke["exit5_price"] - ke["entry_price"]) / PIP
            if kw.get("block_mode") == "1w":
                kb = [f"{pd.Timestamp(t).isocalendar().year}-W{pd.Timestamp(t).isocalendar().week:02d}"
                      for t in ke["onset"]]
                ko, kp, _ = block_perm_p(ke["net5"].to_numpy(), np.array(kb), SEED_PRIMARY)
            else:
                ko = float(ke["net5"].mean())
            knife[tag] = {"n": int(len(ke)), "mean_net5": round(ko, 3), "sign_ok": bool(ko > 0)}
        if not all(v["sign_ok"] for v in knife.values()):
            verdict = "FAIL"

    out = {"pass": 2, "date": "2026-08-05", "ledger": 21, "survivors": survivors,
           "gate_C": gate_c, "gate_D": gate_d, "gate_E": gate_e, "gate_F": gate_f,
           "gate_G": gate_g, "binding": binding, "knife_edge": knife,
           "diagnostics": diag, "verdict": verdict}
    cols2 = ["pair", "onset", "side", "z", "entry_ts", "entry_price", "exit5_price",
             "exit10_price", "h_cal5", "net5", "net10", "mfe5", "mae5", "block", "year"]
    fe[cols2].to_csv(OUT_DIR / "cc-mr-pass2-events-2026-08-05.csv", index=False)
    (OUT_DIR / "cc-mr-pass2-2026-08-05.json").write_text(
        json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pass", dest="stage", type=int, required=True, choices=(1, 2))
    args = ap.parse_args(argv)
    return run_pass1() if args.stage == 1 else run_pass2()


if __name__ == "__main__":
    sys.exit(main())
