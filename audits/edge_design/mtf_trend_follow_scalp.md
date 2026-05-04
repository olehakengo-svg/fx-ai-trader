---
strategy: mtf_trend_follow_scalp
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

M15 で ADX + EMA slope による方向性を確認し、M5 の SMA21 pullback bounce を待って、M1 の micro pivot break と短期 momentum 確認で順張り scalp を取る 15m→5m→1m cascade trend-follow thesis。`strategies/scalp/mtf_trend_follow_scalp.py:1`, `strategies/scalp/mtf_trend_follow_scalp.py:7`, `strategies/scalp/mtf_trend_follow_scalp.py:8`, `strategies/scalp/mtf_trend_follow_scalp.py:9`, `strategies/scalp/mtf_trend_follow_scalp.py:47`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-follow thesis に対し、BUY は `m15_adx >= 22 AND m15_ema9 > m15_ema21 AND m15_slope > 0 AND m5_prev_low <= m5_sma21 + 0.3*m5_atr AND m5_close > m5_prev_close AND 0.20 <= m5_bbpb <= 0.65 AND entry > recent_3bar_high AND macdh > 0 AND macdh > macdh_prev AND stoch_k > stoch_d AND stoch_k < 75 AND entry > open_price`。SELL は符号反転条件。M15 trend 確認、M5 pullback bounce、M1 breakout/momentum が thesis を数学的に捕捉している。`strategies/scalp/mtf_trend_follow_scalp.py:32`, `strategies/scalp/mtf_trend_follow_scalp.py:75`, `strategies/scalp/mtf_trend_follow_scalp.py:80`, `strategies/scalp/mtf_trend_follow_scalp.py:81`, `strategies/scalp/mtf_trend_follow_scalp.py:109`, `strategies/scalp/mtf_trend_follow_scalp.py:111`, `strategies/scalp/mtf_trend_follow_scalp.py:112`, `strategies/scalp/mtf_trend_follow_scalp.py:116`, `strategies/scalp/mtf_trend_follow_scalp.py:118`, `strategies/scalp/mtf_trend_follow_scalp.py:120`, `strategies/scalp/mtf_trend_follow_scalp.py:122`, `strategies/scalp/mtf_trend_follow_scalp.py:140`, `strategies/scalp/mtf_trend_follow_scalp.py:141`, `strategies/scalp/mtf_trend_follow_scalp.py:142`, `strategies/scalp/mtf_trend_follow_scalp.py:145`, `strategies/scalp/mtf_trend_follow_scalp.py:147`, `strategies/scalp/mtf_trend_follow_scalp.py:149`, `strategies/scalp/mtf_trend_follow_scalp.py:151` |
| 3 (timing window) | LOOKAHEAD | 明示的な未来 index 参照はなく、M1 pivot は `df["High"].iloc[-4:-1]` / `df["Low"].iloc[-4:-1]` で current bar を除外している。一方、M5 は `m5_close > m5_prev_close` / `<` を current 5m bounce として評価し、M1 も同じ evaluate 内で `ctx.entry`、`ctx.open_price`、MACD-H、Stoch を読んで即 Candidate を返す。strategy 内に closed-bar 確認、signal bar timestamp、または `(symbol, signal, bar_time)` dedup がないため、BT の bar-close 仮定と live intrabar evaluation がズレ、同一 bar 多重 entry になるリスクがある。`strategies/scalp/mtf_trend_follow_scalp.py:64`, `strategies/scalp/mtf_trend_follow_scalp.py:65`, `strategies/scalp/mtf_trend_follow_scalp.py:66`, `strategies/scalp/mtf_trend_follow_scalp.py:70`, `strategies/scalp/mtf_trend_follow_scalp.py:99`, `strategies/scalp/mtf_trend_follow_scalp.py:100`, `strategies/scalp/mtf_trend_follow_scalp.py:111`, `strategies/scalp/mtf_trend_follow_scalp.py:116`, `strategies/scalp/mtf_trend_follow_scalp.py:118`, `strategies/scalp/mtf_trend_follow_scalp.py:120`, `strategies/scalp/mtf_trend_follow_scalp.py:122`, `strategies/scalp/mtf_trend_follow_scalp.py:141`, `strategies/scalp/mtf_trend_follow_scalp.py:145`, `strategies/scalp/mtf_trend_follow_scalp.py:147`, `strategies/scalp/mtf_trend_follow_scalp.py:149`, `strategies/scalp/mtf_trend_follow_scalp.py:151`, `strategies/scalp/mtf_trend_follow_scalp.py:191` |
| 4 (filter coherence) | STRENGTHENS | Pair gate は USD_JPY/EUR_USD の低スプレッド majors に限定し、hour friction gate は scalp cost を下げるので STRENGTHENS。M15 ADX/EMA/slope は trend thesis を定義し、M5 SMA21 pullback + BB%B mid-zone は trend 中の過熱追随を避け、M1 pivot break + MACD-H + Stoch + candle direction は continuation timing を強化する。MA filter on MR strategy や HMM regime gate same-trap の先行例とは異なり、filter が thesis と逆向きには働いていない。`strategies/scalp/mtf_trend_follow_scalp.py:29`, `strategies/scalp/mtf_trend_follow_scalp.py:30`, `strategies/scalp/mtf_trend_follow_scalp.py:31`, `strategies/scalp/mtf_trend_follow_scalp.py:32`, `strategies/scalp/mtf_trend_follow_scalp.py:33`, `strategies/scalp/mtf_trend_follow_scalp.py:54`, `strategies/scalp/mtf_trend_follow_scalp.py:56`, `strategies/scalp/mtf_trend_follow_scalp.py:60`, `strategies/scalp/mtf_trend_follow_scalp.py:61`, `strategies/scalp/mtf_trend_follow_scalp.py:80`, `strategies/scalp/mtf_trend_follow_scalp.py:81`, `strategies/scalp/mtf_trend_follow_scalp.py:109`, `strategies/scalp/mtf_trend_follow_scalp.py:111`, `strategies/scalp/mtf_trend_follow_scalp.py:112`, `strategies/scalp/mtf_trend_follow_scalp.py:116`, `strategies/scalp/mtf_trend_follow_scalp.py:118`, `strategies/scalp/mtf_trend_follow_scalp.py:120`, `strategies/scalp/mtf_trend_follow_scalp.py:122`, `strategies/scalp/mtf_trend_follow_scalp.py:140`, `strategies/scalp/mtf_trend_follow_scalp.py:141`, `strategies/scalp/mtf_trend_follow_scalp.py:142`, `strategies/scalp/mtf_trend_follow_scalp.py:145`, `strategies/scalp/mtf_trend_follow_scalp.py:147`, `strategies/scalp/mtf_trend_follow_scalp.py:149`, `strategies/scalp/mtf_trend_follow_scalp.py:151`, `strategies/scalp/mtf_trend_follow_scalp.py:173`, `strategies/scalp/mtf_trend_follow_scalp.py:177`, `strategies/scalp/mtf_trend_follow_scalp.py:181` |
| 5 (stop/TP geometry) | ALIGNED | BUY SL は `recent_low - 1pip`、SELL SL は `recent_high + 1pip` の micro-structure stop。TP は BUY `max(m5_swing_high, entry + sl_dist*1.3)`、SELL `min(m5_swing_low, entry - sl_dist*1.3)` で R:R floor は 1.3、さらに TP 幅が ATR7×1.0 未満なら reject。trend-follow scalp として asymmetric continuation を狙う構造で、MR の mean 到達前 tight stop 問題には該当しない。`strategies/scalp/mtf_trend_follow_scalp.py:34`, `strategies/scalp/mtf_trend_follow_scalp.py:35`, `strategies/scalp/mtf_trend_follow_scalp.py:125`, `strategies/scalp/mtf_trend_follow_scalp.py:126`, `strategies/scalp/mtf_trend_follow_scalp.py:129`, `strategies/scalp/mtf_trend_follow_scalp.py:130`, `strategies/scalp/mtf_trend_follow_scalp.py:131`, `strategies/scalp/mtf_trend_follow_scalp.py:132`, `strategies/scalp/mtf_trend_follow_scalp.py:154`, `strategies/scalp/mtf_trend_follow_scalp.py:155`, `strategies/scalp/mtf_trend_follow_scalp.py:158`, `strategies/scalp/mtf_trend_follow_scalp.py:159`, `strategies/scalp/mtf_trend_follow_scalp.py:160`, `strategies/scalp/mtf_trend_follow_scalp.py:161` |
| 6 (pair-regime fit) | FIT / FORCED | Input は `ALL` だが、実装は `_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}` のみ。USD_JPY/EUR_USD は low-friction liquid majors として code-level fit、その他 pairs は audit scope 上は ALL でも実装上 no-trade。pair table below. |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master は SCALP_SENTINEL 所属のみで、prompt-supplied 365d BT EV は `—`。local `demo_trades.db` では `demo_trades` / `evaluated_candidates` / `oanda_audit` の exact `mtf_trend_follow_scalp` 行が 0 件。既存分析には標準 BT が HTF m15/m5 欠落で N=0、別途「修正適用後」180d BT が USD_JPY N=1331 WR=34.2% PF=0.88 EV=-0.55p / EUR_USD N=1093 WR=36.9% PF=0.88 EV=-0.46p とあるが、これは current exact strategy の tier-master/audit DB 指標ではない。Wilson lower / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は decision-grade source から揃わないため、`feedback_partial_quant_trap.md` 基準では統計判断不可。 |

### Pair-Regime Table

| Pair / scope | Verdict | Evidence |
|--------------|---------|----------|
| USD_JPY | FIT / empirically unproven | 実装で許可され、低スプレッド時間帯 gate を持つ。M15 trend + M5 pullback + M1 breakout scalp の対象として thesis と衝突しないが、decision-grade Wilson/PF/Kelly は不足。`strategies/scalp/mtf_trend_follow_scalp.py:29`, `strategies/scalp/mtf_trend_follow_scalp.py:54`, `strategies/scalp/mtf_trend_follow_scalp.py:56`, `strategies/scalp/mtf_trend_follow_scalp.py:60`, `strategies/scalp/mtf_trend_follow_scalp.py:61` |
| EUR_USD | FIT / empirically unproven | 実装で許可され、USD_JPY と同じ low-friction major 前提。code-level fit はあるが、pair-specific decision-grade evidence は不足。`strategies/scalp/mtf_trend_follow_scalp.py:29`, `strategies/scalp/mtf_trend_follow_scalp.py:54`, `strategies/scalp/mtf_trend_follow_scalp.py:56`, `strategies/scalp/mtf_trend_follow_scalp.py:60`, `strategies/scalp/mtf_trend_follow_scalp.py:61` |
| Other pairs in ALL | FORCED / NO-TRADE | Audit input は ALL だが、実装では許可ペア以外を即 return するため、強制適用すると no-trade になる。`strategies/scalp/mtf_trend_follow_scalp.py:29`, `strategies/scalp/mtf_trend_follow_scalp.py:54`, `strategies/scalp/mtf_trend_follow_scalp.py:56`, `strategies/scalp/mtf_trend_follow_scalp.py:57` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 が主で、Axis 7 が検証不足として残る。Axis 2/4/5 は thesis と概ね整合しており、思想は「M15 trend + M5 pullback + M1 continuation break」として明確。ただし current 5m bounce と current 1m momentum/candle を同一 evaluate で読み、strategy 内に bar-close gate と dedup key がないため、BT/Shadow/Live の signal timing がズレる。さらに既存分析では HTF data contract 欠落時に N=0、別修正で gate が緩むと 180d で N=1000 超かつ PF=0.88 に落ちることが記録されており、data contract と timing を固定しないまま trigger を緩めると flood losing 化する。

再設計案は Timing/Data-contract 修正を主軸にする。M15/M5 features は close 済み bar だけを `ctx.htf` に渡す契約にし、M5 pullback bounce も確定済み M5 bar で判定する。M1 micro pivot break は signal bar close で確定し、entry は次 bar open または routing 層の明示 execution price に分離する。Candidate または routing 層には `entry_type + symbol + signal + signal_bar_time` の dedup key を持たせ、同一 signal bar の多重 entry を止める。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

trigger/filter/stop は thesis と大きく衝突していないため、最初に直すべき箇所は timing と data contract。具体的には、`m5_close` / `m5_prev_close` / `m5_prev_low` / `m5_prev_high` がすべて確定 M5 bar 由来であることを context contract に明記し、未確定 HTF なら return ではなく監査可能な reject reason を残す。M1 側も `ctx.entry > recent_high` / `< recent_low`、MACD-H、Stoch、足色を signal bar close 後に評価し、execution は次 bar にずらす。

コードレベルの想定 diff は、entry 条件群の前に `if not ctx.is_closed: return None` 相当を追加し、`Candidate` または上位 routing に `signal_bar_time` を伝播させる方向。既存分析から、単純に 1m oscillator を削る・trigger を緩める redesign は flood losing 化するため避ける。closed-bar + dedup 版で USD_JPY/EUR_USD の 365d BT、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 pipeline で再集計することが Shadow 復帰前の必要条件。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE. tier-master 365d BT: `—`; local `demo_trades.db` exact rows: `demo_trades=0`, `evaluated_candidates=0`, `oanda_audit=0`; existing analysis records standard BT original N=0 due HTF m15/m5 issue, and separate reverted redesign 180d BT as USD_JPY N=1331 / EUR_USD N=1093. | `knowledge-base/wiki/tier-master.md`; local `demo_trades.db`; `knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md` |
| Win rate | INSUFFICIENT_EVIDENCE for current exact strategy. Non-decision side evidence from reverted redesign: USD_JPY 34.2%, EUR_USD 36.9% over 180d. | audit DB / tier-master; `knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md` |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE; no current exact strategy decision-grade trade set. Reverted redesign N/WR is not accepted as current audit DB evidence. | audit DB / tier-master |
| PF | INSUFFICIENT_EVIDENCE in tier-master/audit DB for current exact strategy. Non-decision side evidence from reverted redesign: PF=0.88 on USD_JPY and EUR_USD 180d. | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/tier-master.json`; `knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE; no stored 3+ fold WF artifact for this exact strategy. | audit DB / tier-master |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE; no stored Bonferroni-adjusted p for this exact strategy. | audit DB / tier-master |
| Kelly fraction | INSUFFICIENT_EVIDENCE; local exact rows are 0 and tier-master does not store Kelly for this strategy. | local `demo_trades.db`; `knowledge-base/wiki/tier-master.md` |
