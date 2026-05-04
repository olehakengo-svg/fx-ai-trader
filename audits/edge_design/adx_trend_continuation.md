---
strategy: adx_trend_continuation
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

確立済みトレンドを ADX と DI/EMA パーフェクトオーダーで確認し、直近 1-3 本の EMA9-EMA21 ゾーンへのプルバック後、現在足の EMA9 回復・足色反転でトレンド再開に乗る momentum / trend-continuation 戦略。ブレイクアウトではなく「確立済みトレンドへの再乗車」を狙う思想はコード内コメントと条件列から導出可能。`strategies/daytrade/adx_trend_continuation.py:11`, `strategies/daytrade/adx_trend_continuation.py:12`, `strategies/daytrade/adx_trend_continuation.py:13`, `strategies/daytrade/adx_trend_continuation.py:14`, `strategies/daytrade/adx_trend_continuation.py:20`, `strategies/daytrade/adx_trend_continuation.py:21`, `strategies/daytrade/adx_trend_continuation.py:28`, `strategies/daytrade/adx_trend_continuation.py:30`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-continuation thesis に対し、`ADX >= 25`、`BUY: +DI > -DI AND EMA9 > EMA21 > EMA50`、`SELL: -DI > +DI AND EMA9 < EMA21 < EMA50` でトレンド方向を確認し、前 1-3 本で `BUY: Low <= EMA9 AND Low >= EMA21 - 0.5ATR AND RSI < 55`、`SELL: High >= EMA9 AND High <= EMA21 + 0.5ATR AND RSI > 45` を要求する。その後、現在足で `BUY: Close > Open AND Close > EMA9 AND RSI >= 45`、`SELL: Close < Open AND Close < EMA9 AND RSI <= 55` を確認するため、MR の oversold 単独 trigger ではなく、プルバック後の順張り再開を数学的に捕捉している。`strategies/daytrade/adx_trend_continuation.py:102`, `strategies/daytrade/adx_trend_continuation.py:108`, `strategies/daytrade/adx_trend_continuation.py:109`, `strategies/daytrade/adx_trend_continuation.py:111`, `strategies/daytrade/adx_trend_continuation.py:112`, `strategies/daytrade/adx_trend_continuation.py:142`, `strategies/daytrade/adx_trend_continuation.py:152`, `strategies/daytrade/adx_trend_continuation.py:154`, `strategies/daytrade/adx_trend_continuation.py:156`, `strategies/daytrade/adx_trend_continuation.py:159`, `strategies/daytrade/adx_trend_continuation.py:160`, `strategies/daytrade/adx_trend_continuation.py:161`, `strategies/daytrade/adx_trend_continuation.py:177`, `strategies/daytrade/adx_trend_continuation.py:183`, `strategies/daytrade/adx_trend_continuation.py:190` |
| 3 (timing window) | LOOKAHEAD | プルバック検出自体は `idx = -2, -3, -4` で前 1-3 本に限定しており同一足矛盾は避けている。一方、リバウンド確認と EMA9 回復は現在 `ctx.entry` / `ctx.open_price` / `ctx.ema9` を直接読むため、実行層が未確定足で `evaluate()` を呼ぶ場合は intrabar の途中状態で emit できる。strategy 内には `ctx.bar_time` による closed-bar 判定や per-bar dedup がなく、同一 bar 多重 entry を strategy 単体では抑止していない。SL も `ctx.df` の直近 window から high/low を読むため、未確定足が含まれる呼び出しでは stop geometry が intrabar high/low に依存する。`strategies/daytrade/adx_trend_continuation.py:142`, `strategies/daytrade/adx_trend_continuation.py:143`, `strategies/daytrade/adx_trend_continuation.py:176`, `strategies/daytrade/adx_trend_continuation.py:177`, `strategies/daytrade/adx_trend_continuation.py:179`, `strategies/daytrade/adx_trend_continuation.py:182`, `strategies/daytrade/adx_trend_continuation.py:183`, `strategies/daytrade/adx_trend_continuation.py:185`, `strategies/daytrade/adx_trend_continuation.py:205`, `strategies/daytrade/adx_trend_continuation.py:208` |
| 4 (filter coherence) | STRENGTHENS | EURUSD 専用 filter は、コードコメント上の USDJPY/GBPUSD/EURGBP 負 EV を避ける pair filter として thesis を壊さないが、audit 対象 `ALL` とは齟齬があるため pair scope では NEUTRAL/要明示。ADX>=25、DI 方向、EMA9/21/50 パーフェクトオーダー、HTF 逆方向ブロックは trend-continuation thesis を強化する。RSI pullback と RSI recovery は「押し目があり、暴落中ではない」ことを確認する補助 filter で、MA filter on MR strategy や HMM regime gate same-trap の先行例と異なり、momentum tail を直接破壊する hard gate は見えない。`strategies/daytrade/adx_trend_continuation.py:80`, `strategies/daytrade/adx_trend_continuation.py:81`, `strategies/daytrade/adx_trend_continuation.py:82`, `strategies/daytrade/adx_trend_continuation.py:83`, `strategies/daytrade/adx_trend_continuation.py:84`, `strategies/daytrade/adx_trend_continuation.py:86`, `strategies/daytrade/adx_trend_continuation.py:102`, `strategies/daytrade/adx_trend_continuation.py:111`, `strategies/daytrade/adx_trend_continuation.py:112`, `strategies/daytrade/adx_trend_continuation.py:123`, `strategies/daytrade/adx_trend_continuation.py:125`, `strategies/daytrade/adx_trend_continuation.py:127`, `strategies/daytrade/adx_trend_continuation.py:156`, `strategies/daytrade/adx_trend_continuation.py:161`, `strategies/daytrade/adx_trend_continuation.py:190`, `strategies/daytrade/adx_trend_continuation.py:192` |
| 5 (stop/TP geometry) | ALIGNED | SL は BUY で直近 swing low から `0.3ATR` 下、SELL で swing high から `0.3ATR` 上。TP は `max(2.5ATR, 1.5R)` で、最低 R:R は `1.5`。Trend continuation として勝ち方向を stop より広く取りに行く非対称 payoff になっており、momentum thesis と整合する。ただし `MAX_HOLD_BARS=12` は定義のみで Candidate に渡されておらず、保持時間 geometry は実装上この strategy file からは確認できない。`strategies/daytrade/adx_trend_continuation.py:71`, `strategies/daytrade/adx_trend_continuation.py:72`, `strategies/daytrade/adx_trend_continuation.py:73`, `strategies/daytrade/adx_trend_continuation.py:74`, `strategies/daytrade/adx_trend_continuation.py:77`, `strategies/daytrade/adx_trend_continuation.py:205`, `strategies/daytrade/adx_trend_continuation.py:206`, `strategies/daytrade/adx_trend_continuation.py:208`, `strategies/daytrade/adx_trend_continuation.py:209`, `strategies/daytrade/adx_trend_continuation.py:213`, `strategies/daytrade/adx_trend_continuation.py:214`, `strategies/daytrade/adx_trend_continuation.py:215`, `strategies/daytrade/adx_trend_continuation.py:223` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。入力 scope は `ALL` だが、実装は EURUSD 以外を即 return するため、ALL cell としては FORCED。EURUSD 単体なら trend pullback fit はあるが、USDJPY/GBPUSD/EURGBP はコードコメント上も負 EV とされる。`strategies/daytrade/adx_trend_continuation.py:80`, `strategies/daytrade/adx_trend_continuation.py:81`, `strategies/daytrade/adx_trend_continuation.py:82`, `strategies/daytrade/adx_trend_continuation.py:83`, `strategies/daytrade/adx_trend_continuation.py:84`, `strategies/daytrade/adx_trend_continuation.py:85`, `strategies/daytrade/adx_trend_continuation.py:86`, `strategies/daytrade/adx_trend_continuation.py:87` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow 行は 365d BT EV が `—` で、promotion-grade の PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が tier-master では揃わない。audit DB 相当の gate-progression 集計では N=1, WR=0.00%, Wilson lo=0.00%, PF=0.000, Kelly=0.0000, Bonferroni p=1.0000 で、`feedback_partial_quant_trap.md` 基準では N/WR/EV 以前に統計証拠不足。既存 sidecar BT/WF には参考値があるが、本タスク指定の tier-master 由来値は `—` のため、採用判断には追加 BT/WF 集計が必要。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EURUSD | FIT / INSUFFICIENT_EVIDENCE | Strategy file は EURUSD のみ許可。コードコメントでは EURUSD 15t WR=78.6%, EV=+1.706 とされるが、tier-master 365d EV は `—`。既存 gate-progression audit は strategy 全体 N=1 で証拠不足。 |
| USDJPY | FORCED / BLOCKED | Strategy file コメントで USDJPY は 14t WR=50%, EV=-0.719 とされ、実装でも EURUSD 以外は `return None`。 |
| GBPUSD | FORCED / BLOCKED | Strategy file コメントで GBPUSD は 11t WR=36.4%, EV=-1.618 とされ、実装でも EURUSD 以外は `return None`。 |
| EURGBP | FORCED / BLOCKED | Strategy file コメントで EURGBP は 12t WR=41.7%, EV=-1.215 とされ、実装でも EURUSD 以外は `return None`。 |
| Other ALL pairs | FORCED / BLOCKED | Pair universe `ALL` とは異なり、実装上の signal universe は EURUSD のみ。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) であり Tier 3/4 ではないが、phase0_shadow かつ empirical evidence が N=1 / tier-master EV `—` のため、昇格候補としての failure mode を診断する。

破綻候補は Axis 2/4/5 ではなく、Axis 3 と Axis 6/7。思想と trigger は整合しており、filter も momentum thesis を破壊していない。問題は、strategy 内で closed-bar / per-bar dedup が保証されず、現在足の `ctx.entry` と high/low 依存の geometry をそのまま使う点、さらに `ALL` cell として dispatch されているのに実装は EURUSD 専用である点、そして Wilson / PF / WF / Bonferroni / Kelly が decision-grade に不足している点。

再設計案は timing hardening と scope 明示の 2 点。まず trigger 判定を closed bar に固定し、`bar_id = ctx.bar_time or ctx.df.index[-1]` を使った `(symbol, signal, bar_id)` dedup を strategy または dispatch 層で必ず通す。次に audit / tier-master 上の cell を `ALL` ではなく `EURUSD` に切り、USDJPY/GBPUSD/EURGBP はコードコメントどおり BLOCKED として扱う。そのうえで EURUSD 365d + WF folds>=3 の既存ハーネス集計を取り直し、Wilson lower / PF / Bonferroni p / Kelly を同一 source で埋める必要がある。本 audit では新規 BT は実行しない。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`A`

思想は明確で、trigger/filter/stop は概ね整合しているため棄却ではない。最小の実装方針は、現在の ADX/DI/EMA/pullback/rebound 条件を維持したまま、signal を closed-bar 化し、同一 `(symbol, signal, bar_id)` の再 emit を禁止する timing guard を追加すること。具体的には現在足を confirmation bar とするなら、その bar が確定済みであることを実行層から `ctx.backtest_mode` / `ctx.bar_time` で保証し、live intrabar では `return None` にする。

scope も修正対象。`pairs: ALL` として扱うと Axis 6 が FORCED になるため、tier-master / audit inventory 上は EURUSD 専用 cell に分割する。USDJPY/GBPUSD/EURGBP は現行コードコメント上も負 EV とされているので、再設計の主対象にはしない。採用前には BT 追加ではなく既存 audit pipeline の再集計として、EURUSD 365d、WF folds>=3、Bonferroni-adjusted p、Kelly fraction を同一テーブルで発行する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB: 1; tier-master 365d BT: `—`; sidecar 365d BT reference: N=16 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/tier-master.md`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json` |
| Win rate | audit DB: 0.00%; sidecar 365d BT reference: 50.0% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json` |
| Wilson lo (95%) | audit DB: 0.00%; sidecar BT Wilson not present in source | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| PF | audit DB: 0.000; sidecar 365d WF reference: PF=0.84; sidecar 365d BT JSON PF not present | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE for target 365d 15m cell: W60 active_windows=1, W90 active_windows=1, W30 active_windows=0, W7 active_windows=0, all `N_windows<2`. 180d 5m sidecar has active_windows=3 / borderline, but timeframe/category mismatch. | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w7-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.json` |
| Bonferroni-adj p | audit DB: 1.0000; tier-master: not present | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/tier-master.md` |
| Kelly fraction | audit DB: 0.0000; tier-master: not present | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/tier-master.md` |
