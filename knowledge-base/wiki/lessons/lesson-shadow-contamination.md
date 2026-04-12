# Shadow Contamination --- Shadow trade polluting stats

**発見日**: 2026-04-10 | **修正**: v8.4

## 何が起きたか
get_stats()がShadowトレードを含めてWR/EVを算出していた。

## 根本原因
is_shadow=0フィルターが欠如していた。

## 教訓
統計を出す前に「このデータに何が含まれているか」を常に確認する。
