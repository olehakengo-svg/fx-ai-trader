---
strategy: squeeze_release_momentum
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: EUR_USD
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

BB squeeze で蓄積した低ボラ状態が、BB 幅拡大と band 端方向への価格位置で解放される初動を momentum follow する戦略。コードコメントは「BB圧縮→解放のトレンド初動」を明示し、`squeeze_bars>=3`、BB width 拡大、`bbpb` 方向、陽線/陰線確認を保持 filter として定義している。`strategies/daytrade/squeeze_release_momentum.py:2`, `strategies/daytrade/squeeze_release_momentum.py:10`, `strategies/daytrade/squeeze_release_momentum.py:18`, `strategies/daytrade/squeeze_release_momentum.py:48`, `strategies/daytrade/squeeze_release_momentum.py:52`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / breakout thesis に対して、precondition は `3 <= squeeze_bars <= 40`、release は `ctx.bb_width >= prev_bb_width`、方向は `BUY: bbpb > 0.75` / `SELL: bbpb < 0.25`、足方向は `BUY: entry > open_price` / `SELL: entry < open_price`。これは BB 圧縮後の volatility expansion と方向確定を直接捕捉しており、MR trigger ではない。`strategies/daytrade/squeeze_release_momentum.py:49`, `strategies/daytrade/squeeze_release_momentum.py:50`, `strategies/daytrade/squeeze_release_momentum.py:102`, `strategies/daytrade/squeeze_release_momentum.py:104`, `strategies/daytrade/squeeze_release_momentum.py:114`, `strategies/daytrade/squeeze_release_momentum.py:118`, `strategies/daytrade/squeeze_release_momentum.py:122`, `strategies/daytrade/squeeze_release_momentum.py:128` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に bar-close 確定チェックや `ctx.bar_time` ベースの per-bar dedup がない。さらに trigger は現在 `ctx.bb_width` / `ctx.bbpb` / `ctx.entry` / `ctx.open_price` を直接使い、SL は `ctx.df["Low"].iloc[-_lookback:]` または `High` の直近 window を含めて計算するため、live evaluate が intrabar で呼ばれると未確定足の BB 幅・足色・高安に依存する。実行層で closed-bar を保証していれば緩和されるが、この strategy file 単体では保証されていない。`strategies/daytrade/squeeze_release_momentum.py:75`, `strategies/daytrade/squeeze_release_momentum.py:118`, `strategies/daytrade/squeeze_release_momentum.py:122`, `strategies/daytrade/squeeze_release_momentum.py:128`, `strategies/daytrade/squeeze_release_momentum.py:130`, `strategies/daytrade/squeeze_release_momentum.py:140`, `strategies/daytrade/squeeze_release_momentum.py:143` |
| 4 (filter coherence) | STRENGTHENS | Pair filter は EURUSD/GBPUSD に限定し、USDJPY は BT WR=50% / BEV=53% を理由に除外している。session gate は UTC 7-17 と金曜 13時以降 block で流動性を担保する。`squeeze_bars` 下限は圧縮蓄積、上限は dead market 排除、BB width 拡大と candle direction は release 方向確認として thesis を強化する。EMA200 / EMA PO は score bonus のみで hard gate ではないため、MA filter on MR strategy や HMM regime gate same-trap のように edge tail を破壊する filter ではない。`strategies/daytrade/squeeze_release_momentum.py:71`, `strategies/daytrade/squeeze_release_momentum.py:72`, `strategies/daytrade/squeeze_release_momentum.py:73`, `strategies/daytrade/squeeze_release_momentum.py:89`, `strategies/daytrade/squeeze_release_momentum.py:90`, `strategies/daytrade/squeeze_release_momentum.py:92`, `strategies/daytrade/squeeze_release_momentum.py:102`, `strategies/daytrade/squeeze_release_momentum.py:104`, `strategies/daytrade/squeeze_release_momentum.py:190`, `strategies/daytrade/squeeze_release_momentum.py:197` |
| 5 (stop/TP geometry) | ALIGNED | SL は swing H/L 8本 +/- `0.3ATR` を起点にしつつ、距離を `0.8ATR <= SL <= 1.5ATR` に制限する。TP は `max(2.5ATR, 1.5R)` で、breakout / momentum thesis に必要な非対称 payoff を持つ。trailing はないが、固定 TP でも minimum R:R は momentum continuation と整合している。`strategies/daytrade/squeeze_release_momentum.py:57`, `strategies/daytrade/squeeze_release_momentum.py:58`, `strategies/daytrade/squeeze_release_momentum.py:59`, `strategies/daytrade/squeeze_release_momentum.py:60`, `strategies/daytrade/squeeze_release_momentum.py:61`, `strategies/daytrade/squeeze_release_momentum.py:62`, `strategies/daytrade/squeeze_release_momentum.py:139`, `strategies/daytrade/squeeze_release_momentum.py:146`, `strategies/daytrade/squeeze_release_momentum.py:157`, `strategies/daytrade/squeeze_release_momentum.py:163` |
| 6 (pair-regime fit) | FIT | EUR_USD は promotion 時 N=15, WR=66.7%, EV=+0.460, PF=1.91、2026-04-21 再計測でも N=10, WR=70.0%, EV=+0.411 と小 N ながら positive signal を維持。GBP_USD は allowed だが本 cell 対象外で、USDJPY はコード上も除外されている。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | N/WR/EV/PF は既存 BT と Audit B に positive signal があるが、pair-promoted の tier-master は 365d BT EV `—`、Audit B は N=10 で保留、Bonferroni は「N不足のため計算意味なし」、Live EUR_USD は未発火。Wilson/PF/Kelly の既存値・導出値は下表に分離する。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_USD | FIT / INSUFFICIENT_N | promotion 時 N=15, WR=66.7%, EV=+0.460, PF=1.91。Audit B 2026-04-21 は N=10, WR=70.0%, EV=+0.411 で現状維持だが N不足。tier-master 365d BT EV は `—`。 |

## Axis 8: failure mode 診断

Tier 3/4 ではないが、Tier 1 (LIVE) で Axis 7 が insufficient、かつ Axis 3 に timing 実装リスクがあるため診断対象とする。思想と trigger/filter/SLTP の方向性は整合しており、破綻候補は Axis 3 の intrabar / same-bar 重複リスク。特に SRM は「BB 幅が前足より拡大したか」と「足色」を現在 ctx 値で判定するため、closed-bar 前提が崩れると release 確認が未確定足の途中経過になる。

再設計案は timing hardening 1 系統。`ctx.bar_time` または `ctx.df.index[-1]` を使った per-bar dedup を strategy 内に持たせ、同一 symbol/signal/bar では一度しか emit しない。加えて trigger 判定は closed bar の `df.iloc[-2]` を signal bar、`ctx.entry` を次 bar entry として明示する variant を作る。新規 BT は本タスクでは実行せず、既存 positive signal を壊さないかを 365d + WF folds>=3 + Bonferroni/Kelly で検証する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

最小修正は timing 1 系統。現在の thesis と trigger は維持し、closed-bar 化と per-bar dedup を追加する。コードレベルでは `evaluate()` 冒頭で `bar_id = ctx.bar_time or ctx.df.index[-1]` を得て、`(ctx.symbol, signal, bar_id)` の last-emitted guard を置く案が最小差分になる。ただし signal は trigger 後に確定するため、guard は `_is_buy/_is_sell` 判定直後に配置するのが自然。

より厳密な variant では、release 判定を current ctx 値から `signal_bar = ctx.df.iloc[-2]` に移し、`prev_bar = ctx.df.iloc[-3]` と比較して `signal_bar.bb_width >= prev_bar.bb_width`、`signal_bar.bbpb > 0.75 / < 0.25`、`signal_bar.Close > signal_bar.Open / < signal_bar.Open` を要求する。entry は次 bar の `ctx.entry` に限定する。この修正は latency を 1 bar 増やす可能性があるため、現行版との A/B は必須。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | promotion 時 N=15; Audit B 2026-04-21 365d recheck N=10; 180d WF aggregate N=23; Live EUR_USD N=0 | `knowledge-base/wiki/analyses/shadow-sentinel-decomposition.md`; `knowledge-base/wiki/analyses/audit-b-promoted-strategies-2026-04-21.md`; `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.json`; `knowledge-base/wiki/decisions/tier1-routing-rca-2026-05-04.md` |
| Win rate | promotion 時 66.7%; Audit B recheck 70.0%; 180d WF aggregate 69.6%; Live EUR_USD 0.0% on N=0 | same sources |
| Wilson lo (95%) | promotion-derived 41.7% (10/15); Audit B recheck-derived 39.7% (7/10); 180d WF aggregate-derived 49.1% (16/23). N<30 のため decision-grade ではない。 | derived from existing N/WR in above sources |
| PF | promotion PF=1.91; 180d WF aggregate PF=1.67; Audit B/tier-master 365d PF unavailable | `knowledge-base/wiki/analyses/shadow-sentinel-decomposition.md`; `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.json`; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | PARTIAL / INSUFFICIENT_EVIDENCE: 180d WF reports active_windows=3, positive_ratio=1.00, min_ev=+0.028; W60/W90/730d reports for EURUSD show N_windows<2 or insufficient. Not enough as 365d pair-promoted decision evidence. | `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.md` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: Audit B states squeeze_release_momentum is N不足 and Bonferroni calculation is not meaningful; tier-master has no p-value. Promotion N=15 vs EURUSD BEV 39.7% gives derived one-sided p≈0.032, Bonferroni m=3 p≈0.096, not significant. | `knowledge-base/wiki/analyses/audit-b-promoted-strategies-2026-04-21.md`; derived from existing promotion N/WR and BEV |
| Kelly fraction | promotion-derived full Kelly approx +0.318 from WR=66.7% and PF=1.91; 180d WF aggregate-derived full Kelly approx +0.279 from WR=69.6% and PF=1.67. No tier-master/audit DB Kelly column for this cell, so decision-grade Kelly is INSUFFICIENT_EVIDENCE. | derived from existing WR/PF in `knowledge-base/wiki/analyses/shadow-sentinel-decomposition.md` and `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.json` |
| tier-master EV | 365d BT EV `—` | `knowledge-base/wiki/tier-master.md` |
