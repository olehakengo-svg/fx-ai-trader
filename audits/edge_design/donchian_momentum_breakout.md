---
strategy: donchian_momentum_breakout
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

48本 Donchian channel の上限/下限を bar close で明確に突破し、DI/ADX/MACD-H と HTF 非逆行で momentum continuation を確認して、多日レンジの壁突破後の stop cascade / trend continuation を取る breakout thesis。コード上も 48本レンジ、fresh breakout、実体比率、DI/ADX/MACD-H、HTF filter を entry logic として明示している。`strategies/hourly/donchian_momentum_breakout.py:10`, `strategies/hourly/donchian_momentum_breakout.py:11`, `strategies/hourly/donchian_momentum_breakout.py:12`, `strategies/hourly/donchian_momentum_breakout.py:20`, `strategies/hourly/donchian_momentum_breakout.py:25`, `strategies/hourly/donchian_momentum_breakout.py:30`, `strategies/hourly/donchian_momentum_breakout.py:31`, `strategies/hourly/donchian_momentum_breakout.py:32`, `strategies/hourly/donchian_momentum_breakout.py:34`, `strategies/hourly/donchian_momentum_breakout.py:35`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum breakout thesis に対して、entry trigger は `DonRange48[-2] >= ATR * 1.5 ∧ (Close > DonHigh48[-2] OR Close < DonLow48[-2]) ∧ previous close not already broken ∧ body/range >= 0.40 ∧ candle direction agrees ∧ DI direction agrees ∧ (ADX >= threshold OR ADX rise >= 2.0) ∧ MACD-H direction agrees`。MR 用の RSI/BB/z-score oversold trigger ではなく、range wall の close breakout と trend/momentum confirmation を捕捉しているため整合する。`strategies/hourly/donchian_momentum_breakout.py:58`, `strategies/hourly/donchian_momentum_breakout.py:61`, `strategies/hourly/donchian_momentum_breakout.py:67`, `strategies/hourly/donchian_momentum_breakout.py:105`, `strategies/hourly/donchian_momentum_breakout.py:106`, `strategies/hourly/donchian_momentum_breakout.py:110`, `strategies/hourly/donchian_momentum_breakout.py:116`, `strategies/hourly/donchian_momentum_breakout.py:119`, `strategies/hourly/donchian_momentum_breakout.py:120`, `strategies/hourly/donchian_momentum_breakout.py:132`, `strategies/hourly/donchian_momentum_breakout.py:134`, `strategies/hourly/donchian_momentum_breakout.py:157`, `strategies/hourly/donchian_momentum_breakout.py:161`, `strategies/hourly/donchian_momentum_breakout.py:163`, `strategies/hourly/donchian_momentum_breakout.py:169`, `strategies/hourly/donchian_momentum_breakout.py:171`, `strategies/hourly/donchian_momentum_breakout.py:180`, `strategies/hourly/donchian_momentum_breakout.py:182`, `strategies/hourly/donchian_momentum_breakout.py:188`, `strategies/hourly/donchian_momentum_breakout.py:190` |
| 3 (timing window) | LOOKAHEAD | Donchian threshold 自体は前足値 `iloc[-2]` を使うため channel 計算の直接 look-ahead は避けている。一方、signal は `ctx.entry` と current bar `df.iloc[-1]` の High/Low/Open から body ratio と足色を同時判定して返すため、実行層が形成中 1H bar を渡す場合は intrabar high/low/body を見た entry になる。strategy 内に `(pair, bar_time, direction)` の per-bar dedup state もなく、同一 bar 再評価で同じ Candidate を返し得るため、bar-close 契約が外部依存になっている。`strategies/hourly/donchian_momentum_breakout.py:104`, `strategies/hourly/donchian_momentum_breakout.py:105`, `strategies/hourly/donchian_momentum_breakout.py:106`, `strategies/hourly/donchian_momentum_breakout.py:116`, `strategies/hourly/donchian_momentum_breakout.py:117`, `strategies/hourly/donchian_momentum_breakout.py:153`, `strategies/hourly/donchian_momentum_breakout.py:154`, `strategies/hourly/donchian_momentum_breakout.py:155`, `strategies/hourly/donchian_momentum_breakout.py:157`, `strategies/hourly/donchian_momentum_breakout.py:320` |
| 4 (filter coherence) | STRENGTHENS | Range width filter は十分な wall / noise exclusion を要求するため STRENGTHENS。fresh breakout check、body ratio、direction candle、DI、ADX/ADX rise、MACD-H は breakout momentum を強化する。USDJPY SELL の ADX>=25 と D1 EMA50 falling は funding/macro 逆行 short を絞る pair-specific filter として STRENGTHENS だが、やや過密。HTF agreement hard filter は逆 HTF continuation を避けるため STRENGTHENS/NEUTRAL。MR 戦略に MA filter を被せる `feedback_ma_filter_breaks_mr.md` 型ではなく、HMM regime gate が tail を消す `feedback_hmm_gate_same_trap.md` 型の generic regime gate もない。`strategies/hourly/donchian_momentum_breakout.py:110`, `strategies/hourly/donchian_momentum_breakout.py:127`, `strategies/hourly/donchian_momentum_breakout.py:132`, `strategies/hourly/donchian_momentum_breakout.py:134`, `strategies/hourly/donchian_momentum_breakout.py:141`, `strategies/hourly/donchian_momentum_breakout.py:143`, `strategies/hourly/donchian_momentum_breakout.py:147`, `strategies/hourly/donchian_momentum_breakout.py:157`, `strategies/hourly/donchian_momentum_breakout.py:161`, `strategies/hourly/donchian_momentum_breakout.py:163`, `strategies/hourly/donchian_momentum_breakout.py:169`, `strategies/hourly/donchian_momentum_breakout.py:171`, `strategies/hourly/donchian_momentum_breakout.py:182`, `strategies/hourly/donchian_momentum_breakout.py:188`, `strategies/hourly/donchian_momentum_breakout.py:190`, `strategies/hourly/donchian_momentum_breakout.py:196`, `strategies/hourly/donchian_momentum_breakout.py:198`, `strategies/hourly/donchian_momentum_breakout.py:200` |
| 5 (stop/TP geometry) | MISALIGNED | Initial SL は Donchian mid ± 0.3ATR を ATR*1.5 cap で丸め、TP は `max(ATR*3.0, SL_dist*1.5)` なので minimum RR は 1.5。breakout thesis には asymm / trailing が必要だが、実際の `Candidate` は fixed `sl` / fixed `tp` だけを返し、class attr の BE/trailing parameters は exit object に渡されない。コメントは BE/trailing を掲げるが、entry output geometry は fixed TP で右尾 continuation を伸ばしにくい。`strategies/hourly/donchian_momentum_breakout.py:70`, `strategies/hourly/donchian_momentum_breakout.py:71`, `strategies/hourly/donchian_momentum_breakout.py:72`, `strategies/hourly/donchian_momentum_breakout.py:73`, `strategies/hourly/donchian_momentum_breakout.py:76`, `strategies/hourly/donchian_momentum_breakout.py:77`, `strategies/hourly/donchian_momentum_breakout.py:210`, `strategies/hourly/donchian_momentum_breakout.py:212`, `strategies/hourly/donchian_momentum_breakout.py:214`, `strategies/hourly/donchian_momentum_breakout.py:215`, `strategies/hourly/donchian_momentum_breakout.py:217`, `strategies/hourly/donchian_momentum_breakout.py:218`, `strategies/hourly/donchian_momentum_breakout.py:221`, `strategies/hourly/donchian_momentum_breakout.py:222`, `strategies/hourly/donchian_momentum_breakout.py:223`, `strategies/hourly/donchian_momentum_breakout.py:224`, `strategies/hourly/donchian_momentum_breakout.py:226`, `strategies/hourly/donchian_momentum_breakout.py:229`, `strategies/hourly/donchian_momentum_breakout.py:232`, `strategies/hourly/donchian_momentum_breakout.py:320`, `strategies/hourly/donchian_momentum_breakout.py:321` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。コードコメントは USDJPY 優位性を強く仮定する一方、実装は `ctx.is_jpy` と non-JPY の二分で TP/ADX を選ぶだけで、EURUSD/GBPUSD/JPY cross 別の channel width、session、spread、macro asymmetry を設計していない。ALL cell としては pair-specific evidence / parameters が不足する。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / NEGATIVE SMALL-N | tier-master の force_demoted 行は 365d BT EV が全ペア `—`。gate-progression audit には strategy aggregate `N=6`, `WR=33.33%`, `Wilson lo=9.68%`, `EV=-8.63p`, `PF=0.257`, `Kelly=0.0000`, `raw Kelly=-0.9646`, `Bonferroni p=1.0000` があるが、N が小さく Bonferroni 不通過で、WF folds>=3 も確認できない。local `demo_trades.db` の exact `demo_trades` / `evaluated_candidates` / `oanda_audit` では該当行 0 件。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可であり、既存値は negative かつ decision-grade 不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT | コードコメントは USDJPY が日米金利差やマクロ要因で数日 trend を作りやすく、48期間レンジ壁に stop が集中しやすいと明示する。JPY SELL には ADX と D1 EMA50 falling の追加制約もある。`strategies/hourly/donchian_momentum_breakout.py:14`, `strategies/hourly/donchian_momentum_breakout.py:15`, `strategies/hourly/donchian_momentum_breakout.py:16`, `strategies/hourly/donchian_momentum_breakout.py:141`, `strategies/hourly/donchian_momentum_breakout.py:143`, `strategies/hourly/donchian_momentum_breakout.py:147` |
| EURUSD | FORCED | non-JPY branch は ADX/TP multiplier を EUR として扱うだけで、EURUSD 固有の breakout session / volatility / spread / macro regime は未分離。`strategies/hourly/donchian_momentum_breakout.py:97`, `strategies/hourly/donchian_momentum_breakout.py:98`, `strategies/hourly/donchian_momentum_breakout.py:99` |
| GBPUSD | FORCED | ALL scope だが GBPUSD 固有分岐は存在せず、non-JPY は EUR parameter を流用するため pair thesis が未設計。`strategies/hourly/donchian_momentum_breakout.py:65`, `strategies/hourly/donchian_momentum_breakout.py:72`, `strategies/hourly/donchian_momentum_breakout.py:97`, `strategies/hourly/donchian_momentum_breakout.py:98`, `strategies/hourly/donchian_momentum_breakout.py:99` |
| EURJPY / GBPJPY | FORCED | `ctx.is_jpy` により USDJPY と同じ JPY branch へ入るが、cross-JPY 固有の volatility / spread / risk-on/off behavior は未分離。USDJPY 優位性コメントを JPY cross へそのまま拡張する根拠はコードからは出ない。`strategies/hourly/donchian_momentum_breakout.py:14`, `strategies/hourly/donchian_momentum_breakout.py:15`, `strategies/hourly/donchian_momentum_breakout.py:94`, `strategies/hourly/donchian_momentum_breakout.py:95`, `strategies/hourly/donchian_momentum_breakout.py:96` |
| Other ALL pairs | FORCED | pair-specific branch / evidence がなく、ALL cell としては forced deployment。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) のため failure mode を診断する。思想と core trigger は momentum breakout として有効に articulation でき、Axis 2 は PASS、Axis 4 も概ね STRENGTHENS で、思想自体は否定できない。破綻候補は Axis 3 と Axis 5、補助的に Axis 6。現在の signal は current bar の High/Low/Open/Close 相当を使う一方で strategy 内に bar-close / per-bar dedup 契約がなく、実行層次第で intrabar 判定または同一 bar 多重 candidate になる。さらに出口は breakout 右尾を伸ばす trailing/BE を `Candidate` に表現せず、fixed TP/SL で閉じているため、多日レンジ突破の continuation thesis と geometry がずれている。

再設計案は、trigger の骨格を残して timing と exit を v2 化すること。Trigger は `last_closed_close > prev_don_high + buffer` / `< prev_don_low - buffer` の bar-close only に固定し、`buffer = max(spread, 0.05-0.10ATR)` を加える。strategy または execution side に `(instrument, hourly_bar_time, direction, entry_type)` の dedup key を置き、同一 1H bar で Candidate を複数回生成しない。

Exit は fixed `TP=max(ATR*3, 1.5R)` 単独をやめ、initial SL を breakout invalidation point に置いたうえで、1R または TP50% 到達で BE、以後 `highest/lowest close since entry -/+ ATR*1.0-1.5` の trailing を実行層へ明示する。ALL cell のまま復帰させるのではなく、まず USDJPY-only cell と non-JPY/cross-JPY cell を分離し、pair別 365d + WF folds>=3 の Wilson/PF/Bonferroni/Kelly を出してから拡張する。本監査では新規 BT は実行しない。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は明確で、Donchian breakout trigger も thesis を捕捉しているため `THESIS_INVALID` ではない。ただし修正は一行削除ではなく、bar-close / dedup の timing 契約、fixed TP から trailing/BE への exit geometry、ALL scope から pair-specific cell への分離が必要である。

コードレベルの想定は、`_close = ctx.entry` と current bar body 判定を「確定済み bar の close」として明示できる context field に寄せ、`_is_buy = close_closed > _prev_don_high + buffer` の形にすること。fresh breakout check は現在の previous close 判定に加えて bar/session dedup を持たせる。

SL/TP は `Candidate` が fixed `sl` / `tp` しか持てないなら、まず TP を控えめな management target として扱い、別の exit manager に BE/trailing metadata を渡す実装が必要になる。採用前に必要な検証は、USDJPY-only と non-JPY/cross-JPY split の 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact に出すこと。N/WR/EV だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 6 strategy aggregate; local exact DB rows 0 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; local `demo_trades.db` query across `demo_trades`, `evaluated_candidates`, `oanda_audit` |
| Win rate | 33.33% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Wilson lo (95%) | 9.68% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| PF | 0.257 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; tier-master 365d BT EV is `—` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no WF folds>=3 found in tier-master / current audit DB for this strategy | `knowledge-base/wiki/tier-master.md`; local artifact search |
| Bonferroni-adj p | 1.0000 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Kelly fraction | 0.0000 clipped; raw Kelly -0.9646 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
