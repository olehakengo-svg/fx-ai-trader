---
strategy: sr_break_retest
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

Fractal cluster で得た SR level を実体 close で突破し、その後 SR 近傍へ戻ったリテスト足が breakout 方向へ反発した場合に、role reversal 後の trend continuation を取る breakout-pullback thesis。コード上も「真ブレイク → リテスト → 継続」と明示され、ADX/HTF で breakout の方向性を確認する設計になっている。`strategies/daytrade/sr_break_retest.py:10`, `strategies/daytrade/sr_break_retest.py:13`, `strategies/daytrade/sr_break_retest.py:16`, `strategies/daytrade/sr_break_retest.py:17`, `strategies/daytrade/sr_break_retest.py:24`, `strategies/daytrade/sr_break_retest.py:29`, `strategies/daytrade/sr_break_retest.py:37`, `strategies/daytrade/sr_break_retest.py:50`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / breakout-pullback thesis に対し、trigger は `SR = cluster(fractal highs + lows) ∧ ADX >= 20 ∧ break_close > SR + 0.05ATR ∧ pre_close <= SR + 0.05ATR ∧ abs(entry - SR) <= 0.7ATR ∧ entry > open ∧ entry > SR ∧ entry > EMA9` で BUY、SELL は対称。SR 実体 breakout、breakout 前状態、retest zone、反発足、EMA9 回復を直接捕捉しており、MR thesis に momentum filter を誤適用する型ではない。ただし high/low fractal を統合するため、旧 resistance / old support の役割分類は弱い。`strategies/daytrade/sr_break_retest.py:57`, `strategies/daytrade/sr_break_retest.py:59`, `strategies/daytrade/sr_break_retest.py:63`, `strategies/daytrade/sr_break_retest.py:66`, `strategies/daytrade/sr_break_retest.py:69`, `strategies/daytrade/sr_break_retest.py:70`, `strategies/daytrade/sr_break_retest.py:165`, `strategies/daytrade/sr_break_retest.py:176`, `strategies/daytrade/sr_break_retest.py:177`, `strategies/daytrade/sr_break_retest.py:209`, `strategies/daytrade/sr_break_retest.py:213`, `strategies/daytrade/sr_break_retest.py:217`, `strategies/daytrade/sr_break_retest.py:219`, `strategies/daytrade/sr_break_retest.py:221`, `strategies/daytrade/sr_break_retest.py:227`, `strategies/daytrade/sr_break_retest.py:230`, `strategies/daytrade/sr_break_retest.py:233`, `strategies/daytrade/sr_break_retest.py:234`, `strategies/daytrade/sr_break_retest.py:236` |
| 3 (timing window) | LOOKAHEAD | Fractal は `_end = len(df) - n` で未確定の最新 `n` 本を除外し、breakout bar も `BREAK_LOOKBACK_MIN = 2` 以降を見るため、その部分は未来参照ではない。一方、retest confirmation は current bar の `ctx.entry`, `ctx.open_price`, `ctx.ema9` をそのまま使い、strategy 内に signal bar close 固定や同一 bar dedup key がない。実行層が intrabar evaluate すると、同一 15m bar 中の暫定陽線/陰線や EMA crossing で phantom entry / 多重 emit が起きる。`strategies/daytrade/sr_break_retest.py:63`, `strategies/daytrade/sr_break_retest.py:93`, `strategies/daytrade/sr_break_retest.py:191`, `strategies/daytrade/sr_break_retest.py:194`, `strategies/daytrade/sr_break_retest.py:217`, `strategies/daytrade/sr_break_retest.py:219`, `strategies/daytrade/sr_break_retest.py:221`, `strategies/daytrade/sr_break_retest.py:233`, `strategies/daytrade/sr_break_retest.py:234`, `strategies/daytrade/sr_break_retest.py:236`, `strategies/daytrade/sr_break_retest.py:374` |
| 4 (filter coherence) | STRENGTHENS | `ADX_MIN=20` は breakout 信頼度の momentum filter で thesis を補強する。HTF agreement は BUY を bear HTF で、SELL を bull HTF で veto する逆方向 block なので breakout continuation と整合する。EMA9 reclaim は retest 反発確認として STRENGTHENS。EURUSD/EURGBP 除外は empirical pair gate で、思想自体は壊さないが ALL thesis とは不一致なので Axis 6 に回す。MA filter on MR strategy や HMM regime gate same-trap のような tail edge 破壊ではない。`strategies/daytrade/sr_break_retest.py:72`, `strategies/daytrade/sr_break_retest.py:73`, `strategies/daytrade/sr_break_retest.py:148`, `strategies/daytrade/sr_break_retest.py:153`, `strategies/daytrade/sr_break_retest.py:154`, `strategies/daytrade/sr_break_retest.py:165`, `strategies/daytrade/sr_break_retest.py:249`, `strategies/daytrade/sr_break_retest.py:250`, `strategies/daytrade/sr_break_retest.py:252`, `strategies/daytrade/sr_break_retest.py:254`, `strategies/daytrade/sr_break_retest.py:339`, `strategies/daytrade/sr_break_retest.py:345`, `strategies/daytrade/sr_break_retest.py:351`, `strategies/daytrade/sr_break_retest.py:357` |
| 5 (stop/TP geometry) | MISALIGNED | SL は SR 裏側 `0.3ATR`、TP は `max(2.0ATR, 1.5R)` の fixed target、round-number 近傍では TP を内側へ 3 pips ずらし SL を 1.3 倍拡張する。最低 RR は保つが、breakout continuation thesis の出口として trailing / break-even / trend extension capture がなく、spec の breakout=trailing 期待から外れる。`MAX_HOLD_BARS=12` も Candidate へ渡されず、exit geometry として実装されていない。`strategies/daytrade/sr_break_retest.py:76`, `strategies/daytrade/sr_break_retest.py:77`, `strategies/daytrade/sr_break_retest.py:78`, `strategies/daytrade/sr_break_retest.py:81`, `strategies/daytrade/sr_break_retest.py:263`, `strategies/daytrade/sr_break_retest.py:266`, `strategies/daytrade/sr_break_retest.py:269`, `strategies/daytrade/sr_break_retest.py:271`, `strategies/daytrade/sr_break_retest.py:273`, `strategies/daytrade/sr_break_retest.py:274`, `strategies/daytrade/sr_break_retest.py:275`, `strategies/daytrade/sr_break_retest.py:288`, `strategies/daytrade/sr_break_retest.py:290`, `strategies/daytrade/sr_break_retest.py:298`, `strategies/daytrade/sr_break_retest.py:374` |
| 6 (pair-regime fit) | FORCED | Header は全ペア対応を掲げるが、実装は EURUSD/EURGBP を即除外し、USDJPY/GBPUSD だけをコメント上の小標本 EV で採用している。ALL cell としては pair universe が実装と一致せず、pair-specific threshold / session / spread handling もない。下表参照。`strategies/daytrade/sr_break_retest.py:34`, `strategies/daytrade/sr_break_retest.py:35`, `strategies/daytrade/sr_break_retest.py:148`, `strategies/daytrade/sr_break_retest.py:149`, `strategies/daytrade/sr_break_retest.py:150`, `strategies/daytrade/sr_break_retest.py:151`, `strategies/daytrade/sr_break_retest.py:152`, `strategies/daytrade/sr_break_retest.py:153`, `strategies/daytrade/sr_break_retest.py:154` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE / negative partial evidence | tier-master force_demoted 365d BT EV は `—`。既存 audit DB では latest strategy aggregate が N=12, WR=50.0%, Wilson lo=25.4%, avg=-7.24p, net_edge=-12.09p。別 artifact の USDJPY shadow negative cell は N=11, WR=18.2%, Wilson lo=5.14%, PF=0.058, EV_net=-32.427p だが clustering は artifactual。WF folds>=3 と Bonferroni-adjusted p は exact `sr_break_retest` ALL cell で見つからないため、`feedback_partial_quant_trap.md` 基準では decision-grade 不足。 |

### Axis 6 Pair-Regime Fit Detail

| Pair | Fit | Basis |
|------|-----|-------|
| USDJPY | FIT / failed-evidence | Code comment は USDJPY 64t WR=64.1% EV=+0.252 で採用としているが、audit DB negative cell は USD_JPY N=11, WR=18.2%, Wilson lo=5.14%, PF=0.058, EV_net=-32.427p。small / clustered だが現 evidence は悪い。`strategies/daytrade/sr_break_retest.py:149` |
| GBPUSD | FIT / insufficient | Code comment は GBPUSD 46t WR=60.9% EV=+0.145 で採用。ただし tier-master/audit DB から Wilson/PF/Kelly/WF folds を復元できない。`strategies/daytrade/sr_break_retest.py:150` |
| EURUSD | FORCED / blocked | Code comment は EURUSD 27t WR=55.6% EV=+0.017 で不採用、実装も即 `None`。ALL 指定とは不一致。`strategies/daytrade/sr_break_retest.py:151`, `strategies/daytrade/sr_break_retest.py:154` |
| EURGBP | FORCED / blocked | 未検証・低ボラ・spread 負担大として即 `None`。ALL 指定とは不一致。`strategies/daytrade/sr_break_retest.py:152`, `strategies/daytrade/sr_break_retest.py:154` |
| Other ALL pairs | FORCED | コード上は EURUSD/EURGBP 以外を通し得るが、pair-specific validation / threshold がない。 |

## Axis 8: failure mode 診断

Tier 3 (FORCE_DEMOTED) なので failure mode 診断を適用する。破綻軸は主に Axis 3 と Axis 5、補助的に Axis 6。Axis 2 の trigger は SR breakout → retest → bounce を数学的に捕捉しており、Axis 4 の ADX/HTF/EMA filter も breakout continuation thesis を壊していない。一方で、retest/bounce を current bar の `ctx.entry` と `ctx.open_price` で判定するため、bar-close contract と dedup がない運用では未確定 bar 反転を拾う。さらに breakout continuation の利幅を伸ばす trailing がなく、固定 2ATR / 1.5R TP と SR 裏 0.3ATR SL に閉じている。

再設計案は、trigger の思想を維持しつつ timing と exit を変える。まず retest 反転確認を current tick から確定済み signal bar へ移し、`signal_bar = ctx.df.iloc[-2]` の `Close > Open`, `Close > SR`, `Close > EMA9` を BUY 条件、SELL は対称にする。`ctx.entry` は次 bar execution price としてのみ使い、Candidate または dispatch layer に `(symbol, entry_type, side, signal_bar_time, sr_level_bucket)` の dedup key を渡す。次に TP を fixed 2ATR から、初期 `1R` 到達で break-even、以後 `EMA9/EMA21` or `1ATR` trailing に変更する。pair は redesign BT まで USDJPY/GBPUSD に限定し、ALL 復帰は pair 別 Wilson/PF/Kelly/WF folds が揃ってからにする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想は有効候補として残す。SR breakout 後の retest continuation はコードから明確に導出でき、trigger/filter の中心部も thesis に沿っているため、`THESIS_INVALID` ではない。ただし FORCE_DEMOTED かつ既存 audit DB は negative partial evidence を示し、bar-close/dedup と exit geometry の 2 軸を直さない限り Shadow 復帰は弱い。

具体修正は 2 段階。第一に、`ctx.entry > ctx.open_price` / `< ctx.open_price` の current bar 判定を、確定済み signal bar の `Close > Open` / `< Open` と SR reclaim / EMA9 reclaim に置換する。第二に、`TP_ATR_MULT=2.0` の fixed target を主出口にせず、初期 stop は SR 裏側に維持したまま、`1R` 到達後 break-even、以後 EMA9/EMA21 or ATR trailing で breakout continuation を取りに行く。検証は新規 BT が必要だが、本 audit では実行しない。必要 artifact は pair 別 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source で出すこと。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Strategy latest: 12; USDJPY negative cell: 11; USDJPY BUY negative cell: 10 | audit DB: `raw/audits/daily_live_latest.json`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json` |
| Win rate | Strategy latest: 50.0%; USDJPY negative cell: 18.18%; USDJPY BUY negative cell: 20.0% | audit DB: `raw/audits/daily_live_latest.json`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json` |
| Wilson lo (95%) | Strategy latest: 25.4%; USDJPY negative cell: 5.14%; USDJPY BUY negative cell: 5.67% | audit DB: `raw/audits/daily_live_latest.json`; `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json` |
| PF | USDJPY negative cell: 0.058; USDJPY BUY negative cell: 0.062; exact ALL PF: INSUFFICIENT_EVIDENCE | audit DB: `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; tier-master has `—` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: exact `sr_break_retest` ALL WF fold table not found in tier-master/current audit DB | tier-master: `knowledge-base/wiki/tier-master.md`; repo audit artifact search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: exact `sr_break_retest` ALL Bonferroni-adjusted p not found | tier-master: `knowledge-base/wiki/tier-master.md`; repo audit artifact search |
| Kelly fraction | USDJPY negative cell derived from audit DB WR/PF: approximately -2.95 full Kelly; USDJPY BUY derived: approximately -3.03 full Kelly; exact ALL Kelly: INSUFFICIENT_EVIDENCE | derived from `wr - wr / PF` using `raw/audits/cell_negative_edge_2026-04-28_all_shadow.json`; tier-master has `—` |
