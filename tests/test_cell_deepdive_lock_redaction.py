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

from tools.cell_deepdive_audit import (
    DEDUP_GATE_FIX_TS,
    REDACTED_FIELDS,
    dedup_era_breakdown,
    load_locked_cells,
    lock_for_cell,
    run_audit,
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
