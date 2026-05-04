---
strategy: london_session_breakout
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

アジア時間 00-07 UTC のレンジ蓄積後、ロンドン最初の時間帯にレンジ高安を実体のある足でブレイクすると、セッション流動性遷移により同方向へ continuation するという 1H session breakout thesis。コードは Asia range 計測、London open breakout、body quality、MTF EMA confirmation、ATR target を明示している。`strategies/daytrade/london_session_breakout.py:2`, `strategies/daytrade/london_session_breakout.py:16`, `strategies/daytrade/london_session_breakout.py:17`, `strategies/daytrade/london_session_breakout.py:18`, `strategies/daytrade/london_session_breakout.py:19`, `strategies/daytrade/london_session_breakout.py:21`, `strategies/daytrade/london_session_breakout.py:22`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | MISMATCH | Active implementation は `evaluate()` 冒頭で常に `return None` なので、thesis を捕捉する entry condition が実行されない。到達不能な dormant branch には `BUY: entry > asia_high ∧ body_ratio >= 0.40 ∧ close > open ∧ EMA9 > EMA21 ∧ HTF != bear` / `SELL: entry < asia_low ∧ body_ratio >= 0.40 ∧ close < open ∧ EMA9 < EMA21 ∧ HTF != bull` があり、breakout thesis との方向整合はあるが、現行コードの数学的 trigger は実質 `False`。`strategies/daytrade/london_session_breakout.py:56`, `strategies/daytrade/london_session_breakout.py:57`, `strategies/daytrade/london_session_breakout.py:60`, `strategies/daytrade/london_session_breakout.py:148`, `strategies/daytrade/london_session_breakout.py:149`, `strategies/daytrade/london_session_breakout.py:150`, `strategies/daytrade/london_session_breakout.py:156`, `strategies/daytrade/london_session_breakout.py:159`, `strategies/daytrade/london_session_breakout.py:171`, `strategies/daytrade/london_session_breakout.py:172`, `strategies/daytrade/london_session_breakout.py:173`, `strategies/daytrade/london_session_breakout.py:177`, `strategies/daytrade/london_session_breakout.py:179` |
| 3 (timing window) | LOOKAHEAD | Active path は signal を出さないため execution latency は発生しないが、dormant branch は `ctx.entry` と `ctx.open_price` で signal bar の実体を測り、同じ `ctx.entry` で即 entry する設計に見える。さらに entry window は 07-09 UTC まで許す一方で、thesis は 07:00-08:00 の最初の1H足 breakout であり、session/day/bar dedup state がないため、同一 London breakout 後に複数 bar で再発火するリスクが残る。`strategies/daytrade/london_session_breakout.py:18`, `strategies/daytrade/london_session_breakout.py:40`, `strategies/daytrade/london_session_breakout.py:41`, `strategies/daytrade/london_session_breakout.py:68`, `strategies/daytrade/london_session_breakout.py:129`, `strategies/daytrade/london_session_breakout.py:132`, `strategies/daytrade/london_session_breakout.py:148`, `strategies/daytrade/london_session_breakout.py:171`, `strategies/daytrade/london_session_breakout.py:221` |
| 4 (filter coherence) | BREAKS | 現行の最強 filter は `return None` の hard disable で、thesis を完全に破壊している。dormant branch 内では、JPY 除外は「USD/JPY は Tokyo session 活発で Asia compression 不成立」というコード内根拠と整合し、Asia range median gate、body ratio、EMA9/21、HTF agreement、ADX bonus は breakout continuation を強化する。ただし active path の hard disable が支配的で、MA filter on MR や HMM same-trap 以前に entry universe 全体を遮断している。`strategies/daytrade/london_session_breakout.py:57`, `strategies/daytrade/london_session_breakout.py:58`, `strategies/daytrade/london_session_breakout.py:59`, `strategies/daytrade/london_session_breakout.py:60`, `strategies/daytrade/london_session_breakout.py:62`, `strategies/daytrade/london_session_breakout.py:63`, `strategies/daytrade/london_session_breakout.py:64`, `strategies/daytrade/london_session_breakout.py:120`, `strategies/daytrade/london_session_breakout.py:149`, `strategies/daytrade/london_session_breakout.py:156`, `strategies/daytrade/london_session_breakout.py:159`, `strategies/daytrade/london_session_breakout.py:177`, `strategies/daytrade/london_session_breakout.py:179`, `strategies/daytrade/london_session_breakout.py:195` |
| 5 (stop/TP geometry) | MISALIGNED | Dormant branch の TP は fixed `ATR * 2.5`、SL は反対側 Asia range 端に `ATR * 0.3` buffer。BUY の概算は `reward = 2.5ATR`, `risk = entry - asia_low + 0.3ATR`、SELL は対称で、Asia range が広いほど R:R が圧迫される。breakout thesis なら trailing / BE / session time exit が自然だが、`be_trigger_pct` と `max_hold_bars` は class attr にあるだけで `Candidate` へ渡されず、実装上の exit geometry は fixed TP/SL に留まる。`strategies/daytrade/london_session_breakout.py:49`, `strategies/daytrade/london_session_breakout.py:50`, `strategies/daytrade/london_session_breakout.py:51`, `strategies/daytrade/london_session_breakout.py:54`, `strategies/daytrade/london_session_breakout.py:164`, `strategies/daytrade/london_session_breakout.py:165`, `strategies/daytrade/london_session_breakout.py:184`, `strategies/daytrade/london_session_breakout.py:185`, `strategies/daytrade/london_session_breakout.py:221` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。コード内の定量根拠は EUR/USD 90日 1H に限られ、dormant branch は JPY を除外する意図を持つ。一方、input cell は ALL で、非JPY各 pair への pair-specific evidence はない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 入力の 365d BT EV は `—`。local audit DB / BT sqlite / demo DB に `london_session_breakout` の既存行は見つからず、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は decision-grade に埋められない。コードコメントには context fix 後の EUR WR=10% EV=-9.9、JPY WR=0% EV=-10.7 があるが、`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可で、かつ audit DB / tier-master の正式統計ではない。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| EUR_USD | FIT / INSUFFICIENT_EVIDENCE | コード内の唯一の定量裏付けは EUR/USD 90日 1H で、London session breakout thesis 自体の対象としては自然。ただし tier-master / audit DB に Wilson/PF/WF/Kelly がない。 |
| USD_JPY | FORCED | dormant code は `ctx.is_jpy` を除外し、コメントで Tokyo session 活発により Asia compression 不成立、Tokyo→London follow-through 48.1% としている。 |
| EUR_JPY | FORCED | JPY cross として dormant JPY gate により除外対象。pair-specific decision-grade metrics なし。 |
| GBP_JPY | FORCED | JPY cross として dormant JPY gate により除外対象。pair-specific decision-grade metrics なし。 |
| GBP_USD | FORCED / UNTESTED | London liquidity expansion の候補にはなりうるが、コード内・tier-master・audit DB に pair-specific evidence がない。 |
| Other ALL pairs | FORCED / UNTESTED | ALL 配信を正当化する pair-specific session/liquidity/spread evidence がない。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、phase0_shadow かつ 365d BT EV `—` の under-evidenced cell なので failure mode を診断する。破綻軸は Axis 2、Axis 3、Axis 4、Axis 5。思想はコードから明確に導けるが、active path は hard disable により trigger/filter が全停止している。さらに停止理由コメント自体が、context fix 後の EUR WR=10% / JPY WR=0% として既存ロジックの実BT不良を示しているため、単純に `return None` を外すだけでは Shadow 復帰候補にできない。`strategies/daytrade/london_session_breakout.py:57`, `strategies/daytrade/london_session_breakout.py:58`, `strategies/daytrade/london_session_breakout.py:59`, `strategies/daytrade/london_session_breakout.py:60`

再設計案は、まず active disable を維持したまま dormant branch を v2 として分離し、EUR_USD / GBP_USD など非JPY London liquidity pair に限定して trigger/timing/exit を作り直すこと。Trigger は `07:00-08:00 UTC` の確定済み breakout bar close のみを採用し、`close > asia_high + max(spread, 0.1ATR)` / `close < asia_low - max(spread, 0.1ATR)`、body ratio、EMA9/21、HTF direction を条件にする。Timing は `(pair, trade_date, direction)` の dedup を置き、07-09 の後追い再発火を禁止する。

Stop/TP は fixed `ATR*2.5` 単体ではなく、初期SLを Asia range 反対端または breakout invalidation level に置いたうえで、1R 到達後 BE、以後 `ATR trailing` または London close time stop を持つ breakout geometry にする。採用前には新規 BT が必要だが、本監査では実行しないため、必要 BT は pair別 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact で出す内容に限定する。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は明確で、session breakout として再設計余地はある。ただし破綻は一箇所ではなく、active hard disable、bar-close/dedup、pair gating、exit geometry が同時に絡んでいるため、S/A ではなく B とする。

コードレベルの想定は、現行 `london_session_breakout` をそのまま再有効化せず、v2 branch で `return None` 直下の dormant code を再構成する。対象 pair は少なくとも JPY を除外し、EUR_USD / GBP_USD などに分けて検証する。Asia range は当日 00:00-06:59 UTC の確定済み bars から固定計算し、entry は 07:00-08:00 breakout bar close 後の次 execution に寄せる。

Filter は body ratio と EMA/HTF direction を維持候補にし、Asia range median gate は「広すぎるレンジ」を避ける上限も追加する。Exit は `TP=ATR*2.5` fixed のみをやめ、1R BE、ATR trailing、London session time stop を Candidate/実行層が扱える形で設計する。再設計後に必要な証拠は、N/WR/EV ではなく Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction の揃った pair別 audit DB artifact である。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: tier-master 365d BT EV は `—`; local sqlite / demo DB に exact strategy 行なし | audit DB search; prompt tier-master input |
| Win rate | INSUFFICIENT_EVIDENCE: official audit DB / tier-master 値なし。コードコメントには EUR WR=10%, JPY WR=0% があるが N 不明で decision-grade 不可 | `strategies/daytrade/london_session_breakout.py:58`; audit DB search |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N/WR sample が audit DB / tier-master にないため算出不可 | audit DB search; prompt tier-master input |
| PF | INSUFFICIENT_EVIDENCE: tier-master に PF なし、exact strategy row なし | `knowledge-base/wiki/tier-master.md`; audit DB search |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: WF folds>=3 の既存 artifact なし | audit DB search; tier-master search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: multiple-test adjusted p の既存 artifact なし | audit DB search; tier-master search |
| Kelly fraction | INSUFFICIENT_EVIDENCE: PF/payoff/WR sample がなく算出不可 | audit DB search; prompt tier-master input |
