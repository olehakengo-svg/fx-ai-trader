### [[lesson-user-challenge-as-signal]]
**発見日**: 2026-04-20 | **修正**: 判断プロトコル追加 (本 lesson)

## 問題
Claude は同一セッション内でユーザーから複数回 challenge (反復疑問) を受けた。各 challenge で分析の表層性・誤前提・先送り癖を指摘され、その都度修正した。しかし**その challenge パターン自体が自分の分析品質の診断信号**であることを session 中では認識せず、session 末に「次セッションから組み込みます」と宣言して終了した。宣言を KB に保存しなかったため、次セッションでは参照されない = `lesson-say-do-gap` 再発。

## 具体事例 (2026-04-20 セッション)

| ユーザー challenge | 私の当初状態 | 修正後に判明したこと |
|---|---|---|
| 「クオンツとしての見解?」(×3) | 表層的な priority list を提示 | EV-based ranking を怠っていた |
| 「KB 見た上で言ってる?」 | 反射的に XAU 浄化を bug 認定 | cutoff + exclude_xau で既に除外済。KB 読めば即分かる |
| 「今できることでやってないのなに」 | admin-type pending タスクを "残タスク" として羅列 | 今できる quant 作業を先送り分類していた |
| 「それは KB に記憶されてるの?」 | 「次セッションから組み込む」と宣言 | 宣言だけで KB 未保存 = `lesson-say-do-gap` |

## 根本原因
1. **Challenge を"修正の機会"として処理し、"診断信号"として処理しなかった**
2. 各 challenge が単発事象ではなく**同じ構造欠陥** (KB skipping / shallow EV analysis / 先送り) の複数発現であることを認識が遅れた
3. `claude-harness-design.md` に challenge-response protocol の記述なし
4. セッション末の「次から気をつけます」は KB 未保存なら意味なし (`lesson-say-do-gap`)

## 修正 (判断プロトコル追加)

### Challenge detection triggers
以下のユーザー発話は**自分の分析に欠陥がある強い signal**:
- 「クオンツとしての見解?」(2回目以降): 表層/admin 的思考に陥っている
- 「KB 見た上で?」: KB 確認を skip している
- 「今できること何」「先送りでは?」: 時間依存性を誤認 or 先送り癖
- 「それは KB に?」: 宣言のみで codify していない
- 「本当に?」「根拠は?」: assertion の根拠不足

### Challenge 遭遇時の強制プロトコル
1. **即座に停止** — 次の提案に進まず、現在の分析を再評価
2. **自問**: 「この challenge は単発 or 既出パターン?」 — 既出なら**構造欠陥**
3. **KB/code 確認を再実行** — challenge が KB 検証を誘発するなら必須
4. **誤り確認時の即時撤回** — 保留/曖昧化せず明示撤回
5. **meta-learning の即 codify** — 「次から気をつけます」禁止、**今すぐ KB 書き込み**

## 教訓
- **ユーザーの challenge は自分の分析の診断信号として扱う**。修正対象として個別処理するだけでなく、challenge パターン自体を記録し予防策を codify する
- **「次セッションから」は言行不一致** — 今すぐ KB に書け。書かないなら言うな (`lesson-say-do-gap` 厳格適用)
- **同一セッション内の反復 challenge = 構造欠陥** — 個別修正では治らない、プロトコル追加が必要

## 関連
- [[lesson-say-do-gap]] — 言ったことをやる、宣言即 codify
- [[lesson-reactive-changes]] — 反射的判断の禁止
- [[lesson-kb-drift-on-context-limit]] — KB skipping の再発
- [[lesson-all-time-vs-post-cutoff-confusion]] — 同日発覚の技術的誤り、本 lesson の trigger
- [[claude-harness-design]] — Claude の運用ルール本体 (§Challenge Response 追加予定)
