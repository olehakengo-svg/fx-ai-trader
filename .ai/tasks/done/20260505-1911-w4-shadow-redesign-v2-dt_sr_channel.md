---
id: 20260505-1911-w4-shadow-redesign-v2-dt_sr_channel
title: "[W4-Shadow-Redesign v2] dt_sr_channel (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:11:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/dt_sr_channel.md
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

W4-EDA audit (`audits/edge_design/dt_sr_channel.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) だが phase0_shadow / ALL で tier-master 365d BT EV は `—`、May 3 gate progression は PF=0.854 / raw Kelly=-0.0856、Apr 28 negative-edge audit では by-strategy PF=0.30 なので underperforming として failure mode 診断を適用する。

破綻軸は Axis 3 と Axis 5、補助的に Axis 6。Trigger は SR/channel 端 + RSI/MACD 反転で MR thesis と整合するが、closed-bar 化と per-bar dedup が戦略内にないため signal timing が実行層依存になっている。さらに stop/TP が 1ATR stop / 2ATR target の trend-follow 型 geometry で、SR/channel MR の「境界外まで耐えて mean 側へ戻る」構造と噛み合っていない。ALL scope も USD_JPY 以外の negative pockets を混ぜている。

再設計案は、まず closed-bar signal に固定し、`signal_bar = ctx.df.iloc[-2]` 

## Redesign Recommendation 抜粋

> 思想は有効候補として残す。SR/channel 端での反発を RSI/MACD 反転で拾う thesis はコードから明確に導出でき、trigger 自体も大枠では MR と整合している。一方で、現在の実装は signal timing と stop/TP geometry が MR 用に固定されておらず、ALL scope で負の pair/session を混ぜている。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/dt_sr_channel.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`DT_SR_CHANNEL_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_dt_sr_channel_shadow_redesign_v2.py`

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
- BT report (`bt-results/dt_sr_channel-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-05T16:48:57Z)

exit=0 · 4126s

```
実装完了。ただし v2 LOCK verdict は **REJECT** なので、shadow promote は有効化していません。

変更点:
- [strategies/daytrade/dt_sr_channel.py](/data/repo/fx-ai-trader/strategies/daytrade/dt_sr_channel.py:20)
  - `DT_SR_CHANNEL_REDESIGN_V2=1` 配下で closed-bar signal 固定
  - `ctx.df.iloc[-2]` の SR/channel proximity、RSI、MACD-H turn で判定
  - live 時のみ `(symbol, entry_type, signal_bar_time, direction)` dedup
  - boundary 外 SL + mean-side TP の MR geometry
- [app.py](/data/repo/fx-ai-trader/app.py:6438)
  - V2 flag 時だけ BT が dt_sr_channel の戦略 SL/TP を保存し、MR geometry を評価可能に調整
- [strategies/daytrade/__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py:245)
  - shadow worker 登録は `DT_SR_CHANNEL_REDESIGN_V2=1` かつ `DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE=1` の二重 flag 必須
- [tests/test_dt_sr_channel_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_dt_sr_channel_shadow_redesign_v2.py:86)
  - default OFF 保持、closed-bar 判定、current-bar 無視、dedup、double-flag shadow 登録をテスト
- [tools/dt_sr_channel_shadow_bt.py](/data/repo/fx-ai-trader/tools/dt_sr_channel_shadow_bt.py:21)
  - 365d MASSIVE baseline/proposed BT runner 追加

BT report:
- [bt-results/dt_sr_channel-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/dt_sr_channel-shadow-redesign-v2-2026-05-05.json)
- MASSIVE parquet 使用確認: all target `data_source: massive-parquet`
- Overall: **REJECT**
- 主因:
  - `USD_JPY`: PF 0.9339 → 0.7635、sanity floor NG
  - `EUR_JPY`: PF 0.9993 → 0.6743、sanity floor NG
  - `GBP_JPY`: PnL +13.7663 → -48.3385 で `pnl_sign_preserved=false`
  - `EUR_USD` のみ PASS

Verification:
- `.venv/bin/pytest -q tests/test_dt_sr_channel_shadow_redesign_v2.py tests/test_dt_bb_rsi_mr_shadow_redesign_v2.py tests/test_asia_range_fade_v1_shadow_redesign_v2.py` → 14 passed
- `.venv/bin/python -m py_compile app.py strategies/daytrade/dt_sr_channel.py strategies/daytrade/__init__.py tools/dt_sr_channel_shadow_bt.py` → passed

Self-review:
- catastrophic check + sanity floor のみで判定、Kelly/po
…(truncated)
