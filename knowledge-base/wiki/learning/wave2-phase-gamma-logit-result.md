# Wave 2 Phase γ De-Confounding Logit Measurement Result

**Session**: curried-ritchie (Wave 2 Day 7)
**Date**: 2026-04-27 ~15:00 JST (= 06:00 UTC)
**Measurement timing**: Wave 1+2 deploy 後 ~28h (Phase γ +24h 通過、Phase δ +72h 接近中)
**Status**: 🚨 **Logit fit 不可 — critical finding documented**

---

## 0. Executive Summary (Quant TL;DR)

**Phase γ logit multivariate fit は不可能**。理由: Wave 1+2 全 5 treatment indicators のうち 4 件が **N(treated)=0** (post-deploy 107 trades 中)、残 1 件 (fib_promote) のみ N=4 で fit power 不足。

**🚨 重大 finding**:
- **Wave 1 R2-A は構造的に no-op**。R2-A 5 cells 全戦略が **Scalp mode** だが、R2-A gate は DT path (compute_daytrade_signal) にしか挿入されていない (Wave 1 deploy 時点の implementation gap)
- **Wave2 A2/A3/A4 (SL clamp / cost throttle / vol scale) も全て 0 fires**。trigger condition が rare の可能性、または reasons log 文字列マッチング不一致
- **fib_promote (4 件) のみ descriptive observable**

→ Wave 1+2 の defensive 施策はほぼ無効、月利 100% roadmap には **Phase 3 BT + Wave 3 mechanism-driven new strategies** が依然 critical path。

---

## 1. Measurement Data (production API, post-deploy +28h)

### 1.1 Sample summary

```
Post-R2A deploy (since 2026-04-26 14:18 UTC, f1cc1aa): N=107 trades (FX-only)
Post-U18 deploy (since 2026-04-26 23:27 UTC, e362254):  N=107 trades (FX-only)
CLOSED outcomes: WIN=27, LOSS=63, BREAKEVEN=6 (N=96)
WR (closed): 28.1% (Wilson 95% [19.7, 38.4])
Pre-deploy baseline WR: ~30-39% (depending on filter)
```

### 1.2 Per-strategy breakdown (top 10)

| 戦略 | N | mode |
|------|---|------|
| **ema_trend_scalp** | 27 | scalp |
| **bb_rsi_reversion** | 14 | scalp |
| **sr_channel_reversal** | 13 | scalp |
| engulfing_bb | 10 | scalp |
| **stoch_trend_pullback** | 6 | scalp |
| post_news_vol | 5 | daytrade |
| fib_reversal | 4 | scalp_5m |
| **vol_momentum_scalp** | 4 | scalp |
| **vol_surge_detector** | 4 | scalp |
| macdh_reversal | 3 | scalp |

→ **R2-A 5 cells の全戦略 (太字)**は scalp mode、DT path 不通過。

### 1.3 Treatment indicator counts

| Treatment | Count (N=107) | %% | 検出可能性 |
|-----------|---------------|-----|------------|
| `r2a_applied` (R2-A suppress reasons) | **0/107** | 0% | logit fit 不可 |
| `sl_clamped` (SL pip clamp) | **0/107** | 0% | logit fit 不可 |
| `cost_throttled` (frequency throttle) | **0/107** | 0% | logit fit 不可 |
| `vol_scaled` (vol scale) | **0/107** | 0% | logit fit 不可 |
| `fib_promote` (fib_reversal × scalp) | **4/107** | 3.7% | descriptive only (N too small for inference) |

---

## 2. 🚨 Critical Findings (3 件)

### 2.1 Finding A: Wave 1 R2-A は **構造的 no-op** (U20 新規)

**証拠**:
- R2-A 5 target cells の全戦略 (`stoch_trend_pullback`, `sr_channel_reversal`, `ema_trend_scalp` ×2, `vol_surge_detector`) すべて `strategies/scalp/*.py` に実装、`mode = "scalp"`
- R2-A gate (`apply_r2a_suppress_gate()` + `compute_spread_quartile()`) は `app.py:3879-3895` の **`compute_daytrade_signal`** path にのみ挿入
- Scalp signals は別関数 (`compute_scalp_signal` / `compute_scalp_signal_v2` 等) で処理 → R2-A gate を**構造的に通過しない**
- Production reasons log 0/107 件 ("R2-A suppress" 文字列出現なし) で実証

**意味**:
- Wave 1 (commit `f1cc1aa`, 2026-04-26) deploy 後 28h 経過しても **R2-A は一度も発動していない**
- U18 quartile fix (commit `e362254`) も同様、DT path にしか効果なし
- Wave 1 全体が **defensive 施策として最初から無効**

**Wave 1 deploy 時の implementation review error**:
当時の私の認識: "R2-A 4 cells はすべて DT/Scalp mode 戦略で swing path に該当戦略無し、入れても完全 no-op になるため deliberate に skip"
→ **誤認**: Scalp mode 戦略は Scalp path で処理される、DT path に gate 入れても通らない

### 2.2 Finding B: Wave2 A2/A3/A4 も全て 0 fires

3 changes (rule:R1-bypass commit `4df389f`) の deploy 後 28h で:
- **SL pip clamp**: 0/107 件 (trigger: SL < 3pip OR > 50pip on short TF)
- **Cost-aware Frequency Throttle**: 0/107 件 (trigger: friction > pair-baseline ×1.5)
- **Vol scale**: 0/107 件 (trigger: volatility regime 関連)

**可能性**:
1. trigger condition が rare で 28h では未発動
2. reasons log 文字列マッチング不一致 (実装と analysis script 間の string drift)
3. 実装上の bug (gate code が機能していない)

別 session の commits なので詳細調査は別 PR で実施。

### 2.3 Finding C: fib_promote 効果は N=4 で評価不能

C1-PROMOTE `fib_reversal × Tokyo × q0 × Scalp` (commit `7437e19` 0.05lot → `1467d7e` 0.01lot) の post-deploy:
- 4 件発火 (N≥30 の Wilson lower>50% 閾値の 13% のみ)
- outcome 詳細は production API で読み取り可能だが、**N=4 で causal inference 不可**

→ Cell-Audit Q1' next iteration (1-2 週間後) で再評価必要。

---

## 3. 月利 100% Roadmap への影響

### 3.1 Wave 1+2 の定量寄与: **ほぼゼロ**

当初想定: Wave 1+2 の defensive 施策で WR を 30% → 34-36% 程度押し上げ (gap +4-6pp 改善)。

実態: 
- R2-A: 構造的 no-op (U20)
- Wave2 A2/A3/A4: 0 fires (調査必要)
- fib_promote: N=4 で評価不能
- → **defensive 施策の roadmap 寄与は 0**

post-deploy WR 28.1% (N=96) は pre-deploy baseline ~30-39% から **悪化方向**、ただし Wilson 95% [19.7, 38.4] と CI 広く significant ではない。defensive 施策の "副作用" でもなく、natural variation の可能性。

### 3.2 Critical path の再評価

月利 100% gap (+20pp WR) を埋めるには:

1. ~~Wave 1+2 defensive 施策~~ → 構造的 no-op、貢献 0
2. **Phase 3 BT** (K=7 戦略 validation) → ζ +14d 待機、結果次第
3. **R-A pre-reg LOCK 2 戦略** (pullback_to_liquidity_v1, asia_range_fade_v1) → Phase 3 BT 検証後に Live 昇格
4. **Cell-Audit Q1' next iteration** → 1-2 週間後、追加 promote 候補
5. **Wave 3 mechanism-driven new strategies** (POC/VWAP/D1 H/L magnet level) → Phase 3 結果後の design

**Wave 1+2 が roadmap に貢献していない事実は、Phase 3 BT + Wave 3 が一層 critical** であることを意味する。

---

## 4. 即時 Action Items

### 4.1 U20 (Critical, 即時): R2-A gate を Scalp path にも追加

**修正範囲**: `app.py` の Scalp signal 関数 (compute_scalp_signal, compute_scalp_signal_v2 等) に R2-A gate 挿入。

**実装案**:
```python
# compute_scalp_signal_v2 (or other scalp paths) で confidence 計算後に
try:
    from modules.strategy_category import (
        apply_r2a_suppress_gate,
        compute_spread_quartile,
    )
    _pip_unit = 0.01 if "JPY" in symbol.upper() else 0.0001
    _spread_pips = _bt_spread(row.name, symbol) / _pip_unit
    _spread_q = compute_spread_quartile(_spread_pips, symbol)
    _conf_after = apply_r2a_suppress_gate(
        etype, session.get("name"), _spread_q, _conf_raw
    )
    if _conf_after != _conf_raw:
        reasons.append(f"⚠️ R2-A suppress ({etype}×{session.get('name')}×{_spread_q}): conf {_conf_raw}→{_conf_after}")
    _conf_raw = _conf_after
except Exception:
    pass
```

**注意**: U18 fix で USD_JPY q1/q2 cells が empty (cuts=[0.8,0.8,0.8]) のため、R2-A target cell `(Overlap, q2)` は U20 fix 後も該当 trade 0 件。`(London, q0)` `(Overlap, q0)` `(London, q3)` `(Tokyo, q3)` の 4 cells は機能するはず。

→ 別 session で R2-A gate を Scalp path に追加 + 効果再計測 (Phase γ' 等の追加 measurement window 設定)

### 4.2 Wave2 A2/A3/A4 trigger condition 調査

別 session の commit `4df389f` 内の SL pip clamp / cost throttle / vol scale の trigger condition と reasons log 出力を verify。production で 0 fires が bug なのか rare event なのかを切り分け。

### 4.3 Phase 3 BT 着手 timing 維持

Wave 1+2 が無効でも Phase 3 BT の technical readiness は変わらず CLOSED:
- K=7 universe 完全実装 (R-A)
- BT pipeline friction 伝播 (R-B)
- Pre-reg LOCK 不変

→ ζ +14d (2026-05-11) 着手 timing は維持。むしろ defensive 施策が無効なため、Phase 3 BT validation の重要性が増した。

### 4.4 Cell-Audit Q1' next iteration の独立性確保

Cell-Audit は Live data 直接利用、BT pipeline (R2-A gate) と独立。Q1' next iteration (~1-2 週間後) は Wave 1+2 の no-op 状態に依存しない。

---

## 5. 統計的 limitation 認識

本 measurement の限界:
- **N too small for treated cells** (0-4 件)、logit β estimates 不可能
- **Confounding period のため individual effect attribution 不可**
- **WR 28.1% (N=96)** は noise の範囲内、Wave 1+2 副作用の証拠ではない
- → measurement は **descriptive only**、causal claim 一切なし

Phase δ +72h, ε +7d, ζ +14d で N 蓄積を待ち、treatment indicator が正常に発火する状態 (U20 fix 後) で再計測必須。

---

## 6. 次セッション以降の優先度

| Priority | Task | Rationale |
|----------|------|-----------|
| **最高** | U20 修正 (Scalp path に R2-A gate 追加) | Wave 1 R2-A を機能させる、defensive 施策の前提 |
| 高 | Wave2 A2/A3/A4 trigger condition 調査 | 0 fires が bug か rare event か判定 |
| 高 | Phase γ' 再計測 (U20 fix 後の +24h で) | R2-A 実効果の初測定 |
| 中 | Phase 3 BT script Phase 2 (Rolling WFA) | 別 session で実装、ζ +14d までに完了 |
| 中 | deferred R-series (R3 + R5 + R7) | LOCK 外文書整備 |
| 低 | Cell-Audit Q1' next iteration | 1-2 週間後に自動 schedule |

---

## 7. References

- `tools/phase3_friction_e2e_smoke.py` (P4 finding source)
- `wave2-deconfounding-plan.md` (Phase γ logit 設計)
- `app.py:3879-3895` (R2-A gate insertion site, DT path のみ)
- `modules/strategy_category._R2A_SUPPRESS` (5 cells、すべて scalp mode 戦略)
- `strategies/scalp/{stoch_pullback,sr_channel_reversal,ema_trend_scalp,vol_surge}.py` (R2-A target 戦略 source)
- production API: `/api/demo/trades?limit=500&include_shadow=1` (post-deploy +28h trades)
- Master: `wiki/learning/fx-fundamentals.md` Section 6.4 → U20 追加候補
