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

### 4 巡目

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | 必須フィールドを **presence でしか見ていない** — `requirements: [{"path": null}]` は lint を通るが `Path.glob(None)` で落ち、`max_age_hours: null` は `float(None)` で落ちる | **妥当** (one_of 側だけ値検査を入れて required 側に入れ忘れていた) | `_unusable_reason()` を required にも適用 (null / 空文字 / 空コレクション / 数値化不能)。数値化される field は `NUMERIC_FIELDS` で列挙 |

**副産物 — 実在エントリの設計を 1 つ明文化**: この検査は `hourblock-class-exempt-r2-rollback`
の `entry_type: ""` を violation として拾った。調べると**意図的なワイルドカード**で、
母集団は `reasons_marker: [HOURBLOCK_CLASS_EXEMPT]` が定義していた。そのまま禁止すると
正しい設計を壊すので、`WILDCARD_OK_FIELDS` + `ALTERNATIVE_FIELDS_BY_TYPE` を導入し
**「entry_type か reasons_marker のいずれかが非空」**を必須化した。両方空なら
全 live トレードを数える無言の過大計上 (sr-anti-hunt 偽発火と同型) になるため、
禁止すべきなのは「空」ではなく「母集団が誰にも定義されていないこと」。

### 5 巡目

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P1 | 新設した故障 banner は `to_markdown()` の**最後尾** (watch 節) に付くため、Discord の 1900 字カットの外に落ちる。**本文には出ているが読み手には届かない** = 本 PR が直している 2 日間 blind と同型 | **妥当・最重要** | `WATCH_ALERT_MARK` を導入し、故障の 1 行だけを **M1 直後** (カットより前) へ引き上げ |
| P2 | `_unusable_reason()` が numeric 以外は型を見ない — `deadline: 123` (`today > deadline` で TypeError)、`path: 123` (`Path.glob(123)`) が素通り | **妥当** | `STRING_FIELDS` を追加。ただし leaf 名 `match` は type によって意味が違う (文字列 `"prefix"` vs 述語リスト) ため対象外にし、実 registry で回帰 pin |
| P2 | 要素の**任意**フィールドが検査対象外 — `min_files: null` / `min_keys: null` は lint を通り `int(...)` で TypeError | **妥当** | 要素に存在する既知フィールドは必須・任意を問わず型検査 |

counterfactual 3/3 確認。

### 6 巡目

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | `deadline: "soon"` は型検査を通るが `today > deadline` の**文字列比較で常に false** — トリガーが**永久に watching** のまま期日に到達しない | **妥当・型として重要** (「watching 表示を健全性の証拠と誤読する」ZN 教訓と同型) | `DATE_FIELDS` を `YYYY-MM-DD` で検証 (`no-deadline` sentinel は許可) |
| P2 | `n_decide` / `min_files` 等は `int()` で消費されるのに lint は `float()` で通す — `"1.5"` が素通り | **妥当** | `INT_FIELDS` は `int()` で検証 |

counterfactual 2/2 確認。

### 7 巡目 — 「軸ごとの検査漏れ」を個別修正から統一へ

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P1 | 5 巡目で banner を M1 **直後**へ上げたが、M1 節はセル数に比例して伸びる (strategy×instrument×direction ごとに 1 行) ため、セルが増えた日に 1900 字カットの外へ押し出される | **妥当** — 「読み手に届く位置」は絶対位置でなく**相対順序**で決まる | banner を M1 **より前**へ (監視器の故障は KPI より優先) |
| P2 | 型検査が必須フィールドにしか効かず、任意の top-level (`reasons_marker: 123` 等) が素通り | **妥当** | ↓ |
| P2 | `"nan"` / `"inf"` は変換を通るが比較を静かに壊す (`max_age_hours=nan` は `age > max_h` が常に false = **古い ingest を fresh と報告**) | **妥当・静かな腐敗型** | `math.isfinite` を必須化 |

**ここで方針を変えた**: 「必須は見るが任意は見ない」「top-level は見るが要素は見ない」で
**同じ欠陥クラスを 3 巡繰り返した** (4・5・7 巡目)。個別に穴を塞ぐのをやめ、
`KNOWN_VALUE_FIELDS = NUMERIC ∪ STRING ∪ DATE` を単一の集合として定義し、
**必須/任意 × top-level/要素 の 4 象限すべてで「存在すれば検査する」**に統一した。
副産物として `WILDCARD_OK_FIELDS` (type 別) を `EMPTY_OK_FIELDS` (フィールド別) へ
一般化し、`instrument`/`direction` の空文字ワイルドカードも正しく扱えるようになった。

**これが本 PR で最も一般化できる教訓**: 検査器の穴は「どの軸で列挙したか」に沿って空く。
軸ごとに塞ぐと軸の数だけ再発する — **列挙の単位を 1 つに畳んでから検査せよ**。

### 8 巡目 — 統一検査の「集合の中身」を埋める

7 巡目で軸は畳んだが、**集合の中身**が足りていなかった (同じ教訓の 1 段階内側)。

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | `_is_iso_date()` が先頭 10 文字しか解釈せず `since: "2026-01-01Tgarbage"` が通る → `fromisoformat()` が毎回 `DATA_UNAVAILABLE` を返し続ける | **妥当** | 全体を解釈 (`fromisoformat`) |
| P2 | `KNOWN_VALUE_FIELDS` に**評価器の制御フィールド**が入っていない — `closed_only: "false"` は `bool()` で **true**、`dedup_violation: "0"` は `== 0` に一致しない。どちらも**監視母集団が黙って変わり判定期日が前後する** | **妥当・最重要** (sr-anti-hunt 偽発火と同じクラス) | `BOOL_FIELDS` / `EXACT_INT_FIELDS` / `ENUM_FIELDS` (`match`, `count_basis` — 綴り違いは黙って無効化される) を追加 |
| P2 | `int()` 検証は `1.5` を黙って `1` に切り捨て、負値も通す — `n_decide: -1` は即時 TRIGGERED、`min_files: -1` は不在の成果物を「充足」と報告 | **妥当** | 整数値であることと `INT_MIN` の下限を検証 |

counterfactual 3/3 確認。

### 9 巡目 — 「lint は評価器の写しではなく、評価器と同じ呼び出しをせよ」

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | `active` も truthiness 消費だが `BOOL_FIELDS` に無い。しかも `load_registry()` が**フィルタしてから** lint するので、`active: "false"` は true 扱いで評価され、壊れた falsey 値は lint に届く前に消える | **妥当・構造的** | `load_registry_raw()` を新設し lint の既定入口を raw へ。`active` の bool 検査を追加 |
| P2 | `n_decide: "1.0"` は `float()` 経由の検査を通るが評価器の `int("1.0")` は `ValueError` | **妥当** | 検査を**評価器と同じ `int(value)`** に変更 |
| P2 | `strptime` は `2026-9-1` を受けるが、辞書順比較では `"2026-12-31" > "2026-9-1"` が false → 期限切れが永久 WATCHING | **妥当** | 正準形 (0 埋め) を要求 |

counterfactual 3/3 確認。

**構造的な学び**: lint は評価器の型強制を**手で書き写した**ものなので、写し間違いが
必ず起きる (`float` vs `int`、`strptime` が通る形 vs 辞書順が壊れない形)。
9 巡目の修正方針は「評価器と同じ関数を lint でも呼ぶ」— 写しを減らすほど乖離は減る。
残る乖離 (どのフィールドが数値/文字列/bool か) は今も手書き宣言であり、
**次に同型の指摘が出るならそこ**。恒久解は評価器側から宣言を生成することだが、
本 PR のスコープ外 (メタ監査 R3 の estimand 宣言表と同じ方向)。

### 10 巡目 — 一般化した規則の**適用範囲**が広すぎた

7 巡目で「軸を畳む」、8 巡目で「集合の中身を埋める」、9 巡目で「評価器と同じ呼び出し」と
進めたが、その過程で導入した**免除規則が type/field を跨いで効きすぎていた**。

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | `EMPTY_OK_FIELDS` が全 type 共通なので `shadow_count_*` も `entry_type: ""` を許す。`match: "prefix"` と組むと `startswith("")` で**全 shadow トレードを計上**し判定期日を極端に早める | **妥当・危険** (sr-anti-hunt 偽発火と同クラス) | `entry_type` の空許可を `EMPTY_ENTRY_TYPE_OK_TYPES = {live_count_decision}` に限定 (live は `reasons_marker` が母集団を定義するため) |
| P2 | `DATE_SENTINELS` が全 date field に効くので `threshold_date: "no-deadline"` / `since: "no-deadline"` が通る → 永久 WATCHING / DATA_UNAVAILABLE | **妥当** | `DATE_SENTINELS_BY_FIELD` で **deadline 限定**へ |
| P2 | 入れ子 spec の**任意**フィールドは top-level 走査で見つからない — `source.label_columns: 1` は行が一致した瞬間に `TypeError` | **妥当** | `NESTED_SPEC_FIELDS` / `STRING_LIST_FIELDS` を追加し `source` 配下も走査 |

counterfactual 3/3 確認。

**この巡の教訓**: 検査を一般化するときは「どこまで効くか」も同時に決めよ。
**免除 (exemption) は必ず最小スコープで宣言する** — 免除の広すぎは、検査漏れと違って
lint が緑のまま危険を通すので、より悪い。

### 11 巡目 — 「実装している評価器」まで降りて許可を決める

| # | 指摘 | 判定 | 修正 |
|---|---|---|---|
| P2 | 10 巡目で sentinel を **field 単位**に絞ったが、`deadline_info` は `today > deadline` しか見ず sentinel 分岐を**実装していない** → `no-deadline` で永久 WATCHING | **妥当** | sentinel を **type 単位**でも絞り、`evaluate_manual_info` を使う `info`/`conditional_info` と「deadline を消費しない type」のみ許可 |
| P2 | csv 述語の `op` が未検証 — `op: "=>"` は評価器が未知として毎日 `DATA_UNAVAILABLE` を返し続ける | **妥当** | `_CSV_OPS` と突合 |
| P2 | `endpoint` が既知文字列に含まれず、`endpoint: 123` / `""` が通って `fetch_ingest_health()` が誤 URL を叩き続ける | **妥当** | `STRING_FIELDS` へ追加 |

counterfactual 3/3 確認。既存テスト 2 本の期待値を**契約変更として**更新
(`deadline_info` + `no-deadline` は今後 violation)。

### 打ち切り判断 (次巡以降の方針)

11 巡・26 件を経て、残る指摘は全て**同一家系**「lint が評価器の型強制/意味論を
手で写しており、写しの粒度が足りない箇所が 1 つずつ見つかる」に収束した。
これは lint の**設計に内在**する乖離であり、1 件ずつ潰しても原理的に終わらない。

- **本 PR で止める**: 12 巡目以降で「registry の実エントリでは到達しない
  schema 一般化」だけが出る場合は、**反証を thread に返信して resolve** する
  (ゲートの設計どおり採否は Claude の判断)。実際に到達しうる経路
  (制御 field・母集団定義・沈黙する状態遷移) が出れば引き続き修正する
- **恒久解は別件**: 「評価器側から検査宣言を生成する」= メタ監査 R3 の
  estimand 宣言表と同じ方向。registry lint を最初の適用先として起票する

### 11 巡の集計 — ゲートの効果と費用

- **止めた finding: 計 29 件** (P1 4 / P2 25)。全て妥当で、**反証して dismiss したものはゼロ**
- うち 2 件は「本 PR が直そうとした欠陥クラスを修正自身が再発させていた」型 (exit 2 で stdout 破棄 / 評価器の添字の写し漏れ)
- **費用**: 1 巡あたり pre-commit ~10 分 + レビュー ~5 分。11 巡で ~165 分。潜伏中央値 124 日の欠陥を作成時に止める対価としては安い
- **収穫は逓減しつつある** (4 巡目以降は null 値・型・日付形式という schema 一般化寄り。ただし 6 巡目の `deadline: "soon"` は「永久 watching」= 本プロジェクト固有の重大 mode) が、いずれも実際に到達しうる経路であり、素通りは「合格に折り畳む」ことになる
- **観察**: 指摘の 24/29 は「lint/ゲート/検知器が自分の名乗る保証を満たしていない」型 (5 巡目 P1 は極端で、**故障を名乗る行そのものが読み手に届かない位置に置かれていた**) (presence しか見ない / 一部の severity を落とす / 一部のページしか見ない)。**検査器を書くときは『何を保証すると名乗ったか』を毎回自分に適用せよ** — これが本 PR 最大の教訓

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
