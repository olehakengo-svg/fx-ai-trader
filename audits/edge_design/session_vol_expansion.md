---
strategy: session_vol_expansion
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

アジア時間の低ボラ圧縮後、UTC 07:00-08:30 のロンドンオープンで直近レンジを実体のある足が EMA 方向へブレイクすると、セッション遷移のボラティリティ拡大で同方向に continuation するという EUR/USD session volatility expansion thesis。コードはアジア圧縮、ロンドン直後のレンジブレイク、EMA 方向確認、低スプレッドを明示している。`strategies/scalp/session_vol_expansion.py:2`, `strategies/scalp/session_vol_expansion.py:14`, `strategies/scalp/session_vol_expansion.py:15`, `strategies/scalp/session_vol_expansion.py:16`, `strategies/scalp/session_vol_expansion.py:17`, `strategies/scalp/session_vol_expansion.py:18`, `strategies/scalp/session_vol_expansion.py:20`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Thesis は compression breakout だが、実装上の breakout 条件は `BUY: ctx.entry > max(High[-30:])` / `SELL: ctx.entry < min(Low[-30:])`。`_range_slice = ctx.df.iloc[-self.lookback_range:]` が signal 判定対象の直近 30 本を含み、その高安を `_range_high/_range_low` にした後で `ctx.entry` と比較するため、`ctx.df` が current bar を含む通常の context では close が同一 bar を含む max high を上抜ける条件になり、数学的にほぼ発火不能になる。意図は「確定済み直近レンジの外側への break」なので、比較対象は少なくとも signal bar を除いた `High[-31:-1]` / `Low[-31:-1]` であるべき。`strategies/scalp/session_vol_expansion.py:43`, `strategies/scalp/session_vol_expansion.py:109`, `strategies/scalp/session_vol_expansion.py:110`, `strategies/scalp/session_vol_expansion.py:111`, `strategies/scalp/session_vol_expansion.py:112`, `strategies/scalp/session_vol_expansion.py:124`, `strategies/scalp/session_vol_expansion.py:136` |
| 3 (timing window) | LOOKAHEAD | 判定は `ctx.entry` と `ctx.open_price` で signal bar の実体を測り、同じ `ctx.entry` で Candidate を返す。strategy 内には closed-bar flag、次 bar 約定、または同一 `(symbol, strategy, bar_time)` の per-bar dedup がない。さらに compression window と breakout range が `ctx.df.iloc[-...]` の末尾を使うため、呼び出し側が未確定 bar を渡すと intrabar の高安・実体で発火/消滅し、同一 London window 内の多重 entry も strategy 単体では防げない。`strategies/scalp/session_vol_expansion.py:92`, `strategies/scalp/session_vol_expansion.py:93`, `strategies/scalp/session_vol_expansion.py:98`, `strategies/scalp/session_vol_expansion.py:109`, `strategies/scalp/session_vol_expansion.py:110`, `strategies/scalp/session_vol_expansion.py:113`, `strategies/scalp/session_vol_expansion.py:114`, `strategies/scalp/session_vol_expansion.py:115`, `strategies/scalp/session_vol_expansion.py:124`, `strategies/scalp/session_vol_expansion.py:136`, `strategies/scalp/session_vol_expansion.py:170` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | 時間帯 filter `07:00-08:30 UTC` は thesis の London open volatility expansion を直接絞るため STRENGTHENS。JPY 除外はコード上の EUR/USD 専用思想とは整合するが、ALL cell に対しては pair scope filter なので NEUTRAL。live spread <=0.5pip は London open の friction を抑えるため STRENGTHENS。Asia range lower bound、compression ratio <=0.6、body ratio >=0.50、EMA9/21 方向一致は breakout continuation を補強するため STRENGTHENS。ADX と HTF は hard gate ではなく score bonus なので STRENGTHENS 寄りの soft filter。MR thesis ではないため、先行例の MA filter on MR strategy のような BREAKS ではない。HMM regime gate も存在しないため same-trap 型 BREAKS は確認されない。`strategies/scalp/session_vol_expansion.py:34`, `strategies/scalp/session_vol_expansion.py:35`, `strategies/scalp/session_vol_expansion.py:40`, `strategies/scalp/session_vol_expansion.py:44`, `strategies/scalp/session_vol_expansion.py:45`, `strategies/scalp/session_vol_expansion.py:52`, `strategies/scalp/session_vol_expansion.py:58`, `strategies/scalp/session_vol_expansion.py:59`, `strategies/scalp/session_vol_expansion.py:66`, `strategies/scalp/session_vol_expansion.py:73`, `strategies/scalp/session_vol_expansion.py:76`, `strategies/scalp/session_vol_expansion.py:89`, `strategies/scalp/session_vol_expansion.py:106`, `strategies/scalp/session_vol_expansion.py:115`, `strategies/scalp/session_vol_expansion.py:126`, `strategies/scalp/session_vol_expansion.py:138`, `strategies/scalp/session_vol_expansion.py:157`, `strategies/scalp/session_vol_expansion.py:164` |
| 5 (stop/TP geometry) | MISALIGNED | TP は fixed `ATR * 3.0`、SL は Asia range 反対端から `ATR * 0.3` 外側。BUY の実効 R:R は `reward = 3.0ATR`, `risk = entry - asia_low + 0.3ATR`、SELL は `reward = 3.0ATR`, `risk = asia_high - entry + 0.3ATR` で、Asia range が広いほど R:R が圧迫される。Breakout thesis なら trailing / BE / session time stop で winner を伸ばす geometry が自然だが、この strategy が返す Candidate は fixed SL/TP のみで、`max_hold_bars` も Candidate に接続されていない。`strategies/scalp/session_vol_expansion.py:47`, `strategies/scalp/session_vol_expansion.py:48`, `strategies/scalp/session_vol_expansion.py:49`, `strategies/scalp/session_vol_expansion.py:54`, `strategies/scalp/session_vol_expansion.py:55`, `strategies/scalp/session_vol_expansion.py:132`, `strategies/scalp/session_vol_expansion.py:133`, `strategies/scalp/session_vol_expansion.py:144`, `strategies/scalp/session_vol_expansion.py:145`, `strategies/scalp/session_vol_expansion.py:170` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。コードコメントは EUR/USD 専用を明示するが、実装は `ctx.is_jpy` だけを除外し、GBPUSD/EURGBP など非JPY全般を EUR/USD パラメータで通す。ALL cell としては forced scope。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow 行は `PP/EL未指定 -> 自動Shadow` で、prompt 入力の 365d BT EV は `—`。local audit DB (`demo_trades`, `oanda_audit`, `evaluated_candidates`) に `session_vol_expansion` の exact strategy row は 0 件。Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は既存 source から decision-grade に埋まらない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_USD | FIT / INSUFFICIENT_EVIDENCE | コード内 thesis は EUR/USD London open compression breakout 専用。pair-regime fit は自然だが、tier-master / audit DB に Wilson/PF/WF/Kelly がない。`strategies/scalp/session_vol_expansion.py:2`, `strategies/scalp/session_vol_expansion.py:8`, `strategies/scalp/session_vol_expansion.py:20` |
| USD_JPY | FORCED / BLOCKED | JPY pair は即 `return None`。ALL input には含まれるが、実装上は signal universe 外。`strategies/scalp/session_vol_expansion.py:58`, `strategies/scalp/session_vol_expansion.py:59`, `strategies/scalp/session_vol_expansion.py:60` |
| EUR_JPY / GBP_JPY | FORCED / BLOCKED | JPY cross も `ctx.is_jpy` gate で除外される。ALL cell との整合はない。`strategies/scalp/session_vol_expansion.py:58`, `strategies/scalp/session_vol_expansion.py:59`, `strategies/scalp/session_vol_expansion.py:60` |
| GBP_USD | FORCED / UNTESTED | 非JPYなので実装上は通るが、EUR/USD 専用コメントと EUR/USD 60日分析だけで GBPUSD 固有の Asia compression / London expansion calibration はない。`strategies/scalp/session_vol_expansion.py:8`, `strategies/scalp/session_vol_expansion.py:20`, `strategies/scalp/session_vol_expansion.py:58` |
| Other non-JPY | FORCED / UNTESTED | `ctx.is_jpy == False` なら通過しうるが、pair-specific session volatility evidence はこの file から確認できない。`strategies/scalp/session_vol_expansion.py:20`, `strategies/scalp/session_vol_expansion.py:58`, `strategies/scalp/session_vol_expansion.py:59` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、phase0_shadow かつ tier-master 365d BT EV `—` の under-evidenced cell なので failure mode を診断する。思想は明確で、Axis 4 の filter 群も大半は thesis を補強している。一方で破綻軸は Axis 2、Axis 3、Axis 5。Axis 2 は breakout trigger が current range high/low を自己参照しており、発火不能または呼び出し側依存の曖昧な条件になっている。Axis 3 は bar-close / next-bar execution / per-bar dedup が strategy 内で保証されない。Axis 5 は fixed ATR TP と Asia opposite-edge SL だけで、breakout continuation 用の trailing geometry がない。

再設計案は、trigger を「確定済みレンジの外側に signal bar close が抜けた」形へ修正すること。具体的には `_range_slice = ctx.df.iloc[-self.lookback_range-1:-1]` で signal bar を除外し、`BUY: close > range_high + max(spread_pip, 0.1ATR)` / `SELL: close < range_low - max(spread_pip, 0.1ATR)` にする。Timing は close 確定後の次 bar execution に寄せ、`(symbol, trade_date, strategy, direction)` または `(symbol, strategy, bar_time)` の dedup を追加して London window 内の再発火を抑止する。Stop/TP は初期 SL を breakout invalidation level または Asia opposite edge に置きつつ、1R 到達で BE、以後 ATR trailing または 08:30/09:00 UTC time stop を持つ設計にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は EUR/USD London open の volatility expansion として明確で、filter の多くも thesis を破壊していない。ただし復活に必要な修正は trigger 1 行では足りず、range 計算、bar-close/next-bar execution、dedup、exit geometry、pair scope をまとめて再設計する必要があるため B とする。

コードレベルでは、まず `_range_slice` と `_recent` が signal bar を含むかを明示的に分離する。Compression は pre-breakout の確定済み bars だけで測り、breakout 判定は signal bar の close/body で評価する。EUR/USD 専用なら `symbol` gate を追加し、ALL cell のままなら GBPUSD など non-JPY を別パラメータ・別 evidence として分離する。

採用前の必要 BT は、EUR_USD 単独と non-JPY 拡張候補を分けた 365d 以上の既存 pipeline 再集計、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact に出す内容。本監査では制約通り新規 BT は実行していない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 0 (`demo_trades.entry_type = session_vol_expansion`; `oanda_audit.entry_type = session_vol_expansion`; `evaluated_candidates.strategy_name/selected_strategy = session_vol_expansion`) | audit DB: `demo_trades.db` |
| Win rate | INSUFFICIENT_EVIDENCE (N=0) | audit DB: `demo_trades.db` |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE (N=0; CI 算出対象なし) | audit DB: `demo_trades.db` |
| PF | INSUFFICIENT_EVIDENCE (tier-master 365d BT EV/PF は `—`; exact PF row なし) | `knowledge-base/wiki/tier-master.md`; prompt tier-master input |
| WF folds (3+) | INSUFFICIENT_EVIDENCE (target strategy の WF folds>=3 は既存 source で確認できず) | tier-master / existing audit artifacts |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE (N=0; multiple-test adjusted p の既存 artifact なし) | audit DB: `demo_trades.db`; tier-master / existing audit artifacts |
| Kelly fraction | INSUFFICIENT_EVIDENCE (N=0; PF/payoff/WR sample 不在) | audit DB: `demo_trades.db`; tier-master / existing audit artifacts |
