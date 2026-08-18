# E23 central_bank_statement_text — ゲート解除後の台帳裁定 + S2 データ実在 probe (2026-08-18)

> **rule:R3 (裁定 + probe のみ)**。イベント×リターン結合統計は一切計算していない (S2 規律)。live/shadow/tier 変更ゼロ。
> claim: `.ai/tasks/queue/20260818-e23-cb-text-adjudication-s2.md` + PR #188 (race 対策 claim 手順の 2 回目適用)。
> 起点: [[external-hypothesis-scan-round3-2026-08-14]] §E23 行 (保留、ゲート = E7 verdict) / [[e15-e7-event-modality-prereg-2026-07-18]] §13 (E7 verdict 2026-08-17 前倒し確定 = ゲート解除) / 改訂 WIP 原則 (着手可能 ≥1 本) の発動 — E21/E22/E7 クローズで能動測定ライン 0 本。

## 1. 裁定: **採用 — S2 診断枠** (explore スロット未消費、pre-reg LOCK は敵対的検証後の別 commit)

判定軸 3 点:

1. **E7/E15 family との estimand 独立性 — 成立 (処分済み論拠の再確認)**: E7 の ban 射程は「NFP/CPI headline z × sign-follow × M15 全変種」(§13)、E15 の棄却は「無条件イベント窓」。E23 の条件付け変数 = **声明テキストの差分** (票割れ・ガイダンス一語差のニュアンス) は E7 の数値サプライズに不含 — wave-6 THA 裁定 ([[ea-landscape-sweep-2026-07-31]] §5.1) で「08-28 後の新規台帳候補として再評価可」と処分済み。
2. **凍結可能な外部特徴量の実在 — 成立 (probe §2)**: in-house テキスト特徴量の自由度 (scan が指摘した curve-fit 温床) を、**観測窓より前に公刊・凍結された外部スコア/辞書のみ使用**する制約で構造的に封じられる。
3. **banned 19 family 非隣接 — 成立**: テキストモダリティは価格・ポジショニング・volume・カレンダー数値のいずれとも別。banned はすべてシグナル族の別モダリティ。

## 2. S2 データ実在 probe (2026-08-18 実測)

| 資源 | 状態 | 用途裁定 |
|---|---|---|
| **Apel-Grimaldi (2012) hawk-dove 辞書** | 公刊 2012 (Sveriges Riksbank WP) — 全観測窓に先行、ライセンス制約なし | **primary 候補**: net-hawkishness の声明間差分。特徴量の自由度 = 辞書 1 冊で凍結 |
| **Trillion Dollar Words (ACL 2023)** — [GitHub](https://github.com/gtfintechlab/fomc-hawkish-dovish) / [HF dataset](https://huggingface.co/datasets/gtfintechlab/fomc_communication) / [FOMC-RoBERTa](https://huggingface.co/gtfintechlab/FOMC-RoBERTa) | 公開確認 ✓。FOMC 40k 文 (1996-2022) + hawkish/dovish ラベル + 凍結モデル (2023-05 公刊) | **secondary 候補** — ⚠️ **CC BY-NC 4.0 (非商用)**: 実弾トレードシステムでの利用可否は**ライセンス解釈の user 決裁事項**として記録。決裁前は設計にのみ言及し実装に組み込まない |
| **IMF WP 2025/109** ([imf.org](https://www.imf.org/en/publications/wp/issues/2025/06/06/from-text-to-quantified-insights-a-large-scale-llm-analysis-of-central-bank-communication-567522)) | 論文 PDF は公開、**複製データ (74,882 文書スコア) の公開は未確認** | 現時点で**使用不可**と裁定 (実在＝紙、データ＝未確認)。scan の実在根拠は「データセットの存在」であり「入手可能性」ではなかった — 区別を記録 |
| **声明テキスト原文** (federalreserve.gov / ecb.europa.eu / bankofengland.co.uk 等) | 公開アーカイブ (scan §E23 で実在 ✓ 済み)。FOMC は E15/E7 カレンダー (§3.2) にタイムスタンプ既収載 | コーパス取得ハーネスは S2 残作業 |

## 3. 正直な負の prior と power 幾何 (設計への拘束)

- **同一イベント面で二重 FAIL 済み**: E15 (FOMC 無条件窓、phase-0 C5) + E7 (数値サプライズ条件付け、discovery 0/24)。E23 の残余仮説は「数値に現れないテキストニュアンスだけが方向情報を持つ」— **狭い**。これを裁定時点で明記する (FAIL 時に「実は分かっていた」と言わないため)。
- **FOMC 単独では power 不足が既知**: OOS blocks ~20 (phase-0 実測) = 「大効果のみ検出」帯、modal C3/C5。**→ S2 の設計方向 = multi-CB パネル** (Fed/ECB/BOE/BOJ + 可能なら RBA/BOC、各中銀声明 × 自国通貨ペアの方向) — blocks を 4-6 倍にし、G10 横断の pooled 検定にする。これは E15/E7 (US イベント × USD-leg) と母集団も広げる = 独立性がさらに立つ。
- 非英語声明 (BOJ 等) は英語公式版に限定 (辞書適用の一貫性)。英語版が無い期間はそのセルを機械的に欠測扱い。

## 4. S2 残作業 (次ステップ、本裁定には含まない)

1. multi-CB 声明コーパス取得ハーネス (タイムスタンプ規約 = 各中銀の公式発表時刻、E15 §3.2 の ET→UTC 手続きを踏襲) + カバレッジ実測。
2. testable form DRAFT: 凍結辞書 net-hawkishness の**声明間差分**符号 × 自国通貨方向、fixed horizon (E15 grid 踏襲)、explore/OOS split (2014-2023 / 2024-2026H1 — E15/E7 と同一 = 窓消費の会計は family 別に有効)。
3. 敵対的検証 (subagent) → 生存時のみ pre-reg LOCK (別 commit、registry エントリ併設)。
4. **TDW ライセンス (CC BY-NC) の user 決裁** — secondary 特徴量として使うかの判断材料を提示。

## 5. 台帳への反映

- [[hypothesis-catalog-2026-07-24]] E23 行: 保留 → **採用 (S2 診断枠)** (本 commit)。アクティブ本数 0 → 1 (改訂 WIP 原則充足)。
- explore スロット消費はまだゼロ (S2 は診断)。pre-reg LOCK 時に消費を宣言。
