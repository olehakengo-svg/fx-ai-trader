import sqlite3
from datetime import timezone

import pandas as pd

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from modules.regime_classifier import REGIME_MODERATE_TREND, REGIME_NO_GO


def _write_m15_cache(cache_dir, instrument="USD_JPY"):
    idx = pd.date_range("2026-01-01", periods=120, freq="15min", tz="UTC")
    close = pd.Series(
        [150.0 + (i * 0.01) + (0.03 if i % 3 == 0 else 0.0) for i in range(len(idx))],
        index=idx,
    )
    df = pd.DataFrame(
        {
            "open": close - 0.02,
            "high": close + 0.04,
            "low": close - 0.04,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_dir / f"{instrument}_15m.parquet")
    return idx[-1]


def test_v2_regime_column_exists_after_migration(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    with sqlite3.connect(db._path) as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(demo_trades)")]

    assert "v2_regime" in cols


def test_open_trade_records_v2_regime_and_defaults_to_null(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    tagged_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
        v2_regime=REGIME_MODERATE_TREND,
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
                "SELECT trade_id, v2_regime FROM demo_trades "
                "WHERE trade_id IN (?, ?)",
                (tagged_id, untagged_id),
            ).fetchall()
        )

    assert rows[tagged_id] == REGIME_MODERATE_TREND
    assert rows[untagged_id] is None


def test_demo_trader_computes_v2_regime_with_real_classifier(tmp_path, monkeypatch):
    import modules.htf_data_source as htf_data_source

    monkeypatch.setattr(
        htf_data_source,
        "compute_mtf_features",
        lambda instrument: {
            "m15": {"adx": 20.0, "ema_slope": 0.01, "hurst_64": 0.80},
            "m5": None,
            "h1": None,
        },
    )
    db = DemoDB(str(tmp_path / "demo.db"))
    trader = DemoTrader(db)

    v2_regime = trader._compute_v2_regime("USD_JPY")
    trade_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
        v2_regime=v2_regime,
    )

    with sqlite3.connect(db._path) as con:
        stored = con.execute(
            "SELECT v2_regime FROM demo_trades WHERE trade_id=?", (trade_id,)
        ).fetchone()[0]

    assert v2_regime == REGIME_MODERATE_TREND
    assert stored == REGIME_MODERATE_TREND


def test_composite_dow_and_v2_regime_tags_can_coexist(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    trade_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
        dow_regime="TRENDING",
        v2_regime=REGIME_MODERATE_TREND,
    )

    with sqlite3.connect(db._path) as con:
        row = con.execute(
            "SELECT dow_regime, v2_regime FROM demo_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()

    assert row == ("TRENDING", REGIME_MODERATE_TREND)


def test_v2_regime_backfill_dry_run_reports_updates_without_writing(tmp_path):
    cache_dir = tmp_path / "massive"
    ts = _write_m15_cache(cache_dir)

    from tools.v2_regime_backfill import run_backfill

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

    result = run_backfill(str(db._path), apply=False, chunk_size=100, cache_dir=cache_dir)

    with sqlite3.connect(db._path) as con:
        stored = con.execute(
            "SELECT v2_regime FROM demo_trades WHERE trade_id=?", (trade_id,)
        ).fetchone()[0]

    assert result["mode"] == "dry-run"
    assert result["update_sql"] == "UPDATE demo_trades SET v2_regime = ? WHERE trade_id = ?"
    assert result["would_update"] == 1
    assert result["updates"][0]["trade_id"] == trade_id
    assert result["updates"][0]["v2_regime"] in {REGIME_MODERATE_TREND, REGIME_NO_GO}
    assert stored is None
