# Realistic Roadmap Audit — 月利 100% 達成可能性 Quant 評価

**Session**: curried-ritchie (Wave 2 Day 7)
**Date**: 2026-04-27 ~16:00 JST
**Status**: 戦略レベル decision foundation
**Audit type**: 月利 100% target の数学的達成可能性 + alternative path 評価

> **Disclaimer**: 本 audit は LIVE PnL 改善目的、現状実測 + statistical theory ベース。各 scenario の confidence は明示する。

---

## 0. Executive Summary (Quant TL;DR)

**月利 100% は数学的に可能だが、retail FX × 単独 portfolio で 6-12 ヶ月以内達成は困難**。現実的 target:

| Target | 達成期間 | Confidence | 必要条件 |
|--------|----------|-------------|----------|
| **月利 30%** | 3-6 ヶ月 | 高 | Phase 3 BT で 1 戦略 promote |
| **月利 50%** | 6-12 ヶ月 | 中 | Phase 3 BT で 2-3 戦略 promote + Kelly Half scaling |
| **月利 100%** | 12-24 ヶ月 | 低-中 | Wave 3 新戦略 + multi-pair 拡張 + Sharpe 5+ maintained |
| **月利 100%+** | aspirational | 不確実 | 機関 hedge fund 一流レベル必要 |

**Quant 推奨**: **月利 50% を中期 target、月利 100% を long-term aspiration** に設定し、Phase 3 BT 結果次第で再評価。

---

## 1. 数学的監査

### 1.1 月利 100% に必要な 1-trade Kelly edge

```
複利前提: 月 +100% = 365 trades/月で各 trade 期待 +0.273%
Kelly Full = 25% (WR 50% × R:R 1:2 想定)
Kelly Half = 12.5%

balance に対し +12.5% per trade = mean +1.25%
Variance: std ≈ Kelly × √(p × (1-p) / N)
365 trades/月で expected balance grow:
  - μ = 0.0125, σ ≈ 0.18
  - Sharpe (per-trade) ≈ 0.069
  - Annual Sharpe (4175 trades/year) ≈ 0.069 × √4175 ≈ 4.46
```

→ **月利 100% を Kelly Half で実現するには Sharpe ~4.5 必要**。Sharpe 5 ならば月利 ~150%、Sharpe 3 ならば月利 ~50%。

### 1.2 Sharpe 5 の達成可能性

| Sharpe レベル | 例 | 達成難易度 |
|--------------|---|-----------|
| 1-2 | 個人 retail trader 平均的勝者 | 低 |
| 2-3 | 専業 retail / 機関 mid-tier | 中 |
| 3-5 | 機関 top-tier / hedge fund 平均 | 高 |
| 5-7 | 機関 top elite (Renaissance Medallion 等) | 極めて稀 |
| 7+ | 物理的天井? | 数年に一度 |

**現状 (Sharpe -4.74)** からの改善幅 +9.74 は **structural transformation** が必要。

### 1.3 Multiple alpha sources 必要量

単一戦略 Sharpe 2-3 を **multiple uncorrelated** で portfolio Sharpe 5+ に押し上げる:

```
Portfolio Sharpe (uncorrelated, equal weight) = √N × strategy Sharpe
N=4 戦略 Sharpe 2.5 each → portfolio Sharpe = 5.0
N=2 戦略 Sharpe 3.5 each → portfolio Sharpe = 4.95
```

→ **月利 100% には Sharpe 2.5+ × 4 戦略の uncorrelated portfolio**、または **Sharpe 3.5+ × 2 戦略**が必要。

現状 vol_momentum_scalp の Sharpe (per-trade 0.230, annualized ~14.9 — N=93 単一戦略) は outlier、N=5-10 の noise。

---

## 2. 現実的見積 (Realistic Estimate)

### 2.1 Phase 3 BT 後の survive 戦略 数

Pre-reg LOCK K=7 universe + Bonferroni α=0.00714:
- 楽観 estimate: 3 戦略 survive (pullback/asia_range/gbp_deep)
- 中庸 estimate: 2 戦略 (pre-reg 2 で 1, Tier-A で 1)
- 悲観 estimate: 1 戦略 (gbp_deep_pullback ELITE_LIVE 既存)

各 survivor の Live performance (~1-3 ヶ月の実測想定):
- WR 55-65% (Pre-reg LOCK の WR 50% threshold + buffer)
- R:R 1.2-1.8 (LOCK 仕様)
- Sharpe per-trade 0.05-0.15 → annualized 3-9

### 2.2 Portfolio leverage 推定

中庸 estimate (2 strategies survive):
```
Strategy A (gbp_deep_pullback): Sharpe 6 (annualized), WR 60%, R:R 1.5
Strategy B (pullback_to_liquidity_v1): Sharpe 4, WR 55%, R:R 2.0
Correlation 0.3-0.5 (両方 trend-aware 系)

Portfolio Sharpe ≈ 4-5 (correlation depends)
Portfolio Kelly Full ≈ 15-20%
Portfolio Kelly Half ≈ 7-10%
```

→ 月利 30-60% range が**現実的**な期待。月利 100% は楽観 (Sharpe 6+ maintained) で可能。

### 2.3 Time horizon

| Phase | 期間 | 累積 |
|-------|------|------|
| Phase 3 BT 実行 + 結果 | +14d (ζ) + 1-2 週間 | ~5-6 週間 |
| Live shadow N≥30 蓄積 (各戦略) | 1-3 ヶ月 | 2-5 ヶ月 |
| PAIR_PROMOTED 昇格 + Live N≥200 | 2-4 ヶ月 | 4-9 ヶ月 |
| Kelly Half lot scaling 完成 | 1-2 ヶ月 | 5-11 ヶ月 |
| Wave 3 新戦略 (必要なら) | 2-4 ヶ月 | 7-15 ヶ月 |

→ **月利 100% を確実に達成する path は 12-15 ヶ月**、楽観で 6-9 ヶ月。

---

## 3. Critical Path (達成必要条件 5 段階)

### Stage 1: Defensive 施策の機能化 (~1 ヶ月)

- ✅ U18 fix (BT pipeline) — DONE
- 🔧 **U20 fix (R2-A gate を Scalp path に追加)** — 本 session で実装
- 🔧 Wave2 A2/A3/A4 trigger 検証 — 別 session
- 期待効果: WR +2-4pp (loss prevention)

### Stage 2: Phase 3 BT validation (~5-6 週間)

- Phase 3 BT script Phase 2 (Rolling WFA + G1-G5 audit + aggregator) 実装 ~6h
- BT 実行: K=7 × WFA × Mode A/B = 28 runs ~80h wall-clock
- 結果評価 + 採用判定
- 期待: 1-3 戦略 survive

### Stage 3: Live promotion (1-3 ヶ月/戦略)

- Phase 3 survivor を shadow → Live N≥30 で再検証
- Wilson lower>50% 達成戦略のみ PAIR_PROMOTED
- Kelly Quarter (0.05 lot) で initial deploy
- N≥200 で full promote、Kelly Half (0.10-0.50 lot) scaling

### Stage 4: Multi-strategy portfolio (2-4 ヶ月)

- Promoted 戦略 2-3 の portfolio Kelly 計算
- Correlation matrix で実効自由度測定
- Per-strategy lot allocation 最適化
- Risk control automation (DD limit, MC ruin gate active)

### Stage 5: Alpha diversification (4-12 ヶ月)

- WEAK 13 戦略改造 (TAP-1 排除) → Phase 3 BT 候補追加
- Wave 3 新戦略 (POC/VWAP/D1 H/L magnet level) design + Pre-reg LOCK
- Multi-pair 拡張 (AUD/NZD/CHF)
- Multi-mode 拡張 (Swing TF 検討)
- Cell-Audit Q1' iteration (週 1 回 schedule)

---

## 4. Risk Factors (達成阻害)

### 4.1 Market regime change

- 2026-04 期間の market regime (USD/JPY 158-160) は static、regime change 時の戦略 robustness 不確実
- BOJ intervention, Fed pivot 等で trend regime が逆転すると Phase 3 BT validation のサンプルが invalidate

### 4.2 Sample size 限界

- 60 days passive accumulation で N=6800 想定だが、戦略 fire 頻度依存
- 実 fire は predicted の半分以下の可能性 (vol_momentum_scalp 1m が 5 trades/30 days = 60 trades/年)

### 4.3 Broker dynamic routing

- B-book → A-book flip on edge 回復 (Track ① §1.4 hidden risk)
- 月利達成局面で broker が toxic 認定 → fill quality 劣化
- Internalization 比率変化で実 PnL が BT から乖離

### 4.4 Sharpe 5 物理的天井

- 機関 hedge fund 一流レベル、retail で safely 達成可能か疑問
- vol_momentum_scalp PF=20.33 は N=5 noise、再現性疑わしい
- Sharpe maintained での lot scaling が DD 加速の risk

---

## 5. Alternative Path (月利 100% 困難な場合)

### Path A: Realistic mid-term target (月利 50%, 年利 600%)

- Phase 3 BT 後 2 戦略 promote 想定で実現可能
- Sharpe 3.5-4.5 で十分
- 6-9 ヶ月で達成期待
- 機関 mid-tier レベル、retail で realistic

### Path B: Conservative target (月利 30%, 年利 360%)

- 1 戦略 promote (gbp_deep_pullback 既存) で実現
- Sharpe 2.5-3.0 で十分
- 3-6 ヶ月で達成期待
- 確実性高、risk 低

### Path C: Aggressive aspirational (月利 100%+)

- Wave 3 新戦略多数 + multi-pair 拡張 + 高 Sharpe maintained
- 12-24 ヶ月、確実性低-中
- 物理的天井に近い、Sharpe 5+ 必須

---

## 6. Quant 推奨

### 6.1 Target 再設定 (recommended)

**3-tier scenario plan**:
- **Primary target**: 月利 50% (年利 600%)、6-12 ヶ月
- **Stretch target**: 月利 100% (年利 1200%)、12-18 ヶ月、Wave 3 新戦略前提
- **Floor target**: 月利 30% (年利 360%)、3-6 ヶ月、最低保証

CLAUDE.md "月利 100% を最優先目標" は維持しつつ、現実的 milestone として 50% を中継点に設定。

### 6.2 即時 actionable 優先度

**Phase 3 BT 着手前 (now ~ ζ +14d)**:
1. 🔴 U20 fix (compute_scalp_signal* に R2-A gate) — 本 session
2. 🔴 Wave2 A2/A3/A4 trigger 検証
3. 🟠 Phase 3 BT script Phase 2 実装 (~6h)
4. 🟡 deferred R-series (R3 + R5 + R7)

**Phase 3 BT 後 (ζ+14d 〜 1 ヶ月)**:
5. 🔴 Phase 3 BT 実行 + 結果評価
6. 🔴 Live shadow 蓄積 monitoring
7. 🟠 PAIR_PROMOTED 昇格判定

**Promote 後 (1-3 ヶ月)**:
8. 🔴 Portfolio Kelly + correlation 自動化 (modules/risk_analytics.py 既存活用)
9. 🟠 Wave 3 新戦略 design (Track ② §2.4)
10. 🟡 WEAK 13 戦略改造

### 6.3 Process discipline

- HARKing 防止: Pre-reg LOCK の規律 (BT data 観測前 commit) を継続
- Bonferroni / FDR 補正の継続適用
- Live N≥30 / Wilson lower>50% / hold-out validation の rigor
- 「KB は更新するもの、絶対のルールではない」(CLAUDE.md) — 新データで KB を更新する勇気

---

## 7. Conclusion

**月利 100% target は数学的に可能、retail で 12-15 ヶ月の long path**:
1. defensive 施策機能化 (U20 fix 等)
2. Phase 3 BT で K=7 universe 検証
3. Live promotion + Kelly Half lot scaling
4. Wave 3 新戦略で alpha diversification
5. Sharpe 5+ maintained × 12-15 ヶ月

**Realistic mid-term target = 月利 50%** (Phase 3 BT 2 戦略 survive で achievable)。

CLAUDE.md "月利 100% を最優先目標" は **long-term aspiration** として維持、**月利 50% を 6-12 ヶ月 milestone** に設定するのがクオンツ的に最適。

Phase 3 BT 結果が出るまで (ζ +14d + 1-2 週間 = ~5 週間後)、各 scenario の確率分布は不確実。**結果に応じて再 audit** 必要。

---

## 8. References

- Live data: production /api/demo/trades (N=373, post-deploy +28h)
- 数学根拠: Track ⑤ §5.4-5.6 (Bonferroni / Power calc)
- Pre-reg LOCK: `phase3-bt-pre-reg-lock.md` (commit `34c404c`)
- U20 finding: `wave2-phase-gamma-logit-result.md` (Wave 1 R2-A 構造的 no-op)
- CLAUDE.md "月利 100% を最優先目標、Kelly Half 到達の前提条件"
- KB roadmap: `knowledge-base/wiki/syntheses/roadmap-v2.1.md` (Phase 3 月利 594% BT 推定)
