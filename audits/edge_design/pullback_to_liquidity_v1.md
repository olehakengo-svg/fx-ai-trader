---
strategy: pullback_to_liquidity_v1
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

HTF(H4) trend が bull/bear に揃っている方向へ、M15 の過去 swing low/high まで pullback した局面で liquidity touch と rejection candle を確認し、trend resume を 2:1 payoff で取る TF/pullback thesis。これは docstring の mechanism thesis と locked entry 条件から直接導出できる。`strategies/daytrade/pullback_to_liquidity_v1.py:6`, `strategies/daytrade/pullback_to_liquidity_v1.py:7`, `strategies/daytrade/pullback_to_liquidity_v1.py:8`, `strategies/daytrade/pullback_to_liquidity_v1.py:10`, `strategies/daytrade/pullback_to_liquidity_v1.py:16`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | 大枠の trigger は `HTF agreement bull/bear ∧ prior M15 swing ∧ current liquidity touch ∧ rejection wick ∧ volume boost` で thesis と整合する（`strategies/daytrade/pullback_to_liquidity_v1.py:75`, `strategies/daytrade/pullback_to_liquidity_v1.py:84`, `strategies/daytrade/pullback_to_liquidity_v1.py:101`, `strategies/daytrade/pullback_to_liquidity_v1.py:122`, `strategies/daytrade/pullback_to_liquidity_v1.py:146`）。ただし locked comment は `current low/high ≤ swing ± 5pip` だが、実装は BUY `current_low <= swing_price * 1.001` / SELL `current_high >= swing_price * 0.999` の片側 `%` 条件で、固定 pip の近接判定でも `abs(current - swing) <= tolerance` でもない（`strategies/daytrade/pullback_to_liquidity_v1.py:13`, `strategies/daytrade/pullback_to_liquidity_v1.py:52`, `strategies/daytrade/pullback_to_liquidity_v1.py:115`, `strategies/daytrade/pullback_to_liquidity_v1.py:119`）。意図式: `abs(current_low - swing_low) <= 5pip`、実装式: `current_low <= swing_low * 1.001`。深い下抜け/上抜けも通すため、pullback-to-liquidity ではなく loose sweep/reversal へ広がる。 |
| 3 (timing window) | LOOKAHEAD | Swing は `swing_age_bars >= 5` で current bar 由来の swing を避けているが、touch/rejection/volume は同じ latest bar の High/Low/Open/Close/Volume を見て、`ctx.entry` を close として同 bar close entry する前提になっている（`strategies/daytrade/pullback_to_liquidity_v1.py:94`, `strategies/daytrade/pullback_to_liquidity_v1.py:101`, `strategies/daytrade/pullback_to_liquidity_v1.py:109`, `strategies/daytrade/pullback_to_liquidity_v1.py:125`, `strategies/daytrade/pullback_to_liquidity_v1.py:149`, `strategies/daytrade/pullback_to_liquidity_v1.py:186`）。さらに docstring の「直近 4 bars 内に同方向 entry 済み」禁止は実装内に状態がなく、同 bar/近接 bar の再 emit 抑止が外部依存である（`strategies/daytrade/pullback_to_liquidity_v1.py:22`, `strategies/daytrade/pullback_to_liquidity_v1.py:60`, `strategies/daytrade/pullback_to_liquidity_v1.py:186`）。 |
| 4 (filter coherence) | STRENGTHENS | `Asia_early` 除外は liquidity dead zone を避け、ATR min は低 vol の見せかけ touch を避けるため thesis を強化する（`strategies/daytrade/pullback_to_liquidity_v1.py:65`, `strategies/daytrade/pullback_to_liquidity_v1.py:72`）。HTF agreement gate は momentum/pullback thesis の中核で、MR に MA filter を足す破壊例とは異なる（`strategies/daytrade/pullback_to_liquidity_v1.py:75`, `strategies/daytrade/pullback_to_liquidity_v1.py:82`）。Volume confirmation は rejection が liquidity absorption である確度を上げる filter として coherent（`strategies/daytrade/pullback_to_liquidity_v1.py:146`, `strategies/daytrade/pullback_to_liquidity_v1.py:154`）。HMM regime gate same-trap 型の regime tail 破壊 filter は見当たらない。 |
| 5 (stop/TP geometry) | ALIGNED | TP は `2.0 * ATR`、SL は `1.0 * ATR` の 2:1 RR で、HTF trend resume を取りに行く momentum/pullback 型の非対称 payoff と整合する（`strategies/daytrade/pullback_to_liquidity_v1.py:24`, `strategies/daytrade/pullback_to_liquidity_v1.py:25`, `strategies/daytrade/pullback_to_liquidity_v1.py:26`, `strategies/daytrade/pullback_to_liquidity_v1.py:57`, `strategies/daytrade/pullback_to_liquidity_v1.py:58`, `strategies/daytrade/pullback_to_liquidity_v1.py:163`, `strategies/daytrade/pullback_to_liquidity_v1.py:168`）。ただし locked exit の `TIME_STOP: 24 bars` は Candidate に明示されておらず、exit executor 側に依存する（`strategies/daytrade/pullback_to_liquidity_v1.py:27`, `strategies/daytrade/pullback_to_liquidity_v1.py:186`, `strategies/daytrade/pullback_to_liquidity_v1.py:194`）。 |
| 6 (pair-regime fit) | FORCED | Code に pair whitelist がなく `ALL` 適用になりうる一方、pre-reg の Phase 3.A pair set は USD_JPY / EUR_USD / GBP_USD に限定されている。さらに touch tolerance が percentage 実装のため、pip scale が異なる pair へ ALL 外挿するほど liquidity zone の意味が崩れる。詳細は下表。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の 365d BT EV は prompt input で `—`、tier-master でも phase0_shadow 自動Shadowのみ。local audit DB `demo_trades.db` には `demo_trades` 18 rows / `evaluated_candidates` 0 rows / `oanda_audit` 0 rows があるが、この strategy の hit は 0。production routing audit でも `pullback_to_liquidity_v1 | None | False`。Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly は既存 evidence から採れない。 |

### Axis 6 Pair-Regime Fit Detail

| Pair | Fit | Basis |
|------|-----|-------|
| USD_JPY | FIT / INSUFFICIENT_EVIDENCE | Pre-reg Phase 3.A pair set に含まれる trend-following pullback 候補。ただし strategy-specific Wilson/PF/WF/Kelly は未提示。percentage tolerance は JPY pip scale で fixed 5pip 意図からズレる。 |
| EUR_USD | FIT / INSUFFICIENT_EVIDENCE | Pre-reg Phase 3.A pair set に含まれるが、既存 audit DB/tier-master に decision-grade metrics がない。 |
| GBP_USD | FIT / INSUFFICIENT_EVIDENCE | Pre-reg Phase 3.A pair set に含まれるが、既存 audit DB/tier-master に decision-grade metrics がない。 |
| EUR_JPY | FORCED | Pre-reg pair set 外。JPY pip scale かつ ALL 適用を正当化する pair-specific evidence がない。 |
| GBP_JPY | FORCED | Pre-reg pair set 外。trend continuation の可能性はあるが、strategy-specific evidence なし。 |
| Other ALL pairs | FORCED / UNTESTED | Code 上は pair gate がなく、tier-master / audit DB には ALL 外挿に必要な Wilson/PF/WF/Kelly がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で、Tier 3/4 専用の復活診断ではないが、入力 metrics は 365d BT EV `—` かつ audit DB hit 0 のため昇格前 failure mode として診断する。破綻軸は Axis 2 と Axis 3。思想は明確で、HTF trend pullback + liquidity rejection という thesis 自体は成立しうるが、liquidity touch が「固定 pip 近接」ではなく片側 percentage threshold になっており、pair 間で意味が変わる。加えて current bar の rejection close を見た同 bar entry と 4-bar same-direction dedup 未実装により、実運用/BT contract 次第で signal timing が汚れる。

再設計案は trigger/timing の 2 点。Trigger は `tolerance = 5 / ctx.pip_mult` のように fixed-pip 化し、BUY は `abs(current_low - swing_low) <= tolerance` または「下抜け許容は最大 1ATR/特定 pip まで」の bounded sweep にする。Timing は rejection bar を closed signal bar と明示し、execution は次 bar open/market に分離する。さらに `(instrument, signal, bar_time)` または `(instrument, signal, swing_idx)` ベースの last-emitted guard を strategy か execution layer に置き、locked docstring の 4-bar duplicate ban を実装する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想は維持する。最小修正は liquidity touch の数学を「片側 percentage」から「pair-aware fixed pip 近接 + bounded sweep」に変えること。想定 diff は `LIQUIDITY_TOUCH_PCT` を廃止して `LIQUIDITY_TOUCH_PIPS = 5.0` を導入し、`tol = self.LIQUIDITY_TOUCH_PIPS / ctx.pip_mult` を使って BUY `abs(current_low - swing_price) <= tol`、SELL `abs(current_high - swing_price) <= tol` にする形。stop hunt 的な深い sweep を許容したいなら、別 thesis として `current_low <= swing_low + tol and current_low >= swing_low - 0.5 * atr` のように下限/上限を明示する。

Timing 側は signal bar close と execution bar を分ける。`last_row = df.iloc[-1]` は確定済み signal bar とし、Candidate の entry price contract が next-bar execution でないなら executor 側を修正する。あわせて 4-bar same-direction dedup を実装してから、pre-reg 通り USD_JPY / EUR_USD / GBP_USD で 365d BT、5-fold WF、Bonferroni/Kelly を再集計する。現 evidence だけでは shadow 継続は可能でも promote 判定は不可。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: local audit DB hit 0 (`demo_trades` has 18 total rows but no `entry_type=pullback_to_liquidity_v1`; `evaluated_candidates` 0 rows; `oanda_audit` 0 rows) | audit DB: `demo_trades.db`; production routing: `raw/audits/production_routing_audit_2026-04-28.md` |
| Win rate | INSUFFICIENT_EVIDENCE: N=0 / tier-master EV `—` | audit DB + prompt tier-master input |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: no trade sample; pre-reg requires Wilson lower > 50%, but existing audit DB/tier-master has no strategy-specific value | audit DB: `demo_trades.db`; pre-reg validation requirement |
| PF | INSUFFICIENT_EVIDENCE: no wins/losses and tier-master 365d BT EV is `—`; PF not available | tier-master prompt input; `knowledge-base/wiki/tier-master.md` phase0_shadow entry |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: pre-reg requires 5-fold WF, but no completed fold metrics are present in tier-master/audit DB for this strategy | `knowledge-base/wiki/decisions/pre-reg-pullback-to-liquidity-v1-2026-04-26.md`; `knowledge-base/wiki/learning/phase3-bt-pre-reg-lock.md` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: pre-reg α exists, but no observed p-value exists for this strategy in tier-master/audit DB | pre-reg validation requirement; audit DB |
| Kelly fraction | INSUFFICIENT_EVIDENCE: no WR/PF/payoff sample; Kelly cannot be computed from N=0 and EV `—` | audit DB: `demo_trades.db`; prompt tier-master input |
