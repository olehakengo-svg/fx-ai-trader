# Lesson: post-commit-verify check#3 が bash クォート衝突で一度も実行完了していなかった

**発見日**: 2026-07-09 | **修正**: rule:R3 (本コミット)

## 問題 (2層)

### 層1: bash クォート衝突による silent 不発
`scripts/hooks/post-commit-verify.sh` check #3 (demo_trader.py 変更時の tier set 整合検証) が、
導入 (2026-04-14, commit `50979707`) 以来**一度も実行完了していなかった**。

- bash の double-quoted `python3 -c "..."` 内に python f-string `print(f'FAIL:{"; ".join(msg)}')` があり、
  内側の `"` が bash 文字列を途中終端 → python には `print(f'FAIL:{` で截断されたコードが渡る
- 毎回 `SyntaxError: EOL while scanning string literal` → `|| echo "SKIP"` が吸収 →
  健全時ですら `OK` に到達不能。FAIL 検出能力ゼロのまま約3ヶ月稼働
- [[lesson-silent-except-hides-nameerror]] (「silent except は不発とゼロ件を区別不能にする」) と同型。
  握り潰し先が python の `except` ではなく bash の `|| echo SKIP` だっただけ

### 層2: 不発の間に assertion 自体が設計から乖離 (stale assertion)
修復して走らせると即 FAIL — しかし検出された 4 overlap
(`FORCE_DEMOTED∩SENTINEL={post_news_vol}`, `PAIR_PROMOTED-strat∩SENTINEL={doji_breakout, squeeze_release_momentum, vix_carry_unwind}`)
は**全て現行設計の意図的共存**で、stale だったのは assertion 側:

- 旧 assertion は sentinel 優先時代 (2026-04-14) の「PAIR_PROMOTED が SENTINEL に食われて shadow 化する」バグの検出器
- 現行設計では `_is_promoted_ex` / `_resolve_tier` の両方で PAIR_PROMOTED が SENTINEL より先に評価され、
  「demote/sentinel = live 遮断 + shadow 蓄積継続」の共存が正 (demo_trader.py 2026-07-02 コメント
  「PAIR_PROMOTED overrides _UNIVERSAL_SENTINEL shadow eligibility / Shadow accumulation continues (principle 3)」)
- 旧 assertion をそのまま生かすと demo_trader 変更のたびに誤警報 → 警告無視の習慣化 (オオカミ少年化)

## 症状
- check #3 は常に `SKIP` (grep FAIL 不成立) — 3ヶ月間、tier set 整合違反をブロックする能力ゼロ
- SyntaxError は post-commit hook がバックグラウンド実行 (`&`) のため誰の目にも触れず

## 原因
1. inline `python3 -c "..."` (bash double quote) は python コード内の `"`/`$`/`` ` ``/`\` が bash に解釈される構造的罠
2. `|| echo "SKIP"` が「環境要因の SKIP」と「検証スクリプト自体の破損」を同一値に縮退
3. 検証が不発の間、監視対象 (tier 設計) は進化し続け、assertion が無検証のまま陳腐化

## 修正 (rule:R3)
1. **quoted heredoc (`<<'PYEOF'`) 化** — bash が python コードを一切解釈しない = クォート衝突クラスごと消滅。
   check #1 も同様に heredoc 化 (現状は偶然無事だったが `"` 1文字の編集で同じ死に方をする)。
   check #2 は inline python 非使用で対象外
2. 該当行も `'FAIL:' + '; '.join(msg)` へ書き換え (二重防御)
3. check #3 は import 失敗を `FAIL:verify_error:` で可視化 (network 非依存で正当な SKIP が存在しないため)。
   空出力も `${RESULT:-FAIL:verify_no_output}` で FAIL 化 — 将来の構文エラーを silent 化させない
4. assertion を現行設計の invariant へ張替え:
   - `PAIR_PROMOTED ∩ PAIR_DEMOTED` (同一セル) — `_is_promoted_ex` は PAIR_DEMOTED 先勝ち → 昇格セル silent 死
   - `ELITE_LIVE ∩ FORCE_DEMOTED` — live gate はブロック vs `_resolve_tier` は ELITE_LIVE 先返し = gate/write-path 矛盾 (v9.0 trendline_sweep 前例)
5. `POST_COMMIT_VERIFY_CHANGED` テストシーム追加 — hook 全体を commit なしで red→green 検証可能に
6. red→green 実証: 健全状態 green → 両 overlap 注入で FAIL 発火 (メッセージ結合含む) → revert で green

## 教訓
1. **bash 文字列に python を埋め込むな — 検証スクリプトの python は quoted heredoc で渡す**。inline `python3 -c "..."` はコード内の `"` 1文字で silent 不発化するクラスの罠で、`|| echo SKIP` と組むと [[lesson-silent-except-hides-nameerror]] と同じ「不発とゼロ件の区別不能」を bash 層で再生産する
2. **不発だった検証を修復したら「動くか」と「主張が今も正しいか」を両方再検証する**。検証が眠っている間も設計は進化する — 復旧した assertion が現行設計と整合するかを、precedence の実コード (`_is_promoted_ex` / `_resolve_tier`) まで降りて確認してから green 化する。stale assertion の復活は誤警報の常態化 = 検証ゼロと同じ結末を招く

## 関連
- [[lesson-silent-except-hides-nameerror]] — 同型 (握り潰しによる不発/ゼロ件の縮退)
- [[lesson-tool-verification-gap]] — この hook 自体の存在理由 (作ったものが動くことを検証)
- `wiki/decisions/live-bleeder-demotions-2026-07-02.md` — PAIR_PROMOTED/SENTINEL 共存を正とした現行設計の根拠
