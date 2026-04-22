# Spread-at-Entry Gate Pre-Registration (2026-04-22)

**Status**: Pre-registered hypothesis document. **Analysis protocol only — no implementation proposed until OOS検証 PASS**.
**Trigger**: `tp-hit-quant-analysis-2026-04-20.md` において `spread_at_entry` が Bonferroni α=4.67e-4 を2桁下回る p=1.94e-05 で唯一の有意な TP-hit 予測因子として確認されたため、これを OOS で pre-register 検証する。

## 0. Meta — なぜ pre-register か

TP-hit 分析（107条件 × 698 WIN）で Bonferroni 通過した 5 因子のうち、`mafe_favorable_pips` と `mafe_adverse_pips` は **post-hoc tautological**（勝敗が確定してから計算される量）、`confidence` は既知の負相関アーティファクト ([[lesson-confidence-ic-zero]])、`score` は p=0.42 で無相関。**非 tautological かつ entry 時点で観測可能な唯一のエッジ** は `spread_at_entry` のみ。

ただし以下のリスクがある：

1. **Regime-shift fragility**: Pre/Post cutoff の 4-window 符号一致テストをまだ実施していない
2. **Pair-heterogeneity**: USD_JPY BEV=34.4% と GBP_USD BEV=37.9% で friction 構造が異なる。全体平均の p=1.94e-05 は pair-pooled で、分解すると有意性が消える可能性
3. **Session-confounding**: London session の spread=0.55pip vs Tokyo 2.10pip — spread_at_entry エッジが実は session エッジの confound の可能性

Bailey & Lopez de Prado (2014) 流儀で、**データを見る前に** 以下を確定させる。本文書確定後に OOS 検証を実行し、**結果が仮説と一致しなくても**閾値や仮説を後付けで動かさない。

---

## 1. Pre-registered Hypothesis

### H1 (Primary) — Spread Quantile ΔWR Monotonicity

post-cutoff 2026-04-16 以降の非XAU trades に対し、各 pair 毎に `spread_at_entry` を 4 quantile (Q1=lowest, Q4=highest) に分割したとき、**Q1 WR > Q4 WR** が成立する。

**事前予測符号**: ΔWR = WR_Q1 − WR_Q4 > 0（全 pair、session-adjusted）

**Effect size 予測**: `tp-hit-quant-analysis` の pooled Δmean=0.08pip が friction gap として効くと仮定。BEV shift ≈ Δspread / avg_range × 100 ≈ 1.0-1.5pp のWR lift を期待。**H1 PASS 閾値: ΔWR ≥ 1.5pp**（4 pair 中 3 pair 以上で満たす）。

### H2 (Secondary) — Session Confound Test

`spread_at_entry` エッジが session エッジの confound でないことを示すため、session 固定（London のみ）で同じ quantile 分析を実行。London 内でも ΔWR(Q1−Q4) > 0 が残るか検証。

**H2 PASS 閾値**: London subset で ΔWR ≥ 1.0pp（session-independent 成分の存在を示す最低線）。

### H3 (Tertiary) — Pair-wise Bonferroni

4 pair（USD_JPY, EUR_USD, GBP_USD, EUR_JPY）各々で独立検定。**H3 PASS 閾値**: Bonferroni 補正後 α=0.05/4=0.0125 を通過する pair が 2 以上。

### H4 (Gate Simulation) — Economic Significance

H1 PASS 後、`spread_at_entry > p75(per-pair, 30d rolling)` を entry block とする counterfactual gate を BT で適用。**H4 PASS 閾値**:
- 全 365d BT で `trade count` 減少が 25% 以下
- 残った trades の `PF ≥ 1.05 × baseline_PF`（i.e., 5%以上の PF lift）
- `Wilson下限 WR` が BEV_WR を上回る pair が 3 以上

---

## 2. Data / OOS 分割ルール

### 2.1 Universe
- Pairs: USD_JPY, EUR_USD, GBP_USD, EUR_JPY（XAU除外、EUR_GBP除外）
- Strategies: 全 PAIR_PROMOTED + ELITE_LIVE + SHADOW（tier-master.md 準拠、FORCE_DEMOTED 除外）
- Trade source: `GET /api/demo/trades?limit=5000` (Render prod)

### 2.2 分割
| Split | 期間 | 用途 |
|---|---|---|
| **IS** | 2026-04-16 (Cutoff) 〜 2026-04-22 | 本日分析済 (tp-hit-quant) |
| **OOS-1** (held-out) | 2026-04-23 〜 2026-05-07 (2週間) | **一次検証 — 本 pre-register の PASS/FAIL 判定** |
| **WF-1** | 2026-04-23 〜 2026-04-29 | Walk-Forward bucket 1 |
| **WF-2** | 2026-04-30 〜 2026-05-06 | Walk-Forward bucket 2 |
| **WF-3** | 2026-05-07 〜 2026-05-13 | Walk-Forward bucket 3 |

**WF PASS 要件**: 3 bucket 全てで ΔWR > 0 かつ EV > 0（1 bucket でも負 → regime依存、H1 FAIL）。

### 2.3 Backfill 要件
OOS-1 期間で N≥200 の post-cutoff trades が必要（pair毎 N≥50）。現行 trade rate (約 30 trades/日 shadow込) で達成見込。不足時は期間延長可、**ただし閾値は延長前の値を保持**。

---

## 3. 統計手続き（固定）

1. **WR 比較**: Fisher's exact test（per pair, per quantile pair）
2. **CI**: Wilson score 95% CI
3. **Multiple testing**: Bonferroni α=0.05/4 pair=0.0125（H3）、family-wise α=0.05（H1/H2）
4. **PF 比較**: bootstrap 5,000 resamples, 95% CI（H4）
5. **Kelly**: `stats_utils.kelly_criterion` で IS WR/payoff を入力、Half Kelly で lot 根拠

---

## 4. Decision Rules（執行後に改変不可）

| 結果パターン | 判定 | アクション |
|---|---|---|
| H1 ∧ H2 ∧ H3 ∧ H4 全 PASS | **STRONG PASS** | Spread quantile gate を prime_gate に実装提案（別 commit、BT根拠付き） |
| H1 ∧ H4 PASS、H2 FAIL | **WEAK PASS** | Session × spread の交互作用項付き gate のみ London で実装 |
| H1 PASS、H4 FAIL | **INCONCLUSIVE** | 経済的有意性なし → 実装せず、 KB 記録のみ |
| H1 FAIL | **FAIL** | 実装せず、`lesson-partial-quant-trap` に 1次検定通過≠エッジ実在の反例として追記 |

---

## 5. 禁止事項（post-hoc bias 排除）

1. OOS-1 期間終了前に partial 結果を見て閾値を動かさない
2. 追加 covariate を post-hoc に投入しない（H2 session 以外の confound 除外は IS で既済）
3. Kelly fraction は Half 固定。結果次第で Full に動かすなら別 pre-register が必要
4. 「spread_at_entry 以外に有意因子が見つかった」→ 本 pre-register の対象外、別文書で扱う

---

## 6. Related

- Evidence: [[tp-hit-quant-analysis-2026-04-20]] §Phase 5 Bonferroni table line 136
- Friction prior: [[friction-analysis]] per-pair BEV_WR
- Methodology: [[pre-registration-2026-04-21]] LIVE 監視の binding 基準
- Lessons: [[lesson-partial-quant-trap]], [[lesson-reactive-changes]], [[lesson-all-time-vs-post-cutoff-confusion]]
- Counterpart: [[regime-2d-v2-preregister-2026-04-20]] — 並行執行

---

## 7. Execution Timeline

| 日 | アクション |
|---|---|
| 2026-04-22 | 本 pre-register commit（本日） |
| 2026-04-23〜05-07 | OOS-1 データ蓄積（自動） |
| 2026-05-08 | rescan 実行、H1/H2/H3/H4 判定 |
| 2026-05-08+ | Decision Rules §4 に従って分岐 |

**判定スクリプト（未作成、rescan 時に実装）**: `scripts/spread_gate_oos_rescan.py`
