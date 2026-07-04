"""P0-1 (fable5 audit, user 決裁 2026-07-03, rule:R2): edge cell force-live の
pre-reg LOCK 固定 lot に DD defensive multiplier を適用する回帰テスト。

修正前は `_adjusted_units = _edge_cell_lot` の生値代入で、DD defensive 0.2x
下でも stage3 セルが 10000u フルサイズを送信していた (監査 P0-1)。修正後は
`max(1000, int(lot * _dd_lot_mult))` — 口座防御を優先しつつ min 1000u floor
でクリーン N 蓄積は継続する。

ref: knowledge-base/wiki/decisions/fable5-phase-a-p0-fixes-2026-07-03.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader


def _dt_bb_rsi_mr_sell_sig(entry: float = 1.1000):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": "dt_bb_rsi_mr",
        "confidence": 70,
        "score": -1.0,
        "sl": entry + 0.0015,
        "tp": entry - 0.0030,
        "atr": 0.0010,
        "reasons": ["✅ edge-cell E3 DD defensive units test"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _make_dd_trader(tmp_path, monkeypatch, *, dd_lot_mult: float, stage: str | None = None):
    from modules import data as data_mod

    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)
    monkeypatch.setattr(
        data_mod, "fetch_oanda_bid_ask", lambda _inst: {"bid": 1.1000, "ask": 1.1001}
    )
    trader._dd_lot_mult = dd_lot_mult
    trader._defensive_mode = dd_lot_mult < 1.0
    if stage is not None:
        trader._db.set_system_kv("edge_cell_stage:E3", stage)
    return trader, logs


def _latest_trade(db):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT edge_cell_id, is_shadow, oanda_trade_id FROM demo_trades "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()


@pytest.mark.parametrize(
    "case_name,dd_lot_mult,stage,expected_units",
    [
        # stage1 (5000u) × DD 0.2x = 1000u
        ("stage1_dd020", 0.2, None, 1000),
        # stage3 (10000u) × DD 0.2x = 2000u — 監査 P0-1 の主対象ケース
        ("stage3_dd020", 0.2, "3", 2000),
        # floor: stage1 (5000u) × 0.1 = 500u → floor 1000u
        ("stage1_floor_binds", 0.1, None, 1000),
        # 非 defensive (mult=1.0) は従来どおりフルサイズ
        ("stage1_no_dd", 1.0, None, 5000),
        ("stage3_no_dd", 1.0, "3", 10000),
    ],
)
def test_edge_cell_units_respect_dd_lot_multiplier(
    monkeypatch, tmp_path, case_name, dd_lot_mult, stage, expected_units
):
    trader, logs = _make_dd_trader(
        tmp_path, monkeypatch, dd_lot_mult=dd_lot_mult, stage=stage
    )

    trader._tick_entry("daytrade", edge_cfg(), _dt_bb_rsi_mr_sell_sig(), "15m", "EUR_USD")

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == "E3", case_name
    assert row["is_shadow"] == 0, case_name
    assert row["oanda_trade_id"], case_name
    assert trader._oanda.calls, case_name
    assert trader._oanda.calls[-1]["units"] == expected_units, case_name


def test_dd_defensive_sizing_is_logged(monkeypatch, tmp_path):
    """縮小時は [EDGE_CELL] DD defensive sizing ログで観測可能であること。"""
    trader, logs = _make_dd_trader(tmp_path, monkeypatch, dd_lot_mult=0.2, stage="3")

    trader._tick_entry("daytrade", edge_cfg(), _dt_bb_rsi_mr_sell_sig(), "15m", "EUR_USD")

    assert any(
        "[EDGE_CELL] E3 DD defensive sizing: pre-reg 10000u × 0.20 → 2000u" in log
        for log in logs
    ), logs


def test_no_dd_log_when_full_size(monkeypatch, tmp_path):
    """mult=1.0 では縮小ログを出さない (従来挙動の非回帰)。"""
    trader, logs = _make_dd_trader(tmp_path, monkeypatch, dd_lot_mult=1.0)

    trader._tick_entry("daytrade", edge_cfg(), _dt_bb_rsi_mr_sell_sig(), "15m", "EUR_USD")

    assert trader._oanda.calls[-1]["units"] == 5000
    assert not any("DD defensive sizing" in log for log in logs), logs
