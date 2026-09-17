# 外部仮説スキャン第5次 — WIP 会計の訂正 + family A forward コーパス供給の構造修復 (2026-09-17)

**位置づけ**: [[../syntheses/edge-development-pipeline-2026-07-18|edge パイプライン]] §4 月次 cadence の第5回 (registry `edge-supply-scan-monthly`、期日 **2026-09-18** の 1 日前倒し)。
**前回**: [[external-hypothesis-scan-2026-07-13]] (E1-E6) / [[external-hypothesis-scan-round2-2026-07-18]] (E7-E19) / [[external-hypothesis-scan-round3-2026-08-14]] (E21-E25 + 四半期棚卸し) / [[external-hypothesis-scan-round4-2026-09-10]] (family A/B/C 統合裁定 + E23 LOCK + rate-anchor 修復)。
**四半期モダリティ棚卸し**: 第3次で実施済、次回は**第6次に同乗** (第4次で予定、変更なし)。

**live への影響: ゼロ。** live/tier/lot/Kelly/shadow 構成を一切変更しない。イベント×リターンの結合統計も一切計算していない (family A は凍結前のため発言×介入ラベルの joint 計算を含め全面禁止のまま — §2.1 で規律遵守を明記)。

**本スキャンの成果 (先出し)**:
1. 🔴 **WIP 発動会計の誤り訂正 (rule:R3)** — 09-15 の「能動測定ライン = 0 本」は台帳 #27 (family A) を数え落としていた。統治規則 (「今日着手できる本数 ≥1」) 下では臨時スキャン条件は**成立していなかった**。実害はゼロ (期日 09-18 が翌日で、いずれにせよ本スキャンは走る) だが、会計そのものが発動ゲートなので訂正する。**正しい現在値 = 着手可能ライン 1 本 (family A、凍結期日 09-24)**。
2. 🔴 **family A forward コーパスの供給に構造欠陥を発見・修復 (rule:R3、実害を実測)** — `mof-statements-daily` が **8/20 run 失敗 (40%)**、単一根因 = GDELT 429。失敗時に**先行 4 ソースの成果ごと破棄**されていた。**現に 1 文書 (my20260915.html) が repo から欠落**していた (§1.2)。修復 + 欠落分の回収を本 PR で執行。
3. **新規採用 = 0 (3 周連続)** — E29-E31 全棄却 (§3)。free × 非隣接 × 検定可能の空間は実測枯渇のまま。

---

## 1. データ入手性 re-check (全て本セッション 2026-09-17 JST で一次実測)

| 資産 | 前回記録 (第4次) | 本日実測 | 判定 |
|---|---|---|---|
| **E1 Myfxbook positioning** | verified 13 キー、鮮度数時間 | `/api/positioning/status`: 13 ペア `available=true` / `consecutive_failures=0` / stale 1,131-2,424s | ✅ 健全 — first look 2026-10-15 へ向け評価窓進行中 |
| **E12 CME 先物 1h volume** | verified:cme_bars 7/7 | `/api/marketdata/status`: verified 7/7 (09-16T04:37Z)、`cme_fx_bars_1h` latest_bar 09-16T03:00Z、`last_error=""` | ✅ 健全 (stale 閾値 259,200s に対し 82,807s) |
| **MASSIVE 12y キャッシュ** | 右端 2026-09-10 | in-repo parquet 健在 (`{PAIR}_1h/4h`) | ✅ 健全 |
| **MoF 発言コーパス (family A 基盤)** | daily cron 稼働、「09-05〜07 に 3 連続失敗後に自己回復 (恒久損失なし)」 | ❌ **8/20 run 失敗 (40%)・単一根因・実データ欠落 1 件** | ❌ **構造欠陥 → 本 PR で修復 (§1.2)**。前回の「自己回復・恒久損失なし」評価は**楽観に過ぎた** (§1.3) |
| **intervention-watch (E-A 凍結検知器)** | 5/5 success | 直近 4/4 success (09-15〜16、00:20/09:30 UTC 各 2) | ✅ 健全 |
| **rate-anchor-daily (第4次で修復)** | 17/17 全失敗 → 修復 push | **4/4 success** (09-11〜09-16)。`manifest.json`: us_treasury date_max **2026-09-16** / jgb **09-15** / zn_f_daily **09-16** | ✅ **修復を運用実績で確認** — 第4次「次アクション 3」をエビデンス付きでクローズ |
| **zn-cache-refresh (第4次で修復)** | 4/4 全失敗 → 修復 push | **2/2 success** (09-10, 09-14)、修復前の 09-07/08-31 は failure | ✅ 同上。`ws3-round4-eur-divergence-conditional` (閾値 2026-11-15) の到達経路が実際に生きた |

### 1.1 第4次修復の運用検証 (「設置の green ≠ 運用の green」教訓の履行)

第4次 §1.1 は修復を push したが、**次アクション 3「初回 green を実ログで確認するまで修復完了と言わない」を未消化のまま残していた**。本スキャンで消化した:

- `rate-anchor-daily`: 直近 4 run 全 success。`us_treasury_yields.csv` の date_max が **2026-09-16** = Treasury fallback が CI 上で実働している (FRED WAF 遮断は迂回済み)。
- `zn-cache-refresh`: 修復後 2 run 全 success、`zn_f_daily.csv` date_max 2026-09-16 (修復前は 08-18 で凍結)。`git add -f` 修復が効いている。

→ **第4次の 2 修復はいずれも運用実績で確認済み。** 教訓「初回 scheduled run のログまで見て初めて設置完了」は本節で履行した。

### 1.2 `mof-statements-daily` 40% 失敗の根因と実害 (rule:R3、本 PR で執行)

**観測**: 直近 20 run で **success 12 / failure 8**。失敗日 = 09-03, 09-05, 09-06, 09-07, 09-11, 09-12, 09-14, 09-16。

**根因 (単一)**: サンプルした 4 失敗 run (35163419350 / 34910923059 / 34724565983 / 34170641579) の traceback が**全て同一** — `run_gdelt()` → `api.gdeltproject.org` が **HTTP 429** を 4 リトライ全てで返す。
⚠️ 「第4次 FRED と同じ runner IP の WAF 型遮断」仮説は**反証済み**: 本セッションのローカル実行でも同一 429 が再現した (§1.4 の実行ログ) → 環境依存ではなく **GDELT 側の慢性レート制限**。

**欠陥の構造 (2 段重ね、第4次 rate_anchor と同型だが別ツールに残っていた)**:

1. **`tools/mof_statements_daily.py::main()` が dict literal で 5 ソースを直列評価**していた。最後段の GDELT が raise すると、**先に成功していた 4 ソース (interventions / conferences / score / rss) ごとプロセスが落ちる**。
2. **workflow の "Commit data" step に `if:` 条件が無い**ため、collect step 失敗時に**走らない**。runner は ephemeral なので、書き終えたファイルは**ディスクごと消える**。

**実害 (推定ではなく実測)** — 失敗 run 35163419350 (2026-09-16T23:41Z) のログ:

```
[interventions] 386 daily events through 2026-06-30; totals cross-check OK
[daily-conf] months=['202608', '202609'] new=1          ← my20260915.html を取得済み
[score] wrote lexicon_scores.csv: 512 conferences        ← 512 件で採点済み
[daily-rss] fx_items=2 new=1                             ← RSS 新規 1 件
RuntimeError: fetch failed after 4 tries: ...gdeltproject... 429   ← ここで全破棄
```

対して**修復前の repo 実測は 511 conferences** (全 jsonl 行数)。差分 1 = `my20260915.html`。MoF 公式月次インデックス (`202609.html`) を直接叩くと `my20260915.html` が実在するのに、**コーパスには無かった** — 会計が閉じた形で欠落を確認した。

**「恒久損失なし」評価の訂正 (§1.3)**: 第4次は 09-05〜07 の 3 連続失敗を「自己回復、恒久損失なし — 日次 union」と記録した。**union が効く理由は ingest 設計ではなく上流アーカイブの永続性**であり、ソースごとに保証が異なる:

| ソース | 再取得可能性 | 失敗時の恒久損失リスク |
|---|---|---|
| interventions | 公式 CSV を毎回全書き換え | なし (自己修復) |
| conferences | MoF 月次インデックスは恒久アーカイブ。ただし daily driver は **当月+前月のみ**取得 | **回収窓は約 1 ヶ月**。観測最大連続失敗 3 日なので現時点で損失なしだが、余裕は無限ではない |
| score | 全コーパスから再生成 | なし (導出物) |
| **rss** | **MoF news.rss = ローリング窓** | 🔴 **あり** — 失敗中に item が窓から落ちれば恒久損失。上流アーカイブによる救済が構造的に存在しない唯一の経路 |
| gdelt | 全範囲を毎回上書き再取得 | なし (自己修復) |

→ 「日次 union だから安全」は **rss について偽**。今回の欠落 1 件は conferences 側で発覚したが、同じ run で `[daily-rss] new=1` も破棄されている。

**欠落文書の性質 (family A への含意、重要)**: 回収した `my20260915.html` の lexicon スコアは **L 語句ヒット 0 (ladder 言及なし)** だった。family A (#27) の estimand は「発言ラダー → 介入確率」であり、**その検出器の価値は FP 率 (= ラダー非該当日に何も起きないこと) の較正にある**。つまり**失われかけたのは negative sample** であり、negative を落として positive だけ残すのは検出器の precision を機械的に押し上げる方向のバイアスである。凍結 (09-24) 直前に forward コーパスから negative が欠落していたのは、単なるデータ欠損より重い。

**修復 (本 PR)**:
1. `tools/mof_statements_daily.py`: **per-source isolation** — `_STEPS` を明示タプル化し、各ソースを try/except で隔離。**全ソース試行後**に hard 失敗のみ終端で raise。失敗も `summary` に `error` として残す (サイレント欠損の禁止)。
2. **soft / hard のソース分類**: `_SOFT_SOURCES = {"gdelt"}`。GDELT は全範囲を毎回上書き再取得する派生系列なので 1 日の失敗に情報価値がなく、かつ 429 が慢性 (8/20)。hard 扱いを続けると**アラートが 40% の頻度で鳴り、Discord 通知が読まれなくなる** (第4次教訓 (a) 「読み手のいない失敗通知」の再生産)。soft は警告のみ・exit 0。hard (interventions/conferences/score/rss) は従来どおり raise しアラートする。
3. `.github/workflows/mof-statements-daily.yml`: "Commit data" step を **`if: ${{ !cancelled() }}`** 化 — collect が hard 失敗しても部分成果を永続化する (第4次 rate-anchor と同じ処方)。
4. **test pin 4 本** (`tests/test_mof_statements_daily_isolation.py`): soft 失敗は raise しない / hard 失敗は raise する / **raise は全ソース試行後** (後段を道連れにしない) / soft 集合は `{"gdelt"}` に固定 (soft の拡大は「失敗が観測されなくなる」ので pin する)。

### 1.3 欠陥族としての位置づけ (3 例目)

同一の欠陥族が別ツールで 3 度目である:

| # | 対象 | 発見 | 形 |
|---|---|---|---|
| 1 | `zn-cache-refresh` | 2026-09-10 (第4次) | python step は成功、commit step が一度も走らず = write-only |
| 2 | `rate_anchor_ingest` | 2026-09-10 (第4次) | 1 ソース失敗で他ソースを道連れ → per-source 隔離 + `if: !cancelled()` で修復 |
| 3 | **`mof_statements_daily`** | **2026-09-17 (本スキャン)** | **同 #2。第4次は姉妹ツールに横展開しなかった** |

**教訓 (lessons 追記対象)**: **構造欠陥を 1 箇所直したら、同じ形の兄弟を同じ PR で grep すること。** 第4次は `rate_anchor_ingest` を per-source 隔離に直したが、同じ「多ソース直列 ingest + 無条件 commit step」の形を持つ `mof_statements_daily` を検査しなかった。結果、**7 日後に同じ欠陥が実データ欠落として顕在化**した。修復の横展開コストは grep 1 回、放置コストは家族 A 凍結直前の negative sample 欠落だった。

### 1.4 回収の実行記録

修復後の driver をローカル実行 (収集のみ — 価格非接触・joint 計算なし、S2 規律は維持):

```
[daily-conf] months=['202608', '202609'] new=1        ← my20260915.html 回収
[score] wrote lexicon_scores.csv: 512 conferences     ← 511 → 512
[daily-rss] fx_items=2 new=1                          ← RSS 1 件回収
[daily-gdelt] FAILED (soft): ... 429                  ← soft 判定、abort せず
⚠️ soft sources failed (自己修復・アラート対象外): ['gdelt']
```
exit code 0。**4 hard ソースが全て永続化され、GDELT のみ警告**という設計どおりの挙動を行動で確認した。

---

## 2. WIP 会計の訂正 (rule:R3) — 臨時スキャン発動条件は成立していなかった

### 2.1 訂正の内容

[[../decisions/e23-cb-text-explore-prereg-2026-09-10|E23 pre-reg]] §11.4 (2026-09-15) は次のように記録した:

> E23 は park 時点で唯一の能動測定ラインだった。park により**能動測定ライン = 0 本**に戻る (残は時限系のみ: E1 10-15 / ECG 11-06 / E12 2027-02-05)。

**この枚挙は台帳 #27 (family A statement_ladder) を落としている。** #27 は第4次 (09-10) で**採用**され、pre-reg DRAFT §8 の次ステップ (敵対的検証 1 本 → 凍結コミット) は **09-15 時点で着手可能・期日 09-24** の状態にあった。ブロッカーは無い (§8 step 1 の「09-18 scan 裁定」は第4次で前倒し消化済み)。

統治規則は [[../syntheses/edge-development-pipeline-2026-07-18|パイプライン]] §5 追補 (2026-08-14 user 承認) で

> 充足判定は「S1-S4 の本数」ではなく **「今日着手できる本数 ≥1」** で行う

と明文化されている。**「着手できる本数」で数えれば 09-15 時点は 1 本であり、臨時スキャンの発動条件は成立していなかった。**

### 2.2 実害と、それでも訂正する理由

**実害はゼロ**: 期日は翌々日 (09-18) で、本スキャンは前倒しの有無に関わらず走る。焼いた窓も、消費した explore 枠も無い。

それでも訂正するのは、**この会計そのものが発動ゲートだから**である。誤った「0 本」は 2 つの副作用を持つ:
- **緊急度のインフレ** — 「供給ライン全滅」という読み方を KB に残すと、次の判断 (U1 mission 再決裁 / F1 falsification 集計) の入力が歪む。実際は「着手可能な線が 1 本あり、その凍結期日が 7 日後」という平時の状態だった。
- **#27 の不可視化** — 数え落とされた線は催促されない。皮肉なことに、本スキャンが §1.2 で発見した欠陥は**まさにその #27 の forward コーパス供給**の欠陥だった。数えていれば 7 日早く見ていた可能性がある。

これは **phantom blocker / 会計漏れの 2 例目**である (1 例目 = E23 の TDW secondary を「幻のブロッカー」として決裁待ち扱いしていた件、2026-08-18 起票・09-04 に primary 単独で決裁不要と確認)。いずれも「線はあるのに無いことにしていた」型。

### 2.3 訂正後の供給ライン会計 (2026-09-17 現在)

| 分類 | 本数 | 内訳 |
|---|---|---|
| **着手可能 (能動)** | **1** | **#27 family A** — 次ステップ = 敵対的検証 → 凍結コミット、期日 **2026-09-24** (registry `family-a-adversarial-freeze-deadline`) |
| 時限ロック (受動) | 3 | E1 first look 2026-10-15 / ECG #22 2026-11-06 / E12 2027-02-05 |
| 条件付き (受動) | 2 | #4 MoF 次エピソード再判定 (~2026-11-06) / `ws3-round4-eur-divergence-conditional` (cache 2026-11-15) |
| park | 2 | E23 (#25、UNDERPOWERED) / family B (再裁定条件 = A verdict + #4 reverdict) |

→ **WIP 原則は充足 (着手可能 1 ≥ 1)。** 臨時スキャンの再発動条件は「#27 が凍結され測定待ちに移り、かつ他に着手可能な線が無い」時点。

**規律確認**: 本節は #27 の**手続き状態**のみを扱っており、発言×介入ラベルのジョイント量 (hit/FA 率・リード時間・条件付き確率) は一切計算していない。凍結前の joint 計算禁止は継続中。

---

## 3. 新規/再裁定候補 (E29-E31) — round-2/3/4 と同一 hard constraints

文献リフレッシュ (直近 18 ヶ月、web 実測 2026-09-17)。C1 データ入手性 / C2 falsified 除外 / C3 非重複 / C4 摩擦生存 / C5 反 curve-fit / C6 revealed-edge。

| # | 仮説 (lens) | C1 | C2 | C3-C6 | 判定 |
|---|---|---|---|---|---|
| **E29** | **インフレリスク条件付き通貨リターン予測可能性** — 「通貨リターンの予測可能性はインフレリスクの上昇とともに系統的に増大する」(J. Banking & Finance 系 2026, S0927539826000551)。グローバル通貨ボラリスクは米実体活動・不確実性・VIX・センチメントと連動 (regime/conditioning) | ✅ 代理変数は無料 (FRED breakeven/TIPS、VIX) | △ family C (#26、rates anchor) は **水準アンカー**で FAIL、本件は **conditioning 変数**なので estimand は直交 | ❌ **C4 で落ちる** | **棄却 (C4)。** これは「既存シグナルをレジームで条件付ける」型だが、[[../analyses/friction-adjusted-ev-map-2026-07-07|摩擦調整 EV マップ]] が **net+ セルの不在**を確定済み。**条件付けるべき正 EV ホストが母集団に存在しない** — parked 理由「mafe exit 復活 = 正 EV ホスト不在」と同一。ホストが 1 本でも生まれたら再検討可 (条件付き保存) |
| **E30** | **CLS 決済フロー / FX Outstanding データ** — CLS は日次 8.0 兆ドル超を PvP 決済し、市場透明性向上のため FX Outstanding データセットを提供 (真の機関フロー = E1 リテール・E12 先物と別母集団) | ❌ **CLS データは商用製品** (銀行・機関向け販売、無料歴史配布なし) | — | — | **棄却 (C1)。** メカニズムの魅力は高い (母集団独立性が本物) が価格が付いている。§4 U4 の有償候補リストに**条件付きで追加** — ただし優先度は (b) OTC オプション面の下 (CLS は価格未取得、下 3 桁以上の可能性) |
| **E31** | **グラフ学習 / ハイブリッド深層学習 FX 予測** (arXiv 2508.14784 "Graph Learning for FX Rate Prediction and Statistical Arbitrage" / Frontiers Big Data 2026 適応型ハイブリッド) | ✅ OHLCV | ❌ **E28 (第4次棄却) と同型。** OHLCV 内部モダリティは内部 2 周 + 外部 1 周 = **3 周 FAIL + Mesfin 2026 (OHLCV 14 family 全滅) で閉鎖済み** | — | **棄却 (C2/C3)。** 無料 OHLCV×intraday 同型は起案しない (base rate 4% 教訓の明文遵守) |

**新規採用 = 0。3 周連続 (第3次 2/5 → 第4次 0/3 → 第5次 0/3)。**

### 3.1 記録のみ (候補ではないが prior を更新する外部知見)

- **BIS Quarterly Review 2026-03**: 中銀 FX 介入の効果は**概ね 6 ヶ月まで有効、それ以降は不可**。→ family A/B の再裁定時に「介入効果ホライズン」の外部 prior として引用可。当プロジェクトの measurement horizon (D+1〜D+5) はこの窓の**内側**にあり、少なくともホライズン選択は文献と整合している。
- **replication 文献による base rate の外部較正** (McLean–Pontiff 2016: 公表後 58% 減衰 / Hou et al. 2020: 452 アノマリの 65% が単検定不通過、多重補正下 82%)。当プロジェクトの explore→OOS 生存 **0/18 系統 (base rate 4%, CI 0.7-19.5%)** はこれらと**整合的というより、より厳しい**。理由は構造的で正当: 我々の候補は**すでに公表済みの仮説**ばかりで、McLean–Pontiff の「公表後」側の母集団から引いているため。**これは我々の検証設計が厳しすぎる証拠ではなく、母集団選択の必然**である。§4 の含意に接続。

---

## 4. 月次 cadence そのものの費用対効果 (提案 — 執行はしない)

**観測**: 第3次 (08-14) 採用 2 / 第4次 (09-10) 採用 0 / 第5次 (09-17) 採用 0。直近 2 周は**新規供給ゼロ**で、棄却理由は毎回同じ 3 分類 (C1 有償 / C2 既 ban モダリティ / C4 正 EV ホスト不在) に収束している。無料 × 非隣接 × 検定可能の探索空間が実測枯渇しているという第3次 §3 の結論は、以後 2 周の実測で**再現**された。

**提案 (roadmap / user 決裁事項、本 PR では執行しない)**: 月次スキャンを **四半期 + イベント駆動**へ移行する。イベント = (a) ロック済みラインが verdict 到達 (母集団が動く) / (b) 有償だったデータソースの無料化・新 API 出現 / (c) WIP 緊急条件 (着手可能 0 本) の成立。**WIP 緊急トリガは維持**するので「サボり」にはならず、削るのは「毎月同じ 3 理由で棄却する」定型作業のみ。

**本 PR で執行しない理由**: cadence は 2026-08-14 に user 承認された WIP 規律の一部であり、変更は autopilot の R2/R3 権限の外側 (プロセス統治の変更)。**registry の deadline は規定どおり 2026-10-18 (第6次、四半期棚卸し同乗) に更新**し、本節は決裁材料として残す。

---

## 5. 裁定サマリと次アクション

**裁定**: 新規 E29-E31 **全棄却** (C1 / C2 / C4) / **採用 0** / WIP 会計を **訂正 (着手可能 1 本)** / `mof-statements-daily` 構造欠陥を **修復 + 欠落 1 文書を回収** / 第4次の 2 修復を **運用実績で確認しクローズ**。

**本 PR で執行済み**: §1.2 per-source isolation + soft/hard 分類 + commit step `if: !cancelled()` + test pin 4 本 / 欠落文書 `my20260915.html` + RSS 1 件の回収 / §1.1 第4次修復の運用検証 / §2 WIP 会計訂正 / 台帳・registry・lessons 更新。

**registry 更新**:
- `edge-supply-scan-monthly`: deadline 2026-09-18 → **2026-10-18** (第6次、四半期モダリティ棚卸し同乗)。message から「WIP 発動条件成立」の記述を訂正版へ差し替え
- `family-a-adversarial-freeze-deadline` (09-24): **現在唯一の着手可能ライン**であることを message に明記 (催促の可視化)

**次アクション (優先順)**:
1. 🔴 **family A (#27) 敵対的検証 → 凍結コミット (期日 2026-09-24)** — 唯一の着手可能ライン。凍結までは joint 計算禁止を継続
2. `mof-statements-daily` の次回 scheduled run (09-17T21:30Z) が **soft-gdelt で success 終了**することを実ログで確認する (§1.1 と同じ「設置 ≠ 運用」規律。確認まで「修復完了」と言わない)
3. 第6次スキャン (2026-10-18、四半期モダリティ棚卸し同乗) — §4 の cadence 提案を決裁材料として上程

---

## 関連

- [[external-hypothesis-scan-round4-2026-09-10]] (前回)
- [[../decisions/e23-cb-text-explore-prereg-2026-09-10]] (§11.4 の会計を本 doc §2 が訂正)
- [[../decisions/family-a-statement-ladder-prereg-2026-08-19]] (#27、次の着手対象)
- [[../syntheses/hypothesis-catalog-2026-07-24]] (台帳)
- [[../syntheses/edge-development-pipeline-2026-07-18]] (cadence / WIP 原則)
- [[../lessons/lesson-defect-family-sweep-siblings-2026-09-17]] (§1.3 の教訓)
