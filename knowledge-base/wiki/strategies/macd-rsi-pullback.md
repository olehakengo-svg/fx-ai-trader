# macd_rsi_pullback

## Status: PROPOSED (Pine-only, not yet deployed)
**現行**: TV Pine canonical 完成 / Python BT 未実装 / demo_trader 未統合 / Live トレードなし.
deploy agent 経由での QUALIFIED_TYPES 統合 + Shadow promotion を pending.

## 戦略要旨
bb_rsi_reversion の mean-reversion 哲学 (全 cell -EV) を放棄し、
**trend-following pullback** に再設計した後継戦略.

### Architecture
- **Base TF**: 1H (USD_JPY only)
- **Bias gate**: H1 RSI(14) ≥ 60 BUY / ≤ 40 SELL (sustained directional momentum)
- **Entry timing**: 1H RSI prev-bar in pullback zone (BUY 30-55 / SELL 45-70)
- **MACD confirm**: hist > 0 BUY / hist < 0 SELL (state filter, not event)
- **Pullback resumption**: rsi > rsi_prev BUY / rsi < rsi_prev SELL
- **Session gate**: London + NY (UTC 7-22)
- **Confirmation candle**: close > open BUY / close < open SELL
- **SL**: ATR(14) × 1.0
- **TP**: ATR(14) × 2.0 (RR=2.0, BEV_WR=33.3%)
- **ADX floor**: OFF (data-driven choice)

### Inspiration
H1 RSI directional bias is the same mechanism that gave xs_momentum_rsi its TV edge
(Config 3, [[xs-momentum-rsi-tv-phase2-2026-05-13]]).

## ★ 2026-05-14 TV 3.5y Discovery
USD_JPY 1H × OANDA friction (commission_percent 0.0068 = 2.14p RT):

| Config (H1 RSI gate) | N | WR% | PF | Net | MaxDD |
|---|---:|---:|---:|---:|---:|
| Loose 55/45 | 708 | 36.72 | 1.007 | +0.06% | 0.74% |
| **Canonical 60/40** | **196** | **39.29** | **1.161** | **+0.36%** | **0.39%** |
| High-conviction 65/35 | 58 | 43.10 | 1.327 | +0.21% | 0.18% |

詳細: [[../analyses/macd-rsi-pullback-h1-audit-2026-05-14]].

## Cross-pair (negative result)
USDJPY only — EUR_USD / GBP_USD / EUR_JPY all -EV at canonical config.

## TF (negative result)
15m all 3 configs -EV (WR 27-31%, PF 0.60). 1H is the canonical TF.

## Statistical robustness
- N=196 WR=39.29% Wilson_lo ≈ 32.6% (marginally below BEV 33.33%)
- → 3.5y TV BT is **suggestive but not Bonferroni-rigorous**
- Live N≥30 でゲート再判定する

## Promotion gates
| Stage | Criteria |
|---|---|
| Shadow (現在) | TV BT +EV 確認済み (本 audit) |
| Live promotion | Live N≥30, Wilson_lo > 33.3%, PF > 1.05, no regime cluster failure |
| Lot scaling | Live N≥60, sustained PF > 1.15 |

## Stop conditions (Rule 2)
- N=10 で Wilson_lo (WR) < 25% → 即停止
- N=20 で PF < 0.8 → 即停止
- N=30 で EV < -1.0p → 即停止

## Implementation status
- [x] Pine v5 canonical (`bt-results/tv-overlays/macd_rsi_pullback-replica.pine`)
- [x] TV 3.5y BT (USD_JPY 1H, 4 pairs, 6 configs)
- [x] Analysis doc (`wiki/analyses/macd-rsi-pullback-h1-audit-2026-05-14.md`)
- [ ] Python BT (`backtests/macd_rsi_pullback_full.py`)
- [ ] demo_trader signal function (`modules/demo_trader.py::signal_macd_rsi_pullback`)
- [ ] QUALIFIED_TYPES 統合 (deploy agent)
- [ ] tier-master entry (deploy agent)
- [ ] Live N=10 EV milestone
- [ ] Live N=30 Bonferroni gate

## Friction (USD_JPY)
- Spread 0.7p + Slip 0.5p = 2.14p RT (per [[friction-analysis]])
- Pine BT 内訳: `commission_type=strategy.commission.percent, commission_value=0.0068` per side

## Related
- [[../analyses/macd-rsi-pullback-h1-audit-2026-05-14]] — full audit
- [[bb-rsi-reversion]] — predecessor (PAIR_DEMOTED, philosophy 反転後継)
- [[xs-momentum-rsi]] — H1 RSI bias 同根の先行 Live 戦略
- [[../analyses/tv-pine-edge-discovery-framework]] — Pine canon 評価枠組み
- `bt-results/tv-overlays/macd_rsi_pullback-replica.pine`
