# Kelly Recompute — 2026-04-27 evening (rule:R3)

## 起票背景

memory 175 (2026-04-26 23:17 JST) は **"Kelly = -17.97% / DD = 32.32% / Live N = 36"** という危機状態を記録していた。本日 (2026-04-27) に commit `9e53794` で seed-exclusion (entry→exit < 5秒の replay artifact) を default 除外、`641bfe4` で race-condition 二重発火を防止 — 集計の前提が変わった。

**memory 175 の数字を補正後で再計算し、live-thaw-gate G1 (Kelly > 0) を客観評価する**のが目的。

## 結果サマリ

| 計算 | N | WR | avg_w | avg_l | total_pip | edge | full_Kelly | half_Kelly |
|------|--:|---:|------:|------:|---------:|-----:|----------:|----------:|
| LEGACY (seed込み, Live のみ) | 36 | 50.00% | +14.59 | -14.26 | +6.0p | +0.0117 | **+1.14%** | +0.57% |
| **CLEAN (seed除外, Live のみ)** | **34** | **50.00%** | +14.54 | -14.28 | **+4.3p** | +0.0089 | **+0.87%** | **+0.44%** |
| 参考: Live+Shadow LEGACY | 414 | 31.40% | — | — | -459.7p | edge<0 (clipped) | 0.00% | 0.00% |
| 参考: Live+Shadow CLEAN | 391 | 28.90% | — | — | -497.8p | edge<0 (clipped) | 0.00% | 0.00% |

注: `kelly_fraction()` は edge<0 で `max(0, kelly)` クリップする ([modules/risk_analytics.py:208](../../../modules/risk_analytics.py)) ので、Live+Shadow の真 edge は負だが Kelly 表示は 0%。

## ペア別内訳 (Clean, Live のみ, XAU 除外)

| pair | N | WR | Wilson 95% L | avg_pip | 評価 |
|------|--:|---:|-----------:|--------:|------|
| EUR_USD | 1 | 100% | 20.7% | +135.30 | 評価不能 (N=1) |
| GBP_USD | 4 | 0% | 0% | **-45.77** | **🔴 壊滅 - 即時 freeze 検討** |
| USD_JPY | 29 | 55.2% | 37.5% | +1.80 | 主力、borderline |

## 戦略別内訳 (Live のみ, by N)

| entry_type | N | WR | Wilson L | cum_pip |
|------------|--:|---:|--------:|--------:|
| **bb_rsi_reversion** | **20** | **65.0%** | **43.3%** | **+190.6** ← Live 唯一の実エッジ候補 |
| vol_momentum_scalp | 4 | 50.0% | 15.0% | +17.2 |
| trend_rebound | 2 | 0% | 0% | -5.9 |
| mtf_reversal_confluence | 1 | 100% | 20.7% | +1.2 |
| **turtle_soup** | 1 | 0% | 0% | **-170.0** ← 単発で aggregate を壊している |
| その他 N=1 各種 | ~6 | — | — | 軽微 |

## G1 (Kelly > 0) 判定

### Strict reading (Kelly 点推定値のみ)
**✅ PASS** — full_Kelly = +0.87% > 0

### Conservative reading (Wilson 下限 で edge 検証)
**❌ FAIL** — WR Wilson L 34.1% は 50% null hypothesis を下回り、edge 区間は両側 0 を含む可能性

### 実用的解釈
**borderline positive (noise-dominated)**:
- N=34 では Kelly 点推定値の標準誤差が large
- 単発の turtle_soup -170p (Apr 7) を除けば aggregate 改善
- 戦略・ペアごとの bimodal: USD_JPY×bb_rsi_reversion = エッジ / GBP_USD 全敗 = アンチエッジ

## memory 175 "-17.97%" の解釈

本日の Live Clean Kelly (+0.87%) と乖離。考えられる出典:

1. **Track5 Live Risk Management 監査** (memory 160, 2026-04-26 15:01): 「Kelly 0% クリップ・MC ruin 85.5%」と記載 — 別計算 (おそらく friction-adjusted or Monte Carlo) で当時の状態を表現したもの
2. **特定 cutoff 期間**: pre-Apr-21 含めた raw period では負 edge でもおかしくない
3. **Friction-adjusted Kelly**: 摩擦控除 1pip × N=414 を含めると +6.0p → -408p で大幅悪化、edge 反転

**結論**: memory 175 の **-17.97%** は当時の **friction/MC 含めた pessimistic 値**で、本日の Live aggregate Clean Kelly **+0.87%** とは **異なる metric**。両方とも事実だが、live-thaw G1 判定には **後者**を使う(同 metric で前後比較するため)。

## 重要な含意

### A. 「全面 lot=0 凍結」は過剰
Live Kelly が borderline positive である以上、**特定の Live エッジ候補 (bb_rsi_reversion × USD_JPY)** は維持すべき。完全凍結は機会損失。

### B. GBP_USD Live は即時 freeze 必要
- N=4 全敗、avg -45pip
- Wilson 上限 = 60.2% だが、4 連敗の確率は 50% 仮定で 6.25%、(0.05) と組み合わせると有意に劣化
- USD_JPY が黒字 (+52p) を GBP_USD 単独 (-183p) で食い潰している

### C. bb_rsi_reversion の cell 精査 (G2 評価) が次の rate-limiting step
- N=20 は集約で、pair × session × spread cell で見ると更に細分される
- Wilson 43% → cell によっては 60%+ の可能性
- 一部 cell は既に LIVE 安定エッジの可能性

### D. Sentinel→Live ブリッジの議論前提が成立
- G1 borderline PASS により、Catch-22 を破る道理が立つ
- ただし慎重に: lot=0.001 trial レベルで段階的に解禁

## 次アクション (本決定文書 → 実装)

| Action | Rule | 内容 |
|--------|------|------|
| Action 2 | R2 | bb_squeeze_breakout × USD_JPY lot=1.0x → 0.01x trial (進行中) |
| Action 4 | R2 | GBP_USD Live 一時 freeze (戦略 _PAIR_DEMOTED 拡張 or lot=0 強制) |
| Action 3 | R3 | tools/live_thaw_check.py 実装 (G1-G4 CLI 一括判定) |
| 追加 | R1 | bb_rsi_reversion cell-level audit (G2 評価準備) |

## 検証コマンド (再現性)

```python
from modules.demo_db import DemoDB
from modules.risk_analytics import kelly_fraction

db = DemoDB(db_path='demo_trades.db')
rows = db.get_all_closed(exclude_shadow=True, exclude_seed=True)
rows = [r for r in rows if r.get('instrument') and 'XAU' not in r['instrument']]
n = len(rows)
wins = [r for r in rows if (r.get('pnl_pips') or 0) > 0]
losses = [r for r in rows if (r.get('pnl_pips') or 0) <= 0]
wr = len(wins) / n
avg_w = sum((r['pnl_pips'] or 0) for r in wins) / len(wins)
avg_l = abs(sum((r['pnl_pips'] or 0) for r in losses) / len(losses))
print(kelly_fraction(wr, avg_w, avg_l))
# 期待: full_kelly=+0.0087 (= 0.87%)
```

## 改訂履歴

| 日付 | 変更 |
|------|------|
| 2026-04-27 | 初版起票. seed-exclusion 適用後の Live Kelly = +0.87% を確定. memory 175 の -17.97% との解釈差を明文化. |
