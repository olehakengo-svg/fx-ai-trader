---
id: 20260511-1730-mc-ruin-lot-multiplier-fix
title: "[MC-Bug-Fix] monte_carlo_ruin に lot_multiplier 適用 — defensive_mode の ruin 誤導値を是正 (rule:R3)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-11T17:30:00+0900
roadmap_gate: "87b5e3c (clean-live tier demote) 後の本筋整備。/api/risk/dashboard の ruin=35.62% は full-lot 想定の誤導値、defensive_mode (lot_multiplier=0.2) 反映後の実 ruin は 0.5% 級。memory: feedback_partial_quant_trap (PF/Wilson/Kelly/MC の整合性) と feedback_quant_first (数学/code 演繹) に整合した structural fix。"
rule: R3
related:
  - modules/risk_analytics.py
  - app.py
  - knowledge-base/wiki/strategies/equity-protector.md (もし存在)
  - .ai/runs/20260511-164419-20260511-1700-clean-live-per-cell-audit/final.md (MC bug 発見)
  - 87b5e3c (clean-live tier demote)
---

# 0. 背景

20260511-164419 Clean-Live audit final.md §"Monte Carlo Lot Multiplier Consistency" で確定したバグ:

> Code inspection:
> - `app.py::api_risk_dashboard` reads `dd_lot_mult` only for `dashboard["dd_status"]`; it calls `compute_risk_dashboard(closed)` before adding DD status.
> - `modules/risk_analytics.compute_risk_dashboard()` passes raw `pnl_list` into `monte_carlo_ruin()` with `n_simulations=5000`, `n_trades_forward=300`, `initial_capital=1000.0`, `ruin_dd_pct=0.50`.
> - `modules/risk_analytics.monte_carlo_ruin()` has no `lot_multiplier` or DD multiplier parameter.
>
> Snapshot clean cohort MC:
> | simulation | ruin_probability | median_max_dd |
> | current code raw PnL | 0.0234 | 286.75 |
> | manual PnL ×0.2 | 0.0000 | 57.35 |
>
> Conclusion: current risk dashboard MC does not apply defensive `lot_multiplier=0.2`; it reports raw historical pip distribution.

本番 5/11 実測 `/api/risk/dashboard`:

```
kelly.edge=-0.2479  win_rate=0.4094
dd_status.dd_pct=0.4722  defensive_mode=true  lot_multiplier=0.2
monte_carlo.ruin_probability=0.3562  ← 誤導値
monte_carlo.n_simulations=5000  n_trades_forward=300
monte_carlo.initial_capital=1000.0  ruin_dd_pct=0.5
```

ruin=35.62% は **lot_multiplier=1.0 想定の forward simulation**。defensive 運用 (lot=0.2x) では実 ruin は数 % 級と推定。司令塔判断 (戦略の存続/降格) の前提となる ruin 数字が信頼できない状態。

# 1. 数学/code 演繹 (memory: feedback_quant_first)

## 1.1 現状の MC ロジック

`monte_carlo_ruin(pnl_list, n_simulations, n_trades_forward, ruin_dd_pct, initial_capital)`:
1. `pnl_list` (historical pnl_pips) からサンプリング
2. n_trades_forward 回繰り返して equity 軌跡を生成
3. max_dd / initial_capital >= ruin_dd_pct なら ruin

問題: `pnl_pips` は **per-pip 単位**、現実の per-trade dollar impact は `pnl_pips × lot_size × pip_value`。defensive_mode で lot=0.2x なら実 impact は 1/5。raw pnl_pips をそのまま使うと "full-lot 想定の将来" を simulate している。

## 1.2 正しいモデル

選択肢:

**Option A (推奨)**: forward simulation で `pnl_pips × current_lot_multiplier` を使う
- 利点: 現状の defensive lot のまま継続運用した場合の ruin を推定
- 欠点: 将来 lot_multiplier が回復した場合 (equity_protector の動的 lot) は overestimate
- 推奨理由: conservative + 司令塔判断には「今のままで続けたらどうなるか」が一番重要

**Option B**: dynamic lot model — equity_protector のルールを再現
- 利点: より正確
- 欠点: 複雑、 equity_protector の bug が伝播、テスト困難

**Option C**: ユーザに lot_multiplier をクエリパラメータで渡させる
- 利点: 柔軟
- 欠点: UI 露出 + 何が "正"値か不明瞭

**A 採用**。本タスクは A 実装、B/C は将来検討事項として doc 化。

## 1.3 実装

`monte_carlo_ruin()` に `lot_multiplier: float = 1.0` 引数追加:

```python
def monte_carlo_ruin(
    pnl_list,
    n_simulations=5000,
    n_trades_forward=300,
    ruin_dd_pct=0.5,
    initial_capital=1000.0,
    lot_multiplier=1.0,
):
    # サンプリング時に lot_multiplier を適用
    # pip_per_trade = sampled_pnl * lot_multiplier (近似: pip-level scaling)
    ...
```

`compute_risk_dashboard()` で `equity_protector` から lot_multiplier 取得して渡す:
```python
def compute_risk_dashboard(closed_trades, lot_multiplier=1.0):
    ...
    mc = monte_carlo_ruin(pnl_list, lot_multiplier=lot_multiplier, ...)
```

`api_risk_dashboard()` で dashboard 計算より前に lot_multiplier を解決:
```python
@app.route("/api/risk/dashboard")
def api_risk_dashboard():
    ...
    dd_lot_mult = _equity_protector.get_lot_multiplier()  # current defensive lot
    dashboard = compute_risk_dashboard(closed, lot_multiplier=dd_lot_mult)
    dashboard["dd_status"] = ...
    dashboard["monte_carlo"]["lot_multiplier_applied"] = dd_lot_mult  # 透明性
```

レスポンスに `lot_multiplier_applied` を返して、UI 側で「defensive 0.2x 反映」の表示も可能に。

# 2. 仕様

## 2.1 法医学

実測クエリ (production /api/risk/dashboard が DNS で取れない場合、snapshot から再現):

1. **現状 ruin 値の確認**: production または snapshot で `monte_carlo.ruin_probability`
2. **lot_multiplier=0.2 適用後の予測値**: 手動再計算 (Codex audit と同じ手順)
3. **乖離率**: 期待 ruin 改善幅 (Codex audit: 0.0234 → 0.0000)

## 2.2 実装

`modules/risk_analytics.py`:
- `monte_carlo_ruin()` に `lot_multiplier: float = 1.0` 引数追加
- サンプリングした pnl に `* lot_multiplier` を適用
- legacy 呼出 (lot_multiplier=1.0 デフォルト) で挙動不変

`modules/risk_analytics.compute_risk_dashboard()`:
- `lot_multiplier: float = 1.0` 引数追加
- `monte_carlo_ruin(pnl_list, lot_multiplier=lot_multiplier, ...)` で渡す

`app.py::api_risk_dashboard()`:
- equity_protector / defensive_mode から lot_multiplier 取得
  (current production: `dd_lot_mult` 変数として既に dd_status に渡している、再利用)
- `compute_risk_dashboard(closed, lot_multiplier=dd_lot_mult)` で渡す
- レスポンスに `monte_carlo.lot_multiplier_applied=<float>` フィールド追加

## 2.3 テスト

`tests/test_risk_analytics_mc_lot_multiplier.py` 新規:

1. **Legacy unchanged**: `monte_carlo_ruin(pnl, lot_multiplier=1.0)` ≡ `monte_carlo_ruin(pnl)` (引数なし)
2. **Defensive reduces ruin**: 同じ pnl_list で `lot_multiplier=0.2` の方が ruin probability が低い (and 範囲: ruin_1.0 / 25 程度に減少を期待だが大幅減確認のみで OK)
3. **Median_max_dd scales**: lot_multiplier=0.2 → median_max_dd ≈ median_max_dd_at_1.0 × 0.2 (linear scaling、許容 ±10%)
4. **API response includes lot_multiplier_applied**: `/api/risk/dashboard` レスポンスに新フィールドが含まれる

`tests/test_risk_dashboard.py` (もし存在) との回帰確認。

## 2.4 dry-run

production /api/risk/dashboard を 1 回叩いて (DNS 通れば)、または snapshot で sandbox sim:
- before fix: ruin=0.3562 (本番現値)
- after fix (本番反映): ruin が defensive lot=0.2 適用で大幅減 (期待 < 5%)

ただし production sim は deploy 後実測なので、本タスクは local sim で確認 + 期待値計算のみ。

# 3. 受入基準

- [ ] `monte_carlo_ruin()` に lot_multiplier 引数追加、legacy 呼出 (default=1.0) で挙動完全不変
- [ ] `compute_risk_dashboard()` に lot_multiplier 引数追加、down-stream で MC に渡す
- [ ] `api_risk_dashboard()` で equity_protector 由来の lot_multiplier を取得して dashboard に渡す
- [ ] レスポンス `monte_carlo.lot_multiplier_applied=<float>` 追加
- [ ] 新規 4 unit tests 全 PASS
- [ ] 既存 tests/ regression なし (1419 PASS keep)
- [ ] `python3 scripts/check.py` PASS
- [ ] dry-run (snapshot or local): lot_multiplier=0.2 で ruin probability が大幅減 (期待 < 0.05) を確認

# 4. 非ゴール

- equity_protector 動的 lot model (Option B) 実装 — 別タスク
- UI 変更 (dashboard.html に "defensive 0.2x reflected" 表示) — 別タスク
- 過去 ruin 値の retro-correction (本タスクは forward simulation のみ)
- Kelly / VaR / CVaR の lot_multiplier 反映 (本タスクは MC のみ)
- defensive_mode 解除条件の調整

# 5. クオンツ的注意

- **conservative model**: 現在の defensive lot=0.2 が継続前提。将来 lot 回復 (equity_protector 動的) すれば ruin は再上昇する可能性、その時点で MC は新値を反映
- **memory: feedback_partial_quant_trap**: MC は信頼可能になる、しかし Kelly / Wilson / WF / Bonferroni と並列で見ること必須。MC だけで promote/demote 判断しない
- **memory: feedback_quant_first**: 数学的に Option A が正しい (forward at current state)。code 演繹を超えて式の意味を理解した実装が必要
- **legacy compatibility**: `lot_multiplier=1.0` で既存挙動完全保持 (BT スクリプト等が呼んでいる可能性、引数追加で破壊しない)
- **テスト 3 の linear scaling**: pip → equity の関係は概ね linear (initial_capital 一定なら) なので、median_max_dd は概ね x0.2。ただし initial_capital 1000 + variance の絡みで完全 linear ではないため許容 ±10%

# 6. 報告フォーマット

final.md に含めること:
- 現状 production ruin 値 + 期待 fix 後値
- monte_carlo_ruin の引数追加 diff
- compute_risk_dashboard の chain through diff
- api_risk_dashboard の lot_multiplier 取得 source code
- legacy unchanged 確認 (lot_multiplier=1.0 テスト結果)
- defensive_mode 適用シミュレーション結果 (ruin before/after)
- 既知の限界 (Option A の保守性、equity_protector 動的回復は反映しない)
