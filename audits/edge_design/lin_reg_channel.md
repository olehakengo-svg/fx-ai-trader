---
strategy: lin_reg_channel
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

高 R2 の線形回帰チャネルで明確な傾きがある相場だけを対象に、上昇チャネルでは下限側の反発を BUY、下降チャネルでは上限側の反落を SELL し、回帰線中央への mean reversion を取る thesis。Breakout mode はコード上 disabled なので、実運用 thesis は trend-channel pullback MR に限定される。`strategies/daytrade/lin_reg_channel.py:20`, `strategies/daytrade/lin_reg_channel.py:21`, `strategies/daytrade/lin_reg_channel.py:22`, `strategies/daytrade/lin_reg_channel.py:23`, `strategies/daytrade/lin_reg_channel.py:24`, `strategies/daytrade/lin_reg_channel.py:25`, `strategies/daytrade/lin_reg_channel.py:26`, `strategies/daytrade/lin_reg_channel.py:65`, `strategies/daytrade/lin_reg_channel.py:71`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対して、BUY は `beta > 0 ∧ entry <= lower + 0.25*(upper-lower) ∧ entry > open_price ∧ entry > lower`、SELL は `beta < 0 ∧ entry >= upper - 0.25*(upper-lower) ∧ entry < open_price ∧ entry < upper`。チャネル端への extension とチャネル内復帰の反転バーを捕捉しており、MR trigger としては整合する。ただし docstring の「lower/upper band にタッチ」より実装は下位/上位 25% zone で緩い。`strategies/daytrade/lin_reg_channel.py:64`, `strategies/daytrade/lin_reg_channel.py:66`, `strategies/daytrade/lin_reg_channel.py:179`, `strategies/daytrade/lin_reg_channel.py:180`, `strategies/daytrade/lin_reg_channel.py:187`, `strategies/daytrade/lin_reg_channel.py:189`, `strategies/daytrade/lin_reg_channel.py:190`, `strategies/daytrade/lin_reg_channel.py:191`, `strategies/daytrade/lin_reg_channel.py:202`, `strategies/daytrade/lin_reg_channel.py:203`, `strategies/daytrade/lin_reg_channel.py:204` |
| 3 (timing window) | LOOKAHEAD | Channel 計算は `ctx.df["Close"].iloc[-self.LR_PERIOD:]` を使い、entry/reversal 判定も `ctx.entry` と `ctx.open_price` の同一評価足に依存する。strategy 内に closed-bar snapshot、signal bar time、per-bar dedup key がなく、live 側で未確定足から呼ばれると intrabar contamination と同一 bar 多重 entry のリスクが残る。`strategies/daytrade/lin_reg_channel.py:147`, `strategies/daytrade/lin_reg_channel.py:148`, `strategies/daytrade/lin_reg_channel.py:189`, `strategies/daytrade/lin_reg_channel.py:191`, `strategies/daytrade/lin_reg_channel.py:203`, `strategies/daytrade/lin_reg_channel.py:204`, `strategies/daytrade/lin_reg_channel.py:304`, `strategies/daytrade/lin_reg_channel.py:305`, `strategies/daytrade/lin_reg_channel.py:306` |
| 4 (filter coherence) | STRENGTHENS / NEUTRAL | `r2 >= 0.60` は channel quality filter、`abs(beta)/ATR >= 0.02` は trend-channel 存在 filter で thesis を強化する。HTF agreement gate は BUY で bear を、SELL で bull を除外するだけなので trend-channel MR には概ね STRENGTHENS。EMA は hard filter ではなく score bonus のみで NEUTRAL。重要先行例の MA filter on pure MR や HMM regime hard gate の BREAKS 型とは異なり、tail を直接削る hard regime gate はない。`strategies/daytrade/lin_reg_channel.py:61`, `strategies/daytrade/lin_reg_channel.py:62`, `strategies/daytrade/lin_reg_channel.py:154`, `strategies/daytrade/lin_reg_channel.py:155`, `strategies/daytrade/lin_reg_channel.py:158`, `strategies/daytrade/lin_reg_channel.py:159`, `strategies/daytrade/lin_reg_channel.py:160`, `strategies/daytrade/lin_reg_channel.py:170`, `strategies/daytrade/lin_reg_channel.py:171`, `strategies/daytrade/lin_reg_channel.py:192`, `strategies/daytrade/lin_reg_channel.py:205`, `strategies/daytrade/lin_reg_channel.py:292`, `strategies/daytrade/lin_reg_channel.py:293`, `strategies/daytrade/lin_reg_channel.py:294`, `strategies/daytrade/lin_reg_channel.py:295` |
| 5 (stop/TP geometry) | MISALIGNED | Nominal geometry は MR と整合し、SL は band 外側 `0.3ATR`、TP は midline。ただし RR が `1.5` 未満なら TP を `entry ± sl_dist*1.5` へ補正し、midline mean target を超えてしまう。MR thesis では「mean まで戻る」を取るべきで、RR 達成のために TP を mean より遠くへ伸ばす補正は thesis と衝突する。`strategies/daytrade/lin_reg_channel.py:67`, `strategies/daytrade/lin_reg_channel.py:68`, `strategies/daytrade/lin_reg_channel.py:78`, `strategies/daytrade/lin_reg_channel.py:195`, `strategies/daytrade/lin_reg_channel.py:196`, `strategies/daytrade/lin_reg_channel.py:208`, `strategies/daytrade/lin_reg_channel.py:209`, `strategies/daytrade/lin_reg_channel.py:254`, `strategies/daytrade/lin_reg_channel.py:255`, `strategies/daytrade/lin_reg_channel.py:256`, `strategies/daytrade/lin_reg_channel.py:258`, `strategies/daytrade/lin_reg_channel.py:259`, `strategies/daytrade/lin_reg_channel.py:260`, `strategies/daytrade/lin_reg_channel.py:261` |
| 6 (pair-regime fit) | FORCED | Input は `ALL` だが code は EURUSD のみ通し、他 pair は即 `None`。既存 BT/audit evidence も EURUSD 中心で、ALL cell としての pair-regime fit は証明されていない。下の pair-regime table 参照。`strategies/daytrade/lin_reg_channel.py:129`, `strategies/daytrade/lin_reg_channel.py:136`, `strategies/daytrade/lin_reg_channel.py:137`, `strategies/daytrade/lin_reg_channel.py:138` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の force_demoted 行は 365d BT EV が `—`。最新 gate-progression audit は N=2, WR=50.00%, Wilson lo=9.45%, EV=-0.40p, PF=0.917, Kelly=0.0000, Bonferroni p=1.0000。既存 walk-forward は w90 で folds=3 だが positive_ratio=0.333 / unstable。N/WR/EV 単独採用は禁止されるため、decision-grade evidence は不足。 |

### Pair-Regime Table

| Pair | Verdict | Evidence |
|------|---------|----------|
| EURUSD | FIT / weak | Code は EURUSD のみ許可。既存 365d EURUSD edge-lab は N=32, WR=62.5%, Wilson lo=45.25%, PF=1.005, Kelly=0.0034 とほぼ breakeven。session-zoo は London N=21, PF=0.75 に対し NY N=8, PF=3.11 で session 依存が大きい。 |
| XAUUSD | FORCED | コメントでは一度採用候補だったが MR 単独では EV=-0.017 と記載され、現行 code は XAUUSD を通さない。`strategies/daytrade/lin_reg_channel.py:133`, `strategies/daytrade/lin_reg_channel.py:135`, `strategies/daytrade/lin_reg_channel.py:137` |
| USDJPY | FORCED | コメント上 7 trades EV=-0.053 で負 EV、現行 code は USDJPY を通さない。`strategies/daytrade/lin_reg_channel.py:130`, `strategies/daytrade/lin_reg_channel.py:137` |
| GBPUSD | FORCED | コメント上 15 trades EV=+0.002 でゼロ、現行 code は GBPUSD を通さない。`strategies/daytrade/lin_reg_channel.py:131`, `strategies/daytrade/lin_reg_channel.py:137` |
| Other pairs | FORCED | ALL 指定に対し code/evidence とも decision-grade の fit を示していない。`strategies/daytrade/lin_reg_channel.py:137`, `strategies/daytrade/lin_reg_channel.py:138` |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) の failure mode は Axis 3 と Axis 5。Axis 2 は channel extension + reversal を捕捉しており thesis 自体は読めるが、同一評価足の `ctx.entry/open_price` と `df.iloc[-LR_PERIOD:]` に依存するため、closed-bar 化されていない実行系では signal と execution の境界が曖昧になる。さらに Axis 5 では、MR の本来 target である midline を RR 補正で超過させるため、勝ち方が「mean へ戻る」から「mean を越えて 1.5R まで伸びる」に変質する。

再設計案は、signal bar を確定足に固定し、entry は次 bar execution として扱うこと。BUY なら確定足 `Close[signal] <= lower + zone` かつ `Close[signal] > Open[signal]` かつ `Close[signal] > lower`、SELL は対称条件にし、Candidate には `(entry_type, symbol, signal_bar_time, direction)` 相当の dedup key を載せる。Stop/TP は MR geometry を守り、TP は原則 midline 固定、RR が足りない場合は TP を伸ばさず「entry を見送る」または「lower/upper への proximity を厳格化して必要 RR を満たす signal だけ採用」に変える。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

Trigger の思想は維持し、timing と stop/TP geometry を 1 系統ずつ直す。具体的には channel/reversal 判定を確定済み signal bar に限定し、次 bar の entry price で Candidate を返す。現行の `ctx.entry > ctx.open_price` / `ctx.entry < ctx.open_price` は signal bar の `Close > Open` / `Close < Open` に置き換え、同一 bar 再発火防止の signal timestamp を Candidate 周辺に渡す。

Stop/TP は MR として midline target を固定する。`_tp_dist / _sl_dist < 1.5` の場合に TP を外側へ動かすのではなく、entry zone を `MR_ZONE_PCT=0.15` 程度へ狭める、または `sl = min(signal_low, lower) - 0.3ATR` / `max(signal_high, upper) + 0.3ATR` とした上で midline 到達時の実 R が閾値未満なら no-trade にする。採用前には本 audit では実行しない 365d + WF folds>=3 の再集計で、Wilson lower / PF / Bonferroni-adjusted p / Kelly を同一 artifact に出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 2 latest gate-progression aggregate; existing 365d EURUSD edge-lab N=32; tier-master force_demoted 365d BT EV is `—` | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; existing BT artifact `knowledge-base/raw/bt-results/edge-lab-365d-eurusd-2026-04-26.json`; `knowledge-base/wiki/tier-master.md` |
| Win rate | 50.00% latest gate-progression aggregate; existing 365d EURUSD edge-lab 62.5% | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; existing BT artifact `knowledge-base/raw/bt-results/edge-lab-365d-eurusd-2026-04-26.json` |
| Wilson lo (95%) | 9.45% latest gate-progression aggregate; existing 365d EURUSD edge-lab 45.25% | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; read-only calculation from existing BT artifact `knowledge-base/raw/bt-results/edge-lab-365d-eurusd-2026-04-26.json` |
| PF | 0.917 latest gate-progression aggregate; existing 365d EURUSD edge-lab 1.005; tier-master PF not available | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; read-only calculation from existing BT artifact; `knowledge-base/wiki/tier-master.md` |
| WF folds (3+) | w90 existing WF: folds=3, aggregate N=29, WR=62.1%, EV=+0.006, PF=1.01, positive_ratio=0.333, verdict=unstable | existing WF artifact `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.json` |
| Bonferroni-adj p | 1.0000 latest gate-progression aggregate | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md` |
| Kelly fraction | 0.0000 latest gate-progression aggregate (raw Kelly -0.0455); existing 365d EURUSD edge-lab Kelly 0.0034 | audit DB / `knowledge-base/wiki/decisions/gate-progression-audit-2026-05-03.md`; read-only calculation from existing BT artifact `knowledge-base/raw/bt-results/edge-lab-365d-eurusd-2026-04-26.json` |
