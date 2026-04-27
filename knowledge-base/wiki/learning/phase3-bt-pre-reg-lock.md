# Phase 3 BT Pre-Registration LOCK Document

**Session**: curried-ritchie (Wave 2 Day 2 Quant Rigor)
**LOCK Date**: 2026-04-27 JST early morning (= 2026-04-26 PM UTC)
**LOCK Method**: git commit + push (時刻署名), commit hash で BT data 観測前を証明
**目的**: Phase 3 BT の HARKing / post-hoc 調整リスクを構造的に排除

> **🔒 LOCK 規律**: 本文書は BT data を見る前に固定する。BT 実行後に文書内容を変更するのは禁止。NULL 結果でも「成功するまでやる」原則 (memory) に従い、変更は次 Pre-reg LOCK で別仮説を立てて実施。

---

## 0. Executive Summary (Quant TL;DR)

Phase 3 BT は **K=7 Option-B 戦略 universe** を **Anchored + Rolling WFA × Mode A/B friction × G1-G5 gate** で評価し、Bonferroni α=0.00714 で確認的判定を行う。

### Decision Matrix (LOCK 済)

| 項目 | LOCK 値 |
|------|---------|
| **Strategy universe (K)** | **7 戦略 (Option-B)** |
| **Multiple testing correction** | Bonferroni α/K=0.00714 (confirmatory) + FDR q=0.10 (exploratory sub-cell) |
| **Walk-Forward Analysis** | Anchored (long-term) + Rolling 6m IS / 1m OOS (regime) 両方適用 |
| **Friction model** | Mode A (現 multiplier) + Mode B (U13/U14 calibrated) 両方で BT |
| **G1-G5 Gate** | 全戦略に事前適用、不適合は除外候補 |
| **Live 昇格基準** | Live N≥30 + Wilson 95% lower > BEV + Bonferroni p<0.00714 |
| **Live full promote** | Live N≥200 + Wilson 95% lower > 50% + WFA OOS Sharpe > 1.0 |
| **Hold-out validation** | 2026-05-01 以降の forward-walking data |

---

## 1. Strategy Universe (K=7 Option-B)

### 1.1 採用戦略リスト (LOCK)

Pre-reg 2 + Tier-A 5 = **計 7 戦略**:

| # | 戦略 | Category | Mode | 現 Tier | Audit verdict (U11) |
|---|------|----------|------|---------|---------------------|
| 1 | **pullback_to_liquidity_v1** | TF/SMC | DT | pre-reg LOCK 既設 | (新規、別 pre-reg) |
| 2 | **asia_range_fade_v1** | MR | DT | pre-reg LOCK 既設 | (新規、別 pre-reg) |
| 3 | **gbp_deep_pullback** | TF | DT | ELITE_LIVE | VALID |
| 4 | **vol_momentum_scalp** | TF | Scalp | PAIR_PROMOTED EUR_JPY | VALID + U3 deep dive 完了 |
| 5 | **htf_false_breakout** | MR/SMC | DT | Shadow | VALID |
| 6 | **liquidity_sweep** | BR | DT | UNIVERSAL_SENTINEL | VALID (Track ② §2.4 magnet level 補填) |
| 7 | **london_fix_reversal** | MR | DT | PAIR_DEMOTED USDJPY | VALID (Krohn 2024 macroflow) |

### 1.2 Universe 選択根拠 (Bonferroni 数学)

scipy.stats で計算 (baseline WR=39%, β=0.20):

| K | α/K | N=259 | N=500 | N=1000 |
|---|-----|-------|-------|--------|
| 2 (pre-reg のみ) | 0.0250 | 8.49pp | 6.11pp | 4.32pp |
| 5 | 0.0100 | 9.60 | 6.91 | 4.89 |
| **7 (Option-B)** | **0.00714** | **9.98** | **7.18** | **5.08** |
| 11 (全 VALID) | 0.00455 | 10.46 | 7.53 | 5.32 |

**Quant 判定**:
- K=11 vs K=2 の cost は N=259 で +1.97pp、N=1000 で +1.00pp
- N=259 で K=11 は実用上ほぼ不可能 (10.46pp 以上の effect 要求)
- **K=7 (Option-B) が均衡点**: ELITE_LIVE 既設の baseline と新 pre-reg LOCK を同時検証可能、cost 許容範囲

### 1.3 除外戦略

#### Tier-B 5 戦略 (Phase 3 から除外、Wave 3 候補)

- adx_trend_continuation: VALID だが Live N=0、Shadow データ蓄積優先
- gold_trend_momentum: XAU 特化、U17 で XAU 停止と整合しない
- jpy_basket_trend: Shadow のみ、basket proxy で間接
- alpha_atr_regime_break: FORCE_DEMOTED、KB wiki page 未作成
- london_breakout: Scalp Shadow、N 不明

→ Wave 3 で Shadow N≥30 蓄積後に追加検討

#### Tier-C 1 戦略

- orb_trap: VALID だが Live N=2-5 で N 不足、独立検定不能

→ shadow データ蓄積後に再評価

#### WEAK 13 戦略

- 改造後 BT 検証が必要、Wave 4+ で別 Pre-reg LOCK

#### NONE 8 戦略

- 除外確定、Phase 1.5 で registry housekeeping

---

## 2. Multiple Testing Correction

### 2.1 Confirmatory test (Bonferroni)

- **適用範囲**: 戦略採用判定 (K=7)
- **α_corrected**: 0.05 / 7 = **0.00714**
- **Z-critical (one-sided)**: 2.451 (vs Z=1.645 for K=1)
- **β=0.20 (Power=0.80)**: standard
- **判定**: Bonferroni-corrected p < 0.00714 で initial 採用候補

### 2.2 Exploratory test (FDR Benjamini-Hochberg)

- **適用範囲**: sub-cell 探索 (R2-B boost 候補等、Phase 4d-II 流れ)
- **q (FDR)**: 0.10
- **判定**: BH-rejected null hypotheses で descriptive boost 候補
- **Action**: confidence × 1.2 のみ許可、lot 増設は禁止 (Track ② §2.9 R2-B 設計)

### 2.3 Confirmatory / Exploratory 区別の重要性

- Confirmatory tests は **戦略採用** = Live 損失リスクのため Bonferroni FWER strictly < α
- Exploratory tests は **次の Pre-reg LOCK 仮説候補** = false discovery を許容しつつ pattern を発見
- 混同するとサーベイランスバイアスや HARKing リスク

---

## 3. Walk-Forward Analysis (WFA) Design

### 3.1 Anchored WFA (long-term validity)

- **IS (In-Sample)**: 2025-01-01 〜 2025-09-30 (9 months)
- **OOS (Out-of-Sample)**: 2025-10-01 〜 2026-04-26 (~7 months)
- **目的**: 戦略の long-term stationarity 検証

**評価指標**:
- OOS EV / IS EV ≥ 0.50 (degradation < 50%)
- OOS Sharpe > 0
- OOS WR within ±5pp of IS WR

### 3.2 Rolling WFA (regime adaptability)

- **IS window**: 6 months rolling
- **OOS window**: 1 month
- **Step**: 1 month
- **Total steps**: 18 (2025-01〜2026-04 で計算可能)

**評価指標**:
- 各 step の OOS EV を時系列でプロット
- median(OOS EV) > 0
- std(OOS EV) / |mean(OOS EV)| < 1.5 (安定性)
- regime change point (COVID, BOJ intervention 等) 前後の WR 急変なし

### 3.3 戦略別 WFA 適用

| 戦略 | Anchored | Rolling | 理由 |
|------|----------|---------|------|
| pullback_to_liquidity_v1 | ✅ | ✅ | 両方適用、TF dependence |
| asia_range_fade_v1 | ✅ | ✅ | range regime 依存 → Rolling 重要 |
| gbp_deep_pullback | ✅ | ✅ | trend regime 依存 → Rolling 重要 |
| vol_momentum_scalp | ✅ | △ | session 切替時依存、Anchored で十分 |
| htf_false_breakout | ✅ | ✅ | 全 regime で BT 必要 |
| liquidity_sweep | ✅ | ✅ | session boundary、Rolling 重要 |
| london_fix_reversal | ✅ | △ | macroflow timing、Anchored 主体 |

→ 7 戦略 × 1-2 WFA mode = **約 12-14 BT 実行**が Phase 3 BT 本体の規模

---

## 4. Friction Model Selection (Mode A vs Mode B)

### 4.1 Mode A: 現 status quo

`modules/friction_model_v2.py` 現値 (`_SESSION_MULTIPLIER`):
- London 1.00, NY 1.20, Tokyo 1.45, overlap_LN 0.85, default 1.10

### 4.2 Mode B: U13/U14 calibrated

[u13-u14-friction-calibration.md](u13-u14-friction-calibration.md) で N≥30 4 cells から導出:
- London **0.85** (1.00→0.85, EUR_USD/London 0.77 fit)
- Tokyo **0.80** (1.45→0.80, USD_JPY/Tokyo 0.78 fit) ← CRITICAL halve
- NY 1.20 (KEEP, N<30 不足)
- overlap_LN 0.85 (KEEP, 実測 1.005×)

### 4.3 BT design

全 7 戦略 × Anchored + Rolling × Mode A + Mode B = **計 28 BT 実行**を実施。

**Best-fit 採用ロジック**:
1. 各戦略 × Mode で OOS Sharpe / EV degradation 計測
2. Live N≥30 観測値 (post-cutoff Live) と各 Mode の OOS EV を AIC/BIC で比較
3. 戦略ごとに best-fit Mode を採用 (戦略単位の Mode 選択を許容)
4. ただし pair × session friction の共通基盤として system-wide で Mode A or B のどちらかを default に LOCK (戦略ごとに分岐させない)

**default Mode 決定**: 7 戦略中で過半数 (4+) が支持する Mode を default に。

---

## 5. G1-G5 Gate (vol_momentum_scalp deep dive 由来)

各戦略について Phase 3 BT 着手前に gate check:

### G1: Anti-TAP Filter Stack

- TAP-1 (中間帯 RSI/Stoch + AND filter): 不在
- TAP-2 (N-bar pattern): 不在
- TAP-3 (直前 candle 単独): 不在

### G2: Multi-Filter Gate (5+ 段階)

- Level 1: pair whitelist (BT-validated EV positive)
- Level 2: session block (BT-validated EV negative 排除)
- Level 3: regime filter (ADX/vol/trend 閾値)
- Level 4: trigger condition (extreme threshold)
- Level 5: confirmation (candle body / cross / break)

### G3: Asymmetric Exit Mechanics (system-level)

- TP / SL ATR-based (TP > SL)
- TIME_DECAY_EXIT 標準装備
- MAX_HOLD_TIME 標準装備
- SIGNAL_REVERSE 即応 close

### G4: BT-Validated Pair × Session Whitelist

- 全 enabled pair × session で 365 日 BT EV ≥ 0
- Wilson lower 35%+ で baseline-positive

### G5: Instant Death Rate Benchmark

- Wilson 95% lower での mafe_favorable=0 比率 ≤ 20%
- vol_momentum_scalp benchmark (0%)、bb_rsi_reversion 反例 (77.6%)

### 戦略別 G1-G5 適合性 (事前 audit)

| 戦略 | G1 | G2 | G3 | G4 | G5 |
|------|----|----|----|----|----|
| pullback_to_liquidity_v1 | ✓ (rejection wick≥0.4) | ✓ HTF+M15+wick+RR | ✓ system | TBD | TBD |
| asia_range_fade_v1 | ✓ (range touch+rejection) | ✓ UTC+vol+touch+rejection | ✓ system | TBD | TBD |
| gbp_deep_pullback | △ (BB%b+RSI軽 TAP-1) | ✓ ペア限定+ADX+EMA+pullback+confirm | ✓ system | ✓ ELITE_LIVE | TBD |
| vol_momentum_scalp | ✓ | ✓ 5 段 | ✓ system | ✓ 4 pair × session whitelist | ✓ 0% benchmark |
| htf_false_breakout | ✓ (TAP不在) | ✓ SR+break+retest+EMA | ✓ system | △ Shadow N<10 | TBD |
| liquidity_sweep | ✓ (Williams Fractal+wick≥60%) | ✓ Fractal+sweep+regime+session | ✓ system | △ N=0 | TBD |
| london_fix_reversal | ✓ (TAP不在) | ✓ time+pre-fix+post-fix+HTF+RR | ✓ system | △ PAIR_DEMOTED | TBD |

**Gate 不適合**: gbp_deep_pullback の G1 軽 TAP-1 を Phase 3 BT で **Mode A/B で別途検証**、改造 trigger になるか確認。

---

## 6. 採用判定基準 (LOCK)

### 6.1 PAIR_PROMOTED 昇格 (Phase 3 BT 後)

**全条件 AND**:
- Live N ≥ 30
- Wilson 95% lower > BEV (pair-specific, friction-analysis.md per-pair BEV)
- Bonferroni-corrected p < 0.00714 (K=7)
- WFA Anchored OOS EV / IS EV ≥ 0.50

### 6.2 ELITE_LIVE / Live full promote (long-term)

**全条件 AND**:
- Live N ≥ 200
- Wilson 95% lower > 50%
- WFA Rolling median OOS Sharpe > 1.0
- WFA Rolling std / |mean| < 1.5
- Hold-out validation set (2026-05-01 以降) で 同等 EV

### 6.3 NULL / 除外

**いずれか**:
- 365 日 BT EV < 0
- WFA Anchored OOS degradation > 50%
- WFA Rolling median Sharpe ≤ 0
- G1-G5 不適合かつ改造案なし

---

## 7. HARKing 防止 Protocol

### 7.1 Pre-reg LOCK 時刻署名

- 本文書を **commit + push (git)** で時刻署名
- commit hash が BT 実行前を証明
- BT data を見てからの文書内容変更は **絶対禁止**

### 7.2 Re-fit 禁止規律

- IS で best-fit パラメータ最適化
- OOS で **再最適化禁止** (既知の overfitting 防止)
- パラメータ変更が必要なら **次の Pre-reg LOCK** で新仮説として LOCK

### 7.3 Hold-out validation set

- 2026-05-01 以降の forward-walking data を **最終 gate** に
- IS/OOS で通過しても hold-out で同等 EV が出ないと promote しない
- Hold-out 期間は最低 30 days (1 trading month)

### 7.4 NULL 結果の扱い

- BT NULL ならば戦略を即除外、パラメータ調整は禁止
- 「成功するまでやる」原則 (memory feedback_success_until_achieved) は **次 Pre-reg LOCK で別仮説**を意味し、本 LOCK の条件変更ではない
- NULL の構造的説明 (Track ⑤ §5.6: "edge 不在" vs "未検出") を Phase 3 結果文書化時に明記

### 7.5 Sub-cell 探索の制限

- Bonferroni K=7 を超える sub-cell 探索 (戦略 × pair × session × regime 等) は exploratory のみ
- exploratory 結果は次 Pre-reg LOCK 仮説の input、本 BT の判定には使用しない

---

## 8. Phase 3 BT 実行 timeline (推定)

| Phase | Action | 工数 | dependency |
|-------|--------|------|------------|
| Pre-BT 1 | Pre-reg LOCK 文書 commit (本文書) | 30 min | なし |
| Pre-BT 2 | Phase 3 BT script 整備 (`tools/phase3_bt.py`) | 1-2 days | Pre-BT 1 |
| Pre-BT 3 | Friction Mode A/B 切り替え機構 | 4 hours | Pre-BT 2 |
| BT 本体 | 7 戦略 × Anchored + Rolling × Mode A/B = 28 runs | 2-3 days (1 run ~ 2-3h × 28) | Pre-BT 3 |
| Post-BT 1 | 結果集約 + Bonferroni / FDR 判定 | 1 day | BT 本体 |
| Post-BT 2 | Hold-out validation 開始 (passive) | 30+ days | Post-BT 1 |
| Post-BT 3 | promote 判定 + KB 文書化 | 1 day | Post-BT 2 |

**Phase 3 BT 本体合計**: 約 **2 週間 + Hold-out 30+ days** = 約 **6-8 週間**で完了見込み

---

## 9. 残課題 / 接続

### 9.1 Pre-reg LOCK 時点の残未解決

- **U18 (spread quintile mismatch)**: Wave 1 R2-A の Phase 4d-II との実装乖離。Phase 3 設計には直接影響しないが、Wave 1 効果計測の解釈に影響
- **U13/U14 final calibration**: Mode B multiplier は現 4 cells (N≥30) のみベース、60 days passive 蓄積後の最終 calibration が望ましい
- **vol_surge_detector baseline**: Phase 4d-II で baseline 不明、Phase 3 BT で再分析必要

> **Note (2026-04-27 R1 revision)**: 当初本セクションに §9.1.bis として "Multi-Change Confounded Period" の判断 (Phase 3 BT timing ε → ζ 延期、Bonferroni K joint=12、4-arm BT design 等) を追記したが、これは **BT data 観測前に LOCK terms を変更する HARKing pattern** に該当するため revert。LOCK 文書外の補足記録として `phase3-bt-supplementary-2026-04-27.md` を別途作成。本 LOCK §6 採用基準 (K=7, α=0.00714, WFA dates, G1-G5) は **Phase 3 BT 完了まで不変**。

### 9.2 Phase 3 GO/NO-GO 判断 (Wave 1 monitor との接続)

- Phase 3 BT 着手は **Wave 1 monitor δ (+72h, 04-30) または ε (+7 days, 05-04)** の結果次第
- Wave 1 で R2-A 副作用なしを確認後、Phase 3 BT script 整備に着手

### 9.3 Out-of-scope (本 LOCK では扱わない)

- WEAK 13 戦略の改造 → 別 Pre-reg LOCK
- friction multiplier production deploy → Phase 3 BT 後の best-fit 確定後
- registry housekeeping (NONE 戦略削除) → 機械的整理、別 PR

---

## 10. 文書 Lock 確認 (commit 時)

```
LOCK timestamp: (to be set on commit)
commit hash: (to be set on commit)
files modified:
  - wiki/learning/phase3-bt-pre-reg-lock.md (本文書)
  - wiki/learning/wave1-r2a-power-analysis.md
  - wiki/learning/fx-fundamentals.md (Section 6.3 / 6.4)

Cryptographic guarantee:
  Any change to this document after commit will create a new commit hash,
  exposing post-hoc modification (HARKing) detectable by git history audit.
```

**LOCK 後の修正規律**:
1. 本文書修正は新 commit で記録 (誰が・いつ・なぜ を明示)
2. BT 結果に基づく修正は **本 LOCK ではなく Phase 3 BT result document** に記載
3. 本 LOCK の K, α, WFA, G1-G5, 採用基準は BT 完了まで不変

---

## 11. References

- 本 Plan: `/Users/jg-n-012/.claude/plans/fx-edge-reset-curried-ritchie.md`
- U3 (Phase 3 設計指針 G1-G5): `wiki/learning/u3-vol-momentum-scalp-deepdive.md`
- U11 (Phase 3 universe Tier-A 5): `wiki/learning/u11-mechanism-audit-aggregate.md`
- U13/U14 (Mode A/B friction): `wiki/learning/u13-u14-friction-calibration.md`
- Wave 1 R2-A power analysis (B): `wiki/learning/wave1-r2a-power-analysis.md`
- 数学根拠: Track ⑤ §5.4-5.6, `wiki/learning/fx-fundamentals.md`
- 既存 pre-reg: `pre-registration-pullback-to-liquidity-v1.md`, `pre-registration-asia-range-fade-v1.md` (Phase 1.7 既設)
- Audit framework: `knowledge-base/wiki/syntheses/strategy-mechanism-audit-2026-04-26.md`
- Asymmetric Agility Rule 1/2/3: `knowledge-base/wiki/lessons/lesson-asymmetric-agility-2026-04-25.md`
