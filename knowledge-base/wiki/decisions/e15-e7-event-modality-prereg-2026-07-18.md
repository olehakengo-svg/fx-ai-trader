# Pre-registration: イベントモダリティ・プログラム — E15 (FOMC/NFP/CPI イベント窓プレミア/リバーサル) + E7 (指標サプライズ directional) 単一 family (2026-07-18)

**Status**: 🔒 **phase-0 FULL LOCK (凍結 2026-07-22、PR #106) → phase-0 OOS verdict ❌ FAIL 0/6 (2026-07-22、§12)** — phase-1 (E7) は §8 固定分岐どおり予定続行。(旧: 🔓 DESIGN self-LOCK 2026-07-18 — 方法論・窓・grid・凍結規則・判定規則・α 会計を結果観測前に固定。純研究 self-LOCK の根拠 = round-2/3/E1 前例。本文書の変更はレビュー必須 PR のみ。)
**rule**: R1 手続き (新シグナル系統 — pre-reg LOCK が昇格の必要条件)。**純研究 — live/shadow/Kelly/tier 一切不変更**。PASS でも実装は別途 D4 準拠の実装 pre-reg + user 最終承認 (S5、D3 SLA 48h)。
**owner**: claude (autopilot 自走可 — データ in-house + 無料カレンダーで net 到達可)
**pipeline 位置**: [[edge-development-pipeline-2026-07-18]] S1 通過 → **本文書 = S2/S3 統合起案** (S2 診断 = §5a discovery を探索窓のみで実行、S3 = 本 LOCK)。型 B (歴史データあり → discovery→凍結→OOS)。
**関連**: [[external-hypothesis-scan-round2-2026-07-18]] (起案根拠、統合推奨) / [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] (方法論母型) / [[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]] (凍結規則) / [[e1-positioning-contrarian-prereg-2026-07-16]] (event-block 推論・α 会計・市場時間契約の前例) / [[shortest-path-decision-memo-2026-07-10]] D4 / [[roadmap-v2.3-payoff-friction-repair]] トラックB
**タスク票**: `.ai/tasks/queue/20260718-e15-e7-event-phase0.md` (排他 claim)

---

## §0 スコープと方法論上の位置づけ

- **単一 pre-reg family**: E15 (phase-0、無条件イベント窓) と E7 (phase-1、サプライズ条件付き) は同一データモダリティ (US マクロイベントカレンダー × M15 spot) — 別 pre-reg に分割すると multiplicity の二重取りになるため統合する ([[external-hypothesis-scan-round2-2026-07-18]] C5 裁定)。α 会計は §7 で family 横断に固定。
- **設計者ブラインドの宣言**: 本設計時点で観測したのは (a) round-2 スキャンのデータ実在検査 (カレンダー HTTP 200 / EPSOFT 列構成 / FRED endpoint — シグナル×リターンの結合統計は含まない)、(b) 15m cache のカバレッジ範囲 (行数・日付範囲のみ) の 2 点。**イベント×リターンの結合統計は一切計算していない**。discovery 開始まで計算しない。
- **E1 との関係**: 本 family の verdict は E1 (first look 2026-10-15) と独立に、それより先に出す (phase-0 目標 2026-07-31)。E1 FAIL 時の空白期間ゼロ化が本 family の戦略的役割 (WIP 原則)。
- 帰結が何であれ本 verdict は live に触れない。PASS≥1 → S5 実装 pre-reg (user 承認) が唯一の live への経路。

## §1 仮説と文献根拠

**E15-H1 (phase-0)**: 予定された US マクロイベント (FOMC 声明 / NFP / CPI) の後、per-pair の initial reaction (発表後 30–60 分の符号付きリターン R0) に対し、fade (反転) または follow (継続)、あるいは無条件の USD 方向プレミアが、4–24h horizon で**摩擦控除後 EV > 0** に変換できる系統性を持つ。
**E7-H1 (phase-1)**: 指標サプライズ z (= (actual − consensus) / trailing σ) の符号方向 (beat → USD 買い) に、発表後 entry で 1–24h の directional drift が存在し、摩擦控除後 EV > 0 に変換できる。
**H0 (共通)**: 予測性は存在しない、または存在しても摩擦水準 (往復 2.0–4.5p) 未満。

**文献アンカー**:
- **Lee & Wang, RAPS 2025** (実在確認済み、round-2 スキャン) — post-FOMC の initial move は 65% が 12–24h で反転。E15 の fade × FOMC × h12–24 の一次根拠。**同文献のサンプルは ~2023 まで → 本 pre-reg の OOS 窓 (2024-01〜2026-06) は文献 post-sample** — 文献アンカー型仮説で最も重要な「文献自身の standing の OOS 検証」を兼ねる。
- Announcement drift / price discovery 系 (Evans-Lyons ほか) — E7 の sign-follow の一次根拠。イベント後の情報の織り込みは即時完結せず、サプライズ方向に数時間〜1 日の drift。
- 経済機構: イベントは (i) 情報ショック (macro repricing → follow 側)、(ii) ポジショニング/流動性ショック (overshoot → fade 側) の複合。**どちらが勝つかはイベント種×horizon の経験的問題** — 探索窓の discovery が符号を決め、OOS が確認する (型 B の設計理由)。

## §2 falsified 系統・棄却仮説との区別 (再試行禁止の非該当証明)

| 既存の反証/棄却 | 内容 | 本 family との区別 |
|---|---|---|
| **T11 LDN朝×counter-USD MR** (falsified、PR #46) | 固定 clock-time セッション (LDN 朝) 条件付け + counter-USD 方向プール。反証 3 点 = EUR_JPY の USD 露出ゼロ / 擬似反復 / 閾値リーク | 条件付け変数が別 (外生イベントカレンダー時刻 ≠ 固定セッション時刻)。**T11 の教訓を設計に直接反映**: primary 判定は USD-leg 7 ペア block に限定 (§4)、USD 露出ゼロのクロスは記述のみ。ナイフエッジに閾値リーク canary を常設 (§5.8) |
| **WMR month-end fix** ([[melvin-prins-2015]]、REJECT 2026-06-18) | 月末 London fix のエクイティヘッジ・リバランスフロー | イベント種が別 (カレンダー月末 fixing フロー ≠ マクロ情報イベント)。機構も別 (機械的リバランス ≠ 情報/ポジショニングショック)。月末 fix 時刻近傍のイベントは §5.8 ナイフエッジで交絡記録 |
| **E8 pre-announcement drift** (round-2 棄却、C4 構造 FAIL) | 発表**前** 30–120 分の drift 追随 — スプレッド拡大窓と entry が構造衝突 | 本 family は**発表前 entry を構造的に持たない**: E15 entry ≥ t_e + 30m、E7 entry ≥ 発表後次バー open。E8 棄却と完全整合 |
| falsified 6 系統 (H4 level / channel / 水平 sweep&reclaim / mtf SELL / bb_rsi / T11) + 価格モダリティ 3 周 | 無条件 OHLCV 内部・cross-asset 価格構造 | イベントカレンダー + コンセンサス乖離 = **価格外情報の条件付け** ([[external-hypothesis-scan-round2-2026-07-18]] C2 ✅)。Mesfin 2026 (無条件 OHLCV falsification) と非矛盾 |
| tokyo_nakane (現行) | 固定時刻・サプライズ非条件 | 非重複 (round-2 C3 で grep 確認済み) |

## §3 データと estimand

### 3.1 FX 価格 (in-house)

- **MASSIVE 12y OHLCV M15 mid** (本番 signal 関数と同一ソース)。pip 定義: JPY クロス = 0.01、それ以外 = 0.0001。
- **データ準備 (discovery 前必須、round-3 AMENDMENT の教訓を事前構造化)**: ローカル 15m cache はペア間で不均一 (2026-07-18 実測: EUR_USD/GBP_USD = 2014-01〜フル、USD_JPY = 2024-05〜の部分 cache、NZD_JPY = 2025-04〜、EUR_AUD = 未取得)。discovery 開始前に **13 ペア全てをフル歴史で MASSIVE から取得し直し、per-pair floor を凍結台帳 (`raw/bt-results/e15_e7_pair_coverage.json`) に記録**する。
- **coverage gate (機械規則、裁量なし)**: discovery 窓の market-time M15 スロット被覆 < 90% のペアは family から機械除外 (fail-loud 記録)。EUR_AUD が MASSIVE で取得不能なら 12 ペアに機械縮小 (記録のみ、設計変更ではない)。**除外判定はイベント×リターン結合統計の観測前に完了させる**。
- verdict 用データは cutoff で末尾切詰めた parquet を凍結 (部分 parquet 罠 — フル期間版から切詰める。stage-1/2/E1 と同方式)。

### 3.2 イベントカレンダー (無料、価格系列と独立)

| イベント | 日付ソース | 時刻 (固定) | 12y 概算 N |
|---|---|---|---|
| **FOMC 声明** | federalreserve.gov FOMC カレンダー (歴史ページ含む、HTTP 200 確認済み)。**scheduled meeting のみ**、unscheduled/emergency は除外 (件数を記録) | **14:00 ET** (2013 以降固定) | ~96 |
| **NFP** (Employment Situation) | FRED `/fred/release/dates` release_id=50 (無料キー)。fallback = BLS 公式年次スケジュールページ | **08:30 ET** | ~144 |
| **CPI** | 同上 release_id=10 | **08:30 ET** | ~144 |

- **ET→UTC は America/New_York の per-date 変換 (DST 追随)** — 固定 UTC オフセットは spec バグ (E1 レビュー M11 の教訓)。14:00 ET / 08:30 ET はいずれも M15 バー境界に整列する。
- **カレンダー sanity (判定不使用の検出器)**: 各イベントについて event bar (t_e に開く M15 バー) の realized range が「直前 20 営業日の同時刻バー range 中央値」の 2 倍未満なら時刻誤り疑いフラグ (>5% で discovery 停止・カレンダー再検証)。時刻の後付け修正は**破損確認できた行のみ** (E1 jump detector と同じ規律)。
- 同日複衝突 (例: CPI と FOMC が同日): 各イベントは独立に扱い、**collision フラグ**を記録 (horizon 窓内に他イベント発表を含むトレード)。除外しない (裁量トリム回避) — ナイフエッジ #4 で collision 除外 EV の符号を検査。

#### §3.2b AMENDMENT (2026-07-21、結果観測前 data-availability — round-3 前例準拠)

**種別**: データソースの取得経路代替のみ。**grid / 窓 / 判定規則 / 凍結規則 / イベント種 / 時刻規約は一切不変更**。本追記時点でイベント×リターンの結合統計は一切未計算 (§10-1 遵守下)。

1. **FRED 経路の不能確定**: `FRED_API_KEY` は env 不在・self-provision 不能 (2026-07-20/21 runbook `e15_phase0_execution_status.md` に記録)。FRED 公開ページも本環境から 403。
2. **NFP**: §3.2 表に **pre-registered 済みの fallback「BLS 公式スケジュールページ」を発動**する。**CPI**: 表の「同上」は「FRED release_id=10 + 同型 fallback (BLS 公式ページ)」と読む — 本 AMENDMENT で明確化。
3. **アクセス経路**: BLS 直接アクセスは本環境から 403 のため、**Wayback Machine snapshot (web.archive.org、`id_` raw モード) 経由で BLS 一次ページを取得**する。使用 snapshot の URL・timestamp・sha256 はカレンダー JSON の source ledger に凍結する。
4. **一次記録の格上げ**: BLS News Release Archive ページ (`bls.gov/bls/news-release/{empsit,cpi}.htm`) のアーカイブ済み発表ファイル名 `{empsit,cpi}_MMDDYYYY` は **actual release date の一次記録** (計画表ではなく発表実績) であり、アンカーテキストが reference month を与える。スケジュール計画ページより強い記録として主ソースに用いる。
5. **ソース非依存性**: 発表日は客観的事実であり、FRED release/dates と BLS 一次ページは同一事実の別記録。ソース差はイベント×リターン統計に自由度を与えない。
6. **FOMC**: 変更なし (federalreserve.gov 直接 HTTP 200)。歴史ページ (2014-2020) の年別書式は構造パース (panel 見出しの `(unscheduled)`/`(cancelled)`/`(notation vote)` マーカー分類 + statement URL 日付と会合日レンジの突合) で処理し、scheduled meeting のみ採用・除外は件数と日付を記録する (§3.2 本文どおり)。
7. **カレンダー sanity の運用明確化**: §3.2 の range-based 検出器は discovery 時に **explore 窓イベントのみ**に対して実行する。OOS 窓イベントの sanity は verdict 実行時に行う (§10-1 の中間 peeking 禁止を優先する運用解釈であり、検出器の定義・閾値は不変)。

### 3.3 E7 サプライズデータ (phase-1)

- **歴史パネル**: EPSOFT CSV 19y 分単位 (forecast/actual/previous、〜2023-03。列構成は round-2 スキャンで実取得確認済み)。
- **gap**: 2023-04〜現在 ~170 週は ForexFactory 一括 scrape (一回きり工数、round-2 infra #1 に含む)。go-forward の Actual 補完 ingest job は infra 側タスク (本 pre-reg の判定には歴史側 + gap 一括で足りる)。
- **phase-1 データ付録 (観測前凍結の手続きを今宣言)**: 対象系列の正確な指定 (NFP headline = Non-Farm Employment Change / CPI headline m/m、consensus 列の意味論 = 発表前時点の値であることの検証、単位・改定の扱い) は、**イベント×リターン結合統計を一切計算する前に**「phase-1 データ付録」として本文書へ追記コミットし凍結する (round-3 AMENDMENT と同じ「観測前 data-driven 確定」の手続き化)。forecast 列に発表後情報が混入していないことの検証 (公表アーカイブとの spot 突合 ≥10 件) を付録の必須項目とする。
- FOMC の rate surprise は非ゼロ標本が僅少 (well-telegraphed) のため **E7 の判定対象外・記述のみ**。

### 3.4 窓 (calendar 固定、phase 共通)

- **discovery 窓**: per-pair floor (≥2014-01) 〜 **2023-12-31**
- **OOS 窓**: **2024-01-01 〜 2026-06-30** (イベント t_e 基準で帰属。horizon 完結が cache 末尾を超えるイベントは不算入 = censoring、事後裁量処理の構造排除)
- OOS 概算イベント数: FOMC ~20 / NFP ~30 / CPI ~30。
- **窓消費の宣言**: OOS 窓 2024-01-01〜2026-06-30 を**イベントモダリティ family (E15+E7) で消費**。過去 family の窓消費 (round-1/2 の OOS-1、round-3 の 2025-07〜2026-05) とは signal family が異なるため独立に有効。本 family の再検定は 2026-06-30 超の新データが必要 (§8 UNDERPOWERED 分岐)。
- **Lee & Wang post-sample 性**: OOS 窓は文献サンプル (~2023) の後 → 文献アンカーの選択バイアス (文献自身が歴史で「発見」された) に対する追加防御。

### 3.5 執行 estimand (E1/round-2 と同一の契約)

- entry = 指定バーの **open** (mid)。前方リターン終端 = 指定 horizon バーの **open** (E1 §2.3 と同一の一意化)。
- **horizon は market-time bar count** (h4=16 / h12=48 / h24=96 bars。週末ギャップは経過時間に数えず、ギャップ自体はリターンに含める — 現実の保有と同じ。NFP 金曜 entry の h24 は週末を跨ぐ: **除外せず週末跨ぎフラグを記録し Secondary で層別** — E1 前例)。
- **first-touch レグ**: TP = SL = 1.0 × σ_h (σ_h = ATR14d × √(h/24h)、ATR14d = t より厳密に前に完結した直近 14 本の daily bar (NY 17:00 roll、M15 から構築 — E1 §2.3 定義) の TR 平均)。同一バー内 TP+SL 両ヒットは **SL 優先** (ハウス保守規約)。timeout = h (open 決済)。構成は horizon 毎 1 点のみ・grid なし (barrier 幾何の自由度は実装 pre-reg へ温存)。
- **摩擦 (判定値、往復 pips、E1 §3.4 の凍結テーブルを再利用 — 今固定)**: USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50 / GBP_JPY 4.50 / AUD_JPY 3.125 / EUR_GBP 3.00 / AUD_USD 2.50 / NZD_USD 3.00 / USD_CAD 3.00 / USD_CHF 3.00 / NZD_JPY 4.50 / EUR_AUD 4.50
- **stress レグ (PASS 必須の点条件)**: 摩擦 = max(判定値 × 1.25, 判定値 + 1.0p) でも pooled net EV 点推定 > 0。**イベント時スプレッドの追加ストレス**: entry バーの摩擦のみさらに +50% した EV 点推定 > 0 も併記必須 (イベント窓の実効スプレッドは平常値より広い可能性の保守検査 — E15 entry は t_e+30m 以降でスプレッド収縮後だが、実測なしに平常値を信じない)。
- BE/Trail は関与しない (forward scan、round-1/2/3 と同一)。

## §4 ペア族 (T11 教訓の構造反映)

- **Primary block = USD-leg 7 ペア**: USD_JPY, EUR_USD, GBP_USD, AUD_USD, NZD_USD, USD_CAD, USD_CHF。US マクロイベントの機構が直接通るペアのみで判定する (T11 の「EUR_JPY は USD 露出ゼロ」反証の構造的排除)。
- **Cross block = 6 ペア**: EUR_JPY, GBP_JPY, AUD_JPY, NZD_JPY, EUR_GBP, EUR_AUD — **confirmatory/記述のみ、判定に不使用**。役割 = PASS 候補 combo の out-of-block 複製記録 (fade/follow は pair-local R0 なのでクロスにも定義される; uncond-USD はクロスに定義されない)。
- 判定単位は **combo (pooled over primary block)** — 同一イベントに全ペアが同時に発火するためクロスペア相関が構造的に大きく、per-cell (pair 単位) 判定は実効独立数を偽る。per-pair は Stage B 記述に限定 (E1 の階層ゲートキーパーと同型)。ペア選抜の自由度は実装 pre-reg へ温存。
- 方向規約: fade/follow = per-pair R0 の符号に対する操作 (換算不要)。uncond / E7 sign-follow = **USD 軸**で定義し per-pair の USD leg 向きに機械変換 (USD_JPY BUY = USD long、EUR_USD SELL = USD long)。

## §5 E15 phase-0 設計

### 5a. discovery diagnostic (探索窓のみ、= pipeline S2)

- **初期反応**: P0 = t_e に開く M15 バーの open。R0(W0) = close(t_e + W0 に終わるバー) − P0、W0 ∈ {30m, 60m}。
- **ルール 4 種**: fade = −sign(R0) / follow = +sign(R0) / uncond-USD-long / uncond-USD-short (uncond は R0 非依存、entry タイミングは W0=30m に固定)。
- **entry**: t_e + W0 の直後の M15 バー open。**発表前 entry なし** (§2 E8 整合)。|R0| の最小値フィルタは置かない (自由パラメータ増殖の禁止 — ATR 正規化 |R0| 層別は Secondary 記述のみ)。
- **exit**: time-exit h ∈ {4h, 12h, 24h} (primary) + first-touch レグ (§3.5) 併記。
- **combo 空間 (これが検定 family、pair 単位に展開しない)**: fade/follow 系 = 3 event × 2 rule × 2 W0 × 3 h = 36。uncond 系 = 3 event × 2 dir × 3 h = 18。**計 54 combo**。
- 各 combo で primary block pooled の time-exit 摩擦調整 EV / first-touch EV / event-block 数 / fold 別 EV を計測。

### 5b. 選抜と凍結 (self-LOCK → 🔒。凍結規則は raw EV 単独ランクを使わない)

- **選抜規則 (全て充足)**: (i) 探索窓 pooled time-exit 摩擦調整 EV > 0、(ii) **first-touch EV > 0** (sequencing 反転の探索段排除 — round-2 §2(ii)/stage-2 教訓)、(iii) pooled trade N ≥ 60 ∧ event blocks ≥ 40、(iv) **fold 安定性**: 探索窓を時系列 3 等分し time-exit EV の符号一致 ≥ 2/3。
- **凍結規則 ([[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]] 準拠)**: 通過 combo を (1) fold 符号一致数 (3/3 > 2/3)、(2) **EV-per-vol** (pooled net 平均 / per-trade SD — regime-amplified な絶対 EV でなくリスク調整後)、(3) イベント種分散 (**各 event type ≤ 3**) の辞書式順で選抜し **m₀ ≤ 8** を凍結。fade と follow は同一 (event, W0, h) の鏡像 — 両方通過した場合は EV-per-vol 上位のみ (重複排除)。
- 凍結時に本 §5b へ候補表 (combo / 探索 EV_te / EV_ft / blocks / fold) を追記コミット = **🔒 full LOCK**。以後 combo/grid/窓/判定の変更禁止。`raw/bt-results/e15_frozen_candidates.json` に凍結。

#### §5b 凍結表 (🔒 2026-07-22 — discovery PR #106 の `e15_frozen_candidates.json` の転記。m₀=6: FOMC 3 / CPI 3 / NFP 0)

本表は commit e21ea5ff (PR #106、OOS 接触前) で凍結済みの JSON の忠実な転記 (verdict 実行前・2026-07-22 に手続き補完として追記 — §5b 明文の「候補表追記コミット = 🔒」の履行)。

| # | combo (event/rule/W0/h) | 探索 EV_te | EV_ft | N | blocks | fold 符号 | EV-per-vol |
|---|---|---|---|---|---|---|---|
| 1 | FOMC / follow / 60m / h12 | +5.99 | +6.04 | 544 | 79 | +,+,+ (3/3) | 0.1362 |
| 2 | FOMC / follow / 30m / h12 | +3.75 | +3.62 | 545 | 79 | +,−,+ (2/3) | 0.0701 |
| 3 | CPI / fade / 30m / h12 | +2.05 | +2.21 | 804 | 117 | +,+,− (2/3) | 0.0411 |
| 4 | FOMC / follow / 60m / h24 | +2.99 | +3.21 | 544 | 79 | +,−,+ (2/3) | 0.0379 |
| 5 | CPI / fade / 60m / h12 | +1.43 | +0.83 | 804 | 117 | +,+,− (2/3) | 0.0299 |
| 6 | CPI / fade / 30m / h24 | +1.30 | +3.58 | 804 | 117 | +,+,− (2/3) | 0.0178 |

### 5c. OOS verdict (LOCK 後、2 レグ + ナイフエッジ)

- **レグ A (方向性、event-block 推論)**: pooled per-trade net return (ATR14d 正規化 — ペア間スケール混在防止。経済条件は raw pips) の **イベント日ブロック bootstrap** (event block = 同一イベントの全ペア・トレードを 1 ブロックとして resample、B=10,000、seed 固定) 片側 p_boot、**併設 Ibragimov–Müller 型検定** (event-block 毎の平均 net return に対する片側 1 標本 t、df = blocks − 1 — OOS blocks 20–30 は bootstrap 単独では反保守になり得るため。E1 §4.1 M10 と同じ処置)。combo p = **max(p_boot, p_IM)**。判定: **BH-FDR q = 0.05 (m = m₀)**。
- **レグ B (経済性、全て充足)**: (a) OOS pooled time-exit 摩擦調整 EV > 0、(b) first-touch レグ点推定 > 0 (**time-exit のみ正で first-touch ≤ 0 は「sequencing 反転」として REJECT 側** — stage-2 lfr の実証パターン)、(c) stress レグ 2 種 (§3.5) 点推定 > 0、(d) OOS pooled N ≥ 30 ∧ event blocks ≥ 15。
- **ナイフエッジ 4 点 (PASS 必須)**:
  1. **fold 集中**: OOS を年次 fold (2024 / 2025 / 2026H1) に分割、最良 fold 除外の残り pooled EV 符号維持 (LOFO)。
  2. **孤立格子点**: 隣接 combo (同 event×rule で W0 または h が隣) のうち ≥1 の OOS 点 EV > 0。
  3. **閾値リーク / 遅延 canary** (T11 反証第 3 点の常設化): 未来リターンを R0 / ATR 経路に注入した canary をエンジンが検出すること (unit test pin) + entry を +1 M15 バー遅延させた pooled EV の符号維持。
  4. **集中度**: (i) leave-one-pair-out 全 7 通りで pooled EV 符号維持、(ii) トップ 1 event block の寄与 ≤ 40% ∧ 除外後符号維持、(iii) collision フラグ付きトレード除外後の符号維持 (月末 fix 近傍・複数イベント同日の交絡検査、§3.2)。

## §6 E7 phase-1 設計 (combo 級で今固定、系列詳細は §3.3 データ付録で観測前凍結)

- **サプライズ z**: z = (actual − consensus) / σ_trailing (σ_trailing = 当該指標の直近 24 releases のサプライズ標本 SD、strictly trailing、当該 release 自身を含まない)。
- **対象指標**: NFP headline / CPI headline の 2 系列 (core・改定値は Secondary 記述のみ。FOMC rate surprise は記述のみ、§3.3)。
- **ルール**: sign-follow — z > +θ → USD long、z < −θ → USD short (per-pair 変換は §4)。θ ∈ {0.5, 1.0}。|z| ≤ θ は no-trade。**fade 側は grid に入れない** (E7 の文献根拠は drift 側のみ — 符号を観測前に固定。逆符号が有意なら SIGN-FLIP フラグで記録、追うなら新規 pre-reg — E1 前例)。
- **entry**: t_e 後の {+1, +2} 本目の M15 バー open (発表後 ≈0–15 分 / 15–30 分 — スプレッド収縮 30s–2min 後で死圏外、round-2 C4)。
- **exit**: time-exit h ∈ {1h, 4h, 24h} + first-touch レグ (§3.5)。
- **combo 空間**: 2 指標 × 2 θ × 2 entry × 3 h = **24 combo**。
- **選抜・凍結・OOS 判定**: §5b/§5c と完全同一の規則 (**m₁ ≤ 8**、BH q = 0.05 (m = m₁)、event-block 推論、ナイフエッジ 4 点)。凍結表は本 §6 に追記コミット。
- **禁止**: phase-0 で FAIL した unconditional combo を phase-1 の結果で「復活」と主張すること (estimand が別 — サプライズ条件付けは部分集合の別仮説であり、phase-0 の棄却を覆さない。逆も同じ)。

## §7 α 会計 (family 横断、今固定)

- **family FDR ≤ q₀ + q₁ = 0.05 + 0.05 = 0.10** = house 標準 q=0.10 と同水準 (E1 の 2-look 分割と同型の位相分割)。
- phase-0 と phase-1 は候補集合が交わらない (無条件 vs サプライズ条件付き) ため BH は phase 内で独立に適用可。phase の追加・grid 拡張・第 3 の位相は本 pre-reg 下で禁止。
- 探索窓 EV は選抜にのみ使用 (選択バイアス込み)。確認的根拠は OOS 側のみ。OOS での grid 再アンカー・horizon 選び直し禁止 (round-2/3 と同一規律)。

## §8 verdict 分岐 (事前固定)

**combo 分類 (排他、この順)**: C1 PASS (レグ A+B+ナイフエッジ全充足) / C2 sequencing 反転 (REJECT 側) / C3 UNDERPOWERED 適格 (点推定が機構整合 (time-exit>0 ∧ first-touch>0) ∧ N または blocks 不足 (レグ B(d) 不達) — **FOMC 系 combo は OOS blocks ~20 でここに落ちる構造的可能性が高い、§9**) / C4 REJECT-F (レグ A 通過 ∧ EV ≤ 0) / C5 REJECT。

**phase / 全体分岐**:
- **phase-0 PASS ≥ 1** → D4 準拠の実装 pre-reg 起案 + user 最終承認 (S5)。phase-1 は α 予算どおり継続 (併走)。
- **phase-0 PASS = 0** → **phase-1 は予定どおり実行** (無条件仮説の FAIL はサプライズ条件付き仮説を falsify しない — 今宣言)。
- **両 phase PASS = 0** → イベントモダリティ (カレンダー/サプライズ × M15 spot) を枯渇と判定し、**E12 (CME 先物実約定 volume flow) を供給ライン主候補へ格上げ**、E9 probe は予定どおり ([[external-hypothesis-scan-round2-2026-07-18]] の並走設計)。
- **UNDERPOWERED (∃C3 ∧ C1 ゼロ)**: cache が **2027-07-01 以降へ延伸**した時点で、C3 combo のみ・同一 spec・1 回限りの再判定 (BH m = |C3|、q は §7 の当該 phase 予算内で消化済みのため再判定は q=0.05 の新規予算を family 外で明示計上 — registry 条件付きエントリ、round-4 と同型)。
- **DEFERRED**: coverage gate で primary block が 5 ペア未満に縮小、またはカレンダー sanity >5% — user 裁定 (勝手に解釈しない)。

> **✅ 発動分岐 (phase-0、2026-07-22 執行)**: **phase-0 PASS = 0 (全 6 候補 C5 REJECT) → FAIL** — 「phase-1 は予定どおり実行」の分岐に着地。C3 該当ゼロのため UNDERPOWERED 再判定エントリは不発。判定表・全統計は §12。

## §9 power の正直な開示

- **実効独立単位 = event blocks であり trades ではない** (同一イベントに primary 7 ペアが同時発火 — pooled N はブロック内相関で見かけより小さい)。OOS blocks: FOMC ~20 / NFP ~30 / CPI ~30。イベント合算 combo は grid に無い (event type は combo の一部) ため、**FOMC 系 combo の first look は「符号スクリーン + 大効果検出」の役割に限定される** — modal outcome は C3 (UNDERPOWERED) と今予想し記録する (結果を見た後の言い訳の封鎖、E1 §5 と同じ規律)。
- 効果量の目安: per-event net return の SD ≈ σ_h 級 (イベント日はそれ以上)。blocks=20 で 80% power (片側 5%) の検出可能平均効果 ≈ 0.58σ/√20 × 2.5 ≈ **0.33σ_h 級** — h24 で daily ATR の 1/3 (主要ペア 20–35p) 級の大効果のみ。blocks=30 (NFP/CPI) で ≈ 0.27σ_h。**文献の「65% が反転」は方向頻度の主張であり EV の主張ではない** — 頻度優位が摩擦控除後 EV に変換されない可能性 (C4 REJECT-F) は分岐に織り込み済み。
- discovery 側は blocks 76–114/event type で選抜には十分。

## §10 禁止事項 (LOCK〜verdict 間、違反 = 当該 verdict 無効 + lessons ページ)

1. **中間 peeking 禁止**: OOS 窓のイベント×リターン結合統計の計算・目視は verdict 実行まで禁止。discovery は探索窓のみ (§3.4)。
2. **定義変更禁止**: イベント種/時刻規約/W0/rule/θ/entry/h grid/barrier 構成/摩擦判定値/pair block/窓/凍結規則/判定規則。凍結後の候補変更・OOS 再アンカー・horizon 選び直し。
3. **裁量除外禁止**: coverage gate・カレンダー sanity・censoring 以外のイベント/トレード除外 (collision・週末跨ぎはフラグ記録のみ、除外しない)。
4. **事後再分析の引用禁止**: §5c/§6 に事前列挙されていない切り口の事後計算を確認的に引用すること (exploratory 明記のみ可)。
5. **phase 間ロンダリング禁止**: §6 末尾のとおり。
6. 判定器は LOCK 後・verdict 前に実装し、canary/leak/join 契約を `tests/` に pin してから verdict データに触れる (E1 前例)。ハーネスは合成データで dry-run、実 OOS データへの初適用は verdict 実行時。

## §11 期日・registry・成果物

| イベント | 期日 | registry |
|---|---|---|
| phase-0: データ準備 + discovery + 候補凍結 (🔒) | **2026-07-24** | `e15-e7-event-prereg-phase0-verdict` が包含監視 |
| **phase-0 OOS verdict** | **2026-07-31** | 同上 (deadline_info) |
| phase-1: FF gap scrape + データ付録凍結 | **2026-08-14** | `e15-e7-event-prereg-phase1-verdict` が包含監視 |
| phase-1: discovery + 候補凍結 (🔒) | **2026-08-21** | 同上 |
| **phase-1 OOS verdict** | **2026-08-28** | 同上 (deadline_info) |

- **成果物**: 探索ハーネス `tools/event_modality_explore.py` / 判定器 `tools/event_modality_oos_verdict.py` (--extract/--sim 分離、seed 固定、test pin 先行) / イベントカレンダー `raw/bt-results/e15_e7_event_calendar.json` (ソース URL・取得日・sanity 結果込み) / 凍結候補 + 全統計 JSON を `raw/bt-results/e15_e7_*.{json,md}` / verdict は本文書 §12 (phase-0) / §13 (phase-1) へ追記 + session log + pipeline 状態表更新。
- E1 (2026-10-15) との排他: 本 family の全成果物・登記は E1 判定に接触しない (別データ・別 family)。
- FF Actual 補完 ingest job (go-forward) は round-2 infra #1 の別 R3 タスク — 本 pre-reg の判定は歴史側 + gap 一括 scrape で完結する。

---

## §12 phase-0 OOS verdict — ❌ **FAIL (PASS 0/6、全候補 C5 REJECT)** (2026-07-22 執行、期日 07-31 の 9 日前倒し)

**rule:R1 手続き (pre-reg 執行、判定は機械)。純研究 — live/shadow/Kelly/tier 不変更。**
判定器: `tools/event_modality_oos_verdict.py` (extract/verdict 分離、seed=20260718 固定、B=10,000)。
artifact (全統計 + trade/event list): `raw/bt-results/e15_phase0_oos_verdict.json` (+ 抽出中間 `e15_phase0_oos_trades.json`)。
test pin 先行 (§10-6): `tests/test_event_modality_oos_verdict.py` 26 pins (判定分岐 C1–C5 / BH-FDR m 固定 / bootstrap seed 決定論 / IM df / ナイフエッジ / canary 検出能力 / OOS 窓ガード / 摩擦式 / join 契約) — **全て green を確認してから OOS データに接触**。

### 判定表 (§5c レグ A: event-block bootstrap + IM 併設、p = max(p_boot, p_IM)、BH-FDR q=0.05 m=6)

| # | combo | N | blocks | EV_te (p) | EV_ft (p) | EV_norm (σ_ATR) | p_boot | p_IM | p_combo | BH 閾値 (rank) | レグA | 分類 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | FOMC/follow/60m/h12 | 140 | 20 | +4.28 | +2.90 | +0.0432 | 0.2289 | 0.2355 | 0.2355 | 0.0167 (2) | ❌ | **C5** |
| 2 | FOMC/follow/30m/h12 | 140 | 20 | −7.07 | −4.26 | −0.0795 | 0.7941 | 0.7778 | 0.7941 | 0.05 (6) | ❌ | **C5** |
| 3 | CPI/fade/30m/h12 | 195 | 28 | +6.22 | +4.78 | +0.0436 | 0.2504 | 0.2532 | 0.2532 | 0.025 (3) | ❌ | **C5** |
| 4 | FOMC/follow/60m/h24 | 140 | 20 | +4.79 | +4.32 | +0.0305 | 0.4423 | 0.4290 | 0.4423 | 0.0417 (5) | ❌ | **C5** |
| 5 | CPI/fade/60m/h12 | 195 | 28 | −0.32 | +0.39 | +0.0085 | 0.4407 | 0.4399 | 0.4407 | 0.0333 (4) | ❌ | **C5** |
| 6 | CPI/fade/30m/h24 | 195 | 28 | +9.68 | +7.32 | +0.0686 | 0.2089 | 0.2140 | 0.2140 | 0.0083 (1) | ❌ | **C5** |

- **レグ A**: 全滅 — 最小 p_combo = 0.214 (#6) ≫ rank-1 BH 閾値 0.0083。BH-FDR q=0.05 (m=6) 通過ゼロ。
- **レグ B (記録)**: 4/6 が点推定で te>0 ∧ ft>0 (機構整合)、stress 2 種も #1/#3/#4/#6 は正 (#6: s1 +8.67 / s2 +7.69)。**B(d) は全候補充足** (N 140–195 ≥ 30、blocks 20–28 ≥ 15)。
- **分類**: C2 (sequencing 反転) 該当ゼロ (te>0 の候補は全て ft>0)。**C3 (UNDERPOWERED 適格) 該当ゼロ — §9 の modal 予想 (C3) は不成立**: C3 の要件はレグ B(d) 不達だが、OOS blocks は FOMC 20 / CPI 28 で B(d) 閾値 (≥15) を充足したため、レグ A 不通過 combo は §8 の排他順どおり C5 へ機械着地 (§9 の「FOMC 系は blocks ~20 で C3」という予想記述は B(d)≥15 の自らの閾値設定と整合しない予想だった — 判定は §8 明文の字義執行であり再解釈はしていない)。C4 (レグ A 通過 ∧ EV≤0) 該当ゼロ。
- **発動分岐 (§8 固定)**: **phase-0 PASS = 0 → phase-1 (E7 サプライズ条件付き) は予定どおり実行** (無条件仮説の FAIL はサプライズ条件付き仮説を falsify しない — §8 に今宣言済み)。UNDERPOWERED 再判定の条件付き registry エントリは C3 ゼロのため**不発**。
- **文献 standing (Lee & Wang RAPS 2025) の post-sample 検証**: 文献の fade 主張に対し discovery は FOMC **follow** 側を選抜 (探索窓で fade は選抜規則不通過)、その follow も OOS で有意性なし。イベント窓の方向頻度優位が摩擦控除後 EV に変換される証拠は OOS に無い — 文献アンカーの standing も negative。

### データ整合 (判定前の機械ガード、全て green)

- **parquet 台帳再現 13/13**: first 起点・explore coverage・台帳 last 時点行数の完全一致 (末尾余剰 = 台帳スナップショット (07-21 ~05:00 UTC) 後の re-fetch 分 23–24 本のみ、OOS cutoff 2026-06-30 で切詰め = 判定非接触)。per-file sha256 は artifact `data_ledger` に凍結。
- **OOS 窓カレンダー sanity (§3.2b-7 どおり verdict 時実行)**: flag 率 NFP 3.4% / **CPI 14.3% / FOMC 10.0% (>5%)** — ただし offset ピーク検査は**全 3 種 offset +0** (時刻正常)。explore 窓で user 裁定済み (2026-07-22) の「低インパクトイベント由来・時刻正常」と同一シグネチャのため、同裁定の下で続行し記録 (時刻破損の徴候なし。仮に >5% ∧ offset 異常なら DEFERRED 停止する実装 — 発火せず)。
- **リーク canary (§5c-3)**: 実データ全 sweep 686 件 (event×pair×rule×W0 重複排除) **all clean** + unit test で「注入リークを False 検出」する能力自体を pin。
- **collision/週末**: collision フラグ CPI 7 trades / FOMC 0 (除外せず記録、§10-3)。週末跨ぎは CPI 21 trades (Secondary 層別を artifact に記録)。

### 帰結

- E15 (無条件イベント窓プレミア/リバーサル、FOMC/NFP/CPI × M15) は**棄却**。イベントカレンダーの無条件モダリティは供給ラインから外れる。
- **次**: phase-1 (E7 指標サプライズ directional) を §6/§11 の予定どおり実行 (FF gap scrape + データ付録凍結 2026-08-14 → discovery 08-21 → OOS verdict 08-28、registry `e15-e7-event-prereg-phase1-verdict` 監視継続)。両 phase PASS=0 となった場合のみ §8 の E12 格上げ分岐。
- §10 遵守の宣言: OOS 結合統計の観測は本 verdict 実行が初回。観測後の再分析・grid 再アンカー・候補変更は行っていない (本 §12 の記述は §5c/§8 に事前列挙された切り口のみ)。
