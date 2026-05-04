---
strategy: dt_sr_channel
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

15m daytrade の水平 SR / parallel channel 端で、価格が support/lower channel 近傍なら BUY、resistance/upper channel 近傍なら SELL し、RSI の偏りと MACD histogram の反転で短期 mean reversion を確認する戦略。実装 entry_type は `dt_sr_channel_reversal`。`strategies/daytrade/dt_sr_channel.py:1`, `strategies/daytrade/dt_sr_channel.py:8`, `strategies/daytrade/dt_sr_channel.py:28`, `strategies/daytrade/dt_sr_channel.py:37`, `strategies/daytrade/dt_sr_channel.py:38`, `strategies/daytrade/dt_sr_channel.py:39`, `strategies/daytrade/dt_sr_channel.py:40`, `strategies/daytrade/dt_sr_channel.py:41`, `strategies/daytrade/dt_sr_channel.py:44`, `strategies/daytrade/dt_sr_channel.py:46`, `strategies/daytrade/dt_sr_channel.py:61`, `strategies/daytrade/dt_sr_channel.py:63`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `(_sr_buy OR _at_ch_lower) AND rsi < 45 AND macdh > macdh_prev`、SELL は `(_sr_sell OR _at_ch_upper) AND rsi > 55 AND macdh < macdh_prev`。SR/channel 端への extension と oscillator/momentum 反転を条件にしており、思想の数学的捕捉は成立する。ただし RSI 45/55 は浅く、oversold/overbought trigger としては緩い。`strategies/daytrade/dt_sr_channel.py:13`, `strategies/daytrade/dt_sr_channel.py:38`, `strategies/daytrade/dt_sr_channel.py:39`, `strategies/daytrade/dt_sr_channel.py:40`, `strategies/daytrade/dt_sr_channel.py:41`, `strategies/daytrade/dt_sr_channel.py:44`, `strategies/daytrade/dt_sr_channel.py:45`, `strategies/daytrade/dt_sr_channel.py:46`, `strategies/daytrade/dt_sr_channel.py:61`, `strategies/daytrade/dt_sr_channel.py:62`, `strategies/daytrade/dt_sr_channel.py:63` |
| 3 (timing window) | LOOKAHEAD | Channel は `ctx.df` 全体から `lookback=min(100, len(ctx.df) - 1)` で検出し、最後の channel value と現在 `ctx.entry` の距離で判定する。戦略内には closed-bar 固定、signal bar timestamp、同一 bar dedup がなく、実行層が intrabar evaluate する場合は未確定足の entry/channel/SR 状態で同一 bar 再発火し得る。`strategies/daytrade/dt_sr_channel.py:15`, `strategies/daytrade/dt_sr_channel.py:16`, `strategies/daytrade/dt_sr_channel.py:31`, `strategies/daytrade/dt_sr_channel.py:34`, `strategies/daytrade/dt_sr_channel.py:35`, `strategies/daytrade/dt_sr_channel.py:38`, `strategies/daytrade/dt_sr_channel.py:39`, `strategies/daytrade/dt_sr_channel.py:40`, `strategies/daytrade/dt_sr_channel.py:41`, `strategies/daytrade/dt_sr_channel.py:81` |
| 4 (filter coherence) | STRENGTHENS | `ctx.sr_levels` / `ctx.df` / `len(ctx.df)` guard は NEUTRAL。HTF hard block は BUY を HTF bear で止め、SELL を HTF bull で止めるため、SR/channel MR が強トレンドへ逆張りする tail を抑える filter として STRENGTHENS。MA filter on MR や HMM same-trap と異なり、ここでは EMA は hard gate ではなく score bonus なので thesis を直接破壊しない。`strategies/daytrade/dt_sr_channel.py:16`, `strategies/daytrade/dt_sr_channel.py:19`, `strategies/daytrade/dt_sr_channel.py:20`, `strategies/daytrade/dt_sr_channel.py:21`, `strategies/daytrade/dt_sr_channel.py:22`, `strategies/daytrade/dt_sr_channel.py:44`, `strategies/daytrade/dt_sr_channel.py:54`, `strategies/daytrade/dt_sr_channel.py:61`, `strategies/daytrade/dt_sr_channel.py:71` |
| 5 (stop/TP geometry) | MISALIGNED | BUY は `tp = entry + atr7 * 2.0`, `sl = entry - atr7 * 1.0`、SELL は対称で、実質 R:R は 2.0:1.0。これは trend continuation 型の非対称 payoff に近く、MR に必要な「平均回帰前に小さく切られない wide stop / mean target」ではない。`strategies/daytrade/dt_sr_channel.py:57`, `strategies/daytrade/dt_sr_channel.py:58`, `strategies/daytrade/dt_sr_channel.py:74`, `strategies/daytrade/dt_sr_channel.py:75`, `strategies/daytrade/dt_sr_channel.py:81` |
| 6 (pair-regime fit) | FORCED | `ALL` scope は forced。既存 h1-hour-bucket audit では USD_JPY は shadow N=17, WR=47.1%, EV=+1.70 と相対的に fit、EUR_JPY は N=20, EV=+1.02 だが WR=30.0% で mixed、EUR_USD / GBP_USD / GBP_JPY は negative または小 N。下表参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | Gate progression audit では N=12, WR=50.00%, Wilson lo=25.38%, EV=-0.74, PF=0.854, Kelly=0.0000, raw Kelly=-0.0856, Bonf p=1.0000。Negative-edge audit では by-strategy N=13, WR=23.1%, Wilson lo=8.2%, PF=0.30。WF は USD_JPY cell の 1/7 positive folds など cell-level 断片のみで、ALL / phase0_shadow の promotion-grade WF>=3 は揃わない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT / unstable | h1-hour-bucket shadow aggregate N=17, WR=47.1%, EV=+1.70。London/NY-overlap は PF>2 だが、WF reference は USD_JPY × dt_sr_channel_reversal が 1/7 positive folds, EV=-0.368 と不安定。 |
| EUR_JPY | FORCED / mixed | h1-hour-bucket shadow aggregate N=20, WR=30.0%, EV=+1.02。NY-overlap は EV positive だが Asia/London が弱く、pair 全体では確証不足。 |
| EUR_USD | FORCED | h1-hour-bucket shadow aggregate N=11, WR=27.3%, EV=-1.42, PF は London 0.669 / NY-overlap 0.0。 |
| GBP_USD | FORCED | h1-hour-bucket shadow aggregate N=15, WR=26.7%, EV=-2.95。London PF=0.071、NY-overlap PF=0.0 が明確に悪い。 |
| GBP_JPY | FORCED / insufficient | h1-hour-bucket shadow aggregate N=3, WR=66.7%, EV=-1.00。小 N かつ London の単発負けが大きく、fit 判定不能。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが phase0_shadow / ALL で tier-master 365d BT EV は `—`、May 3 gate progression は PF=0.854 / raw Kelly=-0.0856、Apr 28 negative-edge audit では by-strategy PF=0.30 なので underperforming として failure mode 診断を適用する。

破綻軸は Axis 3 と Axis 5、補助的に Axis 6。Trigger は SR/channel 端 + RSI/MACD 反転で MR thesis と整合するが、closed-bar 化と per-bar dedup が戦略内にないため signal timing が実行層依存になっている。さらに stop/TP が 1ATR stop / 2ATR target の trend-follow 型 geometry で、SR/channel MR の「境界外まで耐えて mean 側へ戻る」構造と噛み合っていない。ALL scope も USD_JPY 以外の negative pockets を混ぜている。

再設計案は、まず closed-bar signal に固定し、`signal_bar = ctx.df.iloc[-2]` 相当の確定足で SR/channel proximity、RSI、MACDH turn を判定して次足 `ctx.entry` で候補化すること。併せて `(instrument, entry_type, signal_bar_time, direction)` の dedup を dispatch か strategy state に置く。次に geometry を MR 型へ寄せ、SL は support/resistance/channel 境界の外側に `1.3-1.8 * ATR7` 程度の余裕を置き、TP は channel midline / nearest mean / `0.8-1.2 * ATR7` のいずれかを candidate variant として比較する。pair scope は最初に USD_JPY と EUR_JPY NY-overlap のみに絞り、GBP_USD/EUR_USD は redesign BT で復帰条件を満たすまで除外する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は有効候補として残す。SR/channel 端での反発を RSI/MACD 反転で拾う thesis はコードから明確に導出でき、trigger 自体も大枠では MR と整合している。一方で、現在の実装は signal timing と stop/TP geometry が MR 用に固定されておらず、ALL scope で負の pair/session を混ぜている。

最小 redesign は 2 系統。第一に trigger 評価を確定足へ移し、同一 bar 再発火を防ぐ。第二に `tp/sl = 2ATR/1ATR` をやめ、SR/channel 境界外 wide stop + mean-side target に変える。コード差分イメージとしては、line 31-46 / 61-63 の判定入力を `ctx.df.iloc[-2]` 系へ寄せ、line 57-58 / 74-75 を boundary-aware SL と midline/ATR mean target に置換する。

採用前に必要な BT は、新 variant について USD_JPY / EUR_JPY / GBP_USD / EUR_USD 別、hour bucket 別、365d + WF folds>=3 で Wilson lo / PF / Bonferroni p / Kelly を同一集計から再発行すること。本監査では BT を実行しない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | gate progression by-strategy N=12; negative-edge by-strategy N=13; h1-hour-bucket shadow aggregate N=66 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| Win rate | gate progression 50.00%; negative-edge 23.1%; h1-hour-bucket shadow aggregate 34.8% | same audit DB sources |
| Wilson lo (95%) | gate progression 25.38%; negative-edge 8.18%; h1-hour-bucket per-cell range 0.00%-34.24%, no ALL Wilson emitted | same audit DB sources |
| PF | gate progression 0.854; negative-edge 0.305; h1-hour-bucket pair/session cells range 0.0-inf with USD_JPY London 2.219 and GBP_USD London 0.071 | audit DB / tier-derived audit: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE for ALL / phase0_shadow. USD_JPY cell reference has 1/7 positive folds, EV=-0.368, CV=0.80, but this is not an ALL-cell WF pass. | `knowledge-base/wiki/sessions/handover-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-2026-04-22.md` |
| Bonferroni-adj p | gate progression Bonf p=1.0000; h1-hour-bucket cells all Bonf p=1.0000. No significant adjusted evidence. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| Kelly fraction | gate progression Kelly=0.0000, raw Kelly=-0.0856; h1-hour-bucket USD_JPY London Kelly=+0.3296 but GBP_USD London Kelly=-1.8639 and EUR_USD London Kelly=-0.1649. ALL decision-grade Kelly is non-positive/insufficient. | same audit DB sources |
