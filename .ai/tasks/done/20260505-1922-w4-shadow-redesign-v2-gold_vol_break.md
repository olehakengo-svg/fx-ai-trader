---
id: 20260505-1922-w4-shadow-redesign-v2-gold_vol_break
title: "[W4-Shadow-Redesign v2] gold_vol_break (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:22:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/gold_vol_break.md
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

W4-EDA audit (`audits/edge_design/gold_vol_break.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 3/4 ではなく Tier 2 Shadow だが、既存資料上は XAU production-excluded かつ promotion-grade empirical evidence がない。設計破綻候補は Axis 3 と Axis 5。Axis 2/4 は thesis と整合しており、MR に MA filter を足す型や HMM hard gate で regime tail を消す型ではない。一方、current context の未確定 15m 足で BB 突破・body・DI を評価でき、strategy 内に per-bar dedup がないため、bar-close 前提が崩れると一時的な spike を複数回 chase する。さらに breakout thesis に対して固定 3ATR TP / 1ATR SL は、XAU の retest と trend continuation の両方に中途半端で、伸びる局面を capped にし、初動 wick で切られやすい。

再設計案は timing と geometry の 2 点。Trigger は思想に合っているので維持し、`signal_bar = ctx.df.iloc[-2]` の確定足 close で BB(2.5σ) breakout、ATR surge、ADX/DI、body 

## Redesign Recommendation 抜粋

> 思想は維持する。最小変更は、未確定足依存を外して bar-close signal に固定すること。BUY は `signal_close > bb_upper_25_signal AND signal_close > signal_open AND +DI_signal > -DI_signal AND ATR7_signal > ATR14_signal*1.05`、SELL は対称条件にし、signal bar の次 bar でだけ Candidate を emit する。同一 `signal_bar_time` からの再 emit は拒否する。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/gold_vol_break.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`GOLD_VOL_BREAK_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_gold_vol_break_shadow_redesign_v2.py`

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
- BT report (`bt-results/gold_vol_break-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-05T19:49:32Z)

exit=0 · 204s

```
完了しました。

実装は Axis 3 の最小変更に絞り、`GOLD_VOL_BREAK_REDESIGN_V2=1` のときだけ確定足 `ctx.df.iloc[-2]` の BB(2.5σ) breakout / ATR surge / ADX-DI / body で判定し、同一 `signal_bar_time` の再 emit を dedup します。default OFF なので live 既存挙動は変わりません。  
該当: [gold_vol_break.py](/data/repo/fx-ai-trader/strategies/daytrade/gold_vol_break.py:47)

shadow worker 登録は二重 flag です。`GOLD_VOL_BREAK_REDESIGN_V2=1` かつ `GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE=1` のときだけ `gold_vol_break` を shadow-always に入れます。  
該当: [__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py:263)

BT 比較用に `run_daytrade_backtest()` の cache key に `GOLD_VOL_BREAK_REDESIGN_V2` を追加しました。baseline/proposed が同一プロセスで混ざらないようにするためです。  
該当: [app.py](/data/repo/fx-ai-trader/app.py:6150)

追加テスト: [test_gold_vol_break_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_gold_vol_break_shadow_redesign_v2.py:111)

検証:
- `.venv/bin/pytest -q tests/test_gold_vol_break_shadow_redesign_v2.py` → `5 passed`
- `.venv/bin/pytest -q tests/test_gold_vol_break_shadow_redesign_v2.py tests/test_gold_trend_momentum_shadow_redesign_v2.py` → `10 passed`
- `python3 -m py_compile ...` → OK
- `git diff --check` → OK

BT report は生成済みです: [gold_vol_break-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/gold_vol_break-shadow-redesign-v2-2026-05-05.json:1)

v2 LOCK verdict は **REJECT** です。理由は catastrophic regression ではなく、必須の `data/cache/massive/XAU_USD_15m.parquet` が存在せず、`BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1` で production `run_daytrade_backtest()` が Yahoo/API fallback を拒否して停止したためです。これは `N<20` の `INSUFFICIENT_BT_EVIDENCE` ではなく、mandatory source unavailable として分離しました。shadow promote 設定は有効化していません。
```
