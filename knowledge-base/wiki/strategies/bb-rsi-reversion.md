# bb_rsi_reversion

## Status: Tier 1 (PAIR_PROMOTED x USD_JPY)
**The only strategy with PF > 1 in 556t production audit.**

## Performance History
| Period | N | WR | PnL | PF | Notes |
|--------|---|-----|-----|-----|-------|
| Pre-cutoff (all) | 212 | 44.3% | -274.2 | <1 | All pairs mixed |
| Pre-cutoff (USD_JPY) | 123 | 54.7% | +54.8 | 1.13 | **Only PF>1** |
| Post-cutoff (shadow-excluded) | 77 | 36.4% | -42.2 | - | v8.4 shadow filter applied |
| BT (v3.2, 7d) | 181 | 61.3% | - | - | EV=+0.173 ATR |

## v8.3 Changes (2026-04-10)
- Added confirmation candle: `ctx.entry > ctx.open_price` (BUY) / `< open` (SELL)
- Counter-trend filter: TREND_BULL blocks SELL, TREND_BEAR blocks BUY
- ADX floor: JPY ADX < 15 -> return None
- **Expected**: instant death 77.6% -> 20-25%, WR -> 58-62%
- **Status**: OOS verification pending (data accumulating)

## MAFE Profile
- WIN: avg MAE=1.1pip, avg MFE=3.7pip (entry precision ratio=3.36)
- LOSS: avg MAE=3.2pip (=SL), avg MFE=0.3pip (instant death)
- 77.6% of losses have MFE=0 (never favorable)

## Friction
- USD_JPY: spread 0.7 + slip 0.5 = 2.14pip RT
- BEV_WR = 34.4%
- Edge = 0.45pip/trade (extremely thin)

## Key Risk
- Post-cutoff WR=36.4% is only 2pp above BEV_WR=34.4%
- Independent audit warning: "edge could vanish with slight spread increase"
- v8.3 confirmation candle effect is UNVERIFIED

## v9.3 P2: REGIME_ADAPTIVE Family (2026-04-17)

本戦略は **regime 方向で family 挙動が反転** する非対称性を持つため、
`research/edge_discovery/strategy_family_map.py::REGIME_ADAPTIVE_FAMILY` で
regime 別に family をオーバーライドする。

### 観測された非対称性 (Phase C N=324, P0 forensics)

| Regime | BUY WR | SELL WR | 差 | 実挙動 |
|---|---|---|---|---|
| `trend_up_weak`/`_strong` | **55%** | 50% | +5pp | **TF** (順張り BUY が aligned) |
| `trend_down_weak`/`_strong` | **44%** | 23% | +21pp | **MR** (逆張り BUY = fade 下落が aligned) |
| `range_tight`/`_wide` | — | — | — | default **MR** (両方向 BUY aligned) |

`trend_down` における BUY WR > SELL WR (差 +21pp) は特に強いシグナル.
「下落中に拾う」MR 挙動が顕著で、単一 family 分類では取りこぼすエッジ。

### 現行マッピング

```python
REGIME_ADAPTIVE_FAMILY["bb_rsi_reversion"] = {
    "trend_up_weak": "TF",
    "trend_up_strong": "TF",
    "trend_down_weak": "MR",
    "trend_down_strong": "MR",
    # range_* は override せず default MR
}
```

### 効果 (Phase C OOS データ再実行)

- LIVE ΔWR (aligned vs conflict): +2.4pp → **+9.3pp (4×)**
- IS aligned − conflict WR gap: **+12.0pp**
- IS/OOS 全 family 符号一致維持 (curve-fit 耐性保持)

### 運用

v9.3 Phase D hash-based A/B routing (`gate_group = mtf_gated`) 下で、
本戦略の conflict alignment トレードは LIVE→SHADOW downgrade される。
Group B (`label_only`) では従来通り LIVE 実行 → 並走で gate 効果を直接測定。

## Related
- [[friction-analysis]]
- [[mfe-zero-analysis]]
- [[independent-audit-2026-04-10]]
- [[mtf-regime-validation-2026-04-17]] §C (P0 forensics) / §E (REGIME_ADAPTIVE)
