---
strategy: alpha_wick_imbalance
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

直近 window 本の上ヒゲ/下ヒゲ不均衡が極端なとき、流動性消費後の反対方向への平均回帰を取りに行く MR 戦略。WIR が正なら上値拒絶の蓄積として SELL、WIR が負なら下値拒絶の蓄積として BUY を、確認バーの body 符号で確定する。`strategies/daytrade/alpha_wick_imbalance.py:5`, `strategies/daytrade/alpha_wick_imbalance.py:21`, `strategies/daytrade/alpha_wick_imbalance.py:25`, `strategies/daytrade/alpha_wick_imbalance.py:27`, `strategies/daytrade/alpha_wick_imbalance.py:53`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `WIR = (sum(upper_wick) - sum(lower_wick)) / sum(all_wick)`、`abs(WIR) >= threshold`、かつ `WIR > threshold and current_body < 0 -> SELL` / `WIR < -threshold and current_body > 0 -> BUY`。RSI/BB %B/z-score は使わないが、ヒゲ偏り自体が extension/rejection proxy で、確認バーが反転方向なので MR thesis を数学的に捕捉している。`strategies/daytrade/alpha_wick_imbalance.py:74`, `strategies/daytrade/alpha_wick_imbalance.py:89`, `strategies/daytrade/alpha_wick_imbalance.py:90`, `strategies/daytrade/alpha_wick_imbalance.py:101`, `strategies/daytrade/alpha_wick_imbalance.py:103`, `strategies/daytrade/alpha_wick_imbalance.py:116`, `strategies/daytrade/alpha_wick_imbalance.py:119` |
| 3 (timing window) | LOOKAHEAD | WIR 集計は `df.iloc[-(window + 1):-1]` で現在バーを除外しており、この部分は look-ahead を避けている。一方、方向確認は `df.iloc[-1]["Close"] - df.iloc[-1]["Open"]` の current bar body に依存するため、呼び出し側が closed-bar dataframe を保証しない live 環境では intrabar close で signal が変動する。戦略内に `bar_time` / `(pair, tf, entry_type)` dedup 状態もなく、同一バー再評価の多重 entry 抑止は外部依存。`strategies/daytrade/alpha_wick_imbalance.py:34`, `strategies/daytrade/alpha_wick_imbalance.py:35`, `strategies/daytrade/alpha_wick_imbalance.py:75`, `strategies/daytrade/alpha_wick_imbalance.py:106`, `strategies/daytrade/alpha_wick_imbalance.py:107`, `strategies/daytrade/alpha_wick_imbalance.py:108`, `strategies/daytrade/alpha_wick_imbalance.py:168` |
| 4 (filter coherence) | BREAKS | `ctx.atr > 0` と `len(df) >= window + 2` は NEUTRAL、`abs(current_body) >= 0.05ATR` は micro body を除外するため STRENGTHENS、`bb_width_pct >= 0.15` は極端な圧縮での WIR 歪みを除外するため STRENGTHENS。ただし HTF Hard Block は `HTF bull and SELL` / `HTF bear and BUY` を拒否し、MR が取りたい上位足 trend-tail の反転を hard reject する。これは重要先行例の MA filter on MR strategy -> BREAKS と HMM regime gate same trap と同型で、全体 verdict は BREAKS。`strategies/daytrade/alpha_wick_imbalance.py:67`, `strategies/daytrade/alpha_wick_imbalance.py:71`, `strategies/daytrade/alpha_wick_imbalance.py:111`, `strategies/daytrade/alpha_wick_imbalance.py:126`, `strategies/daytrade/alpha_wick_imbalance.py:129`, `strategies/daytrade/alpha_wick_imbalance.py:131`, `strategies/daytrade/alpha_wick_imbalance.py:134`, `strategies/daytrade/alpha_wick_imbalance.py:136` |
| 5 (stop/TP geometry) | MISALIGNED | SL は固定 `1.5ATR`、TP は `min(2.5, 1.2 + abs(WIR) * 2.0)ATR`。threshold=0.45 の直上でも TP は約 `2.1ATR` になり、R:R は概ね `1.4` から `1.67`。MR は mean 到達前の noise で切られない wide stop / mean-target が自然だが、この geometry は stop より遠い TP を WIR 強度で伸ばす momentum-like payoff になっている。`strategies/daytrade/alpha_wick_imbalance.py:55`, `strategies/daytrade/alpha_wick_imbalance.py:56`, `strategies/daytrade/alpha_wick_imbalance.py:140`, `strategies/daytrade/alpha_wick_imbalance.py:141`, `strategies/daytrade/alpha_wick_imbalance.py:143`, `strategies/daytrade/alpha_wick_imbalance.py:146`, `strategies/daytrade/alpha_wick_imbalance.py:147`, `strategies/daytrade/alpha_wick_imbalance.py:149`, `strategies/daytrade/alpha_wick_imbalance.py:150` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。実装上の `name` は `wick_imbalance_reversion` で、strategy file には pair gate がない。ヒゲ拒絶 MR thesis は pair 汎用に見えるが、既存 evidence は GBP_USD 以外で弱く、ALL cell としては強制適用。`strategies/daytrade/alpha_wick_imbalance.py:50` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | 入力された tier-master 由来の phase0_shadow / ALL 365d BT EV は `—`。local audit DB `demo_trades.db` には `wick_imbalance_reversion` / `alpha_wick_imbalance` の closed trade rows が 0 件。既存 sidecar BT には pair 別参考値があるが、ALL cell の Wilson / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が同一 tier-master/audit DB source で揃っていないため、`feedback_partial_quant_trap.md` 基準では採用判断不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FORCED | 365d target BT reference は N=27, WR=48.1%, EV=-0.370, PF=0.67。W60/W90 も EV=-0.228, positive ratio 0.40/0.33 で unstable。 |
| EUR_USD | FORCED | 365d target BT reference は N=29, WR=51.7%, EV=-0.082, PF=0.99。W60 は EV=-0.064 / unstable、W90 は borderline。 |
| GBP_USD | FIT | 365d target BT reference は N=40, WR=70.0%, EV=+0.123, PF=1.44。W60/W90 は N=38, EV=+0.378, positive ratio=1.00 で stable。ただし今回入力 cell は ALL / phase0_shadow なので単独 FIT を全体へ外挿しない。 |
| EUR_JPY | FORCED / BORDERLINE | W60/W90/730d は正 EV だが positive ratio 0.50/0.50/0.625 で borderline。tier-master phase0_shadow ALL の採用根拠としては不足。 |
| GBP_JPY | FORCED / BORDERLINE | W60/W90/730d は正 EV だが positive ratio 0.667/0.50/0.579 で borderline。pair calibration なしの ALL 適用は強い。 |
| Other ALL pairs | FORCED / UNTESTED | 実装に pair gate がなく ALL に適用されるが、tier-master / local audit DB に decision-grade pair-specific evidence がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で、入力 metric は 365d BT EV `—`。Tier 3/4 専用の復活診断ではないが、underperforming / evidence 欠落の shadow cell として failure mode を診断する。破綻軸は Axis 4 が主、Axis 3 と Axis 5 が副。Axis 2 の WIR trigger は thesis と合っているため維持候補だが、HTF Hard Block が MR の trend-tail reversal を切り、現在足 close 依存の timing と bar dedup 外部依存が live/shadow 記録を汚しうる。さらに MR に対して `TP > SL` の momentum-like geometry が mean-reversion の戻り幅と噛み合っていない。

再設計案は、HTF Hard Block を削除または soft penalty 化し、confirmation bar を closed bar に固定することを第一候補にする。コードレベルでは confirmation を `confirm = df.iloc[-2]` に移し、WIR lookback をその直前 window 本にずらして、entry は次足 `ctx.entry` に限定する variant を作る。Stop/TP は `SL=2.0ATR` 程度、`TP=1.0-1.3ATR` または wick imbalance の平均回帰 target に寄せ、現行の `TP > SL` geometry と比較する。本監査では新規 BT は実行しない。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

Trigger は維持する。`WIR` はヒゲ偏りを直接数量化しており、`current_body` の反転方向確認も MR thesis と整合しているため、最初に壊すべき箇所ではない。

最小の設計修正は filter/timing/stop の 3 点。`_htf_agreement == "bull" and signal == "SELL"` / `bear and BUY` の hard block を confidence penalty 化し、確認足は closed bar に固定する。SL/TP は MR 用に stop を広げ、TP を mean 到達または 1.0-1.3ATR に寄せる shadow 比較が必要。採用判断には、ALL ではなく pair 別に分割した 365d + WF folds>=3 の既存 audit pipeline 再集計で、Wilson lower / PF / Bonferroni-adjusted p / Kelly fraction を同一表に出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB: 0 closed rows for `wick_imbalance_reversion` / `alpha_wick_imbalance`; tier-master input: `—`; sidecar 365d target BT reference: USD_JPY 27, EUR_USD 29, GBP_USD 40, aggregate 96 | `demo_trades.db`; prompt tier-master input; `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| Win rate | audit DB: INSUFFICIENT_EVIDENCE; sidecar target BT aggregate: 56/96 = 58.3%; pair refs: USD_JPY 48.1%, EUR_USD 51.7%, GBP_USD 70.0% | same sources |
| Wilson lo (95%) | audit DB: INSUFFICIENT_EVIDENCE due N=0; sidecar target BT aggregate derived: 48.34% for 56/96; GBP_USD derived: 54.6% for 28/40 | derived from existing BT counts in `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| PF | audit DB: INSUFFICIENT_EVIDENCE due N=0; tier-master input: not present; sidecar target BT refs: USD_JPY 0.67, EUR_USD 0.99, GBP_USD 1.44; ALL aggregate PF not exactly derivable from source because gross win/loss totals are absent | `demo_trades.db`; prompt tier-master input; `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| WF folds (3+) | sidecar W60/W90: GBP_USD PASS with active_windows=4 and positive_ratio=1.00; USD_JPY/EUR_USD unstable; EUR_JPY/GBP_JPY borderline. Target ALL cell therefore MIXED / INSUFFICIENT_EVIDENCE | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE for target phase0_shadow ALL cell: tier-master input and local audit DB do not provide a usable p-value; prior strategy note reports GBP_USD raw one-sided p=0.0089 / Bonferroni alpha'=0.0083, strict Bonferroni fail, but that is not ALL-cell evidence | `knowledge-base/wiki/strategies/wick-imbalance-reversion.md`; `demo_trades.db`; prompt tier-master input |
| Kelly fraction | audit DB: INSUFFICIENT_EVIDENCE due N=0; sidecar pair-derived full Kelly refs: USD_JPY -0.237, EUR_USD -0.005, GBP_USD +0.214; ALL aggregate Kelly is INSUFFICIENT_EVIDENCE because aggregate PF is not present | derived from `knowledge-base/raw/bt-results/bt-target-2026-04-17.json`; `demo_trades.db` |
