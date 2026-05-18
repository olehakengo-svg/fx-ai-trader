---
id: 20260518-1700-prime-gate-v2-apply-verdicts
title: "[PRIME v2 apply] Task A 監査結果を modules/prime_gate.py へ反映 (5 entries DEMOTE → Tier C, EDGES 再計算済)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-18T17:00:00+0900
roadmap_gate: "P1 (20260518-1530-prime-reeval-and-candidates) で Task A 完了: 6 PRIME のうち 5 entries が locked keep thresholds (Wilson_lo ≥ 0.40 / Bonf p×6 < 0.0083 for A, < 0.05 for B / WF EV+ ≥ 2/3) を全て fail。Sanity drift も `fib_reversal_PRIME` で確認 (freeze N=12 WR=75% EV=+2.96p → new N=28 WR=42.9% EV=-1.53p、small-N curve-fit が out-of-sample で崩壊)。Task B (768 cell × 6 戦略 = 4608 hypothesis Bonferroni grid) も全 NULL (Bonf pass=0, FDR pass=0)。司令塔判断 (rule:R3 構造 + 4 原則・shadow-first quant): hot-fix 構造は維持、5 失格 entries を Tier C lot=0 へ降格、engulfing_bb_TOKYO_EARLY は元 Tier C のまま KEEP。新候補 PRIME v2 は別 task (Task C: shadow EV+ 6 戦略 W4-EDA 風 8 軸 audit) で起票。本 task は機械的反映のみ。"
rule: R1
related:
  - modules/prime_gate.py
  - research/prime_gate_v2_proposal.py
  - knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md
  - knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md
  - tests/test_prime_gate_order.py
  - feedback_codex_stash_leak
  - feedback_codex_schema_hallucination
  - feedback_partial_quant_trap
---

# 0. 背景

P1 (`20260518-1530-prime-reeval-and-candidates`) の出力:
- `research/prime_gate_v2_proposal.py` — Codex 生成の差分適用済み draft
- `knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md` — verdict 詳細

司令塔判断: **新 EDGES + 5 entries DEMOTE** を `modules/prime_gate.py` に反映。Tier C 化により当該 cell が match しても `lot_multiplier=0` で **LIVE 昇格しない** (shadow 継続)。

## 0.1 適用後の挙動

| name | before | after | effect |
|---|---|---|---|
| stoch_trend_pullback_PRIME | A 0.3x | **C 0.0** | LIVE 昇格停止、shadow 継続 |
| stoch_trend_pullback_LONDON_LOWVOL | B 0.1x | **C 0.0** | 同上 |
| fib_reversal_PRIME | A 0.3x | **C 0.0** | 同上 |
| bb_rsi_reversion_NY_ATRQ2 | B 0.1x | **C 0.0** | 同上 |
| engulfing_bb_TOKYO_EARLY | C 0.0 | C 0.0 | 不変 (KEEP) |
| sr_fib_confluence_GBP_ADXQ2 | B 0.1x | **C 0.0** | 同上 |

副次効果:
- P0 hot-fix の gate-order 構造は維持される (`_prime_live_lock = bool(match and tier in ("A","B"))` は 今後 v3 で A/B が復活したら自動的に作動)
- Render Live `/api/demo/trades` で `alpha_snapshot.prime.tier == "C"` の Shadow trade が継続記録される (将来の re-eval 用)
- portfolio edge への影響なし (LIVE 経路は ELITE/PAIR/GRAIL/C1 で継続)

# 1. Pre-registered scope (LOCKED)

## 1.1 修正対象

`modules/prime_gate.py` のみ。

## 1.2 必須変更

### Step 1: ヘッダ docstring 更新

L1-20 (`"""..."""`) を更新:

- `2026-04-21` → 維持 (オリジナル pre-reg 日付)
- `frozen until 2026-05-15 re-evaluation` → `re-evaluated 2026-05-18; see knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md`
- "Tier A/B → LIVE 昇格" 説明はそのまま (構造維持)
- Note 追加: "Post-re-eval 2026-05-18 verdict: 5/6 entries failed keep thresholds and were demoted to Tier C (lot=0.0). engulfing_bb_TOKYO_EARLY remains Tier C as before. Awaiting v2 candidates from `20260518-XXXX-prime-v2-shadow-audit`."

### Step 2: EDGES を P1 出力で置換

```python
EDGES: Dict[str, List[float]] = {
    "confidence":         [54.0, 64.0, 71.0],
    "rj_adx":             [18.525844, 24.084449, 31.282508],
    "rj_atr_ratio":       [0.926959, 0.983332, 1.091413],
    "rj_close_vs_ema200": [-0.281692, -0.00188, 0.009222],
}
```

ソース: `research/prime_gate_v2_proposal.py` (P1 生成、5109 shadow non-XAU rows ベース、Render API 2026-04-02 → 2026-05-18)。

### Step 3: `_PRIMES` を 6 entries 全 Tier C lot=0.0 に書き換え

`research/prime_gate_v2_proposal.py` の `_PRIMES` block を **そのままコピー**。各 entry に Pre-reg LOCK コメント (N/WR/Wlo/Bonf_p/verdict) を保持。

### Step 4: コメントブロックの説明文を更新

L139-201 付近 (binding PRIME specifications コメント):
- "Tier A: Bonferroni-6 significant... → lot 0.3x small-lot LIVE trial" 説明は維持 (将来の v3 で復活可能性あり)
- 末尾に "## 2026-05-18 Re-evaluation outcome" セクションを追加し、全 6 entries の verdict と再評価日 (2026-05-18) を記載

## 1.3 不変条件 (DO NOT TOUCH)

- `classify_prime` 関数本体のロジック (Tier C + lot=0.0 は既存ロジックで「never promote」が成立する)
- `prime_fingerprint` 関数
- `_quartile`, `_session_of`, `_feature_bundle` 関数
- `_BY_BASE` map 構築 (entry_type → PRIME rules の dispatch)
- `__all__` exports

# 2. テスト要件

## 2.1 既存テスト (regression)

```bash
python3 -m pytest tests/test_prime_gate_order.py -v        # P0 hot-fix で生成済 (7 test)
python3 -m pytest tests/ -x -q                              # 全 suite
python3 scripts/check.py                                    # KB consistency
```

[feedback_codex_mock_test_trap](memory/feedback_codex_mock_test_trap.md): mock-only PASS で完了させない。

## 2.2 新規 sanity test (推奨追加)

`tests/test_prime_gate_v2_apply.py`:

1. `test_all_primes_are_tier_c` — `from modules.prime_gate import _PRIMES; assert all(p[2] == "C" for p in _PRIMES)`
2. `test_all_lot_multipliers_zero` — `assert all(p[3] == 0.0 for p in _PRIMES)`
3. `test_classify_prime_returns_tier_c_when_predicate_matches` — 元 Tier A の `stoch_trend_pullback_PRIME` (atr_q=Q1 + BUY) が match しても tier="C" lot_mult=0.0 を返す
4. `test_edges_match_p1_recomputation` — EDGES の各値が P1 出力と一致 (回帰防止)

## 2.3 Render Live dry-run

`python3 tools/prime_gate_order_dry_run.py` を実行し、PRIME A/B fires=0 (全 C 化により当然) を確認。出力をレポートに含める。

# 3. KB 更新 (同一 commit)

- `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md` に「v2 apply 完了 ✓」セクション追記
- `knowledge-base/wiki/changelog.md` エントリ追加: "PRIME v2 apply: 5 entries demoted to Tier C per P1 re-eval verdicts"
- `tools/sync_kb_index.py --write` && `tools/tier_integrity_check.py --write`

# 4. 完了条件 (DoD)

- [ ] `modules/prime_gate.py` の 4 step 反映完了
- [ ] `tests/test_prime_gate_v2_apply.py` 4 test PASS
- [ ] `tests/test_prime_gate_order.py` 既存 7 test PASS (regression なし)
- [ ] `python3 -m pytest tests/ -x -q` 全 PASS
- [ ] `python3 scripts/check.py` ERROR=0
- [ ] `python3 tools/prime_gate_order_dry_run.py` 出力で PRIME A/B fires=0 確認
- [ ] decision doc 追記
- [ ] git commit + push (single commit)
- [ ] `git log -1 origin/main -- modules/prime_gate.py` で push 確認 ([feedback_codex_stash_leak](memory/feedback_codex_stash_leak.md))

# 5. Out of scope

- 新 PRIME 候補追加 (Task C: 20260518-XXXX-prime-v2-shadow-audit)
- `modules/demo_trader.py` の gate logic 変更 (P0 で完了済)
- `modules/confidence_q4_gate.py` のロジック変更 (binding pre-reg)
- 5 経路統合 (ELITE/PAIR/GRAIL/C1/PRIME)

# 6. 注意 (Codex)

- [feedback_codex_schema_hallucination](memory/feedback_codex_schema_hallucination.md): `research/prime_gate_v2_proposal.py` を必ず実ファイル参照、推測禁止。EDGES 数値は研究 artifact からそのままコピー
- Tier C entries は LIVE 昇格しないが、shadow trade として記録される (これは設計通り、削除しない)
- 5 entries 「DEMOTE」は **削除ではなく Tier C 化** (将来の v3 で復活可能性を保つため structural preservation)


## Result (2026-05-18T09:08:43Z)

exit=0 · 557s

```
完了しました。`modules/prime_gate.py` に P1 の EDGES と全6 entry Tier C / `lot_multiplier=0.0` を反映し、KB更新・テスト追加・dry-runのv2全C期待値対応まで single commit で push 済みです。

Commit: `5e9bc0be` (`Apply PRIME v2 re-evaluation verdicts`)  
Push確認: `git log -1 origin/main -- modules/prime_gate.py` で同commitを確認済み。作業ツリーは clean です。

検証結果:

- `.venv/bin/python -m pytest tests/test_prime_gate_v2_apply.py -v` → 4 passed
- `.venv/bin/python -m pytest tests/test_prime_gate_order.py -v` → 7 passed
- `.venv/bin/python -m pytest tests/ -x -q` → 1530 passed, 1 skipped, 1 xfailed
- `python3 scripts/check.py` → 全6チェック通過 / ERROR=0
- `python3 tools/prime_gate_order_dry_run.py` → `Total PRIME A/B LIVE fires (est): 0`

補足: `scripts/check.py` は既存KB警告を出していますが、ERROR=0で整合性チェック自体は通過しています。
```
