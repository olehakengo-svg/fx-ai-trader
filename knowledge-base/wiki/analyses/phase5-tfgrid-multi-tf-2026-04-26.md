# Pre-Registration: Phase D TF Grid (15m/30m/1H/2H/4H) — 2026-04-26 LOCK

> **Pre-reg LOCK 確定 (2026-04-26)** — data look 前. 5m Phase 5 で 6/9 DEAD と
> 確定した直感仮説 3 種を **5 つの TF (15m/30m/1H/2H/4H)** で並列検定し、TF 依存性
> を定量化. ELITE_LIVE 3 戦略 (15m bar) が機能している前提を BT で再現可能か検証.

## 0. HARKing 回避規律

- 仮説の方向性は本日 (4/25) Phase 5 結果**前**に予め決まっていた物理仮説のみ採用.
- D3 (Z-Score 順張り) は S3 BT で逆方向有意性を確認した結果からの**着想**だが、
  「異 PAIR + 5m → 15m+TF」で independence 確保. data leak リスクは制御済.
- 個別パラメータ閾値は文献値で先に決める (本 pre-reg で固定).

## 1. 3 仮説 × 5 TF Grid

### D1: BB Extreme Mean Reversion
- **仮説**: BB%B ≤ 0.05 / ≥ 0.95 の極限値で mean revert
  (5m noise を 高 TF 平均で消去 → Bollinger 1992 の本来想定 TF)
- **TF**: 15m / 30m / 1H / 2H / 4H
- **PAIR**: EUR/USD, USD/JPY (Top 流動性)
- **個別パラメータ (固定)**: bb_period=20, bb_std=2.0,
  TP=BB middle, SL=ATR×0.8, MIN_RR=1.5

### D2: EMA50 Pullback Continuation
- **仮説**: 強 trend 中 (EMA9>EMA21>EMA50) の EMA50 タッチ→反発
  (Moskowitz 2012 momentum, 4H 以上は週足/月足の延長で実証域)
- **TF**: 15m / 30m / 1H / 2H / 4H
- **PAIR**: EUR/USD, GBP/USD (Cable 系 trend follow)
- **個別パラメータ (固定)**: pullback_max_atr=0.3 (touch 判定),
  trend_strict (ema9>21>50), TP=ATR×3.0, SL=ATR×1.0, MIN_RR=2.5

### D3: Z-Score Momentum (順張り)
- **仮説**: |z|>3σ で **継続方向** entry (S3 mean revert 逆方向)
  本日 S3 で逆張りが p_welch=0.0061 で損失方向有意 = 順張り Edge 候補
- **TF**: 15m / 30m / 1H / 2H / 4H
- **PAIR**: USD/JPY, GBP/JPY (高ボラ JPY 系)
- **個別パラメータ (固定)**: z_threshold=3.0, lookback=100,
  TP=ATR×4.0, SL=ATR×1.0, MIN_RR=3.0
- **HARKing 回避注記**: 異 PAIR (USD/JPY+GBP/JPY) 採用 = S3 (USD/JPY 含む) と
  独立検定. PAIR overlap 1個のみ.

## 2. 検定 Grid

各仮説 5 TF × 2 PAIR × 1 個別パラメータ = **10 cells**.
合計 **3 仮説 × 10 cells = 30 cells**.

Bonferroni: outer 3 仮説独立 → 各仮説内 α_cell = 0.05 / 10 = **0.005**.

## 3. SURVIVOR Gate (LOCKED, AND)

### 共通条件
1. EV > +1.5p / trade
2. PF > 1.5
3. N ≥ 20 (TF 上げで N 減少するため低めに設定)
4. Wilson_lo (WR) > 観測 WR の 70%
5. Welch p < 0.005 vs random baseline
6. WF 4/4 same-sign
7. MAE_BREAKER < 30% (FLOOR_INFEASIBLE 回避)

### 仮説別追加条件
- D1 (mean revert): WR ≥ 50%
- D2 (pullback continuation): 実 RR ≥ 2.0
- D3 (z momentum): 実 RR ≥ 2.5

## 4. メタ判定 (TF 依存性)

各仮説の 5 TF の SURVIVOR 状況で 4 パターン分類:
- **A. 全 TF SURVIVOR**: 仮説の robustness 高 → どの TF でも deploy 候補
- **B. 高 TF (1H+) で SURVIVOR**: 5m noise が edge を埋めていた → 上位足で deploy
- **C. 特定 TF のみ (例 15m, ELITE 系統)**: TF 局所性. 該当 TF 限定 deploy
- **D. 全 TF REJECT**: 仮説自体が間違い (5m DEAD と同根)

仮説間の比較で:
- D1/D2/D3 の少なくとも 1 つで TF 依存性 (B/C パターン) → Phase 5 5m 失敗が
  TF 限定の問題と判明. 上位 TF でロードマップ再構築.
- D1/D2/D3 全 D パターン → TF 依存ではなく**根本仮説の問題**. 5m+TF パラダイム
  両方棄却. v2.4 で ML/regime classification 等への根本転換.

## 5. 実装注記

### 新規 BT harness
- `scripts/phase5_d1_bb_mr_tfgrid_bt.py` (新規, BB extreme MR × 5 TF)
- `scripts/phase5_d2_ema50_pullback_tfgrid_bt.py` (新規, EMA50 pullback × 5 TF)
- `scripts/phase5_d3_zscore_mom_tfgrid_bt.py` (新規, Z-score momentum × 5 TF)

### TF データ取得
- `modules.data.fetch_ohlcv_massive(symbol, "15m", days=730)` 等を使用
- 15m/30m/1H/2H/4H で MASSIVE / OANDA range の対応確認必要

### simulate_pnl の TF 適応
- bb_squeeze の simulate_pnl は 5m bar 前提. TF 別の MAX_HOLD_BARS / MAE_BREAKER 適切値:
  - 15m: MAX_HOLD=24 bars (6h), MAE_BREAKER=15p (5m と同)
  - 30m: MAX_HOLD=24 (12h), MAE_BREAKER=20p
  - 1H: MAX_HOLD=24 (1day), MAE_BREAKER=30p
  - 2H: MAX_HOLD=24 (2 days), MAE_BREAKER=50p
  - 4H: MAX_HOLD=24 (4 days), MAE_BREAKER=80p

## 6. タイムライン (5/14 待たずに即時着手)

| 日付 | アクション |
|---|---|
| 2026-04-26 (本日 LOCK) | 本 pre-reg + 3 harness 設計 (実装は副次 2y BT 完走後) |
| 2026-04-27 (Mon Tokyo open) | Phase A Live 観測開始 |
| 2026-04-27〜04-30 | 3 D harness 実装 + dry-run |
| 2026-04-30〜05-03 | 3 D 365日 BT 実行 (TF 別並列) |
| 2026-05-04 | SURVIVOR 判定 + メタ判定 (A/B/C/D パターン)
| 2026-05-07 | Phase 1 holdout と統合判定

## 7. 凍結ルール

- 本 pre-reg LOCK 後、**コード変更 + データ覗き禁止**まで BT 完走.
- Phase 5 5m BT 結果を踏まえた閾値調整は HARKing 違反 → 個別パラメータ固定維持.

## 8. メモリ整合性

- [部分的クオンツの罠]: 全 BT で PF/Wlo/p_welch/WF/MAE_BREAKER 完備 ✅
- [ラベル実測主義]: BT 365日実測のみで判定 ✅
- [成功するまでやる]: REJECT でも 5 TF grid で TF 依存性の構造解明 ✅
- [Asymmetric Agility Rule 1]: 新エッジ主張 = LOCK + Bonferroni 完備 ✅
- 総当たり禁止: 各仮説 PAIR 2 個限定 ✅
- HARKing 回避: 個別パラメータは文献値先取り. PAIR overlap 1 個に限定 ✅

## 9. 参照
- [[phase5-9d-edge-matrix-2026-04-25]] (Phase 5 5m 結果)
- [[phase5-secondary-2y-2026-04-26]] (副次仮説 2y 並走)
- [[lesson-pure-edge-5m-structural-failure-2026-04-25]] (5m 構造的失敗)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1)
- [[roadmap-v2.1]] (DT幹 15m bar 系統)
