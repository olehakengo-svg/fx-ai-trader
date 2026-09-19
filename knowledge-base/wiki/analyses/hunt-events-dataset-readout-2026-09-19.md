---
title: hunt_events 観測データセット readout — 書き手だけが 144 日動いていた
date: 2026-09-19
type: readout + bug-finding
rule: R3
related:
  - "[[../decisions/sr-strategies-signal-track-2026-04-28]]"
  - "[[../strategies/sr-anti-hunt-bounce]]"
  - "[[candidate-gap-readout-2026-09-01]]"
  - "[[../lessons/lesson-defect-family-sweep-siblings-2026-09-17]]"
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

### D3. 独立観測の単位 — N が 7.0 倍に膨らむ

engine は同じ bar を tick ごとに再構築・再評価し、logger は評価成功ごとに 1 行
書く (MEMORY `project_engine_reconstruction_live_dedup_dead`)。
`entry_time` 以外が完全一致する行を 1 観測に潰すと:

| 段 | 行数 |
|---|---:|
| 読み込み | 69,577 |
| provenance 隔離 | −1 |
| **重複評価の collapse** | **−59,630** |
| 相異なる観測 | **9,946** |

**膨張係数 = 69,576 / 9,946 = 7.0 倍** (ファイル内だけで数えると 82.9% / 5.8 倍、
ファイル横断も含めると 85.7% / 7.0 倍)。

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
| 9,946 (真の観測数) | **51.473%** |
| 69,577 (膨張後) | **50.558%** |

真の N ではノイズと区別できない WR 51.0% のセルが、膨張後の N では
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
| `collapse_repeats` | identity = `entry_time` 以外の全フィールド完全一致。代表は最古 |
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
[sr_audit] dataset: read=69577 quarantined=1 repeats_collapsed=59630 distinct=9946 in_cell=3057 labeled=0
[sr_audit] verdict: DATA-BLOCKED — 母集団が estimand を支えない
  - labeled rows 0 < floor 30 (unlabeled 3057 — `reversal` は tools/attribute_hunt_outcomes.py が埋める約束のまま未実装)
```

## 3. pin (30 本、`tests/test_hunt_event_dataset.py`)

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

## 4. 未解決 — labeler を作るか、データセットを退役させるか

本 PR は**読み手の防御まで**。`reversal` を埋める labeler
(`tools/attribute_hunt_outcomes.py`) は作っていない。作るべきかは別判断:

- **作る場合**: hunt event (9,946 観測) × `demo_trades` の突合、または
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

[[../decisions/sr-strategies-signal-track-2026-04-28]] の Step 1 は
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

**欠陥族の横展開を今度は先にやった。** [[../lessons/lesson-defect-family-sweep-siblings-2026-09-17]]
の通り、1 箇所直したら同型の兄弟を同じ PR で掃く。今回は指摘された
「重複」「合成行」の 2 件から出発して、同じ読み取り経路の D0/D1/D4/D5 を
先に grep で洗った結果、**指摘 2 件より重い D4 (偽陰性を生む分母汚染) と
D0 (labeler 不在)** に到達した。
