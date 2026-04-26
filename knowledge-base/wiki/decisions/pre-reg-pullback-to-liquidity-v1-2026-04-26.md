# Pre-Registration LOCK: pullback_to_liquidity_v1

**LOCK Date**: 2026-04-26
**Type**: Phase 3 mechanism-driven 新エッジ pre-registration
**Category**: TF (Trend-Following)
**Status**: 🔒 LOCKED — 仮説/閾値を本日付で固定。HARKing 防止のため後付け変更禁止。

## 1. Hypothesis (Mechanism Thesis)

**1 行**: HTF (H4) trend が確立した方向に対し、M15 swing low/high への pullback 局面では
流動性供給により価格が再加速する。pullback 完了 + rejection で entry。

**メカニズム詳細**:
- HTF trend 確立 = institutional flow が一方向に偏る (Time Series Momentum, Moskowitz et al 2012)
- M15 pullback = 短期 contrarian の利食い + 反対方向 stop hunt
- swing low/high touch = 流動性供給 zone (limit orders concentration)
- rejection candle = 流動性吸収完了の signal

**因果方向**: HTF trend → 短期 pullback → liquidity zone touch → rejection → trend resume

**TAP 含有チェック**:
- TAP-1 (中間帯 AND): ❌ 不含 (HTF trend は明示的方向、中間帯ではない)
- TAP-2 (N-bar pattern): ❌ 不含 (rejection は 1 bar の wick body ratio)
- TAP-3 (直前 candle): ⚠️ rejection candle は直前 1 bar 確認だが、liquidity zone touch という構造的前提が必須

→ 構造的に TAP 回避。

## 2. Entry Conditions (LOCKED)

### Required (全て満たす必要)

```
HTF_TREND_CONDITION:
  H4 EMA50 > H4 EMA200 → HTF_BIAS = "bull"  (BUY のみ許可)
  H4 EMA50 < H4 EMA200 → HTF_BIAS = "bear"  (SELL のみ許可)
  otherwise → no entry

M15_PULLBACK_CONDITION:
  recent 20 bars に M15 swing high (BUY時は swing low) が存在
  swing low (BUY): max(low) of last 20 bars が ≥ 5 bar 前
  swing high (SELL): max(high) ...

LIQUIDITY_TOUCH:
  current bar の low (BUY) ≤ swing_low * (1 + 0.001)   [5pip以内]
  current bar の high (SELL) ≥ swing_high * (1 - 0.001)

REJECTION_CANDLE:
  BUY: close > open AND (low - close) / (high - low) ≥ 0.4
       — 下髭比率 40% 以上 (流動性吸収後の上昇)
  SELL: close < open AND (high - close) / (high - low) ≥ 0.4

VOLUME_CONFIRMATION:
  current bar volume ≥ 1.2 × volume_avg(20)
```

### Forbidden (除外条件)

```
- HTF_BIAS == "neutral" (no trend) → no entry
- 直前 4 bars 内に同方向 entry 済み → no entry (重複防止)
- ATR(14) < 5 pip → no entry (volatility too low)
- session = Asia_early (00-02 UTC) → no entry (流動性 dead zone)
```

## 3. Exit Conditions (LOCKED)

```
TP: entry ± 2.0 × ATR(14)  (RR ratio 2:1)
SL: entry ∓ 1.0 × ATR(14)
TIME_STOP: 24 bars (M15 × 24 = 6h) で未達なら成行決済
```

## 4. Validation Requirements (LOCKED — 一切緩和不可)

| 項目 | 閾値 | 検証手段 |
|---|---|---|
| Sample size | N ≥ 200 (Live + Shadow 合算) | Wilson lower bound 計算可能性 |
| Win Rate | Wilson lower bound > 50% | `tools.empirical_validator.wilson_ci` |
| Profit Factor | PF > 1.30 | (sum win) / (sum loss) |
| EV per trade | EV > 0 (after Friction Model v2 cost) | `modules.friction_model_v2.friction_for` |
| Walk-Forward | 5-fold WF, 各 fold で WR > 50% AND PF > 1.0 | 365日 BT を 5 等分 |
| Bonferroni 補正 | α=0.05 / m=10 (10 個の pre-reg 候補想定) → α=0.005 | `tools.empirical_validator.bonferroni_correct` |
| Top-1-drop | drop_pct < 30% | `tools.empirical_validator.top_k_drop_test` |
| Bootstrap CI | 95% CI low > 0 (EV) | `tools.empirical_validator.bootstrap_ci` |
| Monte Carlo DD | DD ≤ Kelly Half 許容範囲 | `modules.risk_analytics` |

**全項目 PASS で初めて shadow → forward → live promote 候補**。
1 項目でも fail → 戦略破棄、HARKing で閾値緩和は禁止。

## 5. Test Plan

### Phase 3.A: 365日 BT (Phase 3 セッションで実施)

- Pair set: USD_JPY, EUR_USD, GBP_USD (Friction Model v2 でサポート)
- Period: 2025-04-26 〜 2026-04-26 (365日)
- Cost: `friction_for(pair, mode="DT", session=auto)` で動的 friction
- ATR: 過去 14 bars (M15)

合格基準: 上記 9 項目全 PASS

### Phase 3.B: Walk-Forward (Phase 3 セッションで実施)

- Period を 5 fold (each ~73日)
- 各 fold で個別 WR/EV/PF
- Out-of-sample な fold ごとに合格判定

### Phase 3.C: Shadow forward test (Phase 3 後)

- 1 ヶ月 shadow forward
- N ≥ 30 で Wilson lower bound > 50% 確認
- A/B route (with/without strategy) で混入させ pure effect 測定

### Phase 3.D: Live promotion

- shadow PASS なら 0.01 lot で live 投入
- N ≥ 30 で再検証、Wilson lower bound > 50%
- Kelly Half ルールで lot 増設

## 6. Anti-pattern 警告 (LOCKED — 違反したら戦略破棄)

- ❌ **閾値緩和**: WR < 50% で「あと少しだから 0.005 だけ緩和」→ HARKing、戦略破棄
- ❌ **期間拡張**: 1 年 BT で fail → 「2 年やれば回復するかも」→ HARKing、戦略破棄
- ❌ **Pair 削除**: 3 pair 中 1 pair fail → 「USD_JPY だけで継続」→ cherry-pick、戦略破棄
- ❌ **TF 変更**: M15 で fail → 「M30 でやれば」→ data dredging、戦略破棄
- ❌ **指標追加**: 既存条件 fail → 「ADX フィルタ追加で復活」→ overfitting、戦略破棄

→ 1 度 LOCK したら、結果を見て条件変更不可。失敗したら破棄、別 hypothesis を新規 LOCK。

## 7. Expected Effect Size (Pre-Registration)

仮の estimate (BT 前なので外れる可能性あり):
- Estimated WR: 55% (HTF trend × pullback の理論値)
- Estimated PF: 1.50
- Estimated EV: +0.5 pip / trade (after Friction Model v2 cost)
- Required N (sample size planner): `sample_size_for_proportion_diff(0.50, 0.55) ≈ 1500`
  → 検出には N≥1500 必要 = 365日 BT で fire 1500 回が前提
- Fire frequency 不足の場合は判定保留 → Phase 3 セッションで再評価

## 8. References

- [[strategy-mechanism-audit-2026-04-26]] — thesis 評価枠組み
- [[edge-reset-direction-2026-04-26]] — Phase 0 方向転換
- [[friction-analysis]] — Friction Model v2 ベース数値
- `modules/friction_model_v2.py` — friction lookup
- `tools/empirical_validator.py` — wilson_ci / bootstrap_ci / monotonicity / top_k_drop
- Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum" — 学術根拠
