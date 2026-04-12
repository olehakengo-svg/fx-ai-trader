# Gotobi Fix — 五十日仲値USD/JPY

## Stage: SENTINEL (v8.5, 発火窓=月6日 N蓄積中)

## Hypothesis
毎月5,10,15,20,25,30日の9:55 JST（仲値）に向けてUSD/JPYが上昇。日本企業の輸入決済のドル買い需要集中が原因（Bessho et al 2023, Ito & Yamada 2017）。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[bessho-2023]] | 五十日の9:55向けUSD/JPY上昇。企業決済慣行がメカニズム | ★★★★ |
| [[ito-yamada-2017]] | 東京Fix顧客注文は外貨買いに偏向。銀行pricing biasも確認 | ★★★★ |
| 既存: tokyo_nakane_momentum | Andersen 2003ベースの仲値戦略が既にシステム内に存在 | ★★★ |

## Quantitative Definition
```python
# 五十日判定: day in {5, 10, 15, 20, 25, 30} (月末は30 or 月末日)
# Entry: 8:45 JST (UTC 23:45) にUSD/JPY BUY
# Exit: 10:00 JST (UTC 01:00) — 仲値直後
# SL: 20pip
# TP: 10-15pip
# Filter: 前日USD/JPYが大幅下落(-50pip超)の場合は見送り
# 月曜/金曜除外（tokyo_nakane_momentumと同一）
```

## Friction Viability
| Pair | Friction(RT) | Est. SL | Friction/SL | BEV_WR | Est. WR |
|------|-------------|---------|-------------|--------|---------|
| USD_JPY | 2.14pip | 20pip | 10.7% | ~57% | 60-70% (文献値) |

## Correlation with Existing
| Strategy | Expected r | Basis |
|----------|-----------|-------|
| tokyo_nakane_momentum | **高** (r>0.7推定) | 同一時間帯・同一方向 → 統合すべき |
| bb_rsi | 低 | 別メカニズム |

## Key Risk
- アノマリー認知度上昇で効果逓減の可能性（Bessho 2023で指摘）
- tokyo_nakane_momentumとの冗長性 → 統合が最適

## Implementation Path
- [x] Stage 1: DISCOVERED
- [ ] Stage 2: tokyo_nakane_momentumに五十日フィルターを追加する形で統合
- [ ] Stage 3: BT (五十日 vs 非五十日のリターン差を統計検定)

## Related
- [[session-effects]]
- [[research/index]]
