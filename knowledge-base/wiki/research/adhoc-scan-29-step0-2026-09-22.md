# 臨時外部仮説スキャン — #29 S1 census step 0: license-free × dense × 凍結可能な中銀声明 stance モデルの候補同定 (2026-09-22)

**位置づけ**: [[edge-development-pipeline-2026-07-18|edge パイプライン]] §5 追補 (2026-08-14 user 承認) の WIP 規則「今日着手できる本数が 0 なら期日を待たず**臨時スキャン (R3)**」の発動。registry `edge-supply-scan-monthly` (第6次 = 2026-10-18) の期日は消費しない (月次 cadence とは別建ての臨時記録、[[path-to-win-decision-memo-2026-09-20|決裁メモ v2]] §4.1-8 / §4.1-17 の「S1 census 結果を第6次に持ち込む」の前段)。
**前回**: [[external-hypothesis-scan-round5-2026-09-17]] (第5次、採用 0 / WIP 会計訂正) / [[external-hypothesis-scan-round4-2026-09-10]] (E23 LOCK)。
**発動根拠 (2026-09-22 時点の供給ライン会計)**: 着手可能 (能動) **0 本** — 台帳 #27 family A は 2026-09-18 FAIL クローズ、#29 は [[hypothesis-catalog-2026-07-24|台帳]] **未登録** (`grep '^| 29 '` → 該当なし)。時限ロック 3 (E1 10-15 / ECG 11-06 / E12 2027-02-05) / 条件付き 2 / park 2 (E23 #25 UNDERPOWERED、family B) は不変。第5次 §2 の訂正教訓 (数え落とし = phantom blocker の逆) を踏まえ、本稿は **#27 が閉じたことを一次資料 (台帳 L76) で確認したうえで**発動している。
**rule:R3** (記述級の同定のみ、モデル重みのダウンロード・推論・census 実行は一切行っていない)。

**live への影響: ゼロ。** live/shadow/tier/lot/Kelly を一切変更しない。**価格・介入ラベル・outcome には一切触れていない** (本稿に登場する数値は文書数・ライセンス・訓練年範囲・N の件数のみ)。凍結 look (E1 / ECG / E12 / wg G1・G2 / E23 OOS) の outcome 計算はゼロ。

**本スキャンの成果 (先出し)**:
1. **(a)〜(d) を無条件に満たす dense stance モデルは 0 本。条件付き候補 2 本** — (i) `gtfintechlab/model_WCB_stance_label` (25 中銀 pooled、dense、4 中銀被覆、凍結可) は **ライセンス表記が不整合** (model card metadata `cc-by-4.0` vs 論文・GitHub LICENSE・全データセット `CC BY-NC-SA 4.0`) で、著者の書面確認か user 決裁 D12 なしに live 転送資格を認めない / (ii) Apel–Blix Grimaldi–Hull (2019) FOMC 辞書は license-free・重複なし・凍結可だが **密度未測定** (ABG 2012 と同じ辞書族で疎性 prior は低くない)。
2. E23 pre-reg §0-4 の「WCB_380k = CC BY-NC-SA」は **正しい** (全 WCB データセットと per-CB 4 モデルは NC-SA を HF API で確認)。不整合は pooled モデル 1 件の metadata のみ。
3. **LLM zero-shot / frozen-LLM 表現採点は (c) 知識カットオフ汚染で恒久除外** → text モダリティの C5 規律として KB 新設を提案 (執行は第6次 or 別 PR、§7)。
4. **#29 S1 は「候補なしクローズ」ではない。** step 1 (census、価格非接触) の着手条件 = ABGH-2019 辞書の逐語転記 + sha256 pin + **E23 P1 監査 (Fed discovery manifest 修正、registry `review-backlog-253-257-digest` 期日 10-03) の後**にコーパスを確定すること。

---

## 0. 規律境界 (最重要)

1. 本稿は **step 0 = 候補同定** のみ。memo §4.1-8 の census (「連続声明ペアの |ΔStance| が雑音帯を超える割合」) は**実行していない**。
2. **ABG 辞書での census は走らせない** (final assessment §3 Rank 8 (iii) の指示、根拠 = E23 pass-1 の再演にしかならない: NH=0 が 279/327 = 85.3%、[[e23-cb-text-explore-prereg-2026-09-10|E23 pre-reg]] §11.2)。
3. 本稿は **explore LOCK を起案しない・承認しない**。explore 枠の現在値 (台帳上 0/3〜2/3 で不定、ground_G3 §4.4) の確定も本稿の範囲外。
4. 「CB テキストは falsified」型の記述は本稿に無い。E23 で否定されたのは **測定可能性** (凍結 ABG 辞書 × 政策声明で検定可能イベントが 56 件しか作れない) であり、方向情報の不在ではない (pre-reg §11.3 power caveat)。
5. #29 は F1 (falsification 集計) の分子・分母に入らない (memo §3 Rank 5、REG 凍結)。time-to-M2 レバーとしては memo Rank 5 で refuted 済み — 本稿はその評価を**変えない** (§5 末尾)。

## 1. 前提の再確認 (KB 原本、2026-09-22 実読)

| 事項 | 原本 | 本稿への拘束 |
|---|---|---|
| E23 park の死因 | pre-reg §11.1–11.2: Gate B **N=56 < 100** (boe 22 / fed 15 / boj 14 / ecb 5)、void 267 件は全件 `delta_nh_zero`、**NH=0 文書 279/327**。形容詞語幹は 7.27 回/文書出るが ABG 名詞が隣接しない (声明の語法 ≠ Riksbank 議事録の語法) | 「dense」の要件 = 文書レベルで ΔStance ≠ 0 が大半で成立すること。**辞書族は同じ疎性を持ちうる** (ABGH-2019 の prior を下げる根拠) |
| 復活経路 | pre-reg §6: 「新特徴量系 (公刊凍結モデル as-is 推論等) + 新 family + 事前差分節 + 新敵対的検証のみ」。UNDERPOWERED 分岐の救済 (窓拡張・CB 追加・語彙拡張・文書種追加) は恒久禁止 | #29 は **新特徴量系 × 新 family**。E23 の窓・CB・文書種を継承するかは新 pre-reg の事前差分節で宣言 (本稿は宣言しない) |
| ライセンス条項 | pre-reg §0-4: TDW (CC BY-NC) / WCB_380k (CC BY-NC-SA) は **研究利用可・記述 secondary・live 転送資格は PASS でも発生しない**。09-04 に「primary 単独では user 決裁不要」確認 (幻ブロッカー 1 例目) | 本稿の (a) 判定はこの条項の**具体化**。NC 素材で census を走らせること自体は禁止されていない (secondary 扱い) |
| memo Rank 5 | 核 refuted (N_required 160 vs Wilson 41、7 CB 上限 4.58 event/月、keeper 控除後 +0.49%→−0.03%、L1 は制約 4.2 違反、P(PASS) 根拠なし、**TDW 学習標本が explore 窓と重複**、CC BY-NC は live 不可)。採用 = **S1 census のみ** (license-free 凍結 lexicon primary / TDW・WCB 記述 secondary / C1–C6 臨時スキャン記録 / LLM zero-shot 恒久禁止を C5 に) | 本稿 = その「C1–C6 臨時スキャン記録」の step 0 |
| under-specification | ground_G3 §4.4 / §5-3: memo §4.1-8 の「license-free 凍結 lexicon」は in-repo では ABG のみ = 疎性そのもの → **dense モデルの同定を step 0 に置かないと census が退化** | 本稿の存在理由 |
| コーパス | [[e23-pass0-census-2026-09-15|pass-0 census]]: 398 文書 (fed 85 / ecb 83 / boe 66 / boj 93 が explore 窓、本文取得 327)、`data/external/cb_statements/` + sha256 manifest。⚠️ PR #257 P1: Fed discovery が FOMC statement 以外 (実装通知・FIMA repo 告知・長期戦略更新) を混入 → manifest 修正で **398 の数字が動く** | step 1 census は **P1 監査後のコーパス**で走らせる (ground_G3 §4.3「4.4 より先に消化する順序が正しい」) |

## 2. 同定基準と検証方法

| 基準 | 内容 | 本稿での検証手段 (全て 2026-09-22 実測) |
|---|---|---|
| **(a) ライセンス** | live 転送 (実弾売買システム内での推論) を許す: Apache-2.0 / MIT / CC BY / パブリックドメイン / 公刊論文本文の語彙転記。**CC BY-NC・NC-SA は不可** (研究利用は E23 §0-4 で可、記述 secondary) | HF API (`/api/models/…`, `/api/datasets/…` の `cardData.license` と `gated`)、GitHub `repos/…/license` + LICENSE 本文、論文本文の license 節 |
| **(b) 訓練標本の重複** | explore 窓 **2014-01-01〜2023-12-31** の Fed/ECB/BOE/BoJ 声明と重複しない、**または重複 (年範囲・文書種) を宣言できる**。ラベルが市場データ由来なら outcome 汚染で不可 | 論文・model card・README の年範囲・文書種・アノテーション手順 |
| **(c) 知識カットオフ汚染** | LLM (API / open-weight) の zero/few-shot 採点、frozen-LLM 表現からの回帰は、事前学習コーパスが当該声明**とその後の市況解説**を含むため**恒久除外**。小型 encoder (RoBERTa-base/large 等) の fine-tune は事前学習テキスト (≤2019) との重複を「低・宣言」で扱う (生成的想起が構造的に無い) | モデル種別・事前学習コーパスの公開情報 |
| **(d) 凍結可能性** | 重み or 辞書の sha256 を pre-reg LOCK commit で pin できる (HF は revision sha で固定可、辞書は転記モジュールの sha256) | HF API `sha` (revision)、ファイル一覧 (`model.safetensors` 等) |
| **dense** | 文書 (声明) レベルで stance が非退化に分布する (E23 の失敗定義の否定形)。**辞書は census (step 1) まで不明**、文分類器は構造的に dense (全文に label が付く) | 出力粒度 (sentence / document、クラス数、確率出力の有無) |
| **被覆** | Fed / ECB / BOE / BoJ の 4 中銀 (E23 §2 と同じパネル) の英語声明に適用可 | 訓練中銀・言語 |

## 3. 候補表 (2026-09-22 実測。⚠️ = 不整合または未確認)

| # | 候補 | 種別 / 出力粒度 | (a) ライセンス | (b) 訓練標本と重複 | (c) 汚染 | (d) 凍結 | 被覆 | dense | **可否** |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **Apel–Blix Grimaldi (2012)** Riksbank WP 261 辞書 — in-repo `tools/e23_lexicon_apel_grimaldi.py` (sha256 `f49586ca…`) | 辞書 / 文書 NH スコア | ✅ 公刊 WP の Appendix 語彙転記 | ✅ Riksbank 議事録、2012 公刊 = 全窓先行 | — | ✅ pin 済 | 4 CB (英語) | ❌ **NH=0 279/327 (85.3%)** | **不可 (疎性)** — 比較基準行。census 再演禁止 |
| 1 | **gtfintechlab/model_WCB_stance_label** (Shah et al. 2025, NeurIPS; WCB pooled 25 中銀) | RoBERTa-base fine-tune / **文** 4 クラス (neutral / hawkish / dovish / irrelevant) | ⚠️ **不整合**: HF model card metadata `cc-by-4.0` (API 実測、revision `2a8d527f`、2025-08-25) vs 論文 abstract「artifacts … under the **CC-BY-NC-SA 4.0**」/ GitHub `WorldCentralBanks` LICENSE 本文 = CC BY-NC-SA 4.0 / 訓練データ `gtfintechlab/WCB` `WCB_380k_sentences` `all_annotated_sentences_25000` 全て `cc-by-nc-sa-4.0`。**gated: manual** (利用条件への同意 + 手動承認、条件文言は未取得) | ⚠️ 議事要旨 (minutes or closest equivalent) **1996–2024**、25 中銀、25k 注釈文 (1k/中銀を全期間から一様抽出)。**explore 窓と重複、かつ 2024 (E23 OOS 窓) も含む**。ラベルは中銀別ガイドラインによる人手二重注釈 — 市場データ不使用 (論文 Appendix H)。声明本文そのものは訓練文書種ではない | 低 (roberta-base、事前学習 ≤2019 テキスト重複は宣言) | ✅ `model.safetensors`、revision sha で固定可 (**未ダウンロード**) | Fed/ECB/BOE/BoJ 全て訓練中銀に含む | ✅ 文分類 = 構造的に dense | **条件付き** — (a) 解消 (著者の書面確認で cc-by-4.0 が意図的、or D12 (ii) license-free 再実装) まで **記述 secondary**。primary 昇格は不可 |
| 2 | gtfintechlab per-CB stance モデル: `model_federal_reserve_system_stance_label` (rev `7695c0ae`) / `model_european_central_bank_stance_label` (`2e8101d4`) / `model_bank_of_japan_stance_label` (`7f07f830`) / `model_bank_of_england_stance_label` (`ac49581d`) | 同上 / 文 4 クラス | ❌ 全 4 件 `cc-by-nc-sa-4.0` (API 実測)。ECB/BoJ/BOE は gated manual、Fed は非 gated | ⚠️ 各中銀 1k 注釈文 (1996–2024) — 同上 | 低 | ✅ | 各 1 CB | ✅ | **不可 (a)** — 記述 secondary のみ |
| 3 | **gtfintechlab/FOMC-RoBERTa** (Trillion Dollar Words、Shah–Paturi–Chava ACL 2023) | RoBERTa-large / 文 3 クラス (dovish / hawkish / neutral) | ❌ `cc-by-nc-4.0` (API 実測、rev `aa3bc428`、2023-09-12)、gated manual | ⚠️ FOMC speeches・minutes・press conference transcripts **1996–2022**、2,480 注釈文 (train 1,984 / test 496) — explore 窓と重複 (memo Rank 5 が指摘済) | 低 | ✅ | Fed のみ | ✅ | **不可 (a)** — E23 §0-4 既定どおり secondary |
| 4 | **Apel, Blix Grimaldi & Hull (2019)** Riksbank WP 381 / JMCB 2022 — FOMC minutes・transcripts から構築した hawk/dove 辞書 (term × modifier、隣接に限らない窓照合、net hawkishness = 1 + (hawk−dove)/(hawk+dove)) | 辞書 / 文書スコア | ✅ 公刊 WP の Appendix に全辞書掲載 (「The full dictionary is presented in the Appendix」) — ABG 2012 と同じ地位 | ✅ **標本 1993–2012** (WP 本文「Our sample period is 1993–2012」) = explore 窓に全面先行 | — | ✅ 転記モジュール + sha256 で pin 可 (**未転記**) | Fed 語彙 (英語)。ABG 2012 (Riksbank 語彙) を 4 CB に当てた前例と同型 | **未測定** — 辞書族。政策声明の語法に近い FOMC 由来 + 非隣接照合で ABG より密の可能性はあるが、prior は低め | **条件付き (license-free primary の唯一候補)** — step 1 census で密度を測るまで採否不能 |
| 5 | **Gardner, Scotti & Vega** (FEDS 2021-074 / J. Econometrics 2022) FOMC sentiment 辞書 (topic-keywords Table A5 + modifiers Tables A6/A7) | 辞書 / 文書 5 トピック (labor / output / inflation / financial / future policy) 合成 | ✅ 米連邦政府職員著作 (FEDS) + 論文 Appendix に語彙掲載。index 本体は「available upon request」 | ⚠️ 語彙選定 = FOMC **statements 2000-01〜2020-12** の高頻度語 (ラベルなし、頻度選定のみ) → explore 窓 2014–2020 と**重複 (宣言可、outcome 不使用)** | — | ✅ 転記可 | Fed のみ (声明語彙) | 声明由来なので密の公算 | **不可 (primary)** — 出力は **景況 sentiment であり hawk/dove stance ではない** (future-policy トピックのみ stance 隣接)。stance への写像は in-house DoF = C5 違反。記述 secondary 可 |
| 6 | **CentralBankRoBERTa** (Pfeifer & Marohl 2023, JFDS; HF `Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier`) | RoBERTa / 文 binary sentiment (positive/negative) + 経済主体 5 クラス | ✅ **MIT** (HF card) | ⚠️ Fed/ECB/BIS **speeches** 19,381 本、注釈 6,683 文 (sentiment) — 年範囲は README 未記載 | 低 | ✅ | Fed/ECB (+BIS) | ✅ | **不可 (出力)** — **hawkish/dovish を出力しない**。sentiment→stance 写像は in-house DoF |
| 7 | **BIS CB-LMs** (Gambacorta et al., BIS WP 1215, 2024-10) | encoder-only MLM (BERT/RoBERTa を中銀スピーチ・政策文書・研究論文で再学習)、**stance ヘッド無し** | ❌ **ライセンス明示なし** (BIS 頁は 1.2 GB DL リンクのみ) | ⚠️ 事前学習コーパスに窓内の中銀文書を含む (年範囲未記載) | 中 (ドメイン再学習、生成なし) | ✅ | 多 CB | — (as-is では stance を出さない) | **不可** — as-is 推論不能。stance を得るには in-house fine-tune (= DoF) が必要で、論文自身の stance 評価は TDW (NC) データで fine-tune |
| 8 | **Loughran–McDonald** Master Dictionary (Notre Dame SRAF) | 辞書 / 7 カテゴリ (negative / positive / uncertainty / litigious / strong & weak modal / constraining) | ❌ 学術無償・**商用は別途ライセンス** (SRAF 頁「for commercial licenses, please contact…」) | ✅ 10-K 由来 | — | ✅ | 汎用 | 密 | **不可 (a・出力)** — hawk/dove カテゴリ無し |
| 9 | **Picault & Renault (2017, JIMF)** ECB field-specific 加重 n-gram 辞書 (stance dovish/neutral/hawkish + 景況) | 辞書 / 文書確率 | ⚠️ **未確認** — cbcomindex.com は TLS 証明書不一致で到達不能、HAL は 403、ScienceDirect 有料 (2026-09-22) | ⚠️ ECB 記者会見 (introductory statements) 由来、年範囲は abstract に無し | — | 転記可 (入手できれば) | **ECB のみ** | 声明系由来で密の可能性 | **保留 (C1 未確認)** — 単独では 4 CB パネルに不足。第6次で再訪 |
| 10 | **Tobback, Nardelli & Martens (2017)** ECB HD indicator (ECB WP 2085) | SVM / 記者会見ごとの指標 | ❌ モデル・データ非公開 | 入力は **メディア報道 9,000 本** (中銀テキストではない) | — | ❌ | ECB | — | **不可 (C1)** |
| 11 | **IMF WP 2025/109** (Silva–Moriya–Veyrune) fine-tuned LLM 分類器、74,882 文書 169 中銀 1884–2025 | LLM 分類 / 文 4 次元 | ❌ 複製データ・モデル非公開 ([[e23-cb-text-adjudication-s2-2026-08-18|E23 裁定 doc]] §2 の判定を再確認、変化なし) | — | ❌ LLM 系 | ❌ | 多 CB | — | **不可 (C1・c)** |
| 12 | **LLM zero/few-shot 採点** (GPT-4o / Claude / Llama-3 / Qwen 等) および frozen-LLM 表現回帰 (例: "Mind the Shift" arXiv 2603.14313、2026-03、Delta-Consistent Scoring) | 生成 LLM / 任意 | (open-weight は Apache/community 等で (a) を満たしうる) | — | ❌ **知識カットオフ汚染** (事前学習が窓内声明とその後の市況解説を含む) | 重みは凍結可だが無意味 | 多 CB | ✅ | **恒久除外 (c)** — C5 規律新設案 (§7) |
| 13 | **FinBERT-tone** (`yiyanghkust/finbert-tone`) / ProsusAI FinBERT | BERT / 文 3 クラス tone (positive / negative / neutral) | ⚠️ HF card にライセンス記載なし | アナリストレポート 10k 注釈文 (企業金融ドメイン) | 低 | ✅ | 汎用 | ✅ | **不可 (出力・ドメイン)** — tone ≠ stance |

**行 1 のライセンス不整合の読み方 (保守側で固定)**: pooled モデルは NC-SA データセット (`gtfintechlab/WCB`) の派生物で、論文・README・LICENSE ファイルの 3 箇所が NC-SA を宣言している。model card の `cc-by-4.0` は 1 箇所の metadata に留まり、意図的な再ライセンスの記述 (論文正誤表・README 追記) が見当たらない。**したがって本稿は NC-SA が支配すると読み、live 転送資格を認めない。** 逆方向 (cc-by-4.0 が意図的) の可能性は残るので、確認経路 = 著者 (gtfintechlab) への書面照会 → 回答を KB に転記。**照会の実行は user 決裁 D12 の一部として扱う** (研究利用は §0-4 で既に可、急がない — memo §4.1 D12「#29 S1 の結果が出るまで急がない」)。

## 4. 候補別の所見 (step 1 設計への入力、価格非接触)

### 4.1 `model_WCB_stance_label` (dense、条件付き secondary)
- **強み**: 4 中銀すべてが訓練中銀 / 文レベル 4 クラス (irrelevant を含む = 声明の定型文を自動で落とせる) / revision sha `2a8d527f70ea7c58976eb01a3570a91512164570` で凍結可 / 論文 (NeurIPS 2025) で pooled モデルが per-CB モデルを上回ると報告 (「the whole is greater than the sum of its parts」)。
- **弱み**: (a) 不整合 / gated manual (条件同意 + 承認待ち、条件文言未取得 — 追加制約の可能性) / 訓練文書種 = 議事要旨 (声明ではない) → domain shift は宣言事項 / 訓練年 1996–2024 は E23 OOS 窓 (2024-01〜) と**テキスト重複** — ラベルは人手ガイドライン (市場データ不使用) なので outcome 汚染ではないが、新 pre-reg の事前差分節で「2024 テキストを訓練に含むモデル」と明記する。
- **step 1 での扱い**: 記述 secondary。文→文書の集約規則は **1 本に凍結** (推奨: E23 と同形 NH = (#hawk − #dove)/(#hawk + #dove + 1)、irrelevant/neutral は分母に入れない) — 集約規則の複数試行は C5 違反。

### 4.2 Apel–Blix Grimaldi–Hull (2019) 辞書 (license-free primary の唯一候補、密度未測定)
- **強み**: 標本 1993–2012 = 全窓先行 (ABG 2012 と同じ「探索自由度ゼロ」の性質) / FOMC 語彙 (Riksbank 議事録より政策声明の語法に近い) / term–modifier を**隣接に限らず**照合 (E23 §11.2 の死因 = 「形容詞は出るが名詞が隣接しない」への直接の反例設計) / 公刊 Appendix で全辞書が転記可。
- **弱み**: 辞書族の疎性 prior (ABG 2012 が 85.3% NH=0) / Fed 由来語彙を ECB/BOE/BoJ 英語版に当てる = out-of-vocabulary の可能性 / 語数・照合窓幅は WP 本文の再読で確定が必要 (本稿では未転記)。
- **step 1 での扱い**: primary 候補として **逐語転記 → sha256 pin → 398 (P1 監査後) 文書に as-is 適用 → NH≠0 文書割合と |ΔNH| 分布 (価格非接触)** を数える。**ここで NH≠0 が E23 並み (≈15%) なら #29 S1 は「license-free dense primary 不在」で候補なしクローズ** (secondary だけでは pre-reg の primary が立たない)。

### 4.3 その他
- Gardner–Scotti–Vega (行 5) は Fed 限定の記述 secondary として census に併載可 (景況 sentiment、stance ではないことを列名で明示)。
- CentralBankRoBERTa (行 6) は MIT だが stance を出さない — 「MIT だから使える」型の誤用を防ぐため本表に残す。
- Picault–Renault (行 9) は第6次 (10-18) で cbcomindex.com / 著者版 PDF の再取得を試み、入手できれば ECB 単独 secondary として追記。

## 5. C1–C6 裁定 (単独候補 = **#29 S1「公刊凍結 stance モデル as-is 推論 × G4 中銀声明 × 声明間ドリフト」の S1 intake**)

round-2/3/4/5 と同一 hard constraints。**本表は family 採用の裁定ではなく、S1 (記述級) 継続可否の裁定**である。

| 制約 | 判定 | 根拠 |
|---|---|---|
| **C1 データ入手性** | **△ 条件付き** | コーパス: in-repo 398 文書 + sha256 manifest (再取得不要、ただし P1 監査で manifest 変更予定)。モデル: primary 候補 (ABGH-2019) は公刊 Appendix で $0・即時 / dense 候補 (WCB pooled) は gated manual + ライセンス不整合。**無条件に入手可能な dense 候補は 0** |
| **C2 falsified 除外** | **✅ 適法** | E23 #25 は **UNDERPOWERED / park であり FAIL ではない** → pre-reg §6 の FAIL クローズ範囲は**未発効**。E7 (NFP/CPI headline z × sign-follow × M15) / E15 (無条件イベント窓) の ban は E23 §8 と同じ 3 要素差分で外。復活経路 (§6「新特徴量系 + 新 family + 事前差分節 + 新敵対的検証」) の字義に一致。⚠️ pre-reg 起草時は E23 との**事前差分節** (窓・CB・文書種・ペア写像の継承有無、E23 pass-1 Gate A の P1 欠陥 = 全期間 median による OOS 窓の無条件リターン接触を宣言) が必須 |
| **C3 非重複** | **✅** | E1 (positioning) / E12 (volume) / ECG #22 (equity curve) / #27 family A (label-facing、FAIL クローズ) とモダリティ・endpoint が直交。同じ text モダリティの E23 とは特徴量系が別 (辞書隣接 bigram vs 文分類器 / 非隣接辞書)。per-pair 1 position での USD_JPY スロット競合 (memo §2.1) は**執行側の論点**で S1 には無関係 |
| **C4 摩擦生存** | **⏸ 未評価 (本稿の設計上、評価不能)** | 価格非接触。E23 pass-1 Gate A「3/3 ペア通過」は PR #257 P1 (全期間 median) の監査待ちで**引用は監査付き**。memo §3 Rank 5: USD_JPY レグの swap を E23 Gate D bound (1.5p/5bd) で継承すると 3–5 倍過小評価 → 新 pre-reg の Gate D は bound を改定して凍結 (数値は本稿で決めない) |
| **C5 反 curve-fit** | **✅ 条件付き** | 特徴量 = 公刊凍結モデル as-is (sha256 pin)、集約規則 1 本凍結、辞書語彙の編集禁止 (E23 §0-3 継承)。**LLM zero/few-shot・frozen-LLM 表現採点は恒久除外 (行 12)**。step 1 census の出力は密度指標のみで閾値探索を含まない |
| **C6 revealed edge** | **△** | プロジェクト内の revealed はゼロ。文献 (Shah et al. 2023 の市場分析、Picault–Renault 2017 の Taylor rule / ボラ説明力) は**公表済み**で McLean–Pontiff 型の公表後減衰 prior に乗る (第5次 §3.1)。E23 §1 の負 prior (E15+E7 二重 FAIL 家系、explore→OOS 生存 0/18 系統) は不変 |

**裁定**: **S1 継続 (step 1 census 着手可、条件付き)。family 採用・explore LOCK は起案しない。** 無条件候補 0 / 条件付き 2 という結果は「候補なしクローズ」でも「採用」でもなく、**クローズ条件を step 1 に委ねる**: ABGH-2019 の密度が E23 並みなら #29 S1 は候補なしクローズ (secondary だけでは primary が立たない)。time-to-M2 への寄与評価は memo Rank 5 (refuted、+0.4〜1.6pp) から**動かない** — 本稿は供給ライン (WIP) の充足手段としてのみ意味を持つ。

## 6. 供給ライン会計 (WIP、2026-09-22 本稿後)

| 分類 | 本数 | 内訳 |
|---|---|---|
| **着手可能 (能動)** | **1 (S1 記述級、family 未採用)** | **#29 S1 step 1 census** — 前提 = ABGH-2019 転記 + sha256 pin + **E23 P1 監査 (10-03) 後のコーパス確定**。価格非接触・$0。⚠️ **台帳 #29 は未登録のまま** (登録は第6次 or 新 pre-reg 起案時の裁定) — 「着手可能 1」は S1 intake の作業単位であって採用 family ではない |
| 時限ロック (受動) | 3 | E1 first look 2026-10-15 / ECG #22 2026-11-06 / E12 2027-02-05 |
| 条件付き (受動) | 2 | #4 MoF 次エピソード再判定 (~11-14) / `ws3-round4-eur-divergence-conditional` (cache 11-15) |
| park | 2 | E23 #25 (UNDERPOWERED — 09-19 追記の P1×3 は「park 根拠の estimand 監査」として 10-03 消化予定) / family B |
| FAIL クローズ (直近) | 1 | #27 family A statement_ladder (09-18 — 凍結 α 規則未達のみを意味し、検出力 caveat 付きでしか引用しない。数値は本稿では転記しない) |

**規律確認**: 本節は手続き状態のみ。発言×介入・声明×価格のジョイント量は一切計算していない。「供給ライン全滅」型の表現は使わない (第5次 §2 教訓)。

## 7. 次アクションと registry 更新案 (執行は本 PR 外)

1. **[10-03 まで / R3 / 別 PR]** E23 P1×3 消化 (`review-backlog-253-257-digest`) — Fed discovery を FOMC statement 限定に修正し manifest を更新。**#29 step 1 はこの後のコーパスで走らせる** (順序固定)。
2. **[E23 P1 後 / R3 / 別 PR、価格非接触]** #29 S1 step 1 census: ABGH-2019 辞書の逐語転記 (`tools/` 新モジュール、WP 381 Appendix 出典明示、sha256 pin、test で語彙編集を封鎖) → 398→修正後コーパスに as-is 適用 → NH≠0 文書割合 / |ΔNH| 分布 / CB 別 (件数のみ)。secondary 併載 = WCB pooled (研究利用、§0-4)、Gardner–Scotti–Vega (Fed 景況 sentiment、stance 非該当を明示)。**閾値・ホライズン・ペア写像の探索は禁止** (それは pre-reg の領分)。クローズ条件を census 実行前に本節の文言で固定: 「ABGH-2019 の NH≠0 割合が E23 (50/327 = 15.3%) の 2 倍未満なら license-free dense primary 不在 → #29 S1 候補なしクローズ」。
3. **[第6次 10-18 / R3]** 本稿 + step 1 結果を持ち込み、(i) #29 の台帳登録可否、(ii) explore 枠の現在値確定 (0/3〜2/3)、(iii) Picault–Renault 再取得、(iv) 下記 C5 規律の KB 反映、を裁定。
4. **[user 決裁 D12 (統合パケット、返答期限 11-30)]** WCB pooled のライセンス不整合の**照会可否**を D12 に同梱 — 選択肢 = (i) 著者照会 (書面回答を KB 転記、cc-by-4.0 確認なら primary 昇格を新 pre-reg で審査) / (ii) license-free 再実装 (NC-SA データで学習しない設計 — 実質 ABGH-2019 路線) / (iii) 研究 secondary のまま。**急がない** (memo §4.1 D12)。
5. **C5 規律新設案 (text モダリティ)**: 「LLM (API / open-weight) の zero/few-shot 採点、および frozen-LLM 表現からの stance 回帰は、事前学習コーパスが観測窓内の中銀文書とその後の市況解説を含む (知識カットオフ汚染) ため、explore/OOS の特徴量として**恒久禁止**。許容 = 観測窓に先行して公刊・凍結された辞書、または訓練標本の年範囲・文書種・注釈手順を宣言できる小型 encoder 分類器の as-is 推論のみ。」— 反映先 = [[edge-development-pipeline-2026-07-18|パイプライン]] §3 (C5 の text 項) と [[e23-cb-text-explore-prereg-2026-09-10|E23 pre-reg]] 相互参照。**本 PR では執行しない** (hot file 回避 + 規律追加は第6次で一括)。

**registry 更新案 (S7 が編集)**:
- `edge-supply-scan-monthly` (deadline **2026-10-18 は据え置き**): message に「**臨時スキャン 2026-09-22 実行済 (#29 S1 step 0、[[adhoc-scan-29-step0-2026-09-22]])**: 無条件候補 0 / 条件付き 2 (WCB pooled = ライセンス不整合で secondary、ABGH-2019 辞書 = license-free primary 候補・密度未測定)。WIP 会計: 着手可能 1 (S1 step 1 census、E23 P1 監査 10-03 後に着手)。第6次で #29 台帳登録可否・explore 枠現在値・C5 text 規律を裁定」を追記。
- `review-backlog-253-257-digest` (10-03): message に「#257 分の Fed discovery 修正は **#29 S1 step 1 census の前提** — 消化順序を先に」を追記。
- 新規 (任意、`deadline_info`): `adhoc-scan-29-step1-census-gate` deadline 2026-10-17 (第6次前日) — 「E23 P1 監査後に ABGH-2019 census を実行し、NH≠0 割合が 15.3%×2 未満なら #29 S1 候補なしクローズを第6次に持ち込む」。

## 8. 正直な caveat

- (a) 判定は **2026-09-22 時点の公開 metadata** に基づく。HF の license タグは作者が随時変更できるため、pre-reg LOCK 時に revision sha と当該時点の card 本文を KB に転記して再確認する。
- WCB pooled の gated 条件文言は未取得 (同意画面はログインが必要)。条件に「非商用」等の追加制約があれば (a) は確定的に不可。
- ABGH-2019 の語数・照合窓幅・極性反転規則は WP 381 本文の精読で確定が必要 (本稿は pypdf 抽出テキストの部分照合のみ: 「dictionary constructed using the FOMC's minutes and transcripts」「full dictionary is presented in the Appendix」「sample period is 1993–2012」の 3 点を確認)。
- Picault–Renault (行 9) は到達不能につき **未評価** — 「不可」ではない。
- 本稿の候補表は網羅ではない (検索 2026-09-22、英語文献のみ)。第6次で追補可。

## 出所索引 (再利用時はこの行を併記)

| 事実 | 出所 |
|---|---|
| WCB pooled model license `cc-by-4.0` / gated manual / rev `2a8d527f…` / 2025-08-25 | `https://huggingface.co/api/models/gtfintechlab/model_WCB_stance_label` (2026-09-22 curl) |
| per-CB 4 モデル `cc-by-nc-sa-4.0` (fed `7695c0ae…` 非 gated / ecb `2e8101d4…` / boj `7f07f830…` / boe `ac49581d…` gated manual) | 同 API、`model_{federal_reserve_system,european_central_bank,bank_of_japan,bank_of_england}_stance_label` |
| WCB データセット 3 件 `cc-by-nc-sa-4.0` (`WCB_380k_sentences` 2025-10-20 / `all_annotated_sentences_25000` / `federal_reserve_system` ほか per-CB) | `https://huggingface.co/api/datasets/gtfintechlab/…` |
| WCB 論文: 1996–2024 / 25 中銀 / 380,200 文 / 25k 注釈 / 「artifacts … under the CC-BY-NC-SA 4.0 license」/ 人手二重注釈 (Appendix H) | arXiv 2505.17048 (HTML) + GitHub `gtfintechlab/WorldCentralBanks` README L32, L64, L73, L526–528 + LICENSE (CC BY-NC-SA 4.0 本文、`gh api repos/…/license` → NOASSERTION/Other) |
| FOMC-RoBERTa `cc-by-nc-4.0` / rev `aa3bc428…` / 2023-09-12; dataset `fomc_communication` 1996–2022、2,480 文 | HF API + model/dataset card (2026-09-22) |
| ABGH-2019: FOMC minutes・transcripts 由来辞書 / Appendix 全掲 / 標本 1993–2012 / net hawkishness 式 | Riksbank WP 381 PDF (pypdf 抽出、`scratchpad/rb381.txt`) |
| Gardner–Scotti–Vega: FOMC statements 2000-01〜2020-12 高頻度語 / Table A5–A7 / 5 トピック / 「available upon request」 | FEDS 2021-074 PDF (pypdf 抽出、`scratchpad/feds2021074.txt`) |
| CentralBankRoBERTa MIT / speeches 19,381 / 注釈 6,205 (agent) + 6,683 (sentiment) / stance 非出力 | HF `Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier` card + GitHub README (2026-09-22) |
| BIS CB-LMs: 重み 1.2 GB 公開、ライセンス記載なし、encoder-only、stance 評価は fine-tune | `https://www.bis.org/publ/work1215.{htm,pdf}` (2024-10-01) |
| Loughran–McDonald: 学術無償・商用別ライセンス・hawk/dove カテゴリ無し | `https://sraf.nd.edu/loughranmcdonald-master-dictionary/` |
| Picault–Renault 到達不能 (TLS 不一致 / HAL 403) | `cbcomindex.com`, `hal.science/hal-03205121` (2026-09-22) |
| E23 park 数値 (N=56、NH=0 279/327、matched 50/327)、§0-4 条項、§6 復活経路 | [[e23-cb-text-explore-prereg-2026-09-10]] §0-4, §6, §10.2, §11.1–11.4 |
| コーパス 398 / explore 331 (本文 327) / per-CB 85・83・66・93 | [[e23-pass0-census-2026-09-15]] |
| memo Rank 5 / §4.1-8 / D12 | [[path-to-win-decision-memo-2026-09-20]] L93, L117, L140 |
| WIP 規則「今日着手できる本数 ≥1」 | [[edge-development-pipeline-2026-07-18]] L73 |
| #27 FAIL クローズ / #29 未登録 | [[hypothesis-catalog-2026-07-24]] L76 / `grep '^| 29 '` 該当なし |

## 関連

- [[external-hypothesis-scan-round5-2026-09-17]] (前回、WIP 会計訂正)
- [[e23-cb-text-explore-prereg-2026-09-10]] (park 根拠、§0-4 ライセンス条項、§6 復活経路)
- [[e23-cb-text-adjudication-s2-2026-08-18]] (S2 データ実在 probe — TDW/IMF の初回裁定)
- [[path-to-win-decision-memo-2026-09-20]] (Rank 5 / §4.1-8 / D12)
- [[hypothesis-catalog-2026-07-24]] (台帳、#29 未登録)
- [[edge-development-pipeline-2026-07-18]] (WIP 原則、C1–C6)
