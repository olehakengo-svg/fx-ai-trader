"""Per-cell Shadow demotion registry for R2 critical cells."""
from __future__ import annotations


# Strategy-level permanent retirement: blocks Shadow emission on ALL
# instruments, including pairs added by future modes (the per-cell entries
# below stopped EUR/GBP/JPY on 2026-05-08, but the daytrade_1h_usdchf
# Phase B-1 slot kept leaking ema_trend_scalp x USD_CHF afterwards).
SHADOW_RETIRED_STRATEGIES = frozenset({
    # 2026-06-12 (rule:R2): edge-factor audit clean N=1,117 — all 8
    # pair x dir cells PF 0.03-0.77, loser MAFE favorable median 0.5p
    # (entry has no predictive power; inverse also fails: gross EV ~ 0),
    # monthly WR 20.8% -> 16.1% -> 6.5%. No salvageable cell, no SIZE
    # lever target. Ref: wiki/learning/edge-factor-audit-2026-06-12-ema-trend-scalp.md
    "ema_trend_scalp",
    # 2026-06-12 (rule:R2): edge-factor audit #2, clean N=780. Thesis is
    # alive but the scalp geometry is arithmetically dead: gross EV
    # +0.5~+0.6p vs friction 1.2-1.5p (24.7% of the 5.2p median TP),
    # BE-WR 40.9% vs actual 35.4%. The same thesis survives at DT
    # geometry as dt_bb_rsi_mr (friction 10.8% of TP, net +1.72, PF
    # 1.61, N=105) which remains the family representative. 12y MASSIVE
    # BT rejected the USD_JPY redesign (PF 0.66, 2026-06-11). Containment
    # kept leaking (E4 -> USD_CHF hourly -> env-bypassable whitelist);
    # this entry closes it structurally.
    # Ref: wiki/learning/edge-factor-audit-2026-06-12-bb-rsi-reversion.md
    "bb_rsi_reversion",
    # 2026-06-12 (rule:R2): edge-factor audit #3, clean N=638. Scalp
    # friction arithmetic again: gross EV +0.59 vs friction 1.49p (29.2%
    # of the 5.1p median TP), BE-WR 41.7% vs actual 29.5%, loser MAFE
    # favorable median 0.2p. ALL 7 pair x dir cells net-negative (LIVE
    # included), monthly net deteriorating, and it was the single
    # biggest active shadow bleeder (30d N=251, -321.7p). Unlike #2
    # there is no surviving sibling to consolidate into — the same
    # thesis at DT geometry (sr_fib_confluence) is gross-NEGATIVE.
    # Ref: wiki/learning/edge-factor-audit-2026-06-12-fib-reversal.md
    "fib_reversal",
    # 2026-06-12 (rule:R2): edge-factor audit #4, clean N=584. Scalp
    # friction arithmetic once more: gross EV +0.58 vs friction 1.71p
    # (23.7% of the 7.2p median TP), BE-WR 35.7% vs actual 25.0%, loser
    # MAFE favorable median 0.2p, SL_HIT 56.2%. ALL 8 pair x dir cells
    # net-negative (USD_CHF BUY +0.35 is N=12 Wilson 0.138 noise). No
    # consolidation target: the SR-weight redesign survivor is the
    # DIFFERENT anti-hunt thesis (sr_anti_hunt_bounce, 30d +0.40), and
    # the DT channel-reversal (dt_sr_channel_reversal) is itself net
    # -1.07 (gross +2.25 friction-killed at 3.32p — a separate
    # pair-restriction hypothesis, not a current survivor). Still
    # leaking GBP_USD/USD_CHF via the per-cell registry gap (only
    # EUR_USD/USD_JPY were listed).
    # Ref: wiki/learning/edge-factor-audit-2026-06-12-sr-channel-reversal.md
    "sr_channel_reversal",
    # 2026-06-12 (rule:R2): edge-factor audit #5, clean N=453. First
    # gross-NEGATIVE aggregate of the series (-0.86p), but decomposition
    # shows it is not uniform: 96% of the -1354p shadow bleed is 4 JPY
    # cells (GBP_JPY/USD_JPY/EUR_JPY SELL+BUY, gross -4~-7.5p with 4-5p
    # cross friction) which the per-cell registry ALREADY stopped on
    # 2026-05-06/08 (confirmed not leaking). Post-JPY-stop the major-pair
    # remainder is near-breakeven but still 30d gross-negative (-0.50);
    # no cell clears Wilson_lo > BE-WR 0.324 (best EUR_USD BUY +0.54
    # Wilson 0.285). Inverse fails (inverse net -1.42). BUY-major shows
    # gross +1.85 (EUR_USD/GBP_USD BUY) friction-compressed to ~breakeven
    # at 15m (friction 8.7% of TP) — logged as a "fib-confluence
    # BUY-major-only" redesign hypothesis, NOT promotable now. Different
    # thesis from the SR survivor sr_anti_hunt_bounce.
    # Ref: wiki/learning/edge-factor-audit-2026-06-12-sr-fib-confluence.md
    "sr_fib_confluence",
})


SHADOW_DEMOTED_CELLS = frozenset({
    # 2026-08-05 (rule:R2): R2 shadow-promote alert batch. 10 cells CRITICAL
    # (N>=30, EV<0, 30d) persistently across the 2026-08-03..08-05 alert
    # series (sr_break_retest x GBP_JPY entered CRITICAL 08-04 on N-crossing
    # with EV -6.3..-7.4 throughout). Cell-level stop chosen over strategy
    # env-var removal: the same strategies keep emitting on their
    # non-CRITICAL pairs, and env KV toggles are not durable pins.
    # xs_momentum x GBP_USD / x USD_JPY were CRITICAL only in the last two
    # alerts (~7h apart, sign flipped from positive within 5h, PF 0.89/0.98)
    # — deferred under the 24h-persistence rule; demote next cycle if still
    # CRITICAL. Ref: wiki/decisions/r2-shadow-demote-2026-08-05.md
    ("dt_sr_channel_reversal", "AUD_JPY"),
    ("engulfing_bb", "EUR_USD"),
    ("london_breakout", "GBP_USD"),
    ("ma_regime_switch", "USD_JPY"),
    ("sr_break_retest", "EUR_JPY"),
    ("sr_break_retest", "GBP_JPY"),
    ("sr_break_retest", "GBP_USD"),
    ("vol_momentum_scalp", "GBP_USD"),
    ("vol_momentum_scalp", "USD_JPY"),
    ("xs_momentum", "EUR_USD"),
    ("bb_rsi_reversion", "EUR_USD"),
    ("bb_rsi_reversion", "GBP_USD"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("ema_trend_scalp", "EUR_USD"),
    ("ema_trend_scalp", "GBP_USD"),
    ("ema_trend_scalp", "USD_JPY"),
    ("engulfing_bb", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("sr_channel_reversal", "USD_JPY"),
    ("sr_fib_confluence", "EUR_JPY"),
    ("sr_fib_confluence", "GBP_JPY"),
    ("sr_fib_confluence", "USD_JPY"),
    # 2026-07-02 (rule:R2): daytrade_1h_usdchf mode audit. The Phase B-1
    # USD_CHF hourly surface bled -416.3p clean all-time (N=169, WR 16.6%,
    # production API re-verified 2026-07-02). 110/169 rows were the
    # 2026-06-12 retired strategies (already blocked above); these four
    # cells are the still-emitting remainder: N=59, WR 23.7%,
    # Wilson_lo 14.7%, -153.2p — below every BEV_WR in the friction table,
    # both directions negative for all four. Per-cell stats:
    #   london_breakout    N=37 WR 29.7% Wilson_lo 17.5% -88.6p (emitting daily)
    #   vol_surge_detector N=12 WR 25.0% Wilson_lo  8.9% -36.0p
    #   three_bar_reversal N=4  WR  0.0%                 -16.6p
    #   engulfing_bb       N=6  WR  0.0%                 -12.0p
    # The mode slot itself stays alive (auto_start unchanged) as the
    # price_shock_reversion Phase B surface — this is a per-cell stop,
    # not a mode stop, so Shadow accumulation for other strategies on
    # USD_CHF continues (principle 3). Re-promotion is R1-only.
    # Ref: wiki/decisions/usdchf-1h-cell-demotions-2026-07-02.md
    ("engulfing_bb", "USD_CHF"),
    ("london_breakout", "USD_CHF"),
    ("three_bar_reversal", "USD_CHF"),
    ("vol_surge_detector", "USD_CHF"),
})


def is_shadow_demoted(strategy: str, instrument: str) -> bool:
    """Return True when a strategy x instrument cell must not emit Shadow rows."""
    strategy_key = str(strategy or "")
    if strategy_key in SHADOW_RETIRED_STRATEGIES:
        return True
    return (strategy_key, str(instrument or "").upper()) in SHADOW_DEMOTED_CELLS
