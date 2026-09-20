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

    locked = []
    for e in entries:
        # Canonical loader is `t.get("active", True)` — an omitted flag means
        # ACTIVE.  Treating it as inactive would let the watcher evaluate a
        # LOCK this audit publishes unredacted (Codex P2, PR #273).
        if not e.get("active", True):
            continue
        if not str(e.get("type", "")).endswith("_count_decision"):
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
            "match": "prefix" if e.get("match") == "prefix" else "exact",
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


def row_in_lock_population(t, lock, *, watcher_compat: bool = False) -> bool:
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
    if kind == "shadow" and live and not watcher_compat:
        # Pre-reg text for the shadow LOCKs says the population is
        # "dedup_violation=0 の shadow rows のみ", and MEMORY
        # feedback_live_vs_shadow_strict_separation makes live =
        # oanda_trade_id != ''.  The canonical watcher's count_matching does
        # NOT apply this filter, so the two can diverge once a shadow LOCK's
        # cell starts taking live fills.  We do NOT silently pick a side on a
        # LOCK trigger: `watcher_compat=True` reproduces the watcher and the
        # report emits BOTH counts plus a divergence flag (Codex P2, PR #273).
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
    return True


def lock_population_count(trades, lock, *, watcher_compat: bool = False) -> int:
    """Count rows in the LOCK's OWN declared population.

    The registry entry — not this audit's window — defines what the trigger
    counts: ``since``, ``closed_only``, ``dedup_violation``, ``mode`` and
    shadow-vs-live.  Emitting the cell's in-window row count instead would be
    the very defect this PR documents (a count that does not match the
    estimand printed beside it).
    """
    return sum(1 for t in trades
               if row_in_lock_population(t, lock, watcher_compat=watcher_compat))


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
    marker_locks = [lk for lk in locked_cells if lk.get("reasons_marker")]
    cell_locks = [lk for lk in locked_cells if lk.get("entry_type")]
    marker_excluded = 0

    # LOCKed rows are routed out from the RAW rows, before `outcome`/`pnl_pips`
    # is ever read.  Previously they passed through the WIN/LOSS filter first,
    # so the emitted count was itself a function of outcome (a BREAKEVEN row
    # changed both the count and whether the cell appeared at all) — the very
    # 35-vs-36 discrepancy this analysis documents, reproduced inside the tool
    # meant to fix it (Codex P1, PR #273).
    locked_raw = defaultdict(list)
    open_raw = []
    for t in target_all:
        if marker_locks and any(row_in_lock_population(t, lk)
                                for lk in marker_locks):
            marker_excluded += 1
            continue
        lock = lock_for_cell(t.get("entry_type"), t.get("instrument"),
                             t.get("direction"), cell_locks)
        if lock is not None:
            locked_raw[(t.get("entry_type"), t.get("instrument"),
                        t.get("direction"))].append(t)
            continue
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
    locked_v2 = defaultdict(list)
    locked_v3 = defaultdict(list)
    for key, rows in locked_raw.items():
        for t in rows:
            if t.get("dedup_violation") == 1:
                continue
            locked_v2[key].append(t)
            locked_v3[(key[0], key[1], derive_session(t.get("entry_time")),
                       key[2])].append(t)

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
            out.append(rec)
        out.sort(key=lambda x: (x.get("redacted", False), -x.get("wilson_lo", 0.0)))
        return out

    def locked_records(groups, level):
        out = []
        for k, rows in groups.items():
            lock = lock_for_cell(k[0], k[1], k[-1], cell_locks)
            out.append(count_only_record(
                level, k, len(rows), lock,
                lock_population_n=lock_population_count(trades, lock),
                lock_population_watcher_n=lock_population_count(
                    trades, lock, watcher_compat=True)))
        return out

    v2_eval = eval_cells(v2_elig, m_family, "v2") + locked_records(locked_v2_elig, "v2")
    v3_eval = eval_cells(v3_elig, m_family, "v3") + locked_records(locked_v3_elig, "v3")
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
            "marker_locked_rows_excluded": marker_excluded,
            "marker_locks": [
                {"registry_id": lk.get("registry_id"),
                 "reasons_marker": lk.get("reasons_marker"),
                 "n_lock_population": lock_population_count(trades, lk),
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
    p.add_argument("trades_json",
                   help="PROD /api/demo/trades JSON (fetch with curl; local DB is stale)")
    p.add_argument("--run-date", default=datetime.now(timezone.utc).date().isoformat())
    p.add_argument("--out-dir", default=None,
                   help="default: knowledge-base/raw/cell_deepdive/<run-date>")
    p.add_argument("--window-days", type=int, default=365,
                   help="audit window length ending at --run-date (default 365)")
    p.add_argument("--no-write", action="store_true", help="print only")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
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
