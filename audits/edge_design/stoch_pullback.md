---
strategy: stoch_pullback
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

上位トレンドを ADX と EMA9/EMA21 の順列で確認し、Stochastic の一時的な押し目/戻りから K/D クロスでトレンド方向へ再開する瞬間を拾う trend-pullback scalp。BUY は上昇トレンド中の Stoch 売られすぎ回復、SELL は下降トレンド中の Stoch 買われすぎ回復として、コードコメントと条件列から直接導出できる。`strategies/scalp/stoch_pullback.py:1`, `strategies/scalp/stoch_pullback.py:12`, `strategies/scalp/stoch_pullback.py:14`, `strategies/scalp/stoch_pullback.py:15`, `strategies/scalp/stoch_pullback.py:17`, `strategies/scalp/stoch_pullback.py:18`, `strategies/scalp/stoch_pullback.py:38`, `strategies/scalp/stoch_pullback.py:53`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-pullback thesis に対し、BUY は `ema9 > ema21 AND entry > ema21 AND stoch_k > stoch_d AND prev_stoch_k < 48 AND stoch_k < 70`、SELL は `ema9 < ema21 AND entry < ema21 AND stoch_k < stoch_d AND prev_stoch_k > 52 AND stoch_k > 30`。MR の oversold 単独逆張りではなく、EMA/ADX で trend を確認し、Stoch の pullback recovery を trigger にしているため thesis と整合する。RSI/BBPB も過熱・深すぎる逆行を避ける bounded pullback 条件になっている。`strategies/scalp/stoch_pullback.py:15`, `strategies/scalp/stoch_pullback.py:17`, `strategies/scalp/stoch_pullback.py:18`, `strategies/scalp/stoch_pullback.py:19`, `strategies/scalp/stoch_pullback.py:20`, `strategies/scalp/stoch_pullback.py:25`, `strategies/scalp/stoch_pullback.py:36`, `strategies/scalp/stoch_pullback.py:39`, `strategies/scalp/stoch_pullback.py:40`, `strategies/scalp/stoch_pullback.py:41`, `strategies/scalp/stoch_pullback.py:42`, `strategies/scalp/stoch_pullback.py:43`, `strategies/scalp/stoch_pullback.py:44`, `strategies/scalp/stoch_pullback.py:54`, `strategies/scalp/stoch_pullback.py:55`, `strategies/scalp/stoch_pullback.py:56`, `strategies/scalp/stoch_pullback.py:57`, `strategies/scalp/stoch_pullback.py:58`, `strategies/scalp/stoch_pullback.py:59` |
| 3 (timing window) | LOOKAHEAD | 前バー Stoch は `ctx.df.iloc[-2]` を使う一方、trend 判定・K/D クロス・RSI/BBPB・entry は現在の `ctx` 値を直接読む。strategy 内に確定足判定や `(instrument, signal, bar_time)` dedup がないため、実行層が intrabar で `evaluate()` を複数回呼ぶ場合、未確定の Stoch/EMA/price で同一 bar 多重 entry が起き得る。Signal→execution latency も strategy file 単体では定義されていない。`strategies/scalp/stoch_pullback.py:24`, `strategies/scalp/stoch_pullback.py:36`, `strategies/scalp/stoch_pullback.py:39`, `strategies/scalp/stoch_pullback.py:40`, `strategies/scalp/stoch_pullback.py:43`, `strategies/scalp/stoch_pullback.py:44`, `strategies/scalp/stoch_pullback.py:54`, `strategies/scalp/stoch_pullback.py:55`, `strategies/scalp/stoch_pullback.py:58`, `strategies/scalp/stoch_pullback.py:59`, `strategies/scalp/stoch_pullback.py:79` |
| 4 (filter coherence) | STRENGTHENS | `ADX >= 20`、EMA9/EMA21 方向一致、price の EMA21 方向側維持は trend-pullback thesis を強化する。RSI と BBPB の上下限は、Stoch pullback が深すぎる逆張りや過熱追随に変質するのを防ぐ補助 filter。`apply_penalty(..., strategy_type="pullback", ctx.adx)` は entry gate ではなく confidence adjustment なので thesis を hard に破壊してはいない。MR 戦略に MA filter を被せる `feedback_ma_filter_breaks_mr.md` 型ではなく、HMM regime gate で edge tail を消す `feedback_hmm_gate_same_trap.md` 型の hard regime gate も存在しない。ただし session/spread/volatility の loss pocket を避ける filter は未実装。`strategies/scalp/stoch_pullback.py:12`, `strategies/scalp/stoch_pullback.py:15`, `strategies/scalp/stoch_pullback.py:16`, `strategies/scalp/stoch_pullback.py:25`, `strategies/scalp/stoch_pullback.py:39`, `strategies/scalp/stoch_pullback.py:43`, `strategies/scalp/stoch_pullback.py:44`, `strategies/scalp/stoch_pullback.py:54`, `strategies/scalp/stoch_pullback.py:58`, `strategies/scalp/stoch_pullback.py:59`, `strategies/scalp/stoch_pullback.py:72`, `strategies/scalp/stoch_pullback.py:73`, `strategies/scalp/stoch_pullback.py:74`, `strategies/scalp/stoch_pullback.py:78` |
| 5 (stop/TP geometry) | ALIGNED | TP は `1.8ATR`、SL は `0.8ATR` で、nominal R:R は `1.8 / 0.8 = 2.25`。Trend-pullback / momentum continuation として勝ち方向を stop より広く取りに行く asymm payoff になっており、MR 用の wide-stop/mean-exit ではなく順張り継続向けの geometry と整合する。`strategies/scalp/stoch_pullback.py:21`, `strategies/scalp/stoch_pullback.py:22`, `strategies/scalp/stoch_pullback.py:50`, `strategies/scalp/stoch_pullback.py:51`, `strategies/scalp/stoch_pullback.py:65`, `strategies/scalp/stoch_pullback.py:66` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。Strategy file に pair filter がなく `ALL` へ強制適用される一方、既存 audit では session/pair による成績差が極端で、USDJPY NY-overlap や GBPUSD Asia/NY-overlap が明確な loss pocket。Trend-pullback thesis 自体は一部 pair/session で fit するが、ALL 一括 cell としては FORCED。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の対象行は 365d BT EV が `—` で、PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が揃わない。local `demo_trades.db` は N=2 のみで Wilson lo=9.45%, PF=1.17, Kelly=+0.073 と小 N。既存 deep dive では N=142, WR=28.9%, Wilson lo=22.1%, PF=0.64, EV=-0.98pips, Kelly=-16.2%、H1 hour-bucket 3month shadow 集計の合算近似でも N=181, WR=22.1%, Wilson lo=16.7%, PF=0.54, Kelly=-18.7%。`feedback_partial_quant_trap.md` 基準では、N/WR/EV だけでなく WF folds>=3 と Bonferroni が不足し、採用証拠は不十分。 |

### Pair-Regime Table

| Pair / bucket | Fit | Evidence |
|---------------|-----|----------|
| EURUSD London | FIT / weak | 3month H1 bucket で N=19, WR=26.3%, EV=-0.832, PF=0.65, Kelly=-0.140。trend-pullback の発火対象としては自然だが、現行条件では負 EV。 |
| EURUSD NY-overlap | FORCED | N=10, WR=20.0%, EV=-0.530, PF=0.80, Kelly=-0.051。 |
| GBPUSD London | FIT / small-N | N=8, WR=50.0%, EV=+4.175, PF=3.90, Kelly=+0.372 だが N<30 で Wilson/Bonferroni 不足。 |
| GBPUSD Asia / NY-overlap / Off | FORCED | Asia N=5 WR=0.0%, NY-overlap N=8 WR=12.5%, Off N=4 WR=25.0%。ALL 適用では loss pocket を踏む。 |
| USDJPY London | FIT / weak | N=31, WR=35.5%, EV=+0.429, PF=1.16, Kelly=+0.049。唯一 N>=30 で弱い正 EV だが Bonferroni p=1.0000。 |
| USDJPY Asia / NY-overlap / Off | FORCED | Asia N=37 WR=18.9%, EV=-1.416, PF=0.47。NY-overlap N=33 WR=6.1%, EV=-4.242, PF=0.07。Off N=26 WR=26.9%, EV=-1.146, PF=0.55。 |
| Other ALL pairs | FORCED / UNTESTED | Strategy file は pair を限定しないため発火し得るが、今回の tier-master / audit DB で decision-grade の pair-specific evidence はない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) 指定だが、同一実装の `entry_type` はコード上 `stoch_trend_pullback` で、tier-master には FORCE_DEMOTED および USDJPY PAIR_DEMOTED としても現れる。既存 audit でも全体 N=142 / PF=0.64 / Kelly=-16.2%、3month H1 bucket 合算近似 N=181 / PF=0.54 / Kelly=-18.7% と underperforming なので failure mode 診断対象とする。

破綻軸は主に Axis 3。Axis 2 の trigger は trend-pullback thesis を捕捉しており、Axis 4 の filter は thesis を直接壊していない。Axis 5 の nominal R:R=2.25 も順張り pullback としては整合する。にもかかわらず成績が崩れる理由は、現在足の Stoch/EMA/price を intrabar で読める構造と dedup 欠落により、Stoch cross の「確定後回復」ではなく未確定の揺れを拾うリスクがあるため。副次的には Axis 6 の ALL 一括適用が session/pair loss pocket を混入させている。

再設計案は timing 修正を第一優先にする。`ctx.df.iloc[-2]` を confirmation bar として Stoch K/D、EMA、RSI、BBPB、close をすべて確定足ベースに揃え、entry は次 bar open または実行層の確定後価格に限定する。さらに `(instrument, signal, bar_time)` dedup を strategy または dispatcher に追加する。次に pair/session scope を分割し、まず USDJPY London と GBPUSD London だけを候補 cell とし、USDJPY NY-overlap、USDJPY Asia、GBPUSD Asia/NY-overlap は hard block または別 variant に隔離する。本 audit では新規 BT は実行しないため、採用前には closed-bar + scoped cell で 365d / WF folds>=3 / Wilson / PF / Bonferroni p / Kelly を既存 audit pipeline から再発行する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は有効候補として残す。Stoch pullback recovery を EMA/ADX trend 方向に限定する設計は明確で、MA filter on MR や HMM hard gate のような thesis 破壊は見えない。現行の最大問題は「回復を確定足で見ているか」が strategy file から保証されず、未確定足の K/D cross と price/EMA 条件で入れること。

具体修正は、BUY 条件を概念的に `prev2_stoch_k < prev_stoch_buy AND prev1_stoch_k > prev1_stoch_d AND prev1_close > prev1_ema21 AND prev1_ema9 > prev1_ema21` のように、直近確定足 `[-2]` の状態へ寄せる。SELL も同様に `prev2_stoch_k > prev_stoch_sell AND prev1_stoch_k < prev1_stoch_d` にする。TP/SL の `1.8ATR / 0.8ATR` は一旦維持し、まず timing と dedup だけを変えた A/B 比較を行う。

scope は `ALL` から pair/session cell に分解する。既存 evidence では USDJPY London と GBPUSD London だけが再検証候補で、USDJPY NY-overlap は N=33 / WR=6.1% / PF=0.07 の loss pocket なので block 候補。closed-bar 化後に WF folds>=3 と Bonferroni-adjusted p が揃わなければ、Shadow 復帰ではなく redesign queue の検証待ちに留める。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master 365d BT: `—`; local `demo_trades.db`: 2; legacy deep dive: 142; 3month H1 bucket shadow合算近似: 181 | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Win rate | local `demo_trades.db`: 50.0% (N=2); legacy deep dive: 28.9%; 3month H1 bucket shadow合算近似: 22.1% | same as above |
| Wilson lo (95%) | local `demo_trades.db`: 9.45%; legacy deep dive recomputed from W=41/N=142: 22.1%; 3month H1 bucket shadow合算近似: 16.7% | `demo_trades.db`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| PF | local `demo_trades.db`: 1.17 (N=2, not decision-grade); legacy deep dive: 0.64; 3month H1 bucket shadow合算近似: 0.54 | same as above |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: legacy deep dive has pre-cutoff N=75 WR=32.0% / post-cutoff N=67 WR=25.4%, but tier-master/audit DB do not provide >=3 valid WF folds for this target cell | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/tier-master.md` |
| Bonferroni-adj p | tier-master: not present; H1 hour-bucket rows mostly 1.0000, USDJPY Asia 0.0337 and USDJPY NY-overlap 0.0001 are negative/loss-pocket evidence, not positive promotion evidence | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Kelly fraction | local `demo_trades.db`: +0.073 (N=2, not decision-grade); legacy deep dive: -16.2%; 3month H1 bucket shadow合算近似: -18.7% | `demo_trades.db`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
