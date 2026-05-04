---
strategy: ma_regime_switch
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

M15 volatility regime を rolling percentile で High/Low/Mid に分け、High vol では M15 大循環 + M5 EMA21 再ブレイクの trend continuation、Low vol では M5 BB%B/RSI/Stoch の range mean reversion だけを発火し、Mid vol は捨てる hybrid regime-switch thesis。コード上の設計意図とカスケードに明示されている。`strategies/scalp/ma_regime_switch.py:8`, `strategies/scalp/ma_regime_switch.py:9`, `strategies/scalp/ma_regime_switch.py:10`, `strategies/scalp/ma_regime_switch.py:11`, `strategies/scalp/ma_regime_switch.py:14`, `strategies/scalp/ma_regime_switch.py:15`, `strategies/scalp/ma_regime_switch.py:16`, `strategies/scalp/ma_regime_switch.py:17`, `strategies/scalp/ma_regime_switch.py:20`, `strategies/scalp/ma_regime_switch.py:23`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Regime selector の thesis は `M15 ATR rolling percentile >= 70 => Trend`, `<= 30 => MR` だが、実装は `atr_pct = ctx.bb_width_pct * 100` で 1m BB width percentile proxy を使っており、中心 trigger が thesis の M15 ATR percentile を数学的に捕捉していない。枝の entry 条件自体は、Trend 側が `EMA9>EMA21>EMA50 AND slope>0 AND ADX>=22 AND M5 close crosses EMA21 AND 1m bullish AND MACDH rising`、MR 側が `BB%B<=0.30 AND RSI<=35 AND Stoch反転 AND 1m bullish` で局所 thesis には整合するが、regime 分岐の代理変数がズレている。`strategies/scalp/ma_regime_switch.py:8`, `strategies/scalp/ma_regime_switch.py:9`, `strategies/scalp/ma_regime_switch.py:10`, `strategies/scalp/ma_regime_switch.py:22`, `strategies/scalp/ma_regime_switch.py:69`, `strategies/scalp/ma_regime_switch.py:70`, `strategies/scalp/ma_regime_switch.py:71`, `strategies/scalp/ma_regime_switch.py:72`, `strategies/scalp/ma_regime_switch.py:80`, `strategies/scalp/ma_regime_switch.py:86`, `strategies/scalp/ma_regime_switch.py:88`, `strategies/scalp/ma_regime_switch.py:97`, `strategies/scalp/ma_regime_switch.py:111`, `strategies/scalp/ma_regime_switch.py:117`, `strategies/scalp/ma_regime_switch.py:123` |
| 3 (timing window) | LOOKAHEAD | この file は `ctx.htf["m15"]` / `ctx.htf["m5"]` の EMA/ADX/BB%B/RSI/Stoch と現在 1m の `ctx.entry` vs `ctx.open_price` / `ctx.macdh` を同一 evaluate で読むが、bar-close 確定確認や per-bar dedup state を持たない。明示的な未来 index 参照はないものの、未確定 M5/M15/1m 値で signal が intrabar に点滅し、同一 bar 多重 entry になり得るため LOOKAHEAD 寄り。`strategies/scalp/ma_regime_switch.py:64`, `strategies/scalp/ma_regime_switch.py:65`, `strategies/scalp/ma_regime_switch.py:81`, `strategies/scalp/ma_regime_switch.py:84`, `strategies/scalp/ma_regime_switch.py:90`, `strategies/scalp/ma_regime_switch.py:91`, `strategies/scalp/ma_regime_switch.py:97`, `strategies/scalp/ma_regime_switch.py:98`, `strategies/scalp/ma_regime_switch.py:99`, `strategies/scalp/ma_regime_switch.py:112`, `strategies/scalp/ma_regime_switch.py:117`, `strategies/scalp/ma_regime_switch.py:119` |
| 4 (filter coherence) | BREAKS | Pair gate `_ALLOWED_PAIRS = {"USD_JPY"}` は USDJPY 特化 thesis を STRENGTHENS。M15/M5 availability と ATR>0 は NEUTRAL。Trend branch の ADX>=22 / EMA order / slope は trend continuation を STRENGTHENS。Mid-vol no-fire は thesis 通りなら STRENGTHENS。ただし最重要 filter である volatility regime gate が M15 ATR percentile ではなく `ctx.bb_width_pct` proxy に置換されており、HMM regime gate same-trap の先行例と同様、edge が依存する regime tail を別 proxy で誤分類する BREAKS リスクがある。MR branch には MA hard filter がないため MA filter breaks MR そのものは回避している。`strategies/scalp/ma_regime_switch.py:34`, `strategies/scalp/ma_regime_switch.py:59`, `strategies/scalp/ma_regime_switch.py:61`, `strategies/scalp/ma_regime_switch.py:64`, `strategies/scalp/ma_regime_switch.py:66`, `strategies/scalp/ma_regime_switch.py:72`, `strategies/scalp/ma_regime_switch.py:80`, `strategies/scalp/ma_regime_switch.py:86`, `strategies/scalp/ma_regime_switch.py:88`, `strategies/scalp/ma_regime_switch.py:89`, `strategies/scalp/ma_regime_switch.py:111`, `strategies/scalp/ma_regime_switch.py:130`, `strategies/scalp/ma_regime_switch.py:132`, `strategies/scalp/ma_regime_switch.py:147`, `strategies/scalp/ma_regime_switch.py:148` |
| 5 (stop/TP geometry) | MISALIGNED | Constants are `SL=1.0*ATR7`, `TP_trend=1.6*ATR7`, `TP_MR=1.0*ATR7`; implementation enforces `tp_dist = max(ctx.atr7 * tp_mult, sl_dist * 1.2)`, so Trend R:R is 1.6 and MR R:R is effectively 1.2. Trend side is plausible asymmetry, but MR side does not target a mean such as BB mid/VWAP/EMA and uses a tight 1 ATR stop that can cut before reversion completes; hybrid strategy overall is therefore MISALIGNED. `strategies/scalp/ma_regime_switch.py:38`, `strategies/scalp/ma_regime_switch.py:39`, `strategies/scalp/ma_regime_switch.py:40`, `strategies/scalp/ma_regime_switch.py:96`, `strategies/scalp/ma_regime_switch.py:116`, `strategies/scalp/ma_regime_switch.py:137`, `strategies/scalp/ma_regime_switch.py:138`, `strategies/scalp/ma_regime_switch.py:140`, `strategies/scalp/ma_regime_switch.py:141`, `strategies/scalp/ma_regime_switch.py:143`, `strategies/scalp/ma_regime_switch.py:144` |
| 6 (pair-regime fit) | FIT / FORCED | Input is `pairs: ALL`, but implementation is USD_JPY-only. USD_JPY is FIT for the code thesis; non-USD_JPY pairs are FORCED by audit scope but become no-trade at L1. Pair table below. |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master has SCALP_SENTINEL membership only and prompt-supplied 365d BT EV is `—`. Existing audit DB has v1c-rev 90d-style MA-family evidence: N=397, WR=49.12%, Wilson lo=44.23%, PF=0.939, Kelly=0.0, EV=-0.137p; WF folds exist but only 1/3 fold has PF>1. Bonferroni-adjusted p is not stored; raw p=0.99999 and BH significant flag is False. Under `feedback_partial_quant_trap.md` standard, this is not decision-grade evidence. |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT | File-level L1 gate allows only USD_JPY, matching the MA-family USDJPY scalp validation scope. `strategies/scalp/ma_regime_switch.py:21`, `strategies/scalp/ma_regime_switch.py:34`, `strategies/scalp/ma_regime_switch.py:59` |
| non-USD_JPY | FORCED / NO-TRADE | Audit input says ALL, but non-USD_JPY is rejected before indicators are read. `strategies/scalp/ma_regime_switch.py:34`, `strategies/scalp/ma_regime_switch.py:59`, `strategies/scalp/ma_regime_switch.py:60` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 2 と Axis 4 が主、Axis 3 と Axis 5 が副次。思想は明確で、Trend branch と MR branch の局所 trigger もそれぞれ EMA/ADX continuation と BB%B/RSI/Stoch reversion を持つため、edge thesis 自体は捨てない。一方、中心の regime switch が M15 ATR rolling percentile ではなく 1m BB width percentile proxy で分岐しており、レジーム誤分類で Trend/MR の適用先を壊す。さらに bar-close/dedup 不在と、MR 側が mean target を持たない ATR 1.2R TP で、scalp の cost-edge ratio を吸収しにくい。

再設計案は Trigger/Filter 置換を主軸にする。`atr_pct = ctx.bb_width_pct * 100` を廃止し、実際の M15 ATR rolling percentile または少なくとも M15 BB/ATR percentile の同一時間足 proxy に置換する。High/Low/Mid の hard threshold は 70/30 固定ではなく、まず `High vol AND ADX percentile high` を Trend、`Low vol AND ADX low/flat` を MR に分け、Mid no-fire は残す。Timing は signal を M5/M15 close 確定後の次 1m bar で一度だけ評価し、routing または strategy state で per-bar dedup を保証する。

Stop/TP は branch 別に分離する。Trend は現行 1.6R を最低線にして trailing または swing continuation target を追加する。MR は `TP = BB mid / VWAP / EMA21 mean target`、`SL = BB outer + ATR buffer` に変更し、固定 `max(sl*1.2)` を使わない。採用前には本 audit では実行しない 365d + WF folds>=3 の再集計で、Wilson lo / PF / Bonferroni-adjusted p / Kelly fraction を同一 source から確認する必要がある。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想はコードから十分に導けるため `THESIS_INVALID` ではない。現行 v1c-rev は旧 v1c の N=22 機能不全から N=397 へ改善しているが、PF=0.939 / Kelly=0.0 / raw p=0.99999 で edge には届いていない。主因は hybrid thesis そのものより、regime trigger が thesis の M15 ATR percentile から 1m BB width proxy にすり替わっている点と、MR exit が mean-reversion geometry になっていない点にある。

具体的には、`strategies/scalp/ma_regime_switch.py:72` の `atr_pct = ctx.bb_width_pct * 100` を M15 ATR rolling percentile の実値に置き換える。Trend branch は `M15 EMA order + ADX + M5 EMA21 cross` を維持しつつ bar-close 化する。MR branch は BB%B/RSI/Stoch trigger を維持し、TP を BB mid/VWAP/EMA21 への平均回帰 target、SL を外側バンド + ATR buffer に変更する。これは trigger/filter/timing/stop の複数点修正だが、中心は regime trigger 1 系統の置換なので Recommendation は A とする。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 397 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv`; `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| Win rate | 49.12% | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| Wilson lo (95%) | 44.23% | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv` |
| PF | 0.939 | audit DB; tier-master has SCALP_SENTINEL membership only and no PF for this strategy |
| WF folds (3+) | 3 folds available; PF by fold = f1 0.916, f2 0.856, f3 1.058, so only 1/3 folds PF>1 and WF stability fails | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE; stored raw p=0.99999 and BH significant flag=False, but Bonferroni-adjusted p is not stored in tier-master or audit CSV. If applying the documented 12-test MA-family Bonferroni mechanically, p_adj caps at 1.0, but this is not a stored audit metric. | audit DB + `knowledge-base/wiki/strategies/ma_generic_family_v1.md` |
| Kelly fraction | 0.0 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
