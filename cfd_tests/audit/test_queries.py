"""audit.queries: centralized read helpers with is_shadow filter enforced."""
from __future__ import annotations

from pathlib import Path

from cfd_trader.audit.oanda_audit import init_db, record_entry, OandaAuditEntry
from cfd_trader.audit.queries import (
    shadow_trades_for, count_shadow, live_trades_for, count_live,
)


def _seed_db(tmp_path: Path) -> Path:
    db = tmp_path / "t.db"
    init_db(str(db))
    for is_shadow, mode, pnl in [(1, "SHADOW", 5.0), (1, "SHADOW", -3.0), (0, "LIVE", 1.0)]:
        record_entry(str(db), OandaAuditEntry(
            ts="2026-05-11T14:30:00Z", instrument="SPX500_USD",
            strategy_name="orb_ny_open_short", bridge_status="filled",
            side="short", units=1, signal_price=5000.0, entry_price=5000.0,
            is_shadow=is_shadow, mode=mode,
            exit_ts="2026-05-11T15:30:00Z", exit_price=5000.0 - pnl,
            pnl_point=pnl,
        ))
    return db


def test_shadow_trades_for_returns_only_shadow_rows(tmp_path: Path) -> None:
    db = _seed_db(tmp_path)
    rows = shadow_trades_for(str(db), strategy_name="orb_ny_open_short")
    assert len(rows) == 2
    for r in rows:
        assert r.is_shadow == 1


def test_count_shadow(tmp_path: Path) -> None:
    db = _seed_db(tmp_path)
    assert count_shadow(str(db), strategy_name="orb_ny_open_short") == 2


def test_live_trades_for_returns_only_live_rows(tmp_path: Path) -> None:
    db = _seed_db(tmp_path)
    rows = live_trades_for(str(db), strategy_name="orb_ny_open_short")
    assert len(rows) == 1
    assert rows[0].is_shadow == 0


def test_count_live(tmp_path: Path) -> None:
    db = _seed_db(tmp_path)
    assert count_live(str(db), strategy_name="orb_ny_open_short") == 1
