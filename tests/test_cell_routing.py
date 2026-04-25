"""Unit tests for modules.cell_routing — EDGE.md runtime loader."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.cell_routing import (  # noqa: E402
    get_routing,
    get_lot_multiplier,
    load_routing,
    routing_summary,
)


@pytest.fixture
def temp_routing_table(tmp_path):
    """Create a temporary routing_table.json for testing."""
    def _make(block=None, kelly_half=None, kelly_full=None):
        data = {
            "version": "0.1",
            "classifier": "v6",
            "generated_at": "2026-04-26T00:00:00Z",
            "source": "test",
            "edges_count": (len(block or []) + len(kelly_half or [])
                            + len(kelly_full or [])),
            "block": block or [],
            "kelly_half": kelly_half or [],
            "kelly_full": kelly_full or [],
        }
        path = tmp_path / "routing_table.json"
        path.write_text(json.dumps(data))
        return path
    return _make


def test_empty_table_returns_none(temp_routing_table):
    path = temp_routing_table()
    load_routing(path, force=True)
    assert get_routing("any_strategy", "USD_JPY", "R1__V_high__NY",
                      path=path) == "NONE"


def test_block_match(temp_routing_table):
    path = temp_routing_table(
        block=[["ema_trend_scalp", "R2_trend_down__V_high__NY"]],
    )
    load_routing(path, force=True)
    assert get_routing("ema_trend_scalp", "USD_JPY",
                      "R2_trend_down__V_high__NY", path=path) == "BLOCK"


def test_block_does_not_leak_to_other_cell(temp_routing_table):
    path = temp_routing_table(
        block=[["ema_trend_scalp", "R2_trend_down__V_high__NY"]],
    )
    load_routing(path, force=True)
    assert get_routing("ema_trend_scalp", "USD_JPY",
                      "R6_reversal__V_low__Off", path=path) == "NONE"


def test_kelly_half_returns_routing(temp_routing_table):
    path = temp_routing_table(
        kelly_half=[["bb_rsi_reversion", "R6_reversal__V_high__NY", 0.5]],
    )
    load_routing(path, force=True)
    assert get_routing("bb_rsi_reversion", "USD_JPY",
                      "R6_reversal__V_high__NY", path=path) == "KELLY_HALF"
    assert get_lot_multiplier("bb_rsi_reversion", "USD_JPY",
                              "R6_reversal__V_high__NY", path=path) == 0.5


def test_kelly_full_returns_routing(temp_routing_table):
    path = temp_routing_table(
        kelly_full=[["fib_reversal", "R5_breakout__V_mid__Asia", 1.0]],
    )
    load_routing(path, force=True)
    assert get_routing("fib_reversal", "USD_JPY",
                      "R5_breakout__V_mid__Asia", path=path) == "KELLY_FULL"
    assert get_lot_multiplier("fib_reversal", "USD_JPY",
                              "R5_breakout__V_mid__Asia", path=path) == 1.0


def test_empty_inputs_return_none(temp_routing_table):
    path = temp_routing_table(
        block=[["ema_trend_scalp", "R2_trend_down__V_high__NY"]],
    )
    load_routing(path, force=True)
    assert get_routing("", "USD_JPY", "R2_trend_down__V_high__NY",
                      path=path) == "NONE"
    assert get_routing("ema_trend_scalp", "USD_JPY", "", path=path) == "NONE"
    assert get_routing("ema_trend_scalp", "USD_JPY", None, path=path) == "NONE"


def test_lot_multiplier_default_one_for_block(temp_routing_table):
    """BLOCK does not contribute a multiplier; caller short-circuits."""
    path = temp_routing_table(
        block=[["ema_trend_scalp", "R2_trend_down__V_high__NY"]],
    )
    load_routing(path, force=True)
    # get_lot_multiplier looks at kelly_* tables, BLOCK gives default 1.0
    assert get_lot_multiplier("ema_trend_scalp", "USD_JPY",
                              "R2_trend_down__V_high__NY", path=path) == 1.0


def test_missing_file_fail_open(tmp_path):
    """If routing_table.json is missing, all queries return NONE without error."""
    missing = tmp_path / "no-such.json"
    assert get_routing("anything", "USD_JPY", "R1__V_low__Asia",
                      path=missing) == "NONE"


def test_summary_reports_counts(temp_routing_table):
    path = temp_routing_table(
        block=[["a", "R1_trend_up__V_low__Asia"]],
        kelly_half=[["b", "R2_trend_down__V_mid__London", 0.5]],
    )
    load_routing(path, force=True)
    s = routing_summary(path=path)
    assert s["block"] == 1
    assert s["kelly_half"] == 1
    assert s["kelly_full"] == 0
