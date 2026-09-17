# vsg_jpy_reversal

## Status: SHADOW_ALWAYS (Phase 10 G2 投入後 60s dedup gate 不在で汚染データ蓄積)

EWMA-forecast Vol Surprise Reversal (15m daytrade). Realized return が EWMA(λ=0.94) forecast の 1.5× を超える「vol surprise」発生時、JPY crosses (EUR_JPY, GBP_JPY) は fade する (mean reversion) という仮説。

## 学術根拠
Engle-Patton 2001 + 実測。panic / carry unwind 系 event の overshoot → 反転構造。

## BT 結果 (vsg_audit 2026-04-27, 365d)
- EUR_JPY reversal th=1.5 fw=2: WR 58.1%, n=718, p_bonf 0.00081 ✅
- EUR_JPY reversal th=2.0 fw=2: WR 59.4%, n=367, p_bonf 0.01674 ✅
- GBP_JPY reversal th=1.0 fw=4: WR 55.6%, n=1439, p_bonf 0.00108 ✅
- 90-test Bonferroni family で 7 combo 通過 — 真のエッジ確定

## エントリ仕様
詳細実装: [vsg_jpy_reversal.py](../../../strategies/daytrade/vsg_jpy_reversal.py)
監査結果生データ: `raw/vsg_audit/vsg_audit_20260427_1201.json`

## 関連
- [[contamination-event-2026-04-30]] (60s dedup gate 不在による shadow 汚染)
- [[phase10-g2-investigation-2026-04-29]] (Phase 10 G2 投入経緯)
