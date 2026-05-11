"""runner: integration of cursor → fetch → replay → persist → advance."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from cfd_trader.audit.oanda_audit import init_db
from cfd_trader.audit.queries import count_shadow
from cfd_trader.shadow.runner import run_shadow_cycle
from cfd_trader.shadow.state import init_state_table, get_cursor

import cfd_trader.strategies.ported.orb_ny_open_short  # registers strategy  # noqa: F401


def _make_breakdown_day() -> pd.DataFrame:
    times = pd.to_datetime(
        pd.date_range("2026-05-11T14:30:00Z", periods=90, freq="5min", tz="UTC")
    )
    closes = [5005.0] * 6 + [4998.0] + [4995.0] * 83
    df = pd.DataFrame({
        "time": times, "open": closes,
        "high": [c + 1.0 for c in closes], "low": [c - 1.0 for c in closes],
        "close": closes, "volume": [10] * 90, "complete": [True] * 90,
    })
    for i in range(6):
        df.at[i, "high"] = 5010.0
        df.at[i, "low"]  = 5000.0
        df.at[i, "close"] = 5005.0
    return df


def test_run_shadow_cycle_writes_audit_and_advances_cursor(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    n_new = run_shadow_cycle(
        db_path=str(db),
        oanda_client=fake_client,
        instrument="SPX500_USD",
        granularity="M5",
        strategy_name="orb_ny_open_short",
        bonferroni_m=2,
        selection_reason="short_only_post_hoc",
    )
    assert n_new == 1
    assert count_shadow(str(db), strategy_name="orb_ny_open_short") == 1
    cursor = get_cursor(str(db), "orb_ny_open_short")
    assert cursor is not None
    assert "2026-05-11" in cursor


def test_run_shadow_cycle_is_idempotent_no_new_candles(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
    )
    # Simulate "no new candles since cursor" on the second call:
    fake_client.get_candles.return_value = pd.DataFrame(columns=[
        "time","open","high","low","close","volume","complete",
    ])
    n_new_2 = run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
    )
    assert n_new_2 == 0
    assert count_shadow(str(db), strategy_name="orb_ny_open_short") == 1
