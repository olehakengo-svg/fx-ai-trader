# 臨時外部仮説スキャン — #29 S1 census step 0: license-free × dense × 凍結可能な中銀声明 stance モデルの候補同定 (2026-09-22)

**位置づけ**: [[edge-development-pipeline-2026-07-18|edge パイプライン]] §5 追補 (2026-08-14 user 承認) の WIP 規則「今日着手できる本数が 0 なら期日を待たず**臨時スキャン (R3)**」の発動。registry `edge-supply-scan-monthly` (第6次 = 2026-10-18) の期日は消費しない (月次 cadence とは別建ての臨時記録、[[path-to-win-decision-memo-2026-09-20|決裁メモ v2]] §4.1-8 / §4.1-17 の「S1 census 結果を第6次に持ち込む」の前段)。⚠️ [[path-to-win-reassessment-2026-09-22|再評価 09-22]] §3 Rank 8 (iii) は **#29 S1 を step 0 のみ**に限定 (候補ゼロでも可) — 第6次に持ち込むのは本稿 step 0 の結論と、step 1 (census) の**実行可否の裁定案**である。
**前回**: [[external-hypothesis-scan-round5-2026-09-17]] (第5次、採用 0 / WIP 会計訂正) / [[external-hypothesis-scan-round4-2026-09-10]] (E23 LOCK)。
**発動根拠 (2026-09-22 時点の供給ライン会計)**: 着手可能 (能動) **0 本** — 台帳 #27 family A は 2026-09-18 FAIL クローズ、#29 は [[hypothesis-catalog-2026-07-24|台帳]] **未登録** (`grep '^| 29 '` → 該当なし)。時限ロック 3 (E1 10-15 / ECG 11-06 / E12 2027-02-05) / 条件付き 2 / park 2 (E23 #25 UNDERPOWERED、family B) は不変。第5次 §2 の訂正教訓 (数え落とし = phantom blocker の逆) を踏まえ、本稿は **#27 が閉じたことを一次資料 (台帳 L76) で確認したうえで**発動している。
**rule:R3** (記述級の同定のみ、モデル重みのダウンロード・推論・census 実行は一切行っていない)。

**live への影響: ゼロ。** live/shadow/tier/lot/Kelly を一切変更しない。**価格・介入ラベル・outcome には一切触れていない** (本稿に登場する数値は文書数・ライセンス・訓練年範囲・N の件数のみ)。凍結 look (E1 / ECG / E12 / wg G1・G2 / E23 OOS) の outcome 計算はゼロ。

**本スキャンの成果 (先出し)**:
1. **(a)〜(d) を無条件に満たす dense stance モデルは 0 本。条件付き候補 2 本** — (i) `gtfintechlab/model_WCB_stance_label` (25 中銀 pooled、文 4 クラス分類器、4 中銀被覆、凍結可。**文書レベル密度は未測定** — 文ごとに label が付くことは文書 NH≠0 を保証しない) は **ライセンス表記が不整合** (model card metadata `cc-by-4.0` vs 論文・GitHub LICENSE・全データセット `CC BY-NC-SA 4.0`) で、著者の書面確認か user 決裁 D12 なしに live 転送資格を認めない。加えて fine-tune 標本 1996–2024 が評価窓の全観測より後を含むため、**許諾が解消しても現行 checkpoint は記述 secondary 固定** (primary は評価窓に先行する cutoff で訓練された checkpoint のみ、基準 (b)) / (ii) Apel–Blix Grimaldi–Hull (2019) FOMC 辞書は NC 条項なし・重複なし・凍結可だが **再利用許諾未確認** (公刊 Appendix 掲載 = 入手可能性であって許諾ではない、行 0 の ABG 2012 と同型) かつ **密度未測定** (ABG 2012 と同じ辞書族で疎性 prior は低くない)。**dense と実測された候補は 0** — 密度は文書レベルの量で、step 1 census でのみ確定する。
2. E23 pre-reg §0-4 の「WCB_380k = CC BY-NC-SA」は **正しい** (全 WCB データセットと per-CB 4 モデルは NC-SA を HF API で確認)。不整合は pooled モデル 1 件の metadata のみ。
3. **LLM zero-shot / frozen-LLM 表現採点は (c) 知識カットオフ汚染で恒久除外**。encoder 分類器 (RoBERTa 系) も免責ではなく、**事前学習コーパスの終端以前の声明は汚染扱い** (RoBERTa の CC-News は 2016-09〜2019-02 を含む → explore 窓 2014〜2019-02 は汚染、清浄区間は終端後のみ) → text モダリティの C5 規律として KB 新設を提案 (執行は第6次 or 別 PR、§7)。
4. **#29 S1 の step 0 結論 = 「無条件候補 0 / 条件付き 2 (いずれも dense 未確認)」。step 1 (census、価格非接触) は本稿の提案であり、本稿は着手を承認しない** — 再評価 09-22 §3 Rank 8 (iii) が #29 S1 を **step 0 のみ**に限定しているため。step 1 の実行可否は **第6次スキャン (2026-10-18) で裁定**し、「実行」なら前提 = ABGH-2019 辞書の**再利用許諾根拠の確定** → 逐語転記 + sha256 pin + **E23 P1 監査 (Fed discovery manifest 修正、registry `review-backlog-253-257-digest` 期日 10-03) 後**のコーパス確定、の順序で走らせる (§7-2, §7-3)。クローズ条件は memo §4.1-8 の census 定義どおり**連続声明ペアの |ΔNH| 推定量** (τ = 0 凍結、スコアは各モデルの公刊/凍結式 as-is — ABGH は 1 + (h−d)/(h+d)、無ヒットのみ中立 1 代入) で、**閾値 = 適格ペアの過半 (> 50%、厳密) で |ΔNH|>0** (本稿 §1/§2 の dense 定義「大半」と一致させた絶対水準。4 巡目で「ABG-2012 比 2 倍 = 34.7%」の相対基準を撤回)。文書 NH≠0 割合はゲートに使わない。**ABG-2012 の再実行は行わない** (再評価 §3 Rank 8 (iii) / 「やらないこと」L134 の禁止を本稿は解かない — 絶対水準ゲートなのでベースライン再計算は不要、56/323 = 17.3% は記述参照値)。

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
| E23 park の死因 | pre-reg §11.1–11.2: Gate B **N=56 < 100** (boe 22 / fed 15 / boj 14 / ecb 5)、void 267 件は全件 `delta_nh_zero`、**NH=0 文書 279/327**。形容詞語幹は 7.27 回/文書出るが ABG 名詞が隣接しない (声明の語法 ≠ Riksbank 議事録の語法) | 「dense」の要件 = **連続同一 CB 声明ペアの過半 (> 50%、厳密) で ΔStance ≠ 0** が成立すること (E23 は 56/323 = 17.3%)。**辞書族は同じ疎性を持ちうる** (ABGH-2019 の prior を下げる根拠) |
| 復活経路 | pre-reg §6: 「新特徴量系 (公刊凍結モデル as-is 推論等) + 新 family + 事前差分節 + 新敵対的検証のみ」。UNDERPOWERED 分岐の救済 (窓拡張・CB 追加・語彙拡張・文書種追加) は恒久禁止 | #29 は **新特徴量系 × 新 family**。E23 の窓・CB・文書種を継承するかは新 pre-reg の事前差分節で宣言 (本稿は宣言しない) |
| ライセンス条項 | pre-reg §0-4: TDW (CC BY-NC) / WCB_380k (CC BY-NC-SA) は **研究利用可・記述 secondary・live 転送資格は PASS でも発生しない**。09-04 に「primary 単独では user 決裁不要」確認 (幻ブロッカー 1 例目) | 本稿の (a) 判定はこの条項の**具体化**。NC 素材で census を走らせること自体は禁止されていない (secondary 扱い) |
| memo Rank 5 | 核 refuted (N_required 160 vs Wilson 41、7 CB 上限 4.58 event/月、keeper 控除後 +0.49%→−0.03%、L1 は制約 4.2 違反、P(PASS) 根拠なし、**TDW 学習標本が explore 窓と重複**、CC BY-NC は live 不可)。採用 = **S1 census のみ** (license-free 凍結 lexicon primary / TDW・WCB 記述 secondary / C1–C6 臨時スキャン記録 / LLM zero-shot 恒久禁止を C5 に) | 本稿 = その「C1–C6 臨時スキャン記録」の step 0 |
| under-specification | ground_G3 §4.4 / §5-3: memo §4.1-8 の「license-free 凍結 lexicon」は in-repo では ABG のみ = 疎性そのもの → **dense モデルの同定を step 0 に置かないと census が退化** | 本稿の存在理由 |
| コーパス | [[e23-pass0-census-2026-09-15|pass-0 census]]: 398 文書 (fed 85 / ecb 83 / boe 66 / boj 93 が explore 窓、本文取得 327)、`data/external/cb_statements/` + sha256 manifest。⚠️ PR #257 P1: Fed discovery が FOMC statement 以外 (実装通知・FIMA repo 告知・長期戦略更新) を混入 → manifest 修正で **398 の数字が動く** | step 1 census は **P1 監査後のコーパス**で走らせる (ground_G3 §4.3「4.4 より先に消化する順序が正しい」) |

## 2. 同定基準と検証方法

| 基準 | 内容 | 本稿での検証手段 (全て 2026-09-22 実測) |
|---|---|---|
| **(a) ライセンス** | live 転送 (実弾売買システム内での推論) を許す: Apache-2.0 / MIT / CC BY / パブリックドメイン / 明示の再利用許諾。**CC BY-NC・NC-SA は不可** (研究利用は E23 §0-4 で可、記述 secondary)。⚠️ **公刊論文の Appendix に辞書が載っていることは入手可能性であって再利用許諾ではない** — 出版機関の利用条件 / 著者許諾 / 語彙リストの著作物性判断のいずれかで根拠を確定するまで「未確認」(レビュー P2、2 巡目で訂正: 初版はこれを license-free と読んでいた) | HF API (`/api/models/…`, `/api/datasets/…` の `cardData.license` と `gated`)、GitHub `repos/…/license` + LICENSE 本文、論文本文の license 節 |
| **(b) 訓練標本の重複** | **primary 要件 = 訓練標本 (事前学習・fine-tune とも) の終端が評価窓に先行する** (ABGH-2019 の 1993–2012 型)。explore 窓 **2014-01-01〜2023-12-31** と重複する訓練標本を持つ候補は、重複 (年範囲・文書種) を宣言できても**記述 secondary まで** — 評価対象より後の中銀語法・ラベルで訓練された分類器は outcome 非接触でも時間的リーク (6 巡目レビュー P2 で初版の「宣言で可」を撤回)。ラベルが市場データ由来なら secondary も不可 | 論文・model card・README の年範囲・文書種・アノテーション手順 |
| **(c) 知識カットオフ汚染** | LLM (API / open-weight) の zero/few-shot 採点、frozen-LLM 表現からの回帰は、事前学習コーパスが当該声明**とその後の市況解説**を含むため**恒久除外**。**小型 encoder (RoBERTa 等) の fine-tune も同じ経路で汚染しうる** — 生成的想起が無いことは、記憶や outcome 関連情報が表現に混入することを構造的に防がない (5 巡目レビュー P2で初版の「低・宣言」扱いを撤回)。要件 = **事前学習コーパスの終端を監査可能に確定し、終端以前の声明は汚染として扱う** (RoBERTa: CC-News 2016-09〜2019-02 を含む [Liu et al. 2019 §3.2] → explore 窓のうち 2014〜2019-02 の声明は汚染、清浄に使えるのは終端後の声明のみ)。終端を確定できないモデルは (c) 不可 | モデル種別・事前学習コーパスの公開情報 (論文の data 節、model card) — 「encoder-only」は免責理由にならない |
| **(d) 凍結可能性** | 重み or 辞書の sha256 を pre-reg LOCK commit で pin できる (HF は revision sha で固定可、辞書は転記モジュールの sha256) | HF API `sha` (revision)、ファイル一覧 (`model.safetensors` 等) |
| **dense** | 文書 (声明) レベルで stance が非退化に分布する (E23 の失敗定義の否定形 = **連続同一 CB ペアの過半 (> 50%、厳密) で |ΔNH|>0**。文書 NH≠0 割合は必要条件・記述指標)。**辞書も文分類器も census (step 1) まで未測定** — 文分類器は全文に label を付けるが、全文が neutral/irrelevant に落ちる、または #hawk = #dove の文書は集約後 NH=0 になり、連続文書で ΔNH=0 も起こりうる。「文レベルで label が付く」ことから文書密度を推論しない (初版の「構造的に dense」は推論で、レビュー P2 により撤回) | 出力粒度 (sentence / document、クラス数、確率出力の有無) を**密度の必要条件**としてのみ記録 — 密度そのものは測らない |
| **被覆** | Fed / ECB / BOE / BoJ の 4 中銀 (E23 §2 と同じパネル) の英語声明に適用可 | 訓練中銀・言語 |

## 3. 候補表 (2026-09-22 実測。⚠️ = 不整合または未確認)

| # | 候補 | 種別 / 出力粒度 | (a) ライセンス | (b) 訓練標本と重複 | (c) 汚染 | (d) 凍結 | 被覆 | dense | **可否** |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **Apel–Blix Grimaldi (2012)** Riksbank WP 261 辞書 — in-repo `tools/e23_lexicon_apel_grimaldi.py` (sha256 `f49586ca…`) | 辞書 / 文書 NH スコア | ⚠️ 公刊 WP の Appendix 語彙転記 = 入手可能性のみ。再利用許諾の根拠は pre-reg §0-3 にも未記録 (行 4 と同型の未確認 — E23 側の扱いは §7-2 (vi) で第6次へ) | ✅ Riksbank 議事録、2012 公刊 = 全窓先行 | — | ✅ pin 済 | 4 CB (英語) | ❌ **NH=0 279/327 (85.3%)** | **不可 (疎性)** — 比較基準行。census 再演禁止 |
| 1 | **gtfintechlab/model_WCB_stance_label** (Shah et al. 2025, NeurIPS; WCB pooled 25 中銀) | RoBERTa-base fine-tune / **文** 4 クラス (neutral / hawkish / dovish / irrelevant) | ⚠️ **不整合**: HF model card metadata `cc-by-4.0` (API 実測、revision `2a8d527f`、2025-08-25) vs 論文 abstract「artifacts … under the **CC-BY-NC-SA 4.0**」/ GitHub `WorldCentralBanks` LICENSE 本文 = CC BY-NC-SA 4.0 / 訓練データ `gtfintechlab/WCB` `WCB_380k_sentences` `all_annotated_sentences_25000` 全て `cc-by-nc-sa-4.0`。**gated: manual** (利用条件への同意 + 手動承認、条件文言は未取得) | ⚠️ 議事要旨 (minutes or closest equivalent) **1996–2024**、25 中銀、25k 注釈文 (1k/中銀を全期間から一様抽出)。**explore 窓と重複、かつ 2024 (E23 OOS 窓) も含む**。ラベルは中銀別ガイドラインによる人手二重注釈 — 市場データ不使用 (論文 Appendix H)。声明本文そのものは訓練文書種ではない。**fine-tune 終端 2024 は評価窓の全観測より後 = primary 不可の決定因 (6 巡目)** | ⚠️ **汚染 (窓前半)** — roberta-base の事前学習は CC-News 2016-09〜2019-02 を含む (Liu et al. 2019 §3.2) → explore 窓 2014〜2019-02 の声明は汚染扱い。清浄区間 = 2019-03 以降 (fine-tune 側の重複は (b) で別途) | ✅ `model.safetensors`、revision sha で固定可 (**未ダウンロード**) | Fed/ECB/BOE/BoJ 全て訓練中銀に含む | **未測定** (文 4 クラスで全文に label が付くが、文書 NH≠0 の割合は step 1 で測る) | **条件付き (記述 secondary 固定)** — (a) 解消 (著者の書面確認で cc-by-4.0 が意図的) ∧ 文書密度の実測が済んでも、**現行 checkpoint は primary 不可**: fine-tune 標本が 1996–2024 で、(c) の清浄区間 2019-03〜2023 の全観測より後の中銀語法・ラベルを含む (基準 (b) の時間的リーク)。primary 経路は (ア) fine-tune 標本の終端を評価窓に先行させた再訓練 checkpoint (監査可能な cutoff) か (イ) D12 (ii) license-free 再実装 (同じ cutoff 要件) のみ — いずれも新 pre-reg の事前差分節で宣言 |
| 2 | gtfintechlab per-CB stance モデル: `model_federal_reserve_system_stance_label` (rev `7695c0ae`) / `model_european_central_bank_stance_label` (`2e8101d4`) / `model_bank_of_japan_stance_label` (`7f07f830`) / `model_bank_of_england_stance_label` (`ac49581d`) | 同上 / 文 4 クラス | ❌ 全 4 件 `cc-by-nc-sa-4.0` (API 実測)。ECB/BoJ/BOE は gated manual、Fed は非 gated | ⚠️ 各中銀 1k 注釈文 (1996–2024) — 同上 | ⚠️ 汚染 (窓前半、行 1 と同じ) | ✅ | 各 1 CB | 未測定 | **不可 (a)** — 記述 secondary のみ |
| 3 | **gtfintechlab/FOMC-RoBERTa** (Trillion Dollar Words、Shah–Paturi–Chava ACL 2023) | RoBERTa-large / 文 3 クラス (dovish / hawkish / neutral) | ❌ `cc-by-nc-4.0` (API 実測、rev `aa3bc428`、2023-09-12)、gated manual | ⚠️ FOMC speeches・minutes・press conference transcripts **1996–2022**、2,480 注釈文 (train 1,984 / test 496) — explore 窓と重複 (memo Rank 5 が指摘済) | ⚠️ 汚染 (窓前半、roberta-large も CC-News 2016-09〜2019-02) | ✅ | Fed のみ | 未測定 | **不可 (a)** — E23 §0-4 既定どおり secondary |
| 4 | **Apel, Blix Grimaldi & Hull (2019)** Riksbank WP 381 / JMCB 2022 — FOMC minutes・transcripts から構築した hawk/dove 辞書 (term × modifier、隣接に限らない窓照合、net hawkishness = 1 + (hawk−dove)/(hawk+dove)) | 辞書 / 文書スコア | ⚠️ **再利用許諾未確認** — 公刊 WP の Appendix に全辞書掲載 (「The full dictionary is presented in the Appendix」) は**入手可能性**であって転記・live 内推論の許諾ではない。NC 条項は無いが、Riksbank の利用条件 / 著者許諾 / 語彙リストの著作物性判断のいずれかで根拠を確定するまで (a) は未確認 (行 0 の ABG 2012 と同じ地位 = 同じ未確認) | ✅ **標本 1993–2012** (WP 本文「Our sample period is 1993–2012」) = explore 窓に全面先行 | — | ✅ 転記モジュール + sha256 で pin 可 (**未転記**) | Fed 語彙 (英語)。ABG 2012 (Riksbank 語彙) を 4 CB に当てた前例と同型 | **未測定** — 辞書族。政策声明の語法に近い FOMC 由来 + 非隣接照合で ABG より密の可能性はあるが、prior は低め | **条件付き (NC 条項なし primary の唯一候補 — 再利用許諾未確認 ∧ 密度未測定)** — 許諾根拠の確定と step 1 census の両方が済むまで採否不能 |
| 5 | **Gardner, Scotti & Vega** (FEDS 2021-074 / J. Econometrics 2022) FOMC sentiment 辞書 (topic-keywords Table A5 + modifiers Tables A6/A7) | 辞書 / 文書 5 トピック (labor / output / inflation / financial / future policy) 合成 | ✅ 米連邦政府職員著作 (FEDS) + 論文 Appendix に語彙掲載。index 本体は「available upon request」 | ⚠️ 語彙選定 = FOMC **statements 2000-01〜2020-12** の高頻度語 (ラベルなし、頻度選定のみ) → explore 窓 2014–2020 と**重複 (宣言可、outcome 不使用)** | — | ✅ 転記可 | Fed のみ (声明語彙) | 未測定 (声明由来語彙で prior は高いが実測なし) | **不可 (primary)** — 出力は **景況 sentiment であり hawk/dove stance ではない** (future-policy トピックのみ stance 隣接)。stance への写像は in-house DoF = C5 違反。記述 secondary 可 |
| 6 | **CentralBankRoBERTa** (Pfeifer & Marohl 2023, JFDS; HF `Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier`) | RoBERTa / 文 binary sentiment (positive/negative) + 経済主体 5 クラス | ✅ **MIT** (HF card) | ⚠️ Fed/ECB/BIS **speeches** 19,381 本、注釈 6,683 文 (sentiment) — 年範囲は README 未記載 | ⚠️ 汚染 (窓前半、RoBERTa 系) | ✅ | Fed/ECB (+BIS) | 未測定 (stance 非出力) | **不可 (出力)** — **hawkish/dovish を出力しない**。sentiment→stance 写像は in-house DoF |
| 7 | **BIS CB-LMs** (Gambacorta et al., BIS WP 1215, 2024-10) | encoder-only MLM (BERT/RoBERTa を中銀スピーチ・政策文書・研究論文で再学習)、**stance ヘッド無し** | ❌ **ライセンス明示なし** (BIS 頁は 1.2 GB DL リンクのみ) | ⚠️ 事前学習コーパスに窓内の中銀文書を含む (年範囲未記載) | ⚠️ 汚染 (中銀文書で窓内を再学習、終端未記載 → 監査不能) | ✅ | 多 CB | — (as-is では stance を出さない) | **不可** — as-is 推論不能。stance を得るには in-house fine-tune (= DoF) が必要で、論文自身の stance 評価は TDW (NC) データで fine-tune |
| 8 | **Loughran–McDonald** Master Dictionary (Notre Dame SRAF) | 辞書 / 7 カテゴリ (negative / positive / uncertainty / litigious / strong & weak modal / constraining) | ❌ 学術無償・**商用は別途ライセンス** (SRAF 頁「for commercial licenses, please contact…」) | ✅ 10-K 由来 | — | ✅ | 汎用 | 未測定 (汎用語彙) | **不可 (a・出力)** — hawk/dove カテゴリ無し |
| 9 | **Picault & Renault (2017, JIMF)** ECB field-specific 加重 n-gram 辞書 (stance dovish/neutral/hawkish + 景況) | 辞書 / 文書確率 | ⚠️ **未確認** — cbcomindex.com は TLS 証明書不一致で到達不能、HAL は 403、ScienceDirect 有料 (2026-09-22) | ⚠️ ECB 記者会見 (introductory statements) 由来、年範囲は abstract に無し | — | 転記可 (入手できれば) | **ECB のみ** | 未測定 (声明系由来) | **保留 (C1 未確認)** — 単独では 4 CB パネルに不足。第6次で再訪 |
| 10 | **Tobback, Nardelli & Martens (2017)** ECB HD indicator (ECB WP 2085) | SVM / 記者会見ごとの指標 | ❌ モデル・データ非公開 | 入力は **メディア報道 9,000 本** (中銀テキストではない) | — | ❌ | ECB | — | **不可 (C1)** |
| 11 | **IMF WP 2025/109** (Silva–Moriya–Veyrune) fine-tuned LLM 分類器、74,882 文書 169 中銀 1884–2025 | LLM 分類 / 文 4 次元 | ❌ 複製データ・モデル非公開 ([[e23-cb-text-adjudication-s2-2026-08-18|E23 裁定 doc]] §2 の判定を再確認、変化なし) | — | ❌ LLM 系 | ❌ | 多 CB | — | **不可 (C1・c)** |
| 12 | **LLM zero/few-shot 採点** (GPT-4o / Claude / Llama-3 / Qwen 等) および frozen-LLM 表現回帰 (例: "Mind the Shift" arXiv 2603.14313、2026-03、Delta-Consistent Scoring) | 生成 LLM / 任意 | (open-weight は Apache/community 等で (a) を満たしうる) | — | ❌ **知識カットオフ汚染** (事前学習が窓内声明とその後の市況解説を含む) | 重みは凍結可だが無意味 | 多 CB | 未測定 | **恒久除外 (c)** — C5 規律新設案 (§7) |
| 13 | **FinBERT-tone** (`yiyanghkust/finbert-tone`) / ProsusAI FinBERT | BERT / 文 3 クラス tone (positive / negative / neutral) | ⚠️ HF card にライセンス記載なし | アナリストレポート 10k 注釈文 (企業金融ドメイン) | ⚠️ 汚染 (窓前半、BERT 系の Wikipedia/BookCorpus 終端 ≈2018) | ✅ | 汎用 | 未測定 | **不可 (出力・ドメイン)** — tone ≠ stance |

**行 1 のライセンス不整合の読み方 (保守側で固定)**: pooled モデルは NC-SA データセット (`gtfintechlab/WCB`) の派生物で、論文・README・LICENSE ファイルの 3 箇所が NC-SA を宣言している。model card の `cc-by-4.0` は 1 箇所の metadata に留まり、意図的な再ライセンスの記述 (論文正誤表・README 追記) が見当たらない。**したがって本稿は NC-SA が支配すると読み、live 転送資格を認めない。** 逆方向 (cc-by-4.0 が意図的) の可能性は残るので、確認経路 = 著者 (gtfintechlab) への書面照会 → 回答を KB に転記。**照会の実行は user 決裁 D12 の一部として扱う** (研究利用は §0-4 で既に可、急がない — memo §4.1 D12「#29 S1 の結果が出るまで急がない」)。

## 4. 候補別の所見 (step 1 設計への入力、価格非接触)

### 4.1 `model_WCB_stance_label` (文分類器、文書密度未測定、条件付き secondary)
- **強み**: 4 中銀すべてが訓練中銀 / 文レベル 4 クラス (irrelevant を含む = 声明の定型文を自動で落とせる) / revision sha `2a8d527f70ea7c58976eb01a3570a91512164570` で凍結可 / 論文 (NeurIPS 2025) で pooled モデルが per-CB モデルを上回ると報告 (「the whole is greater than the sum of its parts」)。
- **弱み**: (a) 不整合 / gated manual (条件同意 + 承認待ち、条件文言未取得 — 追加制約の可能性) / 訓練文書種 = 議事要旨 (声明ではない) → domain shift は宣言事項 / 訓練年 1996–2024 は E23 OOS 窓 (2024-01〜) と**テキスト重複** — ラベルは人手ガイドライン (市場データ不使用) なので outcome 汚染ではないが、新 pre-reg の事前差分節で「2024 テキストを訓練に含むモデル」と明記する / **文書レベル密度は未測定** — 声明の定型文が irrelevant/neutral に落ち、残る hawk/dove 文が少数または同数なら集約後 NH=0 (E23 と同型の退化) が起こりうる。「文分類器だから dense」は成立しない (基準表 dense 行) / **(c) 事前学習汚染** — roberta-base の CC-News (2016-09〜2019-02) が explore 窓前半の声明とその後の市況解説を含む。primary 昇格を審査する新 pre-reg は窓を 2019-03 以降に限定する事前差分節が必須 (encoder-only は免責にならない、5 巡目) / **fine-tune 終端 2024 の時間的リーク** — 事前学習 cutoff を守って窓を 2019-03 以降に限っても、分類器自体は 2024 までの中銀議事要旨・ラベルで訓練されており、評価窓の全観測より後の語法・ラベルを含む。ライセンスが解消しても**現行 checkpoint は primary 不可**、記述 secondary 固定。primary 経路は評価窓に先行する cutoff で再訓練した checkpoint のみ (6 巡目)。
- **step 1 での扱い (第6次で実行と裁定された場合)**: 記述 secondary。文→文書の集約規則は **1 本に凍結**: **NH = (#hawk − #dove)/(#hawk + #dove)** (比を保存 — 全 hawk なら文数が 1 でも 2 でも NH = 1)、irrelevant/neutral は分母に入れない、**#hawk + #dove = 0 (stance 文なし) のみ別規則で NH = 0 (中立) を代入**。5 巡目で E23 形 (h−d)/(h+d+1) を撤回 — 全 hawk 1 文→2 文で 1/2→2/3 と、構成が同一でも文数 (声明の長さ) だけで |ΔNH|>0 を作る分母アーティファクト (§4.2 ABGH と同型) で、secondary が見かけ上 dense になり後の primary 審査を汚染しうる。集約規則の複数試行は C5 違反。分類器には公刊の文書スコアが存在しないため集約規則は不可避で、辞書 (公刊式 as-is、§4.2) とは扱いが異なることを census 出力に明記する。primary と同じ列で **NH≠0 文書割合と |ΔNH| 分布**を報告し、文書密度をここで初めて実測する。

### 4.2 Apel–Blix Grimaldi–Hull (2019) 辞書 (NC 条項なし primary の唯一候補 — 再利用許諾未確認・密度未測定)
- **強み**: 標本 1993–2012 = 全窓先行 (ABG 2012 と同じ「探索自由度ゼロ」の性質) / FOMC 語彙 (Riksbank 議事録より政策声明の語法に近い) / term–modifier を**隣接に限らず**照合 (E23 §11.2 の死因 = 「形容詞は出るが名詞が隣接しない」への直接の反例設計) / 公刊 Appendix で全辞書が**入手**可 (転記の許諾は別問題 — 弱み参照)。
- **弱み**: 辞書族の疎性 prior (ABG 2012 が 85.3% NH=0) / Fed 由来語彙を ECB/BOE/BoJ 英語版に当てる = out-of-vocabulary の可能性 / 語数・照合窓幅は WP 本文の再読で確定が必要 (本稿では未転記) / **再利用許諾未確認** — Appendix 掲載は入手可能性のみ。Riksbank WP の利用条件 (riksbank.se の著作権表示 / WP 381 PDF の colophon)、著者許諾、語彙リストの著作物性 (事実の列挙か表現か) のいずれかで根拠を KB に転記するまで転記モジュールを作らない。同じ未確認は in-repo ABG 2012 にも当てはまる (pre-reg §0-3 は「WP 261 の逐語転記」という事実のみ記録) — E23 側の記録は凍結のため本稿では触らず、第6次 (§7-2 (vi)) で pre-reg §5 PASS 分岐の「凍結辞書のみなら NC 非該当」前提の再点検として上程する。
- **step 1 での扱い (第6次で実行と裁定された場合)**: primary 候補として **許諾根拠確定 → 逐語転記 → sha256 pin → P1 監査後コーパスに as-is 適用 → 連続同一 CB 声明ペアの |ΔNH| (価格非接触)** を数える。**クローズ条件 (§7-3 で事前固定。推定量 = memo §4.1-8 が承認した「連続声明ペアの |ΔStance| が雑音帯を超える割合」)**: ABGH-2019 の **|ΔNH| > τ となる適格連続ペアの割合が過半 (> 50%、厳密) に届かなければ**「dense primary 不在」で #29 S1 候補なしクローズ (secondary だけでは pre-reg の primary が立たない)。閾値は本稿 §1/§2 の dense 定義「大半」に一致させた**絶対水準** — 相対基準 (ABG-2012 比 2 倍 = 34.7%) は 3 巡目版まで書いていたが、35% 通過 = 65% のペアが無変化のまま「dense」と呼ぶ矛盾 (レビュー P2、4 巡目) で撤回。E23 の 323 ペア規模なら過半 (> 161.5) = ≥162 イベントで Gate B 100 を余裕で超え、E23 §10.2 の「上界でようやく閾値」型 knife-edge を避ける (相対 2 倍 = ≈112 は閾値近傍で E23 と同じ死に方をしうる)。ペア規則 = E23 §2/§3 を継承 (同一 CB の直前声明とペア、staleness >120 暦日 void、Fed/ECB 同日衝突 void、各 CB 初回は分母外)、スコア式 = **WP 381 公刊の net hawkishness NH = 1 + (h − d)/(h + d) を as-is で使う** (E23 形 (h−d)/(h+d+1) への置換は禁止 — 全 hawk で 1 ヒット→2 ヒットの連続文書は公刊スコア 2→2 (Δ=0) だが置換式では 0.5→0.667 (Δ≠0) となり drift 推定量そのものが変わる。2 巡目版はこの置換を書いていた — レビュー P2 3 巡目で撤回)。**h + d = 0 (無ヒット) の文書のみ別規則**: 公刊式が未定義なので NH = 1 (公刊式の h = d の値 = 中立) を代入 — ABG-2012 ベースライン (E23 形で無ヒット = 0 = 中立) と同じ扱いにし、「無ヒット → ヒット」の遷移を両側で同じく drift に数える。別案 (無ヒットを含むペアを void) は採らず、1 規則に凍結して試行しない。τ = 0 なら両モデルの尺度差は割合に影響しない (「スコアが変化したペアの割合」は尺度不変) — τ>0 を採るなら尺度調和が要るのも、τ を新 pre-reg の領分に置く理由。**雑音帯 τ = 0 に凍結** (カウント由来スコアでは「雑音」= 語彙カウント無変化のみで、E23 pass-1 の凍結イベント定義 `ΔNH ≠ 0` と同一。τ=0 は候補に最も有利な帯なので、ここで過半に届かない候補は確定的に非 dense。τ>0 の採否は新 pre-reg の事前差分節の領分で、census から決めない)。参照値 (監査前コーパス、pass-1、pre-reg §11.1–11.2): ABG-2012 は 327 文書 = イベント 56 + void 267 (全件 ΔNH=0) + 各 CB 初回 4 → **|ΔNH|>0 ペア = 56/323 = 17.3%** (記述参照値 — ゲートには使わない)。文書 NH≠0 割合 (48/327 = 14.7%。pass-0 の matched bigram 50/327 は別量) は**記述 secondary 指標**として併載し、ゲートには使わない — 文書割合とペア割合は一致しない (同じ非零スコアが連続すれば ΔNH=0、孤立した非零文書は前後 2 ペアに drift を作る) ため、承認された推定量で直接ゲートする (レビュー P2、2 巡目)。**ABG-2012 の扱い**: 再実行しない (再評価 §3 Rank 8 (iii) / L134 の禁止)。絶対水準ゲートなので監査後コーパスでのベースライン再計算は不要 — 監査前 pass-1 の 56/323 を記述参照値として併記し、コーパス不一致 (P1 監査で Fed 文書が動く) を caveat に書く (§7-3)。

### 4.3 その他
- Gardner–Scotti–Vega (行 5) は Fed 限定の記述 secondary として census に併載可 (景況 sentiment、stance ではないことを列名で明示)。
- CentralBankRoBERTa (行 6) は MIT だが stance を出さない — 「MIT だから使える」型の誤用を防ぐため本表に残す。
- Picault–Renault (行 9) は第6次 (10-18) で cbcomindex.com / 著者版 PDF の再取得を試み、入手できれば ECB 単独 secondary として追記。

## 5. C1–C6 裁定 (単独候補 = **#29 S1「公刊凍結 stance モデル as-is 推論 × G4 中銀声明 × 声明間ドリフト」の S1 intake**)

round-2/3/4/5 と同一 hard constraints。**本表は family 採用の裁定ではなく、S1 (記述級) 継続可否の裁定**である。

| 制約 | 判定 | 根拠 |
|---|---|---|
| **C1 データ入手性** | **△ 条件付き** | コーパス: in-repo 398 文書 + sha256 manifest (再取得不要、ただし P1 監査で manifest 変更予定)。モデル: primary 候補 (ABGH-2019) は公刊 Appendix で $0・即時に**入手**可だが再利用許諾は未確認 / 文分類器候補 (WCB pooled) は gated manual + ライセンス不整合。**無条件に利用可能な候補は 0 (ABGH = 許諾未確認、WCB = 不整合)、dense と実測された候補も 0** (密度は全候補で step 1 まで未測定) |
| **C2 falsified 除外** | **✅ 適法** | E23 #25 は **UNDERPOWERED / park であり FAIL ではない** → pre-reg §6 の FAIL クローズ範囲は**未発効**。E7 (NFP/CPI headline z × sign-follow × M15) / E15 (無条件イベント窓) の ban は E23 §8 と同じ 3 要素差分で外。復活経路 (§6「新特徴量系 + 新 family + 事前差分節 + 新敵対的検証」) の字義に一致。⚠️ pre-reg 起草時は E23 との**事前差分節** (窓・CB・文書種・ペア写像の継承有無、E23 pass-1 Gate A の P1 欠陥 = 全期間 median による OOS 窓の無条件リターン接触を宣言) が必須 |
| **C3 非重複** | **✅** | E1 (positioning) / E12 (volume) / ECG #22 (equity curve) / #27 family A (label-facing、FAIL クローズ) とモダリティ・endpoint が直交。同じ text モダリティの E23 とは特徴量系が別 (辞書隣接 bigram vs 文分類器 / 非隣接辞書)。per-pair 1 position での USD_JPY スロット競合 (memo §2.1) は**執行側の論点**で S1 には無関係 |
| **C4 摩擦生存** | **⏸ 未評価 (本稿の設計上、評価不能)** | 価格非接触。E23 pass-1 Gate A「3/3 ペア通過」は PR #257 P1 (全期間 median) の監査待ちで**引用は監査付き**。memo §3 Rank 5: USD_JPY レグの swap を E23 Gate D bound (1.5p/5bd) で継承すると 3–5 倍過小評価 → 新 pre-reg の Gate D は bound を改定して凍結 (数値は本稿で決めない) |
| **C5 反 curve-fit** | **✅ 条件付き** | 特徴量 = 公刊凍結モデル as-is (sha256 pin)、集約規則 1 本凍結、辞書語彙の編集禁止 (E23 §0-3 継承)。**LLM zero/few-shot・frozen-LLM 表現採点は恒久除外 (行 12)**、encoder 分類器も事前学習終端以前の窓は汚染扱い (基準 (c))。step 1 census (実行は第6次裁定後) の出力は密度指標のみで閾値探索を含まない |
| **C6 revealed edge** | **△** | プロジェクト内の revealed はゼロ。文献 (Shah et al. 2023 の市場分析、Picault–Renault 2017 の Taylor rule / ボラ説明力) は**公表済み**で McLean–Pontiff 型の公表後減衰 prior に乗る (第5次 §3.1)。E23 §1 の負 prior (E15+E7 二重 FAIL 家系、explore→OOS 生存 0/18 系統) は不変 |

**裁定**: **step 0 の結論 = 無条件候補 0 / 条件付き 2 (いずれも dense 未確認)。step 1 census は提案として置き、実行可否は第6次 (10-18) の裁定に委ねる。family 採用・explore LOCK は起案しない。** 再評価 09-22 §3 Rank 8 (iii) が #29 S1 を step 0 に限定している (候補ゼロでも可) ため、本稿は step 1 を承認せず、着手可能本数にも数えない (§6)。第6次が「step 1 実行」と裁定した場合のクローズ条件は §7-3 の文言 (適格連続ペアの過半 > 50% (厳密) で |ΔNH|>0、τ=0 凍結、絶対水準 — ABG-2012 は再実行せず 56/323 = 17.3% を記述参照値に) で事前固定済み。time-to-M2 への寄与評価は memo Rank 5 (refuted、+0.4〜1.6pp) から**動かない** — 本稿は供給ライン (WIP) の充足手段としてのみ意味を持つ。

## 6. 供給ライン会計 (WIP、2026-09-22 本稿後)

| 分類 | 本数 | 内訳 |
|---|---|---|
| **着手可能 (能動)** | **0** | 本稿 (step 0) で #29 S1 の承認範囲 (再評価 09-22 §3 Rank 8 (iii) = step 0 のみ) は消化済み。**step 1 census は下段「提案 (裁定待ち)」であって着手可能本数に数えない** — 数えると後続の自動化・レビューが承認範囲外の作業 (辞書転記・census 実行) を能動ラインとして執行しうる。WIP 規則「0 本なら期日を待たず臨時スキャン」は本稿で充足済みで、第6次 (10-18) までの再発動は本稿の結論を再演するだけなので行わない |
| **提案 (裁定待ち)** | 1 | **#29 S1 step 1 census** — 第6次 (10-18) で実行可否を裁定。実行なら前提 = **E23 P1 監査 (10-03) 後のコーパス確定** + ABGH-2019 の再利用許諾根拠確定 + 転記 + sha256 pin。ABG-2012 の再実行は含まない。価格非接触・$0。⚠️ **台帳 #29 は未登録のまま** (登録は第6次 or 新 pre-reg 起案時の裁定) — 提案は S1 intake の作業単位であって採用 family ではない |
| 時限ロック (受動) | 3 | E1 first look 2026-10-15 / ECG #22 2026-11-06 / E12 2027-02-05 |
| 条件付き (受動) | 2 | #4 MoF 次エピソード再判定 (~11-14) / `ws3-round4-eur-divergence-conditional` (cache 11-15) |
| park | 2 | E23 #25 (UNDERPOWERED — 09-19 追記の P1×3 は「park 根拠の estimand 監査」として 10-03 消化予定) / family B |
| FAIL クローズ (直近) | 1 | #27 family A statement_ladder (09-18 — 凍結 α 規則未達のみを意味し、検出力 caveat 付きでしか引用しない。数値は本稿では転記しない) |

**規律確認**: 本節は手続き状態のみ。発言×介入・声明×価格のジョイント量は一切計算していない。「供給ライン全滅」型の表現は使わない (第5次 §2 教訓)。

## 7. 次アクションと registry 更新案 (執行は本 PR 外)

1. **[10-03 まで / R3 / 別 PR]** E23 P1×3 消化 (`review-backlog-253-257-digest`) — Fed discovery を FOMC statement 限定に修正し manifest を更新。**#29 step 1 はこの後のコーパスで走らせる** (順序固定)。
2. **[第6次 2026-10-18 / R3]** 本稿 (step 0) を持ち込み、(i) **#29 S1 step 1 census の実行可否** — 再評価 09-22 §3 Rank 8 (iii) の「step 0 のみ」を解く**新しい裁定**であり、本稿は承認しない ((i) を解いても ABG-2012 再実行の禁止は残る — 本稿のゲートは絶対水準なので再実行を必要としない)、(ii) #29 の台帳登録可否、(iii) explore 枠の現在値確定 (0/3〜2/3)、(iv) Picault–Renault 再取得、(v) 下記 C5 規律の KB 反映、(vi) **ABG-2012 / ABGH-2019 辞書の再利用許諾根拠の確認経路** (Riksbank 利用条件 / 著者照会 / 語彙リストの著作物性) と、E23 pre-reg §5 PASS 分岐の「凍結辞書のみなら NC 非該当」前提の再点検 (E23 記録は凍結のため本稿では触らない)、を裁定。
3. **[第6次で (i) = 実行と裁定された場合のみ / 10-18 以降 / R3 / 別 PR、価格非接触]** #29 S1 step 1 census: ABGH-2019 の再利用許諾根拠を KB に転記 (§7-2 (vi) の裁定に従う) → 辞書の逐語転記 (`tools/` 新モジュール、WP 381 Appendix 出典明示、sha256 pin、test で語彙編集を封鎖) → P1 監査後コーパスに as-is 適用 → **連続同一 CB ペアの |ΔNH|>0 割合 (primary 指標、E23 ペア規則継承)** / 文書 NH≠0 割合 (記述 secondary) / |ΔNH| 分布 / CB 別 (件数のみ)。**ABG-2012 は再実行しない** (再評価 §3 Rank 8 (iii) / L134 の禁止は第6次 (i) では解けない)。ゲートは絶対水準なのでベースライン再計算は不要 — 監査前 pass-1 の 56/323 = 17.3% を記述参照値として併記し、コーパス不一致 (Fed 非声明文書の除去で ABG 側の割合は動く、向きは未検証) を caveat に書く。secondary 併載 = WCB pooled (研究利用、§0-4 — 文書密度の実測を兼ねる)、Gardner–Scotti–Vega (Fed 景況 sentiment、stance 非該当を明示)。**閾値・ホライズン・ペア写像の探索は禁止** (それは pre-reg の領分)。クローズ条件を census 実行前に本節の文言で固定: 「**ABGH-2019 の適格連続同一 CB 声明ペア (staleness >120 暦日と Fed・ECB 同日衝突は分母からも除外、各 CB 初回は分母外) のうち |ΔNH| > τ (τ = 0 凍結) の割合 ≤ 50% (過半未達 — 丁度半数は不通過) なら dense primary 不在 → #29 S1 候補なしクローズ**。スコア式は公刊 as-is: ABGH-2019 = 1 + (h−d)/(h+d)、h+d=0 のみ NH=1 (中立) 代入」。参照値 (監査前、pass-1、pre-reg §11.1–11.2、記述のみ): ABG-2012 (in-repo E23 凍結モジュール、(h−d)/(h+d+1)) = イベント 56 / (327 − 4) = **56/323 = 17.3%** (staleness / 同日 void は 0 件なので分母 323 のまま)。過半 (> 50% — 323 ペアなら > 161.5 → ≥162 イベント、偶数分母なら半数 + 1) = Gate B 100 の 1.6 倍で knife-edge 回避。6 巡目で「≥50% 通過 / < 50% クローズ」を「> 50% 通過 / ≤ 50% クローズ」に訂正 — 偶数分母で丁度半数の候補を通さない (過半 = 厳密不等号)。推定量の訂正履歴: 初版は pass-0 の matched bigram 50/327 (15.3%) を文書 NH≠0 と誤用 → 1 巡目で 48/327 = 14.7% に訂正 → 2 巡目で推定量自体を memo §4.1-8 の承認定義 (連続ペア drift) に合わせて置換し、文書割合は記述 secondary へ (孤立した非零文書スコアだけでは承認推定量の密度にならない) → 4 巡目で閾値を相対 (ABG-2012 比 2 倍 = 34.7%) から絶対 (過半 > 50% (厳密)) に置換 — 本稿の dense 定義「大半」との不整合 (35% 通過で 65% 無変化) を解消。τ=0 は候補に最も有利な帯 (τ>0 は新 pre-reg の事前差分節で凍結、census から決めない)。
4. **[user 決裁 D12 (統合パケット、返答期限 11-30)]** WCB pooled のライセンス不整合の**照会可否**を D12 に同梱 — 選択肢 = (i) 著者照会 (書面回答を KB 転記、cc-by-4.0 確認でも現行 checkpoint は fine-tune 終端 2024 の時間的リークで primary 不可 — 審査対象になるのは評価窓に先行する cutoff で再訓練した checkpoint のみ) / (ii) license-free 再実装 (NC-SA データで学習しない設計 — 実質 ABGH-2019 路線) / (iii) 研究 secondary のまま。**急がない** (memo §4.1 D12)。
5. **C5 規律新設案 (text モダリティ)**: 「LLM (API / open-weight) の zero/few-shot 採点、および frozen-LLM 表現からの stance 回帰は、事前学習コーパスが観測窓内の中銀文書とその後の市況解説を含む (知識カットオフ汚染) ため、explore/OOS の特徴量として**恒久禁止**。許容 = 観測窓に先行して公刊・凍結された辞書、または**事前学習コーパスの終端を監査可能に確定し、終端以前の観測窓を汚染として除外した**小型 encoder 分類器の as-is 推論 (訓練標本の年範囲・文書種・注釈手順の宣言も必須) のみ。encoder-only であること自体は免責にならない。」— 反映先 = [[edge-development-pipeline-2026-07-18|パイプライン]] §3 (C5 の text 項) と [[e23-cb-text-explore-prereg-2026-09-10|E23 pre-reg]] 相互参照。**本 PR では執行しない** (hot file 回避 + 規律追加は第6次で一括)。

**registry 更新案 (S7 が編集)**:
- `edge-supply-scan-monthly` (deadline **2026-10-18 は据え置き**): message に「**臨時スキャン 2026-09-22 実行済 (#29 S1 step 0、[[adhoc-scan-29-step0-2026-09-22]])**: 無条件候補 0 / 条件付き 2 (WCB pooled = ライセンス不整合で secondary、ABGH-2019 辞書 = NC 条項なし primary 候補・再利用許諾未確認・密度未測定)。WIP 会計: 着手可能 (能動) 0 / 提案 1 (S1 step 1 census — 第6次で実行可否を裁定、承認は再評価 09-22 Rank 8 (iii) の step 0 限定を解く新裁定が必要)。第6次で step 1 実行可否・辞書再利用許諾の確認経路・#29 台帳登録可否・explore 枠現在値・C5 text 規律を裁定」を追記。
- `review-backlog-253-257-digest` (10-03): message に「#257 分の Fed discovery 修正は **#29 S1 step 1 census (第6次で実行と裁定された場合) の前提** — 消化順序を先に」を追記。
- 新規 (**第6次で step 1 実行と裁定された場合のみ**、`deadline_info`): `adhoc-scan-29-step1-census-gate` — deadline は第6次が置く (第7次 ≈ 2026-11-18 の前)。「E23 P1 監査後コーパスで ABGH-2019 を census し、適格連続同一 CB ペアの |ΔNH|>0 割合 (τ=0、公刊スコア as-is) ≤ 50% (過半未達 — 丁度半数は不通過) なら #29 S1 候補なしクローズ (ABG-2012 56/323 = 17.3% は記述参照値、再実行なし)」。**本稿時点では起票しない** (初版の 10-17 期日案は step 1 を第6次前に走らせる前提で、step 0 限定の承認範囲を超えていた)。

## 8. 正直な caveat

- (a) 判定は **2026-09-22 時点の公開 metadata** に基づく。HF の license タグは作者が随時変更できるため、pre-reg LOCK 時に revision sha と当該時点の card 本文を KB に転記して再確認する。
- WCB pooled の gated 条件文言は未取得 (同意画面はログインが必要)。条件に「非商用」等の追加制約があれば (a) は確定的に不可。
- ABGH-2019 の語数・照合窓幅・極性反転規則は WP 381 本文の精読で確定が必要 (本稿は pypdf 抽出テキストの部分照合のみ: 「dictionary constructed using the FOMC's minutes and transcripts」「full dictionary is presented in the Appendix」「sample period is 1993–2012」の 3 点を確認)。
- Picault–Renault (行 9) は到達不能につき **未評価** — 「不可」ではない。
- 本稿の候補表は網羅ではない (検索 2026-09-22、英語文献のみ)。第6次で追補可。
- **「dense」列は全候補で未測定**。候補表が記録したのは密度の必要条件 (出力粒度・被覆) のみで、密度そのもの (適格連続ペアの |ΔNH|>0 割合) は step 1 census でしか確定しない。初版が文分類器を「構造的に dense」と書いたのは推論であり、本版で撤回 (レビュー P2、2026-09-22)。
- **本稿は step 1 を承認しない**。再評価 09-22 §3 Rank 8 (iii) の承認範囲は step 0 のみ。step 1 の実行・registry gate 起票は全て第6次 (10-18) の裁定後。ABG-2012 の再実行は第6次後も行わない (「やらないこと」L134) — 4 巡目でゲートを絶対水準にしたため baseline 再計算の必要自体が消え、2 巡目版の (i-b) 裁定項目は削除した。
- **ABGH-2019 の「license-free」は本版で「NC 条項なし・再利用許諾未確認」に格下げ**。公刊 Appendix 掲載は入手可能性であって転記・live 内推論の許諾ではない (レビュー P2、2 巡目)。同じ未確認は in-repo ABG 2012 にも当てはまる (pre-reg §0-3 は転記の事実のみ) — E23 記録は凍結のため本稿では改変せず、第6次 (§7-2 (vi)) に上程。
- **クローズ条件の推定量は連続ペア drift (τ=0 凍結) に固定**し、文書 NH≠0 割合は記述 secondary に降格。1 巡目で文書割合のベースラインを 48/327 に訂正したが、推定量そのものが承認定義 (memo §4.1-8) と異なっていた。4 巡目で閾値を相対 (ABG-2012 比 2 倍 = 34.7%) から絶対 (適格ペアの過半 > 50% (厳密)) に置換 — §1/§2 の dense 定義「大半」と一致させ、35% 通過で 65% 無変化を dense と呼ぶ矛盾を解消 (レビュー P2、4 巡目)。
- **ABGH-2019 のスコアは公刊式 as-is** (1 + (h−d)/(h+d))。2 巡目版が書いた E23 形への置換は drift 推定量を変える (同方向の強度変化を偽の drift に数える) ため撤回。h+d=0 の文書への中立 1 代入だけが本稿の追加規則で、ABG-2012 側の「無ヒット = 中立 0」と対称にするための 1 規則凍結 (レビュー P2、3 巡目)。
- **WCB secondary の集約も比保存形 (#hawk − #dove)/(#hawk + #dove) に訂正**、stance 文ゼロのみ中立 0 代入。3 巡目版まで残っていた (h−d)/(h+d+1) は声明の長さだけで偽 drift を作る (レビュー P2、5 巡目)。
- **(c) の encoder 免責を撤回**。RoBERTa 系の事前学習 (CC-News 2016-09〜2019-02) は explore 窓前半の声明とその後の市況解説を含むため、encoder 分類器も終端以前の声明では汚染扱い。候補表の (c) 列は行 1・2・3・6・7・13 を「低」から「⚠️ 汚染 (窓前半)」に改めた。清浄に使える区間は事前学習終端後のみで、primary 審査の pre-reg はそこに窓を限定する事前差分節が必須 (レビュー P2、5 巡目)。
- **WCB pooled は許諾が解消しても現行 checkpoint では primary 不可** — fine-tune 標本 (1996–2024) が (c) 清浄区間 2019-03〜2023 の全観測より後の中銀語法・ラベルを含む。基準 (b) を「重複の宣言で可」から「訓練標本終端が評価窓に先行」に強化 (6 巡目)。primary 経路は cutoff 先行の再訓練 checkpoint のみ。
- **過半は厳密不等号 (> 50%)**。5 巡目版までの「≥50% 通過 / < 50% クローズ」は偶数分母で丁度半数を通してしまう — 「≤ 50% クローズ」に訂正 (6 巡目)。

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
| E23 park 数値 (N=56、**NH=0 279/327 → NH≠0 48/327 = 14.7%** (pass-1、pre-reg §11.2))、§0-4 条項、§6 復活経路 | [[e23-cb-text-explore-prereg-2026-09-10]] §0-4, §6, §10.2, §11.1–11.4 |
| matched bigram ≥1 の文書 = 50/327 (pass-0、**NH≠0 とは別量** — bigram を持つが #hawk = #dove の 2 文書は NH=0) | [[e23-pass0-census-2026-09-15]] 「Gate B 到達可能性の上界」節 |
| #29 S1 = step 0 のみ (候補ゼロでも可)、ABG 辞書 census 禁止、結論は 10-18 を待たず臨時スキャン記録に | [[path-to-win-reassessment-2026-09-22]] §3 Rank 8 (iii) (L74) + 「やらないこと」L134 (ABG 辞書での #29 census 実行) |
| S1 census の承認推定量 = 「連続声明ペアの \|ΔStance\| が雑音帯を超える割合」 | [[path-to-win-decision-memo-2026-09-20]] §4.1-8 (L117) |
| 連続ペア会計: 327 文書 = イベント 56 + void 267 (全件 ΔNH=0) + 各 CB 初回 4 → ペア 323、\|ΔNH\|>0 = 56/323 = 17.3% / ペア規則 (staleness >120 暦日 void、Fed・ECB 同日 void、t0) / ABG-2012 スコア式 NH = (#hawk − #dove)/(#hawk + #dove + 1) (E23 凍結モジュール、無ヒット = 0) | [[e23-cb-text-explore-prereg-2026-09-10]] §2 (L38–56), §11.1–11.2 |
| RoBERTa 事前学習データに CC-News (63M 英語ニュース記事、2016-09〜2019-02 収集) を含む | Liu et al. 2019 "RoBERTa", arXiv 1907.11692 §3.2 (Data) |
| ABGH-2019 公刊スコア net hawkishness = 1 + (hawk − dove)/(hawk + dove) (h+d=0 で未定義 → census では中立 1 を代入、公刊スコアは不改変) | Riksbank WP 381 PDF (pypdf 抽出、`scratchpad/rb381.txt`) |
| ABG 2012 の in-repo 転記根拠 = 「WP 261 の逐語転記、全観測窓に先行公刊」のみ (再利用許諾の記録なし) / §5 PASS 分岐「凍結辞書のみなら NC 非該当」 | [[e23-cb-text-explore-prereg-2026-09-10]] §0-3 (L13), §5 (L86) |
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
