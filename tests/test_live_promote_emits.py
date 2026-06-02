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


# ──────────────────────────────────────────────────────────────────────
# C) Kalman D7 3-spec (2026-05-22): same 2026-05-19 G2 bug recurrence.
#   Deployed 2026-05-20 (commit 1972bd8b) but never added to
#   LIVE_PROMOTE_LOSERS, so select_best max-score bottleneck (kalman
#   ≤4.8 vs primary 6.0-6.5) silently drops every candidate. Production
#   /api/oanda/audit (500 rows, 2026-05-14..05-22) confirms 0 kalman
#   shadow entries despite 35 UP transitions on USDJPY M15 with filters
#   passing on real bars.
# ──────────────────────────────────────────────────────────────────────


def test_live_promote_losers_includes_kalman_d7_trio():
    """LIVE_PROMOTE_LOSERS must contain the 3 Kalman D7 entry_types so the
    side-channel reaches demo_trader._tick_entry; without this the
    c7b4ab52 KALMAN_D7_LIVE_ENABLE override is unreachable code.
    """
    assert "kalman_d7_po_dn_flip" in DaytradeEngine.LIVE_PROMOTE_LOSERS
    assert "kalman_d7_ema75_break" in DaytradeEngine.LIVE_PROMOTE_LOSERS
    assert "kalman_d7_trail_atr" in DaytradeEngine.LIVE_PROMOTE_LOSERS


def test_split_live_promote_emits_returns_kalman_when_losing():
    """Realistic score gap: kalman (4.0-4.8) loses to session_time_bias (6.5).
    Verify all 3 kalman variants surface in the live_promote_emit list.
    """
    engine = DaytradeEngine()
    winner = _cand("session_time_bias", score=6.5)
    k_po = _cand("kalman_d7_po_dn_flip", score=4.6)
    k_ema = _cand("kalman_d7_ema75_break", score=4.3)
    k_trail = _cand("kalman_d7_trail_atr", score=4.0)
    other = _cand("trendline_sweep", score=5.0)  # not in either set

    emits = engine.split_live_promote_emits(
        [winner, k_po, k_ema, k_trail, other], winner
    )
    emit_types = {e.entry_type for e in emits}
    assert emit_types == {
        "kalman_d7_po_dn_flip",
        "kalman_d7_ema75_break",
        "kalman_d7_trail_atr",
    }


def test_split_live_promote_emits_excludes_kalman_winner():
    """When a kalman variant happens to be the best, it must NOT be
    re-emitted via side-channel (double-processing guard).
    """
    engine = DaytradeEngine()
    winner = _cand("kalman_d7_po_dn_flip", score=4.8)
    k_ema = _cand("kalman_d7_ema75_break", score=4.3)

    emits = engine.split_live_promote_emits([winner, k_ema], winner)
    emit_types = {e.entry_type for e in emits}
    assert "kalman_d7_po_dn_flip" not in emit_types
    assert emit_types == {"kalman_d7_ema75_break"}


# ──────────────────────────────────────────────────────────────────────
# D) ZZ Pivot v60 SR (2026-06-02): third recurrence of 2026-05-19 G2
#   bug pattern. Deployed 2026-05-28 (commit 068cc0db) as LIVE 1.0x /
#   0.5x intentional exception via _PAIR_PROMOTED + _PAIR_LOT_BOOST +
#   _SHIELD_EUR_DT_WHITELIST. Score base 4.0 (MR strategy) loses every
#   select_best competition to session_time_bias (~6.5) / vol_surge_
#   detector (~5-6) on EUR_USD M15. Production audit confirms 6 filter-
#   pass bars 2026-05-28..06-02 but only 1 audit row (and that one
#   bridge_status=skipped/shadow_tracking) — the other 5 silently
#   dropped at select_best. Render log evidence:
#     - 06-02 12:31 [MTF_MONITOR] entry=session_time_bias (zz_pivot pB SELL bar)
#     - 06-01 13:15 [MTF_MONITOR] entry=vol_surge_detector (zz_pivot tD BUY bar)
#   Ref: knowledge-base/raw/audits/kalman-zz-zero-fire-2026-06-02.md
# ──────────────────────────────────────────────────────────────────────


def test_live_promote_losers_includes_zz_pivot_v60_sr_pair():
    """LIVE_PROMOTE_LOSERS must contain both ZZ Pivot v60 SR entry_types
    (normal + loser-zone) so the side-channel reaches demo_trader._tick_entry
    despite session_time_bias / vol_surge_detector winning select_best.
    """
    assert "zz_pivot_v60_sr" in DaytradeEngine.LIVE_PROMOTE_LOSERS
    assert "zz_pivot_v60_sr_lo" in DaytradeEngine.LIVE_PROMOTE_LOSERS


def test_split_live_promote_emits_returns_zz_pivot_when_losing():
    """Realistic 2026-06-02 12:31 EUR_USD M15 bar: zz_pivot v60 pB SELL
    (score ~4.0) loses to session_time_bias SELL (score 6.5). Verify zz
    candidate surfaces in the live_promote_emit list.
    """
    engine = DaytradeEngine()
    winner = _cand("session_time_bias", score=6.5)
    zz_sr = _cand("zz_pivot_v60_sr", score=4.0)
    other = _cand("trendline_sweep", score=5.0)

    emits = engine.split_live_promote_emits(
        [winner, zz_sr, other], winner
    )
    emit_types = {e.entry_type for e in emits}
    assert emit_types == {"zz_pivot_v60_sr"}


def test_split_live_promote_emits_returns_zz_pivot_lo_when_losing():
    """Loser-zone variant (RSI<30 ∩ MACD<0 OR ATR_ratio>=1.6) must also
    survive select_best loss. Realistic 2026-06-01 13:15 bar: zz tD BUY
    score ~4.0 vs vol_surge_detector BUY score ~5.5.
    """
    engine = DaytradeEngine()
    winner = _cand("vol_surge_detector", score=5.5)
    zz_lo = _cand("zz_pivot_v60_sr_lo", score=4.0)

    emits = engine.split_live_promote_emits([winner, zz_lo], winner)
    emit_types = {e.entry_type for e in emits}
    assert emit_types == {"zz_pivot_v60_sr_lo"}
