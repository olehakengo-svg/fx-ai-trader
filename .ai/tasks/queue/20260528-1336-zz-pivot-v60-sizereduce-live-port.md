# Port ZZ Pivot v60 + SizeReduce to fx-ai-trader (LIVE 1.0x, intentional exception)

priority: P1
rule: R1 (feature add — new strategy port, full quant check pending; intentional exception declared)
gate: H1 Gate is **NOT** required pre-deploy per user judgment (memory pattern: Kalman D7 / vix_carry 1x). Watchdog observability still required.

## Source of truth — Pine Script

The reference Pine script currently runs on **TradingView Desktop**, script slot
`USER;978a118f17884c19a823b262a8aceb5a` (title: `Trade-Level Loser Analysis v70.4 (WFO)`).
Latest 1y OOS BT on **EURUSD M15** (2025-05-26 → 2026-05-26):

- 207 trades, WR 48.31%, **PF 1.222, Total PnL +$57.73, Max DD 0.22%** (baseline)
- With SizeReduce ACTIVE: **PF 1.294 (+5.9%), Total PnL +$65.10 (+12.8%), Max DD 0.24%**
- WFO 3-fold robustness: **3/3 folds positive ΔPnL** (+24.9% / +4.0% / +7.6% PF)

The complete Pine source is in TradingView. Codex must read it via the
`mcp__tradingview__pine_get_source` tool if needed, OR refer to the spec below
which captures the strategy in full.

## Strategy spec (v60 MR-at-Trend-Extreme + SizeReduce)

**Symbol**: `EUR_USD` only (Phase 1). M15 timeframe.

**Trend filter**: `trend_ema = ema(close, 50)`
- `uptrend = close > trend_ema`
- `downtrend = close < trend_ema`

**Peak detection** (entry SHORT during uptrend, all on confirmed bar close):

`pA_sig` (dynamic + absolute):
- `rsi(close,14) - rsi(close,14)[5] > 2`
- `rci9 - rci9[5] < -25` (rci9 = 9-period Rank Correlation Index)
- `bbp_b - bbp_b[5] > 0.08` where `bbp_b = (close - bb_lower) / (bb_upper - bb_lower)`,
  `bb = bbands(close, 20, 2.0)`
- `(close - close[5]) / close[5] * 100 > 0.02`
- `rsi(close,14) >= 60 AND bbp_b >= 0.80 AND rci9 <= -30`
- `(highest(high,20)[1] - high) <= 0.5 * atr(14)` (near_high)
- `rsi_accel < 0` where `rsi_accel = rsi_d5 - rsi_d5[5]`
- `up_streak >= 2` (consecutive close > close[1] counter)

`pB_sig` (HH/RSI divergence):
- `high >= highest(high,30)[1]`
- `rsi < highest(rsi,30)[1] - 10`
- `bbp_b >= 0.90 AND rsi >= 63`

`pE_sig` (MACD divergence):
- `high >= highest(high,30)[1]`
- `macd_hist < highest(macd_hist,30)[1] - 0.00025`
- `bbp_b >= 0.85 AND rsi >= 60`

`pF_sig` (prior swing retest):
- `high <= highest(high[20],30) + 0.2*atr AND high >= highest(high[20],30) - 0.2*atr`
- `bbp_b >= 0.88 AND rsi >= 62`

**Trough detection** (entry LONG during downtrend) — mirror of peak with adjusted thresholds:

`tA_sig`, `tB_sig`, `tD_sig` (vol spike: `vol_z >= 2.7 AND rsi<=33 AND bbp_b<=0.30 AND close<open AND body>=0.5*atr`), `tF_sig`. See Pine source for exact symmetric definitions.

**Entry rule**:
- `any_peak = pA_sig OR pB_sig OR pE_sig OR pF_sig`
- `any_trough = tA_sig OR tB_sig OR tD_sig OR tF_sig`
- If `uptrend AND any_peak AND no_position`: enter SHORT at close
- If `downtrend AND any_trough AND no_position`: enter LONG at close

**Exit rule**:
- Emergency SL only: `stop = close ± 4.0 * atr(14)` placed at entry
- Position close on **opposite extreme detected**:
  - SHORT closes when `any_trough` AND `bars_in_trade >= 5`
  - LONG closes when `any_peak` AND `bars_in_trade >= 5`
- No TP target.

**Position sizing (SizeReduce — THE NEW PART)**:

`loser_zone` flag computed at entry:
- F1: `rsi < 30 AND macd_hist < 0`
- F3: `atr_ratio >= 1.6` where `atr_ratio = atr(14) / ema(atr(14), 100)`
- `loser_zone = F1 OR F3`

Lot sizing:
- Normal entry: **10% of equity** (BT default)
- Loser-zone entry: **5% of equity** (50% reduction)

Per user judgment, initial **Live size = 1.0x** of these BT defaults (no Shadow ramp).
This is an intentional exception per memory `project_kalman_d7_regime_bound_live_2026_05_20`
and `project_vix_carry_1x_intentional_exception_2026_05_21` pattern.

## Implementation requirements

### 1. Strategy file

Create `strategies/scalp/zz_pivot_v60_sr.py` (or `strategies/hourly/` if M15 fits there
better in catalog convention — Codex decides per existing layout).

- Inherit `StrategyBase`.
- `name = "zz_pivot_v60_sr"`
- `mode = "scalp"` or appropriate
- `strategy_type = "MR"` (mean reversion at trend extreme)
- Implement entry/exit logic exactly as spec above.
- Expose `loser_zone` flag on the `Candidate` so position sizer can read it.

### 2. Position sizer integration

Find the existing position sizing path in fx-ai-trader (likely
`modules/demo_trader.py` or `modules/position_sizer.py`). Add hook:

- If candidate has `loser_zone == True` and strategy is `zz_pivot_v60_sr`:
  pct_of_equity = 0.05 (instead of default 0.10).
- Else: 0.10.

Use existing infrastructure if there's a per-strategy size override.

### 3. Catalog registration

- Add `zz_pivot_v60_sr` to the strategy catalog with:
  - `instruments: ["EUR_USD"]`
  - `timeframe: "M15"`
  - `mode: "scalp"`
  - `strategy_type: "MR"`
  - **Tier: LIVE** (not Shadow) — intentional exception
  - `is_shadow: False` (mark `is_shadow=0` per memory `feedback_live_shadow_separation`)
  - H1 Gate: **bypass** with flag `intentional_exception=True` similar to vix_carry/Kalman pattern

### 4. OANDA execution

- Use existing OANDA broker integration (same path as Kalman D7, vix_carry).
- Order type: market.
- SL: hard stop at `4 × ATR(14)` from entry (must persist with order, not strategy-side simulated).
- No TP order.
- Exit on signal: when opposite extreme detected AND `bars_in_trade >= 5`, close position
  at market.

### 5. Watchdog observability (Codex MUST implement even though user opted "Manual review")

Add to `tools/` a lightweight monitoring script:

```python
# tools/zz_pivot_live_monitor.py
# - Pulls last 7d + 30d Live PnL/PF/WR/MaxDD for zz_pivot_v60_sr
# - Logs to Discord channel daily at 00:30 JST
# - DOES NOT auto-stop (per user judgment) but flags thresholds visibly:
#   - 30d PF < 1.10: ⚠️ flag
#   - 7-day consecutive loss: 🚨 alert
#   - 30d MaxDD > 0.5%: 🚨 alert
```

### 6. Pre-registered withdrawal conditions (memo only, manual review)

Record in `knowledge-base/wiki/index.md` under "Live strategies — Intentional exceptions":
- ZZ Pivot v60 SR: 30d PF < 1.0 OR 14-day consecutive loss OR MaxDD > 1% → user manual stop

## Verification checklist (Codex MUST run before deploy)

1. ✅ Strategy entry/exit unit tests reproduce 207 trades on EURUSD M15 2025-05-26 → 2026-05-26
   - Sanity tolerance: ±5 trades vs Pine BT (different bar-close timing acceptable)
2. ✅ SizeReduce active: 30 trades flagged `loser_zone=True` (matches Pine WFO sim)
3. ✅ MASSIVE data source used for BT (not Yahoo)
   - per memory `feedback_bt_must_use_massive`
4. ✅ Pre-commit hook passes (or document why bypassed per memory
   `project_fxai_stale_test_backlog_2026_05_07.md`)
5. ✅ Render preview deploy runs without crash for 10 minutes
6. ✅ First Live signal hits OANDA with correct lot size (verify in oanda_audit table)

## Quant rigor disclosure

**N/WR**: 207 / 48.31% baseline → SR variant maintains same trade count, same WR
**EV**: baseline +$57.73 → SR +$65.10 (USD per 1y, 0.5–0.6% of $10k)
**PF**: baseline 1.222 → SR 1.294
**Kelly**: not computed (deferred to Live shadow audit, N=207 insufficient for
robust Kelly without per-fold variance)
**Wilson_lo**: 50% WR ± Wilson(N=207, p=0.5) lower bound ≈ 43.4%, threshold acceptable
**Bonferroni**: 3-fold WFO sign test p=0.125 (3/3 directional wins, NOT statistically
significant at α=0.05). Reported transparently.
**OOS/WF**: 1y OOS baseline + 3-fold WFO on same period. **No truly independent OOS
period yet** (this is a known weakness).

**User judgment**: Despite Bonferroni failure and lack of independent OOS, user has
declared intentional exception based on:
- Cell stats consistency with WFO directionality (all 3 folds positive)
- SizeReduce mechanism logically sound (no entry timing shift, only exposure)
- Memory pattern: Kalman D7 and vix_carry 1x are precedent intentional exceptions

## Files Codex should touch

- `strategies/scalp/zz_pivot_v60_sr.py` (NEW)
- `modules/demo_trader.py` (position sizing hook)
- `config/strategy_catalog.yaml` or equivalent (registration)
- `tools/zz_pivot_live_monitor.py` (NEW watchdog)
- `tests/strategies/test_zz_pivot_v60_sr.py` (NEW unit + integration)
- `knowledge-base/wiki/index.md` (intentional exception note)
- `knowledge-base/wiki/log.md` (today's deploy entry)

## Time budget

Estimate 6–12h (per user "OANDAに転送できるようにfx-ai-trader にpython 実装進めて").
Codex must split into smaller PRs if hitting timeout:
- PR1: Strategy file + unit tests (BT reproduction)
- PR2: Position sizer hook + catalog reg
- PR3: OANDA execution path + watchdog
- PR4: Memory + wiki entries

## Memory triggers (after deploy)

Claude (司令塔) will add:
- `project_zz_pivot_v60_sr_live_2026_05_28.md` — deploy record + pre-reg conditions
- Update `MEMORY.md` index with new entry
- Per `feedback_claude_codex_division`: deploy verification owned by Claude post-Codex
