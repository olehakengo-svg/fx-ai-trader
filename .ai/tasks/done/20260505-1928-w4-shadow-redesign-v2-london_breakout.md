---
id: 20260505-1928-w4-shadow-redesign-v2-london_breakout
title: "[W4-Shadow-Redesign v2] london_breakout (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:28:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/london_breakout.md
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

W4-EDA audit (`audits/edge_design/london_breakout.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) だが、tier-master の 365d BT EV が `—` で昇格根拠がなく、関連 C-1 GBP_JPY 12yr primary も Wilson lo/PF/Bonferroni/Sharpe が不合格なので failure mode 診断を適用する。破綻軸は Axis 2、Axis 3、Axis 5。思想は「London open における Asia range breakout」で明確だが、現コードは Asia session 固定窓ではなく rolling 120 bars を使い、確定bar/entry timing/dedup の契約も strategy 内にない。さらに fixed TP/SL のみで breakout continuation を伸ばす exit geometry になっていない。

再設計案は、まず trigger/timing を同時に閉じること。`asia_high/asia_low` は `00:00-06:59 UTC` などの prior session fixed window から確定済みbarだけで計算し、entry は `last_closed_close > asia_high + buffer` / `< asia_low - buffer` の bar-close trigger 

## Redesign Recommendation 抜粋

> Trigger は rolling range から fixed Asia session range へ変える。コードレベルでは `ctx.df.iloc[-self.asia_bars:]` をやめ、UTC timestamp index から London 当日の `00:00 <= t < 07:00` または broker定義の Asia window を切り出す。判定は current/intrabar `ctx.entry` ではなく、確定済み signal bar の close が `asia_high + buffer` / `asia_low - buffer` を超えた時だけに寄せる。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/london_breakout.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`LONDON_BREAKOUT_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_london_breakout_shadow_redesign_v2.py`

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
- BT report (`bt-results/london_breakout-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-05T23:48:20Z)

exit=0 · 3047s

```
実装完了しました。

主な変更:
- [strategies/scalp/london_breakout.py](/data/repo/fx-ai-trader/strategies/scalp/london_breakout.py:39)
  `LONDON_BREAKOUT_REDESIGN_V2=1` の時だけ、rolling 120 bars ではなく UTC `00:00 <= t < 07:00` の fixed Asia window を使い、確定済み close で breakout 判定します。default OFF なので既存 live 挙動は不変です。
- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:187)
  `LONDON_BREAKOUT_REDESIGN_V2=1` かつ `LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE=1` の double flag 時だけ shadow loser emit 対象に登録。
- [tools/london_breakout_shadow_bt.py](/data/repo/fx-ai-trader/tools/london_breakout_shadow_bt.py:1)
  365d MASSIVE A/B BT runner 追加。`app.run_daytrade_backtest(..., backtest_mode=True)` を呼び、strategy-filter compute patch で `london_breakout` のみ比較。
- [tests/test_london_breakout_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_london_breakout_shadow_redesign_v2.py:77)
  default OFF 保持、fixed Asia window、closed-bar 判定、double-flag shadow 登録をテスト。

BT report:
- [bt-results/london_breakout-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/london_breakout-shadow-redesign-v2-2026-05-05.json:1)
- Overall verdict: `PASS`
- Shadow recommendation: `RECOMMEND_SHADOW`

Proposed 365d MASSIVE results:
- `USD_JPY`: N=103, PF=2.1348, Wilson_lo=0.6872, EV=1.0216
- `EUR_USD`: N=250, PF=1.7361, Wilson_lo=0.6823, EV=0.6840
- `GBP_USD`: N=288, PF=1.3609, Wilson_lo=0.6462, EV=0.3762
- `EUR_JPY`: N=185, PF=1.6603, Wilson_lo=0.6729, EV=0.6306
- `GBP_JPY`: N=217, PF=1.5457, Wilson_lo=0.6461, EV=0.5610

Verification:
- `.venv/bin/pytest tests/test_london_breakout_shadow_redesign_v2.py -q` → `5 passed`
- `.venv/bin/python -m py_compile strategies/scalp/london_breakout.py tools/london_breakout_shadow_bt.py` → passed
- JSON validation for the BT report → passed

Codex self-review: criteria は v2 どおり catastrophic/floor のみで、positive direction や absolute Kelly は要求していません。baseline が `<20` で sample不足だった cell は、proposed N>=20 のため即 REJECT には
…(truncated)
