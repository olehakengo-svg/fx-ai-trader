from modules.shadow_demote_registry import is_shadow_demoted


def _filter_shadow_emits(shadow_emits, instrument):
    return [
        emit for emit in shadow_emits
        if not is_shadow_demoted(emit.get("entry_type", ""), instrument)
    ]


def test_demoted_shadow_emit_cell_is_removed():
    emits = [
        {"entry_type": "engulfing_bb", "signal": "BUY"},
        {"entry_type": "engulfing_bb", "signal": "SELL"},
    ]

    assert _filter_shadow_emits(emits, "USD_JPY") == []


def test_non_demoted_pair_still_emits():
    # engulfing_bb x GBP_USD joined the demoted set in the 2026-08-10 R2
    # batch (N-crossing type), so engulfing_bb has no still-emitting cell
    # left. The per-cell stop must nonetheless stay per-cell: a strategy
    # with a healthy pair keeps emitting there.
    # (dt_sr_channel_reversal x USD_JPY: WARN in the 08-10 alert, below the
    # CRITICAL demote gate.)
    emits = [{"entry_type": "dt_sr_channel_reversal", "signal": "BUY"}]

    assert _filter_shadow_emits(emits, "USD_JPY") == emits


def test_demoted_xs_momentum_cells_stop_but_rsi_variant_survives():
    # 2026-08-10 R2 batch: xs_momentum x GBP_USD / USD_JPY demoted. The
    # registry key is (entry_type, instrument), so the live PAIR_PROMOTED
    # variant xs_momentum_rsi x USD_JPY is a different entry_type and must
    # not be caught by the cell stop.
    assert _filter_shadow_emits(
        [{"entry_type": "xs_momentum", "signal": "BUY"}], "GBP_USD"
    ) == []
    assert _filter_shadow_emits(
        [{"entry_type": "xs_momentum", "signal": "BUY"}], "USD_JPY"
    ) == []

    rsi = [{"entry_type": "xs_momentum_rsi", "signal": "BUY"}]
    assert _filter_shadow_emits(rsi, "USD_JPY") == rsi


def test_retired_sr_fib_gbpusd_is_shadow_demoted():
    # 2026-06-12 Edge Factor Audit #5: sr_fib_confluence fully retired
    # (SHADOW_RETIRED_STRATEGIES) and demoted from _PAIR_PROMOTED. The cell
    # that was previously promotion-exempt on GBP_USD is now blocked.
    emits = [{"entry_type": "sr_fib_confluence", "signal": "BUY"}]

    assert _filter_shadow_emits(emits, "GBP_USD") == []


def test_demo_trader_shadow_emit_path_calls_demote_registry():
    source = __import__("pathlib").Path("modules/demo_trader.py").read_text()

    assert "from modules.shadow_demote_registry import is_shadow_demoted" in source
    assert "if is_shadow_demoted(_se_entry_type, instrument):" in source
    assert "if is_shadow_demoted(entry_type, instrument) and not _is_live_tier_exempt:" in source
