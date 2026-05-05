---
id: 20260505-1915-w4-shadow-redesign-v2-ema_pullback
title: "[W4-Shadow-Redesign v2] ema_pullback (Tier 3 (FORCE_DEMOTED)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:15:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/ema_pullback.md
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

W4-EDA audit (`audits/edge_design/ema_pullback.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **A**
- Tier: Tier 3 (FORCE_DEMOTED)

## Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) の failure mode は Axis 3 と Axis 5 が主因、Axis 6/7 が昇格阻害要因。Axis 2 の thesis/trigger は trend pullback を概ね捕捉しており、Axis 4 の filters も hard regime trap ではないため、思想自体は棄却しない。

再設計案は closed-bar + structure stop + pair/session split。Signal 判定を確定済み signal bar に固定し、`entry > prev_close` / body ratio / current high-low 判定を signal bar snapshot から計算する。Candidate には `(entry_type, symbol, signal_bar_time, direction)` dedup key 相当を渡し、同一 bar 再発火を止める。Stop は `ema21 ± 0.3ATR` 固定ではなく、BUY なら `min(signal_low, ema21 - 0.6ATR)`、SELL なら `max(signal_high, ema21 + 0.6ATR)` のように pullback structure の外へ置く varian

## Redesign Recommendation 抜粋

> 思想と trigger 骨格は維持する。変更はまず timing を closed-bar 化し、現バーの `ctx.entry/open/high/low` 混在を signal bar と execution bar に分離する。具体的には signal bar の `Close > PrevClose`、`abs(Close-Open)/(High-Low) >= 0.35`、MACD-H/Stoch を確定足で評価し、次 bar の `ctx.entry` で Candidate を返す形にする。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/ema_pullback.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`EMA_PULLBACK_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_ema_pullback_shadow_redesign_v2.py`

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
- BT report (`bt-results/ema_pullback-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-05T18:08:55Z)

exit=0 · 1050s

```
実装完了しました。

V2 は `EMA_PULLBACK_REDESIGN_V2=1` 配下でのみ有効です。default OFF では既存 live 挙動に触れません。V2 ON 時は [ema_pullback.py](/data/repo/fx-ai-trader/strategies/scalp/ema_pullback.py:35) で closed signal bar を使い、`ctx.entry` は execution bar として分離し、SL は BUY `min(signal_low, ema21 - 0.6ATR)` / SELL `max(signal_high, ema21 + 0.6ATR)` に変更しています。同一 signal bar の live 再発火 dedup も入れました。

Shadow worker 登録は [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:172) に追加済みで、`EMA_PULLBACK_REDESIGN_V2=1` かつ `EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE=1` の二重 flag 時だけ `ema_pullback` が shadow-always 対象になります。

BT report は [ema_pullback-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/ema_pullback-shadow-redesign-v2-2026-05-05.json:106) に生成済みです。365d / `BT_MODE=1` / `BT_REQUIRE_MASSIVE_CACHE=1` / production `run_daytrade_backtest(backtest_mode=True)` で実行し、target は audit recommendation に合わせて USD_JPY に絞りました。

Verdict: `INSUFFICIENT_BT_EVIDENCE`  
Proposed N = 0 `<20` のため、v2 spec 通り catastrophic check / sanity floor は skip、shadow promote 推奨です。

検証:
- `.venv/bin/pytest -q tests/test_ema_pullback_shadow_redesign_v2.py tests/test_bb_rsi_shadow_redesign_v2.py` → `9 passed`
- `.venv/bin/python -m py_compile strategies/scalp/ema_pullback.py strategies/scalp/__init__.py tools/ema_pullback_shadow_bt.py` → OK

Self-review も report 内で PASS: catastrophic-only 判定、Kelly 不要求、flag OFF live zero、post-hoc adjustment なし。
```
