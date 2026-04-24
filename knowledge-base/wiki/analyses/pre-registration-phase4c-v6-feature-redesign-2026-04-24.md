# Pre-registration: Phase 4c v6 Feature Redesign Classifier (2026-04-24)

**Locked**: 2026-04-24 (本 doc 確定後変更禁止)
**Track**: A (v6 classifier redesign, feature set 入れ替え)
**並行**: [[pre-registration-phase4c-mtf-regime-2026-04-24]] (Track B)
**Upstream**: [[phase4b-cell-edge-test-result-2026-04-24]] (Scenario A, power-limited)

## 0. Rationale

v5 classifier (F1-F6 + meta-percentile) は Phase 4b で power-limited Scenario A に終わった.
**classifier 自体は semantically stable** (Phase 4a で 10 cells PHASE_B authorized) だが
edge 検出には N 不足. v6 は **feature 入れ替えで signal-to-noise 改善** を狙う.

具体的には v5 の F1-F6 (ATR 比・値幅・duration) は **regime の"形状"** を捉えるが、
"order flow" や "time-of-day effect" が欠落. OANDA 5m data で利用可能な資源は:
- OHLCV (Volume = tick count per bar)
- 時刻 (hour-of-day, day-of-week, session)

## 1. New feature set (LOCKED)

v5 F1-F6 を **全保持**、さらに以下 F7-F9 を追加:

### F7: Tick volume z-score
```
V_raw = Volume (OANDA 5m tick count)
V_z = (V_raw − median_200(V)) / MAD_200(V)  (robust z-score, 200-bar rolling)
```
Heavy volume → regime transition 候補として有効かを検定.

### F8: Volume-price divergence
```
range = High − Low
VPD = V_z × sign(Close − Open) × (range / ATR14)
```
High volume + expansion → breakout confirmation signal.

### F9: Hour-of-day dummy (deterministic, categorical)
```
hour_UTC = entry_time.hour
session_dummy ∈ {Asia_00-07, London_07-13, NY_13-21, Off_21-24}
```
Session は Phase 2 で session-cell が失敗したが **feature として使う** のは別機構.

## 2. Classifier cell space (LOCKED)

**3D axis**: Regime × Vol × Session
- Regime: R0-R6 (v5 から不変)
- Vol: V_low / V_mid / V_high (F1 thresholds 0.33/0.67、v5 から不変)
- Session: Asia / London / NY / Off (4 buckets)

Cell 数: 6 × 3 × 4 = **72 nominal** (R0 除外)
実用 cells (N_min 通過想定): 30-50 cells

## 3. Stability tests (LOCKED)

v5 の S1/S2/S3 framework を **3D cell 単位で再適用**:

### S1 v6: per-cell × F2/F3/F7/F8 KS
- M = 72 × 4 × 9 = 2592, α_cell = **1.93e-5**
- F7 (volume z) / F8 (VPD) を新規 stability check 対象に

### S2 v6: per-cell Mann-Kendall on F2
- M = 72, α_cell = 6.94e-4

### S3 v6: per-cell CV < 0.4 (duration)
- 同じ

### Authorization rule
v5 と同じ per-cell AND:
```
CELL_GO := (S1_cell_GO ∧ S2_cell_GO ∧ S3_cell_GO)
PHASE_D_CELLS := go_cells[USDJPY] ∩ go_cells[EURUSD]
```

## 4. Scope

### Pairs (LOCKED)
- USD_JPY, EUR_USD (v5 と同じ、classifier stability 保証)

### Data
- OANDA 5m × 10 months × 2 pairs (v1-v5 と同じ、re-use)

### Phase D authorization
|PHASE_D_CELLS| ≥ 15 → full authorize
|PHASE_D_CELLS| 5-14 → limited
|PHASE_D_CELLS| 1-4 → marginal
|PHASE_D_CELLS| 0 → Track A closure

## 5. Disallowed (post-hoc 禁止)

- F7/F8 parameter 調整 (z-score window, threshold)
- Session 境界変更 (UTC 7/13/21 LOCKED)
- Cell space 再定義
- α_cell 緩和
- F1-F6 の除外 (v5 保持が前提)

## 6. Pre-registered hypotheses

**H1 (moderate)**: F7 (volume z) は breakout-type regime (R5) と F2 共通性高く
Session × Volume で新規 stable cell 発見 (5-10 cells)

**H2 (weak)**: F9 session axis は Asia/London/NY で **cell 内 trade clustering** を変化させ
PHASE_D_CELLS が v5 PHASE_B_CELLS 10 を上回る

**H3 (null)**: 3D 化で Bonferroni burden (α 1.5e-4 → 1.9e-5) が power 喰い、実用 cell 減少

## 7. Execution

1. `/tmp/phase4c_v6_classifier_stability.py` 作成
2. v5 script 再利用、feature compute を F7/F8 追加、cell assignment を 3D 化
3. OANDA 10 months × 2 pairs で S1/S2/S3 検定
4. KB 結果記録: [[phase4c-v6-classifier-stability-2026-04-24]]
5. Phase D cell edge test は別 pre-reg (v6 stability authorize 後)

## 8. Explicit non-goal

v6 classifier **stability** 検定のみ. Edge detection (cell × strategy) は Phase D (Phase 4b 相当)
で別 pre-reg LOCK 後に実行. 今 phase は **classifier 側の改善余地確認** に集中.

## References

- [[phase4a-v5-classifier-stability-2026-04-23]] (v5, 本 v6 の baseline)
- [[phase4b-cell-edge-test-result-2026-04-24]] (v5 power 限界 evidence)
- [[pre-registration-phase4c-mtf-regime-2026-04-24]] (parallel Track B)
- [[lesson-premature-neutralization-2026-04-23]]
