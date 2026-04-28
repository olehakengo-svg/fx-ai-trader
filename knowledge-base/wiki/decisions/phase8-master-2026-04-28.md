# Phase 8 Master Plan — Multi-Track Pattern Discovery (2026-04-28)

## Status: rule:R1 — Multi-track empirical edge mining

Phase 7 の single-feature scan で唯一の survivor は `hour=20 × JPY × SELL` で
既存 LCR-v2 と redundant。novel orthogonal edge 発掘には feature space 拡張が
必要。Phase 8 は **5 つの直交 information sources** を並列で別 session に
spawn し、cross-track de-dup 後 top 3 を採用する。

## 5 Tracks (orthogonal hypotheses)

### Track A — 3-Way Interactions
- Hypothesis: `hour × pair × bbpb_15m` 等の 3-way conditional edge
- Information: existing features の higher-order interaction
- Pre-reg LOCK: feature triplet space を pre-commit

### Track B — Micro-Sequence Patterns
- Hypothesis: 3-5 bar OHLC sequence patterns (engulfing seq, 3-bar momentum)
- Information: sequence encoding (時間順) — bucket では捉えられない
- Pre-reg LOCK: pattern enumeration を pre-commit

### Track C — Quantile-Bucketed Continuous
- Hypothesis: decile-bucketed ATR/BB/RSI (固定 threshold バイアス回避)
- Information: adaptive thresholding
- Pre-reg LOCK: quantile boundaries (per-pair specific) を pre-commit

### Track D — Session Boundary Transitions
- Hypothesis: Tokyo→London / London→NY / NY→Asia 境界 ±1h window
- Information: session crossing dynamics (in-session ではない)
- Pre-reg LOCK: 6 boundary windows (UTC time ranges) を pre-commit

### Track E — Regime-Stratified
- Hypothesis: HMM regime × hour × pair conditional edge
- Information: regime-conditional (constant features では消える)
- Pre-reg LOCK: regime buckets (existing regime_labeler) を pre-commit

## Common LOCK 設定 (全 tracks)

- Data: 365d × 5 majors (USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY)
- Holdout: 直近 90 日 (Phase 7 と同 window 維持、Stage 4 OOS)
- Trade simulation: SL=1ATR, TP=1.5ATR, RR=1.5、`tools/lib/trade_sim.py` 再利用
- Friction: friction_for(pair, mode="DT", session=current) cell-conditioned
- Look-ahead 防止: bar(t-1) close 以前 feature、bar(t) Open entry
- Gates: BH-FDR(0.10) → Bonferroni(0.05) → Stability → Holdout OOS

## Per-Track 制約

- Computational budget: 各 track 60 min
- Pre-reg commit: 各 track が `pre-reg-phase8-track-X-2026-04-28.md` を作成
- Output: `raw/phase8/track_<X>/stage{1,2,3,4}_<date>.json`
- Final survivors: 各 track 0-3 cells (top by Sharpe)

## Cross-Track Aggregation (master responsibility)

1. 各 track 完了後、master が 5 result JSON を読み込み
2. de-dup logic: 同じ underlying phenomenon (cell overlap > 50%、または
   feature/pair/dir/hour 同一) を 1 つに統合
3. 残った candidate を {Sharpe_per_event × Wilson_lower × capacity_score} で
   rank
4. **Top 3 のみ採用** (Bonferroni 通過後の cross-track adoption discipline)
5. それ以外は audit only (raw/phase8/ に保存、deploy せず)

## 採用後 deployment

- Top 3 cells を per-cell strategy file 化
- naming: `pd_track<X>_<descriptor>.py`
- Sentinel deploy (0.01 lot)、PAIR_PROMOTED に追加せず
- Live shadow 30 trade 蓄積後 cell_edge_audit で再判定

## 並行 task との関係

- (b) 既存 7 採用エッジの cell-level 深掘り (別 session で進行中) — 結果は
  Phase 8 の orthogonality check に併用

## 次のアクション (master responsibility)

1. ✅ 本 master plan commit
2. 5 tracks を独立 session で spawn (worktree 分離)
3. 完了通知を待ち、結果集約
4. top 3 を deploy、それ以外 audit only

## Track 別期待成果物

| Track | 期待 survivor | 計算時間 | 主リスク |
|---|---|---|---|
| A | 1-3 cells | 50-60 min | 3-way Bonferroni 重い、N 不足 |
| B | 0-2 patterns | 30-45 min | sequence encoding 設計依存 |
| C | 1-2 cells | 30 min | quantile bucketing で N 過小 |
| D | 0-2 cells | 20-30 min | session boundary effect 弱 (arbed) |
| E | 1-2 cells | 30-45 min | regime label 精度依存 |

合計期待 survivors: 3-11 cells (raw)、de-dup 後 3-5、final adoption top 3。
