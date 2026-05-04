---
strategy: inducement_ob
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

直近の stop cluster / inducement を sweep した後、OB ゾーンと HTF OB が重なる場所で reclaim 反転を確認し、大口の liquidity grab 後の逆方向伸長を取る SMC reversal thesis。SL は OB 境界近くに置き、ATR / impulse 方向の拡大 TP を狙う設計として明示されている。`strategies/daytrade/inducement_ob.py:17`, `strategies/daytrade/inducement_ob.py:19`, `strategies/daytrade/inducement_ob.py:20`, `strategies/daytrade/inducement_ob.py:21`, `strategies/daytrade/inducement_ob.py:22`, `strategies/daytrade/inducement_ob.py:23`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | thesis は liquidity sweep + reclaim + OB 反転なので、trigger は `OB impulse exists ∧ inducement swing exists ∧ recent inducement sweep ∧ current bar touches OB ∧ reversal body ∧ 20-bar H/L sweep on previous bar ∧ current reclaim ∧ HTF OB zone contains price`。Bullish OB は陰線後の 3 本以上 bullish impulse かつ `impulse_total >= ATR*2.0`、bearish は対称条件。entry は BUY で `Low < inducement - 0.05ATR`、`cur_low <= ob_high + 0.3ATR`、`cur_close > cur_open`、`body/range >= 0.35`、さらに前足が 20 本 low を sweep して current close が sweep open を上回る。SELL は高値側で対称。SMC reversal thesis を直接捕捉しており、trigger 自体は MISMATCH ではない。`strategies/daytrade/inducement_ob.py:41`, `strategies/daytrade/inducement_ob.py:42`, `strategies/daytrade/inducement_ob.py:119`, `strategies/daytrade/inducement_ob.py:133`, `strategies/daytrade/inducement_ob.py:144`, `strategies/daytrade/inducement_ob.py:158`, `strategies/daytrade/inducement_ob.py:391`, `strategies/daytrade/inducement_ob.py:399`, `strategies/daytrade/inducement_ob.py:409`, `strategies/daytrade/inducement_ob.py:413`, `strategies/daytrade/inducement_ob.py:415`, `strategies/daytrade/inducement_ob.py:247`, `strategies/daytrade/inducement_ob.py:250`, `strategies/daytrade/inducement_ob.py:253`, `strategies/daytrade/inducement_ob.py:257`, `strategies/daytrade/inducement_ob.py:535`, `strategies/daytrade/inducement_ob.py:543` |
| 3 (timing window) | LOOKAHEAD | `cur_idx = len(ctx.df) - 1` を signal bar とし、`cur_open/high/low/close` で OB touch と反転足を判定し、同じ `cur_idx` を liquidity grab の reclaim 足として使う。実行層が未確定 15m bar 中に evaluate する場合、current bar の High/Low/Close が変動中のまま signal 化される。strategy 内には `ctx.bar_time` を使った closed-bar 固定や `(symbol, side, bar)` dedup がなく、同一 bar 多重 emit の防止もないため LOOKAHEAD 寄り。`strategies/daytrade/inducement_ob.py:224`, `strategies/daytrade/inducement_ob.py:226`, `strategies/daytrade/inducement_ob.py:233`, `strategies/daytrade/inducement_ob.py:234`, `strategies/daytrade/inducement_ob.py:371`, `strategies/daytrade/inducement_ob.py:380`, `strategies/daytrade/inducement_ob.py:382`, `strategies/daytrade/inducement_ob.py:383`, `strategies/daytrade/inducement_ob.py:494`, `strategies/daytrade/inducement_ob.py:626` |
| 4 (filter coherence) | BREAKS | `ADX_MIN=12` / `ADX_MAX=40` は薄商いと強トレンド逆張りを避けるため STRENGTHENS。active hours / Friday block も execution risk filter として NEUTRAL-STRENGTHENS。HTF OB zone gate は thesis の上位構造同期として STRENGTHENS だが、現在価格が疑似 1H OB 付近にないと hard block するため、tail を消す HMM gate same-trap 型のリスクは残る。決定的に壊しているのは pair/direction filter で、コード thesis は BUY/SELL 対称の sweep + reclaim なのに `USDJPY` は BUY only、`EURUSD` は SELL only としており、thesis 由来ではない方向制約で有効な反対側 setup を破壊しうる。MA filter on MR strategy 型そのものではないが、generic hard gate が edge tail を落とす `feedback_hmm_gate_same_trap.md` 寄り。`strategies/daytrade/inducement_ob.py:65`, `strategies/daytrade/inducement_ob.py:66`, `strategies/daytrade/inducement_ob.py:67`, `strategies/daytrade/inducement_ob.py:74`, `strategies/daytrade/inducement_ob.py:75`, `strategies/daytrade/inducement_ob.py:77`, `strategies/daytrade/inducement_ob.py:80`, `strategies/daytrade/inducement_ob.py:83`, `strategies/daytrade/inducement_ob.py:84`, `strategies/daytrade/inducement_ob.py:346`, `strategies/daytrade/inducement_ob.py:347`, `strategies/daytrade/inducement_ob.py:361`, `strategies/daytrade/inducement_ob.py:362`, `strategies/daytrade/inducement_ob.py:480`, `strategies/daytrade/inducement_ob.py:486`, `strategies/daytrade/inducement_ob.py:526`, `strategies/daytrade/inducement_ob.py:528` |
| 5 (stop/TP geometry) | MISALIGNED | Code comment は `SL_FIXED_PIPS=2.0` と `TP_ATR_MULT=3.5`、`MIN_RR=2.0` で 1:10 爆発待ちを意図するが、SL は actual sweep extreme の外側ではなく OB 境界から固定 2 pip 外に置かれる。liquidity grab / stop-hunt reversal では sweep wick 再試行に耐える stop が必要だが、OB 境界 + 2 pip は volatility proxy `bar_range >= 1.5ATR` を要求する trigger と矛盾し、既存 force-demoted 診断の instant SL hit と一致する。TP は `max(impulse 60%, entry+3.5ATR)` / `min(...)` と `MIN_RR=2.0` で非対称だが、stop 側が thesis に対して狭すぎる。`strategies/daytrade/inducement_ob.py:69`, `strategies/daytrade/inducement_ob.py:70`, `strategies/daytrade/inducement_ob.py:71`, `strategies/daytrade/inducement_ob.py:72`, `strategies/daytrade/inducement_ob.py:236`, `strategies/daytrade/inducement_ob.py:240`, `strategies/daytrade/inducement_ob.py:557`, `strategies/daytrade/inducement_ob.py:559`, `strategies/daytrade/inducement_ob.py:561`, `strategies/daytrade/inducement_ob.py:563`, `strategies/daytrade/inducement_ob.py:568`, `strategies/daytrade/inducement_ob.py:573`, `strategies/daytrade/inducement_ob.py:581`, `strategies/daytrade/inducement_ob.py:585` |
| 6 (pair-regime fit) | FORCED | `pairs: ALL` に対し、実装は USDJPY/EURUSD/GBPUSD/EURGBP/XAUUSD の 5 銘柄だけを許可し、さらに USDJPY BUY only / EURUSD SELL only を課す。pair-specific threshold や session/regime 分岐はなく、ALL cell としては forced fit。`strategies/daytrade/inducement_ob.py:80`, `strategies/daytrade/inducement_ob.py:83`, `strategies/daytrade/inducement_ob.py:84`, `strategies/daytrade/inducement_ob.py:470`, `strategies/daytrade/inducement_ob.py:471`, `strategies/daytrade/inducement_ob.py:526`, `strategies/daytrade/inducement_ob.py:528` |
| 7 (empirical evidence) | NEGATIVE / INSUFFICIENT_EVIDENCE | tier-master の FORCE_DEMOTED 365d BT EV は `—`。最新 gate-progression audit では strategy aggregate `N=9`, `WR=11.11%`, `Wilson lo=1.99%`, `EV=-3.17p`, `PF=0.037`, `Kelly=0.0000`, `raw Kelly=-2.8788`, `Bonferroni p=1.0000` と明確に negative。3month H1 counterfactual shadow も `n=4`, `WR=0.0%`, `EV=-6.525`, `Wilson BF lower=0.0`, `p_bonferroni=1.0`。ただし WF folds>=3 は現行 tier/audit source で満たさず、730d WFA 参考値も `N_windows<2` なので、`feedback_partial_quant_trap.md` 基準では redesign 採用判断には不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED | Whitelist 対象だが BUY only に固定され、SELL setup はコード上 block。H1 3month shadow は USD_JPY London `N=1`, `WR=0%`, `EV=-7.4`, `PF=0.0`。`strategies/daytrade/inducement_ob.py:80`, `strategies/daytrade/inducement_ob.py:83`, `strategies/daytrade/inducement_ob.py:526` |
| EURUSD | FORCED | Whitelist 対象だが SELL only に固定され、BUY setup はコード上 block。H1 3month live は EUR_USD Asia `N=2`, `WR=0%`, `EV=-1.7`, `PF=0.0`。`strategies/daytrade/inducement_ob.py:80`, `strategies/daytrade/inducement_ob.py:84`, `strategies/daytrade/inducement_ob.py:528` |
| GBPUSD | FORCED | Whitelist 対象で方向制限はないが、pair-specific threshold なし。H1 3month shadow GBP_USD Asia `N=3`, `WR=0%`, `EV=-6.233`, `PF=0.0`。`strategies/daytrade/inducement_ob.py:80` |
| EURGBP | FORCED | Whitelist 対象で方向制限はないが、latest negative cell は EUR_GBP 14時 `N=3`, `WR=0%`, `EV=-5.17`, `PF=0.0`。`strategies/daytrade/inducement_ob.py:80` |
| XAUUSD | FORCED | Whitelist 対象だが pip unit は JPY と同じ `0.01` 扱いで、gold 専用 stop/volatility geometry ではない。`strategies/daytrade/inducement_ob.py:80`, `strategies/daytrade/inducement_ob.py:554`, `strategies/daytrade/inducement_ob.py:555` |
| Other ALL pairs | FORCED / blocked | `_sym not in ALLOWED_PAIRS` で即 `None`。ALL universe の大半は未対応。`strategies/daytrade/inducement_ob.py:470`, `strategies/daytrade/inducement_ob.py:471` |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) なので failure mode を適用する。破綻軸は Axis 3 / Axis 4 / Axis 5。Axis 2 の thesis 捕捉は比較的明確で、OB impulse、inducement sweep、20-bar liquidity grab、reclaim、HTF OB zone まで要求している。一方、Axis 3 は current bar OHLC を signal / reclaim に使い、bar-close contract と per-bar dedup がない。Axis 4 は symmetric SMC thesis に対して USDJPY BUY only / EURUSD SELL only の根拠不明な hard direction gate を入れている。Axis 5 は最大の実害で、trigger 側では 1.5ATR 以上の sweep 足を大口関与として要求するのに、stop は actual sweep extreme 外ではなく OB 境界 + 固定 2 pip なので、stop-hunt 後の二度目の wick で即死しやすい。

再設計案は、思想は維持しつつ timing と stop geometry を先に直す。`_check_liquidity_grab()` と `_check_entry()` は確定済み signal bar を対象にし、`ctx.df.iloc[-2]` を reclaim / reversal bar、`ctx.entry` を次 bar execution として扱う。Candidate か dispatch layer に `signal_bar_time` を渡し、`(symbol, entry_type, side, signal_bar_time)` で同一 bar dedup を必須にする。stop は BUY なら `min(ob_low, liq_grab.sweep_extreme) - max(0.3ATR, spread_buffer)`、SELL なら `max(ob_high, liq_grab.sweep_extreme) + max(0.3ATR, spread_buffer)` に置換し、固定 2 pip は floor ではなく最小 buffer に降格する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想は捨てない。コードから導出できる thesis は、liquidity sweep と OB reclaim を使う stop-hunt reversal として明確で、trigger も thesis の主要成分を捕捉している。失敗は主に実行設計で、未確定 bar 依存、根拠不明な hard direction filter、そして actual sweep volatility に対して狭すぎる stop geometry が force_demoted の中核。

具体修正は 3 点。第一に signal を closed-bar 化し、`cur_idx` を直接 signal/reclaim に使わず、確定済み bar の OHLC で sweep/reclaim/reversal を判定して次 bar で約定する。第二に USDJPY BUY only / EURUSD SELL only を削除するか、少なくとも pair-specific evidence が出るまで score penalty に落とす。第三に SL を OB 境界固定 2 pip から sweep extreme 外側 + ATR buffer に変更し、TP は現行の impulse/ATR target を維持しつつ最低 RR を 1.5-2.0 の範囲で再検証する。

採用前に必要な検証は新規 BT だが、本 audit では実行しない。必要 artifact は closed-bar + sweep-extreme SL variant について、pair 別 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 audit DB / tier-master source で出すこと。N/WR/EV だけ、または 730d WFA の `N_windows<2` 参考値だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 9 latest gate-progression aggregate; older shadow deep dive N=10; local `demo_trades.db` exact rows for `inducement_ob` are 0 in `demo_trades` / `evaluated_candidates` / `oanda_audit`. | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; local DB read |
| Win rate | 11.11% latest gate-progression aggregate; older shadow deep dive 10.0%. | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Wilson lo (95%) | 1.99% latest gate-progression aggregate. H1 3month shadow status Wilson BF lower = 0.0. | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| PF | 0.037 latest gate-progression aggregate. Older shadow deep dive PF=0.03. 730d WFA reference aggregate PF=1.18 but invalid as decision evidence because stability verdict is `N_windows<2`. | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: 730d WFA has sparse active windows with stability `active_windows=0`, `positive_ratio=None`, `verdict=N_windows<2`; no current tier/audit source provides 3 valid folds. | `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json`; tier-master 365d BT EV `—` |
| Bonferroni-adj p | 1.0000 latest gate-progression aggregate; H1 3month shadow p_bonferroni = 1.0. | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| Kelly fraction | 0.0000 latest gate-progression aggregate; raw Kelly = -2.8788. Older shadow deep dive Kelly = -305.5%. | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
