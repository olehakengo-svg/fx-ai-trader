# Volume Surge Detector

## Status: SCALP_SENTINEL + PAIR_DEMOTED (EUR_JPY のみ) — 2026-04-21 USD_JPY 復活

**Tier**: SCALP_SENTINEL | **現役ペア**: USD_JPY (sentinel lot), EUR_USD (PAIR_LOT_BOOST 1.8x)

現行: Scalp 最小ロット LIVE。EUR_JPY のみ PAIR_DEMOTED (v7.0)。

## 2026-04-21 深部クオンツ分析 (USD_JPY 復活判断)

| Metric | Value | 基準 | 判定 |
|---|---:|---|---|
| 365d BT N | 50 | ≥30 | ✅ |
| 365d BT WR | 68.0% | > BEV 34.4% | ✅ |
| Profit Factor | **1.811** | > 1.1 | ✅ 65% margin |
| Wilson 95% CI (WR) | [54.2%, 79.2%] | 下限 > BEV | ✅ 20pp margin |
| Sharpe (per-trade) | +0.294 | positive | ✅ |
| Walk-Forward (3バケット) | +0.28 / +0.86 / +0.14 | 全 > 0 | ✅ stability |
| Shadow post-cut N=19 | EV=+1.70 | positive | ✅ |

**撤回した v8.9 判断**: "全期間 N=28 EV=-0.34 Kelly=-10.4%" は regime 遷移前のデータに基づく。
365d BT の WF が regime 変動越しに全バケット正 → regime-robust 確認。

**安全弁**:
- SCALP_SENTINEL 継続 (PAIR_PROMOTED ではない) → sentinel 最小ロット
- EUR_JPY は PAIR_DEMOTED 維持 (v7.0 BT 7d WR=25.0% -36.5pip)
- 昇格/降格基準: **[[pre-registration-2026-04-21]]** §3.2 (binding pre-reg)
  - N=30 PF≥1.3 + Wilson 下限>BEV → PAIR_PROMOTED 昇格
  - N=15 WR<40% + sum<-5 → PAIR_DEMOTE 再設定

## 概要
急激なボリューム変化（vol倍率1.7x超）を検出してエントリー。
Momentum（トレンド初動）とClimax（反転）の二面性を持つ。

## 特記事項
- v6.5で momentum/climax 二面性のバグ修正済み
- RANGE_MR_STRATEGIESに含まれるが、momentumモードはSQUEEZE通過

## Related
- [[index]] — Tier 2 Sentinel
- [[system-reference]] — vol_surge_detector詳細
