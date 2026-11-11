# 🔒 Pre-registration LOCK: MoF 円買い介入モダリティ — 観測前 forward pre-reg (rule:R1 stage-1)

**🔒 LOCKED 2026-07-24 — 以降、予測・rule・candidate list・h*・ゲートの変更禁止。verdict は Q2-2026 日次開示着地 +10 日以内 (backstop 2026-09-30)。**
LOCK 手続き: 起案 (strategy-dev agent) → explore 実行 + rule 校正 + §5 凍結記入 (別 agent、`--skip-2026` 規律) → **敵対的レビュー 1 本 (verdict: ISSUES — コア規律・算術は全検算一致 + git タイムラインで事前宣言を客観確認、必須 3 + 任意 5)** → 全反映 (k_eff 規約凍結 / anchor データ存在日 roll / P-10 attestation + forward 計算禁止) → **期限 08-05 の 12 日前倒しで即日 LOCK** (file-drawer 裁量の窓を閉じるため)。executor = claude。

**起案日**: 2026-07-24
**起点**: W1-F1 データ取得 `reports/mof_intervention_w1f1-2026-07-24.md` (+ `data/external/mof_interventions.csv`) / [[hypothesis-catalog-2026-07-24]] **台帳 family #4 (mof_intervention)** / [[edge-dev-postmortem-2026-07-24]] 処方箋 §6
**様式踏襲**: [[ws3-asymmetry-oos-prereg-2026-07-09]] / [[exit-repair-tp-sl-prereg-2026-07-07]]
**承認**: user ミッション委任 (2026-07-08) + 探索最大化指示 (2026-07-24) に基づく純研究。**live パラメータ変更ゼロ。tradeable 化 (Variant B real-time / Variant C 開示時点) は本 verdict PASS 後に stage-2 別 pre-reg + user 最終承認**

---

## 1. 背景と機会 (なぜ今 LOCK するのか)

- MoF 日次介入史 383 events (1991-2024) のうち、現代円買いレジーム (2022+、現行マイクロストラクチャ・摩擦レジームと整合) は **7 日 / 3 エピソードのみ** (2022-09-22 / 2022-10-21,24 / 2024-04-29, 05-01 / 2024-07-11,12)。temporal explore/OOS split は不可能 (W1-F1 verdict)。
- **決定的機会**: 月次開示により **2026-04-28〜05-27 窓に総額 ¥11,734.9bn (¥11.73 兆、単一窓として史上最大) の介入が存在する**ことが既知。しかし**日次内訳・ペア・方向は Q2-2026 四半期開示 (~2026-08 推定、Q1-2026 開示日 2026-05-12 のラグから外挿) まで非公開**。
- 開示前に仮説・測定仕様・事前予測を LOCK すれば、開示される日次データ (推定 2〜5 event days) が **genuine OOS ラベル**になる。価格データは既観測 (公開) だが、「どの日が介入日か」という**ラベルが未観測** — これが OOS の情報源である (§7 peek 会計に厳密に記録)。
- headroom: 2022/2024 介入日の日中レンジは 300〜550p 規模 vs USD_JPY RT 摩擦 2.14p (理論) / 1.30p (実測フロア) = **100x+** (カタログ score 66 の根拠)。凍結探索プロトコルの headroom≥10x を大幅充足。

## 2. 仮説と estimand (厳密定義)

### 2.1 仮説

- **H1 (naive 形)**: MoF 円買い介入日およびその後、USDJPY は下方 drift (円高方向) を示す。すなわち (a) 介入日は day 粒度の価格 signature (大幅下方日次変動) で識別可能であり、(b) 介入日の翌東京日 open を anchor とする forward 純移動は SELL 方向 (負) に偏る。
- **H0**: (a) 介入日は窓内の他営業日と price signature で区別不能 (識別 rule のヒットは偶然)、かつ (b) forward 純移動は placebo と区別不能。
- **校正条項 (LOCK 前確定)**: (b) の方向・持続は explore (§4) の既知 7 日で校正して凍結する。既知事例には初動急落後の retracement (2022-09-22 型) が含まれるため、explore の median 符号が naive H1 と逆 (forward は戻す) の場合、**校正形 (explore 符号) を事前予測として凍結し、その旨を LOCK 追記に明記する**。OOS 接触前の校正であり、リークではない。

### 2.2 Estimand

| 項目 | 定義 (凍結) |
|---|---|
| データ | `data/cache/massive/USD_JPY_15m*.parquet` (Massive 12y、mid)。日次集計は UTC-day バー (= 09:00 JST → 翌 09:00 JST = **東京営業日 d** の慣行と一致。MoF の日付は JST 営業日でこの区切りと整合、深夜 NY 時間帯介入 (2022-10-21 23:40 JST 型) も同一バー内) |
| event day d | MoF 開示の介入日 (day 粒度、intraday 時刻なし) |
| anchor t0(d) | **d の翌営業日の 00:00 UTC (= 09:00 JST) 以降の最初の 15m バー open**。roll forward は**データ存在営業日カレンダー上**で行う (週末・休場に加え、parquet バー 0 本のデータ欠損日もスキップ — 敵対的レビュー必須 #2 で凍結。例: D に 2026-05-06 が含まれる場合、翌営業日 05-07 は欠損のため anchor は 05-08 の最初のバー open)。horizons のカウントも同カレンダー。event-day 内 anchor は lookahead のため全変種で禁止 (W1-F1 caution a) |
| horizons | h ∈ {**1d, 2d, 5d, 10d**} (東京営業日カウント、同じ 00:00 UTC 境界) |
| 純移動 | net_h(d) = mid(t0+h) − mid(t0) [pips, 0.01 JPY]。SELL 方向有利 = 負 |
| MFE/MAE | [t0, t0+h] 内の SELL 方向 MFE/MAE (バー粒度) |
| swap | h5/h10 は short USDJPY のキャリー純額を控除した net-after-carry を併記 (**判定は gross 符号、swap-net は記述**)。swap 実測値は LOCK 時に OANDA financing / e20_rates_ingest 配管から記録 (E20 S2 棄却 (PR #112) は estimand 別で配管残置の流用は可 — MEMORY `project_e20_rate_differential_s2_rejected`) |
| 識別 rule (E-A 用) | 東京営業日バー T(d) の同日 OHLC のみを使う関数 (real-time 計算可能 = anchor 時点で判定可): **candidate(d) = 1 ⟺ close/open − 1 ≤ −Y% かつ range(d) ≥ X × trailing-20d median range**。X, Y は §4 explore (2022/2024 の 7 日 + その周辺 placebo のみ) で「7 日中 ≥6 を捕捉しつつ周辺 false positive 最小」の最緩値として校正し、LOCK で凍結。**2026 窓を見ながらの rule 反復は禁止** (ラベル未観測でも事前信念の混入を避ける) |

## 3. 変種の分離 (tradeable / 非 tradeable)

| 変種 | 定義 | tradeable 性 | 本 pre-reg での役割 |
|---|---|---|---|
| **A: event-day 同日** | 介入日 d 当日の日次リターン・レンジ | **非 tradeable** — 介入は価格に誘発される endogenous 事象で、同日リターンには介入効果とトリガー文脈が混在。covert 介入 (2022-10, 2011-11) はリアルタイム公式確認なし | **記述のみ** (E-A 識別と機構記述に使用。EV 主張には使用禁止) |
| **B: 翌東京日 anchor forward** | t0(d) から h ∈ {1d,2d,5d,10d} | **準 tradeable** — 識別 rule (同日 OHLC のみ) が anchor 時点で計算可能なら執行可能。E-A PASS が real-time 検知可能性の実証を兼ねる | **本 pre-reg の主対象** (E-C) |
| **C: 開示時点リアクション** | 月次/四半期**公表時点** (公表スケジュールは既知) への反応 — 公表額 vs 期待のサプライズ | **完全 tradeable** (公表時刻は ex-ante 既知) | **本 pre-reg の対象外** — verdict PASS 時の stage-2 候補として分離起案 (E7 サプライズ設計の類型) |

## 4. Explore プロトコル (LOCK 前に実行、OOS 非接触)

- **対象**: 既知の現代円買い 7 日 / 3 エピソード (2022-09-22, 2022-10-21, 2022-10-24, 2024-04-29, 2024-05-01, 2024-07-11, 2024-07-12)。1991-2021 の円売り 319 日・旧レジームは方向逆・マイクロストラクチャ別時代のため explore 母集団に混ぜない (W1-F1 verdict)。文脈参照のみ可。
- **測定**: §2.2 estimand どおり per-day net_h / MFE / MAE (h ∈ {1d,2d,5d,10d})、swap-net (h5/h10)。
- **Null**: matched placebo days (同一ペア・同一曜日・trailing-20d realized vol quintile 一致、event±10d 除外) に対する **episode-block permutation** (エピソード = gap≥30d クラスタ、日 (day) は episode 内で 1 draw 扱い)。**有効 N≈3 のため記述統計としてのみ報告 — Bonferroni 級の主張は不可能と事前宣言**。
- **識別 rule 校正**: §2.2 の (X, Y) を 7 日 + 周辺 placebo のみで校正。2026 窓への適用は校正完了後に**一回だけ**行い、candidate list を凍結。
- **成果物**: 本文書 §5 の予測テーブルに数値を記入して LOCK + `raw/bt-results/` に explore JSON 保存。

### 4.1 Explore 実行記録 (2026-07-24 執行 — §4 成果物の記入。ゲート定義は不変更)

実行: `tools/mof_intervention_explore.py` / JSON: `raw/bt-results/mof_intervention_explore-2026-07-24.json` (+ `bt-results/` 同名) / 詳細: `reports/mof_intervention_explore-2026-07-24.md`。データ = `USD_JPY_15m_2014_2026.parquet` (2013-12-29..2026-07-02)。

**per-day net_h (pips、負 = SELL 有利) — §2.2 estimand どおり**:

| h | median | [P25, P75] | 負符号 | MFE med | MAE med | episode 平均 (E1/E2/E3) |
|---|---|---|---|---|---|---|
| 1d | +3.5 | [−53.0, +126.4] | 3/7 | 90.5 | 114.0 | +53.3 / −77.5 / −4.8 |
| 2d | −9.7 | [−133.1, +21.5] | 4/7 | 112.9 | 114.0 | −8.2 / −133.1 / −0.7 |
| 5d | −73.3 | [−97.8, +2.1] | 5/7 | 292.0 | 114.0 | +73.3 / −145.8 / −97.8 |
| 10d | −180.8 | [−319.8, −43.6] | **6/7** | 424.8 | 114.0 | **−9.0 / −95.0 / −433.8 (3/3 負)** |

- episode-block permutation (3 blocks、matched placebo 同曜日+vol quintile、event±10d 除外、N=10,000、seed=20260724): h5 片側 p=0.078 / h10 片側 p=0.099 — **事前宣言どおり記述統計のみ、検定主張なし**。
- swap (h5/h10) は政策金利差**推定** (2022: 3.18% / 2024: 5.28% 年率) で net-after-carry 併記 (h10 で 5/7 負のまま)。OANDA financing **実測**の記録は §9 LOCK 手順 step 3 に残置。
- エピソード初日 anchor 変種 (h10): +277.5 / −9.1 / −454.5 — 初日粒度では 2022-09 retracement が正。§8.2 の有効 N=1 エピソード拘束を verdict で再掲。
- 識別 rule 校正 (2022/2024 のみ、事前宣言 grid Y∈{0.25..2.00 step 0.25}% × X∈{1.5..4.0 step 0.5}、機械的基準 hits≥6→FP最小→hits最大→最緩): **凍結 (X, Y) = (2.0, 0.25%)** — 敵対的レビューが grid を独立再評価し feasible 2 点から一意に同値を再導出 (裁量ゼロ確認、git タイムラインで基準宣言 (commit cc1f9b45 19:54) → explore 実行 (20:17) の先行も客観確認)。hit 6/7 (2022-10-24 は close/open +0.86% で構造的捕捉不能 — covert 追撃日)、FP 39/775 = **5.03%** (event±10d 除外版 **36/717 = 5.02%** — 旧記載 5.06% は転記誤りでレビュー #4 訂正)。binding は 2024-07-12 (co_ret −0.258% / ratio 2.18) — ±20% 摂動 (校正データのみ) で同日が脱落し 5/7、他 5 日は margin 大 (co_ret ≤ −1.17% / ratio ≥ 4.69)。2026 窓側の摂動チェックは §8.3 どおり verdict 時。
- エピソード数の規約統一 (レビュー #5): **正準 = gap≥30d クラスタで 3 エピソード** (2022-09-22↔10-21 は 29 日差で同一 block — knife-edge であることを明記)。§5.4 の「(総額, 日数) 4 グループ」は**開示四半期グループ**であり別の区切り (E-D の記述にのみ使用、検定非使用)。permutation の null 非対称 (obs = episode 内 2-3 日平均の median vs null = 単日 draw) は p を保守側に振る — 記述専用のため許容、引用時注意 (レビュー #7)。

### 5.0 有効性ゲート G0

Q2-2026 四半期開示で 2026-04-28..05-27 窓内に ≥1 日次イベントが帰属されること。**LOCK (2026-08-05) より前に日次内訳が公開された場合、OOS は無効 — 本 pre-reg は破棄し family は explore-only に降格** (verdict 記録は残す)。

### 5.1 E-B: レジーム同定 (validity gate)

**予測 (DRAFT 値、LOCK で凍結)**: 開示ペア = **USD/JPY**、方向 = **sell_USD_buy_JPY (円買い)**。
根拠 (既観測データのみ): 窓内 USDJPY は YTD 高値圏 160.72 から 04-30 に −1.99% 急落 (160.18→156.99) — 2022/2024 円買い介入と同型の価格文脈 (§7 peek 会計 P-6)。
**不成立時 (円売り・他ペア等) → verdict = NO-TEST**: 円買い仮説の OOS データが存在しなかったと記録し、family は次の円買いエピソードまで park (ペナルティなし、台帳に記録)。

### 5.2 E-A: 日次識別 (Primary、唯一の検定エンドポイント)

- 凍結済み candidate list S (identification rule の 2026 窓への一回適用結果、**|S| ≤ 5 に事前上限**) vs 開示 daily list D (|D| = k)。
- **Null**: D は窓内 FX 営業日 (M ≈ 22 日、LOCK 時に確定) からの一様ランダム k 日抽出。**p = 超幾何 P(|S∩D| ≥ 観測 overlap)**。
- **PASS 条件: p ≤ 0.10 (one-shot、再計算・rule 変更禁止)**。
- 解釈の事前拘束: E-A は**識別可能性** (day 粒度 signature の実在 = Variant B の real-time 検知前提) の検定であり、**edge の検定ではない** (endogeneity: 介入は大幅円高日に打たれるため、識別成功は「介入日が極端日である」ことの確認を含む)。

**確定値 (2026-07-24 explore 執行で記入 — 以後変更禁止)**:
- 凍結識別 rule: **(X, Y) = (2.0, 0.25%)** (校正は 2022/2024 のみ — §4.1)。
- 2026 窓への一回適用 (2026-07-24、これで接触消費済み): **M = 21** 営業日 / **S = {2026-04-30, 2026-05-06}**、**|S| = 2 ≤ 5** (上限内)。04-30: co_ret −1.993% / ratio 7.70、05-06: co_ret −0.726% / ratio 3.63。
- データ注記 (敵対的レビュー必須 #1 で凍結): 2026-05-07 (木) は parquet バー 0 本 (ソース欠損、休場ではない) → 母集団外で M=21。**k 規約 (凍結): 検定に用いる k は k_eff = |D ∩ 母集団 (M=21 営業日)|** — S が母集団上でしか定義されない以上、null (一様 k 日抽出) も同母集団から draw するのが統計的に整合。開示 D が 05-07 を含む場合、当該日は k_eff から除外され、その事実を verdict に明記する。⚠️ 旧記述「PASS に不利な方向の欠損」は**撤回** — 欠損の作用方向は不定 (05-07 が candidate になり得たなら |S|=3/M=22 で閾値が変わっていた経路もある — レビュー検算済み)。**バックフィルは実施しない** (2026 窓への二度目の接触・データソース選択の自由度を作らないため。事前宣言)。
- 超幾何閾値 (M=21, |S|=2, α=0.10、k は k_eff): k_eff=1 → overlap≥1 (p=0.0952) / k_eff=2..5 → **overlap≥2 必須** (p = 0.0048 / 0.0143 / 0.0286 / 0.0476)。overlap=1 は k_eff≥2 で不合格 (p 0.186–0.429)。**k_eff≥8 では最大 overlap=2 でも p>0.10 = E-A 構造的 PASS 不能** (現代エピソード日数 1-2 日/開示から k∈[2,5] 予測、k_eff≥8 は E-D 予測の大外れとして記録)。**E-D 予測 k∈[2,5] の下では E-A PASS ≒ 「04-30 と 05-06 の両方が介入日」** — §8.3 のナイフエッジ明記対象。

### 5.3 E-C: forward drift 確認予測 (sign-based scorecard、検定なし)

- **予測 (LOCK 時に explore から機械的に生成して凍結)**:
  - primary horizon h* = explore 7 日で符号が最も一貫する h (tie-break: |median| 最大)。以後変更禁止 (WS3 pre-reg §2 と同じ拘束)。
  - 予測符号 = explore median の符号 (§2.1 校正条項)。
  - 記述 band = explore per-day net_h* の [P25, P75]。
- **PASS 条件: 開示 D の median net_h*(d) が予測符号と一致** (band 内かは記述のみ)。k≈2-5・1 エピソードで検定力ゼロのため sign-based に限定し、p 値主張はしない。
- 副次 (記述のみ、判定不使用): 全 h の net / MFE / MAE、swap-net、エピソード初日 anchor 変種 (episode-level 相関の感度)。

**生成結果 (2026-07-24 explore から機械的に生成 — 以後変更禁止)**:
- **h\* = 10d** (符号一貫 6/7 で最大、tie-break 不要。episode 粒度でも 3/3 負 — §4.1)。
- **予測符号 = 負 (SELL 方向)** — explore median −180.8p。naive H1 と同方向であり §2.1 校正条項の反転凍結は不要。
- 記述 band = **[P25, P75] = [−319.8, −43.6] pips**。

### 5.4 E-D: 構造予測 (Secondary、記述のみ)

**予測 (DRAFT 値、LOCK で explore から最終化)**: 介入日数 k ∈ [2, 5] / 最大単日額 ≥ ¥3.0T。
根拠: 現代 4 エピソードの (総額, 日数) = (2.84T, 1) (6.35T, 2) (9.79T, 2) (5.53T, 2)、単日最大 2.37〜5.92T。総額 11.73T は史上最大 → 少数日集中を予測。判定に不使用 (行動予測であり価格モダリティではない)。

### 5.5 全体 verdict (固定分岐)

| verdict | 条件 | 帰結 |
|---|---|---|
| **PASS** | G0 ∧ E-B ∧ E-A(p≤0.10) ∧ E-C(符号一致) | **stage-2 へ**: (i) Variant B real-time 検知型 (識別 rule = 検知器) の次エピソード forward 設計、(ii) Variant C 開示時点リアクション設計 — いずれも別 pre-reg + user 最終承認。**PASS ≠ edge claim ≠ live 昇格** |
| **PARTIAL** | G0 ∧ E-B ∧ (E-A xor E-C) | family は prior 減で park。**次の円買いエピソード 1 回限り**の同一仕様再判定 (新自由度ゼロ、htf_fb recheck 型)。registry 提案は §9 |
| **FAIL** | G0 ∧ E-B ∧ ¬E-A ∧ ¬E-C | family クローズ: 円買い介入は day 粒度で再現可能な signature/drift を持たないと記録。**同型再試行禁止**を MEMORY/台帳に記録 |
| **NO-TEST** | ¬G0 または ¬E-B | 仮説未検証と記録、park (§5.1) |

## 6. 多重検定の扱い (グローバル台帳 family #4)

- 本 pre-reg は [[hypothesis-catalog-2026-07-24]] (グローバル多重検定台帳) **m=12 の family #4 (mof_intervention)** の confirmatory 段。
- **within-family**: 検定エンドポイントは E-A の 1 本のみ (α=0.10 one-shot)。E-B は validity gate、E-C/E-D は検定なし scorecard — within-family 多重性は発生しない。horizon 4 点は E-C の記述にのみ現れ、h* 事前固定で選択自由度を封鎖。
- **cross-family**: 有効 N=1 エピソードのため、PASS でも「モダリティ実証 (記述級)」であって Bonferroni 級 edge 主張には決してカウントしない。edge 主張・live 経路は stage-2 pre-reg (Rule 1: 365d BT or Live N≥30 + Bonferroni) の責務。台帳には verdict を PASS/FAIL 問わず追記する (台帳運用ルール)。

## 7. Peek 会計 (LOCK 時点までに観測済みの全情報)

| # | 情報 | 状態 |
|---|---|---|
| P-1 | MoF 日次介入史 383 events (1991-05-13〜2024-07-12) — 既知 7 円買い日を含む | **観測済み = explore 専用** (`data/external/mof_interventions.csv`) |
| P-2 | 2026 窓 04-28..05-27 の**月次総額 ¥11,734.9bn** | **観測済み・記録** (月次開示 20260529.html) |
| P-3 | 隣接窓 03-30..04-27 = 0、05-28..06-26 = 0、2025 全四半期 = 0 | 観測済み |
| P-4 | Q1-2026 四半期日次開示の公表日 2026-05-12 (開示ラグ外挿の根拠) | 観測済み |
| P-5 | USDJPY 価格ヒストリ全期間 (2026 窓を含む、parquet) | **観測済み** — OOS の情報源は価格ではなく「どの日が介入日か」の**ラベルのみ** |
| P-6 | 本 DRAFT 起案時の価格文脈クエリ (2026-07-24 実行): 週次 OHLC 2026-03-15..06-08、窓内 high/low = 160.72/155.02、窓内下落日上位 (**最大 2026-04-30 の −1.99%**、次点 05-06 −0.73%) | **観測済み・記録** — E-B 方向予測の根拠。E-A の統計的価値は凍結 rule の適用結果に依存し、この観測自体は candidate list を確定しない |
| P-7 | 2026 窓の**日次内訳・ペア・方向・日次金額** | **未観測 = OOS** (Q2-2026 四半期開示 ~2026-08) |
| P-8 | explore 記述統計 (7 日の net/MFE/MAE) | **観測済み = 2026-07-24 実行** (§4.1 / `raw/bt-results/mof_intervention_explore-2026-07-24.json` / `reports/mof_intervention_explore-2026-07-24.md`)。placebo/校正の接触は 2022-01-01..2024-12-31 のみ |
| P-9 | 2026 窓 daily OHLC (04-28..05-27) + trailing-20d median range 入力 (窓直前営業日) — **凍結 rule (X=2.0, Y=0.25%) の一回適用** (2026-07-24, `tools/mof_intervention_explore.py`) | **観測済み・接触消費済み** — 産出は S={04-30, 05-06}, M=21 の凍結のみ (§5.2)。rule の 2026 窓への反復調整なし (開発 run は `--skip-2026` で窓非接触)。04-30 の −1.99% は P-6 と整合、新規裁量情報なし。2026-05-07 はデータ欠損 (バー 0 本) で母集団外 |
| P-10 | 2026 candidate 日 (04-30, 05-06) の **forward net_h (E-C 対象量)** | **未計算 — attestation (敵対的レビュー必須 #3)**: explore 実行は `--skip-2026`、敵対的レビューも意図的に計算を回避、main セッションも未計算。**開示着地後の verdict 実行まで、いかなる主体もこの量を計算することを禁止** (LOCK は 2026-07-24 即日執行 — LOCK 任意期間中の「先読みして不利なら LOCK しない」file-drawer 裁量の窓を閉じるため、期限 08-05 の 12 日前倒し) |

**リーク経路の事前封鎖**: (i) 識別 rule の校正は 2022/2024 データのみ、2026 窓への適用は一回 (§2.2)。(ii) E-C 予測は explore からの機械的生成 (§5.3) で裁量ゼロ。(iii) 06-27..07-28 窓の月次開示 (~07 月末見込み) が LOCK 前に着地しても月次総額のみで日次ラベルは含まれない — 着地したら peek 会計に追記する (G0 には抵触しない)。

## 8. ナイフエッジ 3 点検査 (verdict 時必須 — T11 lesson、事前宣言)

1. **メカニズム整合**: E-A のヒットが rule の両構成要素 (下方リターン ∧ レンジ拡大) どおりに成立しているか (片側だけの偶然ヒットを分解確認)。E-C の符号一致が MFE 側の実体で成立しているか (MAE 崩壊による見かけの符号でないか)、絶対量が摩擦 (RT 2.14p) の 10 倍以上か。
2. **擬似反復**: 開示介入日が連続日クラスタの場合、日レベルの一致を独立事象として数えない — **有効 N = 1 エピソード**であることを verdict に明記し、超幾何 p は「日選択の null」に対する解釈に限定。forward 窓の重複 (連日介入で h 窓が重なる) は per-day / episode-初日 の両建て報告で感度確認。
3. **閾値リーク / 格子点**: 識別 rule (X, Y) を ±20% 摂動させて candidate list が激変しないか (knife-edge rule の排除)。E-A の p が overlap 1 件の増減で 0.10 を跨ぐ場合はその脆弱性を明記。E-C の符号一致が h* 固有でないか隣接 horizon と整合確認。

## 9. LOCK 手順・期限・監視

- **LOCK 期限: 2026-08-05** (Q2-2026 日次開示の推定着地 ~2026-08 より前。Q1 公表 05-12 のラグ外挿で 8 月上旬〜中旬着地を想定、期限はその手前に設定)。
- **LOCK 手順**: (1) §4 explore 実行 → §5.1-5.4 の予測数値を確定記入 ✅ (2) 識別 rule + 2026 candidate list + M (窓内営業日数) を凍結 ✅ (3) swap: 判定は gross 符号のため**非ゲート** — 推定値 (2022: 3.18% / 2024: 5.28% 年率) で凍結し、OANDA financing 実測は verdict 時に記述として記録 (4) Status を 🔒 LOCKED に変更 ✅ 2026-07-24 (敵対的レビュー ISSUES 必須 3 + 任意 5 全反映後、main セッション執行) (5) registry 更新 ✅ (`mof-forward-prereg-lock-deadline` は commit 5a2a6c1c で追加済み → LOCK で resolved 化し `mof-q2-2026-disclosure-verdict` に置換)。
- **verdict 期日**: Q2-2026 日次開示の着地から **10 日以内**。backstop: **2026-09-30** までに開示が着地しない場合は stale レビュー (開示遅延の事実確認のみ、設計変更禁止)。
- **registry 追加の提案** (T5 の 18 日執行ギャップ教訓 — **本 DRAFT では registry を編集しない。LOCK PR または本 DRAFT 承認時に以下を `prereg-trigger-registry.json` へ追加することを提案する**):

```json
{
  "id": "mof-forward-prereg-lock-deadline",
  "active": true,
  "type": "deadline_info",
  "deadline": "2026-08-05",
  "doc": "knowledge-base/wiki/decisions/mof-intervention-forward-prereg-DRAFT-2026-07-24.md",
  "message": "MoF 円買い介入 forward pre-reg の LOCK 期限 — Q2-2026 四半期日次開示 (~2026-08 推定) より前に explore 記述統計 + 事前予測 + 識別 rule を凍結しないと 2026 エピソード (¥11.73T 窓) の genuine OOS 価値が消滅。未 LOCK なら stale アラート (T5 型ギャップ防止)"
}
```

LOCK 執行時は本エントリを resolved 化し、後継 `mof-q2-2026-disclosure-verdict` (type: deadline_info, deadline: 2026-09-30, 開示着地から 10 日以内の verdict 監視) に置換する。

- **executor**: claude 直接実行 (exit-repair 方式)。verdict 記録 = 本文書に追記 + `raw/bt-results/` 保存 + session log + 台帳 family #4 行更新。

## 10. 除外・注意 (DRAFT 時点で明示)

- 本 pre-reg は **live パラメータ・コード・shadow 構成を一切変更しない** (純研究 stage-1)。
- **endogeneity は設計内在**: 介入は価格に誘発されるため、Variant A の同日リターンは因果効果として解釈しない。E-A PASS は「識別可能性」であり EV 主張ではない (§5.2)。
- **covert 介入**: 2022-10 / 2011-11 は公式リアルタイム確認なし — Variant B の tradeability は公式確認ではなく価格 signature 検知 (識別 rule) に依存する設計とし、その妥当性検証が E-A の役割。
- explore 有効 N≈3 エピソード / OOS 有効 N=1 エピソード — **本 family の全主張は verdict 種別を問わず記述級**。edge 級主張は stage-2 以降でのみ可。
- MFE/MAE はバー粒度 (15m)。intraday 介入時刻は不可知のため event-day 内の執行 counterfactual は全変種で構築禁止。
- 予測・rule・candidate list・h* の LOCK 後変更禁止。開示結果を見た後のいかなる再計算・格子拡張も禁止 (exit-repair pre-reg §7 と同じ拘束)。
- 円売りレジーム (1991-2004, 2010-2011) への本設計の外挿は行わない — 方向逆・別時代であり、E-B NO-TEST 分岐 (§5.1) でのみ言及。

## 10. Verdict (2026-08-18 執行 — 開示 2026-08-07 着地、+11 日 = 期日 1 日超過を明記)

**全体 verdict: 🟡 PARTIAL (G0 ✅ ∧ E-B ✅ ∧ E-A ✅ PASS ∧ E-C ❌ FAIL) — §5.5 固定分岐どおり family park (prior 減)、次の円買いエピソード 1 回限り同一仕様再判定。**

### 開示データ (mof.go.jp `data/quarter/2026_2Q.html`、公表 2026-08-07)

D = {**2026-04-30** (¥6兆2,787億), **2026-05-04** (¥7,802億), **2026-05-06** (¥4兆6,759億)} — 全て米ドル売り/円買い。Q2 総額 ¥11兆7,349億 = §5.4 E-D 予測 (k∈[2,5]、最大単日 ≥¥3.0T) は k=3・最大 ¥6.28T で**両方的中**。

### E-A (primary): ✅ PASS — p = 0.0143

- S 再導出 = 凍結値と完全一致 {04-30, 05-06} (integrity ✓)、母集団 M=21 実測一致
- k_eff = 3 (D 全日が母集団内)、**overlap = 2 ≥ 閾値 2、超幾何 p = 0.0143 ≤ α 0.10**
- **プロジェクト初の forward pre-reg primary 的中** — 2022/2024 のみで校正した識別 rule (X,Y)=(2.0, 0.25%) が観測前凍結の candidate 2 日をともに言い当てた
- 取り逃し 05-04 は close/open **+0.20%** の covert 型 = explore の 2022-10-24 と同一の構造的不可捕捉モード (rule の既知限界どおり)

### E-C (符号予測): ❌ FAIL — 完全リトレース + 反転

| event | anchor | net_h1 | net_h2 | net_h5 | **net_h10** | MFE_sell | MAE_sell |
|---|---|---|---|---|---|---|---|
| 04-30 | 05-01 | −6.7 | +25.4 | −10.3 | **+188.1** | 193.6 | 191.9 |
| 05-04 | 05-05 | +45.0 | −35.8 | +45.6 | **+182.0** | 219.0 | 203.5 |
| 05-06 | 05-08 (05-07 欠損 roll、凍結例どおり) | +0.1 | +37.4 | +152.3 | **+216.1** | 49.7 | 248.6 |

(median: h1 +0.1 / h2 +25.4 / h5 +45.6 / **h10 +188.1**)

- 予測 = **負 (SELL)、band [−319.8, −43.6]p** に対し **median net_h10 = +188.1p (3/3 全日 正)** → 符号不一致で FAIL。隣接 h1/h2/h5 の median も全て正 = h* 固有の偶然ではない
- 2026-05 エピソードの介入効果は 10 営業日で完全リトレースし反転 — 2022/2024 (6/7 負) と**レジームが異なる**。事後の符号反転主張 (「介入後 BUY」) は holiday レグ c 前例どおり禁止 — 本観測は record のみ

### §8 ナイフエッジ 3 点検査

1. **メカニズム整合 ✅**: 両ヒットとも 2 構成要素の実体ヒット (04-30: co_ret −1.99% / range 518p vs 閾 135p、05-06: −0.73% / 287p vs 158p)。E-C は MFE でも SELL 側 49.7-219p vs MAE 191-249p で MAE 支配 = 符号 FAIL は実体
2. **擬似反復 ✅ 明記**: D 3 日は gap≥30d 規約で**単一クラスタ = 有効 N=1 エピソード**。E-A の p=0.0143 は「日選択 null」に対する解釈に限定
3. **閾値リーク ✅**: rule ±20% 摂動 (X 1.6/2.4、Y 0.20/0.30) の全てで S 不変。E-A は overlap −1 で不合格になる構造だが両ヒットの margin は大 (閾値の 3-8 倍)

### 帰結と手続きメモ

- **Variant B (real-time 検知→SELL) は stage-2 に進めない** (E-C 死)。ただし**検知器の real-time 実行可能性は実証された** — 将来の介入系 family (2026-08-18 user 起案の介入回避/ショート仮説を含む) への一次 prior として: **「介入後 10 営業日の SELL drift は 2026 エピソードで符号逆」**
- 再判定 registry: `mof-next-episode-reverdict` (四半期開示ごとに新規円買いエピソード有無を確認、発生時のみ 1 回限り同一仕様)
- **手続き教訓**: verdict が期日を 1 日超過した原因 = `deadline_info` トリガが「開示の実着地」を検知できず backstop (09-30) だけを持っていた。四半期開示型トリガは**予想着地日を deadline に刻み、四半期ごとに roll する** (ZN 到達経路教訓の姉妹形)。検証は `tools/mof_forward_verdict.py` + raw 出力 `knowledge-base/raw/bt-results/mof-forward-verdict-2026-08-18.txt`

### 運用追記 (2026-08-18) — E-A 検知器の defensive alert 化 (凍結条項の変更なし)

E-A の real-time 実行可能性実証を受け、凍結 rule (X,Y)=(2.0, 0.25%) を **as-is (再校正なし)** で日次監視に載せた: `tools/mof_intervention_watch.py` + `.github/workflows/intervention-watch.yml` (前 UTC 営業日を 1 回評価 → Discord 通知 + `knowledge-base/raw/intervention_watch/` JSONL 記録)。**これは Variant B ではない** — 監視/通知のみで、live gating の自動執行は §5.5 どおり別 pre-reg + user 最終承認まで不実装 (E-C FAIL により SELL 執行系は stage-2 進行不可のまま)。alert 記録は yfinance 1h 集計 (grade フィールドで明示) であり、§10 再判定 (mof-next-episode-reverdict) の verdict-grade 計算 (Massive 15m mid) に**流用禁止**。candidate ≠ 介入ラベル (公式ラベルは MoF 開示のみ)。詳細: [[family-c-anchor-automation-2026-08-18]] §2

## 11. 再判定 (§5.5 PARTIAL 分岐の 1 回限り同一仕様、2026-11-11 執行 — 開示 2026-11-09 着地 +2 日)

**全体 verdict: 🟡 PARTIAL (G0 ✅ ∧ E-B ✅ ∧ E-A ✅ PASS p=0.0877 ∧ E-C ❌ FAIL) — 2 エピソード連続で同型 (識別は再現、drift 符号は再び逆)。§5.5 が事前登録した再判定枠はこれで消費済み = family #4 の look はこれ以上存在しない (後段は §11.5)。**
執行: `tools/mof_forward_reverdict.py` (2026-07-24 LOCK 値を一切変更せず、エピソード固有入力 = 窓 / 開示 D のみ差し替え) / raw: `knowledge-base/raw/bt-results/mof-forward-reverdict-2026-11-11.{txt,json}` / test pin: `tests/test_mof_forward_reverdict.py` (凍結値・超幾何閾値表・固定分岐)。rule:R3 record-only、live パラメータ変更ゼロ。

### 11.1 開示データ (mof.go.jp `data/quarter/2026_3Q.html`、公表 令和8年11月9日 = 2026-11-09)

D = {**2026-07-30** (¥7兆9,756億), **2026-07-31** (¥5兆5,523億), **2026-08-03** (¥1兆8,714億)} — 全て米ドル売り・日本円買い (USD/JPY)。Q3 総額 ¥15兆3,993億 = 月次開示 (08-28、`20260828.html`) の 07-30〜08-26 窓総額と**一致** (残差 0)。E-D 予測 (k∈[2,5]、最大単日 ≥¥3.0T) は k=3・最大 ¥7.98T で**両方的中** (2 エピソード連続)。日次 CSV への到達は `mof-statements-daily` cron (11-09 01:05Z commit eed41a58a) = 開示当日に自動取得済み (読み手は本 run)。

### 11.2 窓・母集団・candidate list (peek 会計)

- 窓 = **2026-07-30〜08-26** (月次開示の対象窓、[[mof-monthly-total-verdict-2026-08-31]] で D 観測の **70 日前**に KB 記録済み = 観測前確定)。母集団 M = **20** 営業日 (parquet 欠損日 0、初回の 05-07 型の欠損なし)。
- S = 凍結 rule (X,Y)=(2.0, 0.25%) の窓への 1 回適用 = **{07-30, 07-31, 08-07, 08-19}**、|S|=4 ≤ 5 (事前上限内)。
- ⚠️ 初回 verdict と異なり、LOCK 時点の事前凍結 S は存在しない (§5.5 は再判定の仕様を「同一仕様」と定めるのみ)。S は決定論的 (rule + 窓 + 既存 parquet) で裁量ゼロだが、**計算の実行時刻は D 観測後 (11-11)** である事実を明記する。独立した観測前証拠: 08-19 は `tools/mof_intervention_watch.py` (yfinance 1h alert grade) が **08-20 時点で real-time に candidate=true と記録** (`raw/intervention_watch/2026-08.jsonl`、verdict grade とは別データのため流用はしていない)。07-30 / 07-31 は watch 稼働 (08-18) 前。

### 11.3 E-A (primary): ✅ PASS — p = 0.0877 (α 0.10、**ナイフエッジ**)

- k_eff = 3 (D 全日が母集団内)、**overlap = 2** (07-30 ✓ / 07-31 ✓ / 08-03 ✗) ≥ 閾値 2、超幾何 P(≥2 | M=20, |S|=4, k=3) = **0.0877 ≤ 0.10**。
- 取り逃し 08-03 は close/open **−0.03%** (range 比 4.1 で range 側のみヒット) = 初回の 05-04 (+0.20%)、explore の 2022-10-24 (+0.86%) と同じ **covert 追撃日の構造的不可捕捉モード** (rule の既知限界、3 例目)。
- **同一 rule が 2 エピソード連続で primary 的中** (2026-05: p=0.0143、2026-07/08: p=0.0877) — 2022/2024 のみで校正した識別 rule の real-time 検知可能性は 2 回再現。初回同様、これは識別可能性であって edge ではない (§5.2 endogeneity)。

### 11.4 E-C (符号予測): ❌ FAIL — per-day median net_h10 = +163.6p (予測 負、band [−319.8, −43.6])

| event | anchor | net_h1 | net_h2 | net_h5 | **net_h10** | MFE_sell | MAE_sell |
|---|---|---|---|---|---|---|---|
| 07-30 | 07-31 (p0 160.183) | −260.3 | −264.4 | −177.4 | **−75.6** | 496.8 | 69.3 |
| 07-31 | 08-03 (p0 157.580) | −4.1 | +11.3 | +32.0 | **+163.6** | 236.5 | 198.6 |
| 08-03 | 08-04 (p0 157.539) | +15.4 | +7.0 | +161.2 | **+179.1** | 87.1 | 205.7 |

(median: h1 −4.1 / h2 +7.0 / h5 +32.0 / **h10 +163.6**)

- 凍結 estimand = per-day median → **+163.6p で符号不一致 = FAIL** (2/3 正)。h5 も正、h1/h2 は ±数 pip で符号情報なし。
- §8.2 感度 (判定不使用、事前宣言の両建て報告): **エピソード初日 anchor 変種 (07-31 open) は h10 −75.6p = 予測符号と一致し band 内** (MFE_sell 496.8 / MAE 69.3)。ただし初日 anchor の h1/h2 −260p は **anchor 当日 (07-31) が第 2 介入日**であること自体の作用 (連日介入 = forward 窓の重複) であり、介入後 drift の証拠ではない。初回 (2026-05) は初日 anchor でも +188 で、変種間の符号も 2 エピソードで不一致 → 「初日 anchor なら効く」という事後主張は §10 と同じく禁止 (record のみ)。
- swap-net (h10 short USDJPY キャリー ≈ 数 pip/10d) は gross 符号判定に影響しない (非ゲート、記述省略)。

### 11.5 §8 ナイフエッジ 3 点検査 + 固定分岐の帰結

1. **メカニズム整合 ✅**: 両ヒットとも 2 構成要素の実体ヒットで margin 大 (07-30: co_ret −1.92% / range 579p vs 閾 130p = 8.9 倍、07-31: −1.76% / 370p = 5.7 倍)。E-C FAIL は 07-31 / 08-03 の MAE (199 / 206p) が MFE を支配する実体。
2. **擬似反復 ✅ 明記**: D 3 日は gap≥30d 規約で**単一クラスタ = 有効 N=1 エピソード**。E-A の p は「日選択 null」に対する解釈に限定。2 エピソード累計でも有効 N=2。
3. **閾値リーク / 格子点 ⚠️ ナイフエッジ明記**: (a) p=0.0877 は α 0.10 の近傍。overlap が 1 減ると p=0.509 で不合格 = 構造的に初回と同じ脆弱性 (初回 0.0143→0.186)。(b) rule ±20% 摂動: X+20% で 08-19 (ratio 2.07) が脱落し |S|=3 → p=**0.0456**、他 3 摂動は S 不変 (p=0.0877)。**overlap 2 (07-30/07-31) は全摂動で不変** = ヒット側は knife-edge ではなく、p の値が |S| (false positive 数) に依存して 0.046〜0.088 を動くだけ。(c) E-C の符号 FAIL は h5 / h10 で整合 (h* 固有ではない)。

**固定分岐**: §5.5 PARTIAL → 「次の円買いエピソード 1 回限りの同一仕様再判定」= **本 §11 で消費**。pre-reg が事前登録した look は初回 + 再判定の 2 回のみで、3 回目の look は存在しない。よって family #4 は **PARTIAL ×2 でクローズ (park 恒久化)**: (i) Variant B (real-time 検知 → SELL) は E-C 2 連続 FAIL で stage-2 不可 (確定)、(ii) 識別 rule の real-time 検知能力は 2 エピソードで再現 — **将来の介入系 family の「介入日検知器」としての一次 prior は強化** (ただし drift 方向の prior は「2026 の 2 エピソードとも介入後 10 営業日で正 (リトレース/反転)」= SELL 方向の同型再試行は禁止、BUY 方向の事後主張も禁止)、(iii) 新たな仮説 (例: 開示時点リアクション Variant C、初日 anchor 型) は**新規 pre-reg (R1、user 承認) でのみ**再開可。registry `mof-next-episode-reverdict` は resolve し後継は起票しない (四半期開示の機械取得は `mof-statements-daily` cron が継続、T5 第 2 要件の材料としては `t5-jpy-cap-restore-price` に転記)。

### 11.6 T5 第 2 要件への転記 (認定・lot 変更はしていない)

四半期開示 = **外部一次情報による「介入観測」の肯定 + 方向 (円買い) + 文脈 (07-30 の日次 open 160.18 → 介入当日 −1.9%、07-31 anchor open 160.183 = 160 近傍での防衛)** が初めて同時に揃った。T5 lot 1.0x 復帰は R1 = user 決裁 (registry 注記のみ)。
