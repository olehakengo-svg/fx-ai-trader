# Pre-reg LOCK: Pattern Discovery Phase 7 (2026-04-28)

## Status: rule:R1 — Bottom-up empirical edge mining

Phase 1-6 の top-down hypothesis-driven approach (19 仮説 / 7 採用) を補完する
**bottom-up data mining** audit。365d 全 bar を feature combination で網羅 scan
し、未探索の cell-level edge を発掘する。

このドキュメントは **audit ロジックの LOCK** — 後追加・後変更はすべて data
dredging とみなされ無効。

---

## Pre-registered Feature Axes (LOCKED)

```python
FEATURE_AXES = {
    "hour_utc":      list(range(24)),       # 24 buckets (0-23 UTC)
    "dow":           [0, 1, 2, 3, 4],        # 5 (Mon-Fri only, exclude Sat/Sun)
    "bbpb_15m":      [0, 1, 2, 3, 4],        # quintiles by 15m BB%B value
                                              # (boundaries: 0.2, 0.4, 0.6, 0.8)
    "rsi_15m":       [0, 1, 2, 3],           # quartiles by 15m RSI
                                              # (boundaries: 30, 50, 70)
    "bbpb_1h":       [0, 1, 2, 3, 4],        # 1h aggregated, same boundaries
    "atr_pct_60d":   [0, 1, 2],              # tertiles by 60-day ATR percentile
                                              # (boundaries: 33%, 67%)
    "recent_3bar":   [-1, 0, 1],             # prior 3-bar net direction
                                              # (sum signs: <-1=down, [-1,1]=flat, >1=up)
}

PAIRS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
DIRECTIONS = ["BUY", "SELL"]
FORWARD_BARS = [4, 8, 12]   # 1h / 2h / 3h forward windows
```

**禁止事項**: 上記 axes の追加・bucket boundary 変更・新 feature 追加は audit 完了
までは禁止。

---

## Data Splits (LOCKED)

| split | window | 用途 |
|---|---|---|
| **Training** | `[最古, 最新-90日]` (= 275 日) | Stage 1-3 (audit 全工程) |
| **Holdout** | `[最新-90日, 最新]` | Stage 4 final OOS — audit 完了まで一切触れない |
| **Live Shadow** | Phase 1-5 deploy 後の Live trades (cumulative) | Stage 4 補助 OOS |

`pd_holdout_window.json` に start/end timestamp を記録し、Stage 4 まで read 禁止。

---

## Trade-Outcome Simulation (LOCKED)

各 cell の forward outcome は WR だけでなく **実 P&L** で評価:

```
Entry: bar(t) Open (look-ahead 防止)
SL:    1.0 × ATR(14) (反対方向)
TP:    1.5 × ATR(14) (RR=1.5)
Exit:  SL or TP hit、または forward_bars 経過後 close
Friction: friction_for(pair, mode="DT", session=current_utc_session)
         を control flow で apply (cell-conditioned)
PnL_net = PnL_gross - friction_pip
```

session 定義:
- `tokyo`:    UTC 0-7
- `london`:   UTC 7-13
- `ny`:       UTC 13-21
- `overnight`: UTC 21-24

---

## Gate 通過基準 (LOCKED)

### Stage 1 (Single-feature, BH-FDR primary)
- BH-FDR (q=0.10) 通過
- Wilson lower (95%) > 0.50
- N ≥ 100
- EV_pip_net > 0
- trades/month ≥ 5 (capacity)
- per-event Sharpe > 0.05 (per-event basis、annualized では誤解)

### Stage 2 (Pairwise interaction, Bonferroni primary)
- Bonferroni p_bonf < 0.05
- Stage 1 全条件
- 内部 Bonferroni family size = 全 pairwise combos × pairs × directions × forwards

### Stage 3 (Stability)
- Quarterly WR std < 0.10
- All 4 quarters の Wilson_lower > BEV
- Chow test (pair-quarter boundary): no structural break (p > 0.05)
- WF (3-fold anchored): 各 fold で Wilson_lower > BEV

### Stage 4 (True OOS)
- Holdout 90 日の WR > BEV ∧ EV_net > 0
- Live shadow data (overlap cells のみ): WR > BEV ∧ N ≥ 10
- final survivors: train + holdout + live 全条件 pass

---

## Multiple Testing Correction (LOCKED)

| Stage | family size | 補正 |
|---|---|---|
| 1 | 7 features × 5 pairs × 2 directions × 3 forwards = **210** | BH-FDR (q=0.10) |
| 2 | top4-features pairwise C(4,2)=6 × 5 pairs × 2 dir × 3 fw = **180** | Bonferroni (α/180) + BH-FDR |
| 3 | Stage 2 通過 cell 数 (動的) | Bonferroni (各 sub-test) |
| 4 | Stage 3 通過 cell 数 (動的) | Bonferroni + visual inspection |

Snooping 累積補正: Phase 1-6 で同 365d を 10 audits 使用済 → effective family size
を ×3 補正係数で見積り (conservative)。

---

## Look-Ahead Prevention (LOCKED)

- 全 feature: bar(t-1) close 以前の data のみ
- Entry: bar(t) Open でエントリ前提
- 1h aggregation: bar(t-1) を含む 4 × 15m bar が完了している場合のみ 1h 値を使用
- Indicator warmup: ATR/BB/RSI 等の period (60 bar 必要) は最初 60 bar をスキップ
- regime label: regime_labeler.label_trades() の backward-merge を準拠

---

## Reuse vs New (LOCKED)

### Reuse (既存)
- `research/edge_discovery/significance.py:171` apply_corrections (Bonferroni + BH-FDR)
- `modules/friction_model_v2.py:78` friction_for (cell-conditioned)
- `tools/bt_data_cache.py:80` BTDataCache.get
- `tools/cell_edge_audit.py:84,95` wilson_lower/upper
- `research/edge_discovery/significance.py:217` wf_stable_for_cell

### New (実装)
- `tools/lib/trade_sim.py` — DRY 化された SL/TP + friction simulation
- `tools/pattern_discovery.py` — Stage 1-4 統括 main scanner

---

## 不採用判定基準 (rejection criteria)

以下のいずれかに該当する cell は不採用:
1. Stage 1-4 のいずれかで gate 未通過
2. 既存 Phase 1-6 採用戦略と correlation > 0.5 (orthogonal でない)
3. 月 trade 数 < 5 (capacity 不足)
4. Quarterly std ≥ 0.10 (regime 不安定)
5. Chow test で構造変化 detect

---

## Audit 開始 commit hash

このドキュメント commit 後、すべての audit ツール (`pattern_discovery.py`,
`trade_sim.py`) は本 LOCK を準拠する。

**変更履歴**: 後の amend は禁止、別 pre-reg ドキュメントで管理。

## Related
- [[index]] — Tier classification
- Phase 1-6 採用戦略の cell-level 深掘りは別 session で並行進行 (spawn 済)
