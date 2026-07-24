#!/usr/bin/env python3
"""W0-2: price_shock_rev 5-seat exit-free fixed-horizon audit.

Verification debt on the 5 already-promoted price_shock_rev seats
(promoted 2026-05-18; grid BT window 2021-12-24..2026-05-15, BH-FDR m=3744,
Wilson_lo>=0.58). This re-detects each seat's FROZEN trigger (imported
verbatim from the production strategy classes in strategies/hourly/) on a
~12.6y MASSIVE H1 parquet and measures exit-free forward MFE/MAE/net move at
fixed horizons h in {4h, 12h, 24h, 72h, 120h}. NO exit simulation
(no BE/Trail, no TP/SL). Full-window re-measurement of frozen triggers only —
no new mining, no parameter search.

Data quality (found during this audit, 2026-07-24): the MASSIVE H1 feed
contains (a) Saturday-stamped rows while FX is closed, and (b) bad-print bars
— e.g. EUR_GBP -23.7%/h 2022-06-17 20:00, USD_CAD -26.1%/h 2024-12-20 21:00 —
that instantly revert. A 1%-tile shock trigger is a magnet for these, so the
audit runs two passes:
  raw   = feed as-is (matches the grid-BT input; used for trigger fidelity)
  clean = Saturday rows dropped + spike-and-revert bad prints excluded
          (|1h log return| >= 3% that reverts >= 75% within 2 bars —
          validated to keep real shocks such as Brexit AUD_JPY -5.6%
          2016-06-24 02:00 while catching all known artifacts).
Headline verdicts use CLEAN stats; raw is reported for contrast because the
promoted grid cells were mined on the raw feed.

Usage:
    python3 tools/price_shock_exitfree_audit.py --fetch   # fetch 12y parquets
    python3 tools/price_shock_exitfree_audit.py           # run audit
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.friction_model_v2 import _SESSION_MULTIPLIER  # noqa: E402

DATA_DIR = ROOT / "data" / "cache" / "massive"
DB_PATH = ROOT / "data" / "price_shock_grid_cells.db"
STAMP = "2026-07-24"
OUT_JSON = ROOT / "bt-results" / f"price_shock_exitfree_audit-{STAMP}.json"
OUT_MD = ROOT / "reports" / f"price_shock_exitfree_audit-{STAMP}.md"

# Fixed audit horizons (H1 bars == market hours)
HORIZONS = [4, 12, 24, 72, 120]

# Grid-BT promotion window (matches price_shock_grid_cells period_*)
PROMO_START = pd.Timestamp("2021-12-24T00:00:00Z")
PROMO_END = pd.Timestamp("2026-05-15T23:59:59Z")

BOOT_B = 10_000
BOOT_SEED = 42

# Bad-print detector (spike-and-revert)
ART_RET_THR = 0.03      # |1h log return| >= 3%
ART_REVERT_FRAC = 0.25  # price back within 25% of the spike vs pre-spike close
ART_REVERT_BARS = 2     # ... within 2 subsequent bars

# Task-given theoretical round-trip friction (pips). Pairs not listed fall
# back to the repo-standard BT friction model median (computed per event).
RT_THEORETICAL_PIPS = {
    "EUR_USD": 2.0,
    "USD_JPY": 2.14,
    "EUR_JPY": 2.5,
    "GBP_USD": 4.53,
    "EUR_GBP": 3.0,
}

# Demotion-review flag thresholds (report-only; defined up front)
P_GATE = 0.05           # clean full-window bootstrap p (mean net > 0)
HEADROOM_GATE = 2.0     # MFE_p50 / RT


@dataclass(frozen=True)
class Seat:
    name: str
    pair: str
    horizon_bars: int   # frozen production time-stop horizon (info only)
    vol_q: str
    db_cell_id: str

    @property
    def primary_horizon(self) -> int:
        """Nearest fixed audit horizon to the frozen production horizon."""
        return min(HORIZONS, key=lambda h: abs(h - self.horizon_bars))


SEATS = [
    Seat("price_shock_rev_eur_gbp_h1_long", "EUR_GBP", 3, "Q5",
         "EUR_GBP_H1_LONG_SHOCK_1_3_Q5"),
    Seat("price_shock_rev_eur_aud_h1_long", "EUR_AUD", 12, "Q5",
         "EUR_AUD_H1_LONG_SHOCK_1_12_Q5"),
    Seat("price_shock_rev_usd_cad_h1_long", "USD_CAD", 3, "Q5",
         "USD_CAD_H1_LONG_SHOCK_1_3_Q5"),
    Seat("price_shock_rev_nzd_jpy_h1_long", "NZD_JPY", 12, "Q5",
         "NZD_JPY_H1_LONG_SHOCK_1_12_Q5"),
    Seat("price_shock_rev_aud_jpy_h1_long", "AUD_JPY", 12, "ALL",
         "AUD_JPY_H1_LONG_SHOCK_1_12_ALL"),
]


def _strategy_classes() -> dict:
    """Static imports of the FROZEN production trigger classes (no dynamic import)."""
    from strategies.hourly.price_shock_rev_aud_jpy_h1_long import PriceShockRevAudJpyH1Long
    from strategies.hourly.price_shock_rev_eur_aud_h1_long import PriceShockRevEurAudH1Long
    from strategies.hourly.price_shock_rev_eur_gbp_h1_long import PriceShockRevEurGbpH1Long
    from strategies.hourly.price_shock_rev_nzd_jpy_h1_long import PriceShockRevNzdJpyH1Long
    from strategies.hourly.price_shock_rev_usd_cad_h1_long import PriceShockRevUsdCadH1Long
    return {
        "price_shock_rev_eur_gbp_h1_long": PriceShockRevEurGbpH1Long,
        "price_shock_rev_eur_aud_h1_long": PriceShockRevEurAudH1Long,
        "price_shock_rev_usd_cad_h1_long": PriceShockRevUsdCadH1Long,
        "price_shock_rev_nzd_jpy_h1_long": PriceShockRevNzdJpyH1Long,
        "price_shock_rev_aud_jpy_h1_long": PriceShockRevAudJpyH1Long,
    }


# ── Repo-standard BT friction model (byte-identical numeric model to
#    app.py:_bt_spread / _bt_classify_session / _BT_SLIPPAGE; app.py itself
#    is not importable here because it pulls in flask) ────────────────────
_BT_SLIPPAGE = {
    "USDJPY": 0.005,
    "EURJPY": 0.005,
    "EURUSD": 0.00005,
    "GBPUSD": 0.0001,
    "EURGBP": 0.00005,
    "XAUUSD": 0.025,
}


def _bt_get_slippage(symbol: str) -> float:
    _s = symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
    for k, v in _BT_SLIPPAGE.items():
        if k in _s:
            return v
    if "JPY" in _s:
        return 0.004
    if "XAU" in _s:
        return 0.025
    return 0.00004


def _bt_classify_session(h: int) -> str:
    if 13 <= h < 17:
        return "overlap_LN"
    if 13 <= h < 22:
        return "NY"
    if 7 <= h < 13:
        return "London"
    if 2 <= h < 7:
        return "Tokyo"
    if 0 <= h < 2:
        return "Asia_early"
    return "Sydney"


def _bt_spread(hour: int, symbol: str) -> float:
    h = hour
    _s = symbol.upper()
    _is_gold = "XAU" in _s
    _is_eur_gbp = "EURGBP" in _s or "EUR_GBP" in _s
    _is_gbp_usd = "GBPUSD" in _s or "GBP_USD" in _s
    _is_eur_usd = "EURUSD" in _s or "EUR_USD" in _s
    _is_eur_jpy = "EURJPY" in _s or "EUR_JPY" in _s
    _is_jpy = "JPY" in _s

    if _is_gold:
        base = 0.050 if h < 2 else 0.040 if h < 7 else 0.030 if h < 16 else 0.035 if h < 20 else 0.050
    elif _is_eur_gbp:
        base = 0.00020 if h < 2 else 0.00015 if h < 7 else 0.00010 if h < 16 else 0.00012 if h < 20 else 0.00020
    elif _is_gbp_usd:
        base = 0.00018 if h < 2 else 0.00012 if h < 7 else 0.00008 if h < 16 else 0.00010 if h < 20 else 0.00018
    elif _is_eur_usd:
        base = 0.00010 if h < 2 else 0.00005 if h < 7 else 0.00003 if h < 16 else 0.00004 if h < 20 else 0.00010
    elif _is_eur_jpy:
        base = 0.015 if h < 2 else 0.008 if h < 7 else 0.005 if h < 16 else 0.007 if h < 20 else 0.015
    elif _is_jpy:
        base = 0.010 if h < 2 else 0.005 if h < 7 else 0.003 if h < 16 else 0.004 if h < 20 else 0.010
    else:
        base = 0.00010 if h < 2 else 0.00006 if h < 7 else 0.00003 if h < 16 else 0.00004 if h < 20 else 0.00010

    sess = _bt_classify_session(h)
    mult = _SESSION_MULTIPLIER.get(sess, _SESSION_MULTIPLIER.get("default", 1.0))
    return base * mult


def round_turn_friction_price(entry_hour: int, exit_hour: int, symbol: str) -> float:
    slip = _bt_get_slippage(symbol)
    return (_bt_spread(entry_hour, symbol) + _bt_spread(exit_hour, symbol)) / 2.0 + 2.0 * slip


# ── Helpers ─────────────────────────────────────────────────────────────
def pip_mult(pair: str) -> float:
    return 100.0 if "JPY" in pair else 10000.0


def parquet_path(pair: str) -> Path:
    return DATA_DIR / f"{pair}_1h_12y_audit.parquet"


def load_h1(pair: str) -> pd.DataFrame:
    path = parquet_path(pair)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run with --fetch first (MASSIVE_API_KEY required)")
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    elif df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("Open", "High", "Low", "Close"):
        if col not in df.columns:
            raise ValueError(f"{path}: missing column {col}")
    bad = int((df["Close"] <= 0).sum() + df["Close"].isna().sum())
    if bad:
        raise ValueError(f"{path}: {bad} non-positive/NaN Close rows")
    return df


def drop_saturday(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """FX is closed all Saturday UTC; Saturday-stamped rows are feed garbage.
    Production OANDA H1 has no Saturday bars, so dropping them also improves
    production fidelity."""
    sat = df.index.dayofweek == 5
    return df[~sat], int(sat.sum())


def bad_print_mask(df: pd.DataFrame) -> np.ndarray:
    """Spike-and-revert bad-print bars: |1h log return| >= ART_RET_THR whose
    close returns to within ART_REVERT_FRAC of the spike (vs pre-spike close)
    within ART_REVERT_BARS bars. Validated 2026-07-24: catches all known
    artifacts (EUR_GBP -23.7%, USD_CAD -26.1%, NZD_JPY -11.1%, ...) while
    keeping real shocks (Brexit AUD_JPY -5.6% 2016-06-24 02:00 -> False)."""
    c = df["Close"].to_numpy(float)
    n = len(c)
    lr = np.zeros(n)
    lr[1:] = np.log(c[1:] / c[:-1])
    bad = np.zeros(n, dtype=bool)
    for t in np.flatnonzero(np.abs(lr) >= ART_RET_THR):
        if t < 1:
            continue
        pre = c[t - 1]
        for k in range(1, ART_REVERT_BARS + 1):
            if t + k < n and abs(np.log(c[t + k] / pre)) <= ART_REVERT_FRAC * abs(lr[t]):
                bad[t] = True
                break
    return bad


def fetch_all(days: int) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        print("python-dotenv not installed; relying on ambient env", file=sys.stderr)
    from modules.data import fetch_ohlcv_massive
    for seat in SEATS:
        out = parquet_path(seat.pair)
        if out.exists():
            print(f"[fetch] {out.name} exists — skip")
            continue
        print(f"[fetch] {seat.pair} 1h days={days} -> {out.name}")
        df = fetch_ohlcv_massive(seat.pair, "1h", days)
        if df is None or df.empty:
            raise RuntimeError(f"fetch returned empty frame for {seat.pair}")
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out)
        print(f"[fetch] {seat.pair}: rows={len(df)} span={df.index[0]}..{df.index[-1]}")


def build_strategy(seat: Seat):
    cls = _strategy_classes()[seat.name]
    cfg = cls.cfg
    # sanity: frozen config must match the seat table
    assert cfg.pair == seat.pair, (cfg.pair, seat.pair)
    assert cfg.horizon_bars == seat.horizon_bars, (cfg.horizon_bars, seat.horizon_bars)
    assert cfg.vol_q == seat.vol_q, (cfg.vol_q, seat.vol_q)
    assert cfg.percentile == 0.01
    return cls()


def detect_events(strat, df: pd.DataFrame) -> np.ndarray:
    """Integer positions of trigger bars, using the PRODUCTION mask plus the
    evaluate() runtime guards (finite Close>0, vol20>0)."""
    computed = strat.add_precomputed_columns(df)
    mask = strat.signal_mask_from_dataframe(df)
    guards = (
        computed["Close"].gt(0)
        & np.isfinite(computed["Close"])
        & computed["vol20"].gt(0)
        & computed["vol20"].notna()
    )
    final = mask.to_numpy() & guards.to_numpy()
    return np.flatnonzero(final)


def thin_positions(positions: np.ndarray, min_gap: int) -> np.ndarray:
    """Keep first event of each cluster: next kept event must be >= min_gap
    bars after the previously kept one (non-overlapping forward windows)."""
    kept = []
    last = -10**9
    for p in positions:
        if p - last >= min_gap:
            kept.append(p)
            last = p
    return np.asarray(kept, dtype=int)


def bootstrap_p(net: np.ndarray, rng: np.random.Generator) -> float:
    """One-sided bootstrap p for H1: mean(net) > 0.
    p = P(bootstrap mean <= 0), add-one smoothed."""
    if len(net) == 0:
        return float("nan")
    idx = rng.integers(0, len(net), size=(BOOT_B, len(net)))
    means = net[idx].mean(axis=1)
    return float((np.sum(means <= 0.0) + 1) / (BOOT_B + 1))


def q(a: np.ndarray, pct: float) -> float:
    return float(np.percentile(a, pct)) if len(a) else float("nan")


def horizon_stats(df: pd.DataFrame, positions: np.ndarray, h: int, pair: str,
                  rng: np.random.Generator, bad: np.ndarray | None = None) -> dict:
    """Exit-free forward stats at horizon h bars for LONG events at Close[t].
    Forward window = bars t+1 .. t+h inclusive (event bar excluded).
    If `bad` (bool bar mask) given, events whose forward window touches a
    bad-print bar are excluded (path artifacts) and counted."""
    n_bars = len(df)
    highs = df["High"].to_numpy(float)
    lows = df["Low"].to_numpy(float)
    closes = df["Close"].to_numpy(float)
    hours = df.index.hour.to_numpy()
    pm = pip_mult(pair)

    usable = positions[positions + h < n_bars]
    dropped_tail = int(len(positions) - len(usable))

    n_excluded_path = 0
    if bad is not None and len(usable):
        bad_cum = np.concatenate(([0], np.cumsum(bad.astype(np.int64))))
        # bad bars inside t+1..t+h  <=>  bad_cum[t+h+1] - bad_cum[t+1] > 0
        path_hits = (bad_cum[usable + h + 1] - bad_cum[usable + 1]) > 0
        n_excluded_path = int(path_hits.sum())
        usable = usable[~path_hits]

    mfe, mae, net, rts = [], [], [], []
    for t in usable:
        fwd_start, fwd_end = t + 1, t + h  # inclusive
        assert fwd_start > t, "forward window must exclude the event bar"
        entry = closes[t]
        hi = highs[fwd_start:fwd_end + 1].max()
        lo = lows[fwd_start:fwd_end + 1].min()
        mfe.append((hi - entry) * pm)
        mae.append((entry - lo) * pm)
        net.append((closes[fwd_end] - entry) * pm)
        rts.append(round_turn_friction_price(int(hours[t]), int(hours[fwd_end]), pair) * pm)
    mfe = np.asarray(mfe)
    mae = np.asarray(mae)
    net = np.asarray(net)
    rts = np.asarray(rts)

    thinned = thin_positions(usable, h)
    net_thin = net[np.searchsorted(usable, thinned)] if len(thinned) else np.array([])

    rt_model_median = float(np.median(rts)) if len(rts) else float("nan")
    rt_used = RT_THEORETICAL_PIPS.get(pair, rt_model_median)
    rt_source = "task_theoretical" if pair in RT_THEORETICAL_PIPS else "repo_bt_model_median"

    mfe_p50 = q(mfe, 50)
    return {
        "h_bars": h,
        "n": int(len(usable)),
        "n_dropped_tail": dropped_tail,
        "n_excluded_path_artifact": n_excluded_path,
        "n_nonoverlap": int(len(thinned)),
        "mfe_pips": {"p25": q(mfe, 25), "p50": mfe_p50, "p75": q(mfe, 75)},
        "mae_pips": {"p25": q(mae, 25), "p50": q(mae, 50), "p75": q(mae, 75)},
        "net_pips": {
            "mean": float(net.mean()) if len(net) else float("nan"),
            "p50": q(net, 50),
            "share_pos": float((net > 0).mean()) if len(net) else float("nan"),
        },
        "bootstrap_p_all": bootstrap_p(net, rng),
        "bootstrap_p_nonoverlap": bootstrap_p(net_thin, rng),
        "net_nonoverlap_mean": float(net_thin.mean()) if len(net_thin) else float("nan"),
        "rt_used_pips": rt_used,
        "rt_source": rt_source,
        "rt_repo_model_median_pips": rt_model_median,
        "headroom_mfe_p50_over_rt": (mfe_p50 / rt_used) if rt_used and rt_used > 0 else float("nan"),
        "net_mean_minus_rt": (float(net.mean()) - rt_used) if len(net) else float("nan"),
    }


def db_cell(cell_id: str) -> dict:
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.execute(
            "SELECT n_trades, win_rate, ev_pip, wilson_lower_95, bh_fdr_pass, "
            "bonferroni_pass, verdict, period_start, period_end "
            "FROM price_shock_grid_cells WHERE cell_id = ?", (cell_id,))
        row = cur.fetchone()
    finally:
        con.close()
    if row is None:
        raise KeyError(f"cell {cell_id} not found in {DB_PATH}")
    keys = ["n_trades", "win_rate", "ev_pip", "wilson_lower_95", "bh_fdr_pass",
            "bonferroni_pass", "verdict", "period_start", "period_end"]
    return dict(zip(keys, row))


def window_masks(event_index: pd.DatetimeIndex) -> dict:
    return {
        "full": np.ones(len(event_index), dtype=bool),
        "pre_promo": np.asarray(event_index < PROMO_START),
        "promo_2021_2026": np.asarray((event_index >= PROMO_START) & (event_index <= PROMO_END)),
        "post_promo": np.asarray(event_index > PROMO_END),
    }


def audit_seat(seat: Seat, rng: np.random.Generator) -> dict:
    strat = build_strategy(seat)

    # ── pass 1: RAW feed (grid-BT-equivalent input) for trigger fidelity ──
    raw_df = load_h1(seat.pair)
    raw_pos = detect_events(strat, raw_df)
    raw_bad = bad_print_mask(raw_df)
    raw_ts = raw_df.index[raw_pos]
    raw_promo = np.asarray((raw_ts >= PROMO_START) & (raw_ts <= PROMO_END))
    raw_sat = np.asarray(raw_ts.dayofweek == 5)
    raw_trigger_artifact = raw_bad[raw_pos] | raw_sat
    cell = db_cell(seat.db_cell_id)
    n_raw_promo = int(raw_promo.sum())
    n_promo_artifact = int((raw_promo & raw_trigger_artifact).sum())
    fidelity_ratio = n_raw_promo / cell["n_trades"] if cell["n_trades"] else float("nan")

    print(f"[{seat.name}] RAW rows={len(raw_df)} span={raw_df.index[0]}..{raw_df.index[-1]} "
          f"events={len(raw_pos)} bad_print_bars={int(raw_bad.sum())}")
    print(f"  fidelity: promo-window events={n_raw_promo} vs DB n_trades={cell['n_trades']} "
          f"(ratio {fidelity_ratio:.3f}); artifact-triggered promo events={n_promo_artifact}")

    # ── pass 2: CLEAN feed (headline measurement) ──────────────────────────
    df, n_sat_rows = drop_saturday(raw_df)
    bad = bad_print_mask(df)
    pos_all = detect_events(strat, df)
    trig_art = bad[pos_all]
    positions = pos_all[~trig_art]
    n_trigger_artifact = int(trig_art.sum())
    print(f"  CLEAN rows={len(df)} (sat_dropped={n_sat_rows}) bad_print_bars={int(bad.sum())} "
          f"events={len(pos_all)} trigger_artifacts_excluded={n_trigger_artifact} "
          f"clean_events={len(positions)}")
    if len(positions) == 0:
        raise RuntimeError(f"{seat.name}: zero clean events — bug until proven otherwise")

    masks = window_masks(df.index[positions])
    windows = {name: positions[m] for name, m in masks.items()}
    for wname, wpos in windows.items():
        print(f"  window {wname}: clean events={len(wpos)}")

    window_stats = {}
    for wname, wpos in windows.items():
        window_stats[wname] = {
            "n_events": int(len(wpos)),
            "horizons": {str(h): horizon_stats(df, wpos, h, seat.pair, rng, bad=bad)
                         for h in HORIZONS},
        }

    # raw (artifact-inclusive) stats, full window only — for contrast with
    # the promoted grid cells which were mined on this feed
    raw_full_stats = {str(h): horizon_stats(raw_df, raw_pos, h, seat.pair, rng, bad=None)
                      for h in HORIZONS}

    ph = str(seat.primary_horizon)
    prim = window_stats["full"]["horizons"][ph]
    pre = window_stats["pre_promo"]["horizons"][ph]
    edge_survives = (
        prim["bootstrap_p_all"] < P_GATE
        and prim["net_pips"]["p50"] > 0
        and prim["net_pips"]["mean"] > prim["rt_used_pips"]
    )
    headroom_ok = prim["headroom_mfe_p50_over_rt"] >= HEADROOM_GATE
    robustness_ok = prim["bootstrap_p_nonoverlap"] < P_GATE
    promo_concentration_warning = (
        not np.isfinite(pre["bootstrap_p_all"])
        or pre["bootstrap_p_all"] >= P_GATE
        or pre["net_pips"]["mean"] <= pre["rt_used_pips"]
    )
    flag = not (edge_survives and headroom_ok)

    return {
        "seat": seat.name,
        "pair": seat.pair,
        "frozen_trigger": {
            "percentile": 0.01, "rolling_window": 252, "vol20_window": 20,
            "vol_q": seat.vol_q, "direction": "LONG",
            "production_horizon_bars": seat.horizon_bars,
        },
        "primary_audit_horizon_bars": seat.primary_horizon,
        "data": {
            "path": str(parquet_path(seat.pair)),
            "raw_rows": int(len(raw_df)),
            "clean_rows": int(len(df)),
            "saturday_rows_dropped": n_sat_rows,
            "bad_print_bars_clean_feed": int(bad.sum()),
            "span": [str(df.index[0]), str(df.index[-1])],
            "years": round((df.index[-1] - df.index[0]).days / 365.25, 2),
        },
        "db_promoted_cell": {"cell_id": seat.db_cell_id, **cell},
        "trigger_fidelity_raw_feed": {
            "events_in_promo_window": n_raw_promo,
            "db_n_trades": cell["n_trades"],
            "ratio": round(fidelity_ratio, 4),
            "promo_events_artifact_triggered": n_promo_artifact,
            "promo_artifact_share": round(n_promo_artifact / n_raw_promo, 4) if n_raw_promo else None,
        },
        "event_counts": {
            "raw_full": int(len(raw_pos)),
            "clean_full_before_artifact_excl": int(len(pos_all)),
            "trigger_artifacts_excluded": n_trigger_artifact,
            "clean_full": int(len(positions)),
        },
        "windows_clean": window_stats,
        "raw_full_horizons": raw_full_stats,
        "verdict": {
            "edge_survives_exitfree_clean": bool(edge_survives),
            "headroom_ok": bool(headroom_ok),
            "nonoverlap_robustness_ok": bool(robustness_ok),
            "promo_concentration_warning": bool(promo_concentration_warning),
            "flag_demotion_review": bool(flag),
            "gates": {
                "bootstrap_p_lt": P_GATE,
                "net_median_gt": 0.0,
                "net_mean_gt_rt": True,
                "headroom_ge": HEADROOM_GATE,
                "promo_concentration": "pre_promo p>=0.05 or pre_promo net mean<=RT",
            },
        },
    }


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:.{nd}f}"


def write_markdown(results: list[dict]) -> None:
    lines = []
    lines.append(f"# price_shock 5-seat exit-free fixed-horizon audit — {STAMP}")
    lines.append("")
    lines.append("**Task W0-2** — verification debt on the 5 promoted `price_shock_rev` seats "
                 "(promoted 2026-05-18 off the 2021-12-24..2026-05-15 grid BT, BH-FDR m=3744, "
                 "Wilson_lo>=0.58). Frozen production triggers (strategies/hourly/, "
                 "`signal_mask_from_dataframe`) re-detected on ~12.6y MASSIVE H1 parquet "
                 "(2013-12-16..2026-07-24); forward MFE/MAE/net move measured exit-free at "
                 "fixed horizons {4h, 12h, 24h, 72h, 120h}. No BE/Trail, no TP/SL simulation, "
                 "no new mining. Report-only: no tier action taken.")
    lines.append("")
    lines.append("## Data-quality finding (affects the promoted cells themselves)")
    lines.append("")
    lines.append("The MASSIVE H1 feed contains **Saturday-stamped rows** (FX closed) and "
                 "**spike-and-revert bad prints** — e.g. EUR_GBP −23.7%/h (2022-06-17 20:00, "
                 "0.678 vs real ~0.856), USD_CAD −26.1%/h (2024-12-20 21:00), NZD_JPY −11.1%/h "
                 "(2023-01-17 21:00), AUD_JPY bars on Saturday 2023-12-02 ~16% off market. "
                 "A 1%-tile log-return shock trigger is a magnet for such prints: the bad low "
                 "print triggers the seat, the instant revert books a fake MR profit that live "
                 "OANDA execution could never capture. **The frozen grid-BT caches contain the "
                 "same bars** (bad prints ≥5%/h: EUR_GBP 15, USD_CAD 18, NZD_JPY 17, AUD_JPY 10, "
                 "EUR_AUD 0), so the promoted `ev_pip` values are partly artifact-inflated. "
                 "All headline stats below therefore use a cleaned feed:")
    lines.append("")
    lines.append(f"- drop Saturday rows (production OANDA H1 has none);")
    lines.append(f"- exclude events on bad-print bars (|1h ret| ≥ {ART_RET_THR:.0%} reverting "
                 f"≥ {1 - ART_REVERT_FRAC:.0%} within {ART_REVERT_BARS} bars — validated to keep "
                 "real shocks: Brexit AUD_JPY −5.6% 2016-06-24 stays IN);")
    lines.append("- exclude events whose forward window crosses a bad-print bar (path artifact).")
    lines.append("")
    lines.append("Raw-feed (grid-BT-equivalent) numbers are shown for contrast.")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("- Entry reference = event-bar Close; forward window = bars t+1..t+h "
                 "(event bar excluded, asserted).")
    lines.append("- Horizons are H1 *market* bars (== hours while market open; spans weekends).")
    lines.append(f"- Bootstrap: one-sided p for mean(net)>0, B={BOOT_B:,}, seed={BOOT_SEED}; "
                 "`p_noovl` = same test on cluster-thinned events (non-overlapping forward "
                 "windows) — the honest N under event clustering.")
    lines.append("- RT friction: task theoretical values where given (EUR_GBP 3.0p); otherwise "
                 "repo-standard BT friction model (app.py `_bt_spread`+`_bt_get_slippage`) "
                 "per-event median. Headroom = MFE_p50 / RT.")
    lines.append(f"- Report-only flags: FLAG if bootstrap p >= {P_GATE}, net median <= 0, "
                 f"net mean <= RT, or headroom < {HEADROOM_GATE} at the seat's primary horizon "
                 "(nearest fixed horizon to its frozen production time-stop). "
                 "`promo-conc` = pre-promotion window (2013-2021, pure past-OOS) fails "
                 "p<0.05 or its net mean <= RT — edge concentrated in the mined window.")
    lines.append("")

    lines.append("## Seat verdict summary (primary horizon, full ~12.6y CLEAN window)")
    lines.append("")
    lines.append("| Seat | Pair | Prod h | Audit h | N | net mean (p) | net p50 (p) | boot p | p_noovl | MFE p50 (p) | RT (p) | Headroom | raw mean (p) | Edge survives | promo-conc | FLAG |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        ph = str(r["primary_audit_horizon_bars"])
        s = r["windows_clean"]["full"]["horizons"][ph]
        raw = r["raw_full_horizons"][ph]
        v = r["verdict"]
        lines.append(
            f"| {r['seat']} | {r['pair']} | {r['frozen_trigger']['production_horizon_bars']} "
            f"| {ph}h | {s['n']} | {fmt(s['net_pips']['mean'])} | {fmt(s['net_pips']['p50'])} "
            f"| {fmt(s['bootstrap_p_all'], 4)} | {fmt(s['bootstrap_p_nonoverlap'], 4)} "
            f"| {fmt(s['mfe_pips']['p50'])} | {fmt(s['rt_used_pips'])} "
            f"| {fmt(s['headroom_mfe_p50_over_rt'])}x | {fmt(raw['net_pips']['mean'])} "
            f"| {'YES' if v['edge_survives_exitfree_clean'] else 'NO'} "
            f"| {'⚠️' if v['promo_concentration_warning'] else 'ok'} "
            f"| {'**FLAG**' if v['flag_demotion_review'] else 'ok'} |")
    lines.append("")

    lines.append("## Trigger fidelity + artifact contamination of the promoted cells (raw feed)")
    lines.append("")
    lines.append("| Seat | DB cell | DB N | Re-detected N (promo win) | Ratio | artifact-triggered | artifact share | DB WR | DB ev_pip |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        c = r["db_promoted_cell"]
        f_ = r["trigger_fidelity_raw_feed"]
        lines.append(
            f"| {r['seat']} | {c['cell_id']} | {c['n_trades']} | {f_['events_in_promo_window']} "
            f"| {fmt(f_['ratio'], 3)} | {f_['promo_events_artifact_triggered']} "
            f"| {fmt((f_['promo_artifact_share'] or 0) * 100, 1)}% "
            f"| {fmt(c['win_rate'] * 100, 1)}% | {fmt(c['ev_pip'], 1)} |")
    lines.append("")

    for r in results:
        lines.append(f"## {r['seat']} ({r['pair']}, vol_q={r['frozen_trigger']['vol_q']}, "
                     f"prod horizon={r['frozen_trigger']['production_horizon_bars']} bars)")
        lines.append("")
        d = r["data"]
        ec = r["event_counts"]
        lines.append(f"Data: {d['clean_rows']:,} clean H1 rows ({d['saturday_rows_dropped']} "
                     f"Saturday rows dropped, {d['bad_print_bars_clean_feed']} bad-print bars), "
                     f"{d['span'][0]} .. {d['span'][1]} ({d['years']}y). Events: raw "
                     f"{ec['raw_full']} -> clean {ec['clean_full']} "
                     f"({ec['trigger_artifacts_excluded']} trigger artifacts excluded).")
        lines.append("")
        lines.append("### Full-window CLEAN exit-free stats by horizon")
        lines.append("")
        lines.append("| h | N | excl_path | N_noovl | MFE p25/p50/p75 (p) | MAE p25/p50/p75 (p) | net mean (p) | net p50 (p) | net>0 % | boot p | p_noovl | RT (p) | Headroom | raw mean |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for h in HORIZONS:
            s = r["windows_clean"]["full"]["horizons"][str(h)]
            raw = r["raw_full_horizons"][str(h)]
            mk = "**" if h == r["primary_audit_horizon_bars"] else ""
            lines.append(
                f"| {mk}{h}h{mk} | {s['n']} | {s['n_excluded_path_artifact']} | {s['n_nonoverlap']} "
                f"| {fmt(s['mfe_pips']['p25'])}/{fmt(s['mfe_pips']['p50'])}/{fmt(s['mfe_pips']['p75'])} "
                f"| {fmt(s['mae_pips']['p25'])}/{fmt(s['mae_pips']['p50'])}/{fmt(s['mae_pips']['p75'])} "
                f"| {fmt(s['net_pips']['mean'])} | {fmt(s['net_pips']['p50'])} "
                f"| {fmt(s['net_pips']['share_pos'] * 100, 1)} "
                f"| {fmt(s['bootstrap_p_all'], 4)} | {fmt(s['bootstrap_p_nonoverlap'], 4)} "
                f"| {fmt(s['rt_used_pips'])} | {fmt(s['headroom_mfe_p50_over_rt'])}x "
                f"| {fmt(raw['net_pips']['mean'])} |")
        lines.append("")
        lines.append("### Sub-window CLEAN net move at primary horizon "
                     f"({r['primary_audit_horizon_bars']}h)")
        lines.append("")
        lines.append("| Window | N | net mean (p) | net p50 (p) | boot p | p_noovl |")
        lines.append("|---|---|---|---|---|---|")
        ph = str(r["primary_audit_horizon_bars"])
        for wname in ["full", "pre_promo", "promo_2021_2026", "post_promo"]:
            s = r["windows_clean"][wname]["horizons"][ph]
            lines.append(f"| {wname} | {s['n']} | {fmt(s['net_pips']['mean'])} "
                         f"| {fmt(s['net_pips']['p50'])} | {fmt(s['bootstrap_p_all'], 4)} "
                         f"| {fmt(s['bootstrap_p_nonoverlap'], 4)} |")
        lines.append("")

    lines.append("## Method caveats")
    lines.append("")
    lines.append("- Exit-free net move is NOT the production payoff: production seats exit at "
                 "horizon close or a catastrophic -2xATR-proxy stop. Exit-free removes the stop, "
                 "so tail losses here can exceed production; conversely winners are never cut. "
                 "This is the assumption-free view of whether the raw directional edge exists.")
    lines.append("- Overlapping events (shock clusters) share forward windows; the all-events "
                 "bootstrap overstates significance. `p_noovl` is the honest lower bound.")
    lines.append("- RT for EUR_AUD/USD_CAD/NZD_JPY/AUD_JPY uses the repo BT friction model "
                 "(else-branch/JPY-branch base spreads). For EUR_AUD this is likely optimistic "
                 "(real EUR_AUD spreads run wider than majors); headroom should be read with "
                 "margin. Additionally, Q5-vol shock bars have spreads far above session "
                 "averages (death-zone regime), so ALL headroom numbers are upper bounds.")
    lines.append("- The bad-print detector is conservative (3%/h + 75% revert in 2 bars); "
                 "residual sub-3% artifacts may remain in both clean stats and the grid cells.")
    lines.append("- Grid-BT DB window is 2021-12-24..2026-05-15 (~4.4y), not 12.3y; this audit "
                 "extends the same frozen triggers back to 2013-12 (pre_promo = pure past-OOS) "
                 "and forward past promotion (post_promo, small N).")
    lines.append("")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[out] wrote {OUT_MD}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true",
                        help="fetch 12y H1 parquets for the 5 pairs, then exit")
    parser.add_argument("--days", type=int, default=4600)
    args = parser.parse_args()

    if args.fetch:
        fetch_all(args.days)
        return 0

    rng = np.random.default_rng(BOOT_SEED)
    results = [audit_seat(seat, rng) for seat in SEATS]

    payload = {
        "task": "W0-2 price_shock 5-seat exit-free fixed-horizon audit",
        "generated_at": STAMP,
        "method": {
            "trigger_source": "production strategies/hourly/*.py signal_mask_from_dataframe "
                              "+ evaluate() guards (Close>0, vol20>0)",
            "horizons_bars_h1": HORIZONS,
            "entry_reference": "event bar Close",
            "forward_window": "bars t+1..t+h inclusive (event bar excluded)",
            "exit_simulation": "NONE (exit-free MFE/MAE/net)",
            "data_cleaning": {
                "saturday_rows_dropped": True,
                "bad_print_detector": {
                    "ret_thr": ART_RET_THR,
                    "revert_frac": ART_REVERT_FRAC,
                    "revert_bars": ART_REVERT_BARS,
                    "validation": "catches EUR_GBP -23.7% 2022-06-17 etc.; "
                                  "keeps Brexit AUD_JPY -5.6% 2016-06-24",
                },
            },
            "bootstrap": {"B": BOOT_B, "seed": BOOT_SEED,
                          "test": "one-sided mean(net)>0"},
            "friction": {"task_theoretical_pips": RT_THEORETICAL_PIPS,
                         "fallback": "repo BT friction model per-event median"},
            "flag_gates": {"p": P_GATE, "headroom": HEADROOM_GATE},
        },
        "seats": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(f"[out] wrote {OUT_JSON}")
    write_markdown(results)

    for r in results:
        v = r["verdict"]
        ph = str(r["primary_audit_horizon_bars"])
        s = r["windows_clean"]["full"]["horizons"][ph]
        print(f"[verdict] {r['seat']}: survives_clean={v['edge_survives_exitfree_clean']} "
              f"headroom={s['headroom_mfe_p50_over_rt']:.2f}x "
              f"p={s['bootstrap_p_all']:.4f} p_noovl={s['bootstrap_p_nonoverlap']:.4f} "
              f"promo_conc_warn={v['promo_concentration_warning']} "
              f"FLAG={v['flag_demotion_review']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
