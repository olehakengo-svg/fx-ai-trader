#!/usr/bin/env bash
# Stop Hook — セッション終了時のKB書込
# 1. session logのコミット自動追記を確認
# 2. 未コミットのKB変更があればauto-commit
# 3. git push（KB変更の永続化）
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
KB="$ROOT/knowledge-base"
TODAY=$(date +%Y-%m-%d)

# 1. pre-compact.sh を実行（session log生成/更新）
# v8.9: stdout も抑制（JSON出力を汚染しないように）
bash "$ROOT/scripts/hooks/pre-compact.sh" >/dev/null 2>/dev/null || true

# 1.5 Stub detection (2026-05-26): 当日 session が placeholder + ≤1 commit のままなら警告
# 詳細: knowledge-base/wiki/sessions/_index.md の 3-tier 分類
TODAY_SESSION="$KB/wiki/sessions/${TODAY}-session.md"
if [[ -f "$TODAY_SESSION" ]]; then
    if grep -q "Claudeが記入" "$TODAY_SESSION" 2>/dev/null; then
        # grep -c は不一致時に "0" を出力して exit 1 する — || echo だと "0\n0" になり [[ が壊れる
        SESSION_COMMITS=$(grep -cE "^[0-9]+\. " "$TODAY_SESSION" 2>/dev/null || true)
        if [[ "${SESSION_COMMITS:-0}" -le 1 ]]; then
            echo "⚠️  STUB WARNING: ${TODAY}-session.md は placeholder のまま + commit≤1。Tier 3 stub になります (KB graph noise)。" >&2
            echo "   → narrative を書くか、commit を増やすか、削除候補として _index.md に追加してください" >&2
            echo "   詳細: knowledge-base/wiki/sessions/_index.md" >&2
        fi
    fi
fi

# 2. 未コミットのKB変更をauto-commit
KB_CHANGES=$(git diff --name-only -- "$KB/" 2>/dev/null || true)
KB_UNTRACKED=$(git ls-files --others --exclude-standard -- "$KB/" 2>/dev/null || true)

if [[ -n "$KB_CHANGES" ]] || [[ -n "$KB_UNTRACKED" ]]; then
    git add "$KB/" >/dev/null 2>/dev/null || true
    git commit -m "auto: KB session-end save (${TODAY})

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>" >/dev/null 2>/dev/null || true

    echo "KB changes auto-committed" >&2
fi

# 3. push（リモートにKB永続化）— 失敗しても work をローカルに取り残さない
#
# 🔴 2026-09-22: ここが main 乖離の発生源だった。step 2 は HEAD (= 主 checkout では
# main) に直接コミットし、この push は local main が origin より behind だと必ず失敗
# する。失敗を stderr に出すだけだったので、**コミットは main に積まれ push は落ちる**
# が毎日繰り返され、乖離が再生産されていた (実測 ahead 8 / behind 112)。
# 「commit した」≠「永続化した」— origin に届くまでが保存
# (MEMORY project_main_checkout_stranded_phase1b_rescue_2026_08_12)。
#
# ⇒ main への push が失敗したら、**その commit を日付つき rescue ブランチとして
# origin へ退避する**。成功時の挙動は一切変えない。これで「ローカルにしか無い KB
# コミット」が原理的に残らなくなる (次セッションが PR にして畳める)。
if git push origin main >/dev/null 2>/dev/null; then
    :
else
    BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"
    RESCUE="kb-rescue/${BRANCH}-${TODAY}"
    if git push origin "HEAD:refs/heads/${RESCUE}" >/dev/null 2>/dev/null; then
        echo "⚠️  KB push to ${BRANCH} failed — origin/${RESCUE} へ退避した (要 PR 化)" >&2
    else
        echo "⚠️  KB push failed — session log はローカル commit のみ (要手動 push)" >&2
    fi
fi

echo '{"systemMessage":"Session log saved to KB."}'
