---
strategy: macdh
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

BB %B の下限/上限 extreme と RSI5 の短期売られすぎ/買われすぎを前提に、MACD-H が直前 2 本の減速から反転した瞬間を平均回帰 entry として拾う MR 戦略。Tier1 は BB extreme がさらに深い時だけ TP を拡張する高確信版として扱う。`strategies/scalp/macdh.py:1`, `strategies/scalp/macdh.py:11`, `strategies/scalp/macdh.py:14`, `strategies/scalp/macdh.py:15`, `strategies/scalp/macdh.py:16`, `strategies/scalp/macdh.py:17`, `strategies/scalp/macdh.py:21`, `strategies/scalp/macdh.py:22`, `strategies/scalp/macdh.py:54`, `strategies/scalp/macdh.py:74`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `bbpb < 0.30 AND macdh > macdh_prev AND macdh_prev <= macdh_prev2 AND rsi5 < 48 AND abs(macdh-macdh_prev) >= avg(abs(prev),abs(prev2))*0.5`、SELL は `bbpb > 0.70 AND macdh < macdh_prev AND macdh_prev >= macdh_prev2 AND rsi5 > 52 AND same strength gate`。BB extreme、RSI extreme、MACD-H 反転があり、oversold/overbought + exhaustion reversal を数学的に捕捉している。`strategies/scalp/macdh.py:14`, `strategies/scalp/macdh.py:15`, `strategies/scalp/macdh.py:16`, `strategies/scalp/macdh.py:17`, `strategies/scalp/macdh.py:24`, `strategies/scalp/macdh.py:50`, `strategies/scalp/macdh.py:51`, `strategies/scalp/macdh.py:52`, `strategies/scalp/macdh.py:55`, `strategies/scalp/macdh.py:56`, `strategies/scalp/macdh.py:57`, `strategies/scalp/macdh.py:58`, `strategies/scalp/macdh.py:75`, `strategies/scalp/macdh.py:76`, `strategies/scalp/macdh.py:77`, `strategies/scalp/macdh.py:78` |
| 3 (timing window) | LOOKAHEAD | `evaluate()` は `ctx.bbpb`, `ctx.rsi5`, `ctx.macdh`, `ctx.entry` を現在の context から直接読み、strategy 内に確定足固定、signal bar と execution bar の分離、または `(symbol, bar_time, signal)` dedup がない。明示的な未来参照は見えないが、実行層が未確定足で複数回評価する契約なら current-bar MACD-H 反転の先読み/同 bar 多重 entry になり得る。加えて MACD-H の `prev2 -> prev -> current` 反転確認は構造的に反転後追いで、既存 force-demoted 分析の「1-3pip 遅延」と整合する。`strategies/scalp/macdh.py:35`, `strategies/scalp/macdh.py:50`, `strategies/scalp/macdh.py:51`, `strategies/scalp/macdh.py:55`, `strategies/scalp/macdh.py:56`, `strategies/scalp/macdh.py:57`, `strategies/scalp/macdh.py:71`, `strategies/scalp/macdh.py:72`, `strategies/scalp/macdh.py:75`, `strategies/scalp/macdh.py:76`, `strategies/scalp/macdh.py:77`, `strategies/scalp/macdh.py:90`, `strategies/scalp/macdh.py:91`, `strategies/scalp/macdh.py:98` |
| 4 (filter coherence) | STRENGTHENS | EURGBP disable は pair-level 除外で、ALL 適用の過剰範囲を狭めるため STRENGTHENS。XAUUSD/USDJPY の hour block と Death Valley コメントも、MR/scalp が摩擦・時間帯ノイズに負ける局面を外す意図なので STRENGTHENS。ただし `_death_valley_hours` は定義だけで `evaluate()` では未使用のため NEUTRAL。`apply_penalty(..., strategy_type='MR', ctx.adx)` は高 ADX 逆張りを減点する一般 MR penalty で、MA filter on MR / HMM same-trap のような明確な hard gate 破壊ではないが、EUR_USD high-ADX winner evidence とは衝突し得る注意点。`strategies/scalp/macdh.py:26`, `strategies/scalp/macdh.py:27`, `strategies/scalp/macdh.py:29`, `strategies/scalp/macdh.py:30`, `strategies/scalp/macdh.py:31`, `strategies/scalp/macdh.py:32`, `strategies/scalp/macdh.py:37`, `strategies/scalp/macdh.py:39`, `strategies/scalp/macdh.py:40`, `strategies/scalp/macdh.py:97` |
| 5 (stop/TP geometry) | MISALIGNED | 通常は BUY `TP=entry+1.5ATR`, `SL=entry-1.0ATR`、SELL `TP=entry-1.5ATR`, `SL=entry+1.0ATR` で R:R=1.5。Tier1 でも `TP=1.8ATR`, `SL=1.0ATR` で R:R=1.8。MR thesis なら mean へ戻る前に切られない wide stop と friction-resistant TP が必要だが、既存実測は WR 32.26%, PF 0.468, Kelly 0 で、R:R 1.5 の損益分岐 WR 約 40% に届かない。コード上も stop は単純 1ATR で、BB 外側・直近 swing・time stop を見ていない。`strategies/scalp/macdh.py:18`, `strategies/scalp/macdh.py:19`, `strategies/scalp/macdh.py:23`, `strategies/scalp/macdh.py:71`, `strategies/scalp/macdh.py:72`, `strategies/scalp/macdh.py:90`, `strategies/scalp/macdh.py:91` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。コードは EURGBP を完全停止し、XAUUSD/USDJPY だけ時間帯 block を持つが、phase0_shadow/ALL の一括扱いに対して pair-specific な適合根拠は弱い。tier-master では `macdh_reversal` は force_demoted と pair_demoted(GBP_USD) にも出ており、ALL scope は現行 evidence と衝突する。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / NEGATIVE | tier-master phase0_shadow / ALL 365d BT EV は `—`。ただし既存 audit DB/decision log では strategy aggregate N=62, WR=32.26%, Wilson lo=21.95%, EV=-0.90, PF=0.468, Kelly=0.0000, raw Kelly=-0.3664, Bonferroni p=1.0000。H1 hour-bucket 3-month shadow も Bonferroni p=1.0000 が並び、WF folds>=3 は見つからない。`feedback_partial_quant_trap.md` 基準では採用根拠不足、かつ既存値は negative。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_USD | FIT / unstable | MR trigger 自体は major pair に適用可能。H1 shadow cells は Asia N=6 WR=16.7% PF=0.09、London N=12 WR=25.0% PF=0.16、NY-overlap N=5 WR=40.0% PF=1.48。tp-hit causal deep では EUR_USD baseline N=51 WR=31.4% PF=0.46 だが、`_direction=SELL ∧ _atr_q=Q4` は N=13 WR=61.5% PF=1.99 と rescue tail がある。 |
| GBP_USD | FORCED | tier-master pair_demoted に GBP_USD が明記される。H1 shadow cells は London N=4 WR=25.0% PF=0.57、NY-overlap N=2 WR=50.0% PF=2.18 で N が薄く、ALL 適用根拠にならない。 |
| USD_JPY | FORCED / negative | H1 shadow cells は Asia N=14 WR=14.3% PF=0.28、London N=11 WR=36.4% PF=0.83、NY-overlap N=15 WR=26.7% PF=0.25、Off N=7 WR=0.0% PF=0.00。tp-hit causal deep baseline も N=56 WR=23.2% PF=0.32。 |
| EURGBP | FORCED / BLOCKED | `_disabled_symbols` で実装上は取引不可。ALL scope と実装の tradable universe が一致しない。`strategies/scalp/macdh.py:27`, `strategies/scalp/macdh.py:37`, `strategies/scalp/macdh.py:38` |
| XAUUSD | FORCED / insufficient | XAUUSD は 12-15 UTC block だけあるが、prompt の pair scope は ALL であり、decision-grade の Wilson/PF/WF/Kelly は確認できない。`strategies/scalp/macdh.py:31` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) 指定だが、現行 tier-master では force_demoted と pair_demoted(GBP_USD) にも現れ、strategy aggregate は N=62, WR=32.26%, Wilson lo=21.95%, EV=-0.90, PF=0.468, Kelly=0.0000, Bonferroni p=1.0000。failure mode 診断対象として扱う。

破綻軸は Axis 3 と Axis 5。Axis 2 の thesis/trigger はコードから明確で、BB/RSI extreme と MACD-H exhaustion reversal は MR と整合している。Axis 4 の pair/time filter も大きくは破壊していない。一方、MACD-H 反転を current context で読み、bar-close/dedup 契約が strategy 内にないため、実運用では未確定足反転または同 bar 多重 entry の timing risk が残る。さらに 1ATR stop / 1.5ATR TP は、実測 WR 32.26% と摩擦負けに対して損益分岐を満たせず、MR が平均へ戻る前に切られる geometry になっている。

再設計案は、MACD-H 反転の「1本早い検出」という思想だけ残し、entry を確定足の次 bar に固定した 5m variant へ分離すること。Trigger は `signal_row = closed[-2]` で `bbpb <= 0.15/0.85` の Tier1 のみ、かつ `rsi5` を現行 48/52 からより extreme 側へ戻す。Filter は ALL ではなく EUR_USD NY/ATR高位または USD_JPY NY/ADX中位など既存 rescue tail だけに限定し、GBP_USD と EURGBP は除外する。Stop/TP は `SL = max(1.5ATR, band_outer_or_swing_distance)`、`TP = max(2.5ATR, 2.0R)` または time-stop 併用へ変更し、採用前に 365d + WF folds>=3 + Bonferroni/Kelly を同一 pipeline で再集計する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は捨てない。コードからは「BB/RSI extreme の中で MACD-H の反転を他の MR より早く拾う」という thesis が直接読め、Axis 2 は成立している。ただし現行の `ALL` scope、current-bar timing 契約、1ATR/1.5ATR geometry の組み合わせは既存実測の低 WR・低 PF と整合せず、単一行削除では復活しない。

具体修正は 3 点。まず signal 判定を closed bar に固定し、次 bar 約定 + `(symbol, signal, signal_bar_time)` dedup を入れる。次に trigger を Tier1 extreme 専用へ寄せ、`bbpb <= 0.15` / `>= 0.85` と RSI extreme を必須化し、MACD-H 反転強度は維持する。最後に pair/session/regime を ALL から切り離し、EUR_USD NY + ATR高位の SELL tail、USD_JPY NY + ADX中位 tail のような事前登録 cell だけを再検証する。BT は本 audit では実行しないため、必要 BT は 365d / 5m / cell-specific / WF folds>=3 / Bonferroni-adjusted p / Kelly 付きの再集計。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | tier-master phase0_shadow ALL: `—`; gate-progression strategy aggregate: 62; H1 shadow bucket total in listed cells: 76 | prompt tier-master input; `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Win rate | gate-progression aggregate: 32.26%; H1 shadow buckets range 0.0%-50.0% with most cells negative EV | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Wilson lo (95%) | gate-progression aggregate: 21.95%; H1 shadow buckets include EUR_USD London 8.9%, USD_JPY NY-overlap 10.9%, USD_JPY Off 0.0% | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| PF | gate-progression aggregate: 0.468; H1 shadow buckets: EUR_USD Asia 0.09, London 0.16, NY-overlap 1.48; GBP_USD London 0.57, NY-overlap 2.18; USD_JPY Asia 0.28, London 0.83, NY-overlap 0.25, Off 0.00 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: tier-master/audit DB search did not find macdh_reversal ALL WF folds>=3 suitable for promotion-grade evidence | `knowledge-base/wiki/tier-master.md`; local search of `knowledge-base/raw/bt-results/` and `knowledge-base/wiki/` |
| Bonferroni-adj p | gate-progression aggregate: 1.0000; all listed H1 shadow buckets: 1.0000 | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
| Kelly fraction | gate-progression Kelly: 0.0000, raw Kelly: -0.3664; H1 shadow buckets all show adjusted Kelly `0/+0.000` | `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; `knowledge-base/wiki/learning/h1-hour-bucket-counterfactual-3month-2026-05-03.md` |
