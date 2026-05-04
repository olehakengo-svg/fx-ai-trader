---
strategy: london_shrapnel
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

London/NY overlap の高流動性時間帯に発生した ATR 比で大きいヒゲを stop-hunt / false breakout と見なし、ヒゲ先端を再突破するまでは反対方向への短期平均回帰を取りに行く MR scalp。コード上も「異常ヒゲ」「ストップハント＝偽ブレイクアウト」「ヒゲの反対方向へ即座に逆張り」を明示している。`strategies/scalp/london_shrapnel.py:2`, `strategies/scalp/london_shrapnel.py:5`, `strategies/scalp/london_shrapnel.py:6`, `strategies/scalp/london_shrapnel.py:21`, `strategies/scalp/london_shrapnel.py:22`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | MR の oversold/overbought proxy は入っているが、stop-hunt / false breakout thesis の中核である「どの liquidity level を sweep したか」が条件にない。BUY は `_lower_wick >= 1.5ATR AND lower_wick/body >= 3.0 AND close>open AND close>BB_lower AND RSI5<40`、SELL は対称条件で、巨大ヒゲと RSI 極値は捕捉する。一方、false breakout なら少なくとも `low < prior_low/session_low/BB_lower AND close reclaim` / `high > prior_high/session_high/BB_upper AND close reclaim` が必要だが、現行は BUY で `_low < ctx.bb_lower` すら要求せず、`ctx.entry > ctx.bb_lower` だけで「BBロワー突破からの回帰」と解釈している。`strategies/scalp/london_shrapnel.py:15`, `strategies/scalp/london_shrapnel.py:16`, `strategies/scalp/london_shrapnel.py:17`, `strategies/scalp/london_shrapnel.py:18`, `strategies/scalp/london_shrapnel.py:82`, `strategies/scalp/london_shrapnel.py:83`, `strategies/scalp/london_shrapnel.py:84`, `strategies/scalp/london_shrapnel.py:85`, `strategies/scalp/london_shrapnel.py:86`, `strategies/scalp/london_shrapnel.py:87`, `strategies/scalp/london_shrapnel.py:100`, `strategies/scalp/london_shrapnel.py:101`, `strategies/scalp/london_shrapnel.py:102`, `strategies/scalp/london_shrapnel.py:103`, `strategies/scalp/london_shrapnel.py:104`, `strategies/scalp/london_shrapnel.py:105` |
| 3 (timing window) | LOOKAHEAD | `_high/_low` は `ctx.df["High"].iloc[-1]` / `ctx.df["Low"].iloc[-1]` と current row を使い、同じ current bar の `ctx.entry` / `ctx.open_price` で body と反転足色を判定して即 Candidate を返す。呼び出し側が closed-bar dataframe を保証しない live/scalp 評価では、未確定足の High/Low と close 相当値で signal が変わり得る。strategy 内に `(symbol, bar_time, signal)` dedup もなく、同一 bar 多重 entry 抑止は外部依存。`strategies/scalp/london_shrapnel.py:61`, `strategies/scalp/london_shrapnel.py:64`, `strategies/scalp/london_shrapnel.py:65`, `strategies/scalp/london_shrapnel.py:67`, `strategies/scalp/london_shrapnel.py:68`, `strategies/scalp/london_shrapnel.py:69`, `strategies/scalp/london_shrapnel.py:70`, `strategies/scalp/london_shrapnel.py:72`, `strategies/scalp/london_shrapnel.py:73`, `strategies/scalp/london_shrapnel.py:85`, `strategies/scalp/london_shrapnel.py:103`, `strategies/scalp/london_shrapnel.py:151` |
| 4 (filter coherence) | STRENGTHENS | Pair gate は EURUSD/GBPUSD に限定し、London/NY overlap の流動性 thesis と整合する。UTC 12-17 gate も thesis を直接強化する。`ctx.atr7 <= 0` は NEUTRAL な safety guard。score bonus の BB%B extreme、Stoch 反転、MACD-H 反転は MR rejection を補強するため STRENGTHENS。GBP/USD の `ADX>=20` bonus は trend tail を強める可能性があり NEUTRAL 寄りだが、hard gate ではなく score +0.3 に留まるため、MA filter on MR strategy や HMM regime gate same trap のような thesis 破壊 filter とは判定しない。`strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43`, `strategies/scalp/london_shrapnel.py:44`, `strategies/scalp/london_shrapnel.py:45`, `strategies/scalp/london_shrapnel.py:48`, `strategies/scalp/london_shrapnel.py:49`, `strategies/scalp/london_shrapnel.py:50`, `strategies/scalp/london_shrapnel.py:53`, `strategies/scalp/london_shrapnel.py:54`, `strategies/scalp/london_shrapnel.py:57`, `strategies/scalp/london_shrapnel.py:122`, `strategies/scalp/london_shrapnel.py:123`, `strategies/scalp/london_shrapnel.py:126`, `strategies/scalp/london_shrapnel.py:130`, `strategies/scalp/london_shrapnel.py:131`, `strategies/scalp/london_shrapnel.py:133`, `strategies/scalp/london_shrapnel.py:136`, `strategies/scalp/london_shrapnel.py:137`, `strategies/scalp/london_shrapnel.py:140`, `strategies/scalp/london_shrapnel.py:144`, `strategies/scalp/london_shrapnel.py:145` |
| 5 (stop/TP geometry) | MISALIGNED | BUY の reward は固定 `0.8ATR`、risk は概ね `entry - wick_low + 0.2ATR` で、trigger 最小値でも lower wick が `1.5ATR` 以上なので初期 R:R はおおむね `0.8 / 1.7 <= 0.47` 以下に圧縮される。SELL も同型。ヒゲ先端外側 stop は MR thesis と合うが、ヒゲが大きいほど stop 距離だけが拡大し、TP は BB 中央や実際の mean target ではなく固定 ATR のままなので、stop-hunt reversal の geometry としては high-WR 前提に寄りすぎる。`strategies/scalp/london_shrapnel.py:21`, `strategies/scalp/london_shrapnel.py:22`, `strategies/scalp/london_shrapnel.py:35`, `strategies/scalp/london_shrapnel.py:39`, `strategies/scalp/london_shrapnel.py:40`, `strategies/scalp/london_shrapnel.py:80`, `strategies/scalp/london_shrapnel.py:83`, `strategies/scalp/london_shrapnel.py:96`, `strategies/scalp/london_shrapnel.py:97`, `strategies/scalp/london_shrapnel.py:98`, `strategies/scalp/london_shrapnel.py:101`, `strategies/scalp/london_shrapnel.py:114`, `strategies/scalp/london_shrapnel.py:115`, `strategies/scalp/london_shrapnel.py:116` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。コード上の実稼働対象は EURUSD/GBPUSD のみで、`ALL` cell としては非対象 pair が hard-block される。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow / ALL 365d BT EV は `—`。local audit DB (`demo_trades.db`) の `demo_trades` / `evaluated_candidates` / `oanda_audit` は exact `london_shrapnel` 行が 0 件。既存 wiki も BT data not available / live data accumulating としており、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は `feedback_partial_quant_trap.md` 基準で decision-grade に埋められない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EURUSD | FIT / INSUFFICIENT_EVIDENCE | London/NY overlap の流動性最大ペアとしてコードコメントに明示され、pair gate でも許可される。ただし tier-master / audit DB に Wilson/PF/Kelly がない。`strategies/scalp/london_shrapnel.py:7`, `strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43` |
| GBPUSD | FIT / INSUFFICIENT_EVIDENCE | London/NY overlap と GBP volatility bonus の対象で、pair gate でも許可される。ただし `ADX>=20` bonus の妥当性を裏付ける既存統計はない。`strategies/scalp/london_shrapnel.py:7`, `strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43`, `strategies/scalp/london_shrapnel.py:144`, `strategies/scalp/london_shrapnel.py:145` |
| USDJPY | FORCED / BLOCKED | `ALL` input だが code は `_enabled_symbols` 外として `return None`。`strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43`, `strategies/scalp/london_shrapnel.py:49`, `strategies/scalp/london_shrapnel.py:50`, `strategies/scalp/london_shrapnel.py:51` |
| EURJPY | FORCED / BLOCKED | `ALL` input だが code は `_enabled_symbols` 外として `return None`。`strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43`, `strategies/scalp/london_shrapnel.py:49`, `strategies/scalp/london_shrapnel.py:50`, `strategies/scalp/london_shrapnel.py:51` |
| GBPJPY | FORCED / BLOCKED | `ALL` input だが code は `_enabled_symbols` 外として `return None`。`strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43`, `strategies/scalp/london_shrapnel.py:49`, `strategies/scalp/london_shrapnel.py:50`, `strategies/scalp/london_shrapnel.py:51` |
| Other ALL pairs | FORCED / BLOCKED | 実装は EURUSD/GBPUSD 専用で、ALL 配信を正当化する pair-specific evidence はない。`strategies/scalp/london_shrapnel.py:42`, `strategies/scalp/london_shrapnel.py:43`, `strategies/scalp/london_shrapnel.py:49`, `strategies/scalp/london_shrapnel.py:50`, `strategies/scalp/london_shrapnel.py:51` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、phase0_shadow / ALL の tier-master metric は `—`、audit DB 上も発火行 0 件で、既存本番監査では scalp/1h engine NEVER_EVER 群に入っている。したがって metrics 劣化というより、設計検証不能な under-evidenced shadow cell として failure mode を診断する。

破綻軸は Axis 2、Axis 3、Axis 5。Axis 1 の thesis は明確で、Axis 4 の pair/time/oscillator filters も大きくは thesis を壊していない。一方、trigger は「巨大ヒゲ」だけで liquidity level sweep を要求しないため stop-hunt thesis とずれる。timing は current bar の High/Low と `ctx.entry` でヒゲと足色を同時判定し、closed-bar / dedup が strategy 内にない。stop/TP はヒゲが大きいほど risk が拡大するのに TP は固定 `0.8ATR` で、false-break reversal としての expectancy を高 WR に依存させすぎる。

再設計案は、まず trigger を `sweep + reclaim` に変えること。BUY は `_low < min(prev_low, bb_lower) - spread_buffer` かつ `close > min(prev_low, bb_lower)`、SELL は `_high > max(prev_high, bb_upper) + spread_buffer` かつ `close < max(prev_high, bb_upper)` のように、実際に liquidity / band を掃いたことを条件化する。次に signal は確定足で判定し、次足 entry に寄せ、`(symbol, bar_time, direction)` dedup を置く。Stop/TP は wick-tip stop を維持しつつ、TP を BB middle / VWAP / 1R の小さい方または partial TP + BE に変え、巨大ヒゲ時に R:R が一方的に悪化しない geometry を比較する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は捨てない。London/NY overlap の巨大ヒゲを stop-hunt の反転として扱う thesis はコードから明確に読め、EURUSD/GBPUSD という対象 pair も自然。ただし現行の trigger は stop-hunt ではなく generic long-wick reversal に近く、timing と stop/TP も同時に直す必要があるため、単一行修正の S/A ではなく B とする。

コードレベルの想定は、current bar の `_high/_low` と `ctx.entry` で即発火する構造を closed-bar signal に寄せること。`ctx.df.iloc[-2]` を signal bar、`ctx.df.iloc[-3]` 以前を prior liquidity reference とし、BUY なら `signal_low < min(prev_low, bb_lower)` かつ `signal_close > bb_lower`、SELL なら `signal_high > max(prev_high, bb_upper)` かつ `signal_close < bb_upper` のように reclaim を明示する。RSI5 / wick-body ratio は残すが、`ctx.entry > ctx.bb_lower` だけを「BB突破からの回帰」とみなす条件は置換する。

採用前に必要な検証は新規 BT だが、本 audit では実行しない。必要 artifact は EURUSD/GBPUSD 別、365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source で出す audit DB / tier-master 更新である。N/WR/EV だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: `demo_trades.db` exact `london_shrapnel` rows = 0 in `demo_trades`, `evaluated_candidates`, `oanda_audit`; tier-master 365d BT EV = `—` | audit DB search; `knowledge-base/wiki/tier-master.md`; prompt input |
| Win rate | INSUFFICIENT_EVIDENCE: N=0 のため算出不可 | audit DB search |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N=0 のため decision-grade Wilson lower は算出不可 | audit DB search |
| PF | INSUFFICIENT_EVIDENCE: closed trade sample / tier-master PF なし | `knowledge-base/wiki/tier-master.md`; audit DB search |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: existing WF folds>=3 artifact なし | tier-master / audit DB search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: multiple-test adjusted p artifact なし | tier-master / audit DB search |
| Kelly fraction | INSUFFICIENT_EVIDENCE: PF/payoff/WR sample がなく算出不可 | audit DB search |
