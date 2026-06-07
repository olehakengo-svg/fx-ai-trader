"""Regression pin for the 2026-05-29 cell-forensic config changes.

Locks in the Shadow-cell-evidenced reorganisation of `xs_momentum` and
`session_time_bias`:

- `xs_momentum` × EUR_USD / GBP_USD moved from PAIR_PROMOTED → PAIR_DEMOTED
  (no Shadow cell with Wilson_lo>0.30, current-cohort EV=-5.15)
- `session_time_bias` `_STRATEGY_LOT_BOOST` 1.3x → 1.0x (cell-blind boost
  removed)
- `session_time_bias` × EUR_USD now cell-conditional via
  `_PAIR_SESSION_FILTER`: {"London"} (only Wilson_lo>0.30 cell)

If a future refactor reverts any of these, this test fails and flags the
need for fresh cell forensic + decision doc.

References:
- knowledge-base/wiki/decisions/xs-momentum-pair-demote-2026-05-29.md
- knowledge-base/wiki/decisions/session-time-bias-cell-forensic-2026-05-29.md
"""
from __future__ import annotations

from modules.demo_trader import DemoTrader


# ── xs_momentum: full-pair demote ─────────────────────────────────


def test_xs_momentum_eur_usd_in_pair_demoted():
    assert ("xs_momentum", "EUR_USD") in DemoTrader._PAIR_DEMOTED, (
        "xs_momentum×EUR_USD must remain PAIR_DEMOTED — no Shadow cell with "
        "Wilson_lo>0.30 and current cohort EV=-5.15. See "
        "decisions/xs-momentum-pair-demote-2026-05-29.md."
    )


def test_xs_momentum_gbp_usd_in_pair_demoted():
    assert ("xs_momentum", "GBP_USD") in DemoTrader._PAIR_DEMOTED, (
        "xs_momentum×GBP_USD must remain PAIR_DEMOTED — Shadow BUY EV=-2.25, "
        "SELL EV=+0.21 (Wlo=0.22, noise level). See "
        "decisions/xs-momentum-pair-demote-2026-05-29.md."
    )


def test_xs_momentum_usd_jpy_pair_demoted_unchanged():
    """Existing v8.6 USD_JPY demote must remain."""
    assert ("xs_momentum", "USD_JPY") in DemoTrader._PAIR_DEMOTED


def test_xs_momentum_not_in_pair_promoted():
    """xs_momentum must NOT be in PAIR_PROMOTED for EUR_USD/GBP_USD/USD_JPY."""
    for pair in ("EUR_USD", "GBP_USD", "USD_JPY"):
        assert ("xs_momentum", pair) not in DemoTrader._PAIR_PROMOTED, (
            f"xs_momentum×{pair} must not be PAIR_PROMOTED after 2026-05-29 "
            f"cell forensic demote."
        )


# ── session_time_bias: cell-conditional config ────────────────────


def test_session_time_bias_lot_boost_is_neutral():
    """Cell-blind 1.3x boost removed in 2026-05-29 cell forensic.

    Reinstatement requires Live N≥30 on EUR_USD London cell with
    Wilson_lo>0.40 + Bonferroni p<0.05 (see decision doc).
    """
    boost = DemoTrader._STRATEGY_LOT_BOOST.get("session_time_bias", 1.0)
    assert boost == 1.0, (
        f"session_time_bias lot boost must be 1.0 (was {boost}). Cell-blind "
        f"1.3x amplified losing cells (EUR_USD Overlap -1.88, NY -0.12). See "
        f"decisions/session-time-bias-cell-forensic-2026-05-29.md."
    )


def test_session_time_bias_eur_usd_is_london_only():
    """EUR_USD now cell-conditional: London cell only (Wilson_lo=0.327)."""
    sessions = DemoTrader._PAIR_SESSION_FILTER.get(
        ("session_time_bias", "EUR_USD")
    )
    assert sessions == {"London"}, (
        f"session_time_bias×EUR_USD must be cell-conditional to "
        f"{{'London'}} (got {sessions!r}). Shadow London N=58 Wlo=0.327 "
        f"EV=+1.44 PF=1.41 is the only edge cell."
    )


def test_session_time_bias_eur_usd_still_pair_promoted():
    """EUR_USD PAIR_PROMOTED stays — only the session filter narrows Live."""
    assert ("session_time_bias", "EUR_USD") in DemoTrader._PAIR_PROMOTED, (
        "session_time_bias×EUR_USD must stay PAIR_PROMOTED — the cell "
        "filter narrows Live to London only, not full removal."
    )


def test_session_time_bias_gbp_usd_removed_2026_06_07():
    """GBP_USD revival REMOVED 2026-06-07 (rule:R2) emergency loss containment.

    Supersedes 2026-06-01 R2 cell forensic revival.
    Reason: 2026-06-04 11:31 UTC live fire SELL -7.9p SL confirmed MR-in-trend
    bleed continued despite E8 disable (session_time_bias was firing via this
    PAIR_PROMOTED path, not edge_cell). Original Wlo=0.251 < Bonferroni 0.55 /
    H1 Gate 0.40 was insufficient evidence. 7d LIVE: 5 fills all SELL, net
    -1,090 JPY contribution to family bleed.

    Re-promote requires Shadow N>=30 + Bonferroni-corrected Wilson_lo>=0.55.
    Memory: project_edge_cell_stage3_recovery_phase2_2026_06_07.
    """
    # Removed from PAIR_PROMOTED in 2026-06-07 R2 emergency loss containment.
    assert ("session_time_bias", "GBP_USD") not in DemoTrader._PAIR_PROMOTED, (
        "session_time_bias×GBP_USD must NOT be in PAIR_PROMOTED — removed "
        "2026-06-07 R2 emergency loss containment (06-04 live -7.9p SL, "
        "MR-in-trend, original Wlo=0.251 insufficient evidence)."
    )
    # Also removed from session filter (inert without PAIR_PROMOTED, removed for consistency).
    assert ("session_time_bias", "GBP_USD") not in DemoTrader._PAIR_SESSION_FILTER, (
        "session_time_bias×GBP_USD must NOT have _PAIR_SESSION_FILTER entry "
        "after 2026-06-07 R2 removal — code consistency."
    )


# ── Session filter mechanics sanity ───────────────────────────────


def test_session_filter_entries_use_canonical_session_names():
    """All `_PAIR_SESSION_FILTER` session labels must match
    `_SESSION_BOUNDS_UTC` labels exactly — typo guard."""
    valid = {name for name, _lo, _hi in DemoTrader._SESSION_BOUNDS_UTC}
    for (strat, pair), sessions in DemoTrader._PAIR_SESSION_FILTER.items():
        for s in sessions:
            assert s in valid, (
                f"_PAIR_SESSION_FILTER[{strat!r}, {pair!r}] contains "
                f"unknown session {s!r}; valid: {sorted(valid)}"
            )
