---
id: 20260507-1240-volume-live-promote-10-strategies
title: "[Volume-Live-Promote] 10戦略 PAIR_PROMOTED 化 (OANDA tier 維持目的 + EV+ 候補検証)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-07T12:40:00+0900
roadmap_gate: "OANDA tier (GOLD/PLATINUM) 維持 = システム稼働の必須条件 / 並行で EV+ 候補の Live 検証"
rule: R2
related:
  - knowledge-base/wiki/tier-master.md
  - knowledge-base/wiki/syntheses/roadmap-v2.1.md
  - .ai/tasks/queue/20260507-1220-shadow-promote-r2-auto-alert.md
---

# 0. 背景

OANDA 自動取引の API tier 維持には月間取引高 ≥ $500,000 (GOLD) が必要。現状 Live は scalp_5m のみで月 $126k 程度 → 来月 SILVER 降格 = **API 自動取引停止**。これは月利100%以上に shadow N 蓄積システム稼働の前提条件であり、tier 降格はシステム停止と同義。

直近 30日 shadow trade 集計 (2026-05-07) で **EV>0 / PF>1.0 / N≥10 を満たす 10 cell** を抽出。これらを Live (PAIR_PROMOTED) 化して volume 確保 + Live 期待値検証を同時進行する。

クオンツ規律:
- Wilson_lo>=0.50 を満たす cell は 0 件 (緊急 volume 確保のため Wilson 基準を緩和)
- EV+PF 基準で代替、selection bias リスクは R2 alert tool で監視
- Live N>=10 で EV<0 確認なら即 demote (Rule 2 fast & reactive)

# 1. 仕様

## 1.1 PAIR_PROMOTED 追加対象 (10 cell)

| # | 戦略 | pair | shadow N (30d) | EV | PF | 備考 |
|---|---|---|---|---|---|---|
| 1 | vix_carry_unwind | USD_JPY | 58 | +9.54 | 1.65 | 最強候補 |
| 2 | mqe_gbpusd_fix | GBP_USD | 87 | +1.81 | 1.30 | 頻度最大、SHADOW_ALWAYS hardcode 既 |
| 3 | sr_fib_confluence | GBP_USD | 39 | +1.35 | 1.29 | |
| 4 | xs_momentum | GBP_USD | 29 | +0.47 | 1.06 | 既 PAIR_PROMOTED (確認/維持) |
| 5 | session_time_bias | EUR_USD | 23 | +0.63 | 1.15 | |
| 6 | vsg_jpy_reversal | EUR_JPY | 20 | +1.82 | 1.30 | SHADOW_ALWAYS hardcode 既 |
| 7 | trend_rebound | USD_JPY | 17 | +1.14 | 1.52 | |
| 8 | bb_squeeze_breakout | EUR_USD | 14 | +0.01 | 1.00 | borderline (flat)、要 Live 観察 |
| 9 | dt_sr_channel_reversal | EUR_JPY | 12 | +14.28 | 3.61 | |
| 10 | dt_bb_rsi_mr | USD_JPY | 10 | +8.51 | 4.38 | Round 1 SHADOW_PROMOTE 既 |

### 1.1.1 既存 SHADOW_ALWAYS hardcode との整合
- `mqe_gbpusd_fix` と `vsg_jpy_reversal` は既に `strategies/daytrade/__init__.py:205` の `SHADOW_ALWAYS_STRATEGIES` 入り
- これらを PAIR_PROMOTED にする場合、SHADOW_ALWAYS から除外して二重路を避ける (要検証)

### 1.1.2 既存 PAIR_PROMOTED との整合
- `xs_momentum GBP_USD` は既に `wiki/tier-master.md` PAIR_PROMOTED 入り
- ただし shadow trade として記録されている = OANDA 通過してない可能性
- 原因調査 (friction gate / spread gate / 他 filter) → 解除して実 Live 化

## 1.2 PAIR_PROMOTED 設定方法

- `knowledge-base/wiki/tier-master.md` のテーブル A-2 に 10 行追加 (既存 entries 保持)
- 通過判定の本体: `modules/demo_trader.py` 内 routing logic を確認、PAIR_PROMOTED 戦略 × 指定 pair が OANDA 通過する path を有効化
- 必要に応じて env vars (`{STRAT}_LIVE_PROMOTE=1` など) を追加

## 1.3 Friction gate 確認 (Live 化を阻害する filter)

各 10 戦略 × pair で以下 gate に通過するか確認、阻害があれば緩和:
- `spread_sl_gate` (Spread/SL gate)
- `Q4 gate` / `Phase0 gate`
- `MFE Guard`
- `mtf_gated`
- 任意の戦略固有 filter

具体的に shadow data で「signal は出ているが OANDA bridge_status が sent でない / filled でない」cell を特定し、原因 gate を pinpoint。

## 1.4 R2 自動 demote (Rule 2 fast & reactive)

10 戦略の Live N>=10 で EV<0 確認なら **即時 PAIR_PROMOTED から除外** する仕組みを併設:
- `tools/post_promotion_watchdog.py` を 10 戦略向けに拡張
- もしくは別途 `tools/volume_live_promotion_watchdog.py` を新規作成
- R2 alert tool (`20260507-1220-shadow-promote-r2-auto-alert`) と連携
- CRITICAL 検知 → 自動 demote OR 手動アラート (要判断: 自動 demote を実装するか、人間判断介入か)

推奨: **自動 demote 実装**。緊急 volume 確保のため selection bias リスクが高く、自動安全弁が必須。

## 1.5 Lot size

- 既存 Live (scalp_5m) と同じ lot size (デフォルト 0.05 lot 想定) を使用
- 既存設定で base lot 0.05 と仮定して volume 計算: 309 trade/月 × 0.05 lot ≈ $1.5M/月 (USD volume)
- GOLD ($500k) 余裕で達成、PLATINUM ($?) も射程内

## 1.6 KB 同期

PAIR_PROMOTED 編集後:
```
python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check  # ERROR=0 確認
```

# 2. データ分離 (規律遵守)

- BT: 不使用 (緊急 volume 対応のため)
- Shadow: 直近 30日 shadow data を根拠 (selection bias 認識済)
- Live (is_shadow=0): 投入後の N 蓄積 → R2 watchdog で自動 demote 判定
- OANDA: PAIR_PROMOTED 経由で実弾転送

# 3. クオンツ条件 (Rule 1/2/3 整合)

- **Rule 2 (Fast & Reactive)**: tier 維持 + Live N=10 demote の高速判定
- Wilson_lo>=0.50 / Bonferroni 等の formal pre-reg LOCK は **緊急例外**として今回適用しない
- 代わりに R2 自動 demote で安全網
- Wave 5 で formal promotion 判定が来たら、その結果に置き換え

# 4. 失敗テスト (TDD)

- `tests/test_volume_live_promote_routing.py`
  - 各 10 戦略 × pair で OANDA bridge が `sent` 状態に遷移するか
  - SHADOW_ALWAYS から除外された mqe_gbpusd_fix / vsg_jpy_reversal が二重発火しないか
  - 自動 demote watchdog が EV<0 N>=10 で正しく除外するか (合成 fixture)

# 5. Acceptance Criteria

- `wiki/tier-master.md` PAIR_PROMOTED に 10 cell 追加 (xs_momentum GBP_USD は既存維持)
- `tier_integrity_check.py --check` ERROR=0
- 失敗テスト緑 (合成 fixture)
- Render redeploy 後、Live API `/api/demo/trades` で **24時間以内に 10 戦略のいずれかの is_shadow=0 trade が記録される**
- R2 watchdog が動作確認 (synthetic test)
- Codex self-review: data 分離 OK / Wilson 緩和の justification 記録 / R2 自動 demote 機構が active

# 6. Out of Scope

- Lot size の戦略別最適化 (一律 0.05 lot 想定)
- Wilson_lo / Bonferroni の formal pre-reg LOCK (Wave 5 で扱う)
- 残り 50+ 戦略の Live promote (本 task は 10件のみ)
- Live PnL の forensic 監査 (R2 watchdog 完成後に別 task)

# 7. Notes

- 緊急性 (P0): 来月 SILVER 降格までの猶予が短い、即時 deploy 必須
- 期待 monthly PnL contribution: +750pip 程度 (selection bias 後でも +200~400pip 想定)
- 自動 demote 機構は **selection bias 罠への第二の安全網**
- Wave 5 で formal promotion 結果が出れば、本 task の 10 戦略は再評価対象 (formal 通過 → 維持、不通過 → demote)


## Result (2026-05-07T06:02:54Z)

exit=0 · 270s

```
Implemented the volume emergency promotion path.

Changed:
- Added the 9 new PAIR_PROMOTED cells in [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py) and kept existing `xs_momentum GBP_USD`.
- Removed blocking tier conflicts for promoted cells from `_FORCE_DEMOTED` / `_PAIR_DEMOTED`.
- Made PAIR_PROMOTED cells exempt from the shadow-downgrading gates that were likely to prevent live routing: alpha shadow gates, MTF downgrade, and `spread_sl_gate`.
- Removed `mqe_gbpusd_fix` / `vsg_jpy_reversal` from `SHADOW_ALWAYS_STRATEGIES` to avoid double-path firing.
- Added R2 safety valve: [tools/volume_live_promotion_watchdog.py](/data/repo/fx-ai-trader/tools/volume_live_promotion_watchdog.py), with `Live N>=10 && EV<0 => DEMOTE`, plus optional `--apply` source demotion.
- Added regression tests in [tests/test_volume_live_promote_routing.py](/data/repo/fx-ai-trader/tests/test_volume_live_promote_routing.py).
- Fixed [tools/sync_kb_index.py](/data/repo/fx-ai-trader/tools/sync_kb_index.py) so commented-out tier tuples do not pollute KB index output.
- Regenerated `knowledge-base/wiki/tier-master.md`, `tier-master.json`, and `index.md`.

Verification:
- `.venv/bin/pytest tests/test_volume_live_promote_routing.py tests/test_vsg_jpy_reversal_shadow_redesign_v2.py -q` → `10 passed`
- `python3 tools/sync_kb_index.py --write`
- `python3 tools/tier_integrity_check.py --write`
- `python3 tools/tier_integrity_check.py --check` → `ERROR=0`, all checks passed
- `python3 tools/volume_live_promotion_watchdog.py --smoke` → OK
- `py_compile` passed for touched Python files

Notes:
- PAIR_PROMOTED is now 18 entries: existing 9 plus 9 new cells, with `xs_momentum GBP_USD` maintained.
- I did not perform Render redeploy or the 24h `/api/demo/trades` live confirmation from here; that still needs post-deploy observation.
- Data separation is preserved: promotion basis is Shadow 30d EV/PF, while demotion trigger uses only non-shadow Live
…(truncated)
