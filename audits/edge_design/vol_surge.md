---
strategy: vol_surge
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

出来高またはバー幅の急増を情報イベントとして検出し、BB/RSI の極端値ではクライマックス反転、ADX/DI/EMA 整列ではモメンタム初動として捕捉する二系統 scalp 戦略。Climax は短命反転、Momentum はトレンド追随として TP/SL も分ける意図がコードから読める。`strategies/scalp/vol_surge.py:2`, `strategies/scalp/vol_surge.py:5`, `strategies/scalp/vol_surge.py:6`, `strategies/scalp/vol_surge.py:7`, `strategies/scalp/vol_surge.py:15`, `strategies/scalp/vol_surge.py:16`, `strategies/scalp/vol_surge.py:17`, `strategies/scalp/vol_surge.py:18`, `strategies/scalp/vol_surge.py:21`, `strategies/scalp/vol_surge.py:22`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Climax branch は `_surge AND bbpb<=0.15 AND rsi5<35 AND C>O` / `_surge AND bbpb>=0.85 AND rsi5>65 AND C<O` で、MR thesis に必要な oversold/overbought と反転足を捕捉している。Momentum branch は `_surge AND adx>=20 AND +DI>-DI AND ema9>ema21 AND C>O` / 対称 SELL で、trend direction と同方向 candle を捕捉している。`strategies/scalp/vol_surge.py:35`, `strategies/scalp/vol_surge.py:38`, `strategies/scalp/vol_surge.py:39`, `strategies/scalp/vol_surge.py:40`, `strategies/scalp/vol_surge.py:41`, `strategies/scalp/vol_surge.py:78`, `strategies/scalp/vol_surge.py:87`, `strategies/scalp/vol_surge.py:105`, `strategies/scalp/vol_surge.py:106`, `strategies/scalp/vol_surge.py:107`, `strategies/scalp/vol_surge.py:117`, `strategies/scalp/vol_surge.py:118`, `strategies/scalp/vol_surge.py:119`, `strategies/scalp/vol_surge.py:130`, `strategies/scalp/vol_surge.py:131`, `strategies/scalp/vol_surge.py:132`, `strategies/scalp/vol_surge.py:133`, `strategies/scalp/vol_surge.py:143`, `strategies/scalp/vol_surge.py:144`, `strategies/scalp/vol_surge.py:145`, `strategies/scalp/vol_surge.py:146` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に確定足固定、signal bar と execution bar の分離、または `(strategy, symbol, bar_id)` dedup がない。`ctx.df` の末尾、`ctx.entry`、`ctx.open_price`、`ctx.bbpb`、`ctx.rsi5`、`ctx.adx` を同じ evaluate 時点で直接使うため、実行層が intrabar に呼ぶ場合は未確定の volume/range surge、%B、足色、ADX/DI で発火しうる。同一 bar 多重 entry も strategy file 単体では防げない。`strategies/scalp/vol_surge.py:57`, `strategies/scalp/vol_surge.py:71`, `strategies/scalp/vol_surge.py:73`, `strategies/scalp/vol_surge.py:82`, `strategies/scalp/vol_surge.py:84`, `strategies/scalp/vol_surge.py:105`, `strategies/scalp/vol_surge.py:107`, `strategies/scalp/vol_surge.py:117`, `strategies/scalp/vol_surge.py:119`, `strategies/scalp/vol_surge.py:130`, `strategies/scalp/vol_surge.py:133`, `strategies/scalp/vol_surge.py:143`, `strategies/scalp/vol_surge.py:146`, `strategies/scalp/vol_surge.py:185` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | Volume/range surge gate と bar-range/ATR minimum は二系統 thesis の起点を強化する。Stoch cross bonus は climax MR の確認として STRENGTHENS、EMA200 direction bonus は momentum branch の確認として STRENGTHENS。USDJPY UTC 17-23 block は pair-session filter として NEUTRAL から弱い STRENGTHENS だが、pair/regime evidence が薄く hard filter の根拠は弱い。MR に MA filter を入れる `feedback_ma_filter_breaks_mr.md` 型や、tail 依存 edge を HMM hard gate で消す `feedback_hmm_gate_same_trap.md` 型の thesis 破壊は strategy file 上は確認できない。`strategies/scalp/vol_surge.py:53`, `strategies/scalp/vol_surge.py:54`, `strategies/scalp/vol_surge.py:64`, `strategies/scalp/vol_surge.py:65`, `strategies/scalp/vol_surge.py:78`, `strategies/scalp/vol_surge.py:87`, `strategies/scalp/vol_surge.py:90`, `strategies/scalp/vol_surge.py:91`, `strategies/scalp/vol_surge.py:168`, `strategies/scalp/vol_surge.py:169`, `strategies/scalp/vol_surge.py:172`, `strategies/scalp/vol_surge.py:177`, `strategies/scalp/vol_surge.py:178`, `strategies/scalp/vol_surge.py:180` |
| 5 (stop/TP geometry) | MISALIGNED | Momentum branch は TP=ATR7x2.0 / SL=ATR7x0.8 で R:R 約 2.5 と非対称になっており順張り thesis に合う。一方、Climax MR branch は TP=ATR7x1.3 / SL=ATR7x0.6 で R:R 約 2.17 だが、MR は平均まで戻る前に切らない wide stop が基本であり、短命反転コメントに対して stop が浅すぎる。hybrid strategy 全体として MR 側 geometry が思想と不整合。`strategies/scalp/vol_surge.py:21`, `strategies/scalp/vol_surge.py:22`, `strategies/scalp/vol_surge.py:42`, `strategies/scalp/vol_surge.py:43`, `strategies/scalp/vol_surge.py:46`, `strategies/scalp/vol_surge.py:47`, `strategies/scalp/vol_surge.py:114`, `strategies/scalp/vol_surge.py:115`, `strategies/scalp/vol_surge.py:126`, `strategies/scalp/vol_surge.py:127`, `strategies/scalp/vol_surge.py:140`, `strategies/scalp/vol_surge.py:141`, `strategies/scalp/vol_surge.py:153`, `strategies/scalp/vol_surge.py:154` |
| 6 (pair-regime fit) | FORCED | `pairs: ALL` に対して strategy file は USDJPY の時間帯 block 以外に pair gate を持たず、EURUSD/GBPUSD/EURJPY/USDJPY などへ broad に適用される。Archived evidence では USDJPY London は positive pocket だが、USDJPY Asia、GBPUSD Asia/London、EURUSD London/NY は弱く、ALL 適用は forced。下の pair-regime table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | Prompt の tier-master 入力は phase0_shadow / ALL の 365d BT EV が `—`。current `demo_trades.db` には `vol_surge_detector` rows がなく、archived cell audit には Tokyo q0 N=10 / WR=30.0% / Wilson lo=10.8% / PF=0.41 / Bonferroni p=1.0000 があるが、ALL phase0_shadow の Wilson/PF/WF folds>=3/Bonferroni/Kelly が揃わない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT / session-sensitive | Archived shadow baseline では USDJPY N=22, WR=31.8%, EV=+1.27 の候補があり、tp-hit quant でも USDJPY N=59, WR=40.7%, CI [29.1, 53.4]。ただし h1-hour counterfactual では Asia N=48, WR=31.2%, EV=-0.729 / London N=8, WR=50.0%, EV=+7.912 と時間帯依存が強い。 |
| EURUSD | FORCED | h1-hour counterfactual では London N=16, WR=31.2%, EV=-0.031, PF=0.99、NY-overlap N=4, WR=0.0%, EV=-5.050。 |
| GBPUSD | FORCED | h1-hour counterfactual では Asia N=14, WR=0.0%, EV=-5.800、London N=4, WR=0.0%, EV=-2.375。 |
| EURJPY | FORCED / insufficient | tier-master では `vol_surge_detector × EUR_JPY` が pair_demoted。今回確認した archived cell metrics では promotion-grade evidence なし。 |
| Other ALL pairs | FORCED | strategy file に broad universe を止める symbol gate がないため、pair thesis が確認できないペアにも発火可能。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) かつ SCALP_SENTINEL / pair-demoted 履歴を持つ underperforming strategy として診断する。Axis 2 は二系統とも thesis と trigger が整合し、Axis 4 も hard に thesis を壊す filter は見えない。破綻候補は Axis 3 と Axis 5。未確定足の volume/range surge、BB %B、足色、ADX/DI を同一 evaluate で見て Candidate を返すため、intrabar spike の chase と同一 bar 多重 entry のリスクが残る。さらに Climax MR 側は `TP=1.3ATR / SL=0.6ATR` で、mean reversion が戻る前に浅い stop で切られる geometry になっている。

再設計案は二系統を分離して、まず timing を bar-close 化する。`signal_bar = ctx.df.iloc[-2]` 相当の確定足で surge、BB %B、RSI、足色、ADX/DI/EMA を判定し、次 bar の `ctx.entry` でだけ emit する。`(symbol, self.name, mode, signal_bar_time)` の last-emitted guard を strategy または dispatch 層に追加する。Climax branch は stop を `1.0-1.3*ATR7` 程度へ広げ、TP は BB mid / VWAP / EMA21 など平均回帰先に寄せるか、少なくとも `TP ~= 1.0ATR, SL >= 1.0ATR` の MR geometry variant を比較する。Momentum branch は現行 TP/SL を維持し、必要なら breakout freshness と trailing variant を別候補にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は捨てない。volume/range surge は event detector として残し、Climax MR と Momentum を同じ score/geometry で扱わないように分離する。Trigger は概ね維持し、Climax は `surge AND bbpb extreme AND RSI extreme AND confirmed reversal candle` を確定足で判定、Momentum は `surge AND ADX/DI AND EMA9/21 alignment AND confirmed directional candle` を確定足で判定する。

実装イメージは、現在の `ctx.entry` / `ctx.open_price` 直参照を signal bar snapshot に置き換え、Candidate は次足約定用に一度だけ返す形にする。Climax の SL は現行 0.6ATR から広げ、TP は固定 1.3ATR だけでなく BB mid / EMA21 到達を比較対象にする。採用前には新規 BT ではなく既存 pipeline で、現行版と timing/geometry 修正版を同一条件の 365d, pair-session 別, WF folds>=3, Wilson lower, PF, Bonferroni-adjusted p, Kelly fraction で再集計する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | ALL phase0_shadow official: INSUFFICIENT_EVIDENCE。current `demo_trades.db`: 0 rows for `vol_surge_detector`。Archived cell audit: Tokyo q0 N=10。Other references: USDJPY shadow baseline N=22, tp-hit quant USDJPY N=59, h1-hour shadow cells include EURUSD London N=16 / GBPUSD Asia N=14 / USDJPY Asia N=48 / USDJPY London N=8。 | audit DB; `raw/audits/cell_edge_audit_2026-04-27_inclshadow.md`; `knowledge-base/wiki/analyses/shadow-baseline-2026-04-20.md`; `knowledge-base/wiki/analyses/tp-hit-quant-analysis-2026-04-20.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Win rate | ALL phase0_shadow official: INSUFFICIENT_EVIDENCE。Archived Tokyo q0: 30.0%。USDJPY shadow baseline: 31.8%。tp-hit quant USDJPY: 40.7%。h1-hour shadow: EURUSD London 31.2%, GBPUSD Asia 0.0%, USDJPY Asia 31.2%, USDJPY London 50.0%。 | same sources |
| Wilson lo (95%) | ALL phase0_shadow official: INSUFFICIENT_EVIDENCE。Archived Tokyo q0: 10.8%。tp-hit quant USDJPY CI lower: 29.1%。Phase4d session-spread Tokyo q3: Wilson [15.6%, 50.9%] with N=23, WR=30.4%。 | `raw/audits/cell_edge_audit_2026-04-27_inclshadow.md`; `knowledge-base/wiki/analyses/tp-hit-quant-analysis-2026-04-20.md`; `knowledge-base/wiki/analyses/phase4d-session-spread-routing-result-2026-04-26.md` |
| PF | ALL phase0_shadow official: INSUFFICIENT_EVIDENCE。Archived Tokyo q0 PF=0.41。h1-hour shadow cells: EURUSD London PF=0.99, EURUSD NY-overlap PF=0.00, GBPUSD Asia PF=0.00, GBPUSD London PF=0.00, USDJPY Asia PF=0.76, USDJPY London PF=4.84。 | `raw/audits/cell_edge_audit_2026-04-27_inclshadow.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; tier-master has 365d EV `—` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `vol_surge` / `vol_surge_detector` の ALL phase0_shadow WF folds>=3 artifact は確認できない。 | tier-master / audit DB search |
| Bonferroni-adj p | ALL phase0_shadow official: INSUFFICIENT_EVIDENCE。Archived Tokyo q0 p(raw/Bonf)=0.2059/1.0000。h1-hour shadow cells mostly Bonf=1.0000; GBPUSD Asia Bonf=0.0395 is negative edge, not promotion evidence。 | `raw/audits/cell_edge_audit_2026-04-27_inclshadow.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Kelly fraction | Official Kelly: INSUFFICIENT_EVIDENCE。Archived Tokyo q0 WR=30.0% / PF=0.41 implies approximate Kelly -0.432 if derived from PF/WR, but this is not an official audit DB Kelly field. h1-hour shadow cells report Kelly-like values: EURUSD London -0.004, GBPUSD Asia unavailable due PF=0, USDJPY Asia -0.099, USDJPY London +0.397 with N=8 only。 | derived from archived audit metrics; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; tier-master missing official Kelly |
