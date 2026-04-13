# Alpha Scan: 2026-04-13 (London Session)
**Source**: /api/demo/factors (本番データ, FX-only, non-shadow, post-cutoff)
**Total N**: 355

## 正EV候補 (sorted by EV, N≥5)

### 戦略×ペア
| Strategy | Pair | N | WR | EV | PF | Kelly | PnL | 判断 |
|----------|------|---|-----|-----|-----|-------|------|------|
| dt_bb_rsi_mr | USD_JPY | 5 | 80.0% | +3.080 | 3.48 | +57.0% | +15.4 | N不足、FORCE_DEMOTED |
| vol_momentum_scalp | USD_JPY | 12 | 66.7% | +1.275 | 1.96 | +32.7% | +15.3 | **★最有力候補** |
| ema_pullback | USD_JPY | 14 | 42.9% | +1.093 | 1.53 | +14.9% | +15.3 | FORCE_DEMOTED、PAIR_PROMOTED済 |
| ema_pullback | EUR_USD | 5 | 40.0% | +0.940 | 1.71 | +16.6% | +4.7 | N不足 |
| fib_reversal | USD_JPY | 26 | 34.6% | +0.785 | 1.47 | +11.1% | +20.4 | FORCE_DEMOTED、外れ値依存 |
| vol_surge_detector | USD_JPY | 21 | 47.6% | +0.157 | 1.10 | +4.2% | +3.3 | エッジ微弱 |

### 時間帯×ペア
| Hour | Pair | N | WR | EV | PnL | 判断 |
|------|------|---|-----|-----|------|------|
| H2 | USD_JPY | 13 | 38.5% | +2.154 | +28.0 | **★★ 東京序盤** |
| H15 | USD_JPY | 22 | 59.1% | +1.568 | +34.5 | **★★★ NY前半、最大PnL** |
| H1 | USD_JPY | 9 | 66.7% | +1.389 | +12.5 | ★ 東京オープン |
| H0 | USD_JPY | 5 | 60.0% | +0.780 | +3.9 | N不足 |
| H12 | USD_JPY | 8 | 37.5% | +0.812 | +6.5 | N不足 |

### 方向×レジーム
| Direction | Regime | N | WR | EV | PnL | 判断 |
|-----------|--------|---|-----|-----|------|------|
| SELL | TREND_BULL | 44 | 34.1% | +0.595 | +26.2 | **★ 逆張りショート** |
| BUY | RANGE | 71 | 43.7% | +0.308 | +21.9 | ★ レンジ内ロング |

## 毒性候補 (sorted by PnL damage)

| Factor | N | WR | EV | PnL | 即時アクション |
|--------|---|-----|-----|------|--------|
| SELL × RANGE | 89 | 27.0% | -1.636 | -145.6 | **最大毒性源。RANGE中のSELLを制限** |
| SELL × EUR_USD | 43 | 11.6% | -2.714 | -116.7 | **EUR_USD SELLをブロック** |
| BUY × USD_JPY | 117 | 34.2% | -0.638 | -74.7 | JPY BUYは全体で負 |
| BUY × TREND_BULL | 70 | 31.4% | -0.776 | -54.3 | トレンドフォローBUYが負 |
| H11 × EUR_USD | 9 | 22.2% | -4.489 | -40.4 | London中盤EUR壊滅 |
| H13 × USD_JPY | 14 | 28.6% | -2.486 | -34.8 | NY前USD_JPY壊滅 |

## クオンツ判断

### 即時アクション（BT不要）
1. **EUR_USD SELL ブロック**: N=43 EV=-2.714 → 止めるだけで+116.7pip回復
2. **RANGE中のSELL制限**: N=89 EV=-1.636 → 最大毒性源

### BT検証に載せるべき仮説
1. **H15×JPY (NY前半) に集中**: N=22 EV=+1.568 — 最大PnL、N十分
2. **H2×JPY (東京序盤) に集中**: N=13 EV=+2.154 — 最高EV
3. **SELL×TREND_BULL (逆張り)**: N=44 EV=+0.595 — 大サンプル
4. **vol_momentum_scalp×JPY のスケール**: N=12 EV=+1.275 Kelly=+32.7%

### 3因子深掘り結果 (2026-04-13 14:15 UTC追加)

**H15×JPY (EV=+1.568) の内訳:**
| Strategy | N | WR | EV | PnL |
|----------|---|-----|-----|------|
| vol_surge_detector | 3 | 100% | +2.667 | +8.0 |
| vol_momentum_scalp | 3 | 66.7% | +0.533 | +1.6 |
| bb_rsi_reversion | 9 | 33.3% | -0.911 | -8.2 |

→ **正EVはvol_surge_detectorの3連勝に依存。N不足で信頼不可。**

**H2×JPY (EV=+2.154) の内訳:**
| Strategy | N | WR | EV | PnL |
|----------|---|-----|-----|------|
| fib_reversal | 6 | 33.3% | +1.967 | +11.8 |
| bb_rsi_reversion | 4 | 50.0% | -0.150 | -0.6 |

→ **WR=33%なのにEV正 = 外れ値1-2回に依存。信頼不可。**

### 統計検定 (独立監査結果の引用)
- H15×JPY: t=1.23, p=0.23 → 有意でない
- H2×JPY: t=1.29, p=0.22 → 有意でない
- 多重検定補正後: いずれも生存しない

### 修正判断
- H15/H2の「正EVアルファ」は**偽陽性の可能性が高い**
- BT検証の優先度を**下げる** (N蓄積を待つ方が合理的)
- vol_momentum_scalp (N=12, EV=+1.275, 全時間帯) が依然として**唯一の信頼できる候補**
