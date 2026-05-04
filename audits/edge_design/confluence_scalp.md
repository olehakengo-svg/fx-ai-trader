---
strategy: confluence_scalp
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

London/NY overlap かつ ATR が spread を十分吸収できる局面に限定し、EMA9/21 の短期トレンド方向へ、RSI5/BB%B の押し目・戻り目 extreme と MACD-H 反転が同時に出た時だけ入る trend-aligned pullback / early reversal scalp。CHoCH/MSB は構造転換の補強スコアであり、entry の必須条件ではない。`strategies/scalp/confluence_scalp.py:270`, `strategies/scalp/confluence_scalp.py:273`, `strategies/scalp/confluence_scalp.py:279`, `strategies/scalp/confluence_scalp.py:280`, `strategies/scalp/confluence_scalp.py:281`, `strategies/scalp/confluence_scalp.py:282`, `strategies/scalp/confluence_scalp.py:283`, `strategies/scalp/confluence_scalp.py:284`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | BUY は `(EMA9>EMA21 OR bull cross) AND RSI5<42 AND BB%B<0.30 AND MACD-H turns up`、SELL は `(EMA9<EMA21 OR bear cross) AND RSI5>58 AND BB%B>0.70 AND MACD-H turns down`。trend confirmation、pullback extreme、momentum inflection が thesis の 3 family confluence を数式化している。ただし CHoCH/MSB は signal 後の bonus で、MSS 単独 thesis としては hard gate ではない。`strategies/scalp/confluence_scalp.py:367`, `strategies/scalp/confluence_scalp.py:368`, `strategies/scalp/confluence_scalp.py:369`, `strategies/scalp/confluence_scalp.py:370`, `strategies/scalp/confluence_scalp.py:371`, `strategies/scalp/confluence_scalp.py:373`, `strategies/scalp/confluence_scalp.py:374`, `strategies/scalp/confluence_scalp.py:375`, `strategies/scalp/confluence_scalp.py:376`, `strategies/scalp/confluence_scalp.py:377`, `strategies/scalp/confluence_scalp.py:379`, `strategies/scalp/confluence_scalp.py:380`, `strategies/scalp/confluence_scalp.py:381`, `strategies/scalp/confluence_scalp.py:382`, `strategies/scalp/confluence_scalp.py:383`, `strategies/scalp/confluence_scalp.py:388`, `strategies/scalp/confluence_scalp.py:405`, `strategies/scalp/confluence_scalp.py:426`, `strategies/scalp/confluence_scalp.py:427`, `strategies/scalp/confluence_scalp.py:434` |
| 3 (timing window) | LOOKAHEAD | `evaluate()` は `ctx.ema9/rsi5/bbpb/macdh/entry` をそのまま読むが、strategy 内に closed-bar 固定や `(symbol, bar_time, signal)` dedup がない。CHoCH は `recent = df.iloc[-lookback:]` と `last_bar = recent.iloc[-1]` を使い、fractal swing 判定は後続 bar を必要とするため、df が未確定足を含む実行契約だと current bar 依存が混入する。明示的な未来参照とは断定しないが、bar-close / dedup 欠落は spec 上 LOOKAHEAD 寄りの timing risk。`strategies/scalp/confluence_scalp.py:45`, `strategies/scalp/confluence_scalp.py:51`, `strategies/scalp/confluence_scalp.py:53`, `strategies/scalp/confluence_scalp.py:78`, `strategies/scalp/confluence_scalp.py:84`, `strategies/scalp/confluence_scalp.py:333`, `strategies/scalp/confluence_scalp.py:388`, `strategies/scalp/confluence_scalp.py:405`, `strategies/scalp/confluence_scalp.py:425`, `strategies/scalp/confluence_scalp.py:426`, `strategies/scalp/confluence_scalp.py:516` |
| 4 (filter coherence) | STRENGTHENS | Session Gate は London/NY overlap に限定し、MFE Guard は ATR/Spread>=6 で摩擦耐性を要求するため scalp thesis を強化する。HTF Hard Block は trend-aligned pullback thesis には STRENGTHENS だが、CHoCH を主目的にするなら初動 reversal を消す可能性があるため注意点。ADX>25、HTF alignment、peak overlap、MFE quality、Stoch confirmation は score bonus で hard filter ではなく、MA filter on MR / HMM same-trap 型の edge-tail hard block にはなっていない。`strategies/scalp/confluence_scalp.py:290`, `strategies/scalp/confluence_scalp.py:291`, `strategies/scalp/confluence_scalp.py:292`, `strategies/scalp/confluence_scalp.py:294`, `strategies/scalp/confluence_scalp.py:298`, `strategies/scalp/confluence_scalp.py:311`, `strategies/scalp/confluence_scalp.py:312`, `strategies/scalp/confluence_scalp.py:342`, `strategies/scalp/confluence_scalp.py:351`, `strategies/scalp/confluence_scalp.py:357`, `strategies/scalp/confluence_scalp.py:389`, `strategies/scalp/confluence_scalp.py:406`, `strategies/scalp/confluence_scalp.py:441`, `strategies/scalp/confluence_scalp.py:447`, `strategies/scalp/confluence_scalp.py:453`, `strategies/scalp/confluence_scalp.py:458`, `strategies/scalp/confluence_scalp.py:463` |
| 5 (stop/TP geometry) | ALIGNED | SL=ATR7*1.2、TP=ATR7*2.5 なので通常 R:R は `2.5 / 1.2 = 2.08`。trend-aligned pullback / momentum continuation で利益方向の伸びを取りに行く asymm geometry と整合する。ただし `_min_sl` が発動する極小 ATR 局面では実効 R:R が低下し得る。`strategies/scalp/confluence_scalp.py:307`, `strategies/scalp/confluence_scalp.py:308`, `strategies/scalp/confluence_scalp.py:309`, `strategies/scalp/confluence_scalp.py:475`, `strategies/scalp/confluence_scalp.py:476`, `strategies/scalp/confluence_scalp.py:477`, `strategies/scalp/confluence_scalp.py:478`, `strategies/scalp/confluence_scalp.py:479`, `strategies/scalp/confluence_scalp.py:480`, `strategies/scalp/confluence_scalp.py:481`, `strategies/scalp/confluence_scalp.py:482`, `strategies/scalp/confluence_scalp.py:483` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。コードは EURGBP だけを無効化し、それ以外の ALL に広く適用するが、pair-specific の Wilson / PF / Kelly evidence はほぼ存在しない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は `—`。local `demo_trades.db` は `demo_trades` / `evaluated_candidates` / `oanda_audit` の `confluence_scalp` 行が 0 件。H1 bucket counterfactual は EUR_USD London N=1, WR=0%, Wilson lo=0.000, PF=0.00, Kelly=0.000, Bonferroni p=1.0000。180d scalp BT 参考値は aggregate N=6, WR=50.0%, EV=-0.602 だが PF/WF/Kelly が揃わず、`feedback_partial_quant_trap.md` 基準では採用判断不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_USD | FIT / insufficient | London/NY overlap と低 spread 推定は thesis に合うが、H1 shadow counterfactual は London N=1, WR=0%, EV=-0.600, PF=0.00 のみ。 |
| USD_JPY | FIT / unproven | code は JPY spread 推定を持つが、tier-master ALL には 365d EV がなく、既存 180d BT の USDJPY 1m は N=1, WR=0%, EV=-2.276。 |
| GBP_USD | FIT / unproven | London/NY overlap の流動性は合うが、既存 180d BT では GBPUSD 5m N=1, WR=100%, EV=+1.125 に過ぎない。 |
| GBP_JPY | FIT / unproven | 180d BT では 1m/5m が各 N=1 positive、365d JPY 5m は N=2, WR=50%, EV=-0.441 で decision-grade ではない。 |
| EUR_JPY | FORCED / no evidence | code は JPY branch に含め得るが、既存 confluence_scalp の pair-specific evidence を確認できない。 |
| EUR_GBP | FORCED / BLOCKED | `_disabled_symbols` で明示的に停止されるため、ALL scope とは一致しない。`strategies/scalp/confluence_scalp.py:311`, `strategies/scalp/confluence_scalp.py:312`, `strategies/scalp/confluence_scalp.py:334`, `strategies/scalp/confluence_scalp.py:335`, `strategies/scalp/confluence_scalp.py:336`, `strategies/scalp/confluence_scalp.py:337` |
| Other ALL pairs | FORCED | spread 推定 default はあるが、strategy-specific evidence がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) で Tier 3/4 ではないが、phase0_shadow ALL の tier-master EV が `—`、local audit DB は 0 件、直近 shadow counterfactual も N=1 loss のため under-evidenced / low-firing cell として failure mode を診断する。

破綻軸は Axis 3 が主。Axis 2 は 3 family confluence としては整合し、Axis 4 も generic hard gate が edge tail を明確に破壊している証拠はない。Axis 5 の R:R も current code では概ね aligned。一方で signal bar の closed-bar contract と per-bar dedup が strategy 内に存在せず、fractal CHoCH が current df tail に依存するため、shadow/live の発火数が増えた時に timing bias と同 bar 多重 entry が混入し得る。

再設計案は timing 1 系統。`evaluate()` の trigger 入力を確定済み signal bar に固定し、execution は次 bar の `ctx.entry` に限定する。加えて `(ctx.symbol, signal, bar_time)` の last-emitted guard を strategy または dispatch 層に置き、CHoCH/MSB も `df.iloc[:-1]` の確定 prior window だけで判定する variant を作る。本 audit では BT を実行しないため、採用前には 365d + WF folds>=3 + Bonferroni/Kelly を同一 pipeline で再集計する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は維持する。Session/MFE で摩擦に耐える母集団を作り、EMA trend + oscillator pullback + MACD-H reversal の 3 family confluence で scalp entry を絞る設計はコードから明確に導出できる。問題は trigger の思想不一致ではなく、closed-bar 化と dedup が strategy 境界で明示されていない timing contract にある。

具体修正案は、`evaluate()` の計算対象を `signal_row = ctx.df.iloc[-2]`、`prev_row = ctx.df.iloc[-3]` に寄せ、`ctx.entry` は次 bar execution price としてのみ使う。CHoCH/MSB は `ctx.df.iloc[:-1]` または signal bar までの closed window で判定し、`self._last_signal_bar[(symbol, signal)] == bar_time` なら `None` を返す guard を追加する。CHoCH/MSB を本当に thesis の中核にする場合は、bonus ではなく separate variant として `CHoCH direction == signal` を hard gate にするが、これは N をさらに削るため別 BT/WF で検証する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow ALL: `—`; local `demo_trades.db`: 0 rows in `demo_trades` / `evaluated_candidates` / `oanda_audit`; H1 shadow counterfactual: EUR_USD London N=1; 180d scalp BT reference aggregate N=6 | prompt tier-master input; `demo_trades.db`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md` |
| Win rate | H1 shadow counterfactual: 0.0%; 180d scalp BT reference: 50.0% | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md` |
| Wilson lo (95%) | H1 shadow counterfactual: 0.000; 180d N=6 / WR=50.0% derived Wilson lo=18.76%, not decision-grade | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; derived from `knowledge-base/raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md` |
| PF | H1 shadow counterfactual: 0.00; tier-master / 180d ALL PF: INSUFFICIENT_EVIDENCE | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no confluence_scalp ALL WF>=3 result found in tier-master/audit DB | `knowledge-base/wiki/tier-master.md`; local search of `knowledge-base/raw/bt-results/` |
| Bonferroni-adj p | H1 shadow counterfactual: 1.0000; tier-master ALL p-value unavailable | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; `knowledge-base/wiki/tier-master.md` |
| Kelly fraction | H1 shadow counterfactual: 0.000; tier-master / 180d ALL Kelly: INSUFFICIENT_EVIDENCE | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; `knowledge-base/wiki/tier-master.md` |
