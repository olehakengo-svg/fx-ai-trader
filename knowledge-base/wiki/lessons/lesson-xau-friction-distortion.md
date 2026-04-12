# XAU Friction Distortion --- XAU distorting avg friction

**発見日**: 2026-04-10 | **修正**: v8.4

## 何が起きたか
avg_friction=7.04pip → 「全戦略フリクション負け」と誤解された。

## 根本原因
FX-only=2.14pip, XAU=217.5pip。XAUが平均を30倍に歪めていた。

## 教訓
集計値は必ずセグメント分解する。平均値は嘘をつく。
