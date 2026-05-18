from __future__ import annotations

from pathlib import Path

import pandas as pd


MASSIVE = Path("data/cache/massive")

H1_SHADOW_STRATEGIES = frozenset({
    "keltner_squeeze_breakout",
    "donchian_momentum_breakout",
})

H1_AUTO_START_MODES = (
    "daytrade_1h",
    "daytrade_1h_eur",
    "daytrade_1h_eurgbp",
    "daytrade_1h_audjpy",
    "daytrade_1h_nzdjpy",
    "daytrade_1h_audusd",
    "daytrade_1h_nzdusd",
    "daytrade_1h_euraud",
    "daytrade_1h_usdcad",
    "daytrade_1h_usdchf",
)


def _read_massive(pair: str) -> pd.DataFrame:
    path = MASSIVE / f"{pair}_1h.parquet"
    assert path.exists(), f"MASSIVE {pair} H1 parquet is required"
    return pd.read_parquet(path)


def _symbol(pair: str) -> str:
    return f"{pair.replace('_', '')}=X"


def _ctx_from_df(df: pd.DataFrame, pair: str):
    from strategies.context import SignalContext

    row = df.iloc[-1]
    return SignalContext.from_df(
        df,
        row,
        symbol=_symbol(pair),
        tf="1h",
        sr_levels=[],
        layer0={},
        layer1={},
        regime={},
        layer2={},
        layer3={},
        htf={"agreement": "mixed", "d1_ema50_falling": False},
        session={},
        backtest_mode=True,
        bar_time=df.index[-1],
    )


def _first_price_shock_context(pair: str, strategy_cls):
    from app import add_indicators

    raw = _read_massive(pair)
    strat = strategy_cls()
    positions = strat.signal_mask_from_dataframe(raw).to_numpy().nonzero()[0]
    assert len(positions) > 0, f"{pair}: real MASSIVE data must contain a Price-Shock trigger"
    df = add_indicators(raw.iloc[: int(positions[0]) + 1].copy())
    return _ctx_from_df(df, pair)


def test_hourly_engine_shadow_always_contains_all_h1_shadow_ramp_strategies():
    from strategies.hourly import HourlyEngine
    from modules.demo_trader import PRICE_SHOCK_REV_TIER1_TYPES

    assert isinstance(HourlyEngine._shadow_always, frozenset)
    assert H1_SHADOW_STRATEGIES <= HourlyEngine._shadow_always
    assert PRICE_SHOCK_REV_TIER1_TYPES.isdisjoint(HourlyEngine._shadow_always)


def test_hourly_modes_auto_start_enabled_without_touching_xau_modes():
    from modules.demo_trader import MODE_CONFIG

    for mode in H1_AUTO_START_MODES:
        assert MODE_CONFIG[mode]["signal_fn"] == "compute_hourly_signal"
        assert MODE_CONFIG[mode]["tf"] == "1h"
        assert MODE_CONFIG[mode]["auto_start"] is True

    assert MODE_CONFIG["scalp_xau"]["auto_start"] is False
    assert MODE_CONFIG["daytrade_xau"]["auto_start"] is False


def test_real_price_shock_candidate_uses_single_best_live_emit_path():
    from strategies.hourly import HourlyEngine
    from strategies.hourly.price_shock_rev_aud_jpy_h1_long import PriceShockRevAudJpyH1Long

    engine = HourlyEngine()
    ctx = _first_price_shock_context("AUD_JPY", PriceShockRevAudJpyH1Long)
    candidates = engine.evaluate_all(ctx)
    best = engine.select_best(candidates)
    shadow_emits = engine.split_shadow_always(candidates, best)

    assert candidates
    assert best is not None
    assert best.entry_type.startswith("price_shock_rev_")
    assert best.entry_type not in engine._shadow_always
    assert best.entry_type not in {c.entry_type for c in shadow_emits}


def test_aud_jpy_pair_filtering_observed_on_real_h1_data():
    from strategies.hourly import HourlyEngine
    from strategies.hourly.price_shock_rev_aud_jpy_h1_long import PriceShockRevAudJpyH1Long

    engine = HourlyEngine()
    ctx = _first_price_shock_context("AUD_JPY", PriceShockRevAudJpyH1Long)
    names = {c.entry_type for c in engine.evaluate_all(ctx)}

    target_names = {
        "keltner_squeeze_breakout",
        "donchian_momentum_breakout",
        "price_shock_rev_aud_jpy_h1_long",
    }
    observed = names & target_names

    assert "price_shock_rev_aud_jpy_h1_long" in observed
    assert "keltner_squeeze_breakout" not in observed
    assert observed <= {"donchian_momentum_breakout", "price_shock_rev_aud_jpy_h1_long"}
    assert 1 <= len(observed) <= 2


def test_demo_trader_can_start_audjpy_hourly_auto_mode(tmp_path):
    from modules.demo_db import DemoDB
    from modules.demo_trader import DemoTrader, MODE_CONFIG

    db = DemoDB(str(tmp_path / "demo_trader_h1_shadow_ramp.db"))
    trader = DemoTrader(db)
    try:
        assert MODE_CONFIG["daytrade_1h_audjpy"]["auto_start"] is True
        result = trader.start("daytrade_1h_audjpy")
        assert result["status"] in {"started", "already_running"}
        assert "daytrade_1h_audjpy" in trader._started_modes
        assert trader._runners["daytrade_1h_audjpy"]["running"] is True
    finally:
        trader.stop("daytrade_1h_audjpy")
