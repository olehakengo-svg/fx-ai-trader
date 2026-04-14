# Massive API固有α スキャン結果 (2026-04-14)

**データ**: Parquetキャッシュ (6ペア × 4TF, 53万バー)
**検定**: Bonferroni + Benjamini-Hochberg補正、摩擦込みBT

---

## DT (15m/1h) — 816仮説 → Bonferroni 70件 / BH 98件

### 摩擦込み STRONG (fWR≥55%, fEV>0)

| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | 年間PnL |
|---|---|---|---|---|---|---|---|
| VW2σ BUY | EUR_JPY | 15m | 8b(2h) | 737 | 55.8% | +2.54 | +1,869p |
| VW2σ BUY | EUR_JPY | 15m | 16b(4h) | 737 | 55.8% | +3.85 | +2,837p |
| VW2σ BUY | EUR_JPY | 1h | 16b | 226 | 58.0% | +6.32 | +1,428p |
| VW2σ BUY | GBP_JPY | 15m | 4b(1h) | 740 | 55.7% | +0.42 | +313p |
| VW2σ BUY | GBP_JPY | 15m | 8b(2h) | 740 | 56.9% | +2.56 | +1,893p |
| VW2σ BUY | GBP_JPY | 15m | 16b(4h) | 740 | 56.2% | +5.17 | +3,827p ★★ |
| VW2σ BUY | GBP_JPY | 1h | 16b | 245 | 56.3% | +13.4 | +3,290p |
| VW2σ BUY | GBP_JPY | 5m | 16b | 357 | 56.9% | +2.43 | +866p |
| VW2σ BUY | USD_JPY | 15m | 16b(4h) | 705 | 55.0% | +2.98 | +2,099p |
| VW2σ BUY | USD_JPY | 5m | 16b | 343 | 56.0% | +1.36 | +465p |

### Friction-Kill: EUR_GBP (rawWR=84% → fWR=14%)

EUR_GBP 1m: 摩擦=2.5pip ≈ ATR×100%。構造的に不可能確定。

---

## Scalp (1m/5m) — 564仮説 → Bonferroni 4件 / BH 7件

### 摩擦込み全BH通過 (fEV>0のみ、friction-kill=0件)

| Edge | Pair | TF | Hold | N | fWR | fEV(pip) | 年間PnL | 補正 |
|---|---|---|---|---|---|---|---|---|
| VW2σ BUY | EUR_JPY | 1m | 2min | 2,576 | 57.2% | +0.47 | +1,221p | Bonf |
| VW2σ BUY | EUR_JPY | 1m | 4min | 2,576 | 57.2% | +0.51 | +1,316p | Bonf |
| VW2σ BUY | EUR_JPY | 1m | 8min | 2,576 | 55.8% | +0.64 | +1,658p | Bonf |
| VW2σ BUY | EUR_JPY | 1m | 16min | 2,574 | 56.5% | +0.81 | +2,087p | Bonf |
| VW2σ BUY | GBP_JPY | 1m | 8min | 2,028 | 54.1% | +0.35 | +713p | BH |
| VW2σ BUY | GBP_JPY | 1m | 16min | 2,028 | 53.6% | +0.48 | +975p | BH |
| VW2σ BUY | GBP_JPY | 5m | 80min | 357 | 58.5% | +2.93 | +1,044p | BH |

---

## Bonferroni有意 新戦略 (174仮説, 15m足)

| Edge | Pair | N | WR | p-value |
|---|---|---|---|---|
| H21 BUY | EUR_USD | 1,022 | 58.9% | <10⁻⁷ |
| H20 SELL | GBP_USD | 1,016 | 57.8% | <10⁻⁷ |
| H17 BUY | USD_JPY | 1,028 | 57.3% | 10⁻⁶ |
| H20 SELL | USD_JPY | 1,016 | 57.3% | 2×10⁻⁶ |
| 5streak BUY | USD_JPY | 586 | 58.7% | 1.3×10⁻⁵ |
| VW2σ BUY | GBP_USD | 831 | 56.9% | 3.3×10⁻⁵ |
| VW2σ BUY | USD_JPY | 705 | 57.4% | 3.8×10⁻⁵ |

---

## 実装済み戦略

- ny_close_reversal (UTC 20-22 directional bias)
- streak_reversal (3-5 consecutive candle reversal)
- vwap_mean_reversion (VWAP-2σ MR, Massive API exclusive)
  - DT: EUR_JPY/GBP_JPY 15m PAIR_PROMOTED + 1.8x LOT_BOOST
  - Scalp: EUR_JPY 1m Bonferroni通過、追加設定不要（既存実装で発火）

## Related
- [[roadmap-v2.1]] — DT幹+Scalp枝統合ポートフォリオ
- [[friction-analysis]] — ペア別摩擦
