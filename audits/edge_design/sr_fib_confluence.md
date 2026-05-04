---
strategy: sr_fib_confluence
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

ADX が一定以上ある trend regime で、DT layer が SR/Fib または order-block confluence を示した時だけ、EMA score と EMA9/21 の方向へ入る trend-aligned confluence thesis。SR/Fib/OB の level 反応そのものはこの file 内では再計算せず、`dt_reasons` / `reasons` の内容に依存している。`strategies/daytrade/sr_fib_confluence.py:13`, `strategies/daytrade/sr_fib_confluence.py:24`, `strategies/daytrade/sr_fib_confluence.py:25`, `strategies/daytrade/sr_fib_confluence.py:26`, `strategies/daytrade/sr_fib_confluence.py:27`, `strategies/daytrade/sr_fib_confluence.py:33`, `strategies/daytrade/sr_fib_confluence.py:35`, `strategies/daytrade/sr_fib_confluence.py:42`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Momentum / trend-aligned thesis の EMA 側は `ema_score > 0.28 AND ema9 > ema21` で BUY、`ema_score < -0.28 AND ema9 < ema21` で SELL として捕捉できている。一方、SR/Fib/OB confluence は `any("Fib" in r or "フィボ" in r)` または `any("OB" in r or "オーダーブロック" in r)` という理由文字列の存在確認だけで、`abs(entry - fib_level) <= k*ATR`、support/resistance 近接、OB retest 範囲などの数学条件がこの strategy file にない。したがって `SR/Fib confluence ∧ EMA direction` thesis に対して、実装は `text_contains(Fib or OB) ∧ EMA direction` になっている。`strategies/daytrade/sr_fib_confluence.py:24`, `strategies/daytrade/sr_fib_confluence.py:25`, `strategies/daytrade/sr_fib_confluence.py:26`, `strategies/daytrade/sr_fib_confluence.py:27`, `strategies/daytrade/sr_fib_confluence.py:29`, `strategies/daytrade/sr_fib_confluence.py:33`, `strategies/daytrade/sr_fib_confluence.py:35`, `strategies/daytrade/sr_fib_confluence.py:42` |
| 3 (timing window) | LOOKAHEAD | `evaluate()` は `ctx.entry`, `ctx.ema_score`, `ctx.ema9`, `ctx.ema21`, `ctx.adx`, `ctx.atr7` を current context から直接読み、strategy 内に signal bar の closed-bar 固定、signal→next-bar execution 分離、または `(symbol, signal, bar_time)` dedup がない。明示的な未来参照は見えないが、実行層が intrabar evaluate する契約なら、未確定 EMA/entry と理由文字列で同一 bar 多重 entry が起き得るため spec 上は LOOKAHEAD 寄りの timing risk。`strategies/daytrade/sr_fib_confluence.py:16`, `strategies/daytrade/sr_fib_confluence.py:17`, `strategies/daytrade/sr_fib_confluence.py:25`, `strategies/daytrade/sr_fib_confluence.py:33`, `strategies/daytrade/sr_fib_confluence.py:35`, `strategies/daytrade/sr_fib_confluence.py:40`, `strategies/daytrade/sr_fib_confluence.py:42`, `strategies/daytrade/sr_fib_confluence.py:47`, `strategies/daytrade/sr_fib_confluence.py:57`, `strategies/daytrade/sr_fib_confluence.py:68` |
| 4 (filter coherence) | STRENGTHENS / BREAKS | ADX gate `ctx.adx >= 20` は trend-aligned thesis には STRENGTHENS。EMA score fallback `(ema9 - ema21) / ATR` と EMA9/21 direction gate も momentum direction を補強する。ただし、SR/Fib/OB confluence を文字列 reason で受ける gate は NEUTRAL ではなく設計上 BREAKS 寄りで、上流の reason 文言・翻訳・✅ 形式に edge 定義が結合する。MR strategy に MA filter を足して tail を消す型や HMM regime gate same-trap のような regime tail hard block はこの file では未検出だが、文字列 gate は別種の structural filter failure。`strategies/daytrade/sr_fib_confluence.py:13`, `strategies/daytrade/sr_fib_confluence.py:17`, `strategies/daytrade/sr_fib_confluence.py:25`, `strategies/daytrade/sr_fib_confluence.py:26`, `strategies/daytrade/sr_fib_confluence.py:27`, `strategies/daytrade/sr_fib_confluence.py:29`, `strategies/daytrade/sr_fib_confluence.py:33`, `strategies/daytrade/sr_fib_confluence.py:35`, `strategies/daytrade/sr_fib_confluence.py:42`, `strategies/daytrade/sr_fib_confluence.py:57` |
| 5 (stop/TP geometry) | ALIGNED | 通常時は BUY `TP=entry+2.0*ATR7`, `SL=entry-1.0*ATR7`、SELL は対称なので nominal R:R は `2.0:1.0 = 2.0`。round number 近傍では SL をさらに `0.3*ATR7` 深くするため実効 R:R は概ね `2.0:1.3 = 1.54` へ落ちるが、trend-aligned confluence / momentum continuation の asymm geometry としては整合する。TP を round number 内側へ 3 pips ずらす処理は利幅を削る可能性があるが、stop/TP 思想自体を破壊するほどではない。`strategies/daytrade/sr_fib_confluence.py:40`, `strategies/daytrade/sr_fib_confluence.py:41`, `strategies/daytrade/sr_fib_confluence.py:47`, `strategies/daytrade/sr_fib_confluence.py:48`, `strategies/daytrade/sr_fib_confluence.py:53`, `strategies/daytrade/sr_fib_confluence.py:55`, `strategies/daytrade/sr_fib_confluence.py:57`, `strategies/daytrade/sr_fib_confluence.py:61`, `strategies/daytrade/sr_fib_confluence.py:62`, `strategies/daytrade/sr_fib_confluence.py:64` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。コード上は pair-specific thesis を持たず、JPY pip size 以外は ALL に同一 trigger を適用する。既存 evidence は GBP_USD の一部 session だけが相対的に良く、EUR_JPY / USD_JPY は悪い cell が目立つため、ALL scope は forced broad scope。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative partial evidence | tier-master force_demoted 行は 365d BT EV が `—`。既存 audit output では strategy aggregate N=36, WR=38.89%, Wilson lo=24.78%, EV=-1.78p, PF=0.671, clamped Kelly=0.0000, raw Kelly=-0.1907, Bonferroni p=1.0000。WF folds>=3 は exact ALL cell で見つからないため、`feedback_partial_quant_trap.md` 基準では decision-grade 不足。ただし available evidence は正ではなく、force demotion と整合する。 |

### Axis 6 Pair-Regime Fit Detail

| Pair | Fit | Basis |
|------|-----|-------|
| GBP_USD | FIT / narrow | H1 counterfactual では London N=23, WR=39.1%, PF=1.31, Kelly raw=0.091, NY-overlap N=12, WR=58.3%, PF=2.24, Kelly raw=0.323。ただしいずれも Bonferroni p=1.0000 で decision-grade ではない。 |
| EUR_USD | FORCED / weak | London N=22, WR=36.4%, PF=1.22, Kelly raw=0.066 と小さく、NY-overlap N=13, WR=23.1%, PF=0.52。ALL 復帰を支えるほどではない。 |
| USD_JPY | FORCED / failed | Asia N=9, WR=22.2%, PF=0.71、London N=7, WR=0.0%, PF=0.00、NY-overlap N=8, WR=12.5%, PF=0.21。Off N=7 は positive だが小標本。 |
| EUR_JPY | FORCED / failed | Asia N=11, WR=18.2%, PF=0.28、London N=13, WR=0.0%, PF=0.00、NY-overlap N=7, WR=14.3%, PF=0.30。 |
| GBP_JPY | FORCED / insufficient | NY-overlap N=4, Off N=3 は positive だが N が小さく、Asia/London は弱い。 |
| EUR_GBP | FORCED / insufficient | London N=1, WR=0.0%, PF=0.00 のみ。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) なので failure mode 診断を適用する。破綻軸は Axis 2、Axis 3、Axis 4、補助的に Axis 6。Axis 5 の 2:1 前後の geometry は trend-aligned thesis と大きく矛盾しないが、trigger が SR/Fib/OB の数値条件ではなく上流 reason の文字列パースで、closed-bar / dedup の契約も strategy 内に存在しない。過去 audit にある「理由文字列パースに依存（実装の構造的欠陥）」という評価とも一致する。

再設計案は、思想を維持して trigger と timing を作り直すこと。`dt_reasons` 文字列ではなく、上流 DT layer から `fib_level`, `sr_level`, `ob_zone_low/high`, `confluence_type`, `signal_bar_time` のような構造化 feature を `ctx.layer3` に渡し、この file では `abs(ctx.entry - fib_level) <= 0.35*ATR` または `ob_zone_low <= entry <= ob_zone_high` を hard gate にする。さらに EMA direction は残しつつ、signal 判定を確定済み bar に固定し、execution は次 bar の `ctx.entry` に分離する。dedup key は `(sr_fib_confluence, symbol, signal, signal_bar_time, confluence_type)` が最低限必要。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は棄却しない。SR/Fib/OB confluence を trend direction に乗せる仮説はコードから導出でき、ADX/EMA と 2:1 geometry も大枠では thesis に沿っている。一方で、edge の中核である confluence 判定が文字列 reason による proxy で、bar-close / dedup contract も file 内にないため、単一 filter 削除では復活しない。

具体修正は 2 系統。第一に、`_has_sr_fib` / `_has_ob` を文字列検索から構造化 feature gate に置換する。例: `ctx.layer3["sr_fib"] = {"kind": "fib_retest", "level": ..., "distance_atr": ..., "signal_bar": ...}` を受け、`distance_atr <= 0.35` と `ema_score` direction を同時に満たす時だけ Candidate を返す。第二に、current context 直読みを closed signal bar 評価へ寄せ、同一 signal bar の多重 emit を抑止する。採用前には本 audit では実行しない 365d / WF folds>=3 / Wilson / PF / Bonferroni / Kelly の再集計が必要。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master force_demoted ALL: `—`; latest strategy aggregate: N=36; older shadow L1: N=102; H1 counterfactual has per pair/session rows only | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Win rate | latest aggregate: 38.89%; older shadow L1: 24.5%; H1 best larger cell GBP_USD London: 39.1% (N=23) | same as above |
| Wilson lo (95%) | latest aggregate: 24.78%; older shadow L1 top cell GBP_USD×london×BUY: 26.8%; H1 GBP_USD London row reports 0.222 | same as above |
| PF | latest aggregate: 0.671; older shadow L1: 0.39; H1 GBP_USD London: 1.31, GBP_USD NY-overlap: 2.24 but both small / Bonferroni-failed | same as above |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: older shadow has only pre/post split (60/42), not WF folds>=3; exact ALL WF>=3 table not found in tier-master/current audit DB | `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md`; `knowledge-base/wiki/tier-master.md` |
| Bonferroni-adj p | latest aggregate: 1.0000; H1 pair/session rows mostly 1.0000, EUR_JPY London 0.0673 but negative; older best cell Bonferroni failed | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md`; `knowledge-base/wiki/sessions/task1-shadow-tp-hit-deep-2026-04-21.md` |
| Kelly fraction | latest aggregate: clamped Kelly 0.0000, raw Kelly -0.1907; older shadow L1 Kelly -39.1%; H1 GBP_USD London raw Kelly 0.091 and NY-overlap 0.323 are small-cell / Bonferroni-failed | same as above |
