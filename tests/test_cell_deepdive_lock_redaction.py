"""Pins for tools/cell_deepdive_audit.py (rule:R3, 2026-09-20).

Two defects are pinned here, both of which survived 10 weekly runs because the
tool lived outside the repo as an ad-hoc script with no tests:

1. Outcome statistics of a cell under an active pre-reg LOCK must never be
   emitted (P-10: no intermediate recomputation before the declared N).
2. ``dedup_violation`` accounting must be split by gate-fix era — the overall
   rate mixes a one-shot April backfill burst with the ongoing rate.

Per the "detectors need a known-NG input pinned in the same commit" lesson,
every redaction assertion is paired with a non-redaction assertion, so a
redactor that redacts everything (or nothing) fails.
"""

import json
from pathlib import Path

import pytest

import tools.cell_deepdive_audit as cda
from tools.cell_deepdive_audit import (
    DEDUP_GATE_FIX_TS,
    REDACTED_FIELDS,
    LockRegistryUnavailable,
    dedup_era_breakdown,
    load_locked_cells,
    lock_for_cell,
    lock_population_count,
    row_in_lock_population,
    unique_accrual,
    _entry_type_matches,
    run_audit,
    window_bounds,
)

LOCKED = [
    {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
     "direction": "BUY", "registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm"},
    {"entry_type": "sr_anti_hunt_bounce", "instrument": "USD_JPY",
     "direction": None, "registry_id": "ws3-t11-anti-hunt-usdjpy-recheck"},
]


def _rows(entry_type, instrument, direction, n, *, wins, base_ts="2026-08-10T0"):
    out = []
    for i in range(n):
        out.append({
            "entry_type": entry_type,
            "instrument": instrument,
            "direction": direction,
            "outcome": "WIN" if i < wins else "LOSS",
            "pnl_pips": 10.0 if i < wins else -5.0,
            "dedup_violation": 0,
            "is_shadow": 1,
            "mode": "daytrade",
            # 02:00Z keeps every row in the Tokyo session bucket, so the v3
            # sub-cell is a strict refinement of the v2 cell.
            "entry_time": f"2026-08-{10 + (i % 18):02d}T02:{i % 60:02d}:00",
        })
    return out


# ── 1. LOCK redaction ─────────────────────────────────────────────────────

def test_locked_cell_outcome_fields_are_redacted():
    """KNOWN-NG INPUT: a LOCKed cell with a blowout win rate.

    Before this fix the weekly report printed exactly these numbers.
    """
    trades = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=36)
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)

    v2 = [c for c in res["eligible_cells_v2"]
          if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]]
    assert v2, "the LOCKed cell should still appear (its N drives the trigger)"
    rec = v2[0]
    assert rec["redacted"] is True
    assert rec["n_unique_rows_in_window"] == 40, "the row count must survive"
    assert "n" not in rec, "a bare 'n' is ambiguous next to a gate threshold"
    for field in REDACTED_FIELDS:
        assert field not in rec, f"{field} leaked for a LOCKed cell"
    assert rec["redaction_registry_id"] == "sr-anti-hunt-eurjpy-buy-forward-confirm"

    # ...and the whole serialized payload must not carry the win count either.
    blob = json.dumps(res)
    assert '"wr"' not in blob or not any(
        c.get("redacted") and "wr" in c for c in res["eligible_cells_v2"])


def test_unlocked_cell_keeps_its_outcome_fields():
    """Counter-pin: the redactor must not be vacuously redacting everything."""
    trades = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 40, wins=36)
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("vsg_jpy_reversal",), locked_cells=LOCKED)

    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["vsg_jpy_reversal", "EUR_JPY", "SELL"]][0]
    assert rec["redacted"] is False
    for field in REDACTED_FIELDS:
        assert field in rec, f"{field} missing for an unlocked cell"
    assert rec["wr"] == pytest.approx(0.9)


def test_sub_cell_of_locked_cell_is_also_redacted():
    """A session split of a LOCKed cell reveals it more sharply, not less.

    This is the exact shape the 2026-09-20 run published as a "PAIR_PROMOTED
    candidate" for 4 consecutive weeks (the Tokyo sub-cell).
    """
    trades = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=36)
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)

    v3 = [c for c in res["eligible_cells_v3"]
          if c["cell"][:2] == ["sr_anti_hunt_bounce", "EUR_JPY"]]
    assert v3, "expected a v3 sub-cell for this fixture"
    for rec in v3:
        assert rec["redacted"] is True
        assert "wr" not in rec
    assert res["candidates"] == [], "a redacted cell can never be a candidate"


def test_wildcard_direction_lock_covers_both_directions():
    """ws3-t11 locks sr_anti_hunt_bounce x USD_JPY with direction=None."""
    trades = (_rows("sr_anti_hunt_bounce", "USD_JPY", "BUY", 25, wins=20)
              + _rows("sr_anti_hunt_bounce", "USD_JPY", "SELL", 25, wins=5))
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    cells = [c for c in res["eligible_cells_v2"] if c["cell"][1] == "USD_JPY"]
    assert len(cells) == 2
    assert all(c["redacted"] for c in cells)


def test_lock_does_not_cover_a_different_pair():
    """GBP_JPY is not under LOCK — it must stay fully reported."""
    assert lock_for_cell("sr_anti_hunt_bounce", "GBP_JPY", "BUY", LOCKED) is None
    assert lock_for_cell("sr_anti_hunt_bounce", "EUR_JPY", "SELL", LOCKED) is None
    assert lock_for_cell("sr_anti_hunt_bounce", "EUR_JPY", "BUY", LOCKED) is not None
    assert lock_for_cell("sr_anti_hunt_bounce", "USD_JPY", "SELL", LOCKED) is not None


def test_registry_loader_sees_the_live_lock_and_skips_info_entries():
    """Reads the real registry: the loader must be neither empty nor vacuous."""
    locked = load_locked_cells()
    ids = {lk["registry_id"] for lk in locked}
    assert "sr-anti-hunt-eurjpy-buy-forward-confirm" in ids, (
        "the nearest pre-reg trigger must be redacted")
    # *_count_info entries are frequency monitors with no outcome gate.
    assert "t8-hull-shadow-freq" not in ids
    assert "t9-kalman-d7-fire-info" not in ids
    # Resolved/inactive entries must not be redacted forever.
    assert "vix-sell-pilot-recheck" not in ids


# ── 2. dedup era split ────────────────────────────────────────────────────

def test_dedup_era_split_separates_prefix_burst_from_ongoing_rate():
    """KNOWN-NG INPUT: the mqe_gbpusd_fix shape.

    93% overall, 0% post-fix.  Reporting only the overall rate is what made
    the 2026-09-20 run call a frozen April artifact the cause of N starvation.
    """
    pre = [{"entry_type": "mqe_gbpusd_fix", "instrument": "GBP_USD",
            "dedup_violation": 1 if i >= 4 else 0,
            "entry_time": f"2026-04-29T0{i % 10}:00:00"} for i in range(86)]
    post = [{"entry_type": "mqe_gbpusd_fix", "instrument": "GBP_USD",
             "dedup_violation": 0,
             "entry_time": "2026-08-28T15:31:00"} for _ in range(2)]

    out = dedup_era_breakdown(pre + post, ("mqe_gbpusd_fix",))["mqe_gbpusd_fix"]
    assert out["raw"] == 88
    assert out["dedup_rate_pct_overall"] == pytest.approx(93.2, abs=0.1)
    assert out["pre_fix_raw"] == 86
    assert out["post_fix_raw"] == 2
    assert out["post_fix_rate_pct"] == 0.0, (
        "the ongoing rate is 0 — the 93% is a frozen pre-gate artifact")


def test_dedup_gate_fix_timestamp_matches_the_backfill_cutoff():
    """Arithmetic pin: the era boundary must stay tied to commit 6a45bb2.

    If demo_db's cutoff moves, this split silently attributes rows to the
    wrong era.
    """
    from modules.demo_db import DemoDB

    assert DemoDB._DEDUP_BACKFILL_CUTOFF.startswith(DEDUP_GATE_FIX_TS)


# ── 3. Codex P1/P2 (PR #273) ──────────────────────────────────────────────

def test_no_outcome_statistic_is_computed_for_a_locked_cell(monkeypatch):
    """P-10 bans RECOMPUTATION, not just publication (Codex P1).

    Redacting an already-computed dict would still have run the forbidden
    calculation.  This pins the stronger property: for a LOCKed cell the
    outcome-statistics helpers are never invoked at all.
    """
    calls = []

    def spy_cell_stats(rows):
        calls.append(("cell_stats", len(rows)))
        raise AssertionError("cell_stats ran for a LOCKed cell")

    def spy_wf(rows):
        calls.append(("wf_stable", len(rows)))
        raise AssertionError("wf_stable ran for a LOCKed cell")

    monkeypatch.setattr(cda, "cell_stats", spy_cell_stats)
    monkeypatch.setattr(cda, "wf_stable", spy_wf)

    trades = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=36)
    # Only LOCKed cells present -> no helper may run, so this must not raise.
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    assert calls == [], f"outcome helpers ran for a LOCKed cell: {calls}"

    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["redacted"] is True and rec["n_unique_rows_in_window"] == 40


def test_outcome_statistics_still_run_for_unlocked_cells(monkeypatch):
    """Counter-pin: the skip must be lock-scoped, not a global disable."""
    seen = []
    real = cda.cell_stats
    monkeypatch.setattr(
        cda, "cell_stats", lambda rows: (seen.append(len(rows)), real(rows))[1])

    trades = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 40, wins=36)
    run_audit(trades, run_date="2026-09-20",
              targets=("vsg_jpy_reversal",), locked_cells=LOCKED)
    assert seen, "cell_stats must still run for cells that are not LOCKed"


def test_unreadable_registry_fails_closed(tmp_path):
    """KNOWN-NG INPUT: a corrupt registry must abort, not silently unlock.

    Returning [] here would disable every LOCK and publish exactly what this
    module exists to suppress (Codex P1).
    """
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(LockRegistryUnavailable):
        load_locked_cells(missing)

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json")
    with pytest.raises(LockRegistryUnavailable):
        load_locked_cells(corrupt)

    # Counter-pin: a well-formed registry still loads.
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"triggers": [
        {"id": "x", "active": True, "type": "shadow_count_decision",
         "entry_type": "foo", "instrument": "EUR_JPY", "direction": "BUY"}]}))
    assert len(load_locked_cells(ok)) == 1


def test_run_audit_propagates_registry_failure(monkeypatch):
    """The abort must reach run_audit — not be swallowed into an empty list."""
    def boom(*a, **k):
        raise LockRegistryUnavailable("registry gone")

    monkeypatch.setattr(cda, "load_locked_cells", boom)
    with pytest.raises(LockRegistryUnavailable):
        run_audit(_rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=36),
                  run_date="2026-09-20", targets=("sr_anti_hunt_bounce",))


def test_window_is_enforced_not_merely_advertised():
    """KNOWN-NG INPUT: rows outside the advertised 365d window (Codex P2).

    Before the fix the input was filtered only by strategy/XAU, so stale and
    post-run rows silently changed N and multiplicity while the report still
    claimed 365d.
    """
    inside = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 25, wins=20)
    stale = [dict(r, entry_time="2024-01-15T02:00:00") for r in inside[:10]]
    future = [dict(r, entry_time="2027-01-15T02:00:00") for r in inside[:10]]

    res = run_audit(inside + stale + future, run_date="2026-09-20",
                    targets=("vsg_jpy_reversal",), locked_cells=LOCKED)
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["vsg_jpy_reversal", "EUR_JPY", "SELL"]][0]
    assert rec["n"] == 25, "stale/post-run rows must not enter the window"
    assert res["meta"]["target_rows_raw"] == 25
    assert res["filters"]["window_days"] == 365
    assert res["filters"]["entry_time_ge"] == "2025-09-21"
    assert res["filters"]["entry_time_lt"] == "2026-09-21"


def test_window_includes_run_date_itself():
    """A run executed mid-day must not drop that day's rows."""
    lo, hi = window_bounds("2026-09-20", 365)
    assert lo == "2025-09-21"
    assert hi == "2026-09-21"
    assert lo <= "2026-09-20" < hi
    # ...and it spans exactly 365 inclusive calendar days, not 366 (Codex P2).
    from datetime import date
    span = (date.fromisoformat(hi) - date.fromisoformat(lo)).days
    assert span == 365, f"inclusive window must span 365 days, got {span}"
    assert window_bounds("2026-09-20", 1) == ("2026-09-20", "2026-09-21")


def test_strategy_aggregate_excludes_locked_rows():
    """A strategy aggregate must never BE the LOCKed cell.

    KNOWN-NG INPUT: a strategy whose only rows belong to the LOCKed cell.  The
    original "strict super-sets are a different estimand" exemption held only
    when other pairs had rows, so the leak was data-dependent.
    """
    trades = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=36)
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    summ = res["target_strategies"]["sr_anti_hunt_bounce"]
    assert summ["clean_N"] == 0, "every row was LOCKed — nothing may aggregate"
    assert summ["locked_rows_excluded"] == 40
    assert "WR" not in summ and "EV_net_pips" not in summ


def test_strategy_aggregate_keeps_unlocked_rows_only():
    """Counter-pin: unlocked pairs of the same strategy still aggregate."""
    trades = (_rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=40)
              + _rows("sr_anti_hunt_bounce", "GBP_JPY", "BUY", 20, wins=5))
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    summ = res["target_strategies"]["sr_anti_hunt_bounce"]
    assert summ["clean_N"] == 20, "only the unlocked GBP_JPY rows"
    assert summ["locked_rows_excluded"] == 40
    # 5/20 = 0.25 — if the LOCKed 40 WINs had leaked in, WR would be 45/60.
    assert summ["WR"] == pytest.approx(0.25)


def test_lock_count_uses_the_locks_own_population_not_the_audit_window():
    """KNOWN-NG INPUT: rows that are in the cell but OUTSIDE the LOCK population.

    The LOCK counts fresh CLOSED shadow rows since its `since` date.  Emitting
    the cell's whole in-window row count beside the gate threshold reads as
    "the gate has been passed" when it has not (Codex P2, PR #273) — this is
    the same defect class the PR documents: a count that does not match the
    estimand printed next to it.
    """
    lock = {
        "entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
        "direction": "BUY", "registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
        "kind": "shadow", "since": "2026-08-05", "closed_only": True,
        "dedup_violation": 0, "mode": None, "n_decide": 40,
    }

    def row(ts, **kw):
        base = {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
                "direction": "BUY", "outcome": "WIN", "pnl_pips": 1.0,
                "dedup_violation": 0, "is_shadow": 1, "status": "CLOSED",
                "oanda_trade_id": "", "mode": "daytrade", "entry_time": ts}
        base.update(kw)
        return base

    in_pop = [row(f"2026-08-{10 + i:02d}T02:00:00") for i in range(12)]
    pre_since = [row("2026-07-01T02:00:00") for _ in range(9)]      # before `since`
    open_rows = [row("2026-08-20T02:00:00", status="OPEN") for _ in range(5)]
    live_rows = [row("2026-08-21T02:00:00", oanda_trade_id="99") for _ in range(4)]
    dupes = [row("2026-08-22T02:00:00", dedup_violation=1) for _ in range(6)]
    trades = in_pop + pre_since + open_rows + live_rows + dupes

    assert lock_population_count(trades, lock) == 12

    res = run_audit(trades, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["n_lock_population"] == 12, "the gate-relevant count"
    assert rec["n_decide"] == 40
    # Since routing now admits ONLY LOCK-population rows, the routed count and
    # the population agree by construction — the two fields stay distinct
    # because they answer different questions (rows in THIS window vs the
    # LOCK's own `since`-anchored population, which can pre-date the window).
    assert rec["n_unique_rows_in_window"] == rec["n_lock_population"] == 12
    # The same-cell rows outside the population are kept (here 18 clean rows,
    # under min_n so they form no eligible cell) and the cell is recorded as a
    # partial view so the report cannot be misread as covering the whole cell.
    assert res["prereg_lock_redaction"]["lock_complement_cells"] == [
        ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]]
    assert rec["lock_population_predicates"]["since"] == "2026-08-05"
    assert rec["lock_population_predicates"]["closed_only"] is True


def test_lock_population_predicates_are_read_from_the_real_registry():
    """Counter-pin: the live LOCK must carry its population, not defaults."""
    lock = [lk for lk in load_locked_cells()
            if lk["registry_id"] == "sr-anti-hunt-eurjpy-buy-forward-confirm"][0]
    assert lock["since"] == "2026-08-05"
    assert lock["closed_only"] is True
    assert lock["kind"] == "shadow"
    assert lock["n_decide"] == 40
    assert lock["dedup_violation"] == 0


def test_malformed_but_parseable_registry_fails_closed(tmp_path):
    """KNOWN-NG INPUTS: syntax-valid payloads that would silently unlock.

    The first fail-closed fix only caught unreadable files and parse errors;
    these shapes parse fine, iterate to nothing, and return [] (Codex P1,
    PR #273, 2nd instance of the same fail-open class).
    """
    for name, payload in [
        ("triggers_not_a_list", '{"triggers": "oops"}'),
        ("root_scalar", '42'),
        ("root_string", '"nope"'),
        ("entry_not_object", '[42]'),
        ("triggers_entry_not_object", '{"triggers": [{"id": "a"}, 7]}'),
    ]:
        f = tmp_path / f"{name}.json"
        f.write_text(payload)
        with pytest.raises(LockRegistryUnavailable):
            load_locked_cells(f)

    # Counter-pin: a well-formed, non-empty registry still loads.
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"triggers": [
        {"id": "x", "active": True, "type": "shadow_count_decision",
         "entry_type": "foo"}]}))
    assert len(load_locked_cells(ok)) == 1


def test_prefix_locks_cover_their_variant_family():
    """KNOWN-NG INPUT: a variant of a prefix-locked family.

    The registry marks kalman_d7 / price_shock_rev / weekend_gap with
    `match: "prefix"` and tools/prereg_trigger_watch.py honours it.  Exact
    comparison would miss every variant and publish a frozen family's outcome
    statistics (Codex P2, PR #273).
    """
    fam = {"entry_type": "kalman_d7", "match": "prefix", "instrument": None,
           "direction": None, "registry_id": "t9-kalman-d7-live-n10-ev-check",
           "kind": "live", "since": None, "closed_only": False,
           "dedup_violation": None, "mode": None, "n_decide": 10}

    assert _entry_type_matches("kalman_d7_variant_a", fam)
    assert _entry_type_matches("kalman_d7", fam)
    assert not _entry_type_matches("kalman_d8", fam)
    # Counter-pin: an exact lock must NOT swallow the family.
    exact = dict(fam, match="exact")
    assert _entry_type_matches("kalman_d7", exact)
    assert not _entry_type_matches("kalman_d7_variant_a", exact)

    trades = _rows("kalman_d7_variant_a", "USD_JPY", "BUY", 30, wins=27)
    for t in trades:
        t["oanda_trade_id"] = "1"          # live population
    res = run_audit(trades, run_date="2026-09-20",
                    targets=("kalman_d7_variant_a",), locked_cells=[fam])
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"][0] == "kalman_d7_variant_a"][0]
    assert rec["redacted"] is True, "a prefix-locked variant must be redacted"
    assert "wr" not in rec
    assert rec["n_lock_population"] == 30, "prefix must apply to the count too"
    assert res["candidates"] == []


def test_real_registry_preserves_prefix_match_flags():
    """Counter-pin against the live registry: prefix flags must survive."""
    locked = load_locked_cells()
    by_id = {lk["registry_id"]: lk for lk in locked}
    assert by_id["t9-kalman-d7-live-n10-ev-check"]["match"] == "prefix"
    assert by_id["ps-carveout-regate-post-172"]["match"] == "prefix"
    # ...and a non-prefix lock is not silently widened.
    assert by_id["sr-anti-hunt-eurjpy-buy-forward-confirm"]["match"] == "exact"


def test_marker_defined_lock_rows_are_excluded_from_outcomes():
    """KNOWN-NG INPUT: rows carrying an active marker LOCK's reasons literal.

    `hourblock-class-exempt-r2-rollback` has an EMPTY entry_type and defines
    its population via `reasons_marker`; prereg_trigger_watch supports that
    shape.  Dropping such LOCKs meant their pooled outcomes were recomputed
    inside whatever cell the rows landed in (Codex P1, PR #273).
    """
    marker_lock = {
        "entry_type": None, "instrument": None, "direction": None,
        "registry_id": "hourblock-class-exempt-r2-rollback", "match": "exact",
        # `since` deliberately covers the fixture rows (2026-08-1x); the real
        # entry's 2026-09-02 is exercised by the population test above.
        "kind": "live", "since": "2026-08-01", "closed_only": False,
        "dedup_violation": None, "mode": None, "n_decide": 10,
        "reasons_marker": "[HOURBLOCK_CLASS_EXEMPT]", "count_basis": None,
    }
    plain = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 25, wins=5)
    marked = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 15, wins=15)
    for t in marked:
        t["reasons"] = ["[HOURBLOCK_CLASS_EXEMPT] exempt", "x"]
        t["oanda_trade_id"] = "7"

    res = run_audit(plain + marked, run_date="2026-09-20",
                    targets=("vsg_jpy_reversal",), locked_cells=[marker_lock])
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["vsg_jpy_reversal", "EUR_JPY", "SELL"]][0]
    assert rec["n"] == 25, "marker rows must not enter the cell"
    # 5/25 = 0.2 — if the 15 marked WINs leaked in it would be 20/40 = 0.5.
    assert rec["wr"] == pytest.approx(0.2)
    red = res["prereg_lock_redaction"]
    assert red["marker_locked_rows_excluded"] == 15
    assert red["marker_locks"][0]["n_lock_population"] == 15
    # Counter-pin: `since` still bounds a marker LOCK's population.
    late = dict(marker_lock, since="2026-09-02")
    assert lock_population_count(plain + marked, late) == 0


def test_registry_keeps_the_marker_lock():
    """Counter-pin on the live registry: the marker LOCK must load."""
    ids = {lk["registry_id"] for lk in load_locked_cells()}
    assert "hourblock-class-exempt-r2-rollback" in ids


def test_live_lock_counts_exclude_duplicate_rows_unconditionally():
    """KNOWN-NG INPUT: a duplicate live row on a lock that omits dedup_violation.

    count_live_matching excludes dedup_violation == 1 unconditionally, so
    without this the report's n_lock_population exceeds the canonical watcher
    count and can look like n_decide was reached (Codex P2, PR #273).
    """
    lock = {"entry_type": "kalman_d7", "match": "prefix", "instrument": None,
            "direction": None, "registry_id": "t9-kalman-d7-live-n10-ev-check",
            "kind": "live", "since": None, "closed_only": False,
            "dedup_violation": None, "mode": None, "n_decide": 10,
            "reasons_marker": None, "count_basis": None}
    good = _rows("kalman_d7", "USD_JPY", "BUY", 8, wins=4)
    dupes = _rows("kalman_d7", "USD_JPY", "BUY", 5, wins=5)
    for t in good:
        t["oanda_trade_id"] = "1"
    for t in dupes:
        t["oanda_trade_id"] = "1"
        t["dedup_violation"] = 1

    assert lock_population_count(good + dupes, lock) == 8, (
        "duplicate live rows must never count toward the gate")


def test_entry_without_active_key_is_treated_as_active(tmp_path):
    """Canonical loader is .get('active', True) — an omitted flag means ACTIVE.

    Treating it as inactive fails open: the watcher would evaluate the LOCK
    while this audit publishes it unredacted (Codex P2, PR #273).
    """
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"triggers": [
        {"id": "no-active-key", "type": "shadow_count_decision",
         "entry_type": "foo", "instrument": "EUR_JPY", "direction": "BUY"},
        {"id": "explicitly-off", "active": False,
         "type": "shadow_count_decision", "entry_type": "bar"},
    ]}))
    ids = {lk["registry_id"] for lk in load_locked_cells(f)}
    assert "no-active-key" in ids, "omitted active must default to active"
    assert "explicitly-off" not in ids, "active: false must still deactivate"


def test_missing_or_empty_triggers_ledger_fails_closed(tmp_path):
    """KNOWN-NG INPUTS: a misspelled root key and an empty ledger.

    `.get("triggers", [])` folds both into "no locks", which silently disables
    every redaction.  The canonical load_registry_raw rejects both; this loader
    must match (Codex P1, PR #273, 3rd instance of this fail-open class).

    NOTE: an earlier revision of this file pinned "an empty registry is legal".
    That pin was WRONG — it contradicted the canonical contract and asserted
    exactly the fail-open state.  Corrected here.
    """
    for name, payload in [
        ("typo_key", '{"trigers": []}'),
        ("typo_key_nonempty", '{"trigers": [{"id": "a"}]}'),
        ("empty_ledger", '{"triggers": []}'),
        ("no_triggers_key", '{"other": 1}'),
        ("list_root", '[{"id": "a"}]'),
    ]:
        f = tmp_path / f"{name}.json"
        f.write_text(payload)
        with pytest.raises(LockRegistryUnavailable):
            load_locked_cells(f)

    # The misspelling hint must name the near-miss key, or the operator cannot
    # tell a typo from a genuinely absent ledger.
    f = tmp_path / "hint.json"
    f.write_text('{"trigers": []}')
    with pytest.raises(LockRegistryUnavailable, match="trigers"):
        load_locked_cells(f)

    # Counter-pin: the real registry still loads.
    assert load_locked_cells()


def test_marker_exclusion_honours_the_locks_selectors():
    """KNOWN-NG INPUT: marked rows OUTSIDE the marker lock's population.

    The hourblock lock is live-only from 2026-09-02, but the marker is attached
    before later gates can turn a trade into shadow.  Matching on the reasons
    literal alone deleted shadow / pre-`since` rows from the audit although they
    are not locked — over-exclusion is the mirror image of a leak (Codex P2,
    PR #273).
    """
    lock = {"entry_type": None, "instrument": None, "direction": None,
            "registry_id": "hourblock-class-exempt-r2-rollback", "match": "exact",
            "kind": "live", "since": "2026-08-15", "closed_only": False,
            "dedup_violation": None, "mode": None, "n_decide": 10,
            "reasons_marker": "[HOURBLOCK_CLASS_EXEMPT]", "count_basis": None}

    def marked(ts, **kw):
        base = {"entry_type": "vsg_jpy_reversal", "instrument": "EUR_JPY",
                "direction": "SELL", "outcome": "WIN", "pnl_pips": 1.0,
                "dedup_violation": 0, "is_shadow": 0, "status": "CLOSED",
                "oanda_trade_id": "5", "mode": "daytrade",
                "reasons": ["[HOURBLOCK_CLASS_EXEMPT]"], "entry_time": ts}
        base.update(kw)
        return base

    inside = marked("2026-08-20T02:00:00")
    shadow_row = marked("2026-08-20T02:00:00", oanda_trade_id="")   # not live
    too_early = marked("2026-08-01T02:00:00")                        # before since

    assert row_in_lock_population(inside, lock) is True
    assert row_in_lock_population(shadow_row, lock) is False, (
        "a shadow row carrying the marker is not in a live-only LOCK")
    assert row_in_lock_population(too_early, lock) is False, (
        "a pre-`since` row carrying the marker is not locked yet")

    plain = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 20, wins=4)
    res = run_audit(plain + [inside, shadow_row, too_early],
                    run_date="2026-09-20", targets=("vsg_jpy_reversal",),
                    locked_cells=[lock])
    assert res["prereg_lock_redaction"]["marker_locked_rows_excluded"] == 1, (
        "only the row actually inside the LOCK population may be removed")
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["vsg_jpy_reversal", "EUR_JPY", "SELL"]][0]
    assert rec["n"] == 22, "the two unlocked marked rows must stay in the audit"


def test_locked_cell_count_is_independent_of_outcome():
    """KNOWN-NG INPUT: a LOCKed cell containing BREAKEVEN rows.

    Before the routing fix, LOCKed rows passed the WIN/LOSS filter first, so the
    emitted count was itself a function of `outcome` — a BREAKEVEN row changed
    both the count and whether the cell appeared at all.  That is the 35-vs-36
    discrepancy this PR documents, reproduced inside the tool meant to fix it
    (Codex P1, PR #273).
    """
    rows = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=20)
    for t in rows[:6]:
        t["outcome"] = "BREAKEVEN"
        t["pnl_pips"] = 0.0

    res = run_audit(rows, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["n_unique_rows_in_window"] == 40, (
        "all 40 unique rows must count — the WIN/LOSS filter must not touch "
        "a LOCKed cell (34 would mean outcome leaked into the count)")
    assert rec["redacted"] is True
    assert res["meta"]["locked_rows_routed_out"] == 40
    assert res["meta"]["clean_N"] == 0, "no LOCKed row may enter `clean`"

    # Counter-pin: flipping outcomes must not move any emitted number.
    flipped = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 40, wins=40)
    res2 = run_audit(flipped, run_date="2026-09-20",
                     targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    rec2 = [c for c in res2["eligible_cells_v2"]
            if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec2["n_unique_rows_in_window"] == rec["n_unique_rows_in_window"]


def test_unlocked_cells_still_use_the_winloss_filter():
    """Counter-pin: the outcome filter must remain for cells that are not LOCKed."""
    rows = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 40, wins=20)
    for t in rows[:6]:
        t["outcome"] = "BREAKEVEN"
    res = run_audit(rows, run_date="2026-09-20",
                    targets=("vsg_jpy_reversal",), locked_cells=LOCKED)
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["vsg_jpy_reversal", "EUR_JPY", "SELL"]][0]
    assert rec["n"] == 34, "BREAKEVEN rows are excluded from tested cells"
    assert res["meta"]["locked_rows_routed_out"] == 0


def test_selector_less_active_decision_entry_is_rejected(tmp_path):
    """KNOWN-NG INPUT: a misspelled selector key on an active decision.

    Passes the structural checks and would be silently dropped, removing a
    LOCK while the audit keeps publishing its population (Codex P1, PR #273).
    """
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"triggers": [
        {"id": "typo-selector", "active": True,
         "type": "shadow_count_decision", "entry_typo": "foo"}]}))
    with pytest.raises(LockRegistryUnavailable, match="typo-selector"):
        load_locked_cells(f)

    # Counter-pins: an INACTIVE selector-less entry is fine (not a LOCK), and a
    # non-decision entry is out of scope entirely.
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"triggers": [
        {"id": "off", "active": False, "type": "shadow_count_decision"},
        {"id": "info", "active": True, "type": "shadow_count_info"},
        {"id": "real", "active": True, "type": "shadow_count_decision",
         "entry_type": "foo"}]}))
    assert {lk["registry_id"] for lk in load_locked_cells(ok)} == {"real"}


def test_meta_counters_never_read_outcome_of_locked_rows():
    """KNOWN-NG INPUT: flipping a LOCKed row's outcome must move NO output.

    `meta.non_winloss_excluded` used to be computed over all target rows, so a
    single WIN -> BREAKEVEN flip inside the frozen population changed the
    emitted metadata from 0 to 1 — an outcome-derived property of a LOCKed
    population, published despite the count-only record being unchanged
    (Codex P1, PR #273).
    """
    base = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 30, wins=15)
    flipped = [dict(t) for t in base]
    for t in flipped[:7]:
        t["outcome"] = "BREAKEVEN"
        t["pnl_pips"] = 0.0

    a = run_audit(base, run_date="2026-09-20",
                  targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    b = run_audit(flipped, run_date="2026-09-20",
                  targets=("sr_anti_hunt_bounce",), locked_cells=LOCKED)
    assert a["meta"] == b["meta"], (
        "no meta counter may depend on a LOCKed row's outcome")
    assert a["meta"]["non_winloss_excluded"] == 0
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), (
        "the ENTIRE report must be invariant to LOCKed rows' outcomes")


def test_non_winloss_counter_still_works_for_unlocked_rows():
    """Counter-pin: the metric must not be vacuously zero."""
    rows = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 30, wins=15)
    for t in rows[:7]:
        t["outcome"] = "BREAKEVEN"
    res = run_audit(rows, run_date="2026-09-20",
                    targets=("vsg_jpy_reversal",), locked_cells=LOCKED)
    assert res["meta"]["non_winloss_excluded"] == 7


def test_bonferroni_uses_one_family_across_v2_and_v3():
    """KNOWN-NG INPUT: the reviewer's worked example.

    A lone v3 sub-cell (N=20, 15 wins) has Wilson_lo 0.531 and p_raw ~0.025, so
    under the old per-grid correction (m_v3 = 1 => p_bonf = p_raw) it was
    PROMOTED — while the combined v2 u v3 family rejects it.  That is how the
    Tokyo sub-cell appeared as a "candidate" for 4 consecutive weeks; the
    2026-09-20 report named v2 u v3 (m=8) as the family in prose while the
    harness kept the split (Codex P1, PR #273).
    """
    # One tightly-scoped v3 cell (all rows in the Tokyo bucket) ...
    v3_cell = _rows("vsg_jpy_reversal", "EUR_JPY", "SELL", 20, wins=15)
    # ... plus other eligible v2 cells that enlarge the family.
    others = []
    for pair in ("GBP_JPY", "USD_JPY", "AUD_JPY", "NZD_JPY"):
        others += _rows("vsg_jpy_reversal", pair, "BUY", 20, wins=10)

    res = run_audit(v3_cell + others, run_date="2026-09-20",
                    targets=("vsg_jpy_reversal",), locked_cells=[])
    m_v2 = res["meta"]["m_global_v2"]
    m_v3 = res["meta"]["m_global_v3"]
    assert res["meta"]["m_family_v2_union_v3"] == m_v2 + m_v3

    tested = [c for c in res["eligible_cells_v2"] + res["eligible_cells_v3"]
              if not c.get("redacted")]
    assert tested, "fixture must produce tested cells"
    m_family = res["meta"]["m_family_v2_union_v3"]
    for c in tested:
        expected = min(1.0, c["p_raw"] * m_family)
        # p_raw is emitted rounded to 4dp, so the reconstructed product carries
        # up to 5e-5 * m of rounding error (plus p_bonf's own 5e-5).
        tol = 5e-5 * (m_family + 1)
        assert c["p_bonf"] == pytest.approx(expected, abs=tol), (
            "every tested cell must be corrected over the combined family")

    # The discriminating cell: 15/20 (p_raw ~0.025) must NOT be promoted, and
    # must carry a real penalty rather than p_bonf == p_raw.  (Cells at 10/20
    # already sit at p_raw = 1.0, where the clamp makes the comparison vacuous.)
    target = [c for c in res["eligible_cells_v3"]
              if c["cell"][:2] == ["vsg_jpy_reversal", "EUR_JPY"]
              and not c.get("redacted")]
    assert target, "expected the 15/20 v3 sub-cell"
    for c in target:
        assert c["p_raw"] < 1.0
        assert c["p_bonf"] > c["p_raw"], (
            "a v3 cell must carry a real multiplicity penalty, not p_bonf=p_raw")
        assert c["promoted"] is False, (
            "the combined family must reject what the per-grid split promoted")
    assert res["candidates"] == []


def test_accrual_windows_span_exactly_their_advertised_length():
    """KNOWN-NG INPUT: rows exactly on the old, too-wide boundary.

    `days=d` counted d+1 inclusive days (2026-06-22..2026-09-20 = 91 for
    d=90), inflating the accrual rates used to diagnose signal starvation
    (Codex P2, PR #273).
    """
    def row(ts):
        return {"entry_type": "vdr_jpy", "instrument": "USD_JPY",
                "direction": "BUY", "outcome": "WIN", "pnl_pips": 1.0,
                "dedup_violation": 0, "is_shadow": 1, "entry_time": ts}

    trades = [
        row("2026-09-20T10:00:00"),   # run date -> inside every window
        row("2026-08-22T10:00:00"),   # 30d window: day 30 inclusive -> inside
        row("2026-08-21T10:00:00"),   # day 31 -> outside 30d
        row("2026-06-23T10:00:00"),   # 90d window: day 90 inclusive -> inside
        row("2026-06-22T10:00:00"),   # day 91 -> outside 90d (the old bug)
    ]
    out = unique_accrual(trades, ("vdr_jpy",), "2026-09-20")["vdr_jpy"]
    assert out["unique_30d"] == 2, "30d must span exactly 30 inclusive days"
    assert out["unique_90d"] == 4, "90d must span exactly 90 inclusive days"
    assert out["unique_365d"] == 5
    assert out["last_unique_fire"].startswith("2026-09-20")


def test_shadow_lock_watcher_divergence_is_surfaced_not_silently_resolved():
    """KNOWN-NG INPUT: a shadow LOCK cell that also took live fills.

    The pre-reg says the population is "dedup_violation=0 の shadow rows のみ",
    but the canonical count_matching never filters `oanda_trade_id`, so the two
    diverge once a shadow LOCK's cell takes live fills.  Picking a side would
    change a LOCK trigger's counting rule, so the report emits BOTH counts and
    a divergence flag instead (Codex P2, PR #273).
    """
    lock = {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
            "direction": "BUY", "registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
            "match": "exact", "kind": "shadow", "since": "2026-08-05",
            "closed_only": True, "dedup_violation": 0, "mode": None,
            "n_decide": 40, "reasons_marker": None, "count_basis": None}

    shadow = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 22, wins=11)
    for t in shadow:
        t["status"] = "CLOSED"
        t["oanda_trade_id"] = ""
    live = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 5, wins=3)
    for t in live:
        t["status"] = "CLOSED"
        t["oanda_trade_id"] = "900123"

    assert lock_population_count(shadow + live, lock) == 22, (
        "pre-reg faithful: shadow rows only")
    assert lock_population_count(shadow + live, lock, watcher_compat=True) == 27, (
        "watcher compatible: count_matching does not filter oanda_trade_id")

    res = run_audit(shadow + live, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["n_lock_population"] == 22
    assert rec["n_lock_population_watcher"] == 27
    assert rec["watcher_divergence"] is True
    divergent = res["prereg_lock_redaction"]["watcher_divergent_locks"]
    # Both the v2 cell and its v3 refinement are flagged — they share the LOCK,
    # so they report the same (LOCK-level) population counts.
    assert len(divergent) == 2
    assert {d["registry_id"] for d in divergent} == {
        "sr-anti-hunt-eurjpy-buy-forward-confirm"}
    assert all(d["n_prereg_faithful"] == 22 for d in divergent)
    assert all(d["n_watcher"] == 27 for d in divergent)

    # Counter-pin: with no live fills the two agree and nothing is flagged.
    res2 = run_audit(shadow, run_date="2026-09-20",
                     targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    rec2 = [c for c in res2["eligible_cells_v2"]
            if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec2["watcher_divergence"] is False
    assert res2["prereg_lock_redaction"]["watcher_divergent_locks"] == []


def test_live_locks_agree_with_the_watcher_by_construction():
    """Counter-pin: for live LOCKs both paths filter oanda_trade_id, so no
    divergence can arise there."""
    lock = {"entry_type": "kalman_d7", "match": "prefix", "instrument": None,
            "direction": None, "registry_id": "t9-kalman-d7-live-n10-ev-check",
            "kind": "live", "since": None, "closed_only": False,
            "dedup_violation": None, "mode": None, "n_decide": 10,
            "reasons_marker": None, "count_basis": None}
    rows = _rows("kalman_d7", "USD_JPY", "BUY", 12, wins=6)
    for i, t in enumerate(rows):
        t["oanda_trade_id"] = "1" if i < 8 else ""
    assert (lock_population_count(rows, lock)
            == lock_population_count(rows, lock, watcher_compat=True) == 8)


def test_strict_shadow_requires_is_shadow_not_just_a_blank_oanda_id():
    """KNOWN-NG INPUT: a flag-drift row (blank OANDA id but is_shadow=0).

    The rnb-support-bounce-shadow-forward LOCK spells the population out as
    "厳格 shadow = is_shadow=1 ∧ oanda_trade_id 空".  Checking only the OANDA id
    counted drift rows as shadow and inflated n_lock_population toward the
    first-look threshold.  PROD held 47 such rows when this was found, so the
    hazard is real rather than hypothetical (Codex P2, PR #273).
    """
    lock = {"entry_type": "rnb_support_bounce", "instrument": "USD_JPY",
            "direction": "BUY", "registry_id": "rnb-support-bounce-shadow-forward",
            "match": "exact", "kind": "shadow", "since": "2026-09-10",
            "closed_only": True, "dedup_violation": 0, "mode": None,
            "n_decide": 41, "reasons_marker": None, "count_basis": None}

    def r(**kw):
        base = {"entry_type": "rnb_support_bounce", "instrument": "USD_JPY",
                "direction": "BUY", "status": "CLOSED", "oanda_trade_id": "",
                "dedup_violation": 0, "is_shadow": 1,
                "entry_time": "2026-09-15T02:00:00"}
        base.update(kw)
        return base

    strict = [r() for _ in range(9)]
    drift = [r(is_shadow=0) for _ in range(4)]        # blank id, is_shadow=0
    live = [r(oanda_trade_id="7", is_shadow=0) for _ in range(3)]

    assert lock_population_count(strict + drift + live, lock) == 9, (
        "only is_shadow=1 AND blank OANDA id counts as strict shadow")
    # watcher_compat keeps the canonical (broader) behaviour on purpose.
    assert lock_population_count(strict + drift + live, lock,
                                 watcher_compat=True) == 16
    assert row_in_lock_population(drift[0], lock) is False
    assert row_in_lock_population(drift[0], lock, watcher_compat=True) is True
    assert row_in_lock_population(strict[0], lock) is True


def test_lock_population_is_bounded_by_the_audit_as_of_date():
    """KNOWN-NG INPUT: rows dated after the audit's run_date.

    lock_population_count ran over the whole payload, so re-running an older
    --run-date against a current snapshot counted post-run rows and could imply
    n_decide had already been reached in a historical report (Codex P2,
    PR #273).  `since` stays the LOCK's own lower bound.
    """
    lock = {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
            "direction": "BUY", "registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
            "match": "exact", "kind": "shadow", "since": "2026-08-05",
            "closed_only": True, "dedup_violation": 0, "mode": None,
            "n_decide": 40, "reasons_marker": None, "count_basis": None}

    def r(ts):
        return {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
                "direction": "BUY", "status": "CLOSED", "oanda_trade_id": "",
                "dedup_violation": 0, "is_shadow": 1, "outcome": "WIN",
                "pnl_pips": 1.0, "entry_time": ts}

    rows = ([r(f"2026-08-{d:02d}T02:00:00") for d in range(10, 20)]   # 10 in
            + [r("2026-09-20T23:00:00")]                              # run date: in
            + [r("2026-09-21T02:00:00"), r("2026-10-05T02:00:00")])   # after: out

    assert lock_population_count(rows, lock) == 13, "unbounded counts everything"
    assert lock_population_count(rows, lock, as_of_exclusive="2026-09-21") == 11
    # ...and the audit wires its own upper bound in automatically.
    res = run_audit(rows, run_date="2026-09-20", min_n=5,
                    targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["n_lock_population"] == 11, (
        "post-run rows must not enter a historical report's LOCK count")
    assert rec["n_unique_rows_in_window"] == 11, (
        "the in-window row count is bounded by the audit window too")
    # Counter-pin: `since` still bounds the low side independently.
    early = dict(lock, since="2026-08-15")
    assert lock_population_count(rows, early, as_of_exclusive="2026-09-21") == 6


def test_count_only_monitors_are_not_redacted(tmp_path):
    """KNOWN-NG INPUT: a count-only monitor sharing the decision type.

    Lane-health checkpoints and the weekend_gap live-conversion monitor are
    *_count_decision but freeze no outcome look and say so.  Redacting them
    silently discarded valid results and promotion candidates — the mirror
    image of a leak (Codex P2, PR #273).
    """
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"triggers": [
        {"id": "real-lock", "active": True, "type": "shadow_count_decision",
         "entry_type": "foo"},
        {"id": "count-monitor", "active": True, "type": "live_count_decision",
         "entry_type": "bar", "outcome_lock": False},
        {"id": "default-is-redact", "active": True,
         "type": "shadow_count_decision", "entry_type": "baz"},
    ]}))
    ids = {lk["registry_id"] for lk in load_locked_cells(f)}
    assert "real-lock" in ids
    assert "default-is-redact" in ids, (
        "omitting outcome_lock must default to REDACT (under-redaction is the "
        "silent failure; over-redaction is at least visible)")
    assert "count-monitor" not in ids


def test_real_registry_classification_of_outcome_locks():
    """Counter-pin on the live registry: the three count-only monitors are out,
    every genuine outcome LOCK stays in."""
    ids = {lk["registry_id"] for lk in load_locked_cells()}
    for count_only in ("rnb-shadow-lane-health-checkpoint-1",
                       "rnb-shadow-lane-health-checkpoint-2",
                       "project-falsification-f2-wg-live-conversion"):
        assert count_only not in ids, count_only
    for outcome_lock in ("sr-anti-hunt-eurjpy-buy-forward-confirm",
                         "ws3-t11-anti-hunt-usdjpy-recheck",
                         "rnb-support-bounce-shadow-forward",
                         "t9-kalman-d7-live-n10-ev-check",
                         "hourblock-class-exempt-r2-rollback",
                         "ps-carveout-regate-post-172",
                         "ws3-stage2-underpowered-recheck"):
        assert outcome_lock in ids, outcome_lock


def test_locked_cells_are_reported_below_the_audit_minimum_n():
    """KNOWN-NG INPUT: a LOCK whose own threshold is under MIN_N.

    The kalman LOCK declares n_decide=10, but the inventory only listed groups
    with >= min_n (20), so ten matching rows produced redacted_cell_count=0 and
    no n_lock_population — the declared look was reached and nothing said so
    (Codex P2, PR #273).
    """
    lock = {"entry_type": "kalman_d7", "match": "prefix", "instrument": None,
            "direction": None, "registry_id": "t9-kalman-d7-live-n10-ev-check",
            "kind": "live", "since": None, "closed_only": False,
            "dedup_violation": None, "mode": None, "n_decide": 10,
            "reasons_marker": None, "count_basis": None}
    rows = _rows("kalman_d7", "USD_JPY", "BUY", 10, wins=7)
    for t in rows:
        t["oanda_trade_id"] = "1"

    res = run_audit(rows, run_date="2026-09-20",
                    targets=("kalman_d7",), locked_cells=[lock])
    red = res["prereg_lock_redaction"]
    assert red["redacted_cell_count"] >= 1, (
        "a LOCK at its own declared threshold must appear in the inventory")
    rec = [c for c in res["eligible_cells_v2"]
           if c["cell"] == ["kalman_d7", "USD_JPY", "BUY"]][0]
    assert rec["redacted"] is True
    assert rec["n_lock_population"] == 10
    assert rec["n_decide"] == 10
    assert "wr" not in rec
    # Counter-pin: multiplicity still uses min_n, so a 10-row group must not
    # inflate the Bonferroni family.
    assert res["meta"]["m_global_v2"] == 0
    assert res["meta"]["m_family_v2_union_v3"] == 0


_MISSING = object()


def test_outcome_lock_must_be_a_real_boolean_in_the_registry():
    """KNOWN-NG INPUTS: "false" / 0 / null for outcome_lock.

    load_locked_cells opts out only when the value `is False`, so a truthy or
    non-bool value silently turns a count-only monitor back into an outcome
    lock and suppresses its valid results.  The registry linter must reject
    such values at authoring time (Codex P2, PR #273).
    """
    from tools.prereg_trigger_watch import BOOL_FIELDS, lint_registry

    assert "outcome_lock" in BOOL_FIELDS

    def entry(value):
        e = {"id": "monitor", "active": True, "type": "shadow_count_decision",
             "entry_type": "foo", "deadline": "2027-01-01",
             "since": "2026-09-01", "n_decide": 10, "n_floor": 1}
        if value is not _MISSING:
            e["outcome_lock"] = value
        return e

    for bad in ("false", "true", 0, 1, None, "no"):
        errs = lint_registry([entry(bad)])
        assert any("outcome_lock" in e for e in errs), (
            f"lint must reject outcome_lock={bad!r}")

    # Counter-pin: real booleans pass, and omitting the key is legal
    # (omission means "outcome lock", the safe default).
    for good in (True, False):
        errs = lint_registry([entry(good)])
        assert not any("outcome_lock" in e for e in errs), (
            f"lint must accept outcome_lock={good!r}: {errs}")
    assert not any("outcome_lock" in e
                   for e in lint_registry([entry(_MISSING)]))



def test_locks_that_start_after_the_window_do_not_redact():
    """KNOWN-NG INPUT: a historical rerun predating the LOCK's `since`.

    Re-running --run-date 2026-07-01 redacted sr_anti_hunt_bounce x EUR_JPY x
    BUY under a LOCK that only starts 2026-08-05, reporting n_lock_population:
    0 and deleting valid historical statistics and candidates — over-redaction,
    the mirror image of a leak (Codex P2, PR #273).
    """
    lock = {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
            "direction": "BUY", "registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
            "match": "exact", "kind": "shadow", "since": "2026-08-05",
            "closed_only": True, "dedup_violation": 0, "mode": None,
            "n_decide": 40, "reasons_marker": None, "count_basis": None}
    rows = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 30, wins=24)
    for t in rows:  # all in June, before the LOCK begins
        t["entry_time"] = t["entry_time"].replace("2026-08-", "2026-06-")
        t["status"] = "CLOSED"
        t["oanda_trade_id"] = ""

    early = run_audit(rows, run_date="2026-07-01",
                      targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    red = early["prereg_lock_redaction"]
    assert red["redacted_cell_count"] == 0, (
        "a LOCK that has not begun cannot cover this window")
    assert red["locks_not_yet_started"] == [
        {"registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
         "since": "2026-08-05"}], "the omission must be visible, not silent"
    rec = [c for c in early["eligible_cells_v2"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["redacted"] is False
    assert rec["wr"] == pytest.approx(0.8), "historical statistics survive"

    # Counter-pin: once the window reaches the LOCK, redaction resumes.
    later = _rows("sr_anti_hunt_bounce", "EUR_JPY", "BUY", 30, wins=24)
    for t in later:
        t["status"] = "CLOSED"
        t["oanda_trade_id"] = ""
        t["is_shadow"] = 1
        t["dedup_violation"] = 0
    after = run_audit(rows + later, run_date="2026-09-20",
                      targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    assert after["prereg_lock_redaction"]["locks_not_yet_started"] == []
    assert after["prereg_lock_redaction"]["redacted_cell_count"] >= 1
    rec2 = [c for c in after["eligible_cells_v2"]
            if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]
            and c.get("redacted")]
    assert rec2, "the in-population rows must be redacted once the LOCK begins"
    assert "wr" not in rec2[0]
    # ...while the June complement is still evaluated, flagged as partial.
    comp2 = [c for c in after["eligible_cells_v2"]
             if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]
             and not c.get("redacted")]
    assert comp2 and comp2[0]["lock_complement_only"] is True


def test_only_lock_population_rows_are_routed_out():
    """KNOWN-NG INPUT: same-cell rows that fail the LOCK's own predicates.

    Routing on cell identity alone swallowed live rows and pre-`since` rows of
    a shadow-only LOCK's cell — the committed report showed 75 in-window unique
    rows routed for a population of 36, silently discarding statistics the LOCK
    never covered (Codex P2, PR #273).
    """
    lock = {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
            "direction": "BUY", "registry_id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
            "match": "exact", "kind": "shadow", "since": "2026-08-05",
            "closed_only": True, "dedup_violation": 0, "mode": None,
            "n_decide": 40, "reasons_marker": None, "count_basis": None}

    def r(ts, **kw):
        base = {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
                "direction": "BUY", "outcome": "WIN", "pnl_pips": 2.0,
                "dedup_violation": 0, "is_shadow": 1, "status": "CLOSED",
                "oanda_trade_id": "", "mode": "daytrade", "entry_time": ts}
        base.update(kw)
        return base

    in_pop = [r(f"2026-08-{10 + i:02d}T02:00:00") for i in range(21)]
    pre_since = [r("2026-07-20T02:00:00", outcome="LOSS", pnl_pips=-1.0)
                 for _ in range(13)]                       # before `since`
    live = [r("2026-08-20T02:00:00", oanda_trade_id="9", is_shadow=0,
              outcome="LOSS", pnl_pips=-1.0) for _ in range(9)]   # not shadow

    res = run_audit(in_pop + pre_since + live, run_date="2026-09-20",
                    targets=("sr_anti_hunt_bounce",), locked_cells=[lock])
    red = res["prereg_lock_redaction"]
    assert res["meta"]["locked_rows_routed_out"] == 21, (
        "only the LOCK population may be routed out")

    rec = [c for c in red["redacted_cells"]
           if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]][0]
    assert rec["n_unique_rows_in_window"] == rec["n_lock_population"] == 21, (
        "the routed count must equal the LOCK population, not the whole cell")

    # The unlocked complement stays evaluable, and is flagged as partial.
    comp = [c for c in res["eligible_cells_v2"]
            if c["cell"] == ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]
            and not c.get("redacted")][0]
    assert comp["n"] == 22, "13 pre-since + 9 live rows survive"
    assert comp["lock_complement_only"] is True
    assert red["lock_complement_cells"] == [
        ["sr_anti_hunt_bounce", "EUR_JPY", "BUY"]]
    # ...and it must not carry the LOCKed rows' outcomes (all 22 are LOSS).
    assert comp["wr"] == pytest.approx(0.0)


def test_truncated_api_snapshot_is_refused(tmp_path, monkeypatch, capsys):
    """KNOWN-NG INPUT: the endpoint's DEFAULT 50-row page.

    /api/demo/trades defaults to limit=50, so following the help text with a
    plain curl produced a plausible but severely truncated audit that (without
    --no-write) overwrote the weekly summary (Codex P2, PR #273).
    """
    import tools.cell_deepdive_audit as m

    def run(payload, extra=()):
        f = tmp_path / "t.json"
        f.write_text(json.dumps(payload))
        argv = [str(f), "--run-date", "2026-09-20", "--no-write", *extra]
        with pytest.raises(SystemExit) as ei:
            m.main(argv)
        return str(ei.value)

    row = {"entry_type": "vsg_jpy_reversal", "instrument": "EUR_JPY",
           "direction": "SELL", "outcome": "WIN", "pnl_pips": 1.0,
           "dedup_violation": 0, "is_shadow": 1,
           "entry_time": "2026-08-10T02:00:00"}

    msg = run({"count": 50, "trades": [row] * 50})
    assert "DEFAULT limit" in msg and "limit=100000" in msg

    msg = run({"count": 120, "trades": [row] * 120})
    assert "--min-rows" in msg, "a small-but-not-50 page must still be refused"

    msg = run({"count": 999, "trades": [row] * 120})
    assert "count" in msg and "len(trades)" in msg, "inconsistent snapshot"

    # Counter-pin: a full-size snapshot runs, and --min-rows 0 is an explicit
    # deliberate override for the 50-row case.
    f = tmp_path / "ok.json"
    f.write_text(json.dumps({"count": 1500, "trades": [row] * 1500}))
    assert m.main([str(f), "--run-date", "2026-09-20", "--no-write"]) == 0


def test_malformed_match_selector_fails_closed(tmp_path):
    """KNOWN-NG INPUT: a misspelled `match` value or key.

    "prefx" was silently coerced to exact matching, which would make the
    kalman_d7 prefix LOCK stop covering its variants and publish their frozen
    statistics.  This command never runs lint_registry, so it must validate
    here (Codex P1, PR #273).
    """
    def reg(match_kv):
        f = tmp_path / f"r{abs(hash(str(match_kv)))}.json"
        entry = {"id": "fam", "active": True, "type": "live_count_decision",
                 "entry_type": "kalman_d7"}
        entry.update(match_kv)
        f.write_text(json.dumps({"triggers": [entry]}))
        return f

    for bad in ({"match": "prefx"}, {"match": "PREFIX"}, {"match": True},
                {"match": ""}, {"match": None}, {"match": "exact "}):
        with pytest.raises(LockRegistryUnavailable, match="match="):
            load_locked_cells(reg(bad))

    # Counter-pins: "prefix" works, and an ABSENT key is legal (means exact).
    assert load_locked_cells(reg({"match": "prefix"}))[0]["match"] == "prefix"
    assert load_locked_cells(reg({}))[0]["match"] == "exact"
    # ...and the real registry still loads with its prefix flags intact.
    by_id = {lk["registry_id"]: lk for lk in load_locked_cells()}
    assert by_id["t9-kalman-d7-live-n10-ev-check"]["match"] == "prefix"


def test_a_full_page_is_not_proof_of_completeness(tmp_path):
    """KNOWN-NG INPUT: exactly ?limit= rows.

    /api/demo/trades sets `count` to the PAGE length, so ?limit=1000 returns
    1000 rows with count=1000 and cleared both the count-consistency check and
    --min-rows.  Completeness is proven only by a SHORT page (Codex P2,
    PR #273).
    """
    import tools.cell_deepdive_audit as m

    row = {"entry_type": "vsg_jpy_reversal", "instrument": "EUR_JPY",
           "direction": "SELL", "outcome": "WIN", "pnl_pips": 1.0,
           "dedup_violation": 0, "is_shadow": 1,
           "entry_time": "2026-08-10T02:00:00"}

    def run(n, limit):
        f = tmp_path / f"p{n}_{limit}.json"
        f.write_text(json.dumps({"count": n, "trades": [row] * n}))
        return m.main([str(f), "--run-date", "2026-09-20", "--no-write",
                       "--fetch-limit", str(limit)])

    with pytest.raises(SystemExit, match="FULL page"):
        run(1000, 1000)
    with pytest.raises(SystemExit, match="FULL page"):
        run(1500, 1500)
    # Counter-pin: a SHORT page proves the end was reached and runs.
    assert run(1500, 100000) == 0


def test_committed_report_prose_matches_its_machine_readable_summary():
    """The 2026-09-20 correction must not drift from _summary.json.

    The prose claimed clean_N=273 / 215 routed while the regenerated JSON said
    335 / 58 — the audit narrative described a different sample construction
    than the machine-readable result (Codex P2, PR #273).  This is the same
    "文章では正しく、コードでは違う" failure, in the KB writing this time.
    """
    root = Path(__file__).resolve().parent.parent
    d = root / "knowledge-base" / "raw" / "cell_deepdive" / "2026-09-20"
    data = json.loads((d / "_summary.json").read_text())
    md = (d / "_summary.md").read_text()
    for key in ("clean_N", "locked_rows_routed_out"):
        value = data["meta"][key]
        assert f"**{value}**" in md, (
            f"{key}={value} from _summary.json is not stated in the prose — "
            f"the narrative has drifted from the machine-readable result")
