# Sweep-Reversion Grid Scan 12y — Design

**Date**: 2026-06-12
**Status**: APPROVED (user inline approval)
**Rule classification**: R1 research (探索、production コード変更なし)
**Author**: Claude (一次実装、`[[feedback_codex_as_review_layer_2026_06_05]]`)

## Purpose

Stop-hunt / liquidity-sweep 戻り（マイクロ構造オーバーリアクション）に 12y スケールで
Bonferroni を生き残る edge cell が存在するかを、**production 戦略を書く前に**確認する。

順序の根拠: 2026-06-07〜08 に Kalman D7 / sr_fib V3 / session_time_bias+bb_rsi の
3 系統が「先に実装 → 後で 12y 検証 → 全 REJECT」を繰り返した
(`[[project_session_time_bias_bb_rsi_12y_reject_2026_06_11]]`)。本スキャンは順序を逆転し、
12y 生存 cell が確認できてから初めて productionize する。

凍結解除の経緯: `[[project_strategy_rethink_consolidation_2026_06_08]]` は新規探索を
ROI 低と凍結したが、user が 2026-06-12 に明示判断で解除（矛盾は提起済み）。

## Sweep event 定義（最小・固定）

- Swing level: 直近 L bars の rolling max(high) / min(low)、当該バー除外 (shift 1)
- Sweep (high 側): `high > swing_high + d×ATR14` AND `close < swing_high`（同バー reclaim）
  低値側は対称
- Entry 計測: 次バー open → H bars 後 close、反転方向 (high-sweep→SELL / low-sweep→BUY)
- Net pip = 方向付き move − spread（下表）
- Dedup: イベント間最低 12 bars
- TP/SL シミュレーションなし（出口バイアス排除、方向エッジの有無のみ測る）

## Grid 軸 (m = 1,728)

| 軸 | 値 |
|---|---|
| pair | EUR_USD, GBP_USD, EUR_GBP, EUR_JPY（12y native 15m のみ。USD_JPY は 1.2y で対象外） |
| TF | 15m native / 1h（15m から OHLC 集計 — 補間でない合法導出） |
| L | 24, 96, 288 bars |
| d | 0.05, 0.25, 0.5 ×ATR14 |
| direction | SELL (high-sweep), BUY (low-sweep) |
| H | 4, 16, 48 bars |
| session | ASN(0-7), LDN(7-13), NY(13-21), LATE(21-24) UTC |

## Spread model（12y runner と同一 + EUR_GBP 追加）

EUR_USD 0.8 / GBP_USD 1.2 / EUR_JPY 1.6 / **EUR_GBP 1.5（assumption、OANDA リテール実勢）**

## 判定

- **Hard gate（user 選択: Bonferroni のみ）**: mean_net_pip > 0 AND t_stat ≥ z_bonf
  - α = 0.05 / 1728 ≈ 2.89e-5 → z_bonf ≈ 4.02
- **情報列（gate にしない）**: Wilson_lo(WR)、WFO 3-fold の fold 別 mean 符号、
  年次一貫性（12 年中プラス年数）。昇格判断時の user 材料

## 出力

- `bt-results/sweep-reversion-grid-scan-12y.json`（全 cell + メタ）
- `bt-results/sweep-reversion-grid-scan-12y.md`（生存 cell ランキング t-stat 降順、
  生存ゼロならその旨明記 → 機序棄却記録）

## 実装・実行

- 単一研究スクリプト `tools/research_sweep_reversion_grid_12y.py`（vectorized pandas/numpy）
- Claude がローカル直接実行（Codex 不使用）
- production 戦略・demo_trader・config 一切変更なし
