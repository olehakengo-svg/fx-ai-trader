---
strategy: vwap_mean_reversion
tier: Tier 3 (FORCE_DEMOTED)
source_tier: force_demoted
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

価格が VWAP から直近 50 本の VWAP 乖離率分布で 2σ 以上外れたとき、その外れ値は継続ではなく VWAP 方向へ平均回帰する、という thesis。BUY は `entry < VWAP - 2σ`、SELL は `entry > VWAP + 2σ` で、コードコメントも「VWAP-2σ回帰」と明示している。`app.py:3253-3363,8766+ (INLINE):3253`, `app.py:3253-3363,8766+ (INLINE):3262`, `app.py:3253-3363,8766+ (INLINE):3263`, `app.py:3253-3363,8766+ (INLINE):3267`, `app.py:3253-3363,8766+ (INLINE):3270`, `app.py:3253-3363,8766+ (INLINE):3339`, `app.py:3253-3363,8766+ (INLINE):3341`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `_vmr_dev = (entry - vwap) / vwap * 100`、`sigma = std(tail_50(Close-vwap)/vwap)`、BUY: `_vmr_dev < -2 * _vmr_std`、SELL: `_vmr_dev > 2 * _vmr_std`。MR thesis に必要な extension / z-score 系 trigger を直接捕捉している。`app.py:3253-3363,8766+ (INLINE):3262`, `app.py:3253-3363,8766+ (INLINE):3263`, `app.py:3253-3363,8766+ (INLINE):3264`, `app.py:3253-3363,8766+ (INLINE):3267`, `app.py:3253-3363,8766+ (INLINE):3270` |
| 3 (timing window) | LOOKAHEAD | Signal feature が現在 `row["vwap"]`、現在 `entry`、`df["Close"]`/`df["vwap"]` の `.tail(50)` を使い、同じ bar の終値・VWAP を signal と entry reference に混ぜる。さらに active-hour gate は `bar_time` ではなく `datetime.now(timezone.utc)` を使うため、historical/live evaluation の時刻基準が signal bar と一致しない。グローバルコメントでも「同バー多重発火」と「multiple evaluate()」が停止理由に明記されており、bar dedup 欠落リスクは実害化済み。`app.py:3253-3363,8766+ (INLINE):87`, `app.py:3253-3363,8766+ (INLINE):89`, `app.py:3253-3363,8766+ (INLINE):90`, `app.py:3253-3363,8766+ (INLINE):3260`, `app.py:3253-3363,8766+ (INLINE):3262`, `app.py:3253-3363,8766+ (INLINE):3263`, `app.py:3253-3363,8766+ (INLINE):3300`, `app.py:3253-3363,8766+ (INLINE):8769`, `app.py:3253-3363,8766+ (INLINE):8771`, `app.py:3253-3363,8766+ (INLINE):8772`, `app.py:3253-3363,8766+ (INLINE):8806` |
| 4 (filter coherence) | BREAKS | Slope flat gate、ADX hard block、active hours、reclaim confirmation、MR anti-trend penaltyは、VWAP 回帰が機能しやすい低トレンド・reclaim 局面に寄せるため概ね STRENGTHENS。だが HTF Hard Block は `htf_agreement == "bull"` で SELL MR を、`htf_agreement == "bear"` で BUY MR を拒否するため、VWAP 2σ の counter-trend fade tail を hard cut する。これは MA filter on MR strategy -> BREAKS、HMM regime gate on edge tail -> BREAKS と同型の filter incoherence。`app.py:3253-3363,8766+ (INLINE):3278`, `app.py:3253-3363,8766+ (INLINE):3284`, `app.py:3253-3363,8766+ (INLINE):3289`, `app.py:3253-3363,8766+ (INLINE):3292`, `app.py:3253-3363,8766+ (INLINE):3297`, `app.py:3253-3363,8766+ (INLINE):3300`, `app.py:3253-3363,8766+ (INLINE):3306`, `app.py:3253-3363,8766+ (INLINE):3309`, `app.py:3253-3363,8766+ (INLINE):3323`, `app.py:3253-3363,8766+ (INLINE):3326`, `app.py:3253-3363,8766+ (INLINE):3357` |
| 5 (stop/TP geometry) | MISALIGNED | Daytrade 側は VWAP を TP 目標にせず generic `calc_sl_tp_v3(...)` へ委譲している。Scalp 側は BUY で `SL = entry - 0.5ATR`, `TP = entry + 1.2ATR`、SELL で逆向きの固定距離なので R:R は 1.2 / 0.5 = 2.4R。MR の自然 geometry は「mean まで戻る前に切らない wide stop + TP は mean」であり、現行は tight stop と mean 非連動 TP になっている。`app.py:3253-3363,8766+ (INLINE):3361`, `app.py:3253-3363,8766+ (INLINE):8837`, `app.py:3253-3363,8766+ (INLINE):8838`, `app.py:3253-3363,8766+ (INLINE):8841`, `app.py:3253-3363,8766+ (INLINE):8842` |
| 6 (pair-regime fit) | FORCED | `pairs: ALL` に対して、実装上の pair 差分は confidence boost/penalty だけで、trigger threshold、session、VWAP sigma window、stop/TP は pair 別に calibration されない。コード上は JPY crosses を boost、EURGBP を penalty しており、ALL 一括適用は forced。per-pair: USDJPY=FIT, EURJPY=FIT, GBPJPY=FIT, EURUSD=FORCED, GBPUSD=FORCED, EURGBP=FORCED, その他=FORCED。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | `demo_trades.db` の `demo_trades.entry_type='vwap_mean_reversion'` は 0 rows。`knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite` は chart pattern 用 table で strategy column を持たない。tier-master の force_demoted 行は EV columns だけで、Wilson lower / PF / WF folds / Bonferroni-adjusted p / Kelly fraction は揃わない。N/WR/EV だけで採否判断しない `feedback_partial_quant_trap.md` 基準では decision-grade evidence 不足。下表参照。 |

## Axis 8: failure mode 診断

`vwap_mean_reversion` は Tier 3 (FORCE_DEMOTED) なので failure mode 診断対象。破綻軸は Axis 3 / Axis 4 / Axis 5。Axis 2 の VWAP 2σ extension trigger は thesis と整合しているため、思想そのものは棄却しない。

最大の実害は Axis 3。停止コメントが示すとおり、同一 bar の multiple evaluate による連続発火と live 負 edge が既に発生している。次に Axis 4 の HTF Hard Block が、MR が取りたい counter-trend extension を削る。さらに Axis 5 で TP が VWAP mean ではなく ATR 固定になり、SL も 0.5ATR と狭いため、mean 到達前の noise で切られやすい。

再設計案は、trigger 本体は維持し、signal feature を確定済み bar のみで計算して next-bar / next-tick execution に固定すること。HTF hard direction block は削除し、代わりに ADX/slope を soft score または no-trade threshold として検証する。TP は VWAP、または VWAP までの距離が cost 未満なら entry 拒否に変更し、SL は 2σ 外側または recent swing + ATR buffer に置く。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

Trigger は `_vmr_dev < -2σ -> BUY` / `_vmr_dev > +2σ -> SELL` のまま残す。これはコードから導ける thesis と整合しており、最初に直す対象ではない。

優先修正は timing、filter、stop/TP の 3 点。コードレベルでは、`_vmr_dev_series` と signal 判定を現在 bar 除外の `df.iloc[:-1]` 相当に寄せ、entry は次 bar/tick fill として記録する。bar timestamp ごとの dedup key を `symbol + tf + strategy + bar_time` で持ち、同一 bar 再発火を拒否する。HTF Hard Block は削除し、`_vmr_slope_norm <= 0.3` と `ADX < 22` は v2 cohort として残すが、HTF trend direction による BUY/SELL veto は pre-register から外す。

Exit は scalp の `0.5ATR / 1.2ATR` 固定をやめ、TP を VWAP 方向の mean target に合わせる。`abs(vwap - entry)` が round-trip cost と最低距離を満たさない場合は TP を伸ばさず no-trade にする。SL は entry 側の 2σ 外側、または直近 swing + ATR buffer に置き、mean 到達前に切られにくい MR geometry として再検証する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: local audit DB `demo_trades.db` に `entry_type='vwap_mean_reversion'` row が 0 件。task input の tier-master 365d BT EV も `—` | audit DB query; task input |
| Win rate | INSUFFICIENT_EVIDENCE: audit DB に対象 row なし。historical wiki には live N=10/WR=40.0% 記載があるが、今回指定の tier-master/audit DB decision metrics ではない | audit DB query; `knowledge-base/wiki/strategies/vwap-mean-reversion.md` |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N と wins が audit DB / tier-master から復元不可 | audit DB query; `knowledge-base/wiki/tier-master.md:58` |
| PF | INSUFFICIENT_EVIDENCE: tier-master force_demoted 行は EV columns のみで PF 欄なし | `knowledge-base/wiki/tier-master.md:58` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: exact `vwap_mean_reversion` ALL force_demoted cell の WF folds>=3 は tier-master/audit DB に無し | tier-master / audit DB search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: code reason string は `Bonferroni p<0.001` を表示するが、tier-master/audit DB に raw p、family size、adjusted p の decision record が無い | `app.py:3253-3363,8766+ (INLINE):3339`, `app.py:3253-3363,8766+ (INLINE):3341` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: WR と payoff または trade-level PnL が audit DB / tier-master から復元不可 | audit DB query; tier-master |
