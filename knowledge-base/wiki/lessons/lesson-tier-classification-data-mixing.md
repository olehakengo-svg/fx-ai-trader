# Tier Classification Data Mixing --- Pair-level eval needed

**発見日**: 2026-04-10 | **修正**: -

## 何が起きたか
bb_rsiを全ペア混合でWR=44.3% → Tier 3に分類された。

## 根本原因
USD_JPY限定ではWR=54.7% PF=1.13 → Tier 1相当だった。ペア混合により正エッジが相殺されていた。

## 教訓
ペア x 戦略の粒度で評価しないと相殺される。
