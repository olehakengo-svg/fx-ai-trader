# Pre-registration 🔒 LOCKED: E1 retail-positioning contrarian — Myfxbook aggregate 版・文献駆動 観測前検証 (rule:R1 research-only)

> **🔒 LOCK 執行 2026-07-17 (self-LOCK)**: LOCK 決裁期限 (2026-07-17) 到来時点で user 応答なし。PR #92 (merged 2026-07-16) で user 通知済み・異議なし → 純研究 pre-reg の self-LOCK 前例 (round-2、通知後異議なし) に基づき **self-LOCK を執行**。以後シグナル定義/窓/ペア/閾値/期日/市場時間定義の変更は禁止 (§6)。first look verdict 期日 = **2026-10-15** (registry `e1-prereg-lock-decision-stale` を `e1-prereg-verdict-deadline` へ置換済み)。
> **LOCK 時確定事項 (§7)**: (1) **stale cap = 主モード確定** — per-instrument `verified:{instrument}:{book}` 永続化 (`positioning_health` テーブル、`record_health()`) が本番稼働。2026-07-17 status API で 13 instrument 全ての verified 時刻 + `last_cycle_at` heartbeat を確認。stale cap は「最終検証成功からの age > 2h → NA」の主定義で確定 (fallback 不使用)。(2) **ソース = myfxbook 稼働確認** — `source=myfxbook` / `configured=true` / `logged_in=true` / `waiting_for_credentials=false` (first login 2026-07-16T23:04:48Z)。M1 最短経路の user アクション依存 (Myfxbook credentials 投入) は解消。t0=06:33:31Z の primary snapshot の provenance (credentials 投入前後の source 連続性) は verdict 時 §2.5 品質 gate で検査する。(3) confirmatory 7 ペア t0 台帳 = 付録 A で先行確定済み。(4) `e1-positioning-ingest-freshness` の鮮度監視は credentials 投入条件成立で本格再開。
> **設計来歴 (provenance)**: 2026-07-16、8-agent workflow で設計 — 独立 3 案 (power / microstructure / discipline レンズ) → 統合 → 敵対的レビュー 3 レンズ (major 11 項目) → 改訂。裁定原則 =「薄いデータで第一種過誤を優先制御」。
> **LOCK 手続き (原設計、履歴保存)**: user 承認 (D3 SLA 48h) を第一経路とする。純研究 pre-reg の self-LOCK 前例 (round-2、通知後異議なし) に基づき、**2026-07-17 までに user 応答がない場合は self-LOCK を執行し session log に記録する** (registry `e1-prereg-lock-decision-stale` が監視)。→ **上記のとおり 2026-07-17 に self-LOCK 執行済み**。
> **LOCK 前必須インフラの状態**: per-instrument `last_verified_at` 永続化 (§2.2 主モード) は**本 pre-reg と同一 PR で実装済み** — **LOCK 時に主モードで確定 (本番検証済み、上記 LOCK 時確定事項 (1))**。

**起案日**: 2026-07-16 (t0 = 2026-07-16T06:33:31Z、蓄積 3 cycle 時点 = 実質データブラインド)
**改訂**: 2026-07-16 敵対的レビュー (リーク/統計/KB 整合の 3 レンズ) 反映済み — major 13 件 (統合後 11 項目) + minor 6 件を反映。反映内容は §6 末尾「レビュー反映ログ」に固定。
**起点**: [[e1-positioning-ingest-2026-07-14]] §9 (Myfxbook aggregate 転換・一次統計 2 系統の既定義) / external-hypothesis-scan-2026-07-13 E1 / MEMORY `project_ws3_external_hypothesis_transition_2026_07_13`
**統合元**: 3 独立設計案 (power / microstructure / discipline レンズ)。矛盾点は全て「**薄いデータで第一種過誤を優先制御**」の原則で裁定し、裁定理由を末尾の裁定脚注に固定した。

---

## §0 Status とスコープ

- **Status**: 🔒 **LOCKED (self-LOCK 執行 2026-07-17)** — DRAFT (レビュー反映済み) から確定。本 pre-reg の統計的資産 =「まだ誰もシグナル×リターンの結合統計を見ていない」観測前性を LOCK で固定。LOCK 後の変更はレビュー必須 PR のみ。結果観測後のシグナル定義/窓/ペア/閾値/期日の変更は禁止。設計者ブラインド誓約 (§6) は verdict まで有効。
- **方法論上の位置づけ**: round-1〜3 (歴史データの discovery→凍結→OOS) と異なり、**検証データの全量が LOCK 後に発生する純粋 prospective 検証**。discovery/holdout 分割が不要で、全サンプルが確認的。これが price-modality 3 周 FAIL 後の供給ラインで本設計を成立させる唯一の窓である。
- **スコープ**: 純研究。live 発注・shadow パラメータ・Kelly・tier に一切触れない。**PASS でも実装は別途 D4 準拠の実装 pre-reg + user 最終承認** (本文書は実装内容を拘束しない。barrier 最適化・ペア選抜・lot 設計の自由度は意図的に実装 pre-reg 側へ温存する)。
- **設計者ブラインドの宣言**: 本設計時点で inspect したのは ingest 健全性 (status API / 3 cycle の保存確認) のみ。シグナル×リターンの結合統計は一切計算していない。LOCK 前にこれを超える観測を行わない (§6-8 誓約)。
- 蓄積継続は verdict と独立に走り続ける (history は今からしか貯まらない)。REJECT でもデータ収集の停止は別決裁。

## §1 仮説と文献根拠

**H1**: Myfxbook Community Outlook の retail aggregate positioning が extreme のとき、その**逆方向**の前方リターンが正であり、**摩擦控除後 EV > 0** に変換できる。

**H0**: 予測性は存在しない、または存在しても摩擦水準 (round-trip 2.0–4.5p) 未満。

**文献根拠と経済機構 (符号を観測前に固定する根拠)**:
1. **Retail order flow は intraday〜daily で uninformed、逆側に予測性** (*News and intraday retail investor order flow in FX*, JIFMIM 101, 2025 — E1 の一次根拠)。→ contrarian の基本符号。フローの主張は「変化」、crowdedness の主張は「水準」— 両方を別シグナルとして定義し混ぜない[^1]。
2. **Retail は負のフィードバックトレーダー** (disposition effect)。従って skew 水準は直近リターンのほぼ負の関数であり、「skew contrarian」が価格モメンタムと部分同値になり得る。これは棄却理由ではなく解釈上の交絡として扱い、CONFOUNDED フラグ (partial IC、§4.4) を事前定義する。
3. **Squeeze 力学**: crowded 側が含み損 (現値が平均建値の逆側) のとき、損切り・強制決済がフローを増幅し、retail に逆行する方向へ**継続**圧力。avgLong/ShortPrice はこの proxy を作れる唯一の非価格フィールド。注意: これは厳密には contrarian と別機構 (モメンタム側) — 符号を今固定することが本 pre-reg の主張。
4. **ホライズンの事前確率**: 文献の主張は intraday〜daily。15m 級で効くという主張はどの文献にもなく、摩擦 (2.0–4.5p) が 1h 未満のボラを上回る → grid は intraday (4h) + daily anchor (24h) の最小 2 点に限定 (§3.3)。
5. **効かない条件 (既知)**: extreme の絶対水準はペア構造に強く依存する (USD_JPY は構造的 20/80 帯) → 静的閾値は不可、ペア内 trailing 正規化が必須 (§3.1)。

## §2 データと estimand

### 2.1 estimand の正 (実装事実に即して固定)

- ソース = 本番 SQLite `positioning_snapshots` (book_type='outlook'、`modules/positioning_ingest.py` が DDL/dedup の単一ソース) × MASSIVE 12y OHLCV M15 mid (本番 signal 関数と同一ソース)。
- 1 観測 = (instrument, 20 分規則グリッド時刻 t) における **LOCF 済み positioning 状態** × その後の前方リターン。
- **DB の生行は estimand ではない**。content-hash dedup により「行が在る = payload が変化した cycle」— 行の存在自体が「変化があった」ことを条件付ける (活動条件付けバイアス)。全分析は下記 2.2 の規則グリッド LOCF 系列上でのみ行う (§6-1 で禁止事項化)。content 不変なら LOCF 値は真値なので、LOCF は近似ではなく正確な再構成である (障害との識別は 2.2 の検証証跡で行う)。
- `snapshot_time` は **fetch 時刻** (microsecond 精度、Myfxbook 側の生成時刻は取得不能)。fetch 時刻を「利用可能になった時刻」とみなすのは保守側。
- フィールド: skew 系 = `pct_long_total`/`pct_short_total` (longPercentage/shortPercentage)。avg 価格系 = `buckets_json` (JSON **object** = raw payload) から `avgLongPrice`/`avgShortPrice` をパース (JSON array = OANDA 旧行は型で除外)。0/欠損/非正の avg 価格は当該スロットの S3 を NA (silent 0 埋め禁止)。avg 価格の意味論 (加重方法・更新頻度) は未検証のため、S3 の estimand は「Myfxbook が報告する avg 価格」と操作的に定義する。

### 2.2 市場時間・LOCF リサンプル契約 (全分析共通、verdict 前に unit test で pin)

- **市場時間の定義 (DST 追随、今固定)**: 市場時間 = **America/New_York の Sun 17:00 open 〜 Fri 17:00 close** を各日付で UTC 変換した区間 (夏時間 = Sun 21:00–Fri 21:00 UTC、冬時間 = Sun 22:00–Fri 22:00 UTC)。**second look 窓 (〜2026-12-30) は US DST 終了 (2026-11-01) を跨ぐため、固定 UTC 定義は 11 月以降に実市場時間と 1h ずれる spec バグとなる — 採用しない**。週末スロット除外・LOCF age・stale gap・coverage・「金曜クローズ前 2h」(= NY Fri 15:00–17:00) の全規則は本定義を参照する。LOCF resampler unit test に DST 跨ぎ週 (2026-11-01 前後) のケースを必ず含める。
- グリッド = UTC :00/:20/:40 の 20 分規則グリッドのうち、上記市場時間内のスロットのみ。
- 各 (instrument, t) の値 = `snapshot_time ≤ t − 60s` (安全マージン) を満たす最新行の LOCF。
- **stale cap (検証証跡基準 — 活動条件付けの完全排除)**: 実装上、dedup skip された成功 fetch と per-instrument の fetch/parse 失敗 (MISSING SYMBOL 等) はどちらも「行を書かない」ため DB だけからは識別不能。「最終保存行の age > 2h → NA」という cap は (i) 正当に 2h 超不変だった静穏期間を系統的に NA 化する (= §2.1 が排除した「行の存在 = 変化」条件付けの裏口再導入、ボラレジームと相関する系統的欠測)、(ii) 2h 未満の per-instrument 失敗を「無変化」と誤認し変化していた値を LOCF が真値として供給し得る、の 2 方向で estimand を汚し、「content 不変なら LOCF は正確な再構成」という本 §2.1 の主張と自己矛盾する。従って:
  - **LOCK 前に rule:R3 で実装 (本 pre-reg と同一 PR 群、estimand に触れるため本文反映必須)**: per-instrument の **`last_verified_at`** (dedup skip を含む fetch+parse 成功時刻) を DB へ 1 行 upsert で永続化する (fork コピーの counter は信用できない教訓の適用)。cycle 単位 heartbeat では per-instrument 失敗 (symbol 欠落等) を捕捉できないため、**instrument 単位**であることが要件。
  - **stale cap の定義 (主モード)**: age(t) = t − last_verified_at(instrument) を市場時間で計測し、**> 2h のスロットのみ NA**。検証成功 + content 不変のスロットは **LOCF を無期限に有効**とする (poll 20 分の 6 倍マージン、registry `e1-positioning-ingest-freshness` と同水準)[^2]。
  - **fallback (万一 LOCK までに未実装の場合の事前宣言)**: 旧定義 (最終保存行 age > 2h → NA) を適用するが、これを §5 残存リスクではなく **estimand 制約としてここに宣言する**: (a) 静穏期間 (低変化レジーム) の系統的標本除外、(b) ≤2h の per-instrument 失敗の無変化誤認、の 2 バイアスを含む。この場合、2h-cap 起因 NA の件数と時間帯分布を verdict に必須併記し、**閑散時間帯への欠測集中が観測されたら DEFERRED に接続する** (事前固定分岐)。**LOCK 時にどちらのモードが有効かを本文書へ追記して確定する**。
- **cycle 証跡 (worker 死の検出、因果方向に固定)**: スロット t は、全追跡 instrument を横断して **(t − 90min, t] (市場時間)** に新規行 ≥1 (last_verified_at 実装後は「検証成功 ≥1」) があれば cycle 稼働とみなす。なければ ingest 障害と推定し**全ペア NA** (全 13 instrument が 90 分全て content 不変は実質あり得ない)[^3]。窓は後方 (t 基準の過去) のみ — 「次の行の到着」という将来情報でスロット有効性を決めない。poll cycle heartbeat (`last_cycle_at` 1 行 upsert) の永続化後はそちらを正とする。

### 2.3 OHLCV join 契約 (look-ahead 封鎖)

- mid(t) = **t 以前に確定した最後の M15 bar の close** (mid)。t ちょうどに open する bar・進行中 bar の使用は禁止。
- エントリー価格 = **t より厳密に後に open する最初の M15 bar の open**。LOCF が snapshot_time ≤ t − 60s を保証するため fetch→エントリーの順序逆転は構造的に起きない。`assert entry_bar.open_time > grid_t` をエンジンで pin。
- **前方リターン (IC レグ、一意化)** = entry bar open から **entry + h_bars 番目 bar の open** まで (EV time-exit の決済慣行と同一 — close/open の二者併記を廃し open に固定。事後選択の余地を残さない)。h は market-time bar-count (§3.3)。
- **cutoff 打ち切り (censoring、combo 毎に事前固定)**: 最終シグナルスロット = **cutoff − h (market-time)**。それ以降のスロットは IC 観測・EV エントリーとも不算入とし、**coverage 計算の分母からも除外**する。first-touch レグも timeout = h が cutoff 内に完結する entry のみ算入 (窓外にはみ出すトレード・未決着ポジションの事後裁量処理を構造的に排除)。
- **daily ATR の定義 (look-ahead 封鎖)**: ATR14d(t) = **t より厳密に前に完結した直近 14 本の daily bar** の true range 平均。daily bar 境界 = **NY 17:00 roll (§2.2 市場時間定義と同一、DST 追随)**、M15 mid から構築する (MASSIVE cache の daily 集計規約への暗黙依存を断つ。素朴な暦日 join はエントリー当日の日足レンジ = 未来の intraday 変動を混入させる古典的 look-ahead)。影響先は S3 分母 (pain 正規化)・first-touch barrier 幅 σ_h・Gate 2 の ATR 正規化統計の 3 箇所 — **ナイフエッジ #3 の canary leak test の注入対象に ATR 経路を明示的に含め、unit test で pin する**。
- verdict 用 OHLCV は隔離 worktree に cutoff 日で末尾切詰めた parquet (stage-1/2 と同方式。部分 parquet 罠 — フル期間版から切詰める)。pip 定義: JPY クロス = 0.01、それ以外 = 0.0001 (EUR_GBP 含む)。

### 2.4 ペア族 (2 family、入れ替え禁止)

- **Primary family = 初期 6 ペア** (USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, AUD_JPY。t0 = 2026-07-16T06:33:31Z 共通)。Stage A/B・EV レグ・verdict は全て primary のみで決まる。
- **Confirmatory family = 後発 7 ペア** (AUD_USD, NZD_USD, USD_CAD, USD_CHF, NZD_JPY, EUR_AUD, EUR_GBP。**ペア別 t0 — 各デプロイ確定時刻を LOCK 時に本文書へ追記**)。primary pooled への混入は禁止 (t0/burn-in が異なり panel が不均衡)。役割 = **out-of-family 複製検査**: PASS 候補 combo について、凍結ルールをそのまま適用した confirmatory pooled の**点 net EV ≥ 0 と per-pair IC 符号一致数/7** を検査する。confirmatory 側の post-burn-in 評価期間 ≥6 週かつ pooled trade N ≥ 30 が揃う場合は点 EV ≥ 0 を **PASS 必須条件**とし、符号が両側 α=0.05 で有意逆転した場合は PASS を保留し user 裁定。揃わない場合は本検査を実装 pre-reg へ繰延し verdict に「confirmatory 未検査」と明記 (PASS は止めないが実装前に必ず実施)[^4]。
- primary のペア脱落 (§2.5 品質 gate) が生じても confirmatory からの補充は禁止。
- **JPY 集中の宣言**: primary 6 のうち 4 が JPY 脚 → 実効独立ペア数を保守的に 2.0 と仮定 (§5)。ナイフエッジに leave-JPY-block-out を含める (§4.5)。

### 2.5 データ品質 gate (verdict 実行の前提条件、統計計算より先に機械判定)

1. **coverage**: 各 primary ペアで、burn-in 後の市場時間グリッドスロット (§2.3 の cutoff − h 打ち切り適用後) のうち有効 (§2.2 stale cap の有効モード基準で non-NA かつ cycle 稼働) が **≥ 90%**[^5]。不達ペアは family から機械除外 (裁量なし、fail-loud 記録)。
2. **stale gap**: 単一連続欠測 > 24h (市場時間、週末除く) は当該区間を解析除外 (ペア除外ではない)。除外日 > 評価窓の 20% で当該ペアを primary から除外。
3. **family gate**: 除外後の primary が **4 ペア未満** → verdict を 4 週間 postpone (look を消費しない機械延期、1 回限り)。**postpone 発動時は cutoff・verdict 期日・評価窓終端を同幅 (4 週) スライドし、burn-in と評価窓開始は不変** (§7)。2 回目の不達は **DEFERRED** (明示フラグ + user 裁定)。通過ペアのみで pooling する場合は N_eff 再見積りを verdict に明記。
4. **整合 sanity**: |pct_long + pct_short − 100| > 1.0pp の行、avg 価格が当日価格レンジ ±10% 外の行は破損として除外 + 件数報告 (>1% で要調査フラグ)。snapshot_time 単調性確認。
5. **再現性 spot check (verdict 直前、結果を raw/ へ)**: (a) 無作為 20 行の buckets_json から content-hash 再計算一致、(b) 凍結 artifact と `/api/positioning/export` の roundtrip 突合、(c) Myfxbook web UI と 3 ペア × 1 時点の pct 突合 (±0.5pp、rate limit 内)、(d) LOCF resampler / rank / ATR / canary の unit tests green (§2.2/§2.3/§3.1 で pin 対象を列挙)。
6. **データ凍結**: verdict 用データは cutoff 直後に 1 回だけ export → parquet + sha256 を `raw/bt-results/` に保存。以後の分析は artifact のみ参照 (本番 DB への再クエリ禁止 — 再現性と look 追加の両方を封鎖)。
7. **構成非定常の監視 + jump detector (事前固定、判定不使用の記録と機械除外規則)**: totalPositions/volume の推移、および **量子化粒度 (窓 W 内の skew distinct 値数、ペア×統計毎)** を品質メトリクスとして記録し verdict に併記。**jump detector**: **Δskew = 直前有効スロットとの 1-step 差 (LOCF グリッド上)** と定義し、同一スロットで primary 6 中 ≥4 ペアが |Δskew| > 20pp → データイベント疑いとして**イベント時点から前方 +24h (市場時間) のみ**を全ペア解析除外 (新規 event・IC 観測とも)。**後方への遡及除外は原則禁止** — 時点 t の情報で t 以前の標本を選択する look-ahead であり、≥4 ペア同時 jump は実市場ショック (フラッシュクラッシュ等) でも発火し得るため、contrarian の損益が最も極端になる局面を将来条件付きで除去するとバイアス方向が不定になる。例外: 当該行が raw payload ベースの機械的破損確認 (§2.5-4 の整合 sanity 違反 = |long+short−100| > 1.0pp / avg 価格の当日レンジ ±10% 逸脱) に該当した場合のみ、その破損行の区間を遡及除外できる。**イベント時点で保有中のトレードは除外せず「イベント重複フラグ」を記録し Secondary で層別**。緩慢なドリフトは検出不能 — 限界として verdict に明記 (事後の窓切りは禁止)。

## §3 シグナル定義と grid (a priori 固定)

### 3.1 正規化: ペア内 trailing rolling percentile rank (静的閾値・z-score は棄却)

- 静的閾値はペア構造差 (USD_JPY 恒常 20/80) で不可。z-score は有界 [−100,100]・非正規・構成ドリフトで平均分散が非定常 → 不可。**ペア別 trailing 経験分位点 (percentile rank r ∈ [0,1])** が分布形状非依存・ペア間 pooling 可能な唯一の頑健解。
- **rank 式 (S1/S2/S3 共通、数式で今固定)**: **r(t) = (#{x < v(t)} + 0.5 · #{x = v(t)}) / N_valid** — mid-rank 規約。x は **t 自身を含まない strictly trailing window W 内の有効スロット値**、N_valid = その個数。固定理由: LOCF は同値をスロット反復で複製し、Myfxbook の pct は粗く量子化されている (整数級) ため窓 ≈1,440 スロットの大部分がタイになり得る — タイ規約 (< vs ≤、min/mid/max rank、t 包含) の選択が r を数〜数十 pp 動かし、0.90/0.10 交差 = event の有無と IC の両方を桁で左右する。未固定は観測後の裁量 = リーク。**LOCF 反復値・大量タイ・量子化を含む合成データでの unit test を §2.2 resampler pin に追加する**。
- **window W = 直近 20 営業日** (グリッド ≈1,440 スロット) 固定[^6]。window 内有効スロット被覆 < 70% のスロットは rank NA (補間しない)。
- rank・分位点は **strictly trailing** (t より前の当該ペアデータのみ)。全期間分位・centered 窓の使用は違反 = 当該シグナル FAIL。
- **burn-in = ペア別 t0 + 20 営業日** (それ以前のシグナルは存在しない)。
- タイ密度の帰結: r が 0.90/0.10 に一度も到達しないペア×統計は **event 0 のまま** — 閾値の裁量調整は禁止。量子化粒度は §2.5-7 の品質メトリクスとして verdict に併記。
- 感度 (Secondary 記述のみ、判定不使用): W=10 営業日 / expanding 窓での再計算。

### 3.2 一次統計 3 本 (KB §9 既定義の 2 系統に限定、追加禁止)

| ID | 定義 (LOCF グリッド上) | 経済機構 / **予測符号 (今固定)** |
|---|---|---|
| **S1 (skew 水準)** | skew(t) = pct_long_total − pct_short_total → trailing rank r₁(t) | crowdedness contrarian: r₁ 高 (retail long 偏重) → **下方向** |
| **S2 (skew 変化 = flow proxy)** | Δ₂₄(t) = skew(t) − skew(t − 72 slots、market-time) → rank r₂(t)。両端点有効時のみ定義 | retail 買いフロー急増の逆側 (JIFMIM intraday): r₂ 高 → **下方向**[^1] |
| **S3 (squeeze 圧力)** | pain(t) = [pct_long/100·(avgLongPrice − mid(t)) − pct_short/100·(mid(t) − avgShortPrice)] / ATR14d(t) (§2.3 定義) → rank r₃(t)。クリップなし (profit 側もクッション情報として保持) | 含み損優勢側の投げ (squeeze 継続): r₃ 高 (long 側含み損優勢) → **下方向** |

- 全シグナルの contrarian 連続スコア = −(r − 0.5) とし、IC は contrarian-signed で **H1: IC > 0** に統一 (片側検定の符号を今閉じる)。
- これ以外の派生 (volume/positions 加重、交互作用、セッション/ボラ/VIX/DXY 条件付け、ペア間クロスシグナル) は本 verdict で**全面禁止** — 記録のみ可 (階層ゲートキーパー原則)。

### 3.3 ホライズン grid (m 増殖の禁止)

**h ∈ {4h (16 M15 bars), 24h (96 M15 bars)} の 2 点のみ**[^7]。h は market-time bar-count (週末ギャップを「経過時間」として跨がない。ギャップ自体はリターンに含まれる — 現実の保有と同じ)。1h 未満は摩擦がボラを上回り文献根拠なし、48h 以上は N が絶望的。**grid 拡張・re-grid は verdict 後も本 pre-reg の下では禁止**。

→ 検定 family = 3 統計 × 2 ホライズン = **6 combo**。

### 3.4 EV レグの凍結ルール (grid なし単一定義)

- **エントリー event**: rank が **0.90 を下から上抜き → contrarian 方向 (S1/S2/S3 とも short)** / **0.10 を上から下抜き → long** の初回交差。エントリーは次 M15 bar open (§2.3)。閾値 0.90/0.10 は SSI/センチメント研究の標準 extreme (上下 1 decile) — grid にしない。近傍 0.85/0.95 はナイフエッジ検査のみ (§4.5)。
- **NA を挟む交差と hysteresis 状態 (事前固定)**: 交差判定は「**直前の有効スロットの rank**」との比較で行う。直前有効スロットとのギャップ (市場時間) が **> 2h** (stale cap と同値) なら**状態リセット** — 交差不成立・hysteresis 解除とし、リセット直後の最初の有効スロットは比較対象を持たないため event を発火しない (以後は通常規則)。NA 区間中に 0.80/0.20 を「戻した」ことにはできない (有効スロットの観測のみが状態を進める)。週末跨ぎ (金曜最終有効スロット → 月曜) は有効スロット比較で交差成立可。
- **hysteresis re-arm**: rank が 0.80/0.20 を戻すまで同方向再エントリー禁止 (20 分グリッド微振動の擬似反復封鎖)。同一ペア×方向でホールド中の重複エントリー禁止。
- **金曜クローズ前 2h (= NY Fri 15:00–17:00、§2.2 定義参照) の新規 event は発火禁止** (ギャップ直撃 entry の a priori 除外)。保有中の週末跨ぎは除外しない (裁量トリム回避) — 跨ぎフラグを記録し Secondary で層別記述[^2]。
- **exit 主レグ (検定対象)**: h 経過後 (entry + h_bars) の bar open で決済 (time-exit)。
- **first-touch レグ (必須併記 — stage-2 教訓: 中央値非対称は barrier sequencing で反転し得る)**: TP = SL = 1.0 × σ_h (σ_h = daily ATR14 (§2.3 定義) × √(h/24h))、timeout = h (close 決済)、同一バー内 TP+SL 両ヒットは **SL 優先** (ハウス保守規約、stage-2 §3 と同一)。**構成は horizon 毎 1 点のみ・grid なし** — 役割は sequencing 頑健性の確認であり最適化ではない (barrier 幾何の自由度は実装 pre-reg へ温存)。fut_close tie-break での EV は Secondary 併記。
- **新規 event の受付終端**: cutoff − h (market-time) まで (§2.3 censoring)。それ以降の event は不算入。
- **摩擦 (判定値、往復 pips、今固定 — 実測が後で判明しても first/second look とも変更しない)**[^8]:
  USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50 / GBP_JPY 4.50 / AUD_JPY 3.125 / EUR_GBP 3.00 / AUD_USD 2.50 / NZD_USD 3.00 / USD_CAD 3.00 / USD_CHF 3.00 / NZD_JPY 4.50 / EUR_AUD 4.50
- **stress レグ (PASS 必須の点条件)**: 摩擦 = **max(判定値 × 1.25, 判定値 + 1.0p)** でも pooled net EV 点推定 > 0 (検定は判定値のまま — 符号頑健性のみ要求。stage-2 §4(e) 前例)[^9]。

## §4 検定手続きと verdict 分岐 (全て結果観測前に固定)

per-cell (13 ペア × 6 combo = 78 セル) から始めると多重性が検定力を食い潰す。**階層ゲートキーパー**を採択: pooled panel が verdict を決め、per-cell は条件付き降格。

### 4.1 Gate 1 — 検出 (pooled IC、m=6、二重検定)

- 統計量: primary family 各ペアの Spearman IC (contrarian score −(r−0.5) vs 前方リターン (§2.3 open 終端)、burn-in 後・市場時間・品質有効スロット全点) を有効 N 加重平均した **pooled IC**、combo 毎。
- **推論 1 (bootstrap)**: **営業日単位の moving-block bootstrap、block 長 L = 5 営業日、B = 10,000、seed 固定**。**暦ブロックを全ペア同時に resample** — クロスペア相関 (JPY 脚 4/6) と h=24h の overlap を resample が同時処理する。null は per-combo 中心化、p は片側 (§3.2 で符号固定済み) → p_MBB[^10]。
- **推論 2 (block 数を自由度に反映する併設検定)**: first look の評価窓 40 営業日 / L=5 は実質 **8 block** — block 数一桁の MBB は null 分散を過小推定しやすく (反保守 = 偽 PASS 側)、B=10,000 はこの粗さを補わない。開示だけでは妥当性は回復しないため、**Ibragimov–Müller 型検定を併設する**: 評価窓を 5 営業日 × 8 block に等分し、block 毎の pooled IC を計算、その block 平均に対する片側 1 標本 t 検定 (**df = block 数 − 1 = 7**) → p_IM。
- **combo の Gate 1 p 値 = max(p_MBB, p_IM)** (両検定の充足を要求する保守側合成)。**判定: BH-FDR q = 0.05 (m=6 combo)** — look 毎 q を 0.05 に分割する α 会計 (§5) に基づく。
- **second look では bootstrap 単独に戻す (今固定)**: 累積窓 ≈20 週 → block ≈20 個となり MBB の粗さが解消するため。q₂ = 0.05、m = first look の UNDERPOWERED 適格 combo 数 (§4.4)。
- 感度: L ∈ {3, 10} での p を Secondary 併記 (判定不使用)。

### 4.2 Gate 2 — 経済性 (摩擦調整 EV = M6 gate、Gate 1 通過 combo のみ検定)

- Primary endpoint: §3.4 凍結ルールの **time-exit pooled net EV (p/t)** = mean(per-trade pips − 当該ペア摩擦判定値)、primary family 全トレード。検定統計は ATR 正規化 net return (ペア間スケール混在防止、ATR は §2.3 定義)、経済条件は raw pips (M6 の単位)。
- 推論: trade を entry 営業日でクラスタ化した day-block bootstrap (L=5 営業日、B=10,000、seed 固定)、片側 **p ≤ 0.05**。Gate 1 通過 combo が複数なら BH-FDR **q=0.05** を通過 combo 数で適用。
- **EV-PASS 条件 (combo 毎、全て充足)**: (a) time-exit pooled net EV > 0 かつ p ≤ 0.05[^12]、(b) first-touch レグの pooled net EV 点推定 > 0、(c) stress レグ点推定 > 0 (§3.4)。
- **N gate (d、二重定義の解消)**: 評価窓 pooled trade **N < 60** の combo は Gate 2 検定を実行せず、**§4.4 Step 1 の排他分類 (C2〜C5) に点推定のみで回す** — C3 (UNDERPOWERED 適格) の 3 条件と C2 (sequencing 反転) 不適格条項を通常どおり適用する。「自動 UNDERPOWERED」という短絡は置かない: 点推定が負なら REJECT 側 (C5)、first-touch ≤ 0 なら C2 に落ちる。crossing 発生率仮定の外れを REJECT に誤変換しない趣旨は、C3 の適格性判定が N・検定を不問とすることで担保される。
- **sequencing 反転条項 (今宣言)**: time-exit のみ正で first-touch 点 EV ≤ 0 の combo は PASS 不可・UNDERPOWERED 不可 — 「sequencing 反転」として **REJECT 側**に倒す (stage-2 lfr×EUR_USD の実証パターン。§4.4 C2)。
- IC と EV の役割分担: **IC = 検出 (全グリッド点で power 最大化)、EV = 経済性 (money endpoint)。PASS は両ゲート通過が必要** — conjunction は保守側であり、供給ライン最後の砦で偽 PASS を出すコストが最大のため。

### 4.3 Stage B — 条件付き localization (Gate 1+2 通過時のみ、verdict に影響しない)

- 通過 combo について primary 6 ペアの per-pair IC/EV を同一 bootstrap で評価し BH-FDR q=0.10 (m=6 ペア、記述のみのため house 標準値)。**PASS/REJECT には使わない** — 実装 pre-reg でのペア選抜材料 (記述) に限定。全滅でも Gate 1+2 PASS は portfolio-level の主張として有効 (その旨明示フラグ)。

### 4.4 verdict — 2 段判定 (combo 排他分類 → 全体優先順位、全て結果観測前に固定)

**Step 1 — combo 排他分類**: 各 combo をこの順で評価し、**最初に該当したクラスに一意に分類する** (二重所属なし。N<60 の combo は §4.2(d) により C2 以降を点推定で判定):

| 順 | クラス | 条件 |
|---|---|---|
| **C1: PASS combo** | Gate 1 (§4.1 二重検定 + BH q=0.05) ∧ Gate 2 (a)(b)(c) ∧ N ≥ 60 ∧ ナイフエッジ 4 点 (§4.5) ∧ confirmatory 条件 (§2.4、データが揃う場合) を全充足 |
| **C2: sequencing 反転** | IC 点推定が宣言符号 ∧ time-exit 点 net EV > 0 ∧ first-touch 点 EV ≤ 0 — REJECT 側 (PASS/UNDERPOWERED 不適格) |
| **C3: UNDERPOWERED 適格** | IC 点推定が宣言符号 ∧ time-exit 点 net EV > 0 ∧ first-touch 点 EV > 0 |
| **C4: REJECT-F 型** | Gate 1 通過 (統計的予測性は実在) ∧ time-exit 点 EV ≤ 0 |
| **C5: REJECT 型** | 上記いずれにも非該当 (IC 符号不一致 または EV ≤ 0) |

**付帯フラグ (combo 単位。全体 verdict の分岐そのものにはしない — 相互排他性を保つため)**:
- **SIGN-FLIP**: 宣言と逆符号 (retail 追随 = momentum 側) が両側 α=0.05 で有意 → 当該 combo は C5 に分類した上でフラグ。経済的に別仮説であり、追うなら新規 pre-reg + user 承認 (silent な符号反転採用を構造的に禁止)。PASS combo と併存した場合も全体 PASS は有効だが、フラグと解釈注意を verdict に必須記載。
- **CONFOUNDED**: C1 combo の partial IC (直近 24h・120h リターンを rank 回帰で統制した残差 IC、事前定義) の点推定符号が raw IC と逆転 → PASS-with-flag として user 裁定 + 実装 pre-reg に「価格モメンタムベースラインとの増分検証」必須条項。partial IC は PASS/REJECT 自体を変えない (過剰要件化の回避) がフラグ省略は不可。

**Step 2 — 全体 verdict (優先順位 PASS > UNDERPOWERED > REJECT-F > REJECT で一意に決定)**:

- **PASS** (∃C1): 実装 pre-reg (D4 準拠、shadow 起点) を別途起案し user 最終承認へ。**併存する C3 combo の second look は行わない** (α 節約 — 残 combo は実装 pre-reg の記述材料に留める)。
- **UNDERPOWERED** (C1 ゼロ ∧ ∃C3): **second look へ** (§7。1 回限り・新自由度ゼロ)。仕様を今固定: **標本 = burn-in 後〜cutoff #2 の累積標本** (増分のみではない。年末除外窓適用) / **検定対象 = first look で C3 と分類された combo のみ** (BH の m = |C3|、q=0.05 — first look で点推定が負だった combo の敗者復活を封鎖) / **second look の着地は PASS / REJECT-F / REJECT のみ** (second look で Gate 1 通過 ∧ EV ≤ 0 に着地した combo は first look の C4 と同処置 = REJECT-F。3 回目の look 禁止)。**併存する C4 combo の REJECT-F 処置 (decision memo 起案) は second look verdict まで保留する** — 「クローズ」と「蓄積・検証継続」の処置矛盾を排除。
- **REJECT-F** (C1・C3 ゼロ ∧ ∃C4): aggregate 版クローズ + 「予測性あり・粒度/執行で EV 化不能」として**有償 bucket 級 (KB §8c オプション C) の decision memo を起案** (契約判断は user)。執行再設計以外の再判定経路を持たない。
- **REJECT** (全 combo が C2/C5): E1 aggregate 版クローズ。供給ラインは KB §8c 残オプション (practice 検証 / 有償 / round-4) の再決裁へ。
- **DEFERRED**: 品質 gate 不成立 (postpone 2 回目)、または排他分類の外に落ちる想定外の着地 (排他設計により原則発生しない — 発生した場合は設計違反として記録) → 明示フラグ + user 裁定 (ハウス規律。勝手に解釈しない)。

### 4.5 ナイフエッジ検査 (PASS 必須、4 点)

1. **fold 集中**: 評価窓を時系列 3-fold (first look ≈2.7 週×3) 等分。PASS 候補 combo の**最良 fold 除外の残り 2 fold pooled IC / net EV の符号維持** (単一レジームイベント由来の PASS を棄却。stage-2 htf_fb の [+10.8, +2.9, −10.9] パターンの検出器)。
2. **孤立格子点**: (i) entry 閾値近傍 {0.85, 0.95} での event net EV 符号一致 ≥ 1/2、(ii) 隣接 combo (同統計×他 h、同 h×他統計) のうち**少なくとも 1 つ**の点 EV > 0 (grid 最小のため過半でなく ≥1 — 事前固定)、(iii) W=10/expanding 感度で IC 符号が反転しないこと (窓アーティファクト検査)。
3. **閾値リーク / 遅延頑健性**: (i) code audit で trailing 限定を確認 (全期間統計の混入ゼロ) + 未来リターンをシグナルに注入した canary がエンジンで検出されること — **注入対象に ATR 経路 (S3 分母・σ_h・Gate 2 正規化) を含める (§2.3)**、(ii) 全シグナルを +1 グリッド slot (20 分) 遅延させた pooled net EV の符号維持 (微細 look-ahead / fetch-execution 位相依存の機械検出)。
4. **クロスペア集中**: leave-JPY-block-out (JPY 脚 4 ペア除外) と leave-non-JPY-out の両方で点 EV 符号を記録。**全 EV が単一通貨ブロック由来なら PASS を「当該ブロック限定」の限定 PASS に降格** (実装 pre-reg の scope を拘束)。

### 4.6 Secondary (記述のみ、判定・後続文書での確認的引用を禁止)

q=0.80/0.20 閾値 / W=10・expanding 感度 / L∈{3,10} bootstrap / fut_close tie-break first-touch EV / 実測摩擦での EV / 週末跨ぎ層別 / jump イベント重複フラグ層別 / per-cell 全表 / confirmatory family 符号表 / セッション別 (Asia/LDN/NY) IC 記述 (条件付けは判定に入れない — 次段の仮説素材) / partial IC の数値 / 量子化粒度・2h-cap 起因 NA 分布 (fallback モード時)。

## §5 power 概算と α 会計 (正直な実効 N — 見積り式ごと固定)

- **スケジュール前提**: burn-in 20 営業日 (〜2026-08-12) → **評価窓 = 2026-08-13〜2026-10-08 ≈ 8 週 = 40 営業日**。
- 実効 N ≈ (非 overlap 観測数/日 × 40 日) × pairs_eff。**pairs_eff = 6/(1+5·ρ̄) = 2.0** (クロスペア相関 ρ̄ = 0.4 の保守仮定 — 旧記載の ≈2.5 は算数誤りで、power を約 25% 過大申告していたため訂正。verdict 時に実測 ρ̄ を併記し仮定の当否を記録)。
- **Gate 1 (IC)**: h=4h → 非 overlap ≈5/日 → 実効 N ≈ 5×40×2.0 = **400** → 80% power で検出可能 |IC| ≈ **0.14–0.15** (BH 最小有効 α 込み)。h=24h → ≈1 独立観測/ペア/日 → 実効 N ≈ **80** → 検出可能 |IC| ≈ **0.28–0.33**。**文献級の daily IC (0.05–0.15) は h=24h では first look で構造的に検出不能** — これが h=4h を grid に含める検出力上の理由。
- **Gate 2 (EV) — horizon 別 (旧版は h=4h の SE を全 horizon に誤適用していたため分離)**:
  - **h=4h**: crossing 発生率の事前仮定 = 2–3 event/週/ペア (hysteresis 込み) → pooled trade N ≈ 96–144。per-trade net SD ≈ 0.7–1.0 × σ_4h (σ_4h = daily ATR × √(4/24) ≈ 0.41 × daily ATR。first-touch ±1σ 打ち切りで縮む) → SE ≈ 1.7–2.9p → 80% power (片側) の検出可能 net EV ≈ **+4〜7 p/t 級** (= first look の PASS は大効果のみ)。
  - **h=24h**: σ_24h = daily ATR そのもの (主要ペア 60–100p 級、JPY クロスはそれ以上) → 同 N で SE ≈ **5–9p** → 検出可能 net EV ≈ **+13〜22 p/t 級 = first look の Gate 2 PASS は構造的にほぼ不可能** (これを隠さない — Gate 1 側の h=24h 開示と対称化)。second look (N ≈ 2 倍) でも ≈ +9〜15 p/t 級で依然大きい。**従って h=24h combo の first look の役割は「符号スクリーンのみ」と今位置づける** — 現実的な PASS 経路は h=4h、h=24h は C3 → second look 経由が主線。
- **modal outcome の事前予想 = UNDERPOWERED**。これを今、明示的に記録する (結果を見た後の言い訳を封じる)。first look の役割 = 符号スクリーン + 大効果の早期検出 (実質 h=4h)。本検定は「M6 gate (摩擦 2.0–4.5p 控除後 EV>0) を通る、実装に値する強効果のみを掬うスクリーン」として検出力と目的が整合している — これは検出力の限界の言い換えでもあることを隠さない。
- **α 会計 (明示 — 旧記述「q₁+q₂ ≤ 0.10 級 = house と同水準」は算数誤り (単純加算で 0.20) のため削除)**: Gate 1 の BH-FDR を **look 毎 q = 0.05 に分割**する (first look q₁ = 0.05 / second look q₂ = 0.05、対象は C3 combo のみ)。条件付き 2 look の合計で family FDR ≤ q₁ + q₂ = **0.10 を実際に保証** — house 標準 q=0.10 と同水準の第一種過誤制御を 2 look 構成でも維持する (第一種過誤優先の原則による裁定。power 減は second look の存在が受け皿)。Gate 2 (p≤0.05 conjunction)・ナイフエッジ・confirmatory 複製は全て追加の保守側条件であり、実効の偽 PASS 率はこの上限よりさらに低い。

## §6 禁止事項とリーク防御 (LOCK〜verdict 間、違反 = 当該 verdict 無効 + lessons ページ)

1. **生行 (非 LOCF) での一切の signal-return 分析禁止** (§2.1 活動条件付けバイアス)。分析コードは本番 DB を直接読まず、凍結 export artifact → LOCF resampler (unit test pin 済み) を経由する。行の有無を特徴量・条件・重みに使うことを禁止。
2. **中間 peeking 禁止**: verdict cutoff まで、シグナル×リターンの結合統計の計算・目視 (skew 時系列プロット含む) を禁止。閲覧可能なのは status API の運用フィールドと §2.5 品質メトリクス (coverage/行数/整合/量子化粒度 — 値の分布ではなく欠測/整合のみ) に限定。評価エンジンは合成データ + 置換データで dry-run し、実データへの初適用は verdict 期日。
3. **定義変更禁止**: シグナル定義 (統計量・rank 式・W・閾値・hysteresis・NA リセット規約・符号)・h grid・barrier 構成・摩擦判定値・family 構成・look 日付・市場時間定義・censoring 規約の変更、統計量/ペア/ホライズンの追加。UNDERPOWERED second look での定義変更・対象 combo の拡大・3 回目の look。
4. **rolling 閾値は strictly trailing 限定** (§3.1、t 自身も含まない)。全期間分位・centered 窓 = 当該シグナル FAIL。機械検証はナイフエッジ #3。
5. **OHLCV join** は §2.3 契約のみ (前方リターン終端 = open、ATR = 完結 daily bar のみ、cutoff − h censoring)。synthetic fixture + canary leak test (ATR 経路含む) を LOCK 後実装時に pin。
6. **裁量運用の禁止**: confirmatory の判定昇格 / primary からの裁量除外 (品質 gate 機械除外以外) / 品質 gate 不達時の「部分窓だけ・良いペアだけで判定」(postpone 手続き以外) / jump detector の遡及除外 (§2.5-7 の機械的破損確認以外)。
7. **ingest 実装変更** (スキーマ/dedup/poll) で estimand が変わる場合、pre-reg 改訂 PR なしで進めること禁止 (self-heal・last_verified_at 永続化等、estimand を §2.2 の宣言どおりにする/変えない運用修理は可、session log に記録)。
8. **事後再分析の引用禁止**: verdict 後に不利な結果を「別統計なら通った」形で再分析・確認的引用すること (§4.6 に事前列挙されたもの以外は exploratory 明記が必須)。
9. **カーブフィッティング禁止の担保**: grid は 6 combo + 単一 barrier + 単一閾値のみ (全て文献根拠付き)。verdict 結果を見た後の grid 変更は一切禁止。

### レビュー反映ログ (敵対的レビュー 2026-07-16 — fatal/major への対応要約)

| # | 指摘 (major) | 対応 |
|---|---|---|
| M1 | stale cap が「最終保存行 age」鍵付けで活動条件付けを裏口再導入 (静穏期間の系統欠測 + per-instrument 失敗 ≤2h の無変化誤認)。2 指摘を統合 | §2.2: LOCK 前に per-instrument `last_verified_at` (dedup skip 含む fetch 成功時刻) を rule:R3 で DB 永続化し、stale cap を「最終**検証成功**からの age > 2h」に再鍵付け。検証成功+content 不変は LOCF 無期限有効。未実装 fallback 時は 2 方向バイアスを estimand 制約として宣言 + NA 件数/時間帯分布の verdict 必須併記 + 閑散集中で DEFERRED 接続。LOCK 時にモード確定を追記 |
| M2 | jump detector の後方 ±24h 除外 = 将来情報による標本選択 (look-ahead)。実市場ショックでも発火しバイアス方向不定。Δ間隔・保有中トレード扱い未規定 | §2.5-7: 除外は**前方 +24h のみ**。遡及は raw payload の機械的破損確認 (整合 sanity 基準) 該当行のみ。Δskew = 直前有効スロットとの 1-step 差と明記。保有中トレードは除外せず「イベント重複フラグ」記録 + Secondary 層別 |
| M3 | daily ATR 未定義 (完結 bar 限定・日境界規約なし) — S3 分母/σ_h/Gate 2 正規化に当日レンジ混入の古典 look-ahead | §2.3: ATR14d(t) = t より厳密に前に完結した直近 14 本の daily bar、境界 = NY 17:00 roll (市場時間定義と統一)、M15 mid から構築。canary leak test の注入対象に ATR 経路を明示 + unit test pin |
| M4 | percentile rank のタイ規約・t 包含が未固定 — LOCF 反復 + Myfxbook 量子化で窓の大部分がタイ、event 有無と IC が規約選択で桁変動 = 観測後裁量。2 指摘を統合 | §3.1: r(t) = (#{x<v} + 0.5·#{x=v})/N_valid (mid-rank)、窓は t を含まない strictly trailing、S1/S2/S3 共通と数式で pin。event 0 は裁量調整禁止と明記。量子化粒度を §2.5 品質メトリクス化。大量タイ合成データ unit test 追加 |
| M5 | UNDERPOWERED の二重定義 (§4.2(d) 自動 UNDERPOWERED ⇄ §4.4 の 3 条件) が矛盾し、sequencing 反転条項をバイパス可能 | §4.2(d): 「自動 UNDERPOWERED」を削除。N<60 combo は検定せず §4.4 排他分類 (C2〜C5) に点推定で回す — 適格なら C3、不適格 (点推定負/first-touch≤0) は REJECT 側 |
| M6 | verdict 分岐が combo 単位条件のまま非排他 (REJECT-F クローズ vs UNDERPOWERED 継続の処置矛盾等)、DEFERRED に裁量が漏れる | §4.4: 2 段判定に再構成 — Step 1 で combo を C1〜C5 に順序付き排他分類、Step 2 で全体 verdict を PASS > UNDERPOWERED > REJECT-F > REJECT の優先順位で一意決定。C4 併存時の decision memo は second look まで保留。SIGN-FLIP/CONFOUNDED は combo 単位の付帯フラグに再定義 |
| M7 | α 会計「q₁+q₂ ≤ 0.10 級 = house 同水準」は算数誤り (実際は ~0.20)、誤った保証で user が LOCK 承認する構図 | §5/§4.1/§4.2: 誤記述を削除し、**look 毎 q=0.05 に分割** (合計 ≤0.10 を実際に保証) を採用。Gate 2 の BH も q=0.05 に整合 |
| M8 | second look spec が「同一 spec」の一文だけで、累積/増分・対象 combo・REJECT-F 消失・postpone 時の期日スライドが未固定 | §4.4/§7: 累積標本 (burn-in 後〜12-30)、対象 = first look C3 combo のみ (BH m=\|C3\|)、second look の Gate1 通過+EV≤0 は REJECT-F と同処置、着地は PASS/REJECT-F/REJECT のみ、postpone は cutoff/verdict/窓終端を同幅スライド (burn-in・窓開始不変) と全て固定 |
| M9 | Gate 2 power の SE 1.5–1.8p は h=4h のみ成立 — h=24h は SE 5–9p / 検出可能 +13–22 p/t で first look 通過は構造的に不可能なのに非開示 | §5: Gate 2 power を horizon 別に分離して記載。h=24h の first look の役割を「符号スクリーンのみ」と再定義 (second look 経由が主線と明記) |
| M10 | 8 block の MBB で BH 最小有効閾値 p≈0.017 の tail 推定は反保守 (偽 PASS 側)、開示だけで binding 判定に使う設計 | §4.1: Ibragimov–Müller 型 t 検定 (5 営業日 × 8 block、df=7) を併設し、combo の Gate 1 p = max(p_MBB, p_IM) の二重検定化。second look (block ≈20) は bootstrap 単独に戻すことも今固定 |
| M11 | 市場時間の固定 UTC 定義 (Sun/Fri 21:00) が DST 非対応 — second look 窓内 (2026-11-01 以降) で事実として誤りになり、LOCK 後に直せない spec バグが焼き込まれる | §2.2: 市場時間を America/New_York Sun 17:00–Fri 17:00 (DST 追随、日付毎 UTC 変換) に再定義。金曜 2h 除外 (NY 15:00–17:00)・age 計測・週末除外・daily bar 境界を全てこの定義に紐付け。DST 跨ぎ週の unit test を必須化 |

**minor 反映** (全て妥当と判断し反映): NA を挟む交差/hysteresis のリセット規約 (§3.4) / cutoff − h censoring の IC・EV・coverage への一律適用 (§2.3) / IC 前方リターン終端の open 一意化 (§2.3) / cycle 証跡窓の因果方向固定 (t−90min, t] (§2.2) / pairs_eff 2.5→2.0 の算数訂正と power 再計算 (§5) / second look 累積標本の明文化 (§4.4) / Δskew 差分間隔の明示 (§2.5-7、M2 と統合)。

## §7 registry・期日

| イベント | 日付 (固定、データ非依存) | registry エントリ |
|---|---|---|
| LOCK 決裁期限 | **2026-07-17** (蓄積が進むと観測前性が減衰するため短期) | `e1-prereg-lock-decision-stale` (本 DRAFT と同一 PR で登録、`tools/prereg_trigger_watch.py` が毎日監視 — T5 教訓: 監視主体の併設) |
| データ cutoff #1 | **2026-10-08 (t0+12 週)**[^13] | — |
| **first look verdict 期日** | **2026-10-15** | LOCK 時に `e1-prereg-verdict-deadline` へ置換 |
| データ cutoff #2 (UNDERPOWERED 時のみ) | **2026-12-30 (t0+24 週)**。標本 = **burn-in 後〜cutoff #2 の累積** (§4.4)。年末薄商い (2026-12-19〜2027-01-02) の新規 event は事前宣言で除外 (摩擦判定値が無効化する期間。分析上の a priori 除外であり Shadow 蓄積削減ではない) | UNDERPOWERED verdict 時に `e1-prereg-second-look` を登録 |
| **second look verdict 期日** | **2027-01-06** (同一 spec・新自由度ゼロ・対象は first look C3 combo のみ、stage-2 §4 UNDERPOWERED 前例と同型) | 同上 |

- 品質 gate 起因の postpone (§2.5-3) は look を消費しない (4 週×1 回限り、機械条件のみ)。**発動時は cutoff・verdict 期日・評価窓終端を同幅 (4 週) スライドし、burn-in と評価窓開始は不変** (結果観測後にどちらとも解釈できる余地を残さない)。
- **成果物**: 判定器 `tools/e1_positioning_prereg_eval.py` (LOCK 後実装、seed 固定。LOCF resampler / rank タイ規約 / DST 跨ぎ週 / ATR / join / canary leak test を `tests/` に pin してから verdict データに触れる) / 凍結 artifact + 全統計・trade list JSON を `raw/bt-results/e1_prereg_*.json` へ / verdict は本文書 §8 追記 + session log + roadmap 反映。
- LOCK 時の追記事項: confirmatory 7 ペアの t0 台帳 (§2.4) / **stale cap の有効モード確定 (last_verified_at 実装済み or fallback、§2.2)** / `e1-positioning-ingest-freshness` の鮮度監視再開。
- **必須インフラ (LOCK 前、rule:R3)**: per-instrument `last_verified_at` の DB 永続化 (§2.2 — stale cap の主定義が依存)。**推奨インフラ (LOCK と独立、rule:R3)**: poll cycle heartbeat (`last_cycle_at`) の DB 永続化 — §2.5 coverage gate の測定精度に直結。

## §8 VERDICT (placeholder)

> **未執行。** first look: データ cutoff 2026-10-08 → verdict 期日 2026-10-15。
> 執行時にここへ追記する: 品質 gate 判定表 (stale cap モード・NA 分布・量子化粒度含む) / Gate 1 pooled IC 表 (6 combo、p_MBB / p_IM、BH-FDR q=0.05 判定) / Gate 2 EV 表 (time-exit / first-touch / stress、trade N) / combo 排他分類表 (C1〜C5 + フラグ) / ナイフエッジ 4 点 / confirmatory 符号表 / 実測 ρ̄ と N_eff 事後検証 / 全体 verdict (PASS / UNDERPOWERED / REJECT-F / REJECT / DEFERRED) と固定分岐の執行記録。

---

## 裁定脚注 (3 設計案の矛盾点と裁定理由)

[^1]: **Δskew (S2) の採否**: 案 1 は「水準と情報重複、多重性だけ増える」として verdict から除外、案 2/3 は採用。裁定 = **採用**。第一種過誤は BH-FDR (look 毎 q=0.05、§5 α 会計) の family 補正で制御されるため「第一種過誤優先」原則に抵触せず、JIFMIM の一次主張は order **flow** (= 変化) であり除外は文献整合性を損なう。KB §9 も「水準/変化」を既定義。power コストは §5 で正直に織り込んだ。

[^2]: **週末処理**: 案 1 は週末跨ぎ LOCF・跨ぎエントリーとも除外、案 2/3 は market-time age + bar-count (跨ぎ保持)。裁定 = **market-time 方式** (市場時間の定義自体は敵対的レビューで NY 17:00 基準 DST 追随に固定 — §2.2)。市場閉鎖中は建玉が動かず payload 凍結が正常のため LOCF は正確 (除外は情報を捨てるだけ)。保有中のギャップは現実の保有と同じくリターンに含め、裁量トリムを避ける。ただし案 2 の「金曜クローズ前 2h の新規 event 禁止」は採用 (ギャップ直撃 entry は摩擦判定値の前提外)。

[^3]: **cycle 証跡の窓**: 案 1 = 2h、案 3 = 90 分。裁定 = **90 分** (障害検出が早い方が欠測を「無変化」と誤認するリスクが小さい = データ品質の保守側)。窓の方向は敵対的レビューで (t−90min, t] の因果方向に固定 (§2.2)。

[^4]: **confirmatory family の役割**: 案 1 = 条件付き PASS 必須条件、案 2 = 記述 + 有意逆転で user 裁定、案 3 = 符号表のみ。裁定 = **データが揃う場合は PASS 必須条件 (案 1) + 有意逆転の user 裁定条項 (案 2)**。out-of-family 複製の要求は偽 PASS 抑制 = 第一種過誤優先の直接適用。揃わない場合の実装 pre-reg への繰延で「検定力不足の複製検査が PASS を恣意的に止める」逆リスクも封じた。

[^5]: **coverage 閾値**: 案 1/2 = 90%、案 3 = 85%。裁定 = **90%** (多数派かつ厳格側 — 品質の緩い gate は「欠測だらけの窓で出た偽シグナル」を通しやすい)。coverage の「有効」定義は敵対的レビューで検証証跡基準に再鍵付け (§2.2/§2.5-1)。

[^6]: **正規化窓**: 案 1 = rolling 20 営業日、案 2 = expanding (自由度ゼロ)、案 3 = rolling 10 営業日。裁定 = **rolling W=20 固定**。expanding は案 2 自身が認める burn-in 直後の縮退 (event 定義が一時ブレイクアウト検知化 = 評価窓内でシグナルの質が不均質) があり、12 週 verdict では判定を汚す。rolling は Myfxbook 構成ドリフトへ自動適応。W=10 より W=20 が擬似 extreme (小窓ノイズ由来の交差) を減らす保守側。W は grid にせず単一固定、感度は Secondary。

[^7]: **ホライズン grid**: 案 2 のみ 72h を secondary に持つ。裁定 = **{4h, 24h} の 2 点 (多数派)**。72h は first look 実効 N が絶望的で「検定に載らない仮説を family に足す」だけ — 過剰多重性禁止のハウス規律に従い削除。

[^8]: **摩擦判定値の相違** (USD_CAD/USD_CHF 2.5 vs 3.0、NZD_JPY 4.0 vs 4.5、EUR_AUD 4.0 vs 4.5): 裁定 = **全て高い方**を採択 (net EV の閾を上げる = PASS を難しくする = 偽 PASS 抑制)。AUD_JPY は stage-2 前例値 3.125 で統一。

[^9]: **stress 定義**: 案 1 = +25%、案 2 = ×1.5、案 3 = +1.0p。裁定 = **max(×1.25, +1.0p)** — 低摩擦ペア (EUR_USD 2.0p) では +1.0p が、高摩擦ペア (GBP_USD 4.53p) では ×1.25 が強く効く合成で、全ペアで実質的な stress を保証。×1.5 は「限界的な真エッジを stress だけで落とす」偽陰性側に過大 (stress は点条件であり検定ではないため、判定値 ±25%/±1p の不確実性の無害化が目的)。

[^10]: **null 生成**: 案 3 は circular shift、案 1/2 は centered bootstrap。裁定 = **per-combo 中心化 block bootstrap に一本化** (Gate 1/2 で同一機構を使い、EV 側 (trade 単位) にも自然に延びる。shift null は panel の全ペア同時 resample と併用すると実装が二重化しバグ面積が増える)。first look の block 数の粗さは敵対的レビューで Ibragimov–Müller 併設 (§4.1) により手当て。

[^11]: **多重性手法**: 案 1 = Westfall–Young max-T (FWER)、案 2/3 = BH-FDR q=0.10。裁定 = **BH-FDR** — ハウス規律の明示標準であり、階層ゲートキーパー (Gate 2 は Gate 1 通過時のみ・Stage B は判定外) が選択効果を構造側で処理する。max-T はより強い制御だが、ハウス標準からの逸脱に足る理由がない (逸脱自体が設計自由度)。**q の水準は敵対的レビュー (α 会計の算数誤り指摘) を受け、look 毎 q=0.05 分割 (2 look 合計 ≤0.10 = house 同水準) に確定** (§5)。

[^12]: **EV の有意性要求**: 案 2 は「N が薄く非現実的」として点推定のみ、案 1/3 は p ≤ 0.05 要求。裁定 = **p ≤ 0.05 要求 (第一種過誤優先の直接適用)**。点推定正 + 検定不達は UNDERPOWERED 分岐 (§4.4 C3) が事前固定の受け皿として存在するため、検定要求が真エッジを恒久棄却することはない — 時間コストのみ発生し、それは §5 で宣言済み。

[^13]: **期日の統一**: cutoff は案 1 = 10-07、案 2/3 = 10-08。verdict は 10-14/10-08/10-15。裁定 = **cutoff 2026-10-08 (t0+12 週ちょうど) / verdict 2026-10-15 (cutoff+7 日 — 品質 gate → 凍結 → 判定器実行の実務リード)**。second look は cutoff 2026-12-30 / verdict 2027-01-06。年末除外窓は最も広い 12-19〜01-02 (案 2) を採択 (薄商い期の摩擦非定常はより長く見る方が保守側)。

**残存リスク (統合、verdict 時に再掲)**: 検出力不足が既定路線 (modal = UNDERPOWERED、M1 タイムラインに最短 ~6 ヶ月の E1 依存遅延。h=24h は first look で Gate 2 構造的不達 — §5) / JPY 脚 4/6 の実効独立性 (pairs_eff = 2.0 の前提 ρ̄=0.4 の外れ) / 「worker/ペア障害 ≒ 無変化」の識別は last_verified_at 永続化 (§2.2 主モード) で解消予定 — fallback モード時は estimand 制約として §2.2 に宣言済み / Myfxbook community 構成の非定常性・単一プロバイダの不可逆欠損 (rate limit 100 req/24h、IP-bound session) / avg 価格の意味論未検証 (S3 は操作的定義) / skew の量子化粒度が粗い場合の event 希薄化 (§3.1 — 裁量調整禁止のため N 減としてそのまま顕在化、C3 経由で受け止める) / crossing 発生率仮定 (2–3/週/ペア) 未検証 → N gate は §4.4 排他分類 (C3 適格性は N 不問) に接続済み / 観測窓が 2026 夏〜秋の単一マクロレジーム / 20 分 poll × 15m bar の位相ずれによる最大 ~15 分の執行ラグは短命効果を消す方向 (偽陰性側) のバイアス。


---

## 付録 A: ペア別 t0 台帳 (§2.4 / §7 LOCK 時追記事項の先行確定、2026-07-16 実測)

本番 `/api/positioning/export` の instrument 別最初の snapshot_time (実測、fetch 時刻):

| family | ペア | t0 (first snapshot) |
|---|---|---|
| primary | USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, AUD_JPY | **2026-07-16T06:33:31Z** |
| confirmatory | AUD_USD, NZD_USD, USD_CAD, USD_CHF, NZD_JPY, EUR_AUD, EUR_GBP | **2026-07-16T07:51:18Z** (PR #91 デプロイ) |

primary/confirmatory の family 割当は §2.4 のとおり固定 (入れ替え禁止)。
