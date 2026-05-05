---
id: 20260505-1240-w4-shadow-redesign-bb_rsi
title: "[W4-Shadow Phase 1] bb_rsi (Tier 2 (Shadow)) — implement + shadow promote (BT light filter)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T12:40:00+0900
roadmap_gate: "W4 Shadow-first redesign — quant 推奨 (BT は軽量 filter、shadow が真の estimator)"
rule: R1
prereq_artifacts:
  - audits/edge_design/bb_rsi.md
  - knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
related:
  - knowledge-base/wiki/lessons/feedback_audit_purpose_design_not_n.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/bb_rsi.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **B** と判定。

**クオンツ推奨アーキテクチャ** (2026-05-05 user指摘で確定):
- BT は **軽量 sanity filter** (catastrophic regression 排除のみ)、Live promotion gate ではない
- Shadow が **真の estimator** (production 経路で実 spread/fill/latency)
- Live ramp は別フェーズ

つまり本タスクは「実装 + BT 軽量 check → shadow promote 提案」まで。Live 昇格判定は別タスク。

## Audit Axis 8 抜粋

> Tier 2 (Shadow) だが、SCALP_SENTINEL かつ EUR_JPY / EUR_USD / GBP_USD / USD_JPY が pair_demoted で、既存 audit も negative/insufficient が混在するため failure mode 診断対象とする。

破綻軸は Axis 3 と Axis 4。Axis 2 の trigger は BB/RSI/Stoch の MR と整合しており、Axis 5 も RR floor 後は算数破綻をかなり修正している。主問題は、現在足の `entry/open` 反転確認を closed-bar/dedup なしで使う timing と、USD/JPY の `ADX>=30` を edge tail として加点しながら MR anti-trend confidence penalty で同じ tail を減点する filter/scoring 矛盾である。

再設計案は 2 段。まず signal を closed bar 化し、同一 `(symbol, signal, bar_time)` の再 emit を禁止する。次に JPY high-ADX tail を採用する variant と、純 range MR variant を分離する。具体的には JPY variant では `ADX

## Audit Redesign Recommendation 抜粋

> 思想は捨てない。BB/RSI/Stoch extreme からの反転を狙う MR thesis はコードから明確に導出でき、trigger 自体も概ね妥当。ただし現行設計は timing と regime/scoring が混線しているため、単一行削除ではなく複数軸の再設計が必要。

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

`knowledge-base/wiki/decisions/bb_rsi-shadow-redesign-2026-05-05.md`:
- 現行 vs proposed の差分 (audit 推奨に従う最小 1 軸)
- LOCK criteria (上記 yaml)
- shadow promote 後の N 蓄積目標 (60-90 日 or N>=30)

## Step 2: 失敗テスト追加

`tests/test_bb_rsi_shadow_redesign.py`

## Step 3: 実装

audit Axis 推奨に従い最小差分。**flag 配下** で実装 (`BB_RSI_REDESIGN_V2=1` 等)、デフォルトは現行維持。

## Step 4: テスト緑

## Step 5: BT 軽量 filter (MASSIVE + BT_MODE=1)

```bash
BT_MODE=1 python3 -c "
from app import run_daytrade_backtest
# baseline
r0 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['bb_rsi'], variant=False)
# proposed
r1 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['bb_rsi'], variant=True)
"
```

`knowledge-base/raw/bt-results/bb_rsi-shadow-bt-2026-05-05.json` に保存。

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
