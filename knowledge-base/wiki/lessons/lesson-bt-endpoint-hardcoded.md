# BT Endpoint Hardcoded --- BT endpoint hardcoded to USD_JPY

**発見日**: 2026-04-12 | **修正**: v8.5

## 何が起きたか
DTのBTエンドポイントがUSD_JPYにハードコードされていた。

## 根本原因
BT/本番統一原則においてペア・期間のパラメータ化が漏れていた。

## 教訓
BT/本番統一原則は「ペア・期間のパラメータ化」も含む。
