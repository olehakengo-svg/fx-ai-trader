---
strategy: engulfing_bb
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

BB lower/upper extreme と RSI5 の売られすぎ/買われすぎで短期過伸展を検出し、包み足の反転 candle を確認して mean reversion を取る scalp MR 戦略。コード上は BUY が `BB%B < 0.30 AND RSI5 < 45 AND bullish engulfing`、SELL が `BB%B > 0.70 AND RSI5 > 55 AND bearish engulfing` で、thesis はコードから導出可能。`strategies/scalp/engulfing_bb.py:1`, `strategies/scalp/engulfing_bb.py:13`, `strategies/scalp/engulfing_bb.py:14`, `strategies/scalp/engulfing_bb.py:15`, `strategies/scalp/engulfing_bb.py:16`, `strategies/scalp/engulfing_bb.py:39`, `strategies/scalp/engulfing_bb.py:40`, `strategies/scalp/engulfing_bb.py:46`, `strategies/scalp/engulfing_bb.py:53`, `strategies/scalp/engulfing_bb.py:66`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して BUY は `_is_bullish AND bbpb < 0.30 AND rsi5 < 45`、SELL は `_is_bearish AND bbpb > 0.70 AND rsi5 > 55`。BB%B と RSI5 が extension/oversold・overbought を捕捉し、包み足が reversal confirmation になっているため数学的な方向は整合する。ただし閾値は shallow で、`bbpb < 0.30` / `rsi5 < 45` は極端 MR としては広い。`strategies/scalp/engulfing_bb.py:13`, `strategies/scalp/engulfing_bb.py:14`, `strategies/scalp/engulfing_bb.py:15`, `strategies/scalp/engulfing_bb.py:16`, `strategies/scalp/engulfing_bb.py:40`, `strategies/scalp/engulfing_bb.py:41`, `strategies/scalp/engulfing_bb.py:42`, `strategies/scalp/engulfing_bb.py:43`, `strategies/scalp/engulfing_bb.py:44`, `strategies/scalp/engulfing_bb.py:46`, `strategies/scalp/engulfing_bb.py:47`, `strategies/scalp/engulfing_bb.py:48`, `strategies/scalp/engulfing_bb.py:49`, `strategies/scalp/engulfing_bb.py:50`, `strategies/scalp/engulfing_bb.py:53`, `strategies/scalp/engulfing_bb.py:66` |
| 3 (timing window) | LOOKAHEAD | 現在足の `ctx.entry`, `ctx.open_price`, `df.iloc[-1]["High"]`, `df.iloc[-1]["Low"]`, `ctx.bbpb`, `ctx.rsi5`, `ctx.stoch_k/d` を直接使い、strategy 内に closed-bar 固定や `(symbol, signal, bar_time)` dedup がない。実行層が intrabar evaluate すると未確定 candle の包み足・range・indicator で signal が点灯し、同一 bar 多重 entry も起き得る。`strategies/scalp/engulfing_bb.py:23`, `strategies/scalp/engulfing_bb.py:35`, `strategies/scalp/engulfing_bb.py:36`, `strategies/scalp/engulfing_bb.py:37`, `strategies/scalp/engulfing_bb.py:40`, `strategies/scalp/engulfing_bb.py:41`, `strategies/scalp/engulfing_bb.py:44`, `strategies/scalp/engulfing_bb.py:47`, `strategies/scalp/engulfing_bb.py:50`, `strategies/scalp/engulfing_bb.py:53`, `strategies/scalp/engulfing_bb.py:59`, `strategies/scalp/engulfing_bb.py:66`, `strategies/scalp/engulfing_bb.py:72`, `strategies/scalp/engulfing_bb.py:82` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | Friday block は weekend gap 回避で thesis には NEUTRAL。包み足の body ratio `1.3x`、前足始値突破、range `> 0.5ATR` は reversal candle の実体を要求するため STRENGTHENS。Stoch K/D は hard filter ではなく score bonus なので STRENGTHENS 寄り。MA filter on MR strategy (`feedback_ma_filter_breaks_mr.md`) や HMM regime gate same trap (`feedback_hmm_gate_same_trap.md`) に相当する trend/regime hard block はこの file 内にはない。`strategies/scalp/engulfing_bb.py:17`, `strategies/scalp/engulfing_bb.py:18`, `strategies/scalp/engulfing_bb.py:24`, `strategies/scalp/engulfing_bb.py:40`, `strategies/scalp/engulfing_bb.py:41`, `strategies/scalp/engulfing_bb.py:42`, `strategies/scalp/engulfing_bb.py:43`, `strategies/scalp/engulfing_bb.py:44`, `strategies/scalp/engulfing_bb.py:46`, `strategies/scalp/engulfing_bb.py:47`, `strategies/scalp/engulfing_bb.py:48`, `strategies/scalp/engulfing_bb.py:49`, `strategies/scalp/engulfing_bb.py:50`, `strategies/scalp/engulfing_bb.py:59`, `strategies/scalp/engulfing_bb.py:72` |
| 5 (stop/TP geometry) | MISALIGNED | Nominal TP は `1.5ATR7`、SL は `0.8ATR7 + 0.15ATR7` 相当で、R:R は概算 `1.5 / 0.95 = 1.58`。ただし SL は current bar low/high の外側にも置かれるため、包み足が大きいほど実効 SL が広がり R:R はさらに低下し得る。MR なら mean まで戻る前に切られない wide stop と、回帰先を現実的に取る TP が必要だが、現行は shallow extension trigger に対して高め TP を狙う摩擦負け構造。`strategies/scalp/engulfing_bb.py:19`, `strategies/scalp/engulfing_bb.py:20`, `strategies/scalp/engulfing_bb.py:21`, `strategies/scalp/engulfing_bb.py:62`, `strategies/scalp/engulfing_bb.py:63`, `strategies/scalp/engulfing_bb.py:75`, `strategies/scalp/engulfing_bb.py:76` |
| 6 (pair-regime fit) | FORCED | 下の pair-regime table 参照。strategy file に pair/session filter はなく `ALL` に適用されるが、tier-master は force_demoted に加えて EUR_USD / USD_JPY を pair_demoted としており、既存 evidence も USDJPY 5m sidecar 以外は decision-grade ではない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / sidecar reject | tier-master の force_demoted / ALL 365d BT EV は `—`。local `demo_trades.db` の `demo_trades` / `evaluated_candidates` / `oanda_audit` には exact `engulfing_bb` 行が 0 件。既存 sidecar 180d USDJPY 5m は N=30, WR=53.333%, Wilson lo=36.142%, PF=1.557, Kelly full=0.1909 / half=0.0954 だが、Bonferroni p=0.09299531 で不通過、max DD 188.209% で Reject、WF は 50/50 split で folds>=3 ではない。`feedback_partial_quant_trap.md` 基準では採用判断不可。 |

### Pair-Regime Table

| Pair / scope | Fit | Evidence |
|--------------|-----|----------|
| USD_JPY | FORCED / weak candidate | tier-master で pair_demoted。既存 sidecar 180d 5m は N=30, PF=1.557, Wilson lo=36.142% だが Bonferroni p=0.09299531 と max DD 188.209% で Reject。 |
| EUR_USD | FORCED | tier-master で pair_demoted。strategy wiki には post-cutoff N=6 WR=66.7% の小標本があるが、365d BT は unavailable で decision-grade ではない。 |
| GBP_USD | FORCED / small-N | legacy deep dive の top cell は GBP_USD London BUY N=3 WR=66.7% だけで、N<30 かつ Bonferroni 不通過。 |
| Other ALL pairs | FORCED / UNTESTED | strategy file は pair を限定しないため発火し得るが、今回の tier-master / audit DB で Wilson / PF / Kelly / Bonferroni が揃う pair-specific evidence はない。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の BB%B + RSI5 + 包み足 trigger は MR thesis と方向としては整合するが、すべて現在足依存で signal と execution が分離されていない。さらに `1.5ATR` TP / 実効 `0.95ATR+` SL は、shallow BB/RSI extension の scalp MR に対して必要勝率と摩擦負担を上げる。

再設計案は、まず timing を closed-bar 化すること。`df.iloc[-2]` を signal bar とし、包み足判定、BB%B、RSI5、Stoch K/D、High/Low range をすべて確定足から読む。entry は次 bar execution に分離し、`(engulfing_bb, instrument, signal, signal_bar_time)` dedup を strategy または dispatcher 層で必須にする。

次に trigger と geometry を MR 向けに寄せる。BUY は概念的に `prev1_bbpb < 0.15 AND prev1_rsi5 < 35 AND bullish_engulfing_closed`、SELL は `prev1_bbpb > 0.85 AND prev1_rsi5 > 65 AND bearish_engulfing_closed` へ狭め、current-bar body pattern の偶発発火を減らす。SL は candle low/high 依存の可変幅を明示的に制限し、TP は `1.0-1.2ATR` または middle-band/EMA回帰 target へ下げる variant を作る。pair scope はまず USDJPY 5m のみ再検証し、EURUSD/ALL 復帰は evidence が揃うまで保留する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は維持候補。BB extreme + RSI extension + reversal candle という MR thesis はコードから明確に導出でき、MA/HMM 型の破壊的 filter は見えない。ただし復活には timing closed-bar 化、trigger 閾値の再設計、stop/TP geometry の再設計、pair scope 分離の複数軸修正が必要なので `B` とする。

最小 diff の想定は、現在足参照をすべて確定足系列へ移すこと。`_prev_body` / `_curr_body` / `_curr_range` は `df.iloc[-3]` と `df.iloc[-2]` で作り、`ctx.bbpb` / `ctx.rsi5` / `ctx.stoch_k` も signal bar の列値を参照する。`Candidate` の entry は次 bar 側に残し、reasons には signal bar の指標値を記録する。

採用前には本 audit では実行しない closed-bar + stricter-extreme + revised-geometry variant の再検証が必要。必要 artifact は USDJPY 5m を起点に、365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 audit DB / tier-master source で出すこと。N/WR/EV や sidecar 50/50 split だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master force_demoted/ALL: `—`; local `demo_trades.db`: 0; legacy deep dive: 101; sidecar USDJPY 5m: 30 | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json` |
| Win rate | tier-master/audit DB: INSUFFICIENT_EVIDENCE; legacy deep dive: 31.7%; sidecar USDJPY 5m: 53.333% | same as above |
| Wilson lo (95%) | tier-master/audit DB: INSUFFICIENT_EVIDENCE; legacy deep dive aggregate not listed but cell rows all Bonferroni fail; sidecar USDJPY 5m: 36.142% | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json` |
| PF | tier-master/audit DB: INSUFFICIENT_EVIDENCE; legacy deep dive: 0.86; sidecar USDJPY 5m: 1.557 | same as above |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: legacy deep dive has pre/post split only; sidecar has 50/50 chronological split IS/OOS only, not WF folds>=3 for `engulfing_bb` target cell. | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json` |
| Bonferroni-adj p | tier-master/audit DB: INSUFFICIENT_EVIDENCE; legacy deep dive cells are all Bonferroni fail; sidecar USDJPY 5m: 0.09299531, above 0.01250 threshold | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json` |
| Kelly fraction | tier-master/audit DB: INSUFFICIENT_EVIDENCE; legacy deep dive: -5.1%; sidecar USDJPY 5m: Kelly full 0.1909 / half 0.0954, but Reject due Bonferroni and drawdown | same as above |
