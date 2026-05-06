---
id: 20260505-1947-w4-shadow-redesign-v2-squeeze
title: "[W4-Shadow-Redesign v2.1] squeeze (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:47:00+0900
roadmap_gate: "W4-Shadow-Redesign v2.1: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/squeeze.md
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

W4-EDA audit (`audits/edge_design/squeeze.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **A**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) だが `bb_squeeze_breakout` は tier-master 上で主要 6 pair が PAIR_DEMOTED 扱いで、既存 audit artifact も negative / insufficient が混在するため failure mode を診断する。破綻軸は Axis 2, 3, 5。Axis 2 は「breakout」と称しながら BB 外・range 外への break を要求せず、BB 内 quartile + EMA 順列で入るため false breakout を多く拾う。Axis 3 は未確定足と同一 bar 再発火を strategy 内で抑止しない。Axis 5 は initial R:R こそ 2.5R だが fixed ATR TP/SL のみで、breakout tail を trailing で伸ばす構造ではない。

再設計案は 1 系統にまとめる。Trigger を `squeeze_precondition AND release_bar_closed AND actual_breakout` に変更し、BUY は `prev_close <= upper_band_prev AND signal_close > upper_band_signal` または `signal_close > 

## Redesign Recommendation 抜粋

> 思想は明確で、squeeze から volatility expansion を取る方向性自体は有効候補として残せる。ただし現行 trigger は breakout を数学的に捕捉していないため、最優先修正は Axis 2 の trigger 再定義。`bbpb > 0.75` / `< 0.25` を breakout proxy として使うのをやめ、確定足 close が BB upper/lower または squeeze range high/low を明確に抜けた時だけ signal にする。EMA9/EMA21 は hard gate として残すなら trend continuation filter、または score bonus に下げる。

# 2. v2.1 LOCK criteria (shadow-first 修正)

**v2 → v2.1 修正理由**: v2 spec の `pf_change >= -0.10` / `wilson_lo_change >= -0.05` / `n_change_pct >= -30` / `sanity_floor PF>=0.85, Wilson_lo>=0.20` は実質 Live promotion 級基準であり、`feedback_shadow_first_quant_architecture` の「BT は filter、shadow が真の estimator」と矛盾する。N drop は redesign が signal を絞った正常な結果であり、shadow で観察すべき。PF<0.85 の戦略でも shadow に投入して live で N 蓄積するのが正順 (`feedback_audit_purpose_design_not_n`)。

```yaml
catastrophic_check (NG なら REJECT — これだけが REJECT 根拠):
  - pnl_sign_preserved  # baseline_pnl > 0 かつ proposed_pnl < 0 のとき NG (正→負への符号反転)
  ※ 上記以外 (PF 悪化、Wilson_lo 悪化、N drop) は WARN としてレポートに記録するが REJECT には使わない

shadow_promote_decision:
  - if pnl_sign_preserved == True (正→正 / 負→正 / 負→負 / 0→任意):
      → shadow promote 推奨 (BT は filter として通過、shadow で本判定)
  - else (正→負 確定):
      → REJECT (真の catastrophic regression のみ)

bt_evidence_threshold:
  - if N (proposed BT trades) < 20:
      → "INSUFFICIENT_BT_EVIDENCE" verdict
      → catastrophic_check skip、shadow promote 推奨 (live で N 蓄積)
  - else:
      → pnl_sign_preserved 単独で判定

sanity_floor: **REMOVED in v2.1**
  ※ v2 で PF>=0.85 / Wilson_lo>=0.20 floor が dt_bb_rsi_mr / engulfing_bb / dt_sr_channel
     を誤って REJECT した。shadow 観察に floor は不要。
     proposed_pnl < 0 の戦略は pnl_sign_preserved=False で自動 catch される。

n_change_pct, pf_change, wilson_lo_change: **WARN ONLY in v2.1**
  ※ レポートに記録するが、verdict には使わない。shadow で観察、6mo OOS で再判定。

XAU データ不在 / 必須 parquet 不在の扱い:
  - 戦略が XAU を必須としかつ data/cache/massive/XAU_USD_*.parquet が無い場合
      → "BLOCKED_DATA" verdict (REJECT ではない)
      → shadow promote は flag 配下で実装のみ、デフォルト OFF (データ調達後に opt-in)
```

# 3. BT 仕様

- **データソース**: `data/cache/massive/{PAIR}_{TF}.parquet` (MASSIVE 由来必須)
- **環境**: `BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1` (Yahoo fallback 禁止)
- **期間**: **365d** (90d ではなく、低発火対応)
- **production の `run_daytrade_backtest()` を `backtest_mode=True` で呼ぶ**
- リサンプル代替禁止

# 4. Implementation Steps

## Step 1: 既存 audit 確認 (`audits/edge_design/squeeze.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`SQUEEZE_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_squeeze_shadow_redesign_v2.py`

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
- BT report (`bt-results/squeeze-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T06:18:46Z)

exit=0 · 1372s

```
実装完了しました。

変更点:
- [strategies/scalp/squeeze.py](/data/repo/fx-ai-trader/strategies/scalp/squeeze.py:26)
  - `SQUEEZE_REDESIGN_V2=1` 配下で V2 trigger を追加。
  - `df.iloc[-2]` の確定足だけを signal bar として使い、BB upper/lower cross または直近 range high/low break を要求。
  - default OFF では既存ロジック無変更。
  - live bar_time なしは block、同一 signal bar dedup も追加。
- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:169)
  - `SQUEEZE_REDESIGN_V2=1` + `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE=1` の時だけ shadow emit 対象化。
- [app.py](/data/repo/fx-ai-trader/app.py:6405)
  - `run_daytrade_backtest()` の strategy-filter BT 用 qualified type に `bb_squeeze_breakout` を追加。live signal には影響なし。
- [tests/test_squeeze_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_squeeze_shadow_redesign_v2.py:1)
  - default OFF、closed-bar breakout、BBPB proxy reject、intrabar reject、dedup、shadow opt-in をテスト。
- [tools/squeeze_shadow_bt.py](/data/repo/fx-ai-trader/tools/squeeze_shadow_bt.py:1)
  - 365d MASSIVE A/B BT runner を追加。

BT report:
- [bt-results/squeeze-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/squeeze-shadow-redesign-v2-2026-05-05.json:1)
- Overall verdict: `INSUFFICIENT_BT_EVIDENCE`
- Shadow recommendation: `RECOMMEND_SHADOW`
- Cell verdicts:
  - `USD_JPY`: `PASS`
  - `EUR_USD`: `INSUFFICIENT_BT_EVIDENCE`
  - `GBP_USD`: `PASS`
  - `EUR_JPY`: `PASS`
  - `GBP_JPY`: `PASS`
  - `EUR_GBP`: `INSUFFICIENT_BT_EVIDENCE`

Verification:
- `.venv/bin/pytest -q tests/test_squeeze_shadow_redesign_v2.py tests/test_keltner_squeeze_breakout_shadow_redesign_v2.py`
- Result: `13 passed`
- `py_compile` passed for changed Python files.

Self-review passed: no Kelly/live-promotion criteria used, no positive-direction requirement, default live behavior remains OFF, and BT used `BT_MODE=1` + `BT_REQUIRE_MASSIVE_CACHE=1` with MASSIVE parquet.
```
