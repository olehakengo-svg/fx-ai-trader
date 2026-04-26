# Edge Lab 730日 × 5 PAIR 統合解析 — 15m DT TF の PAIR 依存性 (2026-04-26)

> **観測のみ** (CLAUDE.md / lesson-reactive-changes 遵守).
> 実装判断は別期間 walk-forward で再検証後. 副次 edge 候補は **data-look-blind 別 pre-reg LOCK** で起案.

## 0. データセット

- **Lookback**: 730日 (2024-04-26 〜 2026-04-25)
- **TF**: 15m (DT 主力)
- **PAIR**: USD_JPY / EUR_USD / GBP_USD / EUR_JPY / GBP_JPY
- **Pooled enriched trades**: **N=15,842**
- **Source**: `tools/edge_lab.py` post-hoc multi-feature analysis

## 1. PAIR 別 edge 強度 (R1 Hurst Trend regime + D1 Vol + S3 Round-number)

### 1.1 R1 Hurst Regime (H>0.55 trend, DT 主力局面)

| PAIR | N | WR | EV |
|---|---|---|---|
| **USD_JPY** | 2687 | 63.1% | **+0.30** |
| GBP_JPY | 1446 | 62.4% | +0.14 |
| EUR_JPY | 1395 | 60.8% | +0.06 |
| EUR_USD | 1724 | 59.5% | +0.05 |
| **GBP_USD** | 2220 | 57.2% | **-0.05** |

### 1.2 D1 Vol Z-score Q1 (low vol)

| PAIR | WR | EV |
|---|---|---|
| **USD_JPY** | 64.3% | **+0.47** |
| GBP_JPY | 63.8% | +0.14 |
| EUR_USD | 62.6% | +0.15 |
| GBP_USD | 59.2% | +0.02 |
| EUR_JPY | 58.5% | -0.03 |

### 1.3 S3 Round-number Q1 (closest to .00/.50)

| PAIR | WR | EV |
|---|---|---|
| **GBP_JPY** | 65.0% | +0.19 |
| **EUR_JPY** | 64.6% | +0.15 |
| **USD_JPY** | 62.2% | +0.29 |
| GBP_USD | 59.4% | +0.01 |
| EUR_USD | 56.7% | -0.03 |

### 1.4 T2 Gotobi (JPY pair × Tokyo session)

| PAIR | Gotobi WR/EV | Non-Gotobi WR/EV | Gotobi - Non |
|---|---|---|---|
| **EUR_JPY** | **68.7% / +0.30** (N=83) | 60.7% / +0.04 (N=351) | **+0.26** ✨ |
| GBP_JPY | 64.9% / +0.07 | 64.0% / +0.17 | -0.10 |
| USD_JPY | 58.8% / +0.12 | 63.9% / +0.36 | -0.24 |

## 2. ELITE 3 戦略との整合性検証 (BT vs edge_lab post-hoc)

| 戦略 | PAIR | BT EV | edge_lab PAIR R1 trend EV | 整合性 |
|---|---|---|---|---|
| **session_time_bias** | USD_JPY | +0.580 | **+0.30 (最強)** | ✅ **整合** |
| gbp_deep_pullback | GBP_USD | +1.064 | **-0.05 (負)** | ⚠️ **BT 楽観バイアスリスク** |
| trendline_sweep | GBP_USD | +0.599 | **-0.05 (負)** | ⚠️ 同上 |
| session_time_bias | EUR_USD | +0.215 | +0.05 | ⚪ 弱整合 |
| session_time_bias | GBP_USD | +0.149 | -0.05 | ⚠️ 微負乖離 |
| trendline_sweep | EUR_USD | +0.574 | +0.05 | ⚠️ BT 楽観バイアスリスク中 |

### 解釈

- **USD_JPY 系統 ELITE は BT 妥当**: edge_lab post-hoc でも edge 強, Live 発火後の +EV 期待値高い.
- **GBP_USD 系統 ELITE は BT 楽観バイアスリスク**: edge_lab で R1/D1/S3 全て **edge ほぼゼロ-負**. 5m Phase 5 でも S2 Compression GBP_USD は **C04-06 GBP_USD が大量負け**で整合.
- **EUR_USD ELITE は中等度**: edge_lab で弱い edge (+0.05) のみ.

→ **ELITE 3 戦略 +433pip/年仮説のうち、GBP_USD 由来の +162pip (gbp_deep + trendline_sweep) は楽観バイアスリスク**.
   USD_JPY 由来の +91pip (session_time_bias × USD_JPY) のみが**信頼性の高い edge**.

## 3. 副次新 edge 候補 (HARKing 慎重起案候補)

### 3.1 EUR_JPY × Gotobi Tokyo

- 730日 N=83 (Gotobi) で WR 68.7% EV+0.30
- vs non-Gotobi N=351 で WR 60.7% EV+0.04
- **Edge: +0.26 pip / trade** (相対比較)
- 物理仮説: 本邦実需 (5/10日 month-end / 月初め) の EUR/JPY フロー
- **次アクション**: 別期間 (例: 2022-2024 の独立データ) で walk-forward 検定
  + data-look-blind 新 pre-reg LOCK で **2 cluster 検定** (HARKing 回避)

### 3.2 USD_JPY × D1 Vol Q1 (low vol)

- 730日 N=849 で WR 64.3% EV+0.47
- 物理仮説: low vol 環境での mean-reversion 安定性
- 既存 ELITE_LIVE session_time_bias × USD_JPY (BT +0.58) と非常に近い数値
- → **session_time_bias の物理仮説裏付け** として記録 (新 pre-reg 不要)

### 3.3 USD_JPY × S3 Round-number Q1

- WR 62.2% EV+0.29
- 物理仮説: Round number magnet (.00/.50 fade)
- 副次 edge 候補 (別 pre-reg LOCK 検討)

### 3.4 GBP_JPY × R1 MR Regime (H<0.45) ✨ (365d 完了で新規追加)

- 365日 N=234 で WR **66.2%** EV+0.22
- 730日 N=450 で WR 66.0% EV+0.21 (整合性 ✅)
- 物理仮説: GBP/JPY 高ボラ cross の **range 局面** mean revert
- 副次 edge 候補 (別期間 walk-forward + LOCK 推奨)

## 4. 削除推奨戦略との整合性

[[lesson-six-dead-strategies-removal-2026-04-26]] で削除推奨した 6 戦略のうち:
- ema_trend_scalp / fib_reversal / sr_channel_reversal / stoch_pullback / engulfing_bb (5m scalp)
- macdh_reversal (5m scalp)

これらは 15m DT post-hoc 分析対象外 (5m 戦略). 削除推奨判定変更なし.

## 5. v2.2 ロードマップへの影響

[[roadmap-v2.1]] の DT 幹 +433pip/年仮説の再評価:

| 戦略 | PAIR | BT 想定 | edge_lab 補正後想定 |
|---|---|---|---|
| session_time_bias × USD_JPY | USD_JPY | +91p | **+91p (維持)** ✅ |
| session_time_bias × EUR_USD | EUR_USD | +122p | +60p (50%減) ⚠️ |
| session_time_bias × GBP_USD | GBP_USD | +58p | +0p (負域) ❌ |
| trendline_sweep × GBP_USD | GBP_USD | +80p | +0p (負域) ❌ |
| trendline_sweep × EUR_USD | EUR_USD | +127p | +63p (50%減) ⚠️ |
| gbp_deep_pullback × GBP_USD | GBP_USD | +82p | +0p (負域) ❌ |

**補正後想定 PnL: +220 〜 +250pip/年** (元 +433pip の **50-58%**)

→ ロードマップ v2.1 の DT 幹仮説は **GBP_USD 系統の楽観バイアス補正が必要**.
   Mon Tokyo open Live 発火で実証性検証 → v2.2 で数値補正.

## 6. メモリ整合性

- [部分的クオンツの罠]: PAIR × Feature 4 軸で WR/EV 完備 ✅
- [ラベル実測主義]: edge_lab 730日 N=15,842 実測のみ ✅
- [成功するまでやる]: 副次 edge 候補 (Gotobi/Round number) は別 pre-reg で深掘り継続 ✅
- HARKing 回避: 副次 edge は **別期間 + data-look-blind LOCK** で再検定 ✅

## 7. 参照
- [[edge-reset-direction-2026-04-26]] (Phase 2 棚卸しの起点)
- [[phase2-mechanism-thesis-inventory-2026-04-26]] (60 戦略 mechanism 評価)
- [[lesson-six-dead-strategies-removal-2026-04-26]] (削除推奨 6 戦略)
- [[roadmap-v2.1]] (DT 幹 +433pip/年仮説)
- `tools/edge_lab.py` (post-hoc 分析ツール)
- `knowledge-base/raw/bt-results/edge-lab-2026-04-26.json` (生データ)
