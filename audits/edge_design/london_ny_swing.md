---
strategy: london_ny_swing
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

ロンドン時間に形成された高安レンジを、NY時間の流動性で上抜け/下抜けした方向へ追随し、H1相当の短期 trend と ADX が同方向なら前日高安または ATR target まで continuation を取る session breakout / momentum thesis。コードは London range 計測、NY entry window、range breakout、EMA方向確認、ADX確認を明示している。`strategies/daytrade/london_ny_swing.py:2`, `strategies/daytrade/london_ny_swing.py:5`, `strategies/daytrade/london_ny_swing.py:6`, `strategies/daytrade/london_ny_swing.py:7`, `strategies/daytrade/london_ny_swing.py:37`, `strategies/daytrade/london_ny_swing.py:39`, `strategies/daytrade/london_ny_swing.py:41`, `strategies/daytrade/london_ny_swing.py:42`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / breakout thesis に対して、BUY は `entry > LondonHigh + ATR*0.1 AND EMA trend bull AND entry > open`、SELL は `entry < LondonLow - ATR*0.1 AND EMA trend bear AND entry < open`。MR ではなく range breakout continuation なので、RSI/BB%B/z-score ではなく breakout + trend confirmation を使う設計は整合している。ただし docstring の「H1 EMA20」は実装では 15m EMA9/21/50 proxy に置換されている。`strategies/daytrade/london_ny_swing.py:17`, `strategies/daytrade/london_ny_swing.py:18`, `strategies/daytrade/london_ny_swing.py:19`, `strategies/daytrade/london_ny_swing.py:20`, `strategies/daytrade/london_ny_swing.py:106`, `strategies/daytrade/london_ny_swing.py:108`, `strategies/daytrade/london_ny_swing.py:109`, `strategies/daytrade/london_ny_swing.py:119`, `strategies/daytrade/london_ny_swing.py:139` |
| 3 (timing window) | LOOKAHEAD | London range は `range(len(ctx.df) - 2, ...)` から過去barだけを読むため current bar の高安混入は抑えている。一方、signal 判定は `ctx.entry` と `ctx.open_price` の現在コンテキスト値で即 Candidate を返し、strategy 内に signal bar id / per-bar dedup / next-bar execution contract がない。同一barで evaluate が複数回呼ばれる運用では多重 entry risk が残るため、bar-close hardening が必要。`strategies/daytrade/london_ny_swing.py:72`, `strategies/daytrade/london_ny_swing.py:79`, `strategies/daytrade/london_ny_swing.py:119`, `strategies/daytrade/london_ny_swing.py:121`, `strategies/daytrade/london_ny_swing.py:139`, `strategies/daytrade/london_ny_swing.py:141`, `strategies/daytrade/london_ny_swing.py:190` |
| 4 (filter coherence) | STRENGTHENS | Pair filter は EURUSD/GBPUSD に限定し、London/NY handoff の主要 liquidity pair に寄せる。NY window、ADX>=18、London range min/max、EMA trend proxy、陽線/陰線確認はいずれも breakout continuation thesis を強化する。HTF agreement は hard block ではなく score bonus/penalty なので、MR に MA filter を被せる例や HMM gate same trap のように thesis tail を構造的に破壊してはいない。`strategies/daytrade/london_ny_swing.py:48`, `strategies/daytrade/london_ny_swing.py:57`, `strategies/daytrade/london_ny_swing.py:63`, `strategies/daytrade/london_ny_swing.py:100`, `strategies/daytrade/london_ny_swing.py:101`, `strategies/daytrade/london_ny_swing.py:103`, `strategies/daytrade/london_ny_swing.py:108`, `strategies/daytrade/london_ny_swing.py:109`, `strategies/daytrade/london_ny_swing.py:179` |
| 5 (stop/TP geometry) | ALIGNED | BUY は previous-day high が entry より上ならそこを TP、なければ `entry + ATR*3.0`、SL は `LondonHigh - ATR*0.3` か最小SL。SELL は対称。さらに `_tp_dist >= _sl_dist * 1.3` を要求するため、breakout level 近辺で切り、前日高安/ATR extension を狙う asymmetric continuation geometry になっている。Trailing はないが、docstring の「前日高安まで狙う」swing thesis とは衝突しない。`strategies/daytrade/london_ny_swing.py:22`, `strategies/daytrade/london_ny_swing.py:23`, `strategies/daytrade/london_ny_swing.py:43`, `strategies/daytrade/london_ny_swing.py:44`, `strategies/daytrade/london_ny_swing.py:129`, `strategies/daytrade/london_ny_swing.py:133`, `strategies/daytrade/london_ny_swing.py:135`, `strategies/daytrade/london_ny_swing.py:148`, `strategies/daytrade/london_ny_swing.py:152`, `strategies/daytrade/london_ny_swing.py:154`, `strategies/daytrade/london_ny_swing.py:163` |
| 6 (pair-regime fit) | FIT / FORCED | 実装は EURUSD/GBPUSD のみ許可するため、実行上の target pair は session breakout に自然。ただし監査 input は `pairs: ALL` であり、ALL cell として統計評価するなら code scope と tier scope がずれる。下の Pair-Regime Table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 入力の phase0_shadow / ALL 365d BT EV は `—`。local audit DB `demo_trades.db` では `demo_trades`、`evaluated_candidates`、`oanda_audit` の `london_ny_swing` 行が 0 件で、Wilson lower / PF / Bonferroni p / Kelly を算出できない。既存 sidecar BT/WF には参考値があるが、本タスク指定の tier-master/audit DB decision-grade evidence ではない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EURUSD | FIT / unproven | コードは EURUSD を許可し、London/NY overlap の主流動性 pair として thesis fit は自然。ただし audit DB/tier-master の Wilson/PF/Kelly がない。 |
| GBPUSD | FIT / weak-evidence | コードは GBPUSD を許可し、London/NY handoff と GBP liquidity の組み合わせは自然。ただし target ALL cell の decision-grade evidence はない。 |
| Other ALL pairs | FORCED / BLOCKED | 監査 input は ALL だが、実装は `_enabled_symbols` 外を即 return するため、USDJPY/EURJPY/GBPJPY/XAU などへ ALL 適用する設計ではない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) のため昇格前 failure mode として診断する。主破綻は Axis 3。思想と trigger は明確で、filters も continuation thesis を破壊していないが、strategy 内では signal bar を確定足として固定する契約、signal→next-bar execution、同一bar dedup が保証されていない。副次的には Axis 6/7 で、tier-master 上は ALL / phase0_shadow として扱われる一方、コードは EURUSD/GBPUSD 専用で、さらに audit DB には対象行が 0 件である。

再設計案は timing hardening を最小単位にする。London range は現行どおり過去barから算出しつつ、trigger 判定を `signal_bar = ctx.df.iloc[-2]` の close/open に固定し、entry は次bar execution の `ctx.entry` として分離する。あわせて `(symbol, strategy, signal, bar_time)` の last-emitted guard を strategy または dispatch 層に置き、同一bar複数 Candidate を禁止する。BT は本監査では実行しないため、採用前には EURUSD/GBPUSD 別に既存 audit pipeline で Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction を再発行する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

Trigger の思想自体は維持する。修正対象は timing 1 系統で、`ctx.entry > _ldn_high + ATR*buffer` / `< _ldn_low - ATR*buffer` を current context の即時判定として扱うのではなく、確定済み signal bar の close で breakout と陽線/陰線を判定し、execution price は次barに分ける。これにより intrabar 更新や同一bar再評価での runaway を切れる。

Filter は削除しない。ADX、London range min/max、EMA trend proxy、HTF agreement score は momentum thesis を支えているため、まずは hardening 後の EURUSD/GBPUSD pair-specific audit を優先する。tier-master / inventory 側は `ALL` ではなく `EURUSD, GBPUSD` の cell に切るのが自然で、その他 pair は現行コードどおり BLOCKED と明記する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB: 0 closed trades / 0 evaluated candidates / 0 OANDA audit rows for `london_ny_swing`; tier-master ALL EV is `—` | `demo_trades.db`; prompt tier-master input; `knowledge-base/wiki/tier-master.md` |
| Win rate | INSUFFICIENT_EVIDENCE: audit DB N=0, not estimable | `demo_trades.db` |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: audit DB N=0, Wilson lower not estimable | `demo_trades.db` |
| PF | INSUFFICIENT_EVIDENCE: tier-master provides no PF and audit DB has no realized rows | prompt tier-master input; `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE for target ALL cell: tier-master/audit DB provide no qualifying WF folds>=3 | prompt tier-master input; `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: no audit DB sample and no tier-master p-value | prompt tier-master input; `demo_trades.db` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: no PF/payoff or realized sample in tier-master/audit DB | prompt tier-master input; `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
