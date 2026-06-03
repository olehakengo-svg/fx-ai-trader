import json

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def test_sr_anti_hunt_shadow_emit_persists_cell_sr_mtf_spread_alpha(tmp_path):
    db = DemoDB(str(tmp_path / "sr-shadow-meta.db"))
    trader = DemoTrader(db)

    sr_entry_map = {
        "recommended": {
            "direction": "BUY",
            "entry": 170.12,
            "sl": 169.86,
            "tp": 170.72,
            "rr": 2.3,
            "ema_confidence": 74,
            "sr_basis": 170.04,
        }
    }
    alpha_snapshot = {"factors": {"alpha_001": 0.17}, "source": "unit"}

    trade_id = trader._open_shadow_emit_trade(
        direction="BUY",
        entry_price=170.12,
        sl=169.86,
        tp=170.72,
        entry_type="sr_anti_hunt_bounce",
        confidence=70,
        tf="15m",
        reasons=["[SHADOW_EMIT] sr anti hunt metadata regression"],
        score=3.0,
        mode="daytrade",
        instrument="EUR_JPY",
        sr_entry_map=sr_entry_map,
        signal_price=170.11,
        spread_at_entry=1.2,
        regime={"type": "RANGE"},
        layer1_dir="neutral",
        v2_regime="range",
        mtf_regime="mixed",
        mtf_d1_label=4,
        mtf_h4_label=2,
        mtf_vol_state="normal",
        gate_group="label_only",
        mtf_alignment="aligned",
        mtf_gate_action="kept",
        alpha_snapshot=alpha_snapshot,
    )

    with db._safe_conn() as conn:
        row = conn.execute(
            """
            SELECT sr_basis, edge_cell_id, alpha_snapshot, spread_at_entry,
                   mtf_alignment, mtf_d1_label, mtf_h4_label, mtf_vol_state,
                   regime, layer1_dir, ema_conf
            FROM demo_trades
            WHERE trade_id=?
            """,
            (trade_id,),
        ).fetchone()

    assert row is not None
    assert row["sr_basis"] == sr_entry_map["recommended"]["sr_basis"]
    assert row["edge_cell_id"] == "E12"
    assert json.loads(row["alpha_snapshot"]) == alpha_snapshot
    assert row["spread_at_entry"] == 1.2
    assert row["mtf_alignment"] == "aligned"
    assert row["mtf_d1_label"] == 4
    assert row["mtf_h4_label"] == 2
    assert row["mtf_vol_state"] == "normal"
    assert json.loads(row["regime"]) == {"type": "RANGE"}
    assert row["layer1_dir"] == "neutral"
    assert row["ema_conf"] == sr_entry_map["recommended"]["ema_confidence"]
