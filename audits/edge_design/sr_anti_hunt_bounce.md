---
strategy: sr_anti_hunt_bounce
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

15m daytrade の SR 近接反転を、低 ADX・直近 hunt wick 不在・反転足で確認して entry し、SL は通常 swing 直外ではなく pair 別 P90 hunt excursion + ATR buffer の外側へ置く defensive MR / anti-hunt bounce thesis。5 majors 全走で real-time data を蓄積し、pair 別に後判定する設計もコード上に明示されている。`strategies/daytrade/sr_anti_hunt_bounce.py:2`, `strategies/daytrade/sr_anti_hunt_bounce.py:4`, `strategies/daytrade/sr_anti_hunt_bounce.py:5`, `strategies/daytrade/sr_anti_hunt_bounce.py:9`, `strategies/daytrade/sr_anti_hunt_bounce.py:16`, `strategies/daytrade/sr_anti_hunt_bounce.py:34`, `strategies/daytrade/sr_anti_hunt_bounce.py:36`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、entry は `sym in 5 majors ∧ sr_levels exists ∧ ADX < 30 ∧ min(|entry-level|) <= 0.4ATR ∧ candle body confirms direction ∧ no recent hunt wick`。BUY は `entry > level ∧ entry > open`、SELL は `entry <= level ∧ entry < open` で SR 近接反転を捕捉する。BB%B oversold/overbought は hard trigger ではなく score bonusに留まるが、SR proximity + reversal body が primary trigger なので thesis との大枠整合はある。`strategies/daytrade/sr_anti_hunt_bounce.py:37`, `strategies/daytrade/sr_anti_hunt_bounce.py:39`, `strategies/daytrade/sr_anti_hunt_bounce.py:40`, `strategies/daytrade/sr_anti_hunt_bounce.py:61`, `strategies/daytrade/sr_anti_hunt_bounce.py:63`, `strategies/daytrade/sr_anti_hunt_bounce.py:65`, `strategies/daytrade/sr_anti_hunt_bounce.py:68`, `strategies/daytrade/sr_anti_hunt_bounce.py:78`, `strategies/daytrade/sr_anti_hunt_bounce.py:81`, `strategies/daytrade/sr_anti_hunt_bounce.py:88`, `strategies/daytrade/sr_anti_hunt_bounce.py:93`, `strategies/daytrade/sr_anti_hunt_bounce.py:119` |
| 3 (timing window) | LOOKAHEAD | `ctx.entry` と `ctx.open_price` で現在足の実体方向を判定しており、戦略内には「確定済み signal bar を使う」contract、signal timestamp、同一 15m bar dedup がない。`_confirmed_no_recent_hunt()` は `df.iloc[-3:-1]` で current row を除外するため hunt 判定自体の look-ahead は抑えているが、entry/reversal 判定は実行層が intrabar evaluate すると未確定足で変動し、同一 bar 多重 entry に寄る。既存 lesson でも `sr_anti_hunt_bounce/USD_JPY` は 15m dedup violation 21 件 / -357p が記録されている。`strategies/daytrade/sr_anti_hunt_bounce.py:59`, `strategies/daytrade/sr_anti_hunt_bounce.py:68`, `strategies/daytrade/sr_anti_hunt_bounce.py:81`, `strategies/daytrade/sr_anti_hunt_bounce.py:88`, `strategies/daytrade/sr_anti_hunt_bounce.py:90`, `strategies/daytrade/sr_anti_hunt_bounce.py:149`, `strategies/daytrade/sr_anti_hunt_bounce.py:151`, `strategies/daytrade/sr_anti_hunt_bounce.py:153` |
| 4 (filter coherence) | STRENGTHENS | 5 majors whitelist は data accumulation 目的では NEUTRAL だが pair edge を保証しない。`ADX < 30` は range/MR bounce を強化し、MA filter on MR の破壊例ではない。直近 2 本の large hunt wick 除外は defensive bounce thesis では「SR がすでに強く破られた局面を避ける」filter として STRENGTHENS。Round-number SL expansion / TP inside shift は hunt concentration を意識した execution filter で、HMM gate same-trap 型の regime tail hard block ではない。`strategies/daytrade/sr_anti_hunt_bounce.py:37`, `strategies/daytrade/sr_anti_hunt_bounce.py:40`, `strategies/daytrade/sr_anti_hunt_bounce.py:41`, `strategies/daytrade/sr_anti_hunt_bounce.py:65`, `strategies/daytrade/sr_anti_hunt_bounce.py:93`, `strategies/daytrade/sr_anti_hunt_bounce.py:149`, `strategies/daytrade/sr_anti_hunt_bounce.py:160`, `strategies/daytrade/sr_anti_hunt_bounce.py:164`, `strategies/daytrade/sr_anti_hunt_bounce.py:184`, `strategies/daytrade/sr_anti_hunt_bounce.py:194`, `strategies/daytrade/sr_anti_hunt_bounce.py:197`, `strategies/daytrade/sr_anti_hunt_bounce.py:206` |
| 5 (stop/TP geometry) | ALIGNED | SL は pair 別 `P90_excursion_pip + 0.5ATR` を SR level 外側へ置き、round number 近傍ではさらに 1.3x expansion する。TP は対側 SR があればそれを優先し、なければ nominal `TARGET_RR=2.0`、entry 後は `MIN_RR=1.5` 未満を拒否する。MR として「mean に戻る前に通常 wick で切られない wide stop」は満たしており、anti-hunt thesis と整合する。`strategies/daytrade/sr_anti_hunt_bounce.py:43`, `strategies/daytrade/sr_anti_hunt_bounce.py:51`, `strategies/daytrade/sr_anti_hunt_bounce.py:54`, `strategies/daytrade/sr_anti_hunt_bounce.py:55`, `strategies/daytrade/sr_anti_hunt_bounce.py:100`, `strategies/daytrade/sr_anti_hunt_bounce.py:108`, `strategies/daytrade/sr_anti_hunt_bounce.py:109`, `strategies/daytrade/sr_anti_hunt_bounce.py:179`, `strategies/daytrade/sr_anti_hunt_bounce.py:182`, `strategies/daytrade/sr_anti_hunt_bounce.py:184`, `strategies/daytrade/sr_anti_hunt_bounce.py:191`, `strategies/daytrade/sr_anti_hunt_bounce.py:192`, `strategies/daytrade/sr_anti_hunt_bounce.py:196`, `strategies/daytrade/sr_anti_hunt_bounce.py:204`, `strategies/daytrade/sr_anti_hunt_bounce.py:205` |
| 6 (pair-regime fit) | FORCED | Code は USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY を一括許可するが、既存 Phase 2 sim と本番実測は pair 差が大きい。USD_JPY/EUR_USD/GBP_USD は Phase 2 sim では EV/PF/Kelly が positive、EUR_JPY/GBP_JPY は sim 時点で negative。2026-04-28 本番実測では GBP_USD だけ +0.31p と marginal positive、他 4 pair は negative。下表参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative live | Phase 2 365d sim は per-pair Wilson lower / PF / Kelly を持つが、tier-master の phase0_shadow 365d BT EV は `—`。本番実測は N=300, WR=26%, EV=-1.19p, sum=-355.7p で明確に negative。ただし live PF、exact Bonferroni-adjusted p、WF folds>=3、aggregate Kelly は同一 decision source で揃わず、`feedback_partial_quant_trap.md` 基準では N/WR/EV だけで採用判断不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED / timing-contaminated | Phase 2 sim: N=53 hunts, Wilson lower 46.9%, trade EV +0.55p, PF 1.046, Kelly +0.018。Live: N=173, WR 26%, mean -1.41p, sum -243.9p。15m dedup violation は USD_JPY で 21 件 / -357p。 |
| EURUSD | FORCED / weak | Phase 2 sim: N=81, Wilson lower 54.6%, trade EV +0.57p, PF 1.060, Kelly +0.029。Live: N=65, WR 20%, mean -1.12p, sum -72.7p。 |
| GBPUSD | FIT / marginal | Phase 2 sim: N=104, Wilson lower 47.1%, trade EV +6.45p, PF 1.997, Kelly +0.257。Live: N=50, WR 34%, mean +0.31p, sum +15.5p。ただし +0.31p は friction 1 click で消える水準。 |
| EURJPY | FORCED | Phase 2 sim: N=31, Wilson lower 29.2%, trade EV -6.19p, PF 0.599, Kelly -0.237。Live: N=8, WR 25%, mean -4.59p, sum -36.7p。 |
| GBPJPY | FORCED | Phase 2 sim: N=39, Wilson lower 16.5%, trade EV -10.95p, PF 0.444, Kelly -0.495。Live: N=4, WR 25%, mean -4.47p, sum -17.9p。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、本番実測 N=300 / EV=-1.19p / sum=-355.7p で underperforming として failure mode 診断を適用する。破綻軸は Axis 3。Axis 2 は SR proximity + reversal body で thesis を捕捉しており、Axis 4 の ADX/range/hunt filters は MR thesis を破壊していない。Axis 5 も P90 hunt excursion 外側の wide stop で anti-hunt thesis と整合する。一方、15m 戦略として signal bar close / execution bar / per-bar dedup の contract が strategy file に無く、既存 production audit でも USD_JPY の同一 15m bar 再発火が大きな損失と統計汚染を作っている。

再設計案は timing を 1 系統で修正する。`evaluate()` は `ctx.df.iloc[-2]` を signal bar として SR proximity、反転足、BB%B bonus を判定し、`ctx.entry` は次 bar execution price として扱う。さらに `(symbol, strategy_name, signal_bar_time, signal)` の dedup key を strategy state か dispatch layer に渡し、同一 15m bar で BUY/SELL や複数 SR level が再 emit されないようにする。pair scope は redesign 検証では GBPUSD only、または Phase 2 positive の USDJPY/EURUSD/GBPUSD のみに縮小し、EURJPY/GBPJPY は既存 evidence 上は除外する。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は維持する。SR 近接反転を low-ADX range で拾い、SL を P90 hunt excursion の外側へ置く thesis はコードから明確に導出でき、trigger/filter/SLTP の大枠も破綻していない。現状の負け方は、15m bar の確定性と emit 粒度が崩れて同一 bar の phantom entries を許した timing / execution contract の問題が主因と見る。

具体修正は `evaluate()` の入力 bar を確定足へ固定すること。`ctx.entry > ctx.open_price` / `< ctx.open_price` の判定を current tick ではなく signal bar の `Close > Open` / `Close < Open` に置換し、SR proximity も signal bar close で判定する。Candidate には signal bar timestamp を持たせるか、dispatch 側で `(symbol, entry_type, timeframe=15m, signal_bar_time, direction)` を dedup key にする。pair はまず GBPUSD-only または USDJPY/EURUSD/GBPUSD の Phase 2 positive subset で 365d + WF folds>=3 を再発行し、EURJPY/GBPJPY は redesign BT で PF/Kelly が positive になるまで `FORCED` 扱いで外す。

採用前に必要な検証は新規 BT だが、本 audit では実行しない。必要 artifact は pair 別、365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 audit DB / tier-master source で出すこと。N/WR/EV だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Live production: N=300 closed total; pair split USD_JPY 173 / EUR_USD 65 / GBP_USD 50 / EUR_JPY 8 / GBP_JPY 4. Phase 2 sim hunt sample: USD_JPY 53 / EUR_USD 81 / GBP_USD 104 / EUR_JPY 31 / GBP_JPY 39. | audit DB summary: `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md`; `knowledge-base/wiki/lessons/lesson-shadow-always-emit-cleanup-2026-04-28.md` |
| Win rate | Live production: 26% aggregate; pair split USD_JPY 26%, EUR_USD 20%, GBP_USD 34%, EUR_JPY 25%, GBP_JPY 25%. | audit DB summary: `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md` |
| Wilson lo (95%) | Live aggregate derived from N=300, WR=26%: 21.36%. Phase 2 sim per-pair Wilson lower: USD_JPY 46.9%, EUR_USD 54.6%, GBP_USD 47.1%, EUR_JPY 29.2%, GBP_JPY 16.5%. | audit DB summary + Wilson formula; `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md` |
| PF | Phase 2 sim per-pair PF: USD_JPY 1.046, EUR_USD 1.060, GBP_USD 1.997, EUR_JPY 0.599, GBP_JPY 0.444. Live production PF is INSUFFICIENT_EVIDENCE: not emitted in existing tier-master/audit DB summary. | `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md`; prompt tier-master input EV `—` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: quarterly stability notes exist, but WF folds>=3 with fold-level PF/Kelly are not present for this strategy in tier-master/audit DB. | `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md`; prompt tier-master input |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE for exact values: Phase 2 note says 4 pairs Bonferroni significant on reversal-WR, but exact adjusted p-values are not emitted; live production adjusted p is unavailable. | `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md` |
| Kelly fraction | Phase 2 sim per-pair Kelly: USD_JPY +0.018, EUR_USD +0.029, GBP_USD +0.257, EUR_JPY -0.237, GBP_JPY -0.495. Live production Kelly is INSUFFICIENT_EVIDENCE: payoff distribution / PF not emitted in existing tier-master/audit DB summary. | `knowledge-base/wiki/strategies/sr-anti-hunt-bounce.md`; prompt tier-master input EV `—` |
