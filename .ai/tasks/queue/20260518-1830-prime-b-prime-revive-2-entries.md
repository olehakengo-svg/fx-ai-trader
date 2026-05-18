---
id: 20260518-1830-prime-b-prime-revive-2-entries
title: "[PRIME B' forward-fix] 2 entries を Tier B 0.05x で復活 (Micro LIVE 探索 grade で再評価)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-18T18:30:00+0900
roadmap_gate: "B (20260518-1700) の Task A keep thresholds は LIVE 昇格 grade (Wilson_lo≥0.40 / WF≥2/3) で、Micro LIVE 探索 grade (Wlo≥0.20 / WF≥1/3) ではなかった。司令塔 audit で 4 原則 (攻めは最大の防御、データ蓄積優先) との不整合を確認、過剰 demote の 2 entries を復活させる forward fix。探索 grade で再評価すると 6 entries 中: fib_reversal_PRIME (Wlo=0.265, WF=1/3) と sr_fib_confluence_GBP_ADXQ2 (Wlo=0.231, WF=2/3) は復活基準 PASS。bb_rsi_reversion_NY_ATRQ2 (Wlo=0.217 ✓, WF=0/3 ✗) は WF が zero-of-three で復活見送り。stoch_trend_pullback_PRIME / stoch_trend_pullback_LONDON_LOWVOL / engulfing_bb_TOKYO_EARLY は探索 grade でも Wlo<0.20 で fail、Tier C 維持。Shadow 30d EV=-1.53p は estimator bias (entry_price ベースでない、spread/slippage 保守) を含むため、実 fill での Micro LIVE 実測が真値推定に必要 ([feedback_shadow_first_quant_architecture](memory/feedback_shadow_first_quant_architecture.md))。"
rule: R1
related:
  - modules/prime_gate.py
  - tests/test_prime_gate_v2_apply.py
  - tests/test_prime_gate_order.py
  - tools/volume_live_promotion_watchdog.py
  - knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md
  - knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md
  - feedback_shadow_first_quant_architecture
  - feedback_spread_basis_for_mafe
  - feedback_codex_stash_leak
  - feedback_codex_schema_hallucination
---

# 0. 背景 (Claude 司令塔 forward-fix audit)

## 0.1 B の構造的欠陥

B (20260518-1700) は Task A の verdict を機械的に適用したが、私が P1 spec で設定した「keep thresholds」(Wilson_lo≥0.40 / WF≥2/3) は **LIVE 昇格 grade** であって **Micro LIVE 探索 grade** ではなかった。Micro LIVE は 0.1x-0.3x lot の探索枠であり、LIVE 昇格と同等のハードルを課すのは scope ミスマッチ。

## 0.2 探索 grade 再評価

| name | Wilson_lo | 探索 Wlo≥0.20 | 探索 WF≥1/3 | 探索 verdict |
|---|---:|:---:|:---:|:---:|
| stoch_trend_pullback_PRIME | 0.164 | ❌ | 2/3 ✓ | DEMOTE 妥当 (Wlo<0.20) |
| stoch_trend_pullback_LONDON_LOWVOL | 0.125 | ❌ | 1/3 ✓ | DEMOTE 妥当 |
| **fib_reversal_PRIME** | **0.265** | ✓ | 1/3 ✓ | **REVIVE Tier B 0.05x** |
| bb_rsi_reversion_NY_ATRQ2 | 0.217 | ✓ | 0/3 ❌ | DEMOTE 妥当 (WF zero) |
| engulfing_bb_TOKYO_EARLY | 0.156 | ❌ | 1/3 ✓ | DEMOTE 妥当 (元 Tier C) |
| **sr_fib_confluence_GBP_ADXQ2** | **0.231** | ✓ | 2/3 ✓ | **REVIVE Tier B 0.05x** |

## 0.3 lot 0.05x の根拠

| サイズ | base 1000u | 月間最悪損失推定 (per cell) | 用途 |
|---|---|---|---|
| 0.3x (Tier A original) | 3000u | -22.5p × N → 月最大 -67.5p | LIVE driver |
| 0.1x (Tier B original) | 1000u | -7.5p × N → 月最大 -22.5p | LIVE 軽量 |
| **0.05x (B' 探索)** | **500u** | **-3.75p × N → 月最大 -11p/cell** | **Micro LIVE データ収集** |

2 entries × 月最大 -11p = **-22p/月** のリスク枠で実 fill spread/slippage の真値を測定。

## 0.4 自動 demote safety net

[memory R2 15-cell LOCK SUPERSEDED 2026-05-11](memory/project_r2_15cell_lock_superseded_2026_05_11.md): `tools/volume_live_promotion_watchdog.py` が **Live N>=10 EV<0 で自動 demote**。本 task の 2 entries も同 watchdog 監視下に置く。N=10 蓄積 (Tier A/B fire 想定の ~30-60 日) 後に EV<0 確認なら自動 Tier C 化。

# 1. Pre-registered scope (LOCKED)

## 1.1 修正対象

`modules/prime_gate.py` のみ。

## 1.2 必須変更

### Step 1: ヘッダ docstring 更新

`## 2026-05-18 Re-evaluation outcome` セクションに `## 2026-05-18 forward-fix (B'):` を追記:

```
## 2026-05-18 forward-fix (B'):
# Revive 2 entries at Tier B 0.05x for Micro LIVE exploration:
# - fib_reversal_PRIME: Tier C 0.0 → Tier B 0.05 (Wlo=0.265 ≥ 0.20 exploration gate, WF 1/3 ≥ 1/3)
# - sr_fib_confluence_GBP_ADXQ2: Tier C 0.0 → Tier B 0.05 (Wlo=0.231 ≥ 0.20, WF 2/3 ≥ 1/3)
# Rationale: shadow EV is biased by entry vs signal price (feedback_spread_basis_for_mafe);
# Micro LIVE at 0.05x lot is a measurement tool, not a profit driver. Auto-demoted by
# tools/volume_live_promotion_watchdog.py at Live N>=10 EV<0 (existing R2 safety net).
# Other 4 entries remain Tier C (insufficient Wlo or WF for exploration grade).
```

### Step 2: `_PRIMES` の 2 entries を変更

**fib_reversal_PRIME**:
```python
# Before:
(
    'fib_reversal_PRIME',
    'fib_reversal',
    'C', 0.0,
    lambda f: (f["_conf_q"] == "Q3" and f["_cvema_q"] == "Q3"),
),

# After:
# Pre-reg LOCK 2026-05-18 forward-fix: revived at exploration grade.
# Original 2026-04-21: Tier A. Re-eval 2026-05-18: N=28 WR=42.9% Wlo=0.265 WF=1/3.
# Exploration grade gate (Wlo>=0.20 + WF>=1/3) PASS. Lot=0.05x (data collection).
(
    'fib_reversal_PRIME',
    'fib_reversal',
    'B', 0.05,
    lambda f: (f["_conf_q"] == "Q3" and f["_cvema_q"] == "Q3"),
),
```

**sr_fib_confluence_GBP_ADXQ2**:
```python
# Before:
(
    'sr_fib_confluence_GBP_ADXQ2',
    'sr_fib_confluence',
    'C', 0.0,
    lambda f: (f["instrument"] == "GBP_USD" and f["_adx_q"] == "Q2"),
),

# After:
# Pre-reg LOCK 2026-05-18 forward-fix: revived at exploration grade.
# Original 2026-04-21: Tier B. Re-eval 2026-05-18: N=19 WR=42.1% Wlo=0.231 WF=2/3.
# Exploration grade gate (Wlo>=0.20 + WF>=1/3) PASS. Lot=0.05x (data collection).
(
    'sr_fib_confluence_GBP_ADXQ2',
    'sr_fib_confluence',
    'B', 0.05,
    lambda f: (f["instrument"] == "GBP_USD" and f["_adx_q"] == "Q2"),
),
```

他の 4 entries (stoch_trend_pullback_PRIME, stoch_trend_pullback_LONDON_LOWVOL, bb_rsi_reversion_NY_ATRQ2, engulfing_bb_TOKYO_EARLY) は **不変** (Tier C 0.0 維持)。

## 1.3 不変条件 (DO NOT TOUCH)

- `EDGES` (2026-05-18 P1 値を維持)
- `classify_prime` 関数本体
- 他の `_PRIMES` entries (4 entries)
- `tests/test_prime_gate_order.py` の P0 hot-fix 検証ロジック
- `modules/demo_trader.py` (P0 hot-fix で既に PRIME A/B 経路 unblocked)

## 1.4 Watchdog 監視条件 (binding)

[tools/volume_live_promotion_watchdog.py](tools/volume_live_promotion_watchdog.py) の既存ロジックに依存:
- **Auto-demote 条件**: Live N>=10 かつ EV<0
- 該当時の動作: 当該 entry を `_PRIMES` から `Tier C 0.0` に自動降格 (or `_PAIR_DEMOTED` 相当の処置)
- 2 entries × Live N=10 蓄積を待つ期間: 推定 60-180 日 (PRIME predicate fire rate ~0.2-0.6/日 × 戦略 fire rate)

**本 task では watchdog logic 変更しない**。既存 R2 safety net がそのまま機能することを `tests/test_volume_live_promotion_watchdog.py` (or同等) で確認。

# 2. テスト要件

## 2.1 既存テスト更新

`tests/test_prime_gate_v2_apply.py` の以下 2 test を更新 (現在は「全 Tier C」前提):

```python
# Before:
def test_all_primes_are_tier_c():
    assert all(p[2] == "C" for p in _PRIMES)
def test_all_lot_multipliers_zero():
    assert all(p[3] == 0.0 for p in _PRIMES)

# After:
def test_4_primes_are_tier_c():
    tier_c = [p for p in _PRIMES if p[2] == "C"]
    assert len(tier_c) == 4
def test_2_primes_revived_at_tier_b_005x():
    revived = [p for p in _PRIMES if p[2] == "B" and p[3] == 0.05]
    assert len(revived) == 2
    names = {p[0] for p in revived}
    assert names == {"fib_reversal_PRIME", "sr_fib_confluence_GBP_ADXQ2"}
def test_no_tier_a_entries():
    # Until v3 candidates land, no Tier A
    assert all(p[2] != "A" for p in _PRIMES)
```

## 2.2 新規 sanity

`tests/test_prime_b_prime_revive.py`:

1. `test_fib_reversal_prime_match_returns_tier_b_005x` — `classify_prime` が fib_reversal + conf_q=Q3 + cvema_q=Q3 で `tier="B"`, `lot_multiplier=0.05` を返す
2. `test_sr_fib_confluence_match_returns_tier_b_005x` — sr_fib_confluence + GBP_USD + adx_q=Q2 で同
3. `test_stoch_trend_pullback_prime_still_tier_c` — Wlo<0.20 で revive されないことの regression
4. `test_bb_rsi_reversion_ny_atrq2_still_tier_c` — WF=0/3 で revive されないことの regression

## 2.3 既存 P0 hot-fix tests

```bash
python3 -m pytest tests/test_prime_gate_order.py -v   # P0 hot-fix の 7 test 全 PASS
python3 -m pytest tests/ -x -q                         # 全 suite regression なし
python3 scripts/check.py                               # KB consistency
```

## 2.4 Render API dry-run

`python3 tools/prime_gate_order_dry_run.py` を実行。期待: **PRIME B fires ≥ 6-12 件/30d (fib_reversal_PRIME + sr_fib_confluence_GBP_ADXQ2 の合算)、PRIME A fires=0、PRIME C fires=他 4 entries の合計**。

# 3. KB 更新 (同一 commit)

- `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md` に "B' forward-fix 完了 ✓" + 「LIVE 昇格 grade と探索 grade の区別」教訓を追記
- `knowledge-base/wiki/lessons/lesson-prime-b-grade-mismatch-2026-05-18.md` (新規) — 「Wilson_lo 閾値は LIVE 昇格と Micro LIVE 探索で異なる」教訓
- `knowledge-base/wiki/changelog.md` エントリ
- `tools/sync_kb_index.py --write` && `tools/tier_integrity_check.py --write`

# 4. 完了条件 (DoD)

- [ ] `modules/prime_gate.py` の 2 entries 復活反映
- [ ] `tests/test_prime_gate_v2_apply.py` 既存 test 更新 (3 test 通過)
- [ ] `tests/test_prime_b_prime_revive.py` 4 新規 test PASS
- [ ] `tests/test_prime_gate_order.py` 既存 7 test PASS (regression なし)
- [ ] `python3 -m pytest tests/ -x -q` 全 PASS
- [ ] `python3 scripts/check.py` ERROR=0
- [ ] `python3 tools/prime_gate_order_dry_run.py` 出力で PRIME B fires ≥ 6 件確認
- [ ] decision doc + 新 lesson doc 追記
- [ ] git commit + push
- [ ] `git log -1 origin/main -- modules/prime_gate.py` で push 確認 ([feedback_codex_stash_leak](memory/feedback_codex_stash_leak.md))

# 5. Out of scope

- 新 PRIME 候補追加 (C: 20260518-1730-prime-v2-shadow-audit-w4eda で進行中)
- 他 4 entries の lot 変更 (Tier C 維持)
- `volume_live_promotion_watchdog.py` のロジック変更 (既存 safety net で十分)
- `confidence_q4_gate.py` / emergency_trip の解除
- `modules/demo_trader.py` 変更 (P0 hot-fix で完了)
- EDGES 再計算 (P1 値維持)

# 6. 注意 (Codex)

- [feedback_shadow_first_quant_architecture](memory/feedback_shadow_first_quant_architecture.md): shadow EV<0 だけで demote 判定は estimator bias を真値扱いする error。Micro LIVE 0.05x は **測定装置**、profit driver ではない
- [feedback_spread_basis_for_mafe](memory/feedback_spread_basis_for_mafe.md): shadow EV は entry_price でなく signal_price ベース → spread 1.0p 分の擬陰性を含む
- [feedback_codex_stash_leak](memory/feedback_codex_stash_leak.md): final.md `ACCEPT` だけで完了させない、`git log/diff` で実 verify
- [feedback_codex_schema_hallucination](memory/feedback_codex_schema_hallucination.md): `modules/prime_gate.py` 現状を必ず実ファイル参照、推測禁止
- 復活 2 entries 以外は **DO NOT TOUCH** (post-hoc bias 回避)
- `bb_rsi_reversion_NY_ATRQ2` (Wlo=0.217 で gate 通過に見える) を誤って revive しないこと: WF=0/3 が決定的 fail
