---
id: 20260505-1954-w4-shadow-redesign-v2-stoch_pullback
title: "[W4-Shadow-Redesign v2.1] stoch_pullback (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:54:00+0900
roadmap_gate: "W4-Shadow-Redesign v2.1: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/stoch_pullback.md
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

W4-EDA audit (`audits/edge_design/stoch_pullback.md`):
- Verdict: **THESIS_VALID_TIMING_BROKEN** / Recommendation: **A**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) 指定だが、同一実装の `entry_type` はコード上 `stoch_trend_pullback` で、tier-master には FORCE_DEMOTED および USDJPY PAIR_DEMOTED としても現れる。既存 audit でも全体 N=142 / PF=0.64 / Kelly=-16.2%、3month H1 bucket 合算近似 N=181 / PF=0.54 / Kelly=-18.7% と underperforming なので failure mode 診断対象とする。

破綻軸は主に Axis 3。Axis 2 の trigger は trend-pullback thesis を捕捉しており、Axis 4 の filter は thesis を直接壊していない。Axis 5 の nominal R:R=2.25 も順張り pullback としては整合する。にもかかわらず成績が崩れる理由は、現在足の Stoch/EMA/price を intrabar で読める構造と dedup 欠落により、Stoch cross の「確定後回復」ではなく未確定の揺れを拾うリスクがあるため。副次的には Axis 6 の ALL 一括適用が session/pair loss pocket を混入させている。

再設計案は 

## Redesign Recommendation 抜粋

> 思想は有効候補として残す。Stoch pullback recovery を EMA/ADX trend 方向に限定する設計は明確で、MA filter on MR や HMM hard gate のような thesis 破壊は見えない。現行の最大問題は「回復を確定足で見ているか」が strategy file から保証されず、未確定足の K/D cross と price/EMA 条件で入れること。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/stoch_pullback.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`STOCH_PULLBACK_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_stoch_pullback_shadow_redesign_v2.py`

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
- BT report (`bt-results/stoch_pullback-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T13:15:49Z)

exit=0 · 1085s

```
実装完了しました。

主な変更:
- [strategies/scalp/stoch_pullback.py](/data/repo/fx-ai-trader/strategies/scalp/stoch_pullback.py:30)
  `STOCH_PULLBACK_REDESIGN_V2=1` のときだけ、直近確定足 `df.iloc[:-1].iloc[-1]` を signal bar として Stoch/EMA/RSI/BBPB を判定。live 時は `(symbol, signal, signal_bar_time)` で dedup。
- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:172)
  `STOCH_PULLBACK_REDESIGN_V2=1` かつ `STOCH_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE=1` の二重フラグ時だけ shadow worker に登録。
- [app.py](/data/repo/fx-ai-trader/app.py:6428)
  `run_daytrade_backtest()` の BT-only strategy-filter allowlist に `stoch_trend_pullback` を追加。
- [tests/test_stoch_pullback_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_stoch_pullback_shadow_redesign_v2.py:111)
  default OFF、closed-bar 判定、intrabar 無視、live dedup、shadow 二重フラグをテスト。
- [tools/stoch_pullback_shadow_bt.py](/data/repo/fx-ai-trader/tools/stoch_pullback_shadow_bt.py:1)
  365d MASSIVE / production `run_daytrade_backtest(backtest_mode=True)` runner を追加。v2.1 criteria は `pnl_sign_preserved` のみ REJECT 根拠、PF/Wilson/N は WARN ONLY。

検証:
- `.venv/bin/pytest -q tests/test_stoch_pullback_shadow_redesign_v2.py`
  `5 passed`
- `.venv/bin/python tools/stoch_pullback_shadow_bt.py`
  レポート生成済み: [bt-results/stoch_pullback-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/stoch_pullback-shadow-redesign-v2-2026-05-05.json)

BT 結果は `USD_JPY` 365d / MASSIVE parquet:
- baseline: `N=321`, `PnL=13.6167`, `PF=1.0665`, `Wilson_lo=0.5594`
- proposed: `N=313`, `PnL=17.8677`, `PF=1.0892`, `Wilson_lo=0.5681`
- v2.1 verdict: `PASS`
- shadow recommendation: `RECOMMEND_SHADOW`

Codex self-review もレポート内に記録済みです。Live は default OFF のままで、V2 挙動も shadow emit も環境変数を入れない限り有効になりません。
```
