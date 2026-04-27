# Phase 3 BT × Cell-Audit Q1' Coordination Plan (LOCK 外 supplementary)

**Session**: curried-ritchie (Wave 2 Day 5)
**Date**: 2026-04-27 14:55 JST
**Status**: LOCK 外 supplementary、修正可能
**LOCK 文書**: `phase3-bt-pre-reg-lock.md` (commit `34c404c`、不変)
**目的**: Phase 3 BT (strategy-level K=7) と Cell-Audit Q1' (cell-level) 並行 track の **multiple testing 整合性確保** + family-wise error rate 制御

---

## 0. Executive Summary (Quant TL;DR)

Phase 3 BT と Cell-Audit Q1' は **独立 hypothesis space** で動作 (overlap 戦略は U11 audit で WEAK/NONE 除外済)。両 track の multiple testing は **Option B: 独立 LOCK 管理** が Quant 推奨。

- Phase 3 BT: K=7 strategy-level, Bonferroni α=0.00714 (LOCK)
- Cell-Audit Q1': K_cell=9 cell-level, Bonferroni α=0.0056 (Q1' design)
- Joint K=16 conservative (α=0.0031) は power 不足、独立保持で responsibility / reproducibility 分離
- **P4 finding 影響**: Phase 3 BT Mode A/B 比較は `_bt_spread()` 改修まで保留、Cell-Audit Q1' は影響なし (live data 直接利用)

---

## 1. Background (両 track の概要)

### 1.1 Phase 3 BT (strategy-level)

- 出典: `phase3-bt-pre-reg-lock.md` (commit `34c404c`)
- Universe: K=7 戦略 (pullback_to_liquidity_v1, asia_range_fade_v1, gbp_deep_pullback, vol_momentum_scalp, htf_false_breakout, liquidity_sweep, london_fix_reversal)
- 検定: Bonferroni α=0.00714 (confirmatory) + FDR q=0.10 (exploratory)
- 母集団: 2025-01〜2026-04 BT trade data (Anchored WFA)
- 採用判定: PAIR_PROMOTED (Live N≥30 + Wilson lower>BEV + Bonferroni p<0.00714)

### 1.2 Cell-Audit Q1' (cell-level)

- 出典: `tools/cell_edge_audit.py`, `raw/audits/cell_edge_audit_2026-04-27_inclshadow.md`
- Universe: 全戦略 × session × spread quartile × mode の cell 全集合、N≥10 で qualified
- 検定: Bonferroni 補正 (K_cell=9 qualified cells, α=0.0056)
- 母集団: `demo_trades.db` (Live + Shadow) 直近 trades
- 採用判定: C1-PROMOTE (Wilson lower>50% AND Bonferroni p<0.05)、C2-SUPPRESS (Wilson upper<baseline AND Bonferroni p<0.05)

### 1.3 現 Cell-Audit Q1' 結果

**C1-PROMOTE 1 件**:
- `fib_reversal × Tokyo × q0 × Scalp`: N=24 WR=87.5% Wilson [69.0, 95.7] EV=+10.82 PF=14.60 p_Bonf=0.0022 → Live 0.05→0.01 lot 昇格 (commits `7437e19`, `1467d7e`)

**C2-SUPPRESS 2 件**:
- `ema_trend_scalp × London × q0 × Scalp`: N=21 WR=14.3% p_Bonf=0.0096 → 既 Wave 1 R2-A 登録
- `ema_trend_scalp × Overlap × q0 × Scalp`: N=28 WR=17.9% p_Bonf=0.0060 → C2-SUPPRESS 追加 (commit `795d4af`)

---

## 2. Hypothesis Space Overlap 分析

### 2.1 K=7 Phase 3 universe vs Cell-Audit Q1' universe

| 戦略 (Cell-Audit qualified) | U11 audit | Phase 3 BT K=7 包含 | 重複 risk |
|------------------------------|-----------|----------------------|-----------|
| `fib_reversal` (q0 Tokyo Scalp) | **WEAK** | ❌ NOT included | 重複なし (Phase 3 は WEAK 除外) |
| `bb_rsi_reversion` (q0 Tokyo/London) | **WEAK** | ❌ NOT included | 重複なし |
| `ema_trend_scalp` (q0 全 session) | **NONE** | ❌ NOT included | 重複なし |
| `sr_fib_confluence` (q0 London) | **NONE** | ❌ NOT included | 重複なし |
| `vol_surge_detector` (q0 Tokyo) | (audit 外) | ❌ NOT included | 重複なし |

→ **両 track の戦略集合は完全 disjoint**。Phase 3 BT の VALID 11 (orb_trap, gbp_deep_pullback 等) は Cell-Audit Q1' qualified 9 cells と重複なし。

### 2.2 Implication

両 track は **独立な hypothesis space**:
- Phase 3 BT: VALID 戦略の robustness (mechanism thesis 強度) を検証
- Cell-Audit Q1': WEAK/NONE 戦略の cell-level edge / negative-edge 抽出

→ **multiple testing の cross-contamination リスクは構造的に低い**。

---

## 3. Joint FWER 制御の選択肢

### 3.1 Option A (Conservative): K_joint = 16 で Bonferroni 再補正

```
α_joint = 0.05 / 16 = 0.003125
```

**Pros**:
- Family-wise error rate 厳格 (両 track 全体で α≤0.05)
- Quant rigor 教科書通り

**Cons**:
- Detectable ΔWR 大幅悪化: N=259 で K=7 → 9.98pp、K=16 → 12.07pp (約 +2pp 悪化)
- Power 不足で marginal edge を見逃すリスク
- Phase 3 BT と Cell-Audit Q1' の責任主体・タイミング異なるのに統一 LOCK が困難

### 3.2 Option B (Independent): 各 track 独立 LOCK 維持 (Quant 推奨)

- Phase 3 BT: K=7 の Bonferroni LOCK 維持 (α=0.00714)
- Cell-Audit Q1': K_cell の Bonferroni LOCK 維持 (α=0.0056)
- **両者を別 Pre-reg LOCK として扱い、joint K 補正は適用しない**

**Pros**:
- Power 維持 (各 track の detectable effect size を犠牲にしない)
- 責任 / 再現性 分離 (各 LOCK が独立に audit 可能)
- **Disjoint hypothesis space** であるため joint FWER の問題が構造的に小さい
- Phase 3 BT 結果と Cell-Audit Q1' 結果の **temporal independence** で auto-correction (各 LOCK が異なる時期に発行)

**Cons**:
- 厳密な multiple testing rigor 要件としては緩い (joint α が 0.05 を超える可能性)
- Cell-Audit Q1' 結果が Phase 3 BT 採用判定に影響する場合は追加検討必要

### 3.3 Option C (Hybrid): Phase 3 BT 完了後の new LOCK で統合

- 中間期 (現在 〜 Phase 3 BT 完了): Option B 独立運用
- Phase 3 BT 完了後: 両 track 結果を統合した new Pre-reg LOCK で full universe を確定
- new LOCK で Bonferroni K_joint = (Phase 3 BT survivor 数 + Cell-Audit promote 数) で再補正

**Pros**: 短期 power 維持 + 長期 rigor 統合
**Cons**: new LOCK 発行 timing の判断が必要

### 3.4 Quant 推奨: Option B (現状) → Option C (Phase 3 BT 完了後)

理由:
1. **Hypothesis space disjoint**: Joint FWER concern が構造的に minor
2. **Power preservation**: Option A は detection power 悪化が大きい (N=259 で +2pp ΔWR 悪化)
3. **Responsibility separation**: 各 track の LOCK responsibility と timing が独立
4. **Long-term integration**: Phase 3 BT 完了後の new LOCK で Option C に格上げで rigor も担保

---

## 4. Cell-Audit Q1' Hold-out Validation (生 data 期間)

### 4.1 Phase 3 BT hold-out との関係

LOCK 文書 §7.3 Hold-out validation set: **2026-05-01 以降の forward-walking data**。

Cell-Audit Q1' で promote した cells (`fib_reversal × Tokyo × q0 × Scalp`) も同 hold-out 期間で再検証。

### 4.2 Hold-out 検定 schedule

| Cell | Promote date | Hold-out start | N≥30 期待 timing |
|------|---------------|----------------|------------------|
| `fib_reversal × Tokyo × q0 × Scalp` | 2026-04-27 (commit `7437e19`) | 2026-05-01 | +14-21 days (Tokyo Scalp 発火頻度依存) |

### 4.3 Holdout 失敗時の規律

- N≥30 で Wilson lower<50% に劣化 → Live 0.01 lot を停止 (Rule 2 Fast & Reactive)
- LOCK 不変、Cell-Audit Q1' next iteration で再検定
- Phase 3 BT 結果と独立に判定

---

## 5. P4 Finding の本 coordination への影響 (Cross-reference)

[`p4-friction-pipeline-discovery.md`](p4-friction-pipeline-discovery.md) で発見された:
> Phase 3 BT Mode A/B 比較は `_bt_spread()` 改修まで実装的に成立しない。

本 coordination 文書への impact:

- Phase 3 BT 着手 timing が **後ろ倒し**: `_bt_spread()` 改修 (2-4h) + smoke test 再実行 + ζ (+14d) 待機
- Cell-Audit Q1' は影響なし (Live data 直接利用、BT pipeline 関与なし)
- Cell-Audit Q1' next iteration は scheduled 通り 1-2 週間後に実行可能
- → 両 track の **timing decoupling** が一層明確に

---

## 6. Action Items

### 6.1 即時 (本 session)

- [x] 本 coordination 文書作成
- [x] [`p4-friction-pipeline-discovery.md`](p4-friction-pipeline-discovery.md) 作成
- [ ] supplementary doc (`phase3-bt-supplementary-2026-04-27.md`) §6 として coordination summary 追記
- [ ] mirror to fx-ai-trader/knowledge-base/wiki/learning/
- [ ] commit + push (LOCK 不変、supplementary 文書のみ更新)

### 6.2 別 session (Phase 3 BT 着手前)

- [ ] **`_bt_spread()` session multiplier-aware 改修** (2-4h, P4 finding 由来)
- [ ] P4 smoke test 再実行で PASS 確認
- [ ] Cell-Audit Q1' next iteration (~1-2 週間後)、`fib_reversal × Tokyo × q0 × Scalp` の hold-out N≥30 評価

### 6.3 Phase 3 BT 完了後 (Wave 4+)

- [ ] new Pre-reg LOCK 発行で Option C (両 track 統合) に格上げ
- [ ] Live universe 確定 (Phase 3 BT survivors + Cell-Audit promotes の joint Bonferroni)

---

## 7. Quant Rigor Status (本 supplementary 完了で gate 状況)

| Gate | Status | 備考 |
|------|--------|------|
| Pre-reg LOCK formal design | CLOSED ✅ | LOCK terms 不変 |
| R6 friction_for() unit verify | CLOSED ✅ | passed |
| **P4 BT pipeline end-to-end** | 🚨 **FAIL** | `_bt_spread()` 改修必要 (別 session) |
| **P3 Phase 3 × Cell-Audit coordination** | **CLOSED ✅** | **本文書、Option B 推奨** |
| Phase 3 BT script Phase 1 | CLOSED ✅ | 470 tests pass |
| Wave 1+2 effect 計測 | 計測中 | β +12h, γ +24h, ζ +14d |
| **Phase 3 BT 着手** | **延期** | P4 改修完了 + ζ +14d 達成後 |

---

## 8. References

- LOCK 文書 (不変): `phase3-bt-pre-reg-lock.md` (commit `34c404c`)
- Phase 3 BT supplementary: `phase3-bt-supplementary-2026-04-27.md`
- P4 finding: [`p4-friction-pipeline-discovery.md`](p4-friction-pipeline-discovery.md)
- Cell-Audit Q1' 出力: `raw/audits/cell_edge_audit_2026-04-27_inclshadow.md`
- Cell-Audit Q1' implementation: `tools/cell_edge_audit.py`
- Pre-reg-cell-promotion LOCK: `knowledge-base/wiki/decisions/pre-reg-cell-promotion-2026-04-27.md`
- U11 audit: [`u11-mechanism-audit-aggregate.md`](u11-mechanism-audit-aggregate.md) (両 track の overlap 分析)
- Master: [`fx-fundamentals.md`](fx-fundamentals.md) Section 6.4 (U18, future Cell-Audit U19 候補)
