"""Seat-priority + feed-unification pins for the price_shock_rev supply fix.

Executes price-shock-seat-supply-audit-2026-07-29 §7 (a)+(c), user approved
2026-08-11. Root cause: HourlyEngine winner-take-all with asymmetric scores
(guest DMB/KSB base 5.0+ vs seat price_shock 1.0) silently dropped seat
candidates on crash bars (family supply ~31% of design).
"""
from __future__ import annotations

from pathlib import Path

from strategies.base import Candidate
from strategies.hourly import HourlyEngine
from strategies.hourly.price_shock_reversion_base import PriceShockReversionBase

ROOT = Path(__file__).resolve().parents[1]

PS_TYPES = {
    "price_shock_rev_eur_gbp_h1_long",
    "price_shock_rev_eur_aud_h1_long",
    "price_shock_rev_usd_cad_h1_long",
    "price_shock_rev_nzd_jpy_h1_long",
    "price_shock_rev_aud_jpy_h1_long",
}


def _cand(entry_type: str, score: float, signal: str = "BUY") -> Candidate:
    return Candidate(
        signal=signal, confidence=70, sl=1.0, tp=2.0,
        reasons=[], entry_type=entry_type, score=score,
    )


class TestSeatPrioritySelect:
    def test_seat_types_derived_from_instances(self):
        engine = HourlyEngine()
        assert engine._seat_priority_types() == frozenset(PS_TYPES), (
            "seat set drifted from the registered price_shock family"
        )

    def test_price_shock_beats_higher_scored_guest(self):
        # The exact race from the smoking gun (2026-07-20 14:00:48):
        # DMB SELL score=7.30 vs price_shock BUY score=1.0 on EUR_AUD.
        engine = HourlyEngine()
        dmb = _cand("donchian_momentum_breakout", 7.30, "SELL")
        ps = _cand("price_shock_rev_eur_aud_h1_long", 1.0, "BUY")
        best = engine.select_best([dmb, ps])
        assert best is ps, "seat candidate must own the primary emit"

    def test_displaced_guest_still_flows_to_shadow(self):
        # DMB is in _shadow_always: losing the primary emit must not cut
        # its shadow series (split_shadow_always returns non-best members).
        engine = HourlyEngine()
        dmb = _cand("donchian_momentum_breakout", 7.30, "SELL")
        ps = _cand("price_shock_rev_eur_aud_h1_long", 1.0, "BUY")
        best = engine.select_best([dmb, ps])
        shadows = engine.split_shadow_always([dmb, ps], best)
        assert dmb in shadows, "displaced DMB lost its shadow emit path"

    def test_no_seat_candidate_keeps_max_score(self):
        engine = HourlyEngine()
        dmb = _cand("donchian_momentum_breakout", 7.30, "SELL")
        ksb = _cand("keltner_squeeze_breakout", 5.0, "BUY")
        assert engine.select_best([dmb, ksb]) is dmb

    def test_empty_candidates(self):
        assert HourlyEngine().select_best([]) is None

    def test_seat_alone_unchanged(self):
        engine = HourlyEngine()
        ps = _cand("price_shock_rev_aud_jpy_h1_long", 1.0)
        assert engine.select_best([ps]) is ps


class TestShadowEmitScoreGateMirror:
    def test_mirror_active_in_shadow_emit_loop(self):
        # Guard-chain parity (audit §9 amendment): the shadow_emit path must
        # share the primary SCORE_GATE (direction-aware misalign + sentinel
        # bypass), otherwise displaced-guest SELLs re-suppress seat BUYs via
        # hedge_block. Pin as CODE lines (comment-stripped) so commenting the
        # block out fails the test.
        import inspect

        import modules.demo_trader as dt

        src = inspect.getsource(dt.DemoTrader._tick)
        code_lines = [
            ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "if _se_misaligned and not _se_sentinel_bypass:" in code, (
            "shadow_emit SCORE_GATE mirror removed — displaced-guest SELLs "
            "would open shadow rows that hedge_block seat BUYs (audit §9)"
        )


class TestFeedUnificationPins:
    def test_oanda_symbols_covers_usdcad(self):
        from modules.data import _OANDA_SYMBOLS

        assert _OANDA_SYMBOLS.get("USDCAD=X") == "USD_CAD", (
            "USD_CAD OANDA fallback hole re-opened (audit §4: it fell "
            "through to yfinance)"
        )

    def test_massive_live_dispatch_for_price_shock_pairs(self, monkeypatch):
        # Functional dispatch pin (adversarial review finding: a source-substring
        # pin passed even with the entries commented out). Pattern mirrors
        # tests/test_fetch_ohlcv_bt_mode.py: monkeypatch the providers and
        # assert the live path routes each seat symbol to MASSIVE first.
        import pandas as pd

        import modules.data as data_mod

        def _sample_ohlcv():
            idx = pd.date_range("2026-01-01", periods=1000, freq="h", tz="UTC")
            return pd.DataFrame(
                {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 0.0},
                index=idx,
            )

        monkeypatch.setenv("BT_MODE", "0")
        monkeypatch.setenv("MASSIVE_API_KEY", "test")
        monkeypatch.setenv("OANDA_TOKEN", "test")

        for sym in ("AUDJPY=X", "NZDJPY=X", "EURAUD=X", "USDCAD=X"):
            data_mod._data_cache.clear()
            calls = []
            monkeypatch.setattr(
                data_mod, "fetch_ohlcv_massive",
                lambda s, i, d: calls.append("massive") or _sample_ohlcv(),
            )
            monkeypatch.setattr(
                data_mod, "fetch_ohlcv_oanda",
                lambda s, i, d: calls.append("oanda") or _sample_ohlcv(),
            )
            monkeypatch.setattr(
                data_mod, "_fetch_raw",
                lambda s, p, i: calls.append("yfinance") or _sample_ohlcv(),
            )
            data_mod.fetch_ohlcv(sym, period="60d", interval="1h")
            assert calls and calls[0] == "massive", (
                f"{sym} live 1h feed no longer routes to MASSIVE first "
                f"(got {calls}) — feed drifts from the frozen 12.3y MASSIVE "
                "stats (BT/live source unification)"
            )
