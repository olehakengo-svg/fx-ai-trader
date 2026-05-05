---
id: 20260505-1914-w4-shadow-redesign-v2-ema_cross
title: "[W4-Shadow-Redesign v2] ema_cross (Tier 3 (FORCE_DEMOTED)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:14:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema_cross.md
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

W4-EDA audit (`audits/edge_design/ema_cross.md`):
- Verdict: **THESIS_VALID_TIMING_BROKEN** / Recommendation: **A**
- Tier: Tier 3 (FORCE_DEMOTED)

## Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) のため failure mode を診断する。Axis 2/4/5 は strategy file 単体では大きく破綻していない。trigger は trend-retest を捕捉し、ADX/HTF filter は thesis を補強し、2:1 TP/SL も momentum geometry と整合する。

破綻軸は主に Axis 3。current-bar の `ctx.entry/open_price/macdh/rsi` による confirmation と strategy 内 dedup 欠落が、live intrabar では未確定足の見かけの再加速を拾う。加えてクロスから 2-8 本待つ retest 設計は thesis と矛盾しないが、既存 evidence の負け方を見る限り、発火が「再加速」ではなく「クロス後に伸び切った current-bar continuation」を追っている可能性が高い。Axis 6 の ALL forced scope も失敗を増幅しており、USDJPY の narrow SELL tail と London BUY の負けを同じ戦略集計に混ぜている。

再設計案は timing と cell scope の切り分けを最小単位にする。Trigger 本体は維持しつつ、confi

## Redesign Recommendation 抜粋

> 思想は有効候補として残す。EMA cross + pullback + ADX/HTF alignment は trend-retest の入口として自然で、現行コードから thesis を捏造せずに読める。失敗の中心は trigger そのものより、未確定 current bar を confirmation として読む timing 契約と、ALL scope で tail と toxic cell を混ぜる運用設計にある。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/ema_cross.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`EMA_CROSS_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_ema_cross_shadow_redesign_v2.py`

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
- BT report (`bt-results/ema_cross-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-05T17:50:50Z)

exit=0 · 1998s

```
実装完了しました。

変更点:
- [ema_cross.py](/data/repo/fx-ai-trader/strategies/daytrade/ema_cross.py:37)
  - `EMA_CROSS_REDESIGN_V2=1` 配下で closed-bar confirmation に切替
  - current/intrabar の `entry/open/macdh/rsi/ema_score` を confirmation に使わない
  - live 時のみ `(symbol, direction, signal_bar_time)` dedup
  - default OFF なので既存 live 挙動は変更なし

- [__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py:254)
  - `EMA_CROSS_REDESIGN_V2=1`
  - `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE=1`
  の double flag で shadow worker emit に登録

- [test_ema_cross_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_ema_cross_shadow_redesign_v2.py:1)
  - default OFF 保持
  - V2 closed-bar 使用
  - current-bar だけの intrabar signal reject
  - live dedup
  - shadow promote double flag

- [ema_cross_shadow_bt.py](/data/repo/fx-ai-trader/tools/ema_cross_shadow_bt.py:1)
  - 365d MASSIVE BT report generator

BT report:
- [ema_cross-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/ema_cross-shadow-redesign-v2-2026-05-05.json:1)
- Target: `USD_JPY`
- Baseline: `N=31`, `PF=0.5627`, `Wilson_lo=0.2916`, `PnL=-14.1281`
- Proposed: `N=38`, `PF=1.1441`, `Wilson_lo=0.4989`, `PnL=3.5346`
- v2 LOCK verdict: `PASS`
- Shadow recommendation: `RECOMMEND_SHADOW`

Verification:
- `15 passed` via:
  - `tests/test_ema_cross_shadow_redesign_v2.py`
  - `tests/test_adx_trend_continuation_shadow_redesign_v2.py`
  - `tests/test_dt_bb_rsi_mr_shadow_redesign_v2.py`

Self-review:
- Catastrophic/floor criteria only; Kelly and positive-direction are not required.
- Live impact is zero unless `EMA_CROSS_REDESIGN_V2=1`.
- Shadow emit still requires explicit `EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE=1`.
- No post-hoc parameter adjustment after BT.
```
