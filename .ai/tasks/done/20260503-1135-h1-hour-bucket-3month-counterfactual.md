---
id: 20260503-1135-h1-hour-bucket-3month-counterfactual
title: W2-4r H-1 Cell-Level Hour-Bucket Promotion Gate w/ 3-Month Counterfactual
owner: codex
status: queued
priority: P1
created_at: 2026-05-03T11:35:00+0900
roadmap_gate: Gate 1
rule: R1
---

# Objective

W2-4 で実装済み (commit 5150a1e) の H-1 Hour-Bucket Cell-Level Promotion Gate を、Codex 独立レビュー指摘 (30 日窓ノイズ過大、低 N での構造固定化リスク) に対応するため、**3 ヶ月以上の counterfactual 検証** に拡張する。

REVISED 由来 (Codex Wave 1 review):
> H-1 audit: 30 日窓のノイズが大きく、時間帯崩壊を構造として固定化するには過小サンプル。3 ヶ月以上の窓で再評価が必要。
> PEAK(13-15 UTC): 各時刻 N=13/19/23 と低 N。
> 4-bucket grouping を default に: cell_n_min=30 かつ EV CI lo≥0 を各 cell で判定。

最終 Deliverable: `wiki/learning/h1-hour-bucket-design-2026-05-03.md` (3-month counterfactual + A/B test plan を含む REVISED 設計書) と `.ai/runs/<run-dir>/final.md`。

# Context

- Wave 1 H-1 audit: `wiki/learning/h1-spread-time-audit-2026-05-03.md`
  - 全戦略一律時間ゲート棄却
  - bb_rsi_reversion/USDJPY (LIVE N=317) で公開知見と逆向き (13-15 UTC peak で WR 32.7%, EV -0.50 pip)
  - 21-00, 03-05 UTC で WR 48.4%, EV +0.09 pip
  - spread 時間帯非依存 (mean 0.61-0.82)
- Codex Wave 1 review: `wiki/learning/codex-review-wave1-2026-05-03.md`
- W2-4 (initial) commit: 5150a1e — 8 ファイル 1542 行追加 (h1-hour-bucket ブランチ)。実装本体は完了、本タスクは **検証深化** のみ。
- Internal lessons:
  - feedback_ma_filter_breaks_mr: signal 段階に時間ゲートを置かない
  - feedback_partial_quant_trap: PF/Wilson CI/WF/Bonferroni/Kelly まで要求
  - feedback_live_shadow_separation: LIVE PnL は is_shadow=0 と oanda_trade_id IS NOT NULL で厳格分離
  - feedback_cohort_time_check: cell 統計で good 数字を見たら demote/promote 履歴を時系列確認
  - feedback_check_orphan_local_app: 一次ソースは Render API。`pgrep -f app.py` で orphan 確認
  - reference_oanda_audit_twin_meaning: oanda_audit.entry_type 二義性 (bridge_status='sent'=戦略名 / 'filled'=MODE 名)

# 設計仕様 (Codex 指摘反映)

## 原則
- signal 段階に時間ゲートを置かない (feedback_ma_filter_breaks_mr 整合)
- 既存 cell-level promotion gate に hour_bucket 軸追加のみ
- 既存 LIVE 戦略 (bb_rsi_reversion 等) は **grandfather** で影響を受けない

## 仕様
- `(strategy, instrument, hour_bucket)` で cell 評価
- **default は 4-bucket grouping** (Codex 推奨):
  - Asia: 00-06 UTC
  - London: 07-12 UTC
  - NY-overlap: 13-16 UTC
  - Off: 17-23 UTC
  - 24-bucket は N 不足のため将来 LIVE 拡大後に検討
- 各 bucket で:
  - N ≥ `cell_n_min_hour=30`
  - Wilson 95% lo > `hour_wilson_min=0.40`
  - EV CI lo ≥ 0 (新ガード)
- bucket-level reject: promotion を 1 段階下げる (Live → Shadow 等)。完全排除はしない
- 既存 LIVE 戦略はすべて grandfather (新規 promotion path のみ適用)

# 必須事前検証 (本タスクのコア)

## 3 ヶ月 counterfactual (30 日 → 3 ヶ月以上に拡張)
- 対象期間: 直近 3 ヶ月 (2026-02-01 〜 2026-05-01) Shadow データ
- データソース: Render 本番 (`/api/demo/trades` または production DB read-only)。**ローカル DB は phantom 汚染リスクのため使わない**。実行前に `pgrep -f app.py` で orphan 不在を確認
- 4-bucket gate を後付け適用、各戦略の promotion パスがどう変化するか dry-run

## 検証項目
1. 過去 LIVE promotion 戦略 (bb_rsi 等) を破壊しない (grandfather 機能確認)
2. Shadow only 戦略 (ema_trend_scalp, fib_reversal, mtf_trend_follow_scalp 等) の promotion path 変化を dry-run
3. **false demotion rate** (新 gate で demote されたが旧 logic では LIVE に上がる cell) > 20% なら gate 再調整
4. **bucket-level N 不足の場合の挙動**: N<30 cell は gate 適用せず "insufficient data" でスキップ (false reject 防止)
5. 3 ヶ月でも各 bucket の N が 30 未満なら gate 設計を再考し、設計書に明記

# 統計ガード

- LIVE/Shadow 厳格分離: `is_shadow=0 AND oanda_trade_id IS NOT NULL` を Live 判定として使用
- 時間コホート整合: demote/promote 履歴と現状の取り違え禁止
- Bonferroni: 4 buckets × 戦略数 で multiple comparison 補正 (alpha=0.05)
- Wilson lower bound: WR と EV CI 両方
- 出力に必ず含めること: N, WR, EV, PF, Kelly, Wilson lower (WR/EV), Bonferroni 補正後 p, OOS 切り分け

# Scope

Codex may change:
- `wiki/learning/h1-hour-bucket-design-2026-05-03.md` — REVISED 設計書 (3-month counterfactual + A/B 計画) を新規作成
- `wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` — counterfactual dry-run レポート新規作成
- `tools/h1_hour_bucket_counterfactual.py` — 3-month dry-run スクリプト新規作成 (既存 cell evaluator を library として利用、core logic 重複禁止)
- `.ai/runs/<run-dir>/final.md` — run report

Codex may NOT change:
- live signal logic, OANDA modules, strategy parameters
- `.env`, OANDA keys, production DBs (write)
- W2-4 で実装済みの cell evaluator/promotion 判定 core logic (`modules/cell_evaluator.py` 等)。read-only library として利用
- `live_ng_cells` SQLite テーブル (read-only)
- `wiki/index.md`, `wiki/tier-master.md` (Claude が後で更新)

# Required Reading

- `CLAUDE.md`
- `wiki/learning/h1-spread-time-audit-2026-05-03.md` (Wave 1 audit)
- `wiki/learning/codex-review-wave1-2026-05-03.md` (Codex 指摘原文)
- `knowledge-base/wiki/lessons/index.md` 関連 lesson
- W2-4 commit 5150a1e の差分 (`git show 5150a1e --stat`)
- `tools/cell_edge_audit.py`, `tools/cell_negative_edge_audit.py` (既存 cell 評価 library)

# Data Source

- 一次ソース: Render API `https://fx-ai-trader.onrender.com/api/demo/trades` (Shadow + LIVE)
- DB read: `is_shadow=0 AND oanda_trade_id IS NOT NULL` を Live フィルタに使用
- 実行前: `pgrep -f app.py` で orphan local instance がないこと確認 (feedback_check_orphan_local_app)

# Deliverable

1. `wiki/learning/h1-hour-bucket-design-2026-05-03.md` — REVISED 設計書
2. `wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` — 3 ヶ月 dry-run 結果
   - 各戦略 × pair × hour_bucket で N/WR/EV/PF/Kelly/Wilson lower (WR/EV)/Bonferroni p
   - false demotion rate
   - bucket-level N 不足リスト (N<30 cell)
   - grandfather 機能による既存 LIVE 戦略保護の verification
3. A/B テスト計画書 (Shadow tier 内 1 ヶ月並走、A=control / B=新 gate、月次レポート、false demotion rate > 20% で再調整)
4. `.ai/runs/<run-dir>/final.md` — run report

# Acceptance Criteria

- [ ] 3 ヶ月窓 (2026-02-01 〜 2026-05-01) の counterfactual 完了
- [ ] N/WR/EV/PF/Kelly/Wilson lower/Bonferroni p が出力に含まれる
- [ ] LIVE/Shadow 厳格分離 (`is_shadow=0 AND oanda_trade_id IS NOT NULL`)
- [ ] grandfather 機能で bb_rsi_reversion/USDJPY 等の既存 LIVE 戦略が破壊されないことを示す
- [ ] false demotion rate < 20% を確認、超える場合は再調整提案
- [ ] N<30 cell は "insufficient data" でスキップされることを示す
- [ ] A/B テスト計画書を含む

# 関連

- 親プラン: `/Users/jg-n-012/.claude/plans/find-out-way-of-fizzy-patterson.md`
- W2-4 (initial) commit: 5150a1e
- Wave 1 audit: `wiki/learning/h1-spread-time-audit-2026-05-03.md`
- Codex Wave 1 review: `wiki/learning/codex-review-wave1-2026-05-03.md`
- Wave 2 4/5 (REVISED, 3-month counterfactual)
