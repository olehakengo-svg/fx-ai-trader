---
id: 20260505-1942-w4-shadow-redesign-v2-orb_trap
title: "[W4-Shadow-Redesign v2] orb_trap (Tier 3 (FORCE_DEMOTED)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:42:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/orb_trap.md
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

W4-EDA audit (`audits/edge_design/orb_trap.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **A**
- Tier: Tier 3 (FORCE_DEMOTED)

## Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) の failure mode は Axis 5 主体、補助的に Axis 6/7。Axis 2 の trigger は false breakout fade を捕捉しており、Axis 3 も bar-close confirmation として大きな破綻はない。Axis 4 の filters も entry universe を不自然に潰す MA/HMM 型の破壊ではなく、noise / whipsaw / true breakout 除外として概ね coherent。

破綻は exit geometry にある。コードは thesis 上の自然な利確点を OR 反対端に置くが、RR 最低値を満たさない場合に TP を OR 反対端の外へ動かす。これにより「レンジへ戻る」edge を取る MR ではなく、「レンジ回帰後もさらに同方向へ伸びる」edge を要求する設計になる。365d scan の全ペア負EVと、短期BTだけ好調だった履歴は、trigger ではなく TP geometry と pair/session 条件が相場局面に過適合していた可能性を示す。

再設計案は Stop/TP geometry を先に直すこと。具体的には、TP を常に `OR_low/OR_high` または `OR_mid` へ固定し、RR 不足

## Redesign Recommendation 抜粋

> 修正対象は主に stop/TP geometry の 1 系統。想定 diff は、`_rr < MIN_RR` の場合に `tp` を `ctx.entry +/- _sl_d * MIN_RR` へ延伸する処理を削除し、`return None` に変えるか、`MIN_RR` を `reward_to_or_edge / risk` の診断 metric に格下げする形。これで OR 反対端回帰という thesis と exit が一致する。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/orb_trap.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`ORB_TRAP_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_orb_trap_shadow_redesign_v2.py`

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
- BT report (`bt-results/orb_trap-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T03:57:46Z)

exit=0 · 2024s

```
実装と検証まで完了しました。

変更点:
- [orb_trap.py](/data/repo/fx-ai-trader/strategies/daytrade/orb_trap.py:45): `ORB_TRAP_REDESIGN_V2=1` を追加。
- [orb_trap.py](/data/repo/fx-ai-trader/strategies/daytrade/orb_trap.py:328): V2 有効時は RR 不足で TP を OR 反対端の外へ延伸せず、signal reject に変更。
- [__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py:284): shadow 登録は `ORB_TRAP_REDESIGN_V2=1` かつ `ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE=1` の double flag のみ。
- [test_orb_trap_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_orb_trap_shadow_redesign_v2.py:76): default-off、V2 reject、V2 valid TP、shadow double flag を追加。
- [orb_trap_shadow_bt.py](/data/repo/fx-ai-trader/tools/orb_trap_shadow_bt.py:1): MASSIVE 365d A/B BT runner 追加。

BT report:
- [orb_trap-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/orb_trap-shadow-redesign-v2-2026-05-05.json:1)
- Runner: `app.run_daytrade_backtest(backtest_mode=True)`
- Env: `BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1`
- Data source: MASSIVE parquet confirmed for 15m target caches.

LOCK verdict: `REJECT`

Key BT cells:
- `USD_JPY`: proposed `N=13` → `INSUFFICIENT_BT_EVIDENCE`, shadow would be allowed for this cell alone.
- `EUR_USD`: proposed `N=30`, PF change `-0.2162`, Wilson lo change `-0.1931`, N change `-85.29%` → catastrophic fail.
- `GBP_USD`: proposed `N=39`, PF change `-0.1120`, Wilson lo change `-0.1307`, N change `-76.92%` → catastrophic fail.

Because overall verdict is `REJECT`, I did not enable shadow promotion. The shadow worker path exists but remains inert unless both env flags are explicitly set.

Verification:
- `13 passed`: `tests/test_orb_trap_shadow_redesign_v2.py`, plus adjacent V2 shadow tests for `dt_bb_rsi_mr` and `asia_range_fade_v1`.
- `py_compile` passed for touched strategy/engine/tool files.

Self-review result: passed. The decision used only v2 catastrophic/floor rules where `N>=20`, skipped catastrophic for `N<20`, did not require Kelly or positive direction, kept 
…(truncated)
