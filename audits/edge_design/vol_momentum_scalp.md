---
strategy: vol_momentum_scalp
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: EUR_JPY
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

強い ADX / DI 方向性が出ている高ボラ環境で、BB %B の上端/下端突破と足方向一致を確認して momentum breakout に順張りする scalp。コードは ADX・DI gap・BB width・%B・陽線/陰線を entry 前提として持ち、TP>SL の非対称 payoff で継続分を取りに行く。`strategies/scalp/vol_momentum.py:2`, `strategies/scalp/vol_momentum.py:5`, `strategies/scalp/vol_momentum.py:14`, `strategies/scalp/vol_momentum.py:15`, `strategies/scalp/vol_momentum.py:38`, `strategies/scalp/vol_momentum.py:44`, `strategies/scalp/vol_momentum.py:45`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対して、precondition は `ctx.adx >= 25`、`abs(+DI - -DI) >= 8`、`bb_width_pct >= 0.45`。BUY は `bbpb >= 0.90 ∧ +DI > -DI ∧ entry > open_price`、SELL は `bbpb <= 0.10 ∧ -DI > +DI ∧ entry < open_price` で、trend confirmation と breakout/足方向確認を直接捕捉している。MR trigger ではない。`strategies/scalp/vol_momentum.py:76`, `strategies/scalp/vol_momentum.py:77`, `strategies/scalp/vol_momentum.py:80`, `strategies/scalp/vol_momentum.py:82`, `strategies/scalp/vol_momentum.py:85`, `strategies/scalp/vol_momentum.py:86`, `strategies/scalp/vol_momentum.py:102`, `strategies/scalp/vol_momentum.py:103`, `strategies/scalp/vol_momentum.py:104`, `strategies/scalp/vol_momentum.py:118`, `strategies/scalp/vol_momentum.py:119`, `strategies/scalp/vol_momentum.py:120` |
| 3 (timing window) | LOOKAHEAD | Strategy 内に closed-bar 判定、`ctx.bar_time` / `df.index[-1]` ベースの per-bar dedup、または signal bar と execution bar の分離がない。trigger は現在の `ctx.bbpb`、`ctx.entry`、`ctx.open_price`、`ctx.adx` を直接使うため、実行層が closed 5m bar を保証しない場合は intrabar の一時的な %B/足色で発火しうる。同一 bar 多重 entry も strategy file 単体では防げない。`strategies/scalp/vol_momentum.py:65`, `strategies/scalp/vol_momentum.py:76`, `strategies/scalp/vol_momentum.py:86`, `strategies/scalp/vol_momentum.py:102`, `strategies/scalp/vol_momentum.py:104`, `strategies/scalp/vol_momentum.py:118`, `strategies/scalp/vol_momentum.py:120`, `strategies/scalp/vol_momentum.py:171` |
| 4 (filter coherence) | STRENGTHENS | Pair filter は BT 正EV候補に限定し、EURJPY は NY_Late を block する session filter を持つ。ADX gate、DI gap、BB width gate は trend / volatility breakout thesis を強化する。RSI extreme block は momentum tail を削るリスクがあるが、hard trend gate ではなく過熱追随を避ける品質 filter として設計されており、MA filter on MR や HMM regime gate same-trap のような thesis 破壊とは異なる。`strategies/scalp/vol_momentum.py:48`, `strategies/scalp/vol_momentum.py:52`, `strategies/scalp/vol_momentum.py:60`, `strategies/scalp/vol_momentum.py:62`, `strategies/scalp/vol_momentum.py:66`, `strategies/scalp/vol_momentum.py:71`, `strategies/scalp/vol_momentum.py:76`, `strategies/scalp/vol_momentum.py:80`, `strategies/scalp/vol_momentum.py:85`, `strategies/scalp/vol_momentum.py:89`, `strategies/scalp/vol_momentum.py:90` |
| 5 (stop/TP geometry) | ALIGNED | TP は `ATR7 * 1.8`、SL は `max(ATR7 * 1.0, min_sl)` で、通常時 R:R は約 1.8。momentum / breakout scalp として winner を伸ばし loser を浅く切る非対称構造になっている。固定 TP で trailing はないが、scalp の短期 momentum 継続を取る geometry としては整合する。`strategies/scalp/vol_momentum.py:44`, `strategies/scalp/vol_momentum.py:45`, `strategies/scalp/vol_momentum.py:99`, `strategies/scalp/vol_momentum.py:112`, `strategies/scalp/vol_momentum.py:113`, `strategies/scalp/vol_momentum.py:114`, `strategies/scalp/vol_momentum.py:115`, `strategies/scalp/vol_momentum.py:128`, `strategies/scalp/vol_momentum.py:129`, `strategies/scalp/vol_momentum.py:130`, `strategies/scalp/vol_momentum.py:131` |
| 6 (pair-regime fit) | FIT | EUR_JPY 5m は既存 historical BT で繰り返し positive pocket として出ている。180d scan は N=34, WR=82.4%, EV=+0.608、365d JPY 5m breakdown は N=83, WR=72.3%, EV=+0.287。ただし tier-master の 365d BT EV 欄は `—` で、現 tier-master だけでは決定級の数値が欠けている。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | historical BT には EUR_JPY 5m の positive signal があるが、tier-master は EV `—`、ローカル audit DB は EUR_JPY pair-specific closed row を保持していない。strategy-level live audit では N=21, WR=47.62%, Wilson lo=28.34%, PF=1.115, Kelly=+0.0490 だが、pair-specific / WF>=3 / Bonferroni 有意性は満たしていない。数値は下表に分離する。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_JPY | FIT / INSUFFICIENT_AUDIT_DB | 180d historical BT: N=34, WR=82.4%, EV=+0.608。365d JPY 5m breakdown: N=83, WR=72.3%, EV=+0.287。tier-master 365d BT EV は `—`、audit DB pair-specific metrics は未取得。 |

## Axis 8: failure mode 診断

Tier 3/4 ではないが、Tier 1 (LIVE) で Axis 7 が insufficient、かつ Axis 3 に timing 実装リスクがあるため診断対象とする。Axis 2/4/5 は momentum breakout thesis と整合しており、現時点で「思想は正、trigger/filter/geometry も概ね正」と見る。破綻候補は Axis 3 の closed-bar / per-bar dedup 不在で、live 実行層が intrabar evaluate する場合に BB %B と足色が未確定のまま発火する。

再設計案は timing hardening 1 系統。`evaluate()` 内で signal bar を closed bar に固定し、`ctx.entry` は次 bar execution として扱う。さらに `(symbol, strategy, signal, bar_id)` の last-emitted guard を strategy または実行層に持たせ、同一 5m bar の多重 Candidate を防ぐ。既存 positive pocket を壊す可能性があるため、本監査では実装せず、365d + WF folds>=3 + Bonferroni/Kelly で再検証する。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

最小修正は trigger の思想を変えず、timing だけを固めること。コードレベルでは `evaluate()` 冒頭または signal 確定直後に `bar_id = ctx.bar_time or ctx.df.index[-1]` 相当を得て、同一 `(ctx.symbol, self.name, signal, bar_id)` を再 emit しない guard を追加する案が第一候補になる。

より厳密な variant では、`ctx.bbpb` / `ctx.open_price` / `ctx.entry` 直参照を signal 判定から外し、`signal_bar = ctx.df.iloc[-2]` の %B・Open・Close・ADX/DI snapshot で BUY/SELL を確定、次 bar の `ctx.entry` で約定する形にする。1 bar latency が増えるため、現行版との比較は新規 BT が必要。本タスクでは BT を実行しない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB pair-specific EUR_JPY: 0 rows in local `demo_trades.db`; strategy-level live audit: N=21; historical EUR_JPY 5m: N=34 (180d), N=83 (365d JPY 5m) | `demo_trades.db`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/raw/bt-results/full-bt-scan-2026-04-15.md`; `knowledge-base/raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md`; `knowledge-base/raw/bt-results/bt-scalp-5m-365d-jpy-2026-04-22.json` |
| Win rate | audit DB pair-specific EUR_JPY: INSUFFICIENT_EVIDENCE; strategy-level live audit: 47.62%; historical EUR_JPY 5m: 82.4% (180d), 72.3% (365d) | same sources |
| Wilson lo (95%) | pair-specific audit DB: INSUFFICIENT_EVIDENCE; strategy-level live audit: 28.34%; historical EUR_JPY 5m derived: 66.5% (28/34), 61.8% (60/83) | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; derived from historical N/WR above |
| PF | pair-specific EUR_JPY PF: INSUFFICIENT_EVIDENCE; strategy-level live audit PF=1.115 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: target EUR_JPY pair-promoted cell の WF>=3 既存結果は確認できず | tier-master / audit DB / existing BT docs checked; no qualifying WF>=3 record found |
| Bonferroni-adj p | pair-specific EUR_JPY: INSUFFICIENT_EVIDENCE; strategy-level live audit Bonf p=1.0000 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Kelly fraction | pair-specific EUR_JPY: INSUFFICIENT_EVIDENCE; strategy-level live audit Kelly=+0.0490; 2026-04-29 daily log reports vol_momentum_scalp as only positive Kelly edge (+7.78%, half-Kelly=3.37%) but not pair-specific | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/log.md` |
| tier-master EV | 365d BT EV `—` | `knowledge-base/wiki/tier-master.md` |
