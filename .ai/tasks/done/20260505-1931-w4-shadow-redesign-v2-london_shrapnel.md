---
id: 20260505-1931-w4-shadow-redesign-v2-london_shrapnel
title: "[W4-Shadow-Redesign v2] london_shrapnel (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:31:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/london_shrapnel.md
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

W4-EDA audit (`audits/edge_design/london_shrapnel.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) だが、phase0_shadow / ALL の tier-master metric は `—`、audit DB 上も発火行 0 件で、既存本番監査では scalp/1h engine NEVER_EVER 群に入っている。したがって metrics 劣化というより、設計検証不能な under-evidenced shadow cell として failure mode を診断する。

破綻軸は Axis 2、Axis 3、Axis 5。Axis 1 の thesis は明確で、Axis 4 の pair/time/oscillator filters も大きくは thesis を壊していない。一方、trigger は「巨大ヒゲ」だけで liquidity level sweep を要求しないため stop-hunt thesis とずれる。timing は current bar の High/Low と `ctx.entry` でヒゲと足色を同時判定し、closed-bar / dedup が strategy 内にない。stop/TP はヒゲが大きいほど risk が拡大するのに TP は固定 `0.8ATR` で、false-break reversal としての expectancy を高 WR に依存させすぎる。

再設計案は、まず 

## Redesign Recommendation 抜粋

> 思想は捨てない。London/NY overlap の巨大ヒゲを stop-hunt の反転として扱う thesis はコードから明確に読め、EURUSD/GBPUSD という対象 pair も自然。ただし現行の trigger は stop-hunt ではなく generic long-wick reversal に近く、timing と stop/TP も同時に直す必要があるため、単一行修正の S/A ではなく B とする。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/london_shrapnel.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`LONDON_SHRAPNEL_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_london_shrapnel_shadow_redesign_v2.py`

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
- BT report (`bt-results/london_shrapnel-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T01:04:18Z)

exit=0 · 1382s

```
実装完了です。

変更点:
- [strategies/scalp/london_shrapnel.py](/data/repo/fx-ai-trader/strategies/scalp/london_shrapnel.py:66)
  - `LONDON_SHRAPNEL_REDESIGN_V2=1` 配下でのみ V2 有効化
  - closed-bar の `sweep + reclaim` trigger
  - current/intrabar 判定を避ける next execution 形式
  - per-bar dedup
  - bounded target geometry
- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:190)
  - `LONDON_SHRAPNEL_REDESIGN_V2=1`
  - `LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE=1`
  - の二重 flag 時だけ shadow worker emit 対象に登録
- [tests/test_london_shrapnel_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_london_shrapnel_shadow_redesign_v2.py:102)
  - default OFF legacy preservation
  - V2 sweep/reclaim required
  - closed-bar execution
  - dedup
  - shadow promote double-flag registration
- [tools/london_shrapnel_shadow_bt.py](/data/repo/fx-ai-trader/tools/london_shrapnel_shadow_bt.py:1)
  - 365d MASSIVE BT report generator

Verification:
- `./.venv/bin/python -m pytest tests/test_london_shrapnel_shadow_redesign_v2.py -q` → `5 passed`
- `./.venv/bin/python -m py_compile tools/london_shrapnel_shadow_bt.py strategies/scalp/london_shrapnel.py` → OK
- `git diff --check` → OK
- 365d BT completed with `BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1`

BT report:
- [bt-results/london_shrapnel-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/london_shrapnel-shadow-redesign-v2-2026-05-05.json:1)
- EUR_USD proposed N=0
- GBP_USD proposed N=0
- Overall verdict: `INSUFFICIENT_BT_EVIDENCE`
- Recommendation: `RECOMMEND_SHADOW`

Per v2 LOCK criteria, proposed N<20 なので catastrophic check は skip、Kelly/positive direction は要求していません。Live impact は default OFF で、shadow emit も二重 flag がない限り有効化されません。
```
