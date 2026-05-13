import json
import sqlite3
from datetime import timezone

import pandas as pd

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from tools.confluence_backfill import run_backfill
from tools.cross_pair_confluence import CACHE_DIR, compute_confluence, get_h1_direction


def _write_cache(cache_dir, pair, closes):
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="1h", tz="UTC")
    close = pd.Series(closes, index=idx)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.1,
            "low": close - 0.1,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_dir / f"{pair}_1h.parquet")
    return idx[-1]


def test_get_h1_direction_uses_close_to_close_window(tmp_path):
    ts = _write_cache(tmp_path, "USD_JPY", [100, 101, 102, 103, 104, 105])

    assert get_h1_direction("USD_JPY", ts, cache_dir=tmp_path) == "up"


def test_compute_confluence_strong_with_literal_usdjpy_mapping(tmp_path):
    ts = _write_cache(tmp_path, "USD_JPY", [100, 101, 102, 103, 104, 105])
    _write_cache(tmp_path, "EUR_USD", [1.10, 1.09, 1.08, 1.07, 1.06, 1.05])
    _write_cache(tmp_path, "GBP_USD", [1.30, 1.29, 1.28, 1.27, 1.26, 1.25])
    _write_cache(tmp_path, "USD_CHF", [0.90, 0.91, 0.92, 0.93, 0.94, 0.95])
    _write_cache(tmp_path, "USD_CAD", [1.30, 1.31, 1.32, 1.33, 1.34, 1.35])
    _write_cache(tmp_path, "AUD_USD", [0.70, 0.69, 0.68, 0.67, 0.66, 0.65])

    result = compute_confluence("USDJPY", "BUY", ts, cache_dir=tmp_path)

    assert result.score == "STRONG"
    assert result.confirmations == 3
    details = json.loads(result.details_json())
    assert details["primary_pair"] == "USD_JPY"
    assert len(details["components"]) == 3


def test_demo_db_records_confluence_columns(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))
    trade_id = db.open_trade(
        direction="BUY",
        entry_price=150.0,
        sl=149.5,
        tp=151.0,
        entry_type="test_strategy",
        confidence=70,
        instrument="USD_JPY",
        confluence_score="STRONG",
        confluence_details='{"ok": true}',
    )

    with sqlite3.connect(db._path) as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(demo_trades)")]
        row = con.execute(
            "SELECT confluence_score, confluence_details FROM demo_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()

    assert "confluence_score" in cols
    assert "confluence_details" in cols
    assert row == ("STRONG", '{"ok": true}')


def test_demo_trader_computes_confluence_with_real_massive_cache():
    trader = DemoTrader(DemoDB(":memory:"))
    ts = pd.read_parquet(CACHE_DIR / "USD_JPY_1h.parquet").index[-1]

    tag = trader._compute_confluence_tag("USD_JPY", "BUY", ts)

    assert tag["score"] in {"STRONG", "WEAK", "MIXED", "NULL"}
    assert tag["details"]
    assert json.loads(tag["details"])["primary_pair"] == "USD_JPY"


def test_confluence_backfill_dry_run_reports_without_writing(tmp_path):
    ts = _write_cache(tmp_path, "USD_JPY", [100, 101, 102, 103, 104, 105])
    _write_cache(tmp_path, "EUR_USD", [1.10, 1.09, 1.08, 1.07, 1.06, 1.05])
    _write_cache(tmp_path, "GBP_USD", [1.30, 1.29, 1.28, 1.27, 1.26, 1.25])
    _write_cache(tmp_path, "USD_CHF", [0.90, 0.91, 0.92, 0.93, 0.94, 0.95])
    _write_cache(tmp_path, "USD_CAD", [1.30, 1.31, 1.32, 1.33, 1.34, 1.35])
    _write_cache(tmp_path, "AUD_USD", [0.70, 0.69, 0.68, 0.67, 0.66, 0.65])

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

    result = run_backfill(str(db._path), apply=False, cache_dir=tmp_path)

    with sqlite3.connect(db._path) as con:
        stored = con.execute(
            "SELECT confluence_score FROM demo_trades WHERE trade_id=?", (trade_id,)
        ).fetchone()[0]

    assert result["mode"] == "dry-run"
    assert result["update_sql"].startswith("UPDATE demo_trades SET confluence_score")
    assert result["would_update"] == 1
    assert result["updates"][0]["confluence_score"] == "STRONG"
    assert stored is None
