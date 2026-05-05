---
id: 20260505-1219-w4-shadow-redesign-three_bar_reversal
title: "[W4-Shadow Phase 1] three_bar_reversal (Tier 2 (Shadow)) — implement + shadow promote (BT light filter)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T12:19:00+0900
roadmap_gate: "W4 Shadow-first redesign — quant 推奨 (BT は軽量 filter、shadow が真の estimator)"
rule: R1
prereq_artifacts:
  - audits/edge_design/three_bar_reversal.md
  - knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
related:
  - knowledge-base/wiki/lessons/feedback_audit_purpose_design_not_n.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/three_bar_reversal.md`) で **THESIS_VALID_TIMING_BROKEN** / 推奨度 **A** と判定。

**クオンツ推奨アーキテクチャ** (2026-05-05 user指摘で確定):
- BT は **軽量 sanity filter** (catastrophic regression 排除のみ)、Live promotion gate ではない
- Shadow が **真の estimator** (production 経路で実 spread/fill/latency)
- Live ramp は別フェーズ

つまり本タスクは「実装 + BT 軽量 check → shadow promote 提案」まで。Live 昇格判定は別タスク。

## Audit Axis 8 抜粋

> Tier 2 Shadow の underperforming/low-evidence cell として診断する。破綻軸は主に Axis 3、補助的に Axis 2 の trigger 過密化である。思想は「3本足の過伸展を逆張る」MR として妥当だが、現行 trigger は `3本連続足 + 現在足反転色 + 前足高値/安値突破 + BB%B + RSI5` を同時要求するため、反転の初動ではなく確認後の遅い場所に寄り、既存 decomposition でも「4条件同時必須 → 180日でN=6、年間N=12では統計検証不能」と記録されている。

再設計案は1案に絞る。過伸展条件は維持し、entry confirmation を「前足高値/安値 breakout」から「現在足が反対色で、前足実体 midpoint または前足 open を回復/割れ」に緩める。具体的には BUY を `_three_bear and _curr_bull and ctx.entry > float(ctx.df.iloc[-2]["Open"]) and ctx.bbpb < 0.40 and ctx.rsi5 < 45`、SELL を対称条件にする。これにより MR の反転初動を拾い、bar-close variant では `df.iloc[-2]` 確定足で反転確認、intrabar v

## Audit Redesign Recommendation 抜粋

> Trigger の思想自体は残す。変更対象は confirmation timing で、前足高値/安値の完全突破を必須にする現行条件を、前足実体の回復/割れまたは前足 midpoint cross に置き換える。BB%B と RSI5 は過伸展 gate として維持しつつ、閾値は `0.35/0.65, 42/58` から `0.40/0.60, 45/55` 程度に緩める候補を pre-register する。

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

`knowledge-base/wiki/decisions/three_bar_reversal-shadow-redesign-2026-05-05.md`:
- 現行 vs proposed の差分 (audit 推奨に従う最小 1 軸)
- LOCK criteria (上記 yaml)
- shadow promote 後の N 蓄積目標 (60-90 日 or N>=30)

## Step 2: 失敗テスト追加

`tests/test_three_bar_reversal_shadow_redesign.py`

## Step 3: 実装

audit Axis 推奨に従い最小差分。**flag 配下** で実装 (`THREE_BAR_REVERSAL_REDESIGN_V2=1` 等)、デフォルトは現行維持。

## Step 4: テスト緑

## Step 5: BT 軽量 filter (MASSIVE + BT_MODE=1)

```bash
BT_MODE=1 python3 -c "
from app import run_daytrade_backtest
# baseline
r0 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['three_bar_reversal'], variant=False)
# proposed
r1 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['three_bar_reversal'], variant=True)
"
```

`knowledge-base/raw/bt-results/three_bar_reversal-shadow-bt-2026-05-05.json` に保存。

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
