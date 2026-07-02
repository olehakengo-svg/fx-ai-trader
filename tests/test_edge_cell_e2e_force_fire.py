from __future__ import annotations

import sys
from pathlib import Path

from modules import data as data_mod

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader, session_time_bias_sell_sig


def test_e2e_e8_disabled_force_fire_stays_shadow(monkeypatch, tmp_path):
    """E8 は 2026-06-25 (rule:R2) で code-level DISABLED — force-fire 経路の e2e 検証。

    かつては seed で live slot が埋まっていても E8 force-live override が
    5000u × 5 連射で OANDA に到達していた。DISABLED_CELLS 化後は override が
    外れ、シグナルは shadow に落ちる (OANDA 送信ゼロ)。shadow slot 上限
    (2/mode/pair) が今は通常適用されるため、5 連射のうち 2 件が shadow row、
    残り 3 件は max_per_mode_pair block になる。edge_cell_id タグは match
    適格性基準で付与され続ける (watchdog 可視性 + shadow N 蓄積,
    fable5 audit 2026-07-02 P1-4)。
    ref: knowledge-base/wiki/decisions/edge-cell-e8-demote-2026-06-25.md
    """
    prices = [1.1000, 1.1007, 1.1014, 1.1021, 1.1028]
    current = {"price": prices[0]}

    def _bid_ask(_instrument):
        price = current["price"]
        return {"bid": price, "ask": price + 0.0001}

    import hashlib

    class _FakeMD5:
        def hexdigest(self):
            return "00000001"

    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", _bid_ask)
    monkeypatch.setattr(hashlib, "md5", lambda *_args, **_kwargs: _FakeMD5())
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)

    trader._db.open_trade(
        direction="SELL",
        entry_price=1.2000,
        sl=1.2015,
        tp=1.1985,
        entry_type="seed_live",
        confidence=99,
        tf="15m",
        reasons=["seed live slot"],
        mode="daytrade",
        instrument="EUR_USD",
        is_shadow=False,
        oanda_trade_id="seed-oanda",
    )

    for price in prices:
        current["price"] = price
        trader._tick_entry(
            "daytrade",
            edge_cfg(),
            session_time_bias_sell_sig(price),
            "15m",
            "EUR_USD",
        )

    with trader._db._safe_conn() as conn:
        rows = conn.execute(
            """
            SELECT edge_cell_id, is_shadow, oanda_trade_id
            FROM demo_trades
            WHERE edge_cell_id = 'E8'
            ORDER BY id
            """
        ).fetchall()

    assert len(rows) == 2
    assert all(row["is_shadow"] == 1 for row in rows)
    assert all(not row["oanda_trade_id"] for row in rows)
    assert trader._block_counts["daytrade:max_per_mode_pair"] == 3
    assert not trader._oanda.calls
    assert not any("[EDGE_CELL] E8 shadow→live force override" in log for log in logs), logs
