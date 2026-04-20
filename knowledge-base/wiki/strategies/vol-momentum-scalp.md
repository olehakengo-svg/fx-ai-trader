# vol_momentum_scalp

## Status: PAIR_PROMOTED x EUR_JPY (他ペアは Phase0 Shadow)
**現行**: EUR_JPY のみ PAIR_PROMOTED (5m: EV=+0.608 N=34 STRONG)。LOT_BOOST 1.0x (v8.2 で 2.0x→1.0x 摩擦後 EV 境界的のためデータ蓄積優先)。他ペアは ELITE/PP 未所属で Phase0 Shadow Gate。
**0% instant death rate — system benchmark for entry quality.**

**履歴**: Previously SHADOW (v2.1: BT N=87 EV=-0.014 negative, Live WR=80% was N=10 luck)。以降 EUR_JPY 5m STRONG シグナル確認で PAIR_PROMOTED。

## Performance
| Period | N | WR | PnL | Kelly |
|--------|---|-----|-----|-------|
| Post-cutoff (shadow-excl) | 16 | 50.0% | +4.2 | — |
| Post-cutoff early (N=10) | 10 | 80.0% | +21.6 | 47.0% (CI: [-9.9%, +81.1%]) |
| BT (Scalp v3.2) | 11 | 63.6% | - | EV=+1.61 |

## Why 0% Instant Death (Benchmark)
Entry requires ALL of:
1. ADX >= 25 (strong trend confirmed)
2. +DI > -DI, gap >= 8 (directional force)
3. Close > Open (bullish candle — **confirmation**)
4. BB%B >= 0.90 (already extended — momentum entry)
5. BB width pct > 45% (volatility present)

Key difference from bb_rsi (77.6% instant death):
- vol_momentum enters on **confirmed momentum**, not anticipated reversal
- Requires **existing trend** (ADX>=25), not any environment
- **Candle body confirmation** before entry

## Independent Audit Warning
- N=11: Kelly CI = [-9.9%, +81.1%] — "Kelly discussion meaningless at N=11"
- BOOST was 2.0x → reduced to 1.0x (v8.2)
- Need N>=50 for reliable Kelly estimate

## Friction
- Entry precision ratio: high (MFE=4.39 on wins, MAE=1.7 on losses)
- Friction 2.14pip vs edge ~1.61pip → marginal (needs monitoring)

## Related
- [[mfe-zero-analysis]] — Benchmark: 0% instant death
- [[bb-rsi-reversion]] — Comparison: 77.6% instant death
- [[friction-analysis]] — Friction/edge ratio concern
- [[independent-audit-2026-04-10]] — Kelly CI warning
