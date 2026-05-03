---
id: 20260503-1840-tier1-live-edge-audit
title: A1 — Tier 1 LIVE 戦略 Live 実測 edge audit (R2 counterfactual REJECT 受け、Gate 0 救済の最後の経路)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T18:40:00+0900
roadmap_gate: Gate 0 (生存 — Tier 1 LIVE が真に edge を持つかの最終検証)
rule: R2
prerequisite_audit: 20260503-1815-r2-strategy-instrument-counterfactual (REJECT, all-target STOP でも raw Kelly=-0.25)
prerequisite_decision: 2026-05-03-1834-r2-strategy-instrument-counterfactual-reject
---

## 0. なぜ今このタスクか

R2 strategy × instrument counterfactual が **REJECT** で帰還:
- 6戦略 (bb_rsi_reversion / fib_reversal / macdh_reversal / sr_channel_reversal / sr_fib_confluence / vol_surge_detector) の **all-target STOP** でも aggregate raw Kelly = -0.2536, MC60d = 99.40%
- greedy post-cut で raw Kelly = -0.1932 (baseline -0.1737 より悪化)

drag を全除去しても Kelly < 0 のまま。残存 363 trade (Tier 1 LIVE + その他 small-N) **自体が負 EV**。仮説 H4 (Tier 1 LIVE 戦略再評価) を実測で検証する。

## 1. 仮説

**H1**: 5 つの Tier 1 LIVE / PAIR_PROMOTED cell について、Live 実測 (`is_shadow=0 oanda_trade_id != ''` filter) で:
- `gbp_deep_pullback × GBP_USD` (BT: N=77, WR=75%, EV=+1.064, PF=2.00)
- `trendline_sweep × GBP_USD` (BT: N=134, WR=73%, EV=+0.599, PF=1.68)
- `session_time_bias × USD_JPY` (BT: N=157, WR=79%, EV=+0.580, PF=2.46)
- `session_time_bias × EUR_USD` (BT: N=566, WR=70%, EV=+0.215, PF=1.34)
- `xs_momentum × USD_JPY` (BT: N=342, WR=69%, EV=+0.270, PF=1.43)

少なくとも 1 cell で Live Wilson_lo > BEV_WR (one-sided p < α'=0.05/5=0.010) を満たす **真の edge が残存**。

**H2**: aggregate Kelly が < 0 を解消するには、Tier 1 LIVE 5 cell の **少なくとも 2 cell で BT 期待を Live が満たす** 必要がある。実測でそうなるか。

**H3** (反証用): 5 cell 全てで Wilson_lo < BEV_WR → BT-Live divergence が systematic (構造的劣化) であり、`bt-live-divergence.md` の 6 楽観バイアス監査が必要。

## 2. 対象データ / 分離

| 用途 | 出典 | 混入禁止 |
|---|---|---|
| Live 集計 | `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status=CLOSED` Render API live trades | Shadow / OANDA非通過行 / XAU |
| Cell unit | `(strategy, instrument)` group by | hour bucket / time-of-day は集計しない |
| Statistical test | one-sided binomial test against per-pair BEV_WR | aggregate test 禁止 (cell 単位のみ) |

**Per-pair BEV_WR** (lockdown):
- USD_JPY: 34.4% / EUR_USD: 39.7% / GBP_USD: 37.9% / EUR_JPY: 33.7%

## 3. 統計条件

- Live N で WR / EV / Wilson 95% lo / PF / total pip / max DD / raw Kelly を cell ごとに計算
- N≥30 cell に **Bonferroni m=5** 適用 (Tier 1 LIVE 候補数)、α' = 0.05/5 = 0.010
- one-sided positive-edge binomial test: H0: p ≤ BEV_WR vs H1: p > BEV_WR
- BT 期待値との **delta-from-BT** 表: ΔWR / ΔEV / ΔPF を出力
- 30 ≤ N < 100 の cell には別途 NEEDS_MORE_EVIDENCE 表示 (sample 不足)

## 4. ACCEPT / NEEDS_MORE_EVIDENCE / REJECT 条件

- **ACCEPT**: 5 cell のうち **2 cell 以上**で `Wilson_lo > BEV_WR` AND `Bonferroni p < 0.010` AND `Live PF ≥ 1.10` AND `N ≥ 30` を満たす。Tier 1 LIVE が edge を保持。
- **NEEDS_MORE_EVIDENCE**: 1 cell のみが ACCEPT 条件を満たすか、N<30 で判定不能 cell が 3 つ以上ある。
- **REJECT (H3 fired)**: 5 cell 全てで Wilson_lo < BEV_WR (or Bonferroni p ≥ 0.010 で N≥30 cell について)。Tier 1 LIVE は Live で edge を喪失。Path B (`bt-live-divergence.md` 6 構造的楽観バイアス audit) へ分岐。

## 5. Scope

Codex MAY change:
- `tools/tier1_live_edge_audit.py` (new) — 5 cell の Live 実測 + Bonferroni + delta-from-BT
- `tests/test_tier1_live_edge_audit.py` (new) — Bonferroni m=5, BEV_WR per pair, delta-from-BT 計算 test
- `knowledge-base/wiki/decisions/tier1-live-edge-audit-2026-05-03.md` (new) — verdict + cell table + delta-from-BT
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:
- `app.py` (実装は別タスク。本タスクは LOCK proposal のみ)
- `modules/`, `strategies/`
- `tools/r2_strategy_instrument_counterfactual.py` (前タスク成果物、参照のみ)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (immutable)
- `.env`, OANDA secrets, production credentials, `live_ng_cells`
- 既存未コミット変更

## 6. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive, Rule 3 Immediate)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (REJECT 詳細)
- `.ai/decisions/2026-05-03-1834-r2-strategy-instrument-counterfactual-reject.md` (Claude review)
- `wiki/analyses/bt-live-divergence.md` (6 構造的楽観バイアス)
- `wiki/analyses/friction-analysis.md` (per-pair BEV_WR)
- `wiki/lessons/index.md` の `feedback_ma_filter_breaks_mr`, `feedback_label_empirical_audit`, `feedback_live_shadow_separation`, `feedback_partial_quant_trap`
- `tools/r2_strategy_instrument_counterfactual.py` (Live filter / Wilson / Bonferroni helpers の再利用)
- `tools/gate_progression_audit.py` (filter_closed_live_trades)

## 7. Acceptance Criteria

- [ ] `tools/tier1_live_edge_audit.py --dry-run` で 5 cell × per-pair BEV_WR × Bonferroni m=5 の grid を出力
- [ ] `pytest tests/test_tier1_live_edge_audit.py` pass
- [ ] `wiki/decisions/tier1-live-edge-audit-2026-05-03.md` に: 5 cell 各々の Live N / WR / Wilson_lo / EV / PF / total pip / max DD / Bonferroni p / **delta-from-BT (ΔWR/ΔEV/ΔPF)** / verdict
- [ ] verdict は `ACCEPT / NEEDS_MORE_EVIDENCE / REJECT` のいずれかを明示 + 根拠
- [ ] `.ai/runs/<run-dir>/final.md` に: 5 cell verdict, ACCEPT cell list (あれば), aggregate impact 推定, recommended next task (lot promotion or H3 棄却なら BT-Live divergence audit)
- [ ] `app.py`/`modules/`/`strategies/` 編集 0件

## 8. Verification Commands

```bash
# 1. Dry-run
python3 tools/tier1_live_edge_audit.py --dry-run

# 2. Tests
python3 -m pytest -q tests/test_tier1_live_edge_audit.py

# 3. Production run
curl -s 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000' -o /tmp/live-trades-tier1.json
python3 tools/tier1_live_edge_audit.py \
  --trades /tmp/live-trades-tier1.json \
  --output knowledge-base/wiki/decisions/tier1-live-edge-audit-2026-05-03.md

# 4. Verdict 確認
grep -E "^Verdict:|ACCEPT cell|delta-from-BT" knowledge-base/wiki/decisions/tier1-live-edge-audit-2026-05-03.md
```

## 9. Codex Instructions

これは **Rule 2 (Fast & Reactive)** タスク。Tier 1 LIVE の Live edge を **5 cell 単位で個別検証**。Bonferroni m=5 (Tier 1 LIVE は事前に narrow にlock済み)。

`feedback_partial_quant_trap` 回避: 必ず BT 期待 (KB / friction-analysis) と Live 実測の **delta** を表示。Live 単独 verdict は不可。

`feedback_success_until_achieved` 通り、verdict が ACCEPT 未満で closure 短絡禁止:
- NEEDS_MORE_EVIDENCE → N<30 cell の蓄積待ち or Shadow→Live 通路再点検
- REJECT (H3 fired) → BT-Live divergence 構造 audit (Path B) を提案

PR 作成は本タスクで実行しない。proposal doc 生成のみ。実装は Claude review 後。

最終レポートには status, files changed, verdict, 5 cell delta-from-BT 表, ACCEPT cell list, residual risks, 次タスクを含む。
