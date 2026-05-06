---
id: 20260505-1933-w4-shadow-redesign-v2-ma_regime_switch
title: "[W4-Shadow-Redesign v2] ma_regime_switch (Tier 4 (SCALP_SENTINEL)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:33:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ma_regime_switch.md
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

W4-EDA audit (`audits/edge_design/ma_regime_switch.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **A**
- Tier: Tier 4 (SCALP_SENTINEL)

## Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 2 と Axis 4 が主、Axis 3 と Axis 5 が副次。思想は明確で、Trend branch と MR branch の局所 trigger もそれぞれ EMA/ADX continuation と BB%B/RSI/Stoch reversion を持つため、edge thesis 自体は捨てない。一方、中心の regime switch が M15 ATR rolling percentile ではなく 1m BB width percentile proxy で分岐しており、レジーム誤分類で Trend/MR の適用先を壊す。さらに bar-close/dedup 不在と、MR 側が mean target を持たない ATR 1.2R TP で、scalp の cost-edge ratio を吸収しにくい。

再設計案は Trigger/Filter 置換を主軸にする。`atr_pct = ctx.bb_width_pct * 100` を廃止し、実際の M15 ATR rolling percentile または少なくとも M15 BB/ATR percentile の同一時間足 proxy に置換する。High/Low/Mid の hard t

## Redesign Recommendation 抜粋

> 思想はコードから十分に導けるため `THESIS_INVALID` ではない。現行 v1c-rev は旧 v1c の N=22 機能不全から N=397 へ改善しているが、PF=0.939 / Kelly=0.0 / raw p=0.99999 で edge には届いていない。主因は hybrid thesis そのものより、regime trigger が thesis の M15 ATR percentile から 1m BB width proxy にすり替わっている点と、MR exit が mean-reversion geometry になっていない点にある。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/ma_regime_switch.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`MA_REGIME_SWITCH_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_ma_regime_switch_shadow_redesign_v2.py`

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
- BT report (`bt-results/ma_regime_switch-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T01:37:54Z)

exit=0 · 1756s

```
実装と検証まで完了しました。

変更内容:
- `ma_regime_switch` V2 flag 追加: `MA_REGIME_SWITCH_REDESIGN_V2`
- regime 判定を legacy の `ctx.bb_width_pct * 100` から、flag ON 時は M15 ATR rolling percentile (`atr_pct`) に切替
- live default OFF: `ScalperEngine` には V2 flag ON の時だけ登録
- shadow emit は二重 flag:
  - `MA_REGIME_SWITCH_REDESIGN_V2=1`
  - `MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE=1`
- BT/live HTF feature に `m15.atr_pct` を追加
- 専用テスト追加: `tests/test_ma_regime_switch_shadow_redesign_v2.py`
- BT runner/report 追加:
  - `tools/ma_regime_switch_shadow_bt.py`
  - `bt-results/ma_regime_switch-shadow-redesign-v2-2026-05-05.json`

検証:
- `.venv/bin/python -m pytest tests/test_ma_regime_switch_shadow_redesign_v2.py -q`
  - `5 passed`
- `.venv/bin/python -m pytest tests/test_ma_regime_switch_shadow_redesign_v2.py tests/test_bb_rsi_shadow_redesign_v2.py -q`
  - `9 passed`
- BT: `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, MASSIVE parquet 使用
  - runner: `app.run_daytrade_backtest`
  - interval: `15m`
  - USD_JPY baseline: `N=26`, `PF=0.8949`, `Wilson_lo=0.3546`, `PnL=-1.8131`
  - USD_JPY proposed: `N=131`, `PF=1.0664`, `Wilson_lo=0.5252`, `PnL=5.1733`

v2 LOCK verdict: `PASS`

理由:
- proposed `N=131 >= 20`
- `pf_change=+0.1715`
- `wilson_lo_change=+0.1706`
- `n_change_pct=+403.8462`
- PnL sign preserved
- sanity floor pass: `PF=1.0664 >= 0.85`, `Wilson_lo=0.5252 >= 0.20`

Codex self-review も report 内で PASS です。既存の未追跡 `ma_mr_hybrid` 関連ファイルは今回の対象外として触っていません。
```
