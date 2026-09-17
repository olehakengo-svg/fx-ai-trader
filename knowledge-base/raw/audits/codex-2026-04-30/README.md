# Codex 並列クオンツ監査 2026-04-30

10 sub-audit (Codex×7, Claude×3) + マスター統合 + 提言・パッチ提案。

## 主要結論 (3 行)

1. **LIVE 実弾 (is_shadow=0): N=36, Aggregate Kelly +0.385, 累計+6pip / outlier 除外 +176pip** → Gate 1 達成
2. 検出 bugs: **Sev1×14 / Sev2×36 / Sev3×12 = 計62件**。LIVE 経路に効く Sev1 は 6 件 (P0)
3. **bb_rsi_reversion 昇格提案は取り下げ** (時間コホート混同、システムは既に正しく demote 済み)

## 主要ファイル (top-level)

| ファイル | 内容 |
|---|---|
| `99-senior-quant-memo.md` | マスター統合メモ (v2 訂正版) |
| `06a-live-cell-stats.csv` | LIVE-only cell 集計 (15 cell) |
| `06a-cell-stats.csv` | 全 cell 集計 (146 cell, shadow 込み) |
| `06b-strategy-aggregate.csv` | 戦略別集約 (LIVE/SHADOW 分離) |
| `_gen_cell_stats.py` | 集計再生成スクリプト |

## サブ監査の生出力 (`_sub-audits/`)

各 sub-audit の raw Markdown (Codex × 7、Claude × 3)。再走時の比較用。

## パッチ提案 (`_patches/`)

| ファイル | 内容 |
|---|---|
| `PATCHES-P0-Sev1.md` | Sev1 P0 6 件 (S1/S2/S5/S6/S7/S8) の diff |
| `PATCH-DECISION-5-engine-sl-floor.md` | ScalperEngine SL mutation 廃止案 |
| `DECISION-1-RETRACTION.md` | bb_rsi_reversion 昇格提案の取り下げ理由 |

## 関連ツール (リポジトリ側)

- `tools/tier_live_drift.py` — Tier の Live drift 検出 (read-only、cohort 整合)

## 再走方法

```bash
# 集計 CSV 再生成 (is_shadow 分離込み)
python3 knowledge-base/raw/audits/codex-2026-04-30/_gen_cell_stats.py

# Live drift 検出
python3 tools/tier_live_drift.py
python3 tools/tier_live_drift.py --shadow-n 15 --bev 0.4  # 緩いしきい値
```
