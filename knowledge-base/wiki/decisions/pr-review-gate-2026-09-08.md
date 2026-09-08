---
tags: [decision, process, review-gate, rule-r3]
date: 2026-09-08
rule: R3
status: 執行済み
---

# PR マージゲート新設 — 独立レビューは 5.5 ヶ月間 write-only だった (2026-09-08)

**rule:R3** (構造バグ / プロセス欠陥。365 日 BT 不要 — 統計的主張を含まない)
親: [[process-meta-audit-2026-09-07]] §4.2 **R2**「マージゲート — 既に走っている独立レビューに読み手を付ける」

## 1. 何を測ったか (estimand)

- **母集団**: 直近 merged PR 40 件 (#187〜#226)
- **分子 1**: `chatgpt-codex-connector` の review が head commit に到着したか
- **分子 2**: その PR の inline review thread のうち **未解決 (isResolved=false ∧ isOutdated=false)** のもの
- **時計**: GitHub の `submittedAt` (レビュー到着) と `mergedAt` (マージ)
- **「レビュー未到着」と「レビュー到着・findings ゼロ」は別状態**として数える

## 2. 実測 (2026-09-08)

| 量 | 値 |
|---|---|
| レビュー到着せずマージ | 5 / 40 (#188, #195, #211, #215, #216 — いずれも open 後 4〜33 分) |
| レビュー到着し inline finding あり | **35 / 35** (findings ゼロの PR は 1 件も無かった) |
| finding thread の **解決済み** | **0 件** (35 PR 全部で 0) |
| review→merge の中央値 | **2.8 分** |
| レビュー到着から 1 分以内にマージ | 7 / 35 (うち #199, #213 は **レビュー到着前**にマージ) |

**読み**: 独立レビューは無料で届き続けていて、一度も読まれていなかった。
メタ監査 codex-1 の訂正版 (「レビュー層は存在する。真の欠陥はレビューが
読まれずマージされること」) が定量で確認された。

## 3. 実害の実例 — 本日発見した 2 日間の監視停止

PR #226 の P1 finding:

> `artifact_presence` を宣言しているが必須の `requirements` 配列が無い。
> `prereg_trigger_watch.build_report()` が `KeyError: 'requirements'` で終了する。

このレビューは **マージの 1 秒前**に到着し、読まれずマージされた (2026-09-06T12:18Z)。
結果:

- `tools/prereg_trigger_watch.py` が **51 エントリ全て**評価不能に (1 件の不整合が全体を落とす設計)
- Tier A daily cron (`fx-ai-tier-a-gate-status`, 00:20 UTC) は落ちず、
  `run_prereg_trigger_watch()` が **returncode を無視して stderr を本文として返して**いたため、
  Discord には traceback が「監視結果」として掲載され続けた
- 未監視期間: 2026-09-06T12:18Z 〜 2026-09-08 (daily 2 回分)。
  この間 T5 第1要件 TRIGGERED、`ps-seat-supply-remeasure-30d` (期日 09-10)、
  P-S1(a) N=9/10 は誰も監視していなかった

**estimand の教訓**: 「監視器が落ちた」と「監視器が異常なしと言った」を
折り畳むと、読み手にとって両者は同じに見える。exit code は名乗るために使う。

## 4. 執行した修復 (本 PR)

**(a) マージゲート — 再発の入口を塞ぐ**
- `tools/pr_review_gate.py` — head commit のレビュー到着 ∧ 未解決 P1/P2 ゼロで exit 0。
  内容の妥当性は判定しない (**読み手を強制するだけ**、採否は Claude の判断)。
  P3 は表示のみ・非ブロッキング。解決手段は「修正」か「反証を thread に返信して resolve」の 2 択。
- `CLAUDE.md` のレビュー記述を実機構 (GitHub Codex connector) に訂正 + マージ手順にゲートを組込み

**(b) 監視器の堅牢化 — 今回の実害そのもの**
- `evaluate_trigger` を隔離ラッパ化: 壊れたエントリは自分だけ `EVAL_ERROR` を名乗り、残り 50 件は通常評価
- `STATE_ERROR` を `DATA_UNAVAILABLE` と**別の箱**に分離 (to_markdown に 🔴 EVAL ERROR 節、`main()` は exit 2)
- `lint_schema()` 新設 — type ごとに評価器が添字アクセスするフィールドを authoring 時に検査。
  既存 `lint_reachability` は機械評価型を素通りさせる設計で、この層に穴が空いていた
- `scripts/check.py` に `check_prereg_registry_schema()` を追加 (**skip に落とさない** — 検査不能は ERROR)
- `quant_gate_status.run_prereg_trigger_watch()` が returncode を検査し、失敗を 🔴 で名乗る

**(c) registry エントリの型修復**
`roster-e2-silent-promoted-cells` を `artifact_presence` → `conditional_info` へ。
このエントリの条件は「E2_SILENT 4 セルの意図的無効 vs 配線落ちを 10-06 までに判別する」であり、
成果物着地ではない。`artifact_presence` は型として estimand が合っていなかった
(Codex の代替案「deadline/manual 型を使え」を採用)。`reachability` を明記し reachability lint の対象へ。

## 5. counterfactual 検証 (guard が本当に落ちるか)

| 注入した欠陥 | 落ちたテスト |
|---|---|
| `evaluate_trigger` の隔離 try/except を除去 | `test_one_broken_entry_does_not_blind_the_other_entries`, `test_eval_error_is_not_folded_into_data_unavailable` |
| registry を 09-06 時点の欠陥形へ戻す | `test_registry_schema_lint_is_clean_on_the_real_registry`, `test_e2_silent_entry_is_machine_watchable_with_reachability`, `scripts/check.py` (exit 1) |
| `live_count_decision` の `prefix` 配線を切る | `test_registry_kalman_live_check_entry_is_wired` |
| `quant_gate_status` の returncode 検査を除去 | `test_prereg_watch_crash_is_reported_as_failure_not_content` |

**副次修正**: `test_registry_kalman_live_check_entry_is_wired` は `inspect.getsource` に
よる**構文 pin** だったため、関数名の変更だけで壊れ、配線そのものは検査していなかった
(MEMORY `lesson_validity_check_pins_proxy_2026_09_02`「pin は性質で書け」の 3 領域目)。
monkeypatch で `prefix=True` が実際に届くかを見る性質 pin へ差し替えた。

## 5b. 本 PR 自身がゲートに落ちた (2026-09-08、初適用)

新ゲートを PR #227 (本 PR) に適用したところ **BLOCK / P1 1 件 + P2 2 件**。3 件とも妥当で、
うち 1 件は**本 PR が直そうとしていた盲点を別の層で作り直していた**:

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P1 | `quant_gate_status` が exit 2 (= 一部のみ `EVAL_ERROR`) でも stdout を捨て「全 trigger 未監視」と名乗る → 壊れた 1 件が他エントリの TRIGGERED を隠す | **妥当** — 隔離ラッパの目的をこの層で無効化していた | 構造化レポートがあれば必ず併記し、banner のみ付す。全滅表示は stdout ゼロのときだけ |
| P2 | `lint_schema` が top-level の器しか見ないので `requirements: [{}]` / `checks: [{}]` / `source: {}` が素通りし、同じ欠陥クラスが daily 実行時まで残る | **妥当** | `COLLECTION_ELEMENT_FIELDS` を追加し、評価器が添字アクセスする深さまで検査 (`source.path` も必須化) |
| P2 | レビュアー照合が部分一致 `codex` なので `my-codex-helper` の空レビューでゲートが通る | **妥当** | 完全一致 allowlist (`DEFAULT_REVIEWERS`、env で上書き可) へ。review 側とスレッド著者側の両方に適用 |

counterfactual 3/3 が所望のテストだけを落とすことを確認。
**ゲートの初回実行が実際に欠陥を 3 件止めた** — これ自体が R2 の効果測定の第 1 点。

### 2 巡目 (再レビュー後)

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | 追加した要素スキーマ自体が評価器の添字を写しきれていない — prefix 無しの ingest check は `chk["key"]`、csv 述語は `c["value"]` を添字アクセスするが、どちらも必須にしていなかった | **妥当** (コードで確認) | 「いずれか 1 つ必須」を表現できる形へスキーマ拡張 (`(required, one_of)`)。`value` を必須に追加 |

**同じ欠陥クラスが 2 巡続いた** — 「評価器の添字を authoring 時に写す」という
修正自体を、写し漏らしたまま出していた。ゲートが 2 巡とも止めた。

### 3 巡目

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P1 | severity regex が `P[123]` なので **P0 が `P?` に落ち BLOCKING からも外れる** — 最も重い finding があるのに PASS しうる | **妥当** | `P[0-3]` へ。**非ブロッキングは P3 のみ**とし、バッジ無し/未知は**ブロック側へ倒す** (判定不能を合格に折り畳まない) |
| P2 | `reviewThreads(first:100)` に `pageInfo` が無く、100 スレッドを超えた PR で 2 ページ目の P1/P2 が `evaluate()` に届かない | **妥当** (本 PR 自身がレビュー往復でスレッドを積んでいる) | cursor で全ページ走査。辿りきれなければ `RuntimeError` → exit 2 (fail closed)。`reviews` も `last:` で最新側から取る |
| P2 | `id` 欠落エントリが lint を通るが `_evaluate_trigger_impl` は `trig["id"]` を添字アクセスする | **妥当** | 全 type 共通で非空 `id` を必須化 |
| P2 | `prefix: ""` は presence 検査を通るが評価器の `if prefix:` で false になり `chk["key"]` へ落ちる | **妥当** | one_of は**非空の値**を要求 (評価器の truthiness と同じ判定) |

counterfactual 4/4 確認。

### 3 巡の集計 — ゲートの効果と費用

- **止めた finding: 計 8 件** (P1 2 / P2 6)。全て妥当で、**反証して dismiss したものはゼロ**
- うち 2 件は「本 PR が直そうとした欠陥クラスを修正自身が再発させていた」型 (exit 2 で stdout 破棄 / 評価器の添字の写し漏れ)
- **費用**: 1 巡あたり pre-commit ~10 分 + レビュー ~5 分。3 巡で ~45 分。潜伏中央値 124 日の欠陥を作成時に止める対価としては安い
- **収穫は逓減しつつある** (3 巡目は P0 バッジ・>100 スレッドという境界条件寄り) が、いずれも実際に到達しうる経路であり、素通りは「合格に折り畳む」ことになる

## 5c. 運用上の注意 — push では再レビューされない

connector がレビューするのは **PR を開いた時 / draft を ready にした時 / `@codex review` と
コメントした時**の 3 契機のみ。修正 push だけではレビューが来ないため、ゲートは
`HEAD_UNREVIEWED` で永久に待ち続ける。これを知らないと「ゲートが壊れている」と誤読して
バイパスする誘因になるので、ゲートの detail メッセージ自体に対処法を書いた:

```
gh pr comment <N> --body "@codex review"   # 先にこれ
python3 tools/pr_review_gate.py <N> --wait 900
```

## 6. 残件

- **P1 #2 (未処理)**: PR #226 の 2 件目 — `tools/live_roster_attrition.py` の
  `D_NEVER_PROMOTED` 判定が「現在の昇格集合に不在」を「当時も未昇格」と読み替えており、
  **88.7% 帰属の主張が未裏付け**の可能性がある (MEMORY `project_roster_attrition_attribution_2026_09_06` の根拠)。
  本 PR のスコープ外 — 別途 estimand 監査として起票が必要 (引用前に要検証)。
- 過去 34 PR の未読 finding (計 ~55 スレッド) の遡及棚卸しは未実施。ゲートは**今後の PR にのみ**効く。
