# Pre-Registration: Time-Floor Meta Rescue — 早期撤退病理の横断検定 (2026-04-25)

## 1. 背景と動機

R&D 全件解剖 ([[rd-target-rescue-anatomy-2026-04-25]]) で **N≥100 級の 7 戦略全てに
共通する Time-Decay 異常**を発見:

| 戦略 | hold<5m EV | hold 10-20m EV | hold 20-40m EV | hold 40-80m EV |
|---|---|---|---|---|
| ema_trend_scalp | -3.0 | -0.62 | **+0.09** | **+2.34** |
| sr_channel_reversal | -1.7 | -0.76 | **+1.70** | **+7.19** |
| engulfing_bb | -2.7 | +0.46 | **+2.42** | **+4.93** |
| stoch_trend_pullback | -2.5 | -0.74 | **+2.56** | **+8.65** |
| bb_squeeze_breakout | -1.5 | -1.46 | **+5.04** | **+11.00** |
| fib_reversal | -1.5 | -0.77 | **+2.46** | n/a |

**これは個別戦略の問題ではなくシステム全体のメタ病理**.

仮説: **TIME_DECAY_EXIT (現観測 N=497, 全close の 15.2%) が、本来 EV+ になる
20分以降のトレードを早期に切り捨てている**. 早期エントリーは false-break ノイズで
損切りになりやすく、生き残りトレードは保持時間が伸びるほど edge が顕在化する.

ema_trend_scalp は N=680 で全 cell DEAD だが、Approach B の改善幅が最大 (-3.0→+2.34)。
**Time-Floor が機能すれば 7 戦略全体の EV 押し上げ効果が期待される**.

## 2. 仮説 (Pre-Registered)

### H0 (帰無)
TIME_DECAY_EXIT を delay/抑制しても、対象戦略 (7) のいずれも EV>0 にならない.

### H1 (代替)
保持時間下限 (例 hold≥20分) を強制すると、対象戦略の少なくとも 3つで EV>+0.5p に改善.

### 2.1 Live 観測ベース改善幅推定 (BT検証対象)

各戦略の baseline EV と「20分以上保持トレードのみ」の EV (実測 cum_EV):

| Strategy | Base EV | hold≥20m EV (実測) | ∆EV | N (≥20m) |
|---|---|---|---|---|
| ema_trend_scalp | -1.47 | hold≥20m bin EV +0.09→+2.34 平均 ~+1.0p | +2.5 | ~143 |
| sr_channel_reversal | -0.90 | +1.70 〜 +7.19 平均 ~+3.0p | +3.9 | ~47 |
| engulfing_bb | -0.49 | +2.42 〜 +4.93 平均 ~+3.0p | +3.5 | ~37 |
| stoch_trend_pullback | -0.96 | +2.56 〜 +8.65 平均 ~+4.0p | +5.0 | ~33 |
| bb_squeeze_breakout | -0.26 | +5.04 〜 +11.0 平均 ~+6.0p | +6.3 | ~22 |

注: これらは **Live 観測の生存者バイアス** を含む可能性あり (= 短期で切れる
ものは hold<20m で除外される). BT で「同じトレードを 20分以上保持した時の
ハイポセティカル PnL」を計算する必要がある.

## 3. データセット

- ペア: 全 6 ペア (XAU除外)
- 期間: 365 日 (2025-04-26 〜 2026-04-25)
- 戦略: 7 戦略横断
  - ema_trend_scalp / sr_channel_reversal / fib_reversal
  - engulfing_bb / stoch_trend_pullback / macdh_reversal / bb_squeeze_breakout
- 摩擦モデル: v2

## 4. 検定軸 — 横断 hold-floor グリッド

| Cell | Time Floor | 影響戦略 |
|---|---|---|
| **B0 baseline** | none (現状 TIME_DECAY_EXIT) | 7戦略全部 |
| **B1** | hold ≥ 5min | 7戦略 |
| **B2** | hold ≥ 10min | 7戦略 |
| **B3** | hold ≥ 20min | 7戦略 ★主軸 |
| **B4** | hold ≥ 30min | 7戦略 |

つまり: 7 戦略 × 5 cell = 35 BT セル.

### 主軸: B3 (hold ≥ 20min)

実測 cum_EV のターニングポイントが 20min 付近に集中しているため.
この cell で 7 戦略中 3つ以上が EV>+0.5p なら H1 採択.

## 5. SURVIVOR Gate (Pre-Registered, Bonferroni)

戦略レベル通過条件 (AND, Bonferroni α=0.05/35=0.00143):
1. **EV > +0.5p** (摩擦マージン控えめ)
2. **PF > 1.15**
3. **N ≥ 30** (Wilson_lo 安定)
4. **Wilson_lo (WR) > 観測 WR の 70%** (overfit防止)
5. **Welch t vs B0 baseline で p < 0.00143**
6. **WF 同符号** (90日×4期間 全 EV>0)

メタ仮説 (H1) 採択条件:
- B3 (hold≥20m) cell で 7戦略中 **3 戦略以上** が SURVIVOR

## 6. CANDIDATE / REJECT 判定

- **メタ SURVIVOR (H1採択)**: 3戦略以上が B3 通過 → Time-Floor を Phase2a 議論に格上げ.
  別 pre-reg「TIME_DECAY_EXIT 改修 deploy plan」起案.
- **メタ CANDIDATE**: 1-2 戦略が B3 通過 → 個別戦略 deploy のみ検討、横断改修は保留.
- **メタ REJECT**: 0 戦略 → Time-Decay 仮説を closure ([[lesson-time-decay-bias]] 起案).

## 7. 副次仮説 (Bonferroni対象外)

H2: **保持下限 + 早期 SL widening 併用**  
   → hold<10m は SL を 1.5×ATR に拡げ、ノイズ吸収

H3: **session 別 Time Floor**  
   → Tokyo: hold≥10m / London: hold≥20m / NY: hold≥30m (流動性差)

H4: **strategy-tier 別 Time Floor**  
   → MR系 (bb_rsi/vwap_mr) は短め, トレンド系 (ema_trend_scalp) は長め

## 8. 実装注記 (本番コード変更なし)

- BT harness: `scripts/time_floor_meta_bt.py` (新規, R&D環境)
- Pipeline: 既存 BT に `_HOLD_FLOOR_MIN` 環境変数で hold floor 強制
- Time-Floor 適用方法:
  - エントリー後 hold < floor の間: TP/SL touch でも「保留」(simulate)
  - hold ≥ floor 達成後に TP/SL/MAX_HOLD_TIME を判定
- Output: `raw/bt-results/time-floor-meta-{date}.json` (35 cells)

## 9. 凍結ルール

- 本 pre-reg LOCK 後、**コード変更禁止**まで BT 完走.
- 7 戦略の Shadow 状態維持 (現状通り).
- メタ SURVIVOR 採択 → demo_trader.py の TIME_DECAY_EXIT 改修 deploy pre-reg.
- メタ REJECT → ema_trend_scalp 等を `_FORCE_DEMOTED` に格上げ検討.

## 10. タイムライン

| 日付 | アクション |
|---|---|
| 2026-04-25 | 本 pre-reg LOCK + harness 設計 |
| 2026-04-26〜2026-05-01 | 365日 × 7 戦略 × 5 cell = 35 BT セル実行 |
| 2026-05-02 | 結果分析 + メタ判定 |
| 2026-05-07 | Phase 1 holdout 期限と並走 |
| 2026-05-14 | MAFE Dynamic Exit 再集計と統合判断可能性 |

## 11. リスク (Pre-Reg)

1. **生存者バイアス**: Live 観測の hold≥20m EV+ は早期切捨てされない trade のみ。
   BT で **強制保持 simulation** を行う必要があり、本来 SL hit していた trade が
   hold floor 中に MAE を更に拡大する可能性. → BT 実装で要 careful 検証.
2. **Bonferroni 過保守**: 35 cells で α=0.00143 は厳しい. メタ判定では
   FDR (BY) を secondary 判定に併用.
3. **MAFE Dynamic Exit との衝突**: 既存 [[mafe-dynamic-exit-result-2026-04-24]] と
   方向性が逆 (MAFE 早期 cut vs Time Floor 強制保持). 結果次第で
   どちらを採択するか統合判断が必要.

## 12. メモリ整合性

- [部分的クオンツの罠]: PF/Wilson_lo/W:L/Bonferroni/WF 全て含む ✅
- [ラベル実測主義]: hold-floor 効果は BT 実測で判定 ✅
- [成功するまでやる]: REJECT でも H2/H3/H4 副次仮説で深掘り継続 ✅

## 参照
- [[rd-target-rescue-anatomy-2026-04-25]] (根拠データ)
- [[mafe-dynamic-exit-result-2026-04-24]] (方向逆の関連検定)
- [[bb-squeeze-rescue-2026-04-25]] (個別救済の最有望候補, 並走)
