# Pre-registration: Phase 4 — Regime-native Strategy Design (2026-04-23)

**Locked**: 2026-04-23 (本 doc 確定以降、binding criteria 変更禁止)
**Status (2026-04-23 updated)**: **DOWNSTREAM of
[[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]]**.
本 doc の D1-D4 candidate は adaptive classifier stability GO **かつ**
per-regime edge test の survivor-empty regime が特定された後にのみ authorize.
Upstream 優先理由はユーザー指摘 (2026-04-23): static strategy fitting は
現 regime snapshot への overfitting 危険、adaptive logic は overfitting 判定
機構が別 (classifier stability 検定) で処理できる。

**Scope**: 新戦略 design + backtest-level validation (no live deploy until pass)
**Prerequisite**: [[cell-level-scan-2026-04-23]] Scenario A 確定 +
                  [[pre-registration-phase4-adaptive-regime-classifier-2026-04-23]]
                  Phase B per-regime edge test 完了
**Data foundation**: [[regime-characterization-2026-04-23]]

## Purpose

Current regime (高 volatility + chop + directional edge消失) に対し、
既存 17 strategies の何れも cell レベルで生存しない ([[cell-level-scan-2026-04-23]])。
新戦略を **data-driven + pre-registered** で設計し、**既存戦略に対する
増分エッジ**が confirm できたものだけ shadow deploy する。

**NOT**: 月利100%目標への救済策として焦って live 追加する。
本 doc は **design discipline** の lock であり、code change の authorization
ではない。

## Candidate designs (D1-D4)

[[regime-characterization-2026-04-23]] §9 から以下 4 candidate:

| ID | Name | Hypothesis |
|----|------|-----------|
| D1 | vol_adaptive_sl | ATR-scaled SL/TP で SL hit rate 削減 |
| D2 | directional_persistence_filter | 連続 bar 方向一致 required, false positive 削減 |
| D3 | vol_spike_standdown | ATR > p90 時 entry 停止 (chop 帯回避) |
| D4 | vol_scaled_mean_reversion | BB ±2σ touch + ATR-wide SL での MR |

各 design は **独立 hypothesis** として扱う (M=4 for Bonferroni 下限)。

## Pre-registered workflow (per candidate)

各 candidate D<i> は以下 6-step を厳密に通る。Step 失敗時は該当 design 破棄。

### Step 1. Formalize hypothesis (design doc)

Create `wiki/strategies/<name>-design.md` with:
- Entry logic (疑似コードレベル)
- SL/TP 計算式 (パラメータ含む)
- Baseline comparison (どの既存戦略と比較するか)
- Expected edge magnitude (WR lift estimate, 理論根拠付き)

### Step 2. Pre-register BT thresholds

Create `wiki/analyses/pre-registration-<name>-bt-<date>.md` with **locked** criteria
BEFORE running BT:

**GO (shadow deploy 候補化)**:
1. 365-day BT: N ≥ 200
2. WR ≥ BEV_WR + 5pp (Wilson 95% lower も ≥ BEV_WR+2pp)
3. Walk-Forward 3-bucket で **全 bucket positive EV** (regime robustness)
4. Profit Factor ≥ 1.2
5. Kelly ≥ 0.10 (full, BT_COST=1.0 適用後)
6. Bonferroni 補正: Fisher vs pooled baseline p < 0.0125 (α=0.05/4)

**NO-GO**: 上記いずれか 1 項 fail → design 破棄、lessons に記録

### Step 3. BT execution (code change allowed)

- 新戦略を backtest-mode で実装 (production signal 関数に `backtest_mode=True` 経路)
- 既存 BT ハーネス (`tools/backtest.py` 相当) で 365-day BT
- Output: `raw/bt-results/<name>-<date>.json`

**Note**: BT 実装コード変更はこの step で初めて allow。production signal logic は
backtest_mode 分岐で完全再利用すること (CLAUDE.md rule)。

### Step 4. Shadow deploy (Step 2 GO 通過のみ)

- `entry_type=<name>` で shadow 有効化 (live-weight=0)
- **Pre-register shadow GO criteria**: 14d で N≥30, WR ≥ BT WR - 10pp, Wilson 下限 > BEV
- 違反時 shadow 停止、design 再設計 or 破棄

### Step 5. Live-weight graduation (PAIR_PROMOTED)

既存 promotion harness に従う. 本 doc では new constraint なし。

### Step 6. Post-deploy audit

promotion 30d 後、再監査 ([[feedback_partial_quant_trap]] Audit B pattern):
- N, WR, PF, Wilson CI を現数値で再計算
- 劣化 > 10pp → PAIR_DEMOTED

## Non-binding design constraints (guidance)

これらは hard criteria ではないが設計時に考慮:

- **信号頻度**: pair/day ≥ 1 (低頻度は N 蓄積遅い)
- **average holding time**: < 60 min (intraday 戦略方針)
- **max concurrent positions**: ≤ 2 (margin 制約)
- **correlation with existing strategies**: Spearman ρ < 0.5 vs 既存 top
  winners (redundancy 回避) — ただし既存に生存者なしのため実質緩い

## Disallowed

以下は Phase 4 実装中に発見しても design 変更に使えない:

- **BT 結果を見てから threshold 緩和** (post-hoc bias)
- **パラメータ sweep 後の best picking** (curve fitting; CLAUDE.md 禁止)
- **小-N (N<200) での shadow 昇格正当化**
- **既存戦略の parameter fine-tuning による"救済"** (本 Phase の scope 外)
- **label 追加による cosmetic change** (Phase 1 holdout scope)

## Risk guardrails

本 Phase 4 進行中も以下を **同時進行で** 維持:

1. **[[pre-registration-label-holdout-2026-05-07]] 通り holdout 実行**
   - Phase 4 は Phase 1 holdout を blocking しない (並行可)
2. **live-weight 現状維持** (Phase 4 shadow 結果が出るまで既存構成不変)
3. **CLAUDE.md 4 原則遵守**: 攻撃優先、静的時間ブロック禁止、Spread/SL Gate のみ

## Sequencing

推奨順序 (各 design 独立だが dependency あり):

1. **D3 (vol_spike_standdown)** — 既存戦略への gate、design 最小、data 再利用
2. **D1 (vol_adaptive_sl)** — SL/TP 計算の parameterization 変更、既存戦略横断適用
3. **D2 (directional_persistence_filter)** — entry 側 filter、M の再計上必要
4. **D4 (vol_scaled_mean_reversion)** — 全く新 entry_type、最も大きい投資

D3/D1 は既存戦略の risk 側改修で "攻める" を維持。D2/D4 は新 strategy。

## Authorized scope

次セッション以降 (本 session では design スタートのみ):
- **Step 1 (formalize)** は code change 不要 → 本 session で着手可
- **Step 3 (BT execution)** は別 session で。365-day BT は時間かかる
- **Step 4 (shadow deploy)** は Step 2 GO 確認後のみ

本 session では **D3 から Step 1** に入ることを提案。

## Accountability

**事前約束**:
- BT 結果が微妙に届かない場合 (例: Kelly=0.09) でも threshold を緩めない
- 複数 design 同時進行時 Bonferroni M=4 を崩さない
- 「時間がないから shadow スキップ」しない
- 失敗 design は `wiki/lessons/` に記録 (学習資産化)

## References

- [[regime-characterization-2026-04-23]] (Phase 4 data foundation)
- [[cell-level-scan-2026-04-23]] (Scenario A 確定)
- [[pre-registration-phase2-cell-level-2026-04-23]] (同じ pre-reg 方式)
- [[pre-registration-label-holdout-2026-05-07]] (並行進行)
- [[lesson-premature-neutralization-2026-04-23]]
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
- CLAUDE.md 4 原則
