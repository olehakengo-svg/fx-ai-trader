---
strategy: wick_imbalance_reversion
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: GBP_USD
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
| 6 (pair-regime fit) | FIT | GBP_USD は既存 365d BT で N=40, WR=70.0%, EV=+0.123, PF=1.44、別 365d scan でも N=38, WR=81.6%, EV=+0.463。W60/W90 は N=38, EV=+0.378, folds=4, positive ratio=1.00 で stable。長期 730d は N=104, EV=+0.142, folds=9, positive ratio=0.67 で borderline だが正方向。単一 pair のため GBP_USD=FIT。 |
| 7 (empirical evidence) | MIXED / INSUFFICIENT_LIVE_EVIDENCE | BT/WF 既存 evidence は positive だが、Bonferroni は境界未達、tier-master は EV 欄が `-`、live/shadow audit は N が小さい。N/WR/EV だけで十分とせず、Wilson lower / PF / WF folds / Bonferroni / Kelly は下表に明示する。 |

## Axis 8: failure mode 診断

Tier 1 (LIVE) / pair_promoted なので Tier 3/4 専用の復活診断ではないが、既存監査では `wick_imbalance_reversion (PAIR_PROMOTED GBP_USD) | 0W, 2L (shadow)`、3か月 hour-bucket counterfactual でも GBP_USD 合算は N=6 程度で `Asia +2.900`, `London -0.150`, `Off -8.300` と live evidence は不足している。破綻軸は Axis 4 が主、Axis 3 と Axis 5 が副。Axis 2 の WIR trigger は thesis と合っているため維持候補。

再設計案は、HTF Hard Block を hard reject から soft penalty に落とし、MR tail を routing から消さないことを第一候補にする。次に confirmation bar を closed-bar 固定にして、`df.iloc[-2]` を確認バー、`ctx.entry` を次足 entry とする variant を pre-register する。Stop/TP は `SL=2.0ATR` 程度、`TP=1.0-1.3ATR` または wick imbalance の mean-reversion target に寄せ、現在の `TP > SL` momentum-like geometry と比較する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

Trigger は維持する。`WIR` はヒゲ偏りを直接数量化しており、`current_body` の反転方向確認も MR thesis と整合しているため、ここを大きく変える優先度は低い。

最小の防御修正は filter/timing/stop の 3 点。`_htf_agreement == "bull" and signal == "SELL"` / `bear and BUY` の hard block を confidence penalty 化し、確認足は closed bar に固定する。コードレベルでは confirmation を `confirm = df.iloc[-2]` に移し、WIR lookback をその直前 window 本にずらす variant が第一候補。SL/TP は MR 用に stop を広げ、TP を mean 到達または 1.0-1.3ATR に寄せる shadow 比較が必要。本監査では BT を実行しない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 40 in 2026-04-17 target BT; 38 in 2026-04-22 365d scan; live/shadow audit N=2 loss sample and 3-month hour-bucket GBP_USD N=6 are too small for adoption | `knowledge-base/raw/bt-results/bt-target-2026-04-17.json`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`; `knowledge-base/wiki/analyses/strategy-coverage-audit-2026-04-21.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Win rate | 70.0% (28/40) target BT; 81.6% (about 31/38) 365d scan; live/shadow audit 0W/2L sample is insufficient | same sources |
| Wilson lo (95%) | 54.6% from 28/40 target BT; 66.6% from 31/38 365d scan; live/shadow Wilson not decision-grade because N=2 | derived from existing N/WR |
| PF | 1.44 in 2026-04-17 target BT; 2026-04-22 entry_breakdown lacks PF; W60/W90/730d reports provide CV/stability but not PF | `knowledge-base/raw/bt-results/bt-target-2026-04-17.json`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md` |
| WF folds (3+) | PASS on W60: 4 folds, positive ratio 1.00, EV +0.378; PASS on W90: 4 folds, positive ratio 1.00, EV +0.378; 730d: 9 folds, positive ratio 0.67, EV +0.142, borderline | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.md` |
| Bonferroni-adj p | INSUFFICIENT / FAILS strict Bonferroni: raw one-sided p=0.0089, Bonferroni alpha'=0.0083, adjusted p ~= 0.0534 for 6-cell correction; BH-FDR passes | `knowledge-base/wiki/strategies/wick-imbalance-reversion.md` |
| Kelly fraction | About 0.214 full Kelly derived from target BT WR=70.0% and PF=1.44; live Kelly is not decision-grade due to N<10 | derived from `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| tier-master EV | `-` / unavailable for GBP_USD despite pair_promoted classification | `knowledge-base/wiki/tier-master.md` |
