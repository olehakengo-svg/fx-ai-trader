---
strategy: xs_momentum
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: EUR_USD, GBP_USD
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

20バーのペア内リターンを ATR で正規化し、1.0 ATR 超の方向継続を EMA/足色/ADX で確認して順張りする通貨モメンタム戦略。ディスパージョンが高い局面は momentum timing の品質が高い、という補助仮説を持つ。`strategies/daytrade/xs_momentum.py:2`, `strategies/daytrade/xs_momentum.py:14`, `strategies/daytrade/xs_momentum.py:15`, `strategies/daytrade/xs_momentum.py:20`, `strategies/daytrade/xs_momentum.py:23`, `strategies/daytrade/xs_momentum.py:27`, `strategies/daytrade/xs_momentum.py:30`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対して、`mom = (Close[-1] - Close[-21]) / ATR` を計算し、`BUY: mom > 1.0 AND EMA9 > EMA21 AND entry > open_price`、`SELL: mom < -1.0 AND EMA9 < EMA21 AND entry < open_price` を要求する。MR の oversold trigger ではなく、方向継続と短期トレンド整合を直接捕捉している。`strategies/daytrade/xs_momentum.py:76`, `strategies/daytrade/xs_momentum.py:80`, `strategies/daytrade/xs_momentum.py:81`, `strategies/daytrade/xs_momentum.py:84`, `strategies/daytrade/xs_momentum.py:136`, `strategies/daytrade/xs_momentum.py:139`, `strategies/daytrade/xs_momentum.py:154`, `strategies/daytrade/xs_momentum.py:156`, `strategies/daytrade/xs_momentum.py:158`, `strategies/daytrade/xs_momentum.py:161`, `strategies/daytrade/xs_momentum.py:163`, `strategies/daytrade/xs_momentum.py:165` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に closed-bar 判定や `(symbol, bar_time)` の per-bar dedup がない。`ctx.bar_time` は session gate のみに使われ、trigger は現在足由来の `ctx.entry`, `ctx.open_price`, `ctx.ema9`, `ctx.ema21`, `ctx.adx`, `ctx.atr` と `df.iloc[-1]` を直接読むため、実行層が intrabar evaluate すると未確定足の勢いで複数回 emit できる。実際の Render mirror でも 2026-05-01 14:02-14:21 UTC に EUR_USD/GBP_USD の `xs_momentum` が連続発火している。`strategies/daytrade/xs_momentum.py:100`, `strategies/daytrade/xs_momentum.py:122`, `strategies/daytrade/xs_momentum.py:127`, `strategies/daytrade/xs_momentum.py:136`, `strategies/daytrade/xs_momentum.py:154`, `strategies/daytrade/xs_momentum.py:158`, `strategies/daytrade/xs_momentum.py:161`, `strategies/daytrade/xs_momentum.py:165`, `strategies/daytrade/xs_momentum.py:244` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | Pair filter は EURUSD/GBPUSD/USDJPY を許可するが、本 audit 対象の EUR_USD/GBP_USD とは整合する一方、USDJPY は tier-master 上 pair_demoted なので strategy file 単体では NEUTRAL/危険寄り。ADX>=20 は momentum thesis を強化する。London-NY H12-H17 gate は低流動性時間帯を避ける点で強化。ただし dispersion は hard filter ではなく score bonus だけなので、thesis の品質条件としては NEUTRAL。MA filter on MR や HMM same-trap 例とは異なり、momentum edge tail を明示的に破壊する filter は見えない。`strategies/daytrade/xs_momentum.py:101`, `strategies/daytrade/xs_momentum.py:103`, `strategies/daytrade/xs_momentum.py:114`, `strategies/daytrade/xs_momentum.py:115`, `strategies/daytrade/xs_momentum.py:118`, `strategies/daytrade/xs_momentum.py:128`, `strategies/daytrade/xs_momentum.py:145`, `strategies/daytrade/xs_momentum.py:146`, `strategies/daytrade/xs_momentum.py:211`, `strategies/daytrade/xs_momentum.py:212`, `strategies/daytrade/xs_momentum.py:232`, `strategies/daytrade/xs_momentum.py:235` |
| 5 (stop/TP geometry) | ALIGNED | Nominal SL=`1.5ATR`, TP=`2.0ATR` で R:R は `2.0/1.5=1.33`、`MIN_RR=1.2` を通過する。Momentum 用の非対称 payoff は残っているが、コメント上の Quick Harvest 実効 TP は `1.7ATR` なので実効 R:R は約 `1.13` まで縮み、trend continuation を取りに行く設計としては余裕が薄い。`ALIGNED` だが borderline。`strategies/daytrade/xs_momentum.py:62`, `strategies/daytrade/xs_momentum.py:63`, `strategies/daytrade/xs_momentum.py:65`, `strategies/daytrade/xs_momentum.py:66`, `strategies/daytrade/xs_momentum.py:67`, `strategies/daytrade/xs_momentum.py:174`, `strategies/daytrade/xs_momentum.py:175`, `strategies/daytrade/xs_momentum.py:192`, `strategies/daytrade/xs_momentum.py:193` |
| 6 (pair-regime fit) | FIT / FORCED | 下の pair table 参照。EUR_USD は 365d BT で正、直近 audit mirror では負。GBP_USD は tier-master 365d EV がほぼゼロ/負で、NY-overlap subcell だけ正の偏りがあるため broad pair fit では FORCED 寄り。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | N/WR/EV だけなら 365d BT と直近 audit DB に材料はあるが、pair-promoted 2ペアに対する PF / WF folds>=3 / Bonferroni-adjusted p / Kelly が同一ソースで揃っていない。`feedback_partial_quant_trap.md` 基準では promotion-grade の統計根拠不足。数値は下表に分離する。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_USD | FIT / deteriorating | tier-master 365d BT EV は `+0.126`。別 365d BT JSON は N=237, WR=62.4%, EV=+0.103。一方、Render mirror の promoted-pair audit DB は N=19, WR=21.1%, Wilson lo=8.5%, EV=-2.03p, PF=0.651。 |
| GBP_USD | FORCED / session-dependent | tier-master 365d BT EV は `-0.013`。別 365d BT JSON は N=273, WR=56.0%, EV=-0.194。Render mirror では N=37, WR=29.7%, Wilson lo=17.5%, EV=+1.11p, PF=1.153 だが、H1 bucket audit では London が N=8, WR=0%, NY-overlap が N=16, WR=50%, EV=+8.65p と時間帯依存が強い。 |

## Axis 8: failure mode 診断

Tier 3/4 ではないが、Tier 1 (LIVE) かつ GBP_USD の tier-master EV が `-0.013`、直近 live aggregate でも `xs_momentum` は N=4, WR=25.0%, Wilson lo=4.56%, EV=-5.40p, PF=0.507, Kelly=0.0000 と劣化しているため failure mode 診断対象とする。

破綻候補は Axis 3 が主因。現在の trigger は momentum thesis と整合しているが、closed-bar 化と per-bar dedup が strategy 内にないため、同一 momentum burst を 1 trade ではなく複数 entry に分割して浴びる構造になっている。Axis 5 は nominal には整合するが、Quick Harvest 後の実効 R:R が薄く、強い momentum を取り切る設計としては補助的な弱点がある。Axis 4 は hard break ではない。

再設計案は timing 修正を第一候補にする。`evaluate()` の trigger 後に `bar_id = ctx.bar_time or ctx.df.index[-1]` を使った `(symbol, signal, bar_id)` dedup を入れ、1本の 15m bar で同一方向を一度だけ emit する。より厳密には `df.iloc[-2]` を signal bar、現在の `ctx.entry` を次 bar execution として、`mom/EMA/足色/ADX` を確定足で計算する variant に切る。追加案として、`abs(_mom)` が極端な領域、例えば `> 3.0ATR` では chase せず次足 pullback 確認へ回す trigger cap を検証対象にする。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想と trigger の方向性は維持する。最小修正は timing 1 系統で、bar-close signal と per-bar dedup を strategy 側に持たせること。コードレベルでは `_mom` と `signal` が確定した直後に `bar_id` guard を置き、同一 `(ctx.symbol, signal, bar_id)` は `return None` にする案が最小差分になる。

次の variant では、signal 判定を `ctx.df.iloc[-2]` の確定足に寄せ、execution は次 bar の `ctx.entry` に限定する。現状の 20バー momentum、EMA9/21、ADX、London-NY gate、SL/TP は一旦維持し、A/B で `abs(_mom) <= 3.0ATR` の freshness cap だけを別枝として評価する。新規 BT は本 audit では実行しないが、採用前には pair 別 365d、WF folds>=3、Bonferroni-adjusted p、Kelly を同一集計で再確認する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB promoted pairs: all N=56, EUR_USD N=19, GBP_USD N=37; live-only GBP_USD N=2; gate-progression live aggregate N=4 | `/tmp/live-trades-tier1-rca.json`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Win rate | audit DB promoted pairs: all 26.8%, EUR_USD 21.1%, GBP_USD 29.7%; live-only GBP_USD 50.0%; gate-progression live aggregate 25.0% | `/tmp/live-trades-tier1-rca.json`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Wilson lo (95%) | audit DB promoted pairs: all 16.96%, EUR_USD 8.51%, GBP_USD 17.49%; live-only GBP_USD 9.45%; gate-progression live aggregate 4.56% | derived from `/tmp/live-trades-tier1-rca.json`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| PF | audit DB promoted pairs: all 1.007, EUR_USD 0.651, GBP_USD 1.153; live-only GBP_USD 1.037; gate-progression live aggregate 0.507 | `/tmp/live-trades-tier1-rca.json`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE for target promoted pairs. Strategy-level W60/W90 exists and is borderline (`W60 N=309, WR=63.4%, EV=+0.081, PF=1.11, positive_ratio=0.667`; `W90 N=309, WR=63.4%, EV=+0.081, PF=1.11, positive_ratio=0.75`), but not pair-specific for EUR_USD/GBP_USD in this audit. | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json` |
| Bonferroni-adj p | audit DB promoted pairs: p unavailable in pair aggregate; H1 bucket cells are all p_bonf=1.0 for EUR_USD/GBP_USD subcells; strategy-level shadow status p_bonf=0.589 with Wilson_BF lower=0.1527 and EV gate fail | `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.json` |
| Kelly fraction | audit DB promoted pairs: all -0.0048, EUR_USD negative by PF<1, GBP_USD approx +0.133 from WR/PF; live-only GBP_USD +0.0180; gate-progression live aggregate 0.0000 | derived from `/tmp/live-trades-tier1-rca.json`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| tier-master EV | EUR_USD `+0.126`, GBP_USD `-0.013` | `knowledge-base/wiki/tier-master.md` |
