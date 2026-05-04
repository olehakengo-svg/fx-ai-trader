---
strategy: asia_range_fade_v1
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

アジア時間の低 vol range で high/low touch が発生した後、rejection candle と RSI extreme を確認して range 中央への平均回帰を fade で取りに行く MR 戦略。thesis は docstring と `strategy_type = "MR"` に明示されている。`strategies/daytrade/asia_range_fade_v1.py:6`, `strategies/daytrade/asia_range_fade_v1.py:7`, `strategies/daytrade/asia_range_fade_v1.py:8`, `strategies/daytrade/asia_range_fade_v1.py:48`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、`02 <= hour <= 6`、`range_size <= 1.5 * ATR`、`bars_in_range_pct >= 0.80` で低 vol range を定義し、`current_low <= range_low * 1.0005 -> BUY` / `current_high >= range_high * 0.9995 -> SELL` で boundary touch を捕捉し、陽線+下髭または陰線+上髭、さらに `BUY: RSI <= 30` / `SELL: RSI >= 70` で oversold/overbought rejection を確認している。MR trigger として数学的には整合している。`strategies/daytrade/asia_range_fade_v1.py:70`, `strategies/daytrade/asia_range_fade_v1.py:72`, `strategies/daytrade/asia_range_fade_v1.py:81`, `strategies/daytrade/asia_range_fade_v1.py:95`, `strategies/daytrade/asia_range_fade_v1.py:106`, `strategies/daytrade/asia_range_fade_v1.py:117`, `strategies/daytrade/asia_range_fade_v1.py:118`, `strategies/daytrade/asia_range_fade_v1.py:135`, `strategies/daytrade/asia_range_fade_v1.py:145`, `strategies/daytrade/asia_range_fade_v1.py:151`, `strategies/daytrade/asia_range_fade_v1.py:156` |
| 3 (timing window) | LOOKAHEAD | `recent = df.iloc[-self.RANGE_LOOKBACK:]` が signal/rejection と同じ current bar を range formation に含め、その同じ bar の `Low` / `High` / `Open` / `ctx.entry` を touch と rejection 判定に使っている。closed-bar 呼び出しなら「同一バー close entry」で遅延は小さいが、range は touch 前に形成済みであるべきなので `df.iloc[-25:-1]` 相当へずらす必要がある。さらに docstring の「直近 4 bars 内に同方向 entry 禁止」は実装に状態がなく、同 bar/近接 bar 多重 entry 抑止が外部依存。`strategies/daytrade/asia_range_fade_v1.py:21`, `strategies/daytrade/asia_range_fade_v1.py:82`, `strategies/daytrade/asia_range_fade_v1.py:111`, `strategies/daytrade/asia_range_fade_v1.py:117`, `strategies/daytrade/asia_range_fade_v1.py:118`, `strategies/daytrade/asia_range_fade_v1.py:131`, `strategies/daytrade/asia_range_fade_v1.py:132`, `strategies/daytrade/asia_range_fade_v1.py:195` |
| 4 (filter coherence) | STRENGTHENS | 実装済み filter は session gate、ATR 上限、range size / bars-in-range gate、RSI extreme で、いずれも「低 vol range の端での逆張り」を強化する。重要先行例の MA filter on MR strategy -> BREAKS や HMM regime gate same trap と違い、上位足 trend 整合や regime hard block で MR が取りたい tail を拒否していない。未実装の 4-bar dedup は Axis 3 の timing/risk 欠落であり、現行 filter 自体は BREAKS ではない。`strategies/daytrade/asia_range_fade_v1.py:48`, `strategies/daytrade/asia_range_fade_v1.py:72`, `strategies/daytrade/asia_range_fade_v1.py:78`, `strategies/daytrade/asia_range_fade_v1.py:95`, `strategies/daytrade/asia_range_fade_v1.py:106`, `strategies/daytrade/asia_range_fade_v1.py:151`, `strategies/daytrade/asia_range_fade_v1.py:156` |
| 5 (stop/TP geometry) | ALIGNED | TP は `range_center` または `entry +/- 0.7 * range_size` の近い方、SL は range 外側 `0.5 * ATR` buffer。range edge 近辺 entry なら reward は概ね range 半分、`range_size <= 1.5 * ATR` なので最大 reward/risk はおおよそ `0.5 * range_size / (0.5 * ATR) <= 1.5R`。高 WR 前提の MR として、mean target + range 外 stop + London open time stop は整合している。`strategies/daytrade/asia_range_fade_v1.py:23`, `strategies/daytrade/asia_range_fade_v1.py:24`, `strategies/daytrade/asia_range_fade_v1.py:25`, `strategies/daytrade/asia_range_fade_v1.py:26`, `strategies/daytrade/asia_range_fade_v1.py:27`, `strategies/daytrade/asia_range_fade_v1.py:160`, `strategies/daytrade/asia_range_fade_v1.py:164`, `strategies/daytrade/asia_range_fade_v1.py:165`, `strategies/daytrade/asia_range_fade_v1.py:169`, `strategies/daytrade/asia_range_fade_v1.py:170`, `strategies/daytrade/asia_range_fade_v1.py:173` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。コードに pair whitelist がなく、入力 cell も ALL だが、pre-reg の主検証対象は USD_JPY / EUR_USD であり、ALL 全体へ外挿する既存 evidence はない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の 365d BT EV は `—`。local audit DB `demo_trades.db` では `demo_trades` / `evaluated_candidates` / `oanda_audit` の `asia_range_fade_v1` 行が 0 件。FX Nexus shadow audit でも H3 の PF off/on は 0.0000、N off/on は 0。`feedback_partial_quant_trap.md` 基準では N/WR/EV 以前に Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が揃わない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT / INSUFFICIENT_EVIDENCE | Pre-reg の Phase 3.A pair set に含まれる Asia MR 想定 pair。ただし target cell は ALL で、tier-master / local audit DB に USD_JPY decision-grade metrics がない。 |
| EUR_USD | FIT / INSUFFICIENT_EVIDENCE | Pre-reg の Phase 3.A pair set に含まれるが、FX Nexus audit は EURUSD 15m local parquet unavailable で H3 計測不能。 |
| GBP_USD | FORCED | H2 alpha residual では MR success rate 0.5222 / Bonferroni p 0.0014 の参考 positive はあるが、この strategy の pair-specific BT/WF/Kelly ではない。 |
| EUR_JPY | FORCED | H2 alpha residual では MR success rate 0.5241 / Bonferroni p 0.0005 の参考 positive はあるが、この strategy の pair-specific BT/WF/Kelly ではない。 |
| GBP_JPY | FORCED | Pre-reg pair set 外で、strategy-specific evidence がない。 |
| Other ALL pairs | FORCED / UNTESTED | コード上は pair gate がないため適用されうるが、phase0_shadow ALL の採用根拠として Wilson / PF / WF / Kelly がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で、Tier 3/4 専用の復活診断ではないが、入力 metric は 365d BT EV `—` で evidence 欠落の shadow cell として failure mode を診断する。破綻候補は Axis 3 が主。Axis 2 の trigger と Axis 4 の filter は thesis と整合し、Axis 5 の exit geometry も MR と大きく矛盾しない。一方で range formation が current bar を含むため、touch/rejection bar 自身が range boundary を作る設計になっており、「形成済み range の端を fade する」という因果順序を汚している。さらに docstring の 4-bar same-direction entry 禁止が未実装で、bar-close / per-bar dedup の外部依存が残る。

再設計案は timing 1 系統。range formation を `df.iloc[-(RANGE_LOOKBACK + 1):-1]` の closed prior window に固定し、touch/rejection は `df.iloc[-1]` の確定 signal bar、entry は次 bar execution に分離する。あわせて `(instrument, signal, range_low/high bucket, bar_time)` または最低限 `(instrument, signal, bar_time)` の last-emitted guard を追加し、docstring の「直近 4 bars 内に同方向 entry 禁止」を実装する。本監査では BT を実行しないため、採用前には USD_JPY / EUR_USD を最低対象に 365d + 5-fold WF + Bonferroni/Kelly を既存 pipeline で再集計する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

Trigger/filter/stop は維持候補にする。`touch + rejection + RSI extreme` は MR thesis を直接捕捉しており、MA/HMM 型の thesis 破壊 filter は見当たらない。最初に直すべき箇所は、range 算定と signal/execution の時系列分離である。

コードレベルの想定 diff は、`recent = df.iloc[-self.RANGE_LOOKBACK:]` を prior-window に変更し、`last_row = df.iloc[-1]` は signal bar としてだけ使う。実行層が次足 entry を保証しない場合は strategy 側で current forming bar を読まない contract を明示する。さらに 4-bar dedup state を実装し、既存 pre-reg の locked validation requirements どおり N>=200、Wilson lower>50%、PF>1.40、5-fold WF、Bonferroni α=0.005、Kelly positive を再確認する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB: 0 rows in `demo_trades`, 0 rows in `evaluated_candidates`, 0 rows in `oanda_audit`; FX Nexus H3: N off=0, N on=0 | `demo_trades.db`; `knowledge-base/wiki/decisions/fx-nexus-step1-audit-2026-05-04.md`; prompt tier-master input |
| Win rate | INSUFFICIENT_EVIDENCE due N=0 / tier-master EV `—` | same sources |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: no trade sample; pre-reg requires Wilson lower > 50% but no existing audit DB/tier-master value exists | `demo_trades.db`; `knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md`; prompt tier-master input |
| PF | INSUFFICIENT_EVIDENCE: FX Nexus H3 PF off=0.0000 / on=0.0000 with N=0, not a usable PF estimate | `knowledge-base/wiki/decisions/fx-nexus-step1-audit-2026-05-04.md`; prompt tier-master input |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: pre-reg requires 5-fold WF, but existing tier-master/audit DB does not provide completed fold metrics for this cell | `knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md`; `knowledge-base/wiki/tier-master.md` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: pre-reg α=0.005 exists, but no strategy-specific p-value is present in tier-master/local audit DB | `knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md`; `demo_trades.db` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: no WR/PF/payoff sample; Kelly cannot be computed from N=0 and tier-master EV `—` | `demo_trades.db`; prompt tier-master input |
