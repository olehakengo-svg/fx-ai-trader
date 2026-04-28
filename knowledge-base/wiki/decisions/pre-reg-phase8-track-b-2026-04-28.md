# Pre-reg LOCK: Phase 8 Track B — Micro-Sequence Pattern Discovery (2026-04-28)

## Status: rule:R1 — Sequence-dependent edge mining (Phase 8 master の Track B)

Phase 7 の static feature bucketing では捉えられない **3-5 bar sequence**
patterns に edge があるか empirical に検証する。Master plan:
`phase8-master-2026-04-28.md`。

このドキュメントは **encoding ロジックの LOCK** — 後追加・後変更はすべて
data dredging とみなされ無効。

---

## Pre-registered Pattern Encodings (LOCKED)

### P1: dir_seq_3 — 3-bar close-open direction triplet (27 patterns)

各 bar の close-open sign を {-1, 0, +1} に分類し triplet を作成。

```
sign(t) = +1  if (close - open) >  +eps × atr
        = -1  if (close - open) <  -eps × atr
        =  0  otherwise
eps = 0.05
pattern = (sign(t-2), sign(t-1), sign(t))
```

3^3 = **27 patterns**。bar(t-2), bar(t-1), bar(t) の **close** が確定した時点
の signal とする。Entry は bar(t+1).Open。

### P2: engulf_seq — 3-bar engulfing sequence (8 patterns)

bar(t) の body が bar(t-1) の body を engulf するかを binary 判定:

```
engulf(t, t-1) = max(open(t), close(t)) >= max(open(t-1), close(t-1))
                AND min(open(t), close(t)) <= min(open(t-1), close(t-1))
                AND |close(t) - open(t)| > 0.1 × atr  (real body 必須)

pattern = (engulf(t-1, t-2), engulf(t, t-1), dir(t))
where dir(t) = sign(close(t) - open(t)) in {+1, -1, 0} → binarize: +1 if >=0 else -1
```

2 × 2 × 2 = **8 patterns**。

### P3: wick_dom_seq — 3-bar dominant wick sequence (27 patterns)

各 bar の dominant wick を 3-state 分類:

```
upper_wick(t) = high(t) - max(open(t), close(t))
lower_wick(t) = min(open(t), close(t)) - low(t)
denom = max(|close(t) - open(t)|, 0.1 × atr)

ratio_diff = (upper_wick - lower_wick) / denom

state(t) = 'U'  if ratio_diff >  +0.5
         = 'L'  if ratio_diff <  -0.5
         = 'N'  otherwise

pattern = (state(t-2), state(t-1), state(t))
```

3^3 = **27 patterns**。

### P4: mom_exhaust_5 — 5-bar momentum exhaustion (2 patterns)

5 連続同方向 bar の rare event。

```
all_up_5  = all(sign(close(k) - open(k)) > 0 for k in [t-4..t])
all_dn_5  = all(sign(close(k) - open(k)) < 0 for k in [t-4..t])

pattern = 'UP5' if all_up_5
        = 'DN5' if all_dn_5
        = None  otherwise
```

**2 patterns**。Reversal predictor 候補 (BUY ∩ DN5 / SELL ∩ UP5 が priors)。

### P5: in_out_3 — 3-bar inside/outside-bar combination (9 patterns)

```
inside(t)  = high(t) <= high(t-1) AND low(t) >= low(t-1)
outside(t) = high(t) >= high(t-1) AND low(t) <= low(t-1)
state(t)   = 'IN'   if inside(t)
           = 'OUT'  if outside(t)
           = 'NORM' otherwise

pattern = (state(t-1), state(t))
```

3 × 3 = **9 patterns**。

---

## Encoding Total

| pattern_kind | n_patterns |
|---|---|
| dir_seq_3 | 27 |
| engulf_seq | 8 |
| wick_dom_seq | 27 |
| mom_exhaust_5 | 2 |
| in_out_3 | 9 |
| **合計 unique patterns** | **73** |

Cell grid: 73 patterns × 5 pairs × 2 dir × 3 forwards = **2,190 cells (max)**。
ただし N≥50 gate で大幅 trim。

---

## Pre-registered LOCK 設定 (Master 準拠)

```python
PAIRS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
DIRECTIONS = ["BUY", "SELL"]
FORWARD_BARS = [4, 8, 12]
HOLDOUT_DAYS = 90
TRAINING_DAYS = 275
SL_ATR_MULT = 1.0
TP_ATR_MULT = 1.5
N_MIN = 50              # sequence patterns は rare events のため緩和 (Phase 7 は 100)
WILSON_LOWER_MIN = 0.50
EV_PIP_MIN = 0.0
BH_FDR_Q = 0.10
HOLDOUT_WR_MIN = 0.50
```

---

## Trade Simulation (LOCK — 共通 trade_sim.py 再利用)

```
Entry: bar(t+1).Open  (signal は bar(t).Close 完了時点で生成)
SL:    1.0 × ATR(14)  (反対方向)
TP:    1.5 × ATR(14)  (RR=1.5)
Exit:  SL or TP、または forward_bars 経過後 close
Friction: friction_for(pair, mode="DT", session=session(t+1))
PnL_net = PnL_gross - friction_pip
```

---

## Stage Gate (LOCK)

### Stage 1 — Training scan (275d)
- N ≥ 50 (rare patterns 配慮)
- BH-FDR (q=0.10) significant
- Wilson_lower(95%) > 0.50
- EV_pip_net > 0

### Stage 2 — Holdout OOS (90d)
- 同 cell の holdout で WR > 0.50 ∧ EV_net > 0
- N_holdout ≥ 10 (low-bar、capacity 評価ではなく direction 確認)

---

## Look-Ahead Prevention (LOCK)

- Pattern encoding は **bar(t-2), bar(t-1), bar(t) の close 確定後**のみ計算
- Entry 価格は **bar(t+1).Open** (encoding と entry の間に 1 bar gap)
- ATR は bar(t) の値を使用 (bar(t).close 完了時点)
- Friction は entry bar (t+1) の session で評価
- Holdout window (last 90d) は Stage 2 まで一切触れない

---

## Cross-Track Overlap Check

既存の wick / sequence-related 戦略との潜在重複は report 段階で比較:

| 既存 | 重複可能性 |
|---|---|
| wick_imbalance_reversion (Osler 2003) | wick_dom_seq の特定 patterns と要比較 |
| liquidity_sweep | wick_dom_seq U/L state と要比較 |
| doji_breakout | dir_seq_3 で sign=0 含む patterns と要比較 |
| turtle_soup | mom_exhaust_5 の reversal lens と要比較 |

Report で各 surviving pattern について overlap を明記する。

---

## Reuse vs New (LOCKED)

### Reuse
- `tools/lib/trade_sim.py` (DRY simulation)
- `tools/bt_data_cache.py` (BTDataCache)
- `tools/pattern_discovery.py` の wilson_lower / benjamini_hochberg helper を inline コピー (依存最小化)

### New
- `tools/phase8_track_b.py` — sequence pattern encoding + Stage 1/2 統括
- 出力: `raw/phase8/track_b/`

---

## Rejection Criteria

以下のいずれかに該当する pattern は不採用:
1. Stage 1 で N<50 or gate 未通過
2. Stage 2 holdout で WR≤0.50 or EV≤0
3. 既存 phase 1-6 採用戦略と signal overlap > 50% (orthogonal でない)

---

## Audit 開始 commit hash

このドキュメントの commit 後、`tools/phase8_track_b.py` の encoding は本 LOCK
を準拠する。後 amend は禁止、別 pre-reg ドキュメントで管理。

---

## Related

- [[phase8-master-2026-04-28]]
- [[pre-reg-pattern-discovery-2026-04-28]] (Phase 7 reference)
