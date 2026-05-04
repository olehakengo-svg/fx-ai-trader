---
strategy: dt_bb_rsi_mr
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

15m 足で BB%B 下限/上限接近、RSI14、Stoch 過熱/反転、反転足を合わせ、レンジ環境だけで BB 中心方向への平均回帰を狙う MR 戦略。1m `bb_rsi_reversion` のコアを 15m に移植し、ADX>=25 のトレンド環境は捨てる設計思想である。strategies/daytrade/dt_bb_rsi_mr.py:2, strategies/daytrade/dt_bb_rsi_mr.py:14, strategies/daytrade/dt_bb_rsi_mr.py:15, strategies/daytrade/dt_bb_rsi_mr.py:16, strategies/daytrade/dt_bb_rsi_mr.py:17, strategies/daytrade/dt_bb_rsi_mr.py:18, strategies/daytrade/dt_bb_rsi_mr.py:19

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対し、BUY は `bbpb<=0.30 AND rsi<45 AND stoch_k<40 AND (K>D OR K>prev_K) AND close>open`、SELL は `bbpb>=0.70 AND rsi>55 AND stoch_k>60 AND (K<D OR K<prev_K) AND close<open`。BB extension、RSI/Stoch 過熱、反転確認は揃うため方向は PASS。ただし primary threshold は BB%B 0.30/0.70・RSI 45/55 まで緩く、極端条件は score だけで gate ではないため、15m MR としては弱い trigger。strategies/daytrade/dt_bb_rsi_mr.py:57, strategies/daytrade/dt_bb_rsi_mr.py:58, strategies/daytrade/dt_bb_rsi_mr.py:65, strategies/daytrade/dt_bb_rsi_mr.py:66, strategies/daytrade/dt_bb_rsi_mr.py:73, strategies/daytrade/dt_bb_rsi_mr.py:74, strategies/daytrade/dt_bb_rsi_mr.py:149, strategies/daytrade/dt_bb_rsi_mr.py:150, strategies/daytrade/dt_bb_rsi_mr.py:151, strategies/daytrade/dt_bb_rsi_mr.py:152, strategies/daytrade/dt_bb_rsi_mr.py:153, strategies/daytrade/dt_bb_rsi_mr.py:157, strategies/daytrade/dt_bb_rsi_mr.py:214, strategies/daytrade/dt_bb_rsi_mr.py:215, strategies/daytrade/dt_bb_rsi_mr.py:216, strategies/daytrade/dt_bb_rsi_mr.py:217, strategies/daytrade/dt_bb_rsi_mr.py:218, strategies/daytrade/dt_bb_rsi_mr.py:221 |
| 3 (timing window) | LOOKAHEAD | `ctx.entry` / `ctx.open_price` の現在足反転確認と、`ctx.bbpb`, `ctx.rsi`, `ctx.stoch_k`, `ctx.stoch_d` の現在値で signal を作る一方、strategy 内に closed-bar 判定や `(symbol, bar_time, signal)` dedup がない。`df.iloc[-2]` は Stoch 前バー参照で未来参照ではないが、実行層が intrabar evaluate すると未確定足 signal と同一 bar 多重 entry のリスクが残るため LOOKAHEAD 寄り。strategies/daytrade/dt_bb_rsi_mr.py:140, strategies/daytrade/dt_bb_rsi_mr.py:141, strategies/daytrade/dt_bb_rsi_mr.py:149, strategies/daytrade/dt_bb_rsi_mr.py:150, strategies/daytrade/dt_bb_rsi_mr.py:151, strategies/daytrade/dt_bb_rsi_mr.py:157, strategies/daytrade/dt_bb_rsi_mr.py:214, strategies/daytrade/dt_bb_rsi_mr.py:215, strategies/daytrade/dt_bb_rsi_mr.py:216, strategies/daytrade/dt_bb_rsi_mr.py:221, strategies/daytrade/dt_bb_rsi_mr.py:336 |
| 4 (filter coherence) | BREAKS | Symbol whitelist は設計対象を USDJPY/EURUSD/GBPUSD に絞るため ALL cell には FORCED だが、コードコメント上の対象ペアとは一致する。ADX<25 hard gate はコード上の range MR thesis には STRENGTHENS。ただし既存 regime audit では `trend_up_weak` 側の positive tail が示されており、generic regime gate が edge tail を消す `feedback_hmm_gate_same_trap.md` と同型の疑いがある。さらに HTF bear/bull 逆行を soft penalty する設計は MR の反転 entry を上位足トレンド整合で減点するため、MA filter on MR (`feedback_ma_filter_breaks_mr.md`) 型の BREAKS リスク。strategies/daytrade/dt_bb_rsi_mr.py:78, strategies/daytrade/dt_bb_rsi_mr.py:79, strategies/daytrade/dt_bb_rsi_mr.py:89, strategies/daytrade/dt_bb_rsi_mr.py:92, strategies/daytrade/dt_bb_rsi_mr.py:114, strategies/daytrade/dt_bb_rsi_mr.py:115, strategies/daytrade/dt_bb_rsi_mr.py:124, strategies/daytrade/dt_bb_rsi_mr.py:310, strategies/daytrade/dt_bb_rsi_mr.py:311, strategies/daytrade/dt_bb_rsi_mr.py:312, strategies/daytrade/dt_bb_rsi_mr.py:313, strategies/daytrade/dt_bb_rsi_mr.py:314, strategies/daytrade/dt_bb_rsi_mr.py:315, strategies/daytrade/dt_bb_rsi_mr.py:316, strategies/daytrade/dt_bb_rsi_mr.py:317, strategies/daytrade/dt_bb_rsi_mr.py:318 |
| 5 (stop/TP geometry) | MISALIGNED | SL は `max(ATR*1.2, min_sl)`、TP は `ATR*1.5` で、実効 R:R はおおむね 1.25。コメント上は BB_mid targeting が別途適用される前提だが、Candidate 自体の TP は BB_mid ではなく固定 ATR 距離で、15m MR が平均へ戻る前に 1.2ATR stop で切られる構造を持つ。MR の「wide stop で mean 到達を待つ」幾何としては弱く、RR floor 1.2 も force-demoted 後の evidence に対して不足。strategies/daytrade/dt_bb_rsi_mr.py:20, strategies/daytrade/dt_bb_rsi_mr.py:21, strategies/daytrade/dt_bb_rsi_mr.py:27, strategies/daytrade/dt_bb_rsi_mr.py:28, strategies/daytrade/dt_bb_rsi_mr.py:82, strategies/daytrade/dt_bb_rsi_mr.py:83, strategies/daytrade/dt_bb_rsi_mr.py:84, strategies/daytrade/dt_bb_rsi_mr.py:205, strategies/daytrade/dt_bb_rsi_mr.py:206, strategies/daytrade/dt_bb_rsi_mr.py:207, strategies/daytrade/dt_bb_rsi_mr.py:208, strategies/daytrade/dt_bb_rsi_mr.py:209, strategies/daytrade/dt_bb_rsi_mr.py:269, strategies/daytrade/dt_bb_rsi_mr.py:270, strategies/daytrade/dt_bb_rsi_mr.py:271, strategies/daytrade/dt_bb_rsi_mr.py:272, strategies/daytrade/dt_bb_rsi_mr.py:273, strategies/daytrade/dt_bb_rsi_mr.py:285, strategies/daytrade/dt_bb_rsi_mr.py:287 |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。コードは ALL ではなく USDJPY/EURUSD/GBPUSD のみ通す。既存 365d BT は 3 ペアすべて負 EV / PF<1 で、直近 audit では USDJPY の小 N positive cell はあるが ALL としては forced broad scope。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の FORCE_DEMOTED / ALL 365d BT EV は `—`。最新 gate-progression aggregate では N=14, WR=50.00%, Wilson lo=26.80%, EV=+0.03p, PF=1.008, Kelly=0.0042, Bonferroni p=1.0000。USDJPY cell は N=7, WR=57.14%, Wilson lo=25.05%, PF=1.840, raw Kelly=+0.2609 だが小 N かつ Bonferroni p=1.0000。WF folds>=3 の既存 BT は negative/unstable で、promotion-grade には不足。`feedback_partial_quant_trap.md` 基準では採用判断不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED | Code allows USDJPY, but 365d BT was N=319, WR=54.2%, EV=-0.023, PF=0.96. Latest R2 cell has N=7, WR=57.14%, Wilson lo=25.05%, PF=1.840, raw Kelly=+0.2609, Bonferroni p=1.0000, so positive evidence is small-N tail only. |
| EURUSD | FORCED | Code allows EURUSD, but 365d BT was N=102, WR=52.0%, EV=-0.077, PF=0.87. It is also PAIR_DEMOTED in tier-master. |
| GBPUSD | FORCED | Code allows GBPUSD, but 365d BT was N=187, WR=51.3%, EV=-0.135, PF=0.77. |
| Other pairs in ALL | FORCED | `_ALLOWED_SYMBOLS` excludes all other pairs, so `pairs: ALL` is not actually tradable by this strategy implementation. strategies/daytrade/dt_bb_rsi_mr.py:92, strategies/daytrade/dt_bb_rsi_mr.py:114, strategies/daytrade/dt_bb_rsi_mr.py:115 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) のため failure mode 診断対象。破綻軸は Axis 3 / 4 / 5。Axis 2 の BB/RSI/Stoch trigger は MR 方向を捉えているが、現在足反転確認のまま closed-bar/dedup がなく、HTF 逆行 penalty と ADX hard range gate が MR の有効 tail を落とす可能性がある。さらに TP が BB_mid ではなく ATR 固定で、SL 1.2ATR / TP 1.5ATR の薄い幾何は 15m MR の戻り待ちと合わない。

再設計案は、まず timing を closed-bar 化し、`df.iloc[-2]` の BB%B / RSI / Stoch / candle color で signal を確定し、次 bar で約定する variant を作ること。同時に `(symbol, signal, closed_bar_time)` dedup を dispatch 層または strategy 層で必須にする。次に filter は generic HTF 方向 penalty を外し、ADX<25 range 版と trend_up_weak tail 版を分離して、`feedback_hmm_gate_same_trap.md` 型の hard gate で positive tail を消さない。

Stop/TP は BB_mid target を Candidate の TP に明示し、SL は band 外側 + ATR buffer へ移す。少なくとも現行 `SL_ATR_MULT=1.2`, `TP_ATR_MULT=1.5`, `MIN_RR=1.2` の固定 ATR 形から、`tp = bb_mid`、`sl = bb_outer ± 0.3-0.5ATR`、または RR floor 2.0+ の rescue variant に切り替えるべき。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想はコードから明確に導出でき、BB/RSI/Stoch による 15m 平均回帰という thesis 自体は捨てる段階ではない。ただし force-demoted decomposition は 1m→15m ポーティングの失敗を示し、現行実装も timing、filter、stop/TP の複数軸で壊れているため、一点修正では足りない。

具体修正は三つ。第一に signal 判定を確定足に寄せ、現在足 `ctx.entry/open_price` 反転確認を `df.iloc[-2]` ベースへ移し、同一 bar dedup を追加する。第二に HTF 逆行 soft penalty を削除し、ADX<25 range MR と `trend_up_weak` tail を別 variant に分ける。第三に TP を BB_mid 明示 target、SL を band 外側 + ATR buffer に変更し、固定 ATR 1.2/1.5 の薄い RR 形を捨てる。

採用前には本 audit では実行しない 365d 以上、pair 別、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact で出す再検証が必要。N/WR/EV だけ、または USDJPY N=7 の小標本だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Latest live strategy aggregate: N=14; USDJPY protected cell: N=7; 365d BT pair totals: USDJPY 319 / EURUSD 102 / GBPUSD 187 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`; `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md` |
| Win rate | Latest live strategy aggregate: 50.00%; USDJPY protected cell: 57.14%; 365d BT: USDJPY 54.2% / EURUSD 52.0% / GBPUSD 51.3% | same as above |
| Wilson lo (95%) | Latest live strategy aggregate: 26.80%; USDJPY protected cell: 25.05% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` |
| PF | Latest live strategy aggregate: 1.008; USDJPY protected cell: 1.840; 365d BT: USDJPY 0.96 / EURUSD 0.87 / GBPUSD 0.77 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`; `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md` |
| WF folds (3+) | Existing WF artifacts have folds>=3 but are negative/unstable: 730d USDJPY folds 23 pos_ratio 0.43; GBPUSD folds 24 pos_ratio 0.29; EURUSD folds 12 pos_ratio 0.33. Not promotion-grade for current ALL cell. | `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.md` |
| Bonferroni-adj p | Latest live strategy aggregate: 1.0000; USDJPY protected cell: 1.0000 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` |
| Kelly fraction | Latest live strategy aggregate: 0.0042; USDJPY protected cell raw Kelly: +0.2609; aggregate-kelly decomposition also reports USDJPY Kelly 34.40% but N=7 small-sample only | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`; `knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03-render.md` |
