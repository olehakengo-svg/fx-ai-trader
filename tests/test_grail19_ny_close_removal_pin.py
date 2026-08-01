"""Regression pin for the 2026-07-31 Grail #19 removal (rule:R2).

Locks in the removal of the `ny_close_reversal` Grail live path:

- Registered 2026-04-25 on an N=4 TP-hit deep-mining cluster
  (USD_JPY × NY後半, Wlo=51%).
- Post-cutoff live record through 2026-07-31: 0W/4L −9.7 pips
  (fires 07-06 / 07-08 / 07-15 identified in quant-eval-2026-07-31).
- Shadow record negative on both pairs (GBP_USD −41p / USD_JPY −4p).

Shadow emission continues (原則3). Re-live requires R1 (forward shadow
N≥30 + Bonferroni + pre-reg LOCK).

References:
- knowledge-base/wiki/decisions/grail19-ny-close-removal-2026-07-31.md
- knowledge-base/raw/trade-logs/quant-eval-2026-07-31.md
"""
from __future__ import annotations

from modules.demo_trader import DemoTrader


def test_ny_close_reversal_not_in_grail_candidates():
    assert "ny_close_reversal" not in DemoTrader._GRAIL_CANDIDATES, (
        "ny_close_reversal must stay out of _GRAIL_CANDIDATES — the Grail #19 "
        "live path was removed 2026-07-31 (rule:R2) after live 0W/4L −9.7p on "
        "an N=4 registration basis. Re-live is R1 only. See "
        "decisions/grail19-ny-close-removal-2026-07-31.md."
    )


def test_grail_filter_rejects_ny_close_in_former_window():
    trader = object.__new__(DemoTrader)  # membership check precedes state use
    for hour in (17, 19, 21):
        assert not DemoTrader._check_grail_filter(
            trader, "ny_close_reversal", "USD_JPY", hour
        ), (
            f"_check_grail_filter must reject ny_close_reversal at hour={hour} "
            "— the former Grail #19 window (17-22 UTC) was removed 2026-07-31."
        )


def test_remaining_grail_candidates_unchanged():
    # Grail #1 (ema200) and #4 (vol_surge) stay under monitoring — their
    # removal (or any addition) requires its own decision doc.
    assert DemoTrader._GRAIL_CANDIDATES == {
        "ema200_trend_reversal",
        "vol_surge_detector",
    }, (
        "_GRAIL_CANDIDATES membership changed without a decision doc — "
        "additions/removals must follow the R1/R2 protocol."
    )
