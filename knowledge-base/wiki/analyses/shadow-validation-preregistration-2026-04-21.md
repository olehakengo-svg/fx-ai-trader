# Shadow Validation Pre-Registration — Golden Cells

**登録日**: 2026-04-21 (本日の shadow data に基づく golden cells を定義した時点)
**再評価期日**: 2026-05-05 (14 日後)
**最終期日**: 2026-06-02 (42 日後, 強制判定)

---

## 目的

[[win-conditions-mining-2026-04-21]] で抽出した "golden cells" (feature 組合せで WR >> baseline) が **持続性のある pattern なのか** **cherry-picking artifact なのか** を、追加 shadow 蓄積で判定する.

**binding**: 本文書の基準は LIVE データ蓄積前に固定. 事後変更は amendment log 必須.

---

## 1. 検定対象 Cells

| ID | 戦略 | 条件 | Baseline WR | 観測 WR (N=15-31) |
|---|---|---|---:|---:|
| H1 | ema_trend_scalp | `ema_stack_bull=1 ∧ ATR_ratio=Q3` | 24.1% | 51.6% (N=31) |
| H2 | stoch_trend_pullback | `ADX=Q1 ∧ ATR_ratio=Q1` | 29.2% | 66.7% (N=15) |
| H3 | stoch_trend_pullback | `direction=BUY ∧ ATR_ratio=Q1` | 29.2% | 61.1% (N=18) |
| H4 | sr_fib_confluence | `direction=BUY ∧ ATR_ratio=Q3` | 24.5% | 55.0% (N=20) |
| H5 | bb_squeeze_breakout | `close_vs_ema200=Q1` | 27.1% | 57.1% (N=21) |
| H6 | bb_rsi_reversion | `direction=BUY ∧ HMM=trending` | 26.6% | 55.0% (N=20) |
| H7 | ema_trend_scalp (post-cut) | `ema_stack_bull=1 ∧ ATR_ratio=Q3` | 22.3% | 52.4% (N=21) |

---

## 2. Decision Rules (pre-specified)

### 2.1 Persistence (H1-H7 各 hypothesis)

2026-05-05 時点で、同条件の shadow trade を N_new 追加蓄積した場合の判定:

| N_new (追加) | 判定ロジック |
|---|---|
| 0 ≤ N_new < 10 | **inconclusive** — 発火頻度不足。2026-06-02 に再判定持ち越し |
| N_new ≥ 10 | 以下の判定を実施 |

**追加 N_new trades の WR を観測**:

| 観測 WR_new | 判定 |
|---|---|
| WR_new ≥ baseline × 1.5 | **CONFIRMED** — pattern 持続 |
| baseline × 1.2 ≤ WR_new < baseline × 1.5 | **WEAKENED** — 効果縮小, monitor 継続 |
| baseline × 0.9 ≤ WR_new < baseline × 1.2 | **REGRESSED** — initial finding が cherry-picking bias |
| WR_new < baseline × 0.9 | **REJECTED** — 逆向き signal, hypothesis 破棄 |

### 2.2 Aggregate hypothesis (portfolio-level)

**"ATR_ratio quartile が真の regime indicator"** 仮説:

複数戦略 (ema_trend_scalp, stoch_trend_pullback, sr_fib_confluence) で "ATR-Q 依存性" が共通して見えた. 2026-05-05 時点で:

| 観測 | 判定 |
|---|---|
| 3 戦略中 ≥2 で pattern 維持 (CONFIRMED or WEAKENED) | **ATR_ratio quartile gate の実装候補** |
| 3 戦略中 ≥2 で REGRESSED/REJECTED | **ATR_ratio 仮説 retire** |

### 2.3 Early termination

以下のいずれかが発生した場合、2026-05-05 を待たず再評価:

- 対象戦略のいずれかが FORCE_DEMOTE / PAIR_DEMOTE された場合
- Fidelity Cutoff が再発生 (regime 大転換) した場合
- 対象 cell の N_new が 30 を超えた場合 (早期 N-acceleration)

---

## 3. Observation Protocol

### 3.1 Data source
`/api/demo/trades` (Render production API). `is_shadow=1 AND outcome IN ("WIN","LOSS")`

### 3.2 Cell definition (厳密に固定)

| Feature | 定義 |
|---|---|
| `ATR_ratio=Q1/Q3` | **2026-04-21 時点の strategy × shadow quartile edges** を保存. 新データでは固定 edges に sort-in |
| `ema_stack_bull=1` | regime JSON の `ema_stack_bull` field が true |
| `close_vs_ema200=Q1` | 同上, strategy × shadow quartile edges |
| `direction=BUY` | trade の `direction` field |
| `HMM=trending` | regime JSON の `hmm_regime` = "trending" |
| `ADX=Q1` | 同上, quartile edges |

### 3.3 Quartile edges の保存

本文書登録時点の quartile edges をここに固定 (各 strategy × feature ごと):

```
[PLACEHOLDER] — 2026-04-21 snapshot time の edges
実装: /tmp/win_conditions_mining.py 再走で再現可能
```

(実装メモ: edges 計算は data-dependent. 再評価時は `CUTOFF=2026-04-21` で cell ID 定義を再構成し、新データに対して固定 edges で binning する)

---

## 4. Multiple Testing Correction

H1-H7 (7 hypotheses) を並行検定. **Bonferroni α/7 = 0.0071** で family-wise error rate を制御.

2026-05-05 時点の Fisher exact test:
- `cell_WIN_new, cell_LOSS_new` vs `other_WIN_new, other_LOSS_new`
- p < 0.0071 で有意と判定 (Bonferroni 準拠)

効果量: Cohen's h または Cramer's V も併記.

---

## 5. Success / Failure Criteria (全体)

2026-06-02 最終時点で:

| Outcome | 条件 | Action |
|---|---|---|
| **成功** | H1-H7 中 ≥ 3 件が CONFIRMED + ATR_ratio aggregate hypothesis 成立 | ATR_ratio gate 実装を次セッション優先化 |
| **部分成功** | 1-2 件 CONFIRMED, 残り WEAKENED | cell 個別に shadow 継続蓄積 → LIVE promotion 判断先送り |
| **失敗** | ≥ 4 件 REGRESSED/REJECTED | "golden cell" 仮説 retire. Live promotion せず. |

---

## 6. Amendment Policy

本文書は **binding**:

- **誤字訂正**: 即時可、末尾に追記
- **観察期間延長**: N_new が 0 の場合のみ延長可 (2026-05-05 → 2026-06-02 へ自動スライド済み)
- **Decision rule 変更**: **不可**. 観察データ到来後の閾値変更は post-hoc bias の温床.

緊急停止: production に harm がある場合のみ user override.

---

## 7. Why pre-reg (methodological rationale)

[[shadow-tp-sl-causal-2026-04-21]] と [[win-conditions-unfiltered-2026-04-21]] で明らかになった問題:

1. **Cherry-picking 可能性**: 探索空間が大きく、"top 10 cells" の報告は survivor bias を含む
2. **事後評価の bias**: golden cell は「後付けで説明可能」に見えやすい (confirmation bias)
3. **Multiple testing inflation**: M 検定中 α=0.05 なら期待 M×0.05 false positives

**pre-reg = これらを制度的に排除する唯一の仕組み**.

本日の bb_squeeze / vol_surge × USD_JPY の [[pre-registration-2026-04-21]] と同じ philosophy.

---

## 8. Sign-off

- [x] 2026-04-21 作成. [[win-conditions-mining-2026-04-21]] の金 cells を binding 登録
- [ ] 2026-05-05 中間評価 — H1-H7 の N_new 確認
- [ ] 2026-06-02 最終評価 — 成功/失敗判定と action 決定
- [ ] Amendment log (none yet)

## 9. Related

- [[win-conditions-mining-2026-04-21]] — 探索元データ (filtered golden cells)
- [[win-conditions-unfiltered-2026-04-21]] — portfolio-wide unfiltered view
- [[shadow-tp-sl-causal-2026-04-21]] — regime 仮説の null finding
- [[pre-registration-2026-04-21]] — 本日の bb_squeeze/vol_surge LIVE promotion 用 pre-reg (姉妹文書)
