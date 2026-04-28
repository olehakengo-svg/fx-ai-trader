# Pre-reg LOCK: Overlap session cells (2 件追加)

**Date**: 2026-04-28
**Audit source**: 86-cell v3 audit (cell_edge_audit --mode v3 --include-shadow --window 30d --min-n 10)
**Rule**: R1 (Slow & Strict — pair × direction × session promotion)
**Trigger**: ユーザー指示 "shadow に新戦略を追加開始 (cell-Bonferroni audit で WATCH 候補から 5〜10 個ピックアップ)"

## Discovery

86 qualified cells (N≥10, 30d) で **3 件**が `raw_EV > 0 ∧ Wilson 95% lower > 0.40` を満たす:

1. **bb_rsi_reversion × EUR_USD × BUY × Overlap × Scalp** — 既存 LOCK ([[pre-reg-bbrsi-eurusd-2026-04-27]])
2. **vol_surge_detector × USD_JPY × SELL × Overlap × Scalp** — 本 LOCK ✨
3. **ema_cross × USD_JPY × SELL × Overlap × DT** — 本 LOCK ✨

**共通点**: Overlap session (UTC 12-16, London/NY 重複) に edge が集中。

## Pre-reg LOCK #1: vol_surge_detector × USD_JPY × SELL × Overlap × Scalp

| 項目 | 実測値 | 閾値 | 判定 |
|---|---:|---:|:---:|
| N | 11 | 30 (gate) | ⚠ 19 不足 |
| WR | 81.8% | — | — |
| Wilson 95% lower | 52.3% | 50% | ✓ |
| Wilson_BF (k=86) lower | **38.7%** | 29.4% (BE) | ✓ |
| Wilson_BF (k=624) lower | TBD | 29.4% | TBD |
| EV (raw) | +6.72 pip | 0 | ✓ |
| EV (after 1.5pip friction) | +5.22 pip | 0 | ✓ 強 |
| Profit Factor | 8.78 | 1.0 | ✓ 非常に強 |

**現在の tier**: `pair_demoted` (USD_JPY を含む 4 pair 全敗) — Aggregate Fallacy 事例。

### Trigger to PROMOTE
```yaml
shadow_n_in_cell  >= 30
wilson_bf_lower(k=624, z=3.94) > 0.294
binomial p_bonferroni < 0.05
WF halves verdict in {stable, borderline}
avg_net (post pair-friction USD_JPY = 2.14pip) > 0
unique_days >= 7
session_filter: UTC 12-16 (Overlap)
```

### Action when PROMOTE
- `tier_master.json` `pair_promoted` に [vol_surge_detector, USD_JPY] 追加
- 戦略コードに `if direction != "SELL" and session != "Overlap": return None` 暫定 filter
- lot=0.01 で 30 trades or 14日 mini-pilot
- Aggregate Kelly>0 ∧ DD<2% で A2 boost 経由で 0.05→0.2 へ scale

### Trigger to DISQUALIFY
- N≥30 で Wilson_BF (k=624) ≤ 0.294
- WF verdict = collapse (H1>0 ∧ H2<0)
- 4週間期限 (2026-05-26) 超過で N<30
- friction 控除後 avg_net ≤ 0

## Pre-reg LOCK #2: ema_cross × USD_JPY × SELL × Overlap × DT

| 項目 | 実測値 | 閾値 | 判定 |
|---|---:|---:|:---:|
| N | 13 | 30 (gate) | ⚠ 17 不足 |
| WR | 69.2% | — | — |
| Wilson 95% lower | 42.4% | 50% (strict gate) | ⚠ borderline |
| Wilson_BF (k=86) lower | **31.4%** | 29.4% (BE) | ✓ |
| Wilson_BF (k=624) lower | TBD | 29.4% | TBD |
| EV (raw) | +5.88 pip | 0 | ✓ |
| EV (after 2.14pip friction) | +3.74 pip | 0 | ✓ |
| Profit Factor | 3.01 | 1.0 | ✓ |

**現在の tier**: `QUALIFIED_TYPES` (DT) — 通常運用中。

### Trigger to PROMOTE
```yaml
shadow_n_in_cell  >= 30
wilson_bf_lower(k=624, z=3.94) > 0.294
binomial p_bonferroni < 0.05
WF halves verdict in {stable, borderline}
avg_net > 0
unique_days >= 7
session_filter: UTC 12-16 (Overlap)
direction_filter: SELL
```

### Action when PROMOTE
- `tier_master.json` `pair_promoted` に [ema_cross, USD_JPY] 追加 (DT mode 限定)
- session+direction filter は signal レベルで適用
- lot=0.01 から段階展開

## クオンツ判断の動機 (CLAUDE.md「動機の記録」)

- ✅ **データ駆動**: 86-cell Bonferroni audit で複数 STRICT cell を発見
- ✅ **Shadow asymmetric bet**: Live 投入なし、shadow 蓄積のみ — 実害ゼロ ([[lesson-shadow-vs-live-confusion-2026-04-28]])
- ✅ **既存 KB との整合**: bb_rsi_reversion LOCK と同方式 (cell-level Pre-reg)
- ✅ **Overlap session の cluster** が 3 cells に共通 → 単独偶然ではない (構造的 edge の可能性)
- ❌ **HARKing 防止**: trigger 条件を deploy 前に明示文書化、後付け緩和不可

## 次のアクション

1. `tools/prereg_lock_monitor.py` の `PREREG_LOCKS` リストに本 2 件を追加
2. 週次 cell_edge_audit で N 蓄積を追跡
3. 期限 2026-05-26 までに trigger 全通過なら mini-pilot 起動
4. **Overlap session 全戦略の網羅 audit** を別タスクで実施 (隠れた他 cell 発掘)

## 関連 KB

- [[pre-reg-bbrsi-eurusd-2026-04-27]] (既存 STRICT LOCK)
- [[../../raw/audits/cell-bonferroni-2026-04-27]] (audit framework)
- [[lesson-shadow-vs-live-confusion-2026-04-28]] (shadow asymmetric bet 原則)
- [[../syntheses/roadmap-v2.1]] (Gate 1: Kelly>0 への発掘パス)
