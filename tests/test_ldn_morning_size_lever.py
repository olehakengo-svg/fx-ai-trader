from __future__ import annotations

import json
from datetime import datetime, timezone

from modules.demo_trader import DemoTrader, LDN_MORNING_SIZE_LEVER_REASON

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader


def _dt(hour: int) -> datetime:
    return datetime(2026, 6, 12, hour, 0, tzinfo=timezone.utc)


def _trader():
    return DemoTrader.__new__(DemoTrader)


def test_target_cells_utc_07_08_09_get_half_units(monkeypatch):
    trader = _trader()

    for cell_id in ("E5", "E7", "E10"):
        for hour in (7, 8, 9):
            units, applied = trader._resolve_ldn_morning_size_lever(
                5000,
                cell_id,
                _dt(hour),
                is_shadow=False,
            )
            assert (units, applied) == (2500, True)


def test_target_cell_utc_10_is_unchanged():
    units, applied = _trader()._resolve_ldn_morning_size_lever(
        5000,
        "E5",
        _dt(10),
        is_shadow=False,
    )
    assert (units, applied) == (5000, False)


def test_non_target_e9_utc_08_is_unchanged():
    units, applied = _trader()._resolve_ldn_morning_size_lever(
        5000,
        "E9",
        _dt(8),
        is_shadow=False,
    )
    assert (units, applied) == (5000, False)


def test_shadow_is_unchanged():
    units, applied = _trader()._resolve_ldn_morning_size_lever(
        5000,
        "E5",
        _dt(8),
        is_shadow=True,
    )
    assert (units, applied) == (5000, False)


def test_env_zero_disables_lever(monkeypatch):
    monkeypatch.setenv("LDN_MORNING_SIZE_LEVER", "0")
    units, applied = _trader()._resolve_ldn_morning_size_lever(
        5000,
        "E5",
        _dt(8),
        is_shadow=False,
    )
    assert (units, applied) == (5000, False)


def _sig(entry_type: str, signal: str, entry: float = 1.1000):
    if signal == "SELL":
        sl = entry + 0.0015
        tp = entry - 0.0030
        score = -1.0
    else:
        sl = entry - 0.0015
        tp = entry + 0.0030
        score = 1.0
    return {
        "entry": entry,
        "signal": signal,
        "entry_type": entry_type,
        "confidence": 70,
        "score": score,
        "sl": sl,
        "tp": tp,
        "atr": 0.0010,
        "reasons": [f"✅ edge-cell ldn lever test {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def test_e5_live_oanda_units_halved_and_reason_persisted(monkeypatch, tmp_path):
    from modules import data as data_mod

    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _inst: {"bid": 1.1000, "ask": 1.1001},
    )
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)
    import hashlib
    import research.edge_discovery.strategy_family_map as sfm

    class _FakeMD5:
        def hexdigest(self):
            return "00000000"

    monkeypatch.setattr(hashlib, "md5", lambda *_args, **_kwargs: _FakeMD5())
    monkeypatch.setattr(sfm, "strategy_aware_alignment", lambda *_args, **_kwargs: "conflict")

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sig("dt_bb_rsi_mr", "SELL"),
        "15m",
        "GBP_USD",
    )

    assert trader._oanda.calls[-1]["units"] == 2500
    with trader._db._safe_conn() as conn:
        row = conn.execute(
            """
            SELECT edge_cell_id, is_shadow, reasons
            FROM demo_trades
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()

    assert row["edge_cell_id"] == "E5"
    assert row["is_shadow"] == 0
    assert LDN_MORNING_SIZE_LEVER_REASON in json.loads(row["reasons"])
    assert any("[LDN_MORNING_SIZE] E5 dt_bb_rsi_mr GBP_USD" in log for log in logs)


def test_e9_live_oanda_units_and_reasons_unchanged(monkeypatch, tmp_path):
    from modules import data as data_mod

    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _inst: {"bid": 1.1000, "ask": 1.1001},
    )
    trader, _logs = make_trader(tmp_path, monkeypatch, hour=8)
    sig = _sig("orb_trap", "SELL")
    sig["regime"] = {"regime": "RANGE"}

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        sig,
        "15m",
        "GBP_USD",
    )

    assert trader._oanda.calls[-1]["units"] == 5000
    with trader._db._safe_conn() as conn:
        row = conn.execute(
            "SELECT edge_cell_id, reasons FROM demo_trades ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row["edge_cell_id"] == "E9"
    assert LDN_MORNING_SIZE_LEVER_REASON not in json.loads(row["reasons"])
