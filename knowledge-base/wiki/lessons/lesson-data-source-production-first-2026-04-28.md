---
title: ローカル DB 参照で本番との乖離を見落とした — production-first 規律違反
date: 2026-04-28
type: lesson
severity: HIGH
related: [[lesson-shadow-vs-live-confusion-2026-04-28]], [[lesson-agent-snapshot-bias-2026-04-28]]
---

# ローカル DB 参照で本番との乖離を見落とした (2026-04-28)

## 何が起きたか

ユーザーが「sr_anti_hunt_bounce が大量発火している原因調査」と質問。Claude は調査の最初に **ローカル `demo_trades.db`** に対し sqlite3 query を実行し、「sr_anti_hunt_bounce が 0 件」という結果に基づいて RCA レポート全体を構築した。

実際には**本番 Render demo_trades.db には 4 日で N=300 件**が記録されており、`is_shadow=0` で 25 件、OANDA forwarded 2 件まで存在していた。

ユーザーが画面で見ていた ~22 件 (OPEN trades) を「ローカル 0 件」と乖離させたまま、誤った結論「signal-track Option B は未実装」を出したまま 1 ターン進行してしまった。

## 規律違反

CLAUDE.md L121:
> **IMPORTANT**: 分析は本番(Render)データを使用。ローカルDBは開発用のみ

CLAUDE.md L3:
> Claudeは**クオンツアナリスト兼実装者**として動作する。エンジニアではない。

## 失敗モード分析

1. **engineering reflex の暴走**: ローカルにファイル (`demo_trades.db`) があると `sqlite3` で query する反射が、CLAUDE.md の production-first ルールを上書きした
2. **成功体験による固定化**: 最初に `knowledge-base/raw/hunt_events/2026-04-28.jsonl` (これは KB 一部でローカル正解) を読めたため、「ローカルでよい」モードに入り、後続の query でも継続
3. **乖離兆候の見逃し**: ローカル 0 件 vs ユーザー言及 22 件 のギャップを **「もしや本番を見るべきでは」** と疑うべきだった
4. **判断前 checklist の欠如**: Bash 実行前に「これは production 参照の質問か？」を作動させていなかった

## 再発防止

### 短期 (本セッションで適用)

任意の trade / signal / 「現在の状態」関連の質問で、まず以下を確認する:
1. CLAUDE.md L121 の production-first ルールに該当するか
2. 該当する場合、`curl https://fx-ai-trader.onrender.com/api/demo/...` を**最初**に実行
3. ローカル DB query は schema 確認 / 過去 backup 比較等の限定用途のみ

### 中期 (hookify 推奨)

```yaml
# .claude/hooks/quant-data-source.yaml
PreToolUse:
  matcher: "Bash"
  pattern: 'sqlite3.*demo.*\.db'
  prompt: |
    fx-ai-trader CLAUDE.md L121: "分析は本番(Render)データを使用".
    user の質問が「現在の trade」「直近 N 件」「Live/Shadow 状態」関連なら
    https://fx-ai-trader.onrender.com/api/demo/trades を使うこと。
    ローカル DB は schema 確認 / backup 比較等の限定用途のみ。
```

### 長期 (auto-memory 蓄積)

`feedback_data_source_production_first.md` を user の `~/.claude` memory に保存。

## 教訓

- 「ファイルがあるから query できる」≠「分析として正しい」
- KB / CLAUDE.md ルールは context に入っているだけでは不十分。**tool 実行前に**作動させる必要がある
- 乖離兆候 (user 言及件数 vs query 結果) を見たら**まず疑うべきはデータソース**

## 関連教訓

- [[lesson-bt-endpoint-hardcoded]] — BT エンドポイントのハードコードで本番見ていなかった先行例
- [[lesson-shadow-vs-live-confusion-2026-04-28]] — Shadow / Live 区別の混同 (同じく本番データ未確認が遠因)
- [[lesson-agent-snapshot-bias-2026-04-28]] — 古いスナップショットを真と思い込む癖
