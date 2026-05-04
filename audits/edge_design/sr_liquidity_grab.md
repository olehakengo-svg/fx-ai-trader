---
strategy: sr_liquidity_grab
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

15m daytrade の SR level 周辺で、直近 1-2 bar に 2.0 ATR 超の stop-hunt sweep が発生し、価格が level 内側へ戻った後の逆方向継続を取る post-hunt reversal / liquidity grab thesis。5 majors 全走で data 蓄積し、SR 近接・低 ADX・hunt extreme 外側 SL・対側 SR or 1.5R TP で表現されている。`strategies/daytrade/sr_liquidity_grab.py:2`, `strategies/daytrade/sr_liquidity_grab.py:4`, `strategies/daytrade/sr_liquidity_grab.py:19`, `strategies/daytrade/sr_liquidity_grab.py:21`, `strategies/daytrade/sr_liquidity_grab.py:23`, `strategies/daytrade/sr_liquidity_grab.py:24`, `strategies/daytrade/sr_liquidity_grab.py:25`, `strategies/daytrade/sr_liquidity_grab.py:26`, `strategies/daytrade/sr_liquidity_grab.py:28`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | thesis は SR stop-hunt 後の反転なので、trigger は `sym in 5 majors ∧ sr_levels exists ∧ ADX < 30 ∧ min(|entry-level|) <= 0.5ATR ∧ recent hunt exists`。hunt は resistance 側なら `High > level ∧ Close < level ∧ (High-level) > 2.0ATR`、support 側なら `Low < level ∧ Close > level ∧ (level-Low) > 2.0ATR`。entry 方向は resistance hunt 後に `entry < open ∧ entry < level` で SELL、support hunt 後に `entry > open ∧ entry > level` で BUY。stop-hunt + reclaim + reversal body を直接捕捉しており、MR/reversal thesis と数学的には整合する。`strategies/daytrade/sr_liquidity_grab.py:21`, `strategies/daytrade/sr_liquidity_grab.py:35`, `strategies/daytrade/sr_liquidity_grab.py:37`, `strategies/daytrade/sr_liquidity_grab.py:52`, `strategies/daytrade/sr_liquidity_grab.py:55`, `strategies/daytrade/sr_liquidity_grab.py:60`, `strategies/daytrade/sr_liquidity_grab.py:61`, `strategies/daytrade/sr_liquidity_grab.py:66`, `strategies/daytrade/sr_liquidity_grab.py:154`, `strategies/daytrade/sr_liquidity_grab.py:155`, `strategies/daytrade/sr_liquidity_grab.py:158`, `strategies/daytrade/sr_liquidity_grab.py:162`, `strategies/daytrade/sr_liquidity_grab.py:171` |
| 3 (timing window) | LOOKAHEAD | hunt 検出は `df.iloc[-1-i]` で直近過去 bar を見るため hunt 条件自体は current bar を参照しない。一方、entry 反転確認は `ctx.entry` と `ctx.open_price` の current bar 実体で判定され、戦略内に signal bar close 固定、signal timestamp、同一 15m bar dedup がない。実行層が intrabar evaluate すると、同じ bar 内で `entry > open` / `< open` と SR 近接が揺れ、phantom entry や同一 bar 多重 emit に寄る。`strategies/daytrade/sr_liquidity_grab.py:60`, `strategies/daytrade/sr_liquidity_grab.py:61`, `strategies/daytrade/sr_liquidity_grab.py:66`, `strategies/daytrade/sr_liquidity_grab.py:158`, `strategies/daytrade/sr_liquidity_grab.py:162`, `strategies/daytrade/sr_liquidity_grab.py:171` |
| 4 (filter coherence) | STRENGTHENS | `ADX < 30` は range / reversal 環境を強化し、SR proximity は thesis の対象地点を限定する。5 majors whitelist は data accumulation 目的では NEUTRAL だが、thesis を壊さない。Round-number boost と TP inside shift は stop 集中帯を意識した execution adjustment で、MA filter on MR strategy の BREAKS 例や HMM gate same-trap 型の hard regime tail block には該当しない。`strategies/daytrade/sr_liquidity_grab.py:21`, `strategies/daytrade/sr_liquidity_grab.py:23`, `strategies/daytrade/sr_liquidity_grab.py:24`, `strategies/daytrade/sr_liquidity_grab.py:37`, `strategies/daytrade/sr_liquidity_grab.py:52`, `strategies/daytrade/sr_liquidity_grab.py:83`, `strategies/daytrade/sr_liquidity_grab.py:94`, `strategies/daytrade/sr_liquidity_grab.py:111`, `strategies/daytrade/sr_liquidity_grab.py:112`, `strategies/daytrade/sr_liquidity_grab.py:114` |
| 5 (stop/TP geometry) | ALIGNED | SL は hunt extreme のさらに外側へ `0.3ATR` buffer を置くため、stop-hunt 直後の二度目の wick で即切られにくい。TP は対側 SR があればそこを優先し、なければ `TARGET_RR=1.5` の固定 R target を使う。round number 近傍では TP を 3 pips 内側へずらし、最終 RR は `1.5 * 0.9 = 1.35` 未満を拒否する。post-hunt reversal としては wide SL + opposite SR / positive R target で整合する。`strategies/daytrade/sr_liquidity_grab.py:27`, `strategies/daytrade/sr_liquidity_grab.py:28`, `strategies/daytrade/sr_liquidity_grab.py:64`, `strategies/daytrade/sr_liquidity_grab.py:69`, `strategies/daytrade/sr_liquidity_grab.py:80`, `strategies/daytrade/sr_liquidity_grab.py:81`, `strategies/daytrade/sr_liquidity_grab.py:83`, `strategies/daytrade/sr_liquidity_grab.py:92`, `strategies/daytrade/sr_liquidity_grab.py:93`, `strategies/daytrade/sr_liquidity_grab.py:94`, `strategies/daytrade/sr_liquidity_grab.py:104`, `strategies/daytrade/sr_liquidity_grab.py:105` |
| 6 (pair-regime fit) | FORCED | Code は USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY を一括許可するが、pair 別 trigger/threshold の差分はなく、既存 production 実測では GBP_USD だけ marginal positive、他 4 pair は negative。`ALL` scope としては pair-regime fit が未分化で FORCED。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative production | tier-master の phase0_shadow 365d BT EV は入力どおり `—`。既存 strategy KB は production N=300 / sum=-390.8p / mean=-0.65p を記録するが、現 local `demo_trades.db` には exact `sr_liquidity_grab` 行が 0 件で、Wilson lower / PF / Bonferroni-adjusted p / Kelly / WF folds>=3 を同一 audit DB から decision-grade に復元できない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED | Code whitelist 対象だが production 実測は N=173, WR 26%, mean -1.41p, sum -243.9p。 |
| EURUSD | FORCED | Code whitelist 対象だが production 実測は N=64, WR 19%, mean -1.33p, sum -85.1p。 |
| GBPUSD | FIT / marginal | Production 実測は N=50, WR 34%, mean +0.31p, sum +15.5p。ただし +0.31p は friction 1 click で消える水準。 |
| EURJPY | FORCED | Code whitelist 対象だが production 実測は N=9, WR 22%, mean -6.60p, sum -59.4p。 |
| GBPJPY | FORCED | Code whitelist 対象だが production 実測は N=4, WR 25%, mean -4.47p, sum -17.9p。 |
| Other ALL pairs | FORCED / blocked | `_ALLOWED_SYMBOLS` 外は即 `None`。真の ALL universe には対応していない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、既存 production 実測 N=300 / EV=-0.65p / sum=-390.8p で underperforming として failure mode 診断を適用する。破綻軸は主に Axis 3 と Axis 6。Axis 2 は SR sweep + close-back-inside + reversal body で thesis を直接捕捉し、Axis 4 の ADX/SR/round-number filter も thesis を破壊していない。Axis 5 も hunt extreme 外側 SL と 1.5R / opposite SR TP で大枠は整合する。一方、現在足の `ctx.entry` と `ctx.open_price` で反転確認する設計は bar-close contract がなく、実行層次第で intrabar 変動と同一 bar 多重 entry に寄る。また 5 majors 一括 whitelist は production 実測の pair 差を無視しており、GBPUSD 以外を同じ threshold で流すのは FORCED。

再設計案は timing と pair scope を絞る。`_find_recent_hunt()` は過去確定 bar の hunt 検出として維持し、反転確認だけを current tick から確定済み signal bar へ移す。具体的には `ctx.df.iloc[-2]` を signal bar として `Close > Open` / `< Open` と `Close` の level reclaim を判定し、`ctx.entry` は次 bar execution price として使う。さらに dispatch layer または Candidate metadata で `(symbol, entry_type, timeframe, signal_bar_time, side)` を dedup key にし、同一 15m bar の再 emit を拒否する。pair scope はまず GBPUSD only、または Phase 2 で trade-outcome EV>0 とされた USDJPY/EURUSD/GBPUSD subset だけで redesign BT を要求し、EURJPY/GBPJPY は再検証まで外す。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は維持する。SR に紐づく liquidity grab を、低 ADX の中で hunt 後の反転として取る thesis はコードから明確に導出でき、trigger/filter/SLTP の大枠も破綻していない。現状の負け方は、反転確認が未確定 current bar に依存していることと、pair scope が一括許可になっていることが主因と見る。

具体修正は `evaluate()` の反転確認を bar-close 化すること。`ctx.entry >= ctx.open_price` / `ctx.entry <= ctx.open_price` の current bar 判定を、確定済み signal bar の `Close < Open` / `Close > Open` と `Close` の level 内側回帰に置換する。signal bar timestamp を Candidate または dispatch layer に渡し、同一 15m bar dedup を必須にする。pair gate は暫定で GBPUSD only、または USDJPY/EURUSD/GBPUSD に縮小し、EURJPY/GBPJPY は Wilson lower / PF / Bonferroni / Kelly / WF folds>=3 が positive になるまで `FORCED` 扱いで外す。

採用前に必要な検証は新規 BT だが、本 audit では実行しない。必要 artifact は pair 別、365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 audit DB / tier-master source で出すこと。N/WR/EV だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Production summary: N=300 closed total; pair split USD_JPY 173 / EUR_USD 64 / GBP_USD 50 / EUR_JPY 9 / GBP_JPY 4. Current local `demo_trades.db` exact rows: 0, so raw trade reconstruction is unavailable in this workspace. | `knowledge-base/wiki/strategies/sr-liquidity-grab.md`; local read-only `demo_trades.db` query |
| Win rate | Pair summary: USD_JPY 26%, EUR_USD 19%, GBP_USD 34%, EUR_JPY 22%, GBP_JPY 25%. Aggregate exact WR is INSUFFICIENT_EVIDENCE because pair WR values are rounded and current local DB has 0 exact rows. Approximate aggregate from rounded pair rows is about 25.7%. | `knowledge-base/wiki/strategies/sr-liquidity-grab.md`; local read-only `demo_trades.db` query |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE for decision-grade exact value: exact wins are not present in local DB/tier-master. Approximate Wilson lower from rounded pair WR and N=300 is about 21.1%, but this is not a valid promotion statistic. | derived from rounded KB pair summary; tier-master input EV `—` |
| PF | INSUFFICIENT_EVIDENCE: production PF is not emitted in tier-master / current audit DB; current local `demo_trades.db` has 0 exact rows for payoff reconstruction. | tier-master input EV `—`; local read-only `demo_trades.db` query |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no fold-level PF/Kelly for `sr_liquidity_grab` is present in tier-master/current audit DB. | tier-master input EV `—`; repo audit artifact search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: strategy KB notes Phase 2 reversal-WR Bonferroni significance, but exact adjusted p-values for trade outcomes are not emitted; production adjusted p is unavailable. | `knowledge-base/wiki/strategies/sr-liquidity-grab.md`; tier-master input EV `—` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: payoff distribution / PF is unavailable in tier-master/current audit DB; N/WR/EV alone is insufficient under `feedback_partial_quant_trap.md`. | `knowledge-base/wiki/strategies/sr-liquidity-grab.md`; local read-only `demo_trades.db` query |
