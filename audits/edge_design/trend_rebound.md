---
strategy: trend_rebound
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

強トレンド環境で、トレンド方向と逆側に短期的に行き過ぎた足が反転し始めた瞬間だけ、平均回帰リバウンドを取りに行く戦略。BUY は下降トレンド中の oversold 反転、SELL は上昇トレンド中の overbought 反転として実装されている（`strategies/scalp/trend_rebound.py:1`, `strategies/scalp/trend_rebound.py:44`, `strategies/scalp/trend_rebound.py:67`）。

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | MR/rebound trigger 自体は `BUY: stoch_k < 12 ∧ rsi5 < 28 ∧ bbpb < 0.12 ∧ entry > open ∧ ema9 < ema21`、`SELL: stoch_k > 88 ∧ rsi5 > 72 ∧ bbpb > 0.88 ∧ entry < open ∧ ema9 > ema21` で思想を捕捉している（`strategies/scalp/trend_rebound.py:45`, `strategies/scalp/trend_rebound.py:68`）。ただし「モメンタム中立」と表示する条件が BUY では `_momentum < 8`、SELL では `_momentum > -8` の片側制約で、BUY の急落継続 `_momentum << 0` と SELL の急騰継続 `_momentum >> 0` を許すため、リバウンド開始の数学的捕捉として破綻している（`strategies/scalp/trend_rebound.py:39`, `strategies/scalp/trend_rebound.py:50`, `strategies/scalp/trend_rebound.py:55`, `strategies/scalp/trend_rebound.py:73`, `strategies/scalp/trend_rebound.py:78`）。 |
| 3 (timing window) | OK | `df.iloc[-2]` と `df["Close"].iloc[-10]` だけを参照し、未来足参照はこのファイル内にはない（`strategies/scalp/trend_rebound.py:37`, `strategies/scalp/trend_rebound.py:42`）。entry は反転足の `entry > open_price` / `entry < open_price` 確認後に同じ評価で返すため、bar-close 確定運用なら OK。ただし strategy 内に `bar_time` dedup は無く、同一bar多重 entry 防止は外部責務である（`strategies/scalp/trend_rebound.py:48`, `strategies/scalp/trend_rebound.py:71`, `strategies/scalp/trend_rebound.py:94`）。 |
| 4 (filter coherence) | BREAKS | ADX gate は強トレンド内リバウンド思想を強化する（`strategies/scalp/trend_rebound.py:13`, `strategies/scalp/trend_rebound.py:26`）。EMA9/EMA21 gate も、通常の MR に MA filter を掛ける罠とは異なり、この戦略では「下降/上昇トレンド中」を定義するため STRENGTHENS（`strategies/scalp/trend_rebound.py:49`, `strategies/scalp/trend_rebound.py:72`）。MACD-H/Stoch 追加加点は反転確認なので STRENGTHENS（`strategies/scalp/trend_rebound.py:56`, `strategies/scalp/trend_rebound.py:59`, `strategies/scalp/trend_rebound.py:79`, `strategies/scalp/trend_rebound.py:82`）。一方で momentum gate は Axis 2 の通り片側制約で、tail 継続を除外できず BREAKS（`strategies/scalp/trend_rebound.py:50`, `strategies/scalp/trend_rebound.py:73`）。HMM regime gate はこの戦略ファイル内には無い。 |
| 5 (stop/TP geometry) | MISALIGNED | SL は常に 1.0 ATR、TP は score により 1.0 ATR または 1.5 ATR で、R:R は 1:1 または 1:1.5（`strategies/scalp/trend_rebound.py:21`, `strategies/scalp/trend_rebound.py:22`, `strategies/scalp/trend_rebound.py:23`, `strategies/scalp/trend_rebound.py:64`, `strategies/scalp/trend_rebound.py:65`, `strategies/scalp/trend_rebound.py:87`, `strategies/scalp/trend_rebound.py:88`）。強トレンド内の counter-trend MR は mean 到達前のノイズで切られやすいため、固定 1ATR stop は浅く、MR=wide stop の基準に不整合。 |
| 6 (pair-regime fit) | FORCED | Strategy は `ALL` 扱いで、ファイル内に `ctx.symbol` / `ctx.is_jpy` / pair-specific volatility gate が無い。既存R2 evidenceでは EUR_USD は弱い正、USD_JPY は負、GBP_USD は force-demoted safety net のみで、全ペア一律適用は forced。<br><br>\| Pair \| Fit \| Evidence \|<br>\|---\|---\|---\|<br>\| EUR_USD \| FIT \| N=8, WR=37.50%, PF=1.149, Kelly=+0.0487; ただし N が小さいため FIT は暫定 \|<br>\| USD_JPY \| FORCED \| N=8, WR=37.50%, PF=0.697, Kelly=-0.1630, STOP_OANDA \|<br>\| GBP_USD \| FORCED \| force_demoted_safety_net only; robust PF/Wilson/Kelly not found \| |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | Existing R2 audit has pair-level N/WR/Wilson/PF/Bonferroni/Kelly for EUR_USD and USD_JPY, but tier-master 365d BT EV is `—`, ALL aggregate PF is not available, and WF folds ≥3 are not available. N/WR/EV alone would be a partial-quant trap, so this axis cannot validate resurrection without a proper non-BT-existing evidence row or future BT. |

## Axis 8: failure mode 診断

`trend_rebound` is Tier 3 (FORCE_DEMOTED), so failure diagnosis is required. The thesis is valid enough to audit: strong-trend pullback/rebound is explicit in code and the trigger includes oversold/overbought plus reversal candle confirmation. The design break is concentrated in Axis 2 and Axis 5, with Axis 6 adding deployment risk.

破綻点は `momentum_limit` の符号設計である。現在の BUY 条件 `_momentum < +8` は「急落しすぎていない」ではなく「強い上昇ではない」だけを見ており、下降トレンド中にさらに強く落ちている足を許す。SELL 条件 `_momentum > -8` も同様に、上昇トレンド中にさらに強く上がっている足を許す。再設計案は、BUY を `-momentum_limit <= _momentum <= 0` または `_momentum > -momentum_limit` かつ `macdh > macdh_prev` 必須、SELL を `0 <= _momentum <= momentum_limit` または `_momentum < momentum_limit` かつ `macdh < macdh_prev` 必須に変更し、リバウンド開始前の tail continuation を落とすこと。

Stop/TP は、1ATR固定stopをやめ、MR用に `sl = entry ± 1.5-2.0 * atr7`、TP は固定ATRではなく `bb_mid` / EMA9 / 直近小反発到達点に寄せる。これにより、強トレンド内の反発が平均近傍に戻る前に浅いstopで刈られる構造を緩和する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

修正優先は trigger の `momentum_limit` 条件である。BUY は oversold 条件を維持しつつ、10バーmomentumが過度な下降継続ではないことを両側または逆側下限で確認する。SELL も同様に、過度な上昇継続を除外する。加点扱いの MACD-H/Stoch 反転は、score bonus ではなく最小限の必須反転確認に昇格させる候補がある。

次に stop/TP geometry を MR 型に寄せる。現在の `sl_mult = 1.0` は浅く、強トレンド内の逆張りには不利なので 1.5-2.0ATR へ広げ、TP は 1.0/1.5ATR 固定ではなく BB middle / EMA9 / short mean target へ置換する。USD_JPY は既存 evidence が負なので、再設計BTなしに `ALL` 復帰させず、まず EUR_USD 限定 Shadow または pair gate 付きで検証する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | EUR_USD: 8; USD_JPY: 8; ALL aggregate: `INSUFFICIENT_EVIDENCE` | existing R2 audit output (`knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:48`, `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:58`) |
| Win rate | EUR_USD: 37.50%; USD_JPY: 37.50% | existing R2 audit output (`knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:48`, `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:58`) |
| Wilson lo (95%) | EUR_USD: 13.68%; USD_JPY: 13.68% | existing R2 audit output (`knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:48`, `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:58`) |
| PF | EUR_USD: 1.149; USD_JPY: 0.697; tier-master 365d BT EV: `—` | existing R2 audit output + tier-master prompt input |
| WF folds (3+) | `INSUFFICIENT_EVIDENCE` — no ≥3 fold WF metric found; only older pre/post split was found for L2 trend_rebound | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md:425`, `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md:427` |
| Bonferroni-adj p | EUR_USD: 1.0000; USD_JPY: 1.0000 | existing R2 audit output (`knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:48`, `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:58`) |
| Kelly fraction | EUR_USD: +0.0487; USD_JPY: -0.1630 | existing R2 audit output (`knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:48`, `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md:58`) |
