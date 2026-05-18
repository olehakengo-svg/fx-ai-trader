from __future__ import annotations

from tools.prime_v2_shadow_audit import (
    STRATEGIES,
    analyze,
    bonferroni_alpha,
    total_hypothesis_count,
)


def _trade(strategy: str, idx: int, outcome: str = "WIN") -> dict:
    return {
        "id": idx,
        "entry_type": strategy,
        "instrument": "USD_JPY",
        "is_shadow": 1,
        "outcome": outcome,
        "direction": "BUY" if idx % 2 == 0 else "SELL",
        "entry_time": f"2026-05-{1 + idx % 17:02d}T10:00:00+00:00",
        "entry_price": 150.00,
        "exit_price": 150.08 if outcome == "WIN" else 149.96,
        "spread_at_entry": 0.2,
        "slippage_pips": 0.0,
        "regime": '{"adx": 25.0, "atr_ratio": 1.0, "close_vs_ema200": 0.01}',
        "confidence": 60,
    }


def _sample_rows() -> list[dict]:
    rows = []
    idx = 1
    for strategy in STRATEGIES:
        for i in range(12):
            rows.append(_trade(strategy, idx, "WIN" if i < 7 else "LOSS"))
            idx += 1
    return rows


def test_total_hypothesis_count_at_most_30():
    result = analyze(_sample_rows())
    assert total_hypothesis_count(result["cells_by_strategy"]) <= 30


def test_each_strategy_at_most_5_cells():
    result = analyze(_sample_rows())
    assert all(len(cells) <= 5 for cells in result["cells_by_strategy"].values())


def test_bonferroni_alpha_matches_m_total():
    result = analyze(_sample_rows())
    assert result["alpha"] == 0.05 / result["m_total"]
    assert bonferroni_alpha(result["m_total"]) == result["alpha"]
