---
strategy: ma_mr_hybrid
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

USD/JPY 限定で、M15 の短期方向に沿った M5 の過熱押し目/戻りを、Stoch 反転と 1m 反転足で拾う trend-aware mean reversion thesis。コード上も `strategy_type = "MR"`、USD_JPY gate、M15 close vs EMA21 bias、M5 BB%B/RSI/Stoch、1m 足色確認として明示されている。`strategies/scalp/ma_mr_hybrid.py:13`, `strategies/scalp/ma_mr_hybrid.py:19`, `strategies/scalp/ma_mr_hybrid.py:20`, `strategies/scalp/ma_mr_hybrid.py:21`, `strategies/scalp/ma_mr_hybrid.py:22`, `strategies/scalp/ma_mr_hybrid.py:33`, `strategies/scalp/ma_mr_hybrid.py:57`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | BUY trigger は `bull_bias AND m5_bbpb <= 0.30 AND m5_rsi <= 35 AND stoch_k > stoch_d AND entry > open_price`、SELL trigger は `bear_bias AND m5_bbpb >= 0.70 AND m5_rsi >= 65 AND stoch_k < stoch_d AND entry < open_price`。MR thesis に必要な oversold/overbought 系 BB%B/RSI と反転 proxy は入っており、M15 方向 bias も hybrid thesis の数学的捕捉としては整合する。`strategies/scalp/ma_mr_hybrid.py:34`, `strategies/scalp/ma_mr_hybrid.py:35`, `strategies/scalp/ma_mr_hybrid.py:36`, `strategies/scalp/ma_mr_hybrid.py:37`, `strategies/scalp/ma_mr_hybrid.py:75`, `strategies/scalp/ma_mr_hybrid.py:76`, `strategies/scalp/ma_mr_hybrid.py:77`, `strategies/scalp/ma_mr_hybrid.py:94`, `strategies/scalp/ma_mr_hybrid.py:112` |
| 3 (timing window) | LOOKAHEAD | この file は `ctx.htf["m15"]` / `ctx.htf["m5"]` の `close`, `ema21`, `bbpb`, `rsi14`, `stoch` と、現在 1m の `ctx.entry` vs `ctx.open_price` を同一 evaluate で読むが、bar-close 確定確認や per-bar dedup state を持たない。未来 index 参照はないものの、未確定 M5/M15/1m 値で signal が intrabar に点滅し、同一 bar 多重 entry になり得るため LOOKAHEAD 寄り。`strategies/scalp/ma_mr_hybrid.py:65`, `strategies/scalp/ma_mr_hybrid.py:66`, `strategies/scalp/ma_mr_hybrid.py:71`, `strategies/scalp/ma_mr_hybrid.py:82`, `strategies/scalp/ma_mr_hybrid.py:83`, `strategies/scalp/ma_mr_hybrid.py:84`, `strategies/scalp/ma_mr_hybrid.py:85`, `strategies/scalp/ma_mr_hybrid.py:98`, `strategies/scalp/ma_mr_hybrid.py:116` |
| 4 (filter coherence) | BREAKS | Pair gate `_ALLOWED_PAIRS = {"USD_JPY"}` は thesis を STRENGTHENS。ATR/data availability checks は NEUTRAL。M15 EMA21 5bps hard bias は thesis 内の短期追風 filter だが、MR に MA hard filter を重ねる先行例 `feedback_ma_filter_breaks_mr.md` と同型の破壊リスクがあり、既存 audit でも v1a-rev は N=1 まで過剰絞りになった。ADX>=30 は hard gate ではなく score bonus なので NEUTRAL から STRENGTHENS 寄りだが、直後に MR 用 `apply_penalty` が ADX を罰するため score 設計は矛盾する。HMM regime gate same-trap と同様、edge が出る tail を generic gate/penalty で削る追加 filter は BREAKS。`strategies/scalp/ma_mr_hybrid.py:33`, `strategies/scalp/ma_mr_hybrid.py:38`, `strategies/scalp/ma_mr_hybrid.py:60`, `strategies/scalp/ma_mr_hybrid.py:62`, `strategies/scalp/ma_mr_hybrid.py:65`, `strategies/scalp/ma_mr_hybrid.py:75`, `strategies/scalp/ma_mr_hybrid.py:76`, `strategies/scalp/ma_mr_hybrid.py:77`, `strategies/scalp/ma_mr_hybrid.py:78`, `strategies/scalp/ma_mr_hybrid.py:133`, `strategies/scalp/ma_mr_hybrid.py:134`, `strategies/scalp/ma_mr_hybrid.py:139` |
| 5 (stop/TP geometry) | MISALIGNED | Constants are `SL=1.2*ATR7`, `TP=1.0*ATR7`, `RR_FLOOR=1.0`, but implementation uses `tp_dist = max(ATR7*1.0, sl_dist*1.0)`, so normal case is effectively R:R=1.0 because `sl_dist=1.2*ATR7` dominates. MR geometry should avoid cutting before mean reversion and should target an actual mean such as BB mid/EMA/VWAP; this code uses symmetric ATR distance, not mean target, so thesis geometry is weak. `strategies/scalp/ma_mr_hybrid.py:39`, `strategies/scalp/ma_mr_hybrid.py:40`, `strategies/scalp/ma_mr_hybrid.py:41`, `strategies/scalp/ma_mr_hybrid.py:100`, `strategies/scalp/ma_mr_hybrid.py:101`, `strategies/scalp/ma_mr_hybrid.py:102`, `strategies/scalp/ma_mr_hybrid.py:103`, `strategies/scalp/ma_mr_hybrid.py:118`, `strategies/scalp/ma_mr_hybrid.py:119`, `strategies/scalp/ma_mr_hybrid.py:120`, `strategies/scalp/ma_mr_hybrid.py:121` |
| 6 (pair-regime fit) | FIT / FORCED | Input is `pairs: ALL`, but implementation is USD_JPY-only. USD_JPY is FIT for the code thesis; non-USD_JPY pairs are FORCED by the audit scope but become no-trade at L1. `strategies/scalp/ma_mr_hybrid.py:1`, `strategies/scalp/ma_mr_hybrid.py:19`, `strategies/scalp/ma_mr_hybrid.py:33`, `strategies/scalp/ma_mr_hybrid.py:60`, `strategies/scalp/ma_mr_hybrid.py:61` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master has SCALP_SENTINEL membership only and prompt-supplied 365d BT EV is `—`. Existing audit CSV for current v1a-rev has N=1, WR=100%, Wilson lo=20.65%, PF=99.0, Kelly=0.0, raw p=0.16391, folds f1/f2/f3 = 1/0/0 trades. `feedback_partial_quant_trap.md` 基準では N=1 と raw p only では decision-grade evidence にならず、Bonferroni-adjusted p も保存されていない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT | File header and L1 gate are USD_JPY-only; thesis also USD_JPY 限定。`strategies/scalp/ma_mr_hybrid.py:1`, `strategies/scalp/ma_mr_hybrid.py:19`, `strategies/scalp/ma_mr_hybrid.py:33`, `strategies/scalp/ma_mr_hybrid.py:60` |
| non-USD_JPY | FORCED / NO-TRADE | `pairs: ALL` audit scope is broader than implementation; non-USD_JPY is rejected before indicators are read。`strategies/scalp/ma_mr_hybrid.py:33`, `strategies/scalp/ma_mr_hybrid.py:60`, `strategies/scalp/ma_mr_hybrid.py:61` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 4 が主、Axis 3 と Axis 5 が副次。Axis 2 の trigger は M5 BB%B/RSI/Stoch を持つため思想の捕捉自体は成立しているが、M15 EMA21 5bps hard gate が MR の entry tail を過剰に削り、既存 audit では v1a-rev が 90d N=1 まで縮退している。さらに未確定 bar/dedup 不在の timing と、BB mid/VWAP/EMA などの mean target を使わない 1:1 ATR geometry が、scalp MR の cost-edge ratio を悪化させる。

再設計案は Filter 削除/置換を主軸にする。具体的には M15 bias hard gate を撤去し、方向は entry gate ではなく score feature に落とす。代替 trigger は `m5_bbpb <= 0.30 AND m5_rsi <= 35 AND stoch_k_cross_up` / `m5_bbpb >= 0.70 AND m5_rsi >= 65 AND stoch_k_cross_down` を bar-close 確定で判定し、M15 EMA gap は `abs(gap) <= 1bp` の neutral zone 許容または `ADX/VWAP distance` の soft score にする。Stop/TP は `TP = BB mid or VWAP/EMA mean target`、`SL = BB outer + ATR buffer` に変え、minimum net TP gate で spread 負けする候補を捨てる。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想はコードから十分に導けるため `THESIS_INVALID` ではない。M5 過熱リバージョン trigger は成立しているが、M15 EMA21 5bps hard filter が MR edge を削る構造になっており、既存 audit の N=1 と整合する。まず `strategies/scalp/ma_mr_hybrid.py:75`-`strategies/scalp/ma_mr_hybrid.py:79` の bull/bear hard gate を entry 必須条件から外し、M15 gap は confidence/reason だけに使う設計へ移すのが最小修正。

次に `strategies/scalp/ma_mr_hybrid.py:98` と `strategies/scalp/ma_mr_hybrid.py:116` の 1m 足色確認を bar-close 確定値に限定し、同一 bar dedup を routing 側または strategy state 側で保証する。Exit は `strategies/scalp/ma_mr_hybrid.py:102` / `strategies/scalp/ma_mr_hybrid.py:120` の symmetric ATR TP を、BB mid/VWAP/EMA21 などの mean target に置き換える。採用前には本 audit では実行しない 365d + WF folds>=3 の再集計で、Wilson lo / PF / Bonferroni-adjusted p / Kelly fraction を同一 source から出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 1 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv` / `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| Win rate | 100.0% | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| Wilson lo (95%) | 20.65% | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| PF | 99.0 | audit DB; N=1 artifact, not decision-grade |
| WF folds (3+) | 3 folds available but insufficient: f1 N=1 / PF=99.0, f2 N=0 / PF=0.0, f3 N=0 / PF=0.0 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE; stored raw p=0.16391 and BH significant flag is False, but Bonferroni-adjusted p is not present in tier-master or audit CSV | audit DB + tier-master |
| Kelly fraction | 0.0 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
