---
strategy: vbp
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

30分レンジの上抜け/下抜け直後に飛び乗らず、最初の 38.2%-50% 押し/戻りと短期反発を待って、ブレイク後の二番動きを取る breakout-pullback continuation thesis。コードコメントと実装は、過去レンジ算出、break 検知、pullback 比率、3バー反発確認、pullback 極値外 SL、初速幅ベース TP を明示している。`strategies/micro_scalp/vbp.py:5`, `strategies/micro_scalp/vbp.py:18`, `strategies/micro_scalp/vbp.py:21`, `strategies/micro_scalp/vbp.py:23`, `strategies/micro_scalp/vbp.py:24`, `strategies/micro_scalp/vbp.py:25`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Thesis 上の trigger は `break close > prior_30m_high_at_t_break -> pullback >= 50% -> 3-bar rebound` であるべきだが、実装は `H_prev = max(b.high for b in bars[-(L+1):-1])` / `L_prev = min(...)` を一度だけ計算し、その後 `for i in range(-20, -3)` の各候補 break bar に対して `b.close > H_prev` / `b.close < L_prev` を判定する。候補 `b` 自身が `hist` に含まれるため、通常の OHLC 不変条件 `b.low <= b.close <= b.high` の下では `b.close > max(hist.high)` も `b.close < min(hist.low)` も成立しない。つまり思想は明確だが、break trigger が数学的に捕捉不能に近い。`strategies/micro_scalp/vbp.py:67`, `strategies/micro_scalp/vbp.py:68`, `strategies/micro_scalp/vbp.py:69`, `strategies/micro_scalp/vbp.py:79`, `strategies/micro_scalp/vbp.py:81`, `strategies/micro_scalp/vbp.py:86` |
| 3 (timing window) | LOOKAHEAD | 現在バー除外の意図はあるが、break 候補時点から見ると `H_prev/L_prev` は候補 break bar とその後の post-break bars を含むため、break 発生時点の prior range ではなく後から見た 30分 range で判定している。さらに entry は現在バー終値 `bars[-1].close` にコストを乗せて作られ、strategy 内には closed-bar 契約や同一 bar の signal dedup state がないため、live 側が抑止しない場合は同一バー多重 entry risk が残る。`strategies/micro_scalp/vbp.py:32`, `strategies/micro_scalp/vbp.py:33`, `strategies/micro_scalp/vbp.py:67`, `strategies/micro_scalp/vbp.py:79`, `strategies/micro_scalp/vbp.py:96`, `strategies/micro_scalp/vbp.py:100`, `strategies/micro_scalp/vbp.py:134`, `strategies/micro_scalp/vbp.py:135` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | `len(bars) < L + 10`、`range_prev <= 0`、`atr <= 0` はデータ品質 filter で NEUTRAL。直近20秒以内の break 探索は「長時間前のブレイクはエッジ消失」という thesis を強めるため設計意図としては STRENGTHENS だが、Axis 2 の threshold bug に巻き込まれている。`pullback_ratio` 到達確認、直近3バーの反発/反落確認、`bars[-1].close` が pullback 極値から戻っている確認は breakout-pullback thesis を強化する。MA filter on MR や HMM regime gate same-trap 型の thesis 破壊 filter はない。`strategies/micro_scalp/vbp.py:63`, `strategies/micro_scalp/vbp.py:71`, `strategies/micro_scalp/vbp.py:74`, `strategies/micro_scalp/vbp.py:99`, `strategies/micro_scalp/vbp.py:103`, `strategies/micro_scalp/vbp.py:106`, `strategies/micro_scalp/vbp.py:108`, `strategies/micro_scalp/vbp.py:110`, `strategies/micro_scalp/vbp.py:116`, `strategies/micro_scalp/vbp.py:118`, `strategies/micro_scalp/vbp.py:120`, `strategies/micro_scalp/vbp.py:122`, `strategies/micro_scalp/vbp.py:124`, `strategies/micro_scalp/vbp.py:130` |
| 5 (stop/TP geometry) | ALIGNED | BUY は pullback low の外側 `sl = pb_low - 0.5*ATR`、SELL は pullback high の外側 `sl = pb_high + 0.5*ATR` で、押し/戻りが完了する前の noise では切られにくい。TP は `burst * 2.0` または `min_tp_pips` の大きい方で、breakout 初速から二番動き幅を測る思想と整合する。`tp_dist < sl_dist * 0.8` を拒否する最低 R:R gate は保守的だが、fixed target なので redesign 後の実証では trailing variant との比較余地がある。`strategies/micro_scalp/vbp.py:137`, `strategies/micro_scalp/vbp.py:138`, `strategies/micro_scalp/vbp.py:140`, `strategies/micro_scalp/vbp.py:141`, `strategies/micro_scalp/vbp.py:142`, `strategies/micro_scalp/vbp.py:145`, `strategies/micro_scalp/vbp.py:147`, `strategies/micro_scalp/vbp.py:148`, `strategies/micro_scalp/vbp.py:154`, `strategies/micro_scalp/vbp.py:155` |
| 6 (pair-regime fit) | FORCED | `pairs: ALL` に対して、strategy は `lookback_sec=1800` と `pullback_ratio=0.5` の単一パラメータだけを持ち、pair/session/spread regime の分岐を持たない。breakout-pullback thesis 自体は major FX 全般に適用可能だが、1秒 micro-scalp の cost/slippage と burst/pullback 幅は pair 依存が強いため、ALL 一括は forced。`USD_JPY=FORCED`, `EUR_USD=FORCED`, `GBP_USD=FORCED`, `EUR_JPY=FORCED`, `GBP_JPY=FORCED`, `EUR_GBP=FORCED`。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は `—`。local audit DB (`demo_trades.db`) の `demo_trades.entry_type`, `evaluated_candidates.strategy_name`, `oanda_audit.entry_type` に `vbp` 行は見つからず、chart-pattern 系 sqlite にも該当 pattern はない。Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は `feedback_partial_quant_trap.md` 基準で decision-grade に埋められない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、tier-master metrics は `—` で、audit DB も `vbp` の実測行を持たないため failure mode を診断する。思想は妥当で、stop/TP の基本 geometry も thesis と概ね整合している。破綻軸は Axis 2 と Axis 3。特に Axis 2 は、break 候補バーを含む `hist` から `H_prev/L_prev` を作って同じ候補バーの close と比較するため、通常 OHLC では break trigger が成立しない構造になっている。

再設計案は、break 探索を「候補バーごとの prior range」に戻すこと。各 `i` について `prior = bars[i-L:i]` を作り、`H_i = max(prior.high)`, `L_i = min(prior.low)` として `bars[i].close > H_i` / `< L_i` を判定する。pullback と反発確認はその後の `bars[i+1:]` で行い、entry は signal bar close 確定後の next tick / next bar fill として扱う。あわせて `(strategy, instrument, bar_time, break_side)` の dedup key を execution 層または strategy state に置く。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

Trigger の核は維持するが、range 計算の基準時点を修正する。現行の `hist = bars[-(L + 1):-1]` 一発計算を break 探索内へ移し、候補 `i` ごとに `prior = bars[i-L:i]` から `H_i/L_i` を作る。BUY は `bars[i].close > H_i`、SELL は `bars[i].close < L_i`、その後の `post_break = bars[i:]` で pullback ratio と3バー反発を確認する。これで「30分 prior range break -> first pullback -> rebound」という思想と条件式が一致する。

Timing は closed-bar / next-fill 前提に寄せる。signal features は確定済みバーだけで計算し、`bars[-1].close` で signal を確定した場合、同じ close で約定した扱いにせず次 tick/次 bar の fill に分離する。Stop/TP は初期案として現行の pullback 極値外 SL と burst×2 TP を残してよいが、redesign BT では fixed TP と ATR trailing / 1R break-even variant を比較する。採用前に必要な検証は、pair 別 30日以上の micro data または 365d 相当、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact に出すこと。本 audit では新規 BT は実行していない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: local audit DB に `vbp` 行なし | audit DB: `demo_trades.db` (`demo_trades`, `evaluated_candidates`, `oanda_audit`) |
| Win rate | INSUFFICIENT_EVIDENCE: N と wins が無いため算出不可 | audit DB / tier-master |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N と wins が無いため算出不可 | audit DB / tier-master |
| PF | INSUFFICIENT_EVIDENCE: tier-master 365d BT EV は `—`、gross profit/loss または PF 欄なし | `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `vbp` の walk-forward folds 記録なし | tier-master / existing audit artifacts |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: raw p / family correction count / adjusted p 記録なし | tier-master / audit DB |
| Kelly fraction | INSUFFICIENT_EVIDENCE: WR と payoff distribution または PF が無いため算出不可 | tier-master / audit DB |
