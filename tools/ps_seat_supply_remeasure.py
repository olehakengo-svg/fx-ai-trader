#!/usr/bin/env python3
"""price_shock_rev seat-supply remeasure — design-expected vs observed rows.

Pre-registered harness for the `ps-seat-supply-remeasure-30d` registry entry
(deadline 2026-09-10, doc knowledge-base/wiki/analyses/
price-shock-seat-supply-audit-2026-07-29.md §9 検証計画 4).

Estimand (frozen by the pre-reg — do NOT widen here):
  design 期待 = number of H1 bars inside the window whose *canonical MASSIVE*
    bar satisfies the production entry condition, computed by calling the live
    strategy objects' own `signal_mask_from_dataframe` (BT/本番統一原則: no
    re-implementation of the condition in this file).
  観測 rows   = production `/api/demo/trades` rows for the same window whose
    `entry_type` is one of the five seats, `dedup_violation != 1`, counted
    `unique` on (entry_type, instrument, direction, bar_ts) where bar_ts is
    the H1 bar containing entry_time.
  capture     = 観測 unique total / design 期待.

The two series are NOT known to be the same set of bars. `observed_on_design_bar`
is reported as a diagnostic (never as capture) because the live anchor bar is
ambiguous by one hour: a partial-bar crossing anchors on floor(entry_time)
(tools/price_shock_exit_counterfactual.py header, 2026-07-28), while a
closed-bar detection stamps entry in the following bar and anchors on
floor(entry_time) - 1h. Both patterns appear in the observed rows, so the
diagnostic accepts either.

Deliberately NOT computed here: EV / WR / PnL. The carve-out EV verdict lives
behind the separate frozen `ps-carveout-regate-post-172` look (P-10 style ban
on joint gate×outcome computation). This tool is supply-rate only.

Window completeness guard: the pre-reg forbids a verdict on a partial window
("中途窓での verdict 禁止") unless the early-execution condition (observed
unique N >= 15) is met. That rule is enforced in `decide_verdict`, not just in
prose, so a premature run self-labels MID_WINDOW_DIAGNOSTIC.

Usage:
  python3 tools/ps_seat_supply_remeasure.py --json
  python3 tools/ps_seat_supply_remeasure.py --trades-json dump.json --as-of 2026-09-11
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

API = "https://fx-ai-trader.onrender.com/api/demo/trades"

# Window frozen by the registry entry (`since` 2026-08-11, deadline 09-10).
WINDOW_START = "2026-08-11T00:00:00Z"
WINDOW_END = "2026-09-11T00:00:00Z"  # exclusive == 2026-09-10T23:59:59Z inclusive

# Boundaries frozen by the queue packet (20260907-1330-ps-seat-supply-remeasure-30d).
DESIGN_N_FLOOR = 15
CAPTURE_ACCEPT = 0.80
EARLY_EXEC_OBSERVED_N = 15

# entry_type -> (canonical pair, live/fetch symbol). vol_q / horizon / percentile
# are NOT restated here: they come from the strategy objects themselves.
SEATS = {
    "price_shock_rev_eur_gbp_h1_long": ("EUR_GBP", "EURGBP=X"),
    "price_shock_rev_aud_jpy_h1_long": ("AUD_JPY", "AUDJPY=X"),
    "price_shock_rev_nzd_jpy_h1_long": ("NZD_JPY", "NZDJPY=X"),
    "price_shock_rev_eur_aud_h1_long": ("EUR_AUD", "EURAUD=X"),
    "price_shock_rev_usd_cad_h1_long": ("USD_CAD", "USDCAD=X"),
}

# Frozen 12.3y audit parquets end 2026-07-24; the window needs a live top-up.
# 252 + 20 + 1 bars of warm-up are required by the strategy, so fetch well past
# the window start.
TOPUP_DAYS = 120


def strategy_for(entry_type: str):
    """Return the production strategy instance owning `entry_type`."""
    from strategies.hourly import HourlyEngine

    engine = HourlyEngine()
    for strat in engine.strategies:
        if getattr(strat, "name", None) == entry_type:
            return strat
    raise KeyError(f"{entry_type} not registered in HourlyEngine")


def _norm_utc(df: pd.DataFrame) -> pd.DataFrame:
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    out = df.set_axis(idx).sort_index()
    return out[~out.index.duplicated(keep="last")]


def load_canonical_h1(
    pair: str,
    symbol: str,
    cache_dir: Path,
    fetcher=None,
    topup_days: int = TOPUP_DAYS,
) -> tuple[pd.DataFrame, dict]:
    """Frozen 12.3y MASSIVE audit parquet union-merged with a fresh MASSIVE top-up.

    union-merge (not overwrite) per the rolling-window cache lesson; the still
    forming last bar of the top-up is dropped because the design condition is
    defined on *closed* bars.
    """
    frozen_path = cache_dir / f"{pair}_1h_12y_audit.parquet"
    frozen = _norm_utc(pd.read_parquet(frozen_path)[["Open", "High", "Low", "Close"]])
    prov = {
        "frozen_file": frozen_path.name,
        "frozen_rows": int(len(frozen)),
        "frozen_last": str(frozen.index.max()),
        "topup_rows": 0,
        "topup_last": None,
        "overlap_bars": 0,
        "overlap_close_max_abs_diff": None,
    }
    if fetcher is None:
        return frozen, prov

    fresh = _norm_utc(fetcher(symbol, "1h", topup_days)[["Open", "High", "Low", "Close"]])
    fresh = fresh.iloc[:-1]  # drop the still-forming bar
    prov["topup_rows"] = int(len(fresh))
    prov["topup_last"] = str(fresh.index.max()) if len(fresh) else None

    # Vendor-boundary check: the top-up must agree with the frozen file where
    # they overlap. A mismatch means the two series are not the same estimand,
    # which would silently corrupt the design count.
    shared = frozen.index.intersection(fresh.index)
    prov["overlap_bars"] = int(len(shared))
    if len(shared):
        diff = (frozen.loc[shared, "Close"] - fresh.loc[shared, "Close"]).abs()
        prov["overlap_close_max_abs_diff"] = float(diff.max())
        prov["overlap_close_median_abs_diff"] = float(diff.median())
        prov["overlap_close_p95_abs_diff"] = float(diff.quantile(0.95))
        prov["overlap_bars_exact"] = int((diff == 0).sum())

    merged = pd.concat([frozen, fresh[fresh.index > frozen.index.max()]])
    return _norm_utc(merged), prov


def design_signal_bars(
    strategy, df: pd.DataFrame, win_start: pd.Timestamp, win_end: pd.Timestamp
) -> list[pd.Timestamp]:
    """Design signal bar timestamps inside [win_start, win_end)."""
    mask = strategy.signal_mask_from_dataframe(df)
    hits = df.index[mask.to_numpy(dtype=bool)]
    return list(hits[(hits >= win_start) & (hits < win_end)])


def load_observed(trades_json: str | None, date_from: str) -> list[dict]:
    if trades_json:
        payload = json.load(open(trades_json))
    else:
        import requests

        resp = requests.get(
            API,
            params={"status": "all", "date_from": date_from, "limit": 20000},
            timeout=300,
        )
        resp.raise_for_status()
        payload = resp.json()
    return [
        t for t in payload["trades"]
        if str(t.get("entry_type") or "") in SEATS
        and int(t.get("dedup_violation") or 0) != 1
    ]


def is_live(row: dict) -> bool:
    """Canonical live test (MEMORY feedback_live_vs_shadow_strict_separation)."""
    return bool(str(row.get("oanda_trade_id") or "").strip())


def bar_ts(row: dict) -> pd.Timestamp:
    ts = pd.Timestamp(row["entry_time"])
    ts = ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")
    return ts.floor("1h")


def unique_key(row: dict) -> tuple:
    return (
        row.get("entry_type"),
        row.get("instrument"),
        row.get("direction") or row.get("signal"),
        bar_ts(row),
    )


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k/n; (nan, nan) when n == 0."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def decide_verdict(design_total: int, observed_unique: int, window_complete: bool) -> dict:
    """Pre-registered decision boundaries. Partial windows cannot yield a verdict
    unless the early-execution condition (observed unique N >= 15) holds."""
    capture = (observed_unique / design_total) if design_total else float("nan")
    if not window_complete and observed_unique < EARLY_EXEC_OBSERVED_N:
        return {
            "verdict": "MID_WINDOW_DIAGNOSTIC",
            "capture": capture,
            "reason": (
                f"window incomplete and observed unique N={observed_unique} "
                f"< {EARLY_EXEC_OBSERVED_N} (early-execution condition unmet); "
                "pre-reg forbids a verdict on a partial window"
            ),
        }
    if design_total < DESIGN_N_FLOOR:
        return {
            "verdict": "NEEDS_MORE_EVIDENCE",
            "capture": capture,
            "reason": (
                f"design expectation N={design_total} < {DESIGN_N_FLOOR} "
                "(market produced too few signal bars — capture verdict underpowered)"
            ),
        }
    if capture >= CAPTURE_ACCEPT:
        return {
            "verdict": "ACCEPT",
            "capture": capture,
            "reason": f"design N={design_total} >= {DESIGN_N_FLOOR} and capture {capture:.1%} >= 80%",
        }
    return {
        "verdict": "REJECT",
        "capture": capture,
        "reason": f"design N={design_total} >= {DESIGN_N_FLOOR} and capture {capture:.1%} < 80%",
    }


def remeasure(
    cache_dir: Path,
    observed: list[dict],
    as_of: pd.Timestamp,
    fetcher=None,
) -> dict:
    win_start = pd.Timestamp(WINDOW_START)
    win_end = pd.Timestamp(WINDOW_END)
    # design bars are only observable up to the last closed bar, so a run
    # before win_end measures a shorter effective window.
    effective_end = min(win_end, as_of.floor("1h"))
    window_complete = as_of >= win_end

    in_window = [r for r in observed if win_start <= bar_ts(r) < effective_end]

    per_seat = {}
    design_total = 0
    live_total = shadow_total = 0
    matched_total = 0
    matched_strict_total = 0
    for entry_type, (pair, symbol) in SEATS.items():
        strat = strategy_for(entry_type)
        df, prov = load_canonical_h1(pair, symbol, cache_dir, fetcher=fetcher)
        bars = design_signal_bars(strat, df, win_start, effective_end)
        design_n = len(bars)

        rows = [r for r in in_window if r.get("entry_type") == entry_type]
        live_keys = {unique_key(r) for r in rows if is_live(r)}
        shadow_keys = {unique_key(r) for r in rows if not is_live(r)}
        all_keys = live_keys | shadow_keys
        # Anchor diagnostic. The live anchor bar is ambiguous by an hour: a
        # partial-bar crossing anchors on floor(entry_time), whereas a
        # closed-bar detection stamps entry in the *next* bar and anchors on
        # floor(entry_time) - 1h (both patterns are present in the observed
        # rows). Report the union so the diagnostic cannot be read as stricter
        # than the evidence supports. This is NOT part of the pre-registered
        # capture metric — capture stays observed_unique / design (audit §2).
        bar_set = set(bars)
        matched = len({
            k for k in all_keys
            if k[3] in bar_set or (k[3] - pd.Timedelta(hours=1)) in bar_set
        })
        matched_strict = len({k for k in all_keys if k[3] in bar_set})

        capture = (len(all_keys) / design_n) if design_n else float("nan")
        lo, hi = wilson(min(len(all_keys), design_n), design_n)
        per_seat[entry_type] = {
            "pair": pair,
            "vol_q": strat.cfg.vol_q,
            "horizon_bars": strat.cfg.horizon_bars,
            "design_expected": design_n,
            "design_bars": [str(b) for b in bars],
            "observed_live_unique": len(live_keys),
            "observed_shadow_unique": len(shadow_keys),
            "observed_unique_total": len(all_keys),
            "observed_rows_raw": len(rows),
            "observed_on_design_bar": matched,
            "observed_on_design_bar_strict": matched_strict,
            "capture": capture,
            "capture_wilson_lo": lo,
            "capture_wilson_hi": hi,
            "provenance": prov,
        }
        design_total += design_n
        live_total += len(live_keys)
        shadow_total += len(shadow_keys)
        matched_total += matched
        matched_strict_total += matched_strict

    observed_unique = live_total + shadow_total
    decision = decide_verdict(design_total, observed_unique, window_complete)
    lo, hi = wilson(min(observed_unique, design_total), design_total)
    return {
        "window": {
            "start": str(win_start),
            "end_frozen": str(win_end),
            "effective_end": str(effective_end),
            "complete": window_complete,
            "as_of": str(as_of),
        },
        "totals": {
            "design_expected": design_total,
            "observed_live_unique": live_total,
            "observed_shadow_unique": shadow_total,
            "observed_unique_total": observed_unique,
            "observed_on_design_bar": matched_total,
            "observed_on_design_bar_strict": matched_strict_total,
            "capture": decision["capture"],
            "capture_wilson_lo": lo,
            "capture_wilson_hi": hi,
        },
        "verdict": decision["verdict"],
        "verdict_reason": decision["reason"],
        "seats": per_seat,
    }


def render_text(res: dict) -> str:
    t = res["totals"]
    w = res["window"]
    lines = [
        "price_shock_rev seat-supply remeasure",
        f"window {w['start'][:16]} -> {w['effective_end'][:16]} "
        f"(frozen end {w['end_frozen'][:16]}, complete={w['complete']})",
        "",
        f"{'pair':8s} {'vol_q':5s} {'design':>6s} {'live':>5s} {'shadow':>6s} "
        f"{'uniq':>5s} {'on_bar':>6s} {'strict':>6s} {'capture':>8s}  wilson95",
    ]
    for et, s in res["seats"].items():
        cap = "n/a" if s["design_expected"] == 0 else f"{s['capture']:.0%}"
        wl = (
            "n/a"
            if s["design_expected"] == 0
            else f"[{s['capture_wilson_lo']:.0%}, {s['capture_wilson_hi']:.0%}]"
        )
        lines.append(
            f"{s['pair']:8s} {str(s['vol_q']):5s} {s['design_expected']:6d} "
            f"{s['observed_live_unique']:5d} {s['observed_shadow_unique']:6d} "
            f"{s['observed_unique_total']:5d} {s['observed_on_design_bar']:6d} "
            f"{s['observed_on_design_bar_strict']:6d} {cap:>8s}  {wl}"
        )
    cap = "n/a" if t["design_expected"] == 0 else f"{t['capture']:.0%}"
    lines += [
        f"{'TOTAL':8s} {'':5s} {t['design_expected']:6d} "
        f"{t['observed_live_unique']:5d} {t['observed_shadow_unique']:6d} "
        f"{t['observed_unique_total']:5d} {t['observed_on_design_bar']:6d} "
        f"{t['observed_on_design_bar_strict']:6d} {cap:>8s}  "
        f"[{t['capture_wilson_lo']:.0%}, {t['capture_wilson_hi']:.0%}]"
        if t["design_expected"]
        else f"{'TOTAL':8s} design=0",
        "",
        f"verdict: {res['verdict']} — {res['verdict_reason']}",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--trades-json", default=None, help="offline /api/demo/trades dump")
    parser.add_argument("--as-of", default=None, help="UTC instant of the run (default: now)")
    parser.add_argument("--no-topup", action="store_true",
                        help="skip the live MASSIVE top-up (frozen parquet only)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    fetcher = None
    if not args.no_topup:
        try:
            import os

            from dotenv import load_dotenv

            load_dotenv(ROOT / ".env")
            if not os.environ.get("MASSIVE_API_KEY"):
                # Worktrees carry no .env; fall back to the .env of the repo
                # that owns --cache-dir (<repo>/data/cache/massive → <repo>/.env),
                # same convention as tools/massive_gap_backfill.py.
                load_dotenv(Path(args.cache_dir).resolve().parents[2] / ".env")
        except ImportError:
            print("python-dotenv not installed; relying on ambient env", file=sys.stderr)
        from modules.data import fetch_ohlcv_massive

        fetcher = fetch_ohlcv_massive

    as_of = pd.Timestamp(args.as_of, tz="UTC") if args.as_of else pd.Timestamp.now(tz="UTC")
    observed = load_observed(args.trades_json, WINDOW_START[:10])
    res = remeasure(Path(args.cache_dir), observed, as_of, fetcher=fetcher)
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else render_text(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
