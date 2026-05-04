---
strategy: vol_momentum
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

強い ADX / DI 方向性と高い BB width が出ている局面で、BB %B の上端/下端突破とローソク足実体方向を確認し、その方向へ momentum breakout scalp として順張りする。コード上の実装名は `vol_momentum_scalp` だが、対象ファイルの thesis は ADX・DI gap・BB width・%B・陽線/陰線・TP>SL の非対称 payoff から導出できる。`strategies/scalp/vol_momentum.py:2`, `strategies/scalp/vol_momentum.py:5`, `strategies/scalp/vol_momentum.py:14`, `strategies/scalp/vol_momentum.py:15`, `strategies/scalp/vol_momentum.py:38`, `strategies/scalp/vol_momentum.py:43`, `strategies/scalp/vol_momentum.py:44`, `strategies/scalp/vol_momentum.py:45`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対し、precondition は `ctx.adx >= 25`、`abs(+DI - -DI) >= 8`、`bb_width_pct >= 0.45`。BUY は `bbpb >= 0.90 ∧ +DI > -DI ∧ entry > open_price`、SELL は `bbpb <= 0.10 ∧ -DI > +DI ∧ entry < open_price` で、trend confirmation と breakout/足方向確認を直接捕捉している。`strategies/scalp/vol_momentum.py:76`, `strategies/scalp/vol_momentum.py:77`, `strategies/scalp/vol_momentum.py:80`, `strategies/scalp/vol_momentum.py:82`, `strategies/scalp/vol_momentum.py:85`, `strategies/scalp/vol_momentum.py:86`, `strategies/scalp/vol_momentum.py:102`, `strategies/scalp/vol_momentum.py:103`, `strategies/scalp/vol_momentum.py:104`, `strategies/scalp/vol_momentum.py:118`, `strategies/scalp/vol_momentum.py:119`, `strategies/scalp/vol_momentum.py:120` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に closed-bar 判定、signal bar と execution bar の分離、または `(strategy, symbol, bar_id)` の per-bar dedup がない。trigger は現在の `ctx.adx`, `ctx.bb_width_pct`, `ctx.bbpb`, `ctx.entry`, `ctx.open_price` を直接使うため、実行層が確定足だけを渡す保証がない場合、intrabar の一時的な %B/足色で発火しうる。同一 bar 多重 entry も strategy file 単体では防げない。`strategies/scalp/vol_momentum.py:65`, `strategies/scalp/vol_momentum.py:76`, `strategies/scalp/vol_momentum.py:85`, `strategies/scalp/vol_momentum.py:102`, `strategies/scalp/vol_momentum.py:104`, `strategies/scalp/vol_momentum.py:118`, `strategies/scalp/vol_momentum.py:120`, `strategies/scalp/vol_momentum.py:171` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | Pair filter は BT コメント上の正EV候補に限定し、session filter は XAUUSD/EURJPY の弱い時間帯を block するため、思想を概ね STRENGTHENS。ADX gate、DI gap、BB width gate は trend / volatility breakout thesis を強化する。RSI extreme block は momentum tail を削る可能性があり NEUTRAL 寄りだが、MR に MA filter を入れる例や regime tail 依存 edge に HMM gate を入れる例のような thesis 破壊ではない。`strategies/scalp/vol_momentum.py:48`, `strategies/scalp/vol_momentum.py:52`, `strategies/scalp/vol_momentum.py:56`, `strategies/scalp/vol_momentum.py:60`, `strategies/scalp/vol_momentum.py:66`, `strategies/scalp/vol_momentum.py:71`, `strategies/scalp/vol_momentum.py:76`, `strategies/scalp/vol_momentum.py:80`, `strategies/scalp/vol_momentum.py:85`, `strategies/scalp/vol_momentum.py:89`, `strategies/scalp/vol_momentum.py:90` |
| 5 (stop/TP geometry) | ALIGNED | TP は `ATR7 * 1.8`、SL は `max(ATR7 * 1.0, min_sl)` で、通常時 R:R は約 1.8。momentum / breakout scalp として loser を浅めに切り、winner の継続分を取りに行く非対称 geometry になっている。trailing はないが、短期 scalp の固定 TP/SL としては thesis と整合する。`strategies/scalp/vol_momentum.py:44`, `strategies/scalp/vol_momentum.py:45`, `strategies/scalp/vol_momentum.py:99`, `strategies/scalp/vol_momentum.py:112`, `strategies/scalp/vol_momentum.py:113`, `strategies/scalp/vol_momentum.py:114`, `strategies/scalp/vol_momentum.py:115`, `strategies/scalp/vol_momentum.py:128`, `strategies/scalp/vol_momentum.py:129`, `strategies/scalp/vol_momentum.py:130`, `strategies/scalp/vol_momentum.py:131` |
| 6 (pair-regime fit) | FIT / FORCED | `pairs: ALL` に対して、実装は USDJPY/EURJPY/GBPUSD/XAUUSD のみ許可し、EURUSD/EURGBP などは除外する。コードコメント上は EURJPY/GBPUSD/XAUUSD が正EV、USDJPY は損益分岐点扱い。ALL としては broader universe が FORCED だが、実際の enabled subset は thesis fit を意識している。下の pair table 参照。`strategies/scalp/vol_momentum.py:48`, `strategies/scalp/vol_momentum.py:49`, `strategies/scalp/vol_momentum.py:50`, `strategies/scalp/vol_momentum.py:51`, `strategies/scalp/vol_momentum.py:52`, `strategies/scalp/vol_momentum.py:53`, `strategies/scalp/vol_momentum.py:54`, `strategies/scalp/vol_momentum.py:60`, `strategies/scalp/vol_momentum.py:61`, `strategies/scalp/vol_momentum.py:62` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 入力の phase0_shadow / ALL 365d BT EV は `—`。既存 audit DB 相当の strategy-level live audit では N=21, WR=47.62%, Wilson lo=28.34%, PF=1.115, Kelly=+0.0490, Bonferroni p=1.0000 があるが、ALL phase0_shadow の pair別 Wilson/PF/Kelly、WF folds>=3、Bonferroni 通過が揃わない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可であり、採用判断には不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FORCED / weak FIT | Code allowed。コメントでは EV=-0.028 の損益分岐点で、scalp 主力ペアとして発火機会を残す扱い。実運用 audit では positive cells もあるが、ALL phase0_shadow の決定級 evidence ではない。 |
| EURJPY | FIT | Code allowed。コメントでは EUR/JPY EV=+0.362。既存 historical でも EURJPY 5m positive pocket が複数回確認されているが、今回入力の tier-master 365d BT EV は `—`。 |
| GBPUSD | FIT / session-sensitive | Code allowed。コメントでは GBP/USD EV=+0.160。ただし h1-hour bucket では GBPUSD London/NY/Off などに弱い shadow cell があり、session filter は XAUUSD/EURJPY のみに限定される。 |
| XAUUSD | FIT / session-gated | Code allowed。コメントでは XAU/USD EV=+0.179、session matrix では Tokyo/London が良く NY を block。volatility breakout thesis との相性は自然。 |
| Other ALL pairs | FORCED / blocked | Strategy file は `_enabled_symbols` 外を return None にするため、ALL universe へ無差別適用する設計ではない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) かつ tier-master 由来 metrics が `—` の under-evidenced cell として診断する。Axis 2 は thesis と trigger が整合し、Axis 4/5 も大きく壊していない。破綻候補は Axis 3 で、closed-bar / next-bar execution / per-bar dedup の契約が strategy 内にないため、momentum breakout の「確定した伸び」を取る設計が、実行層次第で intrabar 飛び乗りや同一足多重発火へ変質しうる。

再設計案は timing hardening を最優先にする。`evaluate()` の signal 判定を確定済み足に寄せ、`signal_bar = ctx.df.iloc[-2]` 相当の %B・Open・Close・ADX/DI snapshot で BUY/SELL を確定し、約定は次 bar の `ctx.entry` に分離する。さらに `(symbol, self.name, signal, bar_id)` の last-emitted guard を strategy または dispatch 層に追加して、同一 5m bar の再 emit を防ぐ。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想と trigger/filter/stop geometry は概ね維持し、timing 契約だけを固める。具体的には、現行の `ctx.bbpb` / `ctx.entry` / `ctx.open_price` 直参照による signal 判定を「確定足 snapshot で判定、次足で約定」に変更し、signal bar id を持たせて同一 bar の重複 Candidate を抑止する。

Filter 側は大きく触らない。例外として、GBPUSD の London/NY 弱さや USDJPY の breakeven 性は session/pair 別に再検証し、XAUUSD/EURJPY と同様の pair-session gate を追加する variant は候補にする。ただし本 audit では BT を実行しないため、採用前には現行版と timing-hardened 版を同一データで比較し、pair別 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact に出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | ALL phase0_shadow pair-specific: INSUFFICIENT_EVIDENCE。strategy-level live audit: N=21。historical EURJPY 5m references: N=34 (180d), N=83 (365d JPY 5m). | prompt tier-master input; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/raw/bt-results/full-bt-scan-2026-04-15.md`; `knowledge-base/raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md`; `knowledge-base/raw/bt-results/bt-scalp-5m-365d-jpy-2026-04-22.json` |
| Win rate | ALL phase0_shadow pair-specific: INSUFFICIENT_EVIDENCE。strategy-level live audit: 47.62%。historical EURJPY 5m: 82.4% (180d), 72.3% (365d). | same sources |
| Wilson lo (95%) | ALL phase0_shadow pair-specific: INSUFFICIENT_EVIDENCE。strategy-level live audit: 28.34%。historical EURJPY 5m derived reference: 66.5% (28/34), 61.8% (60/83), not official audit DB decision metric. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; derived from historical N/WR references |
| PF | ALL phase0_shadow pair-specific: INSUFFICIENT_EVIDENCE。strategy-level live audit PF=1.115。h1-hour counterfactual shadow cells show mixed PF, e.g. GBPUSD London PF=0.11 and USDJPY NY-overlap PF=2.33, but no ALL decision-grade aggregate. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `vol_momentum` / `vol_momentum_scalp` の ALL phase0_shadow WF folds>=3 artifact は確認できない。 | tier-master / audit DB search |
| Bonferroni-adj p | ALL phase0_shadow pair-specific: INSUFFICIENT_EVIDENCE。strategy-level live audit Bonf p=1.0000。h1-hour counterfactual includes cells with p_bonf mostly 1.0000 and one weak GBPUSD London p_bonf=0.0003 but negative EV/PF=0.11, so promotion evidenceではない。 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Kelly fraction | ALL phase0_shadow pair-specific: INSUFFICIENT_EVIDENCE。strategy-level live audit Kelly=+0.0490。2026-04-29 daily log reports vol_momentum_scalp as only positive Kelly edge (+7.78%, half-Kelly=3.37%) but not ALL/pair-specific. | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/log.md` |
| tier-master EV | phase0_shadow / ALL 365d BT EV `—`。Repository tier-master has `vol_momentum_scalp` pair_promoted EUR_JPY EV `—`; prompt input treats `vol_momentum` ALL as phase0_shadow with EV `—`. | prompt tier-master input; `knowledge-base/wiki/tier-master.md` |
