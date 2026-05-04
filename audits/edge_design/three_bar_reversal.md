---
strategy: three_bar_reversal
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

3本連続の同方向 candle を短期過伸展とみなし、現在足が反対方向へ反転して前足高値/安値を抜いた時だけ平均回帰方向へ入る MR 戦略。コード上も `strategy_type = "MR"` と明示し、BUY は3連続陰線後の上抜け、SELL は3連続陽線後の下抜けに限定しているため、思想は AMBIGUOUS ではない。`strategies/scalp/three_bar_reversal.py:12`, `strategies/scalp/three_bar_reversal.py:38`, `strategies/scalp/three_bar_reversal.py:39`, `strategies/scalp/three_bar_reversal.py:41`, `strategies/scalp/three_bar_reversal.py:58`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | BUY は `three_bear and current_bull and entry > prev_high and BB%B < 0.35 and RSI5 < 42`、SELL は `three_bull and current_bear and entry < prev_low and BB%B > 0.65 and RSI5 > 58`。MR thesis に必要な extension proxy は連続足、BB%B、RSI5 で捕捉され、前足高値/安値 breakout は反転確認として働く。`strategies/scalp/three_bar_reversal.py:15`, `strategies/scalp/three_bar_reversal.py:16`, `strategies/scalp/three_bar_reversal.py:17`, `strategies/scalp/three_bar_reversal.py:18`, `strategies/scalp/three_bar_reversal.py:43`, `strategies/scalp/three_bar_reversal.py:44`, `strategies/scalp/three_bar_reversal.py:45`, `strategies/scalp/three_bar_reversal.py:46`, `strategies/scalp/three_bar_reversal.py:60`, `strategies/scalp/three_bar_reversal.py:61`, `strategies/scalp/three_bar_reversal.py:62`, `strategies/scalp/three_bar_reversal.py:63` |
| 3 (timing window) | LATE | 過伸展そのものではなく、現在足が反対色になったうえで前足高値/安値を突破するまで待つため、MR としては signal が反転後半に寄る。過去3本は `iloc[-4:-2]` で参照しており未来参照は見えないが、`ctx.entry` と `ctx.open_price` による現在足 intrabar 判定で bar-close 固定ではない。strategy 内に bar_time dedup はなく、同一 bar 多重評価の抑止は外部実行層依存。`strategies/scalp/three_bar_reversal.py:34`, `strategies/scalp/three_bar_reversal.py:35`, `strategies/scalp/three_bar_reversal.py:36`, `strategies/scalp/three_bar_reversal.py:42`, `strategies/scalp/three_bar_reversal.py:43`, `strategies/scalp/three_bar_reversal.py:44`, `strategies/scalp/three_bar_reversal.py:59`, `strategies/scalp/three_bar_reversal.py:60`, `strategies/scalp/three_bar_reversal.py:61`, `strategies/scalp/three_bar_reversal.py:80` |
| 4 (filter coherence) | STRENGTHENS | Friday block は週末流動性回避で NEUTRAL。BB%B と RSI5 は MR の過伸展検出なので STRENGTHENS。Stoch cross は hard filter ではなく score bonus で、反転確認として STRENGTHENS。ADX は `strategy_type="MR"` に対する confidence penalty で entry hard gate ではないため、MA filter on MR strategy -> BREAKS や HMM regime gate same trap 型の thesis 破壊は検出しない。`strategies/scalp/three_bar_reversal.py:23`, `strategies/scalp/three_bar_reversal.py:45`, `strategies/scalp/three_bar_reversal.py:46`, `strategies/scalp/three_bar_reversal.py:52`, `strategies/scalp/three_bar_reversal.py:62`, `strategies/scalp/three_bar_reversal.py:63`, `strategies/scalp/three_bar_reversal.py:69`, `strategies/scalp/three_bar_reversal.py:78`, `strategies/scalp/three_bar_reversal.py:79` |
| 5 (stop/TP geometry) | ALIGNED | TP は `1.5ATR`、SL は直近2本の swing low/high の外側に `0.15ATR` を足す構造。MR として、直近 swing を割るまでは切らない wide stop 寄りで、固定 TP も反転後の短期戻り取りとして概ね整合する。ただし実効 R:R は entry から swing までの距離に依存し、コード上は固定値ではない。`strategies/scalp/three_bar_reversal.py:19`, `strategies/scalp/three_bar_reversal.py:20`, `strategies/scalp/three_bar_reversal.py:55`, `strategies/scalp/three_bar_reversal.py:56`, `strategies/scalp/three_bar_reversal.py:72`, `strategies/scalp/three_bar_reversal.py:73` |
| 6 (pair-regime fit) | FORCED | `ALL` scope だが strategy file に pair/session/spread/regime の選別がなく、既存 evidence も実質 USD_JPY 小Nに偏る。per-pair verdict: ALL=FORCED。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | gate-progression 集計では N=3, WR=33.33%, Wilson lo=6.15%, EV=+0.37p, PF=1.314, Kelly=0.0797, Bonferroni p=1.0000。PF/Kelly は埋まるが、N が極小、Bonferroni 不通過、WF folds>=3 が既存 tier-master/audit DB から確認できない。tier-master 365d BT EV は入力どおり `—`。`feedback_partial_quant_trap.md` 基準では採用判断不可。 |

## Axis 8: failure mode 診断

Tier 2 Shadow の underperforming/low-evidence cell として診断する。破綻軸は主に Axis 3、補助的に Axis 2 の trigger 過密化である。思想は「3本足の過伸展を逆張る」MR として妥当だが、現行 trigger は `3本連続足 + 現在足反転色 + 前足高値/安値突破 + BB%B + RSI5` を同時要求するため、反転の初動ではなく確認後の遅い場所に寄り、既存 decomposition でも「4条件同時必須 → 180日でN=6、年間N=12では統計検証不能」と記録されている。

再設計案は1案に絞る。過伸展条件は維持し、entry confirmation を「前足高値/安値 breakout」から「現在足が反対色で、前足実体 midpoint または前足 open を回復/割れ」に緩める。具体的には BUY を `_three_bear and _curr_bull and ctx.entry > float(ctx.df.iloc[-2]["Open"]) and ctx.bbpb < 0.40 and ctx.rsi5 < 45`、SELL を対称条件にする。これにより MR の反転初動を拾い、bar-close variant では `df.iloc[-2]` 確定足で反転確認、intrabar variant では `symbol + tf + bar_time + entry_type` dedup を必須にする。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

Trigger の思想自体は残す。変更対象は confirmation timing で、前足高値/安値の完全突破を必須にする現行条件を、前足実体の回復/割れまたは前足 midpoint cross に置き換える。BB%B と RSI5 は過伸展 gate として維持しつつ、閾値は `0.35/0.65, 42/58` から `0.40/0.60, 45/55` 程度に緩める候補を pre-register する。

Stop/TP は現行の swing 外 SL と `1.5ATR` TP を初期案では維持する。採用前には本 audit では実行しない 365d 以上、pair別、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source で出す必要がある。N/WR/EV だけで復活判断しない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 3 | audit DB / gate-progression aggregate (`knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`) |
| Win rate | 33.33% | audit DB / gate-progression aggregate (`knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`) |
| Wilson lo (95%) | 6.15% | audit DB / gate-progression aggregate (`knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`) |
| PF | 1.314 | audit DB / gate-progression aggregate (`knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`) |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: existing tier-master/audit DB source does not provide >=3 WF folds for this strategy/cell. | tier-master input `365d BT EV=—`; repo search over existing audit artifacts |
| Bonferroni-adj p | 1.0000 | audit DB / gate-progression aggregate (`knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`) |
| Kelly fraction | 0.0797 | audit DB / gate-progression aggregate (`knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`) |
