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
    assert rec["n_rows_in_window"] == 40, "the row count must survive"
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
    assert rec["redacted"] is True and rec["n_rows_in_window"] == 40


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
    # The in-window row count is larger and must be labelled separately, never
    # presented as the gate count.
    assert rec["n_rows_in_window"] > rec["n_lock_population"]
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

    # Counter-pin: valid shapes still load, and an empty registry is legal.
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"triggers": [
        {"id": "x", "active": True, "type": "shadow_count_decision",
         "entry_type": "foo"}]}))
    assert len(load_locked_cells(ok)) == 1
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"triggers": []}))
    assert load_locked_cells(empty) == []


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
