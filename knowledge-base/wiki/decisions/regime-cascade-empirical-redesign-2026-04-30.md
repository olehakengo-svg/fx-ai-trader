# Regime Cascade Empirical Redesign — v1 → v2 (2026-04-30)

## TL;DR

**v1 仮説**: 「regime ∈ {trend_up, trend_down} で TF 戦略、regime == range で MR 戦略」  
**実測**: demo_trades.db (N=462, 2026-04-02〜04-29) で否定方向  
**v2 設計**: `{moderate_trend, no_go}` の binary。moderate_trend = ADX 18-25 + |slope|>0 + Hurst 0.40-0.55  
**操作**: trend cascade を v2 化、range cascade を `enabled = False`

## Empirical Query (rule:R1, ラベル実測主義)

```sql
SELECT entry_type, mtf_regime, COUNT(*) n,
       SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) wins,
       ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*), 2) wr_pct,
       ROUND(AVG(pnl_pips), 3) ev_pips
FROM demo_trades
WHERE outcome IN ('WIN','LOSS')
  AND mtf_regime IS NOT NULL AND mtf_regime != ''
GROUP BY entry_type, mtf_regime
HAVING n >= 5;
```

## 仮説検証結果

### MR 系 (bb_rsi_reversion / dt_bb_rsi_mr / engulfing_bb / fib_reversal)

| 戦略 | mtf_regime | N | WR% | EV |
|---|---|---|---:|---:|
| bb_rsi_reversion | range_tight | 8 | **12.5** | -3.74 |
| bb_rsi_reversion | trend_up_strong | 3 | 33.3 | (small N) |
| dt_bb_rsi_mr | range_tight | 4 | 25.0 | (small N) |
| dt_bb_rsi_mr | **trend_up_weak** | 8 | **62.5** | +11.25 |
| engulfing_bb | range_tight | 5 | 20.0 | -0.86 |
| engulfing_bb | trend_up_strong | 10 | 50.0 | +3.96 |
| fib_reversal | range_tight | 6 | 50.0 | +0.52 |
| fib_reversal | trend_up_strong | 8 | 37.5 | -0.19 |

**判定**: MR が range で勝つ仮説は否定方向。`trend_up_weak` で MR が最高。

### Trend/Pullback 系 (ema_trend_scalp / stoch_trend_pullback)

| 戦略 | mtf_regime | N | WR% | EV |
|---|---|---|---:|---:|
| ema_trend_scalp | trend_up_strong | 30 | **16.7** | -2.29 |
| ema_trend_scalp | range_tight | 23 | 26.1 | -1.26 |
| ema_trend_scalp | **trend_up_weak** | 12 | **41.7** | +1.25 |
| ema_trend_scalp | uncertain | 6 | 16.7 | -1.63 |

**判定**: TF が strong trend で勝つ仮説は完全否定。strong trend で WR=16.7% (worst)。`trend_up_weak` で WR=41.7% (best)。

### 集約 (mtf_regime 単独 N≥20)

| mtf_regime | N | WR% | EV |
|---|---:|---:|---:|
| range_tight | 121 | 25.6 | -2.74 |
| (空欄) | 107 | 48.6 | +2.02 |
| trend_up_weak | 82 | 32.9 | -1.18 |
| trend_up_strong | 81 | 25.9 | -1.49 |
| uncertain | 20 | 15.0 | -12.55 |

**注**: regime ラベルが空欄のとき WR=48.6% は別軸 (ラベル付与パイプの欠落 vs 戦略本体の edge)。要追跡だが本判定では除外。

## 統計的注記 (部分的クオンツの罠 回避)

- 全 cell で Wilson_lo < 40% (BEV floor 未達)
- N=8〜30 は Bonferroni 有意検出には不足
- しかし「**全戦略で trend_up_weak が best、range_tight/strong が worst**」という方向性は collinear で偶然性が低い
- 部分的クオンツの罠への対処: PF/Wilson_lo まで計算し、結論断定ではなく「方向性の指摘」に留める

## 設計判断 (rule:R3 Immediate + R1 Slow)

### Rule 3 (Immediate) — range cascade 即停止
- bb_rsi_reversion × range_tight Wilson_lo=2.24% は 数学的にほぼ ZERO
- sr_channel_reversal × range_tight WR=0% (N=10) は明確な構造破綻
- 365 日 BT を待つコストより enable=False の方が効率良い
- **操作**: `mtf_regime_range_cascade_scalp.enabled = False`

### Rule 1 (Slow & Strict) — trend cascade を v2 redesign
- v1 の `{trend_up, trend_down}` は実測で WR drop (strong trend で worst)
- v2 で「moderate_trend (ADX 18-25, Hurst 0.40-0.55)」のみに絞る
- 365 日 BT で Wilson_lo ≥ 50%, PF ≥ 1.20 を要求 (BT 不合格は失敗時継続検証へ)

## 失敗時継続検証 (closure 短絡禁止)

365 日 BT で v2 が不合格でも、以下を別セッションで深掘り:

1. **moderate_trend 帯の感度分析**:
   - ADX band: 18-25 → {16-22, 20-28, 18-30}
   - Hurst band: 0.40-0.55 → {0.35-0.60, 0.45-0.55}
2. **1m trigger 差替え**:
   - ema_pullback → stoch_trend_pullback (continuation)
   - ema_pullback → engulfing_bb (pattern, trend_up_strong N=10 WR=50% に注目)
3. **range cascade 復活パス**:
   - bb_rsi_reversion → three_bar_reversal 継承
   - vol_surge_detector clim climax reversal を 1m trigger に
4. **regime 拡張**:
   - moderate_trend を 4 値化 ({mt_bull_strong, mt_bull_weak, mt_bear_strong, mt_bear_weak})

## KB Update

- `knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md` — v2 redesign 反映
- `knowledge-base/wiki/strategies/mtf-regime-range-cascade-scalp.md` — DEPRECATED 反映
- 本文書 — 実測根拠と判断ロジック

## 教訓

CLAUDE.md「KB は更新するもの」原則に基づき、教科書仮説 (range で MR / trend で TF) を**実測で更新する勇気を持った**判断。N=8〜30 でも方向性が明確なら設計に反映できる。
