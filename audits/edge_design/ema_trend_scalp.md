---
strategy: ema_trend_scalp
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

トレンド中間帯で EMA21 付近への押し目/戻りを待ち、ローソク足の反発確認後に EMA9/EMA21 の方向へ順張りで入る trend-pullback scalp。BB 極端の MR と BB breakout の GAP を埋める設計として、ADX と BB%B の中間帯を明示している。`strategies/scalp/ema_trend_scalp.py:12`, `strategies/scalp/ema_trend_scalp.py:13`, `strategies/scalp/ema_trend_scalp.py:14`, `strategies/scalp/ema_trend_scalp.py:15`, `strategies/scalp/ema_trend_scalp.py:23`, `strategies/scalp/ema_trend_scalp.py:24`, `strategies/scalp/ema_trend_scalp.py:25`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / trend-pullback thesis に対し、BUY は `adx >= 15 AND ema9 > ema21 AND ema21 - 0.7ATR <= entry <= ema21 + 1.0ATR AND entry > open_price AND 30 <= RSI5 <= 65 AND 0.25 <= BB%B <= 0.75`、SELL は `ema9 < ema21` と `entry < open_price` の対称条件。EMA alignment、ADX minimum、EMA21 pullback zone、candle bounce、RSI/BBPB bounded pullback がそろっており、MR の oversold 単独 trigger ではない。`strategies/scalp/ema_trend_scalp.py:50`, `strategies/scalp/ema_trend_scalp.py:55`, `strategies/scalp/ema_trend_scalp.py:56`, `strategies/scalp/ema_trend_scalp.py:59`, `strategies/scalp/ema_trend_scalp.py:60`, `strategies/scalp/ema_trend_scalp.py:64`, `strategies/scalp/ema_trend_scalp.py:66`, `strategies/scalp/ema_trend_scalp.py:67`, `strategies/scalp/ema_trend_scalp.py:102`, `strategies/scalp/ema_trend_scalp.py:119`, `strategies/scalp/ema_trend_scalp.py:120`, `strategies/scalp/ema_trend_scalp.py:121`, `strategies/scalp/ema_trend_scalp.py:122`, `strategies/scalp/ema_trend_scalp.py:124`, `strategies/scalp/ema_trend_scalp.py:127`, `strategies/scalp/ema_trend_scalp.py:130`, `strategies/scalp/ema_trend_scalp.py:152`, `strategies/scalp/ema_trend_scalp.py:155`, `strategies/scalp/ema_trend_scalp.py:157`, `strategies/scalp/ema_trend_scalp.py:160`, `strategies/scalp/ema_trend_scalp.py:163` |
| 3 (timing window) | LOOKAHEAD | Bounce 判定が current `ctx.entry` と `ctx.open_price` の同一足比較で、strategy 内には確定足限定、signal bar timestamp、または `(symbol, direction, bar_time)` dedup がない。実行層が未確定足で `evaluate()` を複数回呼ぶ場合、bar close 前の陽線/陰線化で entry し、同一 bar で再発火するリスクが残る。Candidate 返却にも signal bar id は含まれない。`strategies/scalp/ema_trend_scalp.py:122`, `strategies/scalp/ema_trend_scalp.py:124`, `strategies/scalp/ema_trend_scalp.py:142`, `strategies/scalp/ema_trend_scalp.py:155`, `strategies/scalp/ema_trend_scalp.py:157`, `strategies/scalp/ema_trend_scalp.py:175`, `strategies/scalp/ema_trend_scalp.py:254`, `strategies/scalp/ema_trend_scalp.py:260` |
| 4 (filter coherence) | BREAKS | ADX minimum、EMA9/21 direction、RSI5 bounded range、BB%B 中間帯、EMA50/MACD/DI bonuses は trend pullback thesis を概ね STRENGTHENS。ただし `ADX>=30` を score bonus にする一方、同じ file は `ADX>31` で pullback が発達しないため sharp penalty と記述し、`apply_penalty(..., strategy_type="pullback", ctx.adx)` で後段補正している。強トレンドを entry quality として報酬しつつ、同時に pullback anti-trend として罰するため filter/score 設計が矛盾している。これは MR に MA filter を重ねる `feedback_ma_filter_breaks_mr.md` そのものではないが、edge が依存する regime tail を generic trend gate で壊す `feedback_hmm_gate_same_trap.md` 型に近い。`strategies/scalp/ema_trend_scalp.py:43`, `strategies/scalp/ema_trend_scalp.py:50`, `strategies/scalp/ema_trend_scalp.py:59`, `strategies/scalp/ema_trend_scalp.py:60`, `strategies/scalp/ema_trend_scalp.py:64`, `strategies/scalp/ema_trend_scalp.py:66`, `strategies/scalp/ema_trend_scalp.py:67`, `strategies/scalp/ema_trend_scalp.py:102`, `strategies/scalp/ema_trend_scalp.py:200`, `strategies/scalp/ema_trend_scalp.py:201`, `strategies/scalp/ema_trend_scalp.py:205`, `strategies/scalp/ema_trend_scalp.py:213`, `strategies/scalp/ema_trend_scalp.py:221`, `strategies/scalp/ema_trend_scalp.py:229`, `strategies/scalp/ema_trend_scalp.py:243`, `strategies/scalp/ema_trend_scalp.py:244`, `strategies/scalp/ema_trend_scalp.py:245`, `strategies/scalp/ema_trend_scalp.py:248` |
| 5 (stop/TP geometry) | ALIGNED | Nominal SL は `1.0ATR7`、TP は `1.8ATR7`、floor 適用時も `max(1.8ATR, 1.2R)` で RR を維持する。BUY は `sl = entry - sl_dist, tp = entry + tp_dist`、SELL は対称で、trend continuation の asymmetric payoff と整合する。`strategies/scalp/ema_trend_scalp.py:71`, `strategies/scalp/ema_trend_scalp.py:72`, `strategies/scalp/ema_trend_scalp.py:73`, `strategies/scalp/ema_trend_scalp.py:74`, `strategies/scalp/ema_trend_scalp.py:112`, `strategies/scalp/ema_trend_scalp.py:145`, `strategies/scalp/ema_trend_scalp.py:146`, `strategies/scalp/ema_trend_scalp.py:147`, `strategies/scalp/ema_trend_scalp.py:148`, `strategies/scalp/ema_trend_scalp.py:149`, `strategies/scalp/ema_trend_scalp.py:178`, `strategies/scalp/ema_trend_scalp.py:179`, `strategies/scalp/ema_trend_scalp.py:180`, `strategies/scalp/ema_trend_scalp.py:181`, `strategies/scalp/ema_trend_scalp.py:182`, `strategies/scalp/ema_trend_scalp.py:190`, `strategies/scalp/ema_trend_scalp.py:192` |
| 6 (pair-regime fit) | FORCED | Strategy file は EURGBP のみ除外し、その他 pair は ALL に強制適用する。既存 evidence は EUR_USD / GBP_USD / USD_JPY の shadow・live が明確に negative、GBP_JPY だけが BT で一貫 positive だが shadow N 不足。下の pair-regime table 参照。`strategies/scalp/ema_trend_scalp.py:76`, `strategies/scalp/ema_trend_scalp.py:77`, `strategies/scalp/ema_trend_scalp.py:95`, `strategies/scalp/ema_trend_scalp.py:96` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative | tier-master の force_demoted 行は 365d BT EV が `—`。local `demo_trades.db` は `demo_trades` / `evaluated_candidates` / `oanda_audit` に exact `ema_trend_scalp` 行が 0 件。既存 audit artifact では by-strategy N=72, WR=23.61%, Wilson lo=15.30%, EV=-1.431p, PF=0.518 があり、H1 3month shadow でも多くの pair/hour bucket が Bonferroni significant negative。ただし ALL cell の WF folds>=3 と同一 artifact 上の aggregate Bonferroni/Kelly が揃わないため、`feedback_partial_quant_trap.md` 基準では redesign 採用判断には不足。 |

### Pair-Regime Table

| Pair / bucket | Verdict | Evidence |
|---------------|---------|----------|
| EUR_USD | FORCED | 5m 365d BT N=321, WR=56.7%, EV=-0.132。1m 180d BT N=673, WR=60.0%, EV=-0.191。Shadow/live も EUR_USD は負 EV 方向で一致し、H1 3month shadow は London N=139, WR=25.18%, PF=0.657, Kelly=-0.132, Bonferroni p=1.05e-6、NY-overlap N=120, WR=21.67%, PF=0.448, Kelly=-0.267, Bonferroni p=1.16e-7。 |
| GBP_USD | FORCED | 5m 365d BT N=406, WR=62.1%, EV=-0.088。1m 180d BT N=907, WR=54.6%, EV=-0.434。H1 3month shadow は London N=71, WR=21.13%, PF=0.539, Kelly=-0.181、NY-overlap N=38, WR=13.16%, PF=0.338, Kelly=-0.257。 |
| USD_JPY | FORCED / TF-dependent | 5m 365d BT は N=400, WR=64.2%, EV=+0.085 だが、1m 180d BT は N=1025, WR=58.9%, EV=-0.208 に反転。Live/shadow pair evidence は USD_JPY EV=-0.9p 付近で悪化し、H1 3month shadow は Asia N=80, WR=23.75%, PF=0.558, Kelly=-0.188。London N=97, WR=32.99%, PF=1.055, Kelly=+0.017 は唯一弱い正候補だが Bonferroni p=0.174 で不足。 |
| GBP_JPY | FIT / insufficient | 5m 365d BT N=459, WR=64.9%, EV=+0.098、1m 180d BT N=1162, WR=65.0%, EV=+0.035 で一貫 positive。ただし tier-master/audit DB の現行 ALL decision-grade evidence と shadow N>=30 が不足し、ALL 復活の根拠にはならない。 |
| EUR_JPY | FORCED | 5m 365d BT N=413, WR=59.8%, EV=-0.055、1m 180d BT N=1076, WR=61.3%, EV=-0.127。 |
| EUR_GBP | FORCED / disabled | Code は EURGBP を構造的不可能として除外し、BT でも発火ゼロ。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) の主破綻軸は Axis 3 と Axis 4、補助的に Axis 6。Axis 2 は EMA21 pullback continuation を数学的に捕捉しており、Axis 5 の `1.0ATR : 1.8ATR` も順張り continuation と整合する。一方、current bar の `entry/open_price` で bounce を見るため live では未確定足・同一 bar 再発火のリスクがあり、さらに強トレンドを `ADX>=30` bonus で報酬しながら `ADX>31` を pullback anti-trend として罰する矛盾がある。既存 evidence でも NY × high-vol / trend 系 cell の WR 15-17% が繰り返し出ており、思想より実装タイミングと regime handling の破綻が濃い。

再設計案は `closed-bar pullback + moderate-trend gate + pair/session scope`。Signal は直近確定足で `ema9 > ema21`、EMA21 zone、candle bounce、RSI/BBPB を評価し、entry は次 bar 以降に限定する。Candidate には少なくとも `(entry_type, symbol, direction, signal_bar_time)` 相当の dedup key を持たせ、同一 bar の再発火を止める。ADX は `15 <= ADX <= 31` を hard gate または score cap にし、`ADX>=30` bonus は削除する。scope は ALL ではなく、まず GBP_JPY と USD_JPY London などの候補 cell に限定して再集計する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は捨てないが、ALL strategy としての復活推奨度は高くない。現行 aggregate は force demoted 相応に negative で、EUR_USD / GBP_USD / USD_JPY 1m は明確に FORCED。復活候補は、BT で一貫 positive の GBP_JPY、または H1 bucket で弱く positive な USD_JPY London のような cell に限るべき。

具体修正は、まず timing を closed-bar 化する。BUY なら `signal_close > signal_open`、`signal_ema9 > signal_ema21`、`signal_ema21 - 0.7ATR <= signal_close <= signal_ema21 + 1.0ATR` を確定足で評価し、次 bar execution に分離する。SELL も対称にする。次に `ADX>=30` bonus を削除し、`ADX > 31` は confidence penalty ではなく no-trade または score cap とする。最後に pair scope を `ALL` から分離し、GBP_JPY / USD_JPY London のみを redesign candidate、EUR_USD / GBP_USD / USD_JPY 1m / NY high-vol は block candidate として扱う。

本 audit では新規 BT は実行しない。採用前に必要な artifact は、closed-bar + scoped cell 版の 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 tier/audit source で出すこと。N/WR/EV や単発 positive BT だけでは `feedback_partial_quant_trap.md` 基準を満たさない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master ALL 365d BT: `—`; local `demo_trades.db` exact rows: 0; audit by-strategy shadow negative: N=72; daily latest net-edge row: N=79; older live all-time: N=39; 5m 365d BT pair sum excluding EURGBP: N=1999 | `knowledge-base/wiki/tier-master.md`; local `demo_trades.db`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `raw/audits/daily_live_latest.json`; `knowledge-base/wiki/analyses/ema-tr-live-breakdown-2026-04-20.md`; `knowledge-base/wiki/analyses/ema-tr-365d-bt-2026-04-20.md` |
| Win rate | audit by-strategy shadow: 23.61%; daily latest: 20.3%; older live all-time: 23.1%; 5m 365d BT varies by pair from 56.7% to 64.9% but EV is mixed/negative for 3 of 5 active pairs | same as above |
| Wilson lo (95%) | audit by-strategy shadow: 15.30%; daily latest: 12.9%; key negative cells include London/q0 12.83% and Overlap/q0 7.60%; H1 3month shadow buckets include EUR_USD London 18.70%, EUR_USD NY-overlap 15.24%, GBP_USD NY-overlap 5.75% | `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; `raw/audits/daily_live_latest.json`; `raw/audits/cell_edge_audit_2026-05-02_v1_365d_inclshadow.json`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| PF | audit by-strategy shadow: 0.518; London/q0: 0.602; Overlap/q0: 0.327; H1 3month negative buckets range roughly 0.338-0.657, with USD_JPY London 1.055 as weak positive exception | same as above |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: tier-master/audit DB do not provide >=3 WF folds for the ALL cell or redesigned scoped cell. Existing H1 artifact has `is_n=0` and `oos_n` only, not three valid WF folds. | tier-master + audit DB artifacts |
| Bonferroni-adj p | aggregate ALL: INSUFFICIENT_EVIDENCE in tier-master/audit DB; negative cell evidence exists: London/q0 p_bonf=0.00925, Overlap/q0 p_bonf=0.00126, H1 EUR_USD London p_bonf=1.05e-6, EUR_USD NY-overlap p_bonf=1.16e-7, GBP_USD London p_bonf=0.000246, GBP_USD NY-overlap p_bonf=0.00120, USD_JPY Asia p_bonf=0.000574 | `raw/audits/cell_edge_audit_2026-05-02_v1_365d_inclshadow.json`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| Kelly fraction | audit by-strategy aggregate Kelly: INSUFFICIENT_EVIDENCE in current tier-master; negative cell evidence includes Phase 4d V6 R2_trend_down__V_high__NY Kelly=-0.220 and R1_trend_up__V_high__NY Kelly=-0.269; H1 3month shadow buckets include EUR_USD London -0.132, EUR_USD NY-overlap -0.267, GBP_USD London -0.181, GBP_USD NY-overlap -0.257, USD_JPY Asia -0.188, with USD_JPY London +0.017 as weak exception | `knowledge-base/wiki/analyses/phase4d-v6-cell-edge-test-result-2026-04-24.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/wiki/tier-master.md` |
