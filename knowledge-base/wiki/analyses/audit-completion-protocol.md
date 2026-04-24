# Audit Completion Protocol

> **監査後の完了追跡フロー定義.** 監査を実施したら、各 action item の完了状態を都度 KB に
> write する. 監査は「判断点のスナップショット」であり、放置すると `lesson-reactive-changes`
> と同じく形骸化する.

## 1. 対象

以下のいずれかが開始された時に本プロトコルを適用:
- 外部監査 (`wiki/decisions/external-audit-YYYY-MM-DD.md`)
- 独立監査 (`wiki/decisions/independent-audit-YYYY-MM-DD.md`)
- 内部 post-incident review
- pre-registration による major phase 判定

## 2. 必須構造: Audit ドキュメントの §5

監査ドキュメントには **§5 "Action Items (tracked)"** を必ず含める.
最小 schema:

```markdown
| # | Action | Owner | Status | Evidence |
|---|--------|-------|--------|----------|
| A1 | <具体 action> | Claude/User/Market | ⏳ PENDING | <まだ> |
```

Status は以下の 4 値のみ:
- ⏳ PENDING (未着手)
- 🔄 IN PROGRESS (着手中 — 次 session で継続)
- ✅ DONE (完了、Evidence 必須記入)
- ❌ ABORTED (放棄 or Scenario A 等で不要化、Reason 必須)

## 3. Completion Write フロー

### 3.1 アクションが DONE した瞬間

**同じセッション内で**以下を実行:

1. 該当 audit ドキュメントの §5 table を edit:
   - `⏳ PENDING` → `✅ DONE`
   - Evidence 欄に commit SHA / PR 番号 / API query 結果 / log 引用を記入
2. Action が **code change を伴う場合**: CLAUDE.md ルール通り、code change + audit ドキュメント
   update を **同一 commit** に含める
3. Action が **observation-only の場合**: 別 commit でも可だが session 内必須

### 3.2 セッション終了時のチェック

session-end の前に以下を自問:
- 進行中だった A# がある場合、Status を正しく記述しているか?
- 本 session で新たに発見した action があれば §5 に追加したか?
- 放棄した項目があれば ❌ ABORTED + Reason 記入したか?

### 3.3 Session-start での再確認

次 session 開始時、最新 audit ドキュメントの §5 を確認し:
- ⏳ PENDING / 🔄 IN PROGRESS のアクションで **今セッションで進められるもの**を特定
- 市場データ観測が必要な項目は即 API query
- 他者 (User/Market) owner のアクションは blocking かどうかを判定

## 4. Audit の expiration

Audit は time-sensitive. 以下の条件で **新 audit を作成** (古い audit は historical snapshot):
- 最後の audit から **2 週間以上**経過
- Major market regime shift (VIX +50% / DXY ±5% 等)
- Major code refactor が完了 (例: MTF engine v10 移行)
- Binding pre-registration holdout 判定通過後

既存 audit は削除せず、§6 "本監査の限界" / §7 "後続 audit へのリンク" を追記して保管.

## 5. References from CLAUDE.md

本プロトコルは CLAUDE.md `## 判断プロトコル` の **6. 監査追跡** 項目として参照される.

## 6. 違反時の教訓化

§3 を飛ばした (audit 作成 → action 実施 → §5 update なし) 場合:
- session-end hook で検出できれば警告
- `wiki/lessons/` に教訓ページを作成
- 次 session の session-start hook で注入

## 7. 本プロトコル自体の適用

本ドキュメントは **audit-completion-protocol v1**. v2 への更新は:
- 実運用 2 週間後、formalize が機能しているか review
- review 結果を `wiki/analyses/audit-completion-protocol-review-YYYY-MM-DD.md` に記録

## References

- [[external-audit-2026-04-24]] (本プロトコル最初の適用対象)
- [[independent-audit-2026-04-10]] (過去 audit 事例)
- [[lesson-reactive-changes]] (形骸化防止の源流)
- [[lesson-premature-neutralization-2026-04-23]] (audit 判断 premature closure 禁止)
