"""
Test for LIVE_PROMOTE_LOSERS side-channel (2026-05-19, rule:R3).

Verifies:
1. SHADOW_ALWAYS_STRATEGIES baseline contains xs_momentum_rsi + macd_rsi_pullback
2. LIVE_PROMOTE_LOSERS set contains both strategies
3. split_live_promote_emits returns non-best LIVE_PROMOTE_LOSERS candidates
4. split_live_promote_emits excludes the best candidate even if eligible
5. split_live_promote_emits handles empty / None input safely

Rationale:
- Production audit 2026-05-14 → 2026-05-19 showed xs_momentum_rsi and
  macd_rsi_pullback registered (PAIR_PROMOTED / SCALP_SENTINEL) but 0 prod
  fires across 4 London-NY sessions despite base xs_momentum firing 5×
  USD_JPY shadow on 2026-05-14. Root cause: select_best max-score bottleneck
  silently drops their candidates when higher-score primaries
  (session_time_bias / london_fix_reversal / vix_carry_unwind) win.
"""
from __future__ import annotations

from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine


def _cand(entry_type: str, score: float = 5.0, signal: str = "BUY") -> Candidate:
    return Candidate(
        signal=signal,
        confidence=70,
        sl=148.0,
        tp=152.0,
        reasons=["test"],
        entry_type=entry_type,
        score=score,
    )


# ──────────────────────────────────────────────────────────────────────
# A) SHADOW_ALWAYS baseline coverage
# ──────────────────────────────────────────────────────────────────────


def test_shadow_always_includes_xs_momentum_rsi():
    """SHADOW_ALWAYS_STRATEGIES baseline must contain xs_momentum_rsi (Option A)."""
    assert "xs_momentum_rsi" in DaytradeEngine.SHADOW_ALWAYS_STRATEGIES


def test_shadow_always_includes_macd_rsi_pullback():
    """SHADOW_ALWAYS_STRATEGIES baseline must contain macd_rsi_pullback (Option A)."""
    assert "macd_rsi_pullback" in DaytradeEngine.SHADOW_ALWAYS_STRATEGIES


def test_shadow_always_keeps_existing_rsk():
    """rsk_gbpjpy_reversion remains in baseline (regression guard)."""
    assert "rsk_gbpjpy_reversion" in DaytradeEngine.SHADOW_ALWAYS_STRATEGIES


# ──────────────────────────────────────────────────────────────────────
# B) LIVE_PROMOTE_LOSERS coverage and behavior
# ──────────────────────────────────────────────────────────────────────


def test_live_promote_losers_membership():
    """LIVE_PROMOTE_LOSERS contains both target strategies (Option B)."""
    assert "xs_momentum_rsi" in DaytradeEngine.LIVE_PROMOTE_LOSERS
    assert "macd_rsi_pullback" in DaytradeEngine.LIVE_PROMOTE_LOSERS


def test_split_live_promote_emits_returns_loser():
    """When best is another strategy, LIVE_PROMOTE_LOSERS members are emitted."""
    engine = DaytradeEngine()
    winner = _cand("session_time_bias", score=6.5)
    loser_xs = _cand("xs_momentum_rsi", score=5.6)
    loser_macd = _cand("macd_rsi_pullback", score=5.4)
    other_loser = _cand("trendline_sweep", score=5.0)

    emits = engine.split_live_promote_emits(
        [winner, loser_xs, loser_macd, other_loser], winner
    )
    emit_types = {e.entry_type for e in emits}
    assert emit_types == {"xs_momentum_rsi", "macd_rsi_pullback"}


def test_split_live_promote_emits_excludes_winner():
    """When xs_momentum_rsi IS the best, it is NOT in the emit list."""
    engine = DaytradeEngine()
    winner = _cand("xs_momentum_rsi", score=6.0)
    loser_macd = _cand("macd_rsi_pullback", score=5.4)

    emits = engine.split_live_promote_emits([winner, loser_macd], winner)
    emit_types = {e.entry_type for e in emits}
    # winner must not be re-emitted (would cause double processing)
    assert "xs_momentum_rsi" not in emit_types
    assert emit_types == {"macd_rsi_pullback"}


def test_split_live_promote_emits_empty_candidates():
    """Empty / None candidates list returns empty emit list (no exception)."""
    engine = DaytradeEngine()
    assert engine.split_live_promote_emits([], None) == []
    assert engine.split_live_promote_emits(None, None) == []  # type: ignore[arg-type]


def test_split_live_promote_emits_only_non_eligible():
    """If no candidate is a LIVE_PROMOTE_LOSER, returns []."""
    engine = DaytradeEngine()
    a = _cand("session_time_bias", score=6.0)
    b = _cand("trendline_sweep", score=5.5)
    assert engine.split_live_promote_emits([a, b], a) == []


def test_split_live_promote_emits_no_best():
    """If best is None but losers exist, all eligible candidates are emitted."""
    engine = DaytradeEngine()
    c = _cand("xs_momentum_rsi", score=4.0)
    emits = engine.split_live_promote_emits([c], None)
    # `c is not None` so it qualifies
    assert len(emits) == 1
    assert emits[0].entry_type == "xs_momentum_rsi"
