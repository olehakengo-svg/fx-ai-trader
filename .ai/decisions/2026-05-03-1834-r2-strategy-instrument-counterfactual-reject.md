---
date: 2026-05-03T18:34:00+0900
revised_at: 2026-05-03T18:58:00+0900
task: 20260503-1815-r2-strategy-instrument-counterfactual (rev1, superseded by rev2)
codex_job: task-mopkfmmt-1wegik
codex_session: 019ded28-c38e-7d70-9d0b-d7b079f8a2e5
run_dir: .ai/runs/20260503-182601-20260503-1815-r2-strategy-instrument-counterfactual
rule: R2
verdict: ACCEPT (Codex deliverable) / REJECT_SUPERSEDED (data contamination, requires rev2 re-run)
roadmap_gate: Gate 0 (生存) — verdict は contaminated data に基づく、TRUE_LIVE N=371 で再実行必要
---

## ⚠️ POST-VERDICT CORRIGENDUM (2026-05-03 18:58 追記)

ユーザー指示と `aggregate-kelly-decomposition-2026-05-03-corrigendum.md` により、**本 review の REJECT 判定は contaminated data に基づくため supersede 対象**:

| 項目 | rev1 (本 review) | rev2 (正しい SSOT) |
|---|---|---|
| Live N | 917 (`is_shadow=0`) | **371** (`is_shadow=0 AND oanda_trade_id != ''`) |
| Bucket 構成 | TRUE_LIVE 736 + FLAG_DRIFT 181 混合 + post-cutoff未適用 | TRUE_LIVE only, post-cutoff `entry_time >= 2026-04-08` |
| 旧主犯リスト 6戦略 | drag 扱い | **fib_reversal +0.3pip / vol_surge_detector +2.2pip 黒字、`macdh_reversal` / `sr_fib_confluence` は N<5 Insufficient** |
| ELITE_LIVE 異常 | 未検出 | **`session_time_bias × GBP_USD` -28.0pip (N=7), 即時 WATCH 格上げ要検討** |

**結論**: 本 review の REJECT verdict は **そのまま roadmap 判断に使用してはならない**。rev2 task (`.ai/tasks/queue/20260503-1815-r2-strategy-instrument-counterfactual.md`, revised_at 2026-05-03T18:50:00) で TRUE_LIVE bucket の正しい counterfactual を再実行する必要がある。本セッション中の追加変更:

- A1 task `20260503-1840-tier1-live-edge-audit.md` は引き続き有効 (corrigendum は同じ Tier 1 LIVE concern を強化する方向)
- 本 review doc は **歴史記録 (Codex deliverable ACCEPT)** として保持。verdict は **REJECT_SUPERSEDED** に rename

---

## 以下、rev1 verdict (contaminated data version, 歴史記録目的)


# R2 Strategy × Instrument Counterfactual Review — Tier 1 LIVE 戦略の真価が問われる

## 判定: ACCEPT (Codex deliverable) / REJECT (Gate 0 復帰)

Codex 成果物は仕様通り完全に納品。greedy worst-first counterfactual が data-driven に「救済不能」を確定。**verdict は REJECT — H4 (Tier 1 LIVE 戦略再評価必要) が fired**。

## Codex 成果物 (ACCEPT 相当)

- `tools/r2_strategy_instrument_counterfactual.py` 新規実装 (3値 lot {KEEP, LOT_HALF, STOP_OANDA} + greedy worst-first)
- `tests/test_r2_strategy_instrument_counterfactual.py` 6 tests pass
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` verdict + counterfactual table 完備
- `app.py` / `modules/` / `strategies/` 編集 0件 (LOCK proposal scope 遵守)

## 主要 quant 結果

| ケース | N | raw Kelly | clipped Kelly | MC60d 破産 | EV pip | PF | maxDD | total pip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Baseline** | 917 | -0.1737 | 0.0000 | **100.00%** | -0.79 | 0.695 | 74.80% | -720.0 |
| Greedy post-cut (14 cell STOP) | 363 | **-0.1932** | 0.0000 | 97.20% | -1.21 | 0.663 | 45.91% | -438.7 |
| All 20-cell STOP | 317 | -0.2536 | 0.0000 | 99.40% | -1.50 | 0.589 | 49.50% | -474.6 |

**Bonferroni m = 20 strategy × instrument cell, α' = 0.0025**。

## 致命的発見 — drag 除去で aggregate がさらに悪化

| 視点 | 数字 | 解釈 |
|---|---|---|
| 削除 cell 数 | 554 trade (14 cell STOP) | 6戦略のworst-first を全部除去 |
| 残存 N | 363 trade | Tier 1 LIVE + その他 small-N 戦略 |
| 残存 Kelly | -0.1932 | **drag 除去後も負** |
| 結論 | 残存 363 trade 自体が負 EV | **Tier 1 LIVE 戦略 (gbp_deep_pullback / trendline_sweep / session_time_bias) が Live で BT 期待を満たしていない可能性** |

### KEEP cell の microscopic edge (verdict 補強)

protected KEEP cell 6件のうち N≥30 は **0件**。最大は bb_rsi_reversion×GBP_USD (N=9, EV=+0.81) で sample size が statistical edge を担保しない。Bonferroni-significant cell は **0**。

## ロードマップ含意

- **Gate 0 (生存)**: 救済経路 fail。R2 cell-level → strategy×instrument level の二段階 demote では Kelly < 0 を超克できない。
- **真因仮説**: Tier 1 LIVE 戦略 (gbp_deep_pullback / trendline_sweep / session_time_bias) が **BT で +EV だが Live で 0 〜 -EV** に劣化している可能性。`wiki/analyses/bt-live-divergence.md` の 6 構造的楽観バイアスのいずれか or 複数が顕在化している。
- 月利100%ロードマップは引き続き **凍結相当**。

## データ分離確認

- 一次ソース: `/tmp/live-trades-20260503.json` (Render API live trades 100,000 limit, exit 6 で curl 失敗のため前段監査と同一 snapshot 使用)
- Live filter: `is_shadow=0 AND status=CLOSED AND outcome IN (WIN/LOSS/BREAKEVEN) AND pnl_pips != null`
- XAU 除外、Shadow 3,930 件混入なし
- OANDA 転送停止 / lot 変更 / 本番 DB 書き込みは未実施 (LOCK proposal の通り)

## 次の必要分析

`feedback_ma_filter_breaks_mr` / `feedback_label_empirical_audit` 教訓を踏まえつつ:

### Path A — Tier 1 LIVE 戦略の Live 実測 audit (即実施)

各 Tier 1 LIVE 戦略 × instrument の Live N / WR / EV / PF / Wilson_lo / Bonferroni p を計算:

- `gbp_deep_pullback` × `GBP_USD` (BT: N=77, WR=75%, EV=+1.064)
- `trendline_sweep` × `GBP_USD` (BT: N=134, WR=73%, EV=+0.599)
- `session_time_bias` × `USD_JPY` (BT: N=157, WR=79%, EV=+0.580)
- `session_time_bias` × `EUR_USD` (BT: N=566, WR=70%, EV=+0.215)
- `xs_momentum` × `USD_JPY` (BT: N=342, WR=69%, EV=+0.270)

**ACCEPT 条件**: 上記 5 cell のうち少なくとも 1 cell で Live Wilson_lo > BEV_WR (one-sided p < α'=0.05/5=0.01) を満たす edge が残存。
**REJECT 条件**: 5 cell 全てで Wilson_lo < BEV_WR → 全 Tier 1 LIVE OANDA 停止検討、根本的 portfolio rebuild。

### Path B — H4 (BT-Live divergence 構造 audit)

`wiki/analyses/bt-live-divergence.md` の 6 楽観バイアスを実測値で再検証:

1. Spread/slippage 過小評価
2. Adverse fill/queue position
3. Survivorship bias in BT lookback
4. Live のmtf-cascade timing miss
5. Live の OANDA execution latency
6. Live の session boundary effect (Tokyo→London)

## 次タスク提案

**A1 (R2/R3) — `tier1-live-edge-audit-2026-05-03`** (R2 Fast & Reactive):

Tier 1 LIVE 5 cell の Live 実測 audit (Path A)。BT 期待を Live が満たさない cell を特定し、demote / lot 削減候補を出す。N≥30 cell に Bonferroni m=5 適用。

- 出力: `wiki/decisions/tier1-live-edge-audit-2026-05-03.md`
- ACCEPT/NEEDS_MORE_EVIDENCE/REJECT の 3 値判定
- ACCEPT なら delta-from-BT 表 + demote 推奨セット

REJECT なら Path B (構造 audit) に分岐。

## ステータス遷移

- `.ai/tasks/queue/20260503-1815-r2-strategy-instrument-counterfactual.md` → `.ai/tasks/done/`
- 後続: A1 (Tier 1 LIVE edge audit) を新規 task として queue
