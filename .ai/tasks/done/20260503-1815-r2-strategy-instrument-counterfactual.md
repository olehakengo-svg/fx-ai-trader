---
id: 20260503-1815-r2-strategy-instrument-counterfactual
title: R2 — Strategy × Instrument 単位 demote counterfactual (TRUE_LIVE bucket only、Live=371 SSOT 確定後の再起動版)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T18:15:00+0900
revised_at: 2026-05-03T18:50:00+0900
roadmap_gate: Gate 0 復帰 (aggregate raw Kelly < 0 → ≥ 0、生存条件)
rule: R2
prerequisite_audit: 20260503-1722-gate-progression-audit (REJECT but 数値要再計算 — TRUE_LIVE bucket のみで再評価必須)
prerequisite_decision:
  - 2026-05-03 aggregate-kelly-decomposition-2026-05-03-corrigendum (TRUE_LIVE N=371 SSOT)
  - feedback_live_vs_shadow_strict_separation (memory) — Live ≠ is_shadow=0
---

## 0. なぜ書き直したか (rev2)

旧 task は `gate-progression-audit-2026-05-03.md` の主犯6戦略 (bb_rsi_reversion / fib_reversal / macdh_reversal / vol_surge_detector / sr_fib_confluence / sr_channel_reversal) を所与とした。**しかしその表は `is_shadow=0` フィルタで生成され、Bucket 3-split で見ると:**

- N=917 は TRUE_LIVE 736 + FLAG_DRIFT 181 の混合 (post-cutoff 未適用も含む)
- `fib_reversal` は TRUE_LIVE で **net +0.3pip 黒字** (USD_JPY -2.3 + EUR_USD +2.6)
- `vol_surge_detector` は TRUE_LIVE で **net +2.2pip 微黒字** (USD_JPY -9.4 + EUR_USD +11.6)
- `macdh_reversal` / `sr_fib_confluence` は TRUE_LIVE N<5 で Insufficient

→ 旧主犯リストは **黒字戦略を demote しようとしていた**。`feedback_live_vs_shadow_strict_separation` 違反。

ユーザー指示「LIVEとshadowは必ず切り分けて roadmap の設計もしてください、shadow はデータ蓄積用なので」に従い、TRUE_LIVE bucket only での再評価に書き直す。

## 1. 仮説

**H1**: TRUE_LIVE bucket (N=371) の Strategy × Pair 単位で N≥5 の出血セルを demote (lot=0) すると、aggregate raw Kelly が **0.0 以上** に復帰する。

**H2**: 全 demote は粗すぎる。**Bonferroni-significant edge を持つ Strategy × Pair は keep**、それ以外は STOP_OANDA、で aggregate raw Kelly が ≥ 0 に達する組合せが少なくとも1つ存在する。

**H3**: H2 の最適組合せでは MC60d 破産確率が **< 90%** に下がる。

**H4 (Tier 整合性)**: ELITE_LIVE / PAIR_PROMOTED の中に Live 出血戦略が含まれる場合、即時 WATCH 格上げを別アクションとして提案する。

**H5 (反証用)**: TRUE_LIVE bucket の Strategy × Pair をすべて demote しても aggregate raw Kelly < 0 のままなら、戦略 portfolio 抜本見直しが必要。

## 2. 対象データ / 分離 (LOCKED)

| 用途 | 出典 | 必須フィルタ |
|---|---|---|
| Live 集計 | Render API `/api/demo/trades?limit=100000` または `raw/snapshots/render-demo-trades-20260503.db` | `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN ('WIN','LOSS','BREAKEVEN') AND pnl_pips IS NOT NULL AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '2026-04-08'` |
| Strategy × Pair cell | `(entry_type, instrument)` group by | mode フィルタは **適用禁止** (旧 N=29 の暗黙バグ再発防止) |
| Counterfactual MC | `iterations=1000, horizon=60d, forward_trades=1875, ruin_dd=50% of 1000p` | hardcode 改善目標禁止 |
| Shadow データ | **混入禁止** (FLAG_DRIFT も同様に除外) | bucket 3-split 出力で証跡を残す |

## 3. TRUE_LIVE 真の出血ランキング (LOCKED 入力前提)

(corrigendum doc から転記、Strategy × Pair / N≥5 / sorted by Live PnL ascending)

| Strategy × Pair | N | WR | EV | PnL | Tier | demote 候補? |
|---|---:|---:|---:|---:|---|---|
| `vwap_mean_reversion` × GBP_USD | 5 | 20.0% | -11.62 | -58.1 | FORCE_DEMOTED | ✓ (既止血中、確認のみ) |
| `vix_carry_unwind` × USD_JPY | 7 | 28.6% | -6.04 | -42.3 | PAIR_PROMOTED | ✓ |
| `sr_channel_reversal` × USD_JPY | 22 | 22.7% | -1.40 | -30.8 | UNIVERSAL_SENTINEL | ✓ |
| `bb_rsi_reversion` × USD_JPY | 58 | 39.7% | -0.52 | -29.9 | PAIR_DEMOTED 該当? | ✓ (最大 N) |
| `session_time_bias` × GBP_USD | 7 | 28.6% | -4.00 | -28.0 | **ELITE_LIVE** | ⚠️⚠️ ELITE 出血、特別アクション |
| `bb_squeeze_breakout` × USD_JPY | 9 | 33.3% | -1.40 | -12.6 | PAIR_PROMOTED | ✓ |
| `bb_rsi_reversion` × EUR_USD | 12 | 25.0% | -0.97 | -11.6 | PAIR_DEMOTED 該当? | ✓ |
| `vol_surge_detector` × USD_JPY | 26 | 46.2% | -0.36 | -9.4 | SCALP_SENTINEL | borderline (Wlo 28.8% > BEV) |
| `engulfing_bb` × USD_JPY | 9 | 33.3% | -0.83 | -7.5 | PAIR_DEMOTED 該当 | ✓ |
| `engulfing_bb` × EUR_USD | 6 | 16.7% | -0.98 | -5.9 | PAIR_DEMOTED 該当 | ✓ |

### Live で黒字 (demote 候補から **必ず除外**)

| Strategy × Pair | N | WR | EV | PnL |
|---|---:|---:|---:|---:|
| `fib_reversal` × EUR_USD | 13 | 46.2% | +0.20 | +2.6 |
| `fib_reversal` × USD_JPY | 13 | 38.5% | -0.18 | -2.3 (合計 +0.3 → keep) |
| `vol_surge_detector` × EUR_USD | 6 | 66.7% | +1.93 | +11.6 |
| `vol_momentum_scalp` × USD_JPY | 13 | 61.5% | +0.90 | +11.7 |
| `dt_bb_rsi_mr` × USD_JPY | 7 | 57.1% | +1.50 | +10.5 |
| `ema_trend_scalp` × EUR_USD | 10 | 40.0% | +0.35 | +3.5 |
| `bb_squeeze_breakout` × EUR_USD | 5 | 40.0% | +0.56 | +2.8 |
| `bb_rsi_reversion` × GBP_USD | 5 | 40.0% | +0.42 | +2.1 |
| `trend_rebound` × EUR_USD | 8 | 37.5% | +0.25 | +2.0 |
| `stoch_trend_pullback` × EUR_USD | 9 | 33.3% | +0.21 | +1.9 |

## 4. 統計条件

- N≥5 で Strategy × Pair の Bonferroni 補正 (m = 該当 cell 数 ≈ 24, α/m = 0.05/24 ≈ 0.00208)
- WR / EV / Wilson 95% / PF / max DD / raw Kelly を Strategy × Pair ごとに計算
- counterfactual: **greedy worst-first** で Live PnL 寄与の大きい順に STOP し、aggregate raw Kelly が ≥ 0 を超える最小集合を特定
- 加えて **lot half** option も評価 (binary STOP のみではなく {KEEP, LOT_HALF=0.5x, STOP_OANDA=0x})

## 5. ACCEPT / REJECT / NEEDS_MORE 条件

- **ACCEPT**: 最小 demote 集合で aggregate raw Kelly ≥ 0 AND MC60d ≤ 90% を達成、かつ Live 黒字 cell は keep されている
- **NEEDS_MORE_EVIDENCE**: aggregate raw Kelly が +0.0 まで届かないが [-0.05, +0.0] の範囲に入る (Tier 1 LIVE 含む拡張可能)
- **REJECT (H5)**: 全 N≥5 出血 cell を STOP しても aggregate raw Kelly < -0.05 のまま → Tier 1 LIVE 戦略の再評価必要
- **ELITE_FLAG (H4)**: `session_time_bias × GBP_USD` の Live 出血を別アクション (即時 WATCH 格上げ recommendation) として final.md に明示

## 6. Scope

Codex MAY change:

- `tools/r2_strategy_instrument_counterfactual.py` (new) — TRUE_LIVE bucket only + bucket 3-split 出力 + Strategy × Pair greedy worst-first counterfactual + 3値 lot ({KEEP, LOT_HALF=0.5x, STOP_OANDA=0x})
- `tests/test_r2_strategy_instrument_counterfactual.py` (new) — bucket フィルタ unit test (FLAG_DRIFT/SHADOW が混入しないこと), counterfactual logic, Bonferroni m derivation, lot 3値 test
- `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (new) — verdict + 推奨 demote 組合せ + ELITE_FLAG section
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `app.py` (実装は別タスク、本タスクは LOCK proposal のみ)
- `modules/`, `strategies/`
- `tools/r2_cell_demotion_audit.py` (前タスク成果物、参照のみ)
- `tools/aggregate_kelly_decomposition_audit.py` (旧 N=29 バグ要素、別タスクで bucket 3-split 出力に修正)
- `wiki/decisions/aggregate-kelly-decomposition-2026-05-03*.md` (immutable)
- `wiki/decisions/gate-progression-audit-2026-05-03.md` (immutable, ただし数値は使わない)
- `.env`, OANDA secrets, production credentials, `live_ng_cells`
- 既存未コミット変更

## 7. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive)
- `wiki/decisions/aggregate-kelly-decomposition-2026-05-03-corrigendum.md` ★ **本タスクの SSOT**
- `wiki/decisions/aggregate-kelly-decomposition-2026-05-03.md` (旧 doc、TRUE_LIVE 関連数値は無視)
- `~/.claude/projects/-Users-jg-n-012-test-fx-ai-trader/memory/feedback_live_vs_shadow_strict_separation.md`
- `wiki/lessons/index.md` の `feedback_ma_filter_breaks_mr`, `feedback_partial_quant_trap`, `feedback_label_empirical_audit`, `feedback_live_shadow_separation`
- `tools/r2_cell_demotion_audit.py` (counterfactual 計算手法の参考)
- `tools/aggregate_kelly_decomposition_audit.py` (Wilson/Bonferroni helpers、ただし mode 暗黙フィルタは絶対に踏襲しない)

## 8. Acceptance Criteria

- [ ] `tools/r2_strategy_instrument_counterfactual.py --dry-run` で TRUE_LIVE 候補 grid (N≥5 cell list, bucket 3-split サマリ) を出力
- [ ] bucket 3-split 集計を必ず final report に含める (TRUE_LIVE / FLAG_DRIFT / SHADOW の N と PnL)
- [ ] `pytest tests/test_r2_strategy_instrument_counterfactual.py` pass
  - 必須テスト: `is_shadow=0 だが oanda_trade_id 空` 行が混入しないこと
  - 必須テスト: `mode='daytrade'` フィルタが暗黙適用されないこと (旧 N=29 バグ再発防止)
- [ ] `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` に: 対象 cell リスト / 各 cell の N/WR/EV/Wilson_lo/Bonferroni p / Bonferroni-significant cell の keep 印 / greedy 結果 / 最小 demote 集合 / aggregate post-cut Kelly/MC60d / verdict / ELITE_FLAG section
- [ ] verdict は `ACCEPT / NEEDS_MORE_EVIDENCE / REJECT` のいずれかを明示
- [ ] `.ai/runs/<run-dir>/final.md` に: 最小 demote 集合 (Strategy × Pair × lot multiplier), aggregate Kelly 改善幅, MC60d 改善幅, ELITE_FLAG (session_time_bias × GBP_USD), recommended next task
- [ ] `app.py`/`modules/`/`strategies/` 編集 0件

## 9. Verification Commands

```bash
# 0. データ取得 (Render reachable な環境で)
curl -sS --max-time 60 "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000" -o /tmp/live-trades-r2si.json

# 1. Dry-run (cell grid 確認)
python3 tools/r2_strategy_instrument_counterfactual.py --dry-run \
  --trades /tmp/live-trades-r2si.json

# 2. Tests (bucket フィルタ正しさ含む)
python3 -m pytest -q tests/test_r2_strategy_instrument_counterfactual.py

# 3. Production run
python3 tools/r2_strategy_instrument_counterfactual.py \
  --trades /tmp/live-trades-r2si.json \
  --output knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md \
  --mc-iterations 1000 --mc-horizon 60

# 4. Verdict 確認
grep -E "^Verdict:|^Aggregate post-cut|^Min demote set|^ELITE_FLAG" \
  knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md
```

## 10. Codex Instructions

これは **Rule 2 (Fast & Reactive)** タスク。Bonferroni 補正は `m = TRUE_LIVE 内の N≥5 Strategy × Pair cell 数` で適用、α'=0.05/m。

**絶対遵守**:
- データ集計の主条件は `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != ''`
- mode フィルタを暗黙適用しない (旧 N=29 バグ再発防止)
- Live で黒字 cell (`fib_reversal × EUR_USD` など §3 表) は demote 候補から **絶対に除外**
- Shadow / FLAG_DRIFT 行が aggregate Kelly 計算に混入していないことを test で証明
- bucket 3-split サマリを doc 冒頭に必ず提示

`feedback_ma_filter_breaks_mr` の罠回避: Bonferroni-significant edge cell は demote しない。

`feedback_success_until_achieved` 通り、verdict が ACCEPT 未満で closure 短絡禁止。NEEDS_MORE_EVIDENCE なら拡張範囲提案、REJECT なら H5 (Tier 1 LIVE 戦略再評価) を提案。

PR 作成は本タスクで実行しない。proposal doc 生成のみ。実装は Claude review 後の別 task で。

最終レポートには status, files changed, verdict, 最小 demote 集合, aggregate post-cut metrics, ELITE_FLAG (session_time_bias × GBP_USD), residual risks, 次タスクを含む。
