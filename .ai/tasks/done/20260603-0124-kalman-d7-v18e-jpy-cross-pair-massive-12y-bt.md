---
id: 20260603-0124-kalman-d7-v18e-jpy-cross-pair-massive-12y-bt
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-06-03
owner: claude
---

# Kalman D7 v18e — JPY Cross-Pair MASSIVE 12y BT (USDJPY/EURJPY/GBPJPY/AUDJPY)

**Rule classification**: R1 (Slow & Strict — cross-pair promotion candidate.
TV Stage 0 で AUDJPY (PF 1.606) と GBPJPY (PF 1.235) が USDJPY 本家 (PF 1.184) を
上回ったが、10ヶ月 single-regime BT のため Codex MASSIVE 12y + WFO 3-fold +
Bonferroni m=4 検証が必要。Shadow promote / pair extension 判断の前提。)

## Context — Stage 0 findings (TV M15, 2025-08-01 → 2026-06-03, 10mo)

LONG-only Kalman D7 v18e LIVE (USDJPY M15 で稼働中) の cross-pair sweep を TV で
実施。同じ Pine source / 同じ filter / 同じ 0.5×ATR trail exit を 4 pair で適用。

| Pair | N | WR | PF | Net | MaxDD |
|---|---:|---:|---:|---:|---:|
| AUDJPY | 72 | 68.06% | **1.606** | +192.04 JPY (+0.19%) | 0.08% |
| GBPJPY | 128 | 67.19% | **1.235** | +112.11 JPY (+0.11%) | 0.05% |
| **USDJPY (baseline)** | 58 | 53.45% | **1.184** | +58.92 JPY (+0.06%) | 0.08% |
| EURJPY | 106 | 65.09% | 1.039 | +14.02 JPY (+0.01%) | 0.08% |

**Key observation**: thesis (PO-UP regime trend-follow + 0.5×ATR trail) seems to
generalize across JPY crosses, with AUDJPY strongest, EURJPY weakest. But 10mo
single-regime data is insufficient for promotion decision.

## Canonical Pine source

`/Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine` (//@version=6,
65 lines, Pine v6). Codex 必須参照: must reproduce in Python exactly.

Key logic to port:
- EMA periods: 25 / 75 / 200 on close
- ATR(14)
- RSI(14)
- ATR percentile P20/P80 with window=200
- `perfect_up = ema25 > ema75 > ema200 AND close > ema25`
- `po_up_start = perfect_up AND NOT perfect_up[1]` (transition INTO PO-UP)
- 5 filters:
  - DIST: `(close - ema200) / atr < 3.0`
  - GAP: `(ema25 - ema200) / atr < 3.0`
  - ATR_Q: `atr P20 ≤ atr < atr P80` (Q2-Q4 mid vol)
  - RSI: `rsi < 70` (not overbought)
  - Session UTC: ASN (h<7) OR LDN (7≤h<12) OR NY (16≤h<21) — exclude OVL/DEAD
- Entry: po_up_start AND all 5 filters
- Exit: TV native trailing — `strategy.exit(stop=entry - 2.0×ATR, trail_points=round(1.0×ATR/mintick), trail_offset=round(0.5×ATR/mintick))`

Position sizing for BT: `default_qty_type=strategy.percent_of_equity,
default_qty_value=10, pyramiding=0, commission=0.002%, slippage=1 tick`.
Match these in Python BT engine.

## Data source

**MUST USE MASSIVE** (see `wiki/lessons/2026-05-05-bt-must-use-massive.md`):
- `data/cache/massive/USDJPY_M15.parquet`
- `data/cache/massive/EURJPY_M15.parquet`
- `data/cache/massive/GBPJPY_M15.parquet`
- `data/cache/massive/AUDJPY_M15.parquet`

If any parquet missing: 在庫確認 → 入手不可なら REJECT with reason (do NOT
substitute Yahoo / OANDA candles — Yahoo は 60日制限、OANDA は v18e LIVE が
TV 経由で稼働中で重複ロード回避が望ましい)。

Period: max-available, target 12 years (e.g., 2014-01-01 → 2026-06-01)

## Pre-registration (LOCK before BT run)

### Single-pair pass criteria

For each pair, edge claim requires ALL of:
1. **PF ≥ 1.20** (parametric Wilson; v18e LIVE baseline 1.184 で USDJPY 通過は
   marginal、AUDJPY 1.606 / GBPJPY 1.235 は両方 pass 想定)
2. **Wilson 95% lower bound for WR ≥ 0.50** (with sample N from BT)
3. **N ≥ 100** (statistical power)
4. **Max DD ≤ 5% of equity** (capital preservation)
5. **WFO 3-fold all-fold PF > 1.0** (no fold negative)
6. **Bonferroni m=4 corrected**: parametric p-value (using normal approx for log-PF)
   < 0.0125

### Cross-pair correlation adjustment

After pair-level BT, compute pairwise PnL correlation across 4 pairs (daily
aggregated PnL series). Report correlation matrix. If max pairwise correlation
> 0.50, effective m is reduced (use Šidák correction with k=effective_pairs).
Document method and final α_eff per pair in deliverable.

### Catastrophic floor (REJECT if violated)

- Net PnL sign reversal from Stage 0 (TV 10mo positive → Codex 12y negative) →
  REJECT thesis for that pair
- WR drop > 20pp from Stage 0 (e.g., AUDJPY 68% → 12y 48%) → REJECT
- PF crosses below 1.0 → REJECT

## Deliverable

Output file: `raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-YYYY-MM-DD.md`

Required sections:
1. **Replication of v18e Pine logic in Python** — pseudocode + key
   discrepancies vs Pine if any (ATR/EMA initialization, percentile method, etc)
2. **Per-pair BT summary table** — N, WR, PF, Net, MaxDD, Sharpe, avg win, avg
   loss, avg bars in trade
3. **WFO 3-fold per pair** — train/test split dates, per-fold PF/Net, all-fold
   pass/fail
4. **Pairwise PnL correlation matrix** + effective Bonferroni (Šidák if
   correlation high)
5. **Per-pair pre-reg verdict**: PASS_SHADOW_PROMOTE / MARGINAL_WATCHLIST /
   REJECT, with full justification
6. **Recommendation**: shadow promote 候補 pair の有無 + LIVE 拡張可否 (Stage 1
   shadow N=30+ 蓄積後に再評価が前提)

## Files Codex should create

- `tools/kalman_d7_v18e_python_port.py` — Pine→Python port, callable for any pair
- `tools/kalman_d7_v18e_cross_pair_bt.py` — orchestrates 4-pair BT + WFO +
  Bonferroni computation, dumps JSON intermediate + writes markdown report
- `raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-YYYY-MM-DD.md` — final
  deliverable
- `raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-YYYY-MM-DD.json` —
  raw numerical results (for Claude post-hoc analysis)

## Files NOT to touch

- `modules/demo_trader.py` — Kalman D7 LIVE 配線 (USDJPY 用) を保護
- `strategies/` — Python 戦略本体は本タスクの scope 外
- `wiki/strategies/kalman_*.md` — KB 更新は Claude 側で別タスク (Codex は
  raw/bt-results/ への deliverable のみ)

## Acceptance for this Codex task

- 4 pair × 12y BT 完走 (parquet 欠落で fewer pair OK だが理由明記)
- Pine-Python port が unit test で v18e Pine output と一致 (せめて TV 10mo BT の
  trade timestamps と Python BT trade timestamps が >90% 一致)
- 全 deliverable section 提出
- Pass/fail/marginal verdict 各 pair について明記

## Related context

- TV slot for v18e LIVE source: `USER;66bd93e0ac9d458194d7541fc2ea9a37`
- USDJPY 10ヶ月 LIVE 稼働中 (regime-bound discretionary exception, see
  `wiki/decisions/kalman-d7-shadow-first-exception-2026-05-20.md` if exists)
- Previous Kalman D7 cross-pair attempt: EUR_USD M15 全 5 variant fail (PF<1.0,
  see CLAUDE MEMORY `project_kalman_d7_eurusd_po_diag_2026_05_21.md`).
  EURJPY での edge は薄いが positive、cross-pair の thesis 限界線が JPY crosses
  内にあるか外にあるかを本 BT で確定する。
- Memory: `feedback_bt_must_use_massive.md` — Yahoo 60日制限で 12y BT 不可、
  MASSIVE parquet 必須
- Memory: `feedback_codex_schema_hallucination.md` — Codex 外部 DB tool 注意、
  本タスクは MASSIVE parquet read のみで Render Postgres 触らない


## Result (2026-06-07T06:19:07Z)

exit=0 · 366s

```
Implemented and ran the Kalman D7 v18e JPY cross-pair MASSIVE BT.

Created:
- [tools/kalman_d7_v18e_python_port.py](/data/repo/fx-ai-trader/tools/kalman_d7_v18e_python_port.py)
- [tools/kalman_d7_v18e_cross_pair_bt.py](/data/repo/fx-ai-trader/tools/kalman_d7_v18e_cross_pair_bt.py)
- [raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-2026-06-07.md](/data/repo/fx-ai-trader/raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-2026-06-07.md)
- [raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-2026-06-07.json](/data/repo/fx-ai-trader/raw/bt-results/kalman-d7-v18e-jpy-cross-pair-12y-bt-2026-06-07.json)

Result summary:
- `USDJPY`: REJECT, PF `0.861`, Net `-601.96`, used MASSIVE 5m resampled to M15 because native/requested M15 was missing.
- `EURJPY`: REJECT, PF `0.792`, Net `-1609.21`, used repo-native `EUR_JPY_15m` MASSIVE alias with 12.33y coverage.
- `GBPJPY`: REJECT, PF `0.732`, Net `-2296.70`, used MASSIVE 5m resampled to M15 for 12.32y coverage.
- `AUDJPY`: REJECT, PF `0.675`, Net `-321.81`, only ~1.00y native M15 MASSIVE coverage available, so coverage gate fails.

All WFO folds failed the all-fold `PF > 1.0` requirement except isolated AUDJPY fold 1. Max daily PnL correlation was `0.204`, so Bonferroni `m=4` remained in force with `alpha_eff=0.0125`.

Validation run:
- `.venv/bin/python -m py_compile tools/kalman_d7_v18e_python_port.py tools/kalman_d7_v18e_cross_pair_bt.py`
- Fixture smoke: `fixture_bars 6095 signals 24 trades 19`

Important caveat: the canonical Pine file and TV trade export were not present in this container, so the report documents Pine/TV replication discrepancies and could not perform the requested `>90%` trade timestamp match check.
```
