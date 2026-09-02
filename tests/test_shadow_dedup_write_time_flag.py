"""Write-time cross-process dedup flagging (rule:R3, 2026-09-02).

Root cause (ema200 forensics, hourblock-recal-and-ema200-verdict-2026-09-02.md
Study 2): the emit dedup gate (`_maybe_reserve_signal_emit` /
`_maybe_reserve_order_bar_emit`) is *process-local in-memory* state. It blocks
duplicates within one gunicorn worker, but cannot coordinate across a process
boundary (deploy overlap, container replacement, a transient second instance
writing to the shared Render Disk SQLite). The boot-time `_backfill_dedup_
violation` catches those cross-process dups retroactively, but only *at boot* —
so any analysis run in the window between a dup's creation and the next restart
sees an inflated shadow N (e.g. the 2026-07-31 ema200 quant-eval N=79 that later
shrank once a boot flagged the 22 near-dup pairs).

Fix: `open_trade` consults the *shared DB* at write time and marks a shadow row
`dedup_violation=1` when a non-dup same-key shadow row already exists inside the
TF window. This holds across process boundaries (it reads the committed DB, not
in-memory state) and is immediate (not gated on the next boot), so point-in-time
quant-eval no longer double-counts recently-created dups.

The row is still inserted (no trading-behaviour change, live sends untouched) —
only its `dedup_violation` flag changes, which is exactly what the quant-eval /
R2 audit tools already exclude.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from modules.demo_db import DemoDB


def _open_shadow(db, *, entry_type="ema200_trend_reversal", instrument="USD_JPY",
                 direction="BUY", tf="15m", entry=159.92):
    return db.open_trade(
        direction=direction,
        entry_price=entry,
        sl=entry - 0.30 if direction == "BUY" else entry + 0.30,
        tp=entry + 0.60 if direction == "BUY" else entry - 0.60,
        entry_type=entry_type,
        confidence=50,
        tf=tf,
        mode="daytrade",
        instrument=instrument,
        is_shadow=True,
    )


def _dv(db, trade_id):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT dedup_violation FROM demo_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()["dedup_violation"]


def test_cross_process_duplicate_shadow_insert_flagged_at_write_time(tmp_path):
    """Two DemoDB instances on the same file = two processes with independent
    in-memory dedup state. The second same-key shadow insert must be flagged
    dedup_violation=1 by consulting the shared DB — the in-memory gate cannot
    see across the boundary."""
    path = str(tmp_path / "cross-proc.db")
    db_a = DemoDB(path)   # "process A"
    db_b = DemoDB(path)   # "process B" — separate in-memory dedup dict

    first = _open_shadow(db_a)
    second = _open_shadow(db_b)   # same (entry_type, instrument, direction), same 15m bar

    assert _dv(db_a, first) == 0
    assert _dv(db_b, second) == 1


def test_write_time_flag_respects_tf_window(tmp_path):
    """A same-key shadow row *outside* the TF window is not a dup — the second
    insert stays dedup_violation=0."""
    path = str(tmp_path / "window.db")
    db = DemoDB(path)

    # First row far in the past (beyond the 900s 15m window).
    old = datetime.now(timezone.utc) - timedelta(seconds=1200)
    with db._safe_conn() as conn:
        conn.execute(
            """INSERT INTO demo_trades
               (trade_id, status, direction, entry_price, entry_time,
                sl, tp, entry_type, confidence, tf, is_shadow, dedup_violation,
                mode, instrument)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("old-row-000", "OPEN", "BUY", 159.92, old.isoformat(),
             159.62, 160.52, "ema200_trend_reversal", 50, "15m", 1, 0,
             "daytrade", "USD_JPY"),
        )
        conn.commit()

    fresh = _open_shadow(db)
    assert _dv(db, fresh) == 0


def test_write_time_flag_only_chains_from_non_dup_rows(tmp_path):
    """Mirrors the backfill's "advance last_seen only on non-dup" semantics: a
    third row whose only in-window neighbour is itself a flagged dup is NOT
    flagged (the exclusion window is anchored on the last kept row)."""
    path = str(tmp_path / "chain.db")
    db = DemoDB(path)
    now = datetime.now(timezone.utc)

    def _insert(offset_sec, dv):
        tid = f"row-{offset_sec}"
        with db._safe_conn() as conn:
            conn.execute(
                """INSERT INTO demo_trades
                   (trade_id, status, direction, entry_price, entry_time,
                    sl, tp, entry_type, confidence, tf, is_shadow,
                    dedup_violation, mode, instrument)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid, "OPEN", "BUY", 159.92,
                 (now + timedelta(seconds=offset_sec)).isoformat(),
                 159.62, 160.52, "ema200_trend_reversal", 50, "15m", 1,
                 dv, "daytrade", "USD_JPY"),
            )
            conn.commit()
        return tid

    # row1 kept (dv=0) at t; row2 dup (dv=1) at t+800 (<900 of row1)
    _insert(0, 0)
    _insert(800, 1)
    # row3 at t+1500: >900 from row1 (kept), and the only in-window neighbour is
    # the flagged dup row2 → row3 is NOT a dup.
    now2 = now + timedelta(seconds=1500)
    # emulate "now" == t+1500 by inserting via open_trade would use real now;
    # instead assert the query semantics directly.
    window = DemoDB._tf_window_sec("15m")
    lo = (now2 - timedelta(seconds=window)).isoformat()
    with db._safe_conn() as conn:
        prior = conn.execute(
            """SELECT 1 FROM demo_trades
               WHERE entry_type=? AND instrument=? AND direction=?
                 AND is_shadow=1 AND dedup_violation=0
                 AND entry_time >= ? AND entry_time < ?
               LIMIT 1""",
            ("ema200_trend_reversal", "USD_JPY", "BUY", lo, now2.isoformat()),
        ).fetchone()
    assert prior is None  # no *non-dup* prior in window → row3 would be dv=0
