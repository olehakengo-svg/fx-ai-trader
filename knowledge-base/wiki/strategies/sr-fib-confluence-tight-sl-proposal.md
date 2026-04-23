# Proposal: sr_fib_confluence_tight_sl (Shadow Variant)

## Overview
- **Entry Type**: `sr_fib_confluence_tight_sl` (未実装)
- **Base Strategy**: `sr_fib_confluence`
- **Status**: PROPOSAL (未実装、2026-04-23 Phase 2 候補)
- **Stage**: PROPOSAL / DESIGN
- **Target**: SL 現行 `ctx.atr7 * 1.0` → `min(ctx.atr7 * 1.0, 3.0p)` にハードキャップ

## Rationale (2026-04-23 Lever C 分析)

shadow post-cutoff で N=73 の負け戦略:

| Scope | N | WR | EV_real | Bootstrap EV_lo (real) |
|---|---|---|---|---|
| baseline | 73 | 21.9% | **-8.01p** | very negative |
| **SL=3p simulation** | 73 | 21.9% | **-1.75p** | -3.54p |
| SL=5p | 73 | 21.9% | -3.16p | -5.16 |
| SL=8p | 73 | 21.9% | -4.94p | -7.19 |

**EV lift +6.26p/trade** — 高N負け戦略群で最大の改善ポテンシャル。

根拠:
- loss MAE median=11.0p, 90%ile=20.0p → 現行 SL が明らかに緩すぎて大損を許容
- win MFE median=17.8p, 90%ile=27.1p → 勝ち時の利伸びは十分残る
- WR は変わらないが損失キャップで単一戦略 EV を負 → ほぼBE域に
- Bootstrap EV_lo はまだ負で Kelly Half 即昇格不可、Shadow 蓄積必要

## 実装プラン

1. 新 strategy class `SrFibConfluenceTightSl(SrFibConfluence)` を
   `strategies/daytrade/sr_fib_confluence.py` に追加、`evaluate()` で SL を
   `min(ctx.atr7 * 1.0, 3.0)` にキャップ
2. `strategies/daytrade/__init__.py` に登録
3. `modules/demo_trader.py` QUALIFIED_TYPES に `sr_fib_confluence_tight_sl` 追加
4. Wiki strategy page 作成
5. PHASE0_SHADOW で N≥30 蓄積 → 3点検証 (Bootstrap real-cost, top1-drop)
6. 昇格ゲート通過後 Kelly Half Live

## 既存戦略への影響

- base `sr_fib_confluence` は **変更しない** (独立並走)
- 新 strategy は独立 entry_type で Shadow 分離

## なぜ今実装しないか

- 戦略クラス追加は QUALIFIED_TYPES/**init**.py/wiki/tier_integrity_check など 6-7ファイル変更
- 単一 session の scope を超える
- VWAP 修正 (Step A) の効果測定を先に回したい — 既存戦略の EV が改善する可能性

## Dependencies

- 先に VWAP conf_adj 修正が本番反映 → 再計測で sr_fib_confluence baseline が
  どう変化するか確認
- 変化後も EV≤0 なら tight SL 変種を実装

## References

- 分析: `/tmp/triple_audit.py` Lever C output
- 関連 lesson: [[lesson-vwap-inverse-calibration-2026-04-23]]
- Base strategy: `strategies/daytrade/sr_fib_confluence.py`
