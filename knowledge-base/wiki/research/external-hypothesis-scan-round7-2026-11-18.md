# 外部仮説スキャン第7次 — 新規採用 0 (4 周連続) / #29 既定 (b) 保留 / ws3-round4 ZN 脚 TRIGGERED・FX 脚未到達 / R5 (12-03) の先行列挙 (2026-11-18)

**位置づけ**: [[../syntheses/edge-development-pipeline-2026-07-18|edge パイプライン]] §4 月次 cadence の第7回 (registry `edge-supply-scan-monthly`、deadline 2026-11-17 = 意図実行日 11-18 の前日規則、11-18 00:20Z TRIGGERED → 当日 autopilot run で実行、遅延 0 日)。
**前回**: [[external-hypothesis-scan-round6-2026-10-20]] (U4 (a)(b)(c) 再評価、#29 step 1 承認、四半期棚卸し) → §9.1 決裁記録 (2026-11-03、cadence 月次維持 / 案 A 採択 / U4-1 (B) decouple / #29-L 解錠)。臨時: [[adhoc-scan-29-step1-census-2026-11-05]] (#29 step 1 = DENSE_PASS knife-edge)。
**四半期モダリティ棚卸し**: 第6次で実施済み、次回は第9次 (2027-01)。本次は同乗しない。
**実施方法**: 調査 4 面 (入手性 / WIP 会計 + R5 先行列挙 / 文献・データ 18 ヶ月 / 期日到来の裁定) を読み、3 レンズ (ban・estimand・P-10 / 費用・feasibility・決裁 / 手続き・規則) の反証を通した (§5)。文献面は WebSearch 4 クエリ (abstract 級) で、一次資料の精読は棄却分類に必要な範囲に限る — 精読を要する候補は 0 本だった。

**live への影響: ゼロ。** live/tier/lot/Kelly/shadow 構成・凍結 pre-reg 本文を一切変更しない。E1 / ECG / E12 / LOCK 中 shadow セルの outcome は一切計算していない (ECG は件数のみ)。

**本スキャンの成果 (先出し)**:
1. **新規採用 (能動 explore LOCK) = 0 本 (4 周連続、第4〜7次)**。新規候補 E32〜E36 + データ源 3 件は全て既存 ban 分類 (C1 有償 3 / C2 既閉鎖モダリティ 2 / C4 正 EV ホスト不在 3、重複あり) で棄却。棄却理由の 3 分類収束 (第5次所見) は 4 周目も不変。
2. **#29 dense PASS の後段裁定 (registry `adhoc-scan-29-dense-pass-r1-disposition`、期日 11-17)**: user の (a)/(b)/(c) 明示なし → **既定 (b) 診断枠のまま保留**を記録して resolve、第8次 (意図 12-18) の議題へ繰り延べ。枠 0/3 → 0/3 (非消費)、価格結合・τ>0・secondary は未実行のまま。
3. **ws3-round4 の ZN 脚が TRIGGERED** (registry data_coverage: 被覆 2026-11-18 > 閾値 11-15、15,563 行)。**FX 脚は未到達** (origin の MASSIVE 1h cache は 13 ペア全て 2026-05-15 終端のまま、repo secret `MASSIVE_API_KEY` 不在、ローカル checkout の 15m cache は 11-06 右端 = 閾値未満かつローカル key 空で停止中)。ZN entry を resolve し、FX 脚を機械評価する後継 entry `ws3-round4-fx-leg-coverage` に置換 (§4-(iii))。
4. **(a-1) FX オプション面 probe の起案条件 (U4-1 (B) 改定後) は不成立** — U1 継続 ✓ / 一回性 probe 上限 (U4-2) **未提示** ✗ → 起案なし (第6次 §9.1 どおり不変)。
5. **family B の再裁定条件 (A verdict + #4 reverdict 両完了) は形式的に成立** (A = FAIL 09-18、#4 = PARTIAL ×2 → family クローズ 11-11) **が、「A 検出器 → B 回避設計」の設計入力が A の FAIL で消失** → park 継続 (番号非付与のまま)。
6. **R5 機械トリガ (`edge-supply-active-line-idle-r5`、12-03) の先行列挙**: 起点 11-03 以降の registry 追加 id 8 件・台帳 commit 4 件は全て verdict / 記録 / readout 系で、**pre-reg DRAFT 起草・explore LOCK・新 family 登録は 0 件** → 12-03 時点で能動 0 本なら「連続空白 30 日」が成立する見込み (判定は 12-03 の registry 側、本稿は列挙のみ)。
7. **データ入手性 re-check で新規の実欠陥 0 件** (第4〜6次は 3 周連続で実欠陥を検出していた)。既知の未処置 1 件 (MASSIVE 1h 停滞) は継続。

---

## 1. データ入手性 re-check (2026-11-18 04:15〜04:25Z 本番 GET / worktree 実読 / gh run list)

| 系統 | 状態 | 出所 |
|---|---|---|
| E1 positioning ingest (13 ペア) | ✅ 13/13 `verified:*:outlook` 04:15:59Z、Myfxbook `logged_in` true / `auth_failure_streak` 0 / `restarts` 1 (11-16 02:48Z = PR #378 deploy)、`last_error` 11-17 02:18Z outlook 503 (単発、以後 142 cycle 継続)。second look cutoff **12-30T06:33:31Z** / verdict 2027-01-06 (registry `e1-second-look-freeze-due` / `e1-prereg-second-look`) | `/api/positioning/status` |
| E12 CME bars (7 契約) | ✅ 7/7 `latest_bar` 2026-11-17T06:00Z (stale 80,519 s < 72 h 宣言基準)、rows 15,647〜15,650。`ff_calendar` は 11-17 14:33Z に 429 (Rate Limited) 1 回 → 11-18 03:13Z verified で回復。first look 2027-02-05 / 陳腐化 review 11-30 | `/api/marketdata/status` |
| ECG #22 forward 窓 (件数のみ、outcome 非計算) | shadow closed (entry ≥ 2026-08-04、`entry_type` 別): session_time_bias EUR_USD **155** / GBP_USD **140**、xs_momentum USD_JPY 33 / GBP_USD 13 / EUR_USD 3、vol_momentum_scalp USD_JPY 10。第6次 (10-20) の 99 / 122 / 13 / 0 から +56 / +18 / 0 / +10 (29 日)。全セル < 150 → second look 2027-01-31 の見込み不変 | `/api/demo/trades?limit=20000` |
| MASSIVE 1h cache (origin) | 🔴 **不変** — 13 ペア全て end 2026-05-15 (EUR_NZD は 05-11、10-22 universe 追加の AUD_CAD / AUD_NZD / NZD_CAD は 08-05)。`gh secret list` に `MASSIVE_API_KEY` なし (ANTHROPIC / DISCORD ×2 / PAT のみ)。ローカル checkout の 15m は EUR_USD / EUR_JPY / USD_JPY とも **2026-11-06 03:15Z** 右端 (ローカル key 空で以後停止、[[../sessions/2026-11-16-session]] 未解決)。origin の 15m は EUR_JPY のみ 07-21 | `data/cache/massive/*_1h.audit.json`、`gh secret list`、ローカル parquet 実読 |
| ZN 脚 (ws3-round4) | ✅ **TRIGGERED** — `data/cache/yield/ZN_F_1h.parquet` 15,563 行、右端 2026-11-18 > 閾値 11-15 (zn-cache-refresh 週次 11-16 16:21Z run)。評価器 = `tools/prereg_trigger_watch.py` data_coverage | registry `ws3-round4-eur-divergence-conditional` |
| mof-statements daily (family 残置材料) | ✅ 11-15 / 11-16 / 11-17 / 11-18 = 4/4 success | `gh run list --workflow mof-statements-daily.yml` |
| intervention-watch (E-A 凍結検知器) | ✅ 直近 4/4 success (11-14 ×2 / 11-17 ×2) | 同上 |
| rate-anchor-daily (family C 残置 / ws3-round4 到達経路) | ✅ 直近 4/4 success (11-13 / 11-14 / 11-17 / 11-18) | 同上 |
| zn-cache-refresh (週次) | ✅ 10-26 / 11-02 / 11-09 / 11-16 = 4/4 success | 同上 |
| kb-rescue-fold (運用、第7次の対象外だが同 PR で readout) | ✅ PR #378 (11-16 02:47Z) 以降 4 run 全て rc 0: 11-16 07:26Z PRESENT 17 / pruned 17、11-16 22:36Z 0、11-17 08:38Z PRESENT 1 / pruned 1、11-17 21:25Z 0。`kb-rescue/*` ref **0 本** | `gh run list` + `git ls-remote` |
| OANDA 口座銘柄 | 68 CURRENCY / METAL 0 (10-22 凍結、不変)。残余 (c) RT 実測は未着手 (§4-(iv)) | [[../analyses/oanda-instrument-universe-2026-10-22]] |

**新規実欠陥 = 0 件**。第4〜6次の「月次 re-check が毎回実欠陥を検出する」という cadence 月次維持の反対材料 (round6 §7) は本次で 1 周途切れた (1 周の観測で結論は変えない、§5)。

## 2. 供給ライン会計 (WIP、2026-11-18 現在) + R5 先行列挙

| 区分 | 本数 | 内訳 (第6次 → 第7次) |
|---|---|---|
| 着手可能 (能動 explore family) | **0** | — (第4〜7次、**4 周連続**新規採用 0) |
| 診断枠 (供給ライン非算入、F1 分子分母外、explore 枠非消費) | 1 | #29 step 1 census **完了 (11-05、DENSE_PASS knife-edge)** → 後段 (b) 保留 (§4-(i)) |
| 時限ロック | 3 | E1 second look (cutoff 12-30 / verdict 2027-01-06、first look 11-06 = UNDERPOWERED) / ECG #22 second look (2027-01-31、first look 11-06 = UNDERPOWERED) / E12 (2027-02-05) |
| 条件付き | **1** (2 → 1) | ws3-round4 EUR divergence (ZN 脚 ✅ 11-18 / FX 脚 ✗)。**MoF #4 reverdict は 11-11 に PARTIAL ×2 → family クローズで消滅** ([[../decisions/mof-intervention-forward-prereg-2026-07-24]] §11.6) |
| park | 1〜2 | E23 #25 (UNDERPOWERED) / family B (番号非付与; 再裁定条件は形式成立、§4-(v) で park 継続) |
| research-only 予約 (枠非消費) | 3 | #30 idx 19 / #31 catalog[55] / #32 catalog[70] (変更なし。E34 を #31 の差分節参照に追記のみ、§3) |

**WIP 下限「着手可能 ≥1」は本次後も未充足** (第5次訂正どおり診断枠・予約・受動 LOCK は数えない)。臨時スキャンの発動規則 (pipeline §3) は不改変 — 本次が月次定例であり、同規則による臨時起動は本次で消費された形になる (次の空白判定は R5 12-03)。

### 2.1 R5 `edge-supply-active-line-idle-r5` (12-03) の先行列挙 — entry 手順 (1) の列挙方法どおり、判定は 12-03

- **registry**: `git log --since=2026-11-03 -p -- prereg-trigger-registry.json` で追加された `"id"` = 8 件: `adhoc-scan-29-dense-pass-r1-disposition` (user 決裁点) / `daily-market-review-abolition-user-decision` (user 決裁点) / `dd-ledger-broker-close-first-booking-readout` (readout) / `e1-prereg-second-look` + `e1-second-look-freeze-due` (受動 LOCK の look 2 分岐) / `ecg-forward-second-look` (同) / `edge-supply-active-line-idle-r5` (本 entry) / `kb-rescue-fold-first-cron-readout` (readout)。**pre-reg DRAFT 起草 / explore LOCK / 新 family 登録 = 0 件**。
- **台帳** (`hypothesis-catalog-2026-07-24.md` の 11-03 以降 commit 4 件): 460bbdd24 (§9.1 決裁記録) / 7d4d7e6de (字義訂正) / d85bb031a (#29 step 1 verdict 行追記) / f5b3315f2 (E1 / ECG first look 記録) / 712023b64 (MoF #4 クローズ) — いずれも verdict・記録行で、起草・LOCK 行なし。
- **期日時点の能動ライン本数の見込み**: 本稿 §2 = 0 本。11-18〜12-03 に起草/LOCK が入らなければ、12-03 run は手順 (3)「供給ライン空白 30 日 (連続、台帳確認済み)」を note に記録し F1 (2027-02-05) の判定材料に積む。本稿は列挙のみで (3) の記録は行わない (期日前)。
- ⚠️ **ws3-round4 DRAFT の起草で空白を「断絶」させてはならない** — R5 estimand は「凍結/敵対的検証の期日を持つ起草済み DRAFT」。FX 脚の到達経路が user 操作待ち (§4-(iii)) で凍結期日を置けない DRAFT は能動ラインに数えない、と本稿で先に宣言する (空白回避のための起草 = 読み手のいない write の再生産)。

## 3. 文献・データスキャン (18 ヶ月、E32〜E36 + データ源 3 件)

| id | 候補 (出所) | モダリティ / ホライズン | ban・分類 | 裁定 |
|---|---|---|---|---|
| **E32** | Kaourma, Milidonis, Nishiotis & Panayides (2025), *News and intraday retail investor order flow in foreign exchange markets*, JIMF 101 — EUR/USD 分単位の retail long/short 集計ポジション、ニュース sentiment のラグが retail 取引を動かし、retail flow の crossover 戦略が利益 = retail flow は uninformed | positioning / intraday | **C1 + C2**: データは broker proprietary (無料経路なし)。モダリティは E1 positioning (🔒 LOCKED 2026-07-17、Myfxbook contrarian) と同一 estimand 域 — E1 LOCK 中に同モダリティの新ラインは起案しない (P-10) | ❌ 棄却。**価値 = E1 prior の外部文献支持** (retail flow uninformed → contrarian)。E1 second look verdict (2027-01-06) の §8 に「先行文献」として引用可 (結果に影響しない記述のみ) |
| **E33** | Domenech Palacios, Ehrmann, Ferrari Minesso, Mehl & Comazzi (2026-05), *Exchange rate communication*, ECB WP 3229 — 高頻度識別で、MP ショック統制後の為替言及の即時効果は限定的・短命 (VoxEU 版: 会見中の為替変動の ~16% を MP/CBI ショックが説明、為替言及の追加説明力は小) | text (中銀) / intraday | **C2 (text 規律 C5 下の負証拠)**: 新ラインではなく、text モダリティ park (#25) / 診断 (#29) に対する**負の外部証拠**。ECB は #29 census でも疎 (ecb 18.3%) で整合 | ❌ 棄却 (記録のみ)。#29 の (a) 起案時に差分節で「EUR 側の為替言及は効果限定 (ECB WP 3229)」を反証材料として併記する要件を台帳 #29 行に追記 |
| **E34** | Filippou, Rapach, Taylor & Zhou (2026-08), *Economic Fundamentals and Short-Run Exchange Rate Prediction: A Machine-Learning Perspective*, JFQA — 国別 characteristics × global state の ML、non-dollar G10、OOS で no-change を上回り金融ストレス期に最大。**反対証拠**: Kılıç (FEDS 2025-089r1、2026-06 改訂) ridge + random Fourier features は random walk に勝てず「構造的」 | fundamentals ML / 月次 | **C4 (帳簿外: 月次保有、swing DISABLED) + #31 同型 (cross-sectional daily+)**。E28 (ML/DL FX 予測 2025-26 文献群、C2/C3 棄却) の後継で、文献が互いに矛盾 | ❌ 棄却。#31 weekly_xs_reversal の research-only 差分節に「E34 / Kılıç の対立」を参照追記 (起動時 blocking の一つ) |
| **E35** | Xu, Kozhan & Taylor (2026-07), *Prospect Theory and Currency Returns*, JFQA — PT 指標の戦略 ≈5%/年、裁定制約下で予測力↑、bank order flow と正相関 | behavioral cross-sectional / 月次 | **C4** (帳簿外) + 価格由来 synthetic 指標 (E25 ban 隣接) | ❌ 棄却 |
| **E36** | Rostamkhani (SSRN 5349012), *Currency Risk Premia and (Many) Fundamentals Connected in the Long-run* — 11 fundamentals の cross-sectional / dollar 分解 | cross-sectional / 長期 | **C4** + E24 ban (3 ヶ月超 horizon) | ❌ 棄却 |
| データ-1 | CME **FX Tape+** (2026、4 order book 統合、DataMine で歴史) | microstructure | **C1** (有償、DataMine = 第6次 (a-1) と同じ価格未取得問題) | ❌ 不採用 |
| データ-2 | Hugging Face `jshriver/forex` (histdata 由来 bid/ask、〜2026-06、license 未確認) | 価格/OHLCV 内部 | **C2** (OHLCV 内部モダリティは第3次で閉鎖) + 既存 MASSIVE 15m で代替可 + license 未確認 | ❌ 不採用 |
| データ-3 | Tick Data OTC FX tick history (2008-05〜、有償) / OneTick Global FX (2008-05〜、trial) | microstructure | **C1** | ❌ 不採用 |

**分類集計**: C1 3 (E32 データ面 / データ-1 / データ-3)、C2 3 (E32 / E33 / データ-2)、C4 3 (E34 / E35 / E36) — 重複あり、**C3 (in-sample R² 家系) の新規出現なし**。第5次「棄却理由は C1 / C2 / C4 に収束」は 4 周目も成立。
**限界 (正直に)**: 検索は WebSearch 4 クエリ (intraday order flow / 中銀 text / 新規データ源 / SSRN cross-sectional) の abstract 級。精読は棄却分類に必要な範囲のみで、E32 の retail データ出所 (broker 名) と E33 の推定窓は未精読 — いずれも分類を変えない (C1 は「無料経路なし」が確認できれば十分、C2 は E1 LOCK が優先)。精読を要する採用候補は 0 本。

## 4. 裁定 7 件

| # | 裁定 | 結論 | Rule | user |
|---|---|---|---|---|
| (i) | #29 dense PASS 後段 (registry `adhoc-scan-29-dense-pass-r1-disposition`、期日 11-17) | user の (a)/(b)/(c) 明示なし → **既定 (b) 診断枠のまま保留**を記録し resolve。第8次 (12-18) の議題に繰り延べ。枠 0/3 → 0/3、価格結合・τ>0・WCB/GSV secondary は未実行のまま。台帳 #29 行に本行と E33 の反証要件を追記 | R3 (記録) | user が後日 (a) または (c) を明示した場合は第8次を待たず別 entry で起票 (autopilot は (a) を起案しない) |
| (ii) | (a-1) FX オプション面 probe の起案可否 (U4-1 (B) 改定後条件) | [U1 継続 ✓ (U1=(b) 09-17)] ∧ [一回性 probe 上限 = **U4-2 未提示 → 不成立**] ∧ [新 family pre-reg + 敵対的検証とセット: DRAFT 未起草] ∧ [explore 枠 空き ✓ 0/3] → **起案なし** (第6次 §9.1 不変)。U4-3 (vendor) は D4 (11-30) 後に再上程 | R1 (起案は user 決裁後) | U4-2 (円 1 数字) |
| (iii) | ws3-round4 (ZN 脚 TRIGGERED 11-18 / FX 脚未到達) | ZN entry `ws3-round4-eur-divergence-conditional` を**条件成立の記録で resolve** し、FX 脚を機械評価する後継 **`ws3-round4-fx-leg-coverage`** (data_coverage、`data/cache/massive/EUR_JPY_1h.parquet`、閾値 2026-11-15) に置換 — 日次 TRIGGERED の常時表示 (読み手のいない催促) を避け、round3 §8 分岐「FX + rates 両方 6 ヶ月延伸」を字義どおり 2 entry で表す。**pre-reg DRAFT は起草可** (データ非接触、round6 §5-(a) の 7 要件: pair 分散 freeze EUR_USD/EUR_JPY 事前登録 / 新 OOS 窓 2026-05-16〜 固定 / EUR_USD N≈19<30 UNDERPOWERED 分岐 / §2c L64 訂正 / gap 処置 / 15m→1h resample bit-exact の infra 条件 (i)〜(iv) / 週次 workflow) だが、**FX 脚の到達経路が user 操作 (repo secret `MASSIVE_API_KEY`) 待ちで凍結期日を持てないため、起草しても R5 の能動ラインに数えない** (§2.1)。起草の優先度は「secret 登録後」に置く | R3 (registry 置換) / R3 (DRAFT 起草は条件付き) | repo secret `MASSIVE_API_KEY` の登録 (1 回、値は Claude が扱わない) — 第6次 §5-(a) と同じ依頼 |
| (iv) | U4-(c) 残余 = 追加 FX ペア 55 本の RT 実測 (R3、第6次 §9.1 で「RT 実測まで進める」) | **未着手を記録**。10-22 の universe 凍結 (①) は済み、② G0 型 RT 実測 (read-only、stressed_RT = p75(spread)+1.0p ≤ 5.0p) と ③ PASS ペアの backfill は未実行。shadow ペア拡張は市場を変えない (base rate prior 不変) ため優先度は本次も低位 — 着手は autopilot の残余 R3 候補 (11-16 session 3 件) と同列 | R3 | — |
| (v) | family B 再裁定条件 (A verdict + #4 reverdict の両完了) | 形式的に成立 (A FAIL 09-18 / #4 PARTIAL ×2 → クローズ 11-11)。しかし再裁定の設計 =「A 検出器 → B 回避設計を新 family として」で、A 検出器は α 規則未達 FAIL (検出力 0.130、2024 年沈黙) = **B の入力が無い** → **park 継続、番号非付与のまま**。再入条件を更新: (α) 新 pre-reg の text 検出器 (#29 (a) が起案・PASS した場合) を A の代替入力にする、または (β) 外部一次情報のみで episode 時点の執行条件付けが可能になる制度変化 (MoF 日次開示の即時化) | R3 (記録) | — |
| (vi) | cadence / 次期日 | 月次維持 (11-03 決裁済み)。第8次 = 意図実行日 **2026-12-18**、registry deadline **12-17** (前日規則)。四半期棚卸しは第9次 (2027-01)。§1 で新規実欠陥 0 は 1 周の観測で、月次維持の反対材料 (3 周連続検出) を覆す根拠にはしない | R3 | — |
| (vii) | 運用 readout の同梱 (第7次の対象外、registry 批准を同 PR にまとめるため) | `kb-rescue-fold-first-cron-readout` (11-21) を **3 日前倒しで resolve**: PR #378 以降 4 run rc 0、prune 17 + 1、`kb-rescue/*` 0 本、人手救出 PR 0 本 (PR #378 の 14 例目同梱は tool fold)。判定の核 (全 ref の畳み + prune) は既に起きた事実で残り 3 日の観測では覆らない。以後の CONFLICT は常設規則 (Discord ⚠️ → autopilot `--in-place`) が扱う / `dd-ledger-broker-close-first-booking-readout` (11-20) は note のみ (`OANDA_SL_TP` 0 件継続、11-09 以降 live fill 0) | R3 (記録) | — |

## 5. 反証記録 (3 レンズ)

| レンズ | 崩れた点 → 訂正 (本文反映済み) |
|---|---|
| ban・estimand・P-10 | E32 を「E1 の補強」と書く際に E1 の outcome・skew 値に触れていないことを確認 (件数すら読んでいない) / E33 は「text に方向情報なし」型の引用禁止 (#25 power caveat) と衝突しないよう「負の外部証拠 (EUR 側、即時効果)」に限定 / ECG census は `entry_type` × `instrument` × closed の件数のみで outcome 列を読んでいない (10-13 教訓: 集計に outcome 列を入れない) / E35 の PT 指標は価格由来 synthetic = E25 隣接を明記 |
| 費用・feasibility・決裁 | 「ローカル 15m が 11-06 まである」= FX 脚到達ではない (閾値 11-15 未満 + ローカル key 空で停止 + round6 (ii) の commit 先条件) → FX 脚 ✗ を維持 / ZN entry を resolve しても round3 §8 の分岐文言 (両脚) は後継 entry の message に字義転記 / kb-rescue 前倒し resolve は「残り観測で判定不変」を明示 (11-12 lesson) / family B 再裁定条件の形式成立を「再裁定可」と書かない (入力消失) |
| 手続き・規則 | 第7次が R5 の空白を DRAFT 起草で断絶させる誘因を §2.1 で先に封じる (estimand 宣言) / #29 既定 (b) の記録は autopilot 権限内 (entry condition「期日到来で既定 (b) を記録して resolve」) で (a) の起案は行わない / 前日規則: 第8次 deadline = 12-17 / 四半期棚卸しを本次に同乗させない (第6次実施、3 回に 1 回) / registry JSON は Render ignoredPaths 外で deploy を起こす → merge は open live 0 の窓で (11-18 04:15Z `last_live_fill_row_at` 11-09、open live 0) |

## 6. registry / KB 変更一覧 (本 PR)

| 対象 | 変更 |
|---|---|
| `edge-supply-scan-monthly` | deadline 11-17 → **12-17**、message に第7次実績追記、note 2026-11-18 |
| `adhoc-scan-29-dense-pass-r1-disposition` | **resolve** (既定 (b)、第8次議題) |
| `ws3-round4-eur-divergence-conditional` | **resolve** (ZN 脚 条件成立 11-18 記録) |
| 🆕 `ws3-round4-fx-leg-coverage` | data_coverage、`data/cache/massive/EUR_JPY_1h.parquet`、閾値 2026-11-15、到達経路 = round6 §5-(a) R3 infra (secret 登録が前提) |
| `kb-rescue-fold-first-cron-readout` | **resolve** (前倒し、§4-(vii)) |
| `dd-ledger-broker-close-first-booking-readout` | note 2026-11-18 (0 件継続、期日不変) |
| 台帳 [[../syntheses/hypothesis-catalog-2026-07-24]] | #29 行に第7次 (b) 記録 + E33 反証要件 / 「scan 第7次 triage」節 (E32〜E36 棄却、family B 再入条件更新、R5 先行列挙) |
| changelog / session log | 2026-11-18 |

## 7. 次アクション (Claude、執行は本 PR 外)

1. **R5 `edge-supply-active-line-idle-r5` (12-03)**: entry 手順 (1)〜(3) を registry 側で実行 (本稿 §2.1 の列挙を 12-03 まで延長して再確認)。
2. **ws3-round4**: repo secret `MASSIVE_API_KEY` 登録後に R3 infra (15m→1h resample、ignoredPaths 内 dir、keep="first" pin、週次 workflow) → FX 脚 TRIGGERED → DRAFT 凍結 + user 通知 → LOCK。secret 未登録の間は後継 entry が WATCHING を示すのみ。
3. **#29**: 第8次 (12-18) で再裁定 (user の (a)/(c) 明示があれば前倒し)。(a) 起案時の差分節要件 = CB 集合 (fed/boe 限定 or pooled)・τ・窓・文書種の事前凍結 + E33 反証材料。
4. **U4-(c) RT 実測** (R3、②③): 残余 R3 候補と同列で autopilot 容量に空きがある run で。
5. **第8次 (12-17)**: §1 入手性 re-check・§2 WIP 会計は現行どおり。D4 (11-30) の返答があれば U4-3 を議題に。

## 関連
- [[external-hypothesis-scan-round6-2026-10-20]] / [[external-hypothesis-scan-round5-2026-09-17]] / [[adhoc-scan-29-step1-census-2026-11-05]] / [[adhoc-scan-29-step0-2026-09-22]]
- [[../syntheses/hypothesis-catalog-2026-07-24]] (台帳: #29 行、scan 第7次 triage) / [[../syntheses/edge-development-pipeline-2026-07-18]] §3-§4
- [[../decisions/ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8 (round-4 条件) / [[../decisions/e1-positioning-contrarian-prereg-2026-07-16]] (E32 の引用先) / [[../decisions/mof-intervention-forward-prereg-2026-07-24]] §11.6 (family クローズ)
- [[../decisions/sprint-1022-process-fixed-cost-upsubmit-2026-11-05]] (kb-rescue readout)
