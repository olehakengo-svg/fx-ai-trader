# SHADOW/SENTINEL 13戦略 因数分解レビュー (2026-04-15)

## 判定サマリー

| # | Strategy | Best BT | N | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | doji_breakout | GBP +0.724 | 23 | **PROMOTE** | BT STRONG、パターン検出が堅実 |
| 2 | dt_fib_reversal | EUR +0.407 | 10 | **PROMOTE** | GBP N=22正EV、EMAゲート統合済み |
| 3 | dt_sr_channel_reversal | EUR_JPY +0.178 | 362 | KEEP | 高N低EV、摩擦リスク |
| 4 | squeeze_release_momentum | EUR +0.656 | 15 | **PROMOTE** | 低頻度高品質、理論堅実 |
| 5 | vol_spike_mr | JPY +0.148 | 130 | KEEP | 高N低EV、閾値緩和で希薄化 |
| 6 | eurgbp_daily_mr | — | 0 | TEST | EUR_GBP BT未実施 |
| 7 | gold_trend_momentum | — | 0 | **STOP** | XAU除外済み |
| 8 | gotobi_fix | — | 0 | KEEP | 学術根拠強い、低N構造的 |
| 9 | hmm_regime_filter | N/A | 0 | **STOP** | 戦略ではなくユーティリティ |
| 10 | liquidity_sweep | — | 0 | KEEP+TEST | 学術最強、BT未実施 |
| 11 | london_close_reversal | — | 0 | KEEP | 時間窓戦略、低N構造的 |
| 12 | three_bar_reversal | JPY -0.371 | 6 | **STOP** | N=6/180日、構造的にN蓄積不能 |
| 13 | v_reversal | GBP_JPY +0.603 | 7 | KEEP | JPYクロスで有望だがN不足 |

## PROMOTE対象の根拠

### doji_breakout → GBP_USD, USD_JPY
- GBP_USD: N=23, WR=78.3%, EV=+0.724, PF=2.47
- USD_JPY: N=21, WR=61.9%, EV=+0.338, PF=1.40
- 3連続doji後のブレイクアウト追随。ボラティリティクラスタリング理論

### squeeze_release_momentum → EUR_USD
- EUR_USD: N=15, WR=66.7%, EV=+0.460, PF=1.91
- BB圧縮→拡張の初動キャプチャ。低頻度高品質シグナル
- 実装品質最高（5フィルター→2フィルターのオーバーフィット削減済み）

### dt_fib_reversal → GBP_USD
- GBP_USD: N=22, WR=72.7%, EV=+0.310, PF=1.63
- EUR_JPY N=81 EV=-0.199 → EUR_JPYは明示的除外必須
- EMAスコアゲート統合済み（本セッション実装）

## STOP対象の根拠

### gold_trend_momentum — XAU除外
- XAUが全停止中。BT不能。復活時に再評価。

### hmm_regime_filter — 戦略ではない
- evaluate()が常にNone返却。トレードを生成しない。
- ユーティリティモジュールとして再分類すべき。

### three_bar_reversal — 構造的N不足
- 4条件同時必須 → 180日でN=6。年間N=12では統計検証不能。

## 汎用教訓

1. **低NはN/日で評価**: squeeze(月1-2回)は構造的低Nで許容、three_bar(月0.03回)は不許容
2. **ユーティリティはSENTINELに入れない**: hmm_regime_filterはN=0が永久に続く
3. **ペア別判定は必須**: dt_fib_reversalはGBP正EV、EUR_JPY負EV。同一戦略でも逆の結論

## Related
- [[force-demoted-decomposition]] — FORCE_DEMOTED 12戦略
- [[strategy-overlap-analysis]] — 重複・固有性分析
