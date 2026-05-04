---
strategy: ema_cross
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

15m の EMA9/21 クロス後、短いプルバックを待ち、ADX と 4H/1D EMA 配列で上位足トレンドが同方向であることを確認して再加速に乗る trend-follow / retest 戦略。コード上も `strategy_type = "trend"`、ADX trend filter、HTF perfect order、cross window、pullback depth からこの thesis は導出可能。`strategies/daytrade/ema_cross.py:1`, `strategies/daytrade/ema_cross.py:3`, `strategies/daytrade/ema_cross.py:4`, `strategies/daytrade/ema_cross.py:5`, `strategies/daytrade/ema_cross.py:23`, `strategies/daytrade/ema_cross.py:27`, `strategies/daytrade/ema_cross.py:30`, `strategies/daytrade/ema_cross.py:31`, `strategies/daytrade/ema_cross.py:35`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-retest thesis に対し、直近 `cross_window=8` 本内の `BUY: ema9 crosses above ema21` / `SELL: ema9 crosses below ema21` を検出し、`pullback_depth >= 0.3ATR` と `BUY: entry > ema21` / `SELL: entry < ema21` でクロス後リテストを要求する。最終 entry は `BUY: ema9 > ema21 AND candle_bull AND macdh > 0 AND rsi < 70 AND ema_score > 0.30`、`SELL: ema9 < ema21 AND candle_bear AND macdh < 0 AND rsi > 30 AND ema_score < -0.30` で、trend 確認 + pullback + 再加速を数学的に捕捉している。`strategies/daytrade/ema_cross.py:30`, `strategies/daytrade/ema_cross.py:31`, `strategies/daytrade/ema_cross.py:32`, `strategies/daytrade/ema_cross.py:33`, `strategies/daytrade/ema_cross.py:34`, `strategies/daytrade/ema_cross.py:166`, `strategies/daytrade/ema_cross.py:167`, `strategies/daytrade/ema_cross.py:172`, `strategies/daytrade/ema_cross.py:177`, `strategies/daytrade/ema_cross.py:180`, `strategies/daytrade/ema_cross.py:195`, `strategies/daytrade/ema_cross.py:197`, `strategies/daytrade/ema_cross.py:199`, `strategies/daytrade/ema_cross.py:201`, `strategies/daytrade/ema_cross.py:215`, `strategies/daytrade/ema_cross.py:216`, `strategies/daytrade/ema_cross.py:228`, `strategies/daytrade/ema_cross.py:229` |
| 3 (timing window) | LOOKAHEAD | クロス自体は `range(2, ...)` で少なくとも 2 本前の EMA 関係を読むため明示的な未来参照はない。一方、最終 confirmation は現在 context の `ctx.entry`, `ctx.open_price`, `ctx.ema9`, `ctx.ema21`, `ctx.macdh`, `ctx.rsi` を直接読み、strategy 内に closed-bar 固定、signal bar と execution bar の分離、または `(symbol, signal, bar_time)` dedup がない。実行層が未確定足で `evaluate()` を複数回呼ぶ契約なら、current-bar 陽線/陰線や MACD-H の途中値で同一 bar 多重 entry が起き得る。加えてクロスから 2-8 本後の retest なので、signal latency は意図された retest ではあるが breakout 初動捕捉としては LATE。`strategies/daytrade/ema_cross.py:153`, `strategies/daytrade/ema_cross.py:172`, `strategies/daytrade/ema_cross.py:177`, `strategies/daytrade/ema_cross.py:180`, `strategies/daytrade/ema_cross.py:195`, `strategies/daytrade/ema_cross.py:199`, `strategies/daytrade/ema_cross.py:207`, `strategies/daytrade/ema_cross.py:208`, `strategies/daytrade/ema_cross.py:215`, `strategies/daytrade/ema_cross.py:216`, `strategies/daytrade/ema_cross.py:228`, `strategies/daytrade/ema_cross.py:229`, `strategies/daytrade/ema_cross.py:245` |
| 4 (filter coherence) | STRENGTHENS | ADX filter は `15m ADX < 15` を完全レンジとして block し、`15m ADX >= 25 rising` または `1H ADX >= 22` を要求するため trend thesis を強化する。HTF perfect order は BUY で `agreement == bull` かつ 4H/1D score、SELL で `agreement == bear` かつ負 score を要求し、上位足方向一致を強化する。RSI cap/floor は BUY の過熱 (`rsi >= 70`) と SELL の売られすぎ (`rsi <= 30`) を避ける補助 filter で、MA filter on MR の `feedback_ma_filter_breaks_mr.md` 型ではない。HMM regime tail を消す `feedback_hmm_gate_same_trap.md` 型の外部 regime hard gate も strategy file 内にはない。`strategies/daytrade/ema_cross.py:65`, `strategies/daytrade/ema_cross.py:73`, `strategies/daytrade/ema_cross.py:74`, `strategies/daytrade/ema_cross.py:77`, `strategies/daytrade/ema_cross.py:78`, `strategies/daytrade/ema_cross.py:81`, `strategies/daytrade/ema_cross.py:85`, `strategies/daytrade/ema_cross.py:88`, `strategies/daytrade/ema_cross.py:91`, `strategies/daytrade/ema_cross.py:98`, `strategies/daytrade/ema_cross.py:123`, `strategies/daytrade/ema_cross.py:126`, `strategies/daytrade/ema_cross.py:128`, `strategies/daytrade/ema_cross.py:137`, `strategies/daytrade/ema_cross.py:139`, `strategies/daytrade/ema_cross.py:141`, `strategies/daytrade/ema_cross.py:209`, `strategies/daytrade/ema_cross.py:210` |
| 5 (stop/TP geometry) | ALIGNED | BUY は `TP = entry + atr7 * 2.0`, `SL = entry - atr7 * 1.0`、SELL は `TP = entry - atr7 * 2.0`, `SL = entry + atr7 * 1.0` で固定 R:R は 2.0。Trend-follow / retest として勝ち方向を stop の 2 倍取りに行く asymmetric payoff で、MR 用の wide-stop ではなく momentum 用 geometry と整合する。ただし trailing はなく、強い trend continuation を伸ばす設計ではない。`strategies/daytrade/ema_cross.py:225`, `strategies/daytrade/ema_cross.py:226`, `strategies/daytrade/ema_cross.py:238`, `strategies/daytrade/ema_cross.py:239` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。Audit 入力は `ALL` だが、strategy file 内に pair/instrument filter はなく、JPY/EUR/GBP などの pair-regime 差を扱わない。Trend-retest thesis は trending pair/session には fit し得るが、ALL 一括は forced scope。 |
| 7 (empirical evidence) | NEGATIVE / INSUFFICIENT_EVIDENCE | tier-master の force_demoted 行は 365d BT EV が `—` で、PF / WF folds>=3 / Bonferroni p / Kelly は tier-master からは揃わない。既存 audit DB 相当の gate-progression 集計では N=20, WR=30.00%, Wilson lo=14.55%, EV=-3.87p, PF=0.308, Kelly=0.0000, raw Kelly=-0.6730, Bonferroni p=1.0000。古い shadow deep dive でも N=46, WR=34.8%, PF=0.63, EV=-1.97pips, Kelly=-20.2%。ただし promotion-grade の WF folds>=3 は不足し、`feedback_partial_quant_trap.md` 基準では採用根拠として不十分。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED / mixed-negative | 既存 evidence は最も多いが、gate-progression では strategy aggregate N=20 WR=30.00% PF=0.308、R2 cell では USD_JPY hour 15/16 が 0% WR。古い deep dive では USD_JPY×ny×SELL だけ N=24 WR=50.0% PF=1.31 の narrow tail がある一方、USD_JPY×london×BUY は N=11 WR=18.2% PF=0.37。 |
| EURUSD | FORCED / insufficient | Strategy file は EURUSD を許可も拒否もしない。tier-master force_demoted 365d EV は `—` で、decision-grade の pair-specific Wilson/PF/WF/Kelly は揃わない。 |
| EURJPY | FORCED / insufficient | Strategy file は EURJPY を許可も拒否もしない。古い 365d/WF sidecar には参考値があるが、本タスク指定の tier-master/audit DB evidence としては promotion-grade metrics が不足。 |
| GBPUSD | FORCED / insufficient | Strategy file は GBPUSD を許可も拒否もしない。H1 hour-bucket では小 N の mixed result があるが、ALL 適用根拠にはならない。 |
| GBPJPY / other pairs | FORCED / insufficient | Pair-specific filter も pair-specific evidence も不足しており、ALL scope のまま thesis fit を主張できない。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) のため failure mode を診断する。Axis 2/4/5 は strategy file 単体では大きく破綻していない。trigger は trend-retest を捕捉し、ADX/HTF filter は thesis を補強し、2:1 TP/SL も momentum geometry と整合する。

破綻軸は主に Axis 3。current-bar の `ctx.entry/open_price/macdh/rsi` による confirmation と strategy 内 dedup 欠落が、live intrabar では未確定足の見かけの再加速を拾う。加えてクロスから 2-8 本待つ retest 設計は thesis と矛盾しないが、既存 evidence の負け方を見る限り、発火が「再加速」ではなく「クロス後に伸び切った current-bar continuation」を追っている可能性が高い。Axis 6 の ALL forced scope も失敗を増幅しており、USDJPY の narrow SELL tail と London BUY の負けを同じ戦略集計に混ぜている。

再設計案は timing と cell scope の切り分けを最小単位にする。Trigger 本体は維持しつつ、confirmation を確定足 `ctx.df.iloc[-2]` ベースに固定し、次 bar 約定に分離する。strategy または dispatch 層で `(symbol, direction, signal_bar_time)` dedup を必須化する。さらに ALL をやめ、まずは既存 deep dive で唯一形のある `USD_JPY × NY × SELL` tail だけを pre-reg cell として再検証し、BUY 側と London は別 variant か block に分離する。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は有効候補として残す。EMA cross + pullback + ADX/HTF alignment は trend-retest の入口として自然で、現行コードから thesis を捏造せずに読める。失敗の中心は trigger そのものより、未確定 current bar を confirmation として読む timing 契約と、ALL scope で tail と toxic cell を混ぜる運用設計にある。

具体修正は、`_cross_dir` と `_pullback_depth` の検出は維持し、最終条件の `ctx.entry > ctx.open_price`, `ctx.macdh > 0`, `ctx.rsi < 70`, `ema_score > threshold` を signal row = 確定済み最終足に固定すること。Live では signal bar close 後の次 bar open/market でのみ発注し、同じ `bar_time` の再 emit を禁止する。Scope は `ALL` ではなく `USD_JPY × NY × SELL` を第一候補にし、BUY side は既存 Q4/BUY bias evidence があるため別 audit で原因を切り分ける。

本 audit では BT を実行しない。採用前に必要なのは、closed-bar + dedup + USDJPY NY SELL cell 版の既存 audit pipeline 再集計で、365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source から出すこと。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB/gate-progression: 20; older shadow deep dive: 46; tier-master 365d BT: `—` | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/tier-master.md` |
| Win rate | audit DB/gate-progression: 30.00%; older shadow deep dive: 34.8% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Wilson lo (95%) | audit DB/gate-progression: 14.55%; older USD_JPY×ny×SELL tail: 31.4%; older USD_JPY×london×BUY: 5.1% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| PF | audit DB/gate-progression: 0.308; older shadow deep dive aggregate: 0.63; older USD_JPY×ny×SELL tail: 1.31; older USD_JPY×london×BUY: 0.37 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: target tier-master/audit DB does not provide promotion-grade WF folds>=3; older deep dive only has pre/post cutoff, not >=3 folds | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Bonferroni-adj p | audit DB/gate-progression: 1.0000; older USD_JPY×ny×SELL raw p_F=0.0324 but Bonferroni not passed | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Kelly fraction | audit DB/gate-progression: 0.0000, raw Kelly=-0.6730; older shadow deep dive aggregate: -20.2%; older USD_JPY×ny×SELL tail: +11.9% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
