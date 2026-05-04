---
strategy: gold_vol_break
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

XAU/USD の 15m で BB(2.5σ) を ATR 急増・ADX/DI 方向確認・大きな同方向 candle body と同時に突破した局面へ順張りし、金の volatility clustering と momentum burst を高 R:R で捕捉する breakout 戦略。対象は XAUUSD に限定され、TP=ATR7x3.0 / SL=ATR7x1.0 を基本 geometry とする。`strategies/daytrade/gold_vol_break.py:2`, `strategies/daytrade/gold_vol_break.py:5`, `strategies/daytrade/gold_vol_break.py:6`, `strategies/daytrade/gold_vol_break.py:13`, `strategies/daytrade/gold_vol_break.py:14`, `strategies/daytrade/gold_vol_break.py:15`, `strategies/daytrade/gold_vol_break.py:16`, `strategies/daytrade/gold_vol_break.py:17`, `strategies/daytrade/gold_vol_break.py:24`, `strategies/daytrade/gold_vol_break.py:25`, `strategies/daytrade/gold_vol_break.py:26`, `strategies/daytrade/gold_vol_break.py:39`, `strategies/daytrade/gold_vol_break.py:40`, `strategies/daytrade/gold_vol_break.py:41`, `strategies/daytrade/gold_vol_break.py:42`, `strategies/daytrade/gold_vol_break.py:43`, `strategies/daytrade/gold_vol_break.py:44`, `strategies/daytrade/gold_vol_break.py:46`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Breakout / momentum-burst thesis に対して、hard trigger は `ATR7 > ATR14*1.05 AND sigma>0 AND body >= ATR7*0.4 AND BUY(entry > BB_upper_2.5σ AND +DI > -DI AND entry > open) / SELL(entry < BB_lower_2.5σ AND -DI > +DI AND entry < open)`。BB 2.5σ breakout、volatility expansion、trend-strength/direction、同方向 candle body が同時に要求されており、MR trigger ではなく momentum breakout trigger として整合する。`strategies/daytrade/gold_vol_break.py:59`, `strategies/daytrade/gold_vol_break.py:62`, `strategies/daytrade/gold_vol_break.py:63`, `strategies/daytrade/gold_vol_break.py:64`, `strategies/daytrade/gold_vol_break.py:67`, `strategies/daytrade/gold_vol_break.py:72`, `strategies/daytrade/gold_vol_break.py:73`, `strategies/daytrade/gold_vol_break.py:77`, `strategies/daytrade/gold_vol_break.py:78`, `strategies/daytrade/gold_vol_break.py:80`, `strategies/daytrade/gold_vol_break.py:81`, `strategies/daytrade/gold_vol_break.py:82`, `strategies/daytrade/gold_vol_break.py:93`, `strategies/daytrade/gold_vol_break.py:94`, `strategies/daytrade/gold_vol_break.py:95`, `strategies/daytrade/gold_vol_break.py:108`, `strategies/daytrade/gold_vol_break.py:109`, `strategies/daytrade/gold_vol_break.py:110` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に確定足固定、signal bar 時刻、または `(symbol, strategy, bar_time)` dedup がない。Entry 判定は current context の `ctx.entry` と `ctx.open_price` で body と breakout を評価し、`ctx.adx`, `ctx.adx_pos`, `ctx.adx_neg`, `ctx.atr7`, `ctx.atr` も同じ evaluate 時点の値を使う。実行層が intrabar evaluate する場合、未確定 15m 足の一時的な BB 突破・body・DI 状態で signal が出るうえ、同一 bar 内の多重 entry を strategy 側で防げない。`strategies/daytrade/gold_vol_break.py:48`, `strategies/daytrade/gold_vol_break.py:59`, `strategies/daytrade/gold_vol_break.py:63`, `strategies/daytrade/gold_vol_break.py:80`, `strategies/daytrade/gold_vol_break.py:81`, `strategies/daytrade/gold_vol_break.py:82`, `strategies/daytrade/gold_vol_break.py:93`, `strategies/daytrade/gold_vol_break.py:94`, `strategies/daytrade/gold_vol_break.py:95`, `strategies/daytrade/gold_vol_break.py:108`, `strategies/daytrade/gold_vol_break.py:109`, `strategies/daytrade/gold_vol_break.py:110`, `strategies/daytrade/gold_vol_break.py:163` |
| 4 (filter coherence) | STRENGTHENS | XAUUSD 専用 gate、ADX>=20、ATR surge、BB 2.5σ、body>=0.4ATR、DI direction、同方向 candle はすべて volatility breakout thesis を強化する hard filter。ADX/DI gap/MACD/HTF は score adjustment で、HTF 逆行も reject ではなく -1.5 点なので、HMM regime gate が edge tail を hard に消す `feedback_hmm_gate_same_trap.md` 型ではない。MR 戦略に MA filter を足して反転 edge を壊す `feedback_ma_filter_breaks_mr.md` 型でもない。`strategies/daytrade/gold_vol_break.py:46`, `strategies/daytrade/gold_vol_break.py:49`, `strategies/daytrade/gold_vol_break.py:50`, `strategies/daytrade/gold_vol_break.py:59`, `strategies/daytrade/gold_vol_break.py:62`, `strategies/daytrade/gold_vol_break.py:63`, `strategies/daytrade/gold_vol_break.py:67`, `strategies/daytrade/gold_vol_break.py:77`, `strategies/daytrade/gold_vol_break.py:78`, `strategies/daytrade/gold_vol_break.py:80`, `strategies/daytrade/gold_vol_break.py:82`, `strategies/daytrade/gold_vol_break.py:93`, `strategies/daytrade/gold_vol_break.py:94`, `strategies/daytrade/gold_vol_break.py:95`, `strategies/daytrade/gold_vol_break.py:108`, `strategies/daytrade/gold_vol_break.py:109`, `strategies/daytrade/gold_vol_break.py:110`, `strategies/daytrade/gold_vol_break.py:133`, `strategies/daytrade/gold_vol_break.py:140`, `strategies/daytrade/gold_vol_break.py:146`, `strategies/daytrade/gold_vol_break.py:151`, `strategies/daytrade/gold_vol_break.py:153`, `strategies/daytrade/gold_vol_break.py:156` |
| 5 (stop/TP geometry) | MISALIGNED | Code は `TP=ATR7*3.0`、`SL=max(ATR7*1.0, 0.030)`、最低 R:R gate は `_rr >= 2.0`。高 R:R の非対称性は momentum thesis には合うが、BB volatility breakout thesis では spec の基準どおり trailing または breakout freshness / failed-break guard が必要。固定 3ATR TP は burst を途中で capped にし、固定 1ATR SL は XAU の breakout retest / wick に対して硬すぎる可能性があるため、breakout geometry としては不十分。`strategies/daytrade/gold_vol_break.py:24`, `strategies/daytrade/gold_vol_break.py:25`, `strategies/daytrade/gold_vol_break.py:26`, `strategies/daytrade/gold_vol_break.py:43`, `strategies/daytrade/gold_vol_break.py:44`, `strategies/daytrade/gold_vol_break.py:90`, `strategies/daytrade/gold_vol_break.py:103`, `strategies/daytrade/gold_vol_break.py:104`, `strategies/daytrade/gold_vol_break.py:105`, `strategies/daytrade/gold_vol_break.py:118`, `strategies/daytrade/gold_vol_break.py:119`, `strategies/daytrade/gold_vol_break.py:120`, `strategies/daytrade/gold_vol_break.py:125`, `strategies/daytrade/gold_vol_break.py:126`, `strategies/daytrade/gold_vol_break.py:127`, `strategies/daytrade/gold_vol_break.py:128`, `strategies/daytrade/gold_vol_break.py:129`, `strategies/daytrade/gold_vol_break.py:160` |
| 6 (pair-regime fit) | FORCED | 下の pair-regime table 参照。Audit input は `ALL` だが、実装は XAUUSD のみ許可する。XAU breakout thesis 自体は FIT だが、user feedback memory と既存監査では XAU は production scope 外であり、ALL cell としては non-XAU FX pairs に適用不能。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は入力どおり `—`。`demo_trades.db` は `demo_trades` / `evaluated_candidates` / `oanda_audit` / `oanda_trades` / `pending_oanda_ops` に `gold_vol_break` または XAU 行が 0 件。既存 production routing audit でも `gold_vol_break` は DB never bucket、low-firing RCA でも XAU instrument 対象外疑い。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでも不足で、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は採用判断に使えない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| XAUUSD | FIT / production-excluded | Code は `_enabled_symbols = {"XAUUSD"}` のみ許可し、thesis も XAU の BB volatility breakout に特化している。ただし user feedback memory では XAU は production scope 外なので、FX production 昇格根拠にはならない。`strategies/daytrade/gold_vol_break.py:2`, `strategies/daytrade/gold_vol_break.py:5`, `strategies/daytrade/gold_vol_break.py:6`, `strategies/daytrade/gold_vol_break.py:46`, `strategies/daytrade/gold_vol_break.py:49`, `strategies/daytrade/gold_vol_break.py:50` |
| ALL non-XAU FX pairs | FORCED | `_enabled_symbols` と symbol gate により non-XAU FX pair はすべて `return None`。ALL cell としての pair-regime evidence は存在しない。`strategies/daytrade/gold_vol_break.py:46`, `strategies/daytrade/gold_vol_break.py:49`, `strategies/daytrade/gold_vol_break.py:50`, `strategies/daytrade/gold_vol_break.py:51` |

## Axis 8: failure mode 診断

Tier 3/4 ではなく Tier 2 Shadow だが、既存資料上は XAU production-excluded かつ promotion-grade empirical evidence がない。設計破綻候補は Axis 3 と Axis 5。Axis 2/4 は thesis と整合しており、MR に MA filter を足す型や HMM hard gate で regime tail を消す型ではない。一方、current context の未確定 15m 足で BB 突破・body・DI を評価でき、strategy 内に per-bar dedup がないため、bar-close 前提が崩れると一時的な spike を複数回 chase する。さらに breakout thesis に対して固定 3ATR TP / 1ATR SL は、XAU の retest と trend continuation の両方に中途半端で、伸びる局面を capped にし、初動 wick で切られやすい。

再設計案は timing と geometry の 2 点。Trigger は思想に合っているので維持し、`signal_bar = ctx.df.iloc[-2]` の確定足 close で BB(2.5σ) breakout、ATR surge、ADX/DI、body を評価する。Execution は次 bar の `ctx.entry` に限定し、`(symbol, strategy, signal_bar_time)` dedup を追加する。Stop/TP は fixed 3ATR/1ATR から、初期 SL を signal bar の反対側 wick または `1.2*ATR7` の広い方に置き、1R 到達後は ATR trailing に移行する geometry へ変更する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は維持する。最小変更は、未確定足依存を外して bar-close signal に固定すること。BUY は `signal_close > bb_upper_25_signal AND signal_close > signal_open AND +DI_signal > -DI_signal AND ATR7_signal > ATR14_signal*1.05`、SELL は対称条件にし、signal bar の次 bar でだけ Candidate を emit する。同一 `signal_bar_time` からの再 emit は拒否する。

Geometry は fixed TP/SL を breakout 用に寄せる。初期 SL は `max(1.2*ATR7, abs(entry - signal_low/high) + 0.2*ATR7)` とし、TP は固定 3ATR だけでなく `2R partial + ATR trailing`、または `tp = entry ± max(3*ATR7, 2.5*risk)` を比較対象にする。採用前には本 audit では実行しない XAU 専用 365d BT と WF folds>=3 で、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source から再集計する必要がある。XAU が production scope 外である限り、良好でも FX production へ直接昇格せず、XAU shadow/research 専用として扱う。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: `demo_trades.db` の `demo_trades` / `evaluated_candidates` / `oanda_audit` / `oanda_trades` / `pending_oanda_ops` に `gold_vol_break` または XAU rows なし | audit DB |
| Win rate | INSUFFICIENT_EVIDENCE: audit DB に対象 closed trade rows なし | audit DB |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N=0/対象 rows なしのため算出不可 | audit DB |
| PF | INSUFFICIENT_EVIDENCE: tier-master 365d BT EV/PF は `—` | tier-master |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `gold_vol_break` の WF folds>=3 は既存 tier-master から確認不可 | tier-master |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: `gold_vol_break` の補正済み p は既存 tier-master から確認不可 | tier-master |
| Kelly fraction | INSUFFICIENT_EVIDENCE: PF/WR/avg win-loss または closed trade rows がないため算出不可 | tier-master / audit DB |
