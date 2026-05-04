---
date: 2026-05-03
tasks:
  - 20260503-2230-r2-tier1-hour-bucket-extension (ACCEPT)
  - 20260503-2240-r2-14cell-conflict-resolution (BLOCKED, modules/ scope)
  - 20260503-2300-s6-w2-bt-usdjpy-m5 (ACCEPT/REJECT 全 12 patterns)
verdict: 🎯 **Gate 0 ACCEPT 経路完成** (15-cell demote で raw Kelly +0.0094)
rule: R2
gate: Gate 0 ACCEPT 達成 (実装 PR 待ち)
---

# Gate 0 ACCEPT 経路完成 — R2 Tier1 拡張で raw Kelly +0.0094 達成

## Headline

**14-cell base demote** (前回 R2 TRUE_LIVE) **+ Tier 1 LIVE bleeding cell `gbp_deep_pullback × GBP_USD`** (拡張) の合計 **15-cell demote set** で:

- raw Kelly: -0.1326 → **+0.0094** (Gate 0 ACCEPT 閾値突破)
- MC60d 破産: 86.50% → **0.30%** (完全生存圏)
- aggregate EV: -0.79 → **+0.06p** (positive territory)
- PF: 0.695 → **1.021** (≥ 1.0 達成)

これは月利100% ロードマップの Gate 0 救済 **完成形**。

## 15-cell Final Demote Set

### 14-cell base (R2 TRUE_LIVE counterfactual SSOT)
1. vwap_mean_reversion × GBP_USD
2. vix_carry_unwind × USD_JPY ⚠️ pair_promoted 衝突
3. sr_channel_reversal × USD_JPY
4. bb_rsi_reversion × USD_JPY
5. session_time_bias × GBP_USD
6. bb_squeeze_breakout × USD_JPY ⚠️ pair_promoted 衝突
7. bb_rsi_reversion × EUR_USD (already demoted)
8. vol_surge_detector × USD_JPY
9. engulfing_bb × USD_JPY (already demoted)
10. engulfing_bb × EUR_USD (already demoted)
11. v_reversal × USD_JPY
12. trend_rebound × USD_JPY
13. sr_channel_reversal × EUR_USD
14. stoch_trend_pullback × USD_JPY (already demoted)

### Tier 1 拡張 (R2 Tier1 hour-bucket extension)
15. **gbp_deep_pullback × GBP_USD** ⚠️ ELITE_LIVE bleeding (要 elite_live tier 同時調整)

Bonferroni m_add=14, α'_add=0.003571。SSOT positive keep cells は demote 対象外。

## 実装 blocker — `modules/demo_trader.py` scope 拡大必要

R2 conflict resolution task が露呈した重要事実:

- runtime SSOT = `modules/demo_trader.py:6158` (`_PAIR_DEMOTED`)
- `tier_integrity_check.py --write` は `modules/demo_trader.py` を parse して `tier-master.{md,json}` を auto-regenerate
- **`tier-master.json` 単独編集では runtime routing 変わらず、`--write` で上書きされる**

→ **真の SSOT は `modules/demo_trader.py` の定数**。
→ 実装 PR は `modules/demo_trader.py` 編集が必須。

## 必要な実装変更点 (next task に反映)

| 場所 | 変更内容 |
|---|---|
| `modules/demo_trader.py:6158` (`_PAIR_DEMOTED`) | 11 cell 追加 (4 cell は no-op 既存) |
| `modules/demo_trader.py:6209` (`_PAIR_PROMOTED`) | 2 cell 削除 (`vix_carry_unwind × USD_JPY`, `bb_squeeze_breakout × USD_JPY`) |
| `modules/demo_trader.py:_ELITE_LIVE`(該当行) | `gbp_deep_pullback × GBP_USD` を ELITE 解除 (Tier 1 demote の前提) |
| auto-regen `tier-master.{md,json}` | `tier_integrity_check.py --write` で同期 |

post-edit verification:
- `tier_integrity_check.py --check` ERROR=0 WARN=0
- `pytest` の関連テスト pass
- 単一 commit

## S6 W2 BT 補足 (本決定とは disjoint)

12 chart patterns 全て REJECT (3 modes 共通)。検出器 geometry に edge なし。Wave 2b で geometry 見直し OR Wave 3 sweep null-confirmation のみ。月利100% に直接寄与しないが、新戦略族の効率的早期 reject = 価値ある検証完了。

## Roadmap impact

**月利100% ロードマップ復活**:
- Gate 0 ACCEPT 経路確定 → Render auto-deploy で 87% 即時止血 + Kelly positive
- 7d Live N 蓄積で実 aggregate Kelly 検証
- 並行: A3-simple-sr-channel-reversal-shadow-register (Promote 候補確定済)
- Tier 1 LIVE 構造問題 RCA (routing anomaly 解明) は別 path

## Next task

**`r2-15cell-modules-lock-pr-2026-05-03`** (新規起草必要):
- scope: `modules/demo_trader.py` 編集 OK (構造 task)
- 15-cell demote set + 2-cell pair_promoted 削除 + 1-cell elite_live 解除
- `tier_integrity_check.py --write` で auto-regenerate
- 単一 commit、push しない
- Claude review → user push 判断 → Render auto-deploy で Gate 0 ACCEPT 実現
