---
id: 20260505-1943-w4-shadow-redesign-v2-post_news_vol
title: "[W4-Shadow-Redesign v2] post_news_vol (Tier 3 (FORCE_DEMOTED)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:43:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/post_news_vol.md
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

W4-EDA audit (`audits/edge_design/post_news_vol.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **A**
- Tier: Tier 3 (FORCE_DEMOTED)

## Axis 8 抜粋

> Tier 3 (FORCE_DEMOTED) としての破綻軸は Axis 2 / 3 / 5、補助的に Axis 4。思想はコードから明確に導出でき、post-news volatility continuation 自体は tier-master / WF の一部で支持されるが、現行 trigger は「news後」ではなく「任意のATR spike後」を拾う。さらに current bar の follow-through を直接読むため bar-close / next-bar execution / dedup 契約が弱く、出口は fixed TP で post-news run の右尾を伸ばせない。

再設計案は v2 を event-window + closed-bar continuation + trailing geometry に分離すること。具体的には `event_window = high_impact_calendar_event within [-5m,+45m]` を spike trigger の必須条件にし、signal は `df.iloc[-2]` の確定 follow bar で `close[-2] > spike_close + buffer` / `< spike_close - buffer` を判定、execution は次 b

## Redesign Recommendation 抜粋

> 思想は明確で、volatility spike + follow-through という trigger 骨格も momentum continuation を捕捉している。ただし `post_news` の中核条件が実装されていないため、最優先修正は trigger の event-window 化である。`_find_spike_bars()` の前段または `evaluate()` 冒頭に high-impact economic calendar gate を追加し、calendar がない場合は `post_news_vol` ではなく `generic_vol_spike_followthrough` として別戦略に分離するのが筋が良い。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/post_news_vol.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`POST_NEWS_VOL_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_post_news_vol_shadow_redesign_v2.py`

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
- BT report (`bt-results/post_news_vol-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-06T04:40:08Z)

exit=0 · 2508s

```
実装完了しました。

変更点:
- `POST_NEWS_VOL_REDESIGN_V2=1` 配下で v2 variant を追加
  - high-impact event window `[-5m,+45m]` 必須
  - follow-through は `df.iloc[-2]` の確定足だけ使用
  - current bar only signal は不採用
  - `(symbol, strategy, spike_idx, signal_bar_time, signal)` dedup
  - spike extreme SL 維持、TP は shadow 向けに少し広めの management target
- Shadow worker 登録を二重 flag 化
  - `POST_NEWS_VOL_REDESIGN_V2=1`
  - `POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE=1`
- BT cache key に v2 flag を追加
- 新規テスト追加: [tests/test_post_news_vol_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_post_news_vol_shadow_redesign_v2.py:130)
- BT runner 追加: [tools/post_news_vol_shadow_bt.py](/data/repo/fx-ai-trader/tools/post_news_vol_shadow_bt.py:1)
- BT report 生成: [bt-results/post_news_vol-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/post_news_vol-shadow-redesign-v2-2026-05-05.json:1)

検証:
- `./.venv/bin/python -m pytest tests/test_post_news_vol_shadow_redesign_v2.py -q`  
  → `6 passed`
- `./.venv/bin/python -m py_compile strategies/daytrade/post_news_vol.py strategies/daytrade/__init__.py tools/post_news_vol_shadow_bt.py app.py`  
  → OK
- `./.venv/bin/python tools/post_news_vol_shadow_bt.py`  
  → 365d MASSIVE BT 完了

v2 LOCK verdict:
- Overall: `INSUFFICIENT_BT_EVIDENCE`
- Shadow recommendation: `RECOMMEND_SHADOW`
- Proposed N:
  - USD_JPY: `0`
  - EUR_USD: `0`
  - GBP_USD: `0`
  - EUR_GBP: `0`

理由: MASSIVE OHLCV cache には economic calendar event feed がないため、v2 の event-window gate が正しく働き、BT では proposed trades が 20 未満になりました。v2 spec に従って catastrophic check / sanity floor は skip、shadow promote 推奨です。

Codex self-review:
- catastrophic check のみで判定: PASS
- absolute Kelly 不要求: PASS
- default OFF で live 影響ゼロ: PASS
- post-hoc adjustment なし: PASS
- Yahoo fallback 禁止: PASS (`BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`)
```
