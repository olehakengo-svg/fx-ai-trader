---
title: Structural Flow Tier (SFT-1) — Calendar / Fix-flow 戦略の新カテゴリ
date: 2026-05-04
status: PROPOSED → READY_FOR_RESEARCH
owner: claude-司令塔
implementer: codex (research phase 後に実装)
trigger: 構造的制約 (月末/fix/期末) 由来エッジが現行戦略集合に皆無
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_spread_basis_for_mafe.md
  - knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md
roadmap_gate: new tier (cross-Wave)
---

# 1. Why this tier exists

Qiita 記事の②「構造的制約」エッジ。**強制発注由来のフロー** (月末リバランス、WMR fix、期末リパトリ、option NY cut expiry) は decay は早いが本質的に reproducible で、行動ファイナンス系より検証が固い。現行 fx-ai-trader はこのカテゴリの戦略・データ・cell 区分が**皆無**。

# 2. Initial scope (3 候補戦略のみ、Wave 1 = research only)

実装に行く前に、**まず BT で edge 存在性を検証** する。3 候補:

## 2.1 SFT-A: `month_end_usd_rebalance_short`

仮説: 月末 (London 16:00 WMR fix) 直前の **株式リバランス由来 USD 需要 / 供給** が偏り、fix 通過後に解消する。歴史的には円高/EUR 高 (USD 売り) の月が多い。

- Setup: 各月最終 2 営業日のうち、月末日の London fix (16:00 GMT) の 30 分前 〜 fix 直後 30 分のウィンドウ
- 方向: USDJPY/EURUSD で USD short
- Exit: fix 後 60 分または ATR ベース trailing
- Pair: USDJPY, EURUSD, GBPUSD

## 2.2 SFT-B: `tokyo_fix_955_jpy_demand`

仮説: 本邦実需 (輸入企業ヘッジ) が **Tokyo 仲値 (9:55 JST = 00:55 UTC)** に集中。直前 30 分で JPY 需要 (USDJPY 上昇)、9:55 通過後に解消。

- Setup: 営業日の Tokyo 9:55 直前 30 分の上昇傾向を取り、9:55 通過後に売り戻す
- 方向: USDJPY long (前) → 売り戻し
- Exit: 9:55 から 60 分以内にクローズ
- Pair: USDJPY のみ (本邦特有)

## 2.3 SFT-C: `quarter_end_jpy_repat`

仮説: 3 月 / 9 月末 (本邦事業年度末 / 中間決算) の **本邦勢リパトリ** で月末週に JPY 強含み。

- Setup: 3 月 / 9 月の最終 5 営業日
- 方向: USDJPY short (JPY 高)
- Exit: 月末日 17:00 GMT
- Pair: USDJPY のみ
- Sample: 12y データで 24 月末 (12 年 × 2 期)。N が小さいので Wilson_lo を緩く取らず厳密評価

# 3. Research-first protocol (W4-EDA 流用)

**実装の前に W4-EDA 流の literal BT** を 3 候補すべてに適用:

1. データ準備: M5 12y キャッシュは既存利用、calendar event テーブル新規作成
2. Literal BT: 仮説通りの setup/entry/exit を **そのまま** 実装、過剰最適化しない
3. 評価: PF / Wilson_lo / Bonferroni m=3 / Kelly / max DD / single-year concentration / null bootstrap p
4. **NSG-1 適用必須** (本決定文書 §6 で要求)
5. 結果が `THESIS_VALID_DESIGN_BROKEN` なら 1 回だけ再設計、それでも fail なら catalog §academic only に降格

## 3.1 BT に追加で必要な input

- **Calendar event table** (`data/calendar/structural_events.parquet`): 月末日, Tokyo fix 日付, 期末月の identifier。手作業で 12y 分 (~150 月末 + ~24 期末) 作成。
- **Slippage 時間帯別 model**: 月末 fix は流動性が瞬間的に厚いがスプレッドは荒れる。**現行 spread-basis MAFE 規律 (記憶) では足りない可能性**。time-of-day slippage table を併設。

# 4. Expected risks

- **R1 — HFT に取られている**: SFT-A は 2010 年代に HFT が刈った可能性あり。直近 3 年だけで再評価する sub-period 検証必須。
- **R2 — 本邦休日**: SFT-B は本邦祝日で setup 不発。営業日カレンダーが必須。
- **R3 — 政策介入混入**: SFT-C は介入と被ると drawdown 拡大。介入日を除外する dummy 評価を併設。
- **R4 — N が小さい**: SFT-C は N=24 のみ。Bonferroni m=3 でも合格は厳しい。`thesis_valid_evidence_thin` で Shadow に止める設計。

# 5. Acceptance criteria for the research task

- [ ] `data/calendar/structural_events.parquet` 12y 分が生成される (script 化)
- [ ] 3 候補すべてで literal BT 実行、レポート 3 本
- [ ] 各レポートに NSG-1 verdict 記載
- [ ] 1 戦略でも Scenario A/B 通過すれば Wave 2 (Shadow promote) を別決定で計画
- [ ] 全 reject なら catalog §academic only / no-go に降格

# 6. NSG-1 連動

実装される場合 (Top 4 NSG-1 が先行採用済前提):

- 各戦略の primary cell を spec で明示 (post-hoc selection 防止)
- 周辺 cell (時刻 ±15 分, 期間 ±1 営業日) を grid に明示
- NSG-1 で stability 確認

# 7. Out of scope (v1)

- US 期末 (3/12 月末) の本邦以外勢リパトリ
- ECB / BoE 月末 fix
- NY cut option expiry (10:00 EST) は Top 2 (オプション skew) と関連、別 tier 検討
- 米債 coupon / Japan SQ
