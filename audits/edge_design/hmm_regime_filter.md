---
strategy: hmm_regime_filter
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

HMM で直近 60 本の対数リターンから calm/turbulent regime を推定し、売買 alpha ではなく他戦略が参照する防御オーバーレイとして lot multiplier と regime state を共有する。`evaluate()` は trade signal を生成せず、毎バー regime state を更新するだけである。`strategies/daytrade/hmm_regime_filter.py:8`, `strategies/daytrade/hmm_regime_filter.py:9`, `strategies/daytrade/hmm_regime_filter.py:10`, `strategies/daytrade/hmm_regime_filter.py:45`, `strategies/daytrade/hmm_regime_filter.py:86`, `strategies/daytrade/hmm_regime_filter.py:111`, `strategies/daytrade/hmm_regime_filter.py:132`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Entry trigger は存在しない。条件式は `evaluate(ctx) -> update regime state -> return None` であり、alpha thesis ではなく防御 overlay thesis と整合する。MR/momentum の entry 捕捉式を持たないこと自体が設計意図として明示されている。`strategies/daytrade/hmm_regime_filter.py:9`, `strategies/daytrade/hmm_regime_filter.py:10`, `strategies/daytrade/hmm_regime_filter.py:86`, `strategies/daytrade/hmm_regime_filter.py:89`, `strategies/daytrade/hmm_regime_filter.py:132`, `strategies/daytrade/hmm_regime_filter.py:133` |
| 3 (timing window) | OK | Signal execution latency は対象外。`evaluate()` は `ctx.df["Close"]` から対数リターン系列を作り detector を更新するだけで、Candidate を emit しないため同一 bar 多重 entry や signal-to-execution look-ahead は発生しない。ただし regime state の更新タイミングは実行層の `ctx.df` 確定足保証に依存する。`strategies/daytrade/hmm_regime_filter.py:89`, `strategies/daytrade/hmm_regime_filter.py:90`, `strategies/daytrade/hmm_regime_filter.py:91`, `strategies/daytrade/hmm_regime_filter.py:103`, `strategies/daytrade/hmm_regime_filter.py:108`, `strategies/daytrade/hmm_regime_filter.py:111`, `strategies/daytrade/hmm_regime_filter.py:132`, `strategies/daytrade/hmm_regime_filter.py:133` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | `len(ctx.df) < 60` guard は detector lookback=60 と整合し、未学習/低サンプル regime 更新を防ぐので STRENGTHENS。`ctx.atr <= 0` guard も異常データ回避として STRENGTHENS。HMM 自体は他 edge に hard gate として掛けると same-trap になり得るが、この wrapper は gate せず `_lot_mult` と `_regime_label` を公開するだけなので、単体では BREAKS ではない。`strategies/daytrade/hmm_regime_filter.py:45`, `strategies/daytrade/hmm_regime_filter.py:67`, `strategies/daytrade/hmm_regime_filter.py:68`, `strategies/daytrade/hmm_regime_filter.py:72`, `strategies/daytrade/hmm_regime_filter.py:74`, `strategies/daytrade/hmm_regime_filter.py:94`, `strategies/daytrade/hmm_regime_filter.py:98`, `strategies/daytrade/hmm_regime_filter.py:111`, `strategies/daytrade/hmm_regime_filter.py:115`, `strategies/daytrade/hmm_regime_filter.py:117` |
| 5 (stop/TP geometry) | ALIGNED | No-trade overlay なので SL/TP/R:R は存在しない。`Candidate` を返さず、常に `None` を返す設計のため、stop/TP geometry は alpha entry と結合していない。R:R = N/A は防御 overlay thesis と整合する。`strategies/daytrade/hmm_regime_filter.py:27`, `strategies/daytrade/hmm_regime_filter.py:86`, `strategies/daytrade/hmm_regime_filter.py:89`, `strategies/daytrade/hmm_regime_filter.py:132`, `strategies/daytrade/hmm_regime_filter.py:133` |
| 6 (pair-regime fit) | FORCED | Pair-specific thesis はない。`_detector`, `_current_regime`, `_lot_mult`, `_vol_ratio`, `_last_symbol` はクラス変数で全インスタンス共有され、最後に評価された `ctx.symbol` の regime が共有状態になる。ALL pair 戦略として扱うと、pair 別 regime fit ではなく cross-symbol shared overlay になるため FORCED。`strategies/daytrade/hmm_regime_filter.py:43`, `strategies/daytrade/hmm_regime_filter.py:45`, `strategies/daytrade/hmm_regime_filter.py:46`, `strategies/daytrade/hmm_regime_filter.py:47`, `strategies/daytrade/hmm_regime_filter.py:48`, `strategies/daytrade/hmm_regime_filter.py:50`, `strategies/daytrade/hmm_regime_filter.py:79`, `strategies/daytrade/hmm_regime_filter.py:120` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 365d BT EV は `—`、v8.5 BT も N/A、audit DB (`demo_trades.entry_type`, `oanda_audit.entry_type`) は N=0。Wilson lower / PF / WF folds / Bonferroni-adjusted p / Kelly は、trade を生成しない overlay には算出不能。数値は下表に分離する。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| ALL | FORCED | Pair-specific detector/state ではなく class-level shared state。最後に評価された `ctx.symbol` が `_last_symbol` に保存されるため、ALL pair の独立 regime thesis としては不適合。`strategies/daytrade/hmm_regime_filter.py:43`, `strategies/daytrade/hmm_regime_filter.py:45`, `strategies/daytrade/hmm_regime_filter.py:50`, `strategies/daytrade/hmm_regime_filter.py:79`, `strategies/daytrade/hmm_regime_filter.py:120` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、historical metrics が `—` で audit DB N=0 のため failure mode 診断対象とする。破綻は Axis 2/3/5 ではない。コード上は signal を出さない防御 overlay として一貫しており、entry trigger、execution timing、stop/TP を持たないことが仕様である。

主な問題は Axis 6 と Axis 7。`phase0_shadow` の「戦略」として tier-master に入っているが、単体の trade edge として検証できず、ALL pair 共有の class state は pair-specific regime overlay としても粗い。再設計案は、この file を alpha strategy として復活させるのではなく、(1) tier-master から trade strategy 候補として除外して utility/overlay category に移す、(2) 継続するなら detector/state を symbol keyed に分離し、他戦略の trade record に `hmm_regime`, `lot_multiplier`, `vol_ratio` を保存して counterfactual audit できる形にする、のどちらかである。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`C`

この file は「思想は正、設計が誤」の通常候補ではなく、「思想は防御 overlay として明確、しかし strategy audit 対象としての設計単位が誤り」である。コードレベルでは `evaluate()` から Candidate を出す alpha strategy に改造せず、`HmmRegimeFilter` を utility/feature provider として扱うのが最小リスクである。

再設計するなら、`_detector`, `_current_regime`, `_lot_mult`, `_vol_ratio`, `_regime_label` を `dict[symbol, state]` 化し、`get_regime_info(symbol)` / `get_lot_multiplier(symbol)` の API に変える。そのうえで他戦略の entry 時に regime snapshot を記録し、HMM gate を hard filter として即適用せず、regime-stratified Wilson/PF/Kelly と counterfactual lot scaling を既存 audit DB で評価する。採用前に必要な BT/監査は「各 pair × strategy × HMM regime ごとの N, WR, Wilson lower, PF, Bonferroni-adjusted p, Kelly」と「hard gate ではなく lot scaling の PnL counterfactual」である。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 0 (`demo_trades.entry_type = hmm_regime_filter` count 0; `oanda_audit.entry_type = hmm_regime_filter` count 0) | audit DB: `demo_trades.db` |
| Win rate | INSUFFICIENT_EVIDENCE (N=0; trade 生成なし) | audit DB: `demo_trades.db` |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE (N=0; Wilson CI 算出対象外) | audit DB: `demo_trades.db` |
| PF | INSUFFICIENT_EVIDENCE (tier-master 365d BT EV `—`; v8.5 BT N/A) | `knowledge-base/wiki/tier-master.md`; `knowledge-base/raw/bt-results/bt-v85-all-pairs-2026-04-12.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE (trade strategy としての WF fold なし) | tier-master / existing audit artifacts |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE (N=0; hypothesis test 対象外) | audit DB / tier-master |
| Kelly fraction | INSUFFICIENT_EVIDENCE (N=0; PF/WR 不在) | audit DB / tier-master |
