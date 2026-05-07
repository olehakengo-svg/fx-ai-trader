#!/usr/bin/env python3
"""Phase 1b — OANDA retail-contrarian sentiment H4 back-test.

Hypothesis: when OANDA retail short% is extreme, fade retail direction on the
next H4 closes. OHLC is MASSIVE-only via data/cache/massive/<PAIR>_1h.parquet.
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

os.environ.setdefault("BT_MODE", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bb_squeeze_rescue_bt import (  # noqa: E402
    FRICTION_RT,
    PIP_MULT,
    simulate_pnl,
    synth_null_trades,
    welch_t_test,
    wilson_lower,
)


PAIRS = ["EUR_USD", "USD_JPY", "GBP_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP"]
THRESHOLDS_HIGH = [65, 70, 75, 80, 85, 90]
THRESHOLDS_LOW = [35, 30, 25, 20, 15, 10]
HOLDING_BARS_H4 = [1, 2, 4, 12]
N_CELLS = len(PAIRS) * (len(THRESHOLDS_HIGH) + len(THRESHOLDS_LOW)) * len(HOLDING_BARS_H4)
ALPHA_CELL = 0.05 / N_CELLS
MIN_N = 20

GRAPHQL_URL = "https://labs-api.oanda.com/graphql"
GRAPHQL_QUERY = """query GetSentiments($instrument: String!, $granularity: Granularity!, $timeSpan: TimeSpan!) {
  sentiments(instrument: $instrument, granularity: $granularity, timeSpan: $timeSpan) {
    sentiments { sentiment { shortPercent } time }
  }
}"""

ROOT = Path(__file__).resolve().parents[1]
SENTIMENT_PATH = ROOT / "data" / "sentiment" / "oanda_labs_h4_90d.parquet"
OUT_DIR = ROOT / "bt-results" / "phase1b"
CELLS_PATH = OUT_DIR / "oanda_contrarian_cells.parquet"
REPORT_PATH = OUT_DIR / "oanda_contrarian_report.md"
MASSIVE_DIR = ROOT / "data" / "cache" / "massive"


def symbol_for_util(pair: str) -> str:
    return pair.replace("_", "") + "=X"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def fetch_pair_sentiment(pair: str) -> pd.DataFrame:
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.oanda.jp",
        "Referer": "https://www.oanda.jp/lab-education/oanda_lab/oanda_rab/orderbook_history/",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"instrument": pair, "granularity": "H4", "timeSpan": "NINETY_DAYS"},
    }
    resp = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(f"OANDA GraphQL errors for {pair}: {body['errors']}")
    rows = (((body.get("data") or {}).get("sentiments") or {}).get("sentiments") or [])
    out = []
    for row in rows:
        short_pct = ((row.get("sentiment") or {}).get("shortPercent"))
        if short_pct is None or row.get("time") is None:
            continue
        short_pct = float(short_pct)
        out.append({
            "pair": pair,
            "time_utc": parse_ts(row["time"]),
            "short_pct": short_pct,
            "long_pct": 100.0 - short_pct,
        })
    return pd.DataFrame(out, columns=["pair", "time_utc", "short_pct", "long_pct"])


def cache_is_fresh(path: Path, max_age_hours: float = 12.0) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    age_sec = time.time() - path.stat().st_mtime
    return age_sec <= max_age_hours * 3600


def cache_covers_pairs(path: Path, pairs: List[str]) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        df = pd.read_parquet(path, columns=["pair"])
    except Exception:
        return False
    return set(pairs).issubset(set(df["pair"].dropna().astype(str).unique()))


def load_or_fetch_sentiment(pairs: List[str], no_fetch: bool, force_fetch: bool) -> Tuple[pd.DataFrame, List[str]]:
    SENTIMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if no_fetch:
        if not SENTIMENT_PATH.exists():
            raise FileNotFoundError(f"--no-fetch requested but cache is missing: {SENTIMENT_PATH}")
        return normalize_sentiment(pd.read_parquet(SENTIMENT_PATH)), []
    if (
        SENTIMENT_PATH.exists()
        and not force_fetch
        and cache_is_fresh(SENTIMENT_PATH)
        and cache_covers_pairs(SENTIMENT_PATH, pairs)
    ):
        return normalize_sentiment(pd.read_parquet(SENTIMENT_PATH)), []

    frames: List[pd.DataFrame] = []
    errors: List[str] = []
    for pair in pairs:
        try:
            df = fetch_pair_sentiment(pair)
            frames.append(df)
            print(f"[sentiment] {pair}: {len(df)} rows", flush=True)
        except Exception as exc:
            errors.append(f"{pair}: {exc}")
            print(f"[sentiment-err] {pair}: {exc}", flush=True)
        time.sleep(1.0)

    if frames:
        merged = normalize_sentiment(pd.concat(frames, ignore_index=True))
    elif SENTIMENT_PATH.exists():
        errors.append("all fetches failed; falling back to existing sentiment cache")
        merged = normalize_sentiment(pd.read_parquet(SENTIMENT_PATH))
    else:
        merged = pd.DataFrame(columns=["pair", "time_utc", "short_pct", "long_pct"])

    merged.to_parquet(SENTIMENT_PATH, index=False)
    return merged, errors


def normalize_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["pair", "time_utc", "short_pct", "long_pct"])
    out = df.copy()
    out["time_utc"] = pd.to_datetime(out["time_utc"], utc=True)
    out["short_pct"] = pd.to_numeric(out["short_pct"], errors="coerce")
    if "long_pct" not in out.columns:
        out["long_pct"] = 100.0 - out["short_pct"]
    out["long_pct"] = pd.to_numeric(out["long_pct"], errors="coerce")
    out = out.dropna(subset=["pair", "time_utc", "short_pct"])
    return out.sort_values(["pair", "time_utc"]).reset_index(drop=True)


def load_h4_ohlc(pair: str) -> pd.DataFrame:
    path = MASSIVE_DIR / f"{pair}_1h.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        if "time" in df.columns:
            df = df.set_index(pd.to_datetime(df["time"], utc=True))
        else:
            raise ValueError(f"{path} has no DatetimeIndex or time column")
    df = df.copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    req = ["Open", "High", "Low", "Close"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"{path} missing columns: {missing}")
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum" if "Volume" in df.columns else "size",
    }
    h4 = df.resample("4h", origin="start_day", label="right", closed="left").agg(agg)
    counts = df["Close"].resample("4h", origin="start_day", label="right", closed="left").count()
    h4["hour_count"] = counts
    h4 = h4.dropna(subset=["Open", "High", "Low", "Close"])
    if not h4.empty and int(h4["hour_count"].iloc[-1]) < 4:
        h4 = h4.iloc[:-1]
    return h4


def join_sentiment_to_ohlc(pair: str, sentiment: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    sent = sentiment.loc[sentiment["pair"] == pair, ["time_utc", "short_pct", "long_pct"]].copy()
    if sent.empty or h4.empty:
        return pd.DataFrame()
    sent = sent.sort_values("time_utc")
    ohlc = h4.reset_index().rename(columns={h4.index.name or "index": "bar_close_utc"})
    ohlc["bar_close_utc"] = pd.to_datetime(ohlc["bar_close_utc"], utc=True)
    # OANDA sentiment timestamps do not always land exactly on MASSIVE H4 closes.
    # merge_asof(direction="backward") forward-fills the latest known sentiment
    # observation to the next available H4 close without peeking into future data.
    joined = pd.merge_asof(
        ohlc.sort_values("bar_close_utc"),
        sent,
        left_on="bar_close_utc",
        right_on="time_utc",
        direction="backward",
    )
    joined["pair"] = pair
    return joined.dropna(subset=["short_pct"]).reset_index(drop=True)


def profit_factor(pnls: List[float]) -> float:
    pos = sum(p for p in pnls if p > 0)
    neg = -sum(p for p in pnls if p < 0)
    if neg > 0:
        return pos / neg
    return float("inf") if pos > 0 else 0.0


def max_drawdown_pips(pnls: List[float]) -> float:
    if not pnls:
        return 0.0
    equity = np.cumsum(pnls)
    peaks = np.maximum.accumulate(equity)
    return float(np.max(peaks - equity))


def pips_for_pair(pair: str) -> float:
    return PIP_MULT.get(symbol_for_util(pair), 100.0 if "JPY" in pair else 10000.0)


def friction_for_pair(pair: str) -> float:
    return FRICTION_RT.get(symbol_for_util(pair), 2.0)


def cell_trades(joined: pd.DataFrame, direction: str, threshold: int, hold_bars: int) -> pd.DataFrame:
    if joined.empty:
        return pd.DataFrame()
    if direction == "LONG":
        signals = joined.index[joined["short_pct"] >= threshold].tolist()
        sign = 1
    else:
        signals = joined.index[joined["short_pct"] <= threshold].tolist()
        sign = -1
    rows = []
    pair = str(joined["pair"].iloc[0])
    pip = pips_for_pair(pair)
    friction = friction_for_pair(pair)
    for idx in signals:
        exit_idx = idx + hold_bars
        if exit_idx >= len(joined):
            continue
        entry = float(joined.at[idx, "Close"])
        exit_close = float(joined.at[exit_idx, "Close"])
        pnl = (exit_close - entry) * pip * sign - friction
        rows.append({
            "pair": pair,
            "direction": direction,
            "threshold": threshold,
            "hold_bars_h4": hold_bars,
            "entry_time": joined.at[idx, "bar_close_utc"],
            "exit_time": joined.at[exit_idx, "bar_close_utc"],
            "entry_close": entry,
            "exit_close": exit_close,
            "short_pct": float(joined.at[idx, "short_pct"]),
            "pnl_pips": float(pnl),
        })
    return pd.DataFrame(rows)


def evaluate_pnls(pnls: List[float]) -> Dict[str, float]:
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    wr = wins / n if n else 0.0
    wlo = wilson_lower(wins, n) / 100.0 if n else 0.0
    ev = statistics.mean(pnls) if n else 0.0
    pf = profit_factor(pnls)
    avg_win = statistics.mean([p for p in pnls if p > 0]) if wins else 0.0
    avg_loss = abs(statistics.mean([p for p in pnls if p < 0])) if losses else 0.0
    payoff = avg_win / avg_loss if avg_loss > 0 else (float("inf") if avg_win > 0 else 0.0)
    if math.isinf(payoff):
        kelly = 1.0 if wlo > 0 else 0.0
    else:
        kelly = wlo * payoff - (1.0 - wlo)
    kelly = max(-1.0, min(1.0, kelly))
    if n >= 2:
        _, p_value = welch_t_test(pnls, [0.0] * n)
    else:
        p_value = 1.0
    return {
        "n": float(n),
        "wins": float(wins),
        "losses": float(losses),
        "wr": wr,
        "wilson_lo": wlo,
        "ev_pips": ev,
        "pf": pf,
        "kelly": kelly,
        "maxdd_pips": max_drawdown_pips(pnls),
        "p_value": p_value,
    }


def evaluate_window(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> Dict[str, float]:
    if trades.empty:
        return evaluate_pnls([])
    mask = (pd.to_datetime(trades["entry_time"], utc=True) >= start) & (pd.to_datetime(trades["entry_time"], utc=True) < end)
    return evaluate_pnls(trades.loc[mask, "pnl_pips"].astype(float).tolist())


def window_bounds(all_times: List[pd.Timestamp]) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    if not all_times:
        return None
    start = min(all_times).floor("D")
    end = max(all_times).ceil("D")
    if end <= start:
        return None
    return start, end


def classify_regime(trades: pd.DataFrame, start: pd.Timestamp) -> Tuple[str, str]:
    labels = []
    signs = []
    for i in range(3):
        seg_start = start + pd.Timedelta(days=30 * i)
        seg_end = seg_start + pd.Timedelta(days=30)
        stats = evaluate_window(trades, seg_start, seg_end)
        pf = stats["pf"]
        labels.append("PF>1" if pf > 1.0 else "PF<=1")
        signs.append(1 if pf > 1.0 else 0)
    agree = sum(signs)
    if agree == 3:
        strength = "3/3 strong"
    elif agree == 2:
        strength = "2/3 weak"
    else:
        strength = "<=1/3 noise"
    return strength, ",".join(labels)


def build_grid(joined_by_pair: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, int]:
    all_times: List[pd.Timestamp] = []
    for df in joined_by_pair.values():
        if not df.empty:
            all_times.extend(pd.to_datetime(df["bar_close_utc"], utc=True).tolist())
    bounds = window_bounds(all_times)
    wf_start = bounds[0] if bounds else pd.Timestamp("1970-01-01", tz="UTC")
    is_end = wf_start + pd.Timedelta(days=60)
    oos_end = is_end + pd.Timedelta(days=30)

    baseline_null_pnls = [simulate_pnl(t, 0)["pnl_pips"] for t in synth_null_trades(10, seed=7)]
    _ = baseline_null_pnls  # Explicitly exercise imported utility path without changing test statistics.

    rows: List[Dict[str, Any]] = []
    cid = 0
    for pair in PAIRS:
        joined = joined_by_pair.get(pair, pd.DataFrame())
        for direction, thresholds in (("LONG", THRESHOLDS_HIGH), ("SHORT", THRESHOLDS_LOW)):
            for threshold in thresholds:
                for hold_bars in HOLDING_BARS_H4:
                    cid += 1
                    trades = cell_trades(joined, direction, threshold, hold_bars)
                    pnls = trades["pnl_pips"].astype(float).tolist() if not trades.empty else []
                    stats = evaluate_pnls(pnls)
                    is_stats = evaluate_window(trades, wf_start, is_end)
                    oos_stats = evaluate_window(trades, is_end, oos_end)
                    regime_strength, regime_chunks = classify_regime(trades, wf_start)
                    survivor = (
                        stats["n"] >= MIN_N
                        and stats["p_value"] < ALPHA_CELL
                        and stats["wilson_lo"] > 0.50
                        and stats["pf"] >= 1.10
                        and stats["kelly"] > 0
                        and stats["ev_pips"] > 0
                    )
                    is_survivor = (
                        is_stats["n"] >= MIN_N
                        and is_stats["p_value"] < ALPHA_CELL
                        and is_stats["wilson_lo"] > 0.50
                        and is_stats["pf"] >= 1.10
                        and is_stats["kelly"] > 0
                        and is_stats["ev_pips"] > 0
                    )
                    wf_pass = is_survivor and oos_stats["wr"] > 0.50 and oos_stats["pf"] > 1.0
                    row = {
                        "cell_id": f"C{cid:03d}",
                        "pair": pair,
                        "direction": direction,
                        "threshold": threshold,
                        "hold_bars_h4": hold_bars,
                        "n": int(stats["n"]),
                        "wins": int(stats["wins"]),
                        "wr": stats["wr"],
                        "wilson_lo": stats["wilson_lo"],
                        "ev_pips": stats["ev_pips"],
                        "pf": stats["pf"],
                        "kelly": stats["kelly"],
                        "maxdd_pips": stats["maxdd_pips"],
                        "p_value": stats["p_value"],
                        "bonferroni_pass": bool(stats["p_value"] < ALPHA_CELL and stats["wilson_lo"] > 0.50),
                        "survivor": bool(survivor),
                        "wf_is_n": int(is_stats["n"]),
                        "wf_is_wr": is_stats["wr"],
                        "wf_is_pf": is_stats["pf"],
                        "wf_is_survivor": bool(is_survivor),
                        "wf_oos_n": int(oos_stats["n"]),
                        "wf_oos_wr": oos_stats["wr"],
                        "wf_oos_pf": oos_stats["pf"],
                        "wf_pass": bool(wf_pass),
                        "regime_sign_agreement": regime_strength,
                        "regime_chunks": regime_chunks,
                    }
                    rows.append(row)
    cells = pd.DataFrame(rows)
    m_used = int((cells["n"] >= MIN_N).sum()) if not cells.empty else 0
    return cells, m_used


def fmt_float(value: Any, digits: int = 3) -> str:
    try:
        value = float(value)
    except Exception:
        return "NA"
    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def markdown_table(rows: List[List[Any]], headers: List[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def failure_mode_text(cells: pd.DataFrame) -> str:
    if cells.empty:
        return "- No cells were evaluable; insufficient data in source.\n"
    med_wlo = float(cells["wilson_lo"].median())
    med_pf = float(cells["pf"].replace([np.inf, -np.inf], np.nan).median())
    powered = cells[cells["n"] >= MIN_N]
    direction_correct = cells[(cells["ev_pips"] > 0) & (cells["pf"] > 1.0)]
    underpowered = direction_correct[direction_correct["n"] < MIN_N]
    regime_counts = cells["regime_sign_agreement"].value_counts().to_dict()
    if int(cells["n"].sum()) == 0:
        return "\n".join([
            f"- Median Wilson_lo across all cells: {med_wlo:.3f}",
            f"- Median PF across all cells: {med_pf:.3f}" if not math.isnan(med_pf) else "- Median PF across all cells: NA",
            "- Direction-correct-but-underpowered analysis: insufficient data in source; no sentiment/OHLC joined trades were available.",
            "- Powered cells counted in Bonferroni denominator: 0",
            f"- Regime split counts: {regime_counts}",
            "- Interpretation: insufficient data in source for hypothesis rejection; rerun after OANDA Labs DNS/API access or a populated cache is available.",
        ]) + "\n"
    lines = [
        f"- Median Wilson_lo across all cells: {med_wlo:.3f}",
        f"- Median PF across all cells: {med_pf:.3f}" if not math.isnan(med_pf) else "- Median PF across all cells: NA",
        f"- Direction-correct cells (EV>0 and PF>1.0): {len(direction_correct)} / {len(cells)}",
        f"- Direction-correct but underpowered cells (N<{MIN_N}): {len(underpowered)} / {len(direction_correct)}",
        f"- Powered cells counted in Bonferroni denominator: {len(powered)}",
        f"- Regime split counts: {regime_counts}",
    ]
    if len(direction_correct) == 0:
        lines.append("- Interpretation: rejection is direction-led in this 90d slice; the raw contrarian sign is not consistently positive.")
    elif len(underpowered) >= max(1, len(direction_correct) // 2):
        lines.append("- Interpretation: some cells point the right way but are mostly underpowered at the pre-registered thresholds.")
    else:
        lines.append("- Interpretation: near-misses have enough observations but fail the Bonferroni/Wilson/PF gates.")
    return "\n".join(lines) + "\n"


def write_report(
    cells: pd.DataFrame,
    m_used: int,
    sentiment_errors: List[str],
    skipped_pairs: List[str],
    pair_rows: Dict[str, int],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now().isoformat()
    survivors = cells[cells["survivor"]].sort_values(["wilson_lo", "pf", "ev_pips"], ascending=False)
    verdict = "SURVIVOR(s) FOUND" if len(survivors) else "NULL"

    lines: List[str] = []
    lines.append("# Phase 1b OANDA Retail-Contrarian Sentiment BT")
    lines.append("")
    lines.append("## Header")
    lines.append(f"- Run timestamp UTC: {now}")
    lines.append(f"- Pair set: {', '.join(PAIRS)}")
    lines.append(f"- Cell grid: 6 pairs x 12 thresholds x 4 holdings = {N_CELLS}")
    lines.append(f"- m_used (N >= {MIN_N}): {m_used}")
    lines.append(f"- alpha_cell: {ALPHA_CELL:.8f}")
    lines.append(f"- Sentiment cache: `{SENTIMENT_PATH.relative_to(ROOT)}`")
    lines.append("")
    lines.append("## Top-Level Verdict")
    lines.append(f"**{verdict}**")
    lines.append("")
    if sentiment_errors:
        lines.append("Fetch warnings:")
        for err in sentiment_errors:
            lines.append(f"- {err}")
        lines.append("")
    if skipped_pairs:
        lines.append("Skipped pairs:")
        for pair in skipped_pairs:
            lines.append(f"- {pair}")
        lines.append("")
    lines.append("Joined rows by pair:")
    for pair in PAIRS:
        lines.append(f"- {pair}: {pair_rows.get(pair, 0)}")
    lines.append("")

    lines.append("## Survivor Table")
    if len(survivors):
        rows = []
        for _, r in survivors.iterrows():
            rows.append([
                r["pair"], r["direction"], int(r["threshold"]), int(r["hold_bars_h4"]),
                int(r["n"]), fmt_float(r["wr"], 3), fmt_float(r["wilson_lo"], 3),
                fmt_float(r["ev_pips"], 2), fmt_float(r["pf"], 2), fmt_float(r["kelly"], 3),
                fmt_float(r["maxdd_pips"], 2), "PASS" if r["wf_pass"] else "FAIL",
                r["regime_sign_agreement"],
            ])
        lines.append(markdown_table(rows, ["pair", "direction", "threshold", "holding", "N", "WR", "Wilson_lo", "EV(p)", "PF", "Kelly", "MaxDD", "WF", "regime"]))
    else:
        lines.append("No cells passed all survivor gates.")
    lines.append("")

    lines.append("## Per-Pair Best Cell")
    rows = []
    for pair in PAIRS:
        sub = cells[cells["pair"] == pair].sort_values(["survivor", "wilson_lo", "pf", "ev_pips"], ascending=False)
        if sub.empty:
            rows.append([pair, "NA", "NA", "NA", 0, "NA", "NA", "NA", "NA", "NA"])
            continue
        r = sub.iloc[0]
        rows.append([
            pair, r["direction"], int(r["threshold"]), int(r["hold_bars_h4"]), int(r["n"]),
            fmt_float(r["wr"], 3), fmt_float(r["wilson_lo"], 3), fmt_float(r["ev_pips"], 2),
            fmt_float(r["pf"], 2), "YES" if r["survivor"] else "NO",
        ])
    lines.append(markdown_table(rows, ["pair", "direction", "threshold", "holding", "N", "WR", "Wilson_lo", "EV(p)", "PF", "survivor"]))
    lines.append("")

    if len(survivors) == 0:
        lines.append("## Failure Mode Analysis")
        lines.append(failure_mode_text(cells))
        lines.append("## Where To Look Next")
        lines.append("- Extend the sentiment history by cron polling; the current OANDA Labs endpoint only exposes the most recent 90 days.")
        lines.append("- Test longer H4 holds beyond 12 bars after more history exists; the current run is deliberately conservative.")
        lines.append("- Probe thresholds beyond 90/10 only after enough observations exist to avoid sparse-cell overfitting.")
        lines.append("- Test cross-pair sentiment spreads as a separate pre-registered study rather than widening this grid post hoc.")
        lines.append("")

    lines.append("## Honest Caveats")
    lines.append("- The available sentiment window is short; OANDA Labs history starts around 2026-02-06 in this feed.")
    lines.append("- MASSIVE cache coverage can be shorter than the sentiment feed for some pairs, so the effective BT window is the joined intersection.")
    lines.append("- This is a sanity BT only; any survivor still needs shadow validation before strategy integration.")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> int:
    pairs = [args.pair] if args.pair else PAIRS
    invalid = [p for p in pairs if p not in PAIRS]
    if invalid:
        raise ValueError(f"unsupported --pair {invalid}; allowed: {PAIRS}")
    sentiment, sentiment_errors = load_or_fetch_sentiment(pairs, args.no_fetch, args.force_fetch)
    joined_by_pair: Dict[str, pd.DataFrame] = {}
    skipped_pairs: List[str] = []
    pair_rows: Dict[str, int] = {}
    for pair in PAIRS:
        if pair not in pairs:
            joined_by_pair[pair] = pd.DataFrame()
            pair_rows[pair] = 0
            continue
        try:
            h4 = load_h4_ohlc(pair)
            joined = join_sentiment_to_ohlc(pair, sentiment, h4)
            joined_by_pair[pair] = joined
            pair_rows[pair] = len(joined)
            print(f"[join] {pair}: {len(joined)} H4 rows", flush=True)
        except Exception as exc:
            skipped_pairs.append(f"{pair}: {exc}")
            joined_by_pair[pair] = pd.DataFrame()
            pair_rows[pair] = 0
            print(f"[ohlc-err] {pair}: {exc}", flush=True)

    cells, m_used = build_grid(joined_by_pair)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cells.to_parquet(CELLS_PATH, index=False)
    write_report(cells, m_used, sentiment_errors, skipped_pairs, pair_rows)
    print(f"[written] {SENTIMENT_PATH}")
    print(f"[written] {CELLS_PATH}")
    print(f"[written] {REPORT_PATH}")
    survivors = cells[cells["survivor"]]
    print(f"[verdict] {'SURVIVORS ' + str(len(survivors)) if len(survivors) else 'NULL'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 1b OANDA retail-contrarian sentiment BT")
    ap.add_argument("--no-fetch", action="store_true", help="Use cached sentiment and error if it is missing")
    ap.add_argument("--force-fetch", action="store_true", help="Fetch sentiment even when cache is fresh")
    ap.add_argument("--pair", choices=PAIRS, default=None, help="Limit run to one pair for debugging")
    args = ap.parse_args()
    if args.no_fetch and args.force_fetch:
        ap.error("--no-fetch and --force-fetch are mutually exclusive")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
