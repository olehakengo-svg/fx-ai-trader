# #29 S1 step 1 — ABGH-2019 辞書の逐語転記 + 価格非接触 census: **DENSE_PASS 127/228 = 55.7% (knife-edge、Wilson 下限 0.492)** → R1 裁定は user (2026-11-05)

**位置づけ**: [[adhoc-scan-29-step0-2026-09-22|step 0]] (候補同定) の後段。[[external-hypothesis-scan-round6-2026-10-20|第6次スキャン]] §3-(i) で承認された **診断枠** (供給ライン非算入・F1 分子分母外・explore 枠非消費・WIP 下限に数えない) の step 1 = 辞書転記 + 列挙器 + census。辞書転記の gate = **#29-L user 承認 (2026-11-03、§9.1)**。registry `adhoc-scan-29-step1-census-gate` (11-07) を本稿で resolve。
**rule:R3** (価格非接触、$0、閾値・ホライズン・ペア写像の探索なし)。**live への影響: ゼロ** (live/shadow/tier/lot/Kelly/凍結 look 非接触)。
**成果物**: `tools/adhoc29_lexicon_abgh2019.py` (辞書、sha256 `37a76f5392a5694b6e209e5aef86df183c3884a84b37cfc7b5b507b59b833caf`) / `tools/adhoc29_abgh_census.py` (列挙器) / `tests/test_adhoc29_lexicon_abgh2019.py` 9 本 + `tests/test_adhoc29_abgh_census.py` 7 本 (語彙編集・規則変更・価格混入を封鎖) / `knowledge-base/raw/analysis/adhoc29-abgh-census-2026-11-05.{json,md}`。

## 0. 先出し (TL;DR)

1. **primary (step 0 §7-3 の事前固定ゲート、文言不改変)**: 適格連続同一 CB 声明ペア **n = 228** (= ABG-2012 監査後 pass-1 の分母 228 と完全一致 — 同一コーパス・同一ペア規則の確認) のうち |ΔNH| > τ (τ = 0) は **k = 127 = 55.7%** → **> 50% (厳密) を満たす = DENSE_PASS** (dense primary 候補あり)。参照値 ABG-2012 は同じ分母で 40/228 = 17.5% — ABGH-2019 は同一ペア集合で **3.2 倍**。
2. **knife-edge (敵対的 3 点検査、§4)**: Wilson 95% 区間 **[0.492, 0.620]** で下限が 0.5 を割る / CB 別は **boe 87.7% · fed 67.9% · ecb 18.3%** = pooled の通過は 3 CB 中 2 CB が担い、ECB は ABG-2012 と同じ疎性 (FOMC 由来語彙の OOV、step 0 §4.2 で予告した弱み) / 年別は 10 年中 5 年のみ > 50% 厳密。ゲートは census 前に固定 (09-22) で、τ・規則・閾値の代替は一切試していない。
3. **帰結 (台帳 #29 行の規定どおり)**: DENSE_PASS 時の後段 = **「新 pre-reg DRAFT (R1) + explore 枠 1 消費の裁定」= user 決裁** (autopilot は R1 を起案しない)。registry `adhoc-scan-29-dense-pass-r1-disposition` (期日 2026-11-17 = 第7次スキャン) に **user 決裁点** として起票。**推奨 (Claude 案、拘束しない)**: knife-edge + ECB 疎性のため、pre-reg を書くなら事前差分節で CB 集合 (fed/boe 限定か pooled か) と τ を**最初に**凍結し、explore 枠消費は第7次の WIP 会計と同時に裁定する。memo Rank 5「#29 は time-to-M2 レバーとして refuted」は本稿で**変えない** (診断枠)。
4. **やっていないこと**: WCB pooled secondary (user gated 同意なし = 未実行) / Gardner–Scotti–Vega secondary (未実行) / ABG-2012 再実行 (禁止、参照値のみ併記) / 価格・リターン・t0 写像・方向の読み込み (ゼロ)。

## 1. 辞書転記 (逐語、凍結)

| 事項 | 内容 |
|---|---|
| 一次資料 | Apel, M., M. Blix Grimaldi & I. Hull (2019), *How Much Information Do Monetary Policy Committees Disclose? Evidence from the FOMC's Minutes and Transcripts*, Sveriges Riksbank Working Paper Series **No. 381** (November 2019), 6 Appendix Table 4 (Inflation, p.34) / Table 5 (Economic Activity, p.35) / Table 6 (Employment, p.36)、本文 §2.1 と式 (1) (p.8) |
| URL / 取得 | `https://www.riksbank.se/globalassets/media/rapporter/working-papers/2019/no.-381--how-much-information-do-monetary-policy-committees-disclose-evidence-from-the-fomcs-minutes-and-transcripts.pdf` — 2026-11-05 取得 (HTTP 200、614,933 bytes、PDF sha256 `a5e1e048f57d9d5384ffb7ee2e785d8cbf981464b1f8ad657a2cc0679fd6f14f`) |
| 転記方法 | PDF テキスト層を x 座標で TERM / HAWKISH / DOVISH の 3 列に機械分離 (列境界の曖昧さゼロ) → 全行目視照合 → `DICTIONARY` タプルに**印字どおり**転記 (行順・綴り・`*` の有無を保持) |
| 規模 | 8 エントリ / TERM 10 語 (consumer prices, inflation, inflation pressure, consumer spending, economic activity, economic growth, resource utilization, employment, labor market, unemployment) / hawkish modifier 83 / dovish modifier 81 (印字どおり) |
| 印字どおりの異常 (編集せず) | Table 5 "consumer spending" の **HAWKISH 列に `soft*` / `weak*`** (DOVISH 列にも `soft*`)。誤植の可能性があるが転記側で直すことは語彙 DoF の持ち込み = C5 違反なので印字どおり。影響は記述のみ (§3 で consumer spending 由来のヒットは少数) |
| 凍結規則 (WP §2.1 as-is) | TERM = 小文字トークン列の完全一致・同一位置は最長一致 1 件 (「substrings … single instance」) / MODIFIER `x*` = 語幹前方一致、`*` なし = 完全一致、2 語 (`edg* up` 等) = 先頭語前方一致 + 直後 "up"、`run-up/runup` = いずれかの完全一致 / 窓 = **同一文内 ≤ 7 語、前後どちらも** / 計数 = TERM 出現 × 窓内 MODIFIER 出現 (字義読み、WP が明示しない点は 1 規則に凍結し代替は試さない) / **NH = 1 + (h − d)/(h + d)** (式 (1))、h + d = 0 のみ NH = 1 (中立) 代入 (step 0 §4.2 の凍結規則) |
| pin | `test_frozen_dictionary_sha256_pin` (canonical JSON sha256) + 表構造 pin (エントリ 8 / TERM 10 / modifier 件数 [(15,15),(18,16),(10,9),(15,14),(6,5),(12,12),(2,5),(5,5)]) + 規則 pin 7 本 + 価格非結合 pin |

### 1.1 再利用根拠 (#29-L、user 承認 2026-11-03) — 一次資料の転記

- **出所**: Sveriges Riksbank, "Open data – information available for re-use" (`https://www.riksbank.se/en-gb/about-the-riksbank/about-the-website/open-data--information-available-for-re-use/`、2026-11-05 取得)。
- **原文 (条件)**: "The Riksbank's open data is freely available and may be further used without any special consent or agreement being required. Enter source, Sveriges riksbank and date." 同頁は re-use 対象文書として "Publications and reports — The Riksbank's publications are available for download at riksbank.se" を列挙し、根拠法を "The act (2022:818) on the public sector making data available for re-use … implementing EU directive 2019/1024 … and replaces the previous PSI law (2010:566)" としている。
- **条件の履行**: 出所表記 "Source: Sveriges Riksbank, Working Paper No. 381 (2019), retrieved 2026-11-05" をモジュール docstring・本稿・census 成果物に記載。
- **未確認点 (正直に)**: 法 2022:818 の**条文**が WP 付録の語彙表 (著作物性の判断を含む) に及ぶかは一次資料 (riksdagen.se の条文) で**未確認**。本稿の読みは open-data 頁の「Publications and reports」列挙 + 「special consent or agreement 不要」の文言に依拠する。**user が本読みに異論を述べた時点で転記を止め、`tools/adhoc29_lexicon_abgh2019.py` と派生物 (census 成果物・本稿の数値) を削除する** (round6 §9.1 #29-L 行の規定)。

## 2. 母集団と推定量 (E23 ペア規則継承、価格非接触)

- コーパス = `tools/e23_corpus_fetch.load_corpus()` (P1 監査後 loader: Fed 非 statement 除外、窓外除外、manifest 2026-10-01 pass-0 = fed 102 / ecb 83 / boe 90 / boj 113) の explore 窓 [2014-01-01, 2023-12-31] ∧ n_chars > 0。
- CB = pass-0 生存 **fed / ecb / boe** (BoJ は V3 公開時刻未検証で fail-closed、[[../raw/analysis/e23-pass1-events-2026-10-01|pass-1 10-01]])。usable 文書 231 (fed 82 / ecb 83 / boe 66)。
- ペア = 同一 CB の日付順で直前声明とペア。各 CB 初回 (3 件) は分母外。staleness > 120 暦日と Fed×ECB 同日衝突は**分母からも除外** (void) — 本コーパスでは**両 void とも 0 件** (pass-1 10-01 と同じ)。
- 推定量 (memo §4.1-8 承認定義) = 適格ペアのうち |ΔNH| > τ の割合、τ = 0 凍結。ゲート = 過半 (> 50%、厳密不等号)。
- 価格・リターン・t0 写像・ペア→通貨ペア写像・方向は census モジュールから構造的に排除 (`test_census_module_is_price_free`)。

## 3. 結果 (件数・割合のみ)

| 量 | 値 |
|---|---|
| 適格ペア n | **228** (fed 81 / ecb 82 / boe 65) |
| \|ΔNH\| > 0 ペア k | **127** (fed 55 / ecb 15 / boe 57) |
| 割合 k/n (**primary**) | **55.7%** → **DENSE_PASS** (> 50% 厳密) |
| Wilson 95% (記述) | [0.492, 0.620] |
| CB 別 k/n | boe **87.7%** / fed **67.9%** / ecb **18.3%** |
| 文書 h+d>0 | 192/231 (fed 80/82、boe 66/66、ecb 46/83) |
| 文書 NH≠1 | 172/231 |
| ヒット数/文書 中央値 | 全体 5 (p25 1 / p75 8、max 16); fed 7 / boe 6 / **ecb 1** |
| hawk / dove 総数 | 663 / 501 |
| \|ΔNH\| (drift ペアのみ) | min 0.044 / p25 0.200 / p50 0.343 / p75 0.545 / max 2.0 |
| 両文書 h+d>0 のペア | 186 (うち drift 120); 残り drift 7 件は「無ヒット ↔ ヒット」の遷移 |
| 年別 n / k | 2014 17/7 · 2015 16/8 · 2016 27/19 · 2017 23/15 · 2018 24/10 · 2019 24/13 · 2020 25/12 · 2021 24/12 · 2022 24/14 · 2023 24/17 |
| 参照値 (ゲート不使用) | ABG-2012 監査後 **40/228 = 17.5%** (pass-1 10-01、同一分母) / 監査前 56/323 = 17.3% (4 CB) |

## 4. 敵対的 3 点検査 (autopilot 規律: knife-edge pass は採用前に必ず通す)

| 検査 | 結果 | 読み |
|---|---|---|
| (1) メカニズム整合 | FOMC 由来語彙 → fed 7 ヒット/文書、boe 6 (英国声明は Fed 語法に近い)、**ecb 1** (ECB 英語版は "price stability" / "accommodative" 等の語法で TERM–MODIFIER が成立しにくい = step 0 §4.2 の OOV 予告どおり) | 密度は**辞書の出自と整合する形で不均一**。pooled 通過は fed/boe が担う。ECB 単独なら ABG-2012 と同水準 (18.3% vs 参照 17.5%) で非 dense |
| (2) クラスタ補正 (CB・年) | CB: 3 中 2 が > 50% / 年: 10 中 **5 年のみ** > 50% 厳密 (2016 / 2017 / 2019 / 2022 / 2023)、2015・2021 は丁度 50%、2014・2018・2020 は < 50% | pooled の 55.7% はクラスタ内で一様でない。ペアの独立性を仮定した Wilson でも下限 0.492 — **点推定の通過は標本雑音の幅の内側** |
| (3) 閾値の OOS 化 | ゲート (> 50% 厳密、τ = 0、ペア規則、スコア式、無ヒット代入) は **2026-09-22 step 0 §7-3 で census 前に固定**、本稿で改変・再選択なし。代替 τ・代替計数規則・代替文境界は実装前に 1 本へ凍結し試行ゼロ | 多重試行による通過ではない。ただし τ = 0 は候補に最も有利な帯 (step 0 が明記) で、τ > 0 では割合は単調に下がる (新 pre-reg の事前差分節の領分、本稿では測らない) |

**総合**: 事前固定ゲートの字義では **通過**。ただし (i) 区間が閾値を跨ぐ、(ii) 通過が 2/3 CB・5/10 年に偏る、の 2 点で「dense primary 確定」ではなく「**dense primary の可能性あり、採否は R1 で**」が正直な読み。

## 5. 帰結と次アクション (執行は本 PR 外)

1. **registry**: `adhoc-scan-29-step1-census-gate` (11-07) → **resolve** (本稿)。新規 `adhoc-scan-29-dense-pass-r1-disposition` (期日 **2026-11-17** = 第7次スキャン `edge-supply-scan-monthly` と同日、`deadline_info`、🔴 user 決裁点 R1): 選択肢 = (a) 新 pre-reg DRAFT を起案 (R1、explore 枠 1 消費、事前差分節で CB 集合・τ・窓・文書種を凍結) / (b) 診断枠のまま保留 (第8次で再裁定) / (c) 候補なしクローズ (knife-edge を理由に)。**無回答 = (b)** (既定、不可逆の作業なし)。
2. **台帳 #29 行** ([[hypothesis-catalog-2026-07-24|台帳]]): step 1 結果を追記 (診断枠のまま、m 非加算、explore 枠非消費)。
3. **ABG-2012 (E23) 側**: 本稿は触らない (E23 記録は凍結)。同一分母 228 での 40 vs 127 は記述として E23 §11 の疎性診断を補強するのみ。
4. **やらないこと**: pre-reg DRAFT の起案 (R1 = user) / 価格結合 / τ > 0 の試算 / WCB・GSV secondary (gated / 任意) / ABG-2012 再実行。

## 6. 正直な caveat

- 「dense」= ゲート定義上の非退化 (ペアの過半でスコアが動く) であり、方向情報の存在 (pass-2 の領分) を一切含意しない。memo Rank 5 の refuted 評価 (N_required 160 vs Wilson 41、7 CB 上限 4.58 event/月、keeper 控除後 −0.03%) は本稿で変わらない。
- 計数規則「TERM 出現 × 窓内 MODIFIER 出現」は WP が明示しない部分を字義で凍結したもの。別規則 (modifier を最近接 TERM に 1 回だけ帰属) でも τ = 0 の「変化 / 無変化」は多くの場合一致するが、同一視はしていない (未測定、測らない)。
- `inflation pressure` は TERM が単数形で完全一致のため、本文の "inflation pressures" は unigram `inflation` 側 (Table 4 第 1 ブロック) の modifier で拾われる。印字どおりの帰結であり、転記側で複数形を足すことはしない。
- WP 381 PDF 自体は repo に置かない (614 KB、再取得可能、sha256 を記録)。辞書の正本は `DICTIONARY` タプル + sha256 pin。
