---
strategy: bb_rsi
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

BB %B が下限/上限に寄り、RSI5 と Stoch が短期の売られすぎ/買われすぎを示したあと、現在足の足色と Stoch 反転で平均回帰を取りに行く MR 戦略。JPY では低 ADX ノイズを避け、USD/JPY の高 ADX BB 反発も edge として扱う、というペア別補助仮説を持つ。`strategies/scalp/bb_rsi.py:2`, `strategies/scalp/bb_rsi.py:37`, `strategies/scalp/bb_rsi.py:40`, `strategies/scalp/bb_rsi.py:41`, `strategies/scalp/bb_rsi.py:42`, `strategies/scalp/bb_rsi.py:43`, `strategies/scalp/bb_rsi.py:44`, `strategies/scalp/bb_rsi.py:78`, `strategies/scalp/bb_rsi.py:82`, `strategies/scalp/bb_rsi.py:85`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `bbpb <= 0.30 AND rsi5 < 45 AND stoch_k < 45 AND (K>D OR K rising) AND close>open`、SELL は `bbpb >= 0.70 AND rsi5 > 55 AND stoch_k > 55 AND (K<D OR K falling) AND close<open`。BB extension、RSI/Stoch extreme、反転確認が揃っており、MR の oversold/overbought trigger を数学的に捕捉している。`strategies/scalp/bb_rsi.py:41`, `strategies/scalp/bb_rsi.py:42`, `strategies/scalp/bb_rsi.py:43`, `strategies/scalp/bb_rsi.py:44`, `strategies/scalp/bb_rsi.py:45`, `strategies/scalp/bb_rsi.py:46`, `strategies/scalp/bb_rsi.py:104`, `strategies/scalp/bb_rsi.py:114`, `strategies/scalp/bb_rsi.py:115`, `strategies/scalp/bb_rsi.py:116`, `strategies/scalp/bb_rsi.py:117`, `strategies/scalp/bb_rsi.py:167`, `strategies/scalp/bb_rsi.py:168`, `strategies/scalp/bb_rsi.py:169`, `strategies/scalp/bb_rsi.py:170` |
| 3 (timing window) | LOOKAHEAD | `ctx.entry > ctx.open_price` / `< ctx.open_price` を現在足の反転確認として使い、`ctx.entry`, `ctx.open_price`, `ctx.bbpb`, `ctx.rsi5`, `ctx.stoch_k` をそのまま trigger に使う。strategy 内には closed-bar 判定や `(symbol, bar_time, signal)` dedup がなく、実行層が intrabar evaluate すると未確定足で同一 bar 多重 entry が起き得る。`df.iloc[-2]` は Stoch の前バー参照だけなので未来参照そのものではないが、bar dedup 欠落は spec の LOOKAHEAD 寄りリスクに該当する。`strategies/scalp/bb_rsi.py:104`, `strategies/scalp/bb_rsi.py:105`, `strategies/scalp/bb_rsi.py:114`, `strategies/scalp/bb_rsi.py:117`, `strategies/scalp/bb_rsi.py:167`, `strategies/scalp/bb_rsi.py:170`, `strategies/scalp/bb_rsi.py:253` |
| 4 (filter coherence) | BREAKS | EURGBP disable はセッション PF<0.7 の除外なので STRENGTHENS。非 JPY の `ADX < 25` は MR range filter として STRENGTHENS。JPY の `ADX < 15` block も極端ノイズ除外として概ね STRENGTHENS。一方で USD/JPY は `ADX>=30` を「トレンド中BB反発」高 WR 条件として加点するのに、直後の `apply_penalty(..., strategy_type='MR', ctx.adx)` が ADX>25 で confidence を減点する。これは同じ regime tail を entry score では強化し、routing confidence では破壊する矛盾で、HMM regime gate same-trap と同型の BREAKS。MA filter on MR の先行例も踏まえると、MR の有効 tail に trend/regime penalty を重ねる設計は危険。`strategies/scalp/bb_rsi.py:67`, `strategies/scalp/bb_rsi.py:69`, `strategies/scalp/bb_rsi.py:74`, `strategies/scalp/bb_rsi.py:78`, `strategies/scalp/bb_rsi.py:82`, `strategies/scalp/bb_rsi.py:86`, `strategies/scalp/bb_rsi.py:91`, `strategies/scalp/bb_rsi.py:118`, `strategies/scalp/bb_rsi.py:171`, `strategies/scalp/bb_rsi.py:218`, `strategies/scalp/bb_rsi.py:219`, `strategies/scalp/bb_rsi.py:226`, `strategies/scalp/bb_rsi.py:229`, `strategies/scalp/bb_rsi.py:231`, `strategies/scalp/bb_rsi.py:234` |
| 5 (stop/TP geometry) | ALIGNED | SL は band 外側までの距離 `abs(entry - bb_lower/upper) + 0.3ATR` に最小 SL をかけるため、MR が平均へ戻る前の小ノイズで切られにくい。TP は `max(ATR * tp_mult, sl_dist * rr_floor)` で Tier2 RR>=2.5、Tier1 RR>=3.0 を強制する。旧実測 RR=1.17 の算数破綻を修正する形で、現在の R:R geometry は MR の低 WR / fat-tail 復帰取りと整合する。`strategies/scalp/bb_rsi.py:47`, `strategies/scalp/bb_rsi.py:48`, `strategies/scalp/bb_rsi.py:50`, `strategies/scalp/bb_rsi.py:58`, `strategies/scalp/bb_rsi.py:59`, `strategies/scalp/bb_rsi.py:156`, `strategies/scalp/bb_rsi.py:157`, `strategies/scalp/bb_rsi.py:160`, `strategies/scalp/bb_rsi.py:161`, `strategies/scalp/bb_rsi.py:202`, `strategies/scalp/bb_rsi.py:203`, `strategies/scalp/bb_rsi.py:206`, `strategies/scalp/bb_rsi.py:207` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。実装は JPY / non-JPY の粗い分岐で、コメントは主に EUR/USD と USD/JPY を根拠にしている。tier-master では EUR_JPY / EUR_USD / GBP_USD / USD_JPY がすべて pair_demoted で、`ALL` としては forced broad scope。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は `—`。既存 audit DB 系には USD_JPY 小 N の positive cells と shadow all の negative by-strategy が混在するが、ALL cell の Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が同一 source で揃わない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT / unstable | Code comments and score bonus explicitly treat USD/JPY ADX>=30 BB反発 as high WR, but tier-master pair_demoted and production audit showed USDJPY live scalp N=6, WR=16.7%, Wilson lo=3.0%, Kelly=-0.564. |
| EURUSD | FORCED | Non-JPY branch applies `ADX < 25` as EUR/USD range filter, but 180d scalp BT reference was N=245, WR=51.4%, EV=-0.292 on 1m and N=45, WR=53.3%, EV=-0.111 on 5m. |
| GBPUSD | FORCED | Non-JPY branch inherits the EUR/USD ADX design without pair-specific rationale. 180d scalp BT reference was N=327, WR=37.3%, EV=-0.837 on 1m and N=131, WR=39.7%, EV=-0.567 on 5m. |
| EURJPY | FORCED | JPY branch inherits the USD/JPY high-ADX hypothesis, but tier-master pair_demoted and 180d JPY postfix reference was N=397, WR=43.8%, EV=-0.314 on 1m and N=134, WR=49.3%, EV=-0.153 on 5m. |
| EURGBP | FORCED / BLOCKED | Strategy file disables EURGBP entirely because Tokyo PF=0.29 and NY Overlap PF=0.53, so `ALL` scope is not actually tradable for all pairs. |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、SCALP_SENTINEL かつ EUR_JPY / EUR_USD / GBP_USD / USD_JPY が pair_demoted で、既存 audit も negative/insufficient が混在するため failure mode 診断対象とする。

破綻軸は Axis 3 と Axis 4。Axis 2 の trigger は BB/RSI/Stoch の MR と整合しており、Axis 5 も RR floor 後は算数破綻をかなり修正している。主問題は、現在足の `entry/open` 反転確認を closed-bar/dedup なしで使う timing と、USD/JPY の `ADX>=30` を edge tail として加点しながら MR anti-trend confidence penalty で同じ tail を減点する filter/scoring 矛盾である。

再設計案は 2 段。まず signal を closed bar 化し、同一 `(symbol, signal, bar_time)` の再 emit を禁止する。次に JPY high-ADX tail を採用する variant と、純 range MR variant を分離する。具体的には JPY variant では `ADX>=30` bonus と `apply_penalty(... MR, ADX)` の同時適用をやめ、USD/JPY trend-BB-reversion を別 `strategy_type` または penalty bypass で扱う。non-JPY は `ADX < 25` range MR として維持し、GBPUSD/EURJPY は `ALL` から外して pair-specific evidence が出るまで forced scope にしない。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は捨てない。BB/RSI/Stoch extreme からの反転を狙う MR thesis はコードから明確に導出でき、trigger 自体も概ね妥当。ただし現行設計は timing と regime/scoring が混線しているため、単一行削除ではなく複数軸の再設計が必要。

最小の修正方針は、まず `evaluate()` を確定足 signal に寄せ、`ctx.df.iloc[-2]` で BB%B / RSI / Stoch / foot color を判定し、次 bar の `ctx.entry` で約定する variant を作ること。同時に strategy または dispatch 層で `(ctx.symbol, signal, bar_time)` dedup を必須化する。

次に filter を分岐する。range MR 版は non-JPY の `ADX < 25` を維持し、JPY trend-BB-reversion 版は `ADX>=30` bonus を使う代わりに MR anti-trend penalty を適用しない。`feedback_hmm_gate_same_trap.md` と同じく、edge が出ている regime tail を generic gate で消さないことを優先する。採用前には本 audit では実行しない 365d + WF folds>=3 の再集計で、Wilson lower / PF / Bonferroni p / Kelly を同一 source から出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow ALL: `—`; audit DB shadow by-strategy: N=12; audit DB USDJPY Tokyo/London qualified cells: N=10 / N=11; production USDJPY live scalp/scalp_5m: N=6 / N=2 | `knowledge-base/wiki/tier-master.md`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `raw/audits/cell_edge_audit_2026-04-27_v2_all_inclshadow.json`; `raw/audits/phase_a_production_audit_2026-04-27.json` |
| Win rate | audit DB shadow by-strategy: 16.7%; USDJPY Tokyo/London: 70.0% / 54.5%; production USDJPY scalp/scalp_5m: 16.7% / 0.0% | same as above |
| Wilson lo (95%) | audit DB shadow by-strategy: 4.7%; USDJPY Tokyo/London: 39.68% / 28.01%; production USDJPY scalp/scalp_5m: 3.01% / 0.00% | same as above |
| PF | audit DB shadow by-strategy: 0.252; USDJPY Tokyo/London: 3.324 / 2.103; USDJPY RANGE pre-fix diagnostic PF=0.75 | `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `raw/audits/cell_edge_audit_2026-04-27_v2_all_inclshadow.json`; `knowledge-base/wiki/analyses/bb-rsi-fix-rr-2.5-2026-04-25.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE for `bb_rsi` / ALL in tier-master + audit DB. Existing references are BT breakdowns, not promotion-grade WF folds for this cell. | `knowledge-base/wiki/tier-master.md`; `knowledge-base/raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md` |
| Bonferroni-adj p | USDJPY Tokyo/London audit cells: 1.0000 / 1.0000; ALL cell Bonferroni p not available | `raw/audits/cell_edge_audit_2026-04-27_v2_all_inclshadow.json` |
| Kelly fraction | production USDJPY scalp: -0.5644; production USDJPY scalp_5m: 0.0000; ALL shadow Kelly not available in audit DB, so decision-grade Kelly is INSUFFICIENT_EVIDENCE | `raw/audits/phase_a_production_audit_2026-04-27.json` |
