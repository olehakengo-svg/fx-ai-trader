"""Seed/backfill replay-artifact exclusion tests.

`SEED_HOLD_SEC_THRESHOLD = 5` filters out trades where exit_time-entry_time<5s.
These tests opt out of the conftest auto-bypass via `monkeypatch.undo()` and
manually craft trades with custom timestamps to exercise the actual SQL filter.
"""
import os
import tempfile
import sqlite3
import pytest

from modules.demo_db import DemoDB, SEED_HOLD_SEC_THRESHOLD


@pytest.fixture
def db_with_seed_filter(monkeypatch):
    """Test DB with the production seed-exclusion filter active.

    Undoes the global conftest patch that bypasses _SEED_EXCLUSION_SQL.
    """
    monkeypatch.undo()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d, path
    os.unlink(path)


def _insert_trade(path: str, *, entry_time: str, exit_time: str,
                  entry_type: str = "fib_reversal",
                  is_shadow: int = 1,
                  pnl_pips: float = 5.0,
                  outcome: str = "WIN",
                  instrument: str = "USD_JPY",
                  direction: str = "BUY"):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO demo_trades (status, direction, entry_price, entry_time, "
            "exit_price, exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type, "
            "confidence, is_shadow, instrument) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("CLOSED", direction, 150.0, entry_time, 150.5, exit_time,
             149.5, 150.5, pnl_pips, 0.0, outcome, entry_type, 60, is_shadow, instrument),
        )


def test_threshold_constant_is_five():
    assert SEED_HOLD_SEC_THRESHOLD == 5


def test_get_all_closed_excludes_instant_exit_by_default(db_with_seed_filter):
    db, path = db_with_seed_filter
    # 1秒未満 hold (replay artifact)
    _insert_trade(path,
                  entry_time="2026-04-08T02:40:06.961883+00:00",
                  exit_time="2026-04-08T02:40:07.037761+00:00")
    # 60秒 hold (real trade)
    _insert_trade(path,
                  entry_time="2026-04-27T00:01:33.673896+00:00",
                  exit_time="2026-04-27T00:02:34.000000+00:00")

    rows = db.get_all_closed(exclude_shadow=False)  # include shadow
    assert len(rows) == 1, f"Seed trade leaked into get_all_closed: {rows}"
    assert rows[0]["entry_time"].startswith("2026-04-27")


def test_get_all_closed_includes_instant_exit_when_opted_in(db_with_seed_filter):
    db, path = db_with_seed_filter
    _insert_trade(path,
                  entry_time="2026-04-08T02:40:06.961883+00:00",
                  exit_time="2026-04-08T02:40:07.037761+00:00")

    rows = db.get_all_closed(exclude_shadow=False, exclude_seed=False)
    assert len(rows) == 1


def test_get_stats_excludes_seed_inflation(db_with_seed_filter):
    db, path = db_with_seed_filter
    # 4 instant-exit replay wins (mimics fib_reversal Apr 8 cluster)
    for i in range(4):
        _insert_trade(path,
                      entry_time=f"2026-04-08T02:40:{i:02d}.000000+00:00",
                      exit_time=f"2026-04-08T02:40:{i:02d}.500000+00:00",
                      pnl_pips=15.0, outcome="WIN", is_shadow=0)
    # 1 real loss (60s hold)
    _insert_trade(path,
                  entry_time="2026-04-27T00:00:00.000000+00:00",
                  exit_time="2026-04-27T00:01:00.000000+00:00",
                  pnl_pips=-10.0, outcome="LOSS", is_shadow=0)

    # default: seed excluded → only the real loss counted
    stats = db.get_stats()
    assert stats["total"] == 1
    assert stats["wins"] == 0
    assert stats["win_rate"] == 0.0

    # opt-in: seed included → looks like 4W/1L = 80% (the inflation pathology)
    stats_raw = db.get_stats(exclude_seed=False)
    assert stats_raw["total"] == 5
    assert stats_raw["win_rate"] == 80.0


def test_get_shadow_trades_for_evaluation_excludes_seed(db_with_seed_filter):
    db, path = db_with_seed_filter
    # seed shadow win + real shadow loss
    _insert_trade(path,
                  entry_time="2026-04-08T02:40:00.000000+00:00",
                  exit_time="2026-04-08T02:40:01.000000+00:00",
                  pnl_pips=10.0, outcome="WIN", is_shadow=1)
    _insert_trade(path,
                  entry_time="2026-04-27T00:00:00.000000+00:00",
                  exit_time="2026-04-27T00:01:00.000000+00:00",
                  pnl_pips=-5.0, outcome="LOSS", is_shadow=1)

    res = db.get_shadow_trades_for_evaluation()
    assert res["sample"] == 1
    assert res["overall_wr"] == 0.0  # only the real loss

    res_raw = db.get_shadow_trades_for_evaluation(exclude_seed=False)
    assert res_raw["sample"] == 2
    assert res_raw["overall_wr"] == 50.0


def test_exactly_5_second_hold_passes(db_with_seed_filter):
    """Boundary: hold == 5 seconds is treated as real (>=5)."""
    db, path = db_with_seed_filter
    _insert_trade(path,
                  entry_time="2026-04-27T00:00:00.000000+00:00",
                  exit_time="2026-04-27T00:00:05.000000+00:00")
    rows = db.get_all_closed(exclude_shadow=False)
    assert len(rows) == 1


def test_4_second_hold_blocked(db_with_seed_filter):
    """Boundary: hold == 4 seconds is treated as seed."""
    db, path = db_with_seed_filter
    _insert_trade(path,
                  entry_time="2026-04-27T00:00:00.000000+00:00",
                  exit_time="2026-04-27T00:00:04.000000+00:00")
    rows = db.get_all_closed(exclude_shadow=False)
    assert len(rows) == 0
