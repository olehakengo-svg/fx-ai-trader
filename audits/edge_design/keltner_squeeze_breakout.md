---
strategy: keltner_squeeze_breakout
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

1H 足で Bollinger Band が Keltner Channel 内へ収縮した後、スクイーズ解除足の Keltner 方向ブレイク、実体比率、MACD-H 加速、ADX 上昇で「ボラティリティ圧縮後の momentum breakout」を捕捉する思想。SL/TP コメントもスクイーズ swing と ATR 目標、BE/trailing を前提にしており、MR ではなく breakout continuation thesis としてコードから導出可能。`strategies/hourly/keltner_squeeze_breakout.py:10`, `strategies/hourly/keltner_squeeze_breakout.py:11`, `strategies/hourly/keltner_squeeze_breakout.py:12`, `strategies/hourly/keltner_squeeze_breakout.py:22`, `strategies/hourly/keltner_squeeze_breakout.py:29`, `strategies/hourly/keltner_squeeze_breakout.py:32`, `strategies/hourly/keltner_squeeze_breakout.py:39`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum breakout thesis に対し、前 N 本の `squeeze_on=True` を数え、現在足で `squeeze_on=False`、`BUY: Close > kelt_mid + (kelt_upper-kelt_mid)*0.80` / `SELL: Close < kelt_mid - (kelt_mid-kelt_lower)*0.80` を要求する。さらに `body_ratio >= 0.35`、BUY 陽線 / SELL 陰線、`BUY: macdh > 0 AND macdh_prev < macdh` / `SELL: macdh < 0 AND macdh_prev > macdh`、`adx >= 15 OR adx - prev_adx >= 2` を確認しており、oversold 反転ではなく圧縮後の方向放出を数学的に捕捉している。`strategies/hourly/keltner_squeeze_breakout.py:116`, `strategies/hourly/keltner_squeeze_breakout.py:124`, `strategies/hourly/keltner_squeeze_breakout.py:131`, `strategies/hourly/keltner_squeeze_breakout.py:149`, `strategies/hourly/keltner_squeeze_breakout.py:150`, `strategies/hourly/keltner_squeeze_breakout.py:152`, `strategies/hourly/keltner_squeeze_breakout.py:153`, `strategies/hourly/keltner_squeeze_breakout.py:165`, `strategies/hourly/keltner_squeeze_breakout.py:169`, `strategies/hourly/keltner_squeeze_breakout.py:177`, `strategies/hourly/keltner_squeeze_breakout.py:180`, `strategies/hourly/keltner_squeeze_breakout.py:196` |
| 3 (timing window) | LOOKAHEAD | 判定は `ctx.df.iloc[-1]` と `ctx.entry` / `ctx.open_price` の現在足 Close/Open を直接使うため、実行層が未確定 1H 足で `evaluate()` を呼ぶと intrabar の暫定 squeeze release / break / body ratio で emit できる。strategy 内には `ctx.bar_time` や closed-bar flag の検査、同一 `(symbol, strategy, bar)` の per-bar dedup がなく、bar-close 前の変化や同一 bar 多重 entry を strategy 単体では防げない。`strategies/hourly/keltner_squeeze_breakout.py:141`, `strategies/hourly/keltner_squeeze_breakout.py:144`, `strategies/hourly/keltner_squeeze_breakout.py:145`, `strategies/hourly/keltner_squeeze_breakout.py:161`, `strategies/hourly/keltner_squeeze_breakout.py:191`, `strategies/hourly/keltner_squeeze_breakout.py:328`, `strategies/hourly/keltner_squeeze_breakout.py:329` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | `MIN_SQUEEZE_BARS` / `MAX_SQUEEZE_BARS` は圧縮が短すぎる noise と長すぎる dead market を落とすため STRENGTHENS。実体比率、MACD-H 方向一致と拡大、ADX 水準または上昇は breakout momentum を補強するため STRENGTHENS。HTF 逆方向 hard block は「上位足と完全逆の放出」を避ける filter で概ね STRENGTHENS だが、HMM regime gate same-trap の先行例と同様に、regime transition 初動を削る可能性があるため要検証。EMA200 は hard gate ではなく soft penalty なので、MA filter on MR strategy の先行例のような thesis 破壊には該当しない。JPY 全停止は thesis filter ではなく pair scope / friction 対応で NEUTRAL。`strategies/hourly/keltner_squeeze_breakout.py:60`, `strategies/hourly/keltner_squeeze_breakout.py:62`, `strategies/hourly/keltner_squeeze_breakout.py:68`, `strategies/hourly/keltner_squeeze_breakout.py:71`, `strategies/hourly/keltner_squeeze_breakout.py:73`, `strategies/hourly/keltner_squeeze_breakout.py:89`, `strategies/hourly/keltner_squeeze_breakout.py:90`, `strategies/hourly/keltner_squeeze_breakout.py:165`, `strategies/hourly/keltner_squeeze_breakout.py:177`, `strategies/hourly/keltner_squeeze_breakout.py:196`, `strategies/hourly/keltner_squeeze_breakout.py:204`, `strategies/hourly/keltner_squeeze_breakout.py:209`, `strategies/hourly/keltner_squeeze_breakout.py:291` |
| 5 (stop/TP geometry) | MISALIGNED | SL は squeeze 期間の swing low/high から ATR×0.3 外側、ただし最大 ATR×1.5 に cap。TP は `max(ATR×3.0, SL距離×1.5)` で最低 R:R=1.5 を保証するため固定 TP の非対称 payoff はある。一方、コードコメントと breakout geometry は BE/trailing 前提だが、`BE_TRIGGER_PCT` と `TRAIL_ATR_MULT` は Candidate に渡されず、この file 内の返却値は fixed SL/TP のみ。圧縮後の大きな trend continuation を取りに行く breakout thesis に対して、trailing が未接続で winner を早く固定 TP で切る設計になっている。`strategies/hourly/keltner_squeeze_breakout.py:40`, `strategies/hourly/keltner_squeeze_breakout.py:42`, `strategies/hourly/keltner_squeeze_breakout.py:43`, `strategies/hourly/keltner_squeeze_breakout.py:76`, `strategies/hourly/keltner_squeeze_breakout.py:77`, `strategies/hourly/keltner_squeeze_breakout.py:79`, `strategies/hourly/keltner_squeeze_breakout.py:82`, `strategies/hourly/keltner_squeeze_breakout.py:83`, `strategies/hourly/keltner_squeeze_breakout.py:232`, `strategies/hourly/keltner_squeeze_breakout.py:236`, `strategies/hourly/keltner_squeeze_breakout.py:247`, `strategies/hourly/keltner_squeeze_breakout.py:249`, `strategies/hourly/keltner_squeeze_breakout.py:329` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。入力 scope は `ALL` だが、実装は `ctx.is_jpy` を即 `return None` にするため JPY pair は BLOCKED。非 JPY は `EUR` パラメータ名で一括扱いされ、EURUSD 以外の non-JPY major への calibrate 根拠はこの file からは確認できない。`strategies/hourly/keltner_squeeze_breakout.py:89`, `strategies/hourly/keltner_squeeze_breakout.py:90`, `strategies/hourly/keltner_squeeze_breakout.py:103`, `strategies/hourly/keltner_squeeze_breakout.py:108`, `strategies/hourly/keltner_squeeze_breakout.py:109`, `strategies/hourly/keltner_squeeze_breakout.py:110` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow 行は `PP/EL未指定 → 自動Shadow` で 365d BT EV/PF/WF/Kelly が `—`。audit DB (`demo_trades.entry_type`, `oanda_audit.entry_type`) は `keltner_squeeze_breakout` N=0。`feedback_partial_quant_trap.md` 基準の Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は既存 source から decision-grade に埋まらない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED / BLOCKED | JPY pair は即 `return None`。コードコメント上も WR=33.3%, EV=+2.2pip は実環境 friction で負 EV 転落リスクとされる。`strategies/hourly/keltner_squeeze_breakout.py:89`, `strategies/hourly/keltner_squeeze_breakout.py:90`, `strategies/hourly/keltner_squeeze_breakout.py:91` |
| EURUSD | FIT / INSUFFICIENT_EVIDENCE | 非 JPY 側の主要想定 pair として実装上は通るが、tier-master と audit DB に Wilson/PF/WF/Kelly がない。`strategies/hourly/keltner_squeeze_breakout.py:108`, `strategies/hourly/keltner_squeeze_breakout.py:109`, `strategies/hourly/keltner_squeeze_breakout.py:110` |
| GBPUSD | FORCED / INSUFFICIENT_EVIDENCE | 非 JPY なので実装上は EUR パラメータで通るが、GBPUSD 固有の squeeze length / ATR / session fit はこの file で校正されていない。`strategies/hourly/keltner_squeeze_breakout.py:61`, `strategies/hourly/keltner_squeeze_breakout.py:72`, `strategies/hourly/keltner_squeeze_breakout.py:78`, `strategies/hourly/keltner_squeeze_breakout.py:108` |
| EURJPY / GBPJPY | FORCED / BLOCKED | JPY pair は thesis の適否以前に signal universe から除外される。`strategies/hourly/keltner_squeeze_breakout.py:89`, `strategies/hourly/keltner_squeeze_breakout.py:90`, `strategies/hourly/keltner_squeeze_breakout.py:91` |
| Other non-JPY | FORCED / INSUFFICIENT_EVIDENCE | `ctx.is_jpy == False` なら EUR 側パラメータで一括通過するが、ALL pair strategy としての pair-regime fit は未実証。`strategies/hourly/keltner_squeeze_breakout.py:103`, `strategies/hourly/keltner_squeeze_breakout.py:108`, `strategies/hourly/keltner_squeeze_breakout.py:111` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) で Tier 3/4 ではないが、metrics が `—` / N=0 で昇格判断不能なため failure mode を診断する。Axis 2 は破綻していない。思想は明確で、trigger は squeeze release breakout を直接捉えている。Axis 4 も、HTF hard block の same-trap リスクは残るが、現時点で thesis を破壊する MA-on-MR 型の明確な BREAKS ではない。

破綻は Axis 3 と Axis 5。Axis 3 は strategy 内で closed 1H bar と per-bar dedup を保証せず、現在足の `ctx.entry` / `ctx.df.iloc[-1]` に依存して emit する点。Axis 5 は breakout thesis に必要な BE/trailing がコメントと定数だけで、Candidate 返却値に接続されていない点。再設計案は、(1) signal 判定を確定済み 1H bar のみに固定し、同一 `(instrument, strategy, bar_time)` の再 emit を抑止する、(2) fixed TP を「初期 target + BE + trailing」に変更し、TP 到達前後の winner を trailing で伸ばせる geometry にする、の 2 点である。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

Trigger の核は維持する。`_sq_count >= _min_sq`、`_curr_squeeze == False`、Keltner 80% break、body ratio、MACD-H 加速、ADX rising の条件は breakout thesis と整合しているため、ここを大きく変える必要はない。修正優先は timing で、`evaluate()` が未確定足で呼ばれる live 経路では `return None` にし、確定済み bar_time を使って同一 bar の `Candidate` 再発行を禁止する。BT でも close signal を同じ close で約定させていないかを既存 harness 側で確認する必要がある。

Stop/TP は breakout 用に再接続する。現行の swing SL + ATR cap は初期 stop として残し、TP は固定 ATR×3.0 だけで終了させず、`BE_TRIGGER_PCT=0.50` 到達で BE+1pip、以降は直近 N 本 high/low ± `TRAIL_ATR_MULT` で trailing する設計に寄せる。コードレベルでは Candidate が trailing metadata を持たないため、`Candidate` 拡張または execution layer の strategy-specific exit policy に `be_trigger`, `trail_atr_mult`, `trail_lookback` を渡す設計が必要。

最後に scope を `ALL` のまま扱わない。現行実装は JPY を全停止し、非 JPY を EUR パラメータで一括処理しているため、audit / tier-master 上は少なくとも `EURUSD`、`GBPUSD`、`JPY_BLOCKED` を分ける。採用前に必要な既存 pipeline 再集計は、pair 別 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction である。本 audit では新規 BT は実行していない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 0 (`demo_trades.entry_type = keltner_squeeze_breakout`; `oanda_audit.entry_type = keltner_squeeze_breakout`) | audit DB: `demo_trades.db` |
| Win rate | INSUFFICIENT_EVIDENCE (N=0) | audit DB: `demo_trades.db` |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE (N=0; CI 算出対象なし) | audit DB: `demo_trades.db` |
| PF | INSUFFICIENT_EVIDENCE (tier-master 365d BT EV/PF は `—`) | `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE (target strategy の WF folds>=3 は既存 source で確認できず) | tier-master / existing audit artifacts |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE (N=0; tier-master に該当値なし) | audit DB: `demo_trades.db`; `knowledge-base/wiki/tier-master.md` |
| Kelly fraction | INSUFFICIENT_EVIDENCE (N=0; PF/WR 不在) | audit DB: `demo_trades.db`; `knowledge-base/wiki/tier-master.md` |
