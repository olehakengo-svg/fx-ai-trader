---
strategy: ema200_trend_reversal
tier: Tier 1 (LIVE)
source_tier: pair_promoted
pairs: USD_JPY
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

EMA200 を一度 breakout した後、価格が EMA200 近傍へ戻る retest を待ち、短期 EMA 配列と MACD histogram の再加速方向へ入る pullback / trend-reversal continuation 戦略。コード上も `strategy_type = "pullback"` とし、EMA200 cross window と `0.5ATR` 以内の retest 距離を要求している。`strategies/daytrade/ema200_reversal.py:12`, `strategies/daytrade/ema200_reversal.py:15`, `strategies/daytrade/ema200_reversal.py:34`, `strategies/daytrade/ema200_reversal.py:46`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | BUY は `ema9 > ema200 ∧ ema21 > ema200 ∧ 0 < (entry-ema200)/ATR < 0.5 ∧ macdh > macdh_prev ∧ RSI < 55`。SELL は `not bull200 ∧ -0.5 < dist < 0 ∧ macdh < macdh_prev ∧ RSI > 45`。EMA200 cross 後の retest 近傍で、短期 trend alignment と momentum 再加速を確認しており、pullback thesis と整合する。`strategies/daytrade/ema200_reversal.py:26`, `strategies/daytrade/ema200_reversal.py:27`, `strategies/daytrade/ema200_reversal.py:37`, `strategies/daytrade/ema200_reversal.py:42`, `strategies/daytrade/ema200_reversal.py:50`, `strategies/daytrade/ema200_reversal.py:62` |
| 3 (timing window) | OK | EMA200 cross 検出は `df[-ec-1] -> df[-ec]` の閉じた過去 bar を見るため future bar は参照しない。現在 bar では `ctx.entry` と EMA200 の距離で retest を判定し、1 回の `evaluate()` は最大 1 Candidate だけ返す。ただし strategy 内に `bar_time` dedup はなく、同一 bar 多重評価の防止は実行層依存。`strategies/daytrade/ema200_reversal.py:18`, `strategies/daytrade/ema200_reversal.py:37`, `strategies/daytrade/ema200_reversal.py:38`, `strategies/daytrade/ema200_reversal.py:40`, `strategies/daytrade/ema200_reversal.py:46`, `strategies/daytrade/ema200_reversal.py:78` |
| 4 (filter coherence) | STRENGTHENS | `_crosses >= 1` は recent EMA200 break を要求し、`abs(dist) < 0.5ATR` は retest 近傍に絞る。`bull200` / `not bull200` と MACD histogram 方向は breakout 後の短期方向確認で、MR に MA gate を当てる破壊例ではない。RSI は BUY `<55` / SELL `>45` で過熱追随を抑える中立から強化寄りの filter。EMA200 slope は score bonus のみで hard gate ではない。`strategies/daytrade/ema200_reversal.py:26`, `strategies/daytrade/ema200_reversal.py:46`, `strategies/daytrade/ema200_reversal.py:50`, `strategies/daytrade/ema200_reversal.py:51`, `strategies/daytrade/ema200_reversal.py:55`, `strategies/daytrade/ema200_reversal.py:62`, `strategies/daytrade/ema200_reversal.py:67`, `strategies/daytrade/ema200_reversal.py:77` |
| 5 (stop/TP geometry) | ALIGNED | BUY は `TP = entry + 2.0 * ATR7`, `SL = entry - 1.0 * ATR7`、SELL は対称で、R:R は約 2.0。EMA200 retest から trend continuation を取りに行く pullback geometry として、損失を retest failure で切り、利益を継続方向に伸ばす非対称構造になっている。`strategies/daytrade/ema200_reversal.py:58`, `strategies/daytrade/ema200_reversal.py:59`, `strategies/daytrade/ema200_reversal.py:70`, `strategies/daytrade/ema200_reversal.py:71` |
| 6 (pair-regime fit) | FIT | USD_JPY pair-only shadow sub-cell は N=13, WR=61.5%, EV_cost=+5.39p, PF=4.76, Bootstrap 95% EV CI=[+1.12,+11.78]。ただし 365d BT は USD_JPY で負 EV/PF<1 の記録があり、fit は USDJPY 全時間帯ではなく Overlap/NY 寄りの条件付き FIT。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | 昇格根拠の shadow pair-only 数値は positive だが N=13 で Wilson lower は 35.5% に留まり、tier-master は 365d BT EV `—`。WF は USDJPY で folds=2 止まりの report が多く、Bonferroni-adjusted p は decision-grade の pair-level 値がない。数値は下表。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USD_JPY | FIT / WATCH | Pair-promoted 根拠は shadow USDJPY N=13, WR=61.5%, EV_cost=+5.39p, PF=4.76。Overlap は N=7, WR=100%, EV_cost=+11.63p。旧 BT では USDJPY N=24, WR=58.3%, EV=-0.064 または N=32, WR=56.2%, PF=0.77 の負 EV 記録があり、session 依存を疑うべき。 |

## Axis 8: failure mode 診断

Tier 1 (LIVE) かつ pair_promoted だが、BT 365d 側は USDJPY 負 EV / PF<1 の記録があり、直近 R2 cell demotion lock でも hour 17/20 の小 N loss が WATCH、hour 13 の N=1 win が KEEP という粒度に分解されている。Axis 2/3/5 のコード設計は thesis と整合しており、破綻は trigger 数式そのものではない。失敗候補は Axis 4 の「必要な timing/session filter がコードにない」点と Axis 7 の decision-grade evidence 不足。

再設計案: trigger と R:R は維持し、USDJPY の live routing を暫定的に Overlap/NY-overlap 相当の `12 <= ctx.hour_utc < 16` に絞る timing filter を追加する。昇格根拠が Overlap N=7, WR=100%, EV_cost=+11.63p に集中しているため、全時間帯に同じ EMA200 retest thesis を強制するより、session-gated pullback として再定義して shadow / micro-live で N>=30 を蓄積する。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`A`

最小の再設計は timing filter 1 系統。`evaluate()` の冒頭または `_crosses` 通過後に USDJPY pair-promoted 用の session gate を置き、`ctx.hour_utc` が Overlap/NY-overlap 外なら `return None` にする案が最も小さい。これにより、EMA200 retest trigger / MACD再加速 / 2:1 R:R は維持したまま、昇格根拠のある時間帯だけを live 対象にできる。

次点の修正は SELL 側 trend confirmation の厳格化。現状の `not bull200` は `ema9 <= ema200 or ema21 <= ema200` でも成立するため、再設計 variant では SELL を `ema9 < ema200 and ema21 < ema200` にし、BUY と対称にする。ただしこれは trigger 改変なので、まずは session gate のみを A 優先で検証し、追加 BT が必要な場合は新規 BT 内容として「USDJPY 15m, session-gated, 365d + WF folds>=3 + Bonferroni/Kelly」を事前登録する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | Shadow pair-only USDJPY N=13; Overlap N=7; 365d BT references N=24 / N=32; latest R2 hour cells N=1 each | `knowledge-base/wiki/analyses/shadow-subcell-analysis-2026-04-23.md`; `knowledge-base/raw/bt-results/bt-365d-2026-04-22.json`; `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md`; `knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md` |
| Win rate | Shadow pair-only 61.5%; Overlap 100.0%; 365d BT references 58.3% / 56.2%; latest R2 hour cells include 0.0% losses and 100.0% win at N=1 | same sources |
| Wilson lo (95%) | Shadow pair-only derived 35.5% (8/13); Overlap derived 64.6% (7/7); 365d BT derived 38.8% (14/24) or 39.3% (18/32); latest R2 N=1 win 20.65% | derived from existing N/WR; R2 report |
| PF | Shadow pair-only 4.76; Overlap ∞; comprehensive 365d BT USDJPY 0.77; W90 USDJPY 0.87; W60 USDJPY 323.67 on only 2 folds | `knowledge-base/wiki/analyses/shadow-subcell-analysis-2026-04-23.md`; `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: USDJPY W60 folds=2, W90 folds=2, 730d folds=2; fails WF>=3 requirement despite W90 positive_ratio=1.00 | `knowledge-base/raw/bt-results/walkforward-w60-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-w90-2026-04-22.md`; `knowledge-base/raw/bt-results/walkforward-730d-2026-04-22.md` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: promotion analysis used Bootstrap EV CI, not pair-level Bonferroni; latest R2 tiny hour cells show p=1.0000 and are not decision-grade | `knowledge-base/wiki/analyses/shadow-subcell-analysis-2026-04-23.md`; `knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md` |
| Kelly fraction | Shadow-derived full Kelly approx +0.486 from WR=8/13 and PF=4.76; latest R2 N=1 hour cell raw Kelly +0.0000; tier-master has no Kelly column | derived from shadow WR/PF; `knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md`; `knowledge-base/wiki/tier-master.md` |
| tier-master EV | USD_JPY 365d BT EV `—` | `knowledge-base/wiki/tier-master.md` |
