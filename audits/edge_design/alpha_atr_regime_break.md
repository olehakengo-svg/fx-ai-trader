---
strategy: alpha_atr_regime_break
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

低 ATR 変動係数の静穏期後に ATR が前バー比で急伸した最初の足を、新しい volatility regime の開始と見なし、その足の方向へ短期 momentum が継続することを狙う breakout / momentum 戦略。コードコメントは「低ボラティリティ期間後の ATR 急伸」と「現在バーの方向にエントリー」を明示している。`strategies/daytrade/alpha_atr_regime_break.py:5`, `strategies/daytrade/alpha_atr_regime_break.py:7`, `strategies/daytrade/alpha_atr_regime_break.py:8`, `strategies/daytrade/alpha_atr_regime_break.py:9`, `strategies/daytrade/alpha_atr_regime_break.py:22`, `strategies/daytrade/alpha_atr_regime_break.py:24`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / volatility breakout thesis に対し、`surge_ratio = current_atr / prev_atr` かつ `surge_ratio >= surge_mult`、直前 `quiet_window` 本の ATR-CV を `cv_pctl <= 0.25`、方向を `BUY: Close - Open > 0` / `SELL: Close - Open < 0` で決める。MR の oversold trigger ではなく、静穏期後の volatility expansion と足方向確認を直接捕捉している。`strategies/daytrade/alpha_atr_regime_break.py:91`, `strategies/daytrade/alpha_atr_regime_break.py:92`, `strategies/daytrade/alpha_atr_regime_break.py:96`, `strategies/daytrade/alpha_atr_regime_break.py:107`, `strategies/daytrade/alpha_atr_regime_break.py:124`, `strategies/daytrade/alpha_atr_regime_break.py:125`, `strategies/daytrade/alpha_atr_regime_break.py:128`, `strategies/daytrade/alpha_atr_regime_break.py:129`, `strategies/daytrade/alpha_atr_regime_break.py:135`, `strategies/daytrade/alpha_atr_regime_break.py:141` |
| 3 (timing window) | LOOKAHEAD | CV window と percentile history は現在バーを除外しており、この部分の look-ahead は抑制されている。一方で signal は現在バーの ATR、Open/Close、High/Low を直接使い、strategy 内に closed-bar 判定、signal bar と execution bar の分離、`ctx.bar_time` / `df.index[-1]` ベースの per-bar dedup がない。実行層が intrabar evaluate する場合、未確定の ATR 急伸・足色・レンジで emit し、同一 bar 多重 entry も strategy 単体では防げない。`strategies/daytrade/alpha_atr_regime_break.py:85`, `strategies/daytrade/alpha_atr_regime_break.py:86`, `strategies/daytrade/alpha_atr_regime_break.py:111`, `strategies/daytrade/alpha_atr_regime_break.py:133`, `strategies/daytrade/alpha_atr_regime_break.py:134`, `strategies/daytrade/alpha_atr_regime_break.py:141`, `strategies/daytrade/alpha_atr_regime_break.py:152`, `strategies/daytrade/alpha_atr_regime_break.py:188` |
| 4 (filter coherence) | BREAKS | `bar_body >= 0.10ATR` と `bar_range >= 0.8ATR` は、急伸バーの方向と実体を要求するため thesis を STRENGTHENS する。一方、HTF Hard Block は `bull × SELL` / `bear × BUY` を棄却するため、静穏期後の新 regime 開始が既存 HTF 方向と逆に出る tail を切る。これは HMM regime gate same-trap と同型の、regime tail に依存する edge を regime filter で消すリスクであり、総合判定は BREAKS。`strategies/daytrade/alpha_atr_regime_break.py:137`, `strategies/daytrade/alpha_atr_regime_break.py:138`, `strategies/daytrade/alpha_atr_regime_break.py:143`, `strategies/daytrade/alpha_atr_regime_break.py:145`, `strategies/daytrade/alpha_atr_regime_break.py:146`, `strategies/daytrade/alpha_atr_regime_break.py:148`, `strategies/daytrade/alpha_atr_regime_break.py:151`, `strategies/daytrade/alpha_atr_regime_break.py:152`, `strategies/daytrade/alpha_atr_regime_break.py:153` |
| 5 (stop/TP geometry) | ALIGNED | SL は `1.2ATR`、TP は `min(3.0, 1.5 + (surge_ratio - surge_mult) * 1.5)ATR` なので、最小 R:R は約 `1.5 / 1.2 = 1.25R`、最大は `3.0 / 1.2 = 2.5R`。Momentum / breakout として winner を stop より広く取る非対称 payoff で整合する。trailing はないが、短期 regime break の固定 TP geometry としては破壊的ではない。`strategies/daytrade/alpha_atr_regime_break.py:156`, `strategies/daytrade/alpha_atr_regime_break.py:159`, `strategies/daytrade/alpha_atr_regime_break.py:160`, `strategies/daytrade/alpha_atr_regime_break.py:161`, `strategies/daytrade/alpha_atr_regime_break.py:163`, `strategies/daytrade/alpha_atr_regime_break.py:164`, `strategies/daytrade/alpha_atr_regime_break.py:165`, `strategies/daytrade/alpha_atr_regime_break.py:167`, `strategies/daytrade/alpha_atr_regime_break.py:168` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。Volatility clustering thesis 自体は pair 汎用だが、実装に pair/session/spread calibration がなく、ALL cell としては強制適用。既存 365d target BT も USD_JPY/EUR_USD は N=0、GBP_USD は N=1 loss で、pair fit を証明できない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の該当行は 365d BT EV が `—`。local audit DB `demo_trades.db` には `atr_regime_break` / `alpha_atr_regime_break` の closed trade rows が 0 件。既存 target BT では USD_JPY N=0、EUR_USD N=0、GBP_USD N=1 WR=0%, PF=0.0 で、Wilson / PF / WF folds>=3 / Bonferroni / Kelly の decision-grade evidence は揃わない。数値は下表に分離する。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FORCED / INSUFFICIENT_N | 365d target BT は N=0。volatility regime break thesis の適否以前に発火なし。 |
| EUR_USD | FORCED / INSUFFICIENT_N | 365d target BT は N=0。発火なし。 |
| GBP_USD | FORCED / NEGATIVE_TINY_N | 365d target BT は N=1, WR=0.0%, EV=-1.95, PF=0.0。N=1 なので edge 判定不能だが、唯一の発火は loss。 |
| EUR_JPY | FORCED / INSUFFICIENT_N | sidecar 365d JPY BT では N=2, WR=100%, EV=+1.316 だが、N=2 で decision-grade ではない。 |
| Other ALL pairs | FORCED / UNTESTED | 実装に pair gate がなく ALL に適用されるが、tier-master / audit DB に pair-specific evidence がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で、実質的には FORCE_DEMOTED 系の低発火戦略として扱う。破綻軸は Axis 3 と Axis 4、補助的に Axis 7。Axis 2 の trigger は thesis を捉えており、Axis 5 の R:R も momentum breakout と整合するため、「思想は正、設計が誤」仮説に乗る候補ではある。ただし現行設計は quiet CV 下位 25% AND ATR 1.5x surge AND body/range gate AND HTF hard block の AND 過多で、既存 365d target BT は 3 pair 合計 N=1 に潰れている。

再設計案は filter と timing の 2 点を先に直す。第一に HTF Hard Block を削除し、必要なら hard gate ではなく score feature に降格する。regime 転換の初動は既存 HTF 方向と逆に出ることがあり、ここを切ると HMM regime gate same-trap と同じ構造で edge tail を失う。第二に signal bar を closed bar に固定し、`ctx.df.iloc[-2]` を signal、次 bar `ctx.entry` を execution とする variant を作る。併せて `(symbol, strategy, signal, bar_id)` の dedup を strategy または dispatch 層に追加する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は明確で trigger の中核も正しいため、完全棄却ではない。ただし現行の発火率は低すぎ、HTF hard block が regime tail を切る構造リスクを持つため、まずは「ATR quiet→surge→closed-bar direction」だけを残す薄い baseline に戻すべき。具体的には `ctx.htf["agreement"]` による逆方向 return を削除し、`bar_body >= 0.10ATR` と `bar_range >= 0.8ATR` は片方ずつ ablation できる feature に分離する。

コード差分の方向性は、`signal_bar = df.iloc[-2]`、`prev_bar = df.iloc[-3]`、`current_atr = atr_series.iloc[-2]`、`prev_atr = atr_series.iloc[-3]` として closed-bar trigger に寄せ、entry は次 bar の `ctx.entry` に限定する形が第一候補。BT は本タスクでは実行しないが、採用判断には 365d 以上で N>=30、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 audit table で再発行する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB: 0 closed rows; tier-master: `—`; 365d target BT: USD_JPY 0, EUR_USD 0, GBP_USD 1; sidecar EUR_JPY 365d JPY BT: 2 | `demo_trades.db`; `knowledge-base/wiki/tier-master.md`; `knowledge-base/raw/bt-results/bt-target-2026-04-17.json`; `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json` |
| Win rate | audit DB: INSUFFICIENT_EVIDENCE; 365d target BT aggregate USD_JPY/EUR_USD/GBP_USD: 0.0% on N=1; sidecar EUR_JPY: 100.0% on N=2 | same sources |
| Wilson lo (95%) | 365d target BT aggregate derived: 0.00% for 0 wins / 1 trade; sidecar EUR_JPY derived: 34.24% for 2 wins / 2 trades, but N=2 is not decision-grade | derived from existing BT counts in `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` and `knowledge-base/raw/bt-results/bt-365d-jpy-2026-04-22.json` |
| PF | 365d target BT: GBP_USD PF=0.0; USD_JPY/EUR_USD PF=999.0 sentinel due N=0 and non-informative; tier-master PF not present | `knowledge-base/raw/bt-results/bt-target-2026-04-17.json`; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: qualifying WF>=3 record for `alpha_atr_regime_break` / `atr_regime_break` target cell not found in tier-master or local audit DB | `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: tier-master and local audit DB do not provide a usable p-value; N=0-1 target BT makes test non-decision-grade | `knowledge-base/wiki/tier-master.md`; `demo_trades.db`; `knowledge-base/raw/bt-results/bt-target-2026-04-17.json` |
| Kelly fraction | 365d target BT aggregate derived: 0.0000 from WR=0.0% / PF=0.0 on the only realized trade; tier-master/audit DB Kelly not present | derived from `knowledge-base/raw/bt-results/bt-target-2026-04-17.json`; `knowledge-base/wiki/tier-master.md`; `demo_trades.db` |
