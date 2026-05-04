---
strategy: post_news_vol
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

重要指標後の異常ボラ足で stop hunt / liquidity vacuum が発生し、その後は異常足の実体方向へフォロースルーが続く、という news-volatility momentum continuation thesis。コードは異常足の TR・ヒゲ/実体、1本待機後の同方向 close continuation、spike extreme SL と range/ATR TP を明示している。`strategies/daytrade/post_news_vol.py:10`, `strategies/daytrade/post_news_vol.py:13`, `strategies/daytrade/post_news_vol.py:14`, `strategies/daytrade/post_news_vol.py:16`, `strategies/daytrade/post_news_vol.py:23`, `strategies/daytrade/post_news_vol.py:29`, `strategies/daytrade/post_news_vol.py:30`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Momentum continuation 部分は `TR >= ATR*2.0 ∧ wick_sum/range >= 0.30` または `TR >= ATR*1.8 ∧ body/range >= 0.70` の spike 検出後、`body/range >= 0.35 ∧ close` が spike close を同方向に超過、で捕捉できている。一方で thesis の `post_news` 部分に対する event proximity / economic calendar / news timestamp 条件がなく、実装コメントも「15m足のみではニューススパイクとランダムボラの区別不可」と明記するため、`news_event_window ∧ volatility_spike ∧ follow_through` ではなく `volatility_spike ∧ follow_through` になっている。`strategies/daytrade/post_news_vol.py:41`, `strategies/daytrade/post_news_vol.py:51`, `strategies/daytrade/post_news_vol.py:52`, `strategies/daytrade/post_news_vol.py:53`, `strategies/daytrade/post_news_vol.py:54`, `strategies/daytrade/post_news_vol.py:131`, `strategies/daytrade/post_news_vol.py:135`, `strategies/daytrade/post_news_vol.py:179`, `strategies/daytrade/post_news_vol.py:185`, `strategies/daytrade/post_news_vol.py:189`, `strategies/daytrade/post_news_vol.py:193`, `strategies/daytrade/post_news_vol.py:197` |
| 3 (timing window) | LOOKAHEAD | Spike scan は `range(max(0, cur_idx - SPIKE_LOOKBACK), cur_idx)` で現在足を spike 候補から除外するが、follow-through 判定は `cur_idx = len(ctx.df)-1` の current bar の Open/High/Low/Close を直接使う。strategy 内に closed-bar 契約、signal bar と execution bar の分離、または `(symbol, strategy, bar_id)` dedup がないため、実行層が形成中 bar を渡すと intrabar body/close 条件で発火し、同一 bar 再評価で多重 Candidate も返し得る。`strategies/daytrade/post_news_vol.py:111`, `strategies/daytrade/post_news_vol.py:156`, `strategies/daytrade/post_news_vol.py:171`, `strategies/daytrade/post_news_vol.py:172`, `strategies/daytrade/post_news_vol.py:173`, `strategies/daytrade/post_news_vol.py:174`, `strategies/daytrade/post_news_vol.py:225`, `strategies/daytrade/post_news_vol.py:240`, `strategies/daytrade/post_news_vol.py:311` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL / BREAKS | Pair filter は USDJPY/EURUSD/GBPUSD/EURGBP/XAUUSD に限定し、news-vol thesis と概ね STRENGTHENS。時間帯 filter は主要指標が多い UTC 6-21 を許可し、Friday late block は NEUTRAL。ADX lower bound は低ボラ noise を避けるため STRENGTHENS だが、`ADX_MAX = 50` は post-news tail の極端ボラ局面を切り得るため BREAKS 寄り。これは MR に MA filter を被せる `feedback_ma_filter_breaks_mr.md` 型ほど thesis 逆行ではないが、edge が regime tail に依存するのに gate が tail を落とす `feedback_hmm_gate_same_trap.md` 型のリスクに近い。`strategies/daytrade/post_news_vol.py:67`, `strategies/daytrade/post_news_vol.py:68`, `strategies/daytrade/post_news_vol.py:69`, `strategies/daytrade/post_news_vol.py:77`, `strategies/daytrade/post_news_vol.py:78`, `strategies/daytrade/post_news_vol.py:79`, `strategies/daytrade/post_news_vol.py:80`, `strategies/daytrade/post_news_vol.py:82`, `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84`, `strategies/daytrade/post_news_vol.py:216`, `strategies/daytrade/post_news_vol.py:218`, `strategies/daytrade/post_news_vol.py:222` |
| 5 (stop/TP geometry) | MISALIGNED | SL は spike extreme ± `ATR*0.3` で thesis の stop-hunt invalidation point を使うため妥当。一方 TP は `max(spike_range*0.8, ATR*2.5)` に固定され、最低 R:R が 1.5 未満なら TP を広げるだけで trailing/partial/BE はない。post-news liquidity vacuum の右尾 continuation を取る設計としては fixed TP が早利確になりやすく、momentum / breakout 系の asymm/trailing geometry に不足する。`strategies/daytrade/post_news_vol.py:71`, `strategies/daytrade/post_news_vol.py:72`, `strategies/daytrade/post_news_vol.py:73`, `strategies/daytrade/post_news_vol.py:74`, `strategies/daytrade/post_news_vol.py:75`, `strategies/daytrade/post_news_vol.py:257`, `strategies/daytrade/post_news_vol.py:259`, `strategies/daytrade/post_news_vol.py:261`, `strategies/daytrade/post_news_vol.py:263`, `strategies/daytrade/post_news_vol.py:264`, `strategies/daytrade/post_news_vol.py:265`, `strategies/daytrade/post_news_vol.py:266`, `strategies/daytrade/post_news_vol.py:275`, `strategies/daytrade/post_news_vol.py:276`, `strategies/daytrade/post_news_vol.py:277` |
| 6 (pair-regime fit) | FIT / FORCED | 実装上の allowed universe は USDJPY/EURUSD/GBPUSD/EURGBP/XAUUSD。USDJPY/EURUSD/GBPUSD は主要指標と流動性急変の thesis fit があるが、USDJPY は既存 divergence / pair demotion evidence が強く mixed。EURGBP は news impulse が相対的に弱く forced 寄り。XAUUSD は event volatility fit はあるが tier-master の FX EV 三列とは別で、decision-grade evidence 不足。下の pair table 参照。`strategies/daytrade/post_news_vol.py:82`, `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84`, `strategies/daytrade/post_news_vol.py:87`, `strategies/daytrade/post_news_vol.py:88`, `strategies/daytrade/post_news_vol.py:89`, `strategies/daytrade/post_news_vol.py:90`, `strategies/daytrade/post_news_vol.py:207`, `strategies/daytrade/post_news_vol.py:208` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / MIXED | Existing audit DB aggregate has N=4, WR=50.00%, Wilson lo=15.00%, PF=2.317, Kelly=0.2842, Bonferroni p=1.0000. This fills PF/Kelly/Wilson but fails `feedback_partial_quant_trap.md` decision standard because N is tiny, Bonferroni does not pass, and ALL-level WF folds>=3 are not available. Tier-master has positive 365d EV for JPY/EUR/GBP in the repo, while the prompt-supplied ALL row is `—`; pair-level WF artifacts show EURUSD/GBPUSD can be stable on W90 but USDJPY is unstable/mixed, so strategy-level ALL promotion evidence remains insufficient. |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED / mixed | Code allowed。tier-master 365d EV is positive in repo, but USDJPY also appears as PAIR_DEMOTED and prior divergence scans show live degradation / small-N uncertainty. `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84` |
| EURUSD | FIT | Code allowed。Major macro-news pair; repo tier-master records positive 365d EUR EV, and W90 walkforward artifact reports 3 folds / 100% positive folds, but current ALL audit DB N remains too small. `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84` |
| GBPUSD | FIT / session-sensitive | Code allowed。Repo tier-master records positive 365d GBP EV and W90 walkforward artifact reports 3 folds / 100% positive folds, but h1-hour cell evidence is mixed and N is small. `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84` |
| EURGBP | FORCED | Code allowed, but no pair-specific news-vol evidence was found in tier-master EV columns or current audit DB; cross pair may underreact relative to USD majors. `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84` |
| XAUUSD | FIT / under-evidenced | Code normalizes GC/GCF to XAUUSD and allows XAUUSD, which fits event volatility, but tier-master FX EV columns do not provide XAU decision-grade metrics. `strategies/daytrade/post_news_vol.py:83`, `strategies/daytrade/post_news_vol.py:84`, `strategies/daytrade/post_news_vol.py:89`, `strategies/daytrade/post_news_vol.py:90` |
| Other ALL pairs | FORCED / blocked | Strategy returns None outside `ALLOWED_PAIRS`; ALL deployment is therefore not truly universal, and non-allowed pairs have no designed fit. `strategies/daytrade/post_news_vol.py:207`, `strategies/daytrade/post_news_vol.py:208`, `strategies/daytrade/post_news_vol.py:209` |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) としての破綻軸は Axis 2 / 3 / 5、補助的に Axis 4。思想はコードから明確に導出でき、post-news volatility continuation 自体は tier-master / WF の一部で支持されるが、現行 trigger は「news後」ではなく「任意のATR spike後」を拾う。さらに current bar の follow-through を直接読むため bar-close / next-bar execution / dedup 契約が弱く、出口は fixed TP で post-news run の右尾を伸ばせない。

再設計案は v2 を event-window + closed-bar continuation + trailing geometry に分離すること。具体的には `event_window = high_impact_calendar_event within [-5m,+45m]` を spike trigger の必須条件にし、signal は `df.iloc[-2]` の確定 follow bar で `close[-2] > spike_close + buffer` / `< spike_close - buffer` を判定、execution は次 bar の `ctx.entry` に分離する。ADX は `ADX_MIN` のみ残すか `ADX_MAX` を削除し、tail を落とす gate を避ける。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想は明確で、volatility spike + follow-through という trigger 骨格も momentum continuation を捕捉している。ただし `post_news` の中核条件が実装されていないため、最優先修正は trigger の event-window 化である。`_find_spike_bars()` の前段または `evaluate()` 冒頭に high-impact economic calendar gate を追加し、calendar がない場合は `post_news_vol` ではなく `generic_vol_spike_followthrough` として別戦略に分離するのが筋が良い。

Timing は closed-bar 化する。`cur_idx = len(ctx.df)-1` の現在足 follow-through 判定をやめ、`signal_idx = len(ctx.df)-2` の確定足で body ratio / close continuation を判定し、Candidate は次足 execution 前提で返す。併せて `(symbol, self.name, spike_idx, signal_idx, signal)` の dedup key を strategy または dispatch 層に置き、同一 bar の再 emit を防ぐ。

Stop/TP は spike extreme SL を維持しつつ、fixed TP を management target に格下げし、1R 到達で BE、以後 `highest_close_since_entry - ATR*1.0-1.5` / `lowest_close_since_entry + ATR*1.0-1.5` の trailing を exit manager へ渡す設計に変更する。採用前には event-window 版を新規BTとしてではなく Wave 4 の別検証タスクで、pair別 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction まで同一 artifact に出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 4 strategy aggregate; prompt tier-master ALL row has no ALL aggregate EV; repo tier-master 365d scan lists total N=64 for JPY/EUR/GBP scan. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; prompt input; `knowledge-base/raw/bt-results/bt-365d-scan-2026-04-16.md` |
| Win rate | 50.00% strategy aggregate; historical L3 snapshot N=7 WR=57.1% is older and small-N. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Wilson lo (95%) | 15.00% strategy aggregate; 4/30 shadow-only N=7 Wilson95=15.8%; cell-level evidence remains below promotion threshold. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/shadow-audit-2026-04-30.md` |
| PF | 2.317 strategy aggregate; 4/30 shadow-only PF=7.41 is rejected as single-day / intervention-tail concentration. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/shadow-audit-2026-04-30.md` |
| WF folds (3+) | ALL aggregate: INSUFFICIENT_EVIDENCE. Pair-level artifacts: USDJPY W90 folds=4 positive=0.50 unstable/borderline; EURUSD W90 folds=3 positive=1.00 stable; GBPUSD W90 folds=3 positive=1.00 stable; W60 has incomplete folds for EUR/GBP. | `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md` |
| Bonferroni-adj p | 1.0000 strategy aggregate; prior divergence scans have unadjusted p evidence for degradation in USDJPY, but no ALL-level Bonferroni pass. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/bt-live-divergence-scan-2026-04-22.md` |
| Kelly fraction | 0.2842 strategy aggregate; older L3 snapshot Kelly=26.9%; both are small-N and fail decision-grade promotion standard without Wilson/WF/Bonferroni support. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
