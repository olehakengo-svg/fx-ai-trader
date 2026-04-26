# Pre-registration: Phase 4d — Session × Spread × Strategy Routing (2026-04-26)

**Locked**: 2026-04-26 (本 doc 確定後変更禁止)
**Track**: 4d (Track B closure 後の新 track, MTF approach から pivot)
**Plan**: `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (Track B closure 評価入り)

## 0. Rationale

[[phase4c-signalD-multivariate-result-2026-04-26]] (Phase II) で MTF/regime block は
LR p=0.40 で full null 確定. 一方 GBM permutation importance で **session 31.4% +
spread_q 14.0%** が dominant predictor と判明. これらは Phase 4c の pre-reg では
confounder 扱いだったが、本 phase で **primary feature** として disciplined に検定する.

仮説: 各戦略は固有の "勝てる session × spread cell" を持ち、それ以外で entry すると
WR が baseline 以下に落ちる. Routing rule を pre-reg LOCK 下で identify.

## 1. Population (LOCKED)

- Source: production API trades, 2026-04-08 以降, WIN/LOSS, 8 strategies, excl XAU
- 期待 N: ~1804 trades
- Phase 4c Signal D と同じ scope (再現性確保)

## 2. Feature definitions (LOCKED, Phase II と同一)

### 2.1 session_name (UTC hour-of-day から導出)

```
Tokyo    : 0 ≤ hour < 9    (8 hours)
London   : 8 ≤ hour < 17   (9 hours, Tokyo overlap 含む)
NewYork  : 13 ≤ hour < 22  (9 hours)
Overlap  : 13 ≤ hour < 17  (London×NY 4 hours)
Off      : それ以外 (22-24)
```
階層判定: Overlap が最優先 → NY → London → Tokyo → Off (Phase 4c Signal D と完全同一).

### 2.2 spread_q (pair-internal quartile, LOCKED)

各 pair について、本 scope 内の `spread_at_entry` を 4 quantile bin (0=最低, 3=最高).
Pair 別計算で fairness 担保 (USDJPY と GBPUSD で spread の絶対値違うため).

## 3. Test design (LOCKED)

### 3.1 Primary 1: per-strategy session × outcome χ²

各 strategy について 2×4 contingency table (WIN/LOSS × 4 sessions). Pearson χ² test,
df=3.

Bonferroni: M_session = 8 strategies. α_session = 0.05/8 = **6.25e-3**.

### 3.2 Primary 2: per-strategy spread_q × outcome χ²

各 strategy について 2×4 contingency (WIN/LOSS × 4 spread quartiles). Pearson χ²,
df=3.

Bonferroni: M_spread = 8 strategies. α_spread = 0.05/8 = **6.25e-3**.

### 3.3 Family-wise: cross-feature Bonferroni

session と spread_q は別 feature だが同じ outcome に対する検定. **総 family size
M = 16**, α_family = 0.05/16 = **3.125e-3**.

各 cell の verdict は α_family を primary criterion に. α_session/spread (6.25e-3) は
"weak signal" として CANDIDATE 認定に用いる.

### 3.4 SURVIVOR / CANDIDATE

| Decision | Criteria |
|----------|----------|
| **SURVIVOR** | N_total ≥ 50 ∧ ≥2 cell N≥30 ∧ dWR(max-min) ≥ 0.05 ∧ χ² p < 3.125e-3 ∧ Cramér V ≥ 0.15 |
| **CANDIDATE** | 同上で χ² p ∈ [3.125e-3, 6.25e-3] (single feature Bonferroni 通過) |
| **NULL** | χ² p ≥ 0.05 |
| **REJECT** | χ² p < 0.05 ∧ dWR < 0.05 (significance だが effect 小) |
| **INSUFFICIENT** | N_total < 50 or N≥30 cell が 1 個以下 |

## 4. Secondary (exploratory, Bonferroni 対象外, 報告のみ)

- Per-strategy session × spread_q joint cell (16 cells/strategy) の descriptive WR
  table — **検定なし**, **routing rule の hypothesis 生成のみ**
- 各 SURVIVOR strategy の top cell vs bottom cell に対する Wilson 95% CI, half-Kelly,
  PF
- Nature aggregate (TREND/BREAKOUT/RANGE) per session: pooled WR
- `mtf_alignment` interaction (04-20+ subset) — Phase 4c Signal D で fitting 失敗
  だったが descriptive で見る価値あり

## 5. Disallowed (post-hoc 禁止)

- §2.1 session 境界の事後変更
- §2.2 spread quartile 境界の事後変更 (例: tertile に変更)
- α 緩和 (3.125e-3 → 6.25e-3 等)
- Cramér V threshold 緩和
- Strategy 除外 (8 strats fixed)
- 結果から逆算した cell-grain routing (例: hour-of-day 1-bin での argmax)

## 6. Pre-registered hypotheses

| H | Type | Prediction |
|---|------|-----------|
| H1 | strong | ≥1 strategy で session × outcome SURVIVOR (Phase II GBM importance 31.4% 反映) |
| H2 | moderate | ≥1 strategy で spread_q × outcome CANDIDATE 以上 |
| H3 | moderate | TREND nature 戦略の dominant session は London/Overlap (vol 期待値高) |
| H4 | weak | RANGE nature 戦略の dominant session は Tokyo (low-vol session 期待) |
| H5 | overall | ≥3 SURVIVOR/CANDIDATE 戦略 (Phase 4c Signal D の 0/8 と対比) |

## 7. Scenario & authorization

| Scenario | Rule | Action |
|----------|------|--------|
| C | SURVIVOR ≥ 1 | 該当 (strategy, session, spread_q) を Phase 4d-II (joint cell deep-dive) に進める |
| B | SURVIVOR=0 ∧ CANDIDATE ≥ 1 | Suggestive, N 蓄積待ちで再検定 |
| A | 全 NULL | Session × Spread route も dead, **戦略 base WR 改善以外に勝ち筋なし** の evidence |

**重要**: 本 phase は MTF route closure の代替候補. Scenario A なら "MTF も session/
spread も dead" の二重否定になり、**全戦略を一度 base 改修フェーズに戻す** judgment
を要する.

## 8. Execution

- Script: `/tmp/phase4d_session_spread_routing.py`
- Output: `/tmp/phase4d_output.txt`, `/tmp/phase4d_summary.json`
- Result KB: `knowledge-base/wiki/analyses/phase4d-session-spread-routing-result-2026-04-26.md`

## References

- [[phase4c-signalD-multivariate-result-2026-04-26]] (本 phase の trigger)
- [[phase4c-signalC-field-ranking-result-2026-04-26]]
- [[phase4c-mtf-alignment-bug-audit-2026-04-26]]
- `/Users/jg-n-012/.claude/plans/mtf-rustling-candle.md` (上位 plan)
- `app.py` L593-619 `get_session_info` (production session classifier)
