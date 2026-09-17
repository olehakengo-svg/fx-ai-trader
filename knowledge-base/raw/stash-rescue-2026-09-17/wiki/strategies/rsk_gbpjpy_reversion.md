# rsk_gbpjpy_reversion

## Status: SHADOW_ALWAYS (Phase 10 G2 投入後 60s dedup gate 不在で汚染データ蓄積)

Realized Skewness Mean Reversion (15m daytrade). Rolling 30-bar realized skewness の z-score が ±2.0σ extreme で反転 bias 発生 (downside skew exhausts → BUY edge、upside skew → SELL)。GBP_JPY は intraday 変動が最大級で skewness 信号が最も鋭敏。

## 学術根拠
Barndorff-Nielsen-Shephard 2005, Amaya-Christoffersen 2015.

## BT 結果 (rsk_audit 2026-04-27, 365d)
- GBP_JPY sw=30 th=2.0 fw=6: WR 54.7%, n=1915, Sharpe 12.2, p_bonf 0.003 ✅
- +12 more Bonferroni-significant combos すべて GBP_JPY
- Best Sharpe: sw=20 th=2.0 fw=2: 14.2

## エントリ仕様
- GBP_JPY のみ (Bonferroni-significant 唯一の pair)
- rolling 30-bar realized skewness z-score |z| > 2.0
- direction = -sign(z) → MR
- SL = 1 ATR, TP = 1.5 ATR (RR 1.5)
- Hold ≤ 6 bars (90 min)

詳細実装: [rsk_gbpjpy_reversion.py](../../../strategies/daytrade/rsk_gbpjpy_reversion.py)
監査結果生データ: `raw/rsk_audit/rsk_audit_20260427_1306.json`

## 関連
- [[contamination-event-2026-04-30]]
- [[phase10-g2-investigation-2026-04-29]]
