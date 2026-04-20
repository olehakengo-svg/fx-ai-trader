# Stochastic Trend Pullback

## Status: FORCE_DEMOTED (全ペア強制 Shadow)

**Tier**: FORCE_DEMOTED | USD_JPY も PAIR_DEMOTED (明示)
**N(post-cut)**: 19 | **WR**: 31.6% | **EV**: -0.97 | **PnL**: -18.5pip (v8.9 forensics)

## 概要
Stochastic Oscillator + トレンドフォロー + プルバックの組み合わせ戦略。
One big winがPnLを歪めている。

## 現状
- FORCE_DEMOTED (v8.9): Post-cut N=19 WR=31.6% EV=-0.97 全ペアで負 → UNIVERSAL_SENTINEL から昇格剥奪
- PAIR_DEMOTED: USD_JPY (v8.9 alpha scan #2: N=23 WR=30.4% EV=-0.69 Kelly=-15.1%)
- 履歴: Previously _UNIVERSAL_SENTINEL (全モード 0.01lot 観測中) — One big win で見かけ上 +163pip だったが構造的負EV確定

## Related
- [[index]] — Tier 2 Sentinel
- [[edge-pipeline]] — Stage 4 (SENTINEL)
