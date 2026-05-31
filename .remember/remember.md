# Handoff

## State
M5 USDJPY simple price-action edge 探索を 5/15-5/20 で完結。Vol Exhaustion FADE 48/48 REJECT (commit e38b5f26)、HighVol CONTINUATION 375/375 REJECT (commit 3019f5de)。TV 1yr で見えた PF 1.234 (K=3.5, hours {9,11,15}, H=3) は **12.3y で完全消滅 = regime fluke**。BB 2σ Fade と Hourly Bias の 2 task は `.ai/tasks/failed/` に放置中。

## Next
1. **アプローチ転換** — M5 USDJPY simple market-order edge は数学的に取れないと確定。次は H1/H4 (大きい流れ) or 別 pair (EUR/USD, GBP/USD = tighter spread) or microstructure (tick data / passive limit) のどれかを選択。
2. 放置中の `failed/` 2 task (bb_2sigma, hourly_bias) は spec ベースで NULL 確定済なので **drop して OK**。
3. `/tmp/usdjpy_m5_1yr_pattern.md` の agent 分析は資産 — 別 pair で同じ分析を回せば即座に edge 構造を比較できる。

## Context
- **TV ST と Codex 12.3y BT が独立に同じ verdict** を出すパターンが 2 連続 (vol_exhaustion / highvol_continuation)。1yr TV は noise が乗りやすく、12.3y MASSIVE BT が真実。今後 1yr だけで結論しない。
- **クオンツファースト違反** が今回起きた: random strategy iteration に陥り、user に「クオンツの使命忘れてませんか」と指摘されて agent 分析へ pivot。次回は最初から **データ→パターン特定→検証** の順序を守る。
- **Spread cost が edge を上回る**: USDJPY M5 の signal effect は 0.5-4.5 bp、典型 spread 7-14 bp。市場 order では構造的に取れない。GMO/DMM の 0.2 pip なら可能性あり。
- 5/15 の 41h サンプル (-4.16 pip extreme bin) は N=17 で完全 noise。**N<100 で direction 結論しない**。
- Render worker container restart 問題は依然未解決 — heavy BT (≥5min) はローカル `/fx-run-codex` 一択。
