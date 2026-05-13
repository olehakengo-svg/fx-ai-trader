import sqlite3
from datetime import timezone

import pandas as pd

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def _write_trending_cache(cache_dir, instrument="USD_JPY"):
    idx = pd.date_range("2026-01-01", periods=90, freq="1h", tz="UTC")
    close = pd.Series([100.0 + i * 0.2 for i in range(len(idx))], index=idx)
    df = pd.DataFrame(
        {
            "open": close - 0.05,
            "high": close + 0.08,
            "low": close - 0.08,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_dir / f"{instrument}_1h.parquet")
    return idx[-1]


def test_dow_regime_column_exists_after_migration(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    with sqlite3.connect(db._path) as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(demo_trades)")]

    assert "dow_regime" in cols


def test_open_trade_records_dow_regime_and_defaults_to_null(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    tagged_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
        dow_regime="TRENDING",
    )
    untagged_id = db.open_trade(
        direction="SELL",
        entry_price=150.0,
        sl=150.5,
        tp=149.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
    )

    with sqlite3.connect(db._path) as con:
        rows = dict(
            con.execute(
                "SELECT trade_id, dow_regime FROM demo_trades "
                "WHERE trade_id IN (?, ?)",
                (tagged_id, untagged_id),
            ).fetchall()
        )

    assert rows[tagged_id] == "TRENDING"
    assert rows[untagged_id] is None


def test_demo_trader_computes_dow_regime_with_real_classifier(tmp_path, monkeypatch):
    cache_dir = tmp_path / "massive"
    ts = _write_trending_cache(cache_dir)

    import lib.regime_classifier as regime_classifier

    monkeypatch.setattr(regime_classifier, "CACHE_DIR", cache_dir)
    db = DemoDB(str(tmp_path / "demo.db"))
    trader = DemoTrader(db)

    dow_regime = trader._compute_dow_regime("USD_JPY", ts.to_pydatetime())
    trade_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
        dow_regime=dow_regime,
    )

    with sqlite3.connect(db._path) as con:
        stored = con.execute(
            "SELECT dow_regime FROM demo_trades WHERE trade_id=?", (trade_id,)
        ).fetchone()[0]

    assert dow_regime == "TRENDING"
    assert stored == "TRENDING"


def test_dow_regime_backfill_dry_run_reports_updates_without_writing(tmp_path, monkeypatch):
    cache_dir = tmp_path / "massive"
    ts = _write_trending_cache(cache_dir)

    import lib.regime_classifier as regime_classifier
    from tools.dow_regime_backfill import run_backfill

    monkeypatch.setattr(regime_classifier, "CACHE_DIR", cache_dir)
    db = DemoDB(str(tmp_path / "demo.db"))
    trade_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
    )
    aware_ts = ts.to_pydatetime().replace(tzinfo=timezone.utc)
    with sqlite3.connect(db._path) as con:
        con.execute(
            "UPDATE demo_trades SET entry_time=? WHERE trade_id=?",
            (aware_ts.isoformat(), trade_id),
        )
        con.commit()

    result = run_backfill(str(db._path), apply=False, chunk_size=100)

    with sqlite3.connect(db._path) as con:
        stored = con.execute(
            "SELECT dow_regime FROM demo_trades WHERE trade_id=?", (trade_id,)
        ).fetchone()[0]

    assert result["mode"] == "dry-run"
    assert result["update_sql"] == "UPDATE demo_trades SET dow_regime = ? WHERE trade_id = ?"
    assert result["would_update"] == 1
    assert result["updates"][0]["trade_id"] == trade_id
    assert result["updates"][0]["dow_regime"] == "TRENDING"
    assert stored is None
