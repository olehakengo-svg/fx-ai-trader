from __future__ import annotations

import sys
from pathlib import Path

from modules import data as data_mod
from modules.shadow_demote_registry import is_shadow_demoted as is_shadow_demoted_real

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader, session_time_bias_sell_sig


def _sell_sig(entry_type: str, *, entry: float):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": entry_type,
        "confidence": 70,
        "score": -1.0,
        "sl": entry + 0.0015,
        "tp": entry - 0.0030,
        "atr": 0.0010,
        "reasons": [f"✅ edge-cell real block path {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _set_price_feed(monkeypatch, current):
    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _instrument: {
            "bid": current["price"],
            "ask": current["price"] + 0.0001,
        },
    )


def _edge_rows(db, cell_id: str):
    with db._safe_conn() as conn:
        return conn.execute(
            """
            SELECT edge_cell_id, is_shadow, oanda_trade_id
            FROM demo_trades
            WHERE edge_cell_id = ?
            ORDER BY id
            """,
            (cell_id,),
        ).fetchall()


def test_e2e_edge_cells_bypass_real_r2_and_same_price_blocks(monkeypatch, tmp_path):
    import hashlib

    import modules.demo_trader as demo_trader_mod

    class _FakeMD5:
        def hexdigest(self):
            return "00000001"

    monkeypatch.setattr(hashlib, "md5", lambda *_args, **_kwargs: _FakeMD5())

    current = {"price": 1.1000}
    _set_price_feed(monkeypatch, current)

    # R2 bypass 経路は元々 E4 (bb_rsi_reversion NY SELL) で検証していたが、E4 は
    # 2026-07-02 (rule:R2) で code-level DISABLED (edge-cell-e1-e4-code-disable-
    # 2026-07-02.md)。現行 registry には「shadow demoted かつ active cell」の実在
    # 組合せが無いため、registry を合成して active cell E3 (dt_bb_rsi_mr EUR_USD
    # SELL) で 5-tick 実ブロック経路を維持する。
    e3_trader, e3_logs = make_trader(tmp_path, monkeypatch, hour=8)
    monkeypatch.setattr(
        demo_trader_mod,
        "is_shadow_demoted",
        lambda strategy, instrument: (strategy, instrument) == ("dt_bb_rsi_mr", "EUR_USD"),
    )
    e3_prices = [1.1000, 1.1007, 1.1014, 1.1021, 1.1028]
    for price in e3_prices:
        current["price"] = price
        # spike/velocity ガードの入力をリセット: same-price と両立する 5 連発
        # (>5pip 間隔 ×5 = 28pip レンジ) は 60s spike (>10pip) / velocity
        # (>15pip) を必ず踏む。bb_rsi (sentinel-eligible) は shadow bypass で
        # 抜けていたが dt_bb_rsi_mr は hard block されるため、検証対象の
        # R2/SAME_PRICE 経路だけを通す。
        e3_trader._price_history.clear()
        e3_trader._tick_entry(
            "daytrade",
            edge_cfg(),
            _sell_sig("dt_bb_rsi_mr", entry=price),
            "15m",
            "EUR_USD",
        )

    e3_rows = _edge_rows(e3_trader._db, "E3")
    assert len(e3_rows) == 5
    assert all(row["is_shadow"] == 0 for row in e3_rows)
    assert all(row["oanda_trade_id"] for row in e3_rows)
    assert sum("[R2_SHADOW_DEMOTE] edge cell E3 bypass" in log for log in e3_logs) == 5
    assert sum("[EDGE_CELL] E3 shadow→live force override" in log for log in e3_logs) == 5
    # 合成 registry を実 registry に戻す (後半の E8 セクションは実 registry 前提)
    monkeypatch.setattr(demo_trader_mod, "is_shadow_demoted", is_shadow_demoted_real)

    e8_dir = tmp_path / "e8"
    e8_dir.mkdir()
    e8_trader, e8_logs = make_trader(e8_dir, monkeypatch, hour=8)
    e8_trader._db.open_trade(
        direction="SELL",
        entry_price=1.1000,
        sl=1.2500,
        tp=1.0900,
        entry_type="seed_live",
        confidence=99,
        tf="15m",
        reasons=["same price seed"],
        mode="daytrade",
        instrument="EUR_USD",
        is_shadow=False,
        oanda_trade_id="seed-oanda",
    )

    e8_prices = [1.1000, 1.10025, 1.10050, 1.10075, 1.10100]
    for price in e8_prices:
        current["price"] = price
        e8_trader._tick_entry(
            "daytrade",
            edge_cfg(),
            session_time_bias_sell_sig(price),
            "15m",
            "EUR_USD",
        )

    # E8 は 2026-06-25 (rule:R2) で code-level DISABLED — pre-block eligibility
    # (lot>0) を失い、SAME_PRICE ブロックが通常どおり効く (bypass ログなし)。
    # seed(1.1000) から 7.5pip 離れた 1.10075 の 1 tick だけが閾値(~5pip)を
    # 抜けて shadow row になる (E8 タグは match 適格性基準で残る、OANDA 送信なし)。
    # ref: knowledge-base/wiki/decisions/edge-cell-e8-demote-2026-06-25.md
    e8_rows = _edge_rows(e8_trader._db, "E8")
    assert len(e8_rows) == 1
    assert e8_rows[0]["is_shadow"] == 1
    assert not e8_rows[0]["oanda_trade_id"]
    assert e8_trader._block_counts["daytrade:same_price_0pip"] == 4
    assert not any("[SAME_PRICE] edge cell E8 bypass" in log for log in e8_logs)
    assert not any("[EDGE_CELL] E8 shadow→live force override" in log for log in e8_logs)
