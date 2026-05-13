# xs_momentum TV Edge Discovery — Phase 1

## Symbol / Range
- **Symbol/TF**: OANDA:USDJPY, 15m
- **BT range**: 2025-07-01 〜 2026-05-13 (TV Strategy Tester 全期間)
- **Pine**: `bt-results/tv-overlays/xs_momentum-replica.pine` (v8.9 ロジック翻訳)
- **Filters**: London-NY gate / ADX≥20 / mom>1.0 ATR / SL=1.5 ATR / TP=2.0 ATR

## Baseline (filter OFF)
| Metric | Value |
|---|---|
| N (closedtrades) | 501 |
| Wins | 218 |
| Win Rate | **43.5%** |
| Gross Profit | TV report (mirror in `t_sum`) |
| Gross Loss | TV report |
| **PF** | **1.04** |
| Net (price units) | +11.83 |

→ Aggregate ではほぼ break-even。生のままでは Live 化基準を満たさない。

### Python BT vs TV BT discrepancy（未解決）
- **KB 既知**: xs_momentum × USD_JPY 365d Python BT — N=342, WR=69%, EV=+0.270, PF=1.43
- **TV 観測**: N=501, WR=43.5%, PF=1.04
- WR 差 **約 25pp** / N 差 **+159** — 同じ戦略名でも Python と TV で別物
- **可能な原因候補**（仮説、未検証）:
  1. 期間が違う（Python は 365 日 rolling、TV は OANDA データ全期間）
  2. 摩擦モデルが違う（Python は `friction-analysis.md` 準拠の 2.14pip RT、TV は default commission/slippage=0）
  3. Pine 翻訳で本番の追加フィルタが抜けている（confirm 条件・volume guard 等）
  4. TV の OANDA データと Python の OANDA fetch でバーが微妙にズレている
- **次アクション**: friction を TV に反映 (`commission_type=cash_per_contract` + `slippage`) → 期間を Python BT と揃えて再計測

## Segment decomposition

### By session (UTC, non-overlapping)
| Session | N | WR | 備考 |
|---|---|---|---|
| Tokyo | (Pine `t_sess`) | 表示 | gate 外 のはずなので参考値 |
| London | 約 N/3 | 表示 | gate 内 |
| NY | 約 N/3 | 表示 | gate 内 |
| Off | low | 表示 | gate 外 |

→ Pine の Session table を見ると London/NY の差は数 pp。aggregate を救う単一セッションは見つからなかった。

### By H1 RSI bucket × direction
- **AGREE** = momentum 方向と H1 RSI が同方向（BUY rsi≥70 + SELL rsi<50）
- **COUNTER** = 逆方向（BUY rsi<70 + SELL rsi≥50）

| Bucket | N | WR | Wilson 95% CI |
|---|---|---|---|
| AGREE (BUY≥70 ∪ SELL<50) | 261 | **47.9%** | [41.9, 53.9] |
| COUNTER (BUY<70 ∪ SELL≥50) | 238 | **39.1%** | [33.1, 45.4] |

### Statistical test
- Two-proportion z-test: AGREE vs COUNTER
- **z = 1.98, p = 0.04733** — α=0.05 で有意
- Bonferroni 補正（8 cell 比較想定: α=0.05/8=0.00625）では **未到達**
- → directionally consistent だが Bonferroni-locked ではない。仮説 ranking としては採用、本番フィルタ採用は要 N 追加

## Phase 1 Hypothesis (Pine v2 に組込済、未起動)
```pine
use_rsi_filter = input.bool(false, "Apply H1 RSI direction filter (Phase 1)")
buy_rsi_min    = input.int(60, "BUY: H1 RSI min")  // entry on BUY 時 H1 RSI ≥ 60
sell_rsi_max   = input.int(40, "SELL: H1 RSI max") // entry on SELL 時 H1 RSI ≤ 40
```
- **AGREE 定義よりやや緩めた** (60/40) — Wilson lower が widthの広い範囲に留まるため、サンプル取り直しで N を確保
- Toggle OFF が default → 既存挙動を壊さない

## Phase 2 plan
1. TV で `use_rsi_filter = true` に切替 → Strategy Tester 全期間再走
2. 期待値:
   - N が AGREE 寄り bucket のみに減る (≈ 261 → 180-220 想定、buy_rsi_min/max を 60/40 に緩めたぶん少し多め)
   - WR が aggregate 43.5% → 47-50% 帯に上がるか観測
   - PF が 1.04 → 1.15+ になるか観測
3. もし WR Δ ≥ +5pp かつ PF ≥ 1.20 なら、buy_rsi_min/sell_rsi_max を 65/35 / 70/30 で grid を切る
4. friction を入れた再計測（前述 Python vs TV discrepancy 解決と並行）

## Known limitation in this loop
- Pine 編集後、MCP では on-chart instance を確実に再追加する手段がない（framework doc に追記済み）
- TV Strategy Tester は default で commission/slippage=0 → live spread (USDJPY ≈ 0.7pip + 0.5pip slip = 2.14pip RT) を反映していない
- 上記 2 つは framework doc / 本ページに記載し、Phase 2 で対処

## Related
- [tv-pine-edge-discovery-framework](tv-pine-edge-discovery-framework.md)
- [friction-analysis](friction-analysis.md)
- [bt-live-divergence](bt-live-divergence.md)
- `bt-results/tv-overlays/xs_momentum-replica.pine`
