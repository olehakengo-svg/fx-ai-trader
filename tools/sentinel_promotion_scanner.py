#!/usr/bin/env python3
"""Sentinel Promotion Scanner — weekly auto-scan of all shadow cells for PP candidacy.

Purpose
-------
UNIVERSAL_SENTINEL (14 strategies) + Phase0 Shadow (19 strategies) + PAIR_DEMOTED
(23 cells) are all accruing Shadow data concurrently. Manually monitoring every
(strategy, pair) cell is infeasible. This tool scans the live production API,
decomposes all `is_shadow=1` closed trades per (strategy, pair), and auto-flags
PP (pair-promotion) candidates where every gating condition is satisfied:

    PP_CANDIDATE  (all required):
        N                     >= 30
        Kelly edge            > 0           (p*b - (1-p))
        mean_pnl_pip          > 0
        WR Wilson 95% lower   > BEV_WR      (asymmetric R:R aware)
        pos_ratio (30d rolling) >= 0.67     (walk-forward stability proxy)

    MONITOR       : N >= 30 but at least one gate failed
    INSUFFICIENT_N: N < 30

Anti-patterns enforced (lesson links in CLAUDE.md):
  - lesson-wr-only-fd-flag           : WR alone is insufficient — AND mean_pnl>0
  - lesson-shadow-contamination      : strict is_shadow=1 isolation
  - lesson-all-time-vs-post-cutoff   : cutoff = 2026-04-08 (post data-cleanup)
  - feedback_exclude_xau             : XAU pairs dropped from EV calcs

Inputs
------
  Production API: https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000
  Filter        : is_shadow=1 AND status==CLOSED AND non-XAU
                  AND created_at >= 2026-04-08

Outputs
-------
  1. knowledge-base/raw/audits/sentinel-scan-YYYY-MM-DD.md
        - PP_CANDIDATE table + per-row commentary
        - MONITOR table (all N>=30 cells that failed >= 1 gate)
        - INSUFFICIENT_N: top 20 cells by N (full list would be too long)
  2. stdout summary: "N_candidates=X, N_monitor=Y, total_cells=Z"

Usage
-----
    # Default smoke run — hits Render, writes dated report under raw/audits/
    python3 tools/sentinel_promotion_scanner.py

    # Custom date_from / api / output
    python3 tools/sentinel_promotion_scanner.py \
        --date-from 2026-04-08 \
        --api https://fx-ai-trader.onrender.com \
        --output /tmp/scan.md

    # Emit machine-readable JSON alongside the markdown report
    python3 tools/sentinel_promotion_scanner.py --save-json

Exit codes: 0 = OK, 1 = API fetch failure, 2 = validation / IO error.
"""
from __future__ import annotations

import argparse
import json
import math
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_DATE_FROM = "2026-04-08"  # post-cutoff (lesson-all-time-vs-post-cutoff)
DEFAULT_LIMIT = 5000
MIN_N_FULL = 30                   # gate threshold for PP_CANDIDATE / MONITOR
ROLLING_WINDOW_DAYS = 30          # for pos_ratio walk-forward proxy
POS_RATIO_GATE = 0.67             # WF stability proxy gate
TOP_INSUFFICIENT = 20             # truncate INSUFFICIENT_N to top-N by N

# BEV_WR defaults (percent). Mirrors bayesian_edge_check.py.
BEV_WR_PCT = {
    ("USD_JPY", "scalp"):    50.0,
    ("USD_JPY", "daytrade"): 40.0,
    ("USD_JPY", "1h"):       35.0,
    ("EUR_USD", "scalp"):    45.0,
    ("EUR_USD", "daytrade"): 38.0,
    ("EUR_USD", "1h"):       33.0,
    ("GBP_USD", "scalp"):    52.0,
    ("GBP_USD", "daytrade"): 42.0,
    ("GBP_USD", "1h"):       36.0,
}
BEV_WR_FALLBACK_PCT = 50.0

# Wilson score constant for 95% two-sided CI
WILSON_Z_95 = 1.959963984540054

_ALLOWED_SCHEMES = ("http", "https")


# ---------------------------------------------------------------------------
# HTTP helpers (mirrors bayesian_edge_check's hardened opener)
# ---------------------------------------------------------------------------
def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Refusing non-http(s) scheme: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"URL must include hostname (url={url!r})")


_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = True
_SSL_CTX.verify_mode = ssl.CERT_REQUIRED
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def fetch_trades(api: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """GET /api/demo/trades?limit=... and return the trades array."""
    url = f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}"
    _validate_url(url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "sentinel-promotion-scanner/1.0"},
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with _SAFE_OPENER.open(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"ERROR: API fetch failed ({e})", file=sys.stderr)
        sys.exit(1)
    if isinstance(payload, dict):
        return payload.get("trades", [])
    return payload or []


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
def _trade_timestamp(t: dict) -> str:
    """Pick the most reliable timestamp we can find on a trade record."""
    return t.get("created_at") or t.get("entry_time") or t.get("close_time") or ""


def filter_shadow_trades(trades: Iterable[dict], date_from: str) -> list[dict]:
    """Apply is_shadow=1, status=CLOSED, non-XAU, created_at >= date_from.

    Per feedback_exclude_xau and lesson-shadow-contamination.
    """
    kept: list[dict] = []
    for t in trades:
        status = str(t.get("status") or "").upper()
        if status != "CLOSED":
            continue
        if int(t.get("is_shadow", 0) or 0) != 1:
            continue
        inst = str(t.get("instrument") or "")
        if "XAU" in inst:
            continue  # feedback_exclude_xau
        ts = _trade_timestamp(t)
        if ts and ts < date_from:
            continue
        kept.append(t)
    return kept


def _parse_ts(t: dict) -> datetime | None:
    raw = _trade_timestamp(t)
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            ts = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def infer_mode(trades: Iterable[dict]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for t in trades:
        m = str(t.get("mode") or "daytrade").lower()
        counts[m] += 1
    if not counts:
        return "daytrade"
    return max(counts.items(), key=lambda kv: kv[1])[0]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def wilson_lower_bound(wins: int, n: int, z: float = WILSON_Z_95) -> float:
    """95% Wilson score lower bound on win rate (fraction 0..1)."""
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1.0 + (z * z) / n
    center = phat + (z * z) / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)
    return max(0.0, (center - margin) / denom)


def bev_wr_pct_for(pair: str, mode: str, avg_win: float, avg_loss: float) -> float:
    """Choose BEV WR for the cell.

    If we have meaningful asymmetric R:R (|avg_win|, |avg_loss| both > 0),
    derive BEV from observed payoff ratio:   BEV = loss / (win + loss)
    Otherwise fall back to the per-(pair,mode) table used in production.
    """
    if avg_win > 0 and avg_loss > 0:
        return 100.0 * (avg_loss / (avg_win + avg_loss))
    return BEV_WR_PCT.get((pair, mode), BEV_WR_FALLBACK_PCT)


def kelly_edge(p: float, avg_win: float, avg_loss: float) -> float:
    """Kelly numerator edge = p*b - (1-p), where b = avg_win / avg_loss.

    Returns NaN when avg_loss <= 0 (no losses seen yet — cannot size Kelly).
    """
    if avg_loss <= 0:
        return float("nan")
    b = avg_win / avg_loss
    return p * b - (1.0 - p)


def rolling_pos_ratio(trades: list[dict], window_days: int) -> tuple[float | None, int]:
    """Fraction of rolling `window_days` windows with positive EV.

    Implementation: bin trades by day-of-occurrence (UTC), then slide a
    `window_days` window one day at a time from first trade day to last
    trade day. A window is considered "active" when it contains >= 5 trades;
    the ratio is (positive_EV_windows / active_windows).

    Returns (ratio_or_None, active_windows). `None` when no active window exists.
    """
    dated: list[tuple[datetime, float]] = []
    for t in trades:
        ts = _parse_ts(t)
        if ts is None:
            continue
        pnl = float(t.get("pnl_pips") or 0.0)
        dated.append((ts, pnl))
    if not dated:
        return None, 0
    dated.sort(key=lambda x: x[0])
    start = dated[0][0].replace(hour=0, minute=0, second=0, microsecond=0)
    end = dated[-1][0].replace(hour=0, minute=0, second=0, microsecond=0)
    total_days = (end - start).days + 1
    if total_days < window_days:
        # not enough calendar coverage for a full window
        return None, 0

    active = 0
    positive = 0
    for offset in range(total_days - window_days + 1):
        w_start = start + timedelta(days=offset)
        w_end = w_start + timedelta(days=window_days)
        window_pnls = [p for ts, p in dated if w_start <= ts < w_end]
        if len(window_pnls) < 5:
            continue
        active += 1
        if sum(window_pnls) / len(window_pnls) > 0:
            positive += 1
    if active == 0:
        return None, 0
    return positive / active, active


# ---------------------------------------------------------------------------
# Per-cell summary
# ---------------------------------------------------------------------------
def summarize_cell(strategy: str, pair: str, trades: list[dict]) -> dict:
    n = len(trades)
    pnls = [float(t.get("pnl_pips") or 0.0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]  # magnitudes
    n_wins = len(wins)
    wr = (n_wins / n) if n else 0.0
    mean_pnl = (sum(pnls) / n) if n else 0.0
    pos_sum = sum(wins)
    neg_sum = sum(losses)
    pf = (pos_sum / neg_sum) if neg_sum > 0 else (float("inf") if pos_sum > 0 else 0.0)
    avg_win = (pos_sum / n_wins) if n_wins else 0.0
    avg_loss = (neg_sum / len(losses)) if losses else 0.0

    mode = infer_mode(trades)
    bev_pct = bev_wr_pct_for(pair, mode, avg_win, avg_loss)
    wilson_lo = wilson_lower_bound(n_wins, n)  # fraction
    kelly = kelly_edge(wr, avg_win, avg_loss)

    if n >= MIN_N_FULL:
        pos_ratio, active_windows = rolling_pos_ratio(trades, ROLLING_WINDOW_DAYS)
    else:
        pos_ratio, active_windows = None, 0

    # Gate evaluation
    gates = {
        "N_ge_30": n >= MIN_N_FULL,
        "kelly_gt_0": (not math.isnan(kelly)) and kelly > 0,
        "mean_pnl_gt_0": mean_pnl > 0,
        "wilson_gt_bev": (wilson_lo * 100.0) > bev_pct,
        "pos_ratio_ge_067": (pos_ratio is not None) and pos_ratio >= POS_RATIO_GATE,
    }
    all_pass = all(gates.values())
    if n < MIN_N_FULL:
        verdict = "INSUFFICIENT_N"
    elif all_pass:
        verdict = "PP_CANDIDATE"
    else:
        verdict = "MONITOR"

    return {
        "strategy": strategy,
        "pair": pair,
        "mode": mode,
        "n": n,
        "wins": n_wins,
        "wr": wr,
        "mean_pnl_pip": mean_pnl,
        "pf": pf,
        "avg_win_pip": avg_win,
        "avg_loss_pip": avg_loss,
        "bev_wr_pct": bev_pct,
        "wilson_lower_pct": wilson_lo * 100.0,
        "kelly_edge": kelly,
        "pos_ratio": pos_ratio,
        "active_windows": active_windows,
        "gates": gates,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def _fmt(x: Any, spec: str = ".2f") -> str:
    if x is None:
        return "—"
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return "—"
    try:
        return format(x, spec)
    except (TypeError, ValueError):
        return str(x)


def _gate_glyph(rows_gates: dict) -> str:
    """One-char glyphs: O pass, X fail — ordered N|K|P|W|S."""
    order = ["N_ge_30", "kelly_gt_0", "mean_pnl_gt_0", "wilson_gt_bev", "pos_ratio_ge_067"]
    return "".join("O" if rows_gates[g] else "X" for g in order)


def render_markdown(rows: list[dict], *, date_from: str,
                    generated_at: str, total_fetched: int,
                    total_after_filter: int) -> str:
    candidates = [r for r in rows if r["verdict"] == "PP_CANDIDATE"]
    monitors = [r for r in rows if r["verdict"] == "MONITOR"]
    insufficient = [r for r in rows if r["verdict"] == "INSUFFICIENT_N"]

    # sort rules: candidates by Kelly desc, monitors by N desc, insufficient by N desc
    candidates.sort(key=lambda r: (-(r["kelly_edge"] if not math.isnan(r["kelly_edge"]) else -1),
                                    -r["n"]))
    monitors.sort(key=lambda r: -r["n"])
    insufficient.sort(key=lambda r: -r["n"])

    lines: list[str] = []
    lines.append("# Sentinel Promotion Scan")
    lines.append("")
    lines.append(f"- **Generated**: {generated_at}")
    lines.append(f"- **Data source**: Render `/api/demo/trades?limit={DEFAULT_LIMIT}`")
    lines.append(f"- **Filter**: `is_shadow=1 AND status==CLOSED AND non-XAU "
                 f"AND created_at >= {date_from}`")
    lines.append(f"- **Fetched**: {total_fetched} trades → "
                 f"{total_after_filter} after filter")
    lines.append(f"- **Gates**: N≥{MIN_N_FULL}, Kelly>0, mean_pnl>0, "
                 f"Wilson95% lower > BEV_WR, pos_ratio≥{POS_RATIO_GATE} "
                 f"({ROLLING_WINDOW_DAYS}d rolling)")
    lines.append("- **Gate glyph** (N|K|P|W|S): N≥30, Kelly>0, mean_pnl>0, "
                 "Wilson>BEV, pos_ratio≥0.67")
    lines.append("")
    lines.append(f"**Summary**: PP_CANDIDATE={len(candidates)}, "
                 f"MONITOR={len(monitors)}, "
                 f"INSUFFICIENT_N={len(insufficient)}, "
                 f"total_cells={len(rows)}")
    lines.append("")

    # ---- PP_CANDIDATE ----
    lines.append("## PP_CANDIDATE (all gates pass)")
    lines.append("")
    if not candidates:
        lines.append("_None._ No Shadow cell currently satisfies all five gates.")
        lines.append("")
    else:
        lines.append("| Strategy | Pair | N | WR% | Wilson_lo% | BEV% | "
                     "mean_pnl | PF | Kelly | pos_ratio |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in candidates:
            lines.append(
                f"| {r['strategy']} | {r['pair']} | {r['n']} | "
                f"{r['wr']*100:.1f} | {r['wilson_lower_pct']:.1f} | "
                f"{r['bev_wr_pct']:.1f} | {_fmt(r['mean_pnl_pip'], '+.2f')} | "
                f"{_fmt(r['pf'], '.2f')} | {_fmt(r['kelly_edge'], '+.3f')} | "
                f"{_fmt(r['pos_ratio'], '.2f')} |"
            )
        lines.append("")
        lines.append("### Commentary")
        for r in candidates:
            lines.append(
                f"- **{r['strategy']} × {r['pair']}** (N={r['n']}, "
                f"Kelly={_fmt(r['kelly_edge'], '+.3f')}, "
                f"Wilson_lo={r['wilson_lower_pct']:.1f}% > BEV {r['bev_wr_pct']:.1f}%, "
                f"pos_ratio={_fmt(r['pos_ratio'], '.2f')}): "
                "proposal for PP promotion. Before acting, verify against "
                "`wiki/tier-master.md` (not in FORCE_DEMOTED) and latest "
                "365d BT EV sign (lesson-orb-trap-bt-divergence)."
            )
        lines.append("")

    # ---- MONITOR ----
    lines.append(f"## MONITOR ({len(monitors)} cells with N≥{MIN_N_FULL} but ≥1 gate failed)")
    lines.append("")
    if not monitors:
        lines.append("_None._")
        lines.append("")
    else:
        lines.append("| Strategy | Pair | N | WR% | Wilson% | BEV% | mean_pnl | "
                     "PF | Kelly | pos_ratio | Gates(N|K|P|W|S) |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:-:|")
        for r in monitors:
            lines.append(
                f"| {r['strategy']} | {r['pair']} | {r['n']} | "
                f"{r['wr']*100:.1f} | {r['wilson_lower_pct']:.1f} | "
                f"{r['bev_wr_pct']:.1f} | {_fmt(r['mean_pnl_pip'], '+.2f')} | "
                f"{_fmt(r['pf'], '.2f')} | {_fmt(r['kelly_edge'], '+.3f')} | "
                f"{_fmt(r['pos_ratio'], '.2f')} | `{_gate_glyph(r['gates'])}` |"
            )
        lines.append("")

    # ---- INSUFFICIENT_N ----
    lines.append(f"## INSUFFICIENT_N (top {TOP_INSUFFICIENT} by N, "
                 f"total {len(insufficient)})")
    lines.append("")
    if not insufficient:
        lines.append("_None._")
        lines.append("")
    else:
        lines.append("| Strategy | Pair | N | WR% | mean_pnl | Kelly |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for r in insufficient[:TOP_INSUFFICIENT]:
            lines.append(
                f"| {r['strategy']} | {r['pair']} | {r['n']} | "
                f"{r['wr']*100:.1f} | {_fmt(r['mean_pnl_pip'], '+.2f')} | "
                f"{_fmt(r['kelly_edge'], '+.3f')} |"
            )
        if len(insufficient) > TOP_INSUFFICIENT:
            lines.append("")
            lines.append(f"_... {len(insufficient) - TOP_INSUFFICIENT} more cells "
                         f"omitted (full list available via --save-json)._")
        lines.append("")

    lines.append("## Decision protocol reminder (CLAUDE.md)")
    lines.append("")
    lines.append("- PP_CANDIDATE is **necessary but NOT sufficient** — "
                 "confirm 365d BT EV and tier-master.md before promoting.")
    lines.append("- No parameter changes driven by this scan alone "
                 "(lesson-reactive-changes).")
    lines.append("- Source: `tools/sentinel_promotion_scanner.py`")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def run_scan(api: str, date_from: str, limit: int) -> tuple[list[dict], int, int]:
    trades_all = fetch_trades(api, limit=limit)
    trades = filter_shadow_trades(trades_all, date_from=date_from)
    # bucket by (strategy, pair)
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in trades:
        et = str(t.get("entry_type") or "unknown")
        inst = str(t.get("instrument") or "unknown")
        buckets[(et, inst)].append(t)
    rows = [summarize_cell(et, pair, ts) for (et, pair), ts in buckets.items()]
    return rows, len(trades_all), len(trades)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default=DEFAULT_API,
                        help=f"Production API base URL (default: {DEFAULT_API})")
    parser.add_argument("--date-from", default=DEFAULT_DATE_FROM,
                        help=f"Lower-bound cutoff (default: {DEFAULT_DATE_FROM})")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="Trade-fetch limit (default: 5000)")
    parser.add_argument("--output", default=None,
                        help="Override markdown output path")
    parser.add_argument("--save-json", action="store_true",
                        help="Also emit raw rows as JSON alongside markdown")
    args = parser.parse_args()

    try:
        rows, total_fetched, total_after = run_scan(
            args.api, args.date_from, args.limit
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    candidates = [r for r in rows if r["verdict"] == "PP_CANDIDATE"]
    monitors = [r for r in rows if r["verdict"] == "MONITOR"]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = render_markdown(
        rows,
        date_from=args.date_from,
        generated_at=generated_at,
        total_fetched=total_fetched,
        total_after_filter=total_after,
    )

    # Output path
    if args.output:
        out_path = Path(args.output)
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = (_PROJECT_ROOT / "knowledge-base" / "raw" / "audits"
                    / f"sentinel-scan-{date_str}.md")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
    except OSError as e:
        print(f"ERROR: could not write {out_path}: {e}", file=sys.stderr)
        return 2
    print(f"Report written: {out_path}")

    if args.save_json:
        json_path = out_path.with_suffix(".json")
        # gates contains booleans → already JSON safe; handle NaN/Inf → null
        def _clean(v: Any) -> Any:
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return v
        safe_rows = [{k: _clean(v) for k, v in r.items()} for r in rows]
        json_path.write_text(
            json.dumps({
                "generated_at": generated_at,
                "date_from": args.date_from,
                "total_fetched": total_fetched,
                "total_after_filter": total_after,
                "rows": safe_rows,
            }, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Raw JSON:      {json_path}")

    # stdout summary (exact format specified in task)
    print(f"N_candidates={len(candidates)}, "
          f"N_monitor={len(monitors)}, "
          f"total_cells={len(rows)}")
    return 0


if __name__ == "__main__":
    # Default smoke execution — hits Render with default args.
    sys.exit(main())
