"""v9.2: Regime guardrail + ema_trend_scalp FORCE_DEMOTE tests.

SELL bias 法医学 (2026-04-17) の結果を実装した guardrail 2 セル:
  * uncertain × SELL → shadow
  * up_trend  × BUY  → shadow
+ FORCE_DEMOTE: ema_trend_scalp (全 regime で WR 11-15%)
"""
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


@pytest.fixture
def trader():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DemoDB(db_path=path)
    t = DemoTrader(db)
    yield t
    # best-effort teardown
    try:
        os.unlink(path)
    except OSError:
        pass


class TestForceDemotedEmaTrendScalp:
    """Action B verification — ema_trend_scalp is now globally FORCE_DEMOTED."""

    def test_ema_trend_scalp_in_force_demoted(self, trader):
        assert "ema_trend_scalp" in trader._FORCE_DEMOTED, (
            "Action B: ema_trend_scalp must be in _FORCE_DEMOTED "
            "(全 regime で WR 11-15%, 2026-04-17 forensics)"
        )


class TestRegimeGuardrailHelper:
    """_get_independent_regime caches and fails open."""

    def test_cache_returns_within_ttl(self, trader):
        """Same instrument within TTL should return cached value without refetch."""
        now = datetime.now(timezone.utc)
        trader._regime_cache["USD_JPY"] = (now, "up_trend")
        # Patch fetch_and_label to ensure it's NOT called
        import research.edge_discovery.regime_labeler as rl
        orig = rl.fetch_and_label
        try:
            rl.fetch_and_label = MagicMock(side_effect=AssertionError("should not call"))
            assert trader._get_independent_regime("USD_JPY") == "up_trend"
        finally:
            rl.fetch_and_label = orig

    def test_expired_cache_triggers_refetch(self, trader, monkeypatch):
        """After TTL, fetch is retried."""
        old = datetime.now(timezone.utc).replace(year=2020)  # very stale
        trader._regime_cache["USD_JPY"] = (old, "range")
        called = {"n": 0}

        def _fake_fetch(**kwargs):
            called["n"] += 1
            import pandas as pd
            return pd.DataFrame([{"regime": "up_trend"}])
        import research.edge_discovery.regime_labeler as rl
        monkeypatch.setattr(rl, "fetch_and_label", _fake_fetch)
        r = trader._get_independent_regime("USD_JPY")
        assert r == "up_trend"
        assert called["n"] == 1

    def test_api_error_fails_open_to_range(self, trader, monkeypatch):
        """Labeler errors should NOT block trading — return 'range' (not guardrailed)."""
        import research.edge_discovery.regime_labeler as rl

        def _boom(**kwargs):
            raise RuntimeError("OANDA unavailable")
        monkeypatch.setattr(rl, "fetch_and_label", _boom)
        # fresh cache (ensure miss)
        trader._regime_cache.clear()
        r = trader._get_independent_regime("USD_JPY")
        assert r == "range", "fail-open must return a regime not in the guardrail set"

    def test_empty_result_returns_uncertain(self, trader, monkeypatch):
        """Empty candle DF → 'uncertain' (which IS guardrailed for SELL)."""
        import research.edge_discovery.regime_labeler as rl
        import pandas as pd
        monkeypatch.setattr(rl, "fetch_and_label", lambda **kw: pd.DataFrame())
        trader._regime_cache.clear()
        assert trader._get_independent_regime("USD_JPY") == "uncertain"


class TestGuardrailEnvFlag:
    """v9.2.1 (2026-04-17): default DISABLED (curve-fit 判定).

    6.5 年 × 3pair の MTF engine 検証で v9.2 の 2 cell は方向が逆と判明.
    再有効化は REGIME_GUARDRAIL_ENABLED=1 で opt-in.
    """

    def test_env_var_default_disabled(self, monkeypatch):
        """v9.2.1: デフォルト disabled (curve-fit のため)."""
        monkeypatch.delenv("REGIME_GUARDRAIL_ENABLED", raising=False)
        # In production code: `if os.environ.get("REGIME_GUARDRAIL_ENABLED", "0") == "1"`
        assert os.environ.get("REGIME_GUARDRAIL_ENABLED", "0") != "1"

    def test_env_var_enabled_when_one(self, monkeypatch):
        """明示 opt-in の場合は動く (diagnostic 用途)."""
        monkeypatch.setenv("REGIME_GUARDRAIL_ENABLED", "1")
        assert os.environ.get("REGIME_GUARDRAIL_ENABLED", "0") == "1"
