---
id: 20260612-1715-ldn-morning-size-lever
priority: P1
gate: R2
rule: R2
status: queued
created: 2026-06-12
owner: codex
---

# LDN朝 SIZE lever — UTC07-09 の counter-USD MR セル (E5/E7/E10) を LIVE lot 0.5x

**Rule 分類**: R2 (lot↓ は Fast & Reactive で即断可)。user 承認済み 2026-06-12 (roadmap v2.2 T4)。

## Background (Claude 一次データ実測 2026-06-12)

30d clean live (is_shadow=0, dedup除外, XAU除外) で **UTC07-09 (ロンドン朝) が -71.8p / 21 trades** と最大の負け時間帯。クラスタの中身は USD 全面高 (hawkish Fed + 中東情勢) への counter-USD MR。停止済みセル (E2/E8 等) を除く現役セルのうち、この時間帯×counter-USD MR に該当するのは:

- **E5**: `dt_bb_rsi_mr` / GBP_USD / SELL
- **E7**: `dt_bb_rsi_mr` / GBP_USD / session=ASN
- **E10**: `wick_imbalance_reversion` / GBP_USD / v2_regime=no_go

教訓 (2026-05-28 確定): SKIP filter は entry timing shift + compounding 破壊で edge を喪失させる (ZZ Pivot v60 で F1/F3 全 fail 実証)。**SIZE lever (lot 半減) のみが cell stats edge を実 BT で活かす** (PF +5.9% / WFO 3/3 実証)。よって SKIP ではなく lot 0.5x。

## Spec

1. **LIVE (OANDA 転送) 側のみ**: 発火が `edge_cell_id ∈ {E5, E7, E10}` かつ entry の UTC hour ∈ {7, 8, 9} のとき、OANDA 送信 lot に **0.5 倍**を掛ける
2. **Shadow は絶対に無変更** (CLAUDE.md 原則3。demo_trades への記録・shadow 発火は現状維持)
3. 適用時は `demo_trades` の reasons (または既存の調整ログフィールド) に `ldn_morning_size_lever_0.5x` を記録し、事後監査でフィルタ可能にする
4. kill switch: env `LDN_MORNING_SIZE_LEVER` (default "1"=有効、"0" で無効化)。解除条件 (USD 一方向レジーム終了) は手動レビューで env を落とす運用
5. 既存の lot 計算チェーン (`_PAIR_LOT_BOOST`、edge cell stage multiplier 等) との合成順序を derivation で明記 — 二重掛け・打ち消しがないこと

## Tests

- E5/E7/E10 × UTC07/08/09 → lot 0.5x が掛かる
- 同セル × UTC10 → 掛からない
- 非対象セル (E9 orb_trap) × UTC08 → 掛からない (**E9 は N 蓄積中のため絶対に触らない**)
- is_shadow=1 → 掛からない
- env=0 → 掛からない

## 採用/棄却条件

- `pytest tests/ -x -q` 全通過 + `scripts/check.py` 通過
- final.md は git log/diff で実 verify
- E9/E6/E11 など対象外セルの挙動に diff が無いことを明記


## Result (2026-06-12T08:46:52Z)

exit=0 · 597s

```
実装完了しました。

変更点は [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py) に LIVE-only の `LDN_MORNING_SIZE_LEVER` 判定と OANDA 送信直前の 0.5x 適用、[modules/demo_db.py](/data/repo/fx-ai-trader/modules/demo_db.py) に `demo_trades.reasons` 監査タグ追記 helper を追加しました。適用時は `ldn_morning_size_lever_0.5x` を記録します。Shadow 経路は変更していません。

lot 合成順は `final.md` に明記済みです。今回の lever は `_PAIR_LOT_BOOST` / edge-cell stage lot / `Candidate.lot_multiplier` / final gates の後、実 OANDA send path だけに最後に掛けます。E9/E6/E11 など対象外セルにはロジックを追加しておらず、E9 UTC08 unchanged はテストで固定しました。

検証済み:

```text
.venv/bin/pytest tests/test_ldn_morning_size_lever.py -q
7 passed

.venv/bin/pytest tests/test_edge_cell_force_live_override.py tests/test_edge_cell_e2e_force_fire.py tests/test_demo_trader_lot_multiplier_integration.py -q
16 passed

.venv/bin/pytest tests/ -x -q
1855 passed, 1 skipped, 1 xfailed in 274.88s

.venv/bin/python scripts/check.py
全6チェック通過

git diff --check
clean
```

`scripts/check.py` は既存 KB 警告を表示しましたが、checker verdict は OK です。`final.md` も今回の git log/diff/verification 内容で更新済みです。
```
