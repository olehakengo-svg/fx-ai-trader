---
date: 2026-05-03
task: 20260503-1747-r2-cell-demotion-lock-list
verdict: ACCEPT
rule: R2
gate: Gate 0 復帰（cell-cut 単独では不可、ただし減損効果あり）
---

# R2 cell-demotion LOCK list — ACCEPT decision

## Verdict

**ACCEPT** — Rule 2 R2 cell-level 監査として 10 受け入れ条件すべて充足。Codex 自身の `REJECT_INSUFFICIENT` verdict は honest かつ正しい数学的結論。

## Acceptance summary

- 4 区分 cell 表（STOP_OANDA=15, LOT_HALF=3, WATCH=多数, KEEP=147）✅
- 各 cell に N/WR/Wilson lo/EV/raw Kelly/total/PF/Bonf p/maxDD ✅
- Counterfactual aggregate (Kelly/MC/EV/Wilson lo/PF/maxDD) ✅
- Bonferroni m=394 pre-reg LOCK (α'=0.000127)、事後変更なし ✅
- KEEP cell 147 件で EV>0 / Wilson_lo>0.50 / raw Kelly>0 cell を明示維持（Bonferroni-significant edge 保護）✅
- PR template (`feat/r2-cell-demotion-2026-05-03`) ✅
- MC 1000 sim, 60d horizon, ruin=peak DD 50% of 1000p ✅
- pgrep -f app.py: sandbox-restricted-fallback 明示 ✅
- `feedback_ma_filter_breaks_mr` 整合: KEEP cell 保護で bb_rsi_reversion の正 cell（13+）破壊なし ✅
- Tests: 3 passed ✅

## Data hygiene

- Live N=917 (`is_shadow=0`, `status=CLOSED`, `pnl_pips!=null`), XAU除外
- Shadow 3930 件 baseline 比較のみで集計混入なし
- BT/Live/OANDA 一切混在なし
- Read-only audit、OANDA転送・lot変更・本番DB書き込み・`.env` 一切 untouched

## Counterfactual (数値)

| 軸 | Baseline | Post-cut (15 STOP + 3 LOT_HALF) | Δ |
|---|---:|---:|---:|
| N | 917 | 808 | -109 (-12%) |
| raw Kelly | **-0.1737** | **-0.1381** | +0.0356 |
| MC60d | 1.0000 | 0.9970 | -0.30pp |
| EV/trade | -0.79p | -0.63p | +0.16p |
| total pip | -720p | -512p | +208p |
| max DD | 74.80% | 55.05% | -19.75pp |

→ **Cell-cut 単独で Gate 0 復帰は数学的に不可能**（Kelly 依然負、MC 実質 100%）。
→ 減損抑制効果は確実（maxDD -19.7pp, total +208p）。

## 構造的発見（Codex の cell リストから読み取り）

- 18 R2 候補のうち **13 が `bb_rsi_reversion`**（USD_JPY hours 04/05/10/11/13/16/17/18 + EUR_USD hours 06/09/12）
- 同戦略は KEEP 側にも 13+ cell（USD_JPY hours 00/01/03/06-09/12/14/15/19/20 等で Kelly +0.005〜+0.32）
- **bipolar hour-bucket profile** — Tokyo/早期London エッジ、late-NY/夕方 構造的負け
- 戦略全停止（Tier 降格）は KEEP cell のエッジを巻き添えにする → **cell-level アプローチは正しい**

## Roadmap impact

- **Gate 0 復帰**: 単独タスクで達成不可（cut 後も Kelly=-0.14、MC60d=99.7% で死線）
- **減損抑制**: 価値あり（提案 cut PR 化推奨）
- **本質的 Gate 0 復帰**: 新規 +EV 戦略追加（Wave 3 / Scalp pre-reg BT）が必要であることを Codex が data-driven に証明
- **教訓更新候補**: 「aggregate Kelly 復帰には demotion 単独では不足。`+EV 戦略追加 × demotion` の両輪必須」

## Artifacts

- 監査スクリプト: `tools/r2_cell_demotion_audit.py` (16.5 KB)
- テスト: `tests/test_r2_cell_demotion_audit.py` (3 passed)
- レポート: `knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md` (407 行)
- 親 audit: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`

## Next task

Codex 提案 cell cut の OANDA routing override 実装 PR は司令塔承認後の R2 別タスクで spawn 可能。並行して Wave 3 BT で +EV 戦略を追加し、両輪で Gate 0 復帰を狙う。
