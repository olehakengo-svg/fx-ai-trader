# Losing-Factor Identification — wick_imbalance_reversion × GBP_USD (E10)

**Date**: 2026-06-22 · **Author**: CMA coordinator (司令塔) · **Primary source**: Render production API
(`https://fx-ai-trader.onrender.com` /api/risk/dashboard + /api/demo/trades, `is_shadow=0`).
Local DB is treated as stale per discipline. Snapshot JSON: `data/cache/research/wick_imb_gbpusd/primary_source_snapshot.json`.

> **This document is the MOTIVATION (observed loss). It is NOT the pre-reg.** The forward edge hypothesis
> is locked separately in `knowledge-base/wiki/decisions/wick-imbalance-gbpusd-continuation-pre-reg-2026-06-22.md`
> and the ledger `agents/cma/prereg_ledger.jsonl`, BEFORE any conversion backtest is run.

## 1. The book is bleeding directionally (not friction)

30d rolling, clean live (`is_shadow=0`, n=104), Render risk API 2026-06-22:

| metric | value |
|---|---|
| gross PnL | **-217.5 pip** |
| net PnL | **-217.5 pip** (gross == net) |
| friction | 387.2 pip (3.72/trade, **flat**) |
| implication | the loss is **directional/edge**, not friction. Stopping trades stops the bleed but adds no edge. |

By instrument (30d clean live):

| pair | n | PnL (pip) | mean |
|---|---|---|---|
| **GBP_USD** | 30 | **-112.3** | **-3.74**  (#1 drag) |
| EUR_USD | 32 | -48.1 | -1.50 |
| USD_JPY | 20 | -39.3 | -1.96 |
| USD_CHF | 8 | -11.0 | -1.38 |
| EUR_JPY | 14 | -6.8 | -0.49 |

## 2. The single dominant losing CELL (cell-level, not aggregate)

GBP_USD's -113 pip decomposed by cell (entry_type x direction), clean live:

| cell | n | sum PnL | note |
|---|---|---|---|
| **wick_imbalance_reversion · BUY** | **9** | **-50.0** | **mean -5.56/trade — 44% of GBP_USD bleed** |
| session_time_bias · SELL | 3 | -14.8 | |
| sr_fib_confluence · BUY | 3 | -11.8 | |
| trendline_sweep · SELL | 5 | -10.8 | ELITE_LIVE cell |
| doji_breakout · BUY | 1 | -8.1 | |
| bb_rsi_reversion · SELL | 2 | +1.2 | only positive |

**ONE losing factor selected: `wick_imbalance_reversion` × GBP_USD (EdgeCell E10).**

## 3. Why it loses (mechanism)

`strategies/daytrade/alpha_wick_imbalance.py` — Alpha #2, `strategy_type="MR"` (Osler 2003 liquidity-depletion
reversion). BUY leg fires when WIR < -0.45 (down-wick / lower-rejection accumulation over window=8) **+** a bullish
confirm bar -> BUY, expecting a bounce. TP = ATR x (1.2..2.5), SL = ATR x 1.5.

- **Selection-bias casualty.** Promoted to live on a favorable **365d BT (WR 70.0% / EV +0.123 / PF 1.44**,
  demo_trader.py:7829). Live it is **WR-collapsed and net -5.6 pip/trade.** Exactly the
  "favorable short-window BT != edge" trap the promotion rubric forbids as a basis for promotion.
- **Counter-trend MR with no durable trend filter.** Buying lower-wick rejection = "buying the dip."
  In a GBP-weak tape this is catching a falling knife.
- **Both directions lose** (integrity-critical): batch (live+shadow) GBP_USD `wick_imbalance_reversion`
  BUY n=65 mean **-0.58**, SELL n=3 mean **-9.0**. => a naive directional inversion (BUY<->SELL) would
  **fail the both-legs-net-positive gate** — the conversion must be regime/trend-conditioned, not a blind flip.
- **Loss concentrates at London open.** By UTC hour (live BUY): 06h -20.0 (n2), 07h -5.4 (n2), 13h -10.5, 18h -10.9.
- **mtf_regime (live):** range_tight x6, trend_down_weak x2, range_wide x1.

## 4. Conversion direction (handed to research -> dev -> review)

Because both naive legs lose, the conversion is **NOT** a blind inversion. The pre-reg (locked separately,
before any conversion BT) frames the edge as a **trend/regime-conditioned reframe of the WIR rejection signal**,
validated forward shadow-first. Exit gate = full promotion rubric (Wilson_lo>=0.40 FDR-corrected, WF>=3/4 on 12y
MASSIVE, BH-FDR q=0.10, friction<=10%TP, both-legs net+, shadow N>=20). North star (monthly yield) governs
prioritisation only; promotion is rubric-gated. **Shadow-first — never auto-LIVE.**
