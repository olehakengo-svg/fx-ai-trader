---
id: 20260505-1935-w4-shadow-redesign-v2-macdh
title: "[W4-Shadow-Redesign v2] macdh (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:35:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/macdh.md
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

W4-EDA audit (`audits/edge_design/macdh.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) 指定だが、現行 tier-master では force_demoted と pair_demoted(GBP_USD) にも現れ、strategy aggregate は N=62, WR=32.26%, Wilson lo=21.95%, EV=-0.90, PF=0.468, Kelly=0.0000, Bonferroni p=1.0000。failure mode 診断対象として扱う。

破綻軸は Axis 3 と Axis 5。Axis 2 の thesis/trigger はコードから明確で、BB/RSI extreme と MACD-H exhaustion reversal は MR と整合している。Axis 4 の pair/time filter も大きくは破壊していない。一方、MACD-H 反転を current context で読み、bar-close/dedup 契約が strategy 内にないため、実運用では未確定足反転または同 bar 多重 entry の timing risk が残る。さらに 1ATR stop / 1.5ATR TP は、実測 WR 32.26% と摩擦負けに対して損益分岐を満たせず、MR が平均へ戻る前に切られる geometry になっている。

再設計案は、MACD-H 反転の「1本早い

## Redesign Recommendation 抜粋

> 思想は捨てない。コードからは「BB/RSI extreme の中で MACD-H の反転を他の MR より早く拾う」という thesis が直接読め、Axis 2 は成立している。ただし現行の `ALL` scope、current-bar timing 契約、1ATR/1.5ATR geometry の組み合わせは既存実測の低 WR・低 PF と整合せず、単一行削除では復活しない。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/macdh.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`MACDH_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_macdh_shadow_redesign_v2.py`

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
- BT report (`bt-results/macdh-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T02:34:49Z)

exit=0 · 2487s

```
実装完了です。

変更点:
- [strategies/scalp/macdh.py](/data/repo/fx-ai-trader/strategies/scalp/macdh.py:27)
  - `MACDH_REDESIGN_V2=1` 配下でのみ有効。
  - Tier1 extreme 専用化: `%B <= 0.15 / >= 0.85`, `RSI5 < 40 / > 60`
  - MR geometry 修正: `SL=1.5ATR`, `TP=2R = 3.0ATR`
  - default OFF なので live 既存挙動は維持。

- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:193)
  - shadow worker 登録を二重 flag 化。
  - `MACDH_REDESIGN_V2=1` かつ `MACDH_REDESIGN_V2_SHADOW_PROMOTE=1` の時だけ `macdh_reversal` を shadow emit 対象にします。

- [tests/test_macdh_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_macdh_shadow_redesign_v2.py:55)
  - default OFF 保持
  - v2 trigger tightening
  - v2 wide geometry
  - shadow promote worker double-flag registration

- [tools/macdh_shadow_bt.py](/data/repo/fx-ai-trader/tools/macdh_shadow_bt.py:1)
  - `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`
  - `app.run_daytrade_backtest(backtest_mode=True)` 使用
  - 365d / MASSIVE parquet / baseline vs proposed
  - v2 LOCK criteria 実装

BT report:
- [bt-results/macdh-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/macdh-shadow-redesign-v2-2026-05-05.json:1)
- Overall verdict: `INSUFFICIENT_BT_EVIDENCE`
- Proposed BT trades: `N=0`, so v2 spec 通り catastrophic check と sanity floor は skip
- Shadow recommendation: `RECOMMEND_SHADOW`

Verification:
- 先に MACDH test は赤を確認済み。
- `.venv/bin/python -m pytest -q tests/test_macdh_shadow_redesign_v2.py` → `4 passed`
- `.venv/bin/python -m pytest -q tests/test_macdh_shadow_redesign_v2.py tests/test_bb_rsi_shadow_redesign_v2.py tests/test_ema_trend_scalp_shadow_redesign_v2.py` → `12 passed`
- `.venv/bin/python -m py_compile tools/macdh_shadow_bt.py` → OK

Codex self-review:
- catastrophic check のみで判定: PASS
- Kelly/positive direction を要求していない: PASS
- live 影響は `MACDH_REDESIGN_V2` default OFF で zero: PASS
- shadow emit も別 flag 必須: PASS
- post-hoc adjustment なし: PASS

未追跡の既存別タスクらしい `tests/test_ma_trend_perfect_shadow_redesi
…(truncated)
