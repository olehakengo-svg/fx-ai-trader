---
title: hunt_events 観測データセット readout — 書き手だけが 144 日動いていた
date: 2026-09-19
type: readout + bug-finding
rule: R3
related:
  - "[[sr-strategies-signal-track-2026-04-28]]"
  - "[[sr-anti-hunt-bounce]]"
  - "[[candidate-gap-readout-2026-09-01]]"
  - "[[lesson-defect-family-sweep-siblings-2026-09-17]]"
  - "[[lesson-symmetric-side-check-2026-09-19]]"
---

# `raw/hunt_events/` は書けるが読めず、読めても意味を持たなかった (2026-09-19)

**rule:R3** — 算数破綻 + 構造バグ。365 日 BT は不要、code derivation を以下に置く。
価格データ・live・tier・lot には触れていない。

## 0. なぜ今これを見たか

PR #267 (2026-09-18) がマージゲートの findings 軸が恒真だったことを明らかにし、
過去 10 PR に**未消化の connector P1/P2 指摘 19 件**が残っていることが判明した
(MEMORY `project_review_gate_vacuous_2026_09_11`)。その消化作業として
PR #253 / #264 の hunt_events 系指摘 4 件を実査したところ、指摘された 4 件より
深い場所に欠陥が積み上がっていた。

指摘の出所 (すべて `chatgpt-codex-connector`):

| PR | 指摘 | 本 readout での扱い |
|---|---|---|
| #253 | `raw/hunt_events/2026-09-14.jsonl` に pytest 由来 96 行 | PR #266 で書込み側を遮断済み。本 PR は**読み手側**に防御を追加 |
| #264 | `2026-09-10.jsonl` の 13,408 行中 8,886 行が重複 | ✅ 確定。しかも**データセット全体では 85.7%** |
| #264 | `2026-04-28.jsonl` に署名をすり抜けた合成行が残存 | ✅ 確定。69,577 行中ちょうど 1 行 |
| #264 | `2026-08-03.jsonl` に merge conflict marker | すでに main では解消済み (マージ前に消化されていた) |

## 1. 実測 — 6 層の欠陥

データセット: `knowledge-base/raw/hunt_events/*.jsonl`、89 ファイル、
2026-04-28 〜 2026-09-19、**69,577 行**。

### D0 (根因). 約束された labeler が 144 日間存在しない

`modules/hunt_event_logger.py` の docstring:

> The `reversal / actual_outcome / actual_pnl_pips` fields are appended later by
> `tools/attribute_hunt_outcomes.py` (deferred — runs after demo_trades close).

`tools/attribute_hunt_outcomes.py` は**リポジトリに存在しない**。2026-04-28 に
"deferred" と書かれてから 144 日、書き手だけが動き続けた。これが D4 の直接原因。

### D1. documented consumer が documented dataset を読めない

`tools/sr_audit.py` は `--events-json` を `json.loads(path.read_text())` で読む。
データセットは JSONL なので必ず 2 行目で落ちる:

```
$ python3 tools/sr_audit.py --events-json knowledge-base/raw/hunt_events/2026-09-10.jsonl --pair USD_JPY
json.decoder.JSONDecodeError: Extra data: line 2 column 1 (char 506)
```

痕跡: `knowledge-base/raw/audits/` に `sr_audit_*` の出力が**1 件も存在しない**。
5 ヶ月間、この audit は一度も実行されていない。

### D2. provenance — 値ベース署名がすり抜けた合成行 1 行

実収集行の `instrument` は yfinance の feed symbol。実測:

| instrument | 行数 |
|---|---:|
| `USDJPY=X` | 42,852 |
| `EURJPY=X` | 9,231 |
| `GBPUSD=X` | 8,596 |
| `EURUSD=X` | 7,624 |
| `GBPJPY=X` | 1,273 |
| **`USD_JPY`** | **1** |

`^[A-Z]{6}=X$` に合致しない行は **69,577 行中ちょうど 1 行** (`2026-04-28.jsonl`)。
その行は `modules/hunt_event_logger.py` docstring の例示値そのもの
(entry 153.50 / sl 153.30 / tp 154.20 / level 153.42 / atr_price 0.12 / adx 18.5)
で、`rr` / `score` を欠く 18 キーの schema 変種でもある (実行は 20 キー)。

**旧署名 (`adx` 整数 ∧ `atr_price == 0.001`) はこの行を取りこぼす** — adx=18.5 は
整数でなく atr は 0.12。MEMORY `project_hunt_events_pytest_pollution_2026_09_17`
が「署名は生成 36 行中 12 行しか捕まえない」と記録した recall 穴と同じものが、
今度は**別の値域を使う合成行**として現れた。値ベースの署名は、想定しなかった
値域の fixture が 1 つ増えるたびに破れる。

feed-symbol は**収集経路の構造**なので、値が変わっても誤らない。
これを凍結した読み取り規約にする。

補足 (PR #264 の掃除の会計): `2026-04-28.jsonl` は commit `e0836eff3` 時点で
301 行あり、そのうち **300 行が旧署名に合致** (`atr_price == 0.001` かつ adx 整数)、
残る 1 行が上記。PR #264 (`5b7060c46`) は 300 行を正しく除去し、**1 行を取り逃した**。
結果として現在この日付ファイルは**合成行 1 行だけ**になっている。

### D3. 独立観測の単位 — N が 3.4 倍に膨らむ (⚠️ 窓依存、下記)

engine は同じ bar を tick ごとに再構築・再評価し、logger は評価成功ごとに 1 行
書く (MEMORY `project_engine_reconstruction_live_dedup_dead`)。
`entry_time` 以外が完全一致する行を 1 観測に潰すと:

| 段 | 行数 |
|---|---:|
| 読み込み | 69,577 |
| provenance 隔離 | −1 |
| **重複評価の collapse** (既定窓 1h) | **−48,934** |
| 相異なる観測 | **20,642** |

**膨張係数 = 69,576 / 20,642 = 3.37 倍** (重複比率 70.3%)。

🔴 **この数字は dedup の時間窓に強く依存する — 点推定として引用してはいけない**
(PR #272 Codex P2、5 巡目の指摘で判明。**初版は窓無しの 9,946 / 7.0 倍を
点推定として公表しており、誤りだった**):

| 窓 | 相異なる観測 | 膨張係数 |
|---|---:|---:|
| 15m | 27,335 | 2.55x |
| **1h (既定)** | **20,642** | **3.37x** |
| 4h | 14,953 | 4.65x |
| 24h | 11,614 | 5.99x |
| 無制限 (初版) | 9,946 | 7.00x |

既定 **1h** は「同一 bar の tick 再評価はその bar の長さを超えられない」という
**機構からの導出**で、sr 系が使う最長 bar に合わせたもの — データに合わせた
較正ではない。窓が必要な理由は実測で明らか: **窓無しだと同一 identity の群が
2026-05-01〜2026-07-08 = 68.5 日にまたがる**。それは単一 bar の再評価では
説明できず、**別観測を消している**。

重複群の `entry_time` スパンは中央値 **125 分**、最大 21 時間 — 単一 bar 内の
再評価では説明できない長さで、`level` / `hunt_extreme` / `opposite_sr` が同一の
まま数時間続いている。これ自体が「本来変動する量が連続同値」パターン
(MEMORY の DT `ctx.hour_utc` 凍結と同族) の候補だが、**本 readout では原因を
特定していない**。独立観測でないことは原因に依らず成立するので、dedup は
原因特定を待たずに正しい。

**なぜ算数破綻か**: `tools/sr_audit.py:127` は `n = len(events)` を Wilson 下限と
二項検定の分母に直接使う。Stage A strict ゲート
(`wilson_lower_bf40 > 50%`) が通る最小 WR を N ごとに解くと:

| N | 通過に必要な最小 WR |
|---|---:|
| 20,642 (既定窓での観測数) | **51.025%** |
| 69,577 (膨張後) | **50.558%** |

真の N ではノイズと区別できない WR 50.8% のセルが、膨張後の N では
**Bonferroni k=40 の promotion ゲートを通る**。

### D4. 未ラベル行が自動的に敗北票になる

`reversal` の実測分布: **None が 69,577 / 69,577 (100%)**。
`actual_outcome` も全 None、`actual_pnl_pips` の非 None は 0 行。

旧 `stage_a_audit` の分子は `sum(1 for e in events if e.get("reversal"))` で、
None は分子から落ちるが**分母 `n` には数えられる**。つまり
「まだ観測されていない」が「反転しなかった」として集計される。

pre-fix コードに未ラベル 100 行を渡した実測 (counterfactual):

```
n = 100 / wins = 0 / wr = 0.0%
wilson_lower_95 = 0.0%  wilson_upper_95 = 3.7%
p_value_raw = 0.0  p_value_bonferroni = 0.0
```

実データ全量 (69,577 行) なら **WR = 0.00% / z = −263.8 / Wilson 上限 95% =
0.0055% / p = 0 (アンダーフロー)**。

⚠️ **危険の向きは偽陽性ではなく偽陰性**。この経路は sr hunt 仮説を
「N=69,577 で反転率 0.00%、上限 0.0055%」という圧倒的な見かけの証拠で
**棄却**する。一度でも実行されていれば、仮説は虚構の根拠で死んでいた。
D1 (読めない) がたまたま D4 (意味を持たない) を隠していた、という関係にある。

### D5. `--pair` / `--side` が母集団を絞っていない

旧 `main()` は `--pair` / `--side` / `--window` を出力ファイル名と payload に
書き込むだけで、`stage_a_audit(events, ...)` に渡す母集団を**一切絞らない**。
`--pair USD_JPY --side bull` の出力は実際には全ペア・全 side pooled の結果に
`USD_JPY_bull` というラベルが付いたものになる。

本プロジェクトで最も反復している欠陥族 —
「名乗る estimand を測っているか」(MEMORY
`project_live_fill_estimand_shadow_conflation_2026_09_03`,
`project_roster_d_class_estimand_audit_2026_09_10`) の 1 例追加。

## 2. 対処 (本 PR)

**raw ファイルは書き換えない。** 観測記録は as-collected で保存し、除去・
集約・ゲートは**読み取り時**に行う。合成行 1 行はそのまま残し、恒久的な
negative-control fixture として機能させる。

`tools/hunt_event_dataset.py` (新規) に読み取り規約 D1-D5 を凍結:

| 関数 | 規約 |
|---|---|
| `load_rows` | JSONL / ディレクトリ / glob / 単一 JSON 配列。壊れた行は例外 (silent skip しない) |
| `split_provenance` | feed-symbol 不変条件で (実収集, 隔離) に分割 |
| `collapse_repeats` | identity の粒度は `dedup` で選ぶ — **"signal"** (既定、`entry_time` = 書込み時刻なので除外) / **"bar"** (`entry_time` = bar identity なので保持)。どちらも post-hoc outcome 列は除外。代表は最古 + グループ内のラベルを引き継ぐ。ラベル衝突は会計に載せて gate で止める |
| `select_cell` | `pair` / `side` で**実際に**絞る (`bull`→`support`, `bear`→`resistance`) |
| `split_labels` | `reversal is None` = 未ラベル。分母から除外 |
| `prepare` | 上記を直列適用 + validity gate + 各段の会計を返す |

validity gate: ラベル付き行 < **30** (Rule 1 の N 床と同値) で `DATA-BLOCKED`。

`tools/sr_audit.py` の変更:
- 読み取りを `hunt_event_dataset.prepare()` に委譲 (D1/D2/D3/D5 解消)
- `stage_a_audit` の先頭で未ラベル行を検出したら `verdict="data_blocked"` を返し
  `n` を 0 にする (D4)。**統計関数の側で fail-closed** にしたので、
  `prepare()` を飛ばした呼び出し元からも再発できない
- CLI は DATA-BLOCKED 時に exit 5 + 各段の会計を print

現状のデータセットに対する実行結果:

```
$ python3 tools/sr_audit.py --events-json knowledge-base/raw/hunt_events --pair USD_JPY --side bull
[sr_audit] dataset: read=69577 quarantined=1 repeats_collapsed=48934 distinct=20642 in_cell=8296 labeled=0
[sr_audit] verdict: DATA-BLOCKED — 母集団が estimand を支えない
  - labeled rows 0 < floor 30 (unlabeled 8296 — `reversal` は tools/attribute_hunt_outcomes.py が埋める約束のまま未実装)
```

## 3. pin (62 本、`tests/test_hunt_event_dataset.py`)

MEMORY `project_review_gate_vacuous_2026_09_11` の指示
「**検知器には『NG を返す既知の入力』を同じコミットで pin せよ**」に従い、
5 層それぞれについて**落ちるべき入力**を固定した:

- D1: `json.loads(whole_file)` が落ちる実ファイル形状 / conflict marker 行
- D2: 2026-04-28 の実在合成行 (旧署名が通すことを同じ test で assert)
- D3: `entry_time` だけ違う 5 行 → 1 観測 / 微差ある 3 行 → 3 観測 (誤爆しない側)
- D4: 全行未ラベル → DATA-BLOCKED / 全行ラベル付き → PASS (**恒真 NG でないことの pin**)
- D5: pair / side フィルタが実際に絞る / 未知 side は例外

実データセットへの pin 2 本 (`rows_read > 60000` / `quarantined == 1` /
`labeled == 0` / 膨張係数 > 5.0) — **labeler が実装された日にこれが落ちて
本 readout の更新を促す**構造にしてある。

counterfactual: pre-fix の `stage_a_audit` に未ラベル 100 行を渡すと
`verdict` キーが存在せず `n=100` が返るので、D4 の pin 3 本は pre-fix に対して
落ちる (実測済み)。

### 3.1 レビュー 1 巡目 — 自分が 09-18 に書いた教訓をそのまま踏んだ

PR #272 の connector レビューが P1 2 件 + P2 1 件を返し、**すべて正しかった**:

| # | 指摘 | 実体 |
|---|---|---|
| P1 | benchmark の DATA-BLOCKED を CLI が無視 | `bench_prepared["ok"]` を読まずに空リストを渡すと `net_edge=None` になり、**明示的に要求された baseline 比較なしで strict/lenient ゲートが通る** = promotion ゲートを黙って弱める |
| P1 | `stage_a_audit` が benchmark のラベルを検査しない | 未ラベル行は `bench_n` に数えられ `bench_wins` から落ちるので **baseline 側で D4 がそのまま再生**し `net_edge` が過大になる |
| P2 | wrapper JSON 入力の回帰 | 初版の `load_rows` は先頭が `[` のときだけ単一ドキュメントとして読んでいたため、旧 CLI が受けていた `{"events": [...]}` が 1 event 扱いで隔離される / 整形済みなら 1 行目で例外 |

🔴 **P1 2 件は同じ形 — 「primary 側だけ fail-closed にして、対称な benchmark 側を
自分で確認しなかった」。** §2 で「統計関数の側で fail-closed にしたので、
`prepare()` を飛ばした呼び出し元からも再発できない」と書いたが、
`benchmark_events` 経路では**その主張が偽**だった。

これは **2026-09-18 に自分で書いた教訓の再発** — family A の A-8 で
「レビューが signal 側の穴を指摘したとき label 側の同じ穴を自分で確認しなかった」
と記録し、教訓を「**レビューが片側の穴を指摘したら対称な反対側を自分で確認する**」
と定式化した、その翌日に、今度は**レビューを待たずに片側だけ塞いだ**。
教訓を書くことと、次の設計でそれを検索することは別の作業である。

修正は両側を同じループで検査する形にし (`for label, population in (("events", …), ("benchmark_events", …))`)、
どちらが未ラベルだったかを `unlabeled_in` で返す。pin は**両側**に置いた
(primary clean × benchmark 汚染 → DATA-BLOCKED / 両側 clean → `net_edge` 計算)。

### 3.2 レビュー 2 巡目 — 「対称にする」を 1 段取り違えていた

1 巡目の修正で benchmark を**同じ `prepare()` に通した**ところ、connector が P2 を返した:

> **Avoid applying hunt-only provenance rules to benchmarks** — benchmark は
> 「SR 近接 全 bar」という別母集団で hunt logger 由来とは限らないので、
> `^[A-Z]{6}=X$` を強制すると repo 慣行の `instrument: "USD_JPY"` 表記の
> **ラベル完備で妥当な baseline が全行隔離されて exit 5** になる。

**これも正しい。** 1 巡目の指摘 (「benchmark 側も検査せよ」) に対して、
私は「benchmark を primary と同じパイプラインに通す」と読んだが、
**対称にすべき軸とそうでない軸を区別していなかった**:

| 軸 | 対称か | 理由 |
|---|---|---|
| D4 ラベル検査 | ✅ 対称 | 未ラベル行が分母に入る算数は母集団に依らず壊れる |
| D3 独立観測の単位 | ✅ 対称 | 同一 payload が独立観測でないのも母集団に依らない |
| D5 pair / side 絞り | ✅ 対称 | 名乗る estimand を測る要件は同じ |
| **D2 provenance** | ❌ **非対称** | **feed-symbol は `hunt_event_logger` 固有の規約**で、母集団一般の規約ではない |
| **D3 の `entry_time` の意味論** | ❌ **非対称** (⚠️ この行は §3.5 で追加 — 初版の表は不完全だった) | hunt_events では書込み時刻 / benchmark では bar identity |

⇒ `prepare(..., enforce_provenance=False)` を追加し、benchmark はラベル・dedup・
cell 絞りのみを通す。pin 4 本追加 (`USD_JPY` 表記の完備 baseline が strict では
全行隔離 / benchmark モードでは通る / provenance を外してもラベル検査と dedup は
外れない / 会計に `enforce_provenance` を記録)。

**教訓: 「対称に処置せよ」は「同じ関数に通せ」ではない** ([[lesson-symmetric-side-check-2026-09-19]])**。**
どの規約がどの母集団に固有かを先に列挙する。1 巡目で片側を忘れ、
2 巡目で対称化を取り違えた — 同じ指摘の周りで**2 種類の間違いを続けて**やっている。

### 3.3 レビュー 3 巡目 — dedup は「意味を持ち始める日」に静かに壊れる設計だった

> **Exclude post-hoc outcomes from the repeat identity** — `reversal` /
> `actual_outcome` / `actual_pnl_pips` は post-hoc 値なので、labeler が反復発火に
> 異なるラベルを付けると identity が分かれ `collapse_repeats()` が両方を残す。
> **N 膨張が復活するのは、データセットがラベル付きになって validity gate を
> 通り始めるのと同じタイミング。**

**これも正しい。** 今日は全行 `reversal is None` なので dedup は正しく働き、
実害はゼロ。**だから気づけなかった** — 本 readout で診断した D4 (未ラベル) が
D3 (dedup) の欠陥を隠していた。**D1 が D4 を隠していたのと同じ入れ子構造が、
自分が書いたコードの中にもう一段あった。**

修正:
- `IDENTITY_EXCLUDE` に outcome 3 列を追加 ⇒ identity は **signal 時点のフィールドのみ**
- 代表行はグループ内の非 None ラベルを**引き継ぐ** — 反復発火のうち 1 本だけが
  labeler に拾われるのが自然な形なので、代表が未ラベルだからといって観測を捨てない
- **同一 signal に 2 通りの非 None outcome があれば衝突として会計に載せ、
  validity gate で止める** — labeler のバグを黙って片方採用で潰さない

pin 4 本追加。うち「ラベル付き重複 120 行 → distinct 40 / N=40」は
**修正前は 120 を返す** (= NG を返す既知の入力)。

**教訓: ガードが「今は効いている」ことと「効き続ける」ことは別。
今日たまたま無害にしている前提 (= 全行未ラベル) が解消された日に何が起こるかを、
ガードを書いた時点で 1 回シミュレートする。**

### 3.4 Stage B を自分で確認した (§3.1-3.3 の教訓の適用)

3 巡のレビューで「対称な反対側を自分で確認しろ」を 3 回言われたので、
**指摘されていない Stage B (`stage_b_simulation`) を自分で監査した**。

✅ **Stage B は D4 軸ではクリーン**。outcome を解決できない event は
`else: continue` で**母集団から落ちる**ので、`n = len(sims)` は
ラベル付き event のみを数え、全件未ラベルなら `verdict="no_simulatable_events"`
を返す。Stage A の「未ラベル行が分母に入る」欠陥は Stage B には無い。

⚠️ 別軸の観測 1 件 (**本 PR では変更しない**): Stage B は `actual_outcome` 由来の
event と `reversal` proxy 由来の event (後者は `tp_pip * 0.7` の haircut) を
**同一の `n` に混ぜ、内訳を返さない**。混合比が変われば EV / PF / Kelly が動くので、
labeler を実装するなら**そのときに内訳を出す**べき。今は `prepare()` の
validity gate が手前で止めるため到達不能なので、
registry `hunt-events-labeler-disposition` の note に回した。

### 3.5 レビュー 4 巡目 — `entry_time` の意味が母集団で違った (同じ根の 3 例目)

§3.3 の修正 (outcome 列を identity から外す) は hunt_events には正しかったが、
**benchmark には壊れた**:

> **Use bar-level identity when deduplicating benchmarks** — benchmark は
> 1 bar 1 行で、行は `entry_time` と `reversal` だけが違う。hunt-logger の
> dedup 規則は**その両方**を identity から外すので、**相異なる baseline bar が
> 全部 1 群に潰れ**、偽の outcome 衝突が出て N=30 の床を割り、`net_edge` を
> 計算せず exit 5 になる。

**これも正しい。** 根の原因は 1 つ — **`entry_time` が母集団で別の意味を持つ**:

| 母集団 | `entry_time` の意味 | 正しい粒度 |
|---|---|---|
| `hunt_events` | engine の**書込み時刻** (同じ bar を tick ごとに再評価) | `"signal"` = 除外 |
| `sr_audit` benchmark | **bar の identity** (1 bar 1 行) | `"bar"` = 保持 |

⇒ `DEDUP_MODES` を導入し `prepare(..., dedup="bar")` で benchmark 用の粒度を選ぶ。
pin 3 本追加 (同一 40 bar が "signal" では 1 群 + 偽衝突 1 件 / "bar" では 40 観測 /
同一 bar の真の重複は "bar" でも潰れる)。

🔴 **これは 1 巡目 (片側を忘れた) / 2 巡目 (provenance の対称化を取り違えた) と
同じ根の 3 例目。** 2 巡目で「provenance だけが母集団固有」と表を書いたが、
**`entry_time` の意味論も母集団固有**だった — 表そのものが不完全だった。
「対称にすべき軸」を列挙したときに、**列挙が網羅的である保証をどこからも
得ていなかった**。列挙は仮説であって検証ではない。

### 3.7 レビュー 5 巡目 — 3 巡目で足した衝突検出器が広すぎた (2 形)

3 巡目で「同一 signal に 2 つの結果 → 衝突として gate で止める」を足したが、
その検出器が **2 つの正常入力を衝突と誤判定**していた:

| # | 指摘 | 実体 |
|---|---|---|
| P2 | **Merge compatible partial outcome labels** | `(True, None, None)` と `(True, "WIN", 10.0)` をタプル一致で比較していたため**衝突扱い**。logger は 3 列を独立に初期化し、反復発火のうち実約定に対応するのは 1 本だけ = **部分帰属は正常状態** |
| P2 | **Scope conflict validation to the requested cell** | `collapse_repeats` は `select_cell` の**前**に走るので、**別ペアの衝突 1 件で無関係な clean セルが DATA-BLOCKED** になる (USD_JPY 30 観測が EUR_JPY の 1 件で止まる) |

**どちらも正しい。** 修正:
- `merge_outcomes()` を新設し **フィールドごとに**非 None 値をマージ。
  **同一フィールドに相異なる非 None 値が 2 つ以上あるときだけ**衝突
- 衝突エントリに representative 行を持たせ、gate は
  **選択セルに属する衝突だけ**を数える (`outcome_conflicts` / 全セル分は
  `outcome_conflicts_all_cells` に分離)

pin 5 本追加 (部分ラベルはマージされる / 同一フィールドの不一致は衝突のまま /
不一致フィールドだけが報告される / 別セルの衝突は要求セルを止めない /
要求セル内の衝突はちゃんと止める)。

🔴 **パターン: 私が足したガードは、ほぼ毎回「広すぎる」方向の新しい欠陥を作った。**
3 巡目の衝突検出器 → 5 巡目で 2 件。2 巡目の provenance 対称化 → 4 巡目で 1 件。
**fail-closed は安全側だが、安全側に倒しすぎると「正常入力を止める」という
別の故障になる。** ガードを足したら「止めてはいけない入力」も同じコミットで
pin する — NG 入力の pin と対になる **PASS 入力の pin** が必須。

### 3.8 レビュー 6 巡目 — 🔴 **私が公表した数字が誤りだった**

> **Bound signal deduplication to one underlying bar** — `signal` 粒度は唯一の
> 時刻を identity から外すので、`collapse_repeats()` は**全ファイル横断**で
> グループ化する。別 bar の同一 payload が恒久的にマージされ、ラベル後は
> 偽の衝突にもなる。committed dataset で既に観測可能: ひとつの identity が
> **2026-05-01 から 2026-07-08** までグループ化されている。

**正しい。そしてこれは、本 readout が §1 で公表した数字そのものを崩す。**

初版は「相異なる観測 **9,946** / 膨張 **7.0 倍**」を**点推定として**書いた。
実際には dedup の時間窓に強く依存し (§D3 の表)、**9,946 は窓無し = 最も
攻撃的な端**だった。私は §D3 に「重複群のスパンは中央値 125 分、最大 21 時間で
単一 bar の再評価では説明できない」と**自分で書いておきながら**、
「独立観測でないことは原因に依らず成立する」と続けて点推定を publish した。
**その一文が誤り** — 2 ヶ月離れた別 bar が偶然同一 payload を持つなら、
それは**独立な 2 観測**である。payload 一致はデータセット全期間にわたる
観測 identity ではない。

修正: `DEDUP_WINDOW_SEC` (既定 3600 秒、anchored) を導入し、窓を跨いだ同一
payload は**別観測として残す**。既定 1h は「同一 bar の tick 再評価は
その bar 長を超えられない」という機構からの導出。**感度表を §D3 に併記**し、
点推定での引用を禁じた。

📌 **波及した訂正 (本 PR 内で全て実施)**: readout §D3 / §3 pin 数 / CLI 転写 /
changelog 2 箇所 / session log 2 箇所 / strategy card / logger docstring /
registry `hunt-events-labeler-disposition` / MEMORY 2 ファイル。

**教訓: 自分で書いた caveat を、自分の結論で踏み潰していた。**
「原因は特定していない」と書いた直後に「原因に依らず成立する」と書くのは、
caveat を**記録**しただけで**適用**していない。caveat は書いた本人が
最初の読み手であるべきだった。

### 3.6 レビュー 4 巡の総括 — 欠陥は「実データで回せない経路」に集中した

| 巡 | severity | 経路 |
|---|---|---|
| 1 | P1 | benchmark (CLI が DATA-BLOCKED を無視) |
| 1 | P1 | benchmark (`stage_a_audit` がラベル未検査) |
| 1 | P2 | loader (wrapper JSON 回帰、両経路) |
| 2 | P2 | benchmark (provenance の過剰適用) |
| 3 | P2 | identity (両経路、labeler 稼働時に顕在化) |
| 4 | P2 | benchmark (`entry_time` の粒度) |
| 5 | P2 | 衝突検出器 (部分ラベルを誤って衝突扱い、両経路) |
| 5 | P2 | 衝突検出器 (cell 絞り前に判定、両経路) |
| 6 | P2 | **dedup が全期間で潰れる — 公表した点推定が誤りだった** |

**9 件中 4 件が benchmark 経路**、残り 5 件は loader / identity / 衝突検出器 / dedup 窓 (両経路)。 benchmark は repo に実ファイルが無く、
primary の validity gate が手前で止めるので、**本セッションで 1 度も実行できて
いない経路**である。

対比: **実データで回せた primary 側 (D0-D5) は 6 層すべて自力で見つけた。
回せなかった benchmark 側は 1 つも自力で見つけられなかった。**
自分の欠陥検出能力は「実行して出力を見られるか」にほぼ完全に依存していた。

⇒ **実データで通せない経路を書いたら、「書いたが実行していない」と明示し、
レビューの重点として名指しする。** 「pin を書いたから大丈夫」は、
pin 自身が同じ誤解の上に建っていれば成立しない (3 巡目・4 巡目の pin は
いずれも当時の誤った identity 設計を正しいものとして固定していた)。

## 4. 未解決 — labeler を作るか、データセットを退役させるか

本 PR は**読み手の防御まで**。`reversal` を埋める labeler
(`tools/attribute_hunt_outcomes.py`) は作っていない。作るべきかは別判断:

- **作る場合**: hunt event (既定窓で 20,642 観測) × `demo_trades` の突合、または
  hunt 後 H バーの価格 excursion による事後ラベル付け。後者は価格データを
  使うので、sr 系 pre-reg (`sr-anti-hunt-eurjpy-buy-forward-confirm`,
  期日 2027-02-28) の窓との干渉を先に確認する必要がある
- **退役させる場合**: sr 系の判断は既に shadow/live の `demo_trades` 経路で
  行われている (forward confirm 枠も DB 起点)。hunt_events は並行して存在する
  **未使用の**観測系で、書込みコスト (89 ファイル / 69,577 行 / デプロイ churn)
  だけを払っている

registry に `hunt-events-labeler-disposition` (期日 2026-10-20) を追加した。
それまでは validity gate が DATA-BLOCKED を返し続けるので、**この経路から
誤った verdict は出ない**。

## 5. 付随する corrigendum — 2026-04-28 決定文書の Step 1

[[sr-strategies-signal-track-2026-04-28]] の Step 1 は
「`wc -l` → 81 events = 81 actual signal emissions」を根拠に
「戦略は実際に signal を発射している」と結論している。

git に残る同ファイルのスナップショット (`177ad6f5a`: 50 行 / `e0836eff3`: 301 行)
はいずれも **全行が旧合成署名に合致** (`atr_price == 0.001`)。当日の 81 行の
スナップショット自体は git に残っていないため断定はできないが、
**Step 1 の証拠は合成行を数えていた可能性が高い**。

同文書の結論 (「score competition で構造的敗北」) は Step 3 の score 分布表から
独立に導かれているので**結論は揺らがない**。決定文書は書き換えず、本節を
corrigendum として残す (MEMORY `feedback_audit_past_verdicts_2026_08_05`:
過去 verdict は原本を保存したまま estimand を監査する)。

## 6. 教訓

**「観測データセットがある」は 4 段階に割れる — 書ける / 読める / 単位が正しい /
意味を持つ。** C1 candidate テーブルの 4 ヶ月 write-only
([[candidate-gap-readout-2026-09-01]]) は 2 段目で止まっていたが、hunt_events は
1 段目しか通っていなかったうえ、3 段目 (N の単位) と 4 段目 (ラベル) も
独立に壊れていた。**書き手を足したら、同じコミットで読み手を走らせて
出力を見る** — 「読み手を書く」だけでは足りず、実データで 1 回実行すれば
D1 は初日に落ちていた。

**取りこぼしの向きを取り違えるな。** 合成行フィルタの旧署名について 09-17 に
「誤判別ゼロ」(precision) を確認し、09-18 に recall が 33% だったと訂正した。
今回さらに、**別の値域を使う合成行が 1 行**残っていた。値ベースの署名は
値域を増やされるたびに破れる。**収集経路の構造 (feed symbol) で書けば
値に依存しない。**

**欠陥族の横展開を今度は先にやった。** [[lesson-defect-family-sweep-siblings-2026-09-17]]
の通り、1 箇所直したら同型の兄弟を同じ PR で掃く。今回は指摘された
「重複」「合成行」の 2 件から出発して、同じ読み取り経路の D0/D1/D4/D5 を
先に grep で洗った結果、**指摘 2 件より重い D4 (偽陰性を生む分母汚染) と
D0 (labeler 不在)** に到達した。
