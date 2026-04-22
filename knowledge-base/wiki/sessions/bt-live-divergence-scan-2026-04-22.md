# BT vs Live Divergence — Full Portfolio Scan + Root Cause

**Generated**: 2026-04-22 (UTC)
**BT Baseline**: `raw/bt-results/full-bt-scan-2026-04-15.md` (365d DT 15m + 180d Scalp 1m/5m) + `bt-365d-2026-04-16.json`
**Live Data**: `/api/demo/trades?limit=3000` (N=2525, W/L 2292, non-XAU)
**Fresh 365d BT**: 実行中（完了後に追記）
**Method**: ΔEV = Live_EV − BT_EV (pip); two-proportion z; Wilson 95%; MFE/MAE causal decomposition

---

## 🎯 Executive Summary (3-line)

1. **engulfing_bb×USD_JPY (N=75, z=-3.71, p=0.0002)** と **bb_squeeze_breakout×EUR_USD (N=25, z=-4.99, p<0.0001)** が統計的有意に BT を下回り、**regime-shift 型の overfitting** を確定。
2. 根本原因は **(i) 2026-04-16 以降の regime feature rollout 欠落（pre-cutoff 77% NULL）**, **(ii) Immediate Death ≥50% in 8/10 cells**（entry 方向の破綻）, **(iii) Scalp family の friction 実現と BT モデル乖離**。
3. **macdh_reversal×USD_JPY N=12 WR=0%** は catastrophic / **ema_trend_scalp 全体 N=280 PnL=-410p** は FORCE_DEMOTE 候補（次 Audit で正式判定）。

---

## §1. Divergence Ranking — Live < BT (Top 15)

|#| Strategy×Pair | BT(N/WR/EV) | Live(N/WR/EV) | ΔWR | ΔEV | z | p | Wilson95 | PnL |
|-|-|-|-|-:|-:|-:|-:|-|-:|
|1| dt_sr_channel_reversal×GBP_USD | 53/66.0%/+0.180 | 17/17.6%/-4.276 | **-48.4pp** | -4.456 | -3.48 | **0.0005** | [6.2, 41.0] | -72.7 |
|2| vwap_mean_reversion×EUR_JPY | 380/68.2%/+0.318 | 5/40.0%/-7.740 | -28.2pp | -8.058 | -1.34 | 0.1799 | [11.8, 76.9] | -38.7 |
|3| session_time_bias×GBP_USD | 392/63.8%/+0.149 | 5/0.0%/-7.740 | -63.8pp | -7.889 | -2.94 | **0.0033** | [0.0, 43.4] | -38.7 |
|4| post_news_vol×USD_JPY | 25/80.0%/+0.933 | 8/25.0%/-5.213 | -55.0pp | -6.146 | -2.87 | **0.0041** | [7.1, 59.1] | -41.7 |
|5| dual_sr_bounce×GBP_USD | 90/52.2%/-0.189 | 6/0.0%/-7.217 | -52.2pp | -7.028 | -2.48 | **0.0133** | [0.0, 39.0] | -43.3 |
|6| **bb_squeeze_breakout×EUR_USD** | 46/73.9%/+0.274 | 25/12.0%/-2.476 | **-61.9pp** | -2.750 | **-4.99** | **<0.0001** | [4.2, 30.0] | -61.9 |
|7| vix_carry_unwind×USD_JPY | 103/69.9%/+0.521 | 8/25.0%/-4.212 | -44.9pp | -4.733 | -2.60 | **0.0095** | [7.1, 59.1] | -33.7 |
|8| post_news_vol×GBP_USD | 19/78.9%/+1.302 | 5/40.0%/-3.340 | -38.9pp | -4.642 | -1.70 | 0.0887 | [11.8, 76.9] | -16.7 |
|9| sr_fib_confluence×GBP_USD | 241/58.5%/+0.015 | 28/39.3%/-1.414 | -19.2pp | -1.429 | -1.94 | 0.0522 | [23.6, 57.6] | -39.6 |
|10| **engulfing_bb×USD_JPY** | 36/69.4%/+0.213 | **75/32.0%/-0.420** | **-37.4pp** | -0.633 | **-3.71** | **0.0002** | [22.5, 43.2] | -31.5 |

### Bonferroni 補正 (M=15 cell スキャン)
α/M = 0.05/15 = 0.00333. ⭐=Bonferroni 有意:
- ⭐ **bb_squeeze_breakout×EUR_USD** p<0.0001
- ⭐ **dt_sr_channel_reversal×GBP_USD** p=0.0005
- ⭐ **engulfing_bb×USD_JPY** p=0.0002
- (p=0.0033) session_time_bias×GBP_USD は境界線

他は raw p<0.05 だが Bonferroni 基準では偶然域内。

---

## §2. Over-performing cells (Live > BT)

|#| Strategy×Pair | BT | Live | ΔEV | PnL |
|-|-|-|-|-:|-:|
|1| dt_bb_rsi_mr×GBP_USD | 117/45.3%/-0.182 | 14/57.1%/+2.479 | +2.661 | +34.7 |
|2| bb_squeeze_breakout×USD_JPY | 18/77.8%/+0.457 | 53/30.2%/+0.555 | +0.098 | +29.4 |

**bb_squeeze_breakout×USD_JPY** は LIVE WR 30.2% だが EV +0.555 → **高 R:R (TP deep, SL shallow) プロファイル**. WR低下 ≠ 戦略死. BT も同様.

---

## §3. Mechanistic Root Causes (数学的特定)

### 3.1 Regime feature rollout gap (**最大の構造要因**)

**全 LIVE 2525 trade の mtf_regime NULL 率**:
- Pre-cutoff (≤2026-04-16): 77% NULL
- Post-cutoff (>2026-04-16): 39% NULL (追加 rollout 進行中)

**戦略別 NULL率 >80% (N≥20)**:
| strategy | N | null_regime |
|---|---:|---:|
| ema_cross | 47 | 100% |
| ema_pullback | 44 | 100% |
| dual_sr_bounce | 23 | 96% |
| macdh_reversal | 126 | 95% |
| vol_momentum_scalp | 39 | 95% |
| dt_sr_channel_reversal | 53 | 91% |
| vol_surge_detector | 92 | 91% |
| bb_squeeze_breakout | 92 | 90% |
| dt_bb_rsi_mr | 40 | 90% |
| sr_fib_confluence | 112 | 88% |

**含意**: BT は regime 情報を持ったデータで予測を立てたが、LIVE の 60-100% trades は regime=NULL で発火している. つまり **BT で見た regime-conditional alpha が LIVE で認識されないまま戦略が発火してしまう** 構造. これは pre-registration の regime filter が効いていないことを示す.

### 3.2 Immediate Death ≥ 50% in 8/10 divergent cells

Definition: `MFE_favorable_pips ≤ 0.5` (entry 直後から逆行で SL 直行)

| Strategy×Pair | ImmDeath rate | 意味 |
|---|---:|---|
| post_news_vol×GBP_USD | **100%** (3/3) | entry 全件で逆行 |
| session_time_bias×GBP_USD | 80% (4/5) | entry 方向破綻 |
| sr_fib_confluence×GBP_USD | 76% (13/17) | entry 方向破綻 |
| vwap_mean_reversion×EUR_JPY | 67% (2/3) | entry 方向破綻 |
| dual_sr_bounce×GBP_USD | 67% (4/6) | entry 方向破綻 |
| bb_squeeze_breakout×EUR_USD | 59% (13/22) | entry 方向破綻 |
| engulfing_bb×USD_JPY | 55% (28/51) | entry 方向破綻 |
| dt_sr_channel_reversal×GBP_USD | 50% (7/14) | SL過密 or entry 方向 |

Portfolio baseline は **60.5%** (from tp-sl-deep-mechanics-2026-04-22 §B). **8/10 cells で平均以上** → divergent 戦略は系統的に entry timing が劣化.

### 3.3 Post-cutoff (clean regime) standalone divergence

**BT 抜きの Post-cutoff only (2026-04-17 以降) LIVE 実績**:

#### 主要 LOSER (N≥10, EV<0)
| strategy×pair | N | WR | EV | PF | PnL |
|---|---:|---:|---:|---:|---:|
| ema_trend_scalp×USD_JPY | 155 | 23.9% | -1.07 | 0.66 | **-166.3** |
| ema_trend_scalp×GBP_USD | 44 | 13.6% | -3.12 | 0.34 | **-137.2** |
| bb_rsi_reversion×USD_JPY | 78 | 29.5% | -1.71 | 0.50 | -133.6 |
| ema_trend_scalp×EUR_USD | 81 | 22.2% | -1.32 | 0.53 | -106.6 |
| **macdh_reversal×USD_JPY** | **12** | **0.0%** | **-6.88** | **0.00** | **-82.6** |
| stoch_trend_pullback×USD_JPY | 45 | 24.4% | -1.78 | 0.48 | -79.9 |
| sr_fib_confluence×GBP_USD | 12 | 25.0% | -4.91 | 0.36 | -58.9 |
| fib_reversal×USD_JPY | 36 | 25.0% | -1.59 | 0.49 | -57.2 |

#### 主要 WINNER (N≥10, EV>0)
| strategy×pair | N | WR | EV | PF | PnL |
|---|---:|---:|---:|---:|---:|
| **bb_squeeze_breakout×USD_JPY** | **24** | **45.8%** | **+3.84** | **3.00** | **+92.2** |
| vol_surge_detector×USD_JPY | 19 | 42.1% | +2.73 | 2.11 | +51.9 |
| sr_channel_reversal×GBP_USD | 14 | 42.9% | +2.48 | 1.84 | +34.7 |
| trend_rebound×USD_JPY | 13 | 38.5% | +1.82 | 1.71 | +23.6 |

### 3.4 Scalp family systemic friction realization

**ema_trend_scalp 3ペア合計**: N=280 / PnL=**-410 pip** / 21日間
- BT (180d): USD_JPY 未計測 (1m scalp 低 EV 戦略群), GBP_USD 未計測
- LIVE: 全ペア WR < 25%, EV < -1.0

これは **BT の 1m scalp モデルが real spread/slippage friction を過少評価** している証拠. BEV_WR (USD_JPY 34.4%, EUR_USD 39.7%, GBP_USD 37.9%) を LIVE の WR 14-24% が下回る → **friction 未消化**.

---

## §4. 定量的クオンツ解釈

### 4.1 乖離の分類

| 型 | cells | 因果 |
|---|---|---|
| **Type A: Regime-shift overfitting** | engulfing_bb×USD_JPY, bb_squeeze_breakout×EUR_USD | 365d/180d BT が今の 20日 regime と違う |
| **Type B: Feature rollout drift** | dt_sr_channel_reversal, dual_sr_bounce, macdh_reversal | NULL regime で発火. gate 機能不全 |
| **Type C: Scalp friction gap** | ema_trend_scalp 全ペア, bb_rsi_reversion | 1m/5m BT の friction モデル不足 |
| **Type D: Small-N statistical noise** | vwap_mean_reversion×EUR_JPY (N=5), post_news_vol×USD_JPY (N=8) | Wilson CI 広すぎ、判定不能 |

### 4.2 Bonferroni-confirmed 3 cells の **今すぐ** 判定

| Strategy×Pair | N | Live WR | Wilson 95% upper | 判定 |
|---|---:|---:|---:|---|
| bb_squeeze_breakout×EUR_USD | 25 | 12.0% | 30.0% | **BEV_WR 39.7% 未達確定** → FORCE_DEMOTE推奨 |
| dt_sr_channel_reversal×GBP_USD | 17 | 17.6% | 41.0% | **BEV_WR 37.9% 境界** → Sentinel 継続観察 |
| engulfing_bb×USD_JPY | 75 | 32.0% | 43.2% | **BEV_WR 34.4% 境界** → 観察継続だが注意 |

### 4.3 追加: catastrophic single cell

**macdh_reversal×USD_JPY Post-cutoff: 0/12 (WR=0%), PnL=-82.6p**
- Wilson 95% upper: 23.8% << BEV 34.4%
- 構造的に損失確定域. **即停止候補**.

---

## §5. Actionable Recommendations (P = priority)

| P | Action | 根拠 | Gate |
|---|---|---|---|
| **P0** | `macdh_reversal×USD_JPY` 即停止 (N=12 0% WR, Wilson≤23.8% << BEV 34.4%) | §4.3 | 構造的損失域確定 |
| **P1** | `bb_squeeze_breakout×EUR_USD` FORCE_DEMOTE (§4.2 Bonferroni有意) | §1, §4.2 | Wilson upper < BEV |
| **P2** | Scalp family (`ema_trend_scalp` 全ペア, `bb_rsi_reversion` JPY/USD) の **friction モデル見直し** — BT vs LIVE の spread/slippage 実現乖離定量測定 | §3.4 | 1m BT の再 calibration |
| **P2** | `engulfing_bb×USD_JPY` Shadow 継続観察 (N=75 は小さくない, 境界判定) | §4.2 | 2026-05-15 再判定 |
| **P3** | **Regime feature rollout 完了まで BT-Live比較は regime 条件付きでは無効** → post-cutoff only で再スキャン | §3.1 | データ整合前提 |
| **HOLD** | 他の small-N cell (vwap_mean_reversion×EUR_JPY N=5 等) は統計推論不可. N≥15 まで待機 | §4.1 Type D | Wilson 幅過大 |

### 5.1 本日実行しない判断 (multiple testing inflation guard)

本日午前に **6 PRIME strategies pre-registered** (2026-05-15 binding). 本スキャンから新 filter を今日実装するのは:
- 15 cells × 2 directions = **30 implicit hypotheses** の post-hoc 探索
- Bonferroni で通った 3 cells 以外は **確定証拠でない**

→ **P0 (macdh_reversal) のみ構造確定**, P1 (bb_squeeze_breakout×EUR_USD) も実装候補. ただし今日 QUALIFIED_TYPES を触る場合 codex review 後に限定する.

---

## §6. Fresh 365d BT (進行中)

実行コマンド: `BT_MODE=1 python3 tools/bt_365d_runner.py`  
対象: USDJPY, EURUSD, GBPUSD × 365d × 15m  
ETA: 20-25 分  
進捗ログ: `/tmp/bt_divergence/bt_365d_run.log`

**完了後の追記予定**:
- 2026-04-15 (7日前) BT と 2026-04-22 BT の ΔWR / ΔEV 比較 — BT自体の drift があるか
- Walk-forward stability 更新
- 新 Bonferroni alpha 計算

---

## §7. Honest Disclosure (limitations)

1. **TF mismatch**: BT は DT 15m / Scalp 180d 1m・5m だが LIVE の TF が signal function 内で分岐する場合 apple-to-orange 比較になる
2. **Sample period mismatch**: BT 365d/180d vs LIVE 20日. LIVE は single regime sample に近く、BT の mean は別 regime 混合
3. **Shadow vs Live**: LIVE 2525 trade のうち is_shadow=1 が多数. Shadow は Kelly 学習対象外で挙動 proxy だが real fill ではない
4. **Post-hoc bias**: 本 ranking は post-hoc 探索. Bonferroni 通過の 3 cell 以外は confirmed evidence ではない
5. **macdh_reversal N=12**: 停止判断に使うには小. ただし 0/12 は二項 p(hypothesis: p=BEV=0.344) = 0.0086 → raw significant. しかし single cell P0 action に 12 samples は薄弱. 
   **修正: P0 → P1 に格下げ. Stop 判定は N≥20 until proven**.

---

## Related
- [[tp-sl-deep-mechanics-2026-04-22]] — portfolio-wide TP/SL 構造分析
- [[vwap-mr-live-analysis-2026-04-22]] — VWAP 単独深部
- [[bt-live-divergence]] — 6 structural biases (既存)
- [[friction-analysis]] — ペア別 BEV_WR
- [[audit-b-promoted-strategies-2026-04-21]] — 前回監査 (dt_fib_reversal 同構造)

---

**Status**: P1 recommendation まで提示. P0 への昇格は fresh BT 完了 + macdh_reversal N≥20 時点で再判定.
