---
strategy: alpha_intraday_seasonality
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

曜日×時間帯ごとの過去リターン分布に統計的な方向バイアスがあり、その平均リターンが t 検定と効果量で十分強い場合に、同じ曜日×時間帯の次のバーでも同方向へ短期的に持続する、という intraday seasonality thesis。コードは仮説を明示し、同一 `weekday` × `hour` の過去 `Open→Close` リターンから `mean_ret` を推定している。`strategies/daytrade/alpha_intraday_seasonality.py:5`, `strategies/daytrade/alpha_intraday_seasonality.py:6`, `strategies/daytrade/alpha_intraday_seasonality.py:7`, `strategies/daytrade/alpha_intraday_seasonality.py:8`, `strategies/daytrade/alpha_intraday_seasonality.py:12`, `strategies/daytrade/alpha_intraday_seasonality.py:14`, `strategies/daytrade/alpha_intraday_seasonality.py:15`, `strategies/daytrade/alpha_intraday_seasonality.py:81`, `strategies/daytrade/alpha_intraday_seasonality.py:82`, `strategies/daytrade/alpha_intraday_seasonality.py:96`, `strategies/daytrade/alpha_intraday_seasonality.py:111`, `strategies/daytrade/alpha_intraday_seasonality.py:130`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Seasonality thesis に対し、trigger は `matched = hist[(weekday == current_dow) & (hour == current_hour)]`、`returns = (Close - Open) / Open`、`t_stat = mean_ret / (std_ret / sqrt(n))`、`abs(t_stat) >= 2.0`、`cohens_d >= min_effect_size`、`signal = BUY if mean_ret > 0 else SELL`。思想の「同一曜日×同一時間帯の平均リターンが非ゼロなら偏り方向に入る」を直接捕捉している。`strategies/daytrade/alpha_intraday_seasonality.py:70`, `strategies/daytrade/alpha_intraday_seasonality.py:72`, `strategies/daytrade/alpha_intraday_seasonality.py:81`, `strategies/daytrade/alpha_intraday_seasonality.py:82`, `strategies/daytrade/alpha_intraday_seasonality.py:83`, `strategies/daytrade/alpha_intraday_seasonality.py:96`, `strategies/daytrade/alpha_intraday_seasonality.py:118`, `strategies/daytrade/alpha_intraday_seasonality.py:119`, `strategies/daytrade/alpha_intraday_seasonality.py:122`, `strategies/daytrade/alpha_intraday_seasonality.py:126`, `strategies/daytrade/alpha_intraday_seasonality.py:130` |
| 3 (timing window) | OK | 現在バーのリターンは分布計算に入れず、`hist = df.iloc[:-1]` から同一曜日×時間帯だけを抽出するため、trigger 統計そのものに look-ahead は見えない。`current_dow/current_hour` は `ctx.bar_time` または `df.index[-1]` から取得するだけで、現在バーの `Close` / `High` / `Low` を trigger に使っていない。一方、strategy 内に per-bar dedup はないため、実行層が同一 bar で複数回 evaluate する場合は dispatch 側の dedup 前提になる。`strategies/daytrade/alpha_intraday_seasonality.py:23`, `strategies/daytrade/alpha_intraday_seasonality.py:24`, `strategies/daytrade/alpha_intraday_seasonality.py:25`, `strategies/daytrade/alpha_intraday_seasonality.py:53`, `strategies/daytrade/alpha_intraday_seasonality.py:56`, `strategies/daytrade/alpha_intraday_seasonality.py:61`, `strategies/daytrade/alpha_intraday_seasonality.py:62`, `strategies/daytrade/alpha_intraday_seasonality.py:72`, `strategies/daytrade/alpha_intraday_seasonality.py:172` |
| 4 (filter coherence) | BREAKS | `len(df) >= 200`、`hist >= 100`、`matched >= 8`、`valid returns >= 8`、週末除外は statistical seasonality thesis を中立から軽く強化する guard。破壊的なのは HTF Hard Block で、`ctx.htf["agreement"] == "bull"` なら seasonality が SELL を示しても棄却し、`bear` なら BUY を棄却する。曜日×時間帯フローの偏りは HTF trend agreement を前提にしていないため、HMM regime gate same-trap と同様、tail/session edge を上位 regime gate で削る設計リスクがある。総合判定は BREAKS。`strategies/daytrade/alpha_intraday_seasonality.py:49`, `strategies/daytrade/alpha_intraday_seasonality.py:67`, `strategies/daytrade/alpha_intraday_seasonality.py:73`, `strategies/daytrade/alpha_intraday_seasonality.py:87`, `strategies/daytrade/alpha_intraday_seasonality.py:94`, `strategies/daytrade/alpha_intraday_seasonality.py:132`, `strategies/daytrade/alpha_intraday_seasonality.py:133`, `strategies/daytrade/alpha_intraday_seasonality.py:134`, `strategies/daytrade/alpha_intraday_seasonality.py:135`, `strategies/daytrade/alpha_intraday_seasonality.py:136`, `strategies/daytrade/alpha_intraday_seasonality.py:137`, `strategies/daytrade/alpha_intraday_seasonality.py:138` |
| 5 (stop/TP geometry) | MISALIGNED | Edge 推定は historical `Open→Close` の同一曜日×時間帯リターン分布なのに、exit は time-based close ではなく `SL=1.5ATR`、`TP=min(2.5, 1.5 + cohens_d)ATR` の固定 bracket。R:R は最小 `1.5/1.5=1.0R`、最大 `2.5/1.5=1.67R` だが、測定対象の「その時間帯の平均リターン」ではなく任意の ATR 到達を取りに行くため、thesis と exit horizon がずれている。`strategies/daytrade/alpha_intraday_seasonality.py:90`, `strategies/daytrade/alpha_intraday_seasonality.py:91`, `strategies/daytrade/alpha_intraday_seasonality.py:92`, `strategies/daytrade/alpha_intraday_seasonality.py:96`, `strategies/daytrade/alpha_intraday_seasonality.py:145`, `strategies/daytrade/alpha_intraday_seasonality.py:147`, `strategies/daytrade/alpha_intraday_seasonality.py:149`, `strategies/daytrade/alpha_intraday_seasonality.py:150`, `strategies/daytrade/alpha_intraday_seasonality.py:151`, `strategies/daytrade/alpha_intraday_seasonality.py:153`, `strategies/daytrade/alpha_intraday_seasonality.py:154` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。Seasonality thesis 自体は pair 汎用になり得るが、現行コードに pair/session/spread calibration がなく `ALL` に一律適用される。既存 365d target BT では USD_JPY / EUR_USD が負 EV、GBP_USD だけ弱正で、ALL fit は証明できない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow 365d BT EV は `—`。audit DB 相当の H1 bucket counterfactual は strategy-level N=10, WR=30.0%, Wilson BF lower=5.76%, Bonferroni p=1.0, Kelly≈0.0 で全 gate fail。既存 365d target BT は PF と WR を持つが、GBP_USD 以外は負 EV/PF<1 で、WF は folds>=3 があっても positive ratio が 0.25-0.75 に揺れる。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可のため、採用判断は不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FORCED | 365d target BT は N=80, WR=57.5%, EV=-0.109, PF=0.99。WR は 50% 超だが PF と EV が edge を支持しない。 |
| EUR_USD | FORCED | 365d target BT は N=47, WR=53.2%, EV=-0.144, PF=0.94。小 N かつ負 EV。 |
| GBP_USD | FIT / WEAK | 365d target BT は N=61, WR=62.3%, EV=+0.037, PF=1.25 で唯一正方向。ただし Bonferroni/BH は不通過で、H1 bucket 直近 3か月は Asia N=7 の小 N positive に偏る。 |
| Other ALL pairs | FORCED / UNTESTED | コードには pair gate がなく ALL 適用されるが、tier-master / audit DB に decision-grade の pair-specific Wilson / PF / Kelly がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で、既存 evidence は昇格基準を満たさないため failure mode 診断対象とする。破綻軸は Axis 4 と Axis 5 が主、Axis 7 が補助。Axis 2 の trigger は seasonality thesis を直接捉えており、Axis 3 も trigger 統計には look-ahead がない。問題は、曜日×時間帯フローの tail を HTF Hard Block で削ることと、`Open→Close` 分布で推定した edge を ATR bracket exit で取りに行く geometry の不一致にある。

再設計案は 1 案目として「thin seasonality baseline」へ戻す。HTF Hard Block を削除または score feature に降格し、entry は同一曜日×時間帯の `mean_ret` が Bonferroni-aware な閾値を満たす場合だけ許可する。exit は thesis と合わせて time-based にし、signal 対象バーの close または最大 1 bar hold で決済する。保護 SL は同一 bucket の historical adverse quantile、または `k * std_ret * entry` から決め、TP も ATR ではなく bucket return distribution の上側分位に寄せる。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想と trigger 中核は有効候補。再設計の中心は trigger を新しく作ることではなく、HTF filter と exit geometry を thesis に合わせること。具体的には `ctx.htf["agreement"]` による hard return を外し、`mean_ret` / `std_ret` / `t_stat` / `cohens_d` は維持したまま、pair×weekday×hour ごとに最低 N を 30 以上へ上げる variant を作る。

exit は `SL=1.5ATR` / `TP=(1.5+d)ATR` から、time stop + distribution-based guard に変える。コード差分の方向性は、Candidate に `max_hold_bars=1` 相当のメタ情報を渡せる実行層ならそれを使い、使えない場合は redesign branch 側で「1 bar close exit」を backtest harness に明示する。採用前には新規発見ではなく既存 audit pipeline の再集計として、pair×hour bucket の 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 table で発行する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow: `—`; audit DB H1 bucket: strategy-level N=10, GBP_USD Asia 7 / NY-overlap 1 / Off 2; 365d target BT: USD_JPY 80, EUR_USD 47, GBP_USD 61 | prompt input; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| Win rate | audit DB H1 bucket: 30.0%; 365d target BT: USD_JPY 57.5%, EUR_USD 53.2%, GBP_USD 62.3% | same sources |
| Wilson lo (95%) | audit DB H1 bucket Wilson BF lower 5.76%; 365d target BT derived: USD_JPY 46.57%, EUR_USD 39.23%, GBP_USD 49.75%; all below decision-grade promotion threshold | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; derived from `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` counts |
| PF | audit DB H1 bucket cells: GBP_USD Asia 1.685, NY-overlap 0.000, Off 0.000; 365d target BT: USD_JPY 0.99, EUR_USD 0.94, GBP_USD 1.25 | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| WF folds (3+) | W60/W90 records exist but are unstable: W60 examples include n=74 PF=1.07 positive_ratio=0.50, n=45 PF=0.75 positive_ratio=0.40, n=63 PF=0.74 positive_ratio=0.00, n=88 PF=0.96 positive_ratio=0.50, n=119 PF=1.09 positive_ratio=0.833; W90 examples range positive_ratio 0.25-0.75. Fails stable WF evidence. | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json` |
| Bonferroni-adj p | audit DB H1 bucket p_bonferroni=1.0; strategy KB 2026-04-17 reports GBP_USD raw p=0.037 but all pairs fail Bonferroni alpha'=0.0083 and BH q=0.10 | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; `knowledge-base/wiki/strategies/intraday-seasonality.md` |
| Kelly fraction | audit DB H1 bucket strategy-level Kelly≈0.0000 and blocked; cell-level GBP_USD Asia Kelly=0.174 on N=7 only, NY/Off null; 365d target BT derived full Kelly: USD_JPY -0.0058, EUR_USD -0.0340, GBP_USD +0.1246 | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json`; derived from WR/PF in `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
