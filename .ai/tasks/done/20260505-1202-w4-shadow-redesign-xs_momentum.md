---
id: 20260505-1202-w4-shadow-redesign-xs_momentum
title: "[W4-Shadow Phase 1] xs_momentum (Tier 1 (LIVE)) — implement + shadow promote (BT light filter)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T12:02:00+0900
roadmap_gate: "W4 Shadow-first redesign — quant 推奨 (BT は軽量 filter、shadow が真の estimator)"
rule: R1
prereq_artifacts:
  - audits/edge_design/xs_momentum.md
  - knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
related:
  - knowledge-base/wiki/lessons/feedback_audit_purpose_design_not_n.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/xs_momentum.md`) で **THESIS_VALID_TIMING_BROKEN** / 推奨度 **A** と判定。

**クオンツ推奨アーキテクチャ** (2026-05-05 user指摘で確定):
- BT は **軽量 sanity filter** (catastrophic regression 排除のみ)、Live promotion gate ではない
- Shadow が **真の estimator** (production 経路で実 spread/fill/latency)
- Live ramp は別フェーズ

つまり本タスクは「実装 + BT 軽量 check → shadow promote 提案」まで。Live 昇格判定は別タスク。

## Audit Axis 8 抜粋

> Tier 3/4 ではないが、Tier 1 (LIVE) かつ GBP_USD の tier-master EV が `-0.013`、直近 live aggregate でも `xs_momentum` は N=4, WR=25.0%, Wilson lo=4.56%, EV=-5.40p, PF=0.507, Kelly=0.0000 と劣化しているため failure mode 診断対象とする。

破綻候補は Axis 3 が主因。現在の trigger は momentum thesis と整合しているが、closed-bar 化と per-bar dedup が strategy 内にないため、同一 momentum burst を 1 trade ではなく複数 entry に分割して浴びる構造になっている。Axis 5 は nominal には整合するが、Quick Harvest 後の実効 R:R が薄く、強い momentum を取り切る設計としては補助的な弱点がある。Axis 4 は hard break ではない。

再設計案は timing 修正を第一候補にする。`evaluate()` の trigger 後に `bar_id = ctx.bar_time or ctx.df.index[-1]` を使った `(symbol, signal, bar_id)

## Audit Redesign Recommendation 抜粋

> 思想と trigger の方向性は維持する。最小修正は timing 1 系統で、bar-close signal と per-bar dedup を strategy 側に持たせること。コードレベルでは `_mom` と `signal` が確定した直後に `bar_id` guard を置き、同一 `(ctx.symbol, signal, bar_id)` は `return None` にする案が最小差分になる。

# 1. 制約

## BT (軽量 filter)
- データソース: **MASSIVE 必須** (`data/cache/massive/{PAIR}_{TF}.parquet`)
- 環境: `BT_MODE=1` (Task A 完了後の MASSIVE-first 経路、Yahoo 経由禁止)
- 期間: 365d (cache 充足の場合)、最低 90d
- production の `run_daytrade_backtest()` を `backtest_mode=True` で呼ぶ — リサンプル代替禁止

## LOCK criteria (相対非破壊)

```yaml
non_catastrophic_check:
  - pf_change >= -0.05  # PF 5% 以内の悪化なら許容
  - wilson_lo_change >= -0.02  # Wilson lo 2pp 以内の悪化なら許容
  - n_change_pct >= -20  # 発火数 20% 以上の減少は NG
  - pnl_sign_preserved  # 正→負への符号反転は NG
positive_direction (少なくとも 1 つ):
  - wilson_lo_change >= +0.01
  - ev_change_pct >= +5
  - pf_change >= +0.02
sanity_floor:
  - wilson_lo_proposed >= 0.30  # 緩和: 完全 noise でない
  - pf_proposed >= 0.95  # PF 1 近傍でも shadow 投入可
```

**全 catastrophic check PASS + positive_direction 1 つ以上 PASS + sanity floor PASS → shadow promote 推奨**

絶対 Kelly 基準は使わない (W4P1 で誤りと判明)。

# 2. Implementation Steps

## Step 1: Pre-reg LOCK 文書

`knowledge-base/wiki/decisions/xs_momentum-shadow-redesign-2026-05-05.md`:
- 現行 vs proposed の差分 (audit 推奨に従う最小 1 軸)
- LOCK criteria (上記 yaml)
- shadow promote 後の N 蓄積目標 (60-90 日 or N>=30)

## Step 2: 失敗テスト追加

`tests/test_xs_momentum_shadow_redesign.py`

## Step 3: 実装

audit Axis 推奨に従い最小差分。**flag 配下** で実装 (`XS_MOMENTUM_REDESIGN_V2=1` 等)、デフォルトは現行維持。

## Step 4: テスト緑

## Step 5: BT 軽量 filter (MASSIVE + BT_MODE=1)

```bash
BT_MODE=1 python3 -c "
from app import run_daytrade_backtest
# baseline
r0 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['xs_momentum'], variant=False)
# proposed
r1 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['xs_momentum'], variant=True)
"
```

`knowledge-base/raw/bt-results/xs_momentum-shadow-bt-2026-05-05.json` に保存。

## Step 6: LOCK criteria 判定

PASS → Step 7、FAIL → REJECT 文書化、stop。

## Step 7: Shadow promote 提案

PASS の場合、shadow 設定を以下のどれかで提案:
- 環境変数フラグ ON (例: `STREAK_REVERSAL_HTF_SOFT_PENALTY=1`)
- routing config に shadow entry 追加
- demo_trader の shadow tier に登録

実装 merge は OK (live 経路は flag OFF で影響なし)、shadow 観測開始まで含む。

## Step 8: Codex self-review

- BT は relative check か (絶対 Kelly 基準を使っていないか)
- shadow 投入が production live を壊さないか (flag 配下確認)
- post-hoc adjustment になっていないか

# 3. Acceptance

- Pre-reg LOCK doc あり
- 失敗テスト → 緑
- BT 比較レポート (relative check) あり
- LOCK criteria verdict (PASS/REJECT)
- PASS なら shadow promote 設定 + N 蓄積目標明示
- Codex self-review 通過

# 4. Out of Scope

- Live 昇格 (本タスクは shadow promote まで、Live ramp は別フェーズ)
- N 蓄積の待機 (60-90 日後の判定は別 task)
- 他 strategies の修正

# 5. Notes

- BT を Live promotion gate に使う罠を避ける (W4P1 streak_reversal で発覚)
- shadow 観測中の N 蓄積は production 自然進行に任せる
- shadow-first アーキテクチャ: BT で大量 catastrophic 排除 → shadow で真値推定 → live ramp
- 60-90 日後に shadow data から Bonferroni/Wilson/Kelly 判定する別 task が後続


## Result (2026-05-05T08:28:19Z)

exit=0 · 2753s

```
Implemented `xs_momentum` V2 behind `XS_MOMENTUM_REDESIGN_V2=1`, default off.

Changed:
- [xs_momentum.py](/data/repo/fx-ai-trader/strategies/daytrade/xs_momentum.py): closed-bar signal values + per `(symbol, signal, bar_id)` dedup under flag.
- [test_xs_momentum_shadow_redesign.py](/data/repo/fx-ai-trader/tests/test_xs_momentum_shadow_redesign.py): failing coverage for default-off behavior, dedup, and live closed-bar semantics.
- [xs_momentum_shadow_bt.py](/data/repo/fx-ai-trader/tools/xs_momentum_shadow_bt.py): MASSIVE + `BT_MODE=1` A/B BT runner.
- [xs_momentum-shadow-redesign-2026-05-05.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/xs_momentum-shadow-redesign-2026-05-05.md): pre-reg LOCK, BT verdict, self-review.
- [xs_momentum-shadow-bt-2026-05-05.json](/data/repo/fx-ai-trader/knowledge-base/raw/bt-results/xs_momentum-shadow-bt-2026-05-05.json): BT comparison output.

Verification:
- `.venv/bin/pytest tests/test_xs_momentum_shadow_redesign.py` → `4 passed`
- `python3 -m py_compile strategies/daytrade/xs_momentum.py tools/xs_momentum_shadow_bt.py` → OK
- BT used `massive-parquet` for all target cells.

LOCK verdict: `REJECT`.

Reason: `GBP_USD` improved directionally but failed sanity floor:
- `GBP_USD`: PF `0.7722 < 0.95`, Wilson lo `0.5280`
- Overall: `FAIL / REJECT`

No shadow promote setting was applied.
```
