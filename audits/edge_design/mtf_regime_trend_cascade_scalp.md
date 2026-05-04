---
strategy: mtf_regime_trend_cascade_scalp
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

M15 の moderate trend かつ H1 macro 方向と整合する局面だけを選び、M5 SMA21 pullback 後の 1m price-action bounce で trend continuation scalp を取る MTF cascade。BUY/SELL 方向は M15/H1 slope gate で決め、1m oscillator ではなく足色と EMA21 反発で entry を確定する。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:22`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:25`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:70`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:88`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:95`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:132`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:139`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:141`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-continuation thesis に対して、entry は `classify_15m(m15)==REGIME_MODERATE_TREND AND slope_direction_macro_gated(m15,h1)!=0` を前提に、BUY は `m5_prev_low <= m5_sma21 + 0.3*m5_atr AND m5_close > m5_prev_close AND ctx.entry - ctx.ema21 >= 0.2*ctx.atr7 AND ctx.entry > ctx.prev_close AND ctx.entry > ctx.open_price`。SELL は対称に `m5_prev_high >= m5_sma21 - 0.3*m5_atr AND m5_close < m5_prev_close AND ctx.ema21 - ctx.entry >= 0.2*ctx.atr7 AND ctx.entry < ctx.prev_close AND ctx.entry < ctx.open_price`。trend regime、direction gate、pullback、bounce、足色の順で捕捉しており、trigger は thesis と整合する。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:88`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:95`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:132`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:139`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:141`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:160`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:164`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:166` |
| 3 (timing window) | LOOKAHEAD | Signal は `ctx.entry`, `ctx.open_price`, `ctx.prev_close`, `ctx.ema21`, `ctx.atr7` と M5 snapshot を現在評価値として直接使う。strategy 内には closed-bar 固定、signal bar timestamp、または `(symbol, strategy, signal, bar_time)` dedup がなく、実行層が intrabar evaluate する場合は未確定 1m 足の陽線/陰線判定で点灯し、同一 bar 多重 entry も起き得る。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:99`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:120`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:138`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:139`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:141`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:163`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:164`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:166` |
| 4 (filter coherence) | STRENGTHENS | Spread/friction hard gate は scalp の execution cost を抑えるので STRENGTHENS。`REGIME_MODERATE_TREND` gate と H1 macro-gated slope は trend continuation thesis を強化する。M5 SMA21 pullback gate も trend 中の押し目/戻りに entry を限定するため STRENGTHENS。Pair gate は USD_JPY / EUR_USD のみに限定するので ALL scope には FORCED だが、thesis 自体は壊していない。MA filter on MR や HMM regime gate same trap の先行例と異なり、ここでは trend thesis に trend/regime filter を重ねているため、filter-coherence 単体では BREAKS ではない。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:51`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:75`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:79`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:88`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:95`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:132`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:160` |
| 5 (stop/TP geometry) | MISALIGNED | BUY SL は `ctx.ema21 - 0.3*ATR7` 起点で、entry が EMA21 から `0.2*ATR7` 以上反発した後なので、実質 stop はおおむね `0.5*ATR7` または 5pip floor。TP は `max(m5_swing_high, entry + 1.3R)`、SELL は対称に `min(m5_swing_low, entry - 1.3R)`。Trend continuation scalp としては固定 swing / 1.3R floor が浅く、trailing や trend extension capture がなく、勝ち平均を伸ばす asymmetry が弱い。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:52`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:53`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:54`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:138`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:144`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:145`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:149`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:150`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:151`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:169`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:170`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:174`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:175`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:176` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。Prompt scope は ALL だが、実装は USD_JPY / EUR_USD のみ許可する。USD_JPY には 180d negative evidence がある一方、EUR_USD の同等 evidence は見つからない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative partial evidence | tier-master の scalp_sentinel 行は 365d BT EV が `—`。local `demo_trades.db` の `demo_trades`, `evaluated_candidates`, `oanda_audit` には exact `mtf_regime_trend_cascade_scalp` 行が 0 件。既存 180d vec harness USD_JPY では N=34, WR=41.176%, Wilson lo=26.366%, PF=0.741, Bonferroni p=0.25743375, Kelly=0 で Reject。ただし ALL scope / 365d / WF folds>=3 が揃わないため、`feedback_partial_quant_trap.md` 基準では promotion-grade evidence は不足。 |

### Pair-Regime Table

| Pair / scope | Fit | Evidence |
|--------------|-----|----------|
| USD_JPY | FORCED | Code allows USD_JPY, and USDJPY 180d vec harness has N=34, PF=0.741, Wilson lo=26.37%, Kelly=0, OOS PF=0.571. Fit は否定方向で、少なくとも現行 geometry/timing のままでは forced exposure。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:51`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:75`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:88`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:95` |
| EUR_USD | FORCED | Code allows EUR_USD, but EURUSD 固有の moderate-trend pullback evidence は tier-master / local audit DB に見つからない。pair-specific volatility, spread, session 条件も strategy 内にはない。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:51`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:75`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:79`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:132` |
| Other ALL pairs | FORCED | Prompt scope は ALL だが、`_ALLOWED_PAIRS` で USD_JPY / EUR_USD 以外は即 reject されるため、ALL は実装上 tradable universe ではない。`strategies/scalp/mtf_regime_trend_cascade_scalp.py:51`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:74`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:75`, `strategies/scalp/mtf_regime_trend_cascade_scalp.py:76` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。主破綻軸は Axis 3 と Axis 5。Axis 2 は trend/pullback/bounce を数学的に捕捉しており PASS、Axis 4 も thesis と filter の方向性は概ね整合する。ただし現在足依存の 1m bounce 判定と bar dedup 欠落により、未確定足の一時的な EMA21 反発を signal 化するリスクがある。さらに stop/TP は trend continuation に対して固定 swing / RR 1.3 floor で、勝ちを伸ばす設計が弱い。

再設計案は、trigger の思想を維持したまま timing と exit geometry を変えること。BUY/SELL trigger は `df.iloc[-2]` の確定 1m 足で判定し、entry は次 bar open または確定足 close 後の execution に分離する。`signal_bar_time` を Candidate reason または実行層 key に渡し、`(symbol, strategy, signal, signal_bar_time)` dedup を必須にする。

Stop/TP は `SL = pullback swing +/- buffer` または `EMA21 +/- max(0.5ATR, spread-adjusted floor)` に整理し、TP は固定 swing 到達だけで終わらせず、半分を `1.0R-1.3R`、残りを M5 EMA/SMA trailing または `2.0R` まで伸ばす variant を検証する。現行 180d evidence は PF=0.741/OOS PF=0.571 なので、単なる threshold 微調整ではなく exit asymmetry を設計軸として再検証すべき。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想は有効候補として残す。M15 moderate trend、H1 macro direction、M5 pullback、1m bounce という cascade はコードから一貫しており、trigger mismatch や MR に MA filter を被せる型の破壊ではない。一方で、現在足依存の bounce 判定と dedup 欠落、trend continuation に対して浅い固定 RR geometry が、Tier 4 に落ちた現行設計の具体的な破綻候補。

最小 redesign は timing と stop/TP の 2 点。1m trigger を確定足化し、BUY は「前確定足で EMA21 から 0.2ATR 以上反発し、close > prev_close かつ close > open」、SELL は対称条件にする。Execution は次 bar にずらし、同一 signal_bar の再 entry を禁止する。Exit は全量 fixed TP ではなく、`partial TP at 1.0R-1.3R + remainder trailing by M5 swing/EMA21` の momentum geometry に変える。

採用前には本 audit では実行しない再検証が必要。必要 artifact は USD_JPY / EUR_USD を分離した 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction。現存 180d USDJPY vec harness は negative evidence として有用だが、ALL scope の promotion-grade 判断には不足する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | local audit DB exact rows: 0 in `demo_trades`, `evaluated_candidates`, `oanda_audit`; existing USD_JPY 180d vec harness: 34 | `demo_trades.db`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` |
| Win rate | USD_JPY 180d vec harness: 41.176% (14W / 20L) | `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` |
| Wilson lo (95%) | USD_JPY 180d vec harness: 26.366% | `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` |
| PF | tier-master 365d BT EV: `—`; USD_JPY 180d vec harness PF: 0.741 | `knowledge-base/wiki/tier-master.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: existing artifact has only 50/50 IS/OOS split, IS PF=1.083 and OOS PF=0.571; no folds>=3 found in tier-master / local audit DB | `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json`; `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
| Bonferroni-adj p | USD_JPY 180d vec harness: p=0.25743375 with K=5, alpha/K=0.01; not significant | `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` |
| Kelly fraction | USD_JPY 180d vec harness: 0.0 / Kelly half 0.000000 | `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.md`; `knowledge-base/raw/bt-results/scalp-mtf-cascade-180d-2026-05-03.json` |
