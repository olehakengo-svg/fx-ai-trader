---
id: 20260505-1913-w4-shadow-redesign-v2-ema200_trend_reversal
title: "[W4-Shadow-Redesign v2] ema200_trend_reversal (Tier 1 (LIVE)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:13:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema200_trend_reversal.md
related:
  - knowledge-base/wiki/lessons/feedback_shadow_first_quant_architecture.md
  - knowledge-base/wiki/lessons/feedback_audit_purpose_design_not_n.md
---

# 0. v1 から v2 への変更点

v1 spec で 5/5 REJECT した教訓:
- 90d minimum で発火不足 → relative check 判定不可 → REJECT (asia_range_fade_v1 の例)
- BT を filter のはずが Live promotion 級基準を要求してしまっていた

**v2 緩和点:**
1. **minimum_days 90 → 365** (低発火戦略でも N >= 20 取れるように)
2. **BT で <20 trades なら `INSUFFICIENT_BT_EVIDENCE` → shadow promote** (BT 判定保留、shadow で実測)
3. **catastrophic check のみ重視**: PF, Wilson lo, EV の急激悪化を排除するだけ
4. **positive direction は緩いor) なし** (BT bias 大きいので強要しない)
5. **Live 影響皆無の flag 配下実装** が必須

# 1. 再設計対象

W4-EDA audit (`audits/edge_design/ema200_trend_reversal.md`):
- Verdict: **THESIS_VALID_INSUFFICIENT_EVIDENCE** / Recommendation: **A**
- Tier: Tier 1 (LIVE)

## Axis 8 抜粋

> Tier 1 (LIVE) かつ pair_promoted だが、BT 365d 側は USDJPY 負 EV / PF<1 の記録があり、直近 R2 cell demotion lock でも hour 17/20 の小 N loss が WATCH、hour 13 の N=1 win が KEEP という粒度に分解されている。Axis 2/3/5 のコード設計は thesis と整合しており、破綻は trigger 数式そのものではない。失敗候補は Axis 4 の「必要な timing/session filter がコードにない」点と Axis 7 の decision-grade evidence 不足。

再設計案: trigger と R:R は維持し、USDJPY の live routing を暫定的に Overlap/NY-overlap 相当の `12 <= ctx.hour_utc < 16` に絞る timing filter を追加する。昇格根拠が Overlap N=7, WR=100%, EV_cost=+11.63p に集中しているため、全時間帯に同じ EMA200 retest thesis を強制するより、session-gated pullback として再定義して shadow / micro-live で N>=30 を蓄積する。

## Redesign Recommendation 抜粋

> 最小の再設計は timing filter 1 系統。`evaluate()` の冒頭または `_crosses` 通過後に USDJPY pair-promoted 用の session gate を置き、`ctx.hour_utc` が Overlap/NY-overlap 外なら `return None` にする案が最も小さい。これにより、EMA200 retest trigger / MACD再加速 / 2:1 R:R は維持したまま、昇格根拠のある時間帯だけを live 対象にできる。

# 2. v2 LOCK criteria (緩和版)

```yaml
catastrophic_check (NG なら REJECT):
  - pf_change >= -0.10  # 10% 悪化までは許容 (v1 は -5%)
  - wilson_lo_change >= -0.05  # 5pp 悪化まで許容 (v1 は -2%)
  - n_change_pct >= -30  # 30% 減少まで許容
  - pnl_sign_preserved  # 正→負への符号反転は NG (絶対)

shadow_promote_decision:
  - if catastrophic_check ALL PASS:
      → shadow promote 推奨 (BT は filter として通過、shadow で本判定)
  - else:
      → REJECT (catastrophic regression 確定)

  Optional: positive direction は spec に書かない (BT bias が大きいため)

bt_evidence_threshold:
  - if N (proposed BT trades) < 20:
      → "INSUFFICIENT_BT_EVIDENCE" verdict
      → catastrophic_check skip、shadow promote 推奨 (live で N 蓄積)

  - else:
      → catastrophic check 適用

sanity_floor (どんなに緩くても禁止):
  - wilson_lo_proposed >= 0.20  # noise すれすれは shadow にも出さない
  - pf_proposed >= 0.85  # 著しく赤字方向は shadow promote しない
```

# 3. BT 仕様

- **データソース**: `data/cache/massive/{PAIR}_{TF}.parquet` (MASSIVE 由来必須)
- **環境**: `BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1` (Yahoo fallback 禁止)
- **期間**: **365d** (90d ではなく、低発火対応)
- **production の `run_daytrade_backtest()` を `backtest_mode=True` で呼ぶ**
- リサンプル代替禁止

# 4. Implementation Steps

## Step 1: 既存 audit 確認 (`audits/edge_design/ema200_trend_reversal.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`EMA200_TREND_REVERSAL_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_ema200_trend_reversal_shadow_redesign_v2.py`

## Step 4: 365d BT (BT_MODE=1, MASSIVE)

baseline (現行) vs proposed (V2 flag ON) を 365d で比較。

## Step 5: v2 LOCK criteria 適用

`§2 catastrophic_check + bt_evidence_threshold + sanity_floor` で判定。

## Step 6: Shadow promote (if applicable)

PASS or INSUFFICIENT_BT_EVIDENCE → shadow promote (config / env flag で worker に登録)
REJECT → 文書化のみ、shadow 設定変更なし

## Step 7: Codex self-review

- catastrophic check のみで shadow promote 判定しているか
- absolute Kelly 基準を要求していないか
- live 影響が flag OFF で完全に zero か
- post-hoc adjustment ないか

# 5. Acceptance

- 実装 (flag 配下、live OFF default)
- 失敗テスト緑
- BT report (`bt-results/ema200_trend_reversal-shadow-redesign-v2-2026-05-05.json`)
- v2 LOCK verdict (PASS / INSUFFICIENT_BT_EVIDENCE / REJECT)
- Codex self-review 通過

# 6. Out of Scope

- Live 昇格 (shadow promote までで停止)
- 長期 (60-90 日) shadow N 蓄積判定 (別 task で後続)
- 他 strategies

# 7. Notes

- v1 spec で 5/5 REJECT は spec の問題 — **v2 では緩和**
- N<20 の場合は「BT で判定不能なので shadow に出して実測」が正しい (BT bias を真値扱いしない)
- post-hoc justification 罠 — 「v1 を救済する」のではなく「shadow-first 原則を厳密に適用」


## Result (2026-05-05T17:16:57Z)

exit=0 · 800s

```
実装と検証まで完了しました。`EMA200_TREND_REVERSAL_REDESIGN_V2=1` 配下でのみ、`ema200_trend_reversal` を USDJPY かつ `12 <= hour_utc < 16` に絞る session gate を追加しました。default OFF なので live 影響はありません。

変更ファイル:
- [ema200_reversal.py](/data/repo/fx-ai-trader/strategies/daytrade/ema200_reversal.py)
- [__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py)
- [test_ema200_trend_reversal_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_ema200_trend_reversal_shadow_redesign_v2.py)
- [ema200_trend_reversal_shadow_bt.py](/data/repo/fx-ai-trader/tools/ema200_trend_reversal_shadow_bt.py)
- [ema200_reversal_shadow_bt.py](/data/repo/fx-ai-trader/tools/ema200_reversal_shadow_bt.py)
- [ema200_trend_reversal-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/ema200_trend_reversal-shadow-redesign-v2-2026-05-05.json)

BT verdict: `REJECT`

Reason:
- baseline: `N=113`, `PF=1.0126`, `wilson_lo=0.5274`, `PnL=1.0084`
- proposed: `N=32`, `PF=1.1154`, `wilson_lo=0.4831`, `PnL=2.4174`
- proposed N is `32`, so `N<20` の `INSUFFICIENT_BT_EVIDENCE` 免除は使えません
- `n_change_pct=-71.6814%` が v2 catastrophic threshold `>= -30%` に違反
- sanity floor は PASS、Kelly / positive direction は要求していません

Shadow promote は `REJECT` のため有効化していません。double-flag の登録経路は実装済みですが、`EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE=1` を明示しない限り worker 登録されません。

Verification:
- `.venv/bin/pytest -q tests/test_ema200_trend_reversal_shadow_redesign_v2.py tests/test_ema200_reversal_shadow_redesign_v2.py tests/test_dt_sr_channel_shadow_redesign_v2.py` → `16 passed`
- `.venv/bin/python tools/ema200_trend_reversal_shadow_bt.py` → report generated
- `git diff --check` → clean
```
