---
strategy: sr_channel_reversal
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

水平 support/resistance または parallel channel 端に価格が近づいたところで、RSI5 の偏りと Stoch/MACD-H の短期反転を確認して mean reversion を狙う scalp 戦略。コード上も `strategy_type = "MR"` かつ BUY は support/lower channel、SELL は resistance/upper channel 側でのみ発火する。`strategies/scalp/sr_channel_reversal.py:1`, `strategies/scalp/sr_channel_reversal.py:12`, `strategies/scalp/sr_channel_reversal.py:44`, `strategies/scalp/sr_channel_reversal.py:45`, `strategies/scalp/sr_channel_reversal.py:46`, `strategies/scalp/sr_channel_reversal.py:47`, `strategies/scalp/sr_channel_reversal.py:48`, `strategies/scalp/sr_channel_reversal.py:51`, `strategies/scalp/sr_channel_reversal.py:78`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `(_sr_buy OR _at_ch_lower) AND rsi5 < 45 AND stoch_k > stoch_d`、SELL は `(_sr_sell OR _at_ch_upper) AND rsi5 > 55 AND stoch_k < stoch_d`。SR/channel 端への extension と oscillator 反転を同時に要求しており、数学的捕捉は成立する。ただし RSI 閾値 45/55 は浅く、強い oversold/overbought というより「端付近の軽い偏り」なので trigger 強度は弱い。`strategies/scalp/sr_channel_reversal.py:15`, `strategies/scalp/sr_channel_reversal.py:16`, `strategies/scalp/sr_channel_reversal.py:17`, `strategies/scalp/sr_channel_reversal.py:45`, `strategies/scalp/sr_channel_reversal.py:46`, `strategies/scalp/sr_channel_reversal.py:47`, `strategies/scalp/sr_channel_reversal.py:48`, `strategies/scalp/sr_channel_reversal.py:51`, `strategies/scalp/sr_channel_reversal.py:62`, `strategies/scalp/sr_channel_reversal.py:65`, `strategies/scalp/sr_channel_reversal.py:68`, `strategies/scalp/sr_channel_reversal.py:78`, `strategies/scalp/sr_channel_reversal.py:89`, `strategies/scalp/sr_channel_reversal.py:92`, `strategies/scalp/sr_channel_reversal.py:95` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に closed-bar 固定、signal bar timestamp、per-bar dedup がない。channel は `ctx.df` から都度算出し、最後の channel value と現在 `ctx.entry` の距離で判定するため、実行層が未確定足で `evaluate()` する場合は intrabar の SR/channel 接触・oscillator 反転を同一 bar 内で複数回拾うリスクが残る。`strategies/scalp/sr_channel_reversal.py:23`, `strategies/scalp/sr_channel_reversal.py:35`, `strategies/scalp/sr_channel_reversal.py:38`, `strategies/scalp/sr_channel_reversal.py:41`, `strategies/scalp/sr_channel_reversal.py:42`, `strategies/scalp/sr_channel_reversal.py:45`, `strategies/scalp/sr_channel_reversal.py:46`, `strategies/scalp/sr_channel_reversal.py:47`, `strategies/scalp/sr_channel_reversal.py:48`, `strategies/scalp/sr_channel_reversal.py:104`, `strategies/scalp/sr_channel_reversal.py:109` |
| 4 (filter coherence) | STRENGTHENS | Friday skip は週末流動性を避けるので NEUTRAL/STRENGTHENS。`ctx.sr_levels` / `ctx.df` / `len(ctx.df)` guard は NEUTRAL。SR/channel proximity、RSI extreme bonus、Stoch reversal bonus、MACD-H turn bonus は MR thesis を強化する。`apply_penalty(..., self.strategy_type, ctx.adx)` は MR に対する高 ADX penalty で、MA filter on MR や HMM same-trap と異なり trend hard alignment ではなく逆張り tail を抑える confidence filter なので STRENGTHENS。`strategies/scalp/sr_channel_reversal.py:24`, `strategies/scalp/sr_channel_reversal.py:26`, `strategies/scalp/sr_channel_reversal.py:35`, `strategies/scalp/sr_channel_reversal.py:45`, `strategies/scalp/sr_channel_reversal.py:46`, `strategies/scalp/sr_channel_reversal.py:51`, `strategies/scalp/sr_channel_reversal.py:62`, `strategies/scalp/sr_channel_reversal.py:65`, `strategies/scalp/sr_channel_reversal.py:68`, `strategies/scalp/sr_channel_reversal.py:78`, `strategies/scalp/sr_channel_reversal.py:89`, `strategies/scalp/sr_channel_reversal.py:92`, `strategies/scalp/sr_channel_reversal.py:95`, `strategies/scalp/sr_channel_reversal.py:108` |
| 5 (stop/TP geometry) | MISALIGNED | Nominal geometry は `tp_mult=1.5`, `sl_mult=0.5` で R:R ≈ 3:1。BUY は `tp = entry + atr7 * 1.5`, `sl = min(entry - atr7 * 0.5, nearest_support - atr7 * 0.15)`、SELL は対称。MR は mean に戻る前に切られない wide stop / mean-side target が基本だが、現行は 0.5ATR stop と 1.5ATR target の momentum 型 payoff になっており、SR/channel bounce の思想とずれる。`strategies/scalp/sr_channel_reversal.py:18`, `strategies/scalp/sr_channel_reversal.py:19`, `strategies/scalp/sr_channel_reversal.py:20`, `strategies/scalp/sr_channel_reversal.py:73`, `strategies/scalp/sr_channel_reversal.py:74`, `strategies/scalp/sr_channel_reversal.py:75`, `strategies/scalp/sr_channel_reversal.py:100`, `strategies/scalp/sr_channel_reversal.py:101`, `strategies/scalp/sr_channel_reversal.py:102` |
| 6 (pair-regime fit) | FORCED | `ALL` scope は forced。3か月 h1-hour bucket shadow では USD_JPY 全セッションが負 EV、EUR_USD も London/NY-overlap とも負 EV。GBP_USD は NY-overlap/Off に正セルがあるが N=15/N=6 で小さく、London は壊滅的。下表参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / NEGATIVE | tier-master 365d BT EV は `—`。ただし既存 audit DB は一貫して負で、Gate progression は N=34, WR=26.47%, Wilson lo=14.60%, EV=-0.71, PF=0.640, Kelly=0.0000, raw Kelly=-0.1486, Bonf p=1.0000。3か月 h1-hour bucket shadow は N=292, WR=25.3%, Wilson BF lower=17.95%, EV=-1.116, Bonf p=0.0, Kelly=-0.162。WF folds>=3 は `sr_channel_reversal` ALL について見つからないため、promotion-grade evidence は不足。 |

### Pair-Regime Table

| Pair / bucket | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FORCED | h1 shadow: Asia N=67 EV=-1.430 PF=0.436 Kelly=-0.290; London N=59 EV=-1.053 PF=0.589 Kelly=-0.189; NY-overlap N=40 EV=-1.840 PF=0.430 Kelly=-0.265; Off N=44 EV=-0.634 PF=0.745 Kelly=-0.101。 |
| EUR_USD | FORCED | h1 shadow: London N=21 WR=14.3% EV=-2.819 PF=0.275 Kelly=-0.376; NY-overlap N=25 WR=32.0% EV=-0.460 PF=0.821 Kelly=-0.070。 |
| GBP_USD | FORCED / selective | h1 shadow: London N=14 WR=7.1% EV=-3.907 PF=0.164 Kelly=-0.365。NY-overlap N=15 EV=+0.607 PF=1.166 Kelly=+0.057、Off N=6 EV=+8.400 PF=6.362 Kelly=+0.562 だが小 N かつ ALL scope を救う証拠ではない。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) なので failure mode は必須。破綻軸は Axis 3 と Axis 5、補助的に Axis 6。Trigger は SR/channel 端 + RSI/Stoch/MACD-H 反転で thesis と整合するが、戦略内で bar-close 固定と per-bar dedup がないため、未確定足の接触や反転を拾う timing risk が残る。さらに 0.5ATR stop / 1.5ATR target は scalp MR には狭すぎ、既存 decomposition でも `SL=ATR×0.5 ≈ 摩擦コスト` が根本原因として記録されている。

再設計案は、まず `ctx.df.iloc[-2]` 相当の確定足で SR/channel proximity、RSI5、Stoch cross、MACD-H turn を判定し、次足 `ctx.entry` で candidate 化すること。dispatch 側または strategy state に `(instrument, entry_type, signal_bar_time, direction)` dedup を置き、同一 bar 再発火を塞ぐ。

Stop/TP は MR 型へ置換する。具体的には SL を support/resistance/channel 境界の外側 `1.2-1.8 * ATR7` へ広げ、TP は固定 1.5ATR ではなく channel midline / nearest mean / `0.8-1.0 * ATR7` の mean-side target に寄せる。pair scope は最初から ALL に戻さず、GBP_USD NY-overlap/Off の小N候補と USD_JPY/EUR_USD の明確な負セルを分けて redesign BT を要求する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想はコードから明確に導出でき、trigger も大枠では MR と整合している。一方で、timing が実行層依存で、stop/TP が MR ではなく高 R:R の momentum 型になっているため、現行設計のまま復帰させる根拠はない。

修正は 2 系統必要。第一に trigger 評価を確定足化し、同一 bar dedup を追加する。第二に `tp_mult=1.5 / sl_mult=0.5` を廃止し、boundary-aware wide stop + mean-side target に変更する。採用前に必要な BT は、新 variant について pair/session 別、365d、WF folds>=3、Wilson lo / PF / Bonferroni p / Kelly を同一集計から再発行すること。本監査では BT を実行しない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Gate progression by-strategy N=34; h1-hour bucket 3か月 shadow N=292; negative-edge shadow N=23; daily latest net-edge N=24 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `raw/audits/daily_live_latest.json` |
| Win rate | Gate progression 26.47%; h1 shadow 25.3%; negative-edge 4.35%; daily latest 4.2% | same audit DB sources |
| Wilson lo (95%) | Gate progression 14.60%; negative-edge 0.77%; daily latest 0.7%; h1 shadow emits Wilson BF lower 17.95% rather than plain 95% lower | same audit DB sources |
| PF | Gate progression 0.640; h1 shadow aggregate PF not emitted, cell PF mostly <1 except GBP_USD NY/Off small-N cells; negative-edge PF=0.043; daily latest PF not emitted | audit DB / tier-master-derived audits |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `sr_channel_reversal` ALL の WF folds>=3 は既存 tier-master / audit DB から確認できない。新 variant 採用には 365d WF>=3 が必要。 | tier-master / existing audit search |
| Bonferroni-adj p | Gate progression Bonf p=1.0000; h1 shadow aggregate p_bonferroni=0.0 against negative edge; USD_JPY Asia p_bonf=0.001334 and NY-overlap p_bonf=0.031925 are negative cells | audit DB |
| Kelly fraction | Gate progression clipped Kelly=0.0000, raw Kelly=-0.1486; h1 shadow Kelly=-0.1621; negative-edge Kelly not emitted; pair cells mostly negative except GBP_USD NY-overlap +0.057 and Off +0.562 at small N | audit DB |
