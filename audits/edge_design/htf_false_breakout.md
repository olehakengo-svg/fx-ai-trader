---
strategy: htf_false_breakout
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

1H 相当の直近 SR を実体 Close で一度突破した後、短時間で SR 内へ戻る動きは本物の breakout ではなく liquidity sweep / false breakout であり、逆方向へ fade してレンジ中央への回帰を取る、という MR/stop-hunt fade thesis。これは SR 計算、実体 breakout、SR 内回帰、逆方向 entry の一連の条件から導出できる（`strategies/daytrade/htf_false_breakout.py:13`, `strategies/daytrade/htf_false_breakout.py:14`, `strategies/daytrade/htf_false_breakout.py:15`, `strategies/daytrade/htf_false_breakout.py:16`）。

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Thesis は「1H足の実体 Close が SR 外へ出る」だが、実装は 15m DataFrame 上の単一 `_bar_close > _sr_high` / `_bar_close < _sr_low` を走査しており、4本単位の 1H OHLC 集約がない（`strategies/daytrade/htf_false_breakout.py:67`, `strategies/daytrade/htf_false_breakout.py:68`, `strategies/daytrade/htf_false_breakout.py:76`, `strategies/daytrade/htf_false_breakout.py:90`, `strategies/daytrade/htf_false_breakout.py:96`）。実装式は `exists 15m close outside SR ∧ current_close back inside SR` で、意図式 `H1_close outside SR ∧ 1-4 subsequent 15m closes back inside SR` より粗い。 |
| 3 (timing window) | LATE | `_sr_slice = ctx.df.iloc[-_h1_equiv - 8: -4]` は直近4本だけを除外するため、`_offset >= 5` の候補 breakout bar が SR 計算窓へ混入し、実質的に offset=4 近辺の遅延 signal へ潰れる（`strategies/daytrade/htf_false_breakout.py:59`, `strategies/daytrade/htf_false_breakout.py:75`, `strategies/daytrade/htf_false_breakout.py:76`）。さらに entry は breakout bar ではなく現在 Close の SR 内復帰確認後で、signal latency は最低4本の 15m bar 後になる（`strategies/daytrade/htf_false_breakout.py:106`, `strategies/daytrade/htf_false_breakout.py:108`, `strategies/daytrade/htf_false_breakout.py:109`, `strategies/daytrade/htf_false_breakout.py:111`）。 |
| 4 (filter coherence) | STRENGTHENS | SR range minimum は狭すぎる noise range を除外し thesis を補強する（`strategies/daytrade/htf_false_breakout.py:64`）。JPY の RSI divergence / OB proximity gate は JPY の本物 breakout 誤認を減らす確認 filter として coherent（`strategies/daytrade/htf_false_breakout.py:121`, `strategies/daytrade/htf_false_breakout.py:139`, `strategies/daytrade/htf_false_breakout.py:144`, `strategies/daytrade/htf_false_breakout.py:156`, `strategies/daytrade/htf_false_breakout.py:160`）。MTF agreement gate は MR 戦略への MA filter 乱用や HMM regime gate same-trap の先行例と異なり、trend 方向の本物 breakout を除外する目的に限定されているため STRENGTHENS と判定する（`strategies/daytrade/htf_false_breakout.py:166`, `strategies/daytrade/htf_false_breakout.py:178`, `strategies/daytrade/htf_false_breakout.py:179`, `strategies/daytrade/htf_false_breakout.py:194`）。 |
| 5 (stop/TP geometry) | ALIGNED | SELL は `TP = min(SR center side, entry - 1.5ATR)` 相当、`SL = break_high + 0.3ATR`、BUY は対称に `TP = max(SR center side, entry + 1.5ATR)` 相当、`SL = break_low - 0.3ATR` で、false breakout fade の「外側に stop、レンジ中央へ利確」と整合する（`strategies/daytrade/htf_false_breakout.py:38`, `strategies/daytrade/htf_false_breakout.py:39`, `strategies/daytrade/htf_false_breakout.py:40`, `strategies/daytrade/htf_false_breakout.py:183`, `strategies/daytrade/htf_false_breakout.py:184`, `strategies/daytrade/htf_false_breakout.py:188`, `strategies/daytrade/htf_false_breakout.py:198`, `strategies/daytrade/htf_false_breakout.py:199`, `strategies/daytrade/htf_false_breakout.py:202`）。R:R は固定値ではなく、reward は最大でも SR center または 1.5ATR 近辺、risk は `abs(entry - break_extreme) + 0.3ATR` の動的値。 |
| 6 (pair-regime fit) | FORCED | 既存 730d WF では GBP_JPY が FIT、EUR_JPY が FIT 寄り、GBP_USD は borderline、EUR_USD/USD_JPY は folds 不足。ALL 一括は pair-regime を強制している。詳細は下表。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 365d BT EV は入力時点で `—`。既存 audit DB の latest strategy aggregate は N=1, WR=100%, Wilson lo=20.65%, PF=inf, Kelly=0.0000, Bonferroni p=1.0000 で、`feedback_partial_quant_trap.md` 基準の Wilson/PF/WF/Bonferroni/Kelly を満たさない。3month counterfactual も shadow cell は EUR_JPY N=5 WR=0%, GBP_JPY N=1 WR=0%, GBP_USD N=1 WR=100%, USD_JPY N=1 WR=0% で全て insufficient data。 |

### Axis 6 Pair-Regime Fit Detail

| Pair | Fit | Basis |
|---|---|---|
| EUR_USD | FORCED | 730d WF: N=31, folds=0, N_windows<2 |
| EUR_JPY | FIT | 730d WF: N=52, +0.263 EV, stable |
| GBP_JPY | FIT | 730d WF: N=65, +0.515 EV, stable |
| GBP_USD | FORCED | 730d WF: N=49, -0.264 EV, borderline |
| USD_JPY | FORCED | 730d WF: N=22, folds=0, N_windows<2 |

## Axis 8: failure mode 診断

Tier 2 Shadow だが、既存 evidence は N=1 の小標本で、phase0_shadow のまま昇格判断に耐えない。破綻軸は Axis 2 と Axis 3。思想は false breakout fade として明確だが、実装は 1H close breakout を数学的に作らず、15m 単体 close を疑似 1H として扱っている。さらに SR slice が breakout 候補 bar を混ぜるため、breakout 検出窓がコメント通りの 1-4本確認になっていない。

再設計案は、trigger/timing を一体で直すこと。15m df から明示的に 1H OHLC を resample/aggregate し、SR は breakout 1H bar より前の 20本だけで計算する。その後、breakout 1H bar の close が SR 外へ出たことを state として保持し、次の 1-4本の closed 15m bar で SR 内へ戻った最初の close だけを entry signal とする。ALL 運用ではなく、既存 WF が安定している GBP_JPY/EUR_JPY を優先 shadow cell に絞り、GBP_USD/EUR_USD/USD_JPY は redesign 後 BT で再判定する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

Trigger/timing の 1 系統修正で復活余地がある。具体的には、`_sr_slice` を現在時点基準ではなく breakout 候補 1H bar 基準に変更し、`for _offset in range(...)` で 15m 単体 bar を見る処理を廃止する。想定 diff は、1H resample 済み series から `break_h1 = h1.iloc[-2]` などの closed H1 bar を選び、`sr_high/low = h1.iloc[-22:-2].High/Low` のように breakout bar を含めない窓で計算し、15m re-entry は breakout 後の closed 15m bars のみを対象にする形。

Filter は現時点では削除しない。MA filter breaks MR / HMM gate same-trap の先行例に照らすと MR thesis への regime gate は危険だが、この実装の MTF gate は「trend 方向の本物 breakout を避ける」片側 veto で、thesis を壊している主因ではない。Stop/TP は一旦維持し、redesign BT で wick が大きい false breakout だけ stop が遠くなりすぎる場合に `sl_atr_buffer` と `tp_min_atr` を pair 別に再調整する。

必要 BT: redesign 後に pair 別 365d と 730d WF を実行し、最低でも pair×strategy で N>=30、Wilson lo、PF、3 folds 以上、Bonferroni-adjusted p、Kelly fraction を同時に出す。現 evidence だけでは昇格不可。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 1 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Win rate | 100.00% | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Wilson lo (95%) | 20.65% | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate; N=1 のため INSUFFICIENT_EVIDENCE |
| PF | inf | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate; N=1 のため信頼不可 |
| WF folds (3+) | GBP_JPY: 5 folds stable; EUR_JPY: 2 folds stable; GBP_USD: 2 folds borderline; EUR_USD/USD_JPY: 0 folds | existing WF: `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.md`; ALL aggregate としては INSUFFICIENT_EVIDENCE |
| Bonferroni-adj p | 1.0000 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
| Kelly fraction | 0.0000 | audit DB: `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` strategy aggregate |
