import sqlite3

import pytest

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def _fetch_trade(db: DemoDB, trade_id: str) -> sqlite3.Row:
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, is_shadow, oanda_trade_id, entry_type, instrument "
            "FROM demo_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()


@pytest.fixture()
def trader(tmp_path):
    return DemoTrader(DemoDB(str(tmp_path / "flag_drift.db")))


def test_open_trade_without_oanda_id_is_persisted_as_shadow(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    trade_id = db.open_trade(
        "BUY",
        150.0,
        149.8,
        150.4,
        "bb_rsi_reversion",
        80,
        mode="scalp",
        instrument="USD_JPY",
        is_shadow=False,
        enforce_oanda_live_invariant=True,
    )

    row = _fetch_trade(db, trade_id)
    assert row["is_shadow"] == 1
    assert row["oanda_trade_id"] == ""


def test_set_oanda_trade_id_is_only_path_to_live_without_flag_drift(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))
    trade_id = db.open_trade(
        "BUY",
        150.0,
        149.8,
        150.4,
        "trendline_sweep",
        80,
        mode="daytrade",
        instrument="EUR_USD",
        is_shadow=False,
        enforce_oanda_live_invariant=True,
    )

    assert _fetch_trade(db, trade_id)["is_shadow"] == 1

    db.set_oanda_trade_id(trade_id, "OANDA-123")

    row = _fetch_trade(db, trade_id)
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"] == "OANDA-123"


def test_open_trade_with_confirmed_oanda_id_can_persist_live(tmp_path):
    db = DemoDB(str(tmp_path / "demo.db"))

    trade_id = db.open_trade(
        "SELL",
        1.1,
        1.102,
        1.096,
        "trendline_sweep",
        80,
        mode="daytrade",
        instrument="EUR_USD",
        is_shadow=False,
        oanda_trade_id="OANDA-FILLED",
        enforce_oanda_live_invariant=True,
    )

    row = _fetch_trade(db, trade_id)
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"] == "OANDA-FILLED"


def test_sentinel_and_demoted_cells_resolve_to_shadow_tier(trader):
    assert trader._resolve_tier("mtf_trend_follow_scalp", "USD_JPY", "scalp") == "SCALP_SENTINEL"
    assert trader._resolve_tier("bb_rsi_reversion", "EUR_USD", "scalp") == "PAIR_DEMOTED"
    assert trader._resolve_tier("ema_cross", "GBP_USD", "daytrade") == "FORCE_DEMOTED"


def test_trendline_sweep_all_cells_demoted_pin_shadow_even_when_filled(trader):
    # 2026-07-15 (rule:R2) pre-reg trendline_sweep_gbpusd_pairscope_2026-07-13
    # 執行 pin: _ELITE_LIVE は空集合 (all-pairs bypass 廃止)、全 3 セルが
    # _PAIR_DEMOTED。fill 済みでも write-path は shadow を強制する。
    # (旧 test は trendline_sweep×EUR_USD を ELITE_LIVE の代表例として
    # 「fill 前 shadow / fill 後 live」を pin していた — その意味論は
    # test_pair_promoted_filled_can_be_live_but_blocked_remains_shadow が
    # PAIR_PROMOTED セルで引き続きカバーする。)
    assert DemoTrader._ELITE_LIVE == set()
    for pair in ("EUR_USD", "GBP_USD", "EUR_GBP"):
        assert trader._resolve_tier("trendline_sweep", pair, "daytrade") == "PAIR_DEMOTED"
        assert trader._resolve_is_shadow_for_write(
            "trendline_sweep",
            pair,
            "daytrade",
            bridge_status="filled",
            oanda_trade_id="OANDA-123",
        )


def test_pair_promoted_filled_can_be_live_but_blocked_remains_shadow(trader):
    entry_type, instrument = next(iter(trader._PAIR_PROMOTED))
    assert trader._resolve_tier(entry_type, instrument, "scalp") == "PAIR_PROMOTED"
    assert not trader._resolve_is_shadow_for_write(
        entry_type,
        instrument,
        "scalp",
        bridge_status="filled",
        oanda_trade_id="OANDA-PAIR",
    )
    assert trader._resolve_is_shadow_for_write(
        entry_type,
        instrument,
        "scalp",
        bridge_status="blocked",
        oanda_trade_id="",
    )
