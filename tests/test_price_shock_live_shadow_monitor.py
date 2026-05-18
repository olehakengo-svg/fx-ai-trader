import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.demo_db import DemoDB
from tools import price_shock_live_shadow_monitor as monitor


STRATEGY = "price_shock_rev_eur_gbp_h1_long"


@pytest.fixture
def demo_db_path(tmp_path):
    path = tmp_path / "demo_trades.db"
    db = DemoDB(db_path=str(path))
    conn = getattr(db._local, "conn", None)
    if conn is not None:
        conn.close()
        db._local.conn = None
    return path


def _insert_trade(
    db_path: Path,
    strategy: str = STRATEGY,
    pnl: float = 1.0,
    *,
    is_shadow: int = 1,
    status: str = "CLOSED",
    close_reason: str = "horizon",
    days_ago: int = 1,
    trade_id: str | None = None,
):
    opened = datetime.now(timezone.utc) - timedelta(days=days_ago)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO demo_trades (
                trade_id, status, direction, entry_price, entry_time,
                exit_price, exit_time, pnl_pips, outcome, entry_type,
                confidence, close_reason, is_shadow, instrument
            )
            VALUES (?, ?, 'BUY', 1.0, ?, 1.0, ?, ?, ?, ?, 60, ?, ?, 'EUR_GBP')
            """,
            (
                trade_id or f"t-{strategy}-{pnl}-{is_shadow}-{status}-{days_ago}-{datetime.now().timestamp()}",
                status,
                opened.isoformat(),
                (opened + timedelta(hours=1)).isoformat(),
                pnl if status.upper() == "CLOSED" else None,
                "WIN" if pnl > 0 else "LOSS",
                strategy,
                close_reason,
                is_shadow,
            ),
        )
        conn.commit()


def _insert_event_lock_block(db_path: Path, days_ago: int = 1):
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                reason TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO events (event_type, reason, created_at) VALUES (?, ?, ?)",
            ("trade_blocked", "eur_base_shock_lock(eur_gbp_vs_eur_aud)", created.isoformat()),
        )
        conn.commit()


def _populate_closed_set(db_path: Path, wins: int, losses: int, *, strategy: str = STRATEGY):
    pnls = [10.0] * wins + [-5.0] * losses
    for idx, pnl in enumerate(pnls):
        _insert_trade(
            db_path,
            strategy,
            pnl,
            close_reason="horizon",
            days_ago=(idx % 6) * 7 + 6,
            trade_id=f"{strategy}-{idx}",
        )


def test_empty_db_outputs_no_data(demo_db_path):
    result = monitor.analyze(demo_db_path, weeks=6)
    table = monitor.render_table(result)
    assert "No data" in table
    assert all(item["n"] == 0 for item in result["strategies"])


def test_n10_wr50_collecting(demo_db_path):
    _populate_closed_set(demo_db_path, wins=5, losses=5)
    result = monitor.analyze(demo_db_path, weeks=6, strategy=STRATEGY)
    item = result["strategies"][0]
    assert item["n"] == 10
    assert item["wr"] == pytest.approx(0.5)
    assert item["status"] == "COLLECTING"


def test_n35_wr60_promote_pending_one_or_two_criteria_unmet(demo_db_path):
    _populate_closed_set(demo_db_path, wins=21, losses=14)
    result = monitor.analyze(demo_db_path, weeks=6, strategy=STRATEGY)
    item = result["strategies"][0]
    assert item["n"] == 35
    assert item["wr"] == pytest.approx(0.60)
    assert item["promote_criteria"]["n_ge_30"] is True
    assert item["promote_criteria"]["six_weeks_ev_positive"] is True
    assert item["promote_criteria"]["wilson_lo_ge_0_50"] is False
    assert item["promote_criteria"]["raw_binom_p_lt_0_01"] is False
    assert item["status"] == "PROMOTE_PENDING"


def test_n35_high_wr_promote_ready(demo_db_path):
    _populate_closed_set(demo_db_path, wins=25, losses=10)
    result = monitor.analyze(demo_db_path, weeks=6, strategy=STRATEGY)
    item = result["strategies"][0]
    assert item["n"] == 35
    assert item["wr"] == pytest.approx(25 / 35)
    assert item["wilson_lo_95"] >= 0.50
    assert item["raw_binom_p"] < 0.01
    assert item["promote_criteria"]["six_weeks_ev_positive"] is True
    assert item["status"] == "PROMOTE_READY"


def test_n20_low_wilson_demote_deactivate(demo_db_path):
    _populate_closed_set(demo_db_path, wins=8, losses=12)
    result = monitor.analyze(demo_db_path, weeks=6, strategy=STRATEGY)
    item = result["strategies"][0]
    assert item["n"] == 20
    assert item["wilson_lo_95"] < 0.40
    assert item["status"] == "DEMOTE_DEACTIVATE"


def test_live_is_shadow_zero_is_excluded(demo_db_path):
    _insert_trade(demo_db_path, pnl=10.0, is_shadow=1, trade_id="shadow-win")
    _insert_trade(demo_db_path, pnl=-100.0, is_shadow=0, trade_id="live-loss")
    result = monitor.analyze(demo_db_path, weeks=6, strategy=STRATEGY)
    item = result["strategies"][0]
    assert item["n"] == 1
    assert item["wins"] == 1
    assert item["ev_pips"] == pytest.approx(10.0)


def test_price_shock_like_filter_excludes_other_strategy(demo_db_path):
    _insert_trade(demo_db_path, strategy=STRATEGY, pnl=10.0, trade_id="in-family")
    _insert_trade(
        demo_db_path,
        strategy="sr_weighted_bounce",
        pnl=-100.0,
        trade_id="out-of-family",
    )
    result = monitor.analyze(demo_db_path, weeks=6)
    total_n = sum(item["n"] for item in result["strategies"])
    assert total_n == 1


def test_eur_gbp_eur_aud_simultaneous_open_counts_lock_violation(demo_db_path):
    _insert_trade(
        demo_db_path,
        "price_shock_rev_eur_gbp_h1_long",
        status="OPEN",
        pnl=0.0,
        trade_id="open-eur-gbp",
    )
    _insert_trade(
        demo_db_path,
        "price_shock_rev_eur_aud_h1_long",
        status="OPEN",
        pnl=0.0,
        trade_id="open-eur-aud",
    )
    _insert_event_lock_block(demo_db_path)
    result = monitor.analyze(demo_db_path, weeks=6)
    assert result["shared_lock"]["block_count"] == 1
    assert result["shared_lock"]["violation_count"] > 0
    assert "CRITICAL" in monitor.render_table(result)


def test_table_and_json_cli_outputs(demo_db_path):
    _populate_closed_set(demo_db_path, wins=5, losses=5)
    script = Path("tools/price_shock_live_shadow_monitor.py")
    table_run = subprocess.run(
        [sys.executable, str(script), "--db", str(demo_db_path), "--weeks", "6", "--strategy", STRATEGY],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Price-Shock Reversion Tier 1" in table_run.stdout
    assert "COLLECTING" in table_run.stdout

    json_run = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db",
            str(demo_db_path),
            "--weeks",
            "6",
            "--strategy",
            STRATEGY,
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(json_run.stdout)
    assert payload["strategies"][0]["strategy"] == STRATEGY
    assert payload["strategies"][0]["n"] == 10
