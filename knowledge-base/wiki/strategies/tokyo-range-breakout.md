# Tokyo Range Breakout — 東京レンジブレイクアウト (T3)

## Stage: MINIMUM_LIVE (2026-04-23)

**entry_type**: `tokyo_range_breakout_up`
**mode**: `daytrade` (15m)
**status**: 🟢 **Minimum Live** (USD_JPY BUY-only, Kelly 0.25x 相当)

## Hypothesis
東京セッション (UTC 0-7) の日中 range は相対的に狭く、ロンドンオープン (UTC 7-9) で upside breakout が発生する場合、欧州実需フローの流入により 4h 以内に +15-20pip のトレンド継続が発生する確率が有意に高い (Andersen & Bollerslev 1997)。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| Andersen & Bollerslev (1997, J. Emp. Finance) | セッション間ボラティリティ構造と流動性遷移時のトレンド継続性 | ★★★★★ |
| Ito & Hashimoto (2006, JJIE) | Tokyo session range 圧縮と London open 流動性流入 | ★★★★ |
| Corcoran (2002) | London open はFX最大の流動性遷移点 | ★★★★ |

## Walk-Forward Validation (2026-04-23)

### USD_JPY UP breakout (implemented)
| Window | N | mean (pip) | WR(>0)% | t-stat |
|--------|--:|-----------:|--------:|-------:|
| IS (2025-04-20..2025-10-20) | 47 | +17.72 | 70.2% | +2.83 |
| OOS (2025-10-21..2026-04-23) | 51 | +17.62 | 74.5% | +3.59 |

- mean_diff: 0.6% / WR_diff: 4.3pp → 🟢 **STABLE_EDGE** (非カーブフィッティング)
- Net EV (friction 2.14p RT): **+15.48p/trade**

### 他ペア参考 (Minimum Live では未有効化)
| Pair | OOS N | OOS mean | OOS WR | Verdict |
|------|------:|---------:|-------:|---------|
| GBP_JPY | 57 | +16.76 | 66.7% | 🟢 STABLE_EDGE |
| EUR_JPY | 52 | +12.55 | 65.4% | 🟢 STABLE_EDGE |
| GBP_USD | 51 | +9.63 | 64.7% | 🟢 STABLE_EDGE |
| EUR_USD | 48 | +6.23 | 62.5% | 🟡 NOISY_BUT_ALIVE |

## Quantitative Definition
```python
# per day (USD_JPY のみ, UTC 15m足):
tokyo_range = [max(H), min(L)] over UTC 0-7  (min 20 bars = 5h)
IF tokyo_range_pip >= 15:
  AT first 15m bar close during UTC 7-9:
    IF close > tokyo_range.max
       AND no earlier UTC7-9 bar closed above tokyo_range.max
       AND no UTC7-9 bar broke tokyo_range.min (BOTH除外)
       AND HTF != "bear"
       AND 陽線 & body_ratio >= 0.30
       AND NOT Friday:
      entry = BUY at close
      TP = entry + 20pip
      SL = entry - 15pip
      MAX_HOLD = 16 bars (4h)
```

## Friction Viability
| Pair | Friction(RT) | BT mean | Net EV | Friction/mean |
|------|-------------:|--------:|-------:|--------------:|
| USD_JPY | 2.14pip | +17.62pip | **+15.48p** | 12.1% ✅ |

## Correlation with Existing
| Strategy | Expected r | Basis |
|----------|-----------|-------|
| session_time_bias × USD_JPY | 中 | Tokyo session drift vs London open breakout、部分的に重複するがメカニズム別 |
| london_session_breakout | 高 | EUR/USD 1H、DISABLED 中のため衝突なし |
| gotobi_fix | 低 | 仲値 fix 時間帯 (UTC 03-04) と重複せず |
| orb_trap | 低〜中 | ORB fakeout は逆張り、本戦略は breakout follow で逆エッジ |

## Implementation Path
- [x] Stage 1: DISCOVERED (2026-04-23, edge-matrix 2026-04-23)
- [x] Stage 2: FORMULATED (Andersen-Bollerslev 1997)
- [x] Stage 3: BACKTESTED — 365d BT 4/5 ペア STABLE_EDGE
- [x] Stage 4: WALK-FORWARD VALIDATED — IS/OOS 158-159d, Bonferroni safe
- [x] Stage 5: MINIMUM_LIVE — USD_JPY BUY-only, Kelly 0.25x 相当 (2026-04-23)
- [ ] Stage 6: N>=15 check — Live N=15 で EV_cost>-0.5p & WR>=52% 確認
- [ ] Stage 7: 拡大検討 — GBP_JPY / EUR_JPY 追加 (friction 実測後)
- [ ] Stage 8: Full Live (Kelly Half, 4 pair)

## Minimum Live ガードレール (Stop-Loss Rules)
1. **Live N=15 到達時点**で以下のいずれかに該当 → 自動停止検討:
   - Live mean pip が BT mean の 0.5x 以下 (< +8.8p)
   - Live WR が BT WR の 0.7x 以下 (< 52%)
   - Friction 実測 > 3.0pip (BT 仮定 2.14p の 1.4 倍超)
2. **Live N=30 到達時点**で:
   - EV_fric > 0 & Bootstrap 95% CI lower > 0 → Kelly Half 昇格候補
   - それ以外 → _FORCE_DEMOTED に移動 & 再設計

## Key Advantages
- **実装複雑度 3/5** — Tokyo range 計算 + 時間 gate + fresh breakout 判定
- **学術的根拠 ★★★★★** — Andersen-Bollerslev 標準 (被引用数 >3000)
- **WFA safe** — OOS mean diff 0.6%, WR diff 4.3pp で過学習なし
- **friction margin 高** — USD_JPY RT 2.14p は BT mean の 12%

## Risks
- **NONE day (breakout 発生せず)** — BT で ~30%、Live も一致するか確認必要
- **4h 持ち時間中に US 指標 (UTC 12:30) 発表** — 初期は no-gate、実測後に判断
- **narrow-range day (< 15p)** — MIN_RANGE_PIP=15 で除外済み
- **金曜 week-overhang** — 金曜除外 (weekday=4) で除外済み

## Source
- `strategies/daytrade/tokyo_range_breakout.py` (signal 実装)
- `tools/tokyo_range_breakout.py` (post-hoc analyzer)
- `tools/tokyo_range_breakout_wfa.py` (WFA runner)
- `knowledge-base/raw/bt-results/tokyo-range-breakout-2026-04-23.md` (raw BT)
- `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.md` (WFA)
- `knowledge-base/wiki/decisions/t3-tokyo-range-breakout-shadow-proposal-2026-04-23.md` (proposal)
- `knowledge-base/wiki/sessions/quant-edge-scan-2026-04-23.md` (session log)
- `knowledge-base/wiki/analyses/edge-matrix-2026-04-23.md` (hypothesis matrix)

## Related
- [[edge-matrix-2026-04-23]]
- [[quant-edge-scan-2026-04-23]]
- [[t3-tokyo-range-breakout-shadow-proposal-2026-04-23]]
- [[session-time-bias]] — 部分的に重複するメカニズム
