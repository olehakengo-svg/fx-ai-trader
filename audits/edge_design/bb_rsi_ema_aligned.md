---
strategy: bb_rsi_ema_aligned
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

USD/JPY の BB/RSI 平均回帰を、ADX>=30 と Tokyo/London Gold Hours に限定すれば、EMA200 整合のように MR 機構を壊さずに edge を集中できる、という thesis。コード上も `strategy_type = "MR"`、USD_JPY 限定、ADX 下限、Gold Hours、親 `bb_rsi` の MR ロジック委譲として明示されている。`strategies/scalp/bb_rsi_ema_aligned.py:14`, `strategies/scalp/bb_rsi_ema_aligned.py:18`, `strategies/scalp/bb_rsi_ema_aligned.py:35`, `strategies/scalp/bb_rsi_ema_aligned.py:36`, `strategies/scalp/bb_rsi_ema_aligned.py:37`, `strategies/scalp/bb_rsi_ema_aligned.py:53`, `strategies/scalp/bb_rsi_ema_aligned.py:68`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Target wrapper の entry 条件は `normalize_pair(symbol) in {USD_JPY} AND adx >= 30 AND hour_utc in {5,6,7,8,19,20,21,22,23} AND parent_bb_rsi_mr(ctx)`。MR thesis に対し、対象ファイルは BB%B + RSI + Stoch + 確認足を親ロジックとして使うことを明記し、EMA200 整合は撤去済みなので、target file レベルでは MR trigger と filter が数学的に矛盾していない。`strategies/scalp/bb_rsi_ema_aligned.py:8`, `strategies/scalp/bb_rsi_ema_aligned.py:20`, `strategies/scalp/bb_rsi_ema_aligned.py:24`, `strategies/scalp/bb_rsi_ema_aligned.py:57`, `strategies/scalp/bb_rsi_ema_aligned.py:61`, `strategies/scalp/bb_rsi_ema_aligned.py:65`, `strategies/scalp/bb_rsi_ema_aligned.py:69` |
| 3 (timing window) | OK | この派生ファイル自体は `ctx` の現在値で L1-L3 gate を行い、`super().evaluate(ctx)` を一度呼ぶだけで、未来 bar 参照や `df.iloc[-1/+1]` 型の look-ahead はない。bar-close 化と同一 bar dedup はこの strategy file には実装されていないが、同ファイル内で同一 bar 多重 entry を発生させる loop/state 更新もないため、対象ファイル単体の timing verdict は OK。`strategies/scalp/bb_rsi_ema_aligned.py:55`, `strategies/scalp/bb_rsi_ema_aligned.py:57`, `strategies/scalp/bb_rsi_ema_aligned.py:61`, `strategies/scalp/bb_rsi_ema_aligned.py:65`, `strategies/scalp/bb_rsi_ema_aligned.py:69`, `strategies/scalp/bb_rsi_ema_aligned.py:74` |
| 4 (filter coherence) | STRENGTHENS | L1 pair gate は USD_JPY のみで、親 `bb_rsi` の USD/JPY 高 WR 条件を isolation するので STRENGTHENS。L2 ADX>=30 は一般 MR には危険な trend filter だが、このファイルの thesis は「USD_JPY トレンド中 BB 反発」を狙う設計なので STRENGTHENS。ただし MA filter on MR -> BREAKS の先行例に従い、EMA200 整合の再導入は禁止。HMM regime gate same-trap と同様、edge が出る regime tail を generic gate で削る追加 filter も BREAKS になり得る。L3 Gold Hours は thesis の session concentration なので STRENGTHENS。`strategies/scalp/bb_rsi_ema_aligned.py:4`, `strategies/scalp/bb_rsi_ema_aligned.py:6`, `strategies/scalp/bb_rsi_ema_aligned.py:8`, `strategies/scalp/bb_rsi_ema_aligned.py:10`, `strategies/scalp/bb_rsi_ema_aligned.py:11`, `strategies/scalp/bb_rsi_ema_aligned.py:16`, `strategies/scalp/bb_rsi_ema_aligned.py:17`, `strategies/scalp/bb_rsi_ema_aligned.py:57`, `strategies/scalp/bb_rsi_ema_aligned.py:61`, `strategies/scalp/bb_rsi_ema_aligned.py:65` |
| 5 (stop/TP geometry) | MISALIGNED | 対象ファイルは `super().evaluate(ctx)` の Candidate を受け取り、`entry_type` と `reasons` だけを書き換えるため、SL/TP geometry は親 `bb_rsi` から継承され、この file では ADX>=30 / Gold Hours 専用に調整されていない。既存 audit の v1d-rev 記録では、この MR の TP が 4-5 pip 域に収まり spread 比率が重く、ADX>=30 + Gold Hours でも PF=0.97 / Kelly=0 / EV=-0.09 に留まった。よって target wrapper の thesis に対して、継承 stop/TP は cost-edge ratio を吸収できず MISALIGNED。`strategies/scalp/bb_rsi_ema_aligned.py:12`, `strategies/scalp/bb_rsi_ema_aligned.py:68`, `strategies/scalp/bb_rsi_ema_aligned.py:69`, `strategies/scalp/bb_rsi_ema_aligned.py:73`, `strategies/scalp/bb_rsi_ema_aligned.py:74`, `strategies/scalp/bb_rsi_ema_aligned.py:75` |
| 6 (pair-regime fit) | FIT | 入力 pair は ALL だが、実装は USD_JPY 以外を L1 で no-trade にする。したがって実トレード対象は USD_JPY のみで、thesis と pair gate は一致する。下表参照。`strategies/scalp/bb_rsi_ema_aligned.py:21`, `strategies/scalp/bb_rsi_ema_aligned.py:35`, `strategies/scalp/bb_rsi_ema_aligned.py:57` |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master では SCALP_SENTINEL 所属のみで 365d BT EV は `-`。既存 audit DB には v1d-rev 365d 相当で N=365 / WR=35.62% / Wilson lo=30.88% / PF=0.97 / Kelly=0 / p=0.99938 / EV=-0.091、fold PF は f1=1.166, f2=0.793, f3=0.946 がある。ただし Bonferroni-adjusted p は family size として保存されておらず、`feedback_partial_quant_trap.md` 基準の decision-grade evidence は未充足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT | Code gates USD_JPY only and thesis explicitly cites USD/JPY ADX>=30 BB反発 + Gold Hours. `strategies/scalp/bb_rsi_ema_aligned.py:10`, `strategies/scalp/bb_rsi_ema_aligned.py:11`, `strategies/scalp/bb_rsi_ema_aligned.py:21`, `strategies/scalp/bb_rsi_ema_aligned.py:35`, `strategies/scalp/bb_rsi_ema_aligned.py:57` |
| non-USD_JPY | FORCED / NO-TRADE | `pairs: ALL` input is broader than implementation; non-USD_JPY is forced out by L1 and produces no candidate. `strategies/scalp/bb_rsi_ema_aligned.py:35`, `strategies/scalp/bb_rsi_ema_aligned.py:57`, `strategies/scalp/bb_rsi_ema_aligned.py:58` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 5 が主、Axis 4 は現設計では STRENGTHENS だが追加 filter に弱い。Axis 2 の trigger thesis は明確で、EMA200 整合を撤去した点も MA filter breaks MR の先行例に沿う。一方、ADX>=30 + Gold Hours で N を絞っても PF=0.97 / Kelly=0 / EV=-0.091 に止まっており、既存記録は「思想は正寄りだが、scalp MR の利幅と spread/cost に対して stop/TP geometry が足りない」ことを示す。

再設計案は Stop/TP geometry 変更を主軸にする。具体的には ADX>=30 Gold Hours variant を、継承の短距離 MR TP から切り離し、entry 後の平均線復帰だけでなく trend continuation 側の伸びも拾う hybrid exit にする。候補は `tp = max(mean_reversion_target, sl_dist * 3.0, recent_swing_mid)` とし、stop は BB 外側 + ATR buffer を維持、時間切れ exit を短くして spread 負けする小幅 TP を避ける。新規 BT は本タスク範囲外なので、365d + WF folds>=3 で Wilson lo / PF / Bonferroni p / Kelly を同一 source から再集計する必要がある。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想はコードから明確に導けるため棄却しない。trigger と pair/session/regime filter は target wrapper の thesis と一致しているが、現行は親 `bb_rsi` の SL/TP をそのまま使い、ADX>=30 Gold Hours に限定した USD/JPY scalp MR の cost-edge ratio を吸収できていない。再設計の焦点は Stop/TP geometry の 1 系統でよい。

具体的には、`super().evaluate(ctx)` 後に `cand.sl` / `cand.tp` をこの variant 専用に再計算する。BUY は BB lower 外側 + ATR buffer を stop に残しつつ、TP を「BB mid / EMA 短期平均への復帰」と「RR floor 3.0」の大きい方にし、SELL も対称にする。さらに小幅利確が spread に食われる場合は candidate を破棄する minimum net TP gate を追加する。実装前に 365d audit DB で WF folds>=3、Bonferroni-adjusted p、Kelly fraction が揃う再集計が必要。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 365 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv` / `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| Win rate | 35.62% | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| Wilson lo (95%) | 30.88% | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
| PF | 0.97 | audit DB; tier-master has SCALP_SENTINEL membership only and no PF for this strategy |
| WF folds (3+) | 3 folds available; PF by fold = f1 1.166, f2 0.793, f3 0.946, so 1/3 folds PF>1 and WF stability fails | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_summary_20260430_072404.csv` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE; stored p=0.99938, but Bonferroni family size / adjusted p is not present in tier-master or the audit CSV | audit DB + tier-master |
| Kelly fraction | 0.0 | audit DB: `knowledge-base/raw/audits/ma_family_v1/USD_JPY_promotion_20260430_072404.csv` |
