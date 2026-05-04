---
strategy: mtf_regime_range_cascade_scalp
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

M15 がレンジのときだけ、M5 の BB band touch と swing 近接でレンジ端の exhaustion を確認し、1m の BB%B / RSI5 / Stoch / 足色反転で平均回帰を取る MTF range MR cascade。コード上は `strategy_type = "MR"` で、BUY は range bottom、SELL は range top に限定される。`strategies/scalp/mtf_regime_range_cascade_scalp.py:4`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:55`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:76`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:81`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:89`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:110`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:139`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `m5_bbpb<=0.08 AND |m5_low-m5_swing_low|<=0.3*m5_atr AND ctx.bbpb<=0.30 AND rsi5<45 AND stoch_k<45 AND (K>D OR K rising) AND close>open`。SELL は対称に `m5_bbpb>=0.92 AND swing_high近接 AND ctx.bbpb>=0.70 AND rsi5>55 AND stoch_k>55 AND (K<D OR K falling) AND close<open`。BB extension、swing 近接、短期 oscillator extreme、反転足を使っており、数式上は range-edge MR を捕捉している。`strategies/scalp/mtf_regime_range_cascade_scalp.py:57`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:58`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:59`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:60`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:61`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:62`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:63`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:113`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:119`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:140`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:146` |
| 3 (timing window) | LOOKAHEAD | Trigger は `ctx.entry`, `ctx.open_price`, `ctx.bbpb`, `ctx.rsi5`, `ctx.stoch_k/d` と M5 snapshot を現在評価時点の値として直接使う。strategy 内に closed-bar 固定や `(symbol, signal, bar_time)` dedup はなく、実行層が intrabar evaluate すると未確定足の足色反転で signal が点灯し、同一 bar 多重 entry も起き得る。`df.iloc[-2]` は Stoch の前バー比較だけで、signal 全体の closed-bar 化にはなっていない。`strategies/scalp/mtf_regime_range_cascade_scalp.py:90`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:101`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:113`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:119`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:140`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:146`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:183` |
| 4 (filter coherence) | BREAKS | Spread/friction gate は scalp execution risk を落とすので STRENGTHENS。Pair gate は USD_JPY / EUR_USD のみに絞るため ALL scope には FORCED だが、摩擦面では NEUTRAL。破壊的なのは M15 `classify_15m(m15) == REGIME_RANGE` hard gate で、コード自身が v2 廃止理由として `range_tight regime での MR` を実測で構造的に負けと記録している。これは HMM regime gate same trap と同型で、generic regime gate が edge tail を選ぶのではなく、既に負けが観測された tail に entry を固定している。MR に MA filter を追加する先行例とは別型だが、generic hard filter が MR trigger の有効領域を壊す点は同じ。`strategies/scalp/mtf_regime_range_cascade_scalp.py:4`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:10`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:33`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:68`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:72`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:81`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:178` |
| 5 (stop/TP geometry) | ALIGNED | SL は band 外側までの距離に `0.3ATR` を足し、最小 SL も確保する。さらに `SL > 12 pips` は exhaustion 失敗として reject する。TP は `max(2.0ATR, SL*RR_floor)` で、Tier1 は RR>=3.0、通常は RR>=2.5。レンジ端 MR として、平均回帰前の小ノイズで切られにくい wide stop と正の R:R floor は概ね整合する。ただし tight range では TP が平均回帰先を超え得るため、Axis 8 では target geometry の再検証を要求する。`strategies/scalp/mtf_regime_range_cascade_scalp.py:34`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:35`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:36`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:121`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:129`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:148`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:156` |
| 6 (pair-regime fit) | FORCED | 下の pair-regime table 参照。Prompt scope は ALL だが、実装は USD_JPY / EUR_USD のみを許可する。かつ戦略の中心 regime である range_tight MR は既存ラベル実測で negative 方向。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative partial evidence | tier-master 由来の 365d BT EV は入力どおり `—`。local `demo_trades.db` には exact `mtf_regime_range_cascade_scalp` / `%mtf_regime_range%` / `%range_cascade%` の `demo_trades`, `evaluated_candidates`, `oanda_audit` 行が 0 件。補助資料には range_tight × 近縁 MR の小標本 negative があるが、PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction が target strategy の同一 decision source で揃わないため、`feedback_partial_quant_trap.md` 基準では decision-grade evidence 不足。 |

### Pair-Regime Table

| Pair / scope | Fit | Evidence |
|--------------|-----|----------|
| USD_JPY | FORCED | Code allows USD_JPY, but the thesis depends on `REGIME_RANGE` hard gate and inherited BB/RSI MR trigger. Existing retirement notes cite `bb_rsi_reversion × range_tight` as N=8, WR=12.5%, Wilson_lo=2.24%, EV=-3.74, so current range-MR cell is not fit for promotion-grade use. `strategies/scalp/mtf_regime_range_cascade_scalp.py:33`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:81`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:113` |
| EUR_USD | FORCED | Code allows EUR_USD but provides no pair-specific EURUSD range microstructure condition beyond the same generic range gate and same 1m bb_rsi trigger. Exact target strategy evidence is absent. `strategies/scalp/mtf_regime_range_cascade_scalp.py:33`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:68`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:140` |
| Other ALL pairs | FORCED / BLOCKED | Prompt scope is ALL, but `_ALLOWED_PAIRS` rejects every pair except USD_JPY and EUR_USD, so ALL is not actually tradable by this strategy. `strategies/scalp/mtf_regime_range_cascade_scalp.py:33`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:67`, `strategies/scalp/mtf_regime_range_cascade_scalp.py:69` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 と Axis 4、補助的に Axis 2 の trigger 選択。Axis 2 は数式上は MR と整合するが、実際には `bb_rsi_reversion` 継承 trigger を range_tight に重ねた設計が既存ラベル実測で否定方向になっている。Axis 3 は現在足依存かつ dedup 欠落で、scalp の intrabar 再発火リスクが残る。Axis 4 は `REGIME_RANGE` hard gate が、コードコメント上すでに負けと記録された range_tight MR tail へ entry を固定している点が主破綻。

再設計案は、range hard gate をそのまま残して 1m bb_rsi trigger だけを薄く調整するのではなく、range edge を「レンジ端の reclaim」に再定義すること。具体的には BUY を `closed signal bar low <= m5_swing_low or bb_lower breach` かつ `closed back inside band` かつ `RSI5 recross 30 or Stoch K cross D`、SELL を対称条件にする。signal は `df.iloc[-2]` の確定足で判定し、entry は次 bar に分離し、`(symbol, strategy, signal, signal_bar_time)` dedup を必須にする。

Filter は `classify_15m == REGIME_RANGE` の単一 hard gateを廃止または分解し、少なくとも range_tight / range_wide / moderate_trend を別 cohort として記録する。range_tight は既存 evidence が negative なので default block、range_wide または moderate_trend でのみ reclaim trigger を試す。Stop/TP は現行 RR floor を初期案として維持してよいが、tight range では `TP = min(mid-band/reversion target, SL*rr_floor)` の variant を別に作り、mean を超えた TP 要求で勝率を落としていないか検証する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は完全棄却ではなく、レンジ端の exhaustion から平均回帰を取る仮説としては再設計候補に残す。ただし現在の設計は、既に負けが観測された range_tight × inherited bb_rsi trigger へ hard gate で固定しており、未確定足依存も残る。単一行削除では足りず、trigger と timing と regime filter をまとめて直す必要がある。

最小の再設計 diff は、`classify_15m(m15) != REGIME_RANGE` の即 reject を外し、range_tight / range_wide / moderate_trend を別 cohort として `reasons` と audit key に残すこと。その上で 1m trigger を `ctx` 現在値ではなく確定足の sweep-and-reclaim 条件に置き換える。BUY は「前確定足が M5 swing_low / BB lower を一度割り、同足 close が band 内へ戻り、RSI/Stoch が反転」、SELL はその逆にする。

採用前には本 audit では実行しない再検証が必要。必要 artifact は USD_JPY と EUR_USD を分離し、365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 audit DB / tier-master source で出すこと。N/WR/EV だけ、または range_tight 近縁 MR の小標本だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | exact target strategy: 0 rows in local `demo_trades`, `evaluated_candidates`, `oanda_audit`; tier-master 365d BT EV: `—`; retirement note range_tight proxy: `bb_rsi_reversion` N=8, `engulfing_bb` N=5, `sr_channel_reversal` N=10, aggregate `range_tight` N=121 | `demo_trades.db`; `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/strategies/mtf-regime-range-cascade-scalp.md`; `knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md` |
| Win rate | exact target strategy: INSUFFICIENT_EVIDENCE; range_tight proxy: `bb_rsi_reversion` 12.5%, `engulfing_bb` 20.0%, `sr_channel_reversal` 0.0%, aggregate `range_tight` 25.6% | same as above |
| Wilson lo (95%) | exact target strategy: INSUFFICIENT_EVIDENCE; range_tight proxy from strategy wiki: `bb_rsi_reversion` 2.24%, `engulfing_bb` 3.62%, `sr_channel_reversal` 0.00%; decision note says all cells Wilson_lo < 40% | `knowledge-base/wiki/strategies/mtf-regime-range-cascade-scalp.md`; `knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md` |
| PF | INSUFFICIENT_EVIDENCE: target strategy PF is not present in tier-master or local audit DB; retirement note says PF/Wilson were considered, but target-strategy PF is not persisted in the available artifact | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md`; `demo_trades.db` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no target-strategy WF folds>=3 found in tier-master / local audit DB | `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: retirement note states N=8-30 is insufficient for Bonferroni significance, but target-strategy adjusted p is not persisted | `knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: target-strategy payoff distribution / PF is absent, so Kelly fraction cannot be computed from existing tier-master / audit DB without new BT | `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
