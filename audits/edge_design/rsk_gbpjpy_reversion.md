---
strategy: rsk_gbpjpy_reversion
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

Rolling realized skewness の z-score が極端値に達した後、skew の符号と逆方向へ張り、downside/upside skew の exhaustion から 6 bar 程度の短期平均回帰を取る。対象は intraday skewness signal が鋭い GBPJPY に限定する。`strategies/daytrade/rsk_gbpjpy_reversion.py:2`, `strategies/daytrade/rsk_gbpjpy_reversion.py:5`, `strategies/daytrade/rsk_gbpjpy_reversion.py:6`, `strategies/daytrade/rsk_gbpjpy_reversion.py:7`, `strategies/daytrade/rsk_gbpjpy_reversion.py:14`, `strategies/daytrade/rsk_gbpjpy_reversion.py:15`, `strategies/daytrade/rsk_gbpjpy_reversion.py:16`, `strategies/daytrade/rsk_gbpjpy_reversion.py:17`, `strategies/daytrade/rsk_gbpjpy_reversion.py:19`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `skew = E[(r - mean(r))^3] / std(r)^3`、`skew_z = (skew - rolling_mean(skew)) / rolling_std(skew)`、`abs(latest_z) >= 2.0`、`latest_z < 0 -> BUY` / `latest_z > 0 -> SELL`。MR thesis に必要な extension/extreme proxy が realized skewness z-score として明示され、方向も `-sign(z)` になっている。`strategies/daytrade/rsk_gbpjpy_reversion.py:48`, `strategies/daytrade/rsk_gbpjpy_reversion.py:49`, `strategies/daytrade/rsk_gbpjpy_reversion.py:50`, `strategies/daytrade/rsk_gbpjpy_reversion.py:77`, `strategies/daytrade/rsk_gbpjpy_reversion.py:78`, `strategies/daytrade/rsk_gbpjpy_reversion.py:80`, `strategies/daytrade/rsk_gbpjpy_reversion.py:81`, `strategies/daytrade/rsk_gbpjpy_reversion.py:83`, `strategies/daytrade/rsk_gbpjpy_reversion.py:86`, `strategies/daytrade/rsk_gbpjpy_reversion.py:88`, `strategies/daytrade/rsk_gbpjpy_reversion.py:90`, `strategies/daytrade/rsk_gbpjpy_reversion.py:94`, `strategies/daytrade/rsk_gbpjpy_reversion.py:98` |
| 3 (timing window) | OK | Signal は BT では closed bar `iloc[-1]`、live では in-progress bar を避けて closed bar `iloc[-2]` を評価する設計。さらに closed bar timestamp と `(symbol, direction)` の per-bar dedup があり、同一 closed bar の 30s polling 多重 entry をブロックしている。bar-close 化と dedup は明示されており、現コード上の look-ahead / same-bar runaway は修正済み。`strategies/daytrade/rsk_gbpjpy_reversion.py:21`, `strategies/daytrade/rsk_gbpjpy_reversion.py:22`, `strategies/daytrade/rsk_gbpjpy_reversion.py:23`, `strategies/daytrade/rsk_gbpjpy_reversion.py:24`, `strategies/daytrade/rsk_gbpjpy_reversion.py:59`, `strategies/daytrade/rsk_gbpjpy_reversion.py:60`, `strategies/daytrade/rsk_gbpjpy_reversion.py:61`, `strategies/daytrade/rsk_gbpjpy_reversion.py:71`, `strategies/daytrade/rsk_gbpjpy_reversion.py:72`, `strategies/daytrade/rsk_gbpjpy_reversion.py:73`, `strategies/daytrade/rsk_gbpjpy_reversion.py:74`, `strategies/daytrade/rsk_gbpjpy_reversion.py:110`, `strategies/daytrade/rsk_gbpjpy_reversion.py:114`, `strategies/daytrade/rsk_gbpjpy_reversion.py:118`, `strategies/daytrade/rsk_gbpjpy_reversion.py:147`, `strategies/daytrade/rsk_gbpjpy_reversion.py:149` |
| 4 (filter coherence) | STRENGTHENS | `GBPJPY` only gate は、コード内の「Bonferroni-significant 唯一の pair」という根拠と一致し STRENGTHENS。履歴長・finite z・`sl_dist > 0` は NEUTRAL。closed-bar candle direction confirmation は、negative skew BUY なら陽線確認、positive skew SELL なら陰線確認で、exhaustion 後に反転が始まった bar だけを通すため STRENGTHENS。ただし確認待ちで entry が遅れる可能性は Axis 3/8 の redesign 候補。MA filter on MR や HMM regime gate same trap と同型の trend/regime hard block は無い。`strategies/daytrade/rsk_gbpjpy_reversion.py:10`, `strategies/daytrade/rsk_gbpjpy_reversion.py:11`, `strategies/daytrade/rsk_gbpjpy_reversion.py:46`, `strategies/daytrade/rsk_gbpjpy_reversion.py:66`, `strategies/daytrade/rsk_gbpjpy_reversion.py:68`, `strategies/daytrade/rsk_gbpjpy_reversion.py:91`, `strategies/daytrade/rsk_gbpjpy_reversion.py:100`, `strategies/daytrade/rsk_gbpjpy_reversion.py:103`, `strategies/daytrade/rsk_gbpjpy_reversion.py:104`, `strategies/daytrade/rsk_gbpjpy_reversion.py:105`, `strategies/daytrade/rsk_gbpjpy_reversion.py:107`, `strategies/daytrade/rsk_gbpjpy_reversion.py:133` |
| 5 (stop/TP geometry) | MISALIGNED | 現 geometry は `SL = 1.0ATR`、`TP = 1.5ATR`、`MIN_RR = 1.4`、`hold <= 6 bars`。MR thesis なら自然 target は skew/price の mean 回帰完了点で、stop は mean 到達前の GBPJPY noise を許容する必要があるが、現設計は mean target を測らず、TP を stop より遠くに固定する momentum 型の非対称 R:R になっている。`shift_tp_inside` 後も `rr >= 1.4` を要求するため、短期 MR の自然な小幅回帰を捨てやすい。`strategies/daytrade/rsk_gbpjpy_reversion.py:18`, `strategies/daytrade/rsk_gbpjpy_reversion.py:19`, `strategies/daytrade/rsk_gbpjpy_reversion.py:52`, `strategies/daytrade/rsk_gbpjpy_reversion.py:53`, `strategies/daytrade/rsk_gbpjpy_reversion.py:54`, `strategies/daytrade/rsk_gbpjpy_reversion.py:55`, `strategies/daytrade/rsk_gbpjpy_reversion.py:121`, `strategies/daytrade/rsk_gbpjpy_reversion.py:123`, `strategies/daytrade/rsk_gbpjpy_reversion.py:124`, `strategies/daytrade/rsk_gbpjpy_reversion.py:126`, `strategies/daytrade/rsk_gbpjpy_reversion.py:127`, `strategies/daytrade/rsk_gbpjpy_reversion.py:129`, `strategies/daytrade/rsk_gbpjpy_reversion.py:135`, `strategies/daytrade/rsk_gbpjpy_reversion.py:136`, `strategies/daytrade/rsk_gbpjpy_reversion.py:144` |
| 6 (pair-regime fit) | FIT | `pairs: ALL` dispatch でも strategy 本体は GBPJPY 以外を即 `None` にする。raw `rsk_audit_20260427_1306.json` では target combo `GBP_JPY sw=30 th=2.0 fw=6` が Bonferroni significant で、significant combos も GBPJPY に集中しているため、実装対象 pair は thesis と合う。per-pair: `GBPJPY=FIT`; `USDJPY/EURUSD/GBPUSD/EURJPY/EURGBP=not traded by code, not forced`。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | raw rsk audit には target combo の `N=1915`, `WR=54.67%`, `Wilson lo=52.44%`, `p_bonf=0.00310`, `avg_pip=1.96`, `Sharpe=12.18` がある。一方、tier-master の 365d BT EV は `—`、既存 SQLite は `chart_pattern_outcomes` のみで strategy 列がなく、PF / WF folds / empirical Kelly fraction は既存 audit DB / tier-master から復元できない。`feedback_partial_quant_trap.md` 準拠では N/WR/EV と部分指標だけで decision-grade としない。下表参照。 |

## Axis 8: failure mode 診断

`rsk_gbpjpy_reversion` は Tier 2 (Shadow) / phase0_shadow。破綻軸は Axis 5。Axis 2 の realized skewness extreme fade は thesis と一致し、Axis 3 の bar-close/dedup 問題も現コードでは修正済み。Axis 4 も MR を壊す MA/HMM 型 filter ではなく、GBPJPY 限定と反転確認で概ね thesis を補強している。

再設計案は stop/TP geometry の単独修正を第一候補にする。現行の `TP_ATR_MULT = 1.5`, `SL_ATR_MULT = 1.0`, `MIN_RR = 1.4` を前提にした「遠い TP / 近い SL」ではなく、MR 用に `TP = entry ± k * ATR` を縮めるか、skew_z の mean reversion 完了を proxy する target（例: `abs(skew_z)` が低下するまでの time exit / half-ATR target）へ変える。GBPJPY noise を許容するため stop は 1.5-2.0ATR 側へ広げ、`MAX_HOLD_BARS = 6` の time stop を主 exit に近づける variant を pre-register して比較すべき。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

Trigger と pair gate は維持する。`abs(latest_z) >= 2.0` と `signal = -sign(skew_z)` は、realized skewness exhaustion を fade する thesis を直接表しており、ここを大きく変える理由はコード・既存 rsk audit の範囲では薄い。

優先修正は stop/TP geometry。コードレベルでは、第一 variant として `SL_ATR_MULT` を `1.5` 以上、`TP_ATR_MULT` を `0.7-1.0` 程度へ寄せ、`MIN_RR` を削除または MR 用の cost-adjusted minimum distance gate に置換する。第二 variant として固定 TP をやめ、`MAX_HOLD_BARS=6` 内で skew_z の absolute value が閾値未満へ戻る、または price が signal bar の midpoint/短期 VWAP へ戻る、という mean target を使う。新規 BT が必要なため、この監査では実装変更せず、PF / WF folds / empirical Kelly 付きの redesign BT を必要 evidence として明記する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 1915 | `raw/rsk_audit/rsk_audit_20260427_1306.json` target combo `GBP_JPY sw=30 th=2.0 fw=6` |
| Win rate | 54.67% | `raw/rsk_audit/rsk_audit_20260427_1306.json` |
| Wilson lo (95%) | 52.44% | `raw/rsk_audit/rsk_audit_20260427_1306.json` |
| PF | INSUFFICIENT_EVIDENCE: tier-master / raw rsk audit / existing SQLite に gross profit-loss または PF 欄なし | `knowledge-base/wiki/tier-master.md`; `raw/rsk_audit/rsk_audit_20260427_1306.json`; `knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: walk-forward fold 記録なし | tier-master / audit DB search |
| Bonferroni-adj p | 0.00310 | `raw/rsk_audit/rsk_audit_20260427_1306.json` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: empirical payoff distribution / PF / avg win-loss が無く、nominal RR からの推定は decision-grade evidence ではない | tier-master / audit DB search |
