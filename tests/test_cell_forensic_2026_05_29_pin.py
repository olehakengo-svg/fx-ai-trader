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


def test_session_time_bias_gbp_usd_cell_conditional_london():
    """GBP_USD cell-conditional (2026-06-01 R2 cell forensic revival).

    Supersedes 2026-05-03 R2 LOCK PAIR_DEMOTED with symmetric treatment
    to EUR_USD London (vix_carry Overlap pilot pattern).
    Shadow London: N=45 WR=37.8% Wlo=0.251 EV=+0.98 PF=1.19 edge cell.
    Other sessions (Asia/NY/Overlap, EV=-4.74 aggregate) auto-blocked.
    """
    # Removed from PAIR_DEMOTED in 2026-06-01 revival.
    assert ("session_time_bias", "GBP_USD") not in DemoTrader._PAIR_DEMOTED, (
        "session_time_bias×GBP_USD must NOT be in PAIR_DEMOTED — superseded "
        "by 2026-06-01 cell forensic revival (cell-conditional London)."
    )
    # Now in PAIR_PROMOTED.
    assert ("session_time_bias", "GBP_USD") in DemoTrader._PAIR_PROMOTED, (
        "session_time_bias×GBP_USD must be PAIR_PROMOTED after 2026-06-01 "
        "cell forensic revival."
    )
    # Cell-conditional: London only.
    sessions = DemoTrader._PAIR_SESSION_FILTER.get(
        ("session_time_bias", "GBP_USD")
    )
    assert sessions == {"London"}, (
        f"session_time_bias×GBP_USD must be cell-conditional to "
        f"{{'London'}} (got {sessions!r}). Shadow London N=45 Wlo=0.251 "
        f"EV=+0.98 PF=1.19."
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
