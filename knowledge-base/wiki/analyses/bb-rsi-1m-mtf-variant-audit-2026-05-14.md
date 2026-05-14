# bb_rsi_reversion 1m-MTF Variant — TV Cell Audit (2026-05-14)

**Rule**: R3 (Immediate) — hypothesis test, math invariant friction baked in.
**Hypothesis**: bb_rsi_reversion 5m の負 EV を、**1m MACD (entry confirm) + 1m RSI (exhaustion exit)** で
逆転できるか? Pine v5 strategy で USD_JPY 5m × OANDA friction (0.0136% RT = 2.14p) を直接検証。
**Source**: `bt-results/tv-overlays/bb_rsi_1m_mtf-replica.pine`.

## Method

TV Strategy Tester (chart-visible subset, 2026-02-02 → 2026-05-14, ≈3.5 months):
- Symbol: OANDA:USDJPY
- TF: 5m base + `request.security(..., "1", ...)` for MACD/RSI MTF
- Friction: `strategy.commission.percent=0.0068` per side (=2.14p RT)
- 5 Pine tables: Summary / Session / H1 RSI×Dir / Tier×Dir / **Exit-reason×Dir** (new)
- Configurations tested:
  - **A**: MACD `hist_dir` filter ON + 1m RSI exit ON (default)
  - **B**: MACD `hist_cross` filter ON + 1m RSI exit ON
  - **C**: MACD `hist_dir` filter ON + 1m RSI exit OFF

## Results — Overall

| Config | N | WR% | PF | Net | vs Parent |
|---|---:|---:|---:|---:|---|
| Parent 5m (no 1m MTF, chart subset) | 733 | 30.97 | 0.59 | -0.92% | baseline |
| **A**: MACD hist_dir + 1m RSI exit | 619 | **32.15** | 0.55 | -0.86% | +1.18pp WR, -0.04 PF |
| **B**: MACD hist_cross + 1m RSI exit | 100 | 22.00 | 0.34 | -0.22% | catastrophic |
| **C**: MACD hist_dir only (no exit) | 616 | 30.84 | 0.56 | -0.85% | flat |

**Parent 1y full deep BT** (reference): N=2,512, WR=30.65%, PF=0.605, Net=-3.13%.

## Cell breakdown (Config A, default — 619 trades)

### Session × overall (UTC)

| Session | N | WR% | PF | NetP |
|---|---:|---:|---:|---:|
| Tokyo | 181 | 24.3 | 0.37 | -38.8 |
| London | 161 | 36.0 | 0.66 | -16.0 |
| NY | 245 | 35.9 | 0.63 | -27.5 |
| Off | 32 | 28.1 | 0.57 | -3.3 |

→ London/NY が WR 36% で BEV_WR (28.6%) を +7pp 上回るが、それでも PF<1 → -EV。

### H1 RSI bin × Direction

| Dir | RSI | N | WR% | NetP |
|---|---|---:|---:|---:|
| BUY | <30 | 10 | 20.0 | -3.0 |
| BUY | 30-50 | 101 | 32.7 | -15.8 |
| BUY | 50-70 | 157 | 35.7 | -17.8 |
| BUY | ≥70 | 9 | 33.3 | -1.7 |
| SELL | <30 | 15 | 26.7 | -3.5 |
| SELL | 30-50 | 147 | 27.2 | -27.3 |
| SELL | 50-70 | 176 | 33.0 | -18.3 |
| SELL | ≥70 | **4** | **75.0** | **+1.7** |

→ 「SELL ≥70」のみ NetP>0 だが N=4 で統計的に無意味。それ以外 8 cell 全て -EV。

### Tier × Direction

| Tier | Dir | N | WR% | NetP | vs Parent WR |
|---|---|---:|---:|---:|---|
| Tier1 | BUY | 11 | 27.3 | -1.5 | +2.3pp |
| Tier1 | SELL | 23 | 21.7 | -3.4 | +3.8pp |
| Tier2 | BUY | 266 | 34.2 | -36.9 | -0.8pp |
| Tier2 | SELL | 319 | 31.3 | -44.0 | +1.9pp |

→ 全 4 cell -EV 維持。Tier1 paradox 軽減 (WR 改善) するも依然 BEV_WR (25.0%) と僅差。

### **Exit-reason × Direction (新規 view)**

| Dir | Exit | N | WR% | NetP |
|---|---|---:|---:|---:|
| BUY | SL | 170 | 0.0 | **-82.3** |
| BUY | TP | 42 | 100.0 | +27.3 |
| BUY | 1mRSI-exit | 23 | 100.0 | +10.1 |
| BUY | time-stop | 42 | 69.0 | +6.5 |
| SELL | SL | 208 | 0.0 | **-99.1** |
| SELL | TP | 56 | 100.0 | +36.8 |
| SELL | 1mRSI-exit | 28 | 100.0 | +14.2 |
| SELL | time-stop | 50 | 42.0 | +0.8 |

→ SL hits dominate (378 / 619 = 61%)、累積損失 -181.4p。
1m RSI exhaustion exit は新規に 51 trades を 100% 勝ち (+24.3p) に変換。
ただし、これらは ATR×2.0 の full TP に届く前の早期撤退なので 1 trade あたりの利幅が小さい
→ **PF 改善せず** (むしろ PF 0.59→0.55 に低下)。

## Decisive analysis: why 1m MTF didn't save the strategy

**Hypothesis verification**:

1. **Entry precision (1m MACD hist_dir filter)** — Config C で検証:
   - N 733→616 (-16%) drop
   - WR 30.97% → 30.84% (実質変化なし)
   - PF 0.59 → 0.558 (僅か悪化)
   - **結論**: 1m MACD は entry を絞り込むが、勝ち負け比率を改善しない (random filtering)

2. **Exit precision (1m RSI exhaustion early-TP)** — Config A vs C で検証:
   - WR +1.31pp (30.84 → 32.15)
   - PF 実質横ばい (0.558 → 0.551)
   - 51 trades を SL から +利益に転換 (+24.3p gross)
   - **結論**: WR は上がるが、利幅が小さく PF が上がらない = trade-off zero-sum

3. **Hist_cross 厳格化** — Config B:
   - N 619→100 (大幅 drop)
   - WR 22% に崩壊
   - **結論**: MACD cross 直後の entry = "momentum just flipped" = mean reversion fade として最悪のタイミング

**構造的結論**: USDJPY 5m bb_rsi_reversion の負 EV は friction 2.14p RT が原因であり、
entry/exit timing 精度では覆らない。1m MTF も含めて 16+ cells, 4 configurations すべて -EV。

## Decision (R3)

**bb_rsi_reversion variant 化を完全停止 — PAIR_DEMOTED 維持**

- 親戦略 (2026-05-14 audit) + 1m MTF variant (本 audit) で **計 20+ cells を確認、+EV cell 不在**
- 1m MTF hypothesis は **データで反証** された
- 今後 bb_rsi_reversion 系の派生案は受け付けない (KB ガード)

## What was learned (再現知見)

1. **1m MTF entry filter は mean reversion を救わない** — momentum confirmation は MR の哲学と逆
2. **早期 TP は WR を上げるが PF を上げない** — 利幅縮小と勝率上昇は zero-sum 関係
3. **Pine `request.security` で MTF 検証は実用的** — 5m base + 1m sub-signal の検証コストが極小
4. **Exit-reason breakdown は新しい強力 view** — SL/TP/early-exit/time の構成比で戦略本質が見える

## Related

- [[bb-rsi-tv-friction-cell-audit-2026-05-14]] — 親戦略 audit (全 16 cells -EV)
- [[../strategies/bb-rsi-reversion]] — 戦略カード
- [[tv-pine-edge-discovery-framework]] — Pine edge 検証フレーム
- `bt-results/tv-overlays/bb_rsi_1m_mtf-replica.pine` — Pine source (371 lines)
