from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.intraday.kalman_d7_v18e_jpy_cross import (
    KalmanD7V18eJpyCross,
    add_kalman_d7_v18e_indicators,
)
from tools.kalman_d7_v18e_python_port import add_v18e_indicators


ROOT = Path(__file__).resolve().parents[1]


def _ctx_from_data(pair: str, data: pd.DataFrame) -> SignalContext:
    row = data.iloc[-1]
    prev = data.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row.get("atr", 0.1)),
        ema200=float(row.get("ema200", row["Close"])),
        rsi=float(row.get("rsi", 55.0)),
        adx=26.0,
        macdh=0.2,
        macdh_prev=0.1,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol=pair,
        tf="15m",
        hour_utc=int(data.index[-1].hour),
        is_jpy=True,
        pip_mult=100,
        df=data,
        backtest_mode=True,
        bar_time=data.index[-1],
    )


def test_usdjpy_365d_golden_fixture_is_locked():
    fixture = json.loads(
        (ROOT / "tests/fixtures/kalman_d7_v18e_usdjpy_365d_golden.json").read_text()
    )

    assert fixture["strategy"] == "kalman_d7_v18e"
    assert fixture["pair"] == "USDJPY"
    assert fixture["timeframe"] == "M15"
    assert fixture["summary"] == {
        "pf": 1.101,
        "n": 72,
        "wr": 0.5417,
        "net_pct": 0.054,
        "max_dd_pct": -0.109,
    }
    assert fixture["exit_rules"]["mintick"] == 0.001


def test_massive_recent_100_bars_entry_signal_matches_reference_port():
    from tests.conftest import require_data_file
    for pair in ("AUD_JPY", "EUR_JPY"):
        path = ROOT / f"data/cache/massive/{pair}_15m.parquet"
        require_data_file(path, "MASSIVE 15m integration")
        df = pd.read_parquet(path).tail(320)

        expected = add_v18e_indicators(df).tail(100)["entry_signal"].reset_index(drop=True)
        actual = add_kalman_d7_v18e_indicators(df).tail(100)["entry_signal"].reset_index(drop=True)

        assert actual.equals(expected), pair


def test_strategy_default_env_off_does_not_fire(monkeypatch):
    monkeypatch.delenv("KALMAN_D7_V18E_AUDJPY_SHADOW", raising=False)
    monkeypatch.delenv("KALMAN_D7_V18E_EURJPY_SHADOW", raising=False)

    from tests.conftest import require_data_file
    require_data_file(ROOT / "data/cache/massive/AUD_JPY_15m.parquet", "MASSIVE 15m integration")
    df = pd.read_parquet(ROOT / "data/cache/massive/AUD_JPY_15m.parquet").tail(320)
    enriched = add_kalman_d7_v18e_indicators(df)
    ctx = _ctx_from_data("AUD_JPY", enriched)

    assert KalmanD7V18eJpyCross().evaluate(ctx) is None
    assert all(s.name != "kalman_d7_v18e" for s in DaytradeEngine().strategies)


def test_strategy_env_on_registers_shadow_always(monkeypatch):
    monkeypatch.setenv("KALMAN_D7_V18E_AUDJPY_SHADOW", "1")
    monkeypatch.delenv("KALMAN_D7_V18E_EURJPY_SHADOW", raising=False)
    engine = DaytradeEngine()
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    kalman = Candidate("BUY", 70, 1.0, 2.0, [], "kalman_d7_v18e", 4.0)

    assert any(s.name == "kalman_d7_v18e" for s in engine.strategies)
    assert engine.split_shadow_always([other, kalman], other) == [kalman]


def test_new_entry_type_is_not_kalman_live_override(monkeypatch):
    monkeypatch.setenv("KALMAN_D7_LIVE_ENABLE", "1")

    assert "kalman_d7_v18e" not in DaytradeEngine.LIVE_PROMOTE_LOSERS
    assert DemoTrader._kalman_d7_live_eligible("kalman_d7_v18e", "AUD_JPY") is False
    assert DemoTrader._kalman_d7_live_eligible("kalman_d7_v18e", "EUR_JPY") is False


def test_shadow_emit_writes_oanda_audit_shadow_tracking(tmp_path, monkeypatch):
    monkeypatch.setenv("KALMAN_D7_V18E_AUDJPY_SHADOW", "1")
    db = DemoDB(str(tmp_path / "kalman-v18e-shadow.db"))
    trader = DemoTrader(db)

    trade_id = trader._open_shadow_emit_trade(
        direction="BUY",
        entry_price=100.123,
        sl=99.987,
        tp=100.200,
        entry_type="kalman_d7_v18e",
        confidence=76,
        tf="15m",
        reasons=["Kalman D7 v18e AUD_JPY shadow integration test"],
        score=4.3,
        mode="daytrade",
        instrument="AUD_JPY",
    )

    with db._safe_conn() as conn:
        row = conn.execute(
            """
            SELECT demo_trade_id, entry_type, instrument, is_live,
                   bridge_status, block_reason, units
            FROM oanda_audit
            WHERE demo_trade_id=?
            """,
            (trade_id,),
        ).fetchone()

    assert row is not None
    assert row["entry_type"] == "kalman_d7_v18e"
    assert row["instrument"] == "AUD_JPY"
    assert row["is_live"] == 0
    assert row["bridge_status"] == "skipped"
    # 2026-09-02 (rule:R3): units=0 self-described via "(shadow_emit_no_lot)"
    # suffix; "shadow_tracking" prefix preserved for guard/tool compatibility.
    assert row["block_reason"] == "shadow_tracking(shadow_emit_no_lot)"
    assert row["block_reason"].startswith("shadow_tracking")
    assert row["units"] == 0  # marker only — not an order size
