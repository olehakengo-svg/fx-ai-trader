"""v9.3: MTF Regime Monitor shadow-integration tests."""
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


@pytest.fixture
def trader():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DemoDB(db_path=path)
    t = DemoTrader(db)
    yield t
    try:
        os.unlink(path)
    except OSError:
        pass


class TestMTFCache:
    def test_mtf_cache_returns_within_ttl(self, trader):
        """Cached MTF payload returned without re-fetching within TTL."""
        now = datetime.now(timezone.utc)
        payload = {"regime": "trend_up_weak", "d1": 1, "h4": 1, "vol": "normal"}
        trader._mtf_cache["USD_JPY"] = (now, payload)
        with patch("research.edge_discovery.mtf_regime_engine.fetch_mtf_data") as mock:
            mock.side_effect = AssertionError("should not be called")
            got = trader._get_mtf_regime("USD_JPY")
        assert got == payload

    def test_mtf_expired_cache_triggers_refetch(self, trader, monkeypatch):
        old = datetime.now(timezone.utc).replace(year=2020)
        trader._mtf_cache["USD_JPY"] = (old, {"regime": "range_tight", "d1": 0,
                                                "h4": 0, "vol": "squeeze"})
        called = {"n": 0}

        def _fake_fetch(instrument=None, *args, **kwargs):
            called["n"] += 1
            import pandas as pd
            # minimal valid OHLC with enough bars for ADX/EMA200
            idx = pd.date_range("2024-01-01", periods=250, freq="1D", tz="UTC")
            d = pd.DataFrame({
                "time": idx,
                "open": 1.0, "high": 1.01, "low": 0.99, "close": 1.0,
                "volume": 100,
            })
            return {"instrument": instrument,
                    "base": d.copy(), "h4": d.copy(), "d1": d.copy()}

        import research.edge_discovery.mtf_regime_engine as me
        monkeypatch.setattr(me, "fetch_mtf_data", _fake_fetch)
        r = trader._get_mtf_regime("USD_JPY")
        assert called["n"] == 1
        assert "regime" in r

    def test_mtf_fetch_failure_fails_safe(self, trader, monkeypatch):
        """Engine errors should NOT block — return 'uncertain' safely."""
        import research.edge_discovery.mtf_regime_engine as me

        def _boom(**kwargs):
            raise RuntimeError("OANDA down")
        monkeypatch.setattr(me, "fetch_mtf_data", _boom)
        trader._mtf_cache.clear()
        r = trader._get_mtf_regime("USD_JPY")
        assert r["regime"] == "uncertain"

    def test_mtf_empty_result_returns_uncertain(self, trader, monkeypatch):
        import research.edge_discovery.mtf_regime_engine as me
        import pandas as pd

        def _empty(**kwargs):
            return {"instrument": kwargs.get("instrument"),
                    "base": pd.DataFrame(),
                    "h4": pd.DataFrame(), "d1": pd.DataFrame()}
        monkeypatch.setattr(me, "fetch_mtf_data", _empty)
        trader._mtf_cache.clear()
        r = trader._get_mtf_regime("USD_JPY")
        assert r["regime"] == "uncertain"


class TestDBSchema:
    def test_mtf_columns_exist(self, trader):
        """demo_trades should have mtf_* columns after migration."""
        import sqlite3
        with sqlite3.connect(trader._db._path) as con:
            cols = [r[1] for r in con.execute("PRAGMA table_info(demo_trades)")]
        for c in ("mtf_regime", "mtf_d1_label", "mtf_h4_label", "mtf_vol_state"):
            assert c in cols, f"missing column: {c}"

    def test_open_trade_accepts_mtf_params(self, trader):
        """open_trade should record MTF fields."""
        tid = trader._db.open_trade(
            direction="BUY", entry_price=150.0, sl=149.5, tp=150.8,
            entry_type="ema_trend_scalp", confidence=80, tf="15m",
            instrument="USD_JPY",
            mtf_regime="trend_up_weak", mtf_d1_label=1,
            mtf_h4_label=1, mtf_vol_state="normal",
        )
        import sqlite3
        with sqlite3.connect(trader._db._path) as con:
            row = con.execute(
                "SELECT mtf_regime, mtf_d1_label, mtf_h4_label, mtf_vol_state "
                "FROM demo_trades WHERE trade_id=?", (tid,)
            ).fetchone()
        assert row == ("trend_up_weak", 1, 1, "normal")
