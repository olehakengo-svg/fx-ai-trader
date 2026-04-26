# Pre-registration: Phase 4d-II — Strategy Nature Pooling Analysis (2026-04-26)

**Locked**: 2026-04-26 (本 doc 確定後変更禁止)
**Track**: 4d-II (Phase 4d 結果に基づく power 回復のための pooling)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`

## 0. Rationale

[[phase4d-session-spread-routing-result-2026-04-26]] (Phase 4d) で Bonferroni 厳格
基準では 0 SURVIVOR. 原因は **per-strategy N=98-608 を 4-level に splitting した
power loss**. Phase II GBM は session 31% + spread 14% を non-trivial と検出している
ことから、**集約レベルでは signal が存在**.

仮説: 戦略を **nature (TREND/BREAKOUT/RANGE)** で pooling すると、N が 3-5x 大きくなり
Bonferroni family も縮小 (M=16 → M=6) で power が大幅改善. **nature レベルの
"勝てる session × spread × nature" cell が浮上する**可能性.

## 1. Population (LOCKED)

- Source: production API trades, 2026-04-08 以降, WIN/LOSS, 8 strategies, excl XAU
- Phase 4d と同じ scope (1804 trades 期待)
- Pooling 単位:
  - **TREND**: ema_trend_scalp + stoch_trend_pullback (~770 trades)
  - **BREAKOUT**: vol_surge_detector + bb_squeeze_breakout (~213 trades)
  - **RANGE**: bb_rsi_reversion + engulfing_bb + fib_reversal + sr_channel_reversal (~819 trades)

## 2. Feature definitions (Phase 4d と完全同一, LOCKED)

§2.1 session_name (Tokyo/London/Overlap/NewYork/Off, hour-of-day から導出)
§2.2 spread_q (pair-internal quartile)

## 3. Test design (LOCKED)

### 3.1 Primary 1: per-nature session × outcome χ²

各 nature (3 個) で 2×K contingency. Pearson χ², df = K−1.

Bonferroni: M_session = 3 nature. α_session = 0.05/3 = **1.667e-2**.

### 3.2 Primary 2: per-nature spread_q × outcome χ²

同上で 2×4. df=3. Bonferroni M_spread = 3.

### 3.3 Family-wise: cross-feature Bonferroni

**M_total = 6** (3 nature × 2 features). α_family = 0.05/6 = **8.33e-3**.

SURVIVOR primary criterion: α_family. CANDIDATE: α_single (1.667e-2).

### 3.4 Primary 3: per-nature session × spread_q joint (4×4=16 cells)

各 nature の 16-cell contingency. df = 15. Bonferroni M_joint = 3, α = 1.667e-2.

これは **descriptive routing の検定的 backbone**. Phase 4d で descriptive のみだった
joint cells に正式な statistical authorization を与える.

### 3.5 SURVIVOR / CANDIDATE / Scenario

| Decision | Criteria |
|----------|----------|
| **SURVIVOR** | N_total ≥ 100 ∧ ≥3 cell N≥30 ∧ dWR ≥ 0.05 ∧ p < 8.33e-3 ∧ Cramér V ≥ 0.15 |
| **CANDIDATE** | 上記で α_family 未通過, α_single 通過 |
| **NULL** | p ≥ 0.05 |
| **REJECT** | p < 0.05 ∧ dWR < 0.05 |

| Scenario | Rule | Action |
|----------|------|--------|
| C | SURVIVOR ≥ 1 | nature 別 routing rule を R1 framework で認可 |
| B | CANDIDATE ≥ 1 | suggestive, R2 reactive monitoring |
| A | 全 NULL | nature pooling でも null → 真の data 不足 (Path 4 待機) |

## 4. Secondary (exploratory, Bonferroni 対象外)

- 各 nature × session × spread_q の Wilson 95% CI ranking
- Per-pair × nature ranking (USDJPY/EURUSD で nature behavior 違うか)
- Half-Kelly per cell
- Cross-validation 指標として: train/test 50/50 で top-cell の保持率

## 5. Disallowed

- §1 nature 構成変更 (8 戦略 LOCK)
- §2 session/spread_q 境界変更
- α 緩和
- Pooling 単位の事後変更 (例: BREAKOUT を TREND に merge)

## 6. Pre-registered hypotheses

| H | Type | Prediction |
|---|------|-----------|
| H1 | strong | TREND nature の session × outcome SURVIVOR (pooled N=770 で power 十分) |
| H2 | moderate | RANGE nature × spread_q CANDIDATE 以上 (fib_reversal × q3 high WR の補強) |
| H3 | weak | BREAKOUT は N=213 で INSUFFICIENT |
| H4 | overall | ≥1 SURVIVOR (Phase 4d Scenario A から脱却) |

## 7. Execution

- Script: `/tmp/phase4d_II_nature_pooling.py`
- Output: `/tmp/phase4d_II_output.txt`, `/tmp/phase4d_II_summary.json`
- Result KB: `knowledge-base/wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md`

## References

- [[phase4d-session-spread-routing-result-2026-04-26]] (本 phase の trigger)
- [[phase4c-signalD-multivariate-result-2026-04-26]] (GBM importance evidence)
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md`
