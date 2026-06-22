# Wick-Imbalance GBP_USD Continuation — pre-reg LOCK (2026-06-22)

**Status: LOCKED — committed BEFORE any conversion backtest.** Post-hoc parameter tuning voids this pre-reg.
**Rule**: R1 (new strategy / new edge — slow & strict). **Campaign**: m=2 signed legs, BH-FDR q=0.10.
**Source**: CMA research agent forensic + frozen spec 2026-06-22 (`data/cache/research/wick_imb_gbpusd/hypothesis.md`).
**Motivation (losing factor)**: [[losing-factor-wick-imbalance-gbpusd-2026-06-22]] — Render API primary source.
**Ledger**: `agents/cma/prereg_ledger.jsonl` id=`wick_imbalance_gbpusd_continuation_2026-06-22`.

## Losing factor (the thing we are converting)
`wick_imbalance_reversion` × GBP_USD (EdgeCell **E10**) is the single dominant live loser:
LIVE `is_shadow=0` **n=9, -50.0 pip, mean -5.56, WR 33%** (= 44% of GBP_USD's -112.3 pip 30d bleed; GBP_USD = #1 drag).
Promoted on a favorable **365d BT (WR70%/EV+0.123/PF1.44)** -> bled in live = selection-bias casualty (rubric forbids
BT-+EV as promotion basis). **Decisive forensic finding: a D1-bull gate (d1_label in {+1,+2}) would have blocked
ALL 9/9 live losers** — 100% fired at d1 in {0,-1} (neutral / weak-bear), ZERO in an uptrend. The MR "bounce"
fires on lower-wick rejection that structurally forms while price grinds down = catching a falling knife.

## Mechanism (academic basis)
WIR trigger = Osler (2003) liquidity-cluster signal. Direction reframed to **with-trend continuation** via the
existing closed-bar D1 trend label — basis: FX time-series momentum (Moskowitz-Ooi-Pedersen 2012; Menkhoff et al. 2012).
This is a **trend-alignment FILTER on an existing trigger** (adds ONE binary DoF: the D1 label), NOT a blind
directional inversion. Rationale for not inverting: BOTH naive legs lose (batch BUY mean -0.58 / SELL -9.0), so an
inversion would fail the both-legs gate; the filter instead converts knife-catching into with-trend pullback entry.

### DISTINCT from killed/rejected ledger items
Not `hull_donchian_fade` (Donchian fade — opposite philosophy), not `monthend_fix` (EUR_USD WMR), not
`d1_tsmom_basket` (D1 risk-premia basket), not `ob_retest_h1`/`ema10_8pattern`/`fx_nexus`/`scalp_re_enable`/
`cell_promotion`/`phase3`/`bb_rsi revival`. This is a single-pair H1 wick-imbalance **continuation** cell.

## Hypothesis (FROZEN — closed bars only, no look-ahead)
- **strategy_id**: `wick_imbalance_continuation_gbpusd` · **pair**: GBP_USD · **TF**: H1 · **mode**: daytrade.
- **WIR**: computed over `df.iloc[-10:-2]` (window=8); **confirm bar** = `df.iloc[-2]` (last CLOSED bar);
  **entry** = next H1 open. (Reuses the existing REDESIGN_V2 closed-bar path.) threshold=0.45 (inherited).
- **d1_label**: prior COMPLETED daily bar label (already causal at demo_trader.py:9043). The ONLY new DoF.
- **LONG**  : `WIR < -0.45` AND `d1_label in {+1,+2}` AND `confirm_body > 0` -> BUY  (with-trend pullback).
- **SHORT** : `WIR > +0.45` AND `d1_label in {-1,-2}` AND `confirm_body < 0` -> SELL (with-trend rally-rejection).
- **NO-TRADE** if `d1_label in {0,3}` (3 = insufficient-data sentinel) or `|WIR| < 0.45` or `|confirm_body| < 0.05*ATR`.
- **Exits**: SL = 1.5 x ATR14(H1) (unchanged). **TP = 2.5 x ATR14(H1) FROZEN FLAT** (drops the |WIR|-scaled TP DoF).
  RR = 1.67, breakeven WR = 37.5%.

## Friction pre-check (gate 5 pre-filter)
GBP_USD ATR14(H1): cache median 18.7 pip (p25 15 / p75 23.7), conservative floor 14 pip. RT friction ~1.5-2 pip.
At ATR floor 14 -> TP = 35 pip -> friction = 2/35 = **5.7% <= 10%** PASS (median ATR -> 4.3%).

## Decision gates (ALL required for SURVIVE)
- **G1** net EV > 0 (combined AND each leg).
- **G2** stationary/IID bootstrap p (10k resamples, **fixed seed=42**, 1-sided) survives **BH-FDR q=0.10 @ m=2**.
- **G3** Walk-Forward >= **3/4** folds net-positive on the registered **12y MASSIVE** history.
- **G4** **Wilson_lo(WR,95%) >= 0.40** AND WR >= 37.5% breakeven (cell-single, not aggregate; FDR-corrected).
- **G5** friction <= **10% of TP** (~5.7%).
- **G6** **BOTH signed legs net-positive** (mandatory — month-end-fix single-side-artifact trap).
- **G7** per-year / drop-one-year robustness (no single-year or 2014-16/2022-fall dependence — hull_donchian learning).
- **G8** **shadow N >= 20 forward** before ANY LIVE consideration.

A leg failing any gate -> that leg REJECT. Both legs may pass/fail independently under BH-FDR(m=2).

## Data plan (for dev — fetch BEFORE BT, all from MASSIVE primary)
- GBP_USD H1 MASSIVE cache currently 2021-12-24 -> 2026-05-15 (27,556 rows, ~4.5y) = **INSUFFICIENT for 12y WF**.
  Dev MUST fetch full GBP_USD **H1 back to ~2014** via Massive API (`MASSIVE_API_KEY` in `.env`).
- GBP_USD D1 cache 2016-04 -> 2026-06 (~10y) for the d1 gate; extend to ~2014. pip = 0.0001.

## Promotion policy
- If SURVIVE -> **shadow-first** (`is_shadow=1`), accumulate forward N. **Never auto-LIVE on BT alone.**
- LIVE flip requires the orchestrator gate: forward **shadow N>=20** AND Wilson_lo>=0.40 (BH-FDR corrected)
  AND WF>=3/4 AND friction<=10%TP. lot ramp N>=20->1000u / >=35->2500u / >=50->5000u. (propose_live_flip only.)
- If NULL/FAILED -> kill & record in ledger (m + reason). No post-hoc rescue; re-angles become a NEW pre-reg.

## Constraints honored
XAU excluded · Render API = live-stat primary · is_shadow separation strict · not a re-propose of any killed item ·
both-legs gate enforced · 12y WF on registered history · friction-aware TP.
