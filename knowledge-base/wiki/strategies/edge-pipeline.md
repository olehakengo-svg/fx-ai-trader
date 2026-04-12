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
| Session time bias × 3ペア | [[session-time-bias]] | Breedon & Ranaldo 2013 | insuff (N蓄積中) |
| London fix reversal × GBP | [[london-fix-reversal]] | Krohn 2024 | insuff (N蓄積中) |

### Stage 4: SENTINEL
| Edge | Strategy | Paper | Status |
|------|----------|-------|--------|
| Volume momentum breakout | [[vol-momentum-scalp]] | Jegadeesh & Titman 1993 | N=10, WR=80% |
| Liquidity sweep reversal | [[liquidity-sweep]] | Osler 2003 | N=0, deployed |
| Fib pullback (improved) | [[fib-reversal]] | - | N=32, WR=40.6%, recovery path |
| Vol spike mean-reversion | [[vol-spike-mr]] | Osler 2003 | v8.8: BT JPY PF=1.92★, N蓄積中 |
| Doji breakout follow | [[doji-breakout]] | Mandelbrot 1963 | v8.8: BT JPY PF=1.28, N蓄積中 |
| Gotobi fix USD/JPY BUY | [[gotobi-fix]] | Bessho 2023 | v8.5: 発火窓=月6日, N蓄積待ち |
| VIX carry unwind | [[vix-carry-unwind]] | Brunnermeier 2009 | v8.5: 低頻度(年2-5回), N蓄積待ち |
| XS momentum + dispersion | [[xs-momentum-dispersion]] | Menkhoff 2012 | v8.5: JPY PAIR_DEMOTED |
| HMM regime filter | [[hmm-regime-overlay]] | Nystrup 2024 | v8.5: 防御オーバーレイ |

**Priority C — 保留/棄却**
| Edge | Status | Reason |
|------|--------|--------|
| Vol smile forecasting | REJECTED | 機関データ必要 |
| NLP news spillover | REJECTED | NLPインフラ過大 |
| Dealer inventory | THEORETICAL | リテールでフロー情報なし |
| Weekend gap MR | WEAK | 1990年代以降効果消失 |
| regression-channel-mr | REJECTED (audit) | 独立監査で棄却 |

## Related
- [[research/index]] — Full paper index
- [[friction-analysis]] — Friction constraints on edge viability
- [[independent-audit-2026-04-10]] — Audit constraints on new strategy deployment
