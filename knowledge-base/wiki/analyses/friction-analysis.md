# Friction Analysis

## Per-Pair Friction (RT = Round Trip)
| Pair | Spread | Slippage | RT Friction | BEV_WR | Notes |
|------|--------|----------|-------------|--------|-------|
| USD_JPY | 0.7pip | 0.5pip | **2.14pip** | 34.4% | Most efficient |
| EUR_USD | 0.7pip | 0.5pip | **2.00pip** | 39.7% | |
| GBP_USD | 1.3pip | 1.0pip | **4.53pip** | 37.9% | Limit-only enforced |
| EUR_JPY | 1.0pip | 0.5pip | **2.50pip** | 33.7% | |
| EUR_GBP | 1.5pip | - | **~3.0pip** | 57.1% | **STRUCTURALLY IMPOSSIBLE** (stopped) |
| XAU_USD | 86pip | 46pip | **217.5pip** | ~35% ATR-rel | **STOPPED v8.4** |

## Aggregate Friction
- Pre-v8.4: avg 7.04pip/trade (XAU-distorted)
- Post-v8.4 (FX only): est. 2.5-3.5pip/trade

## Key Insight: XAU Was 102% of Post-Cutoff Loss
```
Post-cutoff 237 trades:
  XAU loss:  -2,280pip
  FX profit: +96.8pip
  Total:     -2,183pip
```
XAU stop alone flips the system from deep loss to marginal profit.

## Friction by Session
| Session | Avg Slippage | Avg Spread | Total (全体) | FX-only推定 |
|---------|-------------|-----------|-------------|------------|
| London | 0.31pip | 0.55pip | **0.86pip** (best) | ~0.86pip |
| Tokyo | 1.04pip | 2.10pip | **3.14pip** | ~2.5pip |
| New York | 2.48pip | 4.82pip | **7.30pip** | ~2.0pip |

> **注**: Total列はXAU込み（v8.4以前データ）。FX-only推定はXAUトレード除外後の概算値。
> NY sessionのTotal=7.30pipはXAU(spread~86pip)に大きく歪められている。

## Tier 1 BT Validation (2026-04-21)

摩擦係数更新 (commit a22fa14) 後の BT 検証:

| Pair | 期間 | TF | N | WR | EV | 備考 |
|---|---|---|---|---|---|---|
| USD_JPY | 7d | 1m | 136→114 | 57.4%→55.3% | -0.240→-0.318 | **Scalp: Live 方向 ✓** |
| USD_JPY | 365d | 15m | — | 63.1%→63.0% | +0.407→+0.391 | DT: 変化微小 (予想通り) |
| GBP_USD | 7d | 1m | 93 | 40.9% | -0.882 | after only (before 未計測) |
| EUR_USD | 7d | 1m | 67 | 55.2% | -0.308 | after only (before 未計測) |

**Tier 1 評価**: USD_JPY で Scalp BT が Live 方向に移動 ✅。GBP_USD/EUR_USD は "after" のみで before/after 比較未実施。
Tier 2 (session-of-day spread テーブル) は P1 として継続。

## Related
- [[bb-rsi-reversion]] (edge=0.45pip vs friction 2.14pip)
- [[xau-stop-rationale]]
- [[independent-audit-2026-04-10]] (摩擦削減が最優先勧告)
