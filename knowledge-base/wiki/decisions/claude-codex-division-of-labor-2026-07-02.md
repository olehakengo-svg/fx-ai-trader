# Claude/Codex 役割分担基準 + レビューゲート必須化 (2026-07-02)

**Rule**: R3（プロセス構造欠陥の修正 — 統計検定不要、evidence は運用実測）
**決裁**: user 承認 2026-07-02（「進めて」）
**背景セッション**: [[sessions/2026-07-02-session]]

---

## 発見された構造欠陥（evidence）

1. **幽霊タスク**: KB/roadmap 上「Codex task pending」とされていた watchdog Bearer 修正が、`.ai/tasks/queue/` に実タスクとして存在しなかった。queue は 2026-05-05 の `_paused_v3_for_v2` 凍結（~70件）以降アクティブ0件、最終完了は 2026-06-12。この間に DD は 81%→98.2% へ悪化。
2. **レビュー非対称**: Claude→実装→Codex 自動レビュー（plugin）は機能しているが、Codex→実装→Claude レビュー（`/fx-review-result`）は任意実行で、done 移動に強制力がなく証跡も残らない。
3. 共通パターン: **「やったことになっている」記録と「実際にやった」状態の機械的整合チェック不在**（教訓「自動生成KBと手書きKBは機械的整合チェックで固定する」と同型）。

## 役割分担基準（本決定）

| タスク種別 | 担当 | 根拠 |
|---|---|---|
| R2/R3 止血・構造バグ・判断を伴う変更 | **Claude 直接**（Codex queue に入れない） | 必要レイテンシ=時間単位。queue 実測レイテンシは凍結時∞。クオンツ判断は CLAUDE.md 上 Claude の責務 |
| 仕様固定可能な大型実装・長時間BT・forensic | **Codex queue** | 実績 278 done / 33 failed（~89%）。T2/T3 型の成功パターン |
| コードレビュー（Claude 実装分） | Codex（自動、継続） | CLAUDE.md 既定 |
| Codex 実装分のレビュー | **Claude（必須化 — 下記ゲート）** | 本決定 |
| クオンツ判断・tier 変更・KB 更新 | Claude 専任（委譲禁止） | 判断一貫性 + KB 整合 |
| 資本に触る決裁（LIVE 停止/再開・lot・昇格） | user | — |

## レビューゲート（必須化）

1. **done 移動条件**: `.ai/tasks/done/<task>.md` へ移動する前に、対応する **`review.md`**（`.ai/runs/<run>/review.md` または task md 内 `## Claude Review` セクション）が存在すること。内容: verdict (accept/rework) + git diff 実 verify + テスト再実行結果。
2. **レビュー独立性**: Codex の final.md 自己報告を読むだけのレビューは禁止。git diff + テスト再実行 + （本番影響がある場合）本番挙動確認で行う（stash leak 教訓 2026-05-11 の一般化）。
3. **機械的検出**: 「review 記録なしの done」「KB 上 pending だが queue に実体なし（幽霊タスク）」を日次ループの整合チェックに追加する。
4. **SLA**: queue 投入済み R3 タスクが 3 日未処理なら Discord アラート → Claude 直接実行にフォールバック。

## 運用ループへの反映

- 日次ループ: Codex 非依存で構築（guard 監査 / R2 止血評価 / N 進捗 / 整合チェック）
- 週次ループ: エッジ解析シリーズ・R1 BT のみ Codex に委譲（queue 再稼働後）
- queue 再稼働は「幽霊タスク検出 + レビューゲート」整備後に別途 user 決裁

## 関連

- [[claude-harness-design]] — Claude の判断規律本体（本ページはその補遺）
- [[audit-completion-protocol]] — 監査 completion 追跡（同じ「記録⇄実体」整合思想）
- 教訓ページ化: 幽霊タスクは lesson 候補（本ページで代替、再発時に lessons/ へ昇格）
