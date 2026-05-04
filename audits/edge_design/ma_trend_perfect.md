---
strategy: ma_trend_perfect
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

H1 EMA200 でマクロ方向を固定し、M15 EMA9/21/50 のパーフェクトオーダーと ADX でメソトレンドを確認したうえで、M5 EMA21 再ブレイクと 1m 同方向確認で順張り再加速を取る pure trend-follow scalp。`strategies/scalp/ma_trend_perfect.py:1`, `strategies/scalp/ma_trend_perfect.py:7`, `strategies/scalp/ma_trend_perfect.py:13`, `strategies/scalp/ma_trend_perfect.py:14`, `strategies/scalp/ma_trend_perfect.py:16`, `strategies/scalp/ma_trend_perfect.py:17`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対し、BUY は `h1_gap_pct > 0.001 AND m15_ema9 > m15_ema21 > m15_ema50 AND m15_slope > 0 AND m15_adx >= 22 AND m5_prev_close <= m5_ema21 < m5_close AND ctx.entry > ctx.open_price AND ctx.macdh > ctx.macdh_prev`。SELL は符号反転。EMA 整合、ADX、再ブレイク、1m candle/MACD-H がすべて trend continuation を直接捕捉しており、MR trigger との混線はない。`strategies/scalp/ma_trend_perfect.py:31`, `strategies/scalp/ma_trend_perfect.py:32`, `strategies/scalp/ma_trend_perfect.py:37`, `strategies/scalp/ma_trend_perfect.py:72`, `strategies/scalp/ma_trend_perfect.py:73`, `strategies/scalp/ma_trend_perfect.py:74`, `strategies/scalp/ma_trend_perfect.py:84`, `strategies/scalp/ma_trend_perfect.py:87`, `strategies/scalp/ma_trend_perfect.py:88`, `strategies/scalp/ma_trend_perfect.py:104`, `strategies/scalp/ma_trend_perfect.py:105`, `strategies/scalp/ma_trend_perfect.py:106`, `strategies/scalp/ma_trend_perfect.py:107`, `strategies/scalp/ma_trend_perfect.py:108`, `strategies/scalp/ma_trend_perfect.py:122`, `strategies/scalp/ma_trend_perfect.py:123`, `strategies/scalp/ma_trend_perfect.py:124`, `strategies/scalp/ma_trend_perfect.py:125`, `strategies/scalp/ma_trend_perfect.py:126` |
| 3 (timing window) | LOOKAHEAD | M5 再ブレイクは `m5_prev_close` と `m5_close` を使うが、strategy 内に M5 確定バー保証、signal bar timestamp、または `(symbol, direction, bar_time)` dedup がない。さらに 1m 確認は current `ctx.entry` と `ctx.open_price`、current `ctx.macdh` と previous MACD-H の同一評価時点比較で、未確定足中の陽線/陰線化・MACD-H 変化で発火しうる。Candidate にも signal bar id は含まれない。`strategies/scalp/ma_trend_perfect.py:90`, `strategies/scalp/ma_trend_perfect.py:91`, `strategies/scalp/ma_trend_perfect.py:92`, `strategies/scalp/ma_trend_perfect.py:93`, `strategies/scalp/ma_trend_perfect.py:104`, `strategies/scalp/ma_trend_perfect.py:105`, `strategies/scalp/ma_trend_perfect.py:106`, `strategies/scalp/ma_trend_perfect.py:107`, `strategies/scalp/ma_trend_perfect.py:108`, `strategies/scalp/ma_trend_perfect.py:122`, `strategies/scalp/ma_trend_perfect.py:123`, `strategies/scalp/ma_trend_perfect.py:124`, `strategies/scalp/ma_trend_perfect.py:125`, `strategies/scalp/ma_trend_perfect.py:126`, `strategies/scalp/ma_trend_perfect.py:146`, `strategies/scalp/ma_trend_perfect.py:149` |
| 4 (filter coherence) | STRENGTHENS | H1 EMA200 gap filter は macro trend direction を固定し、M15 perfect order + slope + ADX は trend persistence を強化し、M5 EMA21 再ブレイクは pullback 終了後の再加速を確認する。`ADX>=28` は score bonus だけで hard exclusion ではなく、`strategy_type="trend"` で confidence penalty へ渡すため、MR に MA filter を重ねる BREAKS 例や regime tail を HMM gate で消す BREAKS 例には該当しない。`strategies/scalp/ma_trend_perfect.py:31`, `strategies/scalp/ma_trend_perfect.py:32`, `strategies/scalp/ma_trend_perfect.py:33`, `strategies/scalp/ma_trend_perfect.py:37`, `strategies/scalp/ma_trend_perfect.py:53`, `strategies/scalp/ma_trend_perfect.py:73`, `strategies/scalp/ma_trend_perfect.py:74`, `strategies/scalp/ma_trend_perfect.py:84`, `strategies/scalp/ma_trend_perfect.py:87`, `strategies/scalp/ma_trend_perfect.py:88`, `strategies/scalp/ma_trend_perfect.py:118`, `strategies/scalp/ma_trend_perfect.py:119`, `strategies/scalp/ma_trend_perfect.py:136`, `strategies/scalp/ma_trend_perfect.py:137`, `strategies/scalp/ma_trend_perfect.py:144` |
| 5 (stop/TP geometry) | ALIGNED | SL は `1.0 * ATR7`、TP は `max(1.8 * ATR7, 1.5R)` で、nominal RR=1.8、floor RR=1.5。BUY/SELL とも trend continuation の asymmetric payoff と整合する。trailing はないが、scalp の固定 TP/SL としては momentum thesis を壊していない。`strategies/scalp/ma_trend_perfect.py:34`, `strategies/scalp/ma_trend_perfect.py:35`, `strategies/scalp/ma_trend_perfect.py:36`, `strategies/scalp/ma_trend_perfect.py:110`, `strategies/scalp/ma_trend_perfect.py:111`, `strategies/scalp/ma_trend_perfect.py:112`, `strategies/scalp/ma_trend_perfect.py:113`, `strategies/scalp/ma_trend_perfect.py:128`, `strategies/scalp/ma_trend_perfect.py:129`, `strategies/scalp/ma_trend_perfect.py:130`, `strategies/scalp/ma_trend_perfect.py:131` |
| 6 (pair-regime fit) | FIT | Input は `ALL` だが実装は `_ALLOWED_PAIRS = {"USD_JPY"}` で USD_JPY 以外を即 return するため、実効 pair は USD_JPY のみ。USD_JPY は既存 MA-family v1b 180d evidence で Tokyo/NY が positive だが、ALL-pair 展開は未実装かつ未検証。`strategies/scalp/ma_trend_perfect.py:31`, `strategies/scalp/ma_trend_perfect.py:56`, `strategies/scalp/ma_trend_perfect.py:57` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / positive BT prior | tier-master の scalp_sentinel 行は 365d BT EV が `—` で、local `demo_trades.db` には exact `ma_trend_perfect` 行が 0 件。既存 pre-reg / MA-family artifact には USD_JPY 180d v1b 単独で ALL N=369, WR=60.7%, Wilson lo=55.64%, PF=1.99, Kelly=30.2%, p=0.00026、WF 3 folds all PF>1.3 がある。ただし 365d tier-master 値、Shadow live N、Bonferroni-adjusted p として保存された値、現行 audit DB の Kelly が揃わないため、`feedback_partial_quant_trap.md` 基準では current promotion evidence は不足。 |

### Pair-Regime Table

| Pair / scope | Verdict | Evidence |
|--------------|---------|----------|
| USD_JPY | FIT | Code-level allowed pair。MA-family v1b 180d pre-reg BT は Tokyo N=91 WR=73.6% PF=3.84 Kelly=54.5% Wilson lo=63.75%、NY N=124 WR=61.3% PF=2.19 Kelly=33.3% Wilson lo=52.50%、ALL N=369 WR=60.7% PF=1.99 Kelly=30.2% Wilson lo=55.64%。 |
| Non-USD_JPY | FORCED if expanded | 現行 code は non-USD_JPY を発火させないため強制適用はない。将来 ALL に広げるなら pair-regime fit は未検証で、既存 artifact からは判断不能。 |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) としての主破綻候補は Axis 3。Axis 2 は順張り再加速を数学的に捕捉し、Axis 4 の H1/M15/M5 フィルタは thesis を強化し、Axis 5 の `1.0ATR : 1.8ATR` は momentum scalp と整合する。一方で、1m 確認が current bar の `ctx.entry > ctx.open_price` / `ctx.entry < ctx.open_price` と MACD-H 増減に依存し、strategy 内に bar-close gating と dedup key がないため、BT の bar-close 仮定と live evaluation の intrabar 挙動がズレるリスクがある。

再設計案は `closed-bar M5 breakout + next-bar 1m confirmation + per-bar dedup`。M5 EMA21 再ブレイクと 1m candle/MACD-H 確認を確定足のみで評価し、entry は次 bar execution に分離する。Candidate または上位 execution 層に `(entry_type, symbol, signal, signal_bar_time)` を渡して同一 bar 多重発火を止める。filter と stop/TP は現行維持でよいが、Phase B 判定では Tokyo/London decay が観測済みなので、まず NY-only または Tokyo+NY 限定で closed-bar 版の既存 BT/Shadow 指標を再集計する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想と trigger/filter/stop の骨格は維持する。修正対象は timing の 1 系統で、`ctx.entry > ctx.open_price` / `ctx.entry < ctx.open_price` と `ctx.macdh` 増減を評価する足を「直近確定 1m bar」に固定し、発注は次 bar 以降にする。M5 側も `m5_close` が確定済みであることをコンテキスト契約に明示し、未確定 M5 snapshot なら発火させない。

コードレベルでは、SignalContext に `bar_time` / `is_closed` 相当があるなら `if not ctx.is_closed: return None` を entry 条件前に置き、Candidate に signal bar id を含めるか上位層の dedup key に `entry_type + symbol + signal + bar_time` を使う。既存の H1 EMA200、M15 perfect order、ADX、RR は変更しない。採用前に必要な artifact は closed-bar 版の USD_JPY Tokyo/NY 365d または少なくとも pre-reg 同等 180d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction、Shadow live N>=30 の同一 source 再集計。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master 365d BT: `—`; local `demo_trades.db` exact rows: 0; pre-reg USD_JPY 180d v1b ALL: 369; Tokyo: 91; London: 99; NY: 124 | `knowledge-base/wiki/tier-master.md`; local `demo_trades.db`; `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; `knowledge-base/wiki/strategies/ma_generic_family_v1.md` |
| Win rate | pre-reg USD_JPY 180d v1b ALL: 60.7%; Tokyo: 73.6%; London: 59.6%; NY: 61.3% | `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; `knowledge-base/wiki/strategies/ma_generic_family_v1.md` |
| Wilson lo (95%) | pre-reg USD_JPY 180d v1b ALL: 55.64%; Tokyo: 63.75%; London: 49.75%; NY: 52.50%; current live/audit DB exact ma_trend_perfect: INSUFFICIENT_EVIDENCE (0 rows found locally) | `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; local `demo_trades.db` |
| PF | pre-reg USD_JPY 180d v1b ALL: 1.99; Tokyo: 3.84; London: 1.97; NY: 2.19; tier-master 365d: INSUFFICIENT_EVIDENCE (`—`) | `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | f1 N=123 WR=64.2% PF=2.18 Kelly=34.7% p=0.012; f2 N=123 WR=61.8% PF=2.20 Kelly=33.7% p=0.005; f3 N=123 WR=56.1% PF=1.67 Kelly=22.4% p=0.146; all folds PF>1.3. 365d current tier-master WF: INSUFFICIENT_EVIDENCE | `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; `knowledge-base/wiki/strategies/ma_generic_family_v1.md` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE as stored metric. Available evidence uses raw p and BH: Tokyo p=0.00001 and NY p=0.005 pass 3-cell BH; London p=0.0503 misses; strategy-level 4-cell grouping has 0 BH-pass with ma_trend_perfect p=0.038 above BH threshold 0.0125. | `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; `knowledge-base/wiki/strategies/ma_generic_family_v1.md` |
| Kelly fraction | pre-reg USD_JPY 180d v1b ALL: 30.2%; Tokyo: 54.5%; London: 29.4%; NY: 33.3%; current live/audit DB exact ma_trend_perfect: INSUFFICIENT_EVIDENCE (0 rows found locally) | `knowledge-base/wiki/decisions/pre-reg-ma-trend-perfect-2026-04-30.md`; local `demo_trades.db` |
