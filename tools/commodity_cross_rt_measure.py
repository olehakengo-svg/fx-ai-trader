#!/usr/bin/env python3
"""G0 RT measurement for commodity_cross_range_mr (ledger #21) — rule:R3.

OANDA M5 bid/ask candles (retroactive 60 trading days) for
AUD_NZD / AUD_CAD / NZD_CAD, with AUD_USD / USD_JPY as sanity anchors.
Spread-only measurement: no forward returns, no signals, no MFE contact.

Frozen spec: knowledge-base/wiki/decisions/commodity-cross-g0-rt-freeze-2026-08-03.md
  - spread = (ask.c - bid.c) / pip, complete M5 bars, weekend bars excluded
  - stressed_RT_primary      = p75(all-hours) + 1.0p
  - stressed_RT_conservative = p90(all-hours) + 2.0p  (reference only)
  - pair PASS <= 5.0p / MARGINAL <= 6.5p / FAIL > 6.5p (on primary)
  - family ABORT iff all three crosses FAIL
  - INVALID iff anchor p50 > 2.5x friction-table spread

Read-only: uses only GET /v3/instruments/:pair/candles.

Usage:
    python3 tools/commodity_cross_rt_measure.py [--days 60] [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

CROSSES = ("AUD_NZD", "AUD_CAD", "NZD_CAD")
ANCHORS = ("AUD_USD", "USD_JPY")
PIP = {
    "AUD_NZD": 1e-4, "AUD_CAD": 1e-4, "NZD_CAD": 1e-4,
    "AUD_USD": 1e-4, "USD_JPY": 1e-2,
}
# friction table spreads for anchor sanity check (INVALID iff p50 > 2.5x)
ANCHOR_TABLE_SPREAD = {"USD_JPY": 0.7, "AUD_USD": 1.2}

SLIPPAGE_RT_PRIMARY = 1.0       # 0.5p x2 (entry+exit)
SLIPPAGE_RT_CONSERVATIVE = 2.0  # thin-book sensitivity
PASS_THRESHOLD = 5.0            # stressed_RT_primary
MARGINAL_THRESHOLD = 6.5
ROLLOVER_HOURS = (21, 22)       # UTC, D1-close / rollover band
LIQUID_HOURS = tuple(range(7, 16))
EXEC_MAP_HOURS = (20, 21, 22, 23, 0, 1, 2)

CHUNK_DAYS = 7
REQUEST_SLEEP_S = 0.15
MAX_RETRY = 3


def load_env_file(path: Path) -> None:
    """Load .env into os.environ without overwriting (values never printed)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def is_weekend_bar(ts: datetime) -> bool:
    """FX closed window: Fri 21:00 UTC .. Sun 21:00 UTC."""
    wd, h = ts.weekday(), ts.hour
    if wd == 5:  # Saturday
        return True
    if wd == 4 and h >= 21:  # Friday late
        return True
    if wd == 6 and h < 21:  # Sunday before open
        return True
    return False


def fetch_spreads(client, pair: str, t0: datetime, t1: datetime) -> List[dict]:
    """Fetch M5 BA candles, return complete-bar close spreads in pips."""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    last_err = None
    for attempt in range(MAX_RETRY):
        ok, data = client.get_candles(
            pair, granularity="M5", price="BA",
            from_time=t0.strftime(fmt), to_time=t1.strftime(fmt))
        if ok:
            bars = []
            pip = PIP[pair]
            for c in data.get("candles", []):
                if not c.get("complete"):
                    continue
                ts = datetime.strptime(
                    c["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(
                    tzinfo=timezone.utc)
                if is_weekend_bar(ts):
                    continue
                bars.append({
                    "time": ts,
                    "spread_c": (float(c["ask"]["c"]) - float(c["bid"]["c"])) / pip,
                })
            return bars
        last_err = data
        time.sleep(1.0 + attempt)
    raise RuntimeError(
        f"OANDA candles fetch failed for {pair} {t0}..{t1}: {last_err}")


def pctile(vals: List[float], q: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = q / 100.0 * (len(s) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def summarize(pair: str, bars: List[dict]) -> dict:
    all_sp = [b["spread_c"] for b in bars]
    by_hour: Dict[int, List[float]] = {}
    for b in bars:
        by_hour.setdefault(b["time"].hour, []).append(b["spread_c"])
    p75 = pctile(all_sp, 75)
    p90 = pctile(all_sp, 90)
    rollover = [s for h in ROLLOVER_HOURS for s in by_hour.get(h, [])]
    liquid = [s for h in LIQUID_HOURS for s in by_hour.get(h, [])]
    stressed_primary = (p75 + SLIPPAGE_RT_PRIMARY) if p75 is not None else None
    stressed_conservative = (
        (p90 + SLIPPAGE_RT_CONSERVATIVE) if p90 is not None else None)
    verdict = None
    if pair in CROSSES and stressed_primary is not None:
        if stressed_primary <= PASS_THRESHOLD:
            verdict = "PASS"
        elif stressed_primary <= MARGINAL_THRESHOLD:
            verdict = "MARGINAL"
        else:
            verdict = "FAIL"
    exec_map = {
        str(h): {"p50": pctile(by_hour.get(h, []), 50),
                 "p75": pctile(by_hour.get(h, []), 75),
                 "n": len(by_hour.get(h, []))}
        for h in EXEC_MAP_HOURS
    }
    return {
        "pair": pair,
        "n_bars": len(all_sp),
        "spread_pips": {
            "p50": pctile(all_sp, 50), "p75": p75,
            "p90": p90, "p99": pctile(all_sp, 99),
        },
        "rollover_21_22utc": {
            "p50": pctile(rollover, 50), "p75": pctile(rollover, 75),
            "p90": pctile(rollover, 90), "n": len(rollover),
        },
        "liquid_07_16utc": {
            "p50": pctile(liquid, 50), "p75": pctile(liquid, 75),
            "n": len(liquid),
        },
        "by_hour_p75": {str(h): pctile(v, 75) for h, v in sorted(by_hour.items())},
        "exec_window_map_20_02utc": exec_map,
        "stressed_rt_primary": stressed_primary,
        "stressed_rt_conservative": stressed_conservative,
        "g0_verdict": verdict,
    }


def render_md(run: dict) -> str:
    lines = [
        "# G0 RT 実測 — commodity_cross_range_mr (#21) — %s" % run["asof"],
        "",
        "> rule:R3 摩擦実測 (fwd/シグナル非接触)。凍結仕様: "
        "[[commodity-cross-g0-rt-freeze-2026-08-03]]。"
        "%d 営業日 / M5 BA candles / OANDA live。" % run["days"],
        "",
        "| pair | n_bars | p50 | p75 | p90 | p99 | rollover p75 (21-22) | "
        "liquid p75 (07-16) | stressed_RT | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in run["pairs"]:
        sp = s["spread_pips"]
        fmtv = lambda v: ("%.2f" % v) if v is not None else "—"
        lines.append(
            "| %s | %d | %s | %s | %s | %s | %s | %s | **%s** | %s |" % (
                s["pair"], s["n_bars"], fmtv(sp["p50"]), fmtv(sp["p75"]),
                fmtv(sp["p90"]), fmtv(sp["p99"]),
                fmtv(s["rollover_21_22utc"]["p75"]),
                fmtv(s["liquid_07_16utc"]["p75"]),
                fmtv(s["stressed_rt_primary"]),
                s["g0_verdict"] or "(anchor)"))
    lines += ["", "## Family verdict: **%s**" % run["family_verdict"],
              "", "anchor sanity: %s" % run["anchor_sanity"], ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60,
                    help="trading days lookback (default 60)")
    ap.add_argument("--date", type=str, default=None,
                    help="as-of date YYYY-MM-DD (default: today UTC)")
    args = ap.parse_args()

    load_env_file(REPO_ROOT / ".env")
    sys.path.insert(0, str(REPO_ROOT))
    from modules.oanda_client import OandaClient  # noqa: E402
    client = OandaClient()
    if not os.environ.get("OANDA_TOKEN"):
        print("ERROR: OANDA_TOKEN not configured", file=sys.stderr)
        return 2

    asof = (date.fromisoformat(args.date) if args.date
            else datetime.now(timezone.utc).date())
    # calendar window generously covering N trading days
    t1 = datetime(asof.year, asof.month, asof.day, tzinfo=timezone.utc)
    t0 = t1 - timedelta(days=int(args.days * 7 / 5) + 4)

    summaries = []
    for pair in CROSSES + ANCHORS:
        bars: List[dict] = []
        cur = t0
        while cur < t1:
            nxt = min(cur + timedelta(days=CHUNK_DAYS), t1)
            bars.extend(fetch_spreads(client, pair, cur, nxt))
            time.sleep(REQUEST_SLEEP_S)
            cur = nxt
        s = summarize(pair, bars)
        summaries.append(s)
        print("  %s: n=%d p75=%s stressed=%s %s" % (
            pair, s["n_bars"],
            ("%.2f" % s["spread_pips"]["p75"]) if s["spread_pips"]["p75"] else "—",
            ("%.2f" % s["stressed_rt_primary"]) if s["stressed_rt_primary"] else "—",
            s["g0_verdict"] or ""))

    # anchor sanity
    invalid = []
    for s in summaries:
        if s["pair"] in ANCHOR_TABLE_SPREAD:
            p50 = s["spread_pips"]["p50"]
            limit = 2.5 * ANCHOR_TABLE_SPREAD[s["pair"]]
            if p50 is None or p50 > limit:
                invalid.append("%s p50=%s > %.2f" % (s["pair"], p50, limit))
    anchor_sanity = "INVALID: " + "; ".join(invalid) if invalid else "OK"

    cross_verdicts = [s["g0_verdict"] for s in summaries if s["pair"] in CROSSES]
    if invalid:
        family_verdict = "INVALID (anchor sanity fail — no verdict)"
    elif all(v == "FAIL" for v in cross_verdicts):
        family_verdict = "ABORT (all crosses FAIL)"
    elif any(v == "PASS" for v in cross_verdicts):
        family_verdict = "PROCEED (>=1 PASS)"
    else:
        family_verdict = "PROCEED-MARGINAL (no PASS, >=1 MARGINAL — 敵対的検証で可否判断)"

    run = {
        "asof": asof.isoformat(),
        "days": args.days,
        "granularity": "M5", "price": "BA",
        "spread_def": "(ask.c - bid.c)/pip, complete bars, weekend excluded",
        "stressed_def": {
            "primary": "p75_all + %.1fp" % SLIPPAGE_RT_PRIMARY,
            "conservative": "p90_all + %.1fp" % SLIPPAGE_RT_CONSERVATIVE,
        },
        "thresholds": {"pass": PASS_THRESHOLD, "marginal": MARGINAL_THRESHOLD},
        "pairs": summaries,
        "anchor_sanity": anchor_sanity,
        "family_verdict": family_verdict,
        "freeze_doc": "knowledge-base/wiki/decisions/"
                      "commodity-cross-g0-rt-freeze-2026-08-03.md",
    }

    out_json = REPO_ROOT / "knowledge-base" / "raw" / "bt-results" / (
        "commodity_cross_rt-%s.json" % asof.isoformat())
    out_json.write_text(json.dumps(run, indent=1))
    out_md = REPO_ROOT / "reports" / (
        "commodity-cross-rt-g0-%s.md" % asof.isoformat())
    out_md.parent.mkdir(parents=True, exist_ok=True)
    if out_md.exists():
        print("NOTE: %s exists — not overwriting" % out_md, file=sys.stderr)
    else:
        out_md.write_text(render_md(run))
    print("family_verdict:", family_verdict)
    print("json:", out_json)
    print("md:", out_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
