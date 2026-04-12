# BT Before Deploy --- Always BT before deploy

**発見日**: - | **修正**: -

## 何が起きたか
6つの新エッジ戦略をBTなしでSentinelにデプロイした。

## 根本原因
正しいフローは 実装 → BT → BT結果で判断 → デプロイ。Edge Pipeline Stage 2 → 3のGateが飛ばされた。

## 教訓
Edge Pipeline Stage 2 → 3のGateを飛ばさない。
