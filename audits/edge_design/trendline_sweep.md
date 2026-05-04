---
strategy: trendline_sweep
tier: Tier 1 (LIVE)
source_tier: elite_live
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

個人投資家の stop が集まる斜めの trendline を一度 sweep し、直後に TL 内へ reclaim した足で、大口の流動性獲得後の元トレンド継続に乗る戦略。コード上も「SL集中帯を狙って一時的にトレンドラインを突き抜けさせ、急速にTL内に回帰し、元のトレンド方向へ継続する」と明示されている。`strategies/daytrade/trendline_sweep.py:10`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | ascending: `Low[t-lb] < TL[t-lb] - 0.1ATR` かつ `range/ATR >= 1.0` の sweep 後、`Close[t] > TL[t]` かつ `Close[t-1] <= TL[t-1]` かつ陽線 reclaim で BUY。descending は対称に SELL。sweep + fresh reclaim + body confirmation が thesis を直接捕捉している。`strategies/daytrade/trendline_sweep.py:272`, `strategies/daytrade/trendline_sweep.py:305`, `strategies/daytrade/trendline_sweep.py:314`, `strategies/daytrade/trendline_sweep.py:338`, `strategies/daytrade/trendline_sweep.py:347` |
| 3 (timing window) | OK | Williams fractal は `len(df) - n` より前だけを評価し、未確定の右側バーを現在足に対して参照しない。sweep 検出も `range(1, SWEEP_LOOKBACK + 1)` で現在足を除外し、現在足は bar-close reclaim として判定される。戦略内に per-bar dedup 状態はないが、1 evaluate で返す Candidate は最大 1 件。`strategies/daytrade/trendline_sweep.py:129`, `strategies/daytrade/trendline_sweep.py:137`, `strategies/daytrade/trendline_sweep.py:270`, `strategies/daytrade/trendline_sweep.py:296`, `strategies/daytrade/trendline_sweep.py:405` |
| 4 (filter coherence) | STRENGTHENS | TL 品質 filter は距離・傾き・respect で主観的 TL を抑制するため thesis を強化。ADX 15-45 は無風と極端な本物 trend break を避ける中庸 trend filter。pair / SELL-only filter は USDJPY の本物 TL break や BUY 弱さを避ける意図で、MR に MA gate を当てる破壊例や HMM same-trap 型の regime tail 破壊とは異なる。`strategies/daytrade/trendline_sweep.py:74`, `strategies/daytrade/trendline_sweep.py:88`, `strategies/daytrade/trendline_sweep.py:102`, `strategies/daytrade/trendline_sweep.py:167`, `strategies/daytrade/trendline_sweep.py:197`, `strategies/daytrade/trendline_sweep.py:380`, `strategies/daytrade/trendline_sweep.py:414` |
| 5 (stop/TP geometry) | ALIGNED | SL は sweep extreme の外側に `0.3ATR` buffer を置き、stop-hunt の wick を許容する。TP は `2.5ATR`、最低 `RR=1.5` へ補正され、流動性 sweep 後の trend continuation を非対称 payoff で取りに行く。trailing ではないが、固定 ATR continuation target として thesis とは衝突しない。`strategies/daytrade/trendline_sweep.py:92`, `strategies/daytrade/trendline_sweep.py:426`, `strategies/daytrade/trendline_sweep.py:432`, `strategies/daytrade/trendline_sweep.py:441` |
| 6 (pair-regime fit) | FORCED | 実装 universe は `EURUSD, GBPUSD, EURGBP, XAUUSD` に限定され、USDJPY はコードコメント上も除外。tier-master の明示 EV は EUR/GBP のみで、EURGBP/XAUUSD は SELL-only コメントはあるが同等の tier-master evidence がないため、`ALL` live 扱いとしては FORCED を含む。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master は EUR EV `+0.574`、GBP EV `+0.838` を持つが、指定 sqlite `knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite` には `trendline_sweep` 行が存在しない。既存監査レポートでは live aggregate N=6, WR=33.33%, Wilson lo=9.68%, PF=0.077, Bonferroni p=1.0000, Kelly=0.0000 / raw Kelly=-4.0119 で、N<30 のため採否判断には不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EURUSD | FIT | tier-master EUR EV `+0.574`; 730d WF では N=106, 9 folds, positive ratio 1.00, stable。 |
| GBPUSD | FIT / WATCH | tier-master GBP EV `+0.838`; 730d WF は N=204, 22 folds, positive ratio 0.64 で borderline。 |
| EURGBP | FORCED | code では SELL-only だが、この audit input/tier-master には pair-level PF/Wilson/Kelly がない。 |
| XAUUSD | FORCED | code では SELL-only だが、この audit input/tier-master には pair-level PF/Wilson/Kelly がない。 |
| USDJPY | FORCED if routed | code 上は ALLOWED_PAIRS 外。コメントも macro trend 方向の本物 TL break として除外。 |

## Axis 8: failure mode 診断

Tier 1 LIVE だが、直近監査 metrics は劣化しているため Axis 8 を適用する。Axis 2/3/4/5 のコード設計そのものは破綻していない。破綻箇所は Axis 7 の evidence 不足と Axis 6 の `ALL` live scope で、特に EURGBP/XAUUSD まで elite_live として扱うには、この task の入力と audit DB から Wilson/PF/Kelly が確認できない。

再設計案: trigger/timing/stop は維持し、live routing scope を「tier-master と WF で根拠がある EURUSD / GBPUSD」に限定する。EURGBP/XAUUSD は SELL-only のまま shadow に落とし、N>=30 かつ Wilson lo / PF / Bonferroni / Kelly が揃うまで elite_live の `ALL` 扱いから外す。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`A`

コードレベルでは `_detect_sweep_reclaim()` の条件式や SL/TP geometry は変えない。変更候補は routing/pair filter のみで、`ALLOWED_PAIRS` または live 側 tier routing を EURUSD / GBPUSD に縮小し、EURGBP / XAUUSD は shadow evidence collection に戻す。これは thesis 修正ではなく、evidence のない pair-regime exposure を切る防御的な設計変更である。

追加で必要な検証は新規 edge 探索ではなく、既存 audit DB に `trendline_sweep` の pair-level Wilson lo / PF / Kelly / Bonferroni / WF を復元すること。現 sqlite には対象行がないため、BT を新規実行しない制約下では、EURGBP/XAUUSD の live 許可を正当化できない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Live aggregate N=6; Tier1 GBP_USD cell N=4 | audit report: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/decisions/tier1-live-edge-audit-2026-05-03.md` |
| Win rate | Live aggregate 33.33%; Tier1 GBP_USD cell 50.00% | audit report |
| Wilson lo (95%) | Live aggregate 9.68%; Tier1 GBP_USD cell 15.00% | audit report |
| PF | Live aggregate 0.077; Tier1 GBP_USD cell 0.418; BT reference EUR_USD 2.52 / GBP_USD 1.68 | audit report; strategy KB |
| WF folds (3+) | W60: EUR_USD 6 folds pos_ratio 1.00, GBP_USD 6 folds pos_ratio 0.83; 730d: EUR_USD 9 folds pos_ratio 1.00, GBP_USD 22 folds pos_ratio 0.64 | walkforward reports |
| Bonferroni-adj p | Live aggregate 1.0000; Tier1 GBP_USD cell 1.0000 | audit report |
| Kelly fraction | Live aggregate Kelly 0.0000, raw Kelly -4.0119; Tier1 GBP_USD raw Kelly -0.6964 | audit report |
| tier-master EV | 365d BT JPY EV `—`; EUR EV `+0.574`; GBP EV `+0.838` | `knowledge-base/wiki/tier-master.md` |
| audit DB availability | `s6-w1p0-production-2026-05-04.sqlite` has no `trendline_sweep` rows; chart-pattern tables are unrelated to this strategy | local sqlite schema/content query |
