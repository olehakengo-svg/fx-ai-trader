# trendline_sweep GBP_USD — LIVE loss factor → shadow-first conversion (PRE-REG LOCK)

**PRE-REG LOCK timestamp (UTC):** 2026-07-13T20:11:11Z
**Ledger id:** `trendline_sweep_gbpusd_pairscope_2026-07-13`
**Outcome mode:** loss_hunt (identify one LIVE losing factor → convert to a shadow-first, rubric-verified edge)
**rule:** R1 (Slow & Strict — ELITE_LIVE scope change requires 12y BT + Bonferroni/FDR + pre-reg LOCK)
**Discipline note:** This document is written and time-stamped BEFORE the conversion 12y backtest is run.
The forward LIVE/shadow numbers below are *problem identification* (why the cell loses), NOT the edge test.
The edge test (12y MASSIVE walk-forward on independent registration-time history) is the dev step that follows.

---

## 1. Losing factor (identified from PRIMARY data = Render production API)

`trendline_sweep` (SMC "trendline liquidity sweep → reclaim → trend continuation", DT 15m) is currently
**ELITE_LIVE**: it bypasses the shadow→live promotion system and trades all allowed pairs on real money.
It earned ELITE_LIVE purely on a **favorable 365d backtest** (GBP_USD BT WR≈73% EV +0.60; EUR_USD BT WR≈81%
EV +0.93 — see `modules/demo_trader.py:7410`, `knowledge-base/wiki/strategies/trendline-sweep.md`).
The promotion rubric explicitly states a favorable BT/40d/TV window is NOT valid promotion evidence
(favorable = selection bias, demonstrated on 3 strategies). ELITE_LIVE is therefore an un-earned LIVE seat.

Forward reality (Render `/api/demo/factors` + `/api/demo/trades`, is_shadow SEPARATED, post-cutoff):

| cell | cohort | N | WR | netEV (pip) | totPnL | avgWin | avgLoss | realized RR | MFE(fav) | MAE(adv) | close_reason |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| trendline_sweep GBP_USD | **LIVE** | 19 | 63.2% | **-2.35** | -44.7 | +1.67 | -11.07 | **0.15** | +3.08 | +5.85 | SL_HIT 11 / OANDA_SL_TP 7 / REVERSE 1 |
| trendline_sweep GBP_USD | shadow | 39 | 61.5% | -3.49 | -136.1 | +1.73 | -11.84 | 0.15 | +3.02 | +7.51 | SL_HIT 33 / REVERSE 6 |
| trendline_sweep EUR_GBP | shadow | 49 | 57.1% | -1.52 | -74.4 | +1.86 | -6.03 | 0.31 | +2.23 | +3.95 | SL_HIT 40 / TIME 8 / REVERSE 1 |
| trendline_sweep EUR_USD | shadow | 40 | 80.0% | **+1.72** | +68.8 | +4.97 | -11.28 | 0.44 | +6.90 | +5.02 | SL_HIT 31 / TP_HIT 8 / REVERSE 1 |

(LIVE cell decomposition by close_reason, GBP_USD: OANDA_SL_TP wins avg +1.18p; SL_HIT losers -1.66 to -8.03p;
SIGNAL_REVERSE 100% loss. Confirmed with `/api/demo/factors?factors=strategy,instrument,direction,close_reason`.)

### Root-cause mechanism (why it loses)
Designed geometry: SL = sweep-extreme ± 0.3·ATR, **TP = 2.5·ATR**, MIN_RR 1.5 (`strategies/daytrade/trendline_sweep.py:94`).
On GBP_USD the average trade reaches only **+3.08p favorable (MFE)** — nowhere near a 2.5·ATR (~20p+) TP — before
reversing into a wide sweep-based SL. Winners are scratched tiny (+1.67p); losers run full size (-11p). Realized
RR collapses to **0.15**, so WR 63% still yields net **-2.35 pip/trade**. Even *gross* (adding back ~1.5p friction),
EV ≈ 0.63·3 − 0.37·11 ≈ **-2.2p < 0** → the trigger has **no continuation edge on GBP_USD** (diagnosis class (c):
concept-broken on this pair, not merely a friction or exit-geometry-repairable case).

Contrast EUR_USD (MFE +6.9, avgWin +4.97, netEV +1.72): the sweep→continuation follow-through is genuinely present.
The edge is **pair-specific**; ELITE_LIVE's "all pairs" bypass is the mechanism that exposes real money to the
non-edge GBP_USD (and EUR_GBP) cells. This matches the 2026-05-04 edge_design audit
(`audits/edge_design/trendline_sweep.md`): EUR_USD 730d WF positive-ratio 1.00 (stable); GBP_USD 0.64 (borderline).

---

## 2. Conversion hypothesis (falsifiable, theory-motivated)

**H:** On 12y MASSIVE (2014-2026) 15m walk-forward with the **unchanged production trigger** + realistic
round-turn friction, evaluated **per cell** (pair × direction), the trendline_sweep continuation edge is
**pair-specific**: EUR_USD clears all rubric gates; GBP_USD and EUR_GBP do not. Therefore the ELITE_LIVE
all-pairs bypass must be removed and the non-clearing cells demoted to **shadow-only**; any cell may only
(re)enter LIVE via shadow-first forward OOS (N≥20 ∧ Wilson_lo≥0.40), never via a favorable BT.

Reusing the production trigger only (no new signal invented). No parameter tuning of the trigger; the ONLY
change under test is **routing/pair-scope** (which cells are LIVE vs shadow).

## 3. Pre-declared gates (LOCKED — evaluated per cell after the 12y BT)

- **m = 3** pair-level tests (EUR_USD, GBP_USD, EUR_GBP), BH-FDR q=0.10 (rolling window; cumulative Bonferroni not used).
- **G1** netEV > 0 (post-friction, 12y).
- **G2** BH-FDR q=0.10 survive (m=3).
- **G3** Walk-Forward ≥ 3/4 folds directional-positive (12y history split into 4; shadow N NOT re-split).
- **G4** Wilson_lo ≥ 0.40 (FDR-corrected, cell-level; NOT aggregate WR).
- **G5** friction ≤ 10% of TP.
- **G6** both-legs: BUY and SELL each net ≥ 0 (no single-side artifact).
- satisfied = ALL of G1..G6 for that cell. Any miss on GBP_USD/EUR_GBP → demote ELITE_LIVE→shadow (stop LIVE bleed).

## 4. Predicted verdict (pre-registered so it can be graded honestly)

| cell | predicted | rationale |
|---|---|---|
| EUR_USD | **PASS** (verified edge; still shadow-first to LIVE) | MFE +6.9, forward shadow +EV, WF 1.00 |
| GBP_USD | **FAIL** G1/G3/G4/G6 → ELITE_LIVE→shadow (kill LIVE cell) | gross-negative, RR 0.15, MFE +3.08 |
| EUR_GBP | **FAIL** → shadow | MFE +2.23, forward shadow -EV |

## 5. North-star linkage
Removing a real-money loss maker (GBP_USD ELITE_LIVE, forward -2.35 pip/trade) is a direct, low-risk lift to
monthly return, and it re-imposes the shadow-first discipline the ELITE_LIVE bypass had removed. Promotion of
any surviving cell remains rubric-gated (shadow N≥20 ∧ Wilson_lo≥0.40 FDR-corrected), never on the favorable BT.

## 6. Verdict log
- 2026-07-13T20:11:11Z — PRE-REG LOCK created (this doc). status=locked. Pending: dev 12y MASSIVE WF BT → adversarial review.

---

## Amendment 1 — structural, pre-results (2026-07-13T20:21:45Z)

Recorded BEFORE any conversion-BT results were observed. Basis = fxai-research collision-check +
code `SELL_ONLY_PAIRS` structure. NOT results-driven. Original §2–§4 lock text above is preserved unchanged.

1. **Framing is DEMOTE / pair-scope re-qualification ONLY.** The exit/TP/SL geometry-repair path is already
   R1-KILLED (`exit-repair-tp-sl-prereg-2026-07-07`: 0/9 configs, H0 adopted "signal replacement is the only
   path"). This pre-reg tests ONLY routing/pair-scope (which cells are LIVE vs shadow); it does not, and must not,
   re-propose capture/geometry repair.
2. **m = 4 effective (was 3).** `SELL_ONLY_PAIRS = {EURUSD, EURGBP, XAUUSD}` blocks BUY on those pairs → EUR_USD×BUY
   and EUR_GBP×BUY are structurally VOID (0 trades). Effective tradable cells = {EUR_USD×SELL, EUR_GBP×SELL,
   GBP_USD×BUY, GBP_USD×SELL}. BH-FDR family m=4. (Larger m is strictly more conservative — no goalpost softening.)
3. **G4 clarified:** Wilson_lo ≥ 0.40 AND WR ≥ BE-WR computed at **REALIZED payoff (avgWin/|avgLoss|), NOT design
   RR.** At design RR the BE-WR looks ~30–38% and GBP_USD *false-passes* (Wilson_lo 42.4% > 40%); at realized
   payoff 0.15 the BE-WR is ~87%, which GBP_USD misses. This is the exact trap behind the 2026-07-02 KEEP deferral.
4. **EUR_USD is the positive control / KEEP leg, EXCLUDED from the demote scope.** It is on a protected WS3
   live-N re-qualification track (`ws3-asymmetry-oos §8.3(c)`, `ws3-round2 §2`). This pre-reg makes NO promotion
   claim for EUR_USD; it only asserts EUR_USD is NOT part of the losing factor being demoted.

**Collision status:** No ledger kill/lock covers this hypothesis. The GBP_USD demote was deferred twice
(2026-07-02 R2 "KEEP"; 2026-07-07 "hold") on the premise "directional edge preserved" — which the forward
MFE≤MAE / gross-negative evidence refutes. Both deferrals named R1 (12y BT + Bonferroni + pre-reg LOCK) as the
reopen path — i.e. exactly this pre-reg. Partial mitigation `HTF_MIXED_LIVE_STOP_CELLS={(trendline_sweep,GBP_USD)}`
is already live but only stops LIVE when 4H+1D HTF is mixed; a full pair-demote is not redundant with it.
