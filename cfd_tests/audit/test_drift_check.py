"""drift_check: orphan detection (audit rows with unregistered strategies)."""
from __future__ import annotations

from pathlib import Path

import pytest

from cfd_trader.audit.oanda_audit import init_db, record_entry, OandaAuditEntry
from cfd_trader.audit.drift_check import find_orphan_strategies
from cfd_trader.strategies import catalog


@pytest.fixture(autouse=True)
def _reset_catalog():
    saved = dict(catalog.STRATEGIES)
    catalog.STRATEGIES.clear()
    def f(c, p):
        import pandas as pd
        return pd.DataFrame()
    catalog.register("orb_ny_open_short", f)
    yield
    catalog.STRATEGIES.clear()
    catalog.STRATEGIES.update(saved)


def _record(db: str, name: str) -> None:
    record_entry(db, OandaAuditEntry(
        ts="2026-05-11T14:30:00Z", instrument="SPX500_USD",
        strategy_name=name, bridge_status="filled",
        side="short", units=1, signal_price=5000.0, entry_price=5000.0,
        is_shadow=1, mode="SHADOW",
    ))


def test_no_orphans_when_all_strategies_registered(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    _record(str(db), "orb_ny_open_short")
    orphans = find_orphan_strategies(str(db))
    assert orphans == []


def test_detects_orphan(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    _record(str(db), "orb_ny_open_short")
    _record(str(db), "deprecated_strategy")
    orphans = find_orphan_strategies(str(db))
    assert "deprecated_strategy" in orphans
    assert "orb_ny_open_short" not in orphans


def test_no_audit_rows_no_orphans(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    assert find_orphan_strategies(str(db)) == []
