---
strategy: tvsm
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

TVSM の思想は、tick_volume の 3σ 級スパイクを大口注文・成行 sweep の proxy とみなし、スパイク足の実体方向に数分間のマイクロトレンドが続く局面だけを 2 秒後の方向継続確認で取る momentum thesis。コード上も「即エントリーは HFT 領域で遅延負け」と明記し、数秒後に方向が確定した時点で入る設計である。`strategies/micro_scalp/tvsm.py:5`, `strategies/micro_scalp/tvsm.py:6`, `strategies/micro_scalp/tvsm.py:7`, `strategies/micro_scalp/tvsm.py:8`, `strategies/micro_scalp/tvsm.py:12`, `strategies/micro_scalp/tvsm.py:13`, `strategies/micro_scalp/tvsm.py:14`, `strategies/micro_scalp/tvsm.py:15`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対して、trigger は `z_spike = (tick_volume[t-2] - mu) / sigma >= spike_z`、スパイク足の実体方向 `side = BUY if close-open > 0 else SELL`、その後の `move_1` と `move_2` が同方向であることを要求する。これは volume shock + price direction + continuation confirmation なので、momentum 捕捉として整合する。`strategies/micro_scalp/tvsm.py:61`, `strategies/micro_scalp/tvsm.py:72`, `strategies/micro_scalp/tvsm.py:73`, `strategies/micro_scalp/tvsm.py:77`, `strategies/micro_scalp/tvsm.py:81`, `strategies/micro_scalp/tvsm.py:84`, `strategies/micro_scalp/tvsm.py:85`, `strategies/micro_scalp/tvsm.py:86`, `strategies/micro_scalp/tvsm.py:88` |
| 3 (timing window) | OK | 分布は `bars[-(LOOKBACK + 3):-3]` でスパイク候補と現在確認窓を除外し、`spike_bar=bars[-3]`、`conf_bar=bars[-2]`、`latest=bars[-1]` の closed-bar 系で判定する。ATR も `bars[:-1]` で現在バーを除外するため、明示的な look-ahead は見えない。2 秒待ちは遅延負けを避けるための設計上の confirmation であり、現コード単体では LATE 判定までは不要。ただし per-bar dedup は strategy 内 state としては持たないため、呼び出し側が同一確定バーで複数回 `evaluate()` しない前提が残る。`strategies/micro_scalp/tvsm.py:30`, `strategies/micro_scalp/tvsm.py:31`, `strategies/micro_scalp/tvsm.py:32`, `strategies/micro_scalp/tvsm.py:61`, `strategies/micro_scalp/tvsm.py:67`, `strategies/micro_scalp/tvsm.py:68`, `strategies/micro_scalp/tvsm.py:69`, `strategies/micro_scalp/tvsm.py:92`, `strategies/micro_scalp/tvsm.py:116`, `strategies/micro_scalp/tvsm.py:117` |
| 4 (filter coherence) | STRENGTHENS | `sigma <= 0` guard、body 最小幅、2 本連続の同方向確認、ATR がコストに埋もれる局面の停止、R:R 下限はいずれも momentum thesis または execution viability を強化する。重要先行例の MA filter on MR strategy -> BREAKS、HMM regime gate on edge tail -> BREAKS と異なり、現コードに trend/MR の thesis を逆向きに hard reject する filter はない。`strategies/micro_scalp/tvsm.py:64`, `strategies/micro_scalp/tvsm.py:78`, `strategies/micro_scalp/tvsm.py:86`, `strategies/micro_scalp/tvsm.py:88`, `strategies/micro_scalp/tvsm.py:96`, `strategies/micro_scalp/tvsm.py:97`, `strategies/micro_scalp/tvsm.py:98`, `strategies/micro_scalp/tvsm.py:99`, `strategies/micro_scalp/tvsm.py:100`, `strategies/micro_scalp/tvsm.py:101`, `strategies/micro_scalp/tvsm.py:103`, `strategies/micro_scalp/tvsm.py:104`, `strategies/micro_scalp/tvsm.py:105`, `strategies/micro_scalp/tvsm.py:112`, `strategies/micro_scalp/tvsm.py:113` |
| 5 (stop/TP geometry) | ALIGNED | Momentum thesis に対して、SL は `max(1.2 * ATR, 2.0 * entry_slip + 0.5 * ATR)`、TP は `max(tp_atr_mult * ATR, 8 pips)`、かつ `TP/SL >= 1.5` の asymm geometry。デフォルトでは概ね `TP=3.0ATR` vs `SL>=1.2ATR` で、cost-aware buffer も持つため、短期 momentum の伸びを取りに行く構造として整合する。`strategies/micro_scalp/tvsm.py:48`, `strategies/micro_scalp/tvsm.py:98`, `strategies/micro_scalp/tvsm.py:99`, `strategies/micro_scalp/tvsm.py:100`, `strategies/micro_scalp/tvsm.py:101`, `strategies/micro_scalp/tvsm.py:107`, `strategies/micro_scalp/tvsm.py:109`, `strategies/micro_scalp/tvsm.py:110`, `strategies/micro_scalp/tvsm.py:112`, `strategies/micro_scalp/tvsm.py:113` |
| 6 (pair-regime fit) | FORCED | `ALL` 指定に対して、TVSM 本体には pair/session whitelist がない。tick_volume momentum は USDJPY など高流動性・高 tick density の major では FIT 候補だが、低 tick density・高 spread・tick_volume proxy が不安定な pair まで ALL 適用する根拠は現行 evidence では不足。`USDJPY=FIT candidate`, `EURUSD/GBPUSD=FIT candidate pending tick evidence`, `Other ALL=FORCED/UNTESTED`。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 由来の phase0_shadow / ALL 365d BT EV は入力どおり `—`。local audit DB 相当の `demo_trades.db` では `demo_trades.entry_type`、`evaluated_candidates.strategy_name/selected_strategy`、`oanda_audit.entry_type` の exact `tvsm` 行が 0 件。既存 micro-scalp 診断には合成データの PF があるが、実 audit DB / tier-master の Wilson lower、PF、WF folds>=3、Bonferroni-adjusted p、Kelly fraction ではないため、`feedback_partial_quant_trap.md` 基準では採用判断不可。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で Tier 3/4 ではないが、入力 metric は 365d BT EV `—` で、audit DB に exact `tvsm` row もないため under-evidenced shadow cell として failure mode を診断する。破綻軸は Axis 2/3/4/5 ではなく Axis 7。設計上は momentum thesis、2 秒 confirmation、cost-aware SL、R:R gate が整合している一方、`ALL` pair に広げる実証根拠がない。

再設計案は、trigger 自体を大きく変えるより先に pair-regime/timing filter を 1 系統追加すること。具体的には `evaluate()` の前段または caller 側で、major pair whitelist、London/NY open など tick density の高い時間帯、`ATR/spread` または `ATR/entry_slip` の下限を同時に満たす時だけ TVSM を評価し、その限定 universe で 30d/365d 実 tick BT を作る。新規 BT は本 audit では実行しない。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`A`

現行の中核 trigger は維持する。変更候補は trigger 条件そのものではなく、entry universe を「tick_volume shock が観測可能で、retail latency/cost を吸収できる pair-session-regime」に限定する timing/filter redesign である。コードレベルでは `z_spike >= spike_z` と同方向 2-bar confirmation の前に、pair whitelist と session gate、さらに `atr >= k * entry_slip_price` または `ATR/spread >= threshold` を追加する設計が妥当。

そのうえで必要な evidence は、実 OANDA tick 由来の 1 秒足で pair 別・session 別・vol regime 別に N、WR、Wilson lower 95%、PF、WF folds>=3、Bonferroni-adjusted p、Kelly fraction を同一 artifact から出すこと。合成データの positive PF は参考に留め、Shadow 昇格判断には使わない。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: tier-master phase0_shadow/ALL は `—`; local `demo_trades.db` exact `tvsm` rows = 0 | prompt tier-master input; local audit DB search |
| Win rate | INSUFFICIENT_EVIDENCE | prompt tier-master input; local audit DB search |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: exact `tvsm` N/W が既存 audit DB にない | local audit DB search |
| PF | INSUFFICIENT_EVIDENCE: tier-master PF なし。synthetic diagnostic PF は decision-grade source ではない | prompt tier-master input; `knowledge-base/wiki/analyses/micro-scalp-diagnostic-2026-04-17.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: phase0_shadow/ALL の walk-forward folds artifact なし | tier-master / audit DB search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE | tier-master / audit DB search |
| Kelly fraction | INSUFFICIENT_EVIDENCE | tier-master / audit DB search |
