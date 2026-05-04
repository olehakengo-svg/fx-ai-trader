---
strategy: ema_pullback
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

ADX でトレンド環境を確認し、EMA9/EMA21 の方向へ浅い EMA pullback が入った直後の反発・反落を拾う trend-continuation thesis。BUY は `ema9 > ema21` かつ EMA21 上への復帰、前バー EMA9 touch、現バー反発、SELL はその対称条件で定義されている。`strategies/scalp/ema_pullback.py:12`, `strategies/scalp/ema_pullback.py:29`, `strategies/scalp/ema_pullback.py:40`, `strategies/scalp/ema_pullback.py:41`, `strategies/scalp/ema_pullback.py:42`, `strategies/scalp/ema_pullback.py:43`, `strategies/scalp/ema_pullback.py:45`, `strategies/scalp/ema_pullback.py:72`, `strategies/scalp/ema_pullback.py:73`, `strategies/scalp/ema_pullback.py:74`, `strategies/scalp/ema_pullback.py:75`, `strategies/scalp/ema_pullback.py:77`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trend pullback thesis に対して、BUY は `ADX >= 20 ∧ ema9 > ema21 ∧ entry >= ema21 ∧ prev_low <= ema9 ∧ prev_low >= ema21 - 0.3ATR ∧ entry > prev_close`、SELL は符号反転条件。さらに bounce `abs(entry-ema21) >= 0.2ATR`、MACD-H 方向、Stoch cross、body/range >= 0.35 で反発確認を追加している。EMA50 は理由文にだけ出るが条件からは外れており、trend confirmation は EMA9/21 + ADX に限定される。`strategies/scalp/ema_pullback.py:15`, `strategies/scalp/ema_pullback.py:26`, `strategies/scalp/ema_pullback.py:41`, `strategies/scalp/ema_pullback.py:42`, `strategies/scalp/ema_pullback.py:43`, `strategies/scalp/ema_pullback.py:44`, `strategies/scalp/ema_pullback.py:45`, `strategies/scalp/ema_pullback.py:49`, `strategies/scalp/ema_pullback.py:50`, `strategies/scalp/ema_pullback.py:52`, `strategies/scalp/ema_pullback.py:54`, `strategies/scalp/ema_pullback.py:58`, `strategies/scalp/ema_pullback.py:73`, `strategies/scalp/ema_pullback.py:74`, `strategies/scalp/ema_pullback.py:75`, `strategies/scalp/ema_pullback.py:76`, `strategies/scalp/ema_pullback.py:77`, `strategies/scalp/ema_pullback.py:81`, `strategies/scalp/ema_pullback.py:82`, `strategies/scalp/ema_pullback.py:84`, `strategies/scalp/ema_pullback.py:86`, `strategies/scalp/ema_pullback.py:90` |
| 3 (timing window) | LOOKAHEAD | Strategy は current `ctx.entry` / `ctx.open_price` と `ctx.df["High"].iloc[-1]`, `ctx.df["Low"].iloc[-1]` を同じ判定で使い、Candidate に signal bar id や dedup key を載せない。closed bar 専用に呼ばれる保証が strategy 内にないため、live では mutable current bar の反発・body 判定で intrabar contamination と同一 bar 多重 entry のリスクが残る。`strategies/scalp/ema_pullback.py:45`, `strategies/scalp/ema_pullback.py:56`, `strategies/scalp/ema_pullback.py:57`, `strategies/scalp/ema_pullback.py:58`, `strategies/scalp/ema_pullback.py:77`, `strategies/scalp/ema_pullback.py:88`, `strategies/scalp/ema_pullback.py:89`, `strategies/scalp/ema_pullback.py:90`, `strategies/scalp/ema_pullback.py:114` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | ADX minimum は trend pullback を強化し、RSI5 と BB %B は extreme 追随を避ける pullback depth filter として概ね STRENGTHENS。MACD-H、Stoch cross、body ratio は bounce confirmation で STRENGTHENS。ADX weak/overheat は confidence adjustment で hard filter ではないため NEUTRAL 寄り。MR に MA filter を被せる BREAKS 例ではなく、HMM regime hard gate も存在しない。`strategies/scalp/ema_pullback.py:15`, `strategies/scalp/ema_pullback.py:16`, `strategies/scalp/ema_pullback.py:17`, `strategies/scalp/ema_pullback.py:18`, `strategies/scalp/ema_pullback.py:19`, `strategies/scalp/ema_pullback.py:20`, `strategies/scalp/ema_pullback.py:21`, `strategies/scalp/ema_pullback.py:22`, `strategies/scalp/ema_pullback.py:23`, `strategies/scalp/ema_pullback.py:24`, `strategies/scalp/ema_pullback.py:46`, `strategies/scalp/ema_pullback.py:47`, `strategies/scalp/ema_pullback.py:52`, `strategies/scalp/ema_pullback.py:54`, `strategies/scalp/ema_pullback.py:58`, `strategies/scalp/ema_pullback.py:78`, `strategies/scalp/ema_pullback.py:79`, `strategies/scalp/ema_pullback.py:84`, `strategies/scalp/ema_pullback.py:86`, `strategies/scalp/ema_pullback.py:90`, `strategies/scalp/ema_pullback.py:109`, `strategies/scalp/ema_pullback.py:113` |
| 5 (stop/TP geometry) | MISALIGNED | Nominal TP は `1.8ATR`、SL は EMA21 から `0.3ATR` 外側。BUY risk は `entry - ema21 + 0.3ATR`、かつ bounce gate により最小 `0.5ATR` なので nominal R:R は最大約 `1.8/0.5 = 3.6R` だが、entry が EMA21 から離れるほど R が急速に悪化する。trend pullback continuation として asymmetric TP は正しい一方、SL が EMA21 offset 固定で pullback low / volatility structure を見ず、浅押し限定と tight stop が即死を誘発しやすい。`strategies/scalp/ema_pullback.py:25`, `strategies/scalp/ema_pullback.py:26`, `strategies/scalp/ema_pullback.py:49`, `strategies/scalp/ema_pullback.py:50`, `strategies/scalp/ema_pullback.py:69`, `strategies/scalp/ema_pullback.py:70`, `strategies/scalp/ema_pullback.py:81`, `strategies/scalp/ema_pullback.py:82`, `strategies/scalp/ema_pullback.py:101`, `strategies/scalp/ema_pullback.py:102` |
| 6 (pair-regime fit) | FORCED | Code に pair gate はなく `ALL` cell として扱われるが、既存 evidence は USD_JPY NY に偏り、EUR_USD London と GBP_USD は弱い。下の pair-regime table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / weak positive aggregate | tier-master の force_demoted 行は 365d BT EV が `—`。gate-progression audit aggregate は N=23, WR=30.43%, Wilson lo=15.60%, EV=+0.07p, PF=1.074, Kelly=0.0210, raw Kelly=+0.0210, Bonferroni p=1.0000。PF/Kelly はわずかに positive だが、小N・Bonferroni 不通過・WF folds>=3 欠落により `feedback_partial_quant_trap.md` 基準では採用根拠不足。 |

### Pair-Regime Table

| Pair | Verdict | Evidence |
|------|---------|----------|
| USD_JPY | FIT / session-dependent | 古い cell profile は USD_JPY×NY×SELL N=8, WR=62.5%, PF=2.54, Kelly=37.9%、USD_JPY×NY×BUY N=7, WR=42.9%, PF=2.27。ただし最新 H1 bucket では USD_JPY London N=7, WR=14.3%, PF=0.23、NY-overlap N=3, WR=66.7%, PF=4.00、Off N=4, WR=50.0%, PF=1.63 と session 依存が強い。 |
| EUR_USD | FORCED | 古い profile は EUR_USD×NY×SELL N=3, PF=0.87、EUR_USD×London×BUY N=4, PF=0.00。最新 H1 bucket は London N=3, WR=0.0%, PF=0.00、NY-overlap N=2, WR=100.0%, PF=inf だが小N。 |
| GBP_USD | FORCED | 最新 H1 bucket に GBP_USD Asia N=1, WR=0.0%, PF=0.00 のみ。trend pullback thesis との相性を否定する十分な標本ではないが、ALL cell へ含める evidence はない。 |
| Other pairs | FORCED | Code は pair を制限しないが、tier-master/audit DB で decision-grade の Wilson/PF/Kelly/WF が確認できない。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) の failure mode は Axis 3 と Axis 5 が主因、Axis 6/7 が昇格阻害要因。Axis 2 の thesis/trigger は trend pullback を概ね捕捉しており、Axis 4 の filters も hard regime trap ではないため、思想自体は棄却しない。

再設計案は closed-bar + structure stop + pair/session split。Signal 判定を確定済み signal bar に固定し、`entry > prev_close` / body ratio / current high-low 判定を signal bar snapshot から計算する。Candidate には `(entry_type, symbol, signal_bar_time, direction)` dedup key 相当を渡し、同一 bar 再発火を止める。Stop は `ema21 ± 0.3ATR` 固定ではなく、BUY なら `min(signal_low, ema21 - 0.6ATR)`、SELL なら `max(signal_high, ema21 + 0.6ATR)` のように pullback structure の外へ置く variant を比較する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想と trigger 骨格は維持する。変更はまず timing を closed-bar 化し、現バーの `ctx.entry/open/high/low` 混在を signal bar と execution bar に分離する。具体的には signal bar の `Close > PrevClose`、`abs(Close-Open)/(High-Low) >= 0.35`、MACD-H/Stoch を確定足で評価し、次 bar の `ctx.entry` で Candidate を返す形にする。

次に stop/TP geometry を pullback structure に合わせる。現行の `sl = ema21 ± 0.3ATR` は浅押し専用で tight なので、SL を signal low/high 外側または `0.6-1.0ATR` offset に広げ、TP は `max(1.5R, 1.8ATR)` と `2R partial + trailing` の 2 variant を比較する。Pair scope は最初から `ALL` に戻さず、USD_JPY NY-overlap / NY セルを主候補、EUR_USD/GBP_USD は別 cell として evidence が出るまで FORCED 扱いにする。採用前には本 audit では実行しない 365d + WF folds>=3 の再集計で、Wilson lower / PF / Bonferroni-adjusted p / Kelly を同一 artifact に出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 23 latest gate-progression aggregate; older shadow TP-hit deep dive N=36; local `demo_trades.db` exact strategy rows were not found by read-only sqlite query | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; local `demo_trades.db` |
| Win rate | 30.43% latest aggregate; older shadow TP-hit deep dive 36.1% | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Wilson lo (95%) | 15.60% latest aggregate; older shadow TP-hit deep dive aggregate not listed, cell-level USD_JPY×NY×SELL 30.6% | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| PF | 1.074 latest aggregate; older shadow TP-hit deep dive PF=1.11; tier-master force_demoted 365d BT EV/PF is `—` | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: older deep dive only has pre/post cutoff WR (pre N=35 WR=37.1%, post N=1 WR=0.0%), not >=3 WF folds; tier-master has no fold metric | tier-master + audit DB |
| Bonferroni-adj p | 1.0000 latest aggregate; older cell profile also Bonferroni fail for listed cells | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Kelly fraction | 0.0210 latest aggregate (raw Kelly +0.0210); older shadow TP-hit deep dive Kelly=3.6% aggregate | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
