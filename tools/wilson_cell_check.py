"""Wilson Cell Check — honest, dedup-corrected single-cell edge audit.

Audits ONE edge cell (strategy x pair x direction [x session] [x mode]) from a
Render snapshot DB (table: demo_trades) and reports defensible win-rate /
Wilson-lower statistics, separately for LIVE (is_shadow=0) and SHADOW
(is_shadow=1).

Why this tool exists
--------------------
The SHADOW sample pseudo-replicates: the same setup re-fires many times, often
seconds apart with (near-)identical entry/SL/TP, which inflates N and makes a
tiny edge look "significant". Two corrections are applied:

  1. Exclude rows flagged ``dedup_violation = 1`` (the system already caught
     these as exact replays).
  2. ADDITIONALLY collapse same-day duplicate signals. Even after step (1) the
     survivors still cluster into a few calendar days (the strategy re-enters
     the same opportunity through the session, drifting the price a sub-pip so
     the exact-replay flag misses it). We collapse each (LIVE/SHADOW) group to
     ONE observation per calendar day, keeping the earliest entry of that day
     as the representative ("first fire is the real signal; re-fires are the
     pseudo-replicates"). This first-of-day rule is deterministic and unbiased
     (it can drop a win OR a loss depending on order).

Both ``raw-N`` and ``day-deduped-N`` are reported so nothing is hidden, with
Wilson 95% lower bounds for each. The day-deduped Wilson_lo is the honest input
for any promotion decision; it is almost always far lower because the real
independent N is small.

WR convention (matches tools/cell_edge_audit.py): the denominator is the number
of *decisive* trades (outcome WIN or LOSS). BREAKEVEN / NULL outcomes are
excluded from WR and Wilson but still counted and displayed for transparency.

Pure stdlib — no third-party deps (read-only on the DB).

Usage
-----
  python3 tools/wilson_cell_check.py --db render-fresh-snapshot.db \
      --strategy orb_trap --pair GBP_USD --direction SELL

  # optional narrowing
  python3 tools/wilson_cell_check.py --db snap.db \
      --strategy orb_trap --pair GBP_USD --direction SELL \
      --session NY --mode daytrade_gbpusd

  # machine-readable
  python3 tools/wilson_cell_check.py --db snap.db --strategy orb_trap \
      --pair GBP_USD --direction SELL --json

Column mapping (demo_trades): strategy->entry_type, pair->instrument,
direction->direction, session is derived from entry_time UTC hour, mode->mode.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import OrderedDict
from datetime import datetime, timezone

WILSON_Z: float = 1.96  # 95% CI


# --- Statistics ----------------------------------------------------------
def wilson_lower(wins: int, n: int, z: float = WILSON_Z) -> float:
    """Wilson score-interval lower bound for a binomial proportion.

    Returns 0.0 when n == 0 (no decisive trades).
    """
    if n <= 0:
        return 0.0
    p_hat = wins / n
    denom = 1.0 + z * z / n
    centre = p_hat + z * z / (2 * n)
    spread = z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


# --- Session derivation (self-contained; mirrors cell_edge_audit) --------
def derive_session(entry_time_iso):
    """Map an ISO entry_time (UTC) to a coarse session label.

    0-7 UTC Tokyo / 7-12 London / 12-16 overlap_LN / 16-21 NY / 21-24 Sydney.
    Returns "default" if the timestamp cannot be parsed.
    """
    if not entry_time_iso:
        return "default"
    try:
        ts = datetime.fromisoformat(str(entry_time_iso).replace("Z", "+00:00"))
        h = ts.astimezone(timezone.utc).hour if ts.tzinfo else ts.hour
    except (ValueError, TypeError):
        return "default"
    if h < 7:
        return "Tokyo"
    if h < 12:
        return "London"
    if h < 16:
        return "overlap_LN"
    if h < 21:
        return "NY"
    return "Sydney"


def calendar_day(entry_time_iso):
    """Return the YYYY-MM-DD calendar day of an ISO timestamp, or None."""
    if not entry_time_iso:
        return None
    s = str(entry_time_iso)
    # Fast path: ISO strings start with YYYY-MM-DD.
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return ts.date().isoformat()
    except (ValueError, TypeError):
        return None


def _is_win(outcome):
    return (outcome or "").upper() == "WIN"


def _is_loss(outcome):
    return (outcome or "").upper() == "LOSS"


def _is_breakeven(outcome):
    return (outcome or "").upper() == "BREAKEVEN"


# --- Data access (parametrised SQL — CWE-89 safe) ------------------------
_SELECT_COLS = (
    "id, entry_type, instrument, direction, mode, "
    "entry_time, outcome, is_shadow, dedup_violation, "
    "entry_price, sl, tp, pnl_pips"
)


def fetch_cell_rows(conn, strategy, pair, direction, session=None, mode=None):
    """Fetch rows for one cell. session/mode are applied in Python.

    strategy/pair match exactly; direction is matched case-insensitively.
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT " + _SELECT_COLS + " FROM demo_trades "  # noqa: S608 static cols
        "WHERE entry_type = ? AND instrument = ? "
        "AND UPPER(direction) = UPPER(?)",
        (strategy, pair, direction),
    ).fetchall()
    out = []
    sess_want = session.lower() if session else None
    mode_want = mode.lower() if mode else None
    for r in rows:
        if sess_want is not None and derive_session(r["entry_time"]).lower() != sess_want:
            continue
        if mode_want is not None and (r["mode"] or "").lower() != mode_want:
            continue
        out.append(r)
    return out


# --- Tally / dedup -------------------------------------------------------
def _tally(rows):
    """Win/loss/breakeven tally + WR + Wilson_lo over a set of rows."""
    n_total = len(rows)
    wins = sum(1 for r in rows if _is_win(r["outcome"]))
    losses = sum(1 for r in rows if _is_loss(r["outcome"]))
    breakeven = sum(1 for r in rows if _is_breakeven(r["outcome"]))
    other = n_total - wins - losses - breakeven
    decisive = wins + losses
    return {
        "n_total": n_total,
        "n_decisive": decisive,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "other": other,
        "wr": (wins / decisive) if decisive else None,
        "wilson_lo": wilson_lower(wins, decisive) if decisive else None,
    }


def _day_dedupe(rows):
    """Collapse to one row per calendar day, keeping the earliest entry.

    Rows with an unparseable date are each kept (treated as their own day).
    """
    ordered = sorted(rows, key=lambda r: (str(r["entry_time"] or ""), r["id"]))
    keep = OrderedDict()
    for r in ordered:
        day = calendar_day(r["entry_time"])
        key = day if day is not None else "__nodate__::%s" % r["id"]
        if key not in keep:
            keep[key] = r
    return list(keep.values())


def _summarize_group(rows):
    """Given dedup_violation-excluded rows for ONE is_shadow group, return
    raw + day-deduped summaries."""
    raw = _tally(rows)
    deduped_rows = _day_dedupe(rows)
    dd = _tally(deduped_rows)
    dd["n_calendar_days"] = len(deduped_rows)
    return {"raw": raw, "day_deduped": dd}


# --- Top-level audit -----------------------------------------------------
def audit_cell(db_path, strategy, pair, direction, session=None, mode=None):
    """Audit a single cell. Returns a structured result dict.

    LIVE (is_shadow=0) and SHADOW (is_shadow=1) are reported separately, each
    with ``raw`` and ``day_deduped`` sub-summaries. dedup_violation=1 rows are
    excluded (and counted under ``excluded_dedup_violation``).
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = fetch_cell_rows(conn, strategy, pair, direction, session, mode)
    finally:
        conn.close()

    result = {
        "meta": {
            "db": db_path,
            "strategy": strategy,
            "pair": pair,
            "direction": direction.upper(),
            "session": session or "ALL",
            "mode": mode or "ALL",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "wilson_z": WILSON_Z,
        }
    }
    for shadow_flag, label in ((0, "live"), (1, "shadow")):
        grp = [r for r in rows if int(r["is_shadow"] or 0) == shadow_flag]
        excluded = [r for r in grp if int(r["dedup_violation"] or 0) == 1]
        kept = [r for r in grp if int(r["dedup_violation"] or 0) != 1]
        summary = _summarize_group(kept)
        summary["excluded_dedup_violation"] = len(excluded)
        summary["rows_before_exclusion"] = len(grp)
        result[label] = summary
    return result


# --- Rendering -----------------------------------------------------------
def _fmt_pct(x):
    return ("%6.1f%%" % (x * 100)) if x is not None else "   n/a"


def _fmt_line(tag, t):
    extra = ""
    if "n_calendar_days" in t:
        extra = "  (%d calendar days)" % t["n_calendar_days"]
    return (
        "  %-12s: N=%-4d decisive=%-4d W=%-3d L=%-3d BE=%-3d WR=%s  "
        "Wilson_lo(95%%)=%s%s" % (
            tag, t["n_total"], t["n_decisive"], t["wins"], t["losses"],
            t["breakeven"], _fmt_pct(t["wr"]), _fmt_pct(t["wilson_lo"]), extra,
        )
    )


def format_report(result):
    m = result["meta"]
    lines = [
        "== Wilson Cell Check ==",
        "DB:        %s" % m["db"],
        "Cell:      %s | %s | %s   (session=%s mode=%s)" % (
            m["strategy"], m["pair"], m["direction"], m["session"], m["mode"]),
        "Generated: %s" % m["generated_at"],
        "",
    ]
    for label, human in (("live", "LIVE (is_shadow=0)"),
                         ("shadow", "SHADOW (is_shadow=1)")):
        sec = result[label]
        lines.append("-- %s --" % human)
        lines.append("  rows=%d  excluded dedup_violation=1: %d" % (
            sec["rows_before_exclusion"], sec["excluded_dedup_violation"]))
        lines.append(_fmt_line("raw", sec["raw"]))
        lines.append(_fmt_line("day-deduped", sec["day_deduped"]))
        lines.append("")
    lines.append(
        "Note: WR denominator = decisive (WIN+LOSS); BREAKEVEN/other excluded. "
        "day-deduped keeps the earliest fire per calendar day (unbiased)."
    )
    return "\n".join(lines)


# --- CLI -----------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="Honest, dedup-corrected single-cell Wilson edge check.",
    )
    p.add_argument("--db", required=True, help="Path to sqlite snapshot DB")
    p.add_argument("--strategy", required=True, help="entry_type, e.g. orb_trap")
    p.add_argument("--pair", required=True, help="instrument, e.g. GBP_USD")
    p.add_argument("--direction", required=True, help="BUY or SELL")
    p.add_argument("--session", default=None,
                   help="Optional session filter (Tokyo/London/overlap_LN/NY/Sydney)")
    p.add_argument("--mode", default=None,
                   help="Optional mode filter (exact, case-insensitive)")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of the text report")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = audit_cell(
        args.db, args.strategy, args.pair, args.direction,
        session=args.session, mode=args.mode,
    )
    total = (result["live"]["rows_before_exclusion"]
             + result["shadow"]["rows_before_exclusion"])
    if total == 0:
        sys.stderr.write(
            "[wilson_cell_check] No rows for %s|%s|%s (session=%s, mode=%s)\n" % (
                args.strategy, args.pair, args.direction.upper(),
                args.session or "ALL", args.mode or "ALL")
        )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
