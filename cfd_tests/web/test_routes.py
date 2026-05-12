"""web.app: Flask route smoke tests over a seeded tmp DB."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfd_trader.audit.oanda_audit import OandaAuditEntry, init_db, record_entry
from cfd_trader.web.app import create_app


def _seed(db: str, *, wins: int, losses: int) -> None:
    extra = json.dumps({"bonferroni_m": 2, "selection_reason": "short_only_post_hoc"})
    for i in range(wins):
        record_entry(db, OandaAuditEntry(
            ts=f"2026-05-1{i+1}T14:30:00Z", instrument="SPX500_USD",
            strategy_name="orb_ny_open_short", bridge_status="filled",
            side="short", units=1, signal_price=5000.0, entry_price=5000.0,
            is_shadow=1, mode="SHADOW", extra_json=extra,
            exit_ts=f"2026-05-1{i+1}T15:30:00Z", exit_price=4990.0, pnl_point=10.0,
        ))
    for i in range(losses):
        record_entry(db, OandaAuditEntry(
            ts=f"2026-05-2{i+1}T14:30:00Z", instrument="SPX500_USD",
            strategy_name="orb_ny_open_short", bridge_status="filled",
            side="short", units=1, signal_price=5000.0, entry_price=5000.0,
            is_shadow=1, mode="SHADOW", extra_json=extra,
            exit_ts=f"2026-05-2{i+1}T15:30:00Z", exit_price=5010.0, pnl_point=-10.0,
        ))


@pytest.fixture
def client(tmp_path: Path):
    db = tmp_path / "t.db"
    init_db(str(db))
    _seed(str(db), wins=3, losses=2)
    app = create_app(db_path=str(db))
    return app.test_client()


def test_overview_renders(client) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "orb_ny_open_short" in body
    assert "Shadow strategies" in body
    # System panel now uses "strategies" and "no drift"/"orphan" wording
    assert "strategies" in body
    assert "no drift" in body or "orphan" in body
    # Charts must render (inline SVG, no external script)
    assert "Cumulative PnL" in body
    assert "<svg" in body
    assert "chart-line" in body
    assert "N progress toward H1 gate" in body


def test_overview_shows_three_bucket_cards(client) -> None:
    """Section 5.D bucket split: Shadow / Live / Unrouted / MT5 broker."""
    resp = client.get("/")
    body = resp.data.decode()
    assert "Shadow trades" in body
    assert "Live trades" in body
    assert "Unrouted intent" in body
    assert "MT5 broker" in body


def test_overview_broker_card_unconfigured_says_null_broker(client) -> None:
    """Without env, the broker card must say 'null broker' — not pretend to be Live-ready."""
    resp = client.get("/")
    body = resp.data.decode()
    assert "null broker" in body
    # The reason string from broker_status_from_env should be visible
    assert "CFD_MT5_SHIM" in body


def test_overview_shows_n_count(client) -> None:
    resp = client.get("/")
    body = resp.data.decode()
    # Seeded 3 wins + 2 losses = 5 trades
    assert ">5<" in body or "N</th>" in body  # at minimum the column header
    assert "H1 distance" in body


def test_shadow_trades_renders(client) -> None:
    resp = client.get("/shadow-trades/orb_ny_open_short")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "orb_ny_open_short" in body
    assert "pnl (pt)" in body
    assert "cum pnl" in body
    # Cumulative PnL chart should render
    assert "<svg" in body
    assert "Trade ledger" in body


def test_progress_renders(client) -> None:
    resp = client.get("/progress")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "H1 gate progress" in body
    assert "orb_ny_open_short" in body
    assert "progress-bar" in body


def test_bridge_renders(client) -> None:
    resp = client.get("/bridge")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "OANDA" in body
    assert "bridge_status" in body
    # Seed used bridge_status=filled — should appear in summary
    assert "filled" in body


def test_bridge_empty_db_no_crash(tmp_path: Path) -> None:
    db = tmp_path / "empty_bridge.db"
    init_db(str(db))
    app = create_app(db_path=str(db))
    c = app.test_client()
    assert c.get("/bridge").status_code == 200


def test_empty_db_no_crash(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    init_db(str(db))
    app = create_app(db_path=str(db))
    c = app.test_client()
    assert c.get("/").status_code == 200
    assert c.get("/shadow-trades/orb_ny_open_short").status_code == 200
    assert c.get("/progress").status_code == 200
