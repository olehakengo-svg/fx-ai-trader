---
strategy: vsg_jpy_reversal
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

EWMA forecast に対する直近確定足の realized volatility surprise が極端に大きいとき、EUR_JPY/GBP_JPY は panic / carry unwind 的な overshoot 後に fade 方向へ平均回帰する、という MR thesis。コード上も `strategy_type = "MR"`、JPY cross 限定、`direction = -sign(realized_ret)` が明示されている。`strategies/daytrade/vsg_jpy_reversal.py:4` `strategies/daytrade/vsg_jpy_reversal.py:7` `strategies/daytrade/vsg_jpy_reversal.py:49` `strategies/daytrade/vsg_jpy_reversal.py:51` `strategies/daytrade/vsg_jpy_reversal.py:97`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `surprise = (abs(ret_t) - EWMA_forecast_{t-1}) / EWMA_forecast_{t-1}` かつ `surprise > 1.5`、direction は `SELL if ret_t > 0 else BUY`。vol extension を検出して逆方向に入るため MR thesis と数学的に整合する。`strategies/daytrade/vsg_jpy_reversal.py:84` `strategies/daytrade/vsg_jpy_reversal.py:86` `strategies/daytrade/vsg_jpy_reversal.py:87` `strategies/daytrade/vsg_jpy_reversal.py:88` `strategies/daytrade/vsg_jpy_reversal.py:92` `strategies/daytrade/vsg_jpy_reversal.py:94` `strategies/daytrade/vsg_jpy_reversal.py:101` |
| 3 (timing window) | OK | BT は `iloc[-1]` を評価中の closed bar、Live は in-progress bar を避けて `iloc[-2]` を closed bar として評価する。forecast はそれぞれ 1 本前を使うため realized bar 自身の情報を forecast に混ぜない。per-bar dedup も `(symbol, direction)` 単位で同一 closed bar の多重 emit を止める。`strategies/daytrade/vsg_jpy_reversal.py:76` `strategies/daytrade/vsg_jpy_reversal.py:79` `strategies/daytrade/vsg_jpy_reversal.py:82` `strategies/daytrade/vsg_jpy_reversal.py:103` `strategies/daytrade/vsg_jpy_reversal.py:107` `strategies/daytrade/vsg_jpy_reversal.py:111` `strategies/daytrade/vsg_jpy_reversal.py:142` |
| 4 (filter coherence) | STRENGTHENS | Pair filter は Bonferroni 通過の EURJPY/GBPJPY のみに限定し、USDJPY など弱い cell を排除するため thesis を強化する。MA filter / HMM regime gate は存在せず、MR を trend alignment で壊す先行失敗例には該当しない。最小データ長、forecast epsilon、dedup は実装安全性フィルタで thesis 破壊ではない。`strategies/daytrade/vsg_jpy_reversal.py:51` `strategies/daytrade/vsg_jpy_reversal.py:52` `strategies/daytrade/vsg_jpy_reversal.py:71` `strategies/daytrade/vsg_jpy_reversal.py:73` `strategies/daytrade/vsg_jpy_reversal.py:90` `strategies/daytrade/vsg_jpy_reversal.py:111` |
| 5 (stop/TP geometry) | MISALIGNED | MR なのに SL=1.0 ATR、TP=1.5 ATR、MIN_RR=1.4 で、mean への短い戻りを取りに行くよりも遠い TP を要求する asymmetry になっている。R:R は約 1.5 だが、MR の「戻る前に狭い stop で切らない」幾何とは逆寄り。`strategies/daytrade/vsg_jpy_reversal.py:57` `strategies/daytrade/vsg_jpy_reversal.py:58` `strategies/daytrade/vsg_jpy_reversal.py:59` `strategies/daytrade/vsg_jpy_reversal.py:115` `strategies/daytrade/vsg_jpy_reversal.py:120` `strategies/daytrade/vsg_jpy_reversal.py:123` `strategies/daytrade/vsg_jpy_reversal.py:129` `strategies/daytrade/vsg_jpy_reversal.py:130` |
| 6 (pair-regime fit) | FIT | EUR_JPY=FIT、GBP_JPY=FIT。USD_JPY=FORCED/blocked by design、EUR_USD=FORCED/blocked、GBP_USD=FORCED/blocked。コードは JPY cross のうち audit 通過 pair だけを許可し、それ以外は即 `None`。`strategies/daytrade/vsg_jpy_reversal.py:51` `strategies/daytrade/vsg_jpy_reversal.py:52` `strategies/daytrade/vsg_jpy_reversal.py:71` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | vsg_audit には Wilson / Bonferroni の event-level evidence があるが、tier-master 365d BT EV は `—`、audit DB / production DB では `vsg_jpy_reversal` の logged trade が 0 件。PF / WF folds / Kelly は既存成果物から確認不能。数値は下表。 |

## Axis 8: failure mode 診断

Tier 2 Shadow なので Tier 3/4 必須診断対象ではないが、現状の失敗モードは Axis 5 と Axis 7。Axis 2/3/4 は設計としては通っており、思想自体はコードと vsg_audit の Bonferroni evidence で支持される。一方、実装された trade geometry は MR に対して TP が遠く stop が狭い。また production routing audit では BT fires 331 に対して DB total 0 / Live 0 と記録されており、実弾・Shadow の PF/Kelly を評価できない。

再設計案は、trigger は維持しつつ exit を MR 用に変更すること。具体的には `SL_ATR_MULT` を 1.5-2.0、`TP_ATR_MULT` を 0.8-1.0、`MIN_RR` を MR 用に撤廃または 0.5-0.7 へ下げ、最大 2-4 bars の time exit で audit の forward-window evidence と対応させる。追加で pair 別に EUR_JPY は `threshold=1.5, hold=2`、GBP_JPY は `threshold=1.0, hold=4` を候補にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想と trigger/timing/filter は成立しているため、復活候補としては高い。主修正は stop/TP geometry の 1 系統でよい。MR としては「大きな surprise 後の短い戻り」を取りに行くべきなので、TP を近く、SL を広く、time exit を明示する設計に寄せる。

コードレベルでは `strategies/daytrade/vsg_jpy_reversal.py:57`-`strategies/daytrade/vsg_jpy_reversal.py:59` の定数を MR 用に再設定し、`strategies/daytrade/vsg_jpy_reversal.py:129`-`strategies/daytrade/vsg_jpy_reversal.py:130` の `MIN_RR` gate を削除または MR-specific gate に置換する。GBP_JPY は既存 vsg_audit で `threshold=1.0, forward_bars=4` が Bonferroni 通過しているため、`SURPRISE_THRESHOLD` を pair 別 dict にする案も併せて検証対象。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB logged trades: 0; G1 BT firing diagnostic: 331 total signals (EUR_JPY 145, GBP_JPY 186) | audit DB `demo_trades.db`; `raw/audits/never_logged_diagnosis_2026-04-28.md`; `raw/audits/production_routing_audit_2026-04-28.md` |
| Win rate | EUR_JPY th=1.5 fw=2 reversal: 58.08%; EUR_JPY th=1.5 fw=4 reversal: 55.57%; GBP_JPY th=1.0 fw=4 reversal: 55.59%; implemented GBP_JPY th=1.5 fw=4 proxy: 54.32% | `raw/vsg_audit/vsg_audit_20260427_1201.json` |
| Wilson lo (95%) | EUR_JPY th=1.5 fw=2: 54.44%; EUR_JPY th=1.5 fw=4: 51.92%; GBP_JPY th=1.0 fw=4: 53.02%; implemented GBP_JPY th=1.5 fw=4 proxy: 50.66% | `raw/vsg_audit/vsg_audit_20260427_1201.json` |
| PF | INSUFFICIENT_EVIDENCE: vsg_audit grid has WR/Wilson/avg_pip/Sharpe/p but no gross win/loss distribution; audit DB logged trades are 0 | audit DB; `raw/vsg_audit/vsg_audit_20260427_1201.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no WF fold result found in tier-master or vsg_audit | tier-master; `raw/vsg_audit/vsg_audit_20260427_1201.json` |
| Bonferroni-adj p | EUR_JPY th=1.5 fw=2: 0.00081; EUR_JPY th=1.5 fw=4: 0.14256; GBP_JPY th=1.0 fw=4: 0.00108; implemented GBP_JPY th=1.5 fw=4 proxy: 1.02375 | `raw/vsg_audit/vsg_audit_20260427_1201.json` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: no PF / avg win / avg loss / realized trade distribution available for this strategy; audit DB logged trades are 0 | audit DB; tier-master |
