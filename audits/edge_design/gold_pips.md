---
strategy: gold_pips
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

XAU/USD の短期モメンタムは持続しやすいという前提で、直前 5 本の 1m 足から 5m 相当の方向を作り、その方向に 1m の大きな同色包み足が出た瞬間へ順張りで入る scalp 戦略。ADX と EMA21 は、その包み足が単なる反転足ではなくトレンド方向の加速であることを確認する補助条件。`strategies/scalp/gold_pips.py:2`, `strategies/scalp/gold_pips.py:5`, `strategies/scalp/gold_pips.py:6`, `strategies/scalp/gold_pips.py:7`, `strategies/scalp/gold_pips.py:14`, `strategies/scalp/gold_pips.py:15`, `strategies/scalp/gold_pips.py:16`, `strategies/scalp/gold_pips.py:21`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum thesis に対して、`_5m_close_avg > _5m_open_avg` で UP、`_5m_close_avg <= _5m_open_avg` で DOWN を作り、さらに 5 本中 3 本以上の同方向足を要求する。Entry は `BUY: _5m_dir == "UP" AND _cur_body > 0 AND ctx.entry > ctx.ema21`、`SELL: _5m_dir == "DOWN" AND _cur_body < 0 AND ctx.entry < ctx.ema21`。包み足判定は `_cur_body_abs > _prev_body_abs AND _cur_body_abs >= ATR7*0.3` で、厳密な engulfing open/close 包含ではないが、順張り momentum burst の大陽線/大陰線 trigger としては thesis と整合する。`strategies/scalp/gold_pips.py:35`, `strategies/scalp/gold_pips.py:38`, `strategies/scalp/gold_pips.py:61`, `strategies/scalp/gold_pips.py:68`, `strategies/scalp/gold_pips.py:72`, `strategies/scalp/gold_pips.py:73`, `strategies/scalp/gold_pips.py:74`, `strategies/scalp/gold_pips.py:77`, `strategies/scalp/gold_pips.py:81`, `strategies/scalp/gold_pips.py:85`, `strategies/scalp/gold_pips.py:91`, `strategies/scalp/gold_pips.py:92`, `strategies/scalp/gold_pips.py:109`, `strategies/scalp/gold_pips.py:110`, `strategies/scalp/gold_pips.py:122`, `strategies/scalp/gold_pips.py:123` |
| 3 (timing window) | LOOKAHEAD | 5m 方向は `_last5 = ctx.df.iloc[-6:-1]` で現在足を除外しており良いが、entry trigger と SL 参照は現在足の `ctx.entry`, `ctx.open_price`, `ctx.df.iloc[-1]["High/Low"]` を直接使う。Strategy 内に closed-bar 判定も `(symbol, bar_time)` dedup もないため、実行層が intrabar evaluate すると未確定足の body/high/low で signal が出て、同一 1m bar 内で多重 entry するリスクがある。`strategies/scalp/gold_pips.py:68`, `strategies/scalp/gold_pips.py:85`, `strategies/scalp/gold_pips.py:91`, `strategies/scalp/gold_pips.py:104`, `strategies/scalp/gold_pips.py:105`, `strategies/scalp/gold_pips.py:106`, `strategies/scalp/gold_pips.py:109`, `strategies/scalp/gold_pips.py:110`, `strategies/scalp/gold_pips.py:117`, `strategies/scalp/gold_pips.py:118`, `strategies/scalp/gold_pips.py:122`, `strategies/scalp/gold_pips.py:123`, `strategies/scalp/gold_pips.py:130`, `strategies/scalp/gold_pips.py:131`, `strategies/scalp/gold_pips.py:167` |
| 4 (filter coherence) | STRENGTHENS | XAUUSD 専用 filter は gold volatility thesis と一致する。UTC 0-12 session filter はコメント上 Tokyo PF=1.57、NY overlap/late PF<0.7 を根拠に NY を落としており、tail を消す HMM gate 型ではなく、既知の壊滅 session を避ける filter。ADX>=18、EMA21 方向、ADX bonus、EMA spread、MACD 方向、DI 方向はすべて momentum thesis を強化する。MR 戦略に MA filter を足して破壊する `feedback_ma_filter_breaks_mr.md` 型ではなく、HMM regime gate が同じ edge tail を消す `feedback_hmm_gate_same_trap.md` 型の hard regime gate もない。`strategies/scalp/gold_pips.py:40`, `strategies/scalp/gold_pips.py:41`, `strategies/scalp/gold_pips.py:43`, `strategies/scalp/gold_pips.py:44`, `strategies/scalp/gold_pips.py:45`, `strategies/scalp/gold_pips.py:46`, `strategies/scalp/gold_pips.py:50`, `strategies/scalp/gold_pips.py:51`, `strategies/scalp/gold_pips.py:55`, `strategies/scalp/gold_pips.py:61`, `strategies/scalp/gold_pips.py:109`, `strategies/scalp/gold_pips.py:110`, `strategies/scalp/gold_pips.py:122`, `strategies/scalp/gold_pips.py:123`, `strategies/scalp/gold_pips.py:139`, `strategies/scalp/gold_pips.py:146`, `strategies/scalp/gold_pips.py:152`, `strategies/scalp/gold_pips.py:154`, `strategies/scalp/gold_pips.py:158`, `strategies/scalp/gold_pips.py:161` |
| 5 (stop/TP geometry) | MISALIGNED | TP は固定 `1.8*ATR7`。BUY risk は実質 `max(entry - current_low + 0.2*ATR7, 0.030)`、SELL risk は `max(current_high - entry + 0.2*ATR7, 0.030)` で、R:R は `1.8*ATR7 / risk` の可変値。包み足が大きいほど entry が伸びた後になり、wick が長いと risk が膨らむ一方、TP は 1.8ATR 固定で R floor も trailing もない。Momentum thesis なら少なくとも asymmetric payoff を保証する R:R guard、または continuation を取りに行く trailing/freshness cap が必要。`strategies/scalp/gold_pips.py:21`, `strategies/scalp/gold_pips.py:22`, `strategies/scalp/gold_pips.py:36`, `strategies/scalp/gold_pips.py:37`, `strategies/scalp/gold_pips.py:102`, `strategies/scalp/gold_pips.py:117`, `strategies/scalp/gold_pips.py:118`, `strategies/scalp/gold_pips.py:119`, `strategies/scalp/gold_pips.py:130`, `strategies/scalp/gold_pips.py:131`, `strategies/scalp/gold_pips.py:132` |
| 6 (pair-regime fit) | FORCED | 下の pair table 参照。Audit input は `ALL` だが、実装は XAUUSD のみを許可する。XAU momentum thesis 自体は pair-fit するが、production scope では XAU が除外されており、ALL cell としては forced scope。`strategies/scalp/gold_pips.py:40`, `strategies/scalp/gold_pips.py:41`, `strategies/scalp/gold_pips.py:50`, `strategies/scalp/gold_pips.py:51` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master は `gold_pips_hunter` を Phase0 Shadow Gate に置くが、365d BT EV は入力どおり `—`。repo 内の strategy wiki も performance を TBD とし、`demo_trades.db` の `demo_trades` / `evaluated_candidates` に gold_pips_hunter または XAU rows は存在しない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでも不足で、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は採用判断に使えない。数値は下表に分離する。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| XAUUSD | FIT / production-excluded | Code は XAUUSD のみ許可し、gold volatility と 1m momentum を前提にしているため thesis の pair fit はある。ただし user feedback memory と既存 tooling では XAU は production scope から除外されるため、昇格判断用の FX evidence には使えない。`strategies/scalp/gold_pips.py:12`, `strategies/scalp/gold_pips.py:40`, `strategies/scalp/gold_pips.py:41` |
| ALL non-XAU FX pairs | FORCED | Code 上すべて拒否されるため、`ALL` cell としての pair-regime evidence は存在しない。`strategies/scalp/gold_pips.py:50`, `strategies/scalp/gold_pips.py:51` |

## Axis 8: failure mode 診断

Tier 3/4 ではなく Tier 2 Shadow で、metrics 劣化を判定できる既存数値もない。ただし設計上の破綻候補は Axis 3 と Axis 5 に集中する。Trigger/filter は momentum thesis と概ね整合している一方、現在足の body/high/low を未確定のまま使える構造と per-bar dedup 欠落が、1m XAU の高ボラ局面で signal の多重発火や chase entry を起こしうる。さらに fixed TP=1.8ATR に対し、stop は包み足全体の high/low 依存で R:R が保証されない。

再設計案は、まず signal bar を確定足に固定し、`df.iloc[-2]` で body/engulfing/high/low を計算して次 bar の `ctx.entry` で約定する variant に切ること。加えて `(ctx.symbol, signal, bar_id)` の per-bar dedup を入れ、同一 1m bar では一度しか emit しない。Stop/TP は `risk = abs(entry - sl)` を計算して `tp_distance >= 1.5*risk` を満たさない場合は skip、または TP を `max(1.8ATR, 1.5*risk)` に引き上げる。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は維持する。変更対象は trigger の大枠ではなく、timing と stop/TP geometry。最小 redesign は、包み足判定を未確定の `ctx.entry - ctx.open_price` から確定足ベースへ移し、`signal_bar = ctx.df.iloc[-2]`、`prev_bar = ctx.df.iloc[-3]` で body engulfing と signal high/low を計算する。Execution は次 bar の `ctx.entry` に限定し、同一 `(symbol, signal, signal_bar_time)` の再発火を拒否する。

Geometry 側は、SL を signal bar high/low ± `0.2*ATR7` に置いたあと `risk = abs(entry - sl)` を明示計算し、`1.8*ATR7 / risk < 1.5` なら skip する。XAU の爆発的 momentum を取りに行くなら、固定 TP だけでなく `tp = entry ± max(1.8*ATR7, 1.5*risk)`、または 1.0R 到達後の ATR trailing を別 variant として比較する。新規 BT は本 audit では実行しないが、採用前には XAU 専用に 365d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly を同一集計で再確認する必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: `demo_trades.db` の `demo_trades` / `evaluated_candidates` に `gold_pips_hunter` または XAU rows なし | audit DB |
| Win rate | INSUFFICIENT_EVIDENCE | audit DB |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N=0/未確認のため算出不可 | audit DB |
| PF | INSUFFICIENT_EVIDENCE: tier-master 365d BT EV/PF は `—` | tier-master |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: gold_pips_hunter の WF folds>=3 は既存資料から確認不可 | tier-master |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: gold_pips_hunter の補正済み p は既存資料から確認不可 | tier-master |
| Kelly fraction | INSUFFICIENT_EVIDENCE: PF/WR/avg win-loss または closed trade rows がないため算出不可 | tier-master / audit DB |
