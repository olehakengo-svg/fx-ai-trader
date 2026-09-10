# estimand 宣言表システム — 検知器の「名乗る量」と「測る量」の台帳 (2026-09-10)

**rule:R3** — 構造欠陥への即応。365日BT 不要 (取引ロジック非接触、監視インフラのみ)。
**根拠**: [[process-meta-audit-2026-09-07]] §4.2 R3 — 監視/検知器のバグ潜伏中央値 124 日、QA 起点発見 0/8。user 承認 2026-09-10。

## 1. 何を作ったか

| 成果物 | パス | 役割 |
|---|---|---|
| 宣言表 | `monitoring/estimand_declarations.yml` | 本番監視/検知器 14 系列の estimand 台帳 (SSOT) |
| チェッカー | `tools/estimand_declaration_check.py` | schema 検証 + 配線の grep レベル検証 |
| テスト | `tests/test_estimand_declarations.py` | 実宣言表の整合 pin + チェッカー自体の counterfactual |
| PR テンプレ | `.github/pull_request_template.md` | 修理 3 フィールド (混入日/発見日/発見手段) + 検知器チェックリスト |

## 2. なぜ (問題の型)

過去 4 ヶ月で繰り返した監視バグは全て同型 — **検知器が名乗る量と測る量の乖離 (estimand 混同)**:

| 事例 | 名乗っていた量 | 実際に測っていた量 | 潜伏 |
|---|---|---|---|
| live_n_stagnation (PR #221) | LIVE 約定の停止 | demo_trades 全行 (99.8% shadow) の書込み | 126 日 no-op + 7.5 日誤読 |
| rnb block カウンタ (PR #224) | ブロック理由の内訳 | 別の定義のカウンタ | 153 日 |
| candidate_stagnation の時計 (PR #207/#209) | 市場オープン時間 | 実時間 (毎週末誤発火リスク) | — |
| ps capture (PR #228) | closed-bar capture 率 | live=forming bar / grid=closed bar の交わらない 2 母集団の比 | — |

共通根因: **「何を数えるか」「どの時計で」「誰が読むか」がコードの中に暗黙に散在**し、
乖離しても落ちるテストが無かった。宣言表はこれを 1 ファイルに外部化し、チェッカーが
乖離の一部 (配線切れ・SSOT 改名・時計の値域) を CI で機械検出できるようにする。

## 3. 宣言表の書き方

### 3.1 フィールド (全定義は宣言表ヘッダのコメントが正)

- **name** — alert type / family key と一致する識別子 (`[a-z0-9_]+`)
- **claims** — 名乗る量 (日本語 1 文)。**検知器 docstring の estimand 記述と一致させる**
- **population** — 母集団。SQL/フィルタ条件レベルで書く (例: `oanda_trade_id != '' AND dedup_violation != 1 AND instrument != 'XAU_USD'`)。「LIVE」「約定」のような多義語だけで書かない
- **clock** — `wall` | `market_open`。取り違えは「毎週末誤発火」か「本物の週末停止を毎週見逃す」のどちらかを必ず起こす ([[lesson-live-fill-estimand-shadow-conflation-2026-09-03|同型教訓]]、`modules/freshness_policy.py` docstring の表が SSOT)
- **threshold_source** — 閾値の置き場 (`パス[:シンボル]`)。閾値を動かすときはここだけを動かす
- **detector** (任意) — 判定実装の場所
- **reader** — 検知結果が実際に人間へ届く経路のファイル (`"パス :: 検索文字列"` のリスト)。cron 定義 (`render.yaml`) / GitHub workflow / UI テンプレ。**reader の無い検知器は write-only** — `ON_DEMAND` (人手起動) は WARN として明示する
- **counterfactual_test** — **その系列の配線 (main() 呼出し / 読み手到達経路) を殺したとき落ちるテスト**のパス。挙動 (純関数) テストではない — 挙動テストが全部 green のまま main() から呼ばれなくなるのが 126 日 no-op の型。無ければ `"MISSING"`

### 3.2 書式の注意

PyYAML は requirements.txt に無い (監視チェッカーのために本番ビルド依存を増やさない —
デプロイ churn 教訓 [[deploy-churn-trading-gap-2026-08-21]])。チェッカーは厳格な
YAML サブセットを自前パースし、**逸脱は黙って読み飛ばさず ParseError で落とす**。
タブ禁止・1 行スカラーのみ・インデント 0/2/4/6 固定・行内コメント禁止。

## 4. 追加時のルール (運用契約)

**検知器を足す PR は以下 3 点を同一コミットに含める** (別コミット禁止 — KB WRITE ルールと同じ理由):

1. `monitoring/estimand_declarations.yml` への宣言 1 エントリ
2. reader 配線 (cron / workflow / UI のいずれかに実際に到達する経路)
3. counterfactual test (配線を殺すと落ちるテスト — 書いたら**実際に配線を殺して落ちることを確認**してから戻す)

既存検知器の claims (estimand 記述) を修正するときは、実装・docstring・宣言表を
同じコミットで揃える。乖離したまま片方だけ直すのが PR #221 以前の状態そのもの。

検証コマンド:

```bash
python3 tools/estimand_declaration_check.py           # ERROR 0 を確認 (WARN は既知負債)
python3 tools/estimand_declaration_check.py --strict  # MISSING 返済後の目標状態
```

## 5. 既知の MISSING 一覧と返済計画 (2026-09-10 時点)

宣言 14 系列中、counterfactual test 不在 = **8 系列** (+ 自動読み手なし 1 系列)。

| # | 系列 | 現状 | 返済案 | 優先度 |
|---|---|---|---|---|
| 1 | candidate_stagnation | 挙動テストのみ、main() 配線 pin なし | `test_anomaly_watcher_detectors.py` の TestMainWiring に `all_events.extend(check_candidate_stagnation` の source pin を追加 (engine_tick/live_fill と同型、~5 行) | 高 (安価) |
| 2 | db_write_probe | 同上 | 同上 (`check_db_write_health`) | 高 (安価) |
| 3 | disk_capacity | 同上 | 同上 (`check_disk_capacity`) | 高 (安価) |
| 4 | prereg_trigger_watch | evaluator テストのみ、quant_gate_status からの subprocess 配線 pin なし | `test_prereg_trigger_watch.py` に `quant_gate_status.build_report` が `prereg_trigger_watch` セクションを含むことの pin (test_m1 の型を流用) | 中 |
| 5 | shadow_promote_r2_alert | セル判定テストのみ。workflow 配線は本チェッカーが grep pin 済み | workflow 側の起動コマンド (`--apply-demote` フラグ込み) を source pin するテスト | 中 |
| 6 | trade_monitor_activity | **テスト自体なし**。閾値 4h がインライン定数 (freshness_policy SSOT 外)、週末 gate の閉場定義も SSOT と不一致 (金 22:00+日曜のみ — 土曜 00-22 を開場扱い) | 挙動テスト新設 + 閉場判定を `freshness_policy.market_open_hours` に寄せる修理 (別 PR、rule:R3) | 中 |
| 7 | demo_trader_watchdog | watchdog_alive を pin するテストなし | status payload に `watchdog_alive` が載ること + trade_monitor が読むことの pin | 低 (engine_tick が実効的に代替) |
| 8 | live_roster_attrition | counterfactual なし + **reader = ON_DEMAND** (自動読み手なし) | 分析ツールなので配線対象外が妥当。月次監査 (weekly-audit.yml) への組込みを検討するなら reader 化と同時に宣言更新 | 低 |

返済の完了条件: `--strict` が exit 0 になること。そこで CI の呼び出しを `--strict` に
切り替え、`tests/test_estimand_declarations.py::test_default_run_is_warn_not_fail_and_strict_fails`
の期待を反転させる (テスト内コメントに手順を記載済み)。

## 6. scripts/check.py への組込み提案 (親セッション向け・本 PR 非実施)

本 PR は規律により `scripts/check.py` に触れていない。提案:

```python
# scripts/check.py への追加案 (数行):
#   "estimand declarations": python3 tools/estimand_declaration_check.py
# を既存のチェック列に追加 (exit code をそのまま採用。WARN は exit 0 なので
# 既知負債で check.py が赤くなることはない)。
```

- CI (`.github/workflows/ci.yml`) は pytest 経由で `tests/test_estimand_declarations.py`
  が同じ検証を既に走らせるため、check.py への組込みは**ローカル実行の即時性**目的
- MISSING 全返済後は `--strict` に切り替える (§5)

## 7. 修理 PR 3 フィールド (混入日/発見日/発見手段)

`.github/pull_request_template.md` を新設した。bugfix PR のみ記入 (それ以外は N/A のまま)。
目的はメタ監査の「欠陥税 124 日」を**継続測定可能**にすること — 混入日と発見日が
PR に構造化されて残れば、潜伏期間の分布と「どの発見経路が仕事をしたか」(alert /
counterfactual / 人手 / 偶然) を四半期ごとに集計できる。集計主体は次回メタ監査。

## 8. 本 PR が変えないこと (スコープ境界)

- 本番挙動: 変更ゼロ (新規ファイル + テンプレのみ。既存 .py の編集なし)
- 検知器の閾値・ロジック: 変更ゼロ (宣言表は記述であって設定ではない — 閾値の SSOT は従来どおり各 threshold_source)
- `prereg-trigger-registry.json` / `scripts/check.py` / `CLAUDE.md` / `wiki/index.md`: 非接触
- §5 の返済 (テスト追加・trade_monitor の SSOT 寄せ) は別 PR

## 関連

- [[process-meta-audit-2026-09-07]] §4.2 R3 (起票)
- [[rnb-dead-mode-and-block-estimand-2026-09-05]] / PR #221/#224/#207/#209/#228 (事例)
- MEMORY: `project_live_fill_estimand_shadow_conflation_2026_09_03`, `lesson_validity_check_pins_proxy_2026_09_02`, `project_monitoring_blind_during_outage_2026_08_30`
- `modules/freshness_policy.py` (時計と閾値の SSOT — 宣言表の clock 列はここと一致させる)
