---
strategy: jpy_basket_trend
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

USDJPY と EURJPY が同時にパーフェクトオーダー化する局面を「円バスケット全体の方向一致」とみなし、ADX/HTF/DI/足色で強い JPY trend-following に乗る思想。実装上は cross-pair data 制約により、現在ペアの PO + ADX + HTF agreement を basket trend の proxy として使う。`strategies/daytrade/jpy_basket_trend.py:2`, `strategies/daytrade/jpy_basket_trend.py:5`, `strategies/daytrade/jpy_basket_trend.py:6`, `strategies/daytrade/jpy_basket_trend.py:7`, `strategies/daytrade/jpy_basket_trend.py:9`, `strategies/daytrade/jpy_basket_trend.py:10`, `strategies/daytrade/jpy_basket_trend.py:17`, `strategies/daytrade/jpy_basket_trend.py:18`, `strategies/daytrade/jpy_basket_trend.py:19`, `strategies/daytrade/jpy_basket_trend.py:20`, `strategies/daytrade/jpy_basket_trend.py:21`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Momentum trigger としては `BUY: ema9 > ema21 > ema50 AND ADX >= 28 AND +DI > -DI AND close > open AND close > ema9`、`SELL: ema9 < ema21 < ema50 AND ADX >= 28 AND -DI > +DI AND close < open AND close < ema9` なので trend-following は捕捉している。一方、コードコメント上の core thesis は `USDJPY と EURJPY が同時に15分足でパーフェクトオーダー` だが、実条件は current symbol の単独 `_bull_po/_bear_po` と HTF agreement だけで cross-pair simultaneity を検証しない。期待条件は概念的に `PO(USDJPY) AND PO(EURJPY) AND same_jpy_direction`、実条件は `PO(current_symbol) AND ADX(current_symbol) AND HTF(current_symbol)` であり、basket thesis の数学的捕捉が proxy に縮退している。`strategies/daytrade/jpy_basket_trend.py:5`, `strategies/daytrade/jpy_basket_trend.py:9`, `strategies/daytrade/jpy_basket_trend.py:10`, `strategies/daytrade/jpy_basket_trend.py:56`, `strategies/daytrade/jpy_basket_trend.py:57`, `strategies/daytrade/jpy_basket_trend.py:61`, `strategies/daytrade/jpy_basket_trend.py:62`, `strategies/daytrade/jpy_basket_trend.py:68`, `strategies/daytrade/jpy_basket_trend.py:78`, `strategies/daytrade/jpy_basket_trend.py:79`, `strategies/daytrade/jpy_basket_trend.py:80`, `strategies/daytrade/jpy_basket_trend.py:81`, `strategies/daytrade/jpy_basket_trend.py:82`, `strategies/daytrade/jpy_basket_trend.py:95`, `strategies/daytrade/jpy_basket_trend.py:96`, `strategies/daytrade/jpy_basket_trend.py:97`, `strategies/daytrade/jpy_basket_trend.py:98`, `strategies/daytrade/jpy_basket_trend.py:99` |
| 3 (timing window) | LOOKAHEAD | Entry confirmation が `ctx.entry`, `ctx.open_price`, `ctx.ema9` の現在足状態を直接読む。strategy 内に closed-bar 判定、`bar_time` 利用、または `(symbol, signal, bar)` dedup がなく、live 実行層が intrabar で複数回 `evaluate()` する場合、未確定足の陽線/陰線・EMA9 上下で同一 bar 多重 entry が起き得る。bar dedup 欠落リスクは spec 上 `LOOKAHEAD` 寄りに分類する。`strategies/daytrade/jpy_basket_trend.py:45`, `strategies/daytrade/jpy_basket_trend.py:81`, `strategies/daytrade/jpy_basket_trend.py:82`, `strategies/daytrade/jpy_basket_trend.py:98`, `strategies/daytrade/jpy_basket_trend.py:99`, `strategies/daytrade/jpy_basket_trend.py:111`, `strategies/daytrade/jpy_basket_trend.py:161` |
| 4 (filter coherence) | STRENGTHENS | Pair filter は USDJPY/EURJPY のみを許可し、JPY basket thesis とは整合するが、audit scope `ALL` とは不一致。ADX>=28、PO 必須、HTF agreement、DI 方向、足色、EMA9 上下は momentum thesis を強化する。MR 戦略に MA filter を被せる `feedback_ma_filter_breaks_mr.md` 型ではなく、HMM regime gate で regime tail を消す `feedback_hmm_gate_same_trap.md` 型の hard gate もない。ただし filter chain は過密で、既存 low-firing audit では条件AND過多として発火率 <0.01%/bar 試算の対象になっているため、強化ではあるが過剰化リスクがある。`strategies/daytrade/jpy_basket_trend.py:39`, `strategies/daytrade/jpy_basket_trend.py:43`, `strategies/daytrade/jpy_basket_trend.py:47`, `strategies/daytrade/jpy_basket_trend.py:57`, `strategies/daytrade/jpy_basket_trend.py:61`, `strategies/daytrade/jpy_basket_trend.py:62`, `strategies/daytrade/jpy_basket_trend.py:64`, `strategies/daytrade/jpy_basket_trend.py:68`, `strategies/daytrade/jpy_basket_trend.py:79`, `strategies/daytrade/jpy_basket_trend.py:80`, `strategies/daytrade/jpy_basket_trend.py:81`, `strategies/daytrade/jpy_basket_trend.py:82`, `strategies/daytrade/jpy_basket_trend.py:96`, `strategies/daytrade/jpy_basket_trend.py:97`, `strategies/daytrade/jpy_basket_trend.py:98`, `strategies/daytrade/jpy_basket_trend.py:99`, `strategies/daytrade/jpy_basket_trend.py:117`, `strategies/daytrade/jpy_basket_trend.py:137`, `strategies/daytrade/jpy_basket_trend.py:145`, `strategies/daytrade/jpy_basket_trend.py:153` |
| 5 (stop/TP geometry) | ALIGNED | TP は `ATR * 2.5`、SL は BUY で `EMA50 - ATR * 0.3`、SELL で `EMA50 + ATR * 0.3`、さらに `TP distance >= 1.2 * SL distance` を要求する。PO 崩壊点で撤退し、利幅は stop より広く取る asymmetric payoff なので momentum / trend-following thesis と整合する。ただし fixed TP で trailing はなく、強トレンド継続を最大化する breakout 型 geometry ではない。`strategies/daytrade/jpy_basket_trend.py:25`, `strategies/daytrade/jpy_basket_trend.py:26`, `strategies/daytrade/jpy_basket_trend.py:40`, `strategies/daytrade/jpy_basket_trend.py:41`, `strategies/daytrade/jpy_basket_trend.py:75`, `strategies/daytrade/jpy_basket_trend.py:90`, `strategies/daytrade/jpy_basket_trend.py:91`, `strategies/daytrade/jpy_basket_trend.py:92`, `strategies/daytrade/jpy_basket_trend.py:107`, `strategies/daytrade/jpy_basket_trend.py:108`, `strategies/daytrade/jpy_basket_trend.py:109`, `strategies/daytrade/jpy_basket_trend.py:115`, `strategies/daytrade/jpy_basket_trend.py:116`, `strategies/daytrade/jpy_basket_trend.py:117` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。JPY trend thesis は USDJPY/EURJPY には fit するが、input scope は `ALL` で、実装は USDJPY/EURJPY 以外を即 `return None` にする。`ALL` cell としては scope が強制的で、pair-specific evidence も不足している。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow / ALL 行は 365d BT EV が `—`。local audit DB 相当の `demo_trades.db` では `demo_trades` / `evaluated_candidates` / `oanda_audit` の `jpy_basket_trend` 行が 0 件。sidecar raw BT には EURJPY 365d N=18, WR=66.7%, EV=+0.176, PF=1.20、Wilson lower 95% は N=18/W=12 から 43.75% と計算できるが、WF active windows は W60/W90 とも 2 で `>=3` を満たさず、Bonferroni-adjusted p と Kelly fraction は tier-master/audit DB に存在しない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT / INSUFFICIENT_EVIDENCE | JPY strength/weakness thesis の直接対象。実装も許可するが、確認できた 365d sidecar BT は USDJPY N=1 / WR=0.0% / EV=-0.876 のみで decision-grade ではない。`strategies/daytrade/jpy_basket_trend.py:43`, `strategies/daytrade/jpy_basket_trend.py:47` |
| EURJPY | FIT / WEAK_EVIDENCE | JPY basket proxy の直接対象。sidecar 365d BT は N=18 / WR=66.7% / EV=+0.176 / PF=1.20、session split は London N=7 / WR=85.7% / EV=+0.998 / PF=3.03 と示唆はあるが、WF active windows は 2 で promotion-grade ではない。`strategies/daytrade/jpy_basket_trend.py:43`, `strategies/daytrade/jpy_basket_trend.py:47` |
| GBPJPY | FORCED / MISSING | Strategy wiki の signal logic では GBPJPY も JPY cross として語られるが、実装の `_enabled_symbols` に含まれないため発火しない。`strategies/daytrade/jpy_basket_trend.py:43`, `strategies/daytrade/jpy_basket_trend.py:47` |
| Other ALL pairs | FORCED / BLOCKED | `ALL` scope に対して、USDJPY/EURJPY 以外は `_sym not in _enabled_symbols` で即 `return None`。`strategies/daytrade/jpy_basket_trend.py:43`, `strategies/daytrade/jpy_basket_trend.py:46`, `strategies/daytrade/jpy_basket_trend.py:47`, `strategies/daytrade/jpy_basket_trend.py:48` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) で Tier 3/4 ではないが、tier-master は 365d BT EV `—`、local audit DB は 0 rows、既存 low-firing audit では「JPY basket signal -- 稀」および「条件AND過多」に分類されているため、underperforming / evidence-missing shadow として failure mode を診断する。

破綻軸は Axis 2 と Axis 3。Axis 2 では「USDJPY と EURJPY の同時 PO」という basket thesis が実際には current pair の単独 trend proxy に縮退しており、basket edge ではなく通常の per-pair ADX/PO trend-following になっている。Axis 3 では現在足の `ctx.entry/open_price` に依存し、closed-bar guard と per-bar dedup が strategy 内にない。Axis 4 は thesis を直接破壊していないが、ADX>=28 + PO + HTF + DI + candle + EMA9 の AND chain が過密で、発火率不足を増幅している。

再設計案は、basket trigger を本当に basket 化し、timing を closed-bar 化すること。最小案は `SignalContext` か dispatch 層に USDJPY/EURJPY の同一 15m 確定足 snapshot を渡し、`BUY = bull_po(USDJPY) AND bull_po(EURJPY) AND adx>=threshold on traded pair AND htf_agreement != bear`、`SELL = bear_po(USDJPY) AND bear_po(EURJPY) AND adx>=threshold on traded pair AND htf_agreement != bull` に置換する。current bar の足色条件は確定足 `[-2]` に固定し、emit 時に `(symbol, signal, bar_time)` dedup を必須にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は有効候補として残す。JPY cross の同時方向一致を使う basket momentum は、単一ペア noise を減らす設計思想としてコードから明確に読める。ただし現行実装は cross-pair 同時性を直接見ておらず、設計の中心が proxy に置き換わっているため、このままでは `jpy_basket_trend` ではなく「USDJPY/EURJPY の単独 ADX/PO trend」になっている。

具体修正は trigger と timing の 2 系統。`_enabled_symbols` は USDJPY/EURJPY を維持しつつ、entry 条件に同一 bar の counterpart PO を必須化する。例: USDJPY BUY なら `USDJPY: EMA9>EMA21>EMA50` かつ `EURJPY: EMA9>EMA21>EMA50`、SELL は両方 bear PO。HTF agreement は hard `== bull/bear` から `not opposite` 程度に弱め、ADX>=28 は traded pair 側に残すか `max/adx basket average` に変更する。さらに `ctx.entry > ctx.open_price` / `< ctx.open_price` は確定足ベースにし、同一 `(symbol, signal, bar_time)` の再 emit を禁止する。

採用判定には、本 audit では実行しない既存 pipeline 再集計が必要。必要内容は USDJPY/EURJPY を pair 別に分け、real basket trigger + closed-bar + dedup 版で 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source から出すこと。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow ALL: `—`; local `demo_trades.db`: 0 rows; sidecar 365d reference: USDJPY N=1, EURJPY N=18; 730d WF reference: EURJPY N=49 | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`; `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| Win rate | audit DB: INSUFFICIENT_EVIDENCE (0 rows); sidecar 365d reference: USDJPY 0.0%, EURJPY 66.7%; 730d WF reference: EURJPY 63.3% | `demo_trades.db`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`; `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| Wilson lo (95%) | audit DB: INSUFFICIENT_EVIDENCE (0 rows); sidecar EURJPY 365d computed from N=18/W=12: 43.75%; 730d computed from N=49/W=31: 49.27% | `demo_trades.db`; `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| PF | tier-master: not present; audit DB: INSUFFICIENT_EVIDENCE (0 rows); sidecar WF reference: EURJPY 365d aggregate PF=1.20 in W60/W90 files, 730d aggregate PF=1.03 | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: W60 active_windows=2, W90 active_windows=2, 730d active_windows=1; none satisfy `>=3` valid folds | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.json` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: not present in tier-master, local audit DB has 0 rows, and sidecar BT/WF references do not provide Bonferroni-adjusted p for this strategy | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: not present in tier-master, local audit DB has 0 rows, and sidecar BT/WF references do not provide Kelly fraction for this strategy | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.json` |
