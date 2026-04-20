# Volume Surge Detector

## Status: SCALP_SENTINEL (Scalp最小ロット Shadow) + PAIR_DEMOTED (EUR_JPY, USD_JPY)

**Tier**: SCALP_SENTINEL | **N(post-cut)**: 11 | **WR**: 63.6% | **PnL**: +19.6pip (データ蓄積中)

現行: Scalp 最小ロット Shadow。EUR_JPY / USD_JPY は PAIR_DEMOTED (v7.0 / v8.9) で明示的に実弾除外。EUR_USD は _PAIR_LOT_BOOST 1.8x (v8.9 alpha scan: N=7 EV=+1.20 Kelly=32.7% → Half=16.4%)。

## 概要
急激なボリューム変化（vol倍率1.7x超）を検出してエントリー。
Momentum（トレンド初動）とClimax（反転）の二面性を持つ。

## 特記事項
- v6.5で momentum/climax 二面性のバグ修正済み
- RANGE_MR_STRATEGIESに含まれるが、momentumモードはSQUEEZE通過

## Related
- [[index]] — Tier 2 Sentinel
- [[system-reference]] — vol_surge_detector詳細
