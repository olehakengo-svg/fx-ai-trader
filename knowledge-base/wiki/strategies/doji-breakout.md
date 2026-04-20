# Doji Breakout

## Status: UNIVERSAL_SENTINEL + PAIR_PROMOTED (GBP_USD, USD_JPY)

**Stage**: 4 (SENTINEL) | **Version**: v8.8 → PAIR_PROMOTED v2.1

現行: 全モード UNIVERSAL_SENTINEL (最小ロット観測) + GBP_USD / USD_JPY は PAIR_PROMOTED で実弾通過。

| ペア | 状態 | BT (365d) |
|---|---|---|
| GBP_USD | PAIR_PROMOTED | N=23 WR=78.3% EV=+0.724 PF=2.47 |
| USD_JPY | PAIR_PROMOTED | N=21 WR=61.9% EV=+0.338 PF=1.40 |
| EUR_USD | UNIVERSAL_SENTINEL (Shadow) | — |

## 概要
3連続dojiパターン検出 → ブレイクアウトフォロー。
Doji（始値≈終値）の連続は方向の不確実性蓄積を示し、ブレイクアウトの前兆。

## BT結果
- JPY: N=8 WR=0% — 現時点ではエッジ未確認
- Sentinel蓄積中

## Related
- [[edge-pipeline]] — Stage 4
- [[raw-alpha-mining-2026-04-12]] — 発見経緯
