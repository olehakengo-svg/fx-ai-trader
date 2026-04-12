# XAU停止の根拠 (v8.4)

**決定日**: 2026-04-10 | **バージョン**: v8.4

## 決定
XAU (Gold) の全トレーディングモード（scalp_xau, daytrade_xau）を auto_start=False に設定。

## 根拠
- Post-cutoff XAU損失: **-2,280pip**（全損失の102%）
- FX-only post-cutoff: **+96.8pip（黒字）**
- XAUを除外するだけでシステム全体が黒字に転換
- avg_friction: XAU=217.5pip vs FX=2.14pip — 構造的に摩擦負け

## 影響
- DD計算からXAU損失を除外 → v8.9 Equity Resetの前提条件
- FX-only評価が正しいシステムパフォーマンス指標に

## Related
- [[lesson-xau-friction-distortion]] — XAU摩擦歪みの教訓
- [[changelog]] — v8.4エントリー
