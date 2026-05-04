---
strategy: streak_reversal
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: USD_JPY
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

連続した同方向 candle は短期的な行き過ぎを示し、3 本以上の連続陰線なら BUY、3 本以上の連続陽線なら SELL で平均回帰を取る MR 戦略。コードは bearish/bullish streak を数え、`_stk_bearish >= 3 -> BUY` / `else SELL` と反対方向へ入るため、思想は AMBIGUOUS ではない。`app.py:3201-3260,8707-8745 (INLINE):3206`, `app.py:3201-3260,8707-8745 (INLINE):3214`, `app.py:3201-3260,8707-8745 (INLINE):3223`, `app.py:3201-3260,8707-8745 (INLINE):3226`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `streak=max(consecutive(Close<Open), consecutive(Close>Open)) >= 3` かつ `bearish>=3 -> BUY`, `bullish>=3 -> SELL`。RSI/BB/z-score は使わないが、連続 candle count 自体が extension proxy であり、MR thesis を直接捕捉している。daytrade と scalp は同じ構造。`app.py:3201-3260,8707-8745 (INLINE):3208`, `app.py:3201-3260,8707-8745 (INLINE):3210`, `app.py:3201-3260,8707-8745 (INLINE):3216`, `app.py:3201-3260,8707-8745 (INLINE):3218`, `app.py:3201-3260,8707-8745 (INLINE):3224`, `app.py:3201-3260,8707-8745 (INLINE):8730` |
| 3 (timing window) | LOOKAHEAD | Streak 判定が `df.iloc[-1]` から始まるため、呼び出し側が bar-close 済み dataframe を保証しない限り、未確定 current bar の Open/Close で signal が動く。さらに inline block 内に `bar_time` dedup がなく、同一 bar 内で再評価されると多重 entry の抑止は外部依存になる。`app.py:3201-3260,8707-8745 (INLINE):3208`, `app.py:3201-3260,8707-8745 (INLINE):3209`, `app.py:3201-3260,8707-8745 (INLINE):3216`, `app.py:3201-3260,8707-8745 (INLINE):3217`, `app.py:3201-3260,8707-8745 (INLINE):8713`, `app.py:3201-3260,8707-8745 (INLINE):8720` |
| 4 (filter coherence) | BREAKS | Symbol filter は USD/JPY のみに限定するため STRENGTHENS。`signal == WAIT or signal == _stk_dir` は既存 signal arbitration なので NEUTRAL。ただし daytrade 側 HTF hard block は、HTF bull 中の SELL reversal と HTF bear 中の BUY reversal を拒否し、MR が依存する trend-tail reversal を切る。これは重要先行例の MA filter on MR strategy -> BREAKS、および HMM regime gate same trap と同型の conventional trend gate で、streak MR thesis には BREAKS。scalp 側にはこの HTF block がないため variant 間も不整合。`app.py:3201-3260,8707-8745 (INLINE):3205`, `app.py:3201-3260,8707-8745 (INLINE):3227`, `app.py:3201-3260,8707-8745 (INLINE):3229`, `app.py:3201-3260,8707-8745 (INLINE):3231`, `app.py:3201-3260,8707-8745 (INLINE):3234`, `app.py:3201-3260,8707-8745 (INLINE):8731` |
| 5 (stop/TP geometry) | MISALIGNED | Scalp variant は `SL=0.5ATR`, `TP=1.2ATR` で R:R=2.4。MR は平均へ戻る前の noise で切られない wide stop が望ましいが、0.5ATR stop は streak 後の反転待ちとして狭すぎる。daytrade variant は `calc_sl_tp_v3(...)` に委譲しており、inline block 内に MR 専用 geometry がないため、scalp と daytrade で stop/TP 思想も揃っていない。`app.py:3201-3260,8707-8745 (INLINE):3241`, `app.py:3201-3260,8707-8745 (INLINE):8736`, `app.py:3201-3260,8707-8745 (INLINE):8737` |
| 6 (pair-regime fit) | FIT | USD_JPY は pair_promoted 対象で、既存 BT/WF でも streak_reversal の安定性が最も明確。単一 pair のため per-pair 表は省略可能だが、USD_JPY=FIT。 |
| 7 (empirical evidence) | SUFFICIENT_EVIDENCE | N/WR/EV だけでなく、Wilson lower, PF, WF folds, Bonferroni p, Kelly を既存 tier-master 系 KB / audit DB から確認できる。数値は下表。 |

## Axis 8: failure mode 診断

Tier 1 (LIVE) / pair_promoted のため Tier 3/4 専用の復活診断ではないが、Axis 3/4/5 に live 劣化を起こし得る設計破綻がある。破綻軸は Axis 4 が主、Axis 3 と Axis 5 が副。特に daytrade の HTF hard block は「連続足の行き過ぎを逆張る」思想に trend-following filter を重ねており、既存の Bonferroni-significant tail を削る危険がある。

再設計案は 1 案に絞る。Trigger は維持し、daytrade 側の HTF hard block を hard reject から confidence penalty / reason annotation に落とす。あわせて signal 判定は bar-close 済み candle のみを使うよう `df.iloc[-2]` 起点または呼び出し側の closed-bar dataframe に固定し、`symbol + tf + bar_time + entry_type` の dedup を実行層で必須化する。Stop/TP は scalp variant を `SL=1.0ATR`, `TP=1.0-1.2ATR` 程度の MR geometry variant として shadow 比較する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

最小修正は filter 1 系統。`_stk_htf_blocked` による hard block を削除または `conf = max(25, conf - _stk_bonus)` 相当の soft penalty に変更し、MR の tail event を live routing から消さない。Trigger の `streak >= 3` と USD_JPY pair filter は過去 evidence と整合しているため維持する。

次に timing を bar-close 化する。streak count は現在の `df.iloc[-1]` 起点ではなく、未確定 bar が混じる環境では `df.iloc[-2]` から数える variant を pre-register する。scalp の `0.5ATR / 1.2ATR` は profit-seeking すぎるので、MR 用に `1.0ATR / 1.0-1.2ATR` の stop/TP geometry を別 variant として検証する。新規 BT は本監査では実行しない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 468 | audit DB (`knowledge-base/raw/bt-results/edge-lab-2026-04-23.json`) |
| Win rate | 72.2% (338/468) | audit DB (`knowledge-base/raw/bt-results/edge-lab-2026-04-23.json`) |
| Wilson lo (95%) | 68.0% | audit DB derived from 338/468 |
| PF | 3.07 audit DB; 3.05 WF aggregate; older 365d scan PF=2.72 | audit DB; tier-master-linked WF (`knowledge-base/raw/bt-results/walkforward-2026-04-22.json`); `knowledge-base/raw/bt-results/bt-365d-scan-2026-04-16.md` |
| WF folds (3+) | 18/18 positive on 365d W20 USDJPY; 7/7 positive on scalp 5m 180d | tier-master-linked WF (`knowledge-base/raw/bt-results/walkforward-365d-w20-usdjpy-2026-04-22.json`; `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.json`) |
| Bonferroni-adj p | 1.3e-5 for 5streak BUY USD_JPY; code reason string also records p<0.001 | tier-master strategy note (`knowledge-base/wiki/strategies/streak-reversal.md`); `app.py:3201-3260,8707-8745 (INLINE):3244` |
| Kelly fraction | 0.487 full Kelly, derived from audit DB WR/PF/payoff ratio | audit DB derived from `knowledge-base/raw/bt-results/edge-lab-2026-04-23.json` |
