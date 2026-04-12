# Edge Pipeline — エッジ仮説の評価フレームワーク

## Pipeline Stages

```
Stage 1: DISCOVERED   — 論文/観察からエッジ仮説を抽出
Stage 2: FORMULATED   — 数学的定義（エントリー/SL/TP条件式）
Stage 3: BACKTESTED   — 摩擦モデルv2でBT、N>=30、WFO/MC検定
Stage 4: SENTINEL     — 本番0.01lotで稼働、N蓄積中
Stage 5: VALIDATED    — 本番N>=50、Kelly>0、PF>1確認
Stage 6: PROMOTED     — フルロット稼働、PAIR_PROMOTED
```

## Evaluation Criteria (Stage 2 → 3 Gate)

### 必須条件
- [ ] 学術論文に根拠あり（peer-reviewed or established reference）
- [ ] 既存戦略との相関 |r| < 0.5（独立したアルファ）
- [ ] 摩擦耐性: BEV_WR - 期待WR >= 10pp（十分なマージン）
- [ ] 15m以上のTF（1mスキャルプの摩擦/SL比=43-71%は構造的に危険）
- [ ] 最低RR >= 1.2

### ボーナス条件
- [ ] 複数TFで有効（15m + 1H）
- [ ] 複数ペアで有効（USD_JPY + EUR_USD + GBP_USD）
- [ ] 市場レジームに依存しない（RANGE + TREND両方）

## Current Edge Inventory

### Stage 6: PROMOTED
| Edge | Strategy | Paper | Kelly |
|------|----------|-------|-------|
| BB extreme MR × USD_JPY | [[bb-rsi-reversion]] | Lo & MacKinlay 1988 | ~0% (thin edge) |
| ORB fakeout reversal | [[orb-trap]] | Bulkowski 2005 | insuff (N=2) |

### Stage 4: SENTINEL
| Edge | Strategy | Paper | Status |
|------|----------|-------|--------|
| Volume momentum breakout | [[vol-momentum-scalp]] | Jegadeesh & Titman 1993 | N=10, WR=80% |
| Liquidity sweep reversal | [[liquidity-sweep]] | Osler 2003 | N=0, just deployed |
| Fib pullback (improved) | [[fib-reversal]] | - | N=32, WR=40.6%, recovery path |

### Stage 1: DISCOVERED (not yet formulated)
| Edge Hypothesis | Source | Potential |
|----------------|--------|-----------|
| [[dealer-inventory-rebalance]] | Lyons 1995 | Dealers offset risk at session boundaries → predictable flows |
| [[carry-unwind-detection]] | Brunnermeier 2008 | JPY carry trade unwinding creates sharp reversals |
| [[fix-flow-exploitation]] | Evans & Lyons 2002 | London/NY fix creates temporary price distortions |
| [[weekend-gap-mean-reversion]] | Bollen & Inder 2002 | Monday opening gaps mean-revert within first session |
| [[volatility-regime-switch]] | Hamilton 1989 | Markov regime switching for vol prediction |
| [[regression-channel-mr]] | O-U process | Price mean-reverts within trend channels (lin_reg_channel 1H redesign) |

## Related
- [[research/index]] — Full paper index
- [[friction-analysis]] — Friction constraints on edge viability
- [[independent-audit-2026-04-10]] — Audit constraints on new strategy deployment
