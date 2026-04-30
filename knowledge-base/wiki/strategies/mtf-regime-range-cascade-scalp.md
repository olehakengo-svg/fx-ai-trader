# mtf_regime_range_cascade_scalp

## Status: DISABLED (2026-04-30) — `enabled = False` (v1 retired, see retirement notes below)

range_tight regime での MR cascade。**実測根拠で発火停止**。

## 廃止理由 (rule:R3, ラベル実測クオンツ判定)

demo_trades.db (N=462) のラベル実測クエリで、range_tight regime での MR は **構造的に負け**:

| 戦略 × range_tight | N | WR% | Wilson_lo | EV (pips) |
|---|---|---|---|---|
| **bb_rsi_reversion** (継承元) | 8 | **12.5%** | 2.24% | -3.74 |
| **engulfing_bb** | 5 | 20.0% | 3.62% | -0.86 |
| **sr_channel_reversal** | 10 | **0.0%** | 0.00% | -3.20 |
| ema_trend_scalp (反対実装) | 23 | 26.1% | 12.55% | -1.26 |

→ 365 日 BT を回す前に enable を外す方がコスト効率が良い (rule:R3 Immediate)。  
→ moderate_trend (`mtf_regime_trend_cascade_scalp` v2) に edge を集約。

## コード保持理由

- 失敗時継続検証 (closure 短絡禁止) で「**別の range trigger**」を試す可能性:
  - `three_bar_reversal` 派生: 3連続陰線→陽線ブレイク
  - `vol_surge_detector` 派生: 出来高急増クライマックス反転
- 上記試行する場合は `enabled = True` に戻し、1m trigger 部を差替え。

## 元の設計仕様 (参考、enabled=True に戻す場合の仕様)

[詳細は廃止前バージョンに記載されていた仕様を参照]
- Layer 0: spread_gate
- Layer 1: regime == range
- Layer 2: M5 BB band touch + swing 近接
- Layer 3: bb_rsi_reversion 継承 (BB%B + RSI5 + Stoch + 確認足)
- SL 上限 12pip, RR floor Tier1=3.0/Tier2=2.5

## KB references
- knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md
- knowledge-base/wiki/strategies/bb-rsi-reversion.md (継承元、N=77 WR=36.4%)
- knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md (代替)

## Files
- `strategies/scalp/mtf_regime_range_cascade_scalp.py` (`enabled = False`)
