---
id: 20260505-1209-w4-shadow-redesign-htf_false_breakout
title: "[W4-Shadow Phase 1] htf_false_breakout (Tier 2 (Shadow)) — implement + shadow promote (BT light filter)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T12:09:00+0900
roadmap_gate: "W4 Shadow-first redesign — quant 推奨 (BT は軽量 filter、shadow が真の estimator)"
rule: R1
prereq_artifacts:
  - audits/edge_design/htf_false_breakout.md
  - knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
related:
  - knowledge-base/wiki/lessons/feedback_audit_purpose_design_not_n.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/htf_false_breakout.md`) で **THESIS_VALID_DESIGN_BROKEN** / 推奨度 **A** と判定。

**クオンツ推奨アーキテクチャ** (2026-05-05 user指摘で確定):
- BT は **軽量 sanity filter** (catastrophic regression 排除のみ)、Live promotion gate ではない
- Shadow が **真の estimator** (production 経路で実 spread/fill/latency)
- Live ramp は別フェーズ

つまり本タスクは「実装 + BT 軽量 check → shadow promote 提案」まで。Live 昇格判定は別タスク。

## Audit Axis 8 抜粋

> Tier 2 Shadow だが、既存 evidence は N=1 の小標本で、phase0_shadow のまま昇格判断に耐えない。破綻軸は Axis 2 と Axis 3。思想は false breakout fade として明確だが、実装は 1H close breakout を数学的に作らず、15m 単体 close を疑似 1H として扱っている。さらに SR slice が breakout 候補 bar を混ぜるため、breakout 検出窓がコメント通りの 1-4本確認になっていない。

再設計案は、trigger/timing を一体で直すこと。15m df から明示的に 1H OHLC を resample/aggregate し、SR は breakout 1H bar より前の 20本だけで計算する。その後、breakout 1H bar の close が SR 外へ出たことを state として保持し、次の 1-4本の closed 15m bar で SR 内へ戻った最初の close だけを entry signal とする。ALL 運用ではなく、既存 WF が安定している GBP_JPY/EUR_JPY を優先 shadow cell に絞り、GBP_USD/EUR_USD/USD_JPY は redesign 後 BT で再判定する。

## Audit Redesign Recommendation 抜粋

> Trigger/timing の 1 系統修正で復活余地がある。具体的には、`_sr_slice` を現在時点基準ではなく breakout 候補 1H bar 基準に変更し、`for _offset in range(...)` で 15m 単体 bar を見る処理を廃止する。想定 diff は、1H resample 済み series から `break_h1 = h1.iloc[-2]` などの closed H1 bar を選び、`sr_high/low = h1.iloc[-22:-2].High/Low` のように breakout bar を含めない窓で計算し、15m re-entry は breakout 後の closed 15m bars のみを対象にする形。

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

`knowledge-base/wiki/decisions/htf_false_breakout-shadow-redesign-2026-05-05.md`:
- 現行 vs proposed の差分 (audit 推奨に従う最小 1 軸)
- LOCK criteria (上記 yaml)
- shadow promote 後の N 蓄積目標 (60-90 日 or N>=30)

## Step 2: 失敗テスト追加

`tests/test_htf_false_breakout_shadow_redesign.py`

## Step 3: 実装

audit Axis 推奨に従い最小差分。**flag 配下** で実装 (`HTF_FALSE_BREAKOUT_REDESIGN_V2=1` 等)、デフォルトは現行維持。

## Step 4: テスト緑

## Step 5: BT 軽量 filter (MASSIVE + BT_MODE=1)

```bash
BT_MODE=1 python3 -c "
from app import run_daytrade_backtest
# baseline
r0 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['htf_false_breakout'], variant=False)
# proposed
r1 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['htf_false_breakout'], variant=True)
"
```

`knowledge-base/raw/bt-results/htf_false_breakout-shadow-bt-2026-05-05.json` に保存。

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
