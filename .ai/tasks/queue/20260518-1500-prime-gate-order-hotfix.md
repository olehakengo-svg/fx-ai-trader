---
id: 20260518-1500-prime-gate-order-hotfix
title: "[PRIME gate hot-fix] Move PRIME A/B override above Q4 + emergency-trip exempt for matched A/B (R3 structural bug)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-18T15:00:00+0900
roadmap_gate: "Render Live 30d (2026-04-18→2026-05-18, N=2004) で PRIME LIVE fire=0 を実測。Shadow 側で PRIME predicate は 36 件 match しているが、(a) emergency_trip が PRIME より先に _is_shadow=True を立てる (16 件), (b) Q4 gate が PRIME override より先に _is_shadow=True を立てる, (c) PRIME override は `not _is_shadow` 条件下でしか復活させない。結果 PRIME 経路の実 LIVE 発火 0/30d。同期間 EV+ shadow 6 戦略 (gbp_deep_pullback +7.75p, orb_trap +5.83p, ob_retest +2.68p 等) は PRIME base 外で永久 shadow ロック。4 原則 (攻める / 静的ブロック禁止) との整合性が崩れている。pre-reg freeze 2026-05-15 も期限切れ。本 task は構造バグの hot-fix のみで、PRIME re-evaluation (新 EDGES / 新候補) は別 task (P1)。"
rule: R3
related:
  - modules/demo_trader.py
  - modules/prime_gate.py
  - modules/confidence_q4_gate.py
  - knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md
  - knowledge-base/wiki/sessions/prereg-6-prime-strategies-2026-04-21.md
  - feedback_shadow_first_quant_architecture
  - feedback_codex_stash_leak
  - feedback_codex_mock_test_trap
  - feedback_partial_quant_trap
  - project_fxai_state_2026_05_11
---

# 0. 背景 (Claude 司令塔 audit 完了)

詳細: `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md`

## 0.1 観察 (Render API 30d)

| 指標 | 値 |
|---|---|
| 全 trade 数 | 2004 |
| LIVE trade 数 | 40 (うち PRIME 経由 = **0**) |
| PRIME predicate fire (shadow) | 36 件 |
| PRIME-tag を含む trade | **0/2004** |
| 最終 LIVE trade | 2026-05-14 (本日 4 日ドラウト) |
| portfolio edge | -0.23 / DD=47.22% |

## 0.2 死因 (`modules/demo_trader.py` 現行順序)

```
L4645    classify_prime() → _prime_tier 確定
L4774    _lot_ratio = min(_, _prime_lot_mult)   # cap だけは動く
L4822-30 EMERGENCY_TRIP vwap_mean_reversion     → _is_shadow=True
L4839-48 EMERGENCY_TRIP bb_rsi_reversion        → _is_shadow=True   ★Bug 1: 16件 NY_ATRQ2 全死
L4865-70 Q4 gate (conf>69, 4 strategies)        → _is_shadow=True   ★Bug 2: PRIME 復活不可
L4875-76 fallback: not promoted & not shadow & not PRIME A/B → _is_shadow=True
L4879-84 PRIME A/B override: _is_promoted=True   ← `not _is_shadow` 必須 (届かない)
L4890-4901 SHADOW_MODE Phase0 (PRIME exempt 既存)
```

# 1. Pre-registered scope (LOCKED)

## 1.1 期待される動作 (BINDING)

PRIME A/B の precedence を再構成:

```
1. classify_prime()                              # PRIME 判定
2. PRIME A/B → _is_promoted=True 確定             # ★ Q4 / 一般 shadow gate より先
   (PRIME A/B は emergency_trip 個別 exempt 判定)
3. EMERGENCY_TRIP vwap_mean_reversion            # 通常通り (PRIME に該当 base が無いので影響なし)
4. EMERGENCY_TRIP bb_rsi_reversion               # PRIME A/B = bb_rsi_reversion_NY_ATRQ2 ならば exempt
5. Q4 gate                                       # PRIME A/B (= fib_reversal_PRIME / bb_rsi_reversion_NY_ATRQ2) は exempt
6. fallback shadow                               # PRIME A/B exempt 既存維持
7. SHADOW_MODE Phase0 gate                       # PRIME A/B exempt 既存維持
```

## 1.2 修正対象 (修正ファイル)

- `modules/demo_trader.py` のみ。`prime_gate.py` / `confidence_q4_gate.py` は触らない (binding pre-reg)。
- 修正方針: PRIME A/B 通過個体に `_prime_live_lock=True` フラグを立て、後続 gate がこれを尊重する。

## 1.3 Pre-reg LOCK 値

| 項目 | 値 | 不変条件 |
|---|---|---|
| Tier A lot multiplier | 0.3 | `prime_gate.py` のまま |
| Tier B lot multiplier | 0.1 | `prime_gate.py` のまま |
| Tier C lot multiplier | 0.0 (never promote) | `prime_gate.py` のまま |
| Q4 exempt 対象 | PRIME A/B のみ | Tier C は exempt しない |
| emergency_trip exempt 対象 | PRIME A/B のみ | Tier C は exempt しない |
| Phase 0 SHADOW_MODE exempt | PRIME A/B のみ | 現行維持 |

## 1.4 Kill-switch (defensive)

env var `PRIME_OVERRIDE_ENABLED` (default=`1`)。`0` で hot-fix 全体を旧挙動に戻せる。

## 1.5 削除/降格 (動作変更による副作用回避)

- `BB_RSI_OANDA_TRIP` default 値は変更しない。**ただし PRIME A/B = `bb_rsi_reversion_NY_ATRQ2` 個体に限り bypass**。aggregate 戦略の trip は維持し、pre-registered cell のみ復活させる (multiple testing inflation 回避)。

# 2. 実装手順

## 2.1 修正 (modules/demo_trader.py)

### Step 1: PRIME A/B lock flag (L4645 直後に追加)

`_prime_tier` が `"A"` または `"B"` のとき `_prime_live_lock=True` を立てる。

```python
_prime_live_lock = bool(_prime_match and _prime_match.get("tier") in ("A", "B"))
if _prime_live_lock and _os.environ.get("PRIME_OVERRIDE_ENABLED", "1") != "1":
    _prime_live_lock = False
    self._add_log("[PRIME] override disabled via env (PRIME_OVERRIDE_ENABLED=0)")
```

### Step 2: emergency_trip exempt (L4822, L4840)

`if _VWAP_MR_OANDA_TRIP and entry_type == "vwap_mean_reversion":` → 条件に `and not _prime_live_lock` を AND 追加。
`vwap_mean_reversion` は PRIME base に無いため実害 0、対称性のため追加。

`if _BB_RSI_OANDA_TRIP and entry_type == "bb_rsi_reversion":` → 条件に `and not _prime_live_lock` を AND 追加。
これで `bb_rsi_reversion_NY_ATRQ2` (16件/30d) が pre-registered cell に限り復活。

### Step 3: Q4 gate exempt (L4865)

```python
if (not self._is_elite_live(entry_type, instrument)
    and not _prime_live_lock
    and _q4_should_shadow(entry_type, _q4_conf_val)):
```

### Step 4: PRIME override 簡素化 (L4875-4884)

L4875 と L4879 の二重チェックを統合し、Step 1 で `_prime_live_lock=True` を立てた個体は確実に `_is_promoted=True / _is_shadow=False` を持つ:

```python
# PRIME A/B fast-path (pre-reg override)
if _prime_live_lock:
    if _is_shadow:
        # Should not reach here due to gate-order fix, but defensive log
        self._add_log(
            f"[PRIME] WARN: _is_shadow=True under PRIME lock — "
            f"reverting (tier {_prime_tier} {_prime_match['name']})"
        )
    _is_shadow = False
    _is_promoted = True
    self._add_log(
        f"[PRIME] Live promote: {entry_type} {instrument} "
        f"→ LIVE (tier {_prime_tier}, lot {_prime_lot_mult:.2f}x)"
    )

# 既存 fallback (PRIME に該当しない trade のみ評価される)
if not _is_promoted and not _is_shadow:
    _is_shadow = True
```

### Step 5: tag persistence (alpha_snapshot)

PRIME 発火 trade を 30 日後に集計可能にするため、`alpha_snapshot` JSON に `"prime": {"name": ..., "tier": ..., "lot_mult": ...}` を書き込む (現状ログのみで DB 検索不能)。

該当書き込み箇所: alpha_snapshot を JSON 化している箇所を探し、`_prime_match` が non-None なら merge。

## 2.2 テスト (REAL, not mock)

[feedback_codex_mock_test_trap](memory/feedback_codex_mock_test_trap.md) — mock-only 10/10 PASS は信頼しない。

### Unit (mock OK)

`tests/test_prime_gate_order.py` を新規作成:

1. `test_prime_a_bypasses_q4`: fib_reversal_PRIME (Tier A) 個体で `confidence=85, conf_q=Q3` の場合に LIVE 通過 (Q4 gate は conf>69 で発動するが Q3 = conf<=69 なので元々排他)
2. `test_prime_b_bypasses_bb_rsi_trip`: bb_rsi_reversion_NY_ATRQ2 (Tier B) 個体で `BB_RSI_OANDA_TRIP=1` でも LIVE 通過
3. `test_prime_b_bypasses_q4`: bb_rsi_reversion_NY_ATRQ2 で confidence=80 (Q4 帯) でも PRIME 個体は LIVE 通過 (binding override)
4. `test_prime_c_stays_shadow`: engulfing_bb_TOKYO_EARLY は Tier C なので **LIVE 昇格しない** (lot=0)
5. `test_non_prime_q4_still_blocked`: ema_trend_scalp conf=80 は通常 Q4 gate で shadow (regression)
6. `test_non_prime_bb_rsi_still_tripped`: bb_rsi_reversion で NY_ATRQ2 predicate を満たさない個体 (例: London hour) は依然 trip kill (regression)
7. `test_prime_override_disabled_env`: `PRIME_OVERRIDE_ENABLED=0` で旧挙動 (PRIME LIVE fire 0)

### Integration (REAL Render API + dry-run)

`tools/prime_gate_order_dry_run.py` を新規作成:

1. Render Live API (`https://fx-ai-trader.onrender.com/api/demo/trades?limit=3000`) から過去 30 日 shadow trade を取得
2. 各 trade を `classify_prime()` で再判定 + 新 gate 順序を local replay
3. 出力: 新 gate 下で LIVE 化したであろう trade 数、PRIME 内訳、想定累積 PnL、想定 Wilson_lo
4. Pre-reg 期待値: PRIME A/B LIVE fire ≥ 6 件/30d, Tier A 0.3x ≥ 1 件, Tier B 0.1x ≥ 5 件

期待出力 (報告書に含めること):

```
=== Dry-run replay (new gate order, 30d Render data) ===
PRIME A: stoch_trend_pullback_PRIME    fires=N  est_pnl=±X.Xp
PRIME A: fib_reversal_PRIME            fires=N  est_pnl=±X.Xp
PRIME B: stoch_trend_pullback_LONDON   fires=N  est_pnl=±X.Xp
PRIME B: bb_rsi_reversion_NY_ATRQ2     fires=N  est_pnl=±X.Xp  (16件期待)
PRIME B: sr_fib_confluence_GBP_ADXQ2   fires=N  (PAIR_PROMOTED と重複)
PRIME C: engulfing_bb_TOKYO_EARLY      fires=0 (Tier C never)
Total NEW LIVE fires (est): N
Spread/slippage adjusted PnL est: ±X.Xp
```

### Production smoke (post-deploy)

1. deploy 後 24h で `/api/demo/trades` を polling
2. PRIME-tag を含む trade ≥ 1 件出現を確認 (4日ドラウト解消)
3. 解消しない場合は `PRIME_OVERRIDE_ENABLED=0` で即 rollback

## 2.3 KB 更新 (同一 commit に含める)

- `knowledge-base/wiki/changelog.md`: hot-fix エントリ追加
- `knowledge-base/wiki/strategies/` 内の PRIME 関連戦略カードに「2026-05-18 gate-order hot-fix」記述
- `knowledge-base/wiki/lessons/` に新規 lesson:
  `lesson-prime-gate-order-bug-2026-05-18.md` —「pre-reg 後に追加された emergency_trip / Q4 gate は pre-reg を死コード化する。新規 gate 追加時は既存 pre-reg との precedence を必ず明示」
- `tools/sync_kb_index.py --write` && `tools/tier_integrity_check.py --write` 実行

# 3. 完了条件 (DoD)

- [ ] `modules/demo_trader.py` の修正 5 ステップ全完了
- [ ] `tests/test_prime_gate_order.py` 7 test 全 PASS (`python3 -m pytest tests/test_prime_gate_order.py -v`)
- [ ] 既存 `python3 -m pytest tests/ -x -q` 全 PASS (regression なし)
- [ ] `python3 scripts/check.py` ERROR=0
- [ ] `tools/prime_gate_order_dry_run.py` 出力で PRIME A/B 復活件数 ≥ 6/30d を確認
- [ ] decision doc `prime-gate-promotion-path-bug-2026-05-18.md` に「Codex 実装完了 ✓」セクション追記
- [ ] git commit & push (origin/main) — [feedback_codex_stash_leak](memory/feedback_codex_stash_leak.md): final.md ではなく `git log/diff/stash list` で実 verify。stash@{X} 残し禁止。

# 4. Out of scope (この task では触らない)

- PRIME EDGES の再計算 (別 task: 20260518-XXXX-prime-reeval-and-candidates)
- 新 PRIME 候補追加 (gbp_deep_pullback / orb_trap 等 → 別 task)
- 5 経路統合 (ELITE/PAIR/GRAIL/C1/PRIME → 別 task、Phase C)
- `confidence_q4_gate.py` のロジック変更 (binding pre-reg)
- `prime_gate.py` 内の EDGES / lot_multiplier 変更 (binding pre-reg)
- emergency_trip の default 解除 (binding 解除条件未達)

# 5. 注意 (Codex)

- [feedback_codex_schema_hallucination](memory/feedback_codex_schema_hallucination.md): 既存コードは推測せず必ず `modules/demo_trader.py:4630-4910` を読んでから編集
- [feedback_codex_stash_leak](memory/feedback_codex_stash_leak.md): final.md `ACCEPT` だけで終わらせない。`git log --oneline -5 origin/main..HEAD` と `git stash list` を verify 出力に必ず含める
- [feedback_codex_mock_test_trap](memory/feedback_codex_mock_test_trap.md): unit mock PASS だけで終わらせない。Render API dry-run 必須
- Tier C (engulfing_bb_TOKYO_EARLY) は **never promote** の binding。誤って LIVE 復活させないこと
