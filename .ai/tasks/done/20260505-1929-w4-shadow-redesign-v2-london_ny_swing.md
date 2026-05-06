---
id: 20260505-1929-w4-shadow-redesign-v2-london_ny_swing
title: "[W4-Shadow-Redesign v2] london_ny_swing (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:29:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/london_ny_swing.md
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

W4-EDA audit (`audits/edge_design/london_ny_swing.md`):
- Verdict: **THESIS_VALID_TIMING_BROKEN** / Recommendation: **A**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) のため昇格前 failure mode として診断する。主破綻は Axis 3。思想と trigger は明確で、filters も continuation thesis を破壊していないが、strategy 内では signal bar を確定足として固定する契約、signal→next-bar execution、同一bar dedup が保証されていない。副次的には Axis 6/7 で、tier-master 上は ALL / phase0_shadow として扱われる一方、コードは EURUSD/GBPUSD 専用で、さらに audit DB には対象行が 0 件である。

再設計案は timing hardening を最小単位にする。London range は現行どおり過去barから算出しつつ、trigger 判定を `signal_bar = ctx.df.iloc[-2]` の close/open に固定し、entry は次bar execution の `ctx.entry` として分離する。あわせて `(symbol, strategy, signal, bar_time)` の last-emitted guard を strategy または dispatch 層に置き、同一bar複数 Candidate を禁止する。

## Redesign Recommendation 抜粋

> Trigger の思想自体は維持する。修正対象は timing 1 系統で、`ctx.entry > _ldn_high + ATR*buffer` / `< _ldn_low - ATR*buffer` を current context の即時判定として扱うのではなく、確定済み signal bar の close で breakout と陽線/陰線を判定し、execution price は次barに分ける。これにより intrabar 更新や同一bar再評価での runaway を切れる。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/london_ny_swing.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`LONDON_NY_SWING_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_london_ny_swing_shadow_redesign_v2.py`

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
- BT report (`bt-results/london_ny_swing-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T00:22:34Z)

exit=0 · 2019s

```
完了しました。

実装:
- [strategies/daytrade/london_ny_swing.py](/data/repo/fx-ai-trader/strategies/daytrade/london_ny_swing.py): `LONDON_NY_SWING_REDESIGN_V2=1` 配下で timing hardening を追加。live は末尾未確定 bar を使わず closed signal bar で trigger 判定、execution は `ctx.entry` のまま分離。同一 `(symbol, strategy, signal, signal_bar)` dedup も追加。
- [strategies/daytrade/__init__.py](/data/repo/fx-ai-trader/strategies/daytrade/__init__.py): `LONDON_NY_SWING_REDESIGN_V2` + `LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE` の二重 flag で shadow-always 登録。
- [app.py](/data/repo/fx-ai-trader/app.py): BT cache key に V2 flag を追加し、baseline/proposed 混線を防止。
- [tests/test_london_ny_swing_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_london_ny_swing_shadow_redesign_v2.py): default OFF、closed-bar trigger、dedup、shadow promote double flag をテスト。
- [tools/london_ny_swing_shadow_bt.py](/data/repo/fx-ai-trader/tools/london_ny_swing_shadow_bt.py): 365d MASSIVE A/B BT runner を追加。

BT report:
- [bt-results/london_ny_swing-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/london_ny_swing-shadow-redesign-v2-2026-05-05.json)
- Overall verdict: `PASS`
- Shadow recommendation: `RECOMMEND_SHADOW`

Key BT results:
- `EUR_USD`: proposed N=144, PF=2.028, Wilson lo=0.6587, catastrophic PASS
- `GBP_USD`: proposed N=151, PF=1.7591, Wilson lo=0.6525, catastrophic PASS
- MASSIVE source verified: `massive-parquet`, no missing caches.

Verification:
- `.venv/bin/pytest -q tests/test_london_ny_swing_shadow_redesign_v2.py` → `5 passed`
- `.venv/bin/pytest -q tests/test_london_ny_swing_shadow_redesign_v2.py tests/test_asia_range_fade_v1_shadow_redesign_v2.py tests/test_adx_trend_continuation_shadow_redesign_v2.py` → `14 passed`
- `.venv/bin/python -m py_compile ...` → passed
- 365d BT: `BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1`, `run_daytrade_backtest(..., backtest_mode=True)`

Self-review passed: no Kelly/positive-direction requirement was used, catastrophic/floor only; V2 is defa
…(truncated)
