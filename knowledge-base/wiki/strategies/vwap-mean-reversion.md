# VWAP Mean Reversion

## Overview
- **Entry Type**: `vwap_mean_reversion`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp 1m, DT 15m/1h
- **Status**: PAIR_PROMOTED (EUR_JPY, GBP_JPY, EUR_USD, GBP_USD, USD_JPY); LOT_BOOST 1.5x
- **Active Pairs**: EUR_JPY / GBP_JPY / EUR_USD / GBP_USD / USD_JPY (PAIR_PROMOTED)

## BT Performance (365d, 15m)
From massive alpha scan (Bonferroni significant, friction-adjusted):
| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | Annual PnL |
|---|---|---|---|---|---|---|---|
| VW2s BUY | EUR_JPY | 15m | 16b(4h) | 737 | 55.8% | +3.85 | +2,837p |
| VW2s BUY | GBP_JPY | 15m | 16b(4h) | 740 | 56.2% | +5.17 | +3,827p |
| VW2s BUY | USD_JPY | 15m | 16b(4h) | 705 | 55.0% | +2.98 | +2,099p |
| VW2s BUY | GBP_JPY | 1h | 16b | 245 | 56.3% | +13.4 | +3,290p |
| VW2s BUY | EUR_JPY | 1h | 16b | 226 | 58.0% | +6.32 | +1,428p |

### Fresh 365d × 15m BT (2026-04-22, `raw/bt-results/bt-365d-jpy-2026-04-22.json`)
| Pair | N | WR | EV | PnL | Walk-forward EV (w1/w2/w3) |
|---|---|---|---|---|---|
| EUR_JPY | 223 | 68.2% | +0.672 | +149.9 pip | +0.103 / +0.219 / +0.101 |
| GBP_JPY | 267 | 78.3% | +1.025 | +273.7 pip | +0.338 / +0.205 / +0.313 |

PAIR_PROMOTED の既存根拠を 2026-04-22 スキャンで再確証（walk-forward 全窓で正 EV、GBP_JPY は最強セル）。

Scalp (Bonferroni significant):
| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | Annual PnL |
|---|---|---|---|---|---|---|---|
| VW2s BUY | EUR_JPY | 1m | 16min | 2,574 | 56.5% | +0.81 | +2,087p |
| VW2s BUY | GBP_JPY | 1m | 16min | 2,028 | 53.6% | +0.48 | +975p |

### Scalp BT 2026-04-22 バグ発覚 + 修正完了
180d Scalp BT では `vwap_mean_reversion` の発火が 10 cell すべてでゼロ。原因は `app.py:_compute_scalp_signal_v2` 内で `htf_agreement` 変数が未定義、silent except で NameError が飲み込まれていた。2026-04-22 に `app.py:L7992` で `htf_agreement = htf.get("agreement", "mixed")` を追加して修正（commit `0981945`）。

Post-fix 180d × {1m, 5m} × JPY crosses (`raw/bt-results/bt-scalp-180d-jpy-postfix-2026-04-22.json`):
| Pair | TF | N | WR | EV | PnL |
|---|---|---|---|---|---|
| EUR_JPY | 1m | 17 | — | -0.272 | 負 |
| EUR_JPY | 5m | 2 | 100% | +0.874 | 小 N |
| GBP_JPY | 1m | 14 | 50.0% | -0.114 | 負 |
| GBP_JPY | 5m | 3 | 66.7% | +0.132 | 小 N |

- ✅ 発火復活、signal は機能
- ⚠️ 1m 版は両ペア負 EV、5m 版は正 EV だが N=2-3 で結論不可
- 🚫 Scalp 全体 EV は改善せず、Scalp vwap_mr は Live 配置候補として保留（365d 延長 BT or 1 年 N 蓄積まで）

### Scalp 5m × 365d 延長 BT (2026-04-22, `raw/bt-results/bt-scalp-5m-365d-jpy-2026-04-22.json`)

1180s で EUR_JPY / GBP_JPY × 365d × 5m を実行し、180d の小 N (+EV) signal の持続性を検証:

| Window | Pair | N | WR | EV | PnL | ΔN vs 180d |
|---|---|--:|--:|--:|--:|--:|
| 180d | EUR_JPY 5m | 2 | 100.0% | +0.874 | +1.7 | — |
| **365d** | **EUR_JPY 5m** | **4** | **100.0%** | **+0.839** | **+3.4** | +2 |
| 180d | GBP_JPY 5m | 3 | 66.7% | +0.132 | +0.4 | — |
| **365d** | **GBP_JPY 5m** | **5** | **60.0%** | **+0.098** | **+0.5** | +2 |
| **365d 合計** | JPY 2pair | **9** | 77.8% | **+0.427** | +3.9 | |

**判定**:
- 180d → 365d で N 5 → 9 (+4)、signal は維持、方向一致
- 加重 EV +0.427 は正方向だが、Gate 閾値 (N ≥ 20) に未達
- EURJPY 100% WR は「VWAP 2σ mean reversion が日を選んで機能」と整合
- Live 配置は引き続き **保留**（lesson-reactive-changes 遵守、N ≥ 20 or 30 累積まで）
- 5m 版 Live 展開は N 蓄積に 1 年以上要する見込み（180d で N=5 → 年換算 N ≈ 10 前後）

**付随発見 (365d × 5m Overall)**:
- GBP_JPY 5m Overall: N=1300 **EV=+0.026** — Scalp scope で貴重な構造的正 EV cell
- EUR_JPY 5m Overall: N=1206 EV=-0.075
- 詳細: `raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md#addendum`

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pairs | N | WR | PnL | Updated |
|---|---|---|---|---|---|
| vwap_mean_reversion | all | 8 | 50.0% | -17.5 pip | 2026-04-23 |

⚠️ **悪化継続**: N=6 -4.6pip (2026-04-22) → N=8 -17.5pip (2026-04-23). 2新規トレードで**-12.9pip**の追加損失。WRは50%を維持しているが、avg_loss >> avg_win パターンが強まっている。PnLは3日で +36.9→-4.6→-17.5 と急転落。
BT実績 (GBP_JPY: EV=+1.025, EUR_JPY: EV=+0.672) との乖離が拡大中。N=8では統計的判断不可 — 継続監視。N≥20到達まで実装変更なし (lesson-reactive-changes)。
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-23)

## Signal Logic
VWAP 2-sigma mean reversion. Enters BUY when price drops below VWAP minus 2 standard deviations, expecting reversion to VWAP. Massive API exclusive alpha — requires intraday VWAP calculation from tick/volume data. Bonferroni-corrected p<10^-7 across JPY crosses.

## Current Configuration
- Lot Boost: 1.5x (strategy-level)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: EUR_JPY (15m 16bar: annual +2,837pip), GBP_JPY (15m 16bar: annual +3,827pip, strongest alpha), EUR_USD, GBP_USD, **USD_JPY** (v9.x 2026-04-22: 5m 180d WF pos=1.00 CV=0.51 N=155 EV=+0.925)
- PAIR_LOT_BOOST: EUR_JPY 1.8x, GBP_JPY 1.8x

## 緊急トリップ + v2 sublimation (2026-04-24)

Live post-cutoff で N=8→10 (+2 trade) で **PnL -4.6 → -17.5 → -47.7pip** に急転落、
平均 -4.77pip/trade で BT との乖離拡大. 以下を commit で適用:

### Patch C — OANDA 送信 kill-switch (`demo_trader.py:4266+`)
- env var `VWAP_MR_OANDA_TRIP=1` (default on) で vwap_mr のみ OANDA 送信停止
- Shadow (DB 記録) は継続 → 統計蓄積に支障なし
- 即時解除: `VWAP_MR_OANDA_TRIP=0` で Render 環境変数セット
- 解除条件: v2 logic が Shadow で N≥20 かつ正 EV 実証

### Patch D — v2 sublimation filters (`app.py:3175` DT + `:8267` Scalp)
既存 2σ signal の後段に AND gate 追加 (env var `VWAP_MR_V2=1`):
1. VWAP slope flat only (|norm|≤0.3 σ/bar)
2. ADX hard block (ADX≥22 は reject — 従来 penalty のみ)
3. Active hours only (UTC 7-20 — Asia 深夜 / NY 引け後は除外)
4. Reclaim confirmation (直前バーが中心寄り)

Rollback: `VWAP_MR_V2=0` で旧挙動に戻す.

詳細: [[elite-freeing-patch-2026-04-24]]

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[elite-freeing-patch-2026-04-24]] — 本 patch の詳細分析
