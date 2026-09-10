#!/usr/bin/env python3
"""E22 fx_variance_risk_premium explore harness (ledger #24).

Pre-reg: knowledge-base/wiki/decisions/e22-vrp-explore-prereg-2026-08-17.md (FROZEN)
Seed: 20260817. Two-pass discipline:
  --mode manifest  : write sha256/rowcount data-freeze manifest (before freeze commit)
  --mode pass1     : signal panel + unconditional fwd dispersion + gates A/B (NO signal x outcome join)
  --mode pass2     : IC + gates C-G + knife-edge + verdict (requires committed pass1 artifact)
  --mode oos       : single-touch OOS (requires pass2 explore PASS + --unlock-oos + extended swap panel)

P-10 hygiene: parquet is loaded with columns=["Close"] only (Volume/vwap never read).
No module-top side effects (KB lesson).
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

SEED_PRIMARY = 20260817
SEED_BLOCKFLIP = 20260818
SEED_OOS = 20260819
B_PERM = 10_000
MIN_SHIFT = 42

RV_WIN = 21
HORIZON = 21
RV_SPAN_GUARD_CAL = 45          # oldest return within 45 cal days (scaled for knife-edge windows)
FWD_SPAN_GUARD_CAL = 45
RET_GAP_GUARD_CAL = 7           # consecutive valid D1 span > 7 cal days -> return void
EVZ_STALENESS_MAX = 3           # cal days
DAY_VOID_NY_HOUR = 14           # last bar close-time earlier than 14:00 NY -> day void
ABS_RET_ASSERT = 0.05           # |daily log return| > 5% -> hard stop (manual inspection)

EXPLORE_START, EXPLORE_END = "2014-01-01", "2021-12-31"
OOS_START, OOS_END = "2022-01-01", "2025-03-11"

RT_STRESSED = 4.0               # pips (binding)
RT_POINT = 2.0                  # pips (sensitivity)
MARKUP_ADVERSE = 1.65           # %/yr (binding)
MARKUP_POINT = 1.0              # %/yr (sensitivity)

GATE_A_FLOOR = 10.0 * RT_STRESSED          # 40.0p unconditional median |fwd21 move|
GATE_B_N_MIN = 1500
GATE_B_NONOVERLAP_MIN = 70
GATE_F_ANNUAL_MIN = 6                       # of 8 explore years
OOS_N_MIN = 600
OOS_NONOVERLAP_MIN = 28
OOS_ECON_FLOOR = 5.0                        # pips, extreme-tercile gross mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVZ_CSV = os.path.join(ROOT, "data/external/vrp/EVZCLS.csv")
PX_PARQUET = os.path.join(ROOT, "data/cache/massive/EUR_USD_15m.parquet")
SWAP_CSV = os.path.join(ROOT, "knowledge-base/raw/bt-results/e20/e20_carry_level.csv")
SWAP_CSV_OOS_EXT = os.path.join(ROOT, "knowledge-base/raw/bt-results/e20/e20_carry_level_ext_2026-08.csv")
OUT_DIR = os.path.join(ROOT, "knowledge-base/raw/bt-results/e22")
MANIFEST = os.path.join(OUT_DIR, "data_freeze_manifest_2026-08-17.json")
PASS1_JSON = os.path.join(OUT_DIR, "pass1-2026-08-17.json")
PASS1_CSV = os.path.join(OUT_DIR, "pass1-signal-panel-2026-08-17.csv")
PASS2_JSON = os.path.join(OUT_DIR, "pass2-2026-08-17.json")
OOS_JSON = os.path.join(OUT_DIR, "oos-2026-08-17.json")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest():
    os.makedirs(OUT_DIR, exist_ok=True)
    entries = {}
    for path in (EVZ_CSV, PX_PARQUET, SWAP_CSV):
        rel = os.path.relpath(path, ROOT)
        if path.endswith(".parquet"):
            nrows = len(pd.read_parquet(path, columns=["Close"]))
        else:
            nrows = sum(1 for _ in open(path)) - 1
        entries[rel] = {"sha256": sha256_of(path), "rows": nrows}
    manifest = {"family": "e22_fx_variance_risk_premium", "frozen": "2026-08-17",
                "seed": SEED_PRIMARY, "files": entries}
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest written: {MANIFEST}")
    for k, v in entries.items():
        print(f"  {k}: rows={v['rows']} sha256={v['sha256'][:16]}...")


def assert_manifest():
    with open(MANIFEST) as f:
        manifest = json.load(f)
    for rel, meta in manifest["files"].items():
        path = os.path.join(ROOT, rel)
        actual = sha256_of(path)
        assert actual == meta["sha256"], f"sha256 drift: {rel} (frozen {meta['sha256'][:12]} != actual {actual[:12]})"
        if path.endswith(".parquet"):
            nrows = len(pd.read_parquet(path, columns=["Close"]))
        else:
            nrows = sum(1 for _ in open(path)) - 1
        assert nrows == meta["rows"], f"rowcount drift: {rel} (frozen {meta['rows']} != actual {nrows})"
    return manifest


def load_evz():
    ev = pd.read_csv(EVZ_CSV)
    assert list(ev.columns) == ["observation_date", "EVZCLS"], f"unexpected EVZ columns: {list(ev.columns)}"
    ev.columns = ["date", "evz"]
    ev["date"] = pd.to_datetime(ev["date"])
    ev["evz"] = pd.to_numeric(ev["evz"], errors="coerce")
    ev = ev.dropna(subset=["evz"]).sort_values("date").reset_index(drop=True)
    assert ev["date"].is_monotonic_increasing and not ev["date"].duplicated().any()
    assert (ev["date"].dt.dayofweek < 5).all(), "EVZ weekend prints found"
    assert 3.0 < ev["evz"].min() and ev["evz"].max() < 40.0, "EVZ units out of vol-point range"
    # stale-print run labeling (for knife-edge (v); NOT used for exclusion in primary)
    run_id = (ev["evz"] != ev["evz"].shift()).cumsum()
    run_len = run_id.map(run_id.value_counts())
    ev["stale_run3"] = (run_len >= 3).values
    return ev


def build_d1():
    """D1 closes via NY17 boundary from 15m open-labeled UTC bars. P-10: Close column only."""
    px = pd.read_parquet(PX_PARQUET, columns=["Close"])
    assert list(px.columns) == ["Close"], "P-10 violation: extra columns loaded"
    idx = px.index if px.index.tz is not None else px.index.tz_localize("UTC")
    close_time = idx + pd.Timedelta(minutes=15)  # open-label convention (verified in pre-reg sec2)
    ny = close_time.tz_convert("America/New_York")
    ny_date = pd.Series(pd.to_datetime(ny.date))
    after_close = (ny.hour > 17) | ((ny.hour == 17) & (ny.minute > 0))
    tday = ny_date + pd.to_timedelta(after_close.astype(int), unit="D")
    df = pd.DataFrame({"tday": tday.values, "close": px["Close"].values,
                       "ny_hour": ny.hour, "ny_minute": ny.minute})
    weekend_mask = pd.to_datetime(df["tday"]).dt.dayofweek >= 5
    n_weekend_bars = int(weekend_mask.sum())
    df = df[~weekend_mask]
    grp = df.groupby("tday")
    d1 = grp.agg(close=("close", "last"), nbars=("close", "size"),
                 last_hour=("ny_hour", "last"), last_minute=("ny_minute", "last"))
    d1.index = pd.to_datetime(d1.index)
    # day void: last bar close-time earlier than 14:00 NY
    void_mask = d1["last_hour"] < DAY_VOID_NY_HOUR
    n_void_days = int(void_mask.sum())
    d1 = d1[~void_mask]
    return d1[["close"]], {"weekend_label_bars_dropped": n_weekend_bars, "void_days": n_void_days,
                           "d1_days": len(d1)}


def build_returns(d1):
    dates = d1.index
    close = d1["close"].to_numpy()
    r = np.log(close[1:] / close[:-1])
    span_cal = (dates[1:] - dates[:-1]).days
    void = span_cal > RET_GAP_GUARD_CAL
    n_ret_void = int(void.sum())
    assert np.nanmax(np.abs(r[~void])) < ABS_RET_ASSERT, \
        f"|daily return| >= {ABS_RET_ASSERT} found — manual inspection required (silent handling banned)"
    ret = pd.DataFrame({"date": dates[1:], "r": r, "void": void}).set_index("date")
    return ret, n_ret_void


def build_signal_panel(d1, ret, ev, win_start, win_end, rv_win=RV_WIN):
    """Signal rows for D1 days in [win_start, win_end]. No forward-return join here."""
    span_guard = RV_SPAN_GUARD_CAL * rv_win / RV_WIN
    r_valid_dates = ret.index[~ret["void"]]
    r_valid = ret.loc[r_valid_dates, "r"].to_numpy()
    rows = []
    census = {"rv_void": 0, "evz_stale_void": 0, "evz_missing_void": 0}
    ev_dates = ev["date"].to_numpy()
    ev_vals = ev["evz"].to_numpy()
    ev_stale = ev["stale_run3"].to_numpy()
    date_to_pos = {d: i for i, d in enumerate(r_valid_dates)}
    for t in d1.index:
        if not (pd.Timestamp(win_start) <= t <= pd.Timestamp(win_end)):
            continue
        pos = date_to_pos.get(t)
        if pos is None or pos + 1 < rv_win:
            census["rv_void"] += 1
            continue
        window_dates = r_valid_dates[pos - rv_win + 1: pos + 1]
        if (t - window_dates[0]).days > span_guard:
            census["rv_void"] += 1
            continue
        rv = 100.0 * np.sqrt(252.0 * np.mean(r_valid[pos - rv_win + 1: pos + 1] ** 2))
        k = np.searchsorted(ev_dates, np.datetime64(t), side="right") - 1
        if k < 0:
            census["evz_missing_void"] += 1
            continue
        staleness = (t - pd.Timestamp(ev_dates[k])).days
        if staleness > EVZ_STALENESS_MAX:
            census["evz_stale_void"] += 1
            continue
        rows.append({"date": t, "evz": ev_vals[k], "evz_staleness": staleness,
                     "evz_stale_run3": bool(ev_stale[k]), "rv21": rv, "vrp": ev_vals[k] - rv,
                     "close": d1.loc[t, "close"]})
    panel = pd.DataFrame(rows).set_index("date")
    return panel, census


def join_forward(panel, d1):
    """Forward +HORIZON valid-D1 return join. pass-2 / gate-A internals only."""
    dates = d1.index
    close = d1["close"].to_numpy()
    date_to_pos = {d: i for i, d in enumerate(dates)}
    fwd_log, fwd_pips, h_cal, keep = [], [], [], []
    n_fwd_void = 0
    for t in panel.index:
        i = date_to_pos[t]
        j = i + HORIZON
        if j >= len(dates) or (dates[j] - t).days > FWD_SPAN_GUARD_CAL:
            n_fwd_void += 1
            keep.append(False)
            fwd_log.append(np.nan); fwd_pips.append(np.nan); h_cal.append(np.nan)
            continue
        keep.append(True)
        fwd_log.append(np.log(close[j] / close[i]))
        fwd_pips.append((close[j] - close[i]) / 1e-4)
        h_cal.append((dates[j] - t).days)
    out = panel.copy()
    out["fwd_log"] = fwd_log
    out["fwd_pips"] = fwd_pips
    out["h_cal"] = h_cal
    out = out[np.array(keep)]
    return out, n_fwd_void


def load_swap(oos=False):
    path = SWAP_CSV_OOS_EXT if oos else SWAP_CSV
    if oos:
        # verification condition 4: extension file must be FULL-coverage
        # (2013-01..>=2025-04), equal to the frozen panel on overlapping dates,
        # and pinned by a committed manifest addendum before OOS touch.
        assert os.path.exists(path), \
            "OOS swap panel extension missing — run e20_rates_ingest BIS extension before OOS touch (pre-reg sec7)"
    sw = pd.read_csv(path, parse_dates=["date"])[["date", "EUR_USD"]].dropna()
    series = sw.set_index("date")["EUR_USD"].sort_index()
    if oos:
        assert series.index.min() <= pd.Timestamp("2013-01-02"), "ext swap panel must be full-coverage from 2013-01"
        assert series.index.max() >= pd.Timestamp("2025-04-30"), "ext swap panel must cover through 2025-04"
        frozen = pd.read_csv(SWAP_CSV, parse_dates=["date"])[["date", "EUR_USD"]].dropna()
        frozen = frozen.set_index("date")["EUR_USD"].sort_index()
        common = series.index.intersection(frozen.index)
        assert np.allclose(series.loc[common], frozen.loc[common]), \
            "ext swap panel diverges from frozen panel on overlapping dates"
        addendum = os.path.join(OUT_DIR, "oos_swap_manifest_addendum.json")
        assert os.path.exists(addendum), "OOS swap manifest addendum missing (condition 4-iii)"
        with open(addendum) as f:
            add = json.load(f)
        assert add["sha256"] == sha256_of(path), "OOS swap ext sha256 drift vs committed addendum"
        _assert_committed(addendum)
    return series


def _assert_committed(path):
    """Assert a file is committed in git HEAD and has no uncommitted changes."""
    import subprocess
    rel = os.path.relpath(path, ROOT)
    r = subprocess.run(["git", "-C", ROOT, "cat-file", "-e", f"HEAD:{rel}"],
                       capture_output=True)
    assert r.returncode == 0, f"{rel} is not committed in git HEAD (freeze discipline)"
    r2 = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", rel],
                        capture_output=True, text=True)
    assert r2.stdout.strip() == "", f"{rel} has uncommitted changes (freeze discipline)"


def swap_pips_per_obs(joined, swap_series, markup):
    d_asof = swap_series.reindex(swap_series.index.union(joined.index)).ffill().reindex(joined.index)
    assert not d_asof.isna().any(), "swap panel does not cover all signal dates"
    out = {}
    for side in (+1, -1):
        rate_used = side * d_asof.to_numpy() - markup
        out[side] = (rate_used / 100.0) * (joined["h_cal"].to_numpy() / 365.0) \
            * joined["close"].to_numpy() / 1e-4
    return out


def rank_z(x):
    ranks = pd.Series(x).rank(method="average").to_numpy()
    return (ranks - ranks.mean()) / ranks.std(ddof=0)


def spearman(x, y):
    return float(np.mean(rank_z(x) * rank_z(y)))


def circular_shift_p(sig, ret, rng, one_sided_g=None, b=B_PERM):
    zs, zr = rank_z(sig), rank_z(ret)
    n = len(zs)
    assert n > 2 * MIN_SHIFT, "series too short for circular shift"
    obs = float(np.mean(zs * zr))
    shifts = rng.integers(MIN_SHIFT, n - MIN_SHIFT + 1, size=b)
    exceed = 0
    for k in shifts:
        icp = float(np.mean(np.roll(zs, int(k)) * zr))
        if one_sided_g is None:
            exceed += (abs(icp) >= abs(obs))
        else:
            exceed += (one_sided_g * icp >= one_sided_g * obs)
    return obs, (1 + exceed) / (1 + b)


def block_signflip_p(sig, ret, rng, b=B_PERM, block=42):
    zs, zr = rank_z(sig), rank_z(ret)
    n = len(zs)
    obs = float(np.mean(zs * zr))
    nblocks = int(np.ceil(n / block))
    ids = np.repeat(np.arange(nblocks), block)[:n]
    exceed = 0
    for _ in range(b):
        flips = rng.choice([-1.0, 1.0], size=nblocks)[ids]
        icp = float(np.mean(zs * (zr * flips)))
        exceed += (abs(icp) >= abs(obs))
    return obs, (1 + exceed) / (1 + b)


def run_pass1():
    manifest = assert_manifest()
    ev = load_evz()
    d1, d1_census = build_d1()
    ret, n_ret_void = build_returns(d1)
    panel, census = build_signal_panel(d1, ret, ev, EXPLORE_START, EXPLORE_END)
    joined, n_fwd_void = join_forward(panel, d1)
    n = len(joined)
    # unconditional dispersion (signal-independent; per-day values NOT exported)
    absmove = np.abs(joined["fwd_pips"].to_numpy())
    sd_move = float(joined["fwd_pips"].std(ddof=1))
    med_absmove = float(np.median(absmove))
    gate_a = med_absmove >= GATE_A_FLOOR
    nonoverlap = n // HORIZON
    gate_b = (n >= GATE_B_N_MIN) and (nonoverlap >= GATE_B_NONOVERLAP_MIN)
    mde_ic = 2.80 / np.sqrt(nonoverlap)
    mde_mean_cluster = 2.487 * sd_move / np.sqrt(nonoverlap)
    # condition 10: VRP ACF re-measurement (signal side only)
    v = joined["vrp"].to_numpy()
    vrp_acf = {f"lag{lag}": float(np.corrcoef(v[:-lag], v[lag:])[0, 1]) for lag in (5, 10, 21, 42)}
    out = {
        "mode": "pass1", "frozen_manifest": manifest["files"],
        "d1_census": d1_census, "returns_void": n_ret_void, "signal_census": census,
        "fwd_void": n_fwd_void, "n_signal_days": n,
        "n_by_year": {str(y): int(c) for y, c in joined.index.year.value_counts().sort_index().items()},
        "evz_same_day_share": float((joined["evz_staleness"] == 0).mean()),
        "stale_run3_day_share": float(joined["evz_stale_run3"].mean()),
        "unconditional_fwd21": {"median_abs_move_pips": med_absmove, "sd_move_pips": sd_move,
                                "p25_abs": float(np.percentile(absmove, 25)),
                                "p75_abs": float(np.percentile(absmove, 75))},
        "gate_A": {"floor_pips": GATE_A_FLOOR, "observed_median_abs": med_absmove, "pass": bool(gate_a)},
        "gate_B": {"n": n, "n_min": GATE_B_N_MIN, "nonoverlap_windows": nonoverlap,
                   "nonoverlap_min": GATE_B_NONOVERLAP_MIN, "pass": bool(gate_b)},
        "honest_mde": {"ic_mde_at_nonoverlap": float(mde_ic),
                       "tercile_mean_mde_pips_cluster_worst": float(mde_mean_cluster)},
        "vrp_acf": vrp_acf,
        "vrp_summary": {"p5": float(joined["vrp"].quantile(0.05)), "p50": float(joined["vrp"].median()),
                        "p95": float(joined["vrp"].quantile(0.95))},
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(PASS1_JSON, "w") as f:
        json.dump(out, f, indent=2)
    # signal panel export: signal columns only (no fwd columns) — two-pass discipline
    panel[["evz", "evz_staleness", "evz_stale_run3", "rv21", "vrp"]].to_csv(PASS1_CSV)
    print(json.dumps({k: out[k] for k in ("gate_A", "gate_B", "n_signal_days", "honest_mde")}, indent=2))
    print(f"pass1 artifacts: {PASS1_JSON}, {PASS1_CSV}")
    print("NEXT: commit pass-1 artifacts, then run --mode pass2")


def gates_cdefg(joined, swap_series, label="explore", years_expected=8):
    zs = joined["vrp"].to_numpy()
    zr = joined["fwd_log"].to_numpy()
    rng = np.random.default_rng(SEED_PRIMARY)
    ic_obs, p_two = circular_shift_p(zs, zr, rng)
    g = int(np.sign(ic_obs)) or 1
    gate_c = p_two < 0.05

    # terciles (window-local)
    q1, q2 = np.quantile(zs, [1 / 3, 2 / 3])
    terc = np.where(zs <= q1, 0, np.where(zs <= q2, 1, 2))
    move = joined["fwd_pips"].to_numpy()
    swap_adv = swap_pips_per_obs(joined, swap_series, MARKUP_ADVERSE)
    swap_pt = swap_pips_per_obs(joined, swap_series, MARKUP_POINT)
    extreme = terc != 1
    dir_obs = np.where(terc == 2, g, -g)[extreme]
    move_x = move[extreme]
    gross = dir_obs * move_x
    side_arr = dir_obs
    swap_x_adv = np.where(side_arr == 1, swap_adv[1][extreme], swap_adv[-1][extreme])
    swap_x_pt = np.where(side_arr == 1, swap_pt[1][extreme], swap_pt[-1][extreme])
    net_adv = gross + swap_x_adv - RT_STRESSED
    net_pt = gross + swap_x_pt - RT_POINT
    net_rt6 = gross + swap_x_adv - 6.0  # condition 8: 3x RT sensitivity (non-binding)
    gate_d = float(net_adv.mean()) > 0

    years = joined.index.year.to_numpy()
    years_x = years[extreme]
    s_y = {int(y): float(gross[years_x == y].sum()) for y in np.unique(years_x)}
    denom = sum(abs(v) for v in s_y.values())
    conc = max(abs(v) for v in s_y.values()) / denom if denom > 0 else 1.0
    gate_e = conc <= 0.50

    annual_ic = {int(y): spearman(zs[years == y], zr[years == y]) for y in np.unique(years)}
    n_sign_ok = sum(1 for v in annual_ic.values() if np.sign(v) == g)
    loyo = {int(y): spearman(zs[years != y], zr[years != y]) for y in np.unique(years)}
    loyo_ok = sum(1 for v in loyo.values() if np.sign(v) == g)
    gate_f = (n_sign_ok >= GATE_F_ANNUAL_MIN) and (loyo_ok == len(loyo))

    terc_means = [float(move[terc == k].mean()) for k in (0, 1, 2)]
    diffs = np.diff(terc_means) * g
    violations = int((diffs < 0).sum())
    spread_ok = np.sign(terc_means[2] - terc_means[0]) == g
    gate_g = (violations <= 1) and spread_ok

    return {
        "ic_obs": ic_obs, "p_two_sided": p_two, "g": g,
        "gate_C": {"pass": bool(gate_c), "p": p_two},
        "gate_D": {"pass": bool(gate_d), "mean_net_adverse": float(net_adv.mean()),
                   "mean_net_point": float(net_pt.mean()), "mean_gross": float(gross.mean()),
                   "mean_swap_adverse": float(swap_x_adv.mean()), "n_extreme": int(extreme.sum()),
                   "mean_net_rt6_sensitivity_nonbinding": float(net_rt6.mean())},
        "gate_E": {"pass": bool(gate_e), "max_year_share": float(conc), "S_y": s_y},
        "gate_F": {"pass": bool(gate_f), "annual_ic": annual_ic, "annual_sign_ok": n_sign_ok,
                   "of": len(annual_ic), "loyo_ic": loyo, "loyo_sign_ok": loyo_ok},
        "gate_G": {"pass": bool(gate_g), "tercile_mean_fwd_pips": terc_means,
                   "adjacent_violations": violations, "spread_sign_ok": bool(spread_ok)},
    }


def run_pass2():
    assert os.path.exists(PASS1_JSON), "pass1 artifact missing — two-pass order violated"
    with open(PASS1_JSON) as f:
        p1 = json.load(f)
    assert p1["gate_A"]["pass"] and p1["gate_B"]["pass"], \
        "pass2 locked: gate A/B did not pass (KILL/UNDERPOWERED at pass1)"
    assert_manifest()
    ev = load_evz()
    d1, _ = build_d1()
    ret, _ = build_returns(d1)
    panel, _ = build_signal_panel(d1, ret, ev, EXPLORE_START, EXPLORE_END)
    joined, _ = join_forward(panel, d1)
    assert len(joined) == p1["n_signal_days"], "pass1/pass2 sample drift"
    swap_series = load_swap(oos=False)

    res = gates_cdefg(joined, swap_series)
    g = res["g"]
    binding = [res["gate_C"]["pass"], res["gate_D"]["pass"], res["gate_E"]["pass"],
               res["gate_F"]["pass"], res["gate_G"]["pass"]]
    explore_pass = all(binding)

    knife = {}
    if explore_pass:
        zs = joined["vrp"].to_numpy()
        zr = joined["fwd_log"].to_numpy()
        # (i) RV window variants
        for win in (14, 28):
            pv, _ = build_signal_panel(d1, ret, ev, EXPLORE_START, EXPLORE_END, rv_win=win)
            jv, _ = join_forward(pv, d1)
            knife[f"rv{win}_ic"] = spearman(jv["vrp"].to_numpy(), jv["fwd_log"].to_numpy())
        # (ii) alternative null (diagnostic — IC identical by construction)
        _, p_bf = block_signflip_p(zs, zr, np.random.default_rng(SEED_BLOCKFLIP))
        knife["blockflip_p_two_sided"] = p_bf
        # (iii) Wednesday-only subsample
        wed = joined.index.dayofweek == 2
        knife["wednesday_ic"] = spearman(zs[wed], zr[wed])
        # (iv) simple pip-diff forward
        knife["pipdiff_ic"] = spearman(zs, joined["fwd_pips"].to_numpy())
        # (v) exclude stale-print days
        fresh = ~joined["evz_stale_run3"].to_numpy()
        knife["exclude_stale_ic"] = spearman(zs[fresh], zr[fresh])
        sign_keys = ["rv14_ic", "rv28_ic", "wednesday_ic", "pipdiff_ic", "exclude_stale_ic"]
        knife["sign_flip"] = any(np.sign(knife[k]) != g for k in sign_keys)
        if knife["sign_flip"]:
            explore_pass = False

    verdict = "PASS" if explore_pass else "FAIL"
    out = {"mode": "pass2", "verdict_explore": verdict, "g": g, **res, "knife_edge": knife,
           "binding_gates": {"C": res["gate_C"]["pass"], "D": res["gate_D"]["pass"],
                             "E": res["gate_E"]["pass"], "F": res["gate_F"]["pass"],
                             "G": res["gate_G"]["pass"]}}
    with open(PASS2_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(f"pass2 artifact: {PASS2_JSON}")


def run_oos(unlock):
    assert unlock, "OOS mode requires --unlock-oos (single touch, explore PASS only)"
    with open(PASS2_JSON) as f:
        p2 = json.load(f)
    assert p2["verdict_explore"] == "PASS", "OOS locked: explore verdict is not PASS"
    # condition 6: pass-2 verdict must itself be committed before OOS touch.
    # Single-touch semantics (pre-declared): a crash BEFORE OOS_JSON is written
    # counts as the same single touch and may be re-run; once OOS_JSON exists,
    # any re-run is permanently forbidden (assert below).
    _assert_committed(PASS2_JSON)
    assert not os.path.exists(OOS_JSON), "OOS already touched once — second touch forbidden"
    assert_manifest()
    g = p2["g"]
    ev = load_evz()
    d1, _ = build_d1()
    ret, _ = build_returns(d1)
    panel, census = build_signal_panel(d1, ret, ev, OOS_START, OOS_END)
    joined, _ = join_forward(panel, d1)
    swap_series = load_swap(oos=True)
    n = len(joined)
    zs, zr = joined["vrp"].to_numpy(), joined["fwd_log"].to_numpy()
    ic_obs, p_one = circular_shift_p(zs, zr, np.random.default_rng(SEED_OOS), one_sided_g=g)
    q1, q2 = np.quantile(zs, [1 / 3, 2 / 3])
    terc = np.where(zs <= q1, 0, np.where(zs <= q2, 1, 2))
    move = joined["fwd_pips"].to_numpy()
    extreme = terc != 1
    dir_obs = np.where(terc == 2, g, -g)[extreme]
    gross = dir_obs * move[extreme]
    swap_adv = swap_pips_per_obs(joined, swap_series, MARKUP_ADVERSE)
    swap_x = np.where(dir_obs == 1, swap_adv[1][extreme], swap_adv[-1][extreme])
    net_adv = gross + swap_x - RT_STRESSED
    gates = {
        "oos_p_one_sided": {"p": p_one, "pass": p_one < 0.05},
        "oos_gate_D_adverse": {"mean_net": float(net_adv.mean()), "pass": float(net_adv.mean()) > 0},
        "oos_power": {"n": n, "pass": n >= OOS_N_MIN and n // HORIZON >= OOS_NONOVERLAP_MIN},
        "oos_econ_floor": {"gross_mean": float(gross.mean()), "pass": float(gross.mean()) >= OOS_ECON_FLOOR},
    }
    if not gates["oos_power"]["pass"]:
        verdict = "OOS_UNDERPOWERED"
    elif all(v["pass"] for v in gates.values()):
        verdict = "FAMILY_PASS"
    else:
        verdict = "OOS_FAIL"
    out = {"mode": "oos", "verdict_family": verdict, "g": g, "ic_oos": ic_obs,
           "census": census, **gates}
    with open(OOS_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


def main():
    ap = argparse.ArgumentParser(description="E22 VRP explore harness (pre-reg frozen 2026-08-17)")
    ap.add_argument("--mode", required=True, choices=["manifest", "pass1", "pass2", "oos"])
    ap.add_argument("--unlock-oos", action="store_true")
    args = ap.parse_args()
    if args.mode == "manifest":
        write_manifest()
    elif args.mode == "pass1":
        run_pass1()
    elif args.mode == "pass2":
        run_pass2()
    else:
        run_oos(args.unlock_oos)


if __name__ == "__main__":
    main()
