# Pre-reg LOCK: Phase 8 Track E — Regime-Stratified Edge Mining (2026-04-28)

## Status: rule:R1 — Regime-conditional edge discovery

Phase 7 single-feature scan は唯一 `hour=20 × JPY × SELL` のみ survivor。
hypothesis: signal は **regime に対して average化されたから weak だった**。
regime conditioning すれば隠れた edge が surface する可能性がある。

このドキュメントは Track E **audit ロジックの LOCK** — 後追加・後変更は data
dredging とみなす。

---

## Hypothesis (LOCKED)

H_E1: 既存 features (hour, bbpb, atr_pct, recent_3bar) は **regime-conditional**
であり、regime stratification によって hidden edge が surface する。

H_E2: regime transition (regime A → regime B) の直後 N-bar は overshoot/MR
ダイナミクスを生み、forward outcome に edge がある。

---

## Pre-registered Stratifications (LOCKED)

3 stratifications に LOCK。新規追加・bucket 改変は audit 完了まで禁止。

### S1: HMM regime × hour × pair × dir × forward
- regime: `{up_trend, down_trend, range, uncertain}` (regime_labeler 既存)
- hour: 0..23 UTC
- pair: 5 majors (USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY)
- direction: BUY / SELL
- forward_bars: 4 / 8 / 12
- 理論最大: 4 × 24 × 5 × 2 × 3 = 2,880 cells (N≥100 で大幅削減)

### S2: ATR percentile × bbpb_15m × dir × pair × forward
- atr_pct_60d_b: {0=low, 1=mid, 2=high} (Phase 7 LOCK 同)
- bbpb_15m_b: 0..4 (Phase 7 LOCK 同)
- pair × direction × forward: as above
- 理論最大: 3 × 5 × 5 × 2 × 3 = 450 cells

### S3: Regime transition events
- transitions: `{up→down, down→up, range→up, range→down}` (4 種)
- pair: 5 majors
- direction × forward: as above
- 理論最大: 4 × 5 × 2 × 3 = 120 cells
- entry: regime change を検出した bar(t) 後の bar(t+1) Open
  (regime label は bar(t-1) の data から計算済 → look-ahead 安全)

合計理論最大: 3,450 cells (Stage 1 input family)。

---

## Bucket Boundaries (LOCKED)

Phase 7 (`pre-reg-pattern-discovery-2026-04-28.md`) と同一:
- `hour_utc`: 0..23
- `bbpb_15m_b`: quintile (boundaries 0.2, 0.4, 0.6, 0.8)
- `atr_pct_60d_b`: tertile (33%, 67%)

Regime labels: `regime_labeler.RegimeConfig` のデフォルト
(slope_t_trend=2.0, adx_trend=25.0, slope_t_range=1.0, adx_range=20.0)。

---

## Regime Computation (LOCKED, 重要 — look-ahead 防止)

15m timeframe の close から `compute_slope_t(window=48)` + `compute_adx(14)` を
right-aligned で計算 → bar(t-1) 終値までの情報のみ使用。
bar(t) の signal 判定で **bar(t-1) の regime label** を参照、bar(t+1) Open で
entry。

Phase 7 LOCK と同一 timing convention を維持。

---

## Data Splits (LOCKED, Phase 7 LOCK 継承)

| split | window | 用途 |
|---|---|---|
| Training | `[最古, 最新-90日]` (= 275 日) | Stage 1 |
| Holdout  | `[最新-90日, 最新]`              | Stage 2 OOS |

---

## Trade-Outcome Simulation (LOCKED, Phase 7 と同)

```
Entry: bar(t) Open  (regime label は bar(t-1) 以前の data 由来)
SL:    1.0 × ATR(14)
TP:    1.5 × ATR(14)
Exit:  SL/TP hit、または forward_bars 経過後 close
Friction: friction_for(pair, mode="DT", session=current_utc_session)
PnL_net = PnL_gross - friction_pip
```

`tools/lib/trade_sim.py` の `simulate_cell_trades` / `aggregate_trade_stats`
を再利用。

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

uneven regime (range / uncertain が大半) の場合、small regime cell は N≥100
gate で自動的に除外される。

---

## Multiple Testing (LOCKED)

Stage 1: 全 generated cells (N≥100 通過後) に対し BH-FDR(q=0.10) 一括補正。
S1, S2, S3 は **同一 family** として扱う (cross-stratification snooping 補正)。

Phase 8 cross-track Bonferroni は master 担当。

---

## Bonus deliverable: Phase 1-7 採用エッジの regime-conditional 再評価

Phase 1-7 で採用された 7 戦略 (Mode A/B) の signal 発生時 regime distribution
を集計し、`regime × WR/EV` table を出力。
特定 regime (例: range のみ) で edge が集中していれば deployment に
regime gate を追加する価値あり。

これは Track E の bonus output (deploy 判断は master)。

---

## Cross-Track Notes

- Track A (3-way) で `regime × hour × pair` を triplet に含めた場合、Track E
  の S1 と完全 overlap → master の de-dup logic で merge
- 既存 `hmm_regime_filter` は overlay (信号無し)、Track E は signal generation
  → 機能補完
- Track E S1 で survive した cell が Phase 7 で発見済の cell の subset
  (regime constraint 追加版) なら novel ではない → master の orthogonality
  check で除外

---

## Outputs (LOCKED)

- `raw/phase8/track_e/stage1_<date>.json` — 全 cells (S1+S2+S3) と survivors
- `raw/phase8/track_e/stage2_<date>.json` — Stage 1 survivors の holdout 結果
- `raw/phase8/track_e/regime_conditional_phase17_<date>.json` — Bonus

---

## Computational Budget (LOCKED)

30-45 min。Phase 7 と同 data cache 再利用、regime label は新規 compute (15m × 5 pairs × 365d ≈ 175k bars × 5 = 875k bars; slope_t window 48 + ADX は cheap)。

---

Pre-registered: 2026-04-28 (Asia session, 22:00 JST 以降)
Audit start: 同日中。LOCK 解除は master 集約後の post-mortem 時のみ。
