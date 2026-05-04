---
strategy: squeeze
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

BB 幅が低パーセンタイルの squeeze 状態から拡大し始めた直後に、BB 内の方向位置と EMA 順列で上抜け/下抜け momentum breakout を取る思想。コード上の thesis は MR ではなく「圧縮→拡大ブレイクアウト」で、クラス名・コメント・BB 幅 gate・拡大判定・BUY/SELL 方向条件から導出可能。`strategies/scalp/squeeze.py:1`, `strategies/scalp/squeeze.py:7`, `strategies/scalp/squeeze.py:12`, `strategies/scalp/squeeze.py:19`, `strategies/scalp/squeeze.py:30`, `strategies/scalp/squeeze.py:32`, `strategies/scalp/squeeze.py:45`, `strategies/scalp/squeeze.py:53`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Thesis は breakout だが、実際の trigger は squeeze `bb_width_pct < 0.10` と `ctx.bb_width > prev_bb_width` に加え、BUY が `bbpb > 0.75 AND entry > ema9 AND ema9 > ema21`、SELL が `bbpb < 0.25 AND entry < ema9 AND ema9 < ema21`。これは BB 内の上位/下位 quartile + EMA trend alignment であり、`Close > upper_band` / `Close < lower_band`、直近 range high/low break、前足からの band cross のいずれも要求しない。数式上は `bbpb > 0.75` であって `bbpb > 1.0` ではないため、「ブレイクアウト上抜け/下抜け」という reason と数学条件が一致していない。`strategies/scalp/squeeze.py:19`, `strategies/scalp/squeeze.py:31`, `strategies/scalp/squeeze.py:32`, `strategies/scalp/squeeze.py:34`, `strategies/scalp/squeeze.py:45`, `strategies/scalp/squeeze.py:48`, `strategies/scalp/squeeze.py:53`, `strategies/scalp/squeeze.py:56` |
| 3 (timing window) | LOOKAHEAD | 現在 ctx の `bb_width`, `bbpb`, `entry`, `ema9`, `ema21`, `adx` と `ctx.df.iloc[-1]` の Volume をそのまま使う。strategy 内に closed-bar flag、`ctx.bar_time` の確定足検査、同一 bar の per-bar dedup がないため、live 経路が未確定 5m 足で `evaluate()` を呼ぶと intrabar の暫定 BB 幅拡大・BBPB・EMA・出来高で発火し、同一 bar 多重 entry も strategy 単体では防げない。`strategies/scalp/squeeze.py:19`, `strategies/scalp/squeeze.py:21`, `strategies/scalp/squeeze.py:31`, `strategies/scalp/squeeze.py:32`, `strategies/scalp/squeeze.py:40`, `strategies/scalp/squeeze.py:45`, `strategies/scalp/squeeze.py:53`, `strategies/scalp/squeeze.py:73` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | `bb_width_pct < 0.10` は squeeze 前提を作るため STRENGTHENS。`ctx.adx >= 20` は breakout momentum を確認する方向では STRENGTHENS だが、squeeze release 初動では ADX が遅行しやすく、Axis 3 の late/intrabar 問題を増幅し得る。EMA9/EMA21 順列と価格の EMA9 上下は momentum 方向確認として STRENGTHENS。Volume は hard block ではなく score bonus のため STRENGTHENS/NEUTRAL。`feedback_ma_filter_breaks_mr.md` の MA filter on MR 先行例とは異なり、本戦略は MR ではないため EMA filter は thesis 破壊ではない。`feedback_hmm_gate_same_trap.md` 型の hard regime gate もこの file には存在しない。`strategies/scalp/squeeze.py:12`, `strategies/scalp/squeeze.py:13`, `strategies/scalp/squeeze.py:14`, `strategies/scalp/squeeze.py:19`, `strategies/scalp/squeeze.py:21`, `strategies/scalp/squeeze.py:37`, `strategies/scalp/squeeze.py:42`, `strategies/scalp/squeeze.py:45`, `strategies/scalp/squeeze.py:53`, `strategies/scalp/squeeze.py:65`, `strategies/scalp/squeeze.py:68` |
| 5 (stop/TP geometry) | MISALIGNED | Initial R:R は `tp_mult=3.0` / `sl_mult=1.2` = 2.5R で asymmetric だが、breakout thesis に必要な trailing / BE / range-break invalidation は Candidate に渡されず、fixed ATR TP/SL のみ返す。圧縮後の tail を取りに行く breakout なのに、exit は `entry ± ATR*3.0` と `entry ∓ ATR*1.2` の固定幾何で、squeeze range 外側 stop や trailing continuation になっていない。`strategies/scalp/squeeze.py:15`, `strategies/scalp/squeeze.py:16`, `strategies/scalp/squeeze.py:51`, `strategies/scalp/squeeze.py:52`, `strategies/scalp/squeeze.py:59`, `strategies/scalp/squeeze.py:60`, `strategies/scalp/squeeze.py:73` |
| 6 (pair-regime fit) | FORCED | `ALL` scope だが `tier-master` は `bb_squeeze_breakout` を EUR_GBP, EUR_JPY, EUR_USD, GBP_JPY, GBP_USD, USD_JPY の PAIR_DEMOTED かつ phase0_shadow として扱う。コードには pair/session/spread 別の calibration がなく、全 pair に同じ BBPB/EMA/ADX/ATR geometry を強制するため、pair-regime fit は strategy-level では FORCED。下の pair table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow 行は 365d BT EV が `—`。audit DB current tables には `bb_squeeze_breakout` / `squeeze` の現行 row を確認できず、既存 audit artifact では shadow by-strategy N=13, WR=7.7%, Wilson [1.4%, 33.3%], EV=-3.00, PF=0.06 と、aggregate-kelly では USD_JPY N=9 PF=0.34 / EUR_USD N=5 PF=1.35 の小N混在。別の 5m pre-reg BT は USD_JPY N=24, WR=75.0%, Wilson lo=55.1%, PF=4.872, Bonferroni p=0.00023226, Kelly half=0.298 だが verdict は N<30 で `Insufficient`、WF も 50/50 split で folds>=3 ではない。`feedback_partial_quant_trap.md` 基準の Wilson/PF/WF>=3/Bonferroni/Kelly は decision-grade に揃わない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FORCED | tier-master で PAIR_DEMOTED。aggregate-kelly は N=9, WR=33.33%, Wilson lo=12.06%, PF=0.34, EV=-1.40 の小N negative。一方 2026-05-03 5m pre-reg BT は N=24 positive だが N<30 で Insufficient。 |
| EUR_USD | FORCED | tier-master で PAIR_DEMOTED。aggregate-kelly は N=5, WR=40.00%, Wilson lo=11.76%, PF=1.35, EV=+0.56 の小Nで decision-grade 不足。 |
| GBP_USD | FORCED | tier-master で PAIR_DEMOTED。既存 Axis 7 必須指標の pair-specific Wilson/PF/WF/Kelly が不足。 |
| EUR_JPY | FORCED | tier-master で PAIR_DEMOTED。既存 Axis 7 必須指標の pair-specific Wilson/PF/WF/Kelly が不足。 |
| GBP_JPY | FORCED | tier-master で PAIR_DEMOTED。既存 Axis 7 必須指標の pair-specific Wilson/PF/WF/Kelly が不足。 |
| EUR_GBP | FORCED | tier-master で PAIR_DEMOTED。既存 Axis 7 必須指標の pair-specific Wilson/PF/WF/Kelly が不足。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが `bb_squeeze_breakout` は tier-master 上で主要 6 pair が PAIR_DEMOTED 扱いで、既存 audit artifact も negative / insufficient が混在するため failure mode を診断する。破綻軸は Axis 2, 3, 5。Axis 2 は「breakout」と称しながら BB 外・range 外への break を要求せず、BB 内 quartile + EMA 順列で入るため false breakout を多く拾う。Axis 3 は未確定足と同一 bar 再発火を strategy 内で抑止しない。Axis 5 は initial R:R こそ 2.5R だが fixed ATR TP/SL のみで、breakout tail を trailing で伸ばす構造ではない。

再設計案は 1 系統にまとめる。Trigger を `squeeze_precondition AND release_bar_closed AND actual_breakout` に変更し、BUY は `prev_close <= upper_band_prev AND signal_close > upper_band_signal` または `signal_close > rolling_high(N)`、SELL は対称条件にする。ADX は hard precondition から `adx rising OR adx >= threshold` の score/soft gate に落とし、確定済み signal bar の次 bar entry に固定する。Stop は squeeze range 反対側または ATR cap 付き swing stop、exit は initial target + BE + ATR trailing に置き換える。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想は明確で、squeeze から volatility expansion を取る方向性自体は有効候補として残せる。ただし現行 trigger は breakout を数学的に捕捉していないため、最優先修正は Axis 2 の trigger 再定義。`bbpb > 0.75` / `< 0.25` を breakout proxy として使うのをやめ、確定足 close が BB upper/lower または squeeze range high/low を明確に抜けた時だけ signal にする。EMA9/EMA21 は hard gate として残すなら trend continuation filter、または score bonus に下げる。

Timing は closed-bar 化する。`ctx.df.iloc[-2]` を signal bar、`ctx.df.iloc[-3]` を previous bar として squeeze release と band/range cross を判定し、`ctx.entry` は次 bar execution として扱う。さらに `(instrument, strategy, bar_time, signal)` の per-bar dedup を strategy または dispatcher 側に追加する。これにより intrabar の暫定 BBPB/EMA/Volume で同一 bar に複数 entry するリスクを潰す。

Stop/TP は breakout 用に `initial_sl = opposite_squeeze_range ± ATR buffer`、`initial_tp = entry ± max(2R, ATR*2)`、以降は BE 移動と ATR trailing を exit layer に渡す設計にする。新規 BT は本 audit では実行していないため、採用前には 365d pair 別、WF folds>=3、Bonferroni-adjusted p、Kelly fraction を同じ pre-reg decision pool で再集計する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master 365d: `—`; shadow by-strategy artifact: N=13; aggregate-kelly: USD_JPY N=9 / EUR_USD N=5; pre-reg 5m BT: USD_JPY N=24 (`Insufficient`) | `knowledge-base/wiki/tier-master.md`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.md`; `knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03-render.md`; `knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.md` |
| Win rate | shadow by-strategy 7.7%; aggregate-kelly USD_JPY 33.33% / EUR_USD 40.00%; pre-reg 5m BT USD_JPY 75.00% but N<30 | same sources |
| Wilson lo (95%) | shadow by-strategy 1.4%; aggregate-kelly USD_JPY 12.06% / EUR_USD 11.76%; pre-reg 5m BT 55.10% but N<30 and not WF folds>=3 | same sources |
| PF | shadow by-strategy 0.06; aggregate-kelly USD_JPY 0.34 / EUR_USD 1.35; pre-reg 5m BT 4.872 but N<30 | same sources |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: pre-reg 5m BT has only 50/50 IS/OOS split (IS PF 2.442, OOS PF inf), not >=3 folds; tier-master has no fold metric | `knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json`; `knowledge-base/wiki/tier-master.md` |
| Bonferroni-adj p | pre-reg 5m BT p=0.00023226 vs alpha/K=0.0125, but verdict remains `Insufficient` due N<30; 365d tier-master p unavailable | `knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json`; `knowledge-base/wiki/tier-master.md` |
| Kelly fraction | pre-reg 5m BT full Kelly 0.596 / half Kelly 0.298, but N<30; aggregate-kelly artifact labels USD_JPY WATCH and does not provide Kelly fraction; tier-master Kelly unavailable | `knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json`; `knowledge-base/raw/audits/aggregate-kelly-decomposition-2026-05-03-render.md`; `knowledge-base/wiki/tier-master.md` |
