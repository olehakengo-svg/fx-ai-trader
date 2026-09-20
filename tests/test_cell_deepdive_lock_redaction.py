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
    assert rec["n"] == 40, "N must survive — the trigger counts it"
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
    assert rec["redacted"] is True and rec["n"] == 40


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
    assert res["filters"]["entry_time_ge"] == "2025-09-20"
    assert res["filters"]["entry_time_lt"] == "2026-09-21"


def test_window_includes_run_date_itself():
    """A run executed mid-day must not drop that day's rows."""
    lo, hi = window_bounds("2026-09-20", 365)
    assert lo == "2025-09-20"
    assert hi == "2026-09-21"
    assert lo <= "2026-09-20" < hi


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
