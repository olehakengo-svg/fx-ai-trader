---
strategy: ema_ribbon
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

EMA ribbon の順列と ADX/DI で既存トレンドを確認し、EMA9 近傍までの短い押し目/戻りを現在足の足色反転で拾う trend-pullback scalp。12-17 UTC の London/NY overlap で、逆張りが弱い時間帯を順張り側で補完する思想もコードから明示的に導出できる。`strategies/scalp/ema_ribbon.py:2`, `strategies/scalp/ema_ribbon.py:5`, `strategies/scalp/ema_ribbon.py:6`, `strategies/scalp/ema_ribbon.py:7`, `strategies/scalp/ema_ribbon.py:17`, `strategies/scalp/ema_ribbon.py:18`, `strategies/scalp/ema_ribbon.py:19`, `strategies/scalp/ema_ribbon.py:20`, `strategies/scalp/ema_ribbon.py:21`, `strategies/scalp/ema_ribbon.py:22`, `strategies/scalp/ema_ribbon.py:23`, `strategies/scalp/ema_ribbon.py:24`, `strategies/scalp/ema_ribbon.py:25`, `strategies/scalp/ema_ribbon.py:27`, `strategies/scalp/ema_ribbon.py:28`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-pullback thesis に対し、方向は `BUY: ema9 > ema21 > ema50` / `SELL: ema9 < ema21 < ema50`、trend strength は `ADX >= 25` と `abs(+DI - -DI) >= 5`、pullback は `abs(entry - ema9) <= ATR7 * 0.5`、反転は `BUY: entry > open_price` / `SELL: entry < open_price` かつ body ratio `>= 0.40` で捕捉する。Docstring の完全 PO は `ema200` まで含むが、実 entry では `ema200` は必須ではなく bonus に留まるため厳密な「完全PO」ではない。それでも thesis の trend confirmation + pullback trigger は数学的に表現されている。`strategies/scalp/ema_ribbon.py:51`, `strategies/scalp/ema_ribbon.py:52`, `strategies/scalp/ema_ribbon.py:82`, `strategies/scalp/ema_ribbon.py:86`, `strategies/scalp/ema_ribbon.py:87`, `strategies/scalp/ema_ribbon.py:105`, `strategies/scalp/ema_ribbon.py:106`, `strategies/scalp/ema_ribbon.py:108`, `strategies/scalp/ema_ribbon.py:109`, `strategies/scalp/ema_ribbon.py:115`, `strategies/scalp/ema_ribbon.py:116`, `strategies/scalp/ema_ribbon.py:118`, `strategies/scalp/ema_ribbon.py:127`, `strategies/scalp/ema_ribbon.py:130`, `strategies/scalp/ema_ribbon.py:146`, `strategies/scalp/ema_ribbon.py:147`, `strategies/scalp/ema_ribbon.py:191` |
| 3 (timing window) | LOOKAHEAD | Entry confirmation が現在足の `ctx.entry`, `ctx.open_price`, `ctx.high`, `ctx.low` に依存し、strategy 内に closed-bar 判定も `(symbol, signal, bar_time)` dedup もない。実行層が intrabar で `evaluate()` を複数回呼ぶ場合、未確定足の陽線/陰線・body ratio・EMA9 proximity で同一 bar 多重 entry が起き得るため、spec の bar dedup 欠落リスクに該当する。`strategies/scalp/ema_ribbon.py:115`, `strategies/scalp/ema_ribbon.py:122`, `strategies/scalp/ema_ribbon.py:123`, `strategies/scalp/ema_ribbon.py:124`, `strategies/scalp/ema_ribbon.py:130`, `strategies/scalp/ema_ribbon.py:147`, `strategies/scalp/ema_ribbon.py:225` |
| 4 (filter coherence) | STRENGTHENS | Pair filter は USDJPY/EURUSD/EURJPY/XAUUSD のみを許可し、`ALL` scope とは齟齬があるが「BT正EVペアのみ」という目的では thesis を壊さない。0-6 UTC block、ADX>=25、DI gap、BB width percentile、body ratio、EMA spread、Stoch/MACD bonus は、trend-pullback の方向性・流動性・反転品質を強化する。MR 戦略への MA filter 追加で edge を壊す `feedback_ma_filter_breaks_mr.md` 型ではなく、HMM regime gate で tail を消す `feedback_hmm_gate_same_trap.md` 型の hard regime gate も存在しない。ただし filter が多く、発火率を落とす実務リスクは Axis 7/8 側で扱う。`strategies/scalp/ema_ribbon.py:61`, `strategies/scalp/ema_ribbon.py:62`, `strategies/scalp/ema_ribbon.py:63`, `strategies/scalp/ema_ribbon.py:67`, `strategies/scalp/ema_ribbon.py:68`, `strategies/scalp/ema_ribbon.py:69`, `strategies/scalp/ema_ribbon.py:78`, `strategies/scalp/ema_ribbon.py:82`, `strategies/scalp/ema_ribbon.py:87`, `strategies/scalp/ema_ribbon.py:91`, `strategies/scalp/ema_ribbon.py:124`, `strategies/scalp/ema_ribbon.py:181`, `strategies/scalp/ema_ribbon.py:191`, `strategies/scalp/ema_ribbon.py:196`, `strategies/scalp/ema_ribbon.py:203`, `strategies/scalp/ema_ribbon.py:209`, `strategies/scalp/ema_ribbon.py:217` |
| 5 (stop/TP geometry) | MISALIGNED | TP は base `1.2ATR`、EURJPY は `1.1ATR` に短縮される一方、SL は EMA21 の反対側 `±0.3ATR` で、entry が EMA9 近傍かつ EMA9-EMA21 spread が広いほど R:R が悪化する。例: BUY の概算は `R = 1.2ATR / ((entry - ema21) + 0.3ATR)` で、EMA9-EMA21 spread が 1.0ATR なら R:R は約 `0.92` まで低下する。Trend continuation なら asymmetric payoff / trailing で継続を取りに行くべきだが、現行は 1m scalp の小 TP で摩擦に食われやすく、既存 force-demoted 診断の FRICTION_KILL と整合する。`strategies/scalp/ema_ribbon.py:50`, `strategies/scalp/ema_ribbon.py:57`, `strategies/scalp/ema_ribbon.py:58`, `strategies/scalp/ema_ribbon.py:139`, `strategies/scalp/ema_ribbon.py:140`, `strategies/scalp/ema_ribbon.py:142`, `strategies/scalp/ema_ribbon.py:143`, `strategies/scalp/ema_ribbon.py:156`, `strategies/scalp/ema_ribbon.py:157`, `strategies/scalp/ema_ribbon.py:158`, `strategies/scalp/ema_ribbon.py:164`, `strategies/scalp/ema_ribbon.py:167`, `strategies/scalp/ema_ribbon.py:169` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。Audit 対象は `ALL` だが、実装上は USDJPY/EURUSD/EURJPY/XAUUSD のみ許可し、tier-master でも同一 file の `ema_ribbon_ride` は force_demoted に載っている。`ALL` cell としては scope が強制的で、pair-specific evidence も不足する。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は `—`。local `demo_trades.db` には `ema_ribbon_ride` の `demo_trades` / `evaluated_candidates` / `oanda_audit` 行が 0 件。既存 audit 文書では gate-progression N=4, WR=0.00%, Wilson lo=0.00%, PF=0.000, Kelly=0.0000, Bonferroni p=1.0000、H1 hour-bucket shadow status N=6, WR=33.3%, Wilson BF lower=4.75%, Bonferroni p=1.0000, Kelly=-0.0507 があるが、どちらも小 N で WF folds>=3 を満たさない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT / INSUFFICIENT_EVIDENCE | JPY trend session scalp として thesis fit はあるが、H1 hour-bucket では London N=2, WR=50.0%, EV=+1.400, PF=1.933, Kelly=0.241 に留まり、Asia/Off は negative。 |
| EURUSD | FORCED / weak | Allowed pair だが、H1 hour-bucket shadow では Asia N=2, WR=0.0%, EV=-1.900, PF=0.000、London N=2, WR=50.0%, EV=-0.200, PF=0.895。 |
| EURJPY | FIT / INSUFFICIENT_EVIDENCE | Code は EURJPY の TP を `1.1ATR` に縮めるが、今回確認できた audit DB / tier-master では decision-grade の pair-specific Wilson/PF/WF/Kelly が揃わない。`strategies/scalp/ema_ribbon.py:57`, `strategies/scalp/ema_ribbon.py:58` |
| XAUUSD | FORCED / INSUFFICIENT_EVIDENCE | Code は許可しているが、今回の FX-focused audit sources では XAUUSD の pair-specific evidence が不足。`strategies/scalp/ema_ribbon.py:62`, `strategies/scalp/ema_ribbon.py:63` |
| Other ALL pairs | FORCED / BLOCKED | `ALL` 入力に対して、実装は上記 4 symbols 以外を即 `return None` にする。`strategies/scalp/ema_ribbon.py:72`, `strategies/scalp/ema_ribbon.py:73`, `strategies/scalp/ema_ribbon.py:74`, `strategies/scalp/ema_ribbon.py:75` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) 指定だが、同一実装名 `ema_ribbon_ride` は tier-master で force_demoted にも存在し、既存 audit では gate-progression N=4 / WR=0% / PF=0、3-month hour-bucket でも shadow status は pending かつ Bonferroni p=1.0 であるため、underperforming failure mode として診断する。

破綻軸は Axis 3 と Axis 5。Axis 2 の trend-pullback trigger は思想を概ね捕捉しており、Axis 4 の filter も thesis を直接破壊していない。主問題は、現在足の `entry/open/high/low` を使う intrabar timing と dedup 欠落、さらに 1m scalp の `1.1-1.2ATR` 固定 TP が EMA21 stop と摩擦に対して小さすぎる stop/TP geometry である。補助的には Axis 6 の `ALL` scope mismatch も昇格判断を汚している。

再設計案は、trigger は維持しつつ timing と geometry を変える。まず signal 判定を確定足に寄せ、`ctx.df.iloc[-2]` 相当の close/open/high/low と EMA/ADX/DI/RSI を confirmation bar として使い、次 bar で約定する。dispatch または strategy 側で `(symbol, signal, bar_time)` dedup を必須化する。次に TP を `max(2.0ATR, 1.5R)` 以上にし、London/NY session の trend continuation だけは trailing または EMA9/EMA21 close break exit に切り替える。1m のままでは摩擦負けが濃いので、既存知見どおり 5m/15m variant で同じ session weight と BB width / DI gap を再評価するのが最小の復活経路。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は有効候補として残す。EMA ribbon + ADX/DI + EMA9 pullback は trend continuation の入口として自然で、MR に MA filter を被せるような明確な thesis 破壊は見えない。

ただし現行設計のまま Shadow 昇格を進める根拠は不足している。最小 redesign は、`ctx.entry > ctx.open_price` / `< ctx.open_price` と body ratio を未確定足で読まない closed-bar trigger に変更し、同一 bar dedup を追加すること。そのうえで TP/SL を `tp = entry +/- max(2.0*ATR7, 1.5*abs(entry-sl))` のような R floor 付きに変え、EURJPY の `1.1ATR` 早期利確は撤廃または別 variant に隔離する。

採用判定には、本 audit では実行しない 5m/15m の既存 audit pipeline 再集計が必要。必要 BT 内容は、USDJPY/EURUSD/EURJPY/XAUUSD を pair 別に分け、closed-bar + R-floor geometry 版で 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source から出すこと。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow ALL: `—`; local `demo_trades.db`: 0 rows; gate-progression audit: N=4; H1 hour-bucket shadow status: N=6; older shadow TP-hit deep dive: N=10 | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Win rate | gate-progression audit: 0.00%; H1 hour-bucket shadow status: 33.3%; older shadow TP-hit deep dive: 20.0% | same as above |
| Wilson lo (95%) | gate-progression audit: 0.00%; H1 hour-bucket shadow status Wilson BF lower: 4.75%; older shadow-deep analysis: 5.7% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/wiki/sessions/shadow-deep-analysis-2026-04-21.md` |
| PF | gate-progression audit: 0.000; H1 hour-bucket shadow cells: EUR_USD Asia 0.000 / EUR_USD London 0.895 / USD_JPY London 1.933; older shadow TP-hit deep dive: 0.39 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: older deep dive has pre-cutoff N=10 / post-cutoff N=0, not >=3 valid folds; tier-master/audit DB do not provide promotion-grade WF folds for `ema_ribbon` ALL | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/tier-master.md` |
| Bonferroni-adj p | gate-progression audit: 1.0000; H1 hour-bucket shadow status: 1.0000 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| Kelly fraction | gate-progression audit: 0.0000; H1 hour-bucket shadow status: -0.0507; older shadow TP-hit deep dive: -30.7% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
