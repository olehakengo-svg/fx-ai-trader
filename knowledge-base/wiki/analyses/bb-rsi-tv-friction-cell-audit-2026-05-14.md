# bb_rsi_reversion × USD_JPY 5m — TV Friction Cell Audit (2026-05-14)

**Rule**: R3 (Immediate) — friction is a math invariant, not a hypothesis.
**Status**: Pine v5 strategy replica + OANDA 実 friction (USDJPY 2.14 pip RT = 0.0136% RT, 0.0068% per side via `strategy.commission.percent`).
**Source**: `bt-results/tv-overlays/bb_rsi_reversion-replica.pine` (305 lines).

## Question

`bb_rsi_reversion` は friction を含めると BT で -EV だが、
**session × tier × H1 RSI × direction の 4 軸を分解したとき、
+EV を維持する cell が存在するか？** その cell に絞れば variant 化できるか。

## Method

TV Strategy Tester:
- Symbol: OANDA:USDJPY
- Timeframe: 5m
- Date range: 2025-05-14 → 2026-05-14 (1y)
- Commission: 0.0068% per side (RT = 2.14 pip ≈ 0.0136% at ~158)
- Pine 集計: `var int[]/float[]` accumulators across closed trades

## Result (overall, full 1y deep backtest)

| Metric | Value | Note |
|---|---|---|
| Total trades | 2,512 | strategy.closedtrades |
| Win rate | 30.65% (770/2512) | Floor (Tier1 RR≥3.0): 25.0% / Tier2 RR≥2.5: 28.6% |
| Profit factor | **0.605** | < 1.0 → -EV |
| Net P&L | **-¥312.82 (-3.13%)** | Initial capital 10,000 |
| Max DD | ¥313.31 (3.13%) | DD ≈ |Net| → no recovery period |

**Pine chart-bar subset** (733 trades, most recent ~3-4 months) で同じ -EV を確認:
WR=30.97%, PF=0.59, Net=-92.43 (-0.92%). 全データと整合。

## Cell breakdown (Pine 733-trade subset)

### Session × overall (UTC hours)

| Session | UTC | N | WR% | PF | NetP |
|---|---|---|---|---|---|
| Tokyo | <7 | 218 | 24.3 | 0.42 | -41.0 |
| London | 7-13 | 204 | 33.8 | 0.68 | -19.5 |
| NY | 13-22 | 271 | 34.3 | 0.65 | -29.0 |
| Off | ≥22 | 40 | 30.0 | 0.68 | -3.0 |

→ 全 session -EV。Tokyo 特に WR=24.3% で悪化（mean reversion 失敗が顕著）。

### H1 RSI bin × Direction

| Dir | RSI | N | WR% | NetP | vs BEV |
|---|---|---|---|---|---|
| BUY | <30 | 11 | 18.2 | -3.2 | -10pp |
| BUY | 30-50 | 114 | 31.6 | -15.3 | +3pp |
| BUY | 50-70 | 196 | 37.2 | -15.7 | +8pp |
| BUY | ≥70 | 13 | 23.1 | -1.6 | -5pp |
| SELL | <30 | 16 | 25.0 | -3.9 | -3pp |
| SELL | 30-50 | 163 | 26.4 | -25.5 | -2pp |
| SELL | 50-70 | 212 | 29.7 | -27.0 | +1pp |
| SELL | ≥70 | 8 | 37.5 | -0.2 | +9pp |

→ BEV_WR ≈ 28.6% (Tier2 RR≥2.5) を超える cell はあるが、いずれも NetP<0。
"WR≥BEV" だけでは +EV にならない（friction が edge を相殺）。

### Tier × Direction（最重要）

| Tier | Dir | N | Wins | WR% | NetP |
|---|---|---|---|---|---|
| Tier1 | BUY  | 28 | 7   | 25.0 | -4.3 |
| Tier1 | SELL | 39 | 7   | 17.9 | -7.4 |
| Tier2 | BUY  | 306 | 107 | 35.0 | -31.5 |
| Tier2 | SELL | 360 | 106 | 29.4 | -49.2 |

→ **Tier1 paradox**: 高 RR (3.0) を要求する "extreme entry" の方が WR が低い
(25.0% / 17.9% vs Tier2 35.0% / 29.4%)。
"BB±2σ 端 + RSI<25" が即時反転シグナルになっていない = mean reversion 仮説の破綻。

## Conclusion

**Zero cells survive friction.** Session 4 cells × Tier 4 cells × RSI×Dir 8 cells = 16 unique cells を全て確認した結果、NetP > 0 の cell は **存在しない**。

これは「filter を加えれば救える」種類の問題ではなく、構造的問題:
- USD_JPY 5m での mean reversion edge は friction 2.14p RT を上回らない
- WR の上限が Tier2 BUY 35% 程度。BEV_WR (28.6%) を 6.4pp しか超えず、
  かつ RR floor は 2.5 で平均 RR は実現困難（time-stop 比率が高い）

## Decision (R3)

**`bb_rsi_reversion × USDJPY` は更なる variant 化を停止し、PAIR_DEMOTED 維持。**

理由:
1. 全 cell -EV (friction 込み 1y BT で確認)
2. WR 改善余地が 6pp 程度しかなく、その範囲では RR=2.5 で割が合わない
3. Tier1 (extreme entry) が逆に劣勢 = mean reversion 仮説そのものが弱い

## What to look for instead

bb_rsi_reversion 系で +EV を作るには (この BT が反証していない範囲):

1. **他 pair (EUR_USD, GBP_USD)** — friction 違い + market structure 違い。
   ただし EUR/GBP 既に PAIR_DEMOTED (production 30d shadow で確認済み)。
2. **15m / 1H へ昇格** — 5m の friction:edge ratio が悪い。15m で再検証する価値はあるが、
   別戦略 (`xs_momentum`) 系が既に支配している。
3. **Pivot to trend-following on USD_JPY 5m** — mean reversion 仮説を捨てて
   breakout/momentum 系に。これは新戦略になる。

## What NOT to do

- ❌ Tier1 を厳しくしてエントリを絞る → N が更に下がるだけで WR は上がらない
  (このデータが既に証明)
- ❌ RR floor を 4.0 / 5.0 に上げる → time-stop 比率が更に上がり、
  TP 到達がより稀になる
- ❌ ADX min を上げる → BEV_WR を超えるためには WR を 5pp+ 上げる必要があるが、
  単一の filter で達成困難（過去 PP audit が証明）

## Related

- [[../strategies/bb-rsi-reversion]] — 戦略カード
- [[../analyses/friction-analysis]] — USDJPY 2.14 pip RT
- [[../analyses/tv-pine-edge-discovery-framework]] — Pine edge 検証フレーム
- [[../lessons/lesson-kb-blind-pp-proposal]] — 単一 filter で WR 上昇しない教訓
- `bt-results/tv-overlays/bb_rsi_reversion-replica.pine` — Pine source
