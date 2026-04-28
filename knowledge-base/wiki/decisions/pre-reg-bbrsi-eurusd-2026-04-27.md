# Pre-reg LOCK: bb_rsi_reversion × EUR_USD × BUY × Overlap

**Date**: 2026-04-27
**Audit source**: `raw/audits/cell-bonferroni-2026-04-27.md`
**Rule**: R1 (Slow & Strict — pair promotion 候補)
**Author**: クオンツ判断 (KB + 新データ整合確認済み)

## 背景

`tools/cell_edge_audit.py --mode v3` を全 52 戦略の production data (3,075 trades, 30d, post-cutoff 2026-04-08) に展開した結果、**49 qualified cells (N≥15) のうち唯一 Wilson_BF (k=52) > breakeven_wr を満たした cell**。

| 項目 | 実測値 | 閾値 | 判定 |
|---|---:|---:|:---:|
| N (live + shadow) | **19** | 20 (gate min) | ⚠ −1 |
| wins | 14 | — | — |
| WR | 73.7% | — | — |
| Wilson 95% lower | 51.2% | 29.4% | ✓ |
| **Wilson_BF (k=52) lower** | **37.2%** | **29.4%** | **✓** |
| Wilson_BF (k=624) lower | 22.7% | 29.4% | ✗ |
| EV (raw) | +2.10 pip | 0 | ✓ |
| EV (-2.0pip rough friction) | +0.10 pip | 0 | ✓ borderline |
| Profit Factor | 2.86 | 1.0 | ✓ |
| Binomial p (Bonferroni) | 1.000 | 0.05 | ✗ |
| Binomial p (BH-FDR) | 0.0707 | 0.05 | ✗ |

## なぜ即時昇格しないか

1. **N=19 < 20**: gate minimum N に1サンプル不足
2. **Binomial p_bonf=1.0**: Wilson 下限は通過するが、両側検定で「ランダムから有意差」を強く棄却できない
3. **Wilson_BF (k=624)**: 厳密な 3軸 (strategy × pair × direction) 検定多重性補正では FAIL
4. **friction 控除後 EV +0.10**: 利益率は薄く、live で 1〜2 trade の悪結果で容易に負転

## Pre-reg LOCK 条件

### Trigger to PROMOTE (全条件 AND)

```
shadow_n_in_cell  >= 30                         (現在 19 → +11 蓄積必要)
wilson_bf_lower(k=624, z=3.94) > 0.294
binomial p_bonferroni < 0.05
WF halves verdict in {stable, borderline}        # collapse は失格
avg_net_pips (post pair-friction) > 0
unique_days >= 7
```

### Action when PROMOTE

1. `tier_master.json` の `pair_promoted` に `[bb_rsi_reversion, EUR_USD]` 追加 (`scalp_sentinel` から外す)
2. `strategies/scalp/bb_rsi.py` に direction filter 暫定挿入: `if direction != "BUY" and instrument == "EUR_USD": return None`
3. session filter 暫定挿入: Overlap (UTC 12-16) 以外は signal 抑制
4. lot=0.01 で 30 trades or 14日 mini-pilot
5. 通過 → standard lot (0.05) で ELITE 候補昇格、失敗 → `scalp_sentinel` 復帰

### Trigger to DISQUALIFY

```
ANY ONE:
  - shadow_n >= 30 で wilson_bf_lower (k=52) <= 0.294
  - WF halves verdict = collapse  (H1>0 ∧ H2<0)
  - 4週間経過 (= 2026-05-25 期限) でも N < 30
  - production で別エッジ (post_news_vol etc) と signal 重複が頻発
```

## Risk Budget

- 現在 Live N=36 / DD=32% 状態 → 月利100%目標まで非常に遠い
- mini-pilot lot=0.01 = ¥1〜2 / trade のリスクは許容範囲
- 失敗時の DD 影響: 30 trade × 平均-3pip × 0.01 lot = -90 pip × ¥10/pip = ¥900 max

## 反対意見の検討

**Q1**: bb_rsi_reversion は `scalp_sentinel` で「永久 demote」では?
- **A**: tier_master.json の `scalp_sentinel` は「Scalp 戦略全体の品質保証」であり cell 別エッジは別レイヤー判断。**Aggregate Fallacy 防止原則** (CLAUDE.md) により cell-level edge を尊重する。
- ただし **N=30 + Wilson_BF (k=624) > BE まで** 待つことで「全体 sentinel」と「cell promotion」の整合を担保。

**Q2**: 過去 Live で bb_rsi_reversion EUR_USD はどうだった?
- production 30d では Live N=0 (shadow only)。よって Live ペーパーで実績ゼロ。Phase 0 → Phase 1 (mini-pilot) のステップを必須とする。

**Q3**: friction 2.0pip 想定は妥当?
- EUR_USD Overlap session の friction (friction_model_v2): rt=2.85 × DT_mult 1.0 × Overlap_mult 0.85 ≒ 2.42 pip。
- → friction 2.0 は楽観気味。再評価時には pair-specific friction (~2.4) を適用する。

## 監視 SLA

- **週次**: `tools/cell_edge_audit.py --mode v3 --strategy bb_rsi_reversion --window 30d --include-shadow`
- 結果を `wiki/strategies/bb_rsi_reversion.md` の「Phase B watch log」セクションに追記
- N / Wilson_BF / WF / EV の推移を可視化
- 期限 2026-05-25 で TRIGGER 評価

## クオンツ判断の動機 (CLAUDE.md「動機の記録」)

- ✅ **データ駆動**: 49 cells から Bonferroni-corrected で唯一通過
- ✅ **既存 KB との整合性**: bb_rsi_reversion 全体 sentinel と矛盾しないよう **cell-level Pre-reg LOCK** に留める (即昇格しない)
- ✅ **動機**: 月利100%目標への寄与可能性 (新エッジ発掘) — ただし sample 不足で一時保留
- ❌ **感情的でないか**: 「73.7% WR は魅力的」ではなく「N=19 では p_bonf=1.0 のため判定不能」を優先

## 関連 KB

- `raw/audits/cell-bonferroni-2026-04-27.md` (本audit)
- `wiki/strategies/bb_rsi_reversion.md` (戦略概要)
- `wiki/analyses/friction-analysis.md` (EUR_USD friction)
- `wiki/lessons/lesson-aggregate-fallacy-2026-XX-XX.md` (Aggregate Fallacy原則)
