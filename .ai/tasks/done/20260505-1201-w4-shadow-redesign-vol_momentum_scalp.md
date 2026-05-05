---
id: 20260505-1201-w4-shadow-redesign-vol_momentum_scalp
title: "[W4-Shadow Phase 1] vol_momentum_scalp (Tier 1 (LIVE)) — implement + shadow promote (BT light filter)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T12:01:00+0900
roadmap_gate: "W4 Shadow-first redesign — quant 推奨 (BT は軽量 filter、shadow が真の estimator)"
rule: R1
prereq_artifacts:
  - audits/edge_design/vol_momentum_scalp.md
  - knowledge-base/wiki/decisions/w4-redesign-lock-criteria-v2-2026-05-05.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
related:
  - knowledge-base/wiki/lessons/feedback_audit_purpose_design_not_n.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-EDA audit (`audits/edge_design/vol_momentum_scalp.md`) で **THESIS_VALID_TIMING_BROKEN** / 推奨度 **A** と判定。

**クオンツ推奨アーキテクチャ** (2026-05-05 user指摘で確定):
- BT は **軽量 sanity filter** (catastrophic regression 排除のみ)、Live promotion gate ではない
- Shadow が **真の estimator** (production 経路で実 spread/fill/latency)
- Live ramp は別フェーズ

つまり本タスクは「実装 + BT 軽量 check → shadow promote 提案」まで。Live 昇格判定は別タスク。

## Audit Axis 8 抜粋

> Tier 3/4 ではないが、Tier 1 (LIVE) で Axis 7 が insufficient、かつ Axis 3 に timing 実装リスクがあるため診断対象とする。Axis 2/4/5 は momentum breakout thesis と整合しており、現時点で「思想は正、trigger/filter/geometry も概ね正」と見る。破綻候補は Axis 3 の closed-bar / per-bar dedup 不在で、live 実行層が intrabar evaluate する場合に BB %B と足色が未確定のまま発火する。

再設計案は timing hardening 1 系統。`evaluate()` 内で signal bar を closed bar に固定し、`ctx.entry` は次 bar execution として扱う。さらに `(symbol, strategy, signal, bar_id)` の last-emitted guard を strategy または実行層に持たせ、同一 5m bar の多重 Candidate を防ぐ。既存 positive pocket を壊す可能性があるため、本監査では実装せず、365d + WF folds>=3 + Bonferroni/Kelly で再検証する。

## Audit Redesign Recommendation 抜粋

> 最小修正は trigger の思想を変えず、timing だけを固めること。コードレベルでは `evaluate()` 冒頭または signal 確定直後に `bar_id = ctx.bar_time or ctx.df.index[-1]` 相当を得て、同一 `(ctx.symbol, self.name, signal, bar_id)` を再 emit しない guard を追加する案が第一候補になる。

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

`knowledge-base/wiki/decisions/vol_momentum_scalp-shadow-redesign-2026-05-05.md`:
- 現行 vs proposed の差分 (audit 推奨に従う最小 1 軸)
- LOCK criteria (上記 yaml)
- shadow promote 後の N 蓄積目標 (60-90 日 or N>=30)

## Step 2: 失敗テスト追加

`tests/test_vol_momentum_scalp_shadow_redesign.py`

## Step 3: 実装

audit Axis 推奨に従い最小差分。**flag 配下** で実装 (`VOL_MOMENTUM_SCALP_REDESIGN_V2=1` 等)、デフォルトは現行維持。

## Step 4: テスト緑

## Step 5: BT 軽量 filter (MASSIVE + BT_MODE=1)

```bash
BT_MODE=1 python3 -c "
from app import run_daytrade_backtest
# baseline
r0 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['vol_momentum_scalp'], variant=False)
# proposed
r1 = run_daytrade_backtest(pair=..., tf=..., days=365, strategies=['vol_momentum_scalp'], variant=True)
"
```

`knowledge-base/raw/bt-results/vol_momentum_scalp-shadow-bt-2026-05-05.json` に保存。

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


## Result (2026-05-05T02:16:50Z)

exit=0 · 1918s

```
実装と検証まで完了しました。結論は **LOCK FAIL → shadow promote は REJECT** です。

変更内容:
- [strategies/scalp/vol_momentum.py](/data/repo/fx-ai-trader/strategies/scalp/vol_momentum.py:66)
  - `VOL_MOMENTUM_SCALP_REDESIGN_V2=1` 配下で closed-bar signal 固定
  - `df.iloc[-2]` の `%B` / 足色 / ADX / DI / RSI / BB幅pct を評価
  - `ctx.entry` は次bar execution基準として維持
  - `(symbol, strategy, signal, bar_id)` dedup追加
  - default OFFなのでlive production影響なし
- [tests/test_vol_momentum_scalp_shadow_redesign.py](/data/repo/fx-ai-trader/tests/test_vol_momentum_scalp_shadow_redesign.py:104)
  - closed-bar使用、現行default不変、同一bar dedupをテスト
- [knowledge-base/wiki/decisions/vol_momentum_scalp-shadow-redesign-2026-05-05.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/vol_momentum_scalp-shadow-redesign-2026-05-05.md:1)
  - Pre-reg LOCKと判定結果を記録
- [knowledge-base/raw/bt-results/vol_momentum_scalp-shadow-bt-2026-05-05.json](/data/repo/fx-ai-trader/knowledge-base/raw/bt-results/vol_momentum_scalp-shadow-bt-2026-05-05.json:1)
  - 365d MASSIVE BT結果を保存
- [tools/vol_momentum_scalp_shadow_bt.py](/data/repo/fx-ai-trader/tools/vol_momentum_scalp_shadow_bt.py:1)
  - 再実行用BTスクリプト追加

BT結果:
- Runner: `run_scalp_backtest()` production scalp path
  - `vol_momentum_scalp` はScalp engine登録で、`run_daytrade_backtest()` では評価対象外になるため。
- Data: `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, `USD_JPY_5m.parquet`
- Current: `N=80`, `PF=1.4613`, `wilson_lo=0.5408`, `EV=0.2268`
- Proposed: `N=83`, `PF=1.4809`, `wilson_lo=0.5190`, `EV=0.2395`
- FAIL理由: `wilson_lo_change=-0.0218` がLOCK閾値 `>= -0.02` をわずかに下回りました。

Verification:
- `pytest tests/test_vol_momentum_scalp_shadow_redesign.py tests/test_squeeze_release_momentum_shadow_redesign.py tests/test_fetch_ohlcv_bt_mode.py` → `11 passed`
- `py_compile` → OK
- Self-review: relative checkのみ、Kelly絶対基準なし、flag default OFF、post-hoc adjustmentなし。

shadow promote設定は入れていません。
```
