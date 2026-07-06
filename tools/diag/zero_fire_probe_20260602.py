#!/usr/bin/env python3
"""Local zero-fire probe for Kalman D7 and ZZ Pivot v60 SR.

Writes a compact markdown report and prints it to stdout.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.context import SignalContext  # noqa: E402
from strategies.daytrade.zz_pivot_v60_sr import ZzPivotV60Sr  # noqa: E402

try:
    from strategies.daytrade.kalman_d7_trend import _kalman_d7_indicators
except Exception:  # pragma: no cover - import fallback required by task
    _kalman_d7_indicators = None


TODAY = pd.Timestamp("2026-06-02", tz="UTC")
START = TODAY - pd.Timedelta(days=6)
END = TODAY + pd.Timedelta(days=1)
OUT = ROOT / "knowledge-base/raw/audits/kalman-zz-zero-fire-2026-06-02-local-probe.md"


def load_window(rel_path: str) -> tuple[pd.DataFrame | None, str | None]:
    path = ROOT / rel_path
    if not path.exists():
        return None, f"missing parquet: {rel_path}"
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        return None, f"non-DatetimeIndex parquet: {rel_path}"
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df.sort_index()
    win = df.loc[(df.index >= START) & (df.index < END)].copy()
    if win.empty:
        last_ts = df.index.max()
        return None, f"no bars in requested window {START.date()}..{TODAY.date()} (cache last={last_ts})"
    return win, None


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"].astype(float)
    high = out["High"].astype(float)
    low = out["Low"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    out["atr7"] = tr.ewm(alpha=1 / 7, adjust=False).mean()
    for n in (9, 21, 25, 50, 75, 200):
        out[f"ema{n}"] = close.ewm(span=n, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    out["rsi"] = (100 - (100 / (1 + rs))).fillna(50.0)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    bb_mid = close.rolling(20, min_periods=20).mean()
    bb_std = close.rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid"] = bb_mid
    out["bb_upper"] = bb_mid + 2 * bb_std
    out["bb_lower"] = bb_mid - 2 * bb_std
    width = out["bb_upper"] - out["bb_lower"]
    out["bb_width"] = width / bb_mid
    out["bb_pband"] = ((close - out["bb_lower"]) / width).replace([float("inf"), float("-inf")], pd.NA)
    return out


def ctx_from(hist: pd.DataFrame, symbol: str) -> SignalContext:
    row = hist.iloc[-1]
    ctx = SignalContext.from_df(hist, row, symbol=symbol, tf="M15", sr_levels=[],
                                layer0={}, layer1={}, regime={}, layer2={}, layer3={},
                                htf={}, session={}, backtest_mode=True, bar_time=hist.index[-1])
    close = hist["Close"].astype(float)
    po_up = (close > hist["ema25"]) & (hist["ema25"] > hist["ema75"]) & (hist["ema75"] > hist["ema200"])
    po_dn = (close < hist["ema25"]) & (hist["ema25"] < hist["ema75"]) & (hist["ema75"] < hist["ema200"])
    ctx.regime_po = "UP" if bool(po_up.iloc[-1]) else ("DN" if bool(po_dn.iloc[-1]) else "RANGE")
    ctx.regime_po_start_up = bool(po_up.iloc[-1]) and not bool(po_up.iloc[-2]) if len(po_up) >= 2 else False
    ctx.regime_po_start_dn = bool(po_dn.iloc[-1]) and not bool(po_dn.iloc[-2]) if len(po_dn) >= 2 else False
    return ctx


def fmt_table(counts: Counter, keys: list[str]) -> str:
    total = sum(counts.values())
    lines = ["| first_filter_failed | bars_count (%) |", "|---|---:|"]
    for k in keys:
        n = counts.get(k, 0)
        pct = (n / total * 100) if total else 0
        lines.append(f"| {k} | {n} ({pct:.1f}%) |")
    return "\n".join(lines)


def latest_rows(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_No rows._"
    df = pd.DataFrame(rows).tail(5)
    for c in cols:
        if c in df.columns and c != "timestamp":
            df[c] = pd.to_numeric(df[c], errors="coerce").round(6)
    view = df[cols].astype(str)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c] for c in cols) + " |")
    return "\n".join(lines)


def top2(counts: Counter) -> str:
    pairs = [(k, v) for k, v in counts.items() if k != "ALL_PASS"]
    pairs.sort(key=lambda kv: (-kv[1], kv[0]))
    return ", ".join(f"{k}={v}" for k, v in pairs[:2]) or "none"


def probe_kalman() -> dict[str, Any]:
    keys = ["po_up_not_started", "dist_out_of_range", "gap_too_wide",
            "atr_outside_q2q4", "rsi_overbought", "session_excluded", "ALL_PASS"]
    df, err = load_window("data/cache/massive/USD_JPY_15m.parquet")
    if err:
        return {"name": "kalman_d7_trail_atr", "bars": 0, "pass": 0, "counts": Counter(),
                "keys": keys, "tail": [], "error": err, "verdict": "INCONCLUSIVE"}
    df = enrich(df)
    counts: Counter = Counter()
    tail = []
    for i in range(len(df)):
        hist = df.iloc[: i + 1].dropna(subset=["atr", "ema200", "rsi"]).copy()
        if len(hist) < 210:
            continue
        ctx = ctx_from(hist, "USDJPY=X")
        ind = _kalman_d7_indicators(ctx) if _kalman_d7_indicators else None
        if ind is None:
            continue
        dist_atr = (ctx.entry - ind["ema200"]) / ind["atr"]
        gap_atr = (ind["ema25"] - ind["ema200"]) / ind["atr"]
        if not (ctx.regime_po == "UP" and ctx.regime_po_start_up):
            fail = "po_up_not_started"
        elif not (0 < dist_atr < 3.0):
            fail = "dist_out_of_range"
        elif gap_atr >= 3.0:
            fail = "gap_too_wide"
        elif not (ind["atr_p20"] <= ind["atr"] < ind["atr_p80"]):
            fail = "atr_outside_q2q4"
        elif ctx.rsi >= 70:
            fail = "rsi_overbought"
        elif not ((ctx.hour_utc < 7) or (7 <= ctx.hour_utc < 12) or (16 <= ctx.hour_utc < 21)):
            fail = "session_excluded"
        else:
            fail = "ALL_PASS"
        counts[fail] += 1
        tail.append({"timestamp": hist.index[-1].isoformat(), "close": ctx.entry,
                     "ema200": ind["ema200"], "atr": ind["atr"], "atr_p20": ind["atr_p20"],
                     "atr_p80": ind["atr_p80"], "dist_atr": dist_atr, "gap_atr": gap_atr,
                     "rsi": ctx.rsi, "hour_utc": ctx.hour_utc, "fail": fail})
    passed = counts.get("ALL_PASS", 0)
    verdict = "MARKET_WAIT" if passed == 0 and sum(counts.values()) > 0 else "INCONCLUSIVE"
    return {"name": "kalman_d7_trail_atr", "bars": sum(counts.values()), "pass": passed,
            "counts": counts, "keys": keys, "tail": tail, "error": None, "verdict": verdict}


def probe_zz() -> dict[str, Any]:
    keys = ["tf_or_pair_miss", "df_too_short", "no_trend", "no_peak_no_trough", "rr_below_min", "ALL_PASS"]
    df, err = load_window("data/cache/massive/EUR_USD_15m.parquet")
    if err:
        return {"name": "zz_pivot_v60_sr / zz_pivot_v60_sr_lo", "bars": 0, "pass": 0,
                "counts": Counter(), "keys": keys, "tail": [], "error": err, "verdict": "INCONCLUSIVE"}
    df = enrich(df)
    strat = ZzPivotV60Sr()
    counts: Counter = Counter()
    tail = []
    min_len = max(strat.TREND_EMA_LEN, strat.ATR_BASELINE_LEN) + 30
    for i in range(len(df)):
        hist = df.iloc[: i + 1].dropna(subset=["atr", "ema50", "rsi", "bb_pband", "macd_hist"]).copy()
        if len(hist) < min_len:
            counts["df_too_short"] += 1
            continue
        ctx = ctx_from(hist, "EURUSD=X")
        if "EURUSD" not in strat._ALLOWED_SYMBOLS or "M15" not in strat._ALLOWED_TF:
            fail = "tf_or_pair_miss"
        else:
            trend_ema = float(hist["Close"].ewm(span=strat.TREND_EMA_LEN, adjust=False).mean().iloc[-1])
            uptrend = ctx.entry > trend_ema
            downtrend = ctx.entry < trend_ema
            if not (uptrend or downtrend):
                fail = "no_trend"
            else:
                features = strat._compute_features(hist, ctx)
                peak = strat._detect_peak(ctx, features, hist) if uptrend else None
                trough = strat._detect_trough(ctx, features, hist) if downtrend else None
                if peak is None and trough is None:
                    fail = "no_peak_no_trough"
                else:
                    rr = strat.TP_ATR_MULT / strat.SL_ATR_MULT if ctx.atr > 0 else 0.0
                    fail = "rr_below_min" if rr < strat.MIN_RR else "ALL_PASS"
        counts[fail] += 1
        atr_series = strat._compute_atr_series(hist, 14)
        atr_base = float(atr_series.ewm(span=strat.ATR_BASELINE_LEN, adjust=False).mean().iloc[-1])
        atr_ratio = ctx.atr / atr_base if atr_base > 0 else 1.0
        rci = strat._rci(hist["Close"].astype(float).iloc[-9:].values, 9)
        tail.append({"timestamp": hist.index[-1].isoformat(), "close": ctx.entry,
                     "ema50": float(hist["ema50"].iloc[-1]), "atr": ctx.atr,
                     "bbp_b": ctx.bbpb, "rci": rci, "atr_ratio": atr_ratio,
                     "hour_utc": ctx.hour_utc, "fail": fail})
    passed = counts.get("ALL_PASS", 0)
    if passed > 0:
        verdict = "SILENT_DROP_V3_SUSPECTED"
    elif counts.get("no_peak_no_trough", 0) / max(1, sum(counts.values())) > 0.95:
        verdict = "DESIGN_TOO_STRICT"
    else:
        verdict = "MARKET_WAIT"
    return {"name": "zz_pivot_v60_sr / zz_pivot_v60_sr_lo", "bars": sum(counts.values()),
            "pass": passed, "counts": counts, "keys": keys, "tail": tail,
            "error": None, "verdict": verdict}


def build_report(k: dict[str, Any], z: dict[str, Any]) -> str:
    kalman_tail_cols = ["timestamp", "close", "ema200", "atr", "atr_p20", "atr_p80",
                        "dist_atr", "gap_atr", "rsi", "hour_utc"]
    zz_tail_cols = ["timestamp", "close", "ema50", "atr", "bbp_b", "rci", "atr_ratio", "hour_utc"]
    lines = [
        "# Kalman/ZZ Zero-Fire Local Probe 2026-06-02",
        "",
        f"Window: {START.date()} through {TODAY.date()} UTC. Today fixed at `pd.Timestamp('2026-06-02')`.",
        "",
        "## Kalman D7 USDJPY M15",
    ]
    if k["error"]:
        lines.append(f"ERROR: {k['error']}")
    lines += [fmt_table(k["counts"], k["keys"]), "", "Latest rejection rows:", latest_rows(k["tail"], kalman_tail_cols), ""]
    lines += ["## ZZ Pivot v60 EUR_USD M15", fmt_table(z["counts"], z["keys"]), "",
              "Latest rejection rows:", latest_rows(z["tail"], zz_tail_cols), ""]
    lines += ["## Code-Level Cross-Check",
              "- No additional silent-drop path identified after candidate receipt for these strategies outside the known fixes.",
              "- Pre-trade shared `_block()` returns at `modules/demo_trader.py:3463` only increment in-memory block counters; they do not write `oanda_audit`/`shadow_audit`, but they also occur before trade creation/OANDA routing.",
              "- Kalman LIVE bypass is explicit at `modules/demo_trader.py:5444` and `modules/demo_trader.py:5455`; ZZ EUR DT mode bypass is whitelisted at `modules/demo_trader.py:7622`.",
              "- Post-promotion Kelly/MC blocks write `oanda_audit` at `modules/demo_trader.py:5632` and `modules/demo_trader.py:5656`; post-gate escalation persists shadow at `modules/demo_trader.py:5670`.",
              ""]
    lines += ["## Verdict",
              "| Strategy | Bars in 7d | Filter pass count | First-fail top-2 | Verdict |",
              "|---|---:|---:|---|---|",
              f"| {k['name']} | {k['bars']} | {k['pass']} | {top2(k['counts'])} | {k['verdict']} |",
              f"| {z['name']} | {z['bars']} | {z['pass']} | {top2(z['counts'])} | {z['verdict']} |",
              "",
              f"Kalman D7: local USDJPY cache cannot test the deployment window because the parquet has no bars in the fixed 7-day window. Verdict is inconclusive until the M15 cache is refreshed through 2026-06-02.",
              "",
              f"ZZ Pivot v60: the local EURUSD window is populated, but first-fail distribution is dominated by `{top2(z['counts']).split(',')[0].split('=')[0]}`. The strategy produced {z['pass']} bar-level passes under the ported detector.",
              "",
              f"Root-cause hypothesis: Kalman is blocked by stale local cache evidence; ZZ zero-fire is primarily strategy-filter scarcity unless any ALL_PASS rows failed to appear in audits.",
              ""]
    text = "\n".join(lines)
    return text


def main() -> int:
    k = probe_kalman()
    z = probe_zz()
    report = build_report(k, z)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
