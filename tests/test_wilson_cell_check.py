"""Tests for tools/wilson_cell_check.py.

Covers the Wilson lower-bound math, dedup_violation exclusion, day-level
collapsing of pseudo-replicated signals, LIVE vs SHADOW separation, and the
optional session/mode filters. Pure stdlib fixture (no parquet/pyarrow).
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from tools.wilson_cell_check import (
    audit_cell,
    calendar_day,
    derive_session,
    wilson_lower,
)

# Minimal subset of the demo_trades schema the tool reads.
_SCHEMA = """
CREATE TABLE demo_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT,
    instrument TEXT,
    direction TEXT,
    mode TEXT,
    entry_time TEXT,
    outcome TEXT,
    is_shadow INTEGER,
    dedup_violation INTEGER,
    entry_price REAL,
    sl REAL,
    tp REAL,
    pnl_pips REAL
)
"""

# (entry_time, outcome, is_shadow, dedup_violation, mode)
_ROWS = [
    # --- LIVE (is_shadow=0): 2 days, raw 3 decisive (W1/L2) -> dedup keeps
    #     earliest-of-day so day A = LOSS (drops the later WIN). ---
    ("2026-04-06T14:39:11", "LOSS", 0, 0, "daytrade_gbpusd"),  # day A, first
    ("2026-04-06T14:41:30", "WIN", 0, 0, "daytrade_gbpusd"),   # day A, later
    ("2026-06-09T07:58:35", "LOSS", 0, 0, "daytrade_gbpusd"),  # day B
    # --- SHADOW (is_shadow=1) ---
    # dedup_violation=1 rows that MUST be excluded entirely:
    ("2026-05-12T14:17:41", "WIN", 1, 1, "daytrade_gbpusd"),
    ("2026-05-13T14:21:52", "LOSS", 1, 1, "daytrade_gbpusd"),
    # surviving (dv=0) shadow rows -> 3 calendar days:
    ("2026-05-12T14:17:24", "WIN", 1, 0, "daytrade_gbpusd"),       # day X
    ("2026-05-14T14:26:55", "WIN", 1, 0, "daytrade_gbpusd"),       # day Y, first WIN
    ("2026-05-14T14:44:17", "WIN", 1, 0, "daytrade_gbpusd"),       # day Y, dup WIN
    ("2026-05-13T14:16:22", "BREAKEVEN", 1, 0, "daytrade_gbpusd"),  # day Z, first BE
    ("2026-05-13T16:00:25", "LOSS", 1, 0, "daytrade_gbpusd"),      # day Z, later LOSS
]


def _make_db(rows=_ROWS):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(_SCHEMA)
    conn.executemany(
        "INSERT INTO demo_trades "
        "(entry_type, instrument, direction, mode, entry_time, outcome, "
        " is_shadow, dedup_violation, entry_price, sl, tp, pnl_pips) "
        "VALUES ('orb_trap','GBP_USD','SELL',?,?,?,?,?,1.3,1.31,1.29,1.0)",
        [(m, et, oc, sh, dv) for (et, oc, sh, dv, m) in rows],
    )
    conn.commit()
    conn.close()
    return tmp.name


# --- Wilson math ---------------------------------------------------------
def test_wilson_lower_known_values():
    assert wilson_lower(0, 0) == 0.0          # empty guard
    assert wilson_lower(10, 10) == pytest.approx(0.7224598, abs=1e-6)
    assert wilson_lower(8, 9) == pytest.approx(0.5649938, abs=1e-6)
    assert wilson_lower(5, 10) == pytest.approx(0.2365896, abs=1e-6)


def test_wilson_lower_is_below_point_estimate():
    for wins, n in [(8, 9), (5, 10), (50, 100), (1, 3)]:
        assert wilson_lower(wins, n) < wins / n


# --- helpers -------------------------------------------------------------
def test_calendar_day():
    assert calendar_day("2026-05-13T16:00:25") == "2026-05-13"
    assert calendar_day("2026-05-13T16:00:25Z") == "2026-05-13"
    assert calendar_day(None) is None
    assert calendar_day("garbage") is None


def test_derive_session_buckets():
    assert derive_session("2026-04-29T03:30:00+00:00") == "Tokyo"
    assert derive_session("2026-04-29T08:30:00+00:00") == "London"
    assert derive_session("2026-04-29T14:30:00+00:00") == "overlap_LN"
    assert derive_session("2026-04-29T18:30:00+00:00") == "NY"
    assert derive_session("2026-04-29T22:30:00+00:00") == "Sydney"


# --- end-to-end audit ----------------------------------------------------
def test_audit_cell_live_raw_and_dedup():
    db = _make_db()
    res = audit_cell(db, "orb_trap", "GBP_USD", "SELL")
    live = res["live"]
    assert live["rows_before_exclusion"] == 3
    assert live["excluded_dedup_violation"] == 0
    # raw: 3 decisive, W1 L2
    assert live["raw"]["n_total"] == 3
    assert live["raw"]["n_decisive"] == 3
    assert live["raw"]["wins"] == 1
    assert live["raw"]["wr"] == pytest.approx(1 / 3)
    # day-deduped: 2 calendar days, earliest-of-day drops the WIN -> W0 L2
    assert live["day_deduped"]["n_calendar_days"] == 2
    assert live["day_deduped"]["n_total"] == 2
    assert live["day_deduped"]["wins"] == 0
    assert live["day_deduped"]["wr"] == 0.0
    assert live["day_deduped"]["wilson_lo"] == 0.0
    Path(db).unlink()


def test_audit_cell_shadow_excludes_dedup_and_collapses_days():
    db = _make_db()
    res = audit_cell(db, "orb_trap", "GBP_USD", "SELL")
    shadow = res["shadow"]
    # 7 shadow rows total; 2 flagged dedup_violation=1 are excluded -> 5 kept
    assert shadow["rows_before_exclusion"] == 7
    assert shadow["excluded_dedup_violation"] == 2
    # raw (dv excluded): 5 rows, decisive = W3 + L1 = 4, BE1
    assert shadow["raw"]["n_total"] == 5
    assert shadow["raw"]["wins"] == 3
    assert shadow["raw"]["losses"] == 1
    assert shadow["raw"]["breakeven"] == 1
    assert shadow["raw"]["n_decisive"] == 4
    assert shadow["raw"]["wr"] == pytest.approx(0.75)
    # day-deduped: 3 calendar days (X=WIN, Y=WIN first, Z=BREAKEVEN first)
    dd = shadow["day_deduped"]
    assert dd["n_calendar_days"] == 3
    assert dd["n_total"] == 3
    assert dd["wins"] == 2
    assert dd["losses"] == 0
    assert dd["breakeven"] == 1
    assert dd["n_decisive"] == 2
    assert dd["wr"] == pytest.approx(1.0)
    # dedup shrinks the independent N -> wider interval than raw point est.
    assert dd["wilson_lo"] < shadow["raw"]["wr"]
    Path(db).unlink()


def test_session_filter_narrows_rows():
    db = _make_db()
    # Most rows are ~14 UTC (overlap_LN); the 07:58 LIVE is London and the
    # 16:00 SHADOW LOSS is NY.
    res_overlap = audit_cell(db, "orb_trap", "GBP_USD", "SELL", session="overlap_LN")
    res_london = audit_cell(db, "orb_trap", "GBP_USD", "SELL", session="London")
    res_ny = audit_cell(db, "orb_trap", "GBP_USD", "SELL", session="NY")
    assert res_london["live"]["rows_before_exclusion"] == 1   # only 07:58 LOSS
    assert res_overlap["live"]["rows_before_exclusion"] == 2   # the two 14:xx
    assert res_overlap["shadow"]["rows_before_exclusion"] == 6  # 16:00 -> NY
    assert res_ny["shadow"]["rows_before_exclusion"] == 1
    Path(db).unlink()


def test_mode_filter_and_empty_cell():
    db = _make_db()
    res = audit_cell(db, "orb_trap", "GBP_USD", "SELL", mode="daytrade_gbpusd")
    assert res["live"]["rows_before_exclusion"] == 3
    # unknown mode -> empty everywhere
    res_none = audit_cell(db, "orb_trap", "GBP_USD", "SELL", mode="no_such_mode")
    assert res_none["live"]["rows_before_exclusion"] == 0
    assert res_none["shadow"]["rows_before_exclusion"] == 0
    assert res_none["shadow"]["raw"]["wr"] is None
    Path(db).unlink()


def test_direction_case_insensitive():
    db = _make_db()
    res = audit_cell(db, "orb_trap", "GBP_USD", "sell")
    assert res["live"]["rows_before_exclusion"] == 3
    Path(db).unlink()
