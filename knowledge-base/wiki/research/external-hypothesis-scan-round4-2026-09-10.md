# 外部仮説スキャン第4次 — family A/B/C 統合裁定 + E23 完遂 + rate-anchor 修復 (2026-09-10)

**位置づけ**: [[../syntheses/edge-development-pipeline-2026-07-18|edge パイプライン]] §4 月次 cadence の第4回 (registry `edge-supply-scan-monthly`、期日 2026-09-18 を **8 日前倒し**)。
**前回**: [[external-hypothesis-scan-2026-07-13]] (E1-E6) / [[external-hypothesis-scan-round2-2026-07-18]] (E7-E19) / [[external-hypothesis-scan-round3-2026-08-14]] (E21-E25 + 四半期棚卸し)。四半期モダリティ棚卸しは第3次で実施済み — **次回は第6次** (今回は非同乗)。

**起動理由 (期日前倒し、rule:R3)**: WIP 原則 §5 追補 (2026-08-14、user 承認)「今日着手できる本数 <1 なら期日を待たず臨時スキャン」。**能動測定ラインは 2026-08-19 (family C 同日 FAIL) 以降ゼロ** — E23 の残 item は SLA waiver で「09-18 と結合処理」と宣言済みであり、期日を待つルール上の理由は無い (反証レビュー確定)。本スキャンは (1) A/B/C 統合裁定、(2) E23 残 item 3 の完遂 (DRAFT → LOCK)、(3) 裁定の到達経路だった rate-anchor-daily の修復、を 1 PR で処理する。

**live への影響: ゼロ。** 本スキャンは live/tier/lot/Kelly/shadow 構成を一切変更しない。イベント×リターン結合統計も一切計算していない (S1-S2 のみ、測定は pre-reg LOCK 後の別タスク)。

---

## 1. データ入手性 re-check (全て本セッション 2026-09-10〜11 JST で一次実測)

| 資産 | 前回記録 | 本日実測 | 判定 |
|---|---|---|---|
| **E1 Myfxbook positioning** | 健全 (13 ペア) | `/api/positioning/status`: verified 13 キー、鮮度 06:58Z (数時間内) | ✅ 健全 — first look 2026-10-15 へ向け評価窓進行中 |
| **E12 CME 先物 1h volume** | 7/7 fresh | `/api/marketdata/status`: verified:cme_bars 7/7 (04:22Z) + ff_calendar (10:18Z) | ✅ 健全 |
| **MASSIVE 15m 12y** | 右端 2026-08-14 | USD_JPY 316,044 行 / EUR_USD 320,205 行、右端 **2026-09-10 13:30Z** | ✅ 健全 |
| **MoF 発言コーパス (family A 基盤)** | daily cron 稼働 | `lexicon_scores.csv` 右端 **2026-09-08** (片山、L1:注視 + **L5:介入を実施** 語句ヒット)、月次 CSV に 07-30..08-26 窓 **15兆3,993億円** 取得済み | ✅ 健全 — forward corpus は観測前確定で蓄積中。⚠️ mof-statements-daily は 09-05〜07 に 3 連続失敗後に自己回復 (観測メモ、恒久損失なし — 日次 union) |
| **intervention-watch (E-A 凍結検知器、family B 入力)** | 00:20 UTC 稼働 | 直近 run 5/5 success (09-08〜09-10) | ✅ 健全 |
| **rate_anchor 日次蓄積 (family C 材料)** | 08-18 設置 | **右端 JGB 08-17 / DGS 08-14 / ZN 日足 08-18 で 23 日間停止 — workflow 17/17 全失敗** | ❌ **構造欠陥 → 本 PR で修復** (§1.1) |
| **ZN=F 1h cache (ws3-round4 conditional の発火材料)** | 週次 workflow 新設済み | repo 右端 **2026-08-18** — zn-cache-refresh も **4/4 全失敗** (rate-anchor-daily と別根因) | ❌ **同時修復** (§1.1) |

### 1.1 rate-anchor-daily 17/17 全失敗の根因と修復 (rule:R3、本 PR で執行済み)

`gh run view --log-failed` で全 17 run を検分した結果、**二重の独立欠陥**が確定した (「zn-cache と同型」仮説は半分だけ正しかった):

1. **FRED WAF 遮断 (17/17 の直接死因)**: `fred.stlouisfed.org/graph/fredgraph.csv` が GitHub Actions runner (Azure IP) から **read timeout=180s で恒常ハング** (08-18 の初回から 09-09 まで全 run 同一 traceback)。ローカルからは同 URL が数秒で 200 (502KB) — IP レンジ起因の WAF 型遮断。**修復**: `tools/rate_anchor_ingest.py` に `home.treasury.gov` 公式 daily par yield curve CSV への fallback を実装 (`fetch_us_yields`)。**値は同一の一次ソース** — FRED DGS* は Treasury par yield curve の再配布であることを 2026-08-14 行の 4 系列一致 (3.98/4.17/4.36/4.68) で実測確認。FRED は 45s timeout の primary のまま (ローカル/歴史 backfill 用)。
2. **git add の ignored-path 拒否 (潜在欠陥、zn-cache-refresh 4/4 の直接死因)**: `data/cache/` は `.gitignore` 対象で、runner の git 2.54+ は **tracked ファイルでも** ignored パスの `git add` を拒否する (`The following paths are ignored ... Use -f`)。zn-cache-refresh は **python step (yfinance 延伸) は毎回成功していたのに commit step が一度も走らず** — 検知器どころか write 経路そのものが write-only だった。rate-anchor-daily は欠陥 1 で先に死んでいたため未発現の地雷。**修復**: 両 workflow を `git add -f` へ。
3. **構造改善**: ingest を per-source 隔離 (1 ソース失敗でも他ソースを蓄積してから終端で loud に raise) + commit step を `if: !cancelled()` 化 (部分進捗の永続化 — union-merge は冪等なので安全)。test pin 6 本追加 (`tests/test_rate_anchor_ingest.py`: Treasury パーサ / fallback / per-source 隔離)。

**損害の会計**: 恒久データ損失は**ゼロ** — JGB/DGS は全歴史を毎回再取得可、ZN 1h は rolling 730d 窓内 (左端は git 保存済み)。損害は「23 日間の蓄積停止」のみで、修復後の初回成功 run が全て自己修復する。

**教訓 (lesson 追記対象)**: (a) **workflow の失敗は誰にも届いていなかった** — 17/17 と 4/4 が 23 日間気付かれなかったのは、GH Actions 失敗を読む「読み手」が存在しないから (write-only 検知器系列の workflow 版)。今回は scan 期日の到達経路検査が読み手の代わりを果たした — これは registry `edge-supply-scan-monthly` に到達経路が明記されていたから機能した (ZN 教訓の設計が正しく働いた稀な例)。(b) **設置 commit の green は運用の green を意味しない** — 初回 scheduled run のログまで見て初めて「設置完了」。

**マージ後 dispatch 検証手順 (PR 本文にも記載)**:
```
gh workflow run rate-anchor-daily.yml
gh run list --workflow=rate-anchor-daily.yml --limit 1   # → success を確認
gh run view <id> --log | grep -E "source=|rows"          # us_treasury source=treasury (CI) / 右端が当日近傍
gh workflow run zn-cache-refresh.yml && gh run list --workflow=zn-cache-refresh.yml --limit 1
git pull 後 data/external/rate_anchor/manifest.json の date_max 前進を確認
```

---

## 2. family A/B/C 統合裁定 (第4次スキャンの本体)

前提 dossier: [[../../raw/analysis/intervention-history-anatomy-2026-08-18|介入全史解剖]] (A/B 用) + [[../analyses/family-c-anchor-automation-2026-08-18|自動化パケット]]。当初構想 (08-18) は「C をアンカー層とする A/B/C 統合設計」だったが、**family C が 08-19 に explore FAIL でクローズしたため統合設計は不成立** — A/B を単独裁定する。

### 2.1 family C (rate-anchor、台帳 #26) — 台帳整合のみ

- ❌ **FAIL 確定済み (2026-08-19、[[../decisions/family-c-rate-anchor-explore-prereg-2026-08-19|pre-reg §11]])** — gross −20.5p / net −24.2p / gate C p=0.527、点推定が負の符号情報を持つ FAIL。台帳 #26 の記載と本スキャンの裁定は**整合** (更新事項なし)。
- クローズ範囲の再確認: 日次国債金利差アンカー帯 × USD_JPY × 帯下 LONG × 5-63bd 全変種。復活経路 = OIS/先物 implied 政策 path 等 (有償) + 新 family — **§4 U4 材料へ接続**。
- **rate-anchor-daily を修復して残す正当化は family C ではない**: (a) ZN 1h 延伸は registry `ws3-round4-eur-divergence-conditional` (閾値 2026-11-15) の**唯一の到達経路** (週次 backstop も死んでいた)、(b) JGB/DGS 日次は keyless の汎用 rates 材料 (将来 family の pass-0 資産)。停止すれば ZN conditional が再び「飾り」に戻る。
- family C §11 の副次所見「**介入型 dip の固有性** (E-C +188p は非介入 dip では再現されない)」は family B 裁定 (§2.3) の一次入力。

### 2.2 family A (MoF 発言ラダー → 介入確率、pre-reg DRAFT 2026-08-19) — **採用 (台帳 #27 登録)**

[[../decisions/family-a-statement-ladder-prereg-2026-08-19|DRAFT]] を C1-C6 (round-2/3 と同一 hard constraints) で統合裁定:

| 制約 | 判定 |
|---|---|
| C1 データ | ✅ 全て in-repo・$0: lexicon v1 (pin `569dbe3f`) スコア 2022-01〜継続 (右端 09-08 実測)、介入ラベル = MoF 公式開示のみ。**forward corpus は git 履歴で改竄不能に日次確定済み** — 収集開始 (08-18) 以降の蓄積が既に 3 週分ある |
| C2 falsified 除外 | ✅ 発言×介入**ラベル**は未測定 estimand。価格を一切使わない = 価格モダリティ 3 周 FAIL の完全外側 |
| C3 非重複 | ✅ #4 (価格シグネチャ→ラベル) と estimand 直交 (DRAFT §7)。E23 (#25) とは**テキスト特徴量が近いが endpoint 直交** (label-facing vs price-facing) — BH 分母は合流しない。両 doc 相互参照で on-record (本節がその会計) |
| C4 摩擦生存 | — 非該当 (トレードしない検出器較正)。価値は family B 回避設計 + T5 型運用判断への較正済み入力 |
| C5 反 curve-fit | ✅ lexicon v1 pin + primary 検出器 1 本 (L≥4 遷移) + パラメータは論拠のみで凍結 (DRAFT §2) — 較正にデータを使わない設計が既に文書化済み |
| C6 revealed-edge | △ 2022/2024/2026 の実介入前エスカレーションは目視所見あり (P-A1 で半クリーンと自己申告済み) |

**裁定 = 採用**。追加根拠 (08-19 DRAFT 起草後の新事実):
1. **月次開示 08-28 で 07-30..08-26 窓に 15.4 兆円の平衡操作が確定** — forward OOS のイベント供給が実際に発生している (Q3 日次開示 ~2026-11-06 が最初の OOS 判定点、DRAFT §6)。
2. 09-08 会見で L5 語句 (「介入を実施」) がヒット — 検出器の forward 素材が観測前確定で貯まっている。
3. 有効 N = 4 episode blocks の explore は**記述級のみ** (DRAFT §5 で凍結済み) — edge 主張はしない。それでも family B と T5 復帰第 2 要件 (現在 15.4 兆円で肯定側材料、認定保留中) の両方が「発言ラダーの FP 率」を必要としており、**較正の需要が実在する**。

**台帳 #27 で登録** (DRAFT 起草時の仮番 #26 は family C が消費済み → #27 に確定)。**explore 枠は未消費** — 消費は敵対的検証 → 凍結コミット時 (DRAFT §8 手続きどおり)。registry `family-a-adversarial-freeze-deadline` (2026-09-24) を併設 — 凍結まで発言×介入ラベルの joint 計算は全面禁止のまま。

### 2.3 family B (MoF 介入イベント → 回避/執行) — **不採用 (park、再裁定条件付き)**

dossier ([[../../raw/analysis/intervention-history-anatomy-2026-08-18|介入全史解剖]]) を同じ C1-C6 で裁定した結果、**explore family として起案可能な形が現時点で存在しない**:

1. **C1 (実行可能性) ❌ — ラベルの時間構造が執行と両立しない**: 介入認定は外部一次情報のみ (本タスクの拘束 + MoF #4 cross-LOCK)。公式ラベルは日次帰属が**四半期開示 (数ヶ月ラグ)** — イベント時点で trade を条件付けるラベルが存在しない。real-time 側の代替 (E-A 検知器) は価格シグネチャであり、これを介入「認定」に使うことは `mof-next-episode-reverdict` の 2026+ 窓 OOS を burn するため**禁止** (registry 明文)。つまり「介入イベント→執行」の estimand は、ラベル規律を守る限り**構造的に組めない**。
2. **C5/power ❌ — explore の砂場が無い**: 円買い介入は 39 日/35 年、episode blocks は 2022 以降で 4。うち 2026-05 エピソードの outcome (+188.1p リトレース) は #4 verdict で**既公表 = peek 済み**。残り 3 blocks で新規検定は起案不能 (family A が「N=4 は記述級」と自己拘束したのと同じ理由で、こちらは記述にすら執行含意を持たせられない)。
3. **方向 prior 不安定**: E-C 符号逆 (介入後 SELL は 2026 で死亡、N=1 エピソード) + family C 副次所見 (リトレースは介入型 dip に固有の可能性) — 「回避 (flat 化)」と「執行 (方向)」の分離は dossier の指摘どおりだが、執行側は上記 1-2 で起案不能、**回避側は edge 供給ではなく運用防御** (それは intervention-watch alert として既に稼働中 — 追撃 48h 集中の知見も alert 文面に反映済みの運用知識)。

**再裁定条件 (park 解除)**: (a) family A explore verdict (較正済み検出器 = ラベルに対する合法な real-time proxy が手に入る唯一の経路)、かつ (b) `mof-next-episode-reverdict` の 1 回限り再判定 (Q3 開示 ~2026-11-06 見込み) の完了。両方が揃った時点で「A 検出器 → B 回避設計」の統合を**新 family として**再裁定する。それまで family B は dossier 資産 (taxonomy / 初撃-追撃区別 / 48h 集中) のまま凍結。台帳には番号を与えず本節を理由付き記録とする。

### 2.4 E23 (#25) — 残 item 3 の完遂 (本 PR)

- **testable form DRAFT 起草済み**: [[../decisions/e23-cb-text-explore-prereg-2026-09-10]] — Apel–Blix Grimaldi (2012) 凍結辞書 primary (`tools/e23_lexicon_apel_grimaldi.py`、**WP 261 原本 PDF を取得し語彙を逐語転記** — 名詞 11 語幹 + hawkish/dovish 各 4 語幹 + unemployment 反転)、ΔNH sign-follow × G4 中銀 × D1+5、two-pass、census gates 付き。敵対的検証 (自己) 10 条は同 doc §7 で全消化。
- **TDW は secondary のまま事前コミット節で保留** (CC BY-NC = user 決裁点、queue ticket の 09-04 追記どおり)。イベント×リターン結合統計は未計算 (S2 規律)。
- **LOCK は別 commit** (規約) — 同 PR 内の後続 commit で凍結 + registry + 台帳 + queue ticket done 移送 + SLA waiver 削除。測定 (pass-0 census 以降) は LOCK 後の別タスク。

---

## 3. 新規/再裁定候補 (E26-E28、round-2/3 と同一 hard constraints)

文献リフレッシュ (直近 18 ヶ月、web 実測 2026-09-10) からの候補生成と裁定:

| # | 仮説 (lens) | C1 データ | C2 falsified 除外 | C3-C6 | 判定 |
|---|---|---|---|---|---|
| **E26** | **介入情報リリース・マイクロ構造** — BoJ 当預残高予想の短資会社経由リークで介入量を市場が推定する経路 (event/flow)。2026-04 の実証研究 (ScienceDirect S1059056026004247) が「日本の再介入期」で情報リリース効果を確認 | ❌ 短資会社ブローカー情報・当預残高予想の歴史系列は無料入手経路なし (BoJ 公表は事後) | — | — | **棄却 (C1)。** 機構知見 (介入翌営業日の当預公表で規模確定) は family B 再裁定時の設計参照として記録のみ |
| **E27** | **CFTC TFF (dealer/asset-manager) positioning 極値/フロー** (positioning) | ✅ CFTC 公表・無料 | ❌ **#16 ban 原文「COT Δ/flow×週次固定ホライズン全変種 (母集団問わず)」に正面衝突** — TFF は同一 report family の母集団違いに過ぎず、#5+#16 の「週次 COT 設計空間は実質全クローズ」が適用される | — | **棄却 (C2、ban 適用)。** 再挑戦経路なし (鏡像恒等 0.93 の実証が母集団非依存の根拠) |
| **E28** | **ML/深層学習 FX 予測の 2025-26 文献群** (arXiv 2606.15058 / 2506.09851 / Frontiers 2025 等、LSTM R²=0.92 型) | ✅ OHLCV | ❌ in-sample R² と shifted-price artifact の家系 — 独立検証文化の不在は round-3 E25 と同型。**OHLCV 内部モダリティは 3 周 FAIL + Mesfin 2026 で閉鎖済み** | — | **棄却 (C2/C3)。** 無料 OHLCV×intraday 同型は起案しない (base rate 4% 教訓の明文遵守) |

**新規採用 = 0。** 能動ライン供給は E23 (LOCK) + family A (#27、凍結待ち) の 2 本で改訂 WIP 原則 (着手可能 ≥1) を充足する。「無料×非隣接×検定可能」の探索空間が実測枯渇に近いという round-3 §3 の結論は今回も変わらない — これが §4 (U4) の存在理由である。

---

## 4. U4 決裁材料: 有償データ / 長ホライズン / 非価格モダリティの feasibility (09-18 上程用)

**前提となる会計**: 当プロジェクトの explore→OOS 生存は **0/17 系統** (base rate 4% [CI 0.7-19.5%])。有償データの購買判断は「1 family 起案の期待値 ≈ 0.04 × (M2/M3 寄与)」で評価すべきで、**データ費用そのものより OOS 窓と敵対的検証工数が希少資源**である。

| 選択肢 | 対象 | 概算コスト | 何を解錠するか | 正直な評価 |
|---|---|---|---|---|
| **(a) Databento CME** | E12 歴史 unlock + E13 (tick volume 12y) 再入場 | ~$200-1,000/月 + 歴史パッケージ従量 | E12 unsigned primary **PASS 時のみ** E13 を新 family/R1 で再入場可 (台帳 #10 註記) | **今買っても何も速くならない**: E12 pre-reg は設計変更・トリガー前倒しを禁止 (first look 2027-02-05 固定)。購買判断は E12 verdict 後が合理的 — **推奨: 2027-02 まで保留** |
| **(b) OTC FX オプション面 (RR/BF/smile)** | E22 復活経路 (「有償 OTC 面 + 新 family + 新敵対的検証のみ」と凍結済み) | Bloomberg/Refinitiv 級 (~$2k+/月) or CME DataMine FX options 歴史 (数百$〜、取引所上場分のみ) | vol モダリティの再開 — ただし E22 の完全 null (IC −0.025, p=0.76) は ATM proxy 上の実測 | risk-reversal (crash 保険価格) は EVZ レベルと別情報だが、**G10 で日次〜週次の系統エッジ主張は文献でも EM 比で弱い** (round-3 E22 権利文言)。**推奨: U1 (mission 実現可能性再決裁) が「継続」に解決した場合の第 1 候補**として条件付き凍結 |
| **(c) OIS/policy-path anchor** | family C 復活経路 (「新 anchor 構成 + 新 family」と凍結済み) | US レグは **$0 で種まき可能**: 既存 CME capture (`CME_BARS_SYMBOLS` env) に ZQ=F/SR3=F を追加するだけで go-forward 蓄積が始まる (yfinance 1h rolling 730d)。JP レグ (OIS/TONA 先物) は無料経路が細い | 「金利**観測**」アンカー (実現金利差でなく期待パス) — family C の敗因 (JPY 増価年に帯ごとリプライス) を期待レジーム変数で条件付けできる可能性 | family C は**点推定が負**の FAIL — 復活の prior は低い。**推奨: $0 の go-forward 種まき (ZQ/SR3 追加) のみ即時可、family 起案は U1 後 + 新敵対的検証必須** |
| **(d) 長ホライズン (週次〜月次キャリー/バリュー β)** | — | $0〜 | — | **edge 供給ではない**: E21 で user 収益の主成分が β (swap 28% + drift 72%、α p=0.32) と確定済み。長ホライズン β は「バラスト」であり月次目標の主経路にならない (無レバ +0.3-0.4%/月)。**推奨: 起案しない** |
| **(e) 非価格モダリティ残余** | テキスト (E23/#27 で着手済み) / 実約定フロー (E12 蓄積中) / positioning (E1 LOCK 走行中) | $0 | — | **非価格の無料モダリティは既に全て走っている** — これが第4次の実測結論。残る非価格は有償 (b)(c) か、公刊凍結モデル系 (WCB as-is 推論 = E23 の復活経路として §6 に凍結済み) |

**U4 上程の要点 (1 段落)**: 現時点で購買推奨はゼロ。理由は (i) ロック済み 4 本 (E1 10-15 / ECG 11-06 / #4 reverdict ~11-06 / E12 2027-02) は**どれも金で前倒しできない** (pre-reg が禁止)、(ii) 新 family 起案の期待値は base rate 4% で拘束され、費用対効果は「無料で白黒」型 (E22/E23 方式) に常に劣後する、(iii) 無料の非価格モダリティがまだ 2 本 (E23/#27) 走り始めたばかり。**再上程条件**: U1 決裁が「継続」+ ロック済みラインのいずれかが verdict 到達 — その時点で (b) → (a) → (c) の優先順で個別 R1 起案。

---

## 5. 裁定サマリと次アクション

**裁定**: family A **採用** (台帳 #27、explore 枠は凍結時消費) / family B **不採用** (park、再裁定条件 = family A verdict + #4 reverdict) / family C 台帳整合確認 (FAIL 不変) / E23 **testable form DRAFT + LOCK** (残 item 3 完遂、LOCK は別 commit) / 新規 E26-E28 **全棄却** / U4 材料 §4 に凍結。

**本 PR で執行済み**: §1.1 rate-anchor-daily + zn-cache-refresh の修復 (二重根因、test pin 6 本) / E23 凍結辞書モジュール + test 8 本 / E23 pre-reg DRAFT→LOCK / 台帳 #25/#27 更新 / queue ticket done 移送 + SLA waiver 削除。

**registry 更新**:
- `edge-supply-scan-monthly`: deadline 2026-09-18 → **2026-10-18** (第5次。四半期棚卸しは第6次に同乗)
- 新規 `family-a-adversarial-freeze-deadline` (2026-09-24) — family A 敵対的検証 + 凍結コミットの執行期日 (T5 型ギャップ防止、凍結まで joint 計算禁止)
- 新規 `e23-explore-verdict-deadline` (2026-09-20、LOCK commit で併設) — pass-0 census 〜 pass-2 verdict の執行期日

**次アクション (優先順)**:
1. E23 pass-0 コーパス取得ハーネス + census (LOCK 後の別タスク、期日 09-20)
2. family A 敵対的検証 → 凍結コミット (期日 09-24) → two-pass 測定
3. マージ後 dispatch 検証 (§1.1 手順) — rate-anchor-daily / zn-cache-refresh の初回 green を実ログで確認するまで「修復完了」と言わない

---

## 参考文献 (本セッションで実在確認、取得日 2026-09-10)

- Apel, M. & M. Blix Grimaldi (2012), "The Information Content of Central Bank Minutes", Sveriges Riksbank WP No. 261 — **原本 PDF 取得・語彙表逐語転記** (archive.riksbank.se)
- Dictionary-based sentiment analysis of monetary policy communication: on the applicability of lexicons — Quality & Quantity (2024), doi:10.1007/s11135-024-01896-9 (ABG 辞書が lexicon 比較で最良分離 = E23 primary 選定の外部根拠)
- Market response to foreign exchange intervention information release: Evidence from Japan's return to active intervention — ScienceDirect S1059056026004247 (2026-04) (E26 の機構源泉、C1 で棄却)
- Tobback, Nardelli & Martens (2017), "Between hawks and doves: measuring central bank communication", ECB WP 2085 (メディア知覚系 = E23 と別系統であることの確認)
- The Making of Hawks and Doves — NBER w23228 (FOMC 反応関数の背景)
- arXiv 2606.15058 / 2506.09851 / Frontiers fams.2025.1654093 (ML-FX 予測群 — E28 棄却の対象実在確認)
- Wikipedia "2026 U.S.–Japan yen intervention" (**参照のみ — 外部一次情報ではない**。介入ラベルには MoF 公式開示以外を使わない)
