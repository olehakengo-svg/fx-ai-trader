# Lesson: Cell-conditional BT が必須 (2026-04-27)

## 一行要約

**Cell-level Bonferroni-significant な Shadow edge を発見した時、cell-conditional BT (180d 以上) を走らせる前に Live promote するな。**

## 背景

2026-04-27 セッションで、Q1' Cell-by-Cell Edge Audit (`tools/cell_edge_audit.py`) を実行し、**fib_reversal × USD_JPY × Tokyo × q0 × Scalp** に以下の指標を確認:

- N=24 (全 Shadow), WR=87.5%, Wilson lower=69.0%, EV=+10.82pip
- Bonferroni p=0.0007 (3 cells テスト後)
- Kelly Half=0.408

統計的に堅い数字に見えたため、Pre-reg LOCK 起案 → 0.05 lot Live (5000u) で C1-PROMOTE bypass を実装、本番デプロイ済 (commit `7437e19`)。

## 失敗

ユーザー指摘 ("KB を理解したクオンツとしての提案か?") を契機に KB 再読:

1. **fib_reversal は KB で `FORCE_DEMOTED (Recovery Path Active)`** だった
   - post-cutoff WR=40.6% (N=32) — Q1' subset (WR=87.5%) と乖離
   - 180d Scalp BT で **EV符号反転確認** (60d +0.271 → 180d -0.147)
2. **既存 BT cache** (`data/cache/bt_scan_scalp_results.json`) を見れば 180d aggregate **EV=-0.308** が判明していた
   - aggregate negative 環境で subset positive を見つけたら **subset outlier 警戒** が当然
3. **Recovery Path 段階を完全 skip**
   - 正しい pathways: `N≥30 & WR≥50% → SENTINEL (0.01 lot)` → `N≥50 & WR≥52% & PF>1.1 → PAIR_PROMOTED`
   - 私は Live N=0 から 0.05 lot に直接昇格させた

## 教訓 — クオンツ規律の 3 段階防御

将来 cell-level 統計分析から Live promote する際、必ず以下の 3 段階防御を経ること:

### 段階1: KB 必読プロトコル (CLAUDE.md 既存ルール)

- `wiki/strategies/{戦略名}.md` を読む — Tier, Recovery Path, 過去判断履歴
- `wiki/decisions/` で関連判断を読む — past 過剰反応・過小反応事例
- `wiki/analyses/shadow-deep-mining-*.md` で「dead」判定の対象/対象外を確認
- `wiki/lessons/` で類似パターンを確認 (lesson-orb-trap-bt-divergence 等)

### 段階2: cell-conditional BT 必須

cell-level edge を発見したら、**その cell の条件を BT runner に渡して 180d 以上で再現確認**:

```python
# 例: fib_reversal × USD_JPY × Tokyo × spread≤0.8pip × scalp 1m を 180d で検証
python3 tools/bt_scalp_lab.py \
  --strategy fib_reversal \
  --pair USD_JPY \
  --session-filter "0<=hour<7" \
  --spread-max 0.8 \
  --window 180d
```

合格条件:
- 180d cell EV > 0 (positive)
- 180d cell WR > BEV_WR (pair friction-adjusted breakeven)
- 60d / 180d で同符号 (lesson-orb-trap-bt-divergence 回避)

不合格なら **subset outlier 確定** で Live promote 中止。

### 段階3: Recovery Path lot サイズ整合

cell-conditional BT が positive でも、いきなり Kelly Quarter / Half lot に飛ばない:

- Live N=0 → **Recovery Path SENTINEL (0.01 lot)** で開始
- Live N≥10 で WR>50% 維持 → 0.05 lot
- Live N≥30 で WR>50% & PF>1.1 → PAIR_PROMOTED 通常 lot
- 各段階で daily_live_monitor.py の severity=OK を維持

## 反例 — このルールに違反する場合

「Bonferroni p<0.001 だから即 PROMOTE」ロジックは Shadow→Live 構造的 drift を見落とす:
- Shadow 環境は order 受発注のみで execution friction が Live より低い
- Live spread は Shadow より広い瞬間が多い
- Bonferroni は Shadow 内部の偶然性しか除外しない

→ **Bonferroni 統計 + cell-conditional BT + Recovery Path lot** の 3 重防御で初めて OOS 安全。

## 関連 lesson

- [[lesson-orb-trap-bt-divergence]] — 60d positive 戦略が 180d で逆になった例
- [[lesson-asymmetric-agility-2026-04-25]] — Rule 1/2/3 の判断プロトコル
- [[lesson-reactive-changes]] — 1日データで code 変更禁止
- [[lesson-clean-slate-2026-04-16]] — 過去判断を踏まえる規律

## 関連 decision

- [[pre-reg-cell-promotion-2026-04-27]] — C1-PROMOTE の Pre-reg LOCK + lot 縮小経緯
- [[external-audit-2026-04-24]] — 過剰最適化検出の枠組

## Status

Active — 次回 cell promote の際、この lesson を session-start hook 経由で必ず注入する。
