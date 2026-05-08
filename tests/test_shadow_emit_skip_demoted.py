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
    emits = [{"entry_type": "engulfing_bb", "signal": "BUY"}]

    assert _filter_shadow_emits(emits, "EUR_USD") == emits


def test_pair_promoted_sr_fib_gbpusd_is_not_shadow_demoted():
    emits = [{"entry_type": "sr_fib_confluence", "signal": "BUY"}]

    assert _filter_shadow_emits(emits, "GBP_USD") == emits


def test_demo_trader_shadow_emit_path_calls_demote_registry():
    source = __import__("pathlib").Path("modules/demo_trader.py").read_text()

    assert "from modules.shadow_demote_registry import is_shadow_demoted" in source
    assert "if is_shadow_demoted(_se_entry_type, instrument):" in source
    assert "if is_shadow_demoted(entry_type, instrument) and not _is_live_tier_exempt:" in source
