---
title: BSD 専用 stat -f が GNU stat で「成功」し、クラウド Linux セッションの KB 注入フックが全損していた
date: 2026-09-14
type: lesson
severity: MEDIUM
related: [[claude-codex-division-of-labor-2026-07-02]], [[lesson-kpi-without-a-reader-2026-09-04]]
---

# クラウド (Linux) セッションで SessionStart / UserPromptSubmit hook が全損していた (2026-09-14)

## 何が起きたか

「クラウド環境でも自動で動いているか」の棚卸し中に、Claude Code on the web (Linux コンテナ) で
`scripts/hooks/session-start.sh` と `scripts/hooks/user-prompt-kb-sync.sh` が **exit 1・JSON 出力ゼロ**
でクラッシュしていることを実測で確認した。つまりクラウドセッションでは
**KB 自動注入 (index / 未解決事項 / lessons / daily report / analyst-memory / 4原則リマインダ) が一切効いていなかった**。
CLAUDE.md が前提とする「SessionStart hook が自動注入する」はローカル Mac でのみ真だった。

## 原因 (2 層)

1. **BSD/GNU の同名オプション衝突**: `stat -f %m FILE` は macOS (BSD stat) では mtime を返すが、
   GNU stat では `-f` が「ファイルシステム統計モード」として **正常終了** し複数行テキストを返す。
   そのため `stat -f %m || stat -c %Y || echo 0` のフォールバックは Linux で一度も発火せず、
   複数行の出力が変数に入り、直後の算術展開が `set -u` 下で `File: unbound variable` で script 全体を殺した
   (session-start.sh の index 鮮度チェック、user-prompt-kb-sync.sh の session log 更新リマインド)。
2. **静かな全損**: hook が exit 1 で死んでも additionalContext が注入されないだけでセッション自体は動くため、
   誰も気づかない。クラウドセッションは 2026-07 以降 `claude/*-*` ブランチで多数走っていたが
   ([[claude-codex-division-of-labor-2026-07-02]] 以降のセッションログ)、全て KB 注入なしの「素の Claude」だった。

副次バグとして `grep -c ... || echo 0` パターン (3 箇所) も確認: grep -c は不一致時に "0" を**出力しつつ** exit 1
するため `|| echo 0` が二重に 0 を吐き、変数が `0\n0` となって `[[ "$VAR" -gt 0 ]]` が構文エラーになる
(両 OS 共通、実測 `[[: 0 0: syntax error`。条件が false になるだけで致命ではない)。

## 影響

- クラウドセッションは lessons / 未解決事項 / tier SSOT ポインタ / 判断プロトコルの注入なしで判断していた
  (= KB 参照ゼロ判断のリスク。判断プロトコル「KB参照ゼロ→判断停止」の前提が環境依存で崩れていた)
- `session-end-save.sh` は `git push origin main` の失敗を `|| true` で握り潰すため、
  クラウドで main 直 push が拒否されると session log の KB 永続化も黙って消えていた

## 修正 (rule:R3、本 PR)

- stat フォールバックを **GNU 優先** に入替: `stat -c %Y ... || stat -f %m ... || echo 0`
  (macOS では `-c` が失敗して BSD 側に落ちるため後方互換)。2 箇所
- `grep -c ... || echo 0` → `|| true` + `${VAR:-0}` 参照に修正。3 箇所
- `session-end-save.sh` の push 失敗を stderr に可視化 (握り潰し廃止)
- Linux コンテナで両 hook の exit 0 + JSON 妥当性を実測確認済み

## 一般化された教訓

> **クロスプラットフォームのフォールバック連鎖 (`A || B`) は「A が異環境では失敗する」ことを前提にできない —
> 同名オプションが別の意味で「成功」する (BSD `stat -f` vs GNU `stat -f`) と、フォールバックは静かに死ぬ。
> ターゲット環境 (Linux CI/クラウド) で動く形を第一候補に置け。**
> そして **hook・注入系の失敗は「静かな全損」になる** — 出力がなくてもセッションは動くため、
> 数ヶ月単位で気づかれない。環境を増やしたら (ローカル Mac → クラウド Linux) 注入系は実行検証せよ。
