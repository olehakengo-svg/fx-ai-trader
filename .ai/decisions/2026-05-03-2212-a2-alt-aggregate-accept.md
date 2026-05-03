---
date: 2026-05-03T22:12:00+0900
verdict: ACCEPT
rule: R1
roadmap_gate: Gate 1 (Scalp 枝 N-acceleration)
task: 20260503-1700-a2-alt-simple-structure-scalp-pre-reg
supersedes:
  - 2026-05-03-1804-a2-alt-codex-needs-more-evidence.md
  - 2026-05-03-1840-a2-alt-needs-more-evidence-wrapper-bug-fixed.md
wrapper_fingerprint: b6d7386b5c48789871894a76b07f61c3a741fba176353e90e9250014a9533e02
artifacts:
  aggregate_md: knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.md
  aggregate_json: knowledge-base/raw/bt-results/scalp-alt-180d-2026-05-03.json
  prereg_md: knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md
  candidate_jsons:
    - knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json
    - knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json
    - knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json
    - knowledge-base/raw/bt-results/scalp-alt-sr-2026-05-03.json
---

# 判定: ACCEPT — A2-alt simple-structure Scalp pre-registration 完了

## Summary

LOCKED pre-reg (Bonferroni K=4, alpha/K=0.0125) で 4 候補 BT を完走、aggregate verdict は次の通り:

| Strategy | Pair × TF | Verdict | N | WR | EV | PF | Bonferroni p | Max DD% | WF IS/OOS PF |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| **sr_channel_reversal** | EUR_USD 5m | **Promote** ✓ | 52 | 61.5% | +0.373 | 2.72 | 0.00418 | 14.8 | 2.557 / 2.889 |
| fib_reversal | EUR_USD 1m | Reject | 101 | 59.4% | +0.388 | 3.15 | 0.00016 | **220.96** | 2.157 / 4.956 |
| engulfing_bb | USD_JPY 5m | Reject | 30 | 53.3% | +0.212 | 1.56 | 0.093 | 188.21 | 1.162 / 1.948 |
| bb_squeeze_breakout | USD_JPY 5m | Insufficient | 24 | 75.0% | +0.913 | 4.87 | 0.00023 | 26.7 | 2.442 / inf |

Promote cap = 1 (decision policy 上限) → 候補 = `sr_channel_reversal × EUR_USD 5m`.

## sr_channel_reversal × EUR_USD 5m が pass した 6 ゲート

| Gate | 閾値 | 実測 | Pass |
|---|---|---|:-:|
| N | ≥30 | 52 | ✓ |
| PF | ≥1.30 | 2.724 | ✓ |
| Wilson_lo > BEV_WR + 5pp | >44.7% (BEV=39.7) | 47.96% | ✓ (+8.26pp) |
| WF PF_IS | ≥1.20 | 2.557 | ✓ |
| WF PF_OOS | ≥1.20 | 2.889 | ✓ |
| Bonferroni p | <0.0125 | 0.00418 | ✓ |
| Max DD | ≤30% | 14.84% | ✓ |

OVERFIT_SUSPECTED フラグ無し (OOS PF / IS PF = 1.13、+13% むしろ improving)。half-Kelly = 0.1947。

## fib_reversal: 統計は強いが DD で落ちた

N=101, EV=+0.388, PF=3.15, Bonferroni p=0.00016 と数値は極めて強い。しかし `max_drawdown_pct=220.96%` が 30% gate を完全に違反 → Reject。これは「平均的には勝つが drawdown が致命的」のパターンで、Live で乗せると Recovery Path 不能。R1 Slow & Strict が正しく機能した例。

## engulfing_bb / bb_squeeze: 構造的不採用

- engulfing_bb: WR=53.3% → Wilson_lo=36.1% で BEV=34.4 をギリ越えるが Bonferroni p=0.093 で有意性無し、Max DD=188% で構造破綻
- bb_squeeze: WR=75% / PF=4.87 / Bonferroni p=0.00023 と極めて優秀だが N=24<30 で「決定する根拠不足」(Insufficient)。次回 BT で N≥30 達成すれば再評価対象

## R3 wrapper bug 修正経緯（同日 18:40 → 22:12）

1. 18:40 時点で R3 (wrapper bug): `load_local_bt_frame` が parquet の lowercase columns を `add_indicators` に渡し全 BT が KeyError 失敗
2. column rename 1 行で fix → 3 候補 (bb_squeeze / sr / engulfing) が完走
3. fib_reversal × EUR_USD 1m が `interval="1m"` で `_5M_ONLY_TYPES` 入りのため `app.fetch_ohlcv` を別途呼び、OANDA DNS 失敗で 4 回連続 stuck
4. R3 fix 2: `load_app_runtime` で `app.fetch_ohlcv` を local-cache monkeypatch (capitalized columns rename 含む)
5. 結果として fib も完走、verdict=Reject (Max DD)

両 R3 fix は infra (data loading) のみで PnL/LOCKED/CANDIDATES に無影響、wrapper fingerprint `b6d7386b5c48789871894a76b07f61c3a741fba176353e90e9250014a9533e02` は不変。R3 fingerprint design の正当性が再度実例で確認された。

## Roadmap impact

Gate 1 (Scalp 枝 N-acceleration) で 1 つの clean Promote 確保。次は A3-simple で `sr_channel_reversal × EUR_USD 5m` を OANDA bridge に Shadow 登録 → Live N 蓄積。half-Kelly=0.1947 だが初期 lot は Recovery Path lot で開始 (Live N≥30 まで)。

## 次のロードマップ task

**A3-simple — register sr_channel_reversal × EUR_USD 5m to OANDA bridge with monitoring (Gate 1 Live promotion)**

- Lot 設計: 初期 Recovery Path lot, half-Kelly に向かって段階的拡大は Live N≥30 + WR維持時のみ
- 監視: Sentinel R2 demotion (累積 PnL ≤ -10pip / Kelly_observed ≤ 0 / 占有率 ≥ 50%) を発動条件に組み込む
- Pair scope: EUR_USD のみ (BT は EUR_USD でしか pre-reg されていない)。他ペアへの拡張は別 R1 サイクル必要
