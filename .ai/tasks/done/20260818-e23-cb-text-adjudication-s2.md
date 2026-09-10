---
id: 20260818-e23-cb-text-adjudication-s2
title: "[供給ライン] E23 central_bank_statement_text — ゲート解除後の台帳裁定 + S2 データ実在 probe"
owner: claude (session cool-murdock-656c5a — SLA 15日滞留につき Claude 直接実行へ fallback、claude-codex-division-of-labor 規約)
status: done
claimed_at: 2026-09-04T06:40:00+0000
completed_at: 2026-09-10T00:00:00+0000
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
3. 成立なら testable form DRAFT (語彙/スコア凍結の設計) → 敵対的検証 → 別 commit で LOCK。不成立なら正直クローズ。 ✅ **完了 2026-09-10** (scan#4 前倒しに同乗 — waiver の「09-18 統合裁定と同時処理」方針を期日前倒しで履行)

# 2026-09-10 完遂記録

- **testable form DRAFT + 敵対的検証 (自己) 10 条**: `knowledge-base/wiki/decisions/e23-cb-text-explore-prereg-2026-09-10.md` (commit 325359ef)。primary = Apel–Blix Grimaldi 2012 凍結辞書 (`tools/e23_lexicon_apel_grimaldi.py` — **Riksbank WP 261 原本 PDF を取得し語彙を逐語転記**: 名詞 11 語幹 + hawk/dove 各 4 形容詞語幹 + unemployment 極性反転、Net Index = (H−D)/(H+D+1)、test pin 8 本)。設計 = ΔNH sign-follow × G4 中銀 (1 中銀 1 文書種) × D1+5 pooled bp、explore 2014-2023 / OOS 2024-2026H1、pass-0 census gates (DATA-BLOCKED 分岐)。
- **🔒 LOCK (本 commit、別 commit 規約)**: 辞書 sha256 = f49586ca... pin、explore 枠 1/3 消費、registry `e23-explore-verdict-deadline` (2026-09-20) 併設。
- **TDW は事前コミット節どおり secondary 保留** (CC BY-NC = user ライセンス決裁点。WCB_380k も同条項) — 設計は Apel-Grimaldi primary のみで成立 (09-04 追記の設計方針どおり)。
- **イベント×リターン結合統計は一切計算していない** (S2 規律遵守)。測定 (pass-0 census → two-pass) は LOCK 後の別タスク。
- SLA waiver (`.ai/tasks/sla_waivers.json`) は本 commit で削除。

## Claude Review (2026-09-10)

- **裁定品質**: 合格 — item 1/2 は 08-18 完了済み (裁定 doc + dossier)。item 3 は「凍結公刊辞書のみ = in-house 語彙 DoF 構造封鎖」の当初設計思想を維持したまま testable form に落ちている (辞書は WP 261 **原本 PDF から逐語転記** — 二次文献の引き写しでない点を実査)。
- **規律遵守**: 合格 — イベント×リターン結合統計ゼロ (S2)、LOCK は別 commit (規約)、TDW/WCB は CC BY-NC 事前コミット節で user 決裁点として保留 (09-04 追記の方針どおり)。
- **推論の正直さ**: 合格 — 負の prior (E15+E7 二重 FAIL 家系、生存 0/17) を pre-reg §1 に転記し、census 前は実効 N 未知と明記 (V9)。MDE 18-32bp の power caveat を FAIL 分岐に凍結。
- **残リスク**: pass-0 コーパス取得ハーネスが未実装 (registry e23-explore-verdict-deadline 09-20 が監視)。BoJ 英語版同時性 (V3) は census で機械確認するまで仮定のまま — 除外規則を凍結済みなので設計変更なしに処理可能。

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
