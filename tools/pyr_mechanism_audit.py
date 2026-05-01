#!/usr/bin/env python3
"""PYR (Pyramid) mechanism Live audit (rule:R2 monitoring).

Background:
  The pyramiding ladder in `modules/demo_trader.py:1855-1917` adds +10000u to a
  profitable Live position with SL=parent entry (risk-free design). On 2026-04-30
  two PYR adds on GBP_USD (parents: gbp_deep_pullback, xs_momentum) hit BE-SL
  within 1-5 seconds, producing -471 JPY of confirmed loss on top of healthy
  parent trades. This audit measures whether the PYR mechanism is structurally
  giving back parent profits across the full Live history.

Methodology:
  - Fetch all OANDA Live trades + audit log via production API
  - Join: oanda_trades.oanda_trade_id ↔ oanda_audit.oanda_trade_id where
    audit.demo_trade_id LIKE 'PYR_%' identifies pyramid children
  - Resolve parent strategy via demo_trade_id 'PYR_<parent>' → look up parent
    audit row's entry_type (using bridge_status='sent' to get strategy not mode)
  - Compute per-parent-strategy: N, WR (TP_HIT vs STOP_LOSS), EV(pip), total_pl,
    hold_seconds distribution
  - Statistical: Wilson lower bound + Bonferroni-corrected binomial p-value
    against H0: WR ≥ 0.50 (risk-free design implies WR around the noise floor)

Usage:
  python3 tools/pyr_mechanism_audit.py [--out path.md] [--api-base URL]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt

import requests


def _fetch(url: str) -> dict:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_all_audit(api_base: str, max_pages: int = 20) -> list[dict]:
    """Audit endpoint paginates by limit only — fetch in chunks until we
    see no growth. The API returns most-recent-first so we accumulate."""
    seen_ids = set()
    all_rows: list[dict] = []
    for page in range(max_pages):
        limit = 2000 * (page + 1)
        d = _fetch(f"{api_base}/api/oanda/audit?limit={limit}")
        rows = d.get("audit", [])
        new = [r for r in rows if r.get("id") not in seen_ids]
        if not new:
            break
        for r in new:
            seen_ids.add(r.get("id"))
        all_rows = rows
        if len(rows) < limit:
            break
    return all_rows


def fetch_all_trades(api_base: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        d = _fetch(
            f"{api_base}/api/oanda/trades?state=ALL&limit=500&offset={offset}"
        )
        ts = d.get("trades", [])
        if not ts:
            break
        out.extend(ts)
        if len(ts) < 500:
            break
        offset += 500
    return out


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (center - margin) / denom)


def binom_two_sided_p(wins: int, n: int, p0: float = 0.5) -> float:
    """Two-sided binomial p-value vs p0 using normal approximation (sufficient
    for our N>=20 sanity check; prefer scipy.stats.binomtest for production)."""
    if n == 0:
        return 1.0
    p = wins / n
    se = sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = abs(p - p0) / se
    from math import erfc
    return min(1.0, erfc(z / sqrt(2)))


def _parse_iso(ts: str) -> datetime | None:
    """Tolerant ISO parser. Python 3.9 fromisoformat rejects 'Z' and >6 digit
    sub-seconds; OANDA returns 9-digit nanoseconds."""
    if not ts:
        return None
    s = ts.replace("Z", "+00:00")
    if "." in s:
        head, _, rest = s.partition(".")
        digits = ""
        i = 0
        while i < len(rest) and rest[i].isdigit():
            digits += rest[i]
            i += 1
        tz = rest[i:]
        s = f"{head}.{digits[:6]}{tz}"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def hold_seconds(trade: dict) -> float | None:
    ot = _parse_iso(trade.get("open_time", ""))
    ct = _parse_iso(trade.get("close_time", ""))
    if not ot or not ct:
        return None
    return (ct - ot).total_seconds()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-base", default="https://fx-ai-trader.onrender.com")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    print(f"[audit] fetching from {args.api_base} ...", file=sys.stderr)
    audit = fetch_all_audit(args.api_base)
    trades = fetch_all_trades(args.api_base)
    print(f"[audit] audit rows: {len(audit)}, trade rows: {len(trades)}",
          file=sys.stderr)

    by_oid: dict[str, list[dict]] = defaultdict(list)
    by_demo: dict[str, list[dict]] = defaultdict(list)
    for a in audit:
        oid = str(a.get("oanda_trade_id", ""))
        if oid:
            by_oid[oid].append(a)
        did = str(a.get("demo_trade_id", ""))
        if did:
            by_demo[did].append(a)

    pyr_records = []
    for t in trades:
        oid = str(t.get("oanda_trade_id", ""))
        audits = by_oid.get(oid, [])
        pyr_audit = next(
            (a for a in audits
             if str(a.get("demo_trade_id", "")).startswith("PYR_")),
            None,
        )
        if not pyr_audit:
            continue
        parent_demo_id = str(pyr_audit["demo_trade_id"])[4:]
        parent_audits = by_demo.get(parent_demo_id, [])
        parent_strategy = next(
            (a.get("entry_type") for a in parent_audits
             if a.get("bridge_status") == "sent" and a.get("entry_type")),
            None,
        )
        if not parent_strategy:
            modes = {"daytrade_gbpusd", "daytrade_eurjpy", "daytrade_eurgbp",
                     "daytrade_xau", "daytrade_gbpjpy", "scalp", "daytrade",
                     "daytrade_1h", "scalp_eur", "daytrade_eur",
                     "daytrade_1h_eur", "scalp_eurjpy", "scalp_xau",
                     "rnb_usdjpy", "scalp_5m", "scalp_5m_eur", "scalp_5m_gbp"}
            for a in parent_audits:
                et = a.get("entry_type")
                if et and et not in modes:
                    parent_strategy = et
                    break
        pyr_records.append((parent_strategy or "UNRESOLVED", t, pyr_audit))

    if not pyr_records:
        print("No PYR records found in current data window.", file=sys.stderr)
        return 1

    by_parent: dict[str, list[dict]] = defaultdict(list)
    for parent, t, _pa in pyr_records:
        by_parent[parent].append(t)

    times = [r[1].get("open_time", "")[:10] for r in pyr_records
             if r[1].get("open_time")]
    date_min = min(times) if times else "?"
    date_max = max(times) if times else "?"

    lines: list[str] = []
    lines.append("# PYR Mechanism Live Audit — 2026-05-01")
    lines.append("")
    lines.append(f"**Audit window**: {date_min} → {date_max}")
    lines.append(f"**Total PYR Live trades**: {len(pyr_records)}")
    lines.append(f"**Distinct parent strategies**: {len(by_parent)}")
    lines.append("")
    lines.append("## Source")
    lines.append(
        "- `/api/oanda/trades?state=ALL` joined to `/api/oanda/audit` "
        "where `demo_trade_id LIKE 'PYR_%'`"
    )
    lines.append(
        "- Parent strategy resolved via `audit.demo_trade_id = 'PYR_<parent>'` "
        "→ parent's `bridge_status='sent'` audit row's `entry_type` "
        "(filled-row entry_type is MODE name, not strategy)"
    )
    lines.append("")

    holds = [h for h in (hold_seconds(t) for _, t, _ in pyr_records)
             if h is not None]
    bands = [("<=5s", lambda h: h <= 5),
             ("5–60s", lambda h: 5 < h <= 60),
             ("1–10min", lambda h: 60 < h <= 600),
             ("10min–1h", lambda h: 600 < h <= 3600),
             (">1h", lambda h: h > 3600)]
    lines.append("## Hold-time distribution (BE-SL design implies short holds)")
    lines.append("")
    lines.append("| Band | Count | % |")
    lines.append("|---|---:|---:|")
    for label, pred in bands:
        c = sum(1 for h in holds if pred(h))
        pct = 100 * c / len(holds) if holds else 0
        lines.append(f"| {label} | {c} | {pct:.1f}% |")
    lines.append("")

    reasons: dict[str, int] = defaultdict(int)
    for _, t, _ in pyr_records:
        reasons[t.get("close_reason") or "OPEN/UNKNOWN"] += 1
    lines.append("## Close-reason distribution")
    lines.append("")
    lines.append("| Reason | Count | % |")
    lines.append("|---|---:|---:|")
    total = len(pyr_records)
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} | {100*v/total:.1f}% |")
    lines.append("")

    lines.append("## Per parent strategy")
    lines.append("")
    lines.append(
        "| Parent | N | TP | SL | MKT | WR | EV(pip) | Total(pip) | "
        "Total(JPY) | Wilson_BF | Bonf p (vs 50%) | Verdict |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    )
    n_strategies = max(1, len(by_parent))
    for parent in sorted(by_parent):
        ts = by_parent[parent]
        n = len(ts)
        tp = sum(1 for t in ts if t.get("close_reason") == "TAKE_PROFIT")
        sl = sum(1 for t in ts if t.get("close_reason") == "STOP_LOSS")
        mkt = sum(1 for t in ts if t.get("close_reason") == "MARKET_CLOSE")
        decided = tp + sl
        wr = (tp / decided * 100) if decided else 0
        pips = [t.get("pnl_pips") or 0 for t in ts]
        ev = sum(pips) / n if n else 0
        total_pip = sum(pips)
        total_jpy = sum(t.get("realized_pl") or 0 for t in ts)
        wlb = wilson_lower(tp, decided, z=3.29) if decided else 0
        raw_p = binom_two_sided_p(tp, decided) if decided else 1.0
        bonf_p = min(1.0, raw_p * n_strategies)
        if n < 10:
            verdict = "insufficient (N<10)"
        elif total_pip > 0 and wlb > 0.55:
            verdict = "POSITIVE"
        elif total_pip < 0 and bonf_p < 0.05:
            verdict = "NEGATIVE (Bonf-sig)"
        elif total_pip < 0:
            verdict = "negative trend"
        else:
            verdict = "neutral"
        lines.append(
            f"| {parent} | {n} | {tp} | {sl} | {mkt} | {wr:.1f}% | "
            f"{ev:+.2f} | {total_pip:+.1f} | {total_jpy:+.0f} | "
            f"{wlb:.3f} | {bonf_p:.3g} | {verdict} |"
        )
    lines.append("")

    n_all = len(pyr_records)
    tp_all = sum(1 for _, t, _ in pyr_records
                 if t.get("close_reason") == "TAKE_PROFIT")
    sl_all = sum(1 for _, t, _ in pyr_records
                 if t.get("close_reason") == "STOP_LOSS")
    decided_all = tp_all + sl_all
    pips_all = sum(t.get("pnl_pips") or 0 for _, t, _ in pyr_records)
    jpy_all = sum(t.get("realized_pl") or 0 for _, t, _ in pyr_records)
    lines.append("## Aggregate (all PYR)")
    lines.append("")
    lines.append(f"- N: {n_all}")
    lines.append(f"- TP: {tp_all} / SL: {sl_all} / MKT: {n_all - decided_all}")
    if decided_all:
        lines.append(
            f"- Decided WR: {100*tp_all/decided_all:.1f}% "
            f"(Wilson_BF lower @ Z=3.29: "
            f"{wilson_lower(tp_all, decided_all, 3.29):.3f})"
        )
    lines.append(f"- EV per PYR: {pips_all/n_all:+.2f} pip")
    lines.append(f"- Total: {pips_all:+.1f} pip / {jpy_all:+.0f} JPY")
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append(
        "- Risk-free design (SL=parent entry) implies losses should be "
        "small per-event but frequent (BE-SL is easy to hit). The "
        "question is whether net EV across the cohort is non-negative."
    )
    lines.append(
        "- If aggregate `Total(pip) < 0` AND `Bonf p < 0.05` against the "
        "50% TP rate null, the PYR mechanism is structurally giving back "
        "parent profits. → flag-gate `_pyramid_trades` in "
        "`modules/demo_trader.py:1855-1917` pending design fix."
    )
    lines.append(
        "- If aggregate is unclear (Bonf p > 0.05 with mixed signal), "
        "recommend Shadow-only PYR for N≥30 accumulation before re-arming."
    )

    output = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[audit] wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
