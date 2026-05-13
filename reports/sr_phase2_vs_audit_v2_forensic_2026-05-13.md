# Phase 2 BT vs Audit v2 Methodology Divergence Forensic

## 1. Call Graph Mapping

### Phase 2 BT (sr_anti_hunt_bounce path)

- `tools/sr_weight_phase2_bin_bhfdr.py:19-22` sets `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, `NO_AUTOSTART=1`.
- `tools/sr_weight_phase2_bin_bhfdr.py:69-76` registers `sr_anti_hunt_bounce` as 15m daytrade over 5 majors.
- `tools/sr_weight_phase2_bin_bhfdr.py:808-852` `main()` imports `app`, patches `app.compute_daytrade_signal`, loops targets/pairs, then extracts rows from `result.trade_log`.
- `tools/sr_weight_phase2_bin_bhfdr.py:691-700` `_run_target_pair()` clears app/data caches, monkey-patches `app.compute_daytrade_signal = _compute_sr_anti_hunt_only_signal`, then calls `app.run_daytrade_backtest(symbol, 365, "15m", backtest_mode=True)`.
- `app.py:6231-6306` `run_daytrade_backtest()` fetches MASSIVE data via `fetch_ohlcv()`, runs `add_indicators()`, then `dropna()`.
- `app.py:6370-6377` precomputes rolling SR cache every 80 bars from prior 400 bars using `find_sr_levels_weighted(window=5, tolerance_pct=0.003, min_touches=2, max_levels=8, bars_per_day=96)`.
- `app.py:6384-6441` iterates every eligible bar (`range(..., step=1)`), applies volume/range/session/cascade gates, builds `bar_df = df.iloc[max(0, i - 3500):i + 1]`, and calls patched `compute_daytrade_signal()`.
- `tools/sr_weight_phase2_bin_bhfdr.py:397-430` `_compute_sr_anti_hunt_only_signal()` builds `SignalContext` from the latest row, passes `sr_levels` both as float list and as weighted `layer3`, sets `regime={"regime": "RANGE"}`, forwards `backtest_mode`, and calls `SrAntiHuntBounce().evaluate(ctx)`.
- `strategies/daytrade/sr_anti_hunt_bounce.py:61-64` dispatches to redesign v2 only when `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2=1`; otherwise legacy path.
- `strategies/daytrade/sr_anti_hunt_bounce.py:66-162` legacy path applies 5-major pair gate, `ADX < 30`, nearest SR within `0.4 ATR`, candle body confirmation, recent-hunt rejection, anti-hunt SL/TP, and `RR >= 1.5`.
- `app.py:6443-6561` production BT then filters `WAIT`, unknown entry types, post-SL same-direction block, session/pair gate, and reason-quality gate.
- `app.py:6563-6685` entry is next bar open plus spread/slippage, TP is shifted to the filled entry then floored to at least `1.5 ATR`, SL is recomputed from `MIN_RR=1.2` except preserve-set strategies, session buffers may widen SL, and spread/SL gate can reject.
- `app.py:6733-6773` range TP override and quick-harvest may change TP, RR is rechecked, and final `sl_m`/`tp_m_actual` are computed.
- `app.py:6779-6940` native exit loop runs up to `min(MAX_HOLD=24, strategy_max_hold=12)`, with BE/trailing SL, time-decay SL, signal-reverse exit, close-confirmed SL logic, ambiguous same-bar TP/SL resolved by close direction, and post-exit cooldown.
- `tools/sr_weight_phase2_bin_bhfdr.py:356-385` extracts only `entry_type == "sr_anti_hunt_bounce"` and recomputes SR metadata post-hoc with `find_sr_levels_weighted()` over up to 365d history.

### Audit v2 (sr_anti_hunt_bounce path)

- `tools/sr_weight_gate_audit_v2.py:22-25` sets `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, `NO_AUTOSTART=1`.
- `tools/sr_weight_gate_audit_v2.py:36-49` defines 5 majors and strategy universe.
- `tools/sr_weight_gate_audit_v2.py:64-70` sets `RUN_STRIDES["sr_anti_hunt_bounce"] = 4`.
- `tools/sr_weight_gate_audit_v2.py:156-174` `load_data()` reads MASSIVE parquet, truncates to last 365 days, and for 15m runs `modules.indicators.add_indicators().dropna()`.
- `tools/sr_weight_gate_audit_v2.py:1223-1250` `run_all()` loads 15m/1h data, resamples 1D/1W, computes one global SR level set per pair, then calls `run_strategy_bt(..., stride=RUN_STRIDES[strategy])`.
- `tools/sr_weight_gate_audit_v2.py:339-439` `detect_sr_levels_with_weight()` uses either KDE detector or pivot adapter, enriches own/D1/W1 touches, round score, magnitude, composite weight, and sorts global levels.
- `tools/sr_weight_gate_audit_v2.py:689-774` `run_strategy_bt()` imports the strategy class, resets class dedup if present, loops `for i in range(spec.min_bars, len(df) - 13, stride)`, prefilters, builds context, calls `evaluate()`, post-hoc dedups by `(strategy, symbol, signal, rounded_level, 2h bucket)`, simulates exit, and appends a row.
- `tools/sr_weight_gate_audit_v2.py:657-666` `_prefilter_strategy_bar()` duplicates key anti-hunt gates before `evaluate()`: 5 majors, `ADX < 30`, nearest global level within `0.45 ATR`.
- `tools/sr_weight_gate_audit_v2.py:511-565` `_build_ctx()` builds `SignalContext` from current row, with full weighted dict `sr_levels`, structured `layer3`, `regime={"regime": "RANGE"}`, `htf={"agreement": "mixed"}`, and `backtest_mode=True`.
- `strategies/daytrade/sr_anti_hunt_bounce.py:61-64` then chooses legacy/v2 branch by env exactly as in Phase 2.
- `tools/sr_weight_gate_audit_v2.py:622-648` `_simulate_exit()` checks raw high/low TP/SL for at most 12 bars, treats same-bar TP+SL as SL first, and otherwise exits at timeout close.

## 2. Divergence Matrix

| Axis | Phase 2 BT | Audit v2 | Match? | Severity | Estimated N Impact |
|---|---|---|---|---|---|
| Bar iteration cadence | `app.py:6384`: stride=1 over eligible bars, then trade-level cooldown after exits (`app.py:6920`) | `tools/sr_weight_gate_audit_v2.py:64-70`, `709`: fixed stride=4 before evaluation | No | 🔴 dominant | v2 report records buggy stride=1 anti-hunt N=1441 vs fixed N=335; this axis alone can move N by ~4.3x. It can fully explain why v2 fixed is below Phase 2, but stride=1 without production cooldown overshoots 594. |
| Dedup / cooldown | Exit-based `last_bar = i + 1 + bars_held` plus cascade/post-SL blocks (`app.py:6384-6389`, `6450-6453`, `6918-6924`) | Post-hoc 2h bucket dedup by strategy/symbol/signal/level (`tools/sr_weight_gate_audit_v2.py:729-738`) | No | 🔴 dominant | Phase 2 cooldown is outcome-duration dependent; audit dedup is level/time-bucket dependent. Existing v1/fixed delta implies this pair with stride is a multi-x reducer. |
| SR levels source and freshness | Rolling cache every 80 bars from prior 400 bars, max 8 levels (`app.py:6370-6377`) | One global 365d level set per pair; KDE or pivot, max 30 own plus D1/W1 enrichment (`tools/sr_weight_gate_audit_v2.py:1239-1243`, `339-439`) | No | 🔴 dominant | PIVOT audit N=140 vs KDE N=335 on same runner; detector/global-level choice moves N by 2.4x. Rolling 400-bar freshness can plausibly move another 1.3-2x versus global 365d levels. |
| Detector parameters | `find_sr_levels_weighted(... tolerance_pct=0.003, max_levels=8)` (`app.py:6375-6377`) | KDE: `detect_sr_levels`; PIVOT: pip tolerance converted from median ATR, own max 30 (`tools/sr_weight_gate_audit_v2.py:367-400`) | No | 🟠 material | Even PIVOT is not parameter-equivalent to Phase 2. PIVOT v2 falls to 140, so detector alignment by name is insufficient. |
| Pair filtering | Target list is 5 majors (`tools/sr_weight_phase2_bin_bhfdr.py:39-43`, `69-76`) and strategy pair gate (`sr_anti_hunt_bounce.py:67-69`) | Same 5 majors (`tools/sr_weight_gate_audit_v2.py:36-42`) and prefilter/strategy pair gate (`657-664`) | Mostly | 🟢 negligible | Pair universe is not the N mismatch. Existing per-pair Phase 2 totals sum exactly to 594. |
| Pre-evaluate gates | Production BT applies volume, bar range, session, cascade before patched signal (`app.py:6384-6421`) | Audit applies only strategy-specific prefilter before evaluate (`tools/sr_weight_gate_audit_v2.py:657-666`) | No | 🟠 material | Phase 2 has more pre-gates, which should usually lower N, but because audit also stride/dedups, net direction is mixed. Session gate blocks many off-hours Phase 2 bars; audit KDE has many off-hours timestamps. |
| Context row timing | Legacy branch evaluates latest row in `bar_df` at bar `i` (`tools/sr_weight_phase2_bin_bhfdr.py:404-429`) | Same current row in `_build_ctx()` for legacy branch (`tools/sr_weight_gate_audit_v2.py:514-565`) | Yes for legacy | 🟢 negligible | If env is legacy, row timing inside `evaluate()` matches. |
| Context `sr_levels` type | Phase 2 converts `ctx.sr_levels` to floats but keeps dicts in `layer3` (`tools/sr_weight_phase2_bin_bhfdr.py:423-424`) | Audit passes full dict list as `ctx.sr_levels` (`tools/sr_weight_gate_audit_v2.py:521-559`) | No | 🟡 minor | Strategy handles both dict and float levels. Metadata differs, but entry gating mostly uses price; likely <1.3x alone. |
| Context indicators | Both use `modules.indicators.add_indicators()` via app import or direct module import (`app.py:210-215`; `tools/sr_weight_gate_audit_v2.py:156-174`) | Same implementation | Yes | 🟢 negligible | USDJPY 365d check: rows 24644 vs 24644; max absolute diff for adx/atr/ema/bb_pband was 0.0; ADX<30 count was 18631 in both. |
| Regime / HTF | Phase 2 patched context sets `regime=RANGE`; production runner also passes rolling HTF cache but patched strategy only stores it (`tools/sr_weight_phase2_bin_bhfdr.py:425-426`; `app.py:6391-6394`) | Audit sets `regime=RANGE`, `htf=mixed` (`tools/sr_weight_gate_audit_v2.py:560-562`) | Mostly | 🟢 negligible | SrAntiHuntBounce does not use `ctx.htf` or `ctx.regime`; no material N effect. |
| SL/TP geometry before exit | Strategy candidate SL/TP returned, then Phase 2 production runner shifts entry to next open, floors TP to 1.5 ATR, usually recomputes SL from `MIN_RR=1.2`, applies session SL buffer and spread/SL gate (`app.py:6563-6685`) | Audit uses raw candidate entry/SL/TP from evaluate without spread/slippage or production geometry rewrites (`tools/sr_weight_gate_audit_v2.py:720-739`) | No | 🟠 material | This mostly changes outcomes/EV and time-in-trade; it also changes cooldown timing in Phase 2, so it can materially change N through exit-based cooldown. |
| Exit simulation | BE/trailing/time-decay/signal-reverse/close-confirmed SL; ambiguous TP+SL resolved by close direction; max hold min(24, strategy hold=12) (`app.py:6779-6916`) | Raw high/low TP/SL; same-bar ambiguous always SL; timeout close; max hold 12 (`tools/sr_weight_gate_audit_v2.py:622-648`) | No | 🟠 material | Direction on count is indirect via cooldown: Phase 2 exits can happen earlier/later and therefore open/close future opportunities. Audit count itself is independent of exit except no overlapping-position model. |
| Friction / spread | Entry and exit spread/slippage, spread/SL reject, PnL in ATR multiple then pips in Phase 2 extractor (`app.py:6579-6592`, `6681-6685`; `tools/sr_weight_phase2_bin_bhfdr.py:372-373`) | No spread/slippage; `pnl_pip` direct price diff / pip (`tools/sr_weight_gate_audit_v2.py:622-648`, `761`) | No | 🟡 minor for N, 🟠 material for EV | Spread/SL gate can reject some Phase 2 entries; otherwise mostly EV/outcome. |
| PnL normalization | Existing Phase 2 result reports EV_R, while current script shows pips conversion from `_trade_pnl_m * atr * pip_mult` (`tools/sr_weight_phase2_bin_bhfdr.py:103-107`, `372-373`) | Direct pip PnL from simulated price path (`tools/sr_weight_gate_audit_v2.py:622-648`) | No | 🟢 negligible for N | Affects EV comparability, not signal count. |
| Result artifact granularity | Existing Phase 2 JSON has `event_count=4942` and strategy aggregates/run_meta, but no `trades` array | Audit parquet has per-signal rows with timestamps | No | 🟢 negligible | Blocks direct Phase2-v2 timestamp Jaccard unless Phase 2 is rerun or original trade log is recovered. |

New divergence beyond the prompt examples: Phase 2 production runner rewrites candidate SL/TP geometry after `evaluate()` and then uses exit-dependent cooldown; audit v2 does neither. This couples exit methodology back into signal count.

## 3. Hypothesis Test

- H1 (bar cadence): **PASS / dominant contributor**. Audit v2 fixed uses stride=4 (`tools/sr_weight_gate_audit_v2.py:64-70`, `709`) while Phase 2 iterates step=1 (`app.py:6384`). Existing audit report states buggy stride=1 anti-hunt N=1441 and fixed N=335, a ~4.3x reduction. Estimated contribution to 594 vs 335: +77% needed from 335 to 594; H1 can cover this, but unthrottled stride=1 would overshoot Phase 2 by ~142%, so not single-cause in isolation.
- H2 (sr_levels populate): **PASS / dominant-material contributor**. Phase 2 uses rolling 400-bar, 80-bar refresh, max 8 pivot levels (`app.py:6370-6377`); audit v2 uses one global 365d KDE/PIVOT set (`tools/sr_weight_gate_audit_v2.py:1239-1243`). KDE N=335 vs PIVOT N=140 on the same audit runner shows detector/level source alone moves N by 2.4x. The Phase 2 rolling-cache method is neither audit KDE nor audit PIVOT, so this is a co-dominant mismatch.
- H3 (ctx fields): **FAIL as N cause**. Both pipelines use `modules.indicators.add_indicators()` (`app.py:210-215`; `tools/sr_weight_gate_audit_v2.py:156-174`). USDJPY 365d dynamic check found identical rows and max absolute diff 0.0 for `adx`, `atr`, EMAs, and `bb_pband`; `ADX < 30` count was 18631 in both. Estimated contribution: <1%.
- H4 (SL/TP exit): **PARTIAL / material indirect contributor**. Audit exit is simple 12-bar high/low with SL-first ambiguity (`tools/sr_weight_gate_audit_v2.py:622-648`); Phase 2 applies production entry fill, geometry rewrites, spread/SL reject, BE/trailing/time-decay/signal-reverse, and exit-based cooldown (`app.py:6563-6940`). This does not create raw candidates directly, but it changes future eligibility through cooldown. Estimated N contribution: 10-40%, larger for clustered SR signals.
- H5 (backtest_mode / redesign env): **PARTIAL but likely not the observed mismatch**. Both paths pass `backtest_mode=True` (`tools/sr_weight_phase2_bin_bhfdr.py:426`; `tools/sr_weight_gate_audit_v2.py:562`). Strategy dispatch depends on `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2` (`strategies/daytrade/sr_anti_hunt_bounce.py:61-64`). Current shell env has this unset, and neither runner sets it. If the original Phase 2 run externally set it to `1`, the closed-bar v2 branch (`strategies/daytrade/sr_anti_hunt_bounce.py:164-264`) would be a dominant methodology break; however no existing artifact records that env. Estimated observed contribution: 0% if unset; potentially >50% if set externally.

## 4. Dominant Cause Verdict

Single dominant divergence: **None**.

Verdict: **multi-factor with H1 + H2 dominant, H4 material**.

Ranked contribution estimate:

1. **H1 cadence + audit post-hoc dedup vs Phase 2 exit-cooldown**: dominant. Existing v1/fixed audit delta (1441 -> 335) proves this class can move anti-hunt N by >4x. It explains why v2 audit is below Phase 2, but by itself does not land on 594.
2. **H2 SR level source/freshness/parameter mismatch**: dominant-material. Same audit runner changes 335 -> 140 when detector switches KDE -> PIVOT; Phase 2's rolling 400-bar pivot cache is a third method, not equivalent to either.
3. **H4 production SL/TP/exit/cooldown feedback**: material. It likely accounts for why Phase 2 is not simply audit stride=1/no-dedup N and why production-style count settles at 594 rather than the v1 audit's 1441.

The best explanation for **N=594** is: production runner enumerates bars at stride=1, but converts candidates into trades with production filters, fill/SL/TP rewrites, exit-dependent cooldown, and rolling local SR levels. Audit v2 instead samples every 4th bar, uses global SR levels, and post-hoc level-bucket dedup. No single detector switch can reconcile the count.

## 5. Decision Recommendation

Pipeline options:

- (a) **Phase 2 BT pipeline unified**: Pros: closest to production trade count, uses production filters/friction/exits/cooldown, avoids synthetic audit-only N. Cons: slow, harder to isolate pure SR level effects, trade logs must be persisted for reproducibility.
- (b) **v2 audit pipeline unified**: Pros: fast, deterministic, easy per-signal metadata and parquet diffing. Cons: no longer production-equivalent; fixed stride/dedup/global SR levels can manufacture counts/outcomes that do not map to production.
- (c) **Both in parallel**: Pros: preserves fast exploratory audit and production confirmation. Cons: requires explicit naming and no cross-comparison of N/EV unless methodology bridge is defined.

Recommended path: **(c) both in parallel**, with Phase 2 BT as the canonical production-count verdict and v2 audit as exploratory SR-weight metadata only. The immediate next redesign should add a "production-compatible audit mode" that reuses `app.run_daytrade_backtest` trade logs or mirrors its rolling SR cache, cooldown, and exit semantics before comparing N.

PR title:

`audit(sr-redesign): Phase 2 BT vs audit v2 methodology divergence forensic`

PR description excerpt:

Dominant Cause Verdict: multi-factor with H1 cadence/dedup + H2 SR level source dominant, H4 production exit/cooldown material. Decision Recommendation: run both pipelines, but treat Phase 2 BT as canonical production-count verdict and v2 audit as exploratory until it gains production-compatible mode.

## 6. Open Questions

- The existing Phase 2 JSON does not include a `trades` array or `trade_log`, so direct Phase2-v2 timestamp Jaccard and the optional CSV cannot be produced without recovering the original trade log or rerunning Phase 2, which was explicitly prohibited.
- The original commit/run environment did not record `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2`; current environment is unset and both scripts do not set it. Commander should confirm the May 11 shell env if H5 remains a concern.
- The current `tools/sr_weight_phase2_bin_bhfdr.py` source writes a `trades` field, but the existing May 11 JSON has an older schema (`event_count`, `strategy_aggregate`, `run_meta`). Any future audit should persist per-trade rows in the canonical artifact.
- Existing KDE vs PIVOT timestamp overlap for anti-hunt is extremely low: USDJPY 0/134 Jaccard union, EURUSD 10 overlap with Jaccard 0.2703, GBPUSD/EURJPY/GBPJPY 0 overlap. This confirms detector/global-level choice changes not only N but the identity of trades.
