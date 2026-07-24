# Pre-registration DRAFT: MoF 円買い介入モダリティ — 観測前 forward pre-reg (rule:R1 stage-1)

**DRAFT — LOCK 未執行、user/main セッションレビュー待ち。**
本文書は設計固定の起案であり、LOCK 執行・コード変更・live 変更は一切含まない。LOCK は §9 の手順 (explore 記述統計の追記 + 予測値の凍結 + user/main レビュー) を経て **2026-08-05 まで**に別途執行する。

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
| anchor t0(d) | **d の翌営業日の 00:00 UTC (= 09:00 JST) 以降の最初の 15m バー open** (週末・休場は次営業日へ roll forward)。event-day 内 anchor は lookahead のため全変種で禁止 (W1-F1 caution a) |
| horizons | h ∈ {**1d, 2d, 5d, 10d**} (東京営業日カウント、同じ 00:00 UTC 境界) |
| 純移動 | net_h(d) = mid(t0+h) − mid(t0) [pips, 0.01 JPY]。SELL 方向有利 = 負 |
| MFE/MAE | [t0, t0+h] 内の SELL 方向 MFE/MAE (バー粒度) |
| swap | h5/h10 は short USDJPY のキャリー純額を控除した net-after-carry を併記 (**判定は gross 符号、swap-net は記述**)。swap 実測値は LOCK 時に OANDA financing / e20_rates_ingest 配管から記録 (E20 配管残置の流用、[[../../..//knowledge-base/wiki/index|E20 S2 棄却]] は estimand 別で非該当) |
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

## 5. 事前予測と判定ゲート (実行前凍結 — LOCK 時に数値確定、以後変更禁止)

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

### 5.3 E-C: forward drift 確認予測 (sign-based scorecard、検定なし)

- **予測 (LOCK 時に explore から機械的に生成して凍結)**:
  - primary horizon h* = explore 7 日で符号が最も一貫する h (tie-break: |median| 最大)。以後変更禁止 (WS3 pre-reg §2 と同じ拘束)。
  - 予測符号 = explore median の符号 (§2.1 校正条項)。
  - 記述 band = explore per-day net_h* の [P25, P75]。
- **PASS 条件: 開示 D の median net_h*(d) が予測符号と一致** (band 内かは記述のみ)。k≈2-5・1 エピソードで検定力ゼロのため sign-based に限定し、p 値主張はしない。
- 副次 (記述のみ、判定不使用): 全 h の net / MFE / MAE、swap-net、エピソード初日 anchor 変種 (episode-level 相関の感度)。

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

- 本 pre-reg は [[../syntheses/hypothesis-catalog-2026-07-24|仮説カタログ台帳]] **m=12 の family #4 (mof_intervention)** の confirmatory 段。
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
| P-8 | explore 記述統計 (7 日の net/MFE/MAE) | **未実行** (W1-F1 は data+feasibility のみ)。§4 として LOCK 前に実行・追記 |

**リーク経路の事前封鎖**: (i) 識別 rule の校正は 2022/2024 データのみ、2026 窓への適用は一回 (§2.2)。(ii) E-C 予測は explore からの機械的生成 (§5.3) で裁量ゼロ。(iii) 06-27..07-28 窓の月次開示 (~07 月末見込み) が LOCK 前に着地しても月次総額のみで日次ラベルは含まれない — 着地したら peek 会計に追記する (G0 には抵触しない)。

## 8. ナイフエッジ 3 点検査 (verdict 時必須 — T11 lesson、事前宣言)

1. **メカニズム整合**: E-A のヒットが rule の両構成要素 (下方リターン ∧ レンジ拡大) どおりに成立しているか (片側だけの偶然ヒットを分解確認)。E-C の符号一致が MFE 側の実体で成立しているか (MAE 崩壊による見かけの符号でないか)、絶対量が摩擦 (RT 2.14p) の 10 倍以上か。
2. **擬似反復**: 開示介入日が連続日クラスタの場合、日レベルの一致を独立事象として数えない — **有効 N = 1 エピソード**であることを verdict に明記し、超幾何 p は「日選択の null」に対する解釈に限定。forward 窓の重複 (連日介入で h 窓が重なる) は per-day / episode-初日 の両建て報告で感度確認。
3. **閾値リーク / 格子点**: 識別 rule (X, Y) を ±20% 摂動させて candidate list が激変しないか (knife-edge rule の排除)。E-A の p が overlap 1 件の増減で 0.10 を跨ぐ場合はその脆弱性を明記。E-C の符号一致が h* 固有でないか隣接 horizon と整合確認。

## 9. LOCK 手順・期限・監視

- **LOCK 期限: 2026-08-05** (Q2-2026 日次開示の推定着地 ~2026-08 より前。Q1 公表 05-12 のラグ外挿で 8 月上旬〜中旬着地を想定、期限はその手前に設定)。
- **LOCK 手順**: (1) §4 explore 実行 → §5.1-5.4 の予測数値を確定記入 (2) 識別 rule + 2026 candidate list + M (窓内営業日数) を凍結 (3) swap 実測値記録 (4) Status を 🔒 LOCKED に変更する PR (user/main セッションレビュー必須) (5) registry へ監視エントリ追加。
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
