from __future__ import annotations

import pytest

from tools import regime_gate_full_bt as rg


def _trade(entry_type: str, outcome: str, regime: str = "TRENDING", value: float = 1.0) -> dict:
    return {
        "pair": "USDJPY",
        "entry_type": entry_type,
        "entry_time": "2026-01-01 12:00:00+00:00",
        "outcome": outcome,
        "regime": regime,
        "tp_m": value if outcome == "WIN" else 0.0,
        "sl_m": value if outcome == "LOSS" else 1.0,
    }


def test_catastrophic_rules_fire_for_sign_flip_and_low_n() -> None:
    baseline = rg.compute_kpi([_trade("fam", "WIN", value=1.0) for _ in range(40)])
    sign_flip = rg.compute_kpi([_trade("fam", "LOSS", value=1.0) for _ in range(40)])
    low_n = rg.compute_kpi([_trade("fam", "WIN", value=1.0) for _ in range(29)])

    assert rg.catastrophic_verdict(baseline, sign_flip) == (
        "CATASTROPHIC",
        "pnl_sign_flip",
    )
    assert rg.catastrophic_verdict(baseline, low_n) == (
        "CATASTROPHIC",
        "gate_N_lt_30",
    )
    # NOTE: pf_extreme_drop は PF<0.5 が PnL<0 を必然的に含意するため pnl_sign_flip
    # の前で必ず捕捉される。司令塔 next-action でルール統合 or 削除検討。


def test_baseline_negative_no_edge_rejects_all_gates() -> None:
    baseline = rg.compute_kpi([_trade("engulfing_bb", "LOSS", value=1.0) for _ in range(40)])
    gate = rg.compute_kpi([_trade("engulfing_bb", "WIN", value=1.0) for _ in range(40)])

    assert rg.catastrophic_verdict(baseline, gate) == (
        "CATASTROPHIC",
        "baseline_negative_no_edge",
    )


def test_tag_trades_adds_regime_from_classifier_mock() -> None:
    trades = [{"entry_type": "fam", "entry_time": "2026-01-01 12:00:00+00:00"}]

    tagged = rg.tag_trades("USDJPY=X", trades, classifier=lambda instrument, ts: "RANGING")

    assert tagged[0]["pair"] == "USDJPY"
    assert tagged[0]["regime"] == "RANGING"


def test_build_outputs_creates_shadow_proposals_only_for_not_catastrophic() -> None:
    trades = (
        [_trade("fam", "WIN", "TRENDING", value=1.0) for _ in range(35)]
        + [_trade("fam", "WIN", "RANGING", value=1.0) for _ in range(35)]
        + [_trade("bad", "LOSS", "TRENDING", value=1.0) for _ in range(35)]
        + [_trade("bad", "WIN", "RANGING", value=1.0) for _ in range(35)]
    )

    outputs = rg.build_output_tables(trades, family_universe=["fam", "bad", "missing"])

    proposal_names = {row["proposal"] for row in outputs.shadow_proposals}
    assert "fam__regime_TRENDING" in proposal_names
    assert "fam__regime_RANGING" in proposal_names
    assert not any(name.startswith("bad__") for name in proposal_names)
    assert outputs.zero_trade_families == [{"entry_type": "missing", "N": 0}]


def test_integration_usdjpy_30d_real_bt_tags_entry_type_and_regime() -> None:
    result = rg.run_pair_bt("USDJPY=X", lookback_days=30)
    if result.get("error") and result.get("trades", 0) == 0:
        pytest.fail(f"USDJPY 30d BT failed before tagging: {result.get('error')}")

    tagged = rg.tag_trades("USDJPY=X", result.get("trade_log", [])[:10])

    assert tagged
    assert all(t.get("entry_type") for t in tagged)
    assert all("regime" in t for t in tagged)
