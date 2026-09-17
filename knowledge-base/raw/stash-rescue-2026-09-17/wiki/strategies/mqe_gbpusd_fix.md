# mqe_gbpusd_fix

## Status: SHADOW_ALWAYS (Phase 10 G2 投入後 60s dedup gate 不在で汚染データ蓄積)

Month-End London 4pm Fix Reversal (15m daytrade). Month-end last 2 営業日の London 4pm fix window (15:30-16:00 UTC) で GBP_USD は institutional rebalancing 圧力により直前 move を反転する典型。

## 学術根拠
Melvin-Prins 2015 拡張、Frömmel 2008.

## BT 結果 (mqe_audit 2026-04-27, 730d)
- GBP_USD reversal fw=6: WR 69.8%, n=96, p_bonf 0.00158 ✅
- GBP_USD reversal fw=4: WR 66.7%, n=96, p_bonf 0.01709 ✅
- GBP_USD reversal fw=8: WR 66.7%, n=96, p_bonf 0.01709 ✅
- Best Sharpe: 6.03 (fw=6)

## エントリ仕様
- GBP_USD のみ (Bonferroni-significant)
- month_end_last_2_business_days ∧ 15:30-16:00 UTC
- direction = -sign(prior 4-bar move) → fade
- SL = 1 ATR, TP = 1.5 ATR
- Hold ≤ 6 bars (90 min)

詳細実装: [mqe_gbpusd_fix.py](../../../strategies/daytrade/mqe_gbpusd_fix.py)
監査結果生データ: `raw/mqe_audit/mqe_audit_20260427_1305.json`

## 関連
- [[contamination-event-2026-04-30]] (60s dedup 不在で 1 時間に 78 件 emit)
- [[phase10-g2-investigation-2026-04-29]]
