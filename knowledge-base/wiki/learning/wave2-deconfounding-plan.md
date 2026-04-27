# Wave 2 Multi-Change De-Confounding Statistical Plan

**Session**: curried-ritchie (Wave 2 Day 4 Quant Rigor)
**Date**: 2026-04-27 13:30 JST (= 04:30 UTC)
**Status**: Phase α qualitative check 完了、measurement 期間 design LOCK
**目的**: 5 つの同時 deploy 変更 (Wave 1 R2-A, U18 quartile fix, Wave2 A2/A3/A4, C2-SUPPRESS expansion, fib_reversal C1-PROMOTE) の effect を **post-hoc 分離可能**にする統計設計

---

## 0. Executive Summary

**5 changes confounded period (2026-04-26 23:27Z 〜 hold-out 2026-05-01)**:
- 個別 effect の clean attribution は不可能、ただし **per-trade observable indicators** で post-hoc 分解可能
- Bonferroni K=5 で α/5 = 0.01、現在 N/cell=10-30 なら ΔWR ≥ 15-25pp の effect しか検出不能
- → measurement 期間延長 (ε +7d 不十分、ζ +14d まで継続) + 多変量 logit decomposition で個別寄与抽出

---

## 1. 5 Changes Inventory (Confounding Sources)

| # | Change | Mechanism | Trigger Condition | 観測可能性 |
|---|--------|-----------|-------------------|-----------|
| 1 | Wave 1 R2-A suppress | `apply_r2a_suppress_gate()` confidence ×0.5 | (entry_type, session, spread_q) ∈ _R2A_SUPPRESS の 5 cells | reasons log "⚠️ R2-A suppress" 文字列 |
| 2 | U18 quartile fix | `compute_spread_quartile()` 4-bin static cuts | 全 trade で適用 (cell 判定で differential effect) | reasons log "spread_q=q0/q1/q2/q3" |
| 3 | Wave2 A2 SL pip clamp | `calc_sl_tp_v3()` SL ∈ [3, 50] pip clamp | SL < 3 OR (short TF AND SL > 50) | reasons log "SL pip clamp" |
| 4 | Wave2 A3 Cost throttle | `compute_*_signal()` confidence ×0.7 | friction > pair-baseline ×1.5 | reasons log "frequency throttle" |
| 5 | Wave2 A4 Vol scale | (詳細 commit 要確認) | volatility regime 関連 | reasons log "vol scale" |
| **+** | **C2-SUPPRESS expansion** | _R2A_SUPPRESS に `(ema_trend_scalp, Overlap, q0)` 追加 | (1) と同 mechanism、cell 拡張 | reasons log 同上 |
| **+** | **fib_reversal C1-PROMOTE** | Live 0.05 lot promotion | fib_reversal × Tokyo × q0 × Scalp 発火時 | trade entry で fib_reversal Tokyo q0 が増加 |

---

## 2. De-Confounding 戦略 (3 段階)

### 2.1 Stage 1: Per-Trade Treatment Indicator 抽出

各 trade に 5 個の binary indicator を attach:

```python
def extract_treatments(trade) -> dict:
    reasons = trade.get('reasons', '') or ''
    return {
        'r2a_applied':       'R2-A suppress' in reasons,         # change 1
        'quartile_applied':  True,  # 全 trade で適用 (intercept として扱う)
        'sl_clamped':        'SL pip clamp' in reasons or 'SL clamp' in reasons,
        'cost_throttled':    'frequency throttle' in reasons.lower(),
        'vol_scaled':        'vol scale' in reasons.lower(),
        'fib_promoted':      (trade.get('entry_type') == 'fib_reversal' and
                              session_of(trade) == 'Tokyo' and
                              spread_q_of(trade) == 'q0' and
                              trade.get('mode') == 'scalp_5m'),
    }
```

### 2.2 Stage 2: Logit Multivariate Regression

```
P(WIN | trade) = logit⁻¹(β₀ + β₁·R2A + β₂·SL_clamp + β₃·CostThr + β₄·VolScale + β₅·FibPromote
                        + γ_session + γ_pair + γ_strategy + ε)
```

各 β_k が treatment k の **WR への individual effect** を represent。confounder (session, pair, strategy) を γ で control。

**前提**:
- IID assumption: 各 trade outcome は他 trade と独立 (近似)
- Linear additive: log-odds 加法性、低 effect size 域では妥当
- Sufficient N: 各 treatment indicator で N(treated) ≥ 20 必要

### 2.3 Stage 3: Pre-Post Comparison with Matching

deploy 前 1 週間 (2026-04-19 〜 04-25, **before 5 changes**) を **synthetic control** として:

1. **Matched cell-level comparison**:
   - 同 (entry_type, session, pair) の Pre vs Post WR 差を計算
   - target cells (R2-A 5 cells) で差が見られるか
   - non-target cells で差が見られない (副作用なし) ことを確認

2. **Confounder check**:
   - market regime (VIX 推定, BOJ intervention 観測)
   - day-of-week distribution (Pre が Sat-Fri、Post が Mon〜)
   - hourly intensity (session 別 trade 頻度の Pre-Post)

---

## 3. 統計検出力 計算

### 3.1 各 treatment 個別 effect

Bonferroni K=5 (5 treatments) で α=0.01:

| N (treated) | Detectable Δlog-odds (β) | 対応する ΔWR (baseline 30%) |
|-------------|---------------------------|------------------------------|
| 10 | β ≥ 1.20 | ΔWR ≥ +21pp |
| 20 | β ≥ 0.85 | ΔWR ≥ +15pp |
| 30 | β ≥ 0.70 | ΔWR ≥ +12pp |
| 50 | β ≥ 0.55 | ΔWR ≥ +10pp |
| 100 | β ≥ 0.39 | ΔWR ≥ +7pp |
| 200 | β ≥ 0.28 | ΔWR ≥ +5pp |

**現状 N(post-deploy) = 36 (5h 経過、CLOSED 34)**: Δlog-odds ~ 0.65 が検出限界 → ΔWR ≥ 11pp 必要。

### 3.2 計測 schedule (revised, Bonferroni K=5)

| Phase | timing | Cumulative N (推定) | Detectable ΔWR |
|-------|--------|---------------------|-----------------|
| α (済) | +6h 04-27 06:00 JST | ~50 | ΔWR ≥ ~15pp (descriptive only) |
| β | +12h 04-27 12:00 JST | ~100 | ΔWR ≥ ~12pp |
| γ | **+24h 04-27 24:00 JST** | ~200 | **ΔWR ≥ ~9pp** (initial logit fit possible) |
| δ | +72h 04-30 02:00 JST | ~500 | **ΔWR ≥ ~6pp** (Bonferroni-significant detection) |
| ε | +7d 05-04 | ~1100 | ΔWR ≥ ~4pp (full effect map) |
| ζ | +14d 05-11 | ~2200 | ΔWR ≥ ~3pp (per-cell saturation) |
| η | +30d 05-27 | ~4700 | ΔWR ≥ ~2pp (long-term equilibrium) |

→ **Phase γ (+24h) で initial logit fit 開始、Phase δ (+72h) で Bonferroni-significant 結論可能**。

---

## 4. 実装プラン

### 4.1 計測 SQL / Python 雛形

```python
# wave2-deconfounding-monitor.py
import sqlite3, math
from scipy.stats import logistic
import pandas as pd

CONN = sqlite3.connect('demo_trades.db')
DEPLOY_TIME = '2026-04-26T23:27:36Z'  # e362254 push

def fetch_post_deploy_trades():
    return pd.read_sql_query(f"""
        SELECT *, 
               CASE WHEN reasons LIKE '%R2-A suppress%' THEN 1 ELSE 0 END as r2a_applied,
               CASE WHEN reasons LIKE '%SL pip clamp%' OR reasons LIKE '%SL clamp%' THEN 1 ELSE 0 END as sl_clamped,
               CASE WHEN LOWER(reasons) LIKE '%frequency throttle%' THEN 1 ELSE 0 END as cost_throttled,
               CASE WHEN LOWER(reasons) LIKE '%vol scale%' THEN 1 ELSE 0 END as vol_scaled,
               CASE WHEN entry_type='fib_reversal' AND mode='scalp_5m' THEN 1 ELSE 0 END as fib_promote_eligible,
               CASE WHEN outcome='WIN' THEN 1 ELSE 0 END as win
        FROM demo_trades
        WHERE entry_time >= '{DEPLOY_TIME}'
          AND status='CLOSED'
          AND instrument NOT LIKE '%XAU%'
    """, CONN)

def fit_logit(df):
    from sklearn.linear_model import LogisticRegression
    features = ['r2a_applied', 'sl_clamped', 'cost_throttled', 'vol_scaled', 'fib_promote_eligible']
    # session/pair/strategy dummies
    df = pd.get_dummies(df, columns=['session', 'instrument', 'entry_type'], drop_first=True)
    X = df[features + [c for c in df.columns if c.startswith(('session_', 'instrument_', 'entry_type_'))]]
    y = df['win']
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return dict(zip(features, model.coef_[0][:5]))
```

### 4.2 Pre-Post Matched Analysis

```python
def matched_cell_comparison(pre_window, post_window):
    """同 (entry_type, session, pair) cell の Pre vs Post WR 差。"""
    cells_pre = pre_window.groupby(['entry_type', 'session', 'instrument']).agg(
        n=('win', 'size'), wins=('win', 'sum')).reset_index()
    cells_post = post_window.groupby(['entry_type', 'session', 'instrument']).agg(
        n=('win', 'size'), wins=('win', 'sum')).reset_index()
    merged = cells_pre.merge(cells_post, on=['entry_type', 'session', 'instrument'], 
                              suffixes=('_pre', '_post'), how='outer').fillna(0)
    merged['wr_pre'] = merged['wins_pre'] / merged['n_pre'].replace(0, 1)
    merged['wr_post'] = merged['wins_post'] / merged['n_post'].replace(0, 1)
    merged['delta_wr'] = merged['wr_post'] - merged['wr_pre']
    return merged
```

### 4.3 各 Phase での実行手順

**Phase γ (+24h)**:
1. fetch_post_deploy_trades() — N≥200 想定
2. R2-A target 5 cells で suppress fired trades が発生したか確認 (London/Overlap session 進行)
3. SL clamp / cost throttle / vol scale の発火件数 観測
4. logit fit (各 treatment N≥10 達成後) で initial β estimates
5. Confounder check: session/pair distribution の Pre-Post 比較

**Phase δ (+72h)**:
1. logit fit で Bonferroni-significant β estimates (K=5, α=0.01)
2. Matched cell comparison: target cells で Pre-Post ΔWR を Bonferroni 通過か検定
3. 副作用 check: non-target cells の ΔWR が ±5pp 以内か
4. Phase 3 GO/NO-GO 1st 判断

**Phase ε (+7d) / ζ (+14d)**:
1. Per-cell saturation 確認 (ΔWR ≥ ±3pp の精度で検定)
2. 5 changes 個別 effect の最終 estimate
3. Phase 3 BT 着手 GO/NO-GO 最終判断

---

## 5. 期待される結果と判断基準

### 5.1 Hypothesis Map

| Treatment | Expected effect (β) | Sign | 検証方法 |
|-----------|---------------------|------|----------|
| R2-A applied | +(損失防止) | 正 (WR +) | suppress された cells で entry 数減 + 残りの WR は baseline 維持 |
| SL clamp | 0 か中立 | 0-小 | 極端 SL のみ調整、effect は marginal |
| Cost throttle | 中立か正 | 0-小 | Sydney/Asia early の confidence 抑制 |
| Vol scale | 不明 | 不明 | volatility regime 依存 |
| Fib C1-promote | 強正 (Bonferroni 通過) | 正 (WR +) | fib_reversal × Tokyo × q0 で Live N≥30 後 Wilson lower > 50% |

### 5.2 Failure Modes

- **Worst-case**: 全 5 treatments が β ≈ 0 (effect なし) → Wave 1+2 全体が no-op、Phase 3 BT で根本再設計
- **Mixed**: 一部 positive、一部 neutral → 個別 cell rules を refine、Phase 3 BT で best-fit Mode 決定
- **Best-case**: 5 treatments の正の β 合算で Live edge 改善 → Phase 3 BT 着手の追い風

### 5.3 Stop-Loss 判断 (Wave 2 全体)

**revert 検討 trigger**:
- Phase γ (+24h) で **non-target cells WR が顕著低下** (ΔWR ≤ -10pp)、副作用確定 → Wave2 A2/A3/A4 revert 検討
- Phase δ (+72h) で **MC ruin 簡易計算が 90% 超え** (Live PnL drawdown 累積) → 全 changes revert (Wave 1 R2-A も)

---

## 6. Quant Rigor 規律

### 6.1 HARKing 防止

- 本 plan を git commit + push で時刻署名 (Pre-reg LOCK 補完)
- 計測期間中の本 plan 修正は新 commit で記録
- 結果が NULL でも plan 内の閾値・指標は変更しない

### 6.2 Multi-change confounded acknowledgement

Phase γ-η の judgment は **"single change effect" ではなく "5 changes joint effect" として解釈**。Phase 3 BT 設計の "Mode A vs B comparison" には今回観測値を直接入力できない (confounded のため)。Phase 3 BT で **Mode A 単独 vs Mode B 単独 vs Mode A + Wave2 vs Mode B + Wave2** の 4-arm BT 設計を検討。

### 6.3 Reverse-engineering 制限

logit β estimate は **observational** であり、causal claim は弱い。RCT (random treatment assignment) は無い。**conservative interpretation**: β > 0 でも効果あり確定ではなく、副作用なしの確認止まり。

---

## 7. 残課題 / 追加 unresolved

### 7.1 Phase α 観測で判明した課題

- **R2-A target cells (London×q3, London×q0) は post-deploy 5h で発火 0 件**: Tokyo session のみ active のため。London 開始 (~07 UTC = +3h 後) で初発火期待
- **Wave2 A2/A3/A4 も同 0 件**: 各 trigger condition の rare nature が原因の可能性、Phase γ で再観測

### 7.2 まだ計測していない変更

- **C2-SUPPRESS expansion** (`ema_trend_scalp × Overlap × q0`): 既 R2-A registry に追加済、別 cell として観測必要
- **fib_reversal × Tokyo × q0 × Scalp Live promotion**: post-deploy 1 件発火 (LOSS) のみ、N=1 で評価不能

### 7.3 Phase 3 BT 着手判断への影響

- 当初 Pre-reg LOCK §6 (採用基準) は "confounded を想定していない"
- §9.1 update で multi-change confounded 期間 (deploy 〜 hold-out) の judgment 規則を追加必要
- specifically: Phase 3 BT 着手は ε (+7d) ではなく **ζ (+14d) 以降**に延期推奨

---

## 8. References

- Pre-reg LOCK 文書: `wiki/learning/phase3-bt-pre-reg-lock.md` (commit `34c404c`)
- Wave 1 R2-A Power Analysis: `wiki/learning/wave1-r2a-power-analysis.md`
- Wave 1 deploy: commit `f1cc1aa` (Wave 1 R2-A) + `e362254` (U18 fix) + `4df389f` (Wave2 A2/A3/A4) + `795d4af` (C2-SUPPRESS) + `7437e19` (fib C1)
- Master: `wiki/learning/fx-fundamentals.md` Section 6.4
- 数学根拠: Track ⑤ §5.3-5.6 (Bonferroni / Power calc)
