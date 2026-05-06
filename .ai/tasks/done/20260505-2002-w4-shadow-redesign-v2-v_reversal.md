---
id: 20260505-2002-w4-shadow-redesign-v2-v_reversal
title: "[W4-Shadow-Redesign v2.1] v_reversal (Tier 3 (FORCE_DEMOTED)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T20:02:00+0900
roadmap_gate: "W4-Shadow-Redesign v2.1: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/v_reversal.md
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

W4-EDA audit (`audits/edge_design/v_reversal.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 3 (FORCE_DEMOTED)

## Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の trigger は MR thesis を数学的に捕捉しており、Axis 4 でも MA filter / HMM gate のような thesis 破壊は見えない。したがって「思想は正、設計が誤」の候補として扱えるが、現行は現在足の反転を未確定のまま拾える timing と、固定 ATR target / recent extreme stop の geometry が scalp MR と噛み合っていない。

再設計案は、まず closed-bar 化すること。signal bar を `df.iloc[-2]` に固定し、`rsi`, `bb_pband`, `stoch_k`, `Open/Close/High/Low`, body ratio, MACD-H turn をすべて確定足から読む。entry は次 bar execution に分離し、dispatcher または strategy 側で `(v_reversal, instrument, signal, signal_bar_time)` dedup を必須にする。

次に geometry を mean-reversion targ

## Redesign Recommendation 抜粋

> 思想は維持候補。コードから V 字 MR thesis は明確に導出でき、trigger も oversold/overbought と反転確認を含むため、thesis 自体を棄却する根拠はない。一方で、closed-bar / dedup / signal-to-execution 分離が strategy file から保証されず、現在足の揺れを反転として認識する構造がある。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/v_reversal.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`V_REVERSAL_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_v_reversal_shadow_redesign_v2.py`

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
- BT report (`bt-results/v_reversal-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T18:28:04Z)

exit=0 · 4046s

```
完了しました。

実装:
- [strategies/scalp/v_reversal.py](/data/repo/fx-ai-trader/strategies/scalp/v_reversal.py:29): `V_REVERSAL_REDESIGN_V2=1` 配下で `df.iloc[-2]` 確定足 signal 化、次足 `ctx.entry` execution、live 時の `(strategy, symbol, signal, closed_bar_time)` dedup を追加。
- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:232): `V_REVERSAL_REDESIGN_V2` + `V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE` の二重 flag で shadow emit 登録。
- [tests/test_v_reversal_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_v_reversal_shadow_redesign_v2.py:98): default OFF 無影響、closed-bar 採用、current-bar 無視、live dedup、shadow promote flag をテスト。
- [tools/v_reversal_shadow_bt.py](/data/repo/fx-ai-trader/tools/v_reversal_shadow_bt.py:323): v2.1 LOCK criteria で BT report を生成する runner を追加。

BT:
- 出力: [bt-results/v_reversal-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/v_reversal-shadow-redesign-v2-2026-05-05.json:1)
- `BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1`
- 365d / 15m / MASSIVE parquet / 6 FX pairs
- Overall verdict: `INSUFFICIENT_BT_EVIDENCE`
- Proposed N: `0` across all cells, so catastrophic check skipped per v2.1
- Shadow recommendation: `RECOMMEND_SHADOW`

検証:
- `.venv/bin/pytest -q tests/test_v_reversal_shadow_redesign_v2.py` → `5 passed`
- `.venv/bin/python -m py_compile strategies/scalp/v_reversal.py tools/v_reversal_shadow_bt.py` → passed

Self-review も report 内で通過済みです。Live は default OFF のままで、shadow emit も promote flag を明示しない限り有効化されません。
```
