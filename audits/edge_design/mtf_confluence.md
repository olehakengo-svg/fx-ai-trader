---
strategy: mtf_confluence
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

複数時間軸の RSI が売られすぎ/買われすぎに寄った局面で、MACD-H と Stoch の短期反転が同方向に揃った瞬間だけ、平均回帰の初動を取りに行く MR 戦略。コード上も `strategy_type = "MR"` とされ、BUY/SELL は MTF RSI extreme + MACD-H 反転 + Stoch 反転の AND で発火する。`strategies/scalp/mtf_confluence.py:11`, `strategies/scalp/mtf_confluence.py:32`, `strategies/scalp/mtf_confluence.py:34`, `strategies/scalp/mtf_confluence.py:35`, `strategies/scalp/mtf_confluence.py:36`, `strategies/scalp/mtf_confluence.py:38`, `strategies/scalp/mtf_confluence.py:61`, `strategies/scalp/mtf_confluence.py:62`, `strategies/scalp/mtf_confluence.py:63`, `strategies/scalp/mtf_confluence.py:64`, `strategies/scalp/mtf_confluence.py:66`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `((rsi5<45 AND h1_rsi<48) OR (rsi5<40 AND h4_rsi<52)) AND macdh>0 AND macdh>macdh_prev AND stoch_k>stoch_d AND stoch_k<45`。SELL は `((rsi5>55 AND h1_rsi>52) OR (rsi5>60 AND h4_rsi>48)) AND macdh<0 AND macdh<macdh_prev AND stoch_k<stoch_d AND stoch_k>55`。RSI extreme、MACD-H 反転、Stoch 反転を使っており、MR の oversold/overbought trigger を数学的に捕捉している。`strategies/scalp/mtf_confluence.py:34`, `strategies/scalp/mtf_confluence.py:35`, `strategies/scalp/mtf_confluence.py:36`, `strategies/scalp/mtf_confluence.py:38`, `strategies/scalp/mtf_confluence.py:62`, `strategies/scalp/mtf_confluence.py:63`, `strategies/scalp/mtf_confluence.py:64`, `strategies/scalp/mtf_confluence.py:66` |
| 3 (timing window) | LOOKAHEAD | `evaluate()` は `ctx.rsi5`, `ctx.macdh`, `ctx.macdh_prev`, `ctx.stoch_k/d`, `ctx.entry` をそのまま使って signal と TP/SL を返すが、この strategy file 内には closed-bar 判定、bar timestamp、または `(symbol, bar_time, signal)` dedup がない。未来参照式は見えないが、実行層が intrabar に複数回 evaluate する場合、未確定足 signal と同一バー多重 entry のリスクが残るため spec 上は LOOKAHEAD 寄り。`strategies/scalp/mtf_confluence.py:18`, `strategies/scalp/mtf_confluence.py:34`, `strategies/scalp/mtf_confluence.py:35`, `strategies/scalp/mtf_confluence.py:36`, `strategies/scalp/mtf_confluence.py:58`, `strategies/scalp/mtf_confluence.py:59`, `strategies/scalp/mtf_confluence.py:83`, `strategies/scalp/mtf_confluence.py:84`, `strategies/scalp/mtf_confluence.py:91` |
| 4 (filter coherence) | STRENGTHENS | H1/H4 RSI の MTF 条件は単一足の oversold/overbought だけでなく上位足も同じ歪みにあることを要求するため MR thesis を強化する。H1 score は entry gate ではなく、BUY では `_htf_h1_score > 0`、SELL では `_htf_h1_score < 0` の場合だけ加点する補助 confluence なので中立から強化。`apply_penalty(..., strategy_type='MR', ctx.adx)` は高 ADX の MR confidence を落とす汎用 regime penalty で、MA filter on MR や HMM same-trap 型の hard gate ではないが、edge tail を消す可能性は Axis 7 不足のため未検証。`strategies/scalp/mtf_confluence.py:26`, `strategies/scalp/mtf_confluence.py:27`, `strategies/scalp/mtf_confluence.py:28`, `strategies/scalp/mtf_confluence.py:29`, `strategies/scalp/mtf_confluence.py:30`, `strategies/scalp/mtf_confluence.py:34`, `strategies/scalp/mtf_confluence.py:49`, `strategies/scalp/mtf_confluence.py:53`, `strategies/scalp/mtf_confluence.py:62`, `strategies/scalp/mtf_confluence.py:75`, `strategies/scalp/mtf_confluence.py:78`, `strategies/scalp/mtf_confluence.py:90` |
| 5 (stop/TP geometry) | MISALIGNED | Code-level geometry は `tp_mult=1.5`, `sl_mult=0.5` なので nominal R:R は `1.5ATR / 0.5ATR = 3.0R`。BUY は `tp=entry+1.5ATR`, `sl=entry-0.5ATR`、SELL は `tp=entry-1.5ATR`, `sl=entry+0.5ATR`。MR は平均へ戻る前のノイズで切られない wide stop が必要だが、現行は tight stop / far TP の momentum 型 geometry で、MTF 反転の初動を拾う思想と衝突する。`strategies/scalp/mtf_confluence.py:15`, `strategies/scalp/mtf_confluence.py:16`, `strategies/scalp/mtf_confluence.py:58`, `strategies/scalp/mtf_confluence.py:59`, `strategies/scalp/mtf_confluence.py:83`, `strategies/scalp/mtf_confluence.py:84` |
| 6 (pair-regime fit) | FORCED | `ALL` scope に対し、strategy file には instrument/pair 別の許可・除外・閾値調整がない。既存 evidence では USD_JPY に小 N の positive cell がある一方、EUR_USD は NY-overlap N=2/WR=0% で、GBP_USD は phase0 shadow gate 以外の fit evidence が乏しい。下の pair-regime table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / positive small-N | gate-progression 由来の strategy aggregate は N=10, WR=50.00%, Wilson lo=23.66%, EV=+0.49p, PF=1.441, Kelly=0.0664, raw Kelly=+0.0664, Bonferroni p=1.0000。PF/Kelly は positive だが N=10 かつ Bonferroni 不通過で、WF folds (3+) も tier-master/audit DB から確認できない。tier-master 365d BT EV は入力どおり `—`。`feedback_partial_quant_trap.md` 基準では採用判断には不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT / insufficient | H1 hour-bucket counterfactual では USD_JPY NY-overlap N=1/WR=100%/EV=+4.2、Off N=1/WR=100%/EV=+3.2。方向は良いが小 N すぎる。 |
| EUR_USD | FORCED | H1 hour-bucket counterfactual では EUR_USD NY-overlap N=2/WR=0%/EV=-1.8。MTF MR thesis の pair fit は未証明。 |
| GBP_USD | FORCED / unproven | shadow tracking 条件には `phase0_tier_shadow_gate` と `audit_state_drift_shadow_skip_not_final_shadow` があるが、pair-level PF/Wilson/Kelly は確認できない。 |
| Other ALL pairs | FORCED | strategy file に pair filter がなく、ALL へ機械的に広げている。pair-specific thesis fit は audit DB / tier-master から確認できない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、tier-master 365d BT EV が `—` で、既存集計も N=10 / Bonferroni p=1.0000 / WF folds 欠落のため、metrics 劣化または under-evidenced shadow として failure mode を診断する。

破綻軸は Axis 3 と Axis 5。Axis 2 の trigger は MTF RSI extreme + MACD-H/Stoch 反転で MR thesis と整合し、Axis 4 の filter も hard gate で edge tail を消す構造は明確ではない。主問題は、strategy file 内に closed-bar/dedup の担保がなく intrabar 多重 emit リスクがあることと、MR なのに 0.5ATR stop / 1.5ATR TP の tight-stop 3R geometry を採用していること。

再設計案は、まず signal 判定を確定足に寄せ、同一 `(instrument, strategy, bar_time, signal)` の再 emit を禁止する。次に TP/SL を MR 形状へ反転し、例として `sl_mult` を 1.0-1.5ATR、`tp_mult` を 0.6-1.0ATR または BB/EMA mean 到達ベースへ変更する。MACD-H/Stoch は entry の瞬間確認として残し、TP は「平均へ戻ったら利確」、SL は「MTF RSI thesis が否定される深い伸び」で切る形にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想は明確で、trigger も MR と整合しているため棄却しない。修正優先度は stop/TP geometry と timing の 2 点だが、どちらも戦略思想を変えずに実装可能なため `A` とする。

コードレベルでは、`evaluate()` が現在値を直接使って返す構造に対して、dispatch 層または strategy 層で closed bar id を渡し、同一 bar の再発火を抑止する。あわせて `tp_mult = 1.5`, `sl_mult = 0.5` を MR 用に再設計し、BUY/SELL の TP を短期 mean/0.8ATR 近辺、SL を 1.2ATR 以上へ広げる variant を作る。採用前には本 audit では実行しない 365d + WF folds>=3 の再集計で、Wilson lower / PF / Bonferroni p / Kelly を同一 source から出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 10 | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Win rate | 50.00% | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Wilson lo (95%) | 23.66% | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| PF | 1.441 | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; tier-master 365d BT EV is `—` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: tier-master / audit DB から `mtf_confluence` または `mtf_reversal_confluence` の folds>=3 は確認できない | tier-master + audit DB |
| Bonferroni-adj p | 1.0000 | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Kelly fraction | 0.0664 (raw Kelly +0.0664) | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
