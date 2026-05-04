---
strategy: orb_trap
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

セッション開始直後の Opening Range breakout が失敗して実体 Close がレンジ内へ戻った瞬間を、流動性遷移による false breakout / overreaction とみなし、breakout と逆方向へ fade して OR 反対端への回帰を取る MR thesis。これは OR 定義、break 検出、fresh return、逆方向 entry、OR 反対端 TP から直接導出できる（`strategies/daytrade/orb_trap.py:15`, `strategies/daytrade/orb_trap.py:19`, `strategies/daytrade/orb_trap.py:23`, `strategies/daytrade/orb_trap.py:27`, `strategies/daytrade/orb_trap.py:31`）。

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `current_close in [OR_low, OR_high]` かつ `prev_close outside [OR_low, OR_high]` の fresh return を要求し、`prev_close > OR_high -> SELL` / `prev_close < OR_low -> BUY` と breakout の逆方向へ entry する。式は `(_rl <= ctx.entry <= _rh) ∧ !( _rl <= ctx.prev_close <= _rh ) ∧ direction(prev_close)` で、false breakout fade thesis と整合する（`strategies/daytrade/orb_trap.py:237`, `strategies/daytrade/orb_trap.py:238`, `strategies/daytrade/orb_trap.py:241`, `strategies/daytrade/orb_trap.py:242`, `strategies/daytrade/orb_trap.py:246`, `strategies/daytrade/orb_trap.py:248`, `strategies/daytrade/orb_trap.py:286`, `strategies/daytrade/orb_trap.py:298`）。 |
| 3 (timing window) | OK | Signal は現在足 Close が OR 内へ戻った後、前足 Close が OR 外だったことを確認して生成されるため、bar-close confirmation 型であり、`_scan_breaks()` も `j=1` から過去 bar だけを走査して現在足の future 情報を使わない。Fresh return 条件により連続 bar の再発火は抑えられる。ただし strategy 内に `(session, date, direction)` の明示 dedup state はないため、engine が同一 closed bar を複数回 evaluate する運用なら外側 dedup に依存する（`strategies/daytrade/orb_trap.py:128`, `strategies/daytrade/orb_trap.py:129`, `strategies/daytrade/orb_trap.py:153`, `strategies/daytrade/orb_trap.py:237`, `strategies/daytrade/orb_trap.py:241`, `strategies/daytrade/orb_trap.py:366`）。 |
| 4 (filter coherence) | STRENGTHENS | Pair gate は実装対象を EURUSD/USDJPY/GBPUSD に限定し、ALL 入力に対する無差別発火は避ける（`strategies/daytrade/orb_trap.py:155`, `strategies/daytrade/orb_trap.py:156`）。仲値 filter は USDJPY LDN の OR 汚染を落とすため thesis を補強する（`strategies/daytrade/orb_trap.py:195`, `strategies/daytrade/orb_trap.py:208`, `strategies/daytrade/orb_trap.py:209`）。OR range quality、両方向 break 除外、最低 breakout 超過、HTF agreement veto は、noise range / whipsaw / 本物 breakout を落とす目的で coherent。MA filter on MR や HMM gate same-trap の先行例と異なり、EMA/ADX は entry veto ではなく score bonus に留まるため BREAKS とは判定しない（`strategies/daytrade/orb_trap.py:226`, `strategies/daytrade/orb_trap.py:228`, `strategies/daytrade/orb_trap.py:257`, `strategies/daytrade/orb_trap.py:267`, `strategies/daytrade/orb_trap.py:288`, `strategies/daytrade/orb_trap.py:300`, `strategies/daytrade/orb_trap.py:354`, `strategies/daytrade/orb_trap.py:360`）。 |
| 5 (stop/TP geometry) | MISALIGNED | 初期 geometry は SELL `SL = break_extreme + 0.3ATR`, `TP = OR_low`、BUY `SL = break_extreme - 0.3ATR`, `TP = OR_high` で false breakout fade と整合する（`strategies/daytrade/orb_trap.py:31`, `strategies/daytrade/orb_trap.py:67`, `strategies/daytrade/orb_trap.py:291`, `strategies/daytrade/orb_trap.py:292`, `strategies/daytrade/orb_trap.py:303`, `strategies/daytrade/orb_trap.py:304`）。しかし RR 不足時に `TP = entry +/- sl_distance * 1.3` へ補正し、OR 反対端を越えた利確を強制しうるため、MR thesis の「レンジ内回帰を取る」出口が、回帰後の追加 continuation 期待へ変質する（`strategies/daytrade/orb_trap.py:68`, `strategies/daytrade/orb_trap.py:323`, `strategies/daytrade/orb_trap.py:324`, `strategies/daytrade/orb_trap.py:325`, `strategies/daytrade/orb_trap.py:326`）。 |
| 6 (pair-regime fit) | FORCED | コードは EURUSD/USDJPY/GBPUSD のみ通すが、tier-master は ALL force_demoted、365d scan は JPY=-0.854 / EUR=-0.488 / GBP=-0.258 で全対象 pair が負EV。下表参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | audit DB strategy aggregate は N=5, WR=80.00%, Wilson lo=37.55%, PF=5.862, Kelly=0.6635, Bonferroni p=1.0000 で、小標本かつ多重検定後に有意でない。tier-master 365d EV は `—`、旧 365d scan は全対象 pair 負EV、WF は pair ごとに unstable / borderline / folds 不足で、`feedback_partial_quant_trap.md` 基準の Wilson/PF/WF folds>=3/Bonferroni/Kelly を同時に満たさない。 |

### Axis 6 Pair-Regime Fit Detail

| Pair | Fit | Basis |
|---|---|---|
| USD_JPY | FORCED | コード上は許可され、仲値 filter もあるが、365d scan は JPY EV=-0.854、W90/W60/W7/W20 系 WF は folds 不足。 |
| EUR_USD | FORCED | コード上は許可されるが、365d scan は EUR EV=-0.488、W60/W90 は folds>=3 でも unstable。 |
| GBP_USD | FORCED | コード上は許可されるが、365d scan は GBP EV=-0.258、W90 は borderline、W60 は unstable。 |
| Other ALL pairs | FORCED | `evaluate()` は EURUSD/USDJPY/GBPUSD 以外を即 return するため、ALL cell としての pair-regime fit は存在しない（`strategies/daytrade/orb_trap.py:155`, `strategies/daytrade/orb_trap.py:156`, `strategies/daytrade/orb_trap.py:157`）。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) の failure mode は Axis 5 主体、補助的に Axis 6/7。Axis 2 の trigger は false breakout fade を捕捉しており、Axis 3 も bar-close confirmation として大きな破綻はない。Axis 4 の filters も entry universe を不自然に潰す MA/HMM 型の破壊ではなく、noise / whipsaw / true breakout 除外として概ね coherent。

破綻は exit geometry にある。コードは thesis 上の自然な利確点を OR 反対端に置くが、RR 最低値を満たさない場合に TP を OR 反対端の外へ動かす。これにより「レンジへ戻る」edge を取る MR ではなく、「レンジ回帰後もさらに同方向へ伸びる」edge を要求する設計になる。365d scan の全ペア負EVと、短期BTだけ好調だった履歴は、trigger ではなく TP geometry と pair/session 条件が相場局面に過適合していた可能性を示す。

再設計案は Stop/TP geometry を先に直すこと。具体的には、TP を常に `OR_low/OR_high` または `OR_mid` へ固定し、RR 不足時は TP 延伸ではなく signal reject にする。必要なら `MIN_RR` を撤去して、`reward_to_OR_edge / risk_to_break_extreme` が低い setup を別 bucket として記録し、SL は breakout 極値 + buffer のまま維持する。次点で pair/session を分け、USDJPY LDN、USDJPY NY、EURUSD LDN/NY、GBPUSD LDN/NY を別 cell として 365d/WF で再評価する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

修正対象は主に stop/TP geometry の 1 系統。想定 diff は、`_rr < MIN_RR` の場合に `tp` を `ctx.entry +/- _sl_d * MIN_RR` へ延伸する処理を削除し、`return None` に変えるか、`MIN_RR` を `reward_to_or_edge / risk` の診断 metric に格下げする形。これで OR 反対端回帰という thesis と exit が一致する。

Filter は現時点では大きく削らない。仲値 filter、range quality、両方向 break 除外、HTF agreement veto は false breakout と true breakout を分ける方向で coherent だから維持候補にする。ただし redesign BT では EMA/ADX bonus を scoring だけでなく selection に使っていないことを確認し、pair/session 別に USDJPY LDN の仲値 filter 有無、LDN と NY の分離、OR_mid 利確と OR_edge 利確を比較する必要がある。

必要 BT: 新規実装後に EURUSD/USDJPY/GBPUSD の LDN/NY cell 別 365d と 730d WF を実行し、N>=30、Wilson lo、PF、WF folds>=3、Bonferroni-adjusted p、Kelly fraction を同一 artifact で出す。本監査では BT を実行しないため、現状の昇格判断は INSUFFICIENT_EVIDENCE のまま。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 5 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Win rate | 80.00% | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Wilson lo (95%) | 37.55% | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate; N=5 のため INSUFFICIENT_EVIDENCE |
| PF | 5.862 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate; N=5 のため信頼不可 |
| WF folds (3+) | EUR_USD: W60/W90 folds=3 unstable; GBP_USD: W90 folds=4 borderline, W60 folds=3 unstable; USD_JPY: folds不足 | existing WF: `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md`, `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`, `knowledge-base/raw/bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md` |
| Bonferroni-adj p | 1.0000 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Kelly fraction | 0.6635 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate; N=5 のため採用不可 |
