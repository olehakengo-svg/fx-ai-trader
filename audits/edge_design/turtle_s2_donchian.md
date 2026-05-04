---
strategy: turtle_s2_donchian
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

USDJPY long-only の D1 55-day Donchian 上抜けで長期 breakout / trend-following の初動に入り、20-day ATR を N とする 2N stop、+0.5N pyramiding、20-day low exit で大きなトレンド継続を取りに行く Turtle System 2 thesis。現行コードの thesis は MR ではなく、prior high breakout と anti-Martingale pyramid による momentum / breakout continuation である。`strategies/daytrade/turtle_s2_donchian.py:2`, `strategies/daytrade/turtle_s2_donchian.py:6`, `strategies/daytrade/turtle_s2_donchian.py:23`, `strategies/daytrade/turtle_s2_donchian.py:24`, `strategies/daytrade/turtle_s2_donchian.py:26`, `strategies/daytrade/turtle_s2_donchian.py:27`, `strategies/daytrade/turtle_s2_donchian.py:30`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / breakout thesis に対し、entry は `last_close > prior55High`。Donchian high は `shift(1).rolling(55).max()` なので current bar を除外した prior 55-day high breakout を直接捕捉している。MR thesis 用の RSI/BB/z-score は不要で、条件式は `Close[-1] > max(Close[-56:-1])`。`strategies/daytrade/turtle_s2_donchian.py:129`, `strategies/daytrade/turtle_s2_donchian.py:130`, `strategies/daytrade/turtle_s2_donchian.py:131`, `strategies/daytrade/turtle_s2_donchian.py:185`, `strategies/daytrade/turtle_s2_donchian.py:186`, `strategies/daytrade/turtle_s2_donchian.py:197`, `strategies/daytrade/turtle_s2_donchian.py:198` |
| 3 (timing window) | OK | D1 close evaluation が仕様化され、Donchian は `shift(1)` で current bar を prior high 計算から除外するため look-ahead は検出しない。`entry` は strategy struct 上 `close at entry (BT) / next-open (live)` と明記され、signal bar は `bar_time=last_idx` として渡される。strategy file 単体は stateless なので同じ D1 dataframe を複数回評価すれば同じ signal を返せるが、current bar の高値安値を prior channel に混入させる look-ahead ではない。`strategies/daytrade/turtle_s2_donchian.py:23`, `strategies/daytrade/turtle_s2_donchian.py:24`, `strategies/daytrade/turtle_s2_donchian.py:25`, `strategies/daytrade/turtle_s2_donchian.py:90`, `strategies/daytrade/turtle_s2_donchian.py:98`, `strategies/daytrade/turtle_s2_donchian.py:160`, `strategies/daytrade/turtle_s2_donchian.py:189`, `strategies/daytrade/turtle_s2_donchian.py:213`, `strategies/daytrade/turtle_s2_donchian.py:240` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | `SUPPORTED_PAIRS={"USD_JPY"}` と long-only policy は Wave 1 reject cell を切る pair/direction filter で STRENGTHENS。BoJ intervention guards は USDJPY 158以上で size half、160以上で entry block、intervention day ±1 を skip する tail-risk filter で、breakout thesis の通常局面を壊さず risk を削るため STRENGTHENS。`pd.isna` / `atr_n <= 0` / required columns は data quality guard で NEUTRAL。MA filter は明示的に無く、重要先行例の MA filter on MR strategy -> BREAKS や HMM regime gate same trap 型の thesis 破壊 filter はこの file には無い。`strategies/daytrade/turtle_s2_donchian.py:18`, `strategies/daytrade/turtle_s2_donchian.py:31`, `strategies/daytrade/turtle_s2_donchian.py:32`, `strategies/daytrade/turtle_s2_donchian.py:36`, `strategies/daytrade/turtle_s2_donchian.py:37`, `strategies/daytrade/turtle_s2_donchian.py:76`, `strategies/daytrade/turtle_s2_donchian.py:177`, `strategies/daytrade/turtle_s2_donchian.py:194`, `strategies/daytrade/turtle_s2_donchian.py:202`, `strategies/daytrade/turtle_s2_donchian.py:205`, `strategies/daytrade/turtle_s2_donchian.py:209` |
| 5 (stop/TP geometry) | ALIGNED | Initial stop は `entry - 2N`、pyramid は +0.5N favorable move ごとに最大 4 units、exit は prior 20-day low。soft TP は `entry + 20N` で nominal R:R は `20N / 2N = 10R` だが、実際の closure は TP 固定ではなく 20-day low exit による channel/trailing 型。breakout / trend-following thesis の「損は 2N で限定し、伸びる tail を exit channel まで持つ」幾何と整合する。`strategies/daytrade/turtle_s2_donchian.py:26`, `strategies/daytrade/turtle_s2_donchian.py:27`, `strategies/daytrade/turtle_s2_donchian.py:28`, `strategies/daytrade/turtle_s2_donchian.py:30`, `strategies/daytrade/turtle_s2_donchian.py:71`, `strategies/daytrade/turtle_s2_donchian.py:72`, `strategies/daytrade/turtle_s2_donchian.py:214`, `strategies/daytrade/turtle_s2_donchian.py:215`, `strategies/daytrade/turtle_s2_donchian.py:218`, `strategies/daytrade/turtle_s2_donchian.py:247`, `strategies/daytrade/turtle_s2_donchian.py:258`, `strategies/daytrade/turtle_s2_donchian.py:261` |
| 6 (pair-regime fit) | FIT / FORCED | 下の Pair-Regime Table 参照。実装済み deployable cell は USDJPY long-only なので FIT。入力 scope の `ALL` を文字通り全 pair 展開と解釈すると FORCED だが、コードは非 USDJPY を即 `None` にしており、実運用 universe は ALL ではなく USDJPY long に固定されている。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / B-marginal positive | Wave 1 BT 由来の USDJPY long は N=50, WR=32.0%, Wilson 95% lo=0.208, PF=1.99, OOS PF=1.99, Kelly=+0.16, Bonferroni p=0.172 で positive。ただし local audit DB の `turtle_s2%` / `%turtle%` rows は `demo_trades`, `oanda_audit`, `evaluated_candidates` すべて 0 件で live shadow evidence が無く、WF folds>=3 は既存文書でも未充足。tier-master 入力の 365d BT EV も `—` のため、`feedback_partial_quant_trap.md` 基準では live promote-grade evidence は不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY long | FIT | Code whitelist は `USD_JPY` のみで、docstring は USDJPY long-only を唯一の deployable cell とする。`strategies/daytrade/turtle_s2_donchian.py:2`, `strategies/daytrade/turtle_s2_donchian.py:8`, `strategies/daytrade/turtle_s2_donchian.py:18`, `strategies/daytrade/turtle_s2_donchian.py:76`, `strategies/daytrade/turtle_s2_donchian.py:177` |
| USDJPY short | FORCED / BLOCKED | SELL side は deploy しない方針で、`evaluate_d1()` は BUY signal しか返さない。`strategies/daytrade/turtle_s2_donchian.py:18`, `strategies/daytrade/turtle_s2_donchian.py:90`, `strategies/daytrade/turtle_s2_donchian.py:177`, `strategies/daytrade/turtle_s2_donchian.py:232` |
| Non-USDJPY pairs | FORCED / BLOCKED | `pair not in SUPPORTED_PAIRS` は即 `None`。入力 `pairs: ALL` ではなく、実装上は rejected cells として扱うべき。`strategies/daytrade/turtle_s2_donchian.py:76`, `strategies/daytrade/turtle_s2_donchian.py:166`, `strategies/daytrade/turtle_s2_donchian.py:177`, `strategies/daytrade/turtle_s2_donchian.py:178` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) であり Tier 3/4 ではないが、phase0_shadow かつ live audit DB が N=0、WF folds>=3 が未充足なので昇格前 failure mode として診断する。破綻軸は Axis 2/4/5 ではない。trigger は prior 55-day high breakout を直接捕捉し、filter は pair/direction と BoJ tail-risk guard に限定され、stop/exit は Turtle breakout の convex payoff と整合している。

実務上の failure mode は Axis 6/7 と軽微な Axis 3 hardening。`pairs: ALL` として inventory されている一方、実装は USDJPY long-only なので、監査・tier-master 上の cell scope を USDJPY long に明示する必要がある。また live shadow evidence はまだ 0 件で、既存 BT も WF folds>=3 が不足している。再設計案は trigger/filter/stop を変更せず、(1) audit inventory を USDJPY long-only に修正、(2) D1 runner または strategy wrapper で `(pair, entry_type, bar_time)` idempotence を明示、(3) 既存 pipeline で 3+ WF folds と combined BT+shadow Wilson/PF/Kelly/Bonferroni を発行すること。本 audit では新規 BT は実行しない。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`C`

コード上の thesis / trigger / filter / stop geometry は現時点で壊れていないため、条件式をいじる再設計は推奨しない。特に 55-day breakout、2N stop、20-day low exit、+0.5N pyramiding は一体で Turtle System 2 の convex payoff を作っているので、RSI/EMA/HMM のような汎用 filter を追加すると、重要先行例と同様に tail を切る危険がある。

必要なのは redesign というより昇格前の検証設計の補完である。具体的には `pairs: ALL` を USDJPY long-only cell として明示し、runner 側で同一 `bar_time` の unit-1 再 emit を禁止する idempotence guard を置く。そのうえで既存 audit pipeline から 3+ WF folds、live shadow N、combined Wilson lower、PF、Bonferroni p、Kelly を同一 source で出す。これらが揃うまで live promote せず、既存 trigger/filter/stop は凍結する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | audit DB live/shadow rows: 0; Wave 1 BT reference: 50 | audit DB: `demo_trades.db` read-only query; `knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md`; `strategies/daytrade/turtle_s2_donchian.py:8` |
| Win rate | audit DB: INSUFFICIENT_EVIDENCE (N=0); Wave 1 BT reference: 32.0% | audit DB: `demo_trades.db`; `knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md` |
| Wilson lo (95%) | audit DB: INSUFFICIENT_EVIDENCE (N=0); Wave 1 BT reference: 0.208 (docstring rounds to +0.21) | audit DB: `demo_trades.db`; `knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md`; `strategies/daytrade/turtle_s2_donchian.py:9` |
| PF | tier-master input 365d BT EV: `—`; Wave 1 BT reference PF=1.99, OOS PF=1.99 | provided tier-master input; `knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md`; `strategies/daytrade/turtle_s2_donchian.py:8` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: existing note says 2-fold only / 3+ folds required | `knowledge-base/wiki/learning/s2-turtle-verdict-pre-registration-2026-05-03.md` |
| Bonferroni-adj p | Wave 1 BT reference: 0.172 (K=2); live promote gate requires <0.10 | `knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md`; `knowledge-base/wiki/analyses/pre-registration-s2-turtle-usdjpy-long-2026-05-03.md`; `strategies/daytrade/turtle_s2_donchian.py:9`, `strategies/daytrade/turtle_s2_donchian.py:223` |
| Kelly fraction | audit DB: INSUFFICIENT_EVIDENCE (N=0); Wave 1 BT reference: +0.16 | audit DB: `demo_trades.db`; `knowledge-base/wiki/strategies/turtle-s2-donchian-d1.md` |
