---
strategy: fib
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

直近 45/60 バーの高安から 38.2% / 50.0% / 61.8% の Fibonacci retracement を作り、上昇トレンドの押し目・下降トレンドの戻りが Fib level 近傍で短期 oscillator 反転を示した瞬間に平均回帰を取る MR 戦略。コード上も `strategy_type = "MR"`、および「Fib reversal is a mean-reversion at Fibonacci levels」と明示されている。`strategies/scalp/fib.py:7`, `strategies/scalp/fib.py:23`, `strategies/scalp/fib.py:37`, `strategies/scalp/fib.py:44`, `strategies/scalp/fib.py:116`, `strategies/scalp/fib.py:137`, `strategies/scalp/fib.py:165`, `strategies/scalp/fib.py:202`, `strategies/scalp/fib.py:203`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、Fib level 近接 `abs(ctx.entry - fib_level) < ATR * 0.35` を必須にし、BUY は `trend=up AND rsi5<48 AND stoch_k>stoch_d`、SELL は `trend=down AND rsi5>52 AND stoch_k<stoch_d`。さらに MACD-H 反転を非極端 BB%B では hard gate にしており、Fib support/resistance からの短期反転を条件化している。RSI 閾値は浅いが、thesis と数学的には整合する。`strategies/scalp/fib.py:49`, `strategies/scalp/fib.py:50`, `strategies/scalp/fib.py:51`, `strategies/scalp/fib.py:118`, `strategies/scalp/fib.py:119`, `strategies/scalp/fib.py:138`, `strategies/scalp/fib.py:155`, `strategies/scalp/fib.py:160`, `strategies/scalp/fib.py:166`, `strategies/scalp/fib.py:183`, `strategies/scalp/fib.py:188` |
| 3 (timing window) | LOOKAHEAD | Fib swing は `_sub = df.iloc[-lookback:]` の `High.max()` / `Low.min()` で最新 bar を含めて計算し、trigger も現在足由来の `ctx.entry`, `ctx.open_price`, `ctx.high`, `ctx.low`, `ctx.rsi5`, `ctx.stoch_k`, `ctx.macdh` を直接使う。strategy 内に closed-bar 固定や `(symbol, signal, bar_time)` dedup がないため、実行層が intrabar evaluate すると未確定 high/low で Fib level 自体が動き、同 bar 多重 entry も起き得る。`strategies/scalp/fib.py:14`, `strategies/scalp/fib.py:15`, `strategies/scalp/fib.py:16`, `strategies/scalp/fib.py:95`, `strategies/scalp/fib.py:119`, `strategies/scalp/fib.py:130`, `strategies/scalp/fib.py:131`, `strategies/scalp/fib.py:138`, `strategies/scalp/fib.py:166`, `strategies/scalp/fib.py:212` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | EURGBP disable は BT 負 EV ペアを止める filter なので STRENGTHENS。EURUSD/GBPUSD の 0-5 UTC block は低ボラ時間帯を避けるため STRENGTHENS。body ratio はヒゲ足排除、MACD-H 反転 gate は反転確認、38.2% score gate は弱い Fib level に高い確信を要求するため、いずれも Fib MR thesis を強化する。ADX>25 の MR anti-trend confidence penalty は「強トレンドでは Fib level が破られる」というコードコメントと整合し、MA filter on MR や HMM same-trap 型の edge-tail hard block は未検出。`strategies/scalp/fib.py:66`, `strategies/scalp/fib.py:67`, `strategies/scalp/fib.py:72`, `strategies/scalp/fib.py:78`, `strategies/scalp/fib.py:82`, `strategies/scalp/fib.py:83`, `strategies/scalp/fib.py:129`, `strategies/scalp/fib.py:150`, `strategies/scalp/fib.py:155`, `strategies/scalp/fib.py:178`, `strategies/scalp/fib.py:183`, `strategies/scalp/fib.py:193`, `strategies/scalp/fib.py:202`, `strategies/scalp/fib.py:203`, `strategies/scalp/fib.py:207` |
| 5 (stop/TP geometry) | MISALIGNED | Nominal TP は pair 別に `1.3-1.8ATR7`、SL は `0.7ATR7` と Fib offset `0.2ATR7` の外側を選ぶ。だが entry は Fib level から最大 `0.35ATR` 以内なので、`fib_offset` 側の距離は最大約 `0.55ATR` に留まり、実効 SL はほぼ `0.7ATR7` へ固定される。R:R は EURUSD/GBPUSD `1.3/0.7=1.86`、USDJPY `1.8/0.7=2.57` だが、MR の「mean へ戻る前にノイズで切られない wide stop」思想に対して stop が浅く、短期反発を即当てする設計へ寄り過ぎている。`strategies/scalp/fib.py:52`, `strategies/scalp/fib.py:53`, `strategies/scalp/fib.py:54`, `strategies/scalp/fib.py:57`, `strategies/scalp/fib.py:58`, `strategies/scalp/fib.py:119`, `strategies/scalp/fib.py:162`, `strategies/scalp/fib.py:163`, `strategies/scalp/fib.py:190`, `strategies/scalp/fib.py:191` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。実装は `ALL` ではなく、EURGBP を無効化し、USDJPY/EURUSD/GBPUSD/EURJPY/XAUUSD だけに pair-specific TP/session の痕跡がある。positive evidence も USDJPY Tokyo q0 と EURUSD 1m 参考 BT に偏っており、ALL scope は forced broad scope。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の force_demoted 行では 365d BT EV が `—`。audit DB には USDJPY Tokyo/q0 の strong shadow cell と local `demo_trades.db` の N=1 があるが、ALL cell の Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が同一 decision source で揃わない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT / narrow | audit DB の Tokyo USDJPY shadow cell は N=24, WR=87.5%, Wilson lo=69.0%, PF=14.60, Bonferroni p=0.0012。ただし tier-master では `fib_reversal` が force_demoted で ALL 365d EV は `—`。 |
| EURUSD | FIT / drawdown-risk | 既存 sidecar 180d candidate は N=101, WR=59.4%, PF=3.15, Wilson lo=49.655%, Kelly=0.4055 だが、verdict は max DD 理由で Reject。code は EURUSD 0-5 UTC block と TP 1.3ATR を持つ。 |
| GBPUSD | FORCED | code は GBPUSD 0-5 UTC block と TP 1.3ATR を持つが、audit DB の qualified positive cell は確認できない。 |
| EURJPY | FORCED | code は TP 1.5ATR のみで、pair-specific session/regime 根拠は薄い。 |
| XAUUSD | FORCED | code は TP 1.5ATR のみで、Fib scalp MR が XAU の spread/volatility regime に合う根拠は audit DB にない。 |
| EURGBP | FORCED / BLOCKED | strategy file は EURGBP を完全無効化しており、`ALL` scope とは一致しない。`strategies/scalp/fib.py:72`, `strategies/scalp/fib.py:73`, `strategies/scalp/fib.py:78` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) かつ tier-master では `fib_reversal` が FORCE_DEMOTED 側に載り、365d BT EV も `—` なので failure mode 診断対象とする。

破綻軸は Axis 3 と Axis 5。Axis 2 の Fib level + oscillator reversal trigger は thesis と整合し、Axis 4 の filters も概ね thesis を強化している。一方で、Fib swing と trigger が現在足に依存し、strategy 内 dedup がないため、signal bar と execution bar が分離されていない。さらに実効 SL がほぼ 0.7ATR に固定されるため、Fib MR が mean 回帰へ向かう前の通常ノイズで切られやすい。

再設計案は timing と stop geometry の 2 点。第一に `_calc_fibonacci_levels()` と trigger 判定を `ctx.df.iloc[:-1]` または `ctx.df.iloc[-lookback-1:-1]` の確定足で行い、signal は closed bar、execution は次 bar `ctx.entry` に分離する。併せて `(fib_reversal, symbol, signal, signal_bar_time)` の per-bar dedup を strategy または dispatch 層に入れる。第二に stop を `max(1.0ATR, fib_level +/- 0.5ATR)` 相当に広げ、TP は USDJPY 以外を早期利確する既存思想を維持しつつ、最低 R:R が崩れないかを再集計する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は維持する。Fib level 近傍の oscillator reversal を取る MR thesis はコードから明確に導出でき、trigger も大筋では合っている。ただし復活には timing と stop/TP geometry の 2 軸修正が必要なので、単純な filter 1 行削除の S/A ではなく B とする。

コードレベルの最小案は、`_calc_fibonacci_levels(ctx.df, lookback=lb)` に渡す dataframe を確定足までに切り、現在足の high/low で Fib level が再描画されないようにすること。signal 条件も確定足の close/open/indicator で評価し、次 bar execution と per-bar dedup を組み合わせる。

次に SL を 0.7ATR 固定から少なくとも 1.0-1.2ATR へ広げる variant を作る。現行の positive evidence は USDJPY Tokyo/q0 と EURUSD 1m に偏っているため、採用前には本 audit では実行しない closed-bar + wider-stop variant の 365d / WF folds>=3 / Bonferroni / Kelly 再集計が必要。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow/ALL: `—`; audit DB 365d Tokyo q0 Scalp: N=25; audit DB all-window Tokyo USDJPY: N=24; local `demo_trades.db`: N=1 | `knowledge-base/wiki/tier-master.md`; `raw/audits/cell_edge_audit_2026-05-02_v1_365d_inclshadow.json`; `raw/audits/cell_edge_audit_2026-04-27_v2_all_inclshadow.json`; `demo_trades.db` |
| Win rate | audit DB 365d Tokyo q0 Scalp: 84.0%; audit DB all-window Tokyo USDJPY: 87.5%; local `demo_trades.db`: 100.0% (N=1, not decision-grade) | same as above |
| Wilson lo (95%) | audit DB 365d Tokyo q0 Scalp: 65.35%; audit DB all-window Tokyo USDJPY: 69.0%; local `demo_trades.db`: 20.65% (N=1, not decision-grade) | same as above |
| PF | audit DB 365d Tokyo q0 Scalp: 12.179; audit DB all-window Tokyo USDJPY: 14.60; local `demo_trades.db`: infinite because N=1 / 0 losses | same as above |
| WF folds (3+) | INSUFFICIENT_EVIDENCE. Existing sidecar has only a 50/50 chronological split for EURUSD 1m, not WF folds>=3; tier-master/audit DB do not provide WF folds for ALL. | `knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json`; `knowledge-base/wiki/tier-master.md` |
| Bonferroni-adj p | audit DB 365d Tokyo q0 Scalp: 0.00202; audit DB all-window Tokyo USDJPY: 0.0012; ALL Bonferroni p is unavailable. | `raw/audits/cell_edge_audit_2026-05-02_v1_365d_inclshadow.json`; `raw/audits/cell_edge_audit_2026-04-27_v2_all_inclshadow.json` |
| Kelly fraction | local `demo_trades.db`: 1.0000 from N=1 / 0 losses, therefore INSUFFICIENT_EVIDENCE for decision use; sidecar EURUSD 1m reference reports Kelly full 0.4055 but is not tier-master/audit DB ALL evidence. | derived from `demo_trades.db`; `knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json` |
