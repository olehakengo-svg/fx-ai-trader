# デプロイ churn による取引カバレッジ欠損 (2026-08-21, rule:R3)

**verdict: 構造欠陥を確認 → render.yaml `buildFilter.ignoredPaths` で是正 (PR #199)**

関連: [[system-reference]] / [[claude-harness-design]] / MEMORY `project_dt_ctx_hour_utc_live_freeze_2026_08_09`

## 1. 発見経緯

`fx-roadmap-autopilot` の定例ヘルスチェック中、本番 API が 502 を返した。
Render を確認したところ **障害ではなく、自分の push が誘発した再デプロイの
swap 窓**だった (deploy `dep-da3qk8bbc2fs738udf50`、01:30:09→01:32:06)。
「1 コミットで本番取引エンジンが止まる」ことに気づいたのが起点。

⚠️ 502 自体はインシデントではない (再プローブで 200)。問題は**頻度**。

## 2. 実測

### 2.1 デプロイ頻度と内訳 (origin/main, 2026-08-07〜08-21, 14 日)

| 区分 | commit 数 | 比率 |
|---|---:|---:|
| **合計 (= web service デプロイ数)** | **263** | **18.8/日** |
| `knowledge-base/` のみ | 206 | 78% |
| KB + data + .remember のみ | 207 | 79% |
| コード/設定に触れる | 56 | 21% |

`render.yaml` の web service は `autoDeploy: yes` / `autoDeployTrigger: commit`
かつ path filter 無し。**ドキュメント commit がそのまま取引エンジンの再起動**。

### 2.2 1 回のデプロイの取引コスト (Render app ログ実測、2026-08-21)

deploy `dep-da3q9bdckfvc7381h1i0` の前後を instance ラベルで追跡:

| 事象 | 時刻 (UTC) |
|---|---|
| 旧 instance `jvxgr` 最終 tick | 01:07:47.8 |
| 新 instance `z9xx6` MainLoop 開始 | 01:08:47.2 |
| **完全無 tick 窓** | **≈ 59.5 秒** |
| 全 24 モード起動到達 (iter=5) | 01:11:26 (≈ +2m39s) |

さらに **cold cache で初回 tick が桁違いに遅い**: `daytrade_gbpusd` tick#1 =
10.3s / 11.4s に対し定常 0.6-0.7s。

### 2.3 ramp 完了前 kill (最重要)

KB commit が 01:06:50 と 01:09:12 に連続したため:

- `z9xx6` は 01:08:47 起動 → 01:10:12 が最終 tick → 01:10:59 に `lvmcc` が交代
- **寿命 85 秒。iter=5 に達したのは 01:09:11 で、各モードはまだ tick#1〜#3**
- = 全モードが warm-up を終える前に殺され、次も同じ状態から始まる

連続 KB commit が続く限り、エンジンは**定常状態に到達できない**。

## 3. 影響評価 (何が壊れ、何は壊れないか)

**壊れない**: DB は永続ディスク `/var/data/demo_trades.db`。再起動で
約定履歴・shadow 行は失われない。ポジションは OANDA 側に残る。

**壊れる**: tick カバレッジ。1 日 ~15 回の不要再起動 × ~60s の無 tick
≈ **15 分/日の完全断**、加えて ramp 中の部分カバレッジと cold-cache 遅延。
scalp (1m/5m) 系ほど相対損失が大きい。

これは **4 原則①「マーケット開いてる間は攻める」** と最重要ボトルネック
**クリーン N 蓄積** に直接反する。静的時間ブロックは入れない設計方針なのに、
運用上の穴で実質的な取引停止窓を毎日作っていた。

⚠️ **本ページは「取引機会を N pip 逃した」とは主張しない。** 断続窓と
発火の同時性は未測定であり、逸失 pip の定量化には別途 pre-reg が必要。
主張は「不要な断続窓が構造的に存在した」という機構レベルの事実に限る。

## 4. 対策 (rule:R3 — 構造バグ、365日BT 不要)

`render.yaml` の web service に `buildFilter.ignoredPaths` を追加。
**ランタイムが読まない KB パスのみ** を ignore する。

### 4.1 ランタイム KB 参照の全数確定 (`app.py` + `modules/`)

| パス | 種別 | 扱い |
|---|---|---|
| `wiki/tier-master.json` | **read** (app.py:27, :11010) | ignore しない |
| `wiki/snapshots/` | **read** (app.py:28) | ignore しない |
| `raw/trade-logs/analyst-memory.md` | **read** (app.py:11645) | ignore しない |
| `raw/trade-logs/analyst-memory-archive.md` | **read** (app.py:11646) | ignore しない |
| `wiki/decisions/prereg-trigger-registry.json` | cron read | ignore しない (保守的) |
| `raw/hunt_events/` | **write only** (hunt_event_logger.py:40) | ignore 可 |
| `raw/bt-results/` | **write only** (app.py:12309) | ignore 可 |
| `raw/audits/`, `raw/market-analysis/` | コメント参照のみ | ignore 可 |

`analyst-memory.md` は `modules/` からの参照ゼロ = シグナル経路外だが、
ランタイム read である以上は保守的にデプロイを起こさせる。
**残存デプロイの最大要因 (14日で41件)** なので、将来 user 決裁で
ignore に移せば更に削減できる (本 PR では触らない)。

### 4.2 効果 (同じ 14 日窓での再生)

| | before | after |
|---|---:|---:|
| デプロイ数 | 263 | 110 |
| **1日あたり** | **18.8** | **7.9** |
| 削減 | — | **−58%** |

残存トリガ内訳: analyst-memory.md 41 / prereg-trigger-registry.json 21 /
merge commit 35 / 実コード・データ 13。

⚠️ **算定上の訂正 (自己修正)**: 初回モデルは `git show --name-only` が
merge commit で空を返す性質を見落とし、35 件の merge を母数から落として
「16.8→5.9 (−65%)」と出していた。merge は first-parent 差分で評価し直し、
上表が正。merge は必ずコード差分を含むため ignore されない。

## 5. 再発防止 (`tests/test_render_build_filter.py`)

3 テストで不変条件を固定:

1. `buildFilter.ignoredPaths` の存在と最小サイズ (縮小検知)
2. **ランタイム read パスが ignore されていない** — 巻き込むと本番が
   古い KB を掴んだまま気づかれない (サイレント汚染)
3. **drift guard** — `app.py`/`modules/` が触る KB パスを regex 抽出し、
   ignoredPaths に match するものは write-only allowlist 必須。
   「新しく KB を読み始めたのに ignore され続ける」事故を機械で止める

いずれも故意に違反を注入して**赤くなることを確認済み** (vacuous でない)。
pyyaml は requirements 非依存のため `scripts/check.py` と同じ regex 方式。

## 6. 教訓

**「デプロイは無料」という暗黙の前提を、常駐取引プロセスを持つサービスに
持ち込んではいけない。** CI の paths filter (T15 で撤廃) と、CD の
build filter は別問題。前者は「テストを回すか」、後者は
**「取引エンジンを殺すか」**。同じ語彙で議論すると取り違える。

副次: 監視スクリプトが「API unavailable」を返したとき、それが
**自分の push が起こした再デプロイ窓**である可能性を最初に疑う。
今回 11 個の count-based トリガが一斉に data unavailable を出したのは
本番障害ではなくこの窓だった (再実行で全て正常取得)。

---

## 7. 本番実測検証 (2026-08-21T02:00Z、PR #199 マージ直後)

**目的**: `render.yaml` が Blueprint 同期されており buildFilter が実効か。
API は buildFilter を返さないため、**デプロイ挙動で検証**する。

### 7.1 観測

| 時刻 (UTC) | commit | 内容 | デプロイ |
|---|---|---|---|
| 01:57:47 | `4e2b69b9` | PR #199 マージ (コード変更含む) | ✅ `dep-da3r179srm7s73d6eo6g` 作成 → 01:59:29 **live** |
| 01:58:44 | `f2170ba2` | `raw/intervention_watch/2026-08.jsonl` のみ | ❌ **デプロイレコードなし** |

`f2170ba2` は ignoredPaths の `knowledge-base/raw/intervention_watch/**` に
match する KB 専用 commit。**デプロイが作られなかった** = フィルタ実効。

### 7.2 対照 (交絡の排除)

`f2170ba2` はマージデプロイ進行中 (01:57:49-01:59:29) に着地したため、
「進行中デプロイによる合体で skip されただけ」の可能性を排除する必要がある。

**歴史的対照**: 2026-08-18 に同じ状況が存在する。

- `dep-da20dmh42hec73f7gp8g` (commit `5c071601`) 07:16:42 開始 → **07:18:24.8 終了**
- `dep-da20ea3qmmms73ega6dg` (commit `89695b40`, 07:18:00 = **前デプロイ進行中**)
  → **レコードは 07:18:00.58 に即作成**され、07:18:25.2 に開始 (= キュー投入)

つまり Render は進行中デプロイ中の commit にも**即座にデプロイレコードを作る**。
`f2170ba2` にレコードが 1 件も無いのは合体ではなく **buildFilter による skip**。

### 7.3 結論

- ✅ `render.yaml` は Blueprint 同期されており、マージと同時に buildFilter が発効
- ✅ KB 専用 commit がデプロイを起こさないことを本番で実証
- ✅ 本番 `/api/demo/status` = 200 (マージデプロイ後、正常稼働を確認)

§4.2 の「18.8/日 → 7.9/日 (−58%)」は履歴再生による**推定**だが、
機構そのもの (KB 専用 commit が skip される) は上記で**実証済み**。
