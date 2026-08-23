# Changelog — バージョン別変更と評価基準日

## 2026-08-23 — fix(deploy): 残存デプロイ churn を実測分解して恒久ゼロ化 (phase-2, rule:R3)

- **phase-1 の効果を推定でなく実測で確定**: PR #199 マージ (08-21T01:57Z) 以降の main 31 commit に対し Render が実際に走らせたデプロイは **4 件 = 1.7/日** (baseline 18.8/日 から **−91%**)。§4.2 の推定「7.9/日」は保守的に外していた (実測はその 1/4.6) — **以後この種の効果は Render deploy 一覧との突き合わせで報告する** ([[deploy-churn-trading-gap-2026-08-21]] §8)
- **残存源の全量分解** (ローカル再生が Render の deploy 一覧と 4/4 完全一致 = 網羅性の担保): (a) `analyst-memory.md` **3/平日** (daily_report の post_tokyo/london/ny)、(b) `bt-results/phase1b` + `data/sentiment` 1/日 (phase1b 日次 re-run)、(c) `raw/cell_deepdive/` 不定
- **(a) の再分類 — 「ランタイム read」は粒度が粗すぎた**: 全数 grep で参照経路は `_read_analyst_memory` (app.py:11651) → `get_analyst_opinion` (:11749) → `/api/analyst-opinion` (:12229) の**人手起動エンドポイントのみ**。`modules/` / demo_trader / signal / OANDA 転送からの参照は**ゼロ**、起動時ロードも無し。**助言メモの鮮度のために平日 3 回 × (無 tick ~60s + ramp ~2.5-3 分) ≈ 平日 10 分の劣化取引**を払っていた = 原則 1 違反 → 分類を **取引パス read / 助言専用 read / write-only** の 3 階層に改め、助言専用は ignore 可とした
- **代償の可視化 (サイレントにしないことが交換条件)**: ignore により本番 memo は最後のコード系デプロイ時点で固定される → `/api/analyst-opinion` 応答に **`memory_stale_days`** を同梱し陳腐化を観測可能に (`app.py::_analyst_memory_stale_days`)
- **🔴 副産物 — guard の抽出器がコメント行で黙って打ち切られていた**: `_ignored_paths()` の regex `(?:\s*-\s*.+\n)+` はリスト途中の `# ...` で停止し、以降の entry が検査の視界から消える。`data/**` を誤 ignore する counterfactual を注入しても **6 テスト全て pass** した (= 検査の無力化)。修正 + `test_ignored_paths_parser_sees_entries_after_inline_comments` で pin、修正後は同 counterfactual で 4 テストが落ちることを確認
- **drift guard を非 KB ルートへ拡張**: phase-1 の guard は `"knowledge-base"` 起点リテラルしか走査せず、`data/**` / `bt-results/**` を ignore した瞬間に穴が空く → `test_no_new_runtime_data_path_silently_ignored` を新設 (実測検出 = `data/cache/massive` / `data/cache/yield` / `data/_holdout_locked/MANIFEST.json`、`cached["data"]` 等の dict 添字は偽陽性ゼロ)
- **効果**: 同一 31 commit 窓の再生で would-deploy **4 → 0**。過剰抑制でないことの対照 = 直近 276 commit では **32 commit が依然デプロイを起こす** (`modules/demo_trader.py` / `tools/` / `tests/` / `.github/workflows/` / `prereg-trigger-registry.json` / `data/cache/yield/*.parquet` 等のランタイム read)
- **範囲外 (主張しない)**: 逸失 pip の定量化。主張は「不要な断続窓が構造的に存在し、その全量を実測で特定して消した」機構レベルの事実のみ
- 教訓: **設定リストにコメントを足す変更は、その設定を読むパーサ全部を疑え。guard 自身が無力化されても全テストは green になる — guard を触ったら counterfactual を注入して「落ちること」を必ず確認する**

## 2026-08-21 — fix(deploy): KB ドキュメント commit が取引エンジンを再起動する構造欠陥を是正 (rule:R3)

- **発見**: autopilot ヘルスチェックで本番 502 → 障害ではなく**自分の push が誘発した再デプロイ swap 窓**と判明。「1 commit で取引エンジンが止まる」構造に気づいたのが起点 ([[deploy-churn-trading-gap-2026-08-21]])
- **実測 (origin/main 14 日)**: web service デプロイ **18.8/日**、うち **78% が `knowledge-base/` のみの commit**。`autoDeploy: commit` に path filter が無く、ドキュメント更新がそのまま `demo_trader.py` の per-mode background threads 再起動になっていた
- **1 回のコスト (Render app ログ instance 追跡)**: 旧 instance 最終 tick 01:07:47.8 → 新 instance MainLoop 開始 01:08:47.2 = **完全無 tick ≈59.5 秒**、全 24 モード到達まで **+2m39s**、cold cache で tick#1 が 10s 級 (定常 0.6s)
- **最悪ケース実測**: KB commit が 2m22s 間隔で連続した結果、新 instance が **寿命 85 秒・全モード tick#1〜#3 の warm-up 未完了のまま kill**。連続 KB commit 中はエンジンが定常状態に到達できない
- **対策 (R3)**: `render.yaml` web service に `buildFilter.ignoredPaths` を追加。**ランタイム read パスは意図的に除外** — `wiki/tier-master.json` / `wiki/snapshots/` / `raw/trade-logs/analyst-memory*.md` / `wiki/decisions/prereg-trigger-registry.json` はデプロイを起こさせる。ignore 対象は write-only (`raw/hunt_events/`, `raw/bt-results/`) と純ドキュメントのみ
- **効果 (同一 14 日窓で再生)**: デプロイ **18.8/日 → 7.9/日 (−58%)** (263→110。merge commit は first-parent 差分で評価)。残存最大要因は `analyst-memory.md` (41件、シグナル経路外だがランタイム read のため保守的に残置)
- **再発防止** `tests/test_render_build_filter.py` 3 件: ignoredPaths 縮小検知 / **ランタイム read 巻き込み検知** / **drift guard** (`app.py`+`modules/` の KB 参照を regex 抽出し、ignore に match するものは write-only allowlist 必須)。故意の違反注入で赤くなることを確認済み (非 vacuous)。pyyaml 非依存 (`scripts/check.py` と同じ regex 方式)
- **範囲外 (主張しない)**: 逸失 pip の定量化。断続窓と発火の同時性は未測定 — 主張は「不要な断続窓が構造的に存在した」機構レベルの事実のみ
- 教訓: **CI の paths filter (T15 で撤廃) と CD の build filter は別問題。前者は「テストを回すか」、後者は「取引エンジンを殺すか」**

## 2026-08-19 — research(family-C): rate_anchor_deviation explore — 臨時裁定 #26 + pre-reg 凍結 + two-pass (rule:R1 手続き)

- **family C (user 水平線理論の機械核 v2 = 金利観測フェアバリュー帯乖離リバージョン) を臨時裁定で台帳 #26 に採用** (改訂 WIP 原則: 能動 explore 枠 0/3 + user 直接承認 2026-08-19「進めて」)。claim = PR #197 + edge-dev レーン cross-session 承認、explore 枠 1/3 消費
- **pre-reg 凍結** ([[family-c-rate-anchor-explore-prereg-2026-08-19]]): 片側 LONG onset イベント (2y 金利差 rolling OLS 帯、z 下抜けクロス、Z_th 機械選定) × +21bd 固定 horizon、explore 2014-2021 (介入ゼロ実測窓)、swap 込み・gross/net 分解報告、MoF #4 cross-LOCK 遵守 (OOS は介入隣接 partition)
- **敵対的検証 GO-WITH-CONDITIONS (blocking 10 条、[[family-c-adversarial-verification-2026-08-19]])** — 最重要 3 件を凍結前修復: ① 旧 gate C null が合成 probe で反保守 (type-I 20-29% @ 名目 5%) → **年内 demean + episode-block sign-flip + p≤0.02 較正**へ差し替え、② JGB Golden Week gap (実測 11 暦日) × staleness 5d 規則が 2019-2021 を連鎖 blackout → 12d へ、③ rates-content 識別不能リスク → b≡0 ablation 対照 + 解釈規則凍結
- ハーネス `tools/family_c_anchor_explore.py` (freeze/pass1/pass2/oos、4 点 OOS 機械ロック実装済み) + test pin 19 件。registry `family-c-explore-verdict-deadline` (08-29 backstop) 登録 → 同日 resolve
- **verdict = ❌ FAIL (同日 two-pass、期日 10 日前倒し、OOS 2022+ 非接触封印)**: N=41 (Z_th=1.5)、**gross −20.5p / swap −1.6p / net −24.2p (adverse −32.1p)** — 帯下 onset 後の +21bd は平均続落。gate C (timing 超過 vs 同年無条件ロング) p=0.527、LOYO 符号不安定 (JPY 増価年 2015/16/18 が負殺)。median +1.4p・WR 51% = 左テール支配 (falling-knife 型)。**h5 診断 (非 claim): 初週 +10.9p バウンス → 21bd で逆転** = 「dip は跳ねるが多週ホールドで死ぬ」
- **クローズ範囲発効**: 日次金利差アンカー帯 × USD_JPY × 帯下 onset LONG × 5-63bd 全変種。**user 水平線理論の機械核 v2 死亡 — 裁量スタック残余 = 執行層 (15m/1m) + exit 層のみ**。power caveat: MDE 131p、FAIL≠falsified だが点推定負 = 符号情報を持つ FAIL
- **副次所見**: ablation 対照 (価格のみ z) は Jaccard 0.167 で識別作動 + さらに悪い −65.8p = **USD_JPY 多週 dip-buy は 2015-2021 で機構を問わず負け**。E-C の介入 dip +188p (2026) は非介入 dip で再現されず = 介入型の固有性示唆 (09-18 A/B/C 統合裁定の一次材料)。ppp「USD_JPY だけ IC 負」prior が的中

## 2026-08-19 — fix(watch): 条件付きトリガの評価器レベル欠陥 — 「常時 WATCHING」を機械評価へ (rule:R3)
## 2026-08-19 — research(family-A): statement_ladder explore pre-reg 起草 (DRAFT、測定ゼロ) — 09-18 統合裁定の前提材料 (rule:R3)

- **family A (発言ラダー→介入確率) の explore pre-reg を DRAFT 起草** ([[family-a-statement-ladder-prereg-2026-08-19]])。起点 = `statement-ladder-foundation-readiness` resolve (PR #195、基盤 PR #194) + user「進めて」。claim = queue ticket + 本 PR (E23 方式)
- **estimand = ladder 検出器の較正 (hit / false alarm 率、価格全面不使用)** — dossier の指定どおり「発言ラダー先行 (N=4 記述)」の FP 率測定が本 family の仕事。primary = L≥4 遷移検出器 1 本 (m=1)、(T,R,H)=(5,20,20) 設計仮説、凍結は敵対的検証後に論拠のみで確定
- **正直な拘束を事前固定**: 有効 N=4 episode blocks → **全 verdict 記述級** (edge 主張不可) / **P-A1 = lexicon v1 語彙は 2022/2024 目視検証を経た in-sample 汚染チャネル** → クリーン判定は forward OOS のみ (Q3 開示 ~11-06 が最初の機会、エピソードゼロ四半期も FP 側検証として記録) / lexicon は PR #194 commit `569dbe3f` に pin
- **測定は未実施** (発言×介入ジョイント量ゼロ)。採否・explore 枠は 09-18 edge-supply-scan-monthly の A/B/C 統合裁定。台帳登録案 = #26 `statement_ladder_intervention_prob`。family B (介入イベント→回避/執行) は別 family として E-C 符号逆 prior を継承させる設計指示のみ記載

- **`info`/`conditional_info` 型が dispatch で無条件に `WATCHING` を返すハードコードだった** ([[lesson-trigger-reachability-evaluator-2026-08-19]])。`condition` フィールドの発火条件は **一度も評価されず**、条件が成立しても TRIGGERED にならない設計。ZN 教訓 (「条件を書く」と「条件が起こりうる」は別物) の **4 例目、初の評価器レベル**
- **実害**: `statement-ladder-foundation-readiness` は条件 (当局発言ラダー基盤の main 着地) が **PR #194 (`569dbe3f`) で既に成立済み**だったのに watching 表示のまま滞留。同トリガは family A (発言ラダー→介入確率) の pre-reg 起草ゲート = **能動測定ライン 0 本の状況で唯一動かせる供給ライン作業が黙って停止していた**。`deadline` も無視されており、期日付き手動エントリ (`volstate-split-*` / `carry-dip-v3-revival-watch`) は自分から期限切れを名乗れなかった
- **機械評価型 2 種を追加**: `artifact_presence` (glob + `min_files` の実ファイル判定 =「main に着地したら発火」型) / `data_coverage` (cache 被覆 max 日付 vs 閾値 =「cache が延伸したら発火」型)。取得不能は従来どおり `DATA_UNAVAILABLE` で cron を落とさない
- **`evaluate_manual_info`**: 手動判定エントリでも `deadline` 超過で TRIGGERED (`no-deadline` は無期限 watching のまま)
- **到達経路 lint** (`lint_reachability` / `--lint`、pytest 強制): 機械評価型でないエントリは `reachability` (誰/どのジョブが状態を進めるか) の明記を**必須化** — 5 例目の再発防止本体。現行 registry 違反 0 件
- **`statement-ladder-foundation-readiness` = TRIGGERED → resolve 済み** (会見 corpus 56 月次 jsonl / lexicon ladder スコア / forward 日次 cron を実ファイルで確認)。**family A の pre-reg 起草ゲート解除** — 09-18 スキャン (`edge-supply-scan-monthly`) の A/B/C 統合裁定の前提材料が揃った。⚠️ 基盤は**収集のみ**、発言×介入×価格のジョイント測定は別 pre-reg の観測前 LOCK まで禁止 (MoF #4 cross-LOCK 継続)
- `ws3-round4-eur-divergence-conditional` を `data_coverage` へ移行 → 実測表示 (被覆 2026-08-18 / 閾値 2026-11-15) に変化、延伸経路の実在も同時確認
- live/tier/lot 変更ゼロ。test 7 件新設 + 旧 pin 1 件を現行設計へ更新 (2645 passed)

## 2026-08-18 — feat(data): MoF 通信モダリティ収集基盤 — 介入 ground-truth / 会見 transcript / lexicon ladder / GDELT (rule:R3)

- **新データモダリティ (当局コミュニケーション) の収集基盤を新設** ([[mof-communication-data-infrastructure]]、`data/external/mof_statements/`)。起点 = user 介入主張のスコーピング wf_32d378df (MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` 追記4) — 主軸は「発言ラダー lexicon × 公式介入ラベル」、**X は ToS 上不使用**
- **⚠️ 収集のみ**: 発言×介入×価格のジョイント測定は別 pre-reg まで全面禁止 (MoF #4 cross-LOCK)。価格データ不使用・2026 介入日の価格推定なし (P-10 遵守)
- **介入 ground-truth**: 公式日次明細 CSV (1991-04〜) を正規化、凍結 legacy `mof_interventions.csv` と**行単位 383/383 完全一致**。新規 = 2026 Q2 開示 3 行 (04-30/05-04/05-06、Σ¥11,734.8bn ≒ 月次総額と符合)。**2026-06-29〜07-29 月次窓 = 介入額 0 (公式)**
- **会見 corpus 502 会見 (2022-01〜2026-08)**: online 387 + NDL WARP 115 (pywb `id_` 原本、旧 `.htm` 対応)。**MoF index の欠落 8 ヶ月 (202310-12/202601-04) から未リンク孤児 62 会見を日付総当たりで回収** (神田財務官単独会見 2 本を含む)
- **lexicon ladder v1** (`tools/mof_statements_lexicon.py`、Gnabo 系 talk/act 離散化 L1-L5 + no_comment、大臣側発言のみスコア、テスト 19 本): 目視検証 **PASS** — 2022 窓 (L0-2→09-02 L3→09-29 L4→10-03 L5) / 2024 窓 (L0→03-26 L3→04-02 L5) の両方でエスカレーション可視 (詳細テーブル: `reports/mof_statements_backfill-2026-08-18.md`)
- **forward 日次 cron 新設**: `tools/mof_statements_daily.py` + `.github/workflows/mof-statements-daily.yml` (JST 06:30 — 介入 CSV/会見/news.rss/GDELT、月ページ欠落時は日付プローブへ自動フォールバック)
- **観察事実**: 公式 CSV に 2026 Q2 日次明細が着地済み (08-07 公表) = **#4 pre-reg の verdict 期日 (着地+10 日) 超過中** → verdict 執行を別タスクとして起票 (本基盤では E-A/E-C 量を計算していない)

## 2026-08-18 — feat(automation): family C アンカー自動化パケット — 日次データ基盤 + E-A defensive alert + registry トリガ 3 点 (rule:R3)

- **user 承認 (2026-08-18「自動化させて」) の 3 点パケット** ([[family-c-anchor-automation-2026-08-18]])。live/tier/lot 変更ゼロ、シグナル計算ゼロの純データ基盤 + defensive monitoring
- **① rate-anchor-daily**: `tools/rate_anchor_ingest.py` + 平日 21:15 UTC workflow — MoF JGB 15 テナー (歴史+当月英語版) / FRED DGS1-10 / ZN=F 日足を `data/external/rate_anchor/` に union-merge 蓄積 (単調性 assert、決定的 manifest)。凍結 e20 パネルには非接触。シード済み: JGB 3,328 行 (→08-17) / US 3,554 行 / ZN 756 行。**材料のみ — フェアバリュー帯/乖離の計算は family C pre-reg まで構造的に不実施**
- **② intervention-watch**: `tools/mof_intervention_watch.py` + 00:20 UTC workflow — #4 §2.2 凍結 rule (X,Y)=(2.0, 0.25%) **as-is** で前 UTC 営業日を評価、candidate=1 で Discord 通知 + `knowledge-base/raw/intervention_watch/` JSONL 記録 (dedup 兼用)。**監視のみ — live gating 自動執行は不実装 (§5.5 Variant B = 別 pre-reg + user 承認)、candidate ≠ 介入ラベル、alert-grade (yfinance 1h) と verdict-grade (Massive 15m) を grade フィールドで分離**。test pin で order 系 import を構造遮断
- **③ registry トリガ**: `mof-monthly-total-2026-08-29-check` (user 7月「介入をくらった」説の答え合わせ、着地当日 user 報告) / `statement-ladder-foundation-readiness` (family A 基盤、並行 task_a3b5b005) / `edge-supply-scan-monthly` 増補 (09-18 = A/B/C 統合裁定)。**全トリガに到達経路を明記** (ZN 教訓)
- test 22 件新設 (`tests/test_rate_anchor_ingest.py` / `tests/test_mof_intervention_watch.py`) + registry pin

## 2026-08-17 — research(E22): VRP explore ❌ FAIL (IC −0.025 p=0.760、OOS 非接触) — vol モダリティ恒久クローズ (rule:R1 手続き、台帳 #24)

- **E22 (通貨 VRP = EVZ−RV21 × EUR_USD × 21bd 時系列 IC) の凍結 explore を単独 wave で執行** ([[e22-vrp-explore-prereg-2026-08-17]]、scan 第 3 次 §2/§2.1 の explore 枠 1/3)。敵対的検証 GO-WITH-CONDITIONS (17 条 / blocking 10 条) 全消化 → 🔒 凍結 `f50b680a` → two-pass 測定
- **verdict = explore FAIL (gate C+D+F 同時不通過)**: 両側 circular-shift p = **0.760**、IC = **−0.0249 ≈ 0** の完全 null (N=2,066 / 非重複窓 98)。stressed-net は adverse **−11.2p**・point 端でも **−3.1p** — **swap −16.2p が gross +8.9p を支配** (21bd hold の事前記録どおり)。年次符号 5/8・LOYO 7/8
- **クローズ範囲 (凍結どおり発効)**: 通貨 VRP 全変種 × G10 × 日次〜月次 + 無料 proxy (EVZ/VXFXICLS) — **E24/E25 棄却と合わせ vol モダリティ恒久クローズ、生存モダリティ 6→5 系統**。power caveat 凍結済み (FAIL ≠ falsified、検出力 8–17%、引用は estimand 監査必須)。復活 = 有償 OTC 面 + 新 family + 新敵対的検証のみ
- **§2.1 事前コミット節の帰結執行**: OOS 2022-01..2025-03-11 非接触封印 / **Databento 有償調達の user 決裁は不要化** (PASS 時のみの決裁点だった) / 無料で vol モダリティに白黒 = 主目的達成。外部/新規 family 系統の explore→OOS 生存 **0/16** に更新
- **副産物**: EUR_USD 15m の **2020-10-23..11-16 MASSIVE ベンダー穴を OANDA mid backfill で修復 (+1,440 行、米大統領選挙週回収、`tools/e22_gap_backfill.py`)** — 敵対的検証が実測発見した未開示穴。EVZCLS.csv (FRED、確定終了系列) を git 追跡化 + sha256 manifest 凍結
- **能動的に動かせる供給ラインは E21 (帰属分解、user 決裁 registry 08-31) のみに** — 残りは全て calendar-lock (E12 2027-02 / E1 10-15 / #22 ECG 11-06)。E23 はゲート解除済み (起動判断は次スキャン)。live/tier/lot 変更ゼロ

## 2026-08-17 — research(E7): phase-1 verdict ❌ FAIL (discovery 0/24、OOS 非接触) — イベントモダリティ枯渇、E12 格上げ (rule:R1 手続き)

- **E7 phase-1 (指標サプライズ directional) を期日前倒しで執行** (凍結期日 08-21 の 4 日 / verdict 08-28 の 11 日前倒し、[[e15-e7-event-modality-prereg-2026-07-18]] §13、PR #182)。排他 claim = queue ticket + draft PR (race 対策の初適用)
- **verdict = FAIL (discovery 段)**: §5b 選抜通過 **0/24 → m₁=0**。実効空間 (θ=0.5、12 combo) は time-exit EV 全て負 (−0.31〜−8.15p/trade、N 287–416、blocks 41–62) — power 不足でなく**サプライズ方向 drift の符号が系統的に逆** (発表後 overshoot 回帰と整合)。SIGN-FLIP は §6 事前宣言どおり記述記録のみ (fade 追試 = 新 family + 敵対的検証、phase-0 CPI fade C5 が負の prior)
- **OOS 窓 (2024-01〜2026-06) は結合統計未接触のまま保存**。θ=1.0 は §3.3c 予告どおりゲート機械脱落
- **機械ガード全 green**: parquet 台帳再現 13/13 / census-e7 が §3.3c pre-flight と完全一致 (41/62/22/31、19/16/8/5) / 符号・estimand の手計算 spot check (2020-06-05 NFP z=+30.79 × USD_JPY、+10.46p 一致) / self-test 24-combo 結線
- **§8 固定分岐発動: 両 phase PASS=0 → イベントモダリティ (カレンダー/サプライズ × M15 spot) を枯渇と判定、E12 (CME volume flow、first look 2027-02-05) を供給ライン主候補へ格上げ**。E23 (中銀声明テキスト、E7 verdict までゲート) は本日からゲート解除 = 台帳の次回評価対象
- ハーネス: `event_modality_explore.py` に discovery-e7 / census-e7 / self-test-e7 モード追加 (lib 変更ゼロ — E7_HORIZONS/uncond rule は設計時から準備済み)。test pin 4 件新設 (`tests/test_e7_phase1_explore.py`)。registry `e15-e7-event-prereg-phase1-verdict` resolved

## 2026-08-14 — research(scan): 月次外部仮説スキャン第3次 + 四半期モダリティ棚卸し + ZN=F キャッシュ構造欠陥修復 (rule:R3)

- **月次スキャン第3次を期日 (08-18) の 4 日前倒しで実行** ([[external-hypothesis-scan-round3-2026-08-14]])。起動理由 = WIP 原則は名目 3 系統で充足していたが、**実態は 5 系統すべて calendar-lock 待ちで探索アクティブ枠 0/3** が 9 日間継続していた。「在庫はあるが着手可能な仕事がゼロ」は WIP 原則が防ごうとしている状態そのものと判定
- **裁定**: 採用 2 / 保留 1 / 棄却 2 — **E21 human_signal_stream (user 手動実績の帰属分解、S2 診断枠)** + **E22 通貨 VRP (IV−RV、explore 枠 1/3・条件付き)** / 保留 E23 中銀声明テキスト (E7 verdict 08-28 までゲート、multiplicity 二重取り回避) / 棄却 E24 global vol risk (2026 年新研究が horizon >3ヶ月を再確認 = round-2 の E17 棄却を補強)・E25 synthetic vol surface (Yahoo 価格由来 = 価格モダリティ再着せ替え、E13 同型)
- **E22 の事前コミット節を on-record 化**: explore/OOS は**無料で完結**する (EVZCLS 実測 4,529 行、OOS 終端 2025-03-11) が、**forward の無料経路はゼロ** (EVZCLS 廃止確定 / `^EVZ` delisted / CME scrape は ToS 禁止 / Databento 有償)。よって **PASS = 「live 実装承認」ではなく「有償データ調達の user 決裁点に到達」の意味のみ**。user が調達しない判断をした場合に設計を緩める再訴訟を禁止。枠を使う正当化 = 無料で vol モダリティに白黒がつく非対称
- **E21 のスコープ制限**: estimand は 4 分解 (swap / spot ドリフト β / タイミング残差 α / サイズ寄与) の**会計**であって WR 統計ではない (MEMORY 明示指示)。**M2/M3 直接寄与は小さいと前置** (無レバ carry +0.3-0.4%/月、20%/月には ~25x = unwind 即死)。α≈0 でも human-signal-stream 系統を恒久クローズできる情報価値がある
- **四半期モダリティ棚卸し (初回)**: 閉鎖判定の巻き戻し **ゼロ** (12 モダリティ全て前提有効、うち E17 は新研究で強化)。**生存モダリティは 6 系統のみ、うち能動的に動かせるのは E21/E22 の 2 系統だけ**と確定
- **入手性 re-check で 2 件悪化・1 件構造欠陥を検出** — 悪化: EVZCLS 右端 2025-03-11 で確定終了 / VXFXICLS 2022-02-11 終了。**構造欠陥 = ZN=F 1h キャッシュ (下記)**
- **ZN=F キャッシュ構造欠陥 (R3、本 PR で修復)**: `modules/yield_data.py` が rolling 窓 API の結果でキャッシュを**無条件 overwrite**。`interval="1h"` は period=60d を選ぶため、**一度呼べば 12,760 行が 1,162 行に潰れる**。しかも **2024-02-18→2024-03-21 の約 1 ヶ月は既に yfinance 窓外 = ファイルにしか存在しない**。修正 = `merge_bar_cache()` で union-merge (行数単調非減少 / 重複は fresh 採用) + 1h period を 730d へ + **test pin 7 件**。実行結果 **12,760 → 14,175 行 / 右端 2026-05-15 → 2026-08-14、左端 2024-02-18 保持**
- **到達経路のない registry 条件を是正**: `ws3-round4-eur-divergence-conditional` の発火条件 (cache が 2026-11-15+ へ延伸) は、**キャッシュを伸ばすジョブが存在しなかったため構造的に到達不能**だった (毎日 "watching" 表示は健全性の証拠にならない)。`.github/workflows/zn-cache-refresh.yml` (週次 UTC 月 06:40) を新設して伸長経路を実在させた
- **教訓ページ**: [[lesson-rolling-window-cache-overwrite-2026-08-14]] — rolling 窓 API のキャッシュは union-merge が既定 / 条件付きトリガ登録時は到達経路を message に明記する
- **パイプライン運用規則の追補**: WIP 充足判定は「S1-S4 の本数」ではなく **「今日着手できる本数 ≥1」** で行う ([[edge-development-pipeline-2026-07-18]] §5)
- **registry**: `edge-supply-scan-monthly` 期日 08-18 → **09-18**、`ws3-round4-eur-divergence-conditional` に修復注記
- **評価への影響: なし** — live / tier / lot / Kelly は一切不変更 (純研究 + データ基盤)

## 2026-08-12 — docs(KB): ps_aud_jpy demote 可否 user 決裁 — 見送り採択、LOCK watchdog に委任 (rule:R2 手続きクローズ)

- **user「進めて」(2026-08-12) で推奨案採択**: 549250 (−123.2p) 事故起点の demote 提案 ([[mc-ruin-dashboard-artifact-2026-08-05]] #3) は **demote 見送り** — LOCK 済み基準 (watchdog Live N≥10 EV<0 / N=15 Wilson<0.40 / 2週連続 EV<0 / catastrophic SL率>30%) が唯一の判定器。horizon 損失 cap の R1 amendment は起案しない
- 決裁時状態: 08-04 以降 ps 発火ゼロ (live N=2 のまま、前提不変) / watchdog cron 稼働中 (監視主体併設要件充足)。以後の ps 判定は完全自動 — これで 549250 事故の全 disposition がクローズ
- **評価への影響: なし** (live/tier/lot 全て不変更 — 現状維持の正式化)

## 2026-08-12 — docs(KB): ps carve-out 復帰初週 再ゲート disposition — 席枯渇で初週窓は無効、#172 後へ再アンカー (rule:R3)

- **registry `ps-carveout-firstweek-regate` (期日 08-11 超過で stale 点灯) を決着**。**demote せず** — pre-reg 条件 live N≥10 に対し実測 **N=2**。N ゲートを事後に下げることはしない。詳細: [[ps-carveout-firstweek-regate-disposition-2026-08-12]]
- **実測 (本番 `/api/demo/trades`、date_from=07-28 の 1,427 行)**: ps 行 **8** (全て `price_shock_rev_aud_jpy_h1_long` / AUD_JPY / BUY)、うち **clean live 2** (`oanda_trade_id != '' ∧ dedup_violation != 1`) / shadow 6。他 4 セルは発火ゼロ。live 実績 = 07-29 **+0.6 (WIN)** / 07-31 **−123.2 (LOSS)** = 計 −122.6p
- **(a) AGG_KELLY BYPASS 監査 → carve-out は機能、初週の律速は「席」**: Render app ログ (07-29〜08-01) に AGG_KELLY block はゼロ。支配的なのは `[SHADOW] Slot bypass: price_shock_rev_aud_jpy_h1_long ... (live=1/1 shadow=1/2 → shadow)` で **13 分間に 16 行** = live 席が埋まり ps が shadow へ迂回。**初週の N 不足は carve-out の失敗ではなく席供給の枯渇** → **PR #172 (merged 08-11) で是正済み**。よって初週窓 (07-28〜08-11) は carve-out の EV を測る窓として**無効**と判定し、評価窓を #172 後へ再アンカー
- **(b) exit 分布 → ✅ BE_LOCK OFF 実効**: clean live 2 件は**両方 `close_reason=horizon`** (早期 BE/trail exit なし)。N=2 のため「2/2 一致」水準の証拠と明記。`SL_HIT` ラベル衝突 (2026-08-07) の影響圏外
- **(c) estimand 整合 → ⚠️ 潜在的不整合・現時点の影響ゼロ**: `price_shock_rev_live_watchdog.py` (N≥10 で auto DEMOTE) と `price_shock_rev_promote_evaluator.py` (N≥30 で lot ramp 提案) は非 canonical な **`is_shadow=0`** で live 判定し `dedup_violation` 除外を持たない (KB 規約は `oanda_trade_id != ''`)。**ただし実測乖離ゼロ** — 06-01 以降 7,761 行で `is_shadow=0 ∧ oanda_trade_id 空` = **0 件**、`dedup_violation=1` は shadow 側のみ。**バグとして起票せず**、canonical 判定へのハードニングは別タスク (auto-demote を握るため単独 PR + test pin)
- **registry**: 初週エントリを resolved 化 + 後継 **`ps-carveout-regate-post-172`** 新設 (`live_count_decision`、prefix 一致、since 2026-08-11、N≥10 で EV/Wilson 再判定、backstop 2026-09-30。期日で N<10 なら供給側の別問題として stale レビュー)
- **live パラメータ / tier / lot は一切不変更**。M1 見通しも不変 (wg + ps の live N 蓄積待ち)

## 2026-08-12 — research(E7): phase-1 pre-flight — サプライズパネル凍結と power 開示 (θ=1.0 の 12 combo が結果観測前に脱落) (rule:R1)

- **pre-reg §11 の 2026-08-14 マイルストン (FF gap scrape + データ付録凍結) を 2 日前倒しで完了確認**。§3.3c として追記 ([[e15-e7-event-modality-prereg-2026-07-18]])。**価格データ非接触・イベント×リターン結合統計は未計算** (§10-1 遵守) = 結果観測前の記録
- **価格側 pre-flight**: `e15_e7_data_refreeze.py --verify-only --root <repo>` = **13/13 OK** (台帳 3 点再現)。discovery (08-21) / OOS verdict (08-28) の BLOCKED 要因なし
- **サプライズパネル新設** `tools/e7_surprise_panel.py` — §6 の z = (actual − consensus)/σ_trailing (直近 24 releases、strictly trailing) を機械化。canonical NFP 149 / CPI 149 × R4F forecast × actual (R4F 231 + BLS first print 66、**欠落ゼロ**)。成果物 = `raw/bt-results/e7/e7_surprise_panel.csv` + `e7_surprise_coverage.json`
- **block 実測 (block = イベント、primary 7 ペアが同時発火 → N ≈ blocks×7)**: NFP discovery θ0.5 **41** / θ1.0 22、CPI discovery **62** / 31、NFP OOS **19** / 8、CPI OOS **16** / 5
- **帰結 1 — θ=1.0 の 12 combo は結果を見る前に構造的脱落**: 4 セル全てで §5b(iii) ≥40 も §5c B(d) ≥15 も不達。選抜の必須条件なので**凍結候補にすらならない** → 実効候補空間 **24→12 combo (θ=0.5 のみ)**。**grid/θ/ゲート/α 会計の定義は一切変更していない** (§10-2 遵守、これは可用性の開示であって設計変更ではない)
- **帰結 2 — NFP θ=0.5 discovery は knife-edge (41 vs ゲート 40)**: イベント 1 件の増減で NFP 系 6 combo が消える。ゲート値は凍結済みなので動かさず、凍結表に脆さを併記する規約を宣言
- **帰結 3 — modal 予想を事前記録**: OOS blocks 19/16 → 検出可能平均効果 ≈ 0.33σ_h (NFP) / 0.36σ_h (CPI) = 大効果のみ。**phase-1 の modal outcome も C3 (UNDERPOWERED) または C5** と今宣言 (結果後の言い訳封鎖、phase-0 §9 と同規律)
- **σ_trailing warm-up の帰結 (規則から機械的、裁量ゼロ)**: 各系列の最初の 24 イベント (2014-01〜2015-12) は z 不定で discovery から自動脱落 (120→96)。R4F データ開始が 2014-01 のため pre-2014 充当は不可能
- **除外は宣言済み 1 件のみ**: CPI/OOS の 2025-12-18 (forecast 欠落、§3.3b-6(i) で観測前宣言)。事後裁量による除外ゼロ。§8 DEFERRED 条件は不発 (13/13 ペア OK)
- **test pin** `tests/test_e7_surprise_panel.py` (7 tests): 単位規約 / strictly-trailing σ / **look-ahead canary (未来 release 差し替えで過去 z 不変)** / block ゲート / 実測 block 数の回帰 pin。live/shadow/Kelly/tier は**一切不変更** (純研究)

## 2026-08-09 — fix(live): DT `ctx.hour_utc` が live で 12 に凍結 — 全DT戦略の時間帯ゲートが BT と別物だった (rule:R3)

- **`t9-kalman-d7-fire-info` の 0-fire (実測 0.00/週 vs 期待 3.9/週) の分母調査から発見**。`compute_daytrade_signal` の DT 用 `SignalContext` 構築が `bar_time` 不在時に `hour_utc=12` / `is_friday=False` へ固定フォールバックしていた。**`bar_time` を渡すのは BT 経路のみ** (`app.py:6679/7121`)、**live 経路 (`demo_trader._tick` → `compute_fn(df, tf, sr, symbol)`) は渡さない** → live の DT 全戦略が「常に UTC 12:00・常に金曜でない」前提で時間帯ゲートを評価していた。潜伏 **123 日** (`9c849cef` 2026-04-08 の DT構造改革で再混入。2026-04-04 に同型バグを一度修正済み = **回帰**)
- **証拠 3 系統**: ① code derivation (live 呼び出しが位置引数 4 つ)、② **本番 QUALBAR 実測** — `[kalman_d7] QUALBAR` 12 行が実バー 03:00〜21:15 UTC に散らばるのに**全行 `hour=12`**、③ **自然実験** — `ctx.hour_utc` 直読み群は BT 窓外発火 **83/237 = 35.0%**、`df.index` から自前導出する回避策を持つ群 (turtle_soup / london_session_breakout の redesign_v2) は **0/28 = 0.0%**、**Fisher exact one-sided p = 1.32e-05**
- **実害**: (a) h=12 が窓の穴に落ちる戦略 = **live 発火が構造的に不可能** — kalman_d7×3 variant (LIVE 化から **73 日 0 fire**)、pd_eurjpy_h20 (h==20)、tokyo_range_breakout (7-9)、london_ny_swing (13-17)、tokyo_nakane (00:45-01:15) は shadow N すらゼロ = **探索母集団から消えていた**。(b) h=12 を通す戦略 = 時間帯ゲート常時開放 — squeeze_release_momentum は発火の **86.7%** が BT 窓外、liquidity_sweep 50.0% / inducement_ob 26.7% / trendline_sweep 8.4%。(c) `is_friday` が常に False → **金曜ブロック (`FRIDAY_BLOCK_HOUR` 13〜18) が live で一度も作動していなかった**
- **Rule 3 根拠 = 同一関数内の内部矛盾**: 4 行上の `is_trade_prohibited` は当初から `bar_time if bar_time else datetime.now(timezone.utc)` と正しく降りており、scalp が使う `SignalContext.from_df` も `bar_time → row.name → now()` と正しい。**壊れていたのは DT 経路の直接コンストラクタ呼び出しだけ**。統計的新規主張ではないため 365日BT 不要
- **修正**: DT ctx の時刻導出を `bar_time → df.index[-1] → now(UTC)` に統一 (naive は UTC 扱い / aware は UTC 正規化)。`modules/data.py` が fetch 経路 index を UTC 正規化済みのため live の `df.index[-1].hour` は UTC 時刻。**BT 経路の契約は不変** (明示 `bar_time` が最優先)
- **監視配線バグも同時修正**: 退避条件を載せようとした `prereg_trigger_watch` の `live_count_decision` が `match: prefix` を `fetch_live_count` へ渡しておらず、kalman (1セル=3 entry_type) の live 件数が**恒久的に 0 = 監視が沈黙**する状態だった (T5 の 18 日執行ギャップと同型)。`count_live_matching(prefix=)` を shadow 側と同契約に
- **回帰 pin**: `tests/test_dt_ctx_hour_utc_live.py` (9 tests、**修正前ソースで 7 件が落ちることを検証済**) + `test_prereg_trigger_watch.py` に prefix/配線テスト 2 件。全 suite 2561 passed / `check.py` 全9チェック通過
- **修正の作用方向**: 制限側 (trendline_sweep / squeeze_release_momentum / inducement_ob / liquidity_sweep / post_news_vol / ema200_reversal) = **BT 検証済み設計への復帰で安全**。開放側の大半は shadow のみ = **N 蓄積の回復** (原則4)。唯一 **kalman_d7 は `KALMAN_D7_LIVE_ENABLE=1` (本番 effective) のため live 発火が始まる** — ただし 2026-05-28 に user が option B で明示決裁した設計 (lot 0.5×) を初めて実際に動かすものであり新規昇格ではない (Rule 1 対象外)。決裁時の退避条件を機械監視に載せるため registry に `t9-kalman-d7-live-n10-ev-check` (live N≥10 で EV 判定、期日 2026-11-30) を新設
- **既存判定の訂正**: [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] §6.5 の「INCONCLUSIVE = 設計対象外局面」は**誤診**と確定 (DIST fail は事実だが、通過していても session gate で必ず落ちていた)。**live/shadow 発火数に依拠した過去判断は本バグの影響を受ける**が、BT/探索側の verdict (WS3 の lfr / htf_fb / T10 / T11 等) は `bar_time` を持つため**影響なし**
- **評価への影響**: tier/lot/live 送信可否は**不変更**。clean live 負エッジ (−242.6p / payoff 0.274) の説明変数が 1 つ増えた (エッジ消滅ではなく執行窓の逸脱による寄与) — 分離定量は修正デプロイ後の N 蓄積待ち。詳細: [[dt-ctx-hour-utc-live-freeze-2026-08-09]]

## 2026-08-07 — fix(live): `SL_HIT` ラベル衝突 — 勝ち決済が SL 狩り防御を発火させていた (rule:R3)

- **08-05 daily 提起の「`SL_HIT` の 46.2% が正 PnL」を解決。汚染ではなく「ラベル衝突」**: `close_reason="SL_HIT"` は「**現在の** SL に価格が触れた」の意味しかなく、BE-lock / トレーリング / Profit Extender が SL を entry より利益側へ動かした後の**利確 exit** も同じラベルになる。データは正しく、名前と下流の解釈が誤っていた
- **本番実測 (N=3308, `/api/demo/trades`)**: SL が**利益側** 1894 本 → 97.6% が正 PnL (中央値 +2.00p / MFE 中央値 5.70p) / **リスク側** 1414 本 → 99.6% が負 PnL (中央値 −6.95p / MFE 0.00p)。**誤分類 1.5%** = SL 位置は事実上完全な判別子。`outcome` 内訳 = **WIN 1792 (54.2%)** / LOSS 1441 / BE 75。08-05 の 46.2% は小標本 (106本) ゆえの**過小評価**だった
- **実害 (live 挙動)**: `_sl_hit_history` を消費する防御 2 本が「ストップ狩りに遭った」前提で動く — ① **cascade cooldown** = 同一ペアの**全戦略**を 45–600s ブロック、② **Fast-SL 適応防御** = 次エントリーの SL を ATR×0.3 拡大。**発火イベントの 54.2% が勝ち由来の誤発火** (Fast-SL 側は 315 件中 180 = 57.1%)。誤発火は USD_JPY 494 / GBP_USD 444 / EUR_USD 306 と**主力ペアに集中**し、4原則 #1「攻める」/ #4 に反していた
- **Rule 3 根拠 = 設計の内部矛盾**: 同じ close 経路の**直前**のブロック (`if outcome != "WIN":` → `_last_exit` / `_total_losses_window`) が「SL 後の再エントリー防止」という**同一目的で既に WIN を除外**しており、隣接する 2 ブロックが非対称に書かれていた。統計的新規主張ではないため 365日BT 不要
- **修正**: ① `demo_trader.py` の履歴記録を `close_reason=="SL_HIT" and outcome != "WIN"` に (BE 75 本は逆行スイープの証拠として**防御に残す**ため `=="LOSS"` ではなく `!="WIN"`)、② `learning_engine.sl_losses` / ③ `daily_review.sl_hits` を `outcome=="LOSS"` で絞る — 両者は「SLヒット率 >60/70% → **SL幅拡大検討**」を焚く advisory で、生カウントでは **82.7%** (真の損切り率 **36.0%**) となり勝ちの多い book に SL 拡大を勧めていた。④ 回帰 pin `tests/test_sl_hit_history_win_guard.py` (4 tests、修正前ソースで落ちる負のコントロール検証済)
- **意図的に見送り**: `close_reason` の改名 (`TRAIL_EXIT` 等) は既存 3308 行と全 BT/分析ハーネスの estimand を非可換に壊すため**しない** — ラベル据え置き・消費者側を正す方針。shadow 行の混入是非 (誤発火 1792 件中 1786 が `is_shadow=1`) は scope 外で継続課題
- **波及**: `shadow_demote_registry.py:40` の demote 根拠「SL_HIT 56.2%」は本汚染値そのもの → 再検討要 (保守側ゆえ緊急性なし、R2 で別途)。**今後 `close_reason` 起点の分析は `outcome` 分割を前提とすること**。MEMORY `project_be_trail_inflates_python_bt_wr` と同一機構が live 側にも出ていた
- **評価への影響**: tier/lot/live 送信可否は**不変更**。変わるのは防御の誤発火が消える点のみ (エントリー機会の回復方向)。詳細: [[sl-hit-label-collision-2026-08-07]]

## 2026-08-05 — fix(bt): daytrade/scalp BT phantom-loss 記帳修正 — LOSS を実効ストップ基準に (rule:R3)

- **R3 調査完結**: sr_anti_hunt×EUR_JPY BT の 05-05 WR84.9% → 08-05 WR0.0% 反転は **regime ではなく `d87d5b6c` (2026-05-15) の `_BT_ABLATE_BE_TRAIL` default 反転**が直接原因。加えて **phantom-loss 記帳バグ**を発見: time-decay tightening (MAX_HOLD×50%) で entry まで引き上げた stop の退出 (実損≈0) を、`actual_sl_m` が「fut_close >元 SL 時のみ設定」のため planned `sl_m` のフル損失で計上。anti-hunt 系は BT の SL 再計算 (QH 前 TP距離/1.2) で sl_m=6.5〜11 ATR となり **1 件 −8.3R 級の架空損失** (trade dump で bars_held 12-17 集中 + actual_sl_m: null 全件を実証)
- **修正**: daytrade/scalp 両エンジンの LOSS 記帳を実効ストップ (`_dt_current_sl`/`_current_sl`) 基準化 + gap なし分岐でも actual_sl_m 必須設定。tools/sr_anti_hunt_bounce_shadow_bt.py `_pnl_r` の `or 1.0` falsy ガードが正当な 0.0 を coerce するバグも修正。run_backtest(1H)=非発現 / run_1h_backtest=既に close-based で対象外。回帰 pin `tests/test_effective_stop_loss_booking.py` (4 tests)、全 suite 2521 passed
- **判定への影響**: 08-05 cell BT の **EV_R=−8.30 は引用禁止** (gate FAIL 結論と forward 枠は不変)。05-05 の WR84.9% は optimistic 虚構 (BE 退出→+0.6×TP credit) で同じく引用禁止。**ablated BT の WR は wide-TP (≳3ATR) 戦略で構造的 ≈0 → wilson_lo 型 R1 ゲートは TP≲2ATR geometry 限定、wide-TP は TV Pine / shadow live で判定**。d87d5b6c 以降の daytrade/scalp BT 絶対 EV は decay-LOSS 比率×sl_m に比例して過大悲観 (相対比較は方向性有効)。詳細: [[bt-harness-effective-stop-booking-2026-08-05]]
- **評価への影響**: live/shadow/tier/lot/Kelly 全て不変更 (BT 評価ロジックのみ)

## 2026-08-05 — docs(KB): ロット階段 R1 パケット標準テンプレ事前凍結 + 計算ツール (rule:R3、live 変更ゼロ)

- **セル・ポートフォリオ論 (user 合意 2026-08-05) 執行項目②**: G3 到達セルの lot 昇格手続きを事前凍結 — [[lot-ladder-template-2026-08]]。標準階段 L0 1000u → L1 5000u → L2 10000u → L3 30000u、昇格 = 段ごと R1 + user 承認 (SLA 48h) / 降格 = R2 自動 (D1 slippage / D2 at-rung 出血 / D3 disaster / D4 合成 DD 4/6/8% NAV / D5 Wilson gate 割れ) の非対称を凍結
- **推奨 lot = min(6 上限)**: half-Kelly 2 基底 (本番 `kelly_fraction` 式同期) / worst-case イベント損失 ≤2.5% NAV / 証拠金 worst-case 同時 ≤40% NAV (25x) / exposure 20k cap / MC P(セル DD>2% NAV, 12mo)≤5% (`monte_carlo_ruin` JPY 建て)。台帳は broker 実約定 JPY のみ (D-a/D-e 整合)
- **計算ツール**: `tools/lot_ladder_calc.py` (§8 パケット機械生成、手計算禁止) + `tests/test_lot_ladder_calc.py` (25 tests、テンプレ worked example を数値 pin)
- **wg 事前充填の主発見**: ① Wilson gate (D-d 拘束) は wg 級統計で **N_required=41 > G3 の 30** = G3 到達≠即増額、② wg の binding constraint は Kelly でなく **disaster SL 150p** (U_cellDD ≈ 5.4k → L1 が実質上限 @NAV 326k)、③ 3 ペア同時セルの L2+ は exposure 20k cap 改定 R1 同梱必須。単一セル垂直増額では thesis に届かない = セル 2〜5 本の合成が必要という算数を再確認
- **評価への影響: なし** — 全セル lot/tier/live 経路不変更。第 1 適用は wg G3 到達時 (fill 修復前提、ETA 2027-05 @現ペース)

## 2026-08-05 — fix(risk): dashboard MC ruin の資本整合 (D-b 完結) + 549250 事故 disposition (rule:R3)

- **「MC ruin 0%→100% 反転」(08-04 daily) の解剖**: gate 側 (`_get_ruin_probability`、実際に live 送信を止める方) の実測 = **ruin 0.0** (post-cutoff 全 N=566 + JPY 整合資本 5,801p、audit に mc_ruin block ゼロ) — **運用凍結は起きていない**。100% は dashboard 専用の三重 artifact (30d n=10 窓 × 資本 1000p ハードコード取り残し × 単位不均一 pip 系列)
- **修復**: `/api/risk/dashboard` の `compute_risk_dashboard` に gate 側と同一式の `initial_capital` (OANDA_EQ_BASE_JPY/OANDA_JPY_PER_PIP_AVG) を接続 + n<20 低信頼フラグ。同一 n=10 系列で ruin **1.0→0.0**。D-b (Track C) が gate 側だけ直して dashboard 側が取り残された「同じ事実の片方欠落」の完結。pin `tests/test_mc_ruin_dashboard_capital_align.py`
- **549250 (−123.2p) disposition**: 実損 ¥1,232 = NAV 0.34%、設計 horizon exit の範囲内。#4 tp=151.25 は placeholder 設計 (バグ非該当、R3 チェック完了)。#2 live_tier_exempt は pre-reg 承認済み estimand (regime veto 追加は Post-hoc tune 禁止に抵触、変更は R1)。#7 wg 非約定 = MARKET_HALTED 確定済み (2cf940f7)。**#3 ps demote 可否は user 決裁材料として整理 (推奨: LOCK の watchdog に委ねる / 代替: horizon 損失 cap の R1 amendment)**。詳細: [[mc-ruin-dashboard-artifact-2026-08-05]]
- **評価への影響**: 表示計量の修正のみ — live/tier/lot/gate 閾値は全て不変更 (Gate2-4 は他条件で引き続き閉)

## 2026-08-05 — docs(KB): sr_anti_hunt_bounce×EUR_JPY R1 昇格判定 NO-GO → forward 確認 pre-reg (rule:R1 手続き、live 変更なし)

- **user「進めて」(2026-08-05) による R1 パケット起案を精査の結果 NO-GO 裁定**: ①起案動機 p=2.2e-11 は dedup_violation 除去 (23/67 重複 emit) 後 **EV t p≈0.094 = n.s.** に減衰、②累計 +272.4p は 2026-05 単月依存 (5月除外で −53.3p)、③live N=4 符号逆、④事前宣言ゲート付き 365d cell BT は **ハーネス整合破綻を検出** (同一ハーネスが 05-05: WR84.9% → 08-05: WR0.0%、9ヶ月重複窓で反転 = app BT パスとの機械的不整合、R3 調査タスク発行) で評価不能。vix pilot 失敗構図より弱い証拠での昇格を回避
- **forward 確認枠 LOCK**: セル凍結 = EUR_JPY×BUY / dedup=0 / 2026-08-05 以降 fresh N≥40 で 1 回限り判定 (EV>0 ∧ Wilson_lo>38.7% ∧ 月次符号≥3/4)。registry `sr-anti-hunt-eurjpy-buy-forward-confirm` (期限 2027-02-28)。中間再計算禁止 (P-10 型)。詳細: [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]]
- **評価への影響: なし** — live/tier/lot/shadow 全て不変更。成果物 = 決裁 doc + registry + BT runner (`tools/sr_anti_hunt_eurjpy_cell_bt_2026_08_05.py`) + BT 乖離証拠 (raw/bt-results/)

## 2026-08-03 — fix(live): vix_carry_unwind×USD_JPY Overlap pilot 早期 demote (rule:R2, user 決裁)

- **決裁**: 2026-07-31 quant-eval の早期 demote 推奨を user「進めて」承認 (2026-08-03)。07-07 継続裁定の「demote は user 決裁」要件を充足、checkpoint (live SELL N≥20 or 08-31、registry `vix-sell-pilot-recheck`) を待たず執行
- **根拠 (production 実測)**: live N=26 PnL=−46.9p PF=0.66 EV=−1.80 (月次 3/4 負、07-30 −30.1p) + **shadow エッジ崩壊** 04:+537p → 05〜07 累計 −216p/n=139 → 08-01〜03 −17p/n=7。365d BT 正値 (EV=+0.506 / Overlap cell N=22 EV=+1.297) は forward で反証 — 止血判定は EV 軸・Live>BT の規律に従い demotion に新規 BT 不要 (再昇格 R1 側で要求)
- **執行**: `_PAIR_PROMOTED` 除外 (22→21) + `_PAIR_DEMOTED` 復帰 + `_PAIR_SESSION_FILTER`/`_PAIR_LOT_BOOST` 撤去 (inert だが code consistency)。MIN-lot 1000u 契約 code / agg-Kelly min-lot bypass は再昇格時のため残置。**shadow emit 不変更 (原則3)**。registry resolved 化。pin `tests/test_vix_pilot_demote_pin.py` (5 tests)、session-filter/agg-Kelly 機構テストは合成メンバーシップ化で絶縁
- **評価への影響**: 現役 live 送信経路から最大の出血源 (7月 −34.3p) を除去。残る live 経路 = wg×3 + ps×5 + Grail #1/#4 (監視中)。詳細: [[vix-pilot-early-demote-2026-08-03]]

## 2026-07-31 — fix(live): Grail #19 ny_close_reversal live 経路撤去 + shadow 含む全数 quant-eval (rule:R2)

- **quant-eval 全数監査** ([[quant-eval-2026-07-31]] = `raw/trade-logs/`): post-cutoff closed **14,329 行**を 3 バケット分解 (live 565 / shadow 13,758 / other 6)。live 月次 = 04:−230.7 / 05:**+14.8** / 06:−281.9 / 07:−84.4p。**7 月 live 反実仮想: 修正済みバグ経路 + ny_close + vix を除くと −7.6p** = M1 (月次符号転換) の残存出血源を特定
- **Grail #19 撤去 (rule:R2)**: ny_close_reversal live 経路 (N=4 登録根拠、2026-04-25) が live 0W/4L −9.7p + shadow 両ペア負 → `_GRAIL_CANDIDATES`/`_check_grail_filter` から撤去。shadow emit 継続 (原則3)。pin `tests/test_grail19_ny_close_removal_pin.py`。詳細: [[grail19-ny-close-removal-2026-07-31]]
- **勝ちセル抽出** (Bonferroni m=102): WR vs BEV 二項検定 PASS = sr_anti_hunt_bounce×EUR_JPY (p=2.2e-11) / donchian×NZD_USD (4.2e-6) / ema200_trend_rev×USD_JPY (2.6e-6) / orb_trap×GBP_USD (3.0e-4、EV t 検定も PASS)。**横断勝ち条件 = 方向片側性 + Overlap (12-16 UTC)**。母集団レベルでは confidence≥70 が WR+5.0pp (Bonf PASS、04-22 分析の負相関から反転 — KB 矛盾として記録)
- **vix pilot 証拠更新 (live 変更なし)**: shadow エッジ減衰 (05〜07 累計 −216p) + live 月次 3/4 負 → 早期 demote 推奨を戦略カードに追記、**user 決裁待ち** (07-07 裁定準拠)
- **評価への影響**: live 送信経路 −1 (ny_close Grail)。lot/tier/Kelly 不変更。shadow 蓄積は全戦略不変

- **🎉 3.5 ヶ月ぶりの初 live fill (07-29 04:44 UTC)**: price_shock_rev_aud_jpy×AUD_JPY → OANDA #549235 BUY 1000u @113.466 slip+0.8p。経路検証全クリーン — agg-Kelly BYPASS ログ実射 (D-c-1 carve-out 作動) / broker SL #549237 @112.467 (=2×ATR) + TP 付帯の二層防御 / dedup・slot 正常 / BE_LOCK・ATR-BE 不作動。**§7 免除 deploy (04:22) 後の fill = 完全な LOCK 設計 estimand 下の第 1 号** (戦略カード 現況に記録)。副次観測: broker TP に Quick-Harvest ×0.85 が適用される (988p→840p、horizon 12h では非拘束 — §7 スコープ外として記録)
- **[[mfe-be-lock-design-2026-06-03]] §8 追補**: per-strategy 詳細表 (57d 再計測、適格 9 戦略 **0/9 pass**、Bonferroni p 全 1.0、aggregate ΔEV −0.006 p=0.975) — §8 verdict FAIL の per-strategy 粒度での確定。**評価への影響: なし (記録のみ)**
## 2026-07-29 — fix(data): E15/E7 phase-1 データ前提修理 — plain 15m 台帳再現を 13/13 byte-exact 復元 + never-shorten ガード (rule:R3)

- **発見**: coverage 台帳 (`e15_e7_pair_coverage.json`, 07-21 凍結) が参照する plain `{pair}_15m.parquet` が **11/13 ペアで台帳再現不能** (各種 explore の短い `--days` フル取得による無条件上書きが原因、EUR_AUD は消失)。このままでは phase-1 discovery (08-21) / OOS verdict (08-28) が `load_and_verify_bars` で BLOCKED
- **復元**: phase-0 実行 worktree `e15-oos-20260722` に原本が現存、**phase-0 verdict data_ledger の sha256 と 13/13 完全一致** → `tools/e15_e7_data_refreeze.py --restore-from` で byte-exact 復元 + 判定器実コードで 13/13 GREEN 実証。凍結コピー `data/cache/massive/e15_e7_frozen/` + manifest `raw/bt-results/e15_e7_frozen_manifest_2026-07-29.json` (verdict と同一 sha256 = provenance 連鎖が閉じる)
- **副産物 (重要)**: MASSIVE fresh 再取得で **AUD_USD が台帳比 −25 行 drift** = ベンダー歴史バー集合は不変ではない。pre-reg データ凍結は「cache 参照 + 行数 pin」でなく**ファイル実体コピー + sha256** で行うこと
- **再発防止**: `tools/fetch_massive_data.py` に never-shorten merge ガード (既存行優先・head 保持・tail 延長のみ) + tests 8 本。phase-1 pre-flight = `--verify-only` (runbook `e15_phase0_execution_status.md` 2026-07-29 節)
- **評価への影響: なし** — 価格ファイルの復元のみ、イベント×リターン統計未計算 (§10-1 遵守)、live/shadow/Kelly/tier 不変更

## 2026-07-29 — fix(data): MASSIVE ベンダー欠損 2 区間 (2019-09/2020-10) を OANDA v20 で backfill — 45 ファイル +61,709 行 (rule:R3)

- **holiday カレンダー検証中に発見された USD_JPY の 2 窓 0 行** (2019-09-14〜10-05 / 2020-10-13〜11-14) を全ペア×全 TF に横断展開: 欠損は**ベンダー側の穴** (API 直接プローブでローカルと欠損日リスト完全一致 = キャッシュはミラー、再取得では埋まらない)。重症度はペア依存 — USD_JPY 両窓全欠 / USD_CAD・USD_CHF 2020 窓全欠 / EUR・GBP・NZD 系部分欠 / AUD 系ほぼ完備
- **修理** = `tools/massive_gap_backfill.py` (新規): OANDA v20 mid candles (dailyAlignment=0/UTC = MASSIVE alignment 一致) から**欠損バーのみ**補完。era-local (±90d) pattern guard で当時の session 慣行を保存、既存行バイト不変 assert、`.bak-pre-gapfill` バックアップ + `.audit.json` に backfill provenance、冪等。境界連続性 0.003〜0.07% (クロスソース) を検証
- **凍結物ガード**: plain `{pair}_15m.parquet` 13 本は E15/E7 pre-reg data ledger (rows_at_ledger_last 凍結、phase-1 verdict 08-28) が pin するため **backfill 恒久除外を code pin** (誤適用 6 本は .bak からバイト同一復元済み = net ゼロ)。W3 manifest の sha256 は .bak と一致検証済み。HIP-1 holdout lock (2025-11〜2026-05) は窓外
- **refresh cron が埋めない理由を確定**: `bt_data_cache.py` 差分更新は「最終バー→現在」のみ + 全量上限 180〜730d — 履歴中間の穴は構造的に対象外 (かつベンダーに無い)。詳細: [[massive-vendor-gap-backfill-2026-07-29]]
- 影響 explore 注記: gotobi = robustness 評価済み・verdict 不変 (報告書に data note) / holiday family = 凍結前に是正、pre-reg 時は backfill 済みデータで LOCK すること。**評価への影響: なし — live/shadow/Kelly/tier 不変更**

## 2026-07-28 — fix(live): price_shock_rev ×5 BE_LOCK OFF — 並行セッションと同時執行 (rule:R1)

- 本セッション (day-1 監視) 側でも [[preserve-exit-overlay-2026-07-28]] §5 案(a) を user 「進めて」承認で執行 — main には Track C **D-c-1** が先着 (5 エントリ 0.0 は同値、コメント文言のみ相違 → merge で D-c-1 表記に統一)
- 残存 delta: regression pin `tests/test_mfe_be_lock.py::test_price_shock_rev_disabled_returns_zero` (PRICE_SHOCK_REV_TIER1_TYPES 全体パラメタライズ、family 追加 drift を強制検知) + §5 決裁記録の KB 追記

## 2026-07-28 — feat(risk): Track C 資本配管修復 — ps×5 carve-out + JPY 台帳 SSOT 化 + PYR code pin (rule:R1 user 承認 + R2)

- **決裁**: [[track-c-capital-plumbing-decision-packet-2026-07-28]] を user 承認 (「進めて」= Claude 推奨案採択)。診断: [[track-c-plumbing-audit-2026-07-28]] (全クレーム code 検証 + D-a broker 実測)
- **D-c-1 (R1)**: `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` に price_shock_rev ×5 を追加 (全席 1000u 固定契約、>1000u で自動失効) — **07-28「7席再武装」決裁が carve-out 欠落で code 上無効化されていた** (累積 Kelly −0.22 恒久負 → 次 qualify シグナルで shadow 落ち確定だった) の実効化。同時に `MFE_BE_LOCK_STRATEGY_TRIGGERS` へ ps×5 を 0.0 追加 ([[preserve-exit-overlay-2026-07-28]] §5 案(a) — R1 未通過実験レバーの live 波及遮断、estimand を LOCK 済み horizon-exit に近接)。復帰初週再ゲート registry 登録 (`ps-carveout-firstweek-regate`、08-11)
- **D-c-2 (R1)**: donchian×NZD ×2 は選択肢(ii) 採択 — bypass 追加せず gate block のまま shadow N 蓄積 (365d BT FAIL CI 全負、小 N 昇格パターン)
- **D-b (R1)**: DD defensive の SSOT を pip/1000 台帳 → **JPY 台帳** (per-close `pnl_pips × units × pip価値JPY`、母集団 = `oanda_trade_id != ''` broker 実約定 ∧ 非 XAU) に切替。D-a 実測 (実 DD 9.14% / 32,835 JPY) で再基準化 — **切替時 multiplier は 0.20x のまま不変** (現時点の防御は正当)、変わるのは回復経路 (+928p ≈ 57k JPY 相当 → +4.1k JPY で 0.40x 圏 = 恒久ロック解消)。tiers/MC ruin gate は存続、ruin 計量の資本も pip→JPY 整合 (`OANDA_JPY_PER_PIP_AVG`)。`/api/risk/dashboard` dd_status に jpy_ledger 追加・dd_pct の分母 1000 ハードコード修正 (「DD 100.8%」表示 artifact の解消)
- **R2 (D-e 調査起因)**: `_PYRAMIDING_CODE_PIN_DISABLED = True` — PYR child は demo 台帳に行を作らない構造的 orphan (生涯 N=33 / WR 9.5% / net −5,212 JPY / 同一親 6 連 fill = dedup 不全)。[[track-c-de-orphan-investigation-2026-07-28]] (`raw/analysis/`)。**30000u×7 (07-10/13) は preserve 系ではなく手動/外部クライアントと判定 — user 本人操作か要確認 (否ならトークンローテーション Rule 3)**
- tests: `tests/test_track_c_plumbing.py` +33 本 (bypass/BE_LOCK/pip_value_jpy/tier 境界/PYR pin)、`test_pyr_attribution.py` は pin monkeypatch で将来 R1 再武装用に温存。全 2,480 green
- **評価への影響**: live 送信可能セルが wg×3 → **wg×3 + ps×5** に回復 (user 決裁の実効化)。lot は全席 1000u 固定契約のまま — aggregate lot 増はゼロ。dmb×2/legacy は不変

## 2026-07-25 — fix(research): E1 供給ライン phase1b BT の join dtype バグ修正 — 14 ペア中 12 ペアが silent に 0 join だった構造欠陥 (rule:R3)

- **症状**: `phase1b_oanda_contrarian_bt.py` の日次再走が **verdict=NULL** を出し続けていたが、真因は「エッジ不在」ではなく **pandas merge_asof の datetime-unit 不一致**。MASSIVE cache refresh が 12/14 ペアの `{pair}_1h.parquet` を `datetime64[ms, UTC]` で書き直した一方、OANDA-Labs sentiment 履歴は `datetime64[ns, UTC]` のまま → pandas≥2.0 が `incompatible merge keys [0] datetime64[ms, UTC] and datetime64[ns, UTC]` で join 拒否。EUR_CHF/GBP_CHF (偶然 ns のまま) の **2 ペアだけ**が join されていた
- **根拠 (実測)**: 本番 parquet で EUR_USD/USD_JPY/GBP_USD/AUD_USD/EUR_JPY/AUD_JPY = ms → 修正前 **join 0 行** / 修正後 **394〜428 行**。EUR_CHF/GBP_CHF (ns) は 397 行で不変。sentiment 側 = ns 14,140 行
- **修正**: `join_sentiment_to_ohlc` で merge_asof 直前に両キーを `.dt.as_unit("ns")` で ns へ正規化 (resolution-agnostic)。**閾値・grid・holding・survivor gate・verdict ロジックは一切不変** — 純粋に join を成立させるだけの R3 構造 fix (pre-reg LOCK の仮説空間に非接触)
- **影響**: E1 retail-contrarian 供給ライン (M1 の唯一の load-bearing 供給ライン、first-look verdict 2026-10-15) の日次 BT が **2 ペア → 14 ペア全数**で評価されるようになる。verdict は依然 NULL の可能性があるが、以後は「壊れた 2 ペア artifact」でなく全ペア universe 上の真の判定
- **教訓**: 外部 cache refresh がデータの dtype/resolution を変えると、silent に下流 join を破壊しうる。「verdict=NULL が続く」= エッジ不在と即断せず、join 行数の per-pair 監査を挟む (silent 失敗が「不発」と「ゼロ件」を区別不能にする系統: [[lesson-silent-except-hides-nameerror]])
- tests +1 file (`tests/test_phase1b_join_dtype.py`、6 本 — ms/ns/us/s 全 unit で非空 join を pin、全オフライン合成 fixture)。**評価への影響: なし (live/shadow/Kelly/tier 不変更)**

## 2026-07-24 — data(research): E7 phase-1 FF カレンダー歴史+gap import 完了 — §3.3b データ付録凍結 (期日 08-14 の 21 日前倒し、rule:R3)

- **残タスク「FF gap import」を歴史パネルごと一括完結** ([[e15-e7-event-modality-prereg-2026-07-18]] §3.3b 新設): EPSOFT は 2023-03 停止 (延長なし) → **R4F 公開 CSV (keyless、2007〜現在、日次更新) を 2014-01〜2026-07-20 の単一ソースに採用**。値整合 = EPSOFT cross-check **歴史 sample 279/279 完全一致** + 2023 Q1 overlap 114/120 (差分は全て EPSOFT 側 end-of-panel 劣化)
- **dump の実測特性 2 点を E15 canonical anchor 突合 (NFP 149 + CPI 135、miss 0) で特定**: (a) **時刻規約が 2023-08-07 で Europe/London → UTC に切替** → `tools/ff_gap_prepare_r4f.py` が正規化 (b) actual 列が 2023-08 で充填停止 → **判定系列 (NFP/CPI) は BLS 一次リリースの first print** (`tools/ff_gap_bls_first_prints.py`、Wayback §3.2b 経路、**較正 9/9 完全一致**) で補完 — previous 逆引き (改定値) を判定系列に使わない
- **抽出器の kind 順先勝ちバグ 2 種を R4F previous 連鎖との系統突合で検出・修正** (NFP 後方改定括弧 / CPI 後方 y/y — 出現位置最早選択に変更、実文 regression pin 4 本)。shutdown 合算値 (CPI 2025-12-18「over the 2 months」) は機械検出で除外
- **本番 import 済み (Render SSH、dry-run→実行)**: r4f-2014-2026 = 58,713 insert / bls-first-print = 66 actual 補完 / invalid 0。**判定系列 canonical 突合 297/298 完備** (唯一の欠落 = 事前宣言済み CPI 2025-12-18)。forecast の発表前性は発表前日 Wayback snapshot 4/4 一致で機械証明
- tests +23 (全オフライン)。**評価への影響: なし** — 純研究データ基盤、live/shadow/Kelly/tier 不変更。残 = phase-1 discovery 08-21 → verdict 08-28

## 2026-07-24 — data(research): E20 金利差方向バイアス S2 診断 — ❌ §7 exit 未達で棄却・クローズ (rule:R3)

- **rapid_edge_probe の `__dummy_e20__` を実 series に差し替えて S2 執行** ([[e20-rate-differential-s2-diagnostic-2026-07-24]]): `tools/e20_rates_ingest.py` (新規) が S1 §3 台帳の keyless 6 ソース (BIS WS_CBPOL 8/8 政策金利 + 2y = MASSIVE/ECB/MOF/BOE/BoC) から日次パネル→per-pair シグナル CSV を生成 (探索窓保護のため 2022-12-31 で物理切断して commit、sha256 manifest 付き)。GBP は IADB に 2y ZC が無く 5y ZC (IUDSNZC) 代用を明記。価格は **E15 phase-0 凍結 data_ledger と sha256 完全一致の 13 ペア parquet** (main の plain 名は refresh cron 短縮版で研究使用不可 — 部分 parquet 罠の変種を doc §1b/§5-4 に記録)
- **結果 (探索窓 2014-06〜2022-12 のみ、8 run、全 run OOS 非接触確認)**: **carry-level = §7 exit 3/3 欠け** — pooled IC **−0.047 (p≈0) 機構と逆符号で有意**、quintile **単調逆行** (Q1 +7.3 → Q5 −16.0)、EV_net 全負 (AUD_JPY −4.8)。**mom63 = 1/3 欠け (単調性 Q2 −12.9 中抜け) + 補助不合格 3 点** — IC +0.026 (p=0.003) と EV_net(k=5) +2.6p は通るが、EV 正 horizon の fold が [−,−,+] (fold3 単独駆動)、2022 slice +21.4p 集中 (S1 §5-4 の regime 罠)、cell IC 有意ゼロ (78 cell)。breakout 条件付け (user 仮説の形) は**両 variant で uncond より劣化** = テクニカル entry が価値を引く
- **→ E20 クローズ (S3 起案なし、§7 既定の棄却分岐)**。再試行禁止 scope = 凍結 2 variant の同型。rates データ配管は残置 (次の rates 系 S1→S2 は数時間で回せる)。OOS 2023+ は未接触温存
- 成果物: tools 2 本 + spec 8 本 + 診断 raw 17 ファイル + tests +14 (全オフライン)。**評価への影響: なし** — 純研究、live/shadow/Kelly/tier 不変更

## 2026-07-22 — feat(research): S2 共通ハーネス rapid_edge_probe — 仮説スペック 1 ファイル → 探索窓診断 (rule:R3)

- **user 要求「仮説を爆速で実装してテストするフロー」への回答**: [[edge-development-pipeline-2026-07-18]] §2 **S2 (R3 診断) を標準化** — `tools/rapid_edge_probe.py`。YAML/JSON スペック 1 枚 (direction_source: event/series/technical × entry_trigger: none/breakout/pullback × holding: bars/first_touch の小語彙) → ペア×horizon の **IC / 摩擦調整 EV / N / fold 3 分割 / 発火頻度** + S3 起案検討の目安を md+json で自動出力。`--draft-prereg` で S3 pre-reg スケルトン (🔓 DRAFT、LOCK 不能 TODO 付き) も自動 draft。使い方 1 ページ: [[rapid-edge-probe-2026-07-22]]
- **規律は構造で強制**: OOS 窓 (2024-01-01〜) は bars/calendar の load 直後物理スライスで遮断 (明示 `--unlock-oos` + 警告なしにアクセス不能、test pin)。全レポートに「探索診断 ≠ 判定 / live・tier 判断禁止」ヘッダ + **falsified 6 系統 + 価格モダリティ 3 周の再試行禁止チェックリスト**を自動印字。seed 固定 / silent except 禁止 (skip 全件理由カウント) / モジュールトップ副作用ゼロ
- **再発明なし**: estimand コアは `event_modality_lib.py` (§3.5 SSOT: σ_h first-touch SL 優先 / NY17時 roll ATR14d / E1 §3.4 凍結摩擦 / coverage gate)、IC 規律は channel_edge_ic_explore 同型、データは 12y 15m parquet 13 ペア + E15 イベントカレンダー
- **動作実証 2 本 (探索窓のみ — 診断であり判定ではない)**: (a) `nfp_usd_24h` = NFP 後 USD 方向 uncond → pooled EV **−7.4p (h4) / −3.7p (h24)**、fold 不一致 = エッジなし (E15 discovery の NFP uncond 凍結 0 と整合)。(b) `rate_diff_breakout_template` = 金利差方向×breakout の雛形 (外部 series は **E20 feasibility 待ちのためダミー列で構造のみ**) → EV ≈ −摩擦に収束 = 配管正常。`raw/bt-results/rapid_probe_*_2026_07_22.{md,json}`
- tests +27 (`tests/test_rapid_edge_probe.py`、全オフライン合成 fixture — OOS 遮断 / 語彙 / causal entry / SL 優先 / 決定性 / 規律ヘッダ pin)。全 suite 2328 passed / check.py 9/9 green
- **評価への影響: なし** — 純研究インフラ。live/shadow/Kelly/tier 不変
## 2026-07-22 — data(research): E15 phase-0 OOS verdict — ❌ FAIL 0/6 (全候補 C5、rule:R1 手続き、純研究)

- **判定器実装 + clean OOS 判定を執行** ([[e15-e7-event-modality-prereg-2026-07-18]] §5c/§8、期日 07-31 の 9 日前倒し): `tools/event_modality_oos_verdict.py` (extract/verdict 分離、seed=20260718 固定、B=10,000、estimand は lib SSOT 再利用)。**test pin 26 件を先に green にしてから OOS 接触** (§10-6 — 判定分岐 C1–C5/BH-FDR m固定/bootstrap seed 決定論/IM df/ナイフエッジ/canary 検出能力/OOS 窓ガード/摩擦式/join 契約)
- **結果: レグ A 全滅** — BH-FDR q=0.05 (m=6) 通過ゼロ (min p_combo=0.214 ≫ rank-1 閾値 0.0083)。4/6 は点 EV 正 (te/ft 両正、最大 CPI/fade/30m/h24 = +9.68p/p) だが event-block 推論 (bootstrap+IM) で有意性なし → **全 6 候補 C5 REJECT**。C3 ゼロ (blocks 20–28 ≥ 15 で B(d) 充足 — §9 modal 予想 C3 は自らの閾値と整合しない予想だった。§8 字義執行・再解釈なし)。**§8 固定分岐 = phase-1 (E7) 予定どおり実行**。Lee & Wang post-sample 検証も negative (fade は探索で不選抜、follow は OOS 非有意)
- データ整合 green: parquet 台帳再現 13/13 (sha256 凍結) / OOS sanity は CPI 14.3%・FOMC 10.0% >5% だが offset ピーク全種 +0 (時刻正常、explore 窓 user 裁定と同一シグネチャで続行・記録) / リーク canary 実データ 686 件 all clean。collision・週末跨ぎはフラグ記録のみ (§10-3)
- 成果物: `raw/bt-results/e15_phase0_oos_verdict.json` (全統計+trade/event list) + pre-reg §5b 凍結表転記 (🔒 手続き補完)・§8 発動分岐・§12 判定表 + registry `e15-e7-event-prereg-phase0-verdict` resolve + lib 加法拡張 (TradeOutcome.atr / entry_delay_bars / canary ATR 経路) + sanity 検出器の window 共有化
- **評価への影響: なし** — 純研究、live/shadow/Kelly/tier 不変更。次 = phase-1 (FF gap scrape + データ付録凍結 08-14 → verdict 08-28、registry `e15-e7-event-prereg-phase1-verdict` 監視継続)

## 2026-07-22 — docs(research): E20 金利差方向バイアス S1 feasibility — 条件付き採用 (S2 GO) (rule:R3)

- **user 仮説 (2026-07-22)「金利差から計算した方向バイアス × テクニカル entry」を E20 としてパイプライン S1 (C1–C6) で裁定** → [[e20-rate-differential-feasibility-2026-07-22]]。判定 = **条件付き採用 (S2 GO)** — 第 4 モダリティ (rates)、蓄積待ちゼロで BT 即可
- **falsified 台帳との区別を確定**: round-3 (intraday ZN divergence-reversion) とは データ/頻度/機構/役割 の 4 軸で別仮説。hull-donchian USD_CHF ratediff (FALSIFIED) は claim が逆 (fade ゲート ⇔ 継続バイアス)。D1 TSMOM は price-momentum で family 別 — 3 件の教訓ガード (単調性 / USD-neutrality / regime slice) を S2 必須化。E5 term-structure の C1 棄却は日次粒度で解消 (CIP proxy)
- **データ実在を一次確認 (実 fetch 証跡付き)**: 政策金利 8/8 = BIS WS_CBPOL 日次 keyless 単一エンドポイント (1999 実取得、鮮度 07-09〜14)。2y 国債利回り = US (MASSIVE in-house 1962+) / EUR (ECB 2004+) / JPY (MOF 1974+) / GBP (BOE 1995+) / CAD (BoC 2001+) 現行、CHF (SNB 1988+) は **2025-07-31 で cube 凍結**、AUD/NZD は WAF 403 → Wayback 歴史のみ (go-forward gap)
- 条件: claim = 継続バイアス限定 / variant 2 本凍結 / live 段階は AUD/NZD 制限 / 保有 1–10 日は帳簿上限外 (E9 同型 △)。S2 推奨 spec (`tools/rapid_edge_probe_e20.py`) を doc §7 に付す
- **評価への影響: なし** — 純研究 S1、live/shadow/Kelly/tier 不変更

## 2026-07-22 — data(research): E15 phase-0 discovery 実行 — §8 DEFERRED user 承認 → 6 候補凍結 (rule:R1 手続き)

- **§8 DEFERRED 裁定 = user 承認 (2026-07-22)**: sanity フラグ (CPI 43.6%) は verify-times で時刻正常を立証済み・低インパクトイベント由来と裁定、discovery 続行
- **discovery (探索窓 2014-2023 のみ): 54/54 combo 計算 → 選抜規則 (§5b 凍結 = fold→EV-per-vol→種分散) で 6 候補凍結** (FOMC 3 / CPI 3 / NFP 0) — `e15_frozen_candidates.json` + 全 combo 台帳 `e15_discovery.json`
- 価格 parquet は coverage 台帳検証済みフルセット 13/13 を使用 (部分 parquet 罠回避)。OOS 窓 (2024-01-01〜) は未接触 — **次 = clean OOS 判定、verdict 期日 2026-07-31** (registry `e15-e7-event-prereg-phase0-verdict`)。凍結は期日 07-24 の 2 日前倒し
- **評価への影響: なし** — 純研究、live 変更なし
## 2026-07-21 — feat(monitor): R3 market-data ingest 鮮度監視を prereg-trigger-registry に配線 (rule:R3)

- **registry `r3-market-data-ingest-freshness` 追加** ([[market-data-ingest-2026-07-18]] §7 宣言の執行、E1 `e1-positioning-ingest-freshness` と同型): `/api/marketdata/status` の health を毎日機械評価 — `verified:ff_calendar` 24h 超 stale / `verified:cme_bars:*` (7 契約) いずれか 72h 超 stale (週末市場閉鎖 ~2.5d を跨いでも誤警報しない) / キー欠落・min_keys 未達 (worker 未稼働・thread 死の fail-loud 検出) で 🔴 TRIGGERED。API 不達/health DB エラーは DATA_UNAVAILABLE に分離
- 実装 = `tools/prereg_trigger_watch.py` に type=`ingest_freshness` (純関数 `evaluate_ingest_freshness` + fetch 分離、既存パターン準拠)。tests +10 — registry 閾値/契約数がモジュール定数 `STALE_ALERT_*_SEC` / `DEFAULT_CME_SYMBOLS` と乖離したら fail する整合 pin 込み
- deploy 後検証 (§7 次アクション 1) 完了: running=true、ff + cme 7 契約全 verified (2026-07-21T10:55Z)。CME 深 backfill (§7 次アクション 2) は並行セッションが同日 11:10Z に全 7 契約完了済み (§7 に記録)
- **評価への影響: なし** — 監視エントリ + watch ツール拡張のみ。live/shadow/Kelly/tier 不変

## 2026-07-21 — feat(research): E15 phase-0 イベントカレンダー凍結 + §3.2b AMENDMENT — sanity >5% 発火で §8 DEFERRED (rule:R1 手続き、純研究)

- **§3.2b AMENDMENT (結果観測前 data-availability、round-3 前例)**: FRED キー self-provision 不能 → NFP 行に **pre-registered 済み fallback「BLS 公式ページ」を発動** (CPI は「同上」の明確化)。アクセスは Wayback snapshot 経由 (BLS 直接 403)。BLS News Release Archive の**アーカイブ発表ファイル名 = actual release date** を一次記録に格上げ。grid/判定規則は不変更、追記時点でイベント×リターン結合統計は未計算。
- **カレンダー凍結**: `tools/event_calendar_build.py` (politeness 2s/req) → `raw/bt-results/e15_e7_event_calendar.json` + build log。**FOMC 99 / NFP 149 / CPI 149 件** (2014-01〜2026-06、ET→UTC per-date DST)。FOMC は scheduled のみ (unscheduled 4 / cancelled 1 / notation vote 4 除外・記録、monetary20250822a 型の非会合リリースは行内突合で構造排除)。整合性検証 green (explore 窓: NFP 金曜規則・12件/年・欠月ゼロ)、2025 shutdown 異常はフラグのみ (§10-3)。パーサ回帰 pin 15 tests (オフライン fixture)。価格 re-fetch で coverage 台帳 13/13 完全再現。
- **⚠️ §3.2 sanity 発火 → §8 DEFERRED**: フラグ率 CPI 43.6% / NFP 6.8% / FOMC 2.5% (>5%)。処方どおり discovery 停止・再検証 → **verify-times (オフセットピーク検査) で全種 offset +0 ピーク = 時刻は正しい** (フラグは低インフレ期 CPI / COVID 期高ベースライン由来、破損行ゼロ)。しかし §8 明文「sanity >5% — **user 裁定 (勝手に解釈しない)**」に従い **discovery 未実行・user 裁定待ち**。裁定後は push-button (期日 07-24)。
- **役割分離**: 本カレンダー = 歴史 (BLS/Fed 一次、BT 判定用) ⇔ PR #102 FF capture = go-forward ingest (E7 Actual 補完)。非重複。
- **評価への影響なし** — 純研究、live/shadow/Kelly/tier 不変更。**§10-1 遵守: イベント×リターン結合統計は探索窓含め一切未計算** (計算したのはカレンダー件数・整合性・event bar range のみ)。

## 2026-07-21 — feat(research): E15 phase-0 §3.1 価格データ + coverage 凍結 — MASSIVE ブロックは誤り (rule:R1 手続き、純研究)

- **E15 phase-0 の data-run を前進** ([[e15-e7-event-modality-prereg-2026-07-18]] §3.1 執行、runbook `e15_phase0_execution_status.md`)。前回 (07-20) autopilot が「MASSIVE_API_KEY + FRED_API_KEY 双方 credential ブロック」と記録していたが、**MASSIVE 側は事実誤認** (`.env` に実在・稼働)。branch-stale (166 commit 遅れ) を検知し origin/main から再検証 → 自走原則で unblock。
- **成果**: 13 ペア 15m フル歴史 (days=4650) を MASSIVE 取得 → parquet、explore 窓 (2014-01-01〜2023-12-31) coverage 凍結 → `raw/bt-results/e15_e7_pair_coverage.json`。**13/13 pass gate 0.90 (0.974〜1.000)、primary 7/7、EUR_AUD 1.000** → §3.1 縮小分岐 / §8 DEFERRED(primary<5) リスク解消。ハーネス (`_load_pair`→`event_trade`→`run_combo`) を実 parquet でスモーク検証済。
- **残ブロッカー = FRED calendar (NFP/CPI) のみ**: `FRED_API_KEY` 不在・self-provision 不能 (FRED 公開ページ WebFetch 403/urllib timeout、firecrawl キー無)。FOMC は key-free だが歴史ページ書式が不統一 → NFP/CPI と同一 keyed パスで一括構築が正 (discovery は 54 combo family 全 event 揃うまで走らせない=§5b)。
- **§10-1 遵守 (中間 peeking 禁止)**: coverage 件数 + 日付範囲の計上のみ。OOS 窓のイベント×リターン結合統計は一切未計算。**評価への影響なし** — 純研究、live/shadow/Kelly/tier 不変更。期日: 凍結 2026-07-24 / OOS verdict 2026-07-31 (registry `e15-e7-event-prereg-phase0-verdict` 継続監視)。

## 2026-07-18 — docs(prereg): E15+E7 イベントモダリティ・プログラム 単一 family pre-reg 起案 — 🔓 DESIGN self-LOCK (rule:R1 手続き、純研究)

- **[[e15-e7-event-modality-prereg-2026-07-18]]**: round-2 裁定 ([[external-hypothesis-scan-round2-2026-07-18]]) の統合推奨どおり、E15 (FOMC/NFP/CPI イベント窓プレミア/リバーサル、phase-0) + E7 (指標サプライズ directional、phase-1) を**単一 pre-reg family** で起案。方法論 = round-1/2/3 と同一 (discovery diagnostic → 候補固定凍結 → clean OOS、BH-FDR + first-touch EV レグ + ナイフエッジ)、[[edge-development-pipeline-2026-07-18]] S2/S3 統合・型 B
- 設計の要点: (1) **α 会計 = phase 分割 q=0.05+0.05 ≤ 0.10** (E1 の look 分割と同型、multiplicity 二重取り禁止の実装)、(2) **primary = USD-leg 7 ペア block の combo pooled × event-block 推論** (bootstrap + Ibragimov–Müller 併設。T11「EUR_JPY は USD 露出ゼロ」反証の構造的排除)、(3) **凍結規則は raw EV 単独ランク禁止** — fold 安定性 → EV-per-vol → イベント種分散 ([[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]] 反映)、(4) T11 / WMR fix REJECT / E8 棄却との区別を §2 に明示、発表前 entry は構造的にゼロ、(5) 窓 = discovery 〜2023-12-31 / OOS 2024-01〜2026-06-30 (Lee & Wang RAPS 2025 の post-sample = 文献 standing の検証を兼ねる)
- 期日: **phase-0 verdict 2026-07-31** (E1 first look 10-15 より 2.5 ヶ月先行 — WIP 原則の戦略的役割) / phase-1 verdict 2026-08-28。registry `e15-e7-event-prereg-phase0-verdict` / `phase1-verdict` 追加、queue `20260718-e15-e7-event-phase0` 起票、pipeline 状態表 S3 反映
- **評価への影響: なし** — 純研究 pre-reg + 監視エントリのみ。live/shadow/Kelly/tier 一切不変更。PASS でも実装は D4 実装 pre-reg + user 承認 (S5) が別途必要

## 2026-07-18 — docs(process): エッジ開発パイプライン常設化 — 供給ラインの単発プッシュ→常設プロセス転換 (rule:R3)

- **[[edge-development-pipeline-2026-07-18]]**: user 指摘 (07-18) を受け、暗黙だったエッジ開発手続きを S0〜S8 ステージ + **WIP 原則 (S1-S4 に常時 ≥2 仮説、モダリティ分散)** + 月次スキャン cadence として正式化。E1 単一ベット (modal=UNDERPOWERED) の後継不在リスクを構造的に解消する
- registry: `edge-supply-scan-monthly` (次回 2026-08-18) 追加
- **[[external-hypothesis-scan-round2-2026-07-18]] (E7-E19 裁定)**: 採用 3 — **E15 (FOMC/NFP/CPI イベント窓、in-house 12y + 無料カレンダーで即 BT 可 = E1 first look より先に verdict 可能な唯一の候補)** / E7 (指標サプライズ、19y 分単位パネル実確認、E15 と単一 pre-reg family) / E12 (CME 先物 volume flow — **yfinance 1h は 730d rolling で capture 開始遅延 = 歴史の不可逆喪失**)。条件付き E9 (VRP、無料 probe 先行)。棄却 6。データ実在は全て一次確認 (5-agent workflow、敵対的検査込み)
- 今から始めないと不可逆なインフラ 3 件を特定: FF Actual 補完 ingest / CME 1h volume 週次 capture / CME settlement・OI 日次 scrape (§infra 参照)
- 併走: shadow 蓄積詰まり R3 診断 (別ブランチ)
- **評価への影響: なし** — プロセス文書 + 研究裁定 + 監視エントリのみ

## なぜこのページが重要か
定量評価は「いつからのデータを使うか」で結論が180度変わる。
各バージョンの変更が**どのトレードに影響するか**をここで追跡する。

## 2026-07-18 — feat(data): R3 market-data ingest — E7 FF カレンダー + E12 CME 1h volume の go-forward capture 開始 (rule:R3)

- **[[market-data-ingest-2026-07-18]]**: [[external-hypothesis-scan-round2-2026-07-18]] infra_needed_now 3 件の実装裁定。(1) FF カレンダー = ✅ 実装 (faireconomy 公式 feed 6h capture + **翌期 previous 逆引き** actual 補完 + `tools/ff_calendar_import.py` gap 合流経路)、(2) CME FX 先物 1h volume = ✅ 実装 (yfinance 7 契約日次 capture、730d rolling 窓対策)、(3) CME settlement/OI scrape = ❌ **不実装 + round-2 前提訂正** (probe が「scraping は CME Data ToU で禁止」明示 403 / Databento は歴史保持 = 不可逆でない → E9/E10/E14 forward は Databento 一本化)
- 実装 = `modules/market_data_ingest.py` (positioning_ingest パターン準拠: fail-loud / モジュールトップ副作用禁止 / defer_thread fork-safety / health 2 テーブル / content-hash + UNIQUE dedup)。**forecast 凍結を code 強制** (event_time 通過後は feed 側改変を反映しない — E7 surprise estimand の汚染防止)。**形成中 bar 非保存 + 初回 capture 値凍結** (BT 再現性)
- 検証 API: `/api/marketdata/status` / `/api/marketdata/export?table=ff_events|cme_bars|health_log`。tests +38 (offline/deterministic)。smoke: CME 2 symbol × 155 bars 実 fetch→保存成功、FF は 429 rate-limit 実測 → poll 6h + retry 30 分に設計反映
- **評価への影響: なし** — read-only 蓄積 + 検証 API + import ツールのみ。live 発注経路・戦略・Kelly・shadow・BT 関数いずれも不変

## 2026-07-18 — docs(analysis): r2_shadow_demoted_cell「構造的詰まり」診断 — analyst フラグ裁定 = 現状維持 (rule:R3)

- **[[analyses/shadow-accumulation-blockage-diagnosis-2026-07-18]]**: analyst report (07-17 pre_tokyo 等) の「scalp 系全般で r2_shadow_demoted_cell が Sentinel N 蓄積を毎日足止め = 構造的詰まり」フラグをコード + 本番実測で裁定
- **コード実態 = (b)**: gate (`demo_trader.py` L4227-4248 / L3826) は OANDA 送信だけでなく **shadow row の DB 書込み (L5859 `open_trade`) まで完全遮断**。ただし対象は静的 registry (`shadow_demote_registry.py`) の**反証確定済みセルのみ** (retired 5 戦略 N=453〜1,117 + per-cell 5、全て R2 監査根拠つき)
- **実測で「詰まり」を否定**: 30d shadow rows **3,239 件 (~108/日)、147 セル** 蓄積継続。SCALP_SENTINEL 現役 (vol_surge_detector 90 / ma_regime_switch 115 行) は無傷、gate 起因ゼロは bb_rsi_reversion (T10 KILL 済) のみ。registry セルは demotion commit 日 (06-12/06-18/07-02) 以降の流入が正確にゼロ (leak なし)、per-cell 粒度も機能 (engulfing_bb×EUR_USD 157 行 vs ×USD_JPY 0)
- **block 件数は tick 再発火ノイズ**: Render logs 実測 37.4 分で 100 件 (ema_trend_scalp×GBP_USD 単独 ≈2.7/分)。in-memory カウンタは deploy 毎リセット — 「失われた N」の推定量にならない
- **裁定 = 現状維持**: gate は [[lessons/lesson-shadow-always-emit-cleanup-2026-04-28]] が要求した R2 自動 demotion gate の実装そのもので、原則 3 (未解決仮説の検定力保護) と無矛盾。unblock は slot 侵食 (scalp shadow cap 4/pair) で現役セルの蓄積を毀損し統計力を**下げる**。「emit 継続 + 学習除外フラグ」分離案は汚染経路再導入で却下。観測性改善 3 点 (analyst report 注記 / _SCALP_SENTINEL cosmetic 除去 / ログ rate-limit) を別タスク提案
- **評価への影響: なし** — 診断文書のみ、live/shadow 挙動・コード一切不変

## 2026-07-17 — fix(research): E1 ハーネス敵対的レビュー修正 — fatal 2 系統 (look-2 着地 / health 時系列) + major 6 + minor (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] 判定器への敵対的レビュー (spec/leak/stats 3 レンズ、fatal 3 [実質 2 系統] / major 6 / minor 10) を全件処置**。pre-reg 本文は不変更 (LOCK 遵守)
- **F1 (look-2 着地違反)**: `overall_verdict()` が look を知らず second look で C3 → 禁止された `UNDERPOWERED` (= 第 3 look 示唆) を返していた → look=2 では **PASS / REJECT-F / REJECT のみ** に写像 (C3/C2/C5→REJECT、C4→REJECT-F、UNDERPOWERED 到達不能化 = α 会計 q₁+q₂≤0.10 の保証回復)。look=2 × C3 → REJECT / 着地集合の pin テスト追加
- **F2 (health 時系列インフラ、§6-7「estimand を宣言どおりにする運用修理」)**: §2.2 stale cap 主モードが要求する per-instrument verified **時系列**が、本番 `positioning_health` の 1 行 upsert から構造的に得られなかった → (1) `positioning_health_log` append テーブル新設 + `record_health()` が**同一トランザクション**で追記 (~940 行/日)、(2) `/api/positioning/export?table=health_log` read-only export 経路、(3) ハーネス `--verdict-run` は verified 系列欠落で fail-loud 拒否 (明示 `--fallback-mode` でのみ続行)、結果 JSON に `stale_cap_mode: primary|fallback` を必ず記録、fallback 時は §2.2 必須診断 (2h-cap NA の NY 時間帯分布) を併記し**閑散帯集中 → DEFERRED を機械接続** (事前固定分岐、閑散帯 = NY 17:00–03:00 / 総数≥50 / 集中倍率 2.0 を観測前固定)
- **major**: (a) gate2 点推定を全 6 combo 常時計算 — look=2 でナイフエッジ #2(ii) 隣接 combo 参照が機械 FAIL する偽 REJECT バイアスを修復 (`gate2_all_combos` で透明化)、(b) C1/PASS 経路の end-to-end pin — 埋め込み強 contrarian シグナル合成世界で **verdict=PASS/C1 に実到達**する統合テスト (knife 4 点 / confirmatory / Stage B / Gate1+2) + confirmatory 4 分岐・partial IC・S2 lag・S3 pain 式の単体 pin、(c) canary に rank 窓 (strictly trailing / t 非包含) + mid 経路 (確定 bar 限定) の注入点と rank→IC 貫通の検出感度チェックを追加 (リーク rank 実装が fail することを pin — §6-4 委譲の空洞化を修復)、(d) primary parquet 欠落の無言 family 縮小を封鎖 (`--verdict-run` で 13 ペア完備必須、欠落リスト表示で拒否)
- **minor**: verified key の book 成分検査 (outlook 限定) / im_test se=0 の符号盲目 p=0 修正 (逆符号→p=1) / CONFIRMATORY_UNTESTED フラグを C1 限定化 (C2〜C5 汚染除去) / 量子化粒度をペア×統計毎 (S1/S2/S3) に記録 / Stage B 実行条件を c1_candidate (Gate1+2 通過) に拡張 / parquet cutoff 切詰めの機械クリップ + 件数記録 (切詰め規約非依存) / LOCF resampler の DST 跨ぎ週 (2026-11-01) unit test / MBB 全ペア同時 day-draw の pin / **day-block「観測日 index」規約の宣言** (Gate 2 の疎 trade 日で暦 5 営業日と乖離 — LOCK 字義の解釈変更を避け、実装ノートとして verdict JSON (`block_basis`) と本 changelog に宣言。変更でなく宣言で処置した唯一の項目)
- tests 118→160 (E1 96 + ingest 64、全 offline/合成)。**評価への影響: なし** — 判定器 + read-only export 経路 + append テーブルのみ。live 発注経路・戦略・Kelly・shadow 一切不変。verdict 期日 (2026-10-15) の実データ初適用前に修正完了

## 2026-07-17 — feat(research): E1 pre-reg 判定ハーネス実装 — LOCK 後成果物 (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] §7 成果物規定の実装**: 判定器 `tools/e1_positioning_prereg_eval.py` (2,250 行、LOCK 後実装・seed 固定 `SEED_DEFAULT=20261015`)。§7 の規定どおり **LOCF resampler / rank タイ規約 (mid-rank §3.1) / DST 跨ぎ週 (2026-11-01) / ATR (NY17 roll 完結 bar) / OHLCV join 契約 / canary leak test を `tests/test_e1_prereg_eval.py` (58 tests) に pin してから verdict データに触れる**体制を確立
- 実装範囲 = §2.2 市場時間 (America/New_York DST 追随) + LOCF/stale cap (verified 基準)/cycle 証跡、§2.3 join/前方リターン/ATR14d/censoring、§2.5 品質 gate (coverage/stale gap/family postpone/sanity/jump detector 前方+24h)、§3 シグナル 3 本 × rank/hysteresis/金曜窓/年末窓、§4.1 Gate1 (営業日 MBB L=5 B=10k 全ペア同時 + Ibragimov–Müller df=7、p=max、BH q=0.05 m=6)、§4.2 Gate2 (day-block bootstrap、N<60 は点推定分類)、§4.4 C1〜C5 排他分類 + SIGN-FLIP/CONFOUNDED (partial IC)、§4.5 ナイフエッジ 4 点、§2.4 confirmatory 複製検査、§4.3 Stage B、§4.6 Secondary
- **構造的強制 (§6-1/6-2)**: 入力 = 凍結 export artifact + parquet のみ (本番 API/DB 経路をコードに含めない)。synthetic 宣言のない artifact は `--verdict-run` フラグなしで拒否。family gate postpone 時は統計段を一切実行しない (look 非消費の機械化)。canary suite green が verdict 実行の前提条件
- **実データ接触なし — テスト・dry-run は 100% 合成データ** (§6-2「実データへの初適用は verdict 期日 2026-10-15」遵守)。tests 60→118 (58 追加、全 offline/deterministic)。**評価への影響: なし** — 研究ツール + テストのみ、live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — feat(research): E1 positioning contrarian pre-reg DRAFT + positioning_health 永続化 + D4 テンプレート (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] (DRAFT)**: 文献駆動・**データ観測前** pre-reg — discovery 2 段階を省き、first look verdict を **2026-10-15** (cutoff = t0+12週) に固定。従来計画 (2-3ヶ月蓄積 → discovery → 凍結 → OOS) 比で **verdict を 1〜2 ヶ月前倒し**。設計 = 8-agent workflow (独立3案 → 統合 → 敵対的レビュー major 11 反映)。階層ゲートキーパー (pooled IC 二重検定 → 摩擦調整 EV conjunction、look 毎 BH q=0.05)、UNDERPOWERED second look (2027-01-06) 事前固定。LOCK 決裁期限 2026-07-17 (registry `e1-prereg-lock-decision-stale`)
- **positioning_health テーブル (pre-reg §2.2 必須インフラ)**: per-instrument `verified:` 時刻 + `last_cycle_at` heartbeat を DB 永続化 — dedup skip (行を書かない) と fetch 失敗の識別を可能にし、LOCF stale cap の活動条件付けバイアスを排除。status API に `health` 露出。詳細: [[e1-positioning-ingest-2026-07-14]] §13
- **[[d4-implementation-prereg-template-2026-07-16]]**: survivor 到達時に即起案できる D4 実装 pre-reg 雛形 (carve-out 2 択 / R2 自動降格 / セル単位判定 / parity / 防御解除ラダー) — 直列待ちの前倒し削減
- tests 56→60。**評価への影響: なし** — read-only 計測基盤 + 文書のみ。live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — feat(data): E1 instrument 拡張 6→13 — 将来セル候補の蓄積 clock を前倒し開始 (rule:R3)

- **動機 (最短経路)**: history は今から蓄積する以外に入手不可 (§8c 確定) → 将来ペアの clock は今日始めた分だけ discovery が早まる。outlook は全 symbol 一括 1 リクエスト (probe: n_symbols=186) のため **API 予算コストゼロ**、増分は DB ~940 rows/日のみ
- **追加 7 ペア**: AUD_USD / NZD_USD / USD_CAD / USD_CHF / NZD_JPY / EUR_AUD / EUR_GBP (engine モード/Phase B-1 slot 既存の取引可能ペア)。ペア別 t0 が異なる点を pre-reg 窓設計の必須参照事項として記録。詳細: [[e1-positioning-ingest-2026-07-14]] §12
- **評価への影響: なし** — read-only データ収集の対象拡張のみ。live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — fix(data): E1 defer_thread — import 時 network thread 起動の廃止 (第2修正, rule:R3)

- **背景**: §10 修正後も serving プロセスの healed thread がハング (master の cycle は成功 = t0 蓄積開始済み)。帰属 = fork 瞬間に master thread が HTTP 実行中 → socket/ssl 内部 lock が locked のまま複製 (Session 再生成では直らない)
- **根治**: `start_positioning_ingest(defer_thread=True)` — master では thread を起動せず、serving プロセスの初回 heal (§8b) を唯一の起動経路に一本化。status に `current_phase`/`phase_since` 追加 (ハング位置の直接観測)。詳細: [[e1-positioning-ingest-2026-07-14]] §11
- tests 54→56。**評価への影響: なし**

## 2026-07-16 — fix(data): E1 Myfxbook client 2バグ修正 — session 二重エンコード + fork-unsafe HTTP Session (rule:R3)

- **背景**: user が credentials 投入 (05:54Z) → 初回稼働で "Invalid session." + healed thread ハングを実証
- **(a)**: Myfxbook session は発行時点で URL-encoded 済み — params= 再エンコードが二重化。`_get` を組立済み query 方式へ (session は raw 付加)。**(b)**: fork 継承 requests.Session の pool lock が locked のまま複製されハング — pid 変化検知で lazy 再生成。詳細: [[e1-positioning-ingest-2026-07-14]] §10
- 修正版で実 API 検証済み (186 symbols / 対象 6 ペア全取得)。tests 51→54 (回帰 pin 3)
- **評価への影響: なし** — read-only データ収集の修正のみ

## 2026-07-15 — feat(data): E1 ソース転換 — Myfxbook Community Outlook aggregate 版 (オプション A 採択, rule:R3)

- **決裁**: user 全面委任 (2026-07-15「最短がオーダーなので、やり方は任せる」) の下で §8c オプション A 採択。B (practice) は期待値低で保留、C (有償) はコスト非対称、D (閉鎖) は唯一の主戦線を閉じる理由なし。詳細: [[e1-positioning-ingest-2026-07-14]] §9
- **何を**: `modules/myfxbook_client.py` (新規、login/session/re-login、secrets 非開示 pin) + `positioning_ingest.py` ソース抽象 (`POSITIONING_SOURCE` 明示 > MYFXBOOK_EMAIL/PASSWORD 自動検出 > oanda default)。book_type=`outlook`、near_imbalance=NULL (bucket 級放棄の明示)、raw payload を buckets_json に JSON object で温存、content-hash dedup (sha256、snapshot_time は fetch 時刻 μs 精度)、poll ≥900s clamp (rate limit 100 req/24h)
- **受け入れ確認**: `/api/positioning/probe?run=1&source=myfxbook` (login+outlook 1回)。export API は book=outlook を受理
- **user アクション (E1 稼働の唯一の依存点)**: Myfxbook 無料 account 作成 → Render env に `MYFXBOOK_EMAIL`/`MYFXBOOK_PASSWORD` 投入 (§9 手順)
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。read-only データ収集のソース交換のみ。tests: test_positioning_ingest.py 34→51

## 2026-07-15 — fix(routing): trendline_sweep 全セル shadow-first demote — ELITE_LIVE all-pairs bypass 除去 (pre-reg 2026-07-13 執行, rule:R2)

- **何を**: `_ELITE_LIVE` から trendline_sweep を除去 (最後の member → 空集合化) + `_PAIR_DEMOTED` に EUR_USD / GBP_USD / EUR_GBP の 3 セルを追加 (gbp_deep_pullback 2026-05-04 と同型)。`TRENDLINE_SWEEP_REDESIGN_V2=1` env の live 復活パスも PAIR_DEMOTED 先勝ちで無効化。`HTF_MIXED_LIVE_STOP_CELLS` の GBP_USD mixed cell stop は部分集合として残置
- **なぜ**: pre-reg `trendline_sweep_gbpusd_pairscope_2026-07-13` (resolved / reviewer=SATISFIED) の terminal action 執行。12y MASSIVE per-cell WF (本番 trigger 無変更) で**全 3 セル FAIL** — netEV: EUR_USD −0.483 (N=3036, WF 1/4) / GBP_USD −3.121 (N=4884, grossEV=−0.095 = 摩擦以前に負) / EUR_GBP −1.449 (N=2829)。BH-FDR (q=0.10, m_eff=4) 生存ゼロ。ELITE_LIVE 根拠の 365d favorable BT (WR 73-81%) は WR 41-44% に崩壊し反証。forward LIVE GBP_USD netEV=−2.35p RR=0.15 が corroborate
- **shadow 継続**: 3 セルとも emit は止めない — is_shadow=1 で記録継続 (4原則#3)。再LIVE化条件 (R1, cell 単位) = forward shadow N≥20 ∧ Wilson_lo≥0.40 (FDR) ∧ WR≥BE-WR@realized-payoff
- **評価への影響**: あり — trendline_sweep の live 発火が全ペアで停止 (ELITE_LIVE 便乗 live はこれで消滅、`_ELITE_LIVE` は空集合)。clean live 集計から trendline_sweep の新規 live row が消える。shadow 統計は不変
- 詳細: [[trendline-sweep]] 判断履歴 / BT: `bt-results/trendline_sweep-12y-pairscope-2026-07-13.json`

## 2026-07-14 — fix(data): E1 positioning worker self-heal + 401 帰属確定 (OANDA book 提供終了) (rule:R3)

- **本番実証 2 問題** ([[e1-positioning-ingest-2026-07-14]] §8): ①全 12 book が HTTP 401 ②worker thread が process ライフサイクルで死ぬ (started_at ありなのに running:false / poll_cycles:0)
- **401 帰属確定 (§8a)**: 当初仮説「OANDA Japan 区分制限」を**棄却** — OANDA は **2024-09-14 に retail API での book 提供を終了** (公式告知 oanda.jp/info/1193 原文確認 + no-token でも同一 generic 401 の実測 + 非日本ユーザー同時遮断の傍証)。fxlabs `/labs/v1/orderbook_data` は 2020 年廃止 (403 HTML 実測)。**auth 修理では直らない → 代替ソース比較 §8c を user 決裁用に整備 (推奨 = Myfxbook aggregate 版転換)**
- **self-heal (§8b)**: demo_trader StatusHeal パターン準拠 — `ensure_running()` (started_at あり × thread 死のみ heal、stop 後は復活せず) + `status()` 冒頭 heal + app.py `before_request` heartbeat (60s throttle、Render health check を恒常 heal 経路化)。status に `restarts`/`last_restart_at` 追加
- **probe API**: `GET /api/positioning/probe?run=1` — v3/accounts 統制付き可用性 probe (read-only ×4)。token/口座 ID 非開示をテストで pin。instrument は whitelist 検証 (path injection 防止)
- **registry**: `e1-positioning-ingest-freshness` → conditional_info 化 — 蓄積ゼロは既知状態、user 決裁まで stale 調査不要
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。tests: test_positioning_ingest.py 17→34

## 2026-07-14 — feat(data): E1 positioning ingest — OANDA 建玉/注文比率の snapshot 蓄積基盤 (user GO 2026-07-14, rule:R3)

- **何を**: OANDA v20 positionBook/orderBook (read-only) を 20 分毎 + jitter で snapshot し、既存 SQLite に `positioning_snapshots` (UNIQUE(instrument, book_type, snapshot_time)) として蓄積。buckets は mid ±3% trim + 集計列 (pct_long/short_total, near_imbalance)。対象 6 instruments (USD_JPY/EUR_USD/GBP_USD/EUR_JPY/GBP_JPY/AUD_JPY、env override 可)。dedup 3 層 (book.time メモリ / 再起動 DB seed / UNIQUE)
- **なぜ**: WS3 price-modality 計 3 周 FAIL ([[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8) → E1 retail-positioning contrarian が主戦線。positioning history は今から蓄積する以外に入手不可 = 稼働開始が最優先。設計: [[e1-positioning-ingest-2026-07-14]]
- **可観測性 (fail-loud)**: `/api/positioning/status` (行数/最新 snapshot_time/連続失敗/可用性マップ) + `/api/positioning/export` (研究用 JSON)。非対応 instrument は初回 4xx 記録→以後 skip。silent except ゼロ
- **監視 (T5 教訓)**: registry `e1-positioning-ingest-freshness` (最終 snapshot 2h 超 stale = 要調査)。`prereg_trigger_watch.py` に info/conditional_info type 追加 (UNAVAILABLE ノイズ→watching)
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。read-only データ収集 thread の追加のみ。env `POSITIONING_INGEST_ENABLE=0` で無効化可
- tests: `tests/test_positioning_ingest.py` (17) + prereg watch (+2)。本番検証手順は KB ページ §5 (ローカル token 失効のためデプロイ後検証)

## 2026-07-10 — data(bt): WS3 探索2周目 OOS verdict — ❌ FAIL 0/5、外部仮説探索へ転進 (rule:R1)

- **OOS 窓**: 2024-07-07〜2025-07-07 (再利用 2 回目)。切詰め parquet (末尾 2025-07-07T23:45Z) + **N 凍結→判定の順序執行** (`ws3_round2_oos_entries.json`)。GBP_JPY 15m は Massive 遡及取得で充足、EUR_USD/USD_JPY は stage-1 凍結資産再利用、ep 復元不一致 0/428
- **判定** ([[ws3-round2-explore-prereg-2026-07-10]] §8): 2 レグ (ratio BH-FDR m=5 / §2b 凍結 grid first-touch EV) + ナイフエッジ (LOFO) — **全 5 セル FAIL**。vol_spike×USD_JPY N=27<30 機械 FAIL + ratio 崩壊 0.56 / vsg×GBP_JPY 0.88・dt_sr×GBP_JPY 0.90 崩壊 / sr_fib×GBP_USD 1.21 (p=0.13 n.s.) + EV 孤立格子点 / 最接近 sr_fib×EUR_USD 1.25 (p=0.19) + EV 隣接過半 fail
- **一貫した結論**: round-1→stage-2→round-2 の 2 周で「現行エンジン母集団に OOS 再現の方向性非対称 × 固定 barrier EV の組は無い」。探索窓 EV スクリーン通過 5 セル中 4 セルが OOS で崩壊 = 探索窓 EV は選択バイアスの別表現
- **分岐 (§3 事前固定)**: shadow 母集団内の軸は枯渇 → **外部仮説 (新シグナル系統 — 学術/TV 由来、falsified 6 系統除外) の探索へ転進** (v2.3 WS3 反映)。registry `ws3-round2-oos-verdict-deadline` resolved
- **評価への影響**: なし (純研究、live/shadow 変更なし)

## 2026-07-10 — docs(kb): WS3 探索2周目 pre-reg LOCK — 候補 m=5 凍結 (rule:R1 stage-1 型、純研究)

- **診断** (`raw/bt-results/ws3_round2_scan_2026_07`): 方向分割 196 セル + EUR_GBP (entries=0 構造的) + h96 → 1次候補 8 セル。round-1 checkpoint 窓同一性 0 mismatch
- **§2(ii) 探索窓 first-touch EV スクリーン** (`ws3_round2_ev_screen_2026_07`): **5/8 通過**。脱落 = turtle_soup×GBP_USD / dt_sr_channel×GBP_USD×SELL (孤立格子点) / sr_fib×AUD_JPY×SELL (EV<0)。stage-2 verdict の教訓「非対称 ≠ 固定 barrier で EV 化可能」をスクリーン結果観測前に pre-reg へ反映した a priori 改訂が機能
- **LOCK**: [[ws3-round2-explore-prereg-2026-07-10]] §2b に m=5 + 凍結 grid + 摩擦判定値を固定。registry `ws3-round2-oos-verdict-deadline` (2026-07-17) 追加
- **評価への影響**: なし (純研究、live/shadow 変更なし)

## 2026-07-10 — feat(mode): 15m AUD_JPY shadow-only モード `daytrade_audjpy` 新設 (user 承認 D2)

- **目的**: WS3 stage-2 対象セル htf_false_breakout×AUD_JPY の estimand は **15m** だが、本番 AUD_JPY は 1h モード (`daytrade_1h_audjpy`) のみで 15m shadow 発火ゼロだった。stage-2 PASS 時に shadow parity 検証を即開始できる状態 + AUD_JPY 実測摩擦 (spread/slippage) の取得。決裁メモ: [[shortest-path-decision-memo-2026-07-10]] / pre-reg: [[ws3-stage2-barrier-ev-prereg-2026-07-09]]
- **MODE_CONFIG**: interval 30s / 15m / 60d / compute_daytrade_signal / AUD_JPY / auto_start=True / base_sl_pips=15 (JPY クロス既存値 eurjpy=15 準拠) / **`shadow_only: True`**
- **shadow-only 構造保証 (新機構 `_mode_is_shadow_only`)**: 既存機構では塞げないことを確認の上で追加 — htf_false_breakout は `_SHIELD_EUR_DT_WHITELIST` 登録済みのため `_OANDA_MODE_BLOCKED` 方式は bypass され、N<10 sentinel は agg-Kelly gate も bypass して live minlot 発注される (テストの control ケースで実証: 同一入力×mode=daytrade は 1000u send に到達)。ガードは 3 経路: ①送信ガード最終段 (PRIME/GRAIL/C1/Kalman/edge-cell force-live の後・OANDA 判定の前で shadow 強制、以降 promote 復帰経路なし) ②`_resend_promote_gate_block_reason` に `SHADOW_ONLY_MODE_GATE` (補完送信) ③`_resolve_is_shadow_for_write` (write-path fail-closed)
- **htf_false_breakout 発火経路**: `HTF_FALSE_BREAKOUT_REDESIGN_V2` OFF の legacy 経路のまま (コード変更なし、stage-1 と同一母集団)。v6.1 JPY 追加ゲート (RSI div / OB 接触) は本番仕様どおり適用。QUALIFIED_TYPES は既にグローバル登録済みで per-pair 追加不要、live 転送資格の付与は一切なし
- **テスト**: `tests/test_daytrade_audjpy_shadow_only_mode.py` (9 tests) — 構造 pin / 最悪ケース (N<10 sentinel × strategy_mode=live × bridge active × SHADOW_MODE off) の send ゼロ / control 帰属証明 / resend・write-path gate
- **影響トレード: なし** (live パラメータ不変・OANDA 発注ゼロ。AUD_JPY 15m shadow 行の新規蓄積が開始される)

## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
## 2026-07-10 — docs(kb): 最短経路決裁 (user 承認「進めて」) + 月利目標の段階化 (rule:R3 導出)

- **決裁メモ**: [[shortest-path-decision-memo-2026-07-10]] — 8-agent workflow + 敵対的レビュー3レンズによるゼロベース再検討。**agg-Kelly gate 恒久閉鎖の確定** (固定 cutoff 2026-04-16 累積 −0.2758 → per-cell carve-out なしで正セルも live 発火不能)、D3 決裁 SLA 48h、D4 実装 pre-reg 必須項目 (carve-out + R2 自動降格 + セル単位判定 + parity)
- **目標段階化 (D5)**: [[monthly-target-rederivation-2026-07-10]] — 21.6% の導出考古学 (12-cell 母体 1〜2/12 残存、二重楽観バイアス、pips→%変換消失)。現行制約下天井 = 2セルで +0.15〜2.4%/月。**段階目標 M1 (月次符号転換) → M2 (+0.5%/月) → M3 (+2〜3%/月) へ移行、21.6% は aspirational anchor** — CLAUDE.md / index / roadmap v2.3 反映
- **トラックB 起動**: [[ws3-round2-explore-prereg-2026-07-10]] DRAFT (探索2周目: 方向分割×未走査ペア×h96、判定済み8セル+falsified 6系統除外、queue `20260710-ws3-round2-explore` 排他 claim)
- **評価への影響**: なし (live パラメータ変更なし。D2 15m AUD_JPY shadow-only モードは別 PR)
## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
## 2026-07-10 — WS3 stage-2 verdict: ❌ PASS ゼロ / UNDERPOWERED — barrier EV 化は不成立 (rule:R1)

- pre-reg LOCK ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]) の機械的実行 (期日 07-19 の 9 日前倒し)。OOS-2 = 2022-07-07〜2024-07-06 (第3窓、切詰め worktree)。§3 執行順序遵守 (エントリー抽出 → N 凍結 59/46 → sim)。独立実装の再計算で符号一致検証
- **lfr×EUR_USD: 全 9 構成負 (best −6.51 p/t) → セルクローズ**。SL 先着率 44-75% — stage-1 の中央値非対称は first-touch sequencing で反転
- **htf_fb×AUD_JPY: 1/9 構成のみ +1.15、p_cell 0.594** — fold 集中 (2022 円介入期 +10.8 / 直近 −10.9)・孤立格子点。UNDERPOWERED 分岐 = shadow N≥100 で同一 grid 1 回限り再判定 (registry `ws3-stage2-underpowered-recheck`)
- **帰結: v2.3 WS3 は新シグナル系統 (外部仮説) の探索へ**。TV canon は PASS 候補不在で未評価 (moot)
- **監視配線 (R3)**: `prereg_trigger_watch.py` の shadow_count_decision に instrument フィルタを追加 (無指定だと全ペア合算でセル判定を過大計上) + 回帰テスト。`test_session_time_bias_in_bt_metrics` をパーサ実装 (all-pairs/full-audit 優先) に整合 — 旧実装は辞書順最後の .md を盲目的に見ており研究成果物の追加で誤 red になっていた (テストバグ)
- **影響トレード: なし** (純研究。live/tier 変更ゼロ)
## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
- **latent 疑義の確定**: `_is_promoted_ex` のみ PP 先勝ちで、シグナル経路
  `_is_live_tier_exempt` (9b16ebb5 fail-closed) / `_apply_force_demoted_final_gate` /
  再送 gate と逆。final gate が PP 例外なしに shadow 強制するため live 漏れは構造的に
  不可能 = **実害ゼロ (latent)**。実害候補は「PP でペア復活」の silent 死コード化
  (ema_pullback×JPY 前例) と audit block_cause 誤帰属のみ
- **修正**: `_is_promoted_ex` を FD 先勝ちに統一 + docstring 正準化。FD∩PP=∅
  (tier_integrity_check check#1) のため到達可能入力で挙動不変 (no-op 証明、BT 不要 R3)
- **CI 固定**: `tests/test_pair_promoted_force_demoted_precedence.py` (5 tests) で
  FD∩PP=∅ / PP∩PD=∅ 不変量 + precedence pin。正準文書 = [[system-reference]] Tier
  Precedence セクション (経路別 derivation 表)
- **副次発見の相互裏付け**: post-commit-verify.sh check#3 の `pp_sentinel` premise
  stale (PP∩UNIVERSAL_SENTINEL = {vix_carry_unwind, doji_breakout,
  squeeze_release_momentum} は設計上合法) を本調査でも独立に確認 — 並行セッションの
  check#3 修正 (下記 f292ccb1、マージで合流) と同一結論
- **影響トレード: なし**

## 2026-07-09 — WS3 stage-2 pre-reg LOCKED — user 承認 (rule:R1)

- [[ws3-stage2-barrier-ev-prereg-2026-07-09]] を user 承認「進めて」で 📝 DRAFT → 🔒 LOCKED (決裁期日 07-16 の 7 日前倒し)。verdict 期日 2026-07-19 (LOCK+10d、registry `ws3-stage2-verdict-deadline` 監視)
- **影響トレード: なし** (live パラメータ不変。grid BT / TV 検証の実行解禁のみ)
## 2026-07-09 — post-commit-verify check#3 silent 不発修正 + assertion 現行設計へ張替え (rule:R3 構造バグ)

- **不発の実証と修正** ([[lesson-post-commit-verify-silent-misfire-2026-07-09]]): check #3 (demo_trader tier set 整合検証) は bash double-quoted `python3 -c "..."` 内の f-string `"` によるコード截断で導入 (2026-04-14) 以来一度も実行完了せず、SyntaxError が `|| echo "SKIP"` に吸収される silent 検証ギャップだった。quoted heredoc 化 (check #1 も予防的に同化、check #2 は inline python 非使用で対象外) + 空出力/import 失敗の FAIL 可視化 + `POST_COMMIT_VERIFY_CHANGED` テストシームで red→green 実証
- **stale assertion 発見**: 修復後の初実行が検出した 4 overlap (FD∩SENT=post_news_vol / PP-strat∩SENT=doji_breakout, squeeze_release_momentum, vix_carry_unwind) は全て現行設計の意図的共存 (demote = live 遮断 + shadow 蓄積継続、PAIR_PROMOTED は `_is_promoted_ex`/`_resolve_tier` 両 gate で SENTINEL より先勝ち)。assertion を現行 invariant (`PAIR_PROMOTED∩PAIR_DEMOTED` 同一セル / `ELITE_LIVE∩FORCE_DEMOTED`) へ張替え — 両者とも現状空集合 = 本番 tier 状態は健全
- **影響トレード: なし** (ローカル post-commit hook のみ、live シグナル判定・サイジング不変)

## 2026-07-09 — WS3 stage-2 pre-reg DRAFT 起案 + KB stale 棚卸し (rule:R1 起案 / R3 doc-sync)

- **stage-2 barrier/EV pre-reg DRAFT** ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]): PASS 2 セル限定 h24 barrier grid (m=18)。評価 = 第3窓 OOS-2 (2022-07〜2024-07、2年) で winner's curse 遮断、Westfall–Young max-T セル検定 (FWER 0.10)、TV Pine canon trade-level 突合ゲート、3 分岐 verdict (PASS/UNDERPOWERED/REJECT)。敵対的レビュー 3 レンズ 18 findings 反映 (tie-break 帰属訂正 = SL 優先は swing 規約で fut_close pin より保守側、検定力分析による 2 年窓化、timeout ドリフト PASS の排除等)。**DRAFT — user 決裁期日 2026-07-16 (registry `ws3-stage2-lock-decision-stale` 監視)、LOCK 前の grid BT 実行禁止**
- **KB stale 訂正 (R3 doc-sync、tier 実状態の変更なし)**: london_fix_reversal×GBP の PROMOTED/PAIR_PROMOTED 残存 2 箇所 (`wiki/edge-pipeline.md` / `wiki/strategies/edge-pipeline.md` Stage 6 表) を v9.1 実状態 (Phase0 Shadow + PAIR_DEMOTED×USD_JPY、365d BT GBP EV=−0.239 で demote 済み) に同期 — check.py Edge Stage warn の解消
- **影響トレード: なし** (DRAFT 起案 + doc 同期のみ)

## 2026-07-09 — WS3 stage-1 verdict: ✅ PASS 2/8 — 方向性非対称の OOS 再現 (rule:R1 stage-1)

- pre-reg LOCK ([[ws3-asymmetry-oos-prereg-2026-07-09]]) の機械的実行 (claude 直接、期日 07-16 の7日前倒し)。OOS 窓 2024-07-07〜2025-07-07 (切詰め parquet worktree で look-ahead 遮断、USD_JPY/AUD_JPY は Massive 15m を 2024-05 まで遡及取得)、N=4,980 entries。
- **PASS**: london_fix_reversal×EUR_USD (OOS ratio 1.43 vs 探索 1.51、p=0.0115、CI5% 1.14) / htf_false_breakout×AUD_JPY (1.82 vs 1.39、p=0.0118、CI5% 1.20)。BH-FDR q=0.10 (m=8) + ratio≥1.2 + N≥30 + ナイフエッジ3点全通過。
- 選択バイアス組の崩壊 (htf_fb×EUR_JPY 1.81→0.99 / dt_sr_channel×EUR_USD 1.55→0.62) を確認 = 2段スクリーン設計が機能。持続型 2 セル (lin_reg_channel / dt_fib) は不再現でクローズ。
- **影響トレード: なし (純研究 stage-1)**。次 = stage-2 (PASS 2セル限定 barrier/EV pre-reg + TV Pine canon + user 最終承認)。判定器 `tools/ws3_oos_verdict.py` / スキャン `tools/ws3_mfe_scan.py` (--pairs/--out-suffix 追加)。
## 2026-07-09 — WS4 T15: CI paths filter 撤廃 + QUALIFIED_TYPES drift 検査 + 再送ガード共通化 (rule:R3, audit P1-6/7/8)

- **P1-7 (CI 品質ゲート穴)**: ① `ci.yml` push trigger の paths filter を撤廃 — 旧 filter (`*.py`/`strategies/`/`modules/` のみ) は tests/tools/agents/knowledge-base/scripts 変更の直接 push で CI が一切走らない盲点だった。② hip1-holdout-manifest ガードを CI job 化 (`hip1-holdout-guard`) — .git/hooks/pre-commit はカスタムスクリプト symlink のため pre-commit フレームワークの hook はローカルで一度も実行されていなかった。event diff に対して実行、正規編集は commit message の `HOLDOUT-APPROVED` / `HOLDOUT-VALIDATION-APPROVED` マーカーで通過。③ `agents/cma/dev.agent.yaml` の `--no-verify` 根拠誤記 (「hip1 が full pytest を走らせる」→ 実際はカスタム hook 側) を訂正。actions は full SHA pin 化 (supply-chain)。
- **P1-8 (scalp BT QUALIFIED_TYPES drift)**: `run_scalp_backtest` の inline set を `SCALP_BT_QUALIFIED` に改名 (挙動不変) + 意図的除外 `SCALP_BT_EXCLUDED_TYPES` (mtf_trend_follow / mtf_counter_trend / mtf_regime_trend_cascade = vec harness 専用) を文書化。`scripts/check.py` step 5b が「enabled scalp ⊆ QUALIFIED ∪ EXCLUDED」を機械検査 (drift = ERROR、矛盾登録 = ERROR、stale 除外 = WARN)。意図的 drift で red になることを確認後 green 化。
- **P1-6 (再送ガード共通化)**: `_resend_pending_oanda_trades` は FORCE/PAIR demotion しか再チェックせず Q4/aggregate Kelly/MC-ruin/SHIELD mode を素通しだった (is_shadow 反転バグ 1 つで gate 迂回の直通経路)。共通 helper `_resend_promote_gate_block_reason` が主経路の v9.x SHIELD 群と同判定を resend 直前に再実行。ELITE Q4 免除 / SHIELD whitelist / 1000u min-lot bypass / SENTINEL 免除は主経路と同じに保ち、PRIME lock・edge-cell bypass は per-signal コンテキスト不在のため fail-closed 側へ (5分窓の補完送信のみに影響)。`get_open_trades_without_oanda` に confidence 追加 (Q4 再チェック用)。
- **影響トレード: なし** (live シグナル判定・サイジング不変。resend の fail-closed 化と BT/CI/検査系のみ)。回帰: `tests/test_t15_quality_gates.py` (20 cases)。詳細: [[fable5-system-audit-2026-07-02]]。

## 2026-07-09 — P1-2b 検証クローズ: fut_close tie-break は4エンジン既装 + 回帰 pin 移植 (rule:R3, T14 補完)

- **二重実装レース記録**: T14 (P1-2) は autopilot が PR #65 で実装・マージ、並行セッションの PR #64 (同一実装 + 追加テスト 20 cases) と衝突 → #64 close で解決 (07-07 handoff インシデントと同型)。両実装の意味的差分ゼロを精査確認: (a) 3エンジン cache 無効化 (b) 1H系 BE/Trail guard (block-wrap ⇔ 閾値inf は等価) (c) flag semantics 完全一致。
- **P1-2b (fut_close tie-break) 検証結果: 追加実装不要** — 同一バー TP+SL 同時ヒットの fut_close tie-break は 4 エンジン (run_backtest/scalp/daytrade/1h) 全てに既装、swing はより厳格な保守的 SL 優先 (両ヒット=LOSS)。fut_close→SL 優先への厳格化は BT 全体再較正を伴うため監査どおり P2 据置。
- **#64 由来のテスト delta を移植**: `tests/test_bt_tie_break_regression_pins.py` (13 cases) — ① inline flag 式の canonical AST pin (真偽逆転・env typo 検出、main の既存 pin は参照有無のみ) ② cache key/フラグ照合 pin (stale cache = A/B 汚染防止) ③ P1-2b tie-break pin (TP優先への退行封鎖 + swing SL優先維持)。
- 影響トレード: なし (テスト + KB のみ、app.py 不変更)。

## 2026-07-09 — P1-2: BE/Trail ablation を全 BT エンジンへ展開 (rule:R3, WS4 T14)

- MEMORY 確定事実 `project_be_trail_inflates_python_bt_wr` の水増し源が daytrade 以外の 3 エンジン (`run_backtest` 1H / `run_scalp_backtest` / `run_1h_backtest`) に残存していた (Fable5 監査 P1-2)。daytrade と同じ `_BT_ABLATE_BE_TRAIL` (default ablated、`BT_OPTIMISTIC=1` で旧挙動復元) guard を展開。
- **行動証拠** (scalp fixture `_df_override`): ablated(default) N=84 WR=46.4% vs optimistic N=102 WR=56.9% → **+10.5pp inflation を default で排除**。
- BT cache key を flag-aware 化 (A/B で stale 防止)。AST 構造回帰テスト `tests/test_be_trail_ablation_all_engines.py` 同梱 (4 エンジン guard を pin)。
- **影響トレード: なし** (BT 評価ロジックのみ、live signal/OANDA 転送は不変)。過去 scalp/1H verdict は水増し込みのため再解釈対象。詳細: [[be-trail-ablation-all-engines-2026-07-09]]。残 = P1-2b (fut_close tie-break、副次)。

## 2026-07-09 — WS3 MFE 分布診断: 選抜基準を「MFE 絶対量」→「MFE/MAE 方向性非対称」へ改訂 (rule:R3)

- T2 FAIL 後の WS3 初手 ([[ws3-mfe-distribution-2026-07-08]])。365d baseline 6 pair、N=6,995 entries / 104 cells の forward MFE/MAE (H∈{6..96} bars) を exit 非依存で計測 (`tools/ws3_mfe_scan.py`)。
- **発見1**: MFE 絶対量は豊富 (h24 p50 15-30p) — live 診断の「winners MFE 5.18p」は exit 打ち切りアーティファクトと確定。
- **発見2**: MFE/MAE 比の母集団中央値 0.88 = **価格は走るがシグナル方向に走らない**。希少資源は方向性非対称 (ratio≥1.3 = 7/79 cells)。horizon 持続型 2 cells (lin_reg_channel×EUR_USD 1.38→1.94 / dt_fib_reversal×USD_JPY 1.29→2.05) を次期 pre-reg の検証対象に固定。
- 影響トレード: なし (R3 純診断)。roadmap WS3 節の選抜基準を改訂。事後選択セルの promote 禁止を明記。

## 2026-07-08 — T2 exit-repair grid BT verdict: ❌ FAIL / H0 採択 → WS3 全振り (rule:R1)

- pre-reg LOCK ([[exit-repair-tp-sl-prereg-2026-07-07]]) の機械的実行。executor は Codex queue → claude 直接実行に変更 (user 運用委任、期日 07-21 の 13 日前倒し)。
- **結果: 全 9 構成 FAIL** — BH-FDR q=0.10 全構成 p=1.0 (日次ブロックブートストラップ B=10,000、208 取引日) / WF 3-fold 全構成 0/3 / 摩擦調整 EV 全構成負 (最良 tp0.4×sl0.6 で −2.96 p/t、baseline −6.64 から +3.67 改善もレバー不足)。
- ナイフエッジ3点検査: メカニズムは診断通り作動 (TP-hit 0.215→0.44、EV 両軸厳密単調) した上での**構造的 FAIL**。lag-1 ρ ≈ ±0.06 で自己相関影響なし。感度 run (pre-#58 code、mixed 込み) も同結論 FAIL 0/9。
- 実装: `tools/exit_repair_tp_sl_grid_bt.py` (spawn 分離 grid runner) + `app.py` BT 専用 env hook (`BT_TP_MULT`/`BT_SL_MULT`、env 未設定で完全 no-op)。EUR_JPY 15m parquet の 2ヶ月 stale (silent window 罠) を差分修復。
- **影響トレード: なし (純研究、live パラメータ不変更)**。変わるのは roadmap の主戦線 — §4 固定分岐により **WS3 シグナル張り替え (MFE 分布ベースの entry 再設計) が v2.3 の主戦線**に。exit 側レバーの再試行は禁止。
- 成果物: `raw/bt-results/exit_repair_tp_sl_grid_2026_07.{json,md}` + 感度版。registry `exit-repair-bt-deadline` inactive。verdict 詳細: [[exit-repair-tp-sl-prereg-2026-07-07]] §8

## 2026-07-07 — WS4 Phase B follow-up: shadow 修復層の oscillation 封鎖 + 停止可視化 (PR #59 敵対的レビュー起点, rule:R3)

- PR #59 (P1-3 stale SHADOW_MIGRATION 削除 + P1-9 Kelly raw 化) / PR #60 (T4 摩擦調整 EV マップ) のマージ後、10-agent 敵対的検証 workflow が confirmed した欠陥への追修:
- **oscillation 封鎖**: SHADOW_DRIFT_BACKFILL (2026-05-03) が leak backfill の shadow 分類 (pre-RULE_TS の OANDA-filled リーク行) を次 restart で無条件に live へ巻き戻し、冪等マーカーが再修復を恒久ブロックしていた (空 DB 4-init で再現)。drift rollback の WHERE に `force_demoted_live_leak=0` 除外を追加。
- **修復層停止の可視化 (P2-3 部分)**: leak/flag_drift backfill の unsafe/exception 停止を `[SHADOW_REPAIR_PAUSED]` WARN で毎 restart 表面化。**本番は現在 leak 側 status=unsafe で停止中と実測** (P2-10 新設、修復 chip 化済)。
- **P1-9 スコープ訂正**: `_evaluate_shadow_promotions` は production call site ゼロの dead code — P1-9 で武装されるのは live promotion loop の `_kelly_block` のみ (P2-11 新設)。ゼロ境界は `< 0` が仕様と裁定 (`<= 0` 化は正エッジ誤 block の対称害で不採用)、mirror テストを production 述語に整合。
- 影響トレード: なし (シグナル判定・lot 不変更)。変わるのは修復層の分類安定性と観測性のみ。
- 回帰: tests/test_ws4_phase_b_followup.py (5 cases、oscillation は main で red 確認済み) + test_kelly_promotion_gate.py 整合。詳細: [[fable5-system-audit-2026-07-02]] P1-3 follow-up / P2-3 / P2-10 / P2-11

## 2026-07-07 — HTF mixed cell stop: trendline_sweep×GBP_USD live 転送停止 + mixed 診断タグ是正 (rule:R2/R3)

- T1 forensic §7 の異常 (30d 大負け4発 −53.6p 全てに「⚖️ 4H+1D 不一致 → シグナル抑制中」タグ付き LIVE 発注) の根本原因を特定: **タグは診断のみで、v9.1 HTF Hard Block は bull/bear 限定 — mixed は DTE 候補フィルタ no-op**。trendline_sweep は self-contained HTF guard も持たず、demo_trader v9.3 regime gate も ELITE_LIVE 免除で第2層不在。
- R2 執行: `DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS = {(trendline_sweep, GBP_USD)}` — mixed 時に候補除外 + shadow 退避 (`[HTF_MIXED_LIVE_STOP]` タグ、is_shadow=1)。根拠 = clean live (06-03..07-03) mixed N=15 EV=−3.38p/−50.7p vs aligned N=4 +1.5p、shadow mixed N=7 EV=−7.20p corroborate。
- R3 執行: reasons の mixed 文言を実状態記述へ是正 (「4H+1D 不一致」substring は query 互換維持)。
- 影響トレード: trendline_sweep×GBP_USD の HTF mixed 状態エントリーが以後 live に乗らない (shadow は継続)。aligned (bull/bear) 状態は不変。BT は `compute_daytrade_signal` 内適用のため自動同期。
- 回帰: tests/test_htf_mixed_live_stop.py (6 cases)。再 live 化は R1 のみ。詳細: [[mtf-mixed-gate-noop-forensic-2026-07-07]]

## 2026-07-06 — order 層 per-bar dedup — engine 再構築で無効化された strategy 内 guard の構造代替 (rule:R3)

- T8 forensic #2 帰結: DaytradeEngine/HourlyEngine が poll 毎に再構築され strategy instance の per-bar dedup/cooldown が live デッドコードだった問題に対し、order 層 (demo_trader) に `(entry_type, instrument, signal, closed_bar_ts)` の per-bar dedup を追加。
- primary `_tick_entry` と shadow emit DB insert が同一 key 空間を共有 (SHADOW_ALWAYS も bypass 不可)。recent_emit は第2防御として併存。block は `order_bar_dedup` counter で観測可能。
- 影響トレード: 同一バー内の重複 emit (live/shadow とも) が DB insert 前に遮断される。1バー1シグナルの BT 前提に live を整合させる方向の変更。multi-bar cooldown の代替は forensic #3 (BT 突合) 後に判断。
- 回帰: tests/test_dedup_gate_all_paths.py (12 cases)。詳細: [[t8-week1-gate-breach-2026-07-06]]
## 2026-07-06 — T9: Kalman D7 qualifying-bar telemetry + pre-reg 分母付き基準へ追補 (rule:R3)

- roadmap v2.2 T9 (最後の未完了項目)。kalman_d7 に QUALBAR print telemetry を追加 — PO-UP transition バー毎に DIST/GAP/ATR-Q/RSI/session の pass/fail と emit 判定を 1 行出力。0-fire の原因 (dormant / filter落ち / 経路ブロック) が production ログで判別可能に。
- class 属性 dedup により engine 毎tick再構築でも同一バー 1 行 (3 variant 共有)。
- pre-reg 2026-05-28 に追補: 判定を「QUALBAR 数 (分母) vs 発火数 (分子)」の表に書換え。emit=True で発火ゼロなら R3 即時 forensic。
- prereg-trigger-registry に `t9-kalman-d7-fire-info` 追加 (prefix マッチ対応を watch tool に実装、BT 期待 3.9/週)。
- 影響トレード: なし (観測性のみ、シグナル判定・lot 不変更)。回帰: tests/test_kalman_d7_qualbar_logging.py (5) + prefix マッチ 1 件。

## 2026-07-06 — pre-reg トリガー監視の自動化 + env gate 宣言整合チェック (rule:R3)

- **tools/prereg_trigger_watch.py** (新規): 機械判定可能な pre-reg トリガー/決定点を registry (decisions/prereg-trigger-registry.json) で管理し毎日評価。Tier A daily cron (quant_gate_status.py) の Discord レポートに統合。初期登録 3 件: T5 復帰条件 (D1<159.50) / sweep P-S1(a) DEFER 決定点 (N≥10 or 09-30 N<5) / hull 頻度 band
- **scripts/check.py チェック8** (新規): demo_trader.py が読む `*_LIVE_ENABLE` env が render.yaml 未宣言なら WARN — decision-without-provisioning クラス (watchdog token / carry dip gate / T5 未執行の 3 例) の構造防止
- **render.yaml**: `KALMAN_D7_LIVE_ENABLE` / `USDJPY_CARRY_DIP_LIVE_ENABLE` を sync:false で宣言 (dashboard 値は不変更)
- 影響トレード: なし (監視・観測性のみ)。背景: T5 トリガーが監視主体不在で 18 日間未執行だった事故
## 2026-07-06 — T5 pre-reg 発動執行: JPYキャップ撤退 SIZE lever 0.5x (rule:R2)

- [[jpy-cap-exit-prereg-2026-06-12]] トリガー1「USD_JPY D1 close > 160.80」が **2026-06-18 に成立済み** (161.295、以降14営業日連続、max 162.631) と本日検出。18日の執行ギャップ (監視機構不在) — pre-reg 文書に発動記録+教訓を追記。
- 執行: `_resolve_jpy_cap_exit_size_lever` — 対象4戦略 (vsg_jpy_reversal / dt_sr_channel_reversal / vix_carry_unwind / ema200_trend_reversal) の **LIVE lot 0.5x** (SIZE lever、lot チェーン最後段)。Shadow 無変更 (原則3)。code pin (`JPY_CAP_EXIT_SIZE_LEVER_ACTIVE`、env/KV 経路なし) + 回帰テスト 5 件。
- **Floor 1000u**: vix Overlap pilot の 1000u 固定検証ロット契約 ([[vix-carry-grail-removal-overlap-1000u-2026-06-15]], agg-Kelly bypass の正当性根拠) と衝突するため `max(1000, 0.5x)` で適用 — 1000u 検証ロットは no-op、1000u 超のみ半減。
- 影響トレード: 以後の対象4戦略 LIVE 送信 lot が半減 (`(JPYCAP0.5x)` lot tag + trade_reason で識別可)。Shadow/BT 系列は不変。
- 復帰 = 復帰条件 (D1<159.50 回帰+介入再確認 / BOJ 後 clean N≥10 EV>0) の KB 記録 + テスト変更を伴う PR のみ。

## 2026-07-06 — T8 初週 R2 STOP: hull/sweep LIVE 転送を code pin で停止 (rule:R2)

- pre-reg [[sweep-hull-live-week1-prereg-2026-06-12]] 拘束ゲート抵触 (sweep=ゲート① 24日 fill 0 / hull=ゲート④ 同一バー再emit) → 裁量禁止条項に従い LIVE 転送停止。
- env フラグでなく `_*_LIVE_ENABLE = False` の code pin (lesson: KV disable は pin にならない)。Shadow は原則3で継続。
- 影響トレード: なし (両戦略とも live fill 実績 0)。復帰 = forensic 完了 + 再 LOCK PR のみ。
- 詳細: [[t8-week1-gate-breach-2026-07-06]]

## 2026-07-06 — rnb WAIT entry=0 恒常汚染の根絶 + QUALBAR print 化 (観測性 R3 バッチ)

- **rnb_usdjpy**: `compute_rnb_signal` WAIT dict の `entry: 0` (2026-04-05 起源) が PRICE_HISTORY_GUARD 発火 ~2,880件/日 の唯一の発生源と特定 → WAIT に実 Close を埋める 1 行修正。ガードの残発火が真の fetch 障害シグナルに戻る。
- **usdjpy_carry_dip QUALBAR**: `logger.info` は本番 handler 未設定で破棄されており T7 E2E 検証が構造的に不可能だった → `print(flush=True)` 化。
- 回帰: tests/test_rnb_wait_entry_price.py (3 cases)。影響トレードなし (シグナル判定・tier/lot 不変更、観測性のみ)。
- 詳細: [[rnb-wait-entry-zero-forensic-2026-07-06]]

## 2026-07-04 — Fable5 監査 Phase A バッチ: edge-cell DD mult / 孤児クローズ年齢ガード / strategy Kelly 汚染除去 (rule:R2+R3)

- **P0-1 (user 決裁)**: edge cell force-live の固定 lot に `max(1000, int(lot × _dd_lot_mult))` を適用。DD defensive 0.2x 下で stage3=10000u フル送信だったバイパスを封鎖、1000u floor でクリーン N 蓄積は継続。
- **P0-2**: `_sync_demo_to_oanda` 孤児クローズに `_ORPHAN_MIN_AGE_SEC=600` の openTime 年齢ガード (parse 不能も fail-safe skip)。再起動直後の正規 live ポジション誤クローズ競合窓を封鎖。
- **P1-1**: `_get_strategy_kelly` を `_get_strategy_kelly_clean` へ委譲 — 実弾サイジング 2 経路 (dynamic boost / half-Kelly cap) + shadow promotion の all-time 汚染 (pre-cutoff/XAU/shadow 混入) を除去。
- **影響トレード**: DD defensive 継続中の E2/E9 マッチが縮小サイズ (5000→1000u 等) で送信される。per-cell EV 評価は pips ベースのため非影響。Kelly boost/cap はクリーン N<10 戦略で不発化 (誤 boost の停止)。
- 回帰テスト 16 本を同コミットで追加。
- 詳細: [[fable5-phase-a-p0-fixes-2026-07-03]] / 監査 SSOT: [[fable5-system-audit-2026-07-02]]

## 2026-07-03 — _price_history 0価格ガード (spike/velocity gate 誤発火修正, rule:R3)

- P1 データ整合性バグ修正: fetch 全滅時の `current_price=0/None` が `_price_history`
  に混入し、spike gate が range=価格そのもの (07-02 12:31 UTC 実例: 16153.1pip/60s =
  USDJPY 161.53) で誤発火 → 当該 instrument **全戦略**の live 送信を 60s〜30min 封鎖
  (shadow-eligible は shadow 化、それ以外は drop) していた。
- 3層ガード: L1 append 前 `price>0` 検証 + `[PRICE_HISTORY_GUARD]` 検出ログ /
  L2 spike 計算側 `p>0` フィルタ / L3 velocity 計算側 `p>0` + current_price 有効時のみ評価。
- **影響トレード**: データソース障害と同期した spike/velocity の shadow 化・drop が本デプロイ
  以降消滅。07-02 12:31-13:42 の vix_carry_unwind 窓内 14/14 shadow はこのバグ起因
  (清浄データでの窓内 live 実証は依然 N=1)。正常 tick での spike/velocity 発火は不変。
  tier/lot 変更なし。
- TDD 8 cases: `tests/test_price_history_zero_price_guard.py`。
  詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.6

## 2026-07-03 — Watchdog CODE_PIN_SYNC: code pin と KV stage の自動同期

- watchdog に `CODE_PINNED_CELLS` (modules/edge_cell_promote.DISABLED_CELLS のミラー、CI equality テストで乖離固定) を追加。pin cell の KV stage!=0 を検出したら new_stage=0 を発行して同期 (rule:R3 整合性修正)。
- 動機: 2026-07-02 zombie incident で E4 KV が 1 に残置 (DECREMENT stage>=2 ガードのため自然回復しない)。「eligible と effective を区別する」教訓の恒久対応。
- **影響トレード**: なし。lot 決定は従来どおり code pin (`DISABLED_CELLS`) が支配し、本変更は KV 表示状態のみ同期する。
- 詳細: [[edge-cell-e1-e4-code-disable-2026-07-02]] 追記 2026-07-03

## 2026-07-02 — Edge cell E1/E4 code-level DISABLE + watchdog DECREMENT 床バグ修正

- `DISABLED_CELLS` に E1 (dt_bb_rsi_mr ASN SELL) / E4 (bb_rsi_reversion NY SELL) を追加 (rule:R2)。T10 KILL ([[bb-rsi-t10-kill-2026-07-02]]) 拘束事項3 の実施。
- **影響トレード**: E4 経由の bb_rsi_reversion live 発火 (2026-07-02 13:08-19:55 UTC の 11 件が最後) は本デプロイ以降ゼロ。E1 は LOCK 以降 live N=0 で実挙動不変。dt_bb_rsi_mr の通常 PAIR_PROMOTED 経路は不変。
- watchdog `max(1, stage-1)` 床バグ修正 (rule:R3) — stage=0 セルの 0→1 再武装 (zombie) を根絶。**2026-07-02 10:18Z〜デプロイまでの間、E4 の KV disable は 15 分毎に無効化されていた**点に注意 (該当 live 4 件は分析時に E4 force-live として扱う)。
- 詳細: [[edge-cell-e1-e4-code-disable-2026-07-02]]

## 2026-07-02 — Aggregate Kelly Gate raw-fix + 1000u 契約 min-lot bypass (rule:R3+R2)

- P1 死にゲート修正: `kelly_criterion` の `max(0,·)` クリップにより v9.0 SHIELD
  Aggregate Kelly Gate (`< 0` 判定) が構造的に発火不能だった。`full_kelly_raw`
  (非クリップ) を追加し `_get_aggregate_kelly` を raw 化。
- interplay (user 決裁): 1000u 固定契約 3 戦略 (vix_carry_unwind /
  usdjpy_carry_dip_accumulator / sweep_reversion_eurgbp_late) は
  allowlist AND 実効 units<=1000 AND 非XAU の二重ガードで gate bypass。
  hull_donchian_fade (5000u) は対象外。
- 影響: aggregate raw Kelly<0 (2026-07-02 時点 edge=-0.3617) の間、promoted
  非 sentinel/非 edge-cell/非 1000u契約 の OANDA 転送が初めて実ブロックされる。
  tier/lot 変更なし。TDD 10 cases。
- Decision: `decisions/agg-kelly-gate-raw-fix-minlot-bypass-2026-07-02.md`

## 2026-05-21 — SR-family shadow_emit OANDA audit restoration

- `shadow_emit_signals` が `_tick_entry` を経由せず `demo_trades` に直接 Shadow row を書くため、SR-family の OANDA audit skip row が欠落していた問題を修正。
- `sr_*` shadow emit は `demo_trades` 記録後に `oanda_audit` へ `bridge_status=skipped` / `block_reason=shadow_tracking` を永続化する。
- 対象は監視可視性の復旧のみ。OANDA 発注、Live/Shadow 判定、lot sizing は変更しない。

## 2026-05-18 — /api/oanda/stats range window 修正

- OANDA stats endpoint が frontend の `range=today|7d|30d|all` を無視して全期間集計していた問題を修正。
- 既定 window を demo stats と同じ 30d + `2026-04-08T00:00:00` floor にし、`range=all` も fidelity cutoff 以降のみ集計。
- `_filters` / `_db_path` を返し、stats 系 endpoint の表示条件を監査可能にした。

## 2026-05-18 — trend_rebound THESIS_INVALID FORCE_DEMOTED

- C audit verdict により `trend_rebound` を FORCE_DEMOTED に固定。
- 21d shadow N=60 WR=33.3% EV=-1.29p PF=0.66 Kelly=0.000 WF=0/3。
- `trend_rebound` x USD_JPY の PAIR_PROMOTED と EUR_USD の PAIR_DEMOTED を撤去し、
  FORCE_DEMOTED 一括管理へ統合。
- Decision: `decisions/trend-rebound-thesis-invalid-2026-05-18.md`。

## 2026-05-18 — HourlyEngine Shadow Ramp Activation

- 全 10 `daytrade_1h*` modes を `auto_start=True` に変更し、HourlyEngine dormant 状態を解除。
- `_shadow_always` に KSB+DMB+5 PriceShockRev を frozenset 固定し、H1 alpha source を一括 Shadow-only にした。
- XAU modes と 15m/scalp Live 経路は変更なし。Decision: `decisions/hourly-engine-shadow-ramp-2026-05-18.md`。

## 2026-05-18 — Price-Shock Rev Live Activation v2 MIN Lot (rule:R1)

- 5 Price-Shock Rev H1 戦略を Tier 2 Live MIN lot に移行。
- `_shadow_always` から Price-Shock Rev を削除し、KSB/DMB は Shadow-only 維持。
- Live lot は 1000u 固定。lot ramp は N>=30 pre-reg evaluator の提案のみで自動変更しない。
- N>=10 watchdog は EV<0 または Wilson_lower<0.40 で auto-demote state を記録。Decision: `decisions/price-shock-rev-live-activation-2026-05-18.md`。

## 2026-05-18 — Price-Shock Reversion Tier 1 Phase B-1 Shadow

- H1 negative shock LONG 5 戦略を `strategies/hourly/` に追加。
- BT runner と `shift(1)` / rolling 252 / vol quintile を bar-by-bar 一致。
- `demo_trader` で Shadow-only 強制、EUR_GBP/EUR_AUD shared lock を追加。
- Live promote は `decisions/price-shock-rev-promote-criteria-2026-05-18.md` で別判定。

## 2026-05-18 — PRIME v2 Apply

- PRIME v2 apply: 5 entries demoted to Tier C per P1 re-eval verdicts.
- EDGES replaced with the 2026-05-18 Render shadow non-XAU recomputation.
- All current PRIME matches remain Shadow-only; A/B live-lock structure preserved for future candidates.

## 2026-05-18 — PRIME B' Micro LIVE Forward-Fix

- Corrected the grade mismatch between LIVE promotion and Micro LIVE exploration.
- Revived `fib_reversal_PRIME` and `sr_fib_confluence_GBP_ADXQ2` as Tier B `0.05x` measurement cells.
- Kept the other 4 PRIME entries at Tier C `0.0`; no Tier A entries active.
- Existing watchdog safety net remains unchanged: auto-demote at Live `N>=10` and `EV<0`.

## Fidelity Cutoff Timeline

```
2026-04-02  システム稼働開始
     |
2026-04-08  ★ Fidelity Cutoff (v6.3 SLTP修正後)
     |       ├── この日以降のデータ = "クリーンデータ"
     |       └── 以前のデータ = "バグ汚染データ"（SLTPチェッカーバグ含む）
     |
2026-04-09  v7.3-v7.6: XAU修正チェーン
     |       └── XAUデータ: v7.5以前は MAX_SL_DIST=$0.20バグで汚染
     |
2026-04-10  ★★ v8.0-v8.3: 戦略大改革
     |       ├── v8.0: vol_momentum 2.0x, engulfing_bb停止, TREND_BULL遮断
     |       ├── v8.1: TREND_BULL MR免除
     |       ├── v8.2: orb_trap PAIR_PROMOTED, vol_momentum 1.0x
     |       ├── v8.3: 確認足フィルター（bb_rsi/fib/ema_pullback）
     |       └── v8.3以降のデータ = "確認足効果測定用"
     |
2026-04-10  ★★★ v8.4: XAU停止 + Shadow汚染除去
     |       ├── XAUモード停止: scalp_xau, daytrade_xau auto_start=False
     |       ├── get_stats() is_shadow=0 フィルター追加
     |       └── v8.4以降 = "FX-only クリーンデータ"
     |
2026-04-12  Knowledge Base構築
     |       └── 評価基盤の確立
     |
2026-04-12  ★ v8.5: 学術文献6新エッジ戦略 (全Sentinel)
     |       ├── session_time_bias, gotobi_fix, london_fix_reversal
     |       ├── vix_carry_unwind, xs_momentum, hmm_regime_filter
     |       └── 25論文ベース、DaytradeEngine 32戦略化
     |
2026-04-12  ★★ v8.6: 本番昇格 + モード再編
     |       ├── session_time_bias × 3ペア PAIR_PROMOTED (BT WR=69-77%)
     |       ├── london_fix_reversal × GBP_USD PAIR_PROMOTED (BT WR=75%)
     |       ├── london_fix_reversal × USD_JPY PAIR_DEMOTED (BT WR=28.6%)
     |       ├── xs_momentum × USD_JPY PAIR_DEMOTED (BT EV=-0.129)
     |       ├── scalp_eurjpy auto_start=False (friction/ATR=43.6%, 構造的不可能)
     |       ├── scalp_5m_eur + scalp_5m_gbp 新規モード追加 (5m摩擦改善)
     |       ├── 金曜/月曜ブロック全撤去 — 原則#1「攻める」準拠
     |       ├── GBPアジアセッション除外フィルター実装
     |       ├── DSR (Deflated Sharpe Ratio) 実装 — Bailey & Lopez de Prado (2014)
     |       └── BT/Live乖離分析: bb_rsi 25pp乖離の原因分解完了
     |
2026-04-12  v8.7: BT基盤強化
     |       ├── BT Friction Model v3 (Spread/SL Gate + RANGE TP + Quick-Harvest反映)
     |       ├── backtest-long DT/1H対応 (120-365日チャンクBT)
     |       └── BT/Live乖離: Scalp 14-27pp→5-10pp, DT 5.5-10pp→2-4pp (期待)
     |
2026-04-12  v8.8: 生データアルファマイニング
     |       ├── vol_spike_mr: 3x range spike fade (BT JPY PF=1.92, 全戦略最高)
     |       ├── doji_breakout: 3連続doji breakout follow
     |       ├── post_news_vol × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |       └── ema200_trend_reversal × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |
2026-04-13  ★★★ v8.9: Equity Reset — クリーンデータ起点
     |       ├── 旧DD: 2,899pip (289.9%) ← XAU(-2,280pip) + pre-cutoffバグ汚染
     |       ├── リセット: v8.4(2026-04-10T12:00)以降FX-only非Shadowで再計算
     |       ├── 新DD: 8.4pip (0.8%) → lot_mult=1.0x (フルロット)
     |       └── ワンショットマイグレーション (eq_reset_v89フラグで1回のみ実行)
     |
2026-04-17  ★ v9.2.1: MTF Regime Engine + v9.2 guardrail 無効化
     |       ├── D1×H4×H1 階層 regime labeler (7-class)
     |       ├── EUR_USD η² 105× improvement, flip rate 6.1%→0.6%
     |       ├── v9.2 guardrail デフォルト無効化 (6.5年検証で符号逆)
     |       └── shadow_monitor + DB mtf_* カラム追加
     |
2026-04-17  ★★ v9.3 Phase A-C: Strategy-aware MTF + P0 Family Map Forensics
     |       ├── Phase A: 戦略ファミリ考慮 retrospective (LIVE aligned WR +22.9pp)
     |       ├── Phase B: 本番OOS反実仮想 (+508p 改善) — TF sign flip 検出
     |       ├── Phase C P0: 3戦略 mislabel 修正 (macdh_reversal/engulfing_bb → TF, ema_cross → MR)
     |       ├── CORRECTED map で ALL Δ PnL +306p→+1129p (3.7×), 全family符号一致
     |       └── research/edge_discovery/strategy_family_map.py (production module)
     |
2026-04-17  ★★★ v9.3 Phase D+E: A/B Gate Routing + REGIME_ADAPTIVE
             ├── **Phase D**: Hash-based A/B routing (MD5 mod 2 → mtf_gated / label_only)
             │   ├── DB: gate_group / mtf_alignment / mtf_gate_action 追加
             │   ├── Group A conflict → LIVE→SHADOW downgrade (soft gate)
             │   └── 50/50 分布確認 (N=1000 ±50)
             ├── **Phase E**: REGIME_ADAPTIVE_FAMILY (regime別 family override)
             │   ├── bb_rsi_reversion: trend_up=TF / trend_down=MR
             │   ├── fib_reversal: trend_up=MR / trend_down=TF
             │   └── LIVE ΔWR +2.4pp→+9.3pp (4×), IS aligned gap +12.0pp
             └── Tests: 234 passed (new: test_ab_gate.py 7 + TestRegimeAdaptive 7)

2026-04-20  v9.3 Phase F: FAMILY MAP 拡張 — ELITE_LIVE/PAIR_PROMOTED 6戦略追加分類
             ├── **TF追加**: gbp_deep_pullback, trendline_sweep (wiki Category根拠)
             ├── **MR追加**: vwap_mean_reversion, wick_imbalance_reversion (wiki MR根拠)
             ├── **SE追加**: london_fix_reversal (Krohn 2024), vix_carry_unwind (Brunnermeier 2009)
             ├── 未分類→"unknown"から"conflict/neutral"へ: A/B gate が ELITE_LIVEにも機能するように
             ├── RANGINGレジーム下: gbp_deep_pullback/trendline_sweep → conflict → shadow降格（正常）
             ├── RANGINGレジーム下: vwap_mean_reversion/wick_imbalance_reversion → aligned（正常）
             ├── pending (BT forensics必要): doji_breakout, post_news_vol, squeeze_release_momentum
             └── Tests: 234 passed (既存テスト全pass、新分類はwiki根拠で実装)

2026-04-20  ★ v9.x Quant Readiness: 2D v2 Pre-Registration + Dashboard (parallel A+B)
             ├── **Task A — Regime 2D v2 Pre-Registration (data snooping 防止)**:
             │   ├── knowledge-base/wiki/analyses/regime-2d-v2-preregister-2026-04-20.md
             │   ├── 43戦略の family/regime×direction 仮説を backfill 前に pre-commit
             │   ├── Gate 閾値確定: N≥50/cell, |ΔWR|≥10pp, Bonferroni α=0.05/K, IS/OOS 符号一致
             │   ├── Pass/Fail 判定を機械化可能な形で記述 (§3.7)
             │   ├── 禁止事項 (§5): 閾値/仮説の事後調整, cell 除外の事後正当化, 1日データ実装
             │   ├── Bailey & Lopez de Prado (2014) *Backtest Overfitting* 流儀の pre-register
             │   └── Post-execution 記録枠を空のまま commit → data snooping 抑止
             ├── **Task A — Rescan script**: scripts/regime_2d_v2_rescan.py (~470行)
             │   ├── --trades-json input / --output-dir / --dry-run
             │   ├── Fisher's exact (two-sided, SciPy 非依存) + Bonferroni strict
             │   ├── matrix_all / asymmetry_strict / hypothesis_check / gate_candidates / sanity_check
             │   ├── 既存 REGIME_ADAPTIVE_FAMILY (bb_rsi/fib) の sanity check も同時実行
             │   └── Dry-run smoke test pass (synthetic 600 trades, k_eff=1)
             ├── **Task B — Quant Readiness Dashboard**: tools/quant_readiness.py (~340行)
             │   ├── --api / --json / default https://fx-ai-trader.onrender.com
             │   ├── Data accumulation (Live/Shadow N, Kelly progress)
             │   ├── Gate thresholds (Kelly N≥20, DSR N≥50, PP review N≥30+EV>0, FD-risk EV<-0.5)
             │   ├── mtf_regime coverage (labeled/total, regime diversity, missing list)
             │   ├── Alerts (Kelly/coverage/trend_down zero/FD-risk triggers)
             │   ├── セキュリティ: URL scheme allowlist + custom opener (HTTP/HTTPS のみ) →
             │   │   file:// / ftp:// 攻撃面遮断 (CWE-939), verified SSL context (CWE-295)
             │   └── 本番 smoke test: Live=14/20 (70% Kelly), Shadow=849, coverage=30.1% (target 80%)
             │       → trend_down_* 0件警告, backfill 前提の blocker 検出
             ├── **Tests**: tests/test_quant_readiness.py 13 cases
             │   └── URL validation (file/ftp reject), build_accumulation/gate/coverage, alerts, render
             ├── tier_integrity_check --check: PASS (ERROR=0)
             ├── strategies_drift_check: PASS (65 pages clean, exit 0)
             └── 判定プロトコル: **実装提案なし**. 本 commit は "infrastructure 整備" であり
                 backfill 後の 2D v2 rescan / daily readiness snapshot のための pre-commit.
                 実際の strategy 昇格・降格は backfill + N 蓄積後の human review を要求.

2026-04-20  ☆ v9.x Diagnostic: Regime × Strategy 2D Kelly Asymmetry Scan (NO-OP)
             ├── **目的**: 43戦略 × 7 regime × 2 direction の非対称性マトリクスを全探索
             │   └── Phase E (bb_rsi_reversion / fib_reversal) 同等候補があれば REGIME_ADAPTIVE 追加
             ├── **データ**: 本番 API N=786 (Cutoff 2026-04-16以降 / XAU除外 / closed)
             │   └── mtf_regime 本番 DB populate 率 24.5% → research/edge_discovery/mtf_regime_engine で
             │       retrospective labeling (Phase B 済み pipeline 再利用) で 100% カバー
             ├── **結果**: Gate 通過候補 = **0件**
             │   ├── 観測期間 4.6日 → lesson-reactive-changes "1日データ禁止" に抵触
             │   ├── Regime coverage 欠損 (trend_down_* / uncertain が 0 件)
             │   ├── 43戦略中 N≥50/cell を 1つ以上持つのは ema_trend_scalp のみ
             │   ├── Bonferroni α=0.0125 で有意 cell ゼロ (最小 p=0.277)
             │   └── 観測された方向非対称性は全て既存 strategy_aware_alignment で処理済
             ├── **実装**: なし (判断プロトコル #1 違反回避)
             ├── **別 task 提案**: scripts/backfill_mtf_regime.py 作成 → 過去トレードに mtf_regime 注入 → N ≈ 1500+ 規模で再評価
             └── Artifacts: knowledge-base/wiki/analyses/regime-strategy-2d-2026-04-20.md
                 + /tmp/fx-regime-2d-analysis/{matrix_all,asymmetry,asymmetry_strict}.csv

2026-04-20  ★ v9.4: wiki/strategies KB ドリフト一掃 + 検出ツール導入
             ├── 13 ページの Status 行を tier-master.json と整合
             │   ├── bb-rsi-reversion.md: "Tier 1 PP×USD_JPY" → SCALP_SENTINEL + PAIR_DEMOTED(全4ペア)
             │   ├── orb-trap.md: "Tier 1 PP×3ペア" → FORCE_DEMOTED (v9.1 負EV確定)
             │   ├── trendline-sweep.md: "ELITE+FD+PP" → ELITE_LIVE のみ (v9.0 整理)
             │   ├── bb-squeeze-breakout / engulfing-bb / sr-channel-reversal / ema-pullback:
             │   │   FD下のPP死コード記述を削除 (v9.1 cleanup 反映)
             │   ├── london-fix-reversal: "PP×GBP" → Phase0 Shadow (v9.1 GBP PP削除)
             │   ├── vol-momentum-scalp: "SHADOW" → PAIR_PROMOTED×EUR_JPY
             │   ├── three-bar-reversal: "UNI_SENTINEL" → Phase0 Shadow
             │   ├── stoch-trend-pullback: "Sentinel" → FORCE_DEMOTED (v8.9 剥奪)
             │   ├── vol-surge-detector: "Sentinel" → SCALP_SENTINEL + PAIR_DEMOTED
             │   ├── doji-breakout: Status追加 (UNI_SENTINEL + PP×GBP/USDJPY)
             │   ├── fib-reversal: "Tier 2" → FORCE_DEMOTED (Recovery Path active)
             │   ├── liquidity-sweep: "Tier 2 Sentinel" → UNIVERSAL_SENTINEL 明示
             │   ├── post-news-vol: Status 行の USD_JPY をPP→PAIR_DEMOTED に訂正
             │   └── dual-sr-bounce: "FORCE_DEMOTED" → REMOVED (v9.1 死コード削除)
             ├── 旧 Status は「履歴」/「Previously ...」で保持 (削除禁止ルール遵守)
             ├── **新ツール**: tools/strategies_drift_check.py
             │   ├── tier-master.json を truth source として読み込み、md の Status 行を検証
             │   ├── 否定コンテキスト / 履歴マーカーはスキップ
             │   ├── PAIR_PROMOTED scope 内のペアのみ truth と突合
             │   └── exit 1 で pre-commit / CI 組み込み可能
             ├── **テスト**: tests/test_strategies_drift_check.py (11 cases, all pass)
             │   └── 実 KB 回帰テスト込み (test_live_kb_passes_drift_check)
             ├── **lesson**: wiki/lessons/lesson-strategies-page-drift.md
             │   └── lesson-kb-drift-on-context-limit の strategies/ 特化版
             └── 独立ツール設計: tier_integrity_check.py (code 整合) と分離
                 pre-commit 実行順: tier_integrity_check --write → strategies_drift_check

2026-04-20  ★ v9.x Priority 3: Sentinel N 測定バグ修正
             ├── **症状**: UI で 62 戦略中 bb_squeeze_breakout のみ N=1、他 61 戦略 N=0
             │   └── 実測: 本番 DB に closed Shadow trades が 1,466 件存在
             ├── **原因**: `get_trades_for_learning` は is_shadow=0 固定フィルタ
             │   └── `_strategy_n_cache` → `_build_strategy_status_map` の n が Live のみに
             ├── **修正**: `get_shadow_trades_for_evaluation()` 新関数 (is_shadow=1 固定)
             │   ├── `_build_strategy_status_map` に shadow_n/wr/ev 付与
             │   ├── `/api/sentinel/stats` 新設 (entry_type/instrument/after_date フィルタ)
             │   └── `get_trades_for_learning` は**変更なし** (lesson-shadow-contamination 維持)
             └── Tests: 244 passed (new: test_shadow_stats.py 10 = 正例4+負例3+空3)
             参照: [[lesson-sentinel-n-measurement-bug]]

2026-04-20  ★ v9.x Priority 1: Sentinel score_gate バイパス (Clean Slate 窒息対策)
             ├── **背景**: Clean Slate(2026-04-16)以降 Live N=0 / Sentinel N=1(bb_squeeze_breakout only, 62戦略中)
             │   └── score_gate(score<0) が 1日396件ブロック → Sentinel shadow も蓄積不能
             ├── **修正**: demo_trader.py L2761 score_gate に `_sentinel_score_bypass` 追加
             │   ├── SCALP_SENTINEL ∪ UNIVERSAL_SENTINEL のみバイパス (Live 挙動不変)
             │   ├── FORCE_DEMOTED / _ELITE_LIVE / _PAIR_PROMOTED は従来通り score_gate 適用
             │   └── L4179 safety net で is_shadow=True 強制 → 学習汚染リスクゼロ
             ├── **観測性**: Sentinel バイパス時 `[SCORE_GATE] Sentinel bypass:` ログ発行
             ├── **対称性**: spread_wide(L3483) / spike(L3522) と同形パターン
             └── Tests: 234 passed (no new tests — 既存挙動 guard のみ)
             注記: P3 実測で Sentinel N=1,466 判明 → 「N=1」は測定バグ由来。本 bypass は純粋な上振れ策として残存有効。

2026-04-20  ★ v9.x Priority 2: PAIR_PROMOTED SSOT drift 修正 (accounting cleanup)
             ├── demo_db.py `_pair_promoted_overrides` 5 組合せを削除
             │   ├── (ema_pullback, USD_JPY), (fib_reversal, EUR_USD)
             │   ├── (bb_squeeze_breakout, USD_JPY/EUR_USD), (sr_channel_reversal, EUR_USD)
             │   └── 全て v9.1 で demo_trader._PAIR_PROMOTED から既に削除済み → SSOT 二重化解消
             ├── Live 監査 (Render DB, 2046 trades):
             │   ├── fib_reversal×EUR_USD: Live N=51 WR=39% EV=-0.298 PnL=-15p (post 4/7)
             │   ├── bb_squeeze×EUR_USD: Live N=26 WR=11.5% EV=-2.32 (**壊滅**)
             │   ├── sr_channel×EUR_USD: Live N=26 WR=19% EV=-1.20 (**壊滅**)
             │   └── 他 2 組は Live N<20 & Shadow 主体 → 昇格根拠不足
             ├── 365d BT 再検証 Gate: 全 5 組合せが EV≥+0.2 ATR & N≥100 を満たさず
             ├── 60d→180d 符号反転: fib_reversal×EUR_USD (+0.271 → -0.147) — lesson-orb-trap 再現
             ├── 新規 PAIR_PROMOTED 追加: **なし** (Gate 通過候補ゼロ)
             ├── **Retroactive effect**: 起動時 SHADOW_MIGRATION で 66件が is_shadow=0→1 化
             │   └── Kelly プールから stale 負EV trades 除去 → aggregate EV 改善見込み
             ├── **Behavioral change**: なし (5 組合せは既に Live 未送信、shadow 扱い)
             └── 詳細: wiki/analyses/pair-promoted-candidates-2026-04-20.md

2026-04-20  🚨 v9.x Hotfix: resend-shadow-leak — FORCE_DEMOTED が OANDA 実弾送信されるバグ修正
             ├── **症状**: is_shadow=1 の open trade に oanda_trade_id が設定されている
             │   ├── sr_channel_reversal USD_JPY (FORCE_DEMOTED) → oanda_trade_id=320787
             │   ├── orb_trap GBP_USD (FORCE_DEMOTED) → oanda_trade_id=318111
             │   ├── bb_rsi_reversion EUR_USD (PAIR_DEMOTED) → oanda_trade_id=325370
             │   └── vwap_mean_reversion GBP_USD (MTF gate shadow降格) → oanda_trade_id=325362
             ├── **原因**: `_resend_pending_oanda_trades()` (起動時実行) が
             │   `get_open_trades_without_oanda()` を呼ぶ際に `is_shadow` を未フィルタ
             │   → 起動/OANDA再接続時に is_shadow=1 trades も OANDA に送信されていた
             ├── **修正**: `demo_db.py` `get_open_trades_without_oanda()` のSQL に
             │   `AND is_shadow=0` 追加 (1行) → shadow trades は resend 対象外
             └── **lesson**: [[lesson-resend-shadow-leak]]

2026-04-20  ★ v9.5: ema_trend_scalp / trend_rebound Live pair-level breakdown + PAIR_DEMOTED 拡充
             ├── **背景**: Post-P2 Kelly 分析で ema_trend_scalp edge=-0.353 / trend_rebound edge=-0.455
             │   が aggregate edge=-0.1348 の主因と判明 ([[shadow-baseline-2026-04-20]] Phase 2)
             ├── **Live pair-level 実測** (Render prod, is_shadow=0, closed):
             │   ├── ema_trend_scalp: USD_JPY N=19 EV=-0.92 / EUR_USD N=16 EV=-1.22 / GBP_USD N=4 EV=-1.65
             │   ├── trend_rebound:   USD_JPY N=10 EV=-0.78 / EUR_USD N=7 EV=-1.43 / GBP_USD N=1
             │   └── 99% は Fidelity Cutoff (2026-04-16) 以前、v9.2 FORCE_DEMOTE 以降は新規発生なし
             ├── **Shadow↔Live 対照で符号逆転検出** — lesson-orb-trap-bt-divergence 再現:
             │   ├── trend_rebound×USD_JPY: Shadow EV=+1.43 (N=12) → Live EV=-0.78 (N=10)
             │   └── trend_rebound×EUR_USD: Shadow EV=+1.16 (N=7) → Live EV=-1.43 (N=7)
             ├── **Gate (N≥10 ∧ EV≤-0.5 ∧ (WR≤20 ∨ PnL≤-10)) 通過**: 2 combos
             │   ├── ema_trend_scalp×USD_JPY (PnL=-17.5 で PnL criterion 通過)
             │   └── ema_trend_scalp×EUR_USD (既に PAIR_DEMOTED)
             ├── **修正 1**: demo_trader._PAIR_DEMOTED に `(ema_trend_scalp, USD_JPY)` 追加
             │   ├── v8.9 で "SELL PB境界バグ修正済み → 再蓄積" として解除されていたが
             │   │   v9.2 FORCE_DEMOTE で "再蓄積" 方針は無効化。documentation marker として記録
             │   └── 挙動変化なし (strategy が既に FORCE_DEMOTED で OANDA 遮断済)
             ├── **修正 2**: demo_db._force_demoted (shadow migration set) の SSOT drift 修正
             │   ├── demo_trader._FORCE_DEMOTED (18) と demo_db._force_demoted (15) が drift
             │   ├── 欠落: ema_trend_scalp, intraday_seasonality, atr_regime_break
             │   ├── → 起動時 migration で is_shadow=0 残留 trades (ema_trend_scalp Live N=39 等)
             │   │   が shadow pool 化されず Kelly を汚していた bug
             │   └── 修正後、次回起動時 migration で stale Live trades が shadow 化
             ├── **保留**: trend_rebound×USD_JPY (WR=30% PnL=-7.8 で Gate 微不通過、監視継続)
             │   └── 次 Live N≥20 到達時に再判定。lesson-reactive-changes 遵守で反射降格なし
             ├── Validations: tier_integrity_check ERROR=0, strategies_drift_check pass
             └── 詳細: wiki/analyses/ema-tr-live-breakdown-2026-04-20.md
```

2026-04-22  v9.x: TP-hit Quant Analysis (research only, no code change)
             ├── **スコープ**: 全 strategy × pair で TP-hit したトレードの再現性を定量化
             ├── **データ**: `/api/demo/trades?limit=5000` → 非XAU closed 2,267 / WIN 698
             ├── **Phase 1**: Strategy×pair, regime, TF, session, MTF alignment で WR セグメント化
             │   └── 最多 TP-hit = bb_rsi_reversion×USD_JPY (N=127、全 WIN の 18.2%)
             ├── **Phase 2**: TP-hit vs LOSS の feature 分布差 (Mann-Whitney U, Bonferroni)
             │   ├── spread_at_entry: WIN=0.763 < LOSS=0.842 (p=1.94e-5, 有意)
             │   ├── confidence: WIN=59.55 < LOSS=61.16 (負相関, p=1e-3)
             │   └── score: p=0.42 (score_gate は TP-hit 予測力ゼロ)
             ├── **Phase 3-4**: 事前予測可能特徴のみ (post-hoc MAFE 除外) で条件マイニング
             │   ├── 候補 m=107、Bonferroni α=4.7e-4 通過 5 件
             │   └── 高 WR だが 4/5 は Kelly<0 (BEV 押し上げ vs friction キャンセル)
             ├── **Phase 5 安定性** (pre/post cutoff × live/shadow 符号一致):
             │   ├── **最 robust**: bb_rsi_reversion×EUR_USD×BUY (WR 64.5%, EV +1.84 pip,
             │   │   Kelly +0.41, 4/4 window 符号一致) — ただし N=31 境界
             │   └── **最 fragile**: bb_rsi_reversion×USD_JPY×RANGE
             │       pre EV +0.16 → post EV -1.56 (1.7 pip 悪化、[[lesson-orb-trap-bt-divergence]] 再現)
             ├── **DSR 警告**: Bonferroni 通過 5 件は帰無仮説下 FP 期待値 5.4 とほぼ同 → 
             │   family-wise シグナルは弱い、個別採択は stability で決定すべき
             ├── **制限**: Post-cutoff Live N=0、shadow は truncated sample bias 残存、
             │   close_reason 6種(TP_HIT/OANDA_SL_TP/SIGNAL_REVERSE/...)を包括
             ├── **実装提案なし** ([[lesson-reactive-changes]] 遵守) — KB 記録のみ
             └── 詳細: wiki/analyses/tp-hit-quant-analysis-2026-04-20.md,
                 raw/analysis/tp-hit-raw-2026-04-20.csv, scripts/analyze_tp_hits.py

2026-04-22  ★ v9.x: Roadmap-acceleration 二重WF確証による PAIR_PROMOTED 昇格 2件
             ├── **スコープ**: クロスTF walk-forward stability で pos_ratio=1.00 を示した
             │   2セルを Phase0 auto-Shadow / 既存PP未指定 → PAIR_PROMOTED 昇格
             ├── **`streak_reversal × USD_JPY` PAIR_PROMOTED 新規**
             │   ├── P2 15m 365d × 20d window WF (18窓): N=466 EV=+1.362 pos=1.00 CV=0.65 ✅
             │   ├── P4 5m  180d × 30d window WF (7窓):  N=693 EV=+0.948 pos=1.00 CV=0.62 ✅
             │   ├── Bonferroni BT: 5streak BUY N=586 WR=58.7% p=1.3×10⁻⁵
             │   └── 単一TF根拠を超えたクロスTF確証 → 従来 Phase0 inline auto-Shadow を解除
             ├── **`vwap_mean_reversion × USD_JPY` PAIR_PROMOTED 追加**
             │   ├── P4 5m 180d × 30d WF: N=155 EV=+0.925 pos=1.00 CV=0.51 ✅ (最低CV)
             │   ├── 既存PP (EUR_JPY/GBP_JPY/EUR_USD/GBP_USD) に USD_JPY を追加、5ペア化
             │   └── BT 15m 16bar: N=705 WR=55.0% EV=+2.98pip annual +2,099pip
             ├── **根拠プロトコル**: 両セルとも P2(15m)+P4(5m) 二重 WF クロスTF + Bonferroni BT。
             │   lesson-orb-trap-bt-divergence (短期60d BT のカーブフィッティング) を回避するため
             │   365d WF を一次根拠、5m 180d WF を二次確証、単一TF根拠を超える水準を要求した
             ├── **Validations**: tier_integrity_check.py --check ERROR=0 (PP 15→17 entries)、
             │   sync_kb_index.py --write で index.md portfolio セクション更新
             ├── **KB同梱**: wiki/strategies/streak-reversal.md / vwap-mean-reversion.md Status 更新
             │   (lesson-strategies-page-drift / lesson-kb-drift-on-context-limit 遵守)
             └── 詳細: raw/analysis/roadmap-acceleration-synthesis-2026-04-22.md,
                 raw/bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md,
                 raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.md

## バージョン別データ切り口

| 目的 | date_from | 除外条件 | 理由 |
|------|----------|---------|------|
| 全体傾向 | 2026-04-08 | is_shadow=0 | Fidelity Cutoff後クリーンデータ |
| **v8.3確認足効果** | **2026-04-10** | is_shadow=0 | v8.3デプロイ後のみ |
| **XAU停止効果** | **2026-04-10 夕方〜** | is_shadow=0, XAU除外 | v8.4デプロイ後 |
| **FX純粋評価** | 2026-04-08 | is_shadow=0, XAU除外 | FXのみの真のパフォーマンス |
| BT/ライブ比較 | 全期間 | なし | BT乖離幅の把握 |

## 各バージョンの影響範囲

### v7.x (2026-04-09): XAU修正チェーン
| Version | Change | Affected Strategies | Affected Data |
|---------|--------|-------------------|---------------|
| v7.3 | gold PBルーズ化+bbσバグ修正 | gold_trend_momentum | XAU DT |
| v7.4/b/c | extreme_momentum: ADX≥25, MACD-H/EMA9免除 | gold_trend_momentum | XAU DT |
| v7.5 | MAX_SL_DIST: XAU $0.20→$100 | **全XAU戦略** | ★ v7.5前のXAU SLデータは全て汚染 |
| v7.6 | Sentinel units: XAU 1000u→1u | XAU OANDA連携 | XAU audit |

### v8.x (2026-04-10〜): 戦略大改革
| Version | Change | Impact on Data |
|---------|--------|---------------|
| v8.0 | vol_momentum 2.0x, TREND_BULL全遮断 | DT TREBULLトレード消滅 |
| v8.1 | MR免除 (dt_bb_rsi_mr, dt_sr_channel_reversal通過) | DT MRトレード復活 |
| v8.2 | orb_trap PAIR_PROMOTED, vol_momentum 1.0x, bb_squeeze停止 | orb_trap OANDA送信開始 |
| **v8.3** | **確認足(bb_rsi/fib/ema_pullback)** | **★ 即死率の変化を測定する基準点** |
| **v8.4** | **XAU停止 + Shadow除去** | **★ FX-onlyの真のPnLを測定する基準点** |
| v8.5 | 学術文献6新エッジ戦略 (全Sentinel) | 新戦略のライブデータ蓄積開始 |
| **v8.6** | **session_time_bias/london_fix PROMOTED + 5mモード拡張 + DSR実装** | **★ 学術エッジの本番検証開始** |
| v8.7 | BT Friction Model v3 + backtest-long | BT信頼性向上 (乖離幅縮小) |
| v8.8 | vol_spike_mr + doji_breakout + PAIR_DEMOTED追加 | 新アルファ源 + 出血戦略停止 |

## Related
- [[edge-pipeline]] — エッジ仮説の評価はどのデータ期間を使うべきか
- [[independent-audit-2026-04-10]] — "Shadow除去なしにWR/EVは信頼できない"
- [[bb-rsi-reversion]] — WR 52.2% vs 34% の矛盾はデータ期間の差
- [[friction-analysis]] — avg_friction 7.04 は XAU込み。FX-only≈2.5pip
2026-05-04  FX Nexus Step 1 pre-reg and shadow audit scaffolding
             ├── Added FX graph MLE currency value and triangular alpha residual data-layer functions.
             ├── Added opt-in `exec_lag_jitter` timing audit path for DT backtests; default remains 0.0.
             ├── Added `tools/fx_nexus_shadow_audit.py` to produce H1/H2/H3 verdict markdown.
             └── Locked Step 1 criteria in `wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md`.
