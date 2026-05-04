---
strategy: turtle_soup
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

Major Fractal High/Low の外側にある stop-loss cluster を sweep した後、価格が同水準の内側へ reclaim する局面を liquidity grab の失敗とみなし、逆方向へ平均回帰を取る MR / false-breakout fade 戦略。コード上も「ストップ狩り→回帰」を逆張りエントリーする、と明示されている。`strategies/daytrade/turtle_soup.py:10`, `strategies/daytrade/turtle_soup.py:11`, `strategies/daytrade/turtle_soup.py:12`, `strategies/daytrade/turtle_soup.py:13`, `strategies/daytrade/turtle_soup.py:14`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR / false-breakout thesis に対して、SELL は `High > level + 0.05ATR` かつ `bar_range / ATR >= 1.2` の高値 sweep 後、`cur_close < level AND prev_close >= level AND cur_close < cur_open` で reclaim を確認する。BUY は `Low < level - 0.05ATR` 後、`cur_close > level AND prev_close <= level AND cur_close > cur_open`。sweep extreme と実体 reclaim を条件化しており、単なる momentum breakout ではなく stop hunt failure を捕捉している。`strategies/daytrade/turtle_soup.py:63`, `strategies/daytrade/turtle_soup.py:64`, `strategies/daytrade/turtle_soup.py:65`, `strategies/daytrade/turtle_soup.py:203`, `strategies/daytrade/turtle_soup.py:214`, `strategies/daytrade/turtle_soup.py:216`, `strategies/daytrade/turtle_soup.py:223`, `strategies/daytrade/turtle_soup.py:224`, `strategies/daytrade/turtle_soup.py:236`, `strategies/daytrade/turtle_soup.py:238`, `strategies/daytrade/turtle_soup.py:241`, `strategies/daytrade/turtle_soup.py:243` |
| 3 (timing window) | LOOKAHEAD | Fractal 自体は `_end = len(df) - n` で最新 `n` 本を除外しており future fractal 確定の look-ahead は避けている。一方、signal は `df.iloc[-1]` の current close/open と `ctx.entry` を使って返され、strategy 内に closed-bar timestamp、signal→next-bar execution、または `(symbol, strategy, signal_bar)` dedup がない。実行層が intrabar に評価する場合、未確定足の reclaim が途中で消えるリスクと同一 bar 多重 entry リスクがあるため LOOKAHEAD 寄り。`strategies/daytrade/turtle_soup.py:117`, `strategies/daytrade/turtle_soup.py:190`, `strategies/daytrade/turtle_soup.py:194`, `strategies/daytrade/turtle_soup.py:196`, `strategies/daytrade/turtle_soup.py:236`, `strategies/daytrade/turtle_soup.py:241`, `strategies/daytrade/turtle_soup.py:304`, `strategies/daytrade/turtle_soup.py:318`, `strategies/daytrade/turtle_soup.py:418` |
| 4 (filter coherence) | STRENGTHENS | ADX gate は `ADX < 12` の無風と `ADX > 40` の強トレンドを除外し、stop hunt reversal が機能しやすい中間ボラ帯に寄せるため thesis を強化する。時間帯 gate は UTC 06-20 に限定し、liquidity grab が発生しやすい London/NY 流動性帯へ寄せる。金曜後半 block も低流動性回避で中立から強化。pair filter と EURGBP SELL-only は 55d BT 由来で過剰適合リスクはあるが、MA filter on MR や HMM regime gate same-trap のように thesis tail を構造的に消す filter ではない。`strategies/daytrade/turtle_soup.py:70`, `strategies/daytrade/turtle_soup.py:71`, `strategies/daytrade/turtle_soup.py:72`, `strategies/daytrade/turtle_soup.py:79`, `strategies/daytrade/turtle_soup.py:80`, `strategies/daytrade/turtle_soup.py:81`, `strategies/daytrade/turtle_soup.py:83`, `strategies/daytrade/turtle_soup.py:84`, `strategies/daytrade/turtle_soup.py:87`, `strategies/daytrade/turtle_soup.py:94`, `strategies/daytrade/turtle_soup.py:98`, `strategies/daytrade/turtle_soup.py:271`, `strategies/daytrade/turtle_soup.py:275`, `strategies/daytrade/turtle_soup.py:279`, `strategies/daytrade/turtle_soup.py:334` |
| 5 (stop/TP geometry) | ALIGNED | SL は sweep extreme のさらに外側へ `0.3ATR` buffer を置くため、reclaim 前の stop hunt tail に対して MR 用の invalidation stop になっている。TP は対面 Major Fractal、なければ `2.5ATR` fallback、かつ `MIN_RR=1.5` 未満なら TP を拡張する。R:R は最低 1.5R で、range 内回帰を取りに行く構造として概ね整合。ただし `MIN_RR` による TP 拡張は、mean 到達後に利確する MR よりやや遠い target を強制しうるため、採用前に TP 到達率の再検証が必要。`strategies/daytrade/turtle_soup.py:74`, `strategies/daytrade/turtle_soup.py:75`, `strategies/daytrade/turtle_soup.py:76`, `strategies/daytrade/turtle_soup.py:77`, `strategies/daytrade/turtle_soup.py:346`, `strategies/daytrade/turtle_soup.py:348`, `strategies/daytrade/turtle_soup.py:350`, `strategies/daytrade/turtle_soup.py:352`, `strategies/daytrade/turtle_soup.py:356`, `strategies/daytrade/turtle_soup.py:361`, `strategies/daytrade/turtle_soup.py:367`, `strategies/daytrade/turtle_soup.py:379`, `strategies/daytrade/turtle_soup.py:381` |
| 6 (pair-regime fit) | FORCED | Input は `ALL` だが code は `GBPUSD`, `XAUUSD`, `EURGBP` だけを許可し、`EURGBP` は SELL-only にする。GBPUSD は既存 BT/WF に positive 参考値があり FIT。XAUUSD は liquidity sweep thesis との相性は自然だが tier-master/audit DB の promotion-grade PF/Wilson/Kelly がないため unproven。EURGBP SELL-only は 55d コメント由来で、ALL cell としては FORCED。下の pair-regime table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / deteriorated latest audit | tier-master 入力の phase0_shadow / ALL 365d BT EV は `—`。latest gate-progression audit aggregate は N=1, WR=0.00%, Wilson lo=0.00%, EV=-0.10p, PF=0.000, Kelly=0.0000, Bonferroni p=1.0000 で、`feedback_partial_quant_trap.md` 基準では採用判断不可。補助的な古い GBPUSD artifacts には 365d N=46/WR=67.4%/EV=+0.543、W90 aggregate N=50/WR=64.0%/PF=1.87/folds=4/positive_ratio=0.75 があるが、対象 `ALL` Shadow cell の現行 tier-master/audit DB evidence ではない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| GBPUSD | FIT / needs refreshed evidence | Code allowed。古い 365d/WF では GBPUSD に positive 参考値があり、liquidity grab fade の主対象として自然。ただし latest audit aggregate は strategy 全体で N=1/WR=0%。 |
| XAUUSD | FIT / unproven | Code allowed。金は sweep/reclaim thesis と相性はあるが、現行 tier-master/audit DB で XAUUSD の Wilson/PF/Kelly が確認できない。 |
| EURGBP | FORCED / SELL-only | Code allowed かつ SELL-only。コメントでは 55d SELL WR=80% とされるが、direction-only filter は小標本・期間依存の可能性があり、ALL scope の thesis fit とは別証拠が必要。 |
| USDJPY | FORCED / blocked | Code comment で 55d EV negative とされ、実装でも不許可。ALL cell としては対象外が混在している。 |
| EURUSD | FORCED / blocked | Code comment で 55d EV negative とされ、実装でも不許可。ALL cell としては対象外が混在している。 |
| Other ALL pairs | FORCED / blocked | Strategy file は 3 pair のみ許可するため、`pairs: ALL` の tier cell は実装 scope と一致しない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、latest audit aggregate は N=1 / WR=0% / PF=0 / Bonferroni p=1.0000 で、tier-master 365d BT EV も `—`。したがって under-evidenced shadow かつ latest metric deteriorated として failure mode 診断対象にする。

破綻軸は Axis 3 と Axis 6/7。Axis 2 の trigger は sweep + reclaim を数学的に捉えており、Axis 4 の ADX/time/pair filters は thesis を明確には破壊していない。Axis 5 も sweep extreme 外側 SL と対面 fractal TP で概ね整合する。主問題は、current bar の reclaim をそのまま signal 化する一方で closed-bar / next-bar execution / dedup 契約が strategy 内にないこと、そして tier cell が `ALL` なのに code scope は GBPUSD/XAUUSD/EURGBP へ狭く、現行 audit evidence がその scope を支えていないこと。

再設計案は timing hardening を第一優先にする。`_detect_sweep_and_reclaim()` の `cur_*` を確定 signal bar、entry を次 bar execution として分離し、Candidate 生成時または dispatcher で `(symbol, entry_type, signal, signal_bar_time)` の 1 bar 1 emit を保証する。次に scope を `GBPUSD` 主体の cell と `XAUUSD`/`EURGBP SELL-only` の別 cell に分離し、ALL aggregate で昇格判断しない。TP は現状維持でよいが、redesign BT では `MIN_RR` による TP 拡張なしの "opposite fractal or mean-touch exit" variant も比較する。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想と trigger は明確で、旧 GBPUSD BT/WF には復活候補として見るだけの参考値があるため棄却しない。修正優先度は timing 1 系統で、closed-bar 化、next-bar execution、per-bar dedup を入れるだけで現行 thesis を保ったまま検証できる。

具体的には `_detect_sweep_and_reclaim()` の `cur_close`, `prev_close`, `cur_open` を「評価中の current bar」ではなく `signal_bar = df.iloc[-2]`, `prev_bar = df.iloc[-3]` へ寄せ、`sweep` 探索も signal bar 以前に限定する。`evaluate()` は `ctx.entry` を次 bar execution price として使い、Candidate に signal bar timestamp を残す。採用前には本 audit では実行しない refreshed 365d + WF folds>=3 を、GBPUSD / XAUUSD / EURGBP SELL-only に分けて Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction まで同一 artifact で再発行する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | latest audit DB aggregate: 1; local `demo_trades.db`: 0 rows for `turtle_soup`; supplementary old GBPUSD 365d: N=46, old W90: N=50, old 730d WF: N=102 | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `demo_trades.db`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| Win rate | latest audit DB aggregate: 0.00%; supplementary old GBPUSD 365d: 67.4%; old W90: 64.0%; old 730d WF: 55.9% | same as above |
| Wilson lo (95%) | latest audit DB aggregate: 0.00%; supplementary old GBPUSD 365d recomputed from N=46/WR=67.4%: 52.97%; old W90 recomputed from N=50/WR=64.0%: 50.14%; old 730d recomputed from N=102/WR=55.9%: 46.21% | audit DB + Wilson formula on existing BT/WF summaries |
| PF | latest audit DB aggregate: 0.000; supplementary old W90 aggregate: 1.87; old 730d WF aggregate: 1.26; tier-master phase0_shadow ALL 365d BT EV/PF: `—` | audit DB; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json`; prompt tier-master input |
| WF folds (3+) | latest target ALL cell: INSUFFICIENT_EVIDENCE in tier-master/audit DB; supplementary old GBPUSD W90 has active_windows=4, positive_ratio=0.75; old 730d has active_windows=11, positive_ratio=0.545 | `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| Bonferroni-adj p | latest audit DB aggregate: 1.0000; supplementary old BT/WF artifacts do not provide adjusted p for the current ALL cell | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Kelly fraction | latest audit DB aggregate: 0.0000 (raw Kelly +0.0000); supplementary old BT/WF artifacts do not provide Kelly fraction for the current ALL cell | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; old BT/WF artifacts |
