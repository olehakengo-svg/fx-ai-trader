# R&D 解剖: 高N負EV 7戦略の救済可能性評価 (2026-04-25)

## 0. 目的

bb_rsi 緊急トリップ + Grail Sentinel deploy ([[tp-hit-deep-mining-grail-2026-04-25]]) 完了後、
Live 環境は安定. **R&D フェーズ** として Shadow/FORCE_DEMOTED 層の高N 負EV 戦略を
プラスEV に転換可能か体系評価.

データソース: `/api/demo/trades?limit=10000` (3271 closed, 23日, XAU除外).

## 1. ターゲット戦略 (N≥100 級)

| 戦略 | N | TP | WR% | EV | PF | AvgWin | AvgLoss |
|---|---|---|---|---|---|---|---|
| ema_trend_scalp | 680 | 121 | 17.8 | -1.47 | 0.49 | +7.27 | -3.53 |
| fib_reversal | 269 | 57 | 21.2 | -0.59 | 0.70 | +4.43 | -2.90 |
| sr_channel_reversal | 228 | 49 | 21.5 | -0.90 | 0.65 | +6.88 | -3.38 |
| stoch_trend_pullback | 204 | 44 | 21.6 | -0.96 | 0.61 | +6.10 | -3.25 |
| engulfing_bb | 177 | 43 | 24.3 | -0.49 | 0.78 | +6.57 | -2.97 |
| macdh_reversal | 134 | 17 | 12.7 | -1.13 | 0.47 | +3.49 | -3.09 |
| bb_squeeze_breakout | 113 | 20 | 17.7 | -0.26 | 0.89 | +9.79 | -2.97 |

7 戦略合計 N=1805, 月間 PnL 損失推定 ≈ -1700pip.

## 2. 評価方法 (3 アプローチ)

### Approach A: RR 再構築
- 現状 TP距離 / SL距離 から RR 算出
- 全 trade の中央値 MFE / SL距離 で達成可能 RR 推定
- 必要 RR = (1-WR)/WR (BE まで届く RR)
- 達成可能 RR ≥ 必要 RR なら救済可能

### Approach B: Time Decay
- hold_min を 9 ビン (0-1, 1-3, 3-5, 5-10, 10-20, 20-40, 40-80, 80-180, 180+) に分割
- 各ビン EV と累積 EV (cum_EV) を算出
- 累積最大 EV cutoff (hold<X minute) を特定

### Approach C: 極限フィルター
- (Pair × Session × Regime) 27 cells に分解
- N≥8 かつ EV>0 の cell を救済候補として抽出

## 3. 結果

### 3.1 Approach A — 全戦略 NO

```
Strategy              med MFE  AchRR  必要RR
ema_trend_scalp        1.25    0.29    4.62
sr_channel_reversal    0.90    0.21    3.65
fib_reversal           0.60    0.14    3.72
engulfing_bb           1.80    0.46    3.12
stoch_trend_pullback   1.00    0.26    3.64
macdh_reversal         0.00    0.00    6.88
bb_squeeze_breakout    1.00    0.27    4.65
```

med MFE が一桁不足. WR 低 → 必要 RR 3〜7倍 → 達成可能 RR 0.14-0.46.
**RR 拡張による救済は構造的に不可能**.

### 3.2 Approach B — hold>20m で全戦略 EV+ 転換

```
Strategy              hold<5m   10-20m   20-40m   40-80m   max cum_EV
ema_trend_scalp       -3.0      -0.62    +0.09    +2.34    -1.47 (80m)
sr_channel_reversal   -1.7      -0.76    +1.70    +7.19    -0.90 (80m)
fib_reversal          -1.4      -0.77    +2.46    n/a      -0.59 (40m)
engulfing_bb          -2.7      +0.46    +2.42    +4.93    -0.49 (80m)
stoch_trend_pullback  -2.5      -0.74    +2.56    +8.65    -0.96 (80m)
macdh_reversal        -2.7      -0.16    +2.27    -2.70    -1.13 (40m)
bb_squeeze_breakout   -1.5      -1.46    +5.04    +11.0    -0.26 (80m)
```

**全戦略で hold≥20m 後の bin EV が +**. 純粋 cum_EV は依然負だが、
これは早期 (hold<10m) の大損失が過半を占めるため.

仮説: **TIME_DECAY_EXIT が 20分以上保持で edge が顕在化する trade を
早期に切り捨てている可能性**. 横断検定対象 → [[time-floor-meta-rescue-2026-04-25]].

### 3.3 Approach C — 5/7 戦略で救済 cell 存在

| 戦略 | 救済 cell 数 | 最良 cell |
|---|---|---|
| sr_channel_reversal | 3 | GBP_USD × NY × TREND_BULL: N=11 EV+1.60 PF=1.79 |
| engulfing_bb | 3 | USD_JPY × London × TREND_BULL: N=8 EV+1.18 PF=2.07 |
| stoch_trend_pullback | 3 | USD_JPY × Tokyo × TREND_BULL: N=18 EV+0.45 PF=1.36 |
| bb_squeeze_breakout | **1** | **USD_JPY × London × TREND_BEAR: N=9 EV+1.58 PF=1.97 Wlo=18.9%** |
| ema_trend_scalp | 0 | DEAD (N=680 で純粋負 cell のみ) |
| fib_reversal | 0 | DEAD |
| macdh_reversal | 0 | DEAD |

## 4. VERDICT

| 戦略 | 結論 | 採択アプローチ |
|---|---|---|
| **bb_squeeze_breakout** | 救済最有望 (二重正当化) | **C+B** |
| sr_channel_reversal | 救済可能性中 | C のみ |
| engulfing_bb | 救済可能性中 | C のみ |
| stoch_trend_pullback | 救済可能性中 | C のみ |
| **ema_trend_scalp** | メタ救済対象 | **B (システム横断)** |
| fib_reversal | DEAD | FORCE_DEMOTED 推奨 |
| macdh_reversal | DEAD | FORCE_DEMOTED 推奨 |

## 5. 起案する Pre-Reg

1. **[[bb-squeeze-rescue-2026-04-25]]** — 個別戦略救済 (Cell+Time)
   - 4 main cells (Bonferroni α=0.0125)
   - 期待 EV +6 〜 +10p (Cell+Time 重複領域)

2. **[[time-floor-meta-rescue-2026-04-25]]** — システム横断 Time-Decay 検定
   - 7 戦略 × 5 hold-floor cells = 35 BT セル (Bonferroni α=0.00143)
   - 主軸 hold≥20m
   - 採択 → TIME_DECAY_EXIT 改修 deploy

## 6. 凍結ルール

- 本 R&D 期間中、本番コード変更禁止 (Live 環境はバンドエイド完了)
- BT 結果出るまで 7 戦略の Shadow 維持
- DEAD 判定 (fib_reversal, macdh_reversal) は別 lesson 起案後に FORCE_DEMOTED 検討

## 7. メモリ整合性

- [部分的クオンツの罠]: PF/Wilson_lo/RR/W:L/Break-even WR 全て含む ✅
- [ラベル実測主義]: 全数値を Live 実測クエリから抽出 (コード演繹なし) ✅
- [XAU除外]: data 段階で除外 ✅

## 参照
- [[tp-hit-deep-mining-grail-2026-04-25]] (本 R&D の前段)
- [[bb-squeeze-rescue-2026-04-25]] (起案 1)
- [[time-floor-meta-rescue-2026-04-25]] (起案 2)
- [[external-audit-2026-04-24]] (新Phase凍結方針との整合)
