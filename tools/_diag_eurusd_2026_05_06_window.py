#!/usr/bin/env python3
"""One-off: fetch EUR_USD M15 from OANDA for 2026-05-03 → 2026-05-06 12:00 UTC,
compute v15m indicators (EMA25/75/200, RSI, ATR, perfect_up strict/relaxed,
pup_start/pup_start_rel, RSI_d3) and dump the 5/5 14:00 UTC → 5/6 06:00 UTC
window bar-by-bar to reason about why v15m didn't fire at "5/6 00:00 JST".

Run from repo root:  python3 tools/_diag_eurusd_2026_05_06_window.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env (project convention; OANDA_TOKEN, OANDA_ACCOUNT_ID)
def _load_env():
    p = ROOT / ".env"
    if not p.exists():
        return
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

_load_env()

from cfd_trader.data.oanda_client import OandaClient  # noqa: E402


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr_calc(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi_calc(s, n=14):
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def main():
    token = os.environ.get("OANDA_TOKEN", "")
    acct = os.environ.get("OANDA_ACCOUNT_ID", "")
    env = os.environ.get("OANDA_ENV", "live")  # default to live: real prices
    if not token or not acct:
        print("ERROR: OANDA_TOKEN / OANDA_ACCOUNT_ID required in .env")
        sys.exit(1)
    cli = OandaClient(token=token, account_id=acct, env=env)

    # Fetch 5/3 00:00 UTC → 5/6 12:00 UTC (= 5/6 21:00 JST) M15
    # That's ~84h = 336 M15 bars, well under 5000 cap
    df = cli.get_candles(
        instrument="EUR_USD",
        granularity="M15",
        from_iso="2026-05-03T00:00:00Z",
        to_iso="2026-05-06T12:00:00Z",
        price="M",
    )
    if df.empty:
        print("ERROR: OANDA returned 0 candles")
        sys.exit(2)
    df = df.set_index("time").sort_index()
    c = df["close"]

    df["ema_fast"] = ema(c, 25)
    df["ema_mid"] = ema(c, 75)
    df["ema_slow"] = ema(c, 200)
    df["atr"] = atr_calc(df, 14)
    df["rsi"] = rsi_calc(c, 14)

    df["perfect_up"] = (df["ema_fast"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_slow"]) & (c > df["ema_fast"])
    df["pu_relaxed"] = (df["ema_fast"] > df["ema_mid"]) & (c > df["ema_fast"])
    df["perfect_dn"] = (df["ema_slow"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_fast"])

    # bridge / persistent_up reconstruction (strict)
    max_gap = 10
    n = len(df)
    pu = df["perfect_up"].values
    pdn = df["perfect_dn"].values
    bspu = np.empty(n, dtype=np.int64)
    cur = 9999
    for i in range(n):
        if pu[i]:
            cur = 0
        elif pdn[i]:
            cur = 9999
        else:
            cur += 1
        bspu[i] = cur
    df["bspu"] = bspu
    neutral = (~df["perfect_up"]) & (~df["perfect_dn"])
    df["persistent_up"] = df["perfect_up"] | (neutral & (df["bspu"] <= max_gap))
    df["pup_start"] = df["persistent_up"] & ~df["persistent_up"].shift(1, fill_value=False)

    # relaxed bridge
    pur = df["pu_relaxed"].values
    bspu_r = np.empty(n, dtype=np.int64)
    cur = 9999
    for i in range(n):
        if pur[i]:
            cur = 0
        elif pdn[i]:
            cur = 9999
        else:
            cur += 1
        bspu_r[i] = cur
    df["bspu_rel"] = bspu_r
    neutral_r = (~df["pu_relaxed"]) & (~df["perfect_dn"])
    df["persistent_up_rel"] = df["pu_relaxed"] | (neutral_r & (df["bspu_rel"] <= max_gap))
    df["pup_start_rel"] = df["persistent_up_rel"] & ~df["persistent_up_rel"].shift(1, fill_value=False)

    df["rsi_d3"] = df["rsi"] - df["rsi"].shift(3)
    df["pdn_in_50"] = df["perfect_dn"].rolling(50).sum()

    # Focus window: 5/5 14:00 UTC → 5/6 06:00 UTC
    win = df.loc["2026-05-05 14:00":"2026-05-06 06:00"].copy()
    print(f"=== EUR_USD M15 — 2026-05-05 14:00 UTC → 2026-05-06 06:00 UTC ({len(win)} bars) ===")
    print(f"(5/6 00:00 JST = 5/5 15:00 UTC)\n")

    # Bar dump
    cols_fmt = ("time_utc           close   ema25   ema75   ema200    rsi  d3  "
                "PU PUr pSTR pSTRr pdn50 atr")
    print(cols_fmt)
    print("-" * len(cols_fmt))
    for ts, row in win.iterrows():
        marker = ""
        # JST midnight (= 15:00 UTC) marker
        if ts.strftime("%H:%M") == "15:00":
            marker = "  <-- 5/6 00:00 JST"
        print(
            f"{ts.strftime('%Y-%m-%d %H:%M')}  "
            f"{row['close']:.5f}  {row['ema_fast']:.5f}  {row['ema_mid']:.5f}  "
            f"{row['ema_slow']:.5f}  {row['rsi']:5.1f}  {row['rsi_d3']:+5.1f}  "
            f"{int(bool(row['perfect_up']))}   {int(bool(row['pu_relaxed']))}   "
            f"{int(bool(row['pup_start']))}    {int(bool(row['pup_start_rel']))}    "
            f"{row['pdn_in_50']:5.0f}  {row['atr']:.5f}"
            + marker
        )

    # Summary
    print("\n=== Summary in window ===")
    print(f"strict perfect_up bars      : {int(win['perfect_up'].sum())} / {len(win)}")
    print(f"relaxed perfect_up bars     : {int(win['pu_relaxed'].sum())} / {len(win)}")
    print(f"strict  pup_start  triggers : {int(win['pup_start'].sum())}")
    print(f"relaxed pup_start_rel trigs : {int(win['pup_start_rel'].sum())}")

    # Would v15m primary/secondary have fired?
    def classify(row):
        rsi_v = row["rsi"]
        pdn50 = row["pdn_in_50"]
        prim = rsi_v >= 65
        sec = (rsi_v < 65) and (not np.isnan(pdn50)) and (pdn50 >= 30)
        if prim:
            return "PRIMARY"
        if sec:
            return "SECONDARY"
        return "NEITHER (rsi<65 & pdn50<30)"

    print("\n=== Triggers in window (would v15m enter?) ===")
    for ts, row in win.iterrows():
        if row["pup_start"]:
            print(f"  STRICT  pup_start @ {ts.strftime('%Y-%m-%d %H:%M')} UTC  "
                  f"rsi={row['rsi']:.1f} pdn50={row['pdn_in_50']:.0f}  -> {classify(row)}")
        if row["pup_start_rel"] and not row["pup_start"]:
            print(f"  RELAXED pup_start @ {ts.strftime('%Y-%m-%d %H:%M')} UTC  "
                  f"rsi={row['rsi']:.1f} pdn50={row['pdn_in_50']:.0f}  -> {classify(row)} (would need v15n)")


if __name__ == "__main__":
    main()
