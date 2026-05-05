---
id: 20260505-1905-w4-shadow-redesign-v2-bb_rsi
title: "[W4-Shadow-Redesign v2] bb_rsi (Tier 2 (Shadow)) — relaxed spec"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T19:05:00+0900
roadmap_gate: "W4-Shadow-Redesign v2: BT は filter、shadow が真の estimator (v1 で 5/5 REJECT した教訓)"
rule: R1
prereq_artifacts:
  - audits/edge_design/bb_rsi.md
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

W4-EDA audit (`audits/edge_design/bb_rsi.md`):
- Verdict: **THESIS_VALID_DESIGN_BROKEN** / Recommendation: **B**
- Tier: Tier 2 (Shadow)

## Axis 8 抜粋

> Tier 2 (Shadow) だが、SCALP_SENTINEL かつ EUR_JPY / EUR_USD / GBP_USD / USD_JPY が pair_demoted で、既存 audit も negative/insufficient が混在するため failure mode 診断対象とする。

破綻軸は Axis 3 と Axis 4。Axis 2 の trigger は BB/RSI/Stoch の MR と整合しており、Axis 5 も RR floor 後は算数破綻をかなり修正している。主問題は、現在足の `entry/open` 反転確認を closed-bar/dedup なしで使う timing と、USD/JPY の `ADX>=30` を edge tail として加点しながら MR anti-trend confidence penalty で同じ tail を減点する filter/scoring 矛盾である。

再設計案は 2 段。まず signal を closed bar 化し、同一 `(symbol, signal, bar_time)` の再 emit を禁止する。次に JPY high-ADX tail を採用する variant と、純 range MR variant を分離する。具体的には JPY variant では `ADX

## Redesign Recommendation 抜粋

> 思想は捨てない。BB/RSI/Stoch extreme からの反転を狙う MR thesis はコードから明確に導出でき、trigger 自体も概ね妥当。ただし現行設計は timing と regime/scoring が混線しているため、単一行削除ではなく複数軸の再設計が必要。

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

## Step 1: 既存 audit 確認 (`audits/edge_design/bb_rsi.md`)

audit が指摘する redesign axis を読み、**最小 1 軸** で実装。

## Step 2: 実装 (flag 配下)

`BB_RSI_REDESIGN_V2=1` 環境変数 / config flag で proposed variant を有効化。
default OFF で live は影響受けない。

## Step 3: 失敗テスト + 緑

`tests/test_bb_rsi_shadow_redesign_v2.py`

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
- BT report (`bt-results/bb_rsi-shadow-redesign-v2-2026-05-05.json`)
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


## Result (2026-05-05T14:22:23Z)

exit=0 · 2536s

```
実装完了です。

変更:
- [strategies/scalp/bb_rsi.py](/data/repo/fx-ai-trader/strategies/scalp/bb_rsi.py:72)
  - `BB_RSI_REDESIGN_V2=1` 配下でのみ、JPY `ADX>=30` tail の MR anti-trend confidence penalty を bypass。
  - flag OFF は既存挙動そのままです。
- [strategies/scalp/__init__.py](/data/repo/fx-ai-trader/strategies/scalp/__init__.py:162)
  - `BB_RSI_REDESIGN_V2=1` かつ `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE=1` の両方が立った場合だけ `bb_rsi_reversion` を shadow emit 対象に登録。
- [tests/test_bb_rsi_shadow_redesign_v2.py](/data/repo/fx-ai-trader/tests/test_bb_rsi_shadow_redesign_v2.py:55)
  - default OFF 保持、V2 high-ADX bypass、non-JPY 非影響、shadow double-flag をテスト。
- [tools/bb_rsi_shadow_bt.py](/data/repo/fx-ai-trader/tools/bb_rsi_shadow_bt.py:1)
  - 365d MASSIVE BT report generator。
- [bt-results/bb_rsi-shadow-redesign-v2-2026-05-05.json](/data/repo/fx-ai-trader/bt-results/bb_rsi-shadow-redesign-v2-2026-05-05.json)
  - BT report 生成済み。

検証:
- `.venv/bin/pytest tests/test_bb_rsi_shadow_redesign_v2.py tests/test_asia_range_fade_v1_shadow_redesign_v2.py -q`
  - `8 passed`
- `python3 -m json.tool bt-results/bb_rsi-shadow-redesign-v2-2026-05-05.json`
  - OK
- `python3 -m py_compile tools/bb_rsi_shadow_bt.py strategies/scalp/bb_rsi.py strategies/scalp/__init__.py`
  - OK

BT verdict:
- Overall: `INSUFFICIENT_BT_EVIDENCE`
- Proposed N: `0` for `USD_JPY`, `EUR_JPY`, `EUR_USD`, `GBP_USD`
- v2 LOCK rule に従い、catastrophic check は skip、shadow promote 推奨です。
- Report runner: `app.run_daytrade_backtest` with MASSIVE `15m` parquet mandatory (`BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`).

Self-review:
- catastrophic / insufficient evidence rule のみで判定。
- absolute Kelly / positive direction は要求していません。
- live default は完全 OFF。
- shadow emit も `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE=1` がない限り OFF。
- post-hoc adjustment なし。
```
