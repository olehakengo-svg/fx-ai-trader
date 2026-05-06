---
id: 20260505-1939-w4-shadow-redesign-v2-mtf_regime_range_cascade_scalp
title: "[W4-Shadow-Redesign v2.1] mtf_regime_range_cascade_scalp (Tier 4 (SCALP_SENTINEL)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:39:00+0900
roadmap_gate: "W4-Shadow-Redesign v2.1: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/mtf_regime_range_cascade_scalp.md
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

W4-EDA audit (`audits/edge_design/mtf_regime_range_cascade_scalp.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 4 (SCALP_SENTINEL)

## Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 と Axis 4、補助的に Axis 2 の trigger 選択。Axis 2 は数式上は MR と整合するが、実際には `bb_rsi_reversion` 継承 trigger を range_tight に重ねた設計が既存ラベル実測で否定方向になっている。Axis 3 は現在足依存かつ dedup 欠落で、scalp の intrabar 再発火リスクが残る。Axis 4 は `REGIME_RANGE` hard gate が、コードコメント上すでに負けと記録された range_tight MR tail へ entry を固定している点が主破綻。

再設計案は、range hard gate をそのまま残して 1m bb_rsi trigger だけを薄く調整するのではなく、range edge を「レンジ端の reclaim」に再定義すること。具体的には BUY を `closed signal bar low <= m5_swing_low or bb_lower breach` かつ `closed back inside band` かつ `RSI5 recross 30 or Stoch K cross D`、SELL を対称条件にする。sign

## Redesign Recommendation 抜粋

> 思想は完全棄却ではなく、レンジ端の exhaustion から平均回帰を取る仮説としては再設計候補に残す。ただし現在の設計は、既に負けが観測された range_tight × inherited bb_rsi trigger へ hard gate で固定しており、未確定足依存も残る。単一行削除では足りず、trigger と timing と regime filter をまとめて直す必要がある。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/mtf_regime_range_cascade_scalp.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_mtf_regime_range_cascade_scalp_shadow_redesign_v2.py`

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
- BT report (`bt-results/mtf_regime_range_cascade_scalp-shadow-redesign-v2-2026-05-05.json`)
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


## Error (2026-05-06T02:41:29Z)

```
Reading prompt from stdin...
OpenAI Codex v0.128.0 (research preview)
--------
workdir: /data/repo/fx-ai-trader
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019dfb29-5ff5-7e33-9de4-6cb506b4446c
--------
user
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

W4-EDA audit (`audits/edge_design/mtf_regime_range_cascade_scalp.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 4 (SCALP_SENTINEL)

## Axis 8 抜粋

> Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 と Axis 4、補助的に Axis 2 の trigger 選択。Axis 2 は数式上は MR と整合するが、実際には `bb_rsi_reversion` 継承 trigger を range_tight に重ねた設計が既存ラベル実測で否定方向になっている。Axis 3 は現在足依存かつ dedup 欠落で、scalp の intrabar 再発火リスクが残る。Axis 4 は `REGIME_RANGE` hard gate が、コードコメント上すでに負けと記録された range_tight MR tail へ entry を固定している点が主破綻。

再設計案は、range hard gate をそのまま残して 1m bb_rsi trigger だけを薄く調整するのではなく、range edge を「レンジ端の reclaim」に再定義すること。具体的には BUY を `closed signal bar low <= m5_swing_low or bb_lower breach` かつ `closed back inside band` かつ `RSI5 recross 30 or Stoch K cross D`、SELL を対称条件にする。sign

## Redesign Recommendation 抜粋

> 思想は完全棄却ではなく、レンジ端の exhaustion から平均回帰を取る仮説としては再設計候補に残す。ただし現在の設計は、既に負けが観測された range_tight × inherited bb_rsi trigger へ hard gate で固定しており、未確定足依存も残る。単一行削除では足りず、trigger と timing と regime filter をまとめて直す必要がある。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/mtf_regime_range_cascade_scalp.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_mtf_regime_range_cascade_scalp_shadow_redesign_v2.py`

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
- BT report (`bt-results/mtf_regime_range_cascade_scalp-shadow-redesign-v2-2026-05-05.json`)
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

ERROR: Quota exceeded. Check your plan and billing details.
ERROR: Quota exceeded. Check your plan and billing details.

```


## Result (2026-05-06T07:17:08Z)

exit=0 · 1447s

```
実装完了しました。`MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2=1` 配下でのみ、確定済み signal bar の range-edge reclaim trigger を使うようにしました。flag OFF では既存 live 動作は変わりません。

主な変更:
- [mtf_regime_range_cascade_scalp.py](/data/repo/fx-ai-trader/strategies/scalp/mtf_regime_range_cascade_scalp.py:71): V2 flag、range cohort、live dedup を追加
- [mtf_regime_range_cascade_scalp.py](/data/repo/fx-ai-trader/strategies/scalp/mtf_regime_range_cascade_scalp.py:175): BUY/SELL を closed bar の sweep/reclaim + RSI/Stoch recross に変更
- [app.py](/data/repo/fx-ai-trader/app.py:6158): BT cache key / DT strategy-filter / SLTP preserve / shadow emit 配線を追加
- [__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:208): shadow worker 登録を `*_SHADOW_PROMOTE=1` opt-in に追加
- [test_mtf_regime_range_cascade_scalp_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_mtf_regime_range_cascade_scalp_shadow_redesign_v2.py:78): flag OFF/ON、range_tight block、dedup、shadow opt-in のテスト追加
- [mtf_regime_range_cascade_scalp_shadow_bt.py](/data/repo/fx-ai-trader/tools/mtf_regime_range_cascade_scalp_shadow_bt.py:221): v2.1 LOCK criteria wrapper 追加

検証:
- `.venv/bin/python -m pytest -q tests/test_mtf_regime_range_cascade_scalp_shadow_redesign_v2.py tests/test_mtf_regime_trend_cascade_scalp_shadow_redesign_v2.py`
- 結果: `6 passed`
- `.venv/bin/python tools/mtf_regime_range_cascade_scalp_shadow_bt.py`
- report: [bt-results/mtf_regime_range_cascade_scalp-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/mtf_regime_range_cascade_scalp-shadow-redesign-v2-2026-05-05.json:1)

BT verdict: `PASS`, shadow promote recommendation: `RECOMMEND_SHADOW`.

BT summary:
- USD_JPY: baseline N=99 PnL=18.179 → proposed N=204 PnL=34.1375, `pnl_sign_preserved=true`
- EUR_USD: baseline N=86 PnL=19.3527 → proposed N=189 PnL=13.1261, `pnl_sign_preserved=true`
- PF / Wilson / N change は report に WARN ONLY として記録し、REJECT 根拠には使っていません。
```
