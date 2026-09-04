---
id: 20260818-e23-cb-text-adjudication-s2
title: "[供給ライン] E23 central_bank_statement_text — ゲート解除後の台帳裁定 + S2 データ実在 probe"
owner: claude (session cool-murdock-656c5a — SLA 15日滞留につき Claude 直接実行へ fallback、claude-codex-division-of-labor 規約)
status: in_progress
claimed_at: 2026-09-04T06:40:00+0000
priority: P1
roadmap_gate: "トラックB 供給ライン。改訂 WIP 原則 (着手可能 ≥1 本、2026-08-14 改訂) の発動 — E21/E22/E7 クローズで能動測定ライン 0 本。E23 ゲート (E7 verdict まで) は 08-17 の前倒し verdict で解除済み"
rule: R3 (裁定 + データ probe のみ。イベント×リターン結合統計は計算しない — S2 規律)
executor_note: "排他 claim = 本 ticket + draft PR。裁定根拠 = external-hypothesis-scan-round3-2026-08-14 §E23 行 + ea-landscape-sweep §5.1 (E7 不含の処分済み) + E7 §13 ban 射程 (NFP/CPI headline z のみ)。S2 の核心 = 外部公刊スコア (IMF WP 2025/109 等) を凍結特徴量として使えるかのデータ実在検査 — in-house テキスト特徴量の自由度を構造的に封じる設計が成立しなければ不成立と正直に記録"
prereq_artifacts:
  - knowledge-base/wiki/research/external-hypothesis-scan-round3-2026-08-14.md
  - knowledge-base/wiki/research/ea-landscape-sweep-2026-07-31.md
  - knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
---

# 要求仕様

1. **台帳裁定**: E23 を 保留 → 採用 (S2 診断枠) or 棄却。判定軸 = (a) E7 family との estimand 独立性 (処分済み論拠の再確認)、(b) 凍結可能な外部特徴量の実在、(c) banned 19 family 非隣接。 ✅ **完了 2026-08-18** (採用 — S2 診断枠、e23-cb-text-adjudication-s2-2026-08-18.md)
2. **S2 データ実在 probe** (結合統計なし)。 ✅ **完了 2026-08-18** (e23-data-availability-dossier-2026-08-18.md)
3. 成立なら testable form DRAFT (語彙/スコア凍結の設計) → 敵対的検証 → 別 commit で LOCK。不成立なら正直クローズ。 ⬅ **残作業はこれのみ**

# 2026-09-04 fallback 追記 (Claude 直接実行、user「進めて」2026-09-02)

- **「TDW ライセンス user 決裁待ち」は本タスクのブロッカーではない**と確認 (2026-09-02 調査):
  TDW = Trillion Dollar Words (gtfintechlab、**無料の学術データセット**)。決裁対象は購入ではなく
  「CC BY-NC(-SA) 4.0 を live 転送で使うかのライセンス解釈」のみで、しかも TDW は **secondary 候補**。
  **primary = Apel-Grimaldi (2012) hawk-dove 辞書 (ライセンス制約なし) で item 3 は TDW なしで成立する設計** (dossier 記載)。
- **処理**: TDW は E22 §2.1 型の事前コミット節 (「PASS = ライセンス/代替データの user 決裁点到達のみ」) を
  pre-reg に内蔵して secondary のまま保留。S2 は Apel-Grimaldi primary で続行。
- 次の具体作業: multi-CB 声明コーパス取得ハーネス (federalreserve.gov = パブリックドメイン / ECB 公式 CSV) +
  カバレッジ実測 → testable form DRAFT (凍結辞書 net-hawkishness の声明間差分) → 敵対的検証 → LOCK。
- 正直な prior: low-mid (E15+E7 が同一イベント面で二重 FAIL 済み — 残余仮説は「数値に現れない
  テキストニュアンスのみが方向情報を持つ」で狭い)。
