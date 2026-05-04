---
strategy: ema200_reversal
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

コード上の実体名は `ema200_trend_reversal`。思想は「直近で EMA200 を跨いだ後、短期 EMA が EMA200 の新トレンド側に乗り、価格が EMA200 近傍へ戻ったリテストで、MACD ヒストグラムの方向改善を確認して新トレンド方向へ入る」pullback / reversal-following thesis。根拠は `strategy_type = "pullback"`、EMA200 クロス検出、EMA200 から 0.5ATR 未満の距離制約、BUY/SELL の MACDH 方向条件にある。`strategies/daytrade/ema200_reversal.py:12` `strategies/daytrade/ema200_reversal.py:15` `strategies/daytrade/ema200_reversal.py:34` `strategies/daytrade/ema200_reversal.py:46` `strategies/daytrade/ema200_reversal.py:50` `strategies/daytrade/ema200_reversal.py:62`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / pullback thesis に対して、BUY は `ema9 > ema200 ∧ ema21 > ema200 ∧ 0 < (entry - ema200) / ATR < 0.5 ∧ macdh > macdh_prev ∧ rsi < 55`、SELL は `¬bull200 ∧ -0.5 < dist < 0 ∧ macdh < macdh_prev ∧ rsi > 45`。EMA 整合・直近クロス・EMA200 近傍リテスト・MACD 方向確認が入っており、MR thesis の oversold 単独 trigger ではない。`strategies/daytrade/ema200_reversal.py:26` `strategies/daytrade/ema200_reversal.py:27` `strategies/daytrade/ema200_reversal.py:37` `strategies/daytrade/ema200_reversal.py:42` `strategies/daytrade/ema200_reversal.py:50` `strategies/daytrade/ema200_reversal.py:62` |
| 3 (timing window) | LOOKAHEAD | 直接の未来参照は見えないが、クロス検出は `iloc[-_ec - 1]` と `iloc[-_ec]` で過去バーを参照し、現行 `ctx.entry` との距離で実行判定する構造。さらにこの strategy ファイル内には `ctx.bar_time` を使った per-bar dedup がなく、条件が同一バー内で複数回評価される環境では同一シグナル多重 entry のリスクが残る。spec の「bar dedup 欠落は LOOKAHEAD 寄り」に従い `LOOKAHEAD`。`strategies/daytrade/ema200_reversal.py:18` `strategies/daytrade/ema200_reversal.py:37` `strategies/daytrade/ema200_reversal.py:46` `strategies/daytrade/ema200_reversal.py:78` |
| 4 (filter coherence) | STRENGTHENS | EMA200 からの最大距離 `0.5ATR` はリテスト局面に限定し、RSI の BUY `<55` / SELL `>45` は過伸展追随を抑えるため thesis を強化する。EMA200 rising/falling は gate ではなく score 加点で、方向確認として強化。ADX penalty は `pullback` 型に対する confidence cap であり entry gate ではないため中立寄りの強化。本戦略は MR ではないため `feedback_ma_filter_breaks_mr.md` の「MA filter on MR strategy → BREAKS」には該当せず、HMM gate も存在しないため `feedback_hmm_gate_same_trap.md` の same-trap は未検出。`strategies/daytrade/ema200_reversal.py:12` `strategies/daytrade/ema200_reversal.py:15` `strategies/daytrade/ema200_reversal.py:29` `strategies/daytrade/ema200_reversal.py:50` `strategies/daytrade/ema200_reversal.py:55` `strategies/daytrade/ema200_reversal.py:62` `strategies/daytrade/ema200_reversal.py:67` `strategies/daytrade/ema200_reversal.py:77` |
| 5 (stop/TP geometry) | ALIGNED | BUY は `tp = entry + atr7 * 2.0`, `sl = entry - atr7 * 1.0`、SELL は対称に `2.0R : 1.0R`。EMA200 リテスト後の新トレンド継続を取りに行く pullback / momentum 型として、利を伸ばす非対称 R:R は整合。`strategies/daytrade/ema200_reversal.py:58` `strategies/daytrade/ema200_reversal.py:59` `strategies/daytrade/ema200_reversal.py:70` `strategies/daytrade/ema200_reversal.py:71` |
| 6 (pair-regime fit) | FORCED | コード内に pair-specific gate がなく ALL に強制適用される。既存監査集計では USD_JPY は shadow N=12, EV +6.858p, PF 4.724 と fit する一方、EUR_JPY は N=12, EV -1.567p, PF 0.836、EUR_USD は N=2, EV -5.650p, PF 0.000、GBP_USD は N=3, EV -0.433p, PF 0.917。pair-regime fit は USD_JPY=FIT、EUR_JPY=FORCED、EUR_USD=FORCED、GBP_USD=FORCED、GBP_JPY=INSUFFICIENT/FORCED。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | 3-month H1 hour-bucket counterfactual の shadow 集計から ALL 合算は N=32, WR 40.6%, Wilson lo 25.5%, EV +1.881p, PF 1.329, Kelly 0.101。ただし family Bonferroni p は 1.000、tier-master の 365d BT EV は `—`、WF folds (3+) は対象 artifact で欠落。`feedback_partial_quant_trap.md` 準拠では N/WR/EV だけでは不可であり、PF/Kelly は埋まるが Bonferroni/WF が不足するため統計的には insufficient。 |

## Axis 8: failure mode 診断

Tier 2 Shadow / phase0_shadow としての failure mode は、思想そのものではなく Axis 3 と Axis 6/7 に集中する。Axis 2/4/5 は設計上は概ね整合しているが、同一バー dedup 欠落により実運用で signal→execution が過密化する可能性があり、さらに pair gate がないため USD_JPY のみ強い edge を ALL に薄めている。

再設計案: `ctx.bar_time` または df index の最新 closed bar を使った per-bar dedup を追加し、同一 symbol / signal / bar の再発火をブロックする。そのうえで pair gate を USD_JPY 優先、または少なくとも `instrument == "USD_JPY"` と NY-overlap 近辺に限定する shadow variant に分離する。trigger 本体は維持し、`ema200_dist_max` と RSI cap は二次検証対象に留める。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

最小再設計は timing と routing の 1 系統修正。`evaluate()` の先頭または Candidate 返却直前に、`(ctx.symbol, signal, closed_bar_ts)` を key にした per-bar dedup を入れる。既存の daytrade 実装例と同じく `ctx.bar_time` があればそれを使い、なければ `ctx.df.index[-1]` を fallback にする。

次に ALL 運用をやめ、USD_JPY 優先セルとして扱う。既存監査では USD_JPY shadow の aggregate が N=12, WR 58.3%, EV +6.858p, PF 4.724, Kelly 0.460 と最も coherent で、ALL 合算の弱さは EUR/GBP 側の forced application による希釈が大きい。BT 再実行なしで現時点に採れる判断は「trigger は維持、dedup + pair/session routing を再設計して追加 shadow 観測」。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 32 (shadow ALL aggregate); USD_JPY subset 12 | audit DB: `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` shadow cells, derived aggregate |
| Win rate | 40.6% (13/32); USD_JPY 58.3% (7/12) | audit DB: same as above |
| Wilson lo (95%) | 25.5%; USD_JPY 32.0% | audit DB: same as above, Wilson aggregate derived from wins/N |
| PF | 1.329; USD_JPY 4.724 | audit DB: same as above, gross profit/loss reconstructed from cell PF and EV |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no fold-level result in tier-master input; existing 3-month counterfactual is not WF folds | tier-master input: `365d BT EV = —`; audit DB lacks WF fold table for this cell |
| Bonferroni-adj p | 1.000 on available shadow cells | audit DB: `p_value_bonf` in H1 hour-bucket counterfactual |
| Kelly fraction | 0.101; USD_JPY 0.460 | audit DB: derived aggregate from reconstructed payoff; per-cell Kelly present where losses exist |
