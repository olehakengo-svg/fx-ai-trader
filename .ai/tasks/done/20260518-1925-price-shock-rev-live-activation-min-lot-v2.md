---
id: 20260518-1925-price-shock-rev-live-activation-min-lot-v2
title: "[Price-Shock Tier 1 5 戦略 Live Activation v2] MIN lot で本番起動 (rule:R1 — Shadow-first 緩和、BT Wilson_lo>=0.58 高品質根拠)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-18T19:25:00+0900
roadmap_gate: "Phase B-1 (commit 35961351) で 5 戦略を HourlyEngine 登録 + demo_trader 統合済。1809-hourly-engine-shadow-ramp-activation (commit 458392d8) で 10 daytrade_1h_* mode を auto_start=True 化、Shadow ramp 開始。しかし司令塔指示「Live 含めて動かして」は未達: PRICE_SHOCK_REV_TIER1_TYPES が FORCE_DEMOTED に残存、_shadow_always frozenset で 5 戦略を Shadow 強制中。前 spawn 投入の `20260518-1730-price-shock-rev-live-activation-min-lot` task は queue から消失 (1809 と重複と判断され drop されたと推定)。本 v2 task で MIN lot Live activation を実装する。"
rule: R1
related:
  - modules/demo_trader.py                                    # FORCE_DEMOTED / PRICE_SHOCK_REV_TIER1_TYPES
  - strategies/hourly/__init__.py                             # _shadow_always frozenset
  - strategies/hourly/price_shock_reversion_base.py          # 共通基底
  - strategies/hourly/price_shock_rev_*.py                   # 5 戦略
  - knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md
  - knowledge-base/wiki/decisions/hourly-engine-shadow-ramp-2026-05-18.md
  - tools/volume_live_promotion_watchdog.py                  # 既存 watchdog pattern
  - feedback_shadow_first_quant_architecture
  - feedback_live_shadow_separation
  - feedback_partial_quant_trap
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_exclude_xau
  - project_price_shock_reproduction_success_2026_05_15
  - project_fxai_state_2026_05_11
  - .ai/tasks/done/20260518-1352-price-shock-rev-phase-b1.md
  - .ai/tasks/done/20260518-1809-hourly-engine-shadow-ramp-activation.md
---

# 0. 司令塔指示 (literal)

| 項目 | 指示 |
|---|---|
| Live execution | **有効化** (5 戦略の `is_shadow=True` 強制を撤廃) |
| Lot size | **MIN lot** (各 pair の最小取引単位、既存戦略の min_lot pattern を literal 踏襲) |
| Auto-start | **継続 True** (1809 task が既に 10 mode を auto_start=True 化済、変更不要) |
| EUR_GBP/EUR_AUD shared lock | **維持** (Live でも同時 active position 1 個まで) |
| KSB/DMB | **Shadow 維持** (α 不在判定中、本 task では Live 化しない) |
| Pre-reg promote criteria | **維持** (Live N>=30 + Wilson_lo>=0.50 + Bonferroni m=5 + 6 週 EV>0 → lot ramp 司令塔別判断) |

## 0.1 Why Live (Shadow-first 原則の緩和根拠)

5 戦略の BT 品質:
- Wilson_lo ≥ 0.58 (5/5 strategy)
- Bonf-passing cells: 9-28 per family (multiple independent confirmations)
- 12.3y MASSIVE データ + BH-FDR m=3744 (post-hoc selection 排除)
- Cross-pair 5 family (single-pair selection effect 不在)
- Qiita 原典 AUDJPY WR=60.06% を WR=60.00% で再現 (methodology 妥当性)

この品質を Shadow 観測待ち 6 週間で潰すよりも、MIN lot で Live 蓄積を始めるほうが時間効率上回る。Live regime shift risk は watchdog (N=10 EV<0 で auto demote) と MIN lot exposure で bound。

# 1. 実装仕様

## 1.1 demo_trader.py 変更

### 1.1.1 PRICE_SHOCK_REV_TIER1_TYPES を `_FORCE_DEMOTED` から除外

現状 (line 57-63):
```python
PRICE_SHOCK_REV_TIER1_TYPES = frozenset({
    "price_shock_rev_eur_gbp_h1_long",
    ...
})
```

変更:
- `PRICE_SHOCK_REV_TIER1_TYPES` 自体は **保持** (downstream check で使う、例: line 2262 の MIN lot 判定)
- ただし `self._FORCE_DEMOTED` set に含まれている場合は **除外**
- 具体的に `FORCE_DEMOTED` の構築箇所 (DemoTrader.__init__ 内、`_FORCE_DEMOTED = frozenset({...})` を探す) で 5 戦略を含めない

### 1.1.2 MIN lot 設定

5 戦略の lot 計算ロジックを変更:
- 既存戦略の MIN lot pattern: 各 pair の最小取引単位 = 1,000 units (OANDA standard)
- `lot_multiplier` 設定箇所で `PRICE_SHOCK_REV_TIER1_TYPES` の entry_type に対して **min_lot=1000** (or pair-specific min) を返す
- `risk_analytics` の Kelly 計算で MIN lot を尊重 (Kelly half 等の自動 ramp を bypass)

### 1.1.3 EUR_GBP/EUR_AUD shared lock の Live 適用

既存 shared lock (1809 task で実装済) が Live でも有効か確認:
- もし Shadow only の制御だったら Live にも拡張
- 同時 active position 1 個制限が Live position に効くこと、test で検証

## 1.2 strategies/hourly/__init__.py 変更

### 1.2.1 _shadow_always frozenset から 5 戦略を削除

現状 (line 29-39):
```python
_shadow_always = frozenset({
    "price_shock_rev_eur_gbp_h1_long",
    "price_shock_rev_eur_aud_h1_long",
    "price_shock_rev_usd_cad_h1_long",
    "price_shock_rev_nzd_jpy_h1_long",
    "price_shock_rev_aud_jpy_h1_long",
    "keltner_squeeze_breakout",
    "donchian_momentum_breakout",
})
```

変更後:
```python
_shadow_always = frozenset({
    # KSB+DMB Shadow ramp 2026-05-18: v2.1 alpha absence reevaluation. 
    # Maintained as Shadow-only.
    "keltner_squeeze_breakout",
    "donchian_momentum_breakout",
})
# Price-Shock Rev 5 戦略は 2026-05-18 Live activation v2 (本 task) で Shadow 強制解除。
# Live signal は通常パスで emit され、demo_trader の通常 lot 計算 (本 task で MIN lot に変更) を経由。
```

### 1.2.2 split_shadow_always() の挙動確認

`split_shadow_always(candidates, best)` は `_shadow_always` リストの戦略を **best 以外の候補も shadow emit** する仕組み。
- 5 戦略を frozenset から外したので、best 以外の price_shock_rev signal は emit されない (best のみ Live emit)
- これは意図通り (Shadow always-emit から Live single-best emit への切替)

## 1.3 Watchdog (新規)

`tools/price_shock_rev_live_watchdog.py` 新規作成:
- Render production の `/api/demo/trades` から 5 戦略の **Live trade (is_shadow=0)** のみを集計
- Live N >= 10 達成時に集計:
  - cumulative pnl_pips
  - Wilson_lower for win rate
  - EV (pip)
- **判定**: Live N >= 10 AND (EV < 0 OR Wilson_lower < 0.40) → **auto demote**
  - 該当 5 戦略の entry_type を `FORCE_DEMOTED` に動的追加 (state file または DB)
  - Discord 通知 (赤): "🚨 Price-Shock Rev {strategy}: Live N={N} EV={ev} → AUTO DEMOTE"
- **判定**: Live N >= 10 AND EV >= 0 AND Wilson_lower >= 0.40 → **継続観察通知**
  - Discord 通知 (緑): "✅ Price-Shock Rev {strategy}: Live N={N} EV={ev} → 継続"
- スケジューラ: 4 時間毎 cron (既存 scheduled-tasks MCP 経由、または `tools/scheduled-tasks/*`)

既存 `tools/volume_live_promotion_watchdog.py` のパターン (Live N>=10 EV<0 で auto demote) を pattern 踏襲。

## 1.4 Promote evaluator (新規)

`tools/price_shock_rev_promote_evaluator.py` 新規作成:
- Live N >= 30 達成時の **lot ramp 提案** evaluator
- 各戦略について:
  - Live trades から WR / Wilson_lower / Bonf-corrected p-value (m=5, 5 戦略同時 promote 判定) を計算
  - 6 週間 sliding window EV を計算
- **lot ramp 提案条件 (全 pass)**:
  - Live N >= 30
  - Wilson_lower >= 0.50
  - Bonferroni-corrected p < 0.01 (m=5)
  - 6 週間 EV > 0 (slide every week)
- **判定通過時**: Discord 通知 (青): "📈 Price-Shock Rev {strategy}: Live N=30 達成、lot ramp 提案 司令塔へ"
- **重要**: lot ramp は **自動禁止**、司令塔が別 task で承認後に lot_multiplier を増やす

## 1.5 KB / tier-master 更新

1. `knowledge-base/wiki/decisions/price-shock-rev-live-activation-2026-05-18.md` 新規作成:
   - 本判断の文書化 (Shadow-first 緩和の根拠、BT 品質 evidence、MIN lot で exposure 最小化)
   - 5 戦略 × 7 pair の Tier 移行: Tier 3 (Shadow) → Tier 2 (Live MIN lot ramp)
   - Pre-reg promote criteria の維持確認

2. `knowledge-base/wiki/strategies/price_shock_rev_{name}.md` 5 ファイルを Live=有効に更新:
   - Tier 行を "Tier 2 (Live MIN lot)" に変更
   - "Live activation 2026-05-18" 行追加
   - Pre-reg promote criteria へのリンク

3. `knowledge-base/wiki/tier-master.{json,md}`:
   - 5 戦略を Tier 2 に移行
   - `python3 tools/sync_kb_index.py --write`
   - `python3 tools/tier_integrity_check.py --write` で ERROR=0 確認

4. `CHANGELOG.md` + `knowledge-base/wiki/changelog.md` に rule:R1 エントリ追加

## 1.6 テスト

`tests/test_price_shock_rev_live_activation_v2.py` 新規:

1. **Force demote 解除確認**: 
   - `_FORCE_DEMOTED` に 5 戦略が含まれていないことを assert
   - `_check_force_demoted_gate()` 関数で is_shadow=False のまま return される ことを test (`PRICE_SHOCK_REV_TIER1_TYPES` の entry_type を引数に渡す)

2. **MIN lot 計算検証**:
   - 5 戦略の各 entry_type で `compute_lot_size()` (or 該当関数) を call、return が pair の min trade size と一致することを assert

3. **_shadow_always frozenset 検証**:
   - HourlyEngine._shadow_always に 5 戦略が **含まれていない** こと
   - KSB/DMB は **含まれている** こと

4. **Shared lock 動作確認**:
   - mock しない: 実 demo_trader instance で EUR_GBP に active position がある状態で EUR_AUD signal を emit → trade はキャンセル (or block) されることを test
   - 逆も同様 (EUR_AUD active で EUR_GBP block)

5. **Watchdog 動作**:
   - mock しない: 既知の trade history を SQLite に投入、watchdog を run、auto demote ロジックが意図通り動作することを assert

6. **Promote evaluator**:
   - 同じく real DB で test、N=30 達成時の Bonf p-value 計算が正しいことを assert

7. **既存 test pass 維持**:
   - `tests/test_price_shock_rev_strategies.py` (7 tests, Phase B-1) の Shadow テストが引き続き pass する **か、または Live 化により失敗する場合は適切に更新**
   - `tests/test_pine_overlay_equivalence.py` (12 tests, TV overlay) は影響なしのはず

# 2. 完了条件

1. `modules/demo_trader.py` 変更 (PRICE_SHOCK_REV_TIER1_TYPES の FORCE_DEMOTED 除外 + MIN lot 設定 + shared lock Live 対応)
2. `strategies/hourly/__init__.py` 変更 (5 戦略を _shadow_always から削除、KSB/DMB は維持)
3. `tools/price_shock_rev_live_watchdog.py` 新規 (Live N=10 watchdog)
4. `tools/price_shock_rev_promote_evaluator.py` 新規 (Live N=30 evaluator)
5. `tests/test_price_shock_rev_live_activation_v2.py` 新規 (上記 7 検証、mock 禁止)
6. `knowledge-base/wiki/decisions/price-shock-rev-live-activation-2026-05-18.md` 新規 (判断文書化)
7. `knowledge-base/wiki/strategies/price_shock_rev_*.md` 5 ファイル更新 (Tier 2)
8. `knowledge-base/wiki/tier-master.{json,md}` 更新 (5 戦略 Tier 2)
9. `CHANGELOG.md` + `knowledge-base/wiki/changelog.md` rule:R1 エントリ
10. `python3 tools/sync_kb_index.py --write` && `python3 tools/tier_integrity_check.py --check` (ERROR=0)
11. 既存 test (`test_price_shock_rev_strategies.py` 7 件、`test_pine_overlay_equivalence.py` 12 件) pass 確認 (Live 化で失敗する test は適切に更新、ただし pre-reg LOCK 定数の literal 検証等は変更禁止)
12. commit + push (`--no-verify` 可): "feat(price_shock_rev): Tier 1 5 戦略 Live activation v2 MIN lot (rule:R1)"
13. Render auto-deploy 確認: `curl /api/demo/status` で 5 戦略の next signal が Live emit を含むことを確認 (signal emit 前なら hourly bar wait)
14. `git status` clean (untracked artifact は無視可、final.md 明記)

# 3. 司令塔ガード

## 3.1 必須遵守

- [ ] **MIN lot literal**: 通常 lot や lot_multiplier=1.0 に勝手に変更禁止 (各 pair の min trade unit)
- [ ] **5 戦略のみ変更**: KSB/DMB は _shadow_always 維持、他既存戦略の Live status は変更しない
- [ ] **Shared lock 維持**: EUR_GBP + EUR_AUD 同時 active 1 個まで (Live でも)
- [ ] **Watchdog 配置**: Live N=10 EV<0 で auto demote、Discord 通知 (R2 safety net)
- [ ] **Pre-reg promote criteria 維持**: lot ramp は司令塔別判断、自動 ramp 禁止
- [ ] **既存 Shadow data 保持**: Phase B-1 (commit 35961351) 以降 Shadow ramp で蓄積された trade record (もし存在) は保持、forensic 用
- [ ] **Live↔Shadow 集計分離** (feedback_live_shadow_separation): 既存 risk_analytics の is_shadow=0/1 分離パターンを維持
- [ ] **stash 漏れ禁止** (feedback_codex_stash_leak)
- [ ] **mock 禁止** (feedback_codex_mock_test_trap)
- [ ] **XAU 除外** (feedback_exclude_xau)

## 3.2 リスク認識 (final.md に明記)

1. **Shadow-first 違反**: 通常は Shadow N>=30 後に Live、本件は BT 高品質 + 直接 Live MIN lot。Wilson_lo>=0.58 (5/5) + Bonf 9-28/family を根拠
2. **DD 危機継続**: project_fxai_state_2026_05_11 で DD=47.22%、5 戦略の Live で DD 悪化 risk → MIN lot で bound、watchdog N=10 で safety net
3. **Cross-pair concentration**: EUR_GBP + EUR_AUD shared lock で 50% 軽減、USD_CAD + EUR_AUD 等の他 USD/EUR 軸は portfolio 別途
4. **Live regime shift**: Backfill 期間 2021-12〜2026-04 で観測されたエッジが現在 (2026-05) も成立するかは Live 観測でのみ確定

## 3.3 失敗時挙動

- 既存 test が Live 化で失敗 → spec §1.6 の趣旨に従い適切に更新、ただし pre-reg LOCK 定数の literal 検証は変更禁止 (Codex が勝手に literal を変えたら ROLLBACK)
- Render deploy 後に signal emit が出ない → 24h 観察、原因 (mode running=False / FORCE_DEMOTED 残存 / OANDA bridge error) を切り分け、final.md 明記
- watchdog が誤動作 → final.md 明記、別 task で修正 (本 task は ACCEPT 扱い)

# 4. 想定実行時間

- demo_trader / __init__.py 変更: 30 分
- watchdog 新規実装: 45 分
- promote evaluator 新規実装: 30 分
- テスト作成 (real DB 経由): 1 時間
- KB 更新 + commit + deploy 確認: 30 分
- **総計**: 3-4 時間


## Result (2026-05-18T10:34:53Z)

exit=0 · 615s

```
Implemented, committed, pushed.

Commit: `88783064 feat(price_shock_rev): Tier 1 5 戦略 Live activation v2 MIN lot (rule:R1)`

What changed:
- Removed the 5 Price-Shock Rev strategies from `_FORCE_DEMOTED` and `HourlyEngine._shadow_always`.
- Added their 5 pair-specific Live routes as `_PAIR_PROMOTED`.
- Forced Price-Shock Rev Live sizing to `1000u` MIN lot.
- Kept EUR_GBP/EUR_AUD shared lock active for Live/Shadow.
- Added:
  - `tools/price_shock_rev_live_watchdog.py`
  - `tools/price_shock_rev_promote_evaluator.py`
  - `tools/scheduled-tasks/price_shock_rev_watchdogs.cron`
  - `tests/test_price_shock_rev_live_activation_v2.py`
  - KB decision + strategy/tier/changelog updates

Verification:
- `30 passed`
  - `tests/test_price_shock_rev_live_activation_v2.py`
  - `tests/test_price_shock_rev_strategies.py`
  - `tests/test_pine_overlay_equivalence.py`
  - `tests/test_hourly_engine_shadow_ramp.py`
- `python3 tools/tier_integrity_check.py --check` → `ERROR=0`, existing warning only: `ob_retest` legacy inline label.
- `git status` clean.

Deploy check:
- Render `/api/strategies/status` now shows all 5 `price_shock_rev_*` strategies as `PAIR_PROMOTED`.
- `/api/demo/status` shows all 5 target H1 modes running; current last signals are `WAIT`, so no Price-Shock Live emit has occurred yet after deploy.

Note:
- GitHub rejected adding a new workflow file because the available PAT lacks `workflow` scope. I removed the workflow from the commit and placed the 4h schedule definition in `tools/scheduled-tasks/price_shock_rev_watchdogs.cron`.

Risks recorded:
- This intentionally relaxes Shadow-first due to BT quality.
- DD risk remains elevated; bounded by MIN lot and N=10 watchdog.
- EUR_GBP/EUR_AUD concentration is locked to one active position.
- Current Live regime edge remains unproven until new Live observations accumulate.
```
