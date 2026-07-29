#!/usr/bin/env python3
"""price_shock_rev family: realized vs LOCKed-design horizon-exit counterfactual.

Re-scores shadow rows under the promotion-grid estimand and compares with the
realized (BE_LOCK / ATR-BE / trail / SIGNAL_REVERSE overlay) series. Analysis
harness for preserve-exit-overlay-2026-07-28.md §6 — no live behaviour.

Convention (verified 2026-07-28, §6.2 of that doc):
- live enters when the FORMING H1 bar's partial log-return first crosses the
  rolling 1%-tile, so the design anchor bar i = the bar containing entry_time.
- design exit = Close[i + horizon] (bar-index arithmetic, weekend-skipping),
  matching tools/price_shock_reversion_bt.py (signal bar i -> Close[i+h]).
- catastrophic SL = entry - 2 * vol20[i] * Close[i] * sqrt(20), checked on the
  Lows of bars i+1..i+h (vol20[i] full-bar model: median |err| 2.5p vs the 8
  preserved initial SLs; the vol20[i-1] model is worse at 6.5p).
- entry price is the actual row entry for both arms, so the paired diff
  isolates the exit path only.

Usage:
  python3 tools/price_shock_exit_counterfactual.py \
      --date-from 2026-04-10 [--trades-json dump.json] [--topup PAIR=path.parquet]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
API = "https://fx-ai-trader.onrender.com/api/demo/trades"
HORIZON = {
    "price_shock_rev_aud_jpy_h1_long": 12,
    "price_shock_rev_eur_aud_h1_long": 12,
    "price_shock_rev_nzd_jpy_h1_long": 12,
    "price_shock_rev_eur_gbp_h1_long": 3,
    "price_shock_rev_usd_cad_h1_long": 3,
}
BOOTSTRAP_B = 10_000
BOOTSTRAP_SEED = 20260728


def pip_mult(pair: str) -> float:
    return 100.0 if "JPY" in pair else 10000.0


def load_trades(trades_json: str | None, date_from: str) -> list[dict]:
    if trades_json:
        payload = json.load(open(trades_json))
    else:
        import requests

        resp = requests.get(
            API,
            params={"status": "closed", "date_from": date_from, "limit": 20000},
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()
    rows = [
        t for t in payload["trades"]
        if t.get("entry_type") in HORIZON and int(t.get("dedup_violation") or 0) != 1
    ]
    rows.sort(key=lambda t: t["entry_time"])
    return rows


def load_bars(pair: str, topup: dict[str, Path], cache_dir: Path) -> pd.DataFrame:
    df = pd.read_parquet(
        cache_dir / f"{pair}_1h_12y_audit.parquet"
    )[["Open", "High", "Low", "Close"]].copy()
    if pair in topup:
        fresh = pd.read_parquet(topup[pair])[["Open", "High", "Low", "Close"]]
        fresh = fresh.iloc[:-1]  # drop the still-forming last bar
        df = pd.concat([df, fresh[fresh.index > df.index.max()]])
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    lr = np.log(df["Close"] / df["Close"].shift(1))
    df["vol20"] = lr.rolling(20, min_periods=20).std()
    return df


def score(trade: dict, df: pd.DataFrame, exit_offset: int, sl_bar_offset: int) -> dict | None:
    """exit_offset: h (primary) or h-1 (S1); sl_bar_offset: 0 (vol20[i]) or -1 (S2)."""
    et = pd.Timestamp(trade["entry_time"])
    et = et.tz_localize("UTC") if et.tz is None else et.tz_convert("UTC")
    i = df.index.searchsorted(et, side="right") - 1  # forming bar at entry
    exit_i = i + exit_offset
    if exit_i >= len(df):
        return None
    entry = float(trade["entry_price"])
    pm = pip_mult(trade["instrument"])
    j = i + sl_bar_offset
    sl_dist = 2.0 * float(df["vol20"].iloc[j]) * float(df["Close"].iloc[j]) * math.sqrt(20)
    sl_level = entry - sl_dist
    window = df.iloc[i + 1: exit_i + 1]
    sl_hit = bool((window["Low"].to_numpy() <= sl_level).any())
    cf_exit = sl_level if sl_hit else float(df["Close"].iloc[exit_i])
    return {
        "cf_pnl": (cf_exit - entry) * pm,
        "cf_path": "sl_2atr" if sl_hit else "horizon",
        "sl_dist_pips": sl_dist * pm,
        "cf_exit_close": str(df.index[exit_i] + pd.Timedelta(hours=1))[:16],
    }


def series_stats(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    n = len(x)
    gross_profit = x[x > 0].sum()
    gross_loss = -x[x < 0].sum()
    pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
    return {
        "N": n,
        "EV": x.mean() if n else float("nan"),
        "WR": (x > 0).mean() if n else float("nan"),
        "PF": pf,
        "total": x.sum(),
    }


def fmt(s: dict) -> str:
    pf = "inf" if math.isinf(s["PF"]) else f"{s['PF']:.2f}"
    return (
        f"N={s['N']:2d} EV={s['EV']:+7.2f} WR={s['WR'] * 100:5.1f}% "
        f"PF={pf:>5} total={s['total']:+8.1f}p"
    )


def bootstrap_ci(rng: np.random.Generator, x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    means = np.array(
        [rng.choice(x, size=len(x), replace=True).mean() for _ in range(BOOTSTRAP_B)]
    )
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-from", default="2026-04-10")
    parser.add_argument("--trades-json", help="pre-fetched /api/demo/trades dump (skips the API call)")
    parser.add_argument(
        "--topup", action="append", default=[], metavar="PAIR=PARQUET",
        help="fresh H1 parquet appended after the 12y_audit cache (e.g. AUD_JPY=/tmp/aud.parquet)",
    )
    parser.add_argument("--out-csv", help="write the per-row table to this path")
    parser.add_argument(
        "--cache-dir", default=str(ROOT / "data" / "cache" / "massive"),
        help="directory holding {PAIR}_1h_12y_audit.parquet (worktrees lack it; point at the main checkout)",
    )
    args = parser.parse_args()

    topup = {}
    for item in args.topup:
        pair, _, path = item.partition("=")
        topup[pair] = Path(path)

    trades = load_trades(args.trades_json, args.date_from)
    print(f"population: closed, dedup_violation!=1, since {args.date_from} -> N={len(trades)}")
    cache_dir = Path(args.cache_dir)
    bars = {p: load_bars(p, topup, cache_dir) for p in {t["instrument"] for t in trades}}

    rows = []
    for t in trades:
        df = bars[t["instrument"]]
        h = HORIZON[t["entry_type"]]
        rec = {
            "id": t["id"],
            "cell": t["entry_type"].replace("price_shock_rev_", "").replace("_h1_long", ""),
            "h": h,
            "entry_time": t["entry_time"][:16],
            "realized_reason": t["close_reason"],
            "realized_pnl": float(t["pnl_pips"]),
        }
        primary = score(t, df, h, 0)
        if primary is None:
            rec["cf_status"] = "HORIZON_INCOMPLETE"
            rows.append(rec)
            continue
        rec["cf_status"] = "OK"
        rec.update({f"p_{k}": v for k, v in primary.items()})
        rec["s1_cf_pnl"] = score(t, df, h - 1, 0)["cf_pnl"]
        rec["s2_cf_pnl"] = score(t, df, h, -1)["cf_pnl"]
        rows.append(rec)

    out = pd.DataFrame(rows)
    pd.set_option("display.width", 300)
    print("\n=== per-row ===")
    print(out.to_string(index=False))

    paired = out[out["cf_status"] == "OK"].copy()
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    for label, col in [
        ("PRIMARY (exit Close[i+h], SL vol20[i])", "p_cf_pnl"),
        ("S1 (exit Close[i+h-1])", "s1_cf_pnl"),
        ("S2 (SL vol20[i-1])", "s2_cf_pnl"),
    ]:
        print(f"\n=== {label} ===")
        diffs = paired[col] - paired["realized_pnl"]
        for name, g in list(paired.groupby("cell")) + [("POOLED", paired)]:
            r, c = series_stats(g["realized_pnl"]), series_stats(g[col])
            d = (g[col] - g["realized_pnl"]).mean()
            print(f"{name:8s} realized {fmt(r)} | cf {fmt(c)} | dEV {d:+.2f} p/t")
        lo, hi = bootstrap_ci(rng, diffs.to_numpy())
        print(
            f"POOLED paired dEV: {diffs.mean():+.2f} p/t, "
            f"bootstrap 95% CI [{lo:+.2f}, {hi:+.2f}] (N={len(diffs)}, "
            f"B={BOOTSTRAP_B}, seed={BOOTSTRAP_SEED})"
        )

    if args.out_csv:
        out.to_csv(args.out_csv, index=False)
        print(f"\nper-row csv -> {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
