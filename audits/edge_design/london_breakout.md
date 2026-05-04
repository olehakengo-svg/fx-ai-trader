---
strategy: london_breakout
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

ロンドン開始時間帯に、直近のアジア時間レンジを上抜け/下抜けし、短期EMA方向も同じなら、その方向へセッション参加による momentum continuation が発生するという breakout / TF thesis。コードは London window、Asia range、range breakout、EMA順列を明示している。`strategies/scalp/london_breakout.py:1`, `strategies/scalp/london_breakout.py:12`, `strategies/scalp/london_breakout.py:14`, `strategies/scalp/london_breakout.py:35`, `strategies/scalp/london_breakout.py:45`, `strategies/scalp/london_breakout.py:52`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Breakout thesis 自体には `BUY: entry > asia_high + 0.1ATR ∧ EMA9 > EMA21` / `SELL: entry < asia_low - 0.1ATR ∧ EMA9 < EMA21` があり方向条件は合う。ただし、`asia_high/asia_low` は実Asiaセッション固定窓ではなく `ctx.df.iloc[-120:]` の rolling 直近2時間から作られるため、7-10 UTC の後半では「Asia range breakout」ではなく London 中の直近レンジ breakout になる。`strategies/scalp/london_breakout.py:12`, `strategies/scalp/london_breakout.py:13`, `strategies/scalp/london_breakout.py:14`, `strategies/scalp/london_breakout.py:36`, `strategies/scalp/london_breakout.py:37`, `strategies/scalp/london_breakout.py:38`, `strategies/scalp/london_breakout.py:45`, `strategies/scalp/london_breakout.py:52` |
| 3 (timing window) | LOOKAHEAD | `ctx.df.iloc[-self.asia_bars:]` と `ctx.df.iloc[-1]["Volume"]` を使いながら `ctx.entry` で即時判定しており、strategy 内では「確定済みbarだけをrange/volumeに使う」契約が明示されていない。さらに strategy 内に signal bar dedup state がないため、同一barで evaluate が複数回呼ばれる実行層では多重entry risk が残る。`strategies/scalp/london_breakout.py:23`, `strategies/scalp/london_breakout.py:36`, `strategies/scalp/london_breakout.py:45`, `strategies/scalp/london_breakout.py:52`, `strategies/scalp/london_breakout.py:68`, `strategies/scalp/london_breakout.py:75` |
| 4 (filter coherence) | STRENGTHENS | Time gate は London open thesis を支えるが、`hour_end=10` まで許すため後半は Axis 2 の rolling-range 問題を増幅する。Asia range min/max は小さすぎる/大きすぎるレンジを除外し、EMA9/EMA21 は breakout 方向の短期trend確認、ADX/Volume は hard gate ではなく score bonus なので MR の MA filter や HMM same-trap のような thesis tail 破壊ではない。`strategies/scalp/london_breakout.py:12`, `strategies/scalp/london_breakout.py:13`, `strategies/scalp/london_breakout.py:15`, `strategies/scalp/london_breakout.py:16`, `strategies/scalp/london_breakout.py:41`, `strategies/scalp/london_breakout.py:45`, `strategies/scalp/london_breakout.py:52`, `strategies/scalp/london_breakout.py:63`, `strategies/scalp/london_breakout.py:70` |
| 5 (stop/TP geometry) | MISALIGNED | BUY は `tp = entry + max(asia_range*1.5, ATR*2.0)`、`sl = asia_high - 0.3ATR`、SELL は対称で、初期R:Rは悪くない。しかし breakout thesis の期待は session expansion の継続取得であり、実装は fixed TP/SL のみで trailing / time exit / break-even 管理が Candidate に渡らない。`strategies/scalp/london_breakout.py:18`, `strategies/scalp/london_breakout.py:19`, `strategies/scalp/london_breakout.py:20`, `strategies/scalp/london_breakout.py:50`, `strategies/scalp/london_breakout.py:51`, `strategies/scalp/london_breakout.py:57`, `strategies/scalp/london_breakout.py:58`, `strategies/scalp/london_breakout.py:75` |
| 6 (pair-regime fit) | FORCED | Code は pair filter を持たず `pairs: ALL` として配信される。London open breakout は GBP/JPY など London liquidity expansion の大きい pair には自然だが、全pair一律は spread/session/liquidity 特性を無視する。下の Pair-Regime Table 参照。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の phase0_shadow 入力は 365d BT EV が `—`。既存 C-1 London Breakout 12yr artifact には GBP_JPY M5 の Wilson/PF/Bonferroni/Kelly があるが、これは exact `london_breakout` ALL cell ではなく関連 pre-reg variant なので、decision-grade evidence は不足。数値は下表。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| GBP_JPY | FIT / weak-evidence | 関連 C-1 artifact では primary cell が N=673, PF=1.01441, Wilson lo=42.18%, Kelly=0.006522 で REJECT。思想の pair fit はあるが、現仕様の採用根拠には弱い。 |
| GBP_USD | FIT / unproven | London liquidity expansion の対象としては自然。ただし exact cell の tier-master/audit DB 数値がない。 |
| EUR_USD | FIT / unproven | London liquidity は厚いが、実装が ALL 配信のため pair-specific range/spread fit が未検証。 |
| USD_JPY | FORCED | London open の主導pairではなく、Tokyo/London overlap の性質が異なる。exact cell の証拠なし。 |
| Other ALL pairs | FORCED | Code に pair/session/spread gating がなく、全pair一律適用は forced。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、tier-master の 365d BT EV が `—` で昇格根拠がなく、関連 C-1 GBP_JPY 12yr primary も Wilson lo/PF/Bonferroni/Sharpe が不合格なので failure mode 診断を適用する。破綻軸は Axis 2、Axis 3、Axis 5。思想は「London open における Asia range breakout」で明確だが、現コードは Asia session 固定窓ではなく rolling 120 bars を使い、確定bar/entry timing/dedup の契約も strategy 内にない。さらに fixed TP/SL のみで breakout continuation を伸ばす exit geometry になっていない。

再設計案は、まず trigger/timing を同時に閉じること。`asia_high/asia_low` は `00:00-06:59 UTC` などの prior session fixed window から確定済みbarだけで計算し、entry は `last_closed_close > asia_high + buffer` / `< asia_low - buffer` の bar-close trigger にする。`buffer = max(0.1ATR, spread)` とし、同一 pair/date/session で1回だけ発火する dedup key を実行層または strategy state に置く。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

Trigger は rolling range から fixed Asia session range へ変える。コードレベルでは `ctx.df.iloc[-self.asia_bars:]` をやめ、UTC timestamp index から London 当日の `00:00 <= t < 07:00` または broker定義の Asia window を切り出す。判定は current/intrabar `ctx.entry` ではなく、確定済み signal bar の close が `asia_high + buffer` / `asia_low - buffer` を超えた時だけに寄せる。

Filter は EMA9/EMA21 と range min/max を維持してよいが、ADX/Volume は当面 score bonus のままにする。Stop/TP は初期SLを broken range 内側へ戻す現設計を維持しつつ、TPを fixed range target だけにせず、`1R` 到達後の break-even と ATR trailing、または 12:00 UTC time stop を別variantで検証する。採用前には exact ALL ではなく pair別、少なくとも GBP_JPY/GBP_USD/EUR_USD 別に Wilson lower / PF / WF folds>=3 / Bonferroni p / Kelly を同一 artifact で再発行する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | exact phase0_shadow ALL: INSUFFICIENT_EVIDENCE; related C-1 GBP_JPY M5 primary: 673 | prompt tier-master input; `knowledge-base/raw/bt-results/c1-london-breakout.json` |
| Win rate | exact phase0_shadow ALL: INSUFFICIENT_EVIDENCE; related C-1 primary: 45.913819% | `knowledge-base/raw/bt-results/c1-london-breakout.json` |
| Wilson lo (95%) | exact phase0_shadow ALL: INSUFFICIENT_EVIDENCE; related C-1 primary: 42.182653% | `knowledge-base/raw/bt-results/c1-london-breakout.json` |
| PF | exact phase0_shadow ALL: INSUFFICIENT_EVIDENCE; related C-1 primary: 1.01441 | `knowledge-base/raw/bt-results/c1-london-breakout.json`; tier-master EV input is `—` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE for exact cell; related C-1 has OOS/IS PF ratio 0.875574 but no WF folds>=3 decision table | `knowledge-base/raw/bt-results/c1-london-breakout.json` |
| Bonferroni-adj p | exact phase0_shadow ALL: INSUFFICIENT_EVIDENCE; related C-1 primary: 1.0, Bonferroni pass=False | `knowledge-base/raw/bt-results/c1-london-breakout.json` |
| Kelly fraction | exact phase0_shadow ALL: INSUFFICIENT_EVIDENCE; related C-1 primary: 0.006522 | `knowledge-base/raw/bt-results/c1-london-breakout.json` |
