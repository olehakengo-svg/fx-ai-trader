# Edge-Cell Stage-3 Direct LIVE Promotion (2026-05-26) [SUPERSEDED 2026-06-07]

## ⚠️ SUPERSEDED 2026-06-07

本 LOCK は [edge-cells-stage3-wilson-lo-restoration-2026-06-07.md](./edge-cells-stage3-wilson-lo-restoration-2026-06-07.md) で **supersede** されました。

理由: Wilson_lo 0.30 緩和 + watchdog 撤退条件で吸収という仮説が、12 日 LIVE で実証否決。5/12 cell (42%) が disable、watchdog Bearer auth bug で自動執行 1 ヶ月 silent、累積 -38,215 JPY。Wilson_lo は **Bonferroni-correct 0.55** に復帰。新規 Stage-3 promotion は本 doc ではなく restoration doc を参照。

以下は履歴参照用に残しています。

---

# Edge-Cell Stage-3 Direct LIVE Promotion (2026-05-26)

## Status
**rule:R1-EXCEPTION (intentional shadow-first exception, user judgment)** — **SUPERSEDED 2026-06-07**
LOCK timestamp: 2026-05-26 11 UTC (drafted; awaiting user sign-off before merge).
Same pattern as [Kalman D7 3-spec LIVE](../strategies/kalman_d7_3spec.md) and [vix_carry 1.0x intentional exception](./vix-carry-1x-exception-2026-05-21.md).

Stage 1 (Forward shadow) と Stage 2 (Micro-live) を**意図的にスキップ**し、Stage 3 (Scale-up with Kelly Half) から開始する。

## Why this pre-reg

ユーザー指示 (要約):
- 2026-05-06 以降の shadow trades 1,795件のうち Wilson_lo ≥ 0.30 を満たす **12 cell** を Stage 3 直行で LIVE 化
- Lot は **5,000 → 7,500 → 10,000 units** の ladder で 漸進拡大
- DD>5% / PF<1.0 / WR<pre-reg×0.7 で 1段降格 or shadow 強制復帰

司令塔判断: post-hoc selection bias で Kelly 推定は過大評価。Kelly Half = 19.3% (union portfolio) は理論値であり、selection-bias 補正後の現実 Kelly ≈ Kelly/10–20。ユーザー指定 5k-10k units は Kelly/100-200 に相当し十分保守的だが、撤退条件の自動執行 (watchdog) なしには blast radius が大きすぎる。本 pre-reg はその withdrawal trigger を LOCK する。

## Source data (LOCK)

- 期間: 2026-05-06 → 2026-05-26 (20 calendar days, 14 trading days)
- 母集団: Render `/api/demo/trades` is_shadow=1 / status=CLOSED / non-XAU
- N総数: 1,795 (overall WR=25.3%, EV=-2.24p, PF=0.63)
- Bonferroni m: ≈480 (12 cells × 軸組み合わせ 約40通り)
- α=0.05/480 = 1.04e-4 → 必要 Wilson_lo ≈ 0.55 (本 pre-reg は Wilson_lo ≥ 0.30 で緩和、selection bias は撤退条件で吸収)

## Target cells (LOCK, 12 cells)

| # | Cell | N | WR | EV (p) | PF | Wilson_lo | R:R | Half Kelly |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E1 | `dt_bb_rsi_mr` / session=ASN / direction=SELL | 13 | 100.0% | +10.29 | ∞ | **0.77** | n/a | n/a (no-loss) |
| E2 | `session_time_bias` / EUR_USD / session=LDN / mtf_gate_action=live_tier_exempt | 19 | 68.4% | +5.34 | 3.37 | 0.46 | 1.56 | 24.07% |
| E3 | `dt_bb_rsi_mr` / EUR_USD / direction=SELL | 16 | 68.8% | +5.59 | 4.20 | 0.44 | 1.91 | 26.18% |
| E4 | `bb_rsi_reversion` / session=NY / direction=SELL | 16 | 68.8% | +3.40 | 4.78 | 0.44 | 2.17 | 27.18% |
| E5 | `dt_bb_rsi_mr` / GBP_USD / direction=SELL | 22 | 63.6% | +3.56 | 2.19 | 0.43 | 1.25 | 17.26% |
| E6 | `rsk_gbpjpy_reversion` / GBP_JPY / direction=BUY | 12 | 66.7% | +10.10 | 3.12 | 0.39 | 1.56 | 22.65% |
| E7 | `dt_bb_rsi_mr` / GBP_USD / session=ASN | 12 | 66.7% | +5.10 | 5.14 | 0.39 | 2.57 | 26.84% |
| E8 | `session_time_bias` / EUR_USD / session=LDN | 36 | 52.8% | +2.79 | 1.92 | 0.37 | 1.72 | 12.67% |
| E9 | `orb_trap` / GBP_USD / direction=SELL | 13 | 61.5% | +10.98 | 9.25 | 0.36 | 5.78 | 27.44% |
| E10 | `wick_imbalance_reversion` / GBP_USD / v2_regime=no_go | 18 | 55.6% | +6.31 | 3.04 | 0.34 | 2.43 | 18.64% |
| E11 | `dt_bb_rsi_mr` / session=NY / direction=SELL | 28 | 50.0% | +3.23 | 2.04 | 0.33 | 2.04 | 12.73% |
| E12 | `sr_anti_hunt_bounce` / EUR_JPY (all sessions/dirs) | 10 | 60.0% | +8.44 | 5.44 | 0.31 | 3.63 | 24.49% |

### Cell overlap note
E2 ⊂ E8 (live_tier_exempt は LDN cell の部分集合)。E3/E5/E7/E11 は E1 の strategy 内部分集合。**Live 実行時は重複ヒットしても 1 trade 1 fill** (cell 判定はマッチ順優先度: E1 > E2 > E3 > ... > E12)。

## Filter logic (LOCK)

各 cell の フィルタは以下の attributes で完全一致:

```python
EDGE_CELLS = [
    # (cell_id, filters_dict, lot_stage1)
    ("E1",  {"strategy":"dt_bb_rsi_mr","session":"ASN","direction":"SELL"}),
    ("E2",  {"strategy":"session_time_bias","symbol":"EUR_USD","session":"LDN","mtf_gate_action":"live_tier_exempt"}),
    ("E3",  {"strategy":"dt_bb_rsi_mr","symbol":"EUR_USD","direction":"SELL"}),
    ("E4",  {"strategy":"bb_rsi_reversion","session":"NY","direction":"SELL"}),
    ("E5",  {"strategy":"dt_bb_rsi_mr","symbol":"GBP_USD","direction":"SELL"}),
    ("E6",  {"strategy":"rsk_gbpjpy_reversion","symbol":"GBP_JPY","direction":"BUY"}),
    ("E7",  {"strategy":"dt_bb_rsi_mr","symbol":"GBP_USD","session":"ASN"}),
    ("E8",  {"strategy":"session_time_bias","symbol":"EUR_USD","session":"LDN"}),
    ("E9",  {"strategy":"orb_trap","symbol":"GBP_USD","direction":"SELL"}),
    ("E10", {"strategy":"wick_imbalance_reversion","symbol":"GBP_USD","v2_regime":"no_go"}),
    ("E11", {"strategy":"dt_bb_rsi_mr","session":"NY","direction":"SELL"}),
    ("E12", {"strategy":"sr_anti_hunt_bounce","symbol":"EUR_JPY"}),
]
```

Session UTC bounds (LOCK):
```
ASN  : 00 - 07
LDN  : 07 - 13
NY   : 13 - 21
LATE : 21 - 24
```

`session_time_bias` 戦略の `session=LDN` は **entry_time UTC ∈ [07, 13)** で判定（既存 demo_trader の判定と同じ ロジック を流用）。

## Lot ladder (LOCK)

| 段階 | Trigger | Lot/cell (units) | Equivalent OANDA JP |
|---|---|---:|---:|
| **S1** | LOCK 直後 (Live N=0) | **5,000** | 0.5 ロット |
| **S2** | Live N ≥ 10 かつ Live EV > 0 かつ Live Wilson_lo ≥ 0.30 | **7,500** | 0.75 ロット |
| **S3** | Live N ≥ 30 かつ Live EV > +1.0p かつ Live PF ≥ 1.3 | **10,000** | 1.0 ロット |
| **-1** | 1段降格: DD_5d > 5% OR PF (Live N≥10) < 1.0 | one step down | |
| **STOP** | 強制 shadow 復帰: WR (Live N≥10) < 28% (= pre-reg WR 40% × 0.7) OR 単日 DD > 1.5% OR weekly DD > 3% | 0 (shadow only) | |

### Lot 計算根拠 (S1 = 5,000 units)

- Avg loss per trade @10k units: ¥861 (union mix, USDJPY=155 想定)
- @5,000 units: ¥430/trade avg loss
- 1セル 1.5 trades/day × 12 cells = ~18 trades/day (実 frequency 上限)
- 1日最悪損失 = 18 × ¥430 × loss_rate(42.3%) = ¥3,272/日 (期待値)
- Tail: 1日 5σ で約 ¥15,000 = 元本 ¥454,816 の 3.3% (許容範囲内)

## Withdrawal triggers (LOCK)

watchdog `tools/edge_cell_watchdog.py` が15分毎に実行し、以下を**自動執行**する:

### Per-cell triggers (Render KV `edge_cell_state[cell_id]` で管理)

1. **降格 (S3→S2 / S2→S1)**:
   - Live N ≥ 10 かつ PF < 1.0  →  1段降格
   - 5日 rolling DD > 5%  →  1段降格

2. **shadow 強制復帰 (S1→OFF)**:
   - Live N ≥ 10 かつ WR < 28%  →  cell disable
   - Live N ≥ 10 かつ EV < -1.0p  →  cell disable
   - 単日 cell DD > 1.5% (¥6,822) → cell disable
   - cell が 7日連続 fill 0 → cell pause (alive 確認)

### Global triggers (account-wide)

- 元本 DD > 8%  →  全 cell 一斉 OFF + Discord URGENT 通知
- 単日 account DD > 2%  →  全 cell S1 強制ダウン

### Cooldown
- shadow 強制復帰した cell は **N=30 shadow 再観察 + Wilson_lo ≥ 0.30 再達成** までは re-promote 禁止
- 降格は **N=10 + 再 trigger 条件達成**で 1段昇格再開

## Implementation tasks (Codex queue target)

1. **`modules/edge_cell_promote.py` 新規** — フィルタ判定 + lot 取得関数
2. **`modules/demo_trader.py` パッチ** — Tier gate 直前で `edge_cell_promote.match()` を呼び、合致時は force-live + dedicated lot
3. **`tools/edge_cell_watchdog.py` 新規** — Render cron で 15分毎、Live trades から per-cell stats を計算→撤退判定→ system_kv 更新→ Discord 通知
4. **`render.yaml` cron 追加** — `fx-ai-edge-cell-watchdog` を `*/3,18,33,48 * * * *` で (既存 cron と衝突しない slot)
5. **`tests/test_edge_cell_promote.py`** — 12 cell 全てに対し fixture trade で `match()` テスト
6. **DB migration** — `demo_trades` に `edge_cell_id TEXT DEFAULT ''` カラム追加 (post-mortem 用)
7. **wiki/index.md / tier-master.md 更新** — 12 cell の Tier 表示と LOCK doc リンク

## Quant guardrails (Codex spec 必須)

- **MASSIVE parquet 必須** — テストは `data/cache/massive/` を使う ([feedback_bt_must_use_massive](../lessons/lesson-bt-must-use-massive.md))
- **schema を spec に直貼り** ([feedback_codex_schema_hallucination](../lessons/lesson-codex-schema-hallucination.md)) — 上記の `demo_trades` schema + `edge_cell_id` migration を Codex prompt に明記
- **stash 漏れ verify** ([feedback_codex_stash_leak](../lessons/lesson-codex-stash-leak.md)) — Codex final.md だけで判断せず `git log/diff` で実 verify
- **mock-only test 禁止** ([feedback_codex_mock_test_trap](../lessons/lesson-codex-mock-test-trap.md)) — E2E で 1 cell 分の force-fire テストを含めること

## Pre-mortem (期待される失敗モード)

1. **均値回帰**: 12 cell の WR が overall shadow baseline (25.3%) に向かって回帰 → 全 cell が WR<28% で OFF。
   - 対応: watchdog 自動執行で blast radius 限定。
2. **collinearity 崩壊**: GBP_USD-pair の cell が 5/12 ある (E5/E7/E9/E10 + E1の一部)。GBP マクロイベント 1発で同時 drawdown。
   - 対応: account-wide DD 2%/日 trigger で同時降格。
3. **mtf_align=aligned 罠の再現**: Live 実行時に既存 MTF gate が aligned で fire を抑制すれば fire 0 リスク。
   - 対応: force-live ロジックで Tier/MTF gate を意図的にバイパス（cell マッチ時のみ）。
4. **shadow vs live spread divergence**: shadow は signal_price ベース、Live は actual fill。spread 2pip 増で EV 半減の cell あり (E4/E8/E11)。
   - 対応: S1 5,000 units で 2-3週観察 → 実 spread を含む Live EV で S2 判定。

## Success criteria

- 2026-06-23 (LOCK + 4週) 時点で:
  - Active cells ≥ 6/12 (50% 以上 survive)
  - Live cumulative ¥ > +¥30,000 (5k units で +¥30k = 元本 6.6%)
  - Max DD < 5%
- 達成失敗の場合: 全 cell shadow 復帰 → 別系統 (Price-Shock Phase B など) に資本振り替え

## Linked memories

- [feedback_shadow_first_quant_architecture](../../../../../.claude/projects/-Users-jg-n-012-test/memory/feedback_shadow_first_quant_architecture.md) — 本件は意図的例外
- [project_kalman_d7_regime_bound_live_2026_05_20](../../../../../.claude/projects/-Users-jg-n-012-test/memory/project_kalman_d7_regime_bound_live_2026_05_20.md) — 同型例外パターン
- [feedback_partial_quant_trap](../../../../../.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md) — Wilson/PF/Kelly Half 適用済
- [feedback_audit_purpose_design_not_n](../../../../../.claude/projects/-Users-jg-n-012-test/memory/feedback_audit_purpose_design_not_n.md) — N不足 cell も watchdog 付きで shadow→live 移行
- [project_fxai_state_2026_05_11](../../../../../.claude/projects/-Users-jg-n-012-test/memory/project_fxai_state_2026_05_11.md) — 現 DD 47%/ruin 3.8% 環境下の追加 lot は慎重に

## Sign-off

- [ ] User approval: 2026-05-26 ____ UTC
- [ ] Codex task queued: ____
- [ ] Implementation merged: ____
- [ ] Watchdog cron deployed: ____
- [ ] LOCK 発効: ____
