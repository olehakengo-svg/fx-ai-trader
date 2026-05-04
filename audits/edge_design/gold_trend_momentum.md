---
strategy: gold_trend_momentum
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

XAU/USD の構造的モメンタムと安全資産フローの持続性を前提に、ADX/DI/EMA でトレンドを確認し、EMA21 への押し目または強トレンド継続局面で順張りする 15m daytrade 戦略。広い ATR ベースの SL/TP で XAU のスプレッドと振れを吸収し、トレンド継続の非対称 payoff を取りに行く。`strategies/daytrade/gold_trend_momentum.py:13`, `strategies/daytrade/gold_trend_momentum.py:14`, `strategies/daytrade/gold_trend_momentum.py:15`, `strategies/daytrade/gold_trend_momentum.py:16`, `strategies/daytrade/gold_trend_momentum.py:17`, `strategies/daytrade/gold_trend_momentum.py:19`, `strategies/daytrade/gold_trend_momentum.py:23`, `strategies/daytrade/gold_trend_momentum.py:24`, `strategies/daytrade/gold_trend_momentum.py:25`, `strategies/daytrade/gold_trend_momentum.py:35`, `strategies/daytrade/gold_trend_momentum.py:36`, `strategies/daytrade/gold_trend_momentum.py:37`, `strategies/daytrade/gold_trend_momentum.py:38`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対して、hard gate は `ADX >= 20 AND abs(+DI - -DI) >= 5 AND ((EMA9 > EMA21 AND +DI > -DI) OR (EMA9 < EMA21 AND -DI > +DI))`。通常 BUY は `EMA9>EMA21 AND +DI>-DI AND Low[-8:now] <= EMA21+0.3ATR AND body>=0.25ATR AND (MACD-H>0 OR MACD-H rising) AND entry>open AND entry>EMA9`、SELL は対称。強トレンド時は `ADX>=25 AND abs(DI_gap)>=10` で EMA21 pullback と MACD-H/EMA9 条件を免除するため、pullback continuation と momentum continuation の二系統 trigger として数学的に thesis を捕捉している。`strategies/daytrade/gold_trend_momentum.py:75`, `strategies/daytrade/gold_trend_momentum.py:76`, `strategies/daytrade/gold_trend_momentum.py:79`, `strategies/daytrade/gold_trend_momentum.py:80`, `strategies/daytrade/gold_trend_momentum.py:81`, `strategies/daytrade/gold_trend_momentum.py:84`, `strategies/daytrade/gold_trend_momentum.py:85`, `strategies/daytrade/gold_trend_momentum.py:86`, `strategies/daytrade/gold_trend_momentum.py:90`, `strategies/daytrade/gold_trend_momentum.py:93`, `strategies/daytrade/gold_trend_momentum.py:100`, `strategies/daytrade/gold_trend_momentum.py:102`, `strategies/daytrade/gold_trend_momentum.py:105`, `strategies/daytrade/gold_trend_momentum.py:111`, `strategies/daytrade/gold_trend_momentum.py:113`, `strategies/daytrade/gold_trend_momentum.py:127`, `strategies/daytrade/gold_trend_momentum.py:131`, `strategies/daytrade/gold_trend_momentum.py:132`, `strategies/daytrade/gold_trend_momentum.py:133`, `strategies/daytrade/gold_trend_momentum.py:143`, `strategies/daytrade/gold_trend_momentum.py:145`, `strategies/daytrade/gold_trend_momentum.py:147`, `strategies/daytrade/gold_trend_momentum.py:149`, `strategies/daytrade/gold_trend_momentum.py:162`, `strategies/daytrade/gold_trend_momentum.py:163`, `strategies/daytrade/gold_trend_momentum.py:165`, `strategies/daytrade/gold_trend_momentum.py:182` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に確定足判定、signal bar 固定、または `(symbol, bar_time)` dedup がない。Pullback 判定は `range(-PB_LOOKBACK, 0)` で `iloc[-1]` の current bar high/low を含みうるうえ、confirmation も `ctx.entry`, `ctx.open_price`, `ctx.atr`, `ctx.macdh` をその場で使う。実行層が intrabar evaluate する場合、未確定の high/low/body/MACD で signal が出て、同一 15m bar 内の多重 entry または bar-close 前提の signal 先取りが起きるリスクがある。`strategies/daytrade/gold_trend_momentum.py:63`, `strategies/daytrade/gold_trend_momentum.py:93`, `strategies/daytrade/gold_trend_momentum.py:102`, `strategies/daytrade/gold_trend_momentum.py:103`, `strategies/daytrade/gold_trend_momentum.py:105`, `strategies/daytrade/gold_trend_momentum.py:111`, `strategies/daytrade/gold_trend_momentum.py:113`, `strategies/daytrade/gold_trend_momentum.py:131`, `strategies/daytrade/gold_trend_momentum.py:132`, `strategies/daytrade/gold_trend_momentum.py:133`, `strategies/daytrade/gold_trend_momentum.py:143`, `strategies/daytrade/gold_trend_momentum.py:145`, `strategies/daytrade/gold_trend_momentum.py:147`, `strategies/daytrade/gold_trend_momentum.py:165`, `strategies/daytrade/gold_trend_momentum.py:182` |
| 4 (filter coherence) | STRENGTHENS | XAUUSD 専用 filter は XAU 構造モメンタム thesis に一致する。ADX>=20、DI gap、EMA9/EMA21 方向一致、body>=0.25ATR、通常時 MACD-H 方向確認はすべて momentum/pullback thesis を強化する。HTF agreement と BB width は hard filter ではなく score adjustment なので中立から軽い強化。MR 戦略に MA filter を足して壊す `feedback_ma_filter_breaks_mr.md` 型ではなく、edge が依存する regime tail を HMM gate で消す `feedback_hmm_gate_same_trap.md` 型の hard regime gate もない。`strategies/daytrade/gold_trend_momentum.py:61`, `strategies/daytrade/gold_trend_momentum.py:64`, `strategies/daytrade/gold_trend_momentum.py:65`, `strategies/daytrade/gold_trend_momentum.py:66`, `strategies/daytrade/gold_trend_momentum.py:75`, `strategies/daytrade/gold_trend_momentum.py:76`, `strategies/daytrade/gold_trend_momentum.py:79`, `strategies/daytrade/gold_trend_momentum.py:81`, `strategies/daytrade/gold_trend_momentum.py:84`, `strategies/daytrade/gold_trend_momentum.py:85`, `strategies/daytrade/gold_trend_momentum.py:86`, `strategies/daytrade/gold_trend_momentum.py:90`, `strategies/daytrade/gold_trend_momentum.py:131`, `strategies/daytrade/gold_trend_momentum.py:133`, `strategies/daytrade/gold_trend_momentum.py:136`, `strategies/daytrade/gold_trend_momentum.py:145`, `strategies/daytrade/gold_trend_momentum.py:147`, `strategies/daytrade/gold_trend_momentum.py:149`, `strategies/daytrade/gold_trend_momentum.py:221`, `strategies/daytrade/gold_trend_momentum.py:223`, `strategies/daytrade/gold_trend_momentum.py:226`, `strategies/daytrade/gold_trend_momentum.py:230`, `strategies/daytrade/gold_trend_momentum.py:232` |
| 5 (stop/TP geometry) | ALIGNED | Momentum thesis に対し、TP は `ATR*2.5`、SL は通常時 swing low/high ± `ATR*0.3` かつ min `ATR*1.2`、強トレンド継続時は固定 `ATR*1.2`。さらに `MIN_RR=1.5` を下回る trade は拒否し、強トレンド継続時の幾何は `2.5/1.2 = 2.08R`。Trailing はないが、pullback daytrade の asymm payoff としては整合する。未確定足 high/low を stop 計算に含みうる問題は Axis 3 の timing 問題として扱う。`strategies/daytrade/gold_trend_momentum.py:35`, `strategies/daytrade/gold_trend_momentum.py:36`, `strategies/daytrade/gold_trend_momentum.py:37`, `strategies/daytrade/gold_trend_momentum.py:55`, `strategies/daytrade/gold_trend_momentum.py:56`, `strategies/daytrade/gold_trend_momentum.py:57`, `strategies/daytrade/gold_trend_momentum.py:58`, `strategies/daytrade/gold_trend_momentum.py:158`, `strategies/daytrade/gold_trend_momentum.py:171`, `strategies/daytrade/gold_trend_momentum.py:173`, `strategies/daytrade/gold_trend_momentum.py:174`, `strategies/daytrade/gold_trend_momentum.py:177`, `strategies/daytrade/gold_trend_momentum.py:178`, `strategies/daytrade/gold_trend_momentum.py:180`, `strategies/daytrade/gold_trend_momentum.py:188`, `strategies/daytrade/gold_trend_momentum.py:189`, `strategies/daytrade/gold_trend_momentum.py:191`, `strategies/daytrade/gold_trend_momentum.py:192`, `strategies/daytrade/gold_trend_momentum.py:194`, `strategies/daytrade/gold_trend_momentum.py:199`, `strategies/daytrade/gold_trend_momentum.py:202`, `strategies/daytrade/gold_trend_momentum.py:203` |
| 6 (pair-regime fit) | FORCED | 下の pair-regime table 参照。Audit input は `ALL` だが、実装は XAUUSD のみ許可する。XAU momentum thesis 自体は fit する一方、user feedback memory では XAU は production scope 外であり、ALL cell としては non-XAU FX pairs に適用不能。`strategies/daytrade/gold_trend_momentum.py:61`, `strategies/daytrade/gold_trend_momentum.py:64`, `strategies/daytrade/gold_trend_momentum.py:65`, `strategies/daytrade/gold_trend_momentum.py:66` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は入力どおり `—`。local audit DB `demo_trades.db` は `demo_trades` に 18 行あるが instrument はすべて USD_JPY で、`demo_trades` / `evaluated_candidates` / `oanda_audit` に `gold_trend_momentum` 行は 0 件。legacy raw trade log には小 N の XAU 損失記録があるが、tier-master/audit DB の promotion-grade source ではない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでも不足で、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は採用判断に使えない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| XAUUSD | FIT / production-excluded | Code は XAUUSD のみ許可し、Axis 1 の thesis も XAU 固有の構造的モメンタムと安全資産フロー持続性を前提にしている。ただし production scope では XAU が除外されているため、昇格判断は別枠扱い。`strategies/daytrade/gold_trend_momentum.py:13`, `strategies/daytrade/gold_trend_momentum.py:14`, `strategies/daytrade/gold_trend_momentum.py:61` |
| ALL non-XAU FX pairs | FORCED | `_enabled_symbols = {"XAUUSD"}` と symbol filter により、non-XAU FX pair はすべて `return None`。ALL cell としての pair-regime evidence は存在しない。`strategies/daytrade/gold_trend_momentum.py:61`, `strategies/daytrade/gold_trend_momentum.py:64`, `strategies/daytrade/gold_trend_momentum.py:65`, `strategies/daytrade/gold_trend_momentum.py:66`, `strategies/daytrade/gold_trend_momentum.py:67` |

## Axis 8: failure mode 診断

Tier 3/4 ではなく Tier 2 Shadow だが、既存資料上は XAU production-excluded かつ promotion-grade empirical evidence が不足している。設計破綻の主因候補は Axis 3。Trigger、filter、stop/TP geometry は XAU momentum thesis と概ね整合している一方、pullback 判定、confirmation candle、MACD-H、swing stop が current bar を含みうるため、bar-close 前提が崩れると「EMA21 に触れたように見える未確定足」「陽線/陰線が途中で反転する足」「同一 15m bar での重複発火」を拾う。

再設計案は timing 変更に絞る。Signal 判定は `signal_bar = ctx.df.iloc[-2]` に固定し、pullback window も `[-PB_LOOKBACK-1:-1]` の確定足だけを見る。Execution は次 bar の `ctx.entry` に限定し、`(symbol, strategy, signal_bar_time)` の per-bar dedup を実行層または strategy state に追加する。Stop も signal bar 以前の swing high/low で計算し、current bar high/low を含めない。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は維持する。変更対象は trigger の方向性や filter ではなく、bar-close 化と dedup。具体的には、EMA/ADX/DI/MACD は close 確定済みの `signal_bar` で評価し、pullback 判定は current bar を除外した直近 8 本に限定する。BUY なら `signal_close > signal_open` と `signal_close > EMA9_signal`、SELL なら対称条件で確定足 confirmation を作り、次 bar open/現在 `ctx.entry` で Candidate を emit する。

採用前には本 audit では実行しない XAU 専用 365d BT が必要。特に timing redesign 後の `N`, win rate, Wilson lower 95%, PF, WF folds>=3, Bonferroni-adjusted p, Kelly fraction を同一 source で再集計する。XAU が production scope 外である限り、結果が良くても FX production へ直接昇格させず、XAU shadow 専用または research-only として扱う。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: `demo_trades.db` の `demo_trades` / `evaluated_candidates` / `oanda_audit` に `gold_trend_momentum` 行なし | audit DB |
| Win rate | INSUFFICIENT_EVIDENCE: audit DB に対象 trade rows なし | audit DB |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N=0/対象 rows なしのため算出不可 | audit DB |
| PF | INSUFFICIENT_EVIDENCE: tier-master 365d BT EV/PF は `—` | tier-master |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `gold_trend_momentum` の WF folds>=3 は既存 tier-master から確認不可 | tier-master |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: `gold_trend_momentum` の補正済み p は既存 tier-master から確認不可 | tier-master |
| Kelly fraction | INSUFFICIENT_EVIDENCE: audit DB rows と tier-master PF/WR/avg win-loss がなく算出不可 | tier-master / audit DB |
