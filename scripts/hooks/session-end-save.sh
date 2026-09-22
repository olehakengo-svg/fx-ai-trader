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

KB_COMMIT_SUBJECT="auto: KB session-end save (${TODAY})"
COMMITTED_THIS_RUN=0
if [[ -n "$KB_CHANGES" ]] || [[ -n "$KB_UNTRACKED" ]]; then
    HEAD_BEFORE="$(git rev-parse HEAD 2>/dev/null || echo none)"
    git add "$KB/" >/dev/null 2>/dev/null || true
    git commit -m "${KB_COMMIT_SUBJECT}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>" >/dev/null 2>/dev/null || true
    # "exit 0" は commit 成功を意味しない (pre-commit の Commit blocked も 0)
    [[ "$(git rev-parse HEAD 2>/dev/null || echo none)" != "$HEAD_BEFORE" ]] \
        && COMMITTED_THIS_RUN=1

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
    if [[ "$BRANCH" != "main" ]]; then
        # 🔴 feature ブランチ / worktree から退避してはいけない (Codex P1, PR #276)。
        # `git push origin main` は **ローカルの main ref** を押すので、HEAD が
        # feature の時も (main が behind なら) 失敗しうる。そこで HEAD を退避すると
        # **その feature の未公開 WIP コミットまで origin に publish** してしまう —
        # 誰も頼んでいない公開になる。HEAD が main でない場合、step 2 の KB コミットは
        # その feature ブランチ上にあり、当人の PR で push されるので座礁しない。
        echo "⚠️  KB push to main failed (HEAD=${BRANCH}) — この commit は ${BRANCH} 上にあるので退避しない (PR で push される)" >&2
    elif [[ "$COMMITTED_THIS_RUN" != "1" ]]; then
        # このランは何もコミットしていない ⇒ 退避すべき新規 KB work は無い。
        # 既存の local-only 履歴を勝手に publish しない (Codex P1, PR #276)。
        echo "⚠️  KB push to main failed — 本ランの新規 KB コミットは無いので退避しない" >&2
    else
        # 🔴 **退避 ref に載るのが「hook が作った KB コミットだけ」であることを
        # 確認する** (Codex P1, PR #276)。`HEAD:refs/heads/...` は HEAD の履歴を
        # まるごと publish するので、local-only な**非 KB コミット** (誰かが main に
        # 直接コミットした作業) が混じっていると、**それも頼まれずに公開**される。
        # 混在していたら publish せず、理由を出して止まる (公開は不可逆なので
        # fail-closed が正しい向き)。
        # 検査対象の sha を**固定**する (Codex P1, PR #276)。`HEAD` は symbolic
        # なので、収集〜検査の間に**別エージェントがこの共有 checkout へコミット**
        # すると、検査は旧履歴に対して行われたのに `HEAD:refs/heads/...` は**新しい
        # HEAD を publish** する = ガードが留め置くはずの非 KB work がすり抜ける。
        # この repo は並行エージェント前提なので実在のリスク
        # (MEMORY feedback_concurrent_agent_repo_hazard)。以後 VALIDATED のみを使う。
        VALIDATED="$(git rev-parse HEAD 2>/dev/null || echo '')"
        UNPUBLISHED="$(git rev-list origin/main.."$VALIDATED" 2>/dev/null || echo FAIL)"
        [[ -z "$VALIDATED" ]] && UNPUBLISHED=FAIL
        MIXED=0
        if [[ "$UNPUBLISHED" == "FAIL" ]]; then
            MIXED=1                     # 比較できない = 検査不能 ⇒ 公開しない
        else
            for C in $UNPUBLISHED; do
                SUBJ="$(git log -1 --format=%s "$C" 2>/dev/null || echo '')"
                case "$SUBJ" in
                    "auto: KB session-end save"*) ;;
                    *) MIXED=1; break ;;
                esac
                # KB 以外のパスに触っていないことも確認する (subject は自称)。
                #
                # 🔴 **パイプで書いてはいけない** (Codex P1, PR #276)。
                # `git diff-tree ... | grep -qv '^knowledge-base/'` は、非 KB パスが
                # 早い位置にあり後続 KB パスがパイプバッファを埋めるほど多いとき、
                # `grep -q` が先に exit して `git` が **SIGPIPE (141)** を受ける。
                # このスクリプトは `pipefail` なのでパイプライン status が 141 =
                # 非ゼロになり、**`if` は偽** ⇒ **混在履歴を「KB だけ」と判定して
                # publish する** = ガードが存在意義そのものの場面で反転する
                # (本セッションで実際に作ってしまった 3,568 files の混在コミットが
                # まさにこの形)。⇒ パイプを使わず変数に取ってシェルで走査する。
                PATHS="$(git diff-tree --no-commit-id --name-only -r "$C" 2>/dev/null || echo '')"
                if [[ -z "$PATHS" ]]; then
                    MIXED=1; break          # 検査不能 ⇒ 公開しない
                fi
                while IFS= read -r F; do
                    [[ -z "$F" ]] && continue
                    case "$F" in
                        knowledge-base/*) ;;
                        *) MIXED=1 ;;
                    esac
                done <<< "$PATHS"
                [[ "$MIXED" == "1" ]] && break
            done
        fi
        if [[ "$MIXED" == "1" ]]; then
            echo "⚠️  KB push to main failed — local-only 履歴に非 KB コミットが混在するため退避しない (公開は手動判断: git log origin/main..HEAD)" >&2
        else
            # ref 名に **完全な sha** を入れる (Codex P2, PR #276、2 巡)。同日に
            # 2 つの stale な main checkout が走ると `kb-rescue/main-<date>` が衝突し、
            # 2 本目は non-fast-forward で拒否されて**ローカルに座礁したまま**になる。
            # `-f` は使わない (他人の退避を壊すため) ので、名前を一意にする方で解く。
            # ⚠️ `--short` は **`core.abbrev` に従う**ので 4 桁まで縮みうる = 前置が
            # 衝突して同じ問題が再発する。一意性が目的なら省略形を使ってはいけない。
            RESCUE="kb-rescue/main-${TODAY}-${VALIDATED}"
            # **検査した sha を明示的に**押す。`HEAD` を渡すと上記 TOCTOU が開く。
            if git push origin "${VALIDATED}:refs/heads/${RESCUE}" >/dev/null 2>/dev/null; then
                echo "⚠️  KB push to main failed — origin/${RESCUE} へ退避した (要 PR 化)" >&2
            else
                echo "⚠️  KB push failed — session log はローカル commit のみ (要手動 push)" >&2
            fi
        fi
    fi
fi

echo '{"systemMessage":"Session log saved to KB."}'
