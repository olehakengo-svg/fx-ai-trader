---
strategy: doji_breakout
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: GBP_USD, USD_JPY
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

連続 Doji で短期レンジが圧縮された後、次の大きな実体足が示す方向へボラティリティ解放が起きる、という breakout follow 戦略。コードコメントは「連続Doji後のボラティリティ解放ブレイクアウト」とし、3本 Doji の後に `abs(Close - Open) > ATR * 0.5` の breakout 足を追うと定義している。`strategies/daytrade/doji_breakout.py:2`, `strategies/daytrade/doji_breakout.py:15`, `strategies/daytrade/doji_breakout.py:18`, `strategies/daytrade/doji_breakout.py:23`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Doji 圧縮レンジ breakout thesis なら BUY は `bo_close > doji_high`、SELL は `bo_close < doji_low` が最低条件になるべきだが、実装は `bo_body > ctx.atr * 0.5` と `bo_close > bo_open` / `< bo_open` のみで方向を決め、Doji レンジ外への close を要求していない。`doji_high/doji_low` は計算されるが trigger には使われず、SL 計算にしか使われない。`strategies/daytrade/doji_breakout.py:104`, `strategies/daytrade/doji_breakout.py:118`, `strategies/daytrade/doji_breakout.py:127`, `strategies/daytrade/doji_breakout.py:132`, `strategies/daytrade/doji_breakout.py:137`, `strategies/daytrade/doji_breakout.py:154` |
| 3 (timing window) | OK | 3本 Doji は `df.iloc[-5:-2]`、breakout 足は確定済みの `df.iloc[-2]`、entry は次足側の `ctx.entry` として扱われ、breakout 足自身の未確定 intrabar close を参照していない。戦略内に per-bar dedup 状態はないため実行層依存だが、この関数単体では 1 evaluate につき 1 Candidate のみ返す。`strategies/daytrade/doji_breakout.py:91`, `strategies/daytrade/doji_breakout.py:97`, `strategies/daytrade/doji_breakout.py:125`, `strategies/daytrade/doji_breakout.py:150`, `strategies/daytrade/doji_breakout.py:229` |
| 4 (filter coherence) | STRENGTHENS | hard filter は pair universe と ATR 正値ガード。pair filter は対象を USDJPY/EURUSD/GBPUSD に限定し、今回の pair_promoted 対象 GBP_USD/USD_JPY とは衝突しない。HTF agreement / EMA alignment / ADX は entry 阻止ではなく score bonus なので、MA filter on MR や HMM same-trap のように thesis tail を破壊する gate ではない。`strategies/daytrade/doji_breakout.py:44`, `strategies/daytrade/doji_breakout.py:75`, `strategies/daytrade/doji_breakout.py:84`, `strategies/daytrade/doji_breakout.py:195`, `strategies/daytrade/doji_breakout.py:203`, `strategies/daytrade/doji_breakout.py:209` |
| 5 (stop/TP geometry) | MISALIGNED | SL は Doji レンジ反対端 +/- `0.3ATR` で compression range の外側に置くため妥当だが、TP は固定 `2.0ATR` か `MIN_RR=1.2` 補正のみで、breakout thesis に望ましい trailing / structure-follow がない。`MAX_HOLD_BARS=6` も実装上の exit geometry として Candidate へ渡されていない。`strategies/daytrade/doji_breakout.py:52`, `strategies/daytrade/doji_breakout.py:53`, `strategies/daytrade/doji_breakout.py:54`, `strategies/daytrade/doji_breakout.py:55`, `strategies/daytrade/doji_breakout.py:56`, `strategies/daytrade/doji_breakout.py:152`, `strategies/daytrade/doji_breakout.py:171` |
| 6 (pair-regime fit) | FIT | GBP_USD は 365d BT で N=23, WR=78.3%, EV=+0.724, PF=2.47 の positive pocket があり、tier-master でも GBP_USD EV=+0.694。USD_JPY は 365d BT で N=21, WR=61.9%, EV=+0.338, PF=1.40、tier-master EV=+0.339。両方ともレンジ圧縮からの短期 breakout には自然な pair fit だが、USD_JPY は PF が薄く watch 寄り。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | N/WR/EV/PF は既存 BT scan と tier-master から確認できるが、WF は GBP_USD でも folds=2 止まり、USD_JPY は 730d で folds=0。Bonferroni-adjusted p と BT Kelly は既存 tier-master に存在せず、Audit B でも doji_breakout は N不足のため Bonferroni 計算意味なしとされている。数値は下表。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| GBP_USD | FIT / WATCH | tier-master EV `+0.694`; 365d BT reference N=23, WR=78.3%, PF=2.47。ただし live divergence scan では N=3, WR=0.0%, EV=-8.800 の劣化観測があり、小 N のため watch。 |
| USD_JPY | FIT / WATCH | tier-master EV `+0.339`; 365d BT reference N=21, WR=61.9%, PF=1.40。Audit B 再計測では N=7, WR=57.1%, EV=+0.435 で N 不足、live は N=1 のみ。 |

## Axis 8: failure mode 診断

Tier 1 (LIVE) だが、GBP_USD は live divergence scan で BT 20/65.0%/+0.143 に対し live 3/0.0%/-8.800 と劣化し、USD_JPY も Audit B で N=7 まで低下して `insufficient` 扱いになっているため Axis 8 を適用する。破綻軸は Axis 2 と Axis 5。最大の問題は、Doji レンジ圧縮を検出しているのに breakout trigger がレンジ外 close を要求しない点で、large body candle を breakout と誤認する設計になっている。

再設計案は trigger を `BUY: bo_close > doji_high + buffer` / `SELL: bo_close < doji_low - buffer` に変更し、`buffer = max(spread, 0.1 * ATR)` 程度で false break を抑えること。加えて stop/TP は固定 TP のまま即変更せず、まず `tp = entry +/- 1.5ATR` 部分利確 + 残り trailing、または `trailing stop = breakout bar midpoint / 1ATR` の候補を shadow BT 対象にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

最優先の修正は trigger 1 系統。現在の `bo_body > ATR * 0.5` と candle direction は「勢いのある足」検出であって、「Doji レンジの外へ抜けた」ことを保証しない。`doji_high/doji_low` は既に計算済みなので、コードレベルでは `bo_close > doji_high + breakout_buffer` または `bo_close < doji_low - breakout_buffer` を Step 2 に追加するのが最小差分になる。

Stop/TP は second-order。SL は Doji レンジ反対端を使う思想に合っているため維持し、TP だけを fixed ATR から breakout follow 型の trailing へ置換する案を別 variant として検証する。新規 BT が必要なため、本監査では実装変更せず、Wave 4 の redesign queue では trigger 修正を A 優先で扱う。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | GBP_USD BT N=23; USD_JPY BT N=21; Audit B USD_JPY recheck N=7; live USD_JPY N=1; live GBP_USD specific closed sample not found in production audit | `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md`; `knowledge-base/wiki/analyses/audit-b-promoted-strategies-2026-04-21.md`; `raw/audits/phase_a_production_audit_2026-04-27.md` |
| Win rate | GBP_USD BT 78.3%; USD_JPY BT 61.9%; Audit B USD_JPY 57.1%; live USD_JPY 100.0% on N=1 | same sources |
| Wilson lo (95%) | GBP_USD BT-derived 58.1%; USD_JPY BT-derived 40.9%; Audit B USD_JPY derived 25.0%; live USD_JPY 20.6% | derived from existing N/WR; live Wilson from `raw/audits/phase_a_production_audit_2026-04-27.md` |
| PF | GBP_USD 2.47; USD_JPY 1.40; tier-master itself has EV only and no PF column | `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md`; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | GBP_USD W60/W90: 2 folds, positive ratio 0.50, PF 2.17; GBP_USD 730d: 0 folds; USD_JPY 730d: 0 folds. Fails WF>=3 requirement. | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.md` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: Audit B states doji_breakout N不足のため Bonferroni 計算意味なし; tier-master has no p-value | `knowledge-base/wiki/analyses/audit-b-promoted-strategies-2026-04-21.md`; `knowledge-base/wiki/tier-master.md` |
| Kelly fraction | live USD_JPY cell Kelly `+0.000`; BT/tier-master pair-level Kelly unavailable; monthly audit states current cells are N<10/N insufficient for Kelly adoption | `raw/audits/phase_a_production_audit_2026-04-27.md`; `knowledge-base/raw/audits/2026-05-03-monthly.md` |
| tier-master EV | GBP_USD `+0.694`; USD_JPY `+0.339` | `knowledge-base/wiki/tier-master.md` |
