#!/usr/bin/env python3
"""Weekly cell deepdive audit (v2/v3 cell grid) with pre-reg LOCK redaction.

Background
----------
This tool existed only as an ad-hoc script re-typed into
``knowledge-base/raw/cell_deepdive/_run_deepdive_<date>.py`` every week for
10 consecutive weeks (2026-07-02 .. 2026-09-20).  Because it was never in the
repo it had no tests, and two defects survived undetected:

1. **P-10 breach (rule:R3).**  The report recomputed and published the outcome
   statistics (WR / EV / PF / Wilson / p) of cells that are under an *active*
   pre-reg LOCK forbidding intermediate recomputation.  Those cells are
   evaluated once, at their declared N.  Weekly republication of their outcome
   stats is exactly the optional-stopping peek the LOCK exists to prevent.
   The 2026-09-20 run flagged the conflict in prose ("weekly deepdive が毎週
   再計算しており、ツール自体が LOCK と構造的に衝突") but still printed the
   numbers.  This module checks the lock **before** any statistic is computed,
   so a LOCKed cell yields a count-only record and no outcome helper ever runs
   for it — P-10 bans recomputation, not merely publication.

2. **dedup exclusion rate presented as the cause of N starvation.**  Falsified
   2026-09-20: ``dedup_violation=1`` marks *redundant tick-level re-emits of
   an already-recorded event* (median 14-25 s after the kept row, p90 <= 50 s,
   window 900 s for the tf=15m target strategies).  The gate keeps the first
   emit per window, so it removes zero independent observations and cannot
   slow unique-N accrual.  Reporting ``dedup_excluded / raw`` invites the wrong
   remedy ("fix dedup") for what is a signal-frequency problem.  This module
   reports **unique-N accrual** and splits the exclusion by gate-fix era.

See knowledge-base/wiki/analyses/deepdive-dedup-estimand-and-lock-redaction-2026-09-20.md

Side-effect free at import time (rule: tools/*.py are libraries as well as
scripts — no os.environ / os.chdir / parse_args at module top level).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TARGETS = (
    "sr_anti_hunt_bounce", "sr_liquidity_grab", "cpd_divergence",
    "vdr_jpy", "vsg_jpy_reversal", "rsk_gbpjpy_reversion", "mqe_gbpusd_fix",
)

REGISTRY_PATH = (
    PROJECT_ROOT / "knowledge-base" / "wiki" / "decisions"
    / "prereg-trigger-registry.json"
)

MIN_N = 20
WILSON_Z = 1.96
PROMO_WILSON_LO = 0.50
PROMO_BONF_ALPHA = 0.05

# Commit 6a45bb2 — SHADOW_EMIT 60s dedup gate installed.  Rows before this are
# the one-shot April contamination burst flagged by the boot backfill; rows
# after it are the ongoing (cross-process) flag rate.  Conflating the two makes
# a frozen historical artifact look like a live defect (mqe_gbpusd_fix: 93.2%
# overall vs 0.0% post-fix).
DEDUP_GATE_FIX_TS = "2026-04-30T02:42:00"

# /api/demo/trades' default page size (app.py).  A snapshot of exactly this
# size is the signature of a plain curl without ?limit=.
_API_DEFAULT_LIMIT = 50

# Default --min-rows floor.  Kept as a module constant so the CLI default can
# stay None: main() needs to tell "caller said nothing" from "caller
# deliberately lowered the floor" (Codex P3, PR #273).
_DEFAULT_MIN_ROWS = 1000

# Outcome fields that must never be emitted for a LOCKed cell.
REDACTED_FIELDS = (
    "wr", "wilson_lo", "ev_net", "pf", "p_raw", "p_bonf", "kelly",
    "wf_stable", "promoted", "wins",
)


# ── statistics ────────────────────────────────────────────────────────────

def wilson_lower(wins: int, n: int, z: float = WILSON_Z) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def binom_p(wins: int, n: int, p0: float = 0.5) -> float:
    if n == 0:
        return 1.0
    var = n * p0 * (1 - p0)
    if var <= 0:
        return 1.0
    z = (wins - n * p0) / math.sqrt(var)
    return max(0.0, min(1.0, 2 * (1 - _phi(abs(z)))))


def kelly(wr: float, avg_win: float, avg_loss: float) -> float:
    if avg_loss <= 0:
        return 0.0
    rr = avg_win / avg_loss
    if rr <= 0:
        return 0.0
    return max(0.0, wr - (1 - wr) / rr)


def cell_stats(rows: list) -> dict:
    n = len(rows)
    wins = sum(1 for r in rows if r["win"])
    wr = wins / n if n else 0.0
    pnls = [r["pnl"] for r in rows]
    ev = sum(pnls) / n if n else 0.0
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [-p for p in pnls if p < 0]
    avg_w = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_l = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
    return {
        "n": n, "wins": wins, "wr": wr, "wilson_lo": wilson_lower(wins, n),
        "ev": ev, "pf": pf, "kelly": kelly(wr, avg_w, avg_l),
        "p_raw": binom_p(wins, n),
    }


def wf_stable(rows: list):
    """2-fold time split: EV same sign (>0) in both halves. Needs N>=8."""
    if len(rows) < 8:
        return None
    srt = sorted(rows, key=lambda r: r["entry_time"] or "")
    mid = len(srt) // 2
    return (sum(r["pnl"] for r in srt[:mid]) > 0) and (sum(r["pnl"] for r in srt[mid:]) > 0)


# ── pre-reg LOCK redaction ────────────────────────────────────────────────

class LockRegistryUnavailable(RuntimeError):
    """The pre-reg LOCK registry could not be read.

    This MUST abort the audit.  Registry loading is the only thing standing
    between this tool and a P-10 disclosure, so a missing/corrupt registry has
    to fail **closed** — returning an empty lock list would silently disable
    every LOCK and publish exactly the statistics this module exists to
    suppress (Codex P1, PR #273).
    """


def load_locked_cells(registry_path=None) -> list:
    """Return active pre-reg LOCKed cells as (entry_type, instrument, direction).

    ``instrument`` / ``direction`` may be ``None`` = wildcard (the LOCK covers
    every pair / both directions of that strategy).

    Only ``*_count_decision`` entries are redacted: those carry a verdict rule
    evaluated once at a declared N, so recomputing their outcome statistics is
    an optional-stopping peek.  ``*_count_info`` entries are frequency monitors
    with no outcome gate and are left alone.

    Raises:
        LockRegistryUnavailable: if the registry is missing or unparseable.
    """
    path = Path(registry_path) if registry_path else REGISTRY_PATH
    try:
        with open(path) as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry unreadable ({path}): {exc}. "
            "Refusing to run — an unguarded audit would publish LOCKed cells."
        ) from exc
    # Structural validation — mirrors tools/prereg_trigger_watch.load_registry_raw.
    # Invariant: **never fold "cannot inspect" into "nothing wrong"**.
    # `.get("triggers", [])` folds a misspelled/missing root key into an empty
    # ledger, so {"trigers": []} would silently disable every LOCK; an empty
    # ledger is likewise indistinguishable from a truncated one (Codex P1,
    # PR #273, 3rd instance of this fail-open class).
    if not isinstance(payload, dict):
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry root is not an object ({path}): "
            f"got {type(payload).__name__}")
    if "triggers" not in payload:
        near = [k for k in payload if "trig" in k.lower()]
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry has no 'triggers' key ({path}); "
            f"keys present: {sorted(payload)}"
            + (f" — misspelling candidates: {near}" if near else "")
            + " — folding this into an empty ledger would drop every LOCK")
    entries = payload["triggers"]
    if not isinstance(entries, list):
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry 'triggers' must be a list ({path}): "
            f"got {type(entries).__name__}")
    if not entries:
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry 'triggers' is empty ({path}) — "
            "'intentionally empty' and 'ledger lost' are indistinguishable, "
            "so the audit assumes the latter")
    bad = [i for i, e in enumerate(entries) if not isinstance(e, dict)]
    if bad:
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry has non-object entries at {bad[:5]} "
            f"({path}) — refusing to run rather than skipping them silently")

    # Delegate SCHEMA validation to the canonical linter instead of
    # hand-rolling a weaker copy.  A misspelled selector KEY ("mtach":
    # "prefix") slips past value-only checks and silently becomes an exact
    # lock, which would expose a prefix family's frozen outcomes.  The
    # canonical linter already rejects unknown keys (reject-by-default), so
    # the right fix is to call it rather than to keep adding checks that
    # trail it (Codex P1, PR #273).
    _lint_entries_or_raise(entries, path)

    locked = []
    for e in entries:
        # Canonical loader is `t.get("active", True)` — an omitted flag means
        # ACTIVE.  Treating it as inactive would let the watcher evaluate a
        # LOCK this audit publishes unredacted (Codex P2, PR #273).
        if not e.get("active", True):
            continue
        if not str(e.get("type", "")).endswith("_count_decision"):
            continue
        # Not every *_count_decision freezes an outcome look: some are pure
        # count monitors that state they are P-10 compatible (lane-health
        # checkpoints, the weekend_gap live-conversion monitor).  Redacting
        # those silently discards valid results and promotion candidates —
        # the mirror image of a leak (Codex P2, PR #273).
        #
        # The default is True (redact) because under-redaction leaks silently
        # while over-redaction is at least visible; a count-only monitor must
        # opt out EXPLICITLY.  Inferring this from message prose was tried and
        # misclassified rnb-support-bounce-shadow-forward, which IS an outcome
        # LOCK — hence an explicit flag rather than a heuristic.
        if e.get("outcome_lock", True) is False:
            continue
        et = e.get("entry_type")
        marker = e.get("reasons_marker") or ""
        # A misspelled or deleted selector ({"type": "shadow_count_decision",
        # "entry_typo": "foo"}) passes the structural checks and would be
        # silently dropped — removing a LOCK while the audit keeps publishing
        # that population.  This command does not run the canonical registry
        # linter, so it must reject the entry itself (Codex P1, PR #273).
        if not et and not marker:
            raise LockRegistryUnavailable(
                f"active {e.get('type')} entry {e.get('id')!r} has neither "
                f"'entry_type' nor 'reasons_marker' ({path}); keys: "
                f"{sorted(e)} — a selector-less LOCK cannot be honoured, and "
                "skipping it would publish its population unredacted")
        locked.append({
            "entry_type": et or None,
            "instrument": e.get("instrument") or None,
            "direction": e.get("direction") or None,
            "registry_id": e.get("id"),
            # `match: "prefix"` = the LOCK covers a multi-variant family
            # (kalman_d7_*, price_shock_rev_*, weekend_gap_*).  Exact matching
            # would miss every variant and expose a frozen family's outcome
            # statistics (Codex P2, PR #273).  Semantics mirror
            # tools/prereg_trigger_watch.py count_matching(prefix=...).
            "match": _validated_match(e, path),
            "reasons_marker": marker or None,
            "count_basis": e.get("count_basis"),
            # Population predicates — the LOCK's N is defined by THESE, not by
            # this audit's window/filters (Codex P2, PR #273).  Reporting the
            # cell's 365d Live+Shadow row count next to the gate threshold
            # would suggest a gate had been passed that has not been.
            "kind": "live" if str(e.get("type", "")).startswith("live")
                    else "shadow",
            "since": e.get("since") or None,
            "closed_only": bool(e.get("closed_only")),
            "dedup_violation": e.get("dedup_violation"),
            "mode": e.get("mode") or None,
            "n_decide": e.get("n_decide"),
        })
    return locked


def row_in_lock_population(t, lock, *, watcher_compat: bool = False,
                           as_of_exclusive: str | None = None) -> bool:
    """True when row ``t`` belongs to ``lock``'s declared population.

    Single source of truth for BOTH the LOCK's N and the marker-row exclusion.
    They were separate before, and the marker exclusion matched on the reasons
    literal alone — so a shadow or pre-``since`` row carrying the marker was
    dropped from the audit although it is not locked (Codex P2, PR #273).
    Over-exclusion is the mirror image of a leak: it silently deletes real
    observations from the report.
    """
    # A marker LOCK has no entry_type — its population is defined by the
    # reasons literal alone, so entry_type must not filter it out.
    if lock.get("entry_type"):
        if not _entry_type_matches(t.get("entry_type"), lock):
            return False
    elif not lock.get("reasons_marker"):
        return False
    if lock.get("instrument") and t.get("instrument") != lock["instrument"]:
        return False
    if lock.get("direction") and t.get("direction") != lock["direction"]:
        return False
    if lock.get("mode") and t.get("mode") != lock["mode"]:
        return False
    live = bool(t.get("oanda_trade_id"))
    kind = lock.get("kind")
    if kind == "live" and not live:
        return False
    if kind == "shadow" and not watcher_compat and (
            live or not t.get("is_shadow")):
        # Strict shadow = `is_shadow=1 AND oanda_trade_id empty`, spelled out
        # verbatim in the rnb-support-bounce-shadow-forward LOCK
        # ("厳格 shadow = is_shadow=1 ∧ oanda_trade_id 空") and consistent with
        # MEMORY feedback_live_vs_shadow_strict_separation.  Checking only the
        # OANDA id let flag-drift rows (blank id but is_shadow=0) count as
        # shadow — PROD currently holds 47 such rows, so the hazard is real,
        # not hypothetical (Codex P2, PR #273).
        #
        # The canonical watcher's count_matching applies NEITHER filter, so the
        # two can diverge.  We do NOT silently pick a side on a LOCK trigger:
        # `watcher_compat=True` reproduces the watcher and the report emits
        # BOTH counts plus a divergence flag.
        return False
    if lock.get("closed_only") and t.get("status") != "CLOSED":
        return False
    dup = int(t.get("dedup_violation") or 0) == 1
    if kind == "live":
        # count_live_matching excludes dup rows UNCONDITIONALLY.
        if dup:
            return False
    elif (lock.get("count_basis") == "unique"
          or lock.get("dedup_violation") == 0):
        # Mirrors count_matching(exclude_dedup_violation=...).
        if dup:
            return False
    marker = lock.get("reasons_marker")
    if marker and marker not in _reasons_text(t):
        return False
    if lock.get("since") and _ts(t) < str(lock["since"]):
        return False
    # The LOCK's `since` is its own lower bound, but the population still needs
    # the AUDIT's upper bound: re-running --run-date 2026-09-20 against a later
    # snapshot otherwise counts post-run rows and can imply n_decide was already
    # reached in a historical report (Codex P2, PR #273).
    if as_of_exclusive and _ts(t)[:10] >= as_of_exclusive:
        return False
    return True


def _lint_entries_or_raise(entries, path) -> None:
    """Run tools/prereg_trigger_watch's linter over the entries; raise on error.

    Importing the canonical linter keeps this loader from drifting behind it —
    every rule it gains (unknown keys, type checks, selector completeness)
    applies here automatically.
    """
    try:
        # Path insertion is done HERE, not at import time: tools/*.py are also
        # libraries and must stay side-effect free on import.
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from tools.prereg_trigger_watch import lint_registry
    except Exception as exc:                       # pragma: no cover
        raise LockRegistryUnavailable(
            f"cannot import the canonical registry linter ({exc}) — refusing "
            f"to validate the LOCK registry with a weaker local copy") from exc
    errors = lint_registry(entries)
    if errors:
        head = "\n  - ".join(errors[:5])
        raise LockRegistryUnavailable(
            f"pre-reg LOCK registry fails the canonical linter ({path}):\n"
            f"  - {head}"
            + (f"\n  ... (+{len(errors) - 5} more)" if len(errors) > 5 else ""))


def _validated_match(entry, path) -> str:
    """`match` must be absent or exactly "prefix" — never silently coerced.

    A misspelled value ("prefx") or key was being folded into "exact", which
    would make a prefix outcome LOCK (kalman_d7) stop covering its variants and
    publish their frozen statistics.  This command does not run
    prereg_trigger_watch.lint_registry, so it validates here (Codex P1, PR #273).
    """
    if "match" not in entry:
        return "exact"
    value = entry.get("match")
    if value == "prefix":
        return "prefix"
    raise LockRegistryUnavailable(
        f"entry {entry.get('id')!r} has match={value!r} ({path}) — the only "
        f"supported value is 'prefix'. Refusing to fall back to exact matching: "
        f"a misspelled selector would silently un-cover a prefix LOCK's variants")


def lock_population_count(trades, lock, *, watcher_compat: bool = False,
                          as_of_exclusive: str | None = None) -> int:
    """Count rows in the LOCK's OWN declared population.

    The registry entry — not this audit's window — defines what the trigger
    counts: ``since``, ``closed_only``, ``dedup_violation``, ``mode`` and
    shadow-vs-live.  Emitting the cell's in-window row count instead would be
    the very defect this PR documents (a count that does not match the
    estimand printed beside it).
    """
    return sum(1 for t in trades
               if row_in_lock_population(t, lock,
                                         watcher_compat=watcher_compat,
                                         as_of_exclusive=as_of_exclusive))


def _reasons_text(trade) -> str:
    """Flatten a trade's `reasons` to text (mirrors prereg_trigger_watch)."""
    r = trade.get("reasons") or ""
    if isinstance(r, list):
        r = " | ".join(str(x) for x in r)
    return str(r)


def _entry_type_matches(entry_type, lock) -> bool:
    """Exact or prefix entry_type match, per the LOCK's `match` field."""
    target = lock.get("entry_type")
    if not target:
        # Marker-defined LOCK: population is a row set, not a cell, so it
        # never claims a cell here (its rows are removed up-front instead).
        return False
    et = entry_type or ""
    if lock.get("match") == "prefix":
        return et.startswith(target)
    return et == target


def locks_for_cell(entry_type, instrument, direction, locked_cells) -> list:
    """EVERY active LOCK covering this cell, not just the first.

    Two active LOCKs may cover the same (entry_type, instrument, direction)
    with DIFFERENT populations — e.g. a shadow LOCK and a live LOCK on the same
    strategy/pair/direction.  Testing only the first match let a live row fail
    the shadow LOCK's population check, fall into the unlocked complement, and
    have its WR/EV published although it belongs to the second LOCK.  The
    canonical linter does not forbid overlapping selectors, so routing must
    consider all of them (Codex P1, PR #273).
    """
    return [lk for lk in locked_cells
            if _lock_covers_cell(lk, entry_type, instrument, direction)]


def _lock_covers_cell(lk, entry_type, instrument, direction) -> bool:
    if not _entry_type_matches(entry_type, lk):
        return False
    if lk["instrument"] is not None and lk["instrument"] != instrument:
        return False
    if lk["direction"] is not None and lk["direction"] != direction:
        return False
    return True


def lock_for_cell(entry_type, instrument, direction, locked_cells) -> dict | None:
    """Return the LOCK covering this cell, or None.

    A cell is covered when it equals the LOCKed cell **or refines it** (a
    sub-cell such as a session split).  Refinements are covered because a
    sharper slice reveals the LOCKed cell's outcomes more precisely, not less.
    Strict super-sets (e.g. a strategy-level aggregate across other pairs) are
    NOT covered — they are a different estimand and do not isolate the cell.
    """
    for lk in locked_cells:
        if not _entry_type_matches(entry_type, lk):
            continue
        if lk["instrument"] is not None and lk["instrument"] != instrument:
            continue
        if lk["direction"] is not None and lk["direction"] != direction:
            continue
        return lk
    return None


def count_only_record(level, key, unique_rows_in_window: int, lock: dict,
                      lock_population_n=None,
                      lock_population_watcher_n=None) -> dict:
    """Build a LOCKed cell's record WITHOUT computing any outcome statistic.

    P-10 forbids *recomputation*, not merely publication, so no
    outcome-statistics helper (``cell_stats`` / ``wf_stable`` / Bonferroni) may
    run for a LOCKed cell at all — redacting an already-computed dict would
    only prevent serialization (Codex P1, PR #273).

    The counts are deliberately named for their estimands.  A bare ``n`` was
    ambiguous and dangerous: the cell's 365d Live+Shadow row count (74) sitting
    beside a gate threshold of 40 reads as "the gate has been passed", while
    the LOCK's own population (fresh shadow rows since 2026-08-05) is 36
    (Codex P2, PR #273).
    """
    rec = {
        "level": level,
        "cell": list(key),
        "n_unique_rows_in_window": unique_rows_in_window,
        "redacted": True,
        "redaction_reason": "prereg_lock_p10_no_intermediate_recompute",
        "redaction_registry_id": lock.get("registry_id"),
    }
    if lock_population_n is not None:
        rec["n_lock_population"] = lock_population_n
        if lock_population_watcher_n is not None:
            rec["n_lock_population_watcher"] = lock_population_watcher_n
            rec["watcher_divergence"] = (
                lock_population_watcher_n != lock_population_n)
        rec["n_decide"] = lock.get("n_decide")
        rec["lock_population_predicates"] = {
            k: lock.get(k) for k in
            ("kind", "since", "closed_only", "dedup_violation", "mode")
        }
    return rec


# ── row shaping ───────────────────────────────────────────────────────────

def derive_session(iso) -> str:
    if not iso:
        return "default"
    try:
        ts = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        h = ts.astimezone(timezone.utc).hour
    except Exception:
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


def norm_mode(m) -> str:
    if not m:
        return "Unknown"
    ml = str(m).lower()
    if "scalp" in ml:
        return "Scalp"
    if "swing" in ml:
        return "Swing"
    if "daytrade" in ml:
        return "DT"
    return m


def _ts(row) -> str:
    return (row.get("entry_time") or "")[:19].replace(" ", "T")


# ── dedup-era accounting (replaces the falsified "dedup = N starvation") ──

def dedup_era_breakdown(target_all: list, targets) -> dict:
    """Split dedup_violation=1 into pre/post gate-fix era, per strategy.

    The overall rate mixes a one-shot April backfill burst with the ongoing
    cross-process flag rate; only the post-fix rate describes current behaviour.
    """
    out = {}
    for s in targets:
        rows = [t for t in target_all if t.get("entry_type") == s]
        if not rows:
            out[s] = {"raw": 0}
            continue
        pre = [t for t in rows if _ts(t) < DEDUP_GATE_FIX_TS]
        post = [t for t in rows if _ts(t) >= DEDUP_GATE_FIX_TS]
        dv = lambda rs: sum(1 for t in rs if t.get("dedup_violation") == 1)
        rate = lambda n, d: round(100.0 * n / d, 1) if d else None
        out[s] = {
            "raw": len(rows),
            "dedup_excluded": dv(rows),
            "dedup_rate_pct_overall": rate(dv(rows), len(rows)),
            "pre_fix_raw": len(pre),
            "pre_fix_dedup": dv(pre),
            "pre_fix_rate_pct": rate(dv(pre), len(pre)),
            "post_fix_raw": len(post),
            "post_fix_dedup": dv(post),
            "post_fix_rate_pct": rate(dv(post), len(post)),
        }
    return out


def unique_accrual(target_all: list, targets, as_of: str) -> dict:
    """Unique (dedup_violation=0) event accrual — the metric that actually
    governs how fast a cell reaches its N gate."""
    try:
        asof_dt = datetime.fromisoformat(as_of)
    except ValueError:
        asof_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    out = {}
    for s in targets:
        stamps = []
        for t in target_all:
            if t.get("entry_type") != s or t.get("dedup_violation") == 1:
                continue
            ts = _ts(t)
            if not ts:
                continue
            try:
                stamps.append(datetime.fromisoformat(ts))
            except ValueError:
                continue
        if not stamps:
            out[s] = {"unique_365d": 0, "unique_90d": 0, "unique_30d": 0,
                      "unique_per_week_90d": 0.0, "last_unique_fire": None}
            continue
        stamps.sort()
        # d - 1: an INCLUSIVE calendar window ending on as_of spans exactly d
        # days.  `days=d` counted d+1 (2026-06-22..2026-09-20 = 91 for d=90)
        # and inflated the accrual rates used to diagnose signal starvation
        # (Codex P2, PR #273).  Mirrors window_bounds().
        c = lambda d: sum(1 for x in stamps
                          if x >= asof_dt - timedelta(days=d - 1))
        out[s] = {
            "unique_365d": c(365),
            "unique_90d": c(90),
            "unique_30d": c(30),
            "unique_per_week_90d": round(c(90) / (90 / 7), 2),
            "last_unique_fire": stamps[-1].isoformat(),
        }
    return out


# ── main audit ────────────────────────────────────────────────────────────

def window_bounds(run_date: str, window_days: int):
    """Half-open [lo, hi) ISO bounds for the audit window ending at run_date.

    The report advertises a 365-day window; without this the input was filtered
    only by strategy and XAU, so once PROD holds >1y of history — or when
    rerunning an older run_date against a current snapshot — stale and even
    post-run rows would change N, multiplicity and candidates while the report
    still claimed 365d (Codex P2, PR #273).
    """
    run_d = datetime.fromisoformat(run_date).date()
    # hi is exclusive and set to the day AFTER run_date, so rows stamped on
    # run_date itself are included (a run executed mid-day must not silently
    # drop that day's rows) while post-run rows are excluded.
    # window_days - 1: the interval is an INCLUSIVE calendar window whose last
    # day is run_date, so [run_date-(N-1), run_date+1) spans exactly N days.
    # [run_date-N, run_date+1) would span N+1 (Codex P2, PR #273).
    return (run_d - timedelta(days=window_days - 1)).isoformat(), (
        run_d + timedelta(days=1)).isoformat()


def run_audit(trades, *, run_date, targets=DEFAULT_TARGETS, locked_cells=None,
              min_n=MIN_N, window_days=365):
    """Pure function: trades (list of dicts) -> result dict.  No I/O."""
    if locked_cells is None:
        locked_cells = load_locked_cells()
    targets = tuple(targets)

    win_lo, win_hi = window_bounds(run_date, window_days)
    target_all = [t for t in trades
                  if t.get("entry_type") in targets
                  and "XAU" not in (t.get("instrument") or "")
                  and win_lo <= _ts(t)[:10] < win_hi]

    dedup_excl = sum(1 for t in target_all if t.get("dedup_violation") == 1)

    # Marker-defined LOCKs (empty entry_type + `reasons_marker`) define a row
    # set rather than a cell, so their rows are removed BEFORE any outcome
    # statistic is built — otherwise the pooled LOCK outcomes reappear inside
    # whatever cell/strategy those rows happen to land in (Codex P1, PR #273).
    # A LOCK whose population has not begun by the audit's upper bound cannot
    # cover anything in this window.  Without this, re-running a historical
    # --run-date redacts cells under a LOCK that starts later and reports
    # n_lock_population: 0 — removing valid historical statistics and
    # candidates (Codex P2, PR #273).  Over-redaction again: the mirror image
    # of a leak.
    def _lock_started(lk):
        since = lk.get("since")
        return not since or str(since) < win_hi

    active_locks = [lk for lk in locked_cells if _lock_started(lk)]
    not_yet_started = [lk for lk in locked_cells if not _lock_started(lk)]
    marker_locks = [lk for lk in active_locks if lk.get("reasons_marker")]
    cell_locks = [lk for lk in active_locks if lk.get("entry_type")]
    marker_excluded = 0

    # LOCKed rows are routed out from the RAW rows, before `outcome`/`pnl_pips`
    # is ever read.  Previously they passed through the WIN/LOSS filter first,
    # so the emitted count was itself a function of outcome (a BREAKEVEN row
    # changed both the count and whether the cell appeared at all) — the very
    # 35-vs-36 discrepancy this analysis documents, reproduced inside the tool
    # meant to fix it (Codex P1, PR #273).
    locked_raw = defaultdict(list)
    complement_cells = set()
    open_raw = []
    for t in target_all:
        if marker_locks and any(row_in_lock_population(t, lk)
                                for lk in marker_locks):
            marker_excluded += 1
            continue
        covering = locks_for_cell(t.get("entry_type"), t.get("instrument"),
                                  t.get("direction"), cell_locks)
        # Route out ONLY rows that are actually in some LOCK's population.
        # Cell identity alone over-routes (the shadow-only EUR_JPY BUY LOCK was
        # swallowing live and pre-`since` rows too), but checking only ONE
        # covering LOCK under-routes when two LOCKs overlap.  So: in ANY
        # covering LOCK's population => routed out.
        if any(row_in_lock_population(t, lk, as_of_exclusive=win_hi)
               for lk in covering):
            locked_raw[(t.get("entry_type"), t.get("instrument"),
                        t.get("direction"))].append(t)
            continue
        if covering:
            # Same cell, outside the LOCK population: keep it, but remember the
            # cell is a partial view so the report cannot be misread as whole.
            complement_cells.add((t.get("entry_type"), t.get("instrument"),
                                  t.get("direction")))
        open_raw.append(t)

    locked_rows_total = sum(len(v) for v in locked_raw.values())

    # `non_wl` reads `outcome`, so it is computed from `open_raw` ONLY — after
    # locked and marker-defined populations are removed.  Over `target_all` it
    # published an outcome-derived property of a frozen population (flipping
    # one locked row WIN->BREAKEVEN moved the emitted metadata), which the
    # count-only record being unchanged does not excuse (Codex P1, PR #273).
    # `dedup_excl` above is outcome-free, so it may span all rows.
    non_wl = sum(1 for t in open_raw
                 if t.get("dedup_violation") != 1
                 and t.get("outcome") not in ("WIN", "LOSS"))

    clean = []
    for t in open_raw:
        if t.get("dedup_violation") == 1:
            continue
        oc = t.get("outcome")
        if oc not in ("WIN", "LOSS"):
            continue
        clean.append({
            "entry_type": t.get("entry_type"),
            "instrument": t.get("instrument"),
            "direction": t.get("direction"),
            "session": derive_session(t.get("entry_time")),
            "mode": norm_mode(t.get("mode")),
            "is_shadow": t.get("is_shadow"),
            "win": oc == "WIN",
            "pnl": float(t.get("pnl_pips") or 0.0),
            "entry_time": t.get("entry_time"),
        })

    shadow_n = sum(1 for r in clean if r["is_shadow"])

    # Strategy-level aggregate: LOCKed rows are removed BEFORE aggregating.
    #
    # The original design exempted strict super-sets ("a strategy aggregate
    # spans other pairs, so it is a different estimand").  That is only true
    # when other pairs actually have rows — if every row of a strategy belongs
    # to the LOCKed cell, the "aggregate" IS the LOCKed cell and leaks it.  The
    # leak condition is data-dependent, i.e. exactly the kind that breaks
    # silently.  Excluding LOCKed rows makes the aggregate unconditionally a
    # different estimand (all non-LOCKed cells of that strategy).
    strat_summary = {}
    for s in targets:
        raw = sum(1 for t in target_all if t.get("entry_type") == s)
        # LOCKed rows never reach `clean` (they are routed out of the raw rows
        # before any outcome read), so the aggregate is unconditionally a
        # different estimand: "all non-LOCKed cells of this strategy".
        rows = [r for r in clean if r["entry_type"] == s]
        locked_excluded = sum(len(v) for k, v in locked_raw.items() if k[0] == s)
        if not rows:
            strat_summary[s] = {"raw": raw, "clean_N": 0,
                                "locked_rows_excluded": locked_excluded}
            continue
        st = cell_stats(rows)
        strat_summary[s] = {
            "raw": raw, "clean_N": st["n"], "WR": round(st["wr"], 3),
            "wilson_lo": round(st["wilson_lo"], 3),
            "EV_net_pips": round(st["ev"], 2),
            "PF": round(st["pf"], 2) if st["pf"] != float("inf") else None,
            "locked_rows_excluded": locked_excluded,
        }

    def build_cells(keyfn):
        g = defaultdict(list)
        for r in clean:
            g[keyfn(r)].append(r)
        return g

    v2 = build_cells(lambda r: (r["entry_type"], r["instrument"], r["direction"]))
    v3 = build_cells(
        lambda r: (r["entry_type"], r["instrument"], r["session"], r["direction"]))

    # LOCKed cells: grouped from RAW rows with an outcome-FREE filter only
    # (unique = dedup_violation != 1, in-window).  No outcome field is read.
    #
    # The KEY SET comes from the raw rows and the COUNT from the deduplicated
    # ones — two different questions (Codex P2, PR #273).  Building the key set
    # from the deduplicated rows made a non-empty LOCK vanish from the
    # inventory entirely when ALL of its rows carry `dedup_violation=1`: the
    # `ws3-*` shadow decisions declare no unique/dedup predicate, so the
    # canonical watcher counts those rows and the LOCK can reach `n_decide`
    # while `redacted_cells` holds no `n_lock_population` record for it at all.
    # Under-reporting a LOCK that is AT its gate is the same false-negative
    # direction as the rest of this file's defects, so the group must still
    # appear — with `n_unique_rows_in_window` = 0 if that is the truth.
    locked_v2_keys: dict = {}
    locked_v3_keys: dict = {}
    locked_v2 = defaultdict(list)
    locked_v3 = defaultdict(list)
    for key, rows in locked_raw.items():
        for t in rows:
            v3key = (key[0], key[1], derive_session(t.get("entry_time")),
                     key[2])
            locked_v2_keys.setdefault(key, None)      # insertion-ordered set
            locked_v3_keys.setdefault(v3key, None)
            if t.get("dedup_violation") == 1:
                continue
            locked_v2[key].append(t)
            locked_v3[v3key].append(t)

    v2_elig = {k: v for k, v in v2.items() if len(v) >= min_n}
    v3_elig = {k: v for k, v in v3.items() if len(v) >= min_n}
    locked_v2_elig = {k: v for k, v in locked_v2.items() if len(v) >= min_n}
    locked_v3_elig = {k: v for k, v in locked_v3.items() if len(v) >= min_n}
    # Multiplicity DELIBERATELY still counts LOCKed eligible cells.  They can
    # never become candidates, so excluding them would be defensible — but it
    # shrinks m and makes every other cell's p_bonf easier to pass.  On a
    # multiplicity correction we take the conservative direction.
    m_v2 = len(v2_elig) + len(locked_v2_elig)
    m_v3 = len(v3_elig) + len(locked_v3_elig)
    # Bonferroni is applied over ONE exploration family, v2 ∪ v3.  Correcting
    # each grid separately let a lone v3 sub-cell pass with almost no penalty
    # (m_v3 = 1 ⇒ p_bonf = p_raw) even though the combined family rejects it —
    # which is exactly how the Tokyo sub-cell appeared as a "candidate" for 4
    # consecutive weeks.  The 2026-09-20 report had already identified v2 ∪ v3
    # (m = 8, p_bonf = 0.0720, FAIL) as the applicable family in prose while
    # the harness kept the per-grid split (Codex P1, PR #273).
    m_family = m_v2 + m_v3

    def eval_cells(cells, m, level):
        out = []
        for k, rows in cells.items():
            entry_type, instrument = k[0], k[1]
            direction = k[-1]
            # LOCKed cells never reach here — their rows were routed out of
            # `clean` before any outcome field was read.
            st = cell_stats(rows)
            p_bonf = min(1.0, st["p_raw"] * m) if m > 0 else 1.0
            rec = {
                "level": level, "cell": list(k), "n": st["n"],
                "wins": st["wins"], "wr": round(st["wr"], 3),
                "wilson_lo": round(st["wilson_lo"], 3),
                "ev_net": round(st["ev"], 2),
                "pf": round(st["pf"], 2) if st["pf"] != float("inf") else None,
                "p_raw": round(st["p_raw"], 4), "p_bonf": round(p_bonf, 4),
                "kelly": round(st["kelly"], 3), "wf_stable": wf_stable(rows),
                "promoted": (st["n"] >= min_n
                             and st["wilson_lo"] > PROMO_WILSON_LO
                             and p_bonf < PROMO_BONF_ALPHA),
                "redacted": False,
            }
            if (entry_type, instrument, direction) in complement_cells:
                rec["lock_complement_only"] = True
                rec["note"] = ("LOCKed cell の母集団外だけを集計した部分ビュー — "
                               "セル全体の統計ではない")
            out.append(rec)
        out.sort(key=lambda x: (x.get("redacted", False), -x.get("wilson_lo", 0.0)))
        return out

    def locked_records(keys, unique_groups, level):
        out = []
        for k in keys:
            # `locked_raw` is keyed (entry_type, instrument, direction); a v3
            # key carries `session` in the middle, so drop it — and then
            # FILTER BACK DOWN to that session (Codex P2, PR #273).  Using the
            # parent cell's rows made every v3 record of a cell pick the same
            # cell-wide primary: with a shadow lock concentrated in Tokyo and a
            # live lock in London, at least one session reported the other
            # session's registry_id, n_decide and n_rows_matched.
            #
            # Attribution is computed over the RAW rows on purpose: when every
            # row of the group is a dedup repeat, `unique_rows` is empty and an
            # argmax over it would fall back to registry order — exactly the
            # mis-attribution this pass is fixing.
            rows = locked_raw.get((k[0], k[1], k[-1]), [])
            if level == "v3":
                rows = [t for t in rows
                        if derive_session(t.get("entry_time")) == k[2]]
            unique_rows = unique_groups.get(k, [])
            covering = locks_for_cell(k[0], k[1], k[-1], cell_locks)
            # The PRIMARY lock must be the one that actually matched these
            # rows, not `covering[0]` (Codex P2, PR #273).  Routing above
            # retires a row when ANY covering lock's population holds it, so
            # with overlapping locks the first-by-registry-order lock can own
            # zero of them — and the compact `redacted_cells` view drops
            # `covering_locks`, so it would publish that lock's registry_id,
            # threshold and (possibly zero) population as the cause.  That
            # misstates trigger progress for the lock that did the redacting.
            matched = [sum(1 for t in rows
                           if row_in_lock_population(t, lk,
                                                     as_of_exclusive=win_hi))
                       for lk in covering]
            # argmax, ties broken by registry order = stable output.
            lock = covering[matched.index(max(matched))] if covering else None
            rec = count_only_record(
                level, k, len(unique_rows), lock,
                lock_population_n=lock_population_count(
                    trades, lock, as_of_exclusive=win_hi),
                lock_population_watcher_n=lock_population_count(
                    trades, lock, watcher_compat=True,
                    as_of_exclusive=win_hi))
            if len(covering) > 1:
                # Overlapping LOCKs: report EACH lock's population separately.
                # Collapsing them into one number would misrepresent the other
                # lock's gate.  `n_rows_matched` makes the primary's selection
                # auditable instead of implicit.
                rec["covering_locks"] = [
                    {"registry_id": lk.get("registry_id"),
                     "n_lock_population": lock_population_count(
                         trades, lk, as_of_exclusive=win_hi),
                     "n_decide": lk.get("n_decide"),
                     "n_rows_matched": mt,
                     "primary": lk is lock}
                    for lk, mt in zip(covering, matched)]
            out.append(rec)
        return out

    # `min_n` gates MULTIPLICITY eligibility, but the redaction/count inventory
    # must cover EVERY non-empty locked group: a LOCK whose own threshold is
    # below min_n (kalman: n_decide=10) otherwise produced no record at all —
    # no redacted_cell_count, no n_lock_population — even once its declared
    # look had been reached (Codex P2, PR #273).
    v2_eval = (eval_cells(v2_elig, m_family, "v2")
               + locked_records(locked_v2_keys, locked_v2, "v2"))
    v3_eval = (eval_cells(v3_elig, m_family, "v3")
               + locked_records(locked_v3_keys, locked_v3, "v3"))
    candidates = [c for c in (v2_eval + v3_eval) if c.get("promoted")]
    redacted_cells = [c for c in (v2_eval + v3_eval) if c.get("redacted")]

    near = eval_cells({k: v for k, v in v2.items() if len(v) >= 5},
                      max(1, m_family), "v2_all")
    near = [c for c in near
            if not c.get("redacted") and c.get("ev_net") and c["ev_net"] > 0][:8]

    span_lo = min((r["entry_time"] for r in clean if r["entry_time"]), default="?")[:19]
    span_hi = max((r["entry_time"] for r in clean if r["entry_time"]), default="?")[:19]

    return {
        "run_date": run_date,
        "tool": "tools/cell_deepdive_audit.py (in-repo since 2026-09-20; "
                "cell_edge_audit.py v2/v3 methodology against Render PROD API)",
        "data_source": "https://fx-ai-trader.onrender.com/api/demo/trades (PROD) "
                       "— LOCAL demo_trades.db is STALE",
        "window": f"{window_days}d enforced [{win_lo}, {win_hi}) "
                  f"(data span {span_lo} -> {span_hi})",
        "scope": f"Live + Shadow ({shadow_n}/{len(clean)} clean rows are shadow)",
        "filters": {"exclude_xau": True, "exclude_dedup_violation": True,
                    "outcome_in": ["WIN", "LOSS"],
                    "window_days": window_days,
                    "entry_time_ge": win_lo, "entry_time_lt": win_hi},
        "prereg_lock_redaction": {
            "locked_cells": locked_cells,
            "redacted_cell_count": len(redacted_cells),
            "redacted_cells": [
                {"level": c["level"], "cell": c["cell"],
                 "n_unique_rows_in_window": c["n_unique_rows_in_window"],
                 "n_lock_population": c.get("n_lock_population"),
                 "n_lock_population_watcher": c.get("n_lock_population_watcher"),
                 "watcher_divergence": c.get("watcher_divergence"),
                 "n_decide": c.get("n_decide"),
                 "registry_id": c.get("redaction_registry_id")}
                for c in redacted_cells
            ],
            "watcher_divergent_locks": [
                {"registry_id": c.get("redaction_registry_id"),
                 "cell": c["cell"],
                 "n_prereg_faithful": c.get("n_lock_population"),
                 "n_watcher": c.get("n_lock_population_watcher")}
                for c in redacted_cells if c.get("watcher_divergence")
            ],
            "watcher_divergence_note":
                "shadow LOCK の母集団定義が pre-reg 原文 (shadow rows のみ) と "
                "canonical watcher count_matching (oanda_trade_id で絞らない) "
                "で食い違う。両方を出して差異を可視化するのみ — どちらを採るかは "
                "LOCK トリガの計数規則の変更につき user 決裁 "
                "(registry sr-anti-hunt-eurjpy-count-basis-declaration)",
            "locks_not_yet_started": [
                {"registry_id": lk.get("registry_id"), "since": lk.get("since")}
                for lk in not_yet_started
            ],
            "lock_complement_cells": [list(c) for c in sorted(complement_cells)],
            "marker_locked_rows_excluded": marker_excluded,
            "marker_locks": [
                {"registry_id": lk.get("registry_id"),
                 "reasons_marker": lk.get("reasons_marker"),
                 "n_lock_population": lock_population_count(
                     trades, lk, as_of_exclusive=win_hi),
                 "n_decide": lk.get("n_decide")}
                for lk in marker_locks
            ],
            "note": "outcome statistics NOT COMPUTED for these cells — P-10 "
                    "(no intermediate recomputation until the declared N is "
                    "reached); the lock is checked before any statistic runs",
        },
        "meta": {
            "prod_trades_fetched": len(trades),
            "target_rows_raw": len(target_all),
            "dedup_violation_excluded": dedup_excl,
            "non_winloss_excluded": non_wl,
            "clean_N": len(clean),
            "locked_rows_routed_out": locked_rows_total,
            "min_n": min_n,
            "m_global_v2": m_v2,
            "m_global_v3": m_v3,
            "m_family_v2_union_v3": m_family,
            "candidates": len(candidates),
        },
        "dedup_era_breakdown": dedup_era_breakdown(target_all, targets),
        "unique_accrual": unique_accrual(target_all, targets, run_date),
        "candidates": candidates,
        "eligible_cells_v2": v2_eval,
        "eligible_cells_v3": v3_eval,
        "near_miss_positive_v2": near,
        "target_strategies": strat_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("trades_json", nargs="?",
                   help="snapshot produced by --fetch-to (local DB is stale). "
                        "A bare curl is REJECTED: it cannot prove the response "
                        "was not truncated. Standard flow:\n"
                        "  python3 tools/cell_deepdive_audit.py --fetch-to snap.json\n"
                        "  python3 tools/cell_deepdive_audit.py snap.json "
                        "--run-date $(date -u +%%F)")
    p.add_argument("--run-date", default=datetime.now(timezone.utc).date().isoformat())
    p.add_argument("--out-dir", default=None,
                   help="default: knowledge-base/raw/cell_deepdive/<run-date>")
    p.add_argument("--fetch-to", metavar="PATH",
                   help="paginate /api/demo/trades into PATH with a proven-"
                        "complete _fetch_meta, then exit")
    p.add_argument("--allow-unverified-snapshot", action="store_true",
                   help="audit a snapshot whose completeness is NOT proven "
                        "(loud warning; still refuses a full page)")
    p.add_argument("--fetch-limit", type=int, default=100000,
                   help="the ?limit= used when fetching; the snapshot must be a "
                        "SHORT page (len < limit) to prove completeness")
    p.add_argument("--min-rows", type=int, default=None,
                   help=f"refuse a snapshot smaller than this (truncation "
                        f"guard; default {_DEFAULT_MIN_ROWS}, PROD currently "
                        f"returns ~18k rows). Passing a value <= "
                        f"{_API_DEFAULT_LIMIT} EXPLICITLY also waives the "
                        f"exactly-{_API_DEFAULT_LIMIT}-rows truncation "
                        f"signature, for deliberately tiny snapshots")
    p.add_argument("--window-days", type=int, default=365,
                   help="audit window length ending at --run-date (default 365)")
    p.add_argument("--no-write", action="store_true", help="print only")
    return p


def _row_identity(row: dict):
    """Stable identity for de-duplicating a paginated snapshot.

    demo_trades has `id INTEGER PRIMARY KEY` and `trade_id TEXT UNIQUE`, and
    /api/demo/trades does `SELECT *`, so a real page always carries one.  The
    key is (field, value) so that id=5 and trade_id="5" cannot collide.

    Raises when neither field is present: without an identity we cannot tell a
    drift duplicate from a distinct row, so completeness would be an unbacked
    assertion.  Same invariant as everywhere else in this tool — never fold
    "cannot verify" into "fine" (Codex P2, PR #273).
    """
    if isinstance(row, dict):
        for field in ("id", "trade_id"):
            v = row.get(field)
            if v is not None and v != "":
                return (field, v)
    raise SystemExit(
        "paginated row carries neither 'id' nor 'trade_id' "
        f"(keys: {sorted(row)[:8] if isinstance(row, dict) else type(row).__name__}) "
        "— cannot de-duplicate page drift, so completeness cannot be claimed")


def _paginate_pass(fetch_page, page_size: int, max_pages: int) -> dict:
    """ONE full offset pass, de-duplicated by row identity.

    Returns the rows kept plus this pass's drift evidence.  Mirrors
    prereg_trigger_watch.paginate_closed_trades: exhausting max_pages is NOT
    completeness, so it raises instead of returning a silently truncated list.

    The cursor is how many rows the server has already SERVED, not how many we
    kept (Codex P2, PR #273).  Dropping a duplicate and then re-requesting the
    same offset would re-read the same page forever.
    """
    rows: list = []
    seen: set = set()
    fetched = 0                                # rows SERVED == the cursor
    dups = 0
    for page in range(max_pages):
        got = fetch_page(page_size, fetched)
        fetched += len(got)
        for row in got:
            key = _row_identity(row)
            if key in seen:
                dups += 1                      # page drift, not new data
                continue
            seen.add(key)
            rows.append(row)
        if len(got) < page_size:               # short page == end of data
            return {"rows": rows, "pages": page + 1,
                    "rows_served": fetched, "duplicates_dropped": dups}
    raise SystemExit(
        f"pagination hit max_pages={max_pages} at {len(rows)} rows without a "
        f"short page — refusing to return a silently truncated snapshot")


def paginate_trades(fetch_page, page_size: int = 20000,
                    max_pages: int = 50, max_attempts: int = 3) -> dict:
    """Page until a DRIFT-FREE short page proves the end was reached.

    `fetch_page(limit, offset) -> list[dict]`.  Returns a payload carrying
    `_fetch_meta.complete`, which is the only completeness evidence this tool
    accepts.

    get_closed_trades pages with a bare `ORDER BY exit_time DESC LIMIT ?
    OFFSET ?` — no keyset, no snapshot — so a trade that closes mid-pass is
    inserted at the FRONT.  That has TWO consequences, not one (Codex P2,
    PR #273; the skip half was found by this file's own test on 2026-09-22):

    1. IT DUPLICATES.  Every already-passed row shifts one offset further, so
       a fixed cursor re-reads a boundary row.  Undeduplicated, that inflates
       N, the multiplicity family and the LOCK population counts.

    2. IT ALSO SKIPS — and de-duplicating does NOT repair that.  The inserted
       row itself lands at an offset the cursor has already gone past, so it
       is never served at all.  The union of a drifted pass is therefore NOT
       exact: it is missing the newest closed trade while the short page still
       "proves" the end.  The residual error points at UNDER-count, i.e. the
       direction that reads as "no trade happened" — the same false-negative
       direction as the hunt_events readout.

    So a dropped duplicate is evidence that a row may also have been SKIPPED,
    and `complete=true` is claimed only for a pass that dropped none.  A
    drifted pass is discarded and re-run — by then the insertion sits at a
    stable offset, so the retry collects it — and if every attempt drifts we
    raise rather than hand back a snapshot whose completeness we cannot back.
    Never fold "cannot verify" into "fine", the same invariant as everywhere
    else in this tool.
    """
    drift_observed: list = []
    for attempt in range(1, max_attempts + 1):
        got = _paginate_pass(fetch_page, page_size, max_pages)
        if got["duplicates_dropped"] == 0:
            return {"count": len(got["rows"]), "trades": got["rows"],
                    "_fetch_meta": {"complete": True, "limit": page_size,
                                    "pages": got["pages"],
                                    "rows": len(got["rows"]),
                                    "rows_served": got["rows_served"],
                                    "duplicates_dropped": 0,
                                    "attempts": attempt,
                                    "drift_observed": drift_observed}}
        drift_observed.append(got["duplicates_dropped"])
    raise SystemExit(
        f"page drift on all {max_attempts} attempts (duplicates dropped per "
        f"attempt: {drift_observed}) — a drifted pass can SKIP the newly "
        f"closed row entirely, so completeness cannot be claimed. Re-run, or "
        f"fetch a snapshot the writer is not appending to")


def merge_open_into_closed(open_rows: list, closed_rows: list) -> tuple:
    """Prepend open rows, dropping any that already closed mid-fetch.

    The open list is fetched AFTER the closed pages, so a trade that closed in
    between appears in both.  Keep the CLOSED copy (it carries exit_time /
    outcome) and report how many open rows were dropped, rather than letting
    one trade be counted twice (Codex P2, PR #273).
    """
    closed_keys = {_row_identity(r) for r in closed_rows}
    kept = [r for r in open_rows if _row_identity(r) not in closed_keys]
    return kept + closed_rows, len(open_rows) - len(kept)


def _http_fetch(status: str, limit: int, offset: int) -> list:
    """One page from /api/demo/trades with an EXPLICIT status.

    `status` must never be left at the endpoint default ("all"): that route
    returns `open_t + closed_t`, i.e. it prepends the WHOLE open-trade list to
    EVERY page.  Paging by accumulated length then skips that many closed rows
    while duplicating the open ones — and a later short page would still mark
    the snapshot complete (Codex P2, PR #273).
    """
    from urllib.request import urlopen
    url = (f"https://fx-ai-trader.onrender.com/api/demo/trades"
           f"?status={status}&limit={limit}&offset={offset}")
    with urlopen(url, timeout=300) as r:        # noqa: S310 (fixed PROD host)
        payload = json.load(r)
    # An HTTP-200 error object must NOT become []: paginate_trades would read
    # that as a short page proving end-of-data, keep whatever pages already
    # succeeded, and stamp _fetch_meta.complete=true on a truncated snapshot
    # (Codex P2, PR #273).  Never fold "cannot inspect" into "no more data".
    # The ENDPOINT always returns an object carrying `trades` (app.py), so a
    # top-level list is not a valid page here — and accepting one re-opened the
    # hole this check exists to close: an HTTP-200 `[]` from a proxy or a
    # malformed backend would be read by `_paginate_pass` as the short page
    # proving end-of-data, keeping the earlier partial pages and stamping
    # `complete=true` on them (Codex P2, PR #273).  Require the documented
    # shape.  NOTE: the SAVED-SNAPSHOT reader below still accepts a bare array,
    # deliberately — a local file is a different population (a hand-made or
    # `jq '.trades'` snapshot is legitimate there, and its completeness is
    # gated separately by `_fetch_meta`).  Which convention is specific to
    # which population has to be decided per population, not globally
    # ([[feedback_check_the_symmetric_side_2026_09_19]]).
    if not isinstance(payload, dict) or not isinstance(payload.get("trades"), list):
        keys = sorted(payload)[:8] if isinstance(payload, dict) else type(payload).__name__
        raise SystemExit(
            f"/api/demo/trades?status={status}&limit={limit}&offset={offset}: "
            f"response has no list-valued 'trades' (got {keys}) — aborting the "
            f"fetch rather than treating it as end-of-data")
    return payload["trades"]


def _http_fetch_closed_page(limit: int, offset: int) -> list:
    return _http_fetch("closed", limit, offset)


def _http_fetch_open(limit: int = 100000) -> list:
    return _http_fetch("open", limit, 0)


def _fetch_bracketed(max_attempts: int = 3) -> tuple:
    """open -> closed pages -> open, retried until no row fell in a hole.

    Returns (open_rows, closed_payload, evidence).  `open_rows` is the UNION of
    the two open reads, so a trade that opened during the closed pass is
    present even though it never appears in the closed pages.

    Completeness rests on TWO checks, because one of them cannot see the other
    one's hazard (Codex P2, PR #273, two rounds):

    1. A row that was open BEFORE the pass and appears in neither the second
       open read nor the closed pages closed inside the window and was served
       to nobody.
    2. A trade whose ENTIRE lifecycle falls inside the bracket is in none of
       those three reads, so (1) cannot find it.  A second closed pass can:
       closed trades are append-only, so the confirming pass is a superset of
       the first, and the difference is exactly what closed during the
       bracket.  Equality PROVES nothing closed inside the window.

    Either signal discards the attempt and re-runs; if every attempt moves we
    raise instead of claiming completeness.
    """
    holes: list = []
    for attempt in range(1, max_attempts + 1):
        open_before = _http_fetch_open()
        payload = paginate_trades(_http_fetch_closed_page)
        open_after = _http_fetch_open()
        confirm = paginate_trades(_http_fetch_closed_page)

        closed_keys = {_row_identity(r) for r in payload["trades"]}
        confirm_keys = {_row_identity(r) for r in confirm["trades"]}
        after_keys = {_row_identity(r) for r in open_after}

        # A trade whose WHOLE lifecycle falls inside the bracket — opened after
        # `open_before`, closed before `open_after`, closing behind the cursor
        # — is in none of the first three reads, so searching `open_before`
        # cannot find it (Codex P2, PR #273).  The SECOND closed pass can:
        # closed trades are append-only (never deleted), so
        # `confirm_keys ⊇ closed_keys` always, and the difference is exactly
        # the set of trades that closed during the bracket, whatever they were
        # doing beforehand.  Equality is therefore a PROOF that nothing closed
        # inside the window — not a heuristic.
        closed_during = confirm_keys - closed_keys
        missed = [r for r in open_before
                  if _row_identity(r) not in after_keys
                  and _row_identity(r) not in closed_keys]
        if missed or closed_during:
            # Report the two signals SEPARATELY: the same trade can trip both
            # (it was open before AND closed during), and summing them would
            # overstate how many rows were actually unaccounted for.
            holes.append({"open_rows_lost": len(missed),
                          "closed_during_bracket": len(closed_during)})
            continue

        # The CONFIRMING closed pass also wins on VALUES, not just on keys
        # (Codex P2, PR #273).  A closed row mutates in the normal async OANDA
        # path too: `DemoDB.set_oanda_trade_id()` updates `oanda_trade_id` and
        # `is_shadow` with no status predicate, so a fast-closing trade can be
        # mutated after it entered the closed set.  Equal key sets then pass
        # the check above while the older pass's STALE SHADOW representation
        # is what gets written — wrong live/shadow LOCK populations under a
        # `complete=true` stamp.  This is the exact mirror of the open-row case
        # below, which the previous round fixed; the symmetric side has to be
        # checked on the fix itself, not only on the original code.
        by_id_first = {_row_identity(r): r for r in payload["trades"]}
        closed_mutated = sum(1 for r in confirm["trades"]
                             if by_id_first.get(_row_identity(r)) != r)
        payload["trades"] = confirm["trades"]          # newer values win
        payload["_fetch_meta"]["closed_mutated_midfetch"] = closed_mutated
        # Keep BOTH passes' drift evidence; the confirming pass is part of the
        # completeness argument, so its own retries must stay visible.
        payload["_fetch_meta"]["confirm_pass"] = {
            "attempts": confirm["_fetch_meta"]["attempts"],
            "drift_observed": confirm["_fetch_meta"]["drift_observed"],
            "rows": confirm["_fetch_meta"]["rows"],
        }

        # `open_after` WINS for an identity present in both (Codex P2,
        # PR #273).  Keeping the `open_before` copy is not a harmless choice of
        # duplicate: an open row MUTATES in the normal live path, where the
        # OANDA callback `DemoDB.set_oanda_trade_id()` fills `oanda_trade_id`
        # and flips `is_shadow` while the row stays open.  The bracket compares
        # identities, so that mutation is invisible to the hole checks — and
        # the stale copy would report a LIVE trade as shadow, which is the one
        # distinction this project treats as load-bearing
        # ([[feedback_live_vs_shadow_strict_separation]], and the conflation
        # incident [[project_live_fill_estimand_shadow_conflation_2026_09_03]]).
        # The newer read is strictly closer to the truth at snapshot time.
        by_key = {_row_identity(r): r for r in open_before}
        opened_midfetch = 0
        mutated_midfetch = 0
        for r in open_after:
            k = _row_identity(r)
            if k not in by_key:
                opened_midfetch += 1           # opened during the pass
            elif by_key[k] != r:
                mutated_midfetch += 1         # e.g. shadow -> live
            by_key[k] = r
        return (list(by_key.values()), payload,
                {"attempts": attempt, "opened_midfetch": opened_midfetch,
                 "mutated_midfetch": mutated_midfetch,
                 "holes_observed": holes})
    raise SystemExit(
        f"the book moved inside the fetch window on all {max_attempts} "
        f"attempts (rows unaccounted for per attempt: {holes}) — a trade that "
        f"closes inside the bracket can be absent from every read, so "
        f"completeness cannot be claimed. Re-run when the book is quieter, or "
        f"fetch from a server-side stable snapshot")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.fetch_to:
        # The closed pass is BRACKETED by two open reads (Codex P2, PR #273,
        # two rounds).  Neither single order is sound, and they fail in mirror
        # directions:
        #   closed -> open : a trade CLOSING in between is in neither set
        #                    (still open for the closed pass, already closed
        #                    for the open request)
        #   open -> closed : a trade OPENING in between is in neither set
        #                    (not yet open for the open request, never closed
        #                    so never in the closed pages)
        # Fixing only the first order produced the second — the symmetric side
        # of the same window ([[feedback_check_the_symmetric_side_2026_09_19]]).
        # Bracketing makes BOTH observable: open_before ∪ open_after covers a
        # mid-pass open, and a row that was open BEFORE but is in neither
        # open_after nor the closed pages is a row that closed inside the
        # window and was missed — a hole.  A hole is evidence, so we discard
        # the attempt and retry rather than stamp complete=true over it.
        open_rows, payload, brackets = _fetch_bracketed()
        merged, open_dropped = merge_open_into_closed(open_rows,
                                                      payload["trades"])
        payload["trades"] = merged
        payload["count"] = len(payload["trades"])
        payload["_fetch_meta"].update({"status": "closed+open",
                                       "closed": payload["_fetch_meta"]["rows"],
                                       "open": len(open_rows) - open_dropped,
                                       "open_closed_midfetch": open_dropped,
                                       "open_attempts": brackets["attempts"],
                                       "open_opened_midfetch":
                                           brackets["opened_midfetch"],
                                       "open_mutated_midfetch":
                                           brackets["mutated_midfetch"],
                                       "holes_observed":
                                           brackets["holes_observed"]})
        with open(args.fetch_to, "w") as f:
            json.dump(payload, f)
        m = payload["_fetch_meta"]
        print(f"wrote {args.fetch_to}: {payload['count']} rows "
              f"(closed {m['closed']} in {m['pages']} pages + open {m['open']}, "
              f"page attempt {m['attempts']}, discarded drifted passes "
              f"{m['drift_observed']}, bracket attempt {m['open_attempts']} "
              f"(discarded holes {m['holes_observed']}), opened mid-fetch "
              f"{m['open_opened_midfetch']}, open-rows-already-closed dropped "
              f"{m['open_closed_midfetch']}, completeness proven)")
        return 0
    if not args.trades_json:
        raise SystemExit("trades_json is required unless --fetch-to is used")
    with open(args.trades_json) as f:
        payload = json.load(f)
    # An error object (or a truncated response) must NOT become an empty
    # dataset: without --no-write the run would overwrite the weekly summary
    # with a plausible-looking PROD report showing zero rows and no candidates,
    # instead of reporting that input acquisition failed (Codex P2, PR #273).
    # Same invariant as the registry loader: never fold "cannot inspect" into
    # "nothing wrong".
    if isinstance(payload, list):
        trades = payload
    elif isinstance(payload, dict):
        if "trades" not in payload:
            raise SystemExit(
                f"{args.trades_json}: no 'trades' key (keys: {sorted(payload)[:10]}) "
                "— refusing to treat a failed fetch as an empty dataset")
        trades = payload["trades"]
    else:
        raise SystemExit(
            f"{args.trades_json}: root is {type(payload).__name__}, "
            "expected an object with 'trades' or a list")
    if not isinstance(trades, list):
        raise SystemExit(
            f"{args.trades_json}: 'trades' is {type(trades).__name__}, expected a list")

    # Completeness. /api/demo/trades defaults to limit=50 (app.py), so a plain
    # curl of the documented URL yields a plausible but severely truncated
    # audit — and without --no-write it overwrites the weekly summary with
    # wrong N, multiplicity and candidates.  `count` equals len(trades) in the
    # response, so it cannot detect truncation on its own; we fail loud on the
    # signatures instead (Codex P2, PR #273).  Same invariant as the registry
    # loader and paginate_closed_trades: never fold "cannot verify" into "fine".
    if isinstance(payload, dict):
        count = payload.get("count")
        if count is not None and count != len(trades):
            raise SystemExit(
                f"{args.trades_json}: 'count' ({count}) != len(trades) "
                f"({len(trades)}) — inconsistent snapshot, refusing to audit")
    # The escape hatch named in the error below must actually work: this
    # branch used to run unconditionally and ahead of the --min-rows check, so
    # `--min-rows 0` could never reach it (Codex P3, PR #273).  An EXPLICIT
    # --min-rows at or below the signature value is the caller declaring that a
    # tiny snapshot is intended, which is exactly when the heuristic is wrong.
    min_rows = _DEFAULT_MIN_ROWS if args.min_rows is None else args.min_rows
    waives_signature = args.min_rows is not None and min_rows <= _API_DEFAULT_LIMIT
    if len(trades) == _API_DEFAULT_LIMIT and not waives_signature:
        raise SystemExit(
            f"{args.trades_json}: exactly {_API_DEFAULT_LIMIT} rows — that is "
            f"/api/demo/trades' DEFAULT limit, i.e. almost certainly a "
            f"truncated first page. Re-fetch with ?limit=100000 "
            f"(or pass --min-rows 0 if you really mean {_API_DEFAULT_LIMIT})")
    if len(trades) < min_rows:
        raise SystemExit(
            f"{args.trades_json}: only {len(trades)} rows < --min-rows "
            f"{min_rows} — a truncated page must not silently become an "
            f"audit. Re-fetch with ?limit=100000, or lower --min-rows "
            f"deliberately")
    # Reaching a floor is NOT proof of completeness: ?limit=1000 returns
    # exactly 1000 rows and `count` is the PAGE length, so a truncated fetch
    # passes both checks above.  Completeness is proven only by a SHORT page —
    # len(trades) < the limit actually requested (Codex P2, PR #273).  Same
    # idiom as prereg_trigger_watch.paginate_closed_trades, which returns None
    # (DATA_UNAVAILABLE) rather than a silently truncated list.
    # `--fetch-limit` is a CALLER ASSERTION, not evidence: a snapshot fetched
    # with ?limit=1000 audited under CLI defaults compares 1000 rows against
    # 100000 and passes while being a full truncated page (Codex P2, PR #273).
    # Completeness must come from the SNAPSHOT.  `_fetch_meta` is written by
    # fetch_prod_trades(), which paginates and only marks complete=true after
    # it actually sees a short page.
    meta = payload.get("_fetch_meta") if isinstance(payload, dict) else None
    if isinstance(meta, dict) and meta.get("complete") is True:
        pass                                   # proven by construction
    elif args.allow_unverified_snapshot:
        print(f"[WARN] {args.trades_json}: completeness NOT verified "
              f"(--allow-unverified-snapshot). N / multiplicity / candidates "
              f"may be wrong.", file=sys.stderr)
        if len(trades) >= args.fetch_limit:
            raise SystemExit(
                f"{args.trades_json}: {len(trades)} rows >= --fetch-limit "
                f"{args.fetch_limit} — a FULL page proves nothing about "
                f"completeness even with --allow-unverified-snapshot")
    else:
        raise SystemExit(
            f"{args.trades_json}: no '_fetch_meta.complete' — a bare curl "
            f"cannot prove the response was not truncated, and --fetch-limit "
            f"is only an assertion about a file it is not recorded in.\n"
            f"Fetch with this tool instead:\n"
            f"  python3 tools/cell_deepdive_audit.py --fetch-to {args.trades_json}\n"
            f"or pass --allow-unverified-snapshot to audit it anyway "
            f"(the report may carry truncated N / multiplicity / candidates)")
    result = run_audit(trades, run_date=args.run_date,
                       window_days=args.window_days)
    if not args.no_write:
        out_dir = args.out_dir or str(
            PROJECT_ROOT / "knowledge-base" / "raw" / "cell_deepdive" / args.run_date)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "_summary.json"), "w") as f:
            json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
