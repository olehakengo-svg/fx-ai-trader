# Decisions Index — 重要判断の記録

## 目的
トレーディングシステムに影響を与える重要判断を構造化して記録する。
「なぜその判断をしたか」を振り返り可能にし、同じ議論の繰り返しを防ぐ。

## 記録基準（いつ decision を作るか）
1. **戦略のTier変更**: PROMOTED, DEMOTED, FORCE_DEMOTED, 停止/復活
2. **パラメータ変更**: SL/TP/スコア閾値の変更（カーブフィッティング禁止ルール関連）
3. **アーキテクチャ変更**: 新モジュール追加、モード追加/削除
4. **監査・レビュー結果**: 外部/独立監査の勧告とその受諾/却下
5. **リスクポリシー変更**: DD防御、ロットサイズ、Kelly導入

## セッションログでの Decision タグ
セッション中の重要判断を `[DECISION: ...]` タグで記録する:
```
[DECISION: bb_rsi×EUR_JPYをDEMOTE — N=15でWR=26.7%, BEV未達]
[DECISION: v8.9 Equity Reset実施 — XAU損失+pre-cutoffデータがDD計算を汚染]
```
PreCompact hookがこのタグを検出し、decision ページ作成を提案する。

## Decision Pages
- [[independent-audit-2026-04-10]] — 独立監査（macdh吸収REJECT, bb_rsi保護最優先）
- [[academic-audit-2026-04-12]] — 学術研究サーベイ結果（25論文→6新エッジ）
- [[xau-stop-rationale]] — XAU全面停止の根拠

## Related
- [[lessons/index]] — 間違いから学んだ教訓
- [[changelog]] — バージョン別変更タイムライン
- [[edge-pipeline]] — 戦略のStage管理
