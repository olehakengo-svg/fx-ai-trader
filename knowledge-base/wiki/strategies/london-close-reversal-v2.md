# London Close Reversal v2 (LCR v2)

## Overview
- **Entry Type**: `london_close_reversal_v2`
- **Category**: Session microstructure / MR (reversal)
- **Timeframe**: 5m (primary), 15m (secondary auto-scaling)
- **Status**: UNIVERSAL_SENTINEL (新規登録 2026-04-22)
- **Active Pairs**: 全ペアShadow（主要検証対象: EUR_USD, GBP_JPY, GBP_USD）

## 仮説 (H-2026-04-22-005)
UTC 20:30-21:00 (ユーザー定義 London close 前30分) に日中トレンドのポジション調整が集中し、過剰方向への短期push(>0.8ATR)がRSI極値(>68/<32)と同時発生した場合、反転エッジが生じる。

## 学術根拠
- Hau (2001) FX order flow and price impact
- Ito & Hashimoto (2006) intraday FX seasonality
- Melvin & Prins (2015) London fixing flow reversal

## BT Performance (5m, 183日)
| Pair | N | WR | PF | EV_R_fric | Wilson CI | WF3 | Kelly_half | 判定 |
|---|---|---|---|---|---|---|---|---|
| EUR_USD 5m | 37 | 51.4% | 1.62 | +0.22 | [35.9, 66.5] | × (1/3正) | 0.108 | Sentinel ✓ |
| GBP_USD 5m | 25 | 60.0% | 2.45 | +0.52 | [30.6, 86.3] | × (2/3正) | 0.178 | Sentinel △ (N<30) |
| GBP_JPY 5m | 34 | 44.1% | 1.29 | +0.064 | [28.9, 60.6] | × (2/3正) | 0.050 | Sentinel ✓ |
| EUR_JPY 5m | 24 | 37.5% | 0.98 | -0.128 | [21.2, 57.3] | × | -0.004 | 棄却 |
| EUR_USD 15m | 7 | 42.9% | 1.16 | -0.015 | [15.8, 75.0] | × | 0.040 | N不足 |
| GBP_USD 15m | 8 | 62.5% | 2.73 | +0.597 | [30.6, 86.3] | ✓ | 0.198 | N不足 |

Bonferroni α (18検定) = 0.0028 → いずれも未達

## Live Performance (post-cutoff)
未開始 (2026-04-22 Sentinel登録)

## Signal Logic
1. UTC 20:30-21:00 のみエントリー検討
2. 直近30分 (5m=6bars, 15m=2bars) の `Close[i] - Close[i-N]` が `|push| > ATR × 0.8`
3. push > 0 & RSI14 > 68 → SELL (overbought fade)
4. push < 0 & RSI14 < 32 → BUY (oversold fade)
5. ATR-spike フィルター: 直近 2N bars の最大 bar_range が baseline(20bar ATR median) × 2.5 を超えた場合スキップ (news proxy)
6. 金曜 UTC は逆効果(ポジション解消)でブロック
7. TP = ATR × 1.8, SL = ATR × 1.1 (RR=1.64)

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none
- strategy_type: "reversal" → ADX>25で conf penalty (Kyle 1985型 MR)

## Promotion基準 (pre-registered 2026-04-22)

### Tier1 → Tier2 (SCALP_SENTINEL → PAIR_PROMOTED)
全条件:
- Live N ≥ 30 (BT合算不可)
- Wilson 95% CI下限 > BEV_fric
- Sharpe_trade > 0.25
- Kelly_half ≥ 0.10

### 昇格候補ペア
1. **GBP_USD 5m** (最有望, Kelly_half=0.178 BT) — Live N≥30で即審査
2. **EUR_USD 5m** (second, Kelly_half=0.108)
3. **GBP_JPY 5m** (第三, Kelly_half=0.050)

### 60日後(2026-06-21)の判定
- Live N<30 かつ EV<0 なら戦略登録抹消
- Live N≥30 で Tier2基準非達なら別仮説へピボット

## Related
- [[pre-registration-2026-04-22]] — Live昇格binding基準
- [[feedback_partial_quant_trap]] — 判定プロトコル
- [[session-time-bias]] — 既存の session戦略 (ELITE_LIVE、直交性確認)
- 原戦略 [[london-close-reversal]] (UTC 15:00-16:15 wick-based) — 別アルゴリズム、併存
