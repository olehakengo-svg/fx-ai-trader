---
strategy: v_reversal
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

直近 10 本の急落/急騰後に、RSI・BB%B・Stoch の極端値と反転 candle / Stoch 回復を同時確認して、短期 mean reversion の V 字反転を取る scalp MR 戦略。コード上も `strategy_type = "MR"` と明示され、BUY は急落後の oversold、SELL は急騰後の overbought を反転確認付きで拾う。`strategies/scalp/v_reversal.py:1`, `strategies/scalp/v_reversal.py:12`, `strategies/scalp/v_reversal.py:15`, `strategies/scalp/v_reversal.py:16`, `strategies/scalp/v_reversal.py:18`, `strategies/scalp/v_reversal.py:20`, `strategies/scalp/v_reversal.py:36`, `strategies/scalp/v_reversal.py:39`, `strategies/scalp/v_reversal.py:40`, `strategies/scalp/v_reversal.py:59`, `strategies/scalp/v_reversal.py:87`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対し、BUY は `_drop >= 5.0 AND rsi < 30 AND bbpb < 0.15 AND stoch_k < 20 AND entry > open_price AND stoch_k > prev_stoch`、SELL は `_surge >= 5.0 AND rsi > 70 AND bbpb > 0.85 AND stoch_k > 80 AND entry < open_price AND stoch_k < prev_stoch`。急変幅、oversold/overbought、反転 candle、Stoch turn が入っており、MR の extension/reversal trigger として方向は整合する。`strategies/scalp/v_reversal.py:15`, `strategies/scalp/v_reversal.py:16`, `strategies/scalp/v_reversal.py:17`, `strategies/scalp/v_reversal.py:18`, `strategies/scalp/v_reversal.py:19`, `strategies/scalp/v_reversal.py:20`, `strategies/scalp/v_reversal.py:21`, `strategies/scalp/v_reversal.py:22`, `strategies/scalp/v_reversal.py:36`, `strategies/scalp/v_reversal.py:39`, `strategies/scalp/v_reversal.py:40`, `strategies/scalp/v_reversal.py:50`, `strategies/scalp/v_reversal.py:60`, `strategies/scalp/v_reversal.py:61`, `strategies/scalp/v_reversal.py:62`, `strategies/scalp/v_reversal.py:63`, `strategies/scalp/v_reversal.py:64`, `strategies/scalp/v_reversal.py:65`, `strategies/scalp/v_reversal.py:66`, `strategies/scalp/v_reversal.py:88`, `strategies/scalp/v_reversal.py:89`, `strategies/scalp/v_reversal.py:90`, `strategies/scalp/v_reversal.py:91`, `strategies/scalp/v_reversal.py:92`, `strategies/scalp/v_reversal.py:93`, `strategies/scalp/v_reversal.py:94` |
| 3 (timing window) | LOOKAHEAD | 現在足の `ctx.entry`, `ctx.open_price`, `ctx.rsi`, `ctx.bbpb`, `ctx.stoch_k`, `ctx.macdh` と `df.iloc[-1]` の High/Low を直接使う。strategy file 内に closed-bar 固定、signal bar と execution bar の分離、または `(strategy, instrument, bar_time)` dedup がないため、実行層が intrabar evaluate する場合は未確定 candle の陽線/陰線・body ratio・indicator turn で signal が点灯し、同一 bar 多重 entry も起き得る。`strategies/scalp/v_reversal.py:26`, `strategies/scalp/v_reversal.py:53`, `strategies/scalp/v_reversal.py:54`, `strategies/scalp/v_reversal.py:55`, `strategies/scalp/v_reversal.py:57`, `strategies/scalp/v_reversal.py:60`, `strategies/scalp/v_reversal.py:61`, `strategies/scalp/v_reversal.py:62`, `strategies/scalp/v_reversal.py:63`, `strategies/scalp/v_reversal.py:64`, `strategies/scalp/v_reversal.py:66`, `strategies/scalp/v_reversal.py:80`, `strategies/scalp/v_reversal.py:88`, `strategies/scalp/v_reversal.py:89`, `strategies/scalp/v_reversal.py:90`, `strategies/scalp/v_reversal.py:91`, `strategies/scalp/v_reversal.py:92`, `strategies/scalp/v_reversal.py:94`, `strategies/scalp/v_reversal.py:108` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | 追加の MA trend filter や HMM regime hard gate はなく、`feedback_ma_filter_breaks_mr.md` 型の「MR に MA 整合を被せる」破壊や、`feedback_hmm_gate_same_trap.md` 型の regime tail 破壊はこの file では未検出。急変幅、3 指標 extreme、反転 candle、Stoch 回復、任意の RSI divergence / BB%B 回復 / MACD-H 反転加点は thesis を強化する。`apply_penalty(..., self.strategy_type, ctx.adx)` は entry gate ではなく confidence adjustment なので NEUTRAL から STRENGTHENS 寄り。`strategies/scalp/v_reversal.py:12`, `strategies/scalp/v_reversal.py:36`, `strategies/scalp/v_reversal.py:42`, `strategies/scalp/v_reversal.py:50`, `strategies/scalp/v_reversal.py:60`, `strategies/scalp/v_reversal.py:66`, `strategies/scalp/v_reversal.py:73`, `strategies/scalp/v_reversal.py:77`, `strategies/scalp/v_reversal.py:80`, `strategies/scalp/v_reversal.py:88`, `strategies/scalp/v_reversal.py:94`, `strategies/scalp/v_reversal.py:101`, `strategies/scalp/v_reversal.py:105`, `strategies/scalp/v_reversal.py:108`, `strategies/scalp/v_reversal.py:119` |
| 5 (stop/TP geometry) | MISALIGNED | Nominal は `tp_mult = 1.5`, `sl_mult = 0.7` なので基準 R:R は `1.5 / 0.7 = 2.14`。ただし実 SL は BUY で `min(entry - 0.7ATR7, recent_low - 0.002)`、SELL で `max(entry + 0.7ATR7, recent_high + 0.002)` と直近 3 本 extreme 外側へ拡張され得る。MR として「mean まで戻る前に切らない」意図は一部あるが、TP が BB mid / EMA / 急落前水準などの mean target ではなく固定 `1.5ATR` で、現在足反転確認後の scalp MR に対して必要勝率と摩擦負担を上げる。`strategies/scalp/v_reversal.py:23`, `strategies/scalp/v_reversal.py:24`, `strategies/scalp/v_reversal.py:83`, `strategies/scalp/v_reversal.py:84`, `strategies/scalp/v_reversal.py:85`, `strategies/scalp/v_reversal.py:111`, `strategies/scalp/v_reversal.py:112`, `strategies/scalp/v_reversal.py:113` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。strategy file に pair filter はなく `ALL` に適用される一方、既存 evidence はほぼ USDJPY に偏り、USDJPY 内でも London / NY-overlap が negative。ALL cell としては FORCED。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative partial | tier-master の force_demoted / ALL 365d BT EV は `—`。latest gate-progression aggregate は N=5, WR=20.00%, Wilson lo=3.62%, EV=-0.98p, PF=0.642, Kelly=0.0000, raw Kelly=-0.1114, Bonferroni p=1.0000。local `demo_trades.db` の exact `v_reversal` 行は `demo_trades` / `evaluated_candidates` / `oanda_audit` で 0 件。WF folds>=3 は対象 evidence で見つからず、`feedback_partial_quant_trap.md` 基準では N/WR/EV だけで採用判断不可。 |

### Pair-Regime Table

| Pair / scope | Fit | Evidence |
|--------------|-----|----------|
| USD_JPY | FORCED / weak candidate | tier-master JSON では UNIVERSAL_SENTINEL 対象にも `v_reversal × USD_JPY` が残るが、R2 counterfactual は N=5, WR=20.00%, Wilson lo=3.62%, EV=-0.98p, PF=0.642, Kelly raw=-0.1114, Bonferroni p=1.0000 で STOP_OANDA。3month shadow bucket も London N=9 EV=-2.178 / PF=0.40、NY-overlap N=6 EV=-3.183 / PF=0.23。 |
| EUR_USD | FORCED / unproven | 現行 force_demoted / ALL 入力に 365d BT EV はなく、decision-grade の Wilson / PF / Bonferroni / Kelly が揃う pair evidence は見つからない。 |
| GBP_USD | FORCED / unproven | 同上。V reversal thesis 自体は高ボラ pair で自然だが、現行 audit DB / tier-master では復帰根拠なし。 |
| Other ALL pairs | FORCED / untested | strategy file は pair を限定しないため発火し得るが、ALL 適用を支持する既存 decision-grade evidence はない。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の trigger は MR thesis を数学的に捕捉しており、Axis 4 でも MA filter / HMM gate のような thesis 破壊は見えない。したがって「思想は正、設計が誤」の候補として扱えるが、現行は現在足の反転を未確定のまま拾える timing と、固定 ATR target / recent extreme stop の geometry が scalp MR と噛み合っていない。

再設計案は、まず closed-bar 化すること。signal bar を `df.iloc[-2]` に固定し、`rsi`, `bb_pband`, `stoch_k`, `Open/Close/High/Low`, body ratio, MACD-H turn をすべて確定足から読む。entry は次 bar execution に分離し、dispatcher または strategy 側で `(v_reversal, instrument, signal, signal_bar_time)` dedup を必須にする。

次に geometry を mean-reversion target に寄せる。BUY の TP は `min(entry + 1.0ATR7, bb_mid or pre-drop midpoint)`、SELL は `max(entry - 1.0ATR7, bb_mid or pre-surge midpoint)` のように mean target を参照し、SL は直近 3 本 extreme 外側を維持しつつ最大許容幅を ATR で cap する variant を検証対象にする。pair scope はまず USDJPY を bucket 分解し、London / NY-overlap の loss pocket を除外できるかを再検証する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は維持候補。コードから V 字 MR thesis は明確に導出でき、trigger も oversold/overbought と反転確認を含むため、thesis 自体を棄却する根拠はない。一方で、closed-bar / dedup / signal-to-execution 分離が strategy file から保証されず、現在足の揺れを反転として認識する構造がある。

具体修正は複数軸にまたがる。最小 redesign は `[-2]` 確定足で signal を作り、`[-1]` または実行層価格で entry する closed-bar variant を作ること。あわせて TP を固定 `1.5ATR` から BB mid / 直近急変前 midpoint / `1.0ATR` 上限の mean target に変更し、SL は recent extreme 外側を維持しつつ ATR cap を入れる。採用前には本 audit では実行しない 365d 以上、pair/session bucket 別、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact で再発行する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master force_demoted/ALL: `—`; latest gate-progression aggregate: 5; local `demo_trades.db`: 0 exact rows; legacy deep dive: 13; TP-hit causal deep: 14 | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `demo_trades.db`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/sessions/tp-hit-causal-deep-2026-04-22.md` |
| Win rate | latest gate-progression aggregate: 20.00%; legacy deep dive: 23.1%; TP-hit causal deep: 21.4% | same as above |
| Wilson lo (95%) | latest gate-progression aggregate: 3.62%; TP-hit causal deep: 7.6%; legacy cell USDJPY×ny×BUY: 3.0% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/tp-hit-causal-deep-2026-04-22.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| PF | latest gate-progression aggregate: 0.642; R2 counterfactual USDJPY: 0.642; legacy deep dive: 0.41; TP-hit causal deep: 0.40 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/sessions/tp-hit-causal-deep-2026-04-22.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: legacy deep dive has only pre/post split (`pre-Cutoff N=2 WR=50.0% / post-Cutoff N=11 WR=18.2%`), not >=3 WF folds. | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Bonferroni-adj p | latest gate-progression aggregate: 1.0000; R2 counterfactual USDJPY: 1.0000; 3month H1 hour-bucket rows: 1.0000 across USDJPY buckets | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Kelly fraction | latest gate-progression aggregate clipped Kelly: 0.0000, raw Kelly: -0.1114; legacy deep dive Kelly: -33.7%; TP-hit causal deep TP-capable rate: 16.7% but no positive Kelly evidence | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/sessions/tp-hit-causal-deep-2026-04-22.md` |
