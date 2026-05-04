---
strategy: cpd_divergence
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

EUR_USD と GBP_USD は通常 USD common driver で正相関だが、4h rolling correlation が崩れ、短期 z-spread が極端化した瞬間は、laggard の GBP_USD が数 bar 内に leader の EUR_USD 方向へ収束する、という cross-pair convergence thesis。実装上も GBPUSD だけを trade 対象にし、EURUSD を leader として読む。`strategies/daytrade/cpd_divergence.py:4`, `strategies/daytrade/cpd_divergence.py:5`, `strategies/daytrade/cpd_divergence.py:6`, `strategies/daytrade/cpd_divergence.py:7`, `strategies/daytrade/cpd_divergence.py:42`, `strategies/daytrade/cpd_divergence.py:43`, `strategies/daytrade/cpd_divergence.py:44`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Thesis は「相関 breakdown かつ leader/laggard divergence 後の laggard convergence」。実装は `rolling_corr = corr(EURUSD_ret, GBPUSD_ret, 16)`、`latest_corr < 0.1`、`z_spread = a_z - b_z`、`abs(z_spread) > 2.5` を要求し、`z_spread > 0 -> BUY GBPUSD`, `< 0 -> SELL GBPUSD` として laggard を leader 方向へ建てる。条件式は `corr_16(EUR,GBP) < 0.1 AND |z(EUR_ret_60)-z(GBP_ret_60)| > 2.5`。`strategies/daytrade/cpd_divergence.py:47`, `strategies/daytrade/cpd_divergence.py:48`, `strategies/daytrade/cpd_divergence.py:49`, `strategies/daytrade/cpd_divergence.py:74`, `strategies/daytrade/cpd_divergence.py:83`, `strategies/daytrade/cpd_divergence.py:84`, `strategies/daytrade/cpd_divergence.py:85`, `strategies/daytrade/cpd_divergence.py:90`, `strategies/daytrade/cpd_divergence.py:92`, `strategies/daytrade/cpd_divergence.py:93`, `strategies/daytrade/cpd_divergence.py:94`, `strategies/daytrade/cpd_divergence.py:97`, `strategies/daytrade/cpd_divergence.py:99`, `strategies/daytrade/cpd_divergence.py:104`, `strategies/daytrade/cpd_divergence.py:107` |
| 3 (timing window) | LOOKAHEAD | Trigger は `ctx.df` / leader の最新 bar を `iloc[-1]` で直接使い、strategy 内に closed-bar 固定も `(symbol, bar_time)` dedup もない。実行層が intrabar evaluate すると未確定足の return z と rolling correlation で複数 emit できる。また production fallback は leader cache の `tail(120)` を返すだけで、`ctx.df` の時点以前へ明示的に切っていないため、historical evaluation では leader data alignment が fragile。`strategies/daytrade/cpd_divergence.py:58`, `strategies/daytrade/cpd_divergence.py:77`, `strategies/daytrade/cpd_divergence.py:78`, `strategies/daytrade/cpd_divergence.py:85`, `strategies/daytrade/cpd_divergence.py:92`, `strategies/daytrade/cpd_divergence.py:93`, `strategies/daytrade/cpd_divergence.py:97`, `strategies/daytrade/cpd_divergence.py:99`, `strategies/daytrade/cpd_divergence.py:146`, `strategies/daytrade/cpd_divergence.py:168`, `strategies/daytrade/cpd_divergence.py:171`, `strategies/daytrade/cpd_divergence.py:172` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | GBPUSD 限定は pre-registered laggard thesis を強化する。`len(ctx.df) >= 80`、leader data 必須、finite correlation guard は計算品質 filter なので NEUTRAL から STRENGTHENS。`MIN_RR` と RNR TP shift は execution/geometry filter で、MA filter on MR strategy や HMM regime gate same-trap のように convergence tail を hard reject する filter は見えない。ただし `shift_tp_inside` 後に `rr < 1.4` で落とすため、round-number 近傍の本来有効な convergence を薄く削る可能性はある。`strategies/daytrade/cpd_divergence.py:42`, `strategies/daytrade/cpd_divergence.py:43`, `strategies/daytrade/cpd_divergence.py:60`, `strategies/daytrade/cpd_divergence.py:62`, `strategies/daytrade/cpd_divergence.py:70`, `strategies/daytrade/cpd_divergence.py:71`, `strategies/daytrade/cpd_divergence.py:86`, `strategies/daytrade/cpd_divergence.py:117`, `strategies/daytrade/cpd_divergence.py:120`, `strategies/daytrade/cpd_divergence.py:128`, `strategies/daytrade/cpd_divergence.py:129` |
| 5 (stop/TP geometry) | ALIGNED | Nominal SL=`1.0ATR`, TP=`1.5ATR`、`MIN_RR=1.4` で R:R は約 1.5。2 bar convergence thesis は長く粘る classic MR ではなく短期 laggard-follow event なので、wide stop よりも「短期不発なら切る」非対称 payoff と整合する。`shift_tp_inside` で実効 TP は縮むが、`rr < 1.4` の reject で最低 R:R は保つ。`strategies/daytrade/cpd_divergence.py:19`, `strategies/daytrade/cpd_divergence.py:20`, `strategies/daytrade/cpd_divergence.py:52`, `strategies/daytrade/cpd_divergence.py:53`, `strategies/daytrade/cpd_divergence.py:54`, `strategies/daytrade/cpd_divergence.py:109`, `strategies/daytrade/cpd_divergence.py:111`, `strategies/daytrade/cpd_divergence.py:112`, `strategies/daytrade/cpd_divergence.py:114`, `strategies/daytrade/cpd_divergence.py:115`, `strategies/daytrade/cpd_divergence.py:128`, `strategies/daytrade/cpd_divergence.py:129` |
| 6 (pair-regime fit) | FIT / FORCED | 下の pair table 参照。コードは ALL ではなく GBPUSD 専用で、EURUSD は leader data、他 pairs は `return None`。ALL cell としては FORCED だが、GBP_USD laggard cell としては FIT。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | `raw/cpd_refine` では N=19, WR=73.68%, Wilson lo=51.21%, PF=1.72, Kelly=0.2645 が揃う一方、Bonferroni-adjusted p=1.14422 で不通過、WF folds>=3 はなく quarterly stability も Q2/Q4 の 2 buckets のみ。local audit DB `demo_trades.db` には `cpd_divergence` 行が 0 件で、never-logged 診断も 30,592 eval / 0 signal。`feedback_partial_quant_trap.md` 基準では promotion-grade evidence は不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| GBP_USD | FIT / implementation-silent | Strategy は GBPUSD のみ許可し、EURUSD leader divergence から GBPUSD laggard convergence を取る。`raw/cpd_refine` best は EUR_USD -> GBP_USD で N=19, WR=73.68%, Wilson lo=51.21%, EV_net=+1.00p, PF=1.72。ただし production/audit DB では 0 rows、G1 never-logged 診断では 0/6,140 signals。 |
| EUR_USD | FORCED as traded pair / FIT as leader | EURUSD は `LEADER_SYMBOL` であり trade 対象ではない。ALL 指定で EUR_USD trade を期待するなら FORCED。 |
| EUR_JPY | FORCED | CPD base audit では EUR_JPY -> GBP_JPY が N=199, WR=48.24%, avg_pip=-0.519 で thesis fit なし。現行コードも trade 対象外。 |
| GBP_JPY | FORCED | CPD base audit の JPY cross divergenceは正EVでなく、現行コードも trade 対象外。 |
| USD_JPY | FORCED | CPD base audit の USD_JPY leader variants は EUR_USD/GBP_USD laggard とも avg_pip 負。現行コードも trade 対象外。 |

## Axis 8: failure mode 診断

Tier 2 Shadow だが、tier-master 365d BT EV は `—`、audit DB は 0 rows、G1 never-logged 診断は 30,592 eval / 0 signal なので、underperforming/insufficient cell として failure mode 診断対象にする。

破綻候補は Axis 3 と Axis 6。Axis 2 の trigger は thesis と整合しているが、現在足 `iloc[-1]` と leader cache `tail(120)` に依存し、closed-bar alignment と dedup が strategy 内にない。さらに task cell は `pairs: ALL` だが実装は GBPUSD 専用で、ALL routing では 4/5 pairs が必ず `return None` になる。Axis 4 は thesis を壊す MA/HMM 系 hard filter はなく、Axis 5 も大きな破綻ではない。

再設計案は timing/data alignment を先に直す。`ctx.df.iloc[-2]` と leader_df の同一 timestamp 以前だけで signal を作り、execution は次 bar の `ctx.entry` に固定する。併せて `(strategy, symbol, signal, signal_bar_time)` の per-bar dedup を入れる。pair scope は `ALL` ではなく `GBP_USD` cell として tier/audit を分離し、他 pairs は別 hypothesis として扱う。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想と trigger は維持する。修正対象は timing/data alignment の 1 系統を第一優先にする。具体的には、`b_ret` / `a_ret` の z-score と rolling correlation を `ctx.df.index[-2]` までの確定足で計算し、leader_df も `leader_df.loc[:signal_bar_time]` に切ってから reindex する。signal は確定足、entry は次 bar の `ctx.entry` に分離する。

次に dedup と pair scope を明示する。`evaluate()` 内または dispatch 層で `(cpd_divergence, GBPUSD, signal, signal_bar_time)` を 1 回だけ emit し、`pairs: ALL` の集計ではなく `GBP_USD` 専用 Shadow cell に分ける。採用前には本 audit では実行しない 365d BT を、closed-bar + dedup variant で再集計し、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly を同一 source から出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | refine event N=19; trade simulation N=19; audit DB rows=0; G1 never-logged 0 signals / 30,592 evals | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json`; `demo_trades.db`; `raw/audits/never_logged_diagnosis_2026-04-28.md` |
| Win rate | event WR=73.68%; trade simulation WR=63.16%; audit DB `INSUFFICIENT_EVIDENCE` because rows=0 | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json`; `demo_trades.db` |
| Wilson lo (95%) | event Wilson lo=51.21%; audit DB `INSUFFICIENT_EVIDENCE` because rows=0 | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json`; `demo_trades.db` |
| PF | 1.72 | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json` |
| WF folds (3+) | `INSUFFICIENT_EVIDENCE`; only quarterly stability Q2 and Q4 are present, not >=3 WF folds | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json` |
| Bonferroni-adj p | p_bonf=1.14422, not significant; original CPD family size 4 also had EUR_USD -> GBP_USD p_bonf=0.12799, not significant | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json`; `raw/cpd_audit/cpd_audit_20260427_1051.md` |
| Kelly fraction | 0.2645 | `raw/cpd_refine/cpd_refine_20260427_1107.md`; `raw/cpd_refine/cpd_refine_20260427_1107.json` |
