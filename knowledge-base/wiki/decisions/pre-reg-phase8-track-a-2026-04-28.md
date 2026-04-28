# Pre-reg LOCK: Phase 8 Track A — 3-Way Feature Interactions (2026-04-28)

## Status: rule:R1 — Higher-order interaction edge mining

Phase 7 single-feature scan の唯一 survivor (`hour=20 × JPY × SELL`) は既存
LCR-v2 と redundant。novel orthogonal edge 発掘のため、Phase 8 では feature
space を多層化する。Track A は **既存 features の 3-way 交互作用** を per-pair
で網羅 scan する。

このドキュメントは **audit ロジックの LOCK** — 後追加・後変更は data dredging。

---

## Pre-registered Triplets (LOCKED)

Per-pair で評価する feature triplet (pair は外側 iterator なので "3-way 全体" は
pair × feature1 × feature2 [× feature3])。

```python
TRIPLETS_LOCK = [
    # T1: hour × pair × bbpb_15m  — Phase 7 hour×JPY を bbpb で stratify
    ("hour_utc", "bbpb_15m_b"),
    # T2: hour × bbpb × atr_pct_60d  — timing × MR × vol regime (3-feature)
    ("hour_utc", "bbpb_15m_b", "atr_pct_60d_b"),
    # T3: pair × bbpb × rsi  — pair-specific MR signature
    ("bbpb_15m_b", "rsi_15m_b"),
    # T4: dow × hour × pair  — calendar × time × pair
    ("dow", "hour_utc"),
]
```

T1/T3/T4 は **2 within-pair features × pair** = 3-way 全体。
T2 は **3 within-pair features × pair** = 4-way 全体 (最も strict)。

---

## Bucket Boundaries (LOCKED, Phase 7 LOCK 準拠)

Phase 7 (`pre-reg-pattern-discovery-2026-04-28.md`) と同一:
- `hour_utc`: 0..23
- `dow`: 0..4 (Mon-Fri)
- `bbpb_15m_b`: quintile (boundaries 0.2, 0.4, 0.6, 0.8)
- `rsi_15m_b`: quartile (boundaries 30, 50, 70)
- `atr_pct_60d_b`: tertile (33%, 67%)

**禁止事項**: bucket boundary の変更・新 triplet 追加は audit 完了まで禁止。

---

## Data Splits (LOCKED, Phase 7 LOCK 継承)

| split | window | 用途 |
|---|---|---|
| Training | `[最古, 最新-90日]` (= 275 日) | Stage 1 |
| Holdout  | `[最新-90日, 最新]`              | Stage 2 OOS |

Holdout window は Phase 7 と同 (Phase 8 全 track 共通)。

---

## Trade-Outcome Simulation (LOCKED, Phase 7 と同)

```
Entry: bar(t) Open
SL:    1.0 × ATR(14)
TP:    1.5 × ATR(14)
Exit:  SL/TP hit、または forward_bars 経過後 close
Friction: friction_for(pair, mode="DT", session=current_utc_session)
PnL_net = PnL_gross - friction_pip
```

Forward windows: `[4, 8, 12]` bars (1h / 2h / 3h)。
Directions: `["BUY", "SELL"]`。

---

## Gates (LOCKED)

### Stage 1 (Training, BH-FDR primary)
- N ≥ 100 per cell
- BH-FDR (q=0.10) 通過
- Wilson lower (95%) > 0.50
- EV_pip_net > 0
- trades/month ≥ 5
- Sharpe per-event > 0.05

### Stage 2 (Holdout 90d OOS)
- N (holdout) ≥ 10
- WR > 0.50
- EV_pip_net > 0

---

## Multiple Testing (LOCKED)

Stage 1 family size = 全 generated cells (動的、N≥100 通過後)。
BH-FDR (q=0.10) 一括補正。Phase 8 cross-track Bonferroni は master 担当。

Snooping 累積補正: Phase 1-7 で同 365d を 11 audits 使用済 → effective family
size を ×3 補正係数で見積り (master が他 track と統合判定)。

---

## Cross-Track De-dup 注意

Phase 7 単発 survivor `GBP_JPY × hour_utc=20 × SELL` を含む triplet が出た場合:
- 3rd feature が真に WR を加えているか strict check
  例: `hour=20 × JPY × bbpb_15m_b=0` の WR が `hour=20 × JPY × all` より明確に
  高くなければ redundant (master が de-dup 判定)
- de-dup criteria は phase8 master plan 準拠

---

## Look-Ahead Prevention (LOCKED, Phase 7 継承)

- 全 feature: bar(t-1) close 以前
- Entry: bar(t) Open
- 1h aggregation: bar(t-1) を含む 4 × 15m bar 完了時のみ使用
- Indicator warmup: 60 bar 必要

---

## Reuse vs New (LOCKED)

### Reuse
- `tools/lib/trade_sim.py` (simulate_cell_trades, aggregate_trade_stats)
- `tools/pattern_discovery.py` (`_add_features`, `_load_pair`)
- `tools/bt_data_cache.py` (BTDataCache)
- `modules/friction_model_v2.py` (friction_for via trade_sim)

### New
- `tools/phase8_track_a.py` — Stage 1+2 統括 scanner

---

## Output Artifacts

- `raw/phase8/track_a/stage1_<date>.json` (全 cells + survivors)
- `raw/phase8/track_a/stage2_holdout_<date>.json` (final survivors)
- `raw/phase8/track_a/track_a_summary_<date>.md` (人間 readable)

---

## Rejection Criteria

1. Stage 1 or Stage 2 のいずれか gate 未通過
2. Phase 7 survivor との redundancy (master 判定)
3. trades/month < 5 (capacity 不足)

---

## Audit 開始 commit hash

このドキュメント commit 後、`tools/phase8_track_a.py` は本 LOCK 準拠。
変更は別 pre-reg ドキュメントで管理。

## Related
- [[phase8-master-2026-04-28]]
- [[pre-reg-pattern-discovery-2026-04-28]] — Phase 7 LOCK 継承元
