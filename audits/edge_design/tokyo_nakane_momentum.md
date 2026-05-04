---
strategy: tokyo_nakane_momentum
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

東京仲値 09:55 JST 前の USD/JPY 下落は仲値フロー前後の一時的な偏りであり、仲値後に BUY 方向へ短期リバーサルする、という session/fixing event-driven mean reversion thesis。コードは BUY 専用、Pre-fix 3 本の DOWN、Post-fix 陽線確認、月金除外を明示している。`strategies/daytrade/tokyo_nakane_momentum.py:2`, `strategies/daytrade/tokyo_nakane_momentum.py:15`, `strategies/daytrade/tokyo_nakane_momentum.py:16`, `strategies/daytrade/tokyo_nakane_momentum.py:17`, `strategies/daytrade/tokyo_nakane_momentum.py:20`, `strategies/daytrade/tokyo_nakane_momentum.py:21`, `strategies/daytrade/tokyo_nakane_momentum.py:22`, `strategies/daytrade/tokyo_nakane_momentum.py:23`, `strategies/daytrade/tokyo_nakane_momentum.py:24`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Reversal thesis に対し、trigger は `prefix_move_pip = (Close_00:30 - Open_00:00) * pip_mult < -2.0` で pre-fix DOWN を要求し、`ctx.entry > ctx.open_price` で現在足の陽線を要求する。条件式は `PreFixMove <= -min_down_pip ∧ CurrentClose > CurrentOpen -> BUY` で、DOWN→BUY の event-driven MR を直接捕捉している。`strategies/daytrade/tokyo_nakane_momentum.py:43`, `strategies/daytrade/tokyo_nakane_momentum.py:44`, `strategies/daytrade/tokyo_nakane_momentum.py:45`, `strategies/daytrade/tokyo_nakane_momentum.py:48`, `strategies/daytrade/tokyo_nakane_momentum.py:49`, `strategies/daytrade/tokyo_nakane_momentum.py:90`, `strategies/daytrade/tokyo_nakane_momentum.py:95`, `strategies/daytrade/tokyo_nakane_momentum.py:107`, `strategies/daytrade/tokyo_nakane_momentum.py:108`, `strategies/daytrade/tokyo_nakane_momentum.py:109`, `strategies/daytrade/tokyo_nakane_momentum.py:111`, `strategies/daytrade/tokyo_nakane_momentum.py:112`, `strategies/daytrade/tokyo_nakane_momentum.py:128`, `strategies/daytrade/tokyo_nakane_momentum.py:129` |
| 3 (timing window) | OK | Signal は現在足の `Close > Open` 確認後に生成されるため、bar-close 前提なら look-ahead は見えない。Pre-fix bars は `_offset` で現在足より前の 00:00/00:15/00:30 を参照する。ただし entry window が 00:45-01:15 を許可しており、bar timestamp が open-time か close-time かで「post-fix 最初の 15m 足」の解釈が揺れる。strategy 内に per-bar dedup はないため、同一 bar 多重 evaluate は execution/router 側の dedup 前提。`strategies/daytrade/tokyo_nakane_momentum.py:37`, `strategies/daytrade/tokyo_nakane_momentum.py:39`, `strategies/daytrade/tokyo_nakane_momentum.py:40`, `strategies/daytrade/tokyo_nakane_momentum.py:41`, `strategies/daytrade/tokyo_nakane_momentum.py:72`, `strategies/daytrade/tokyo_nakane_momentum.py:76`, `strategies/daytrade/tokyo_nakane_momentum.py:77`, `strategies/daytrade/tokyo_nakane_momentum.py:82`, `strategies/daytrade/tokyo_nakane_momentum.py:90`, `strategies/daytrade/tokyo_nakane_momentum.py:91`, `strategies/daytrade/tokyo_nakane_momentum.py:92`, `strategies/daytrade/tokyo_nakane_momentum.py:128`, `strategies/daytrade/tokyo_nakane_momentum.py:129`, `strategies/daytrade/tokyo_nakane_momentum.py:194` |
| 4 (filter coherence) | BREAKS | `ctx.is_jpy` は thesis の USD/JPY 実需フローを JPY cross 全体へ広げるため中立ではなく薄い破壊要因。月曜/金曜除外と時間帯 gate は fixing thesis を強化する。問題は HTF hard filter で、コードコメントは「HTFはsoft penalty/bonusのみ」「15m EMA方向は使わない」としながら、実装は `agreement == "bear"` で BUY を完全 block する。仲値リバーサルが HTF bearish tail に出やすいなら、HMM regime gate same-trap と同じく edge tail を削る。MA filter on MR strategy -> BREAKS の先行例にも近く、総合判定は BREAKS。`strategies/daytrade/tokyo_nakane_momentum.py:21`, `strategies/daytrade/tokyo_nakane_momentum.py:25`, `strategies/daytrade/tokyo_nakane_momentum.py:60`, `strategies/daytrade/tokyo_nakane_momentum.py:61`, `strategies/daytrade/tokyo_nakane_momentum.py:64`, `strategies/daytrade/tokyo_nakane_momentum.py:65`, `strategies/daytrade/tokyo_nakane_momentum.py:67`, `strategies/daytrade/tokyo_nakane_momentum.py:72`, `strategies/daytrade/tokyo_nakane_momentum.py:77`, `strategies/daytrade/tokyo_nakane_momentum.py:119`, `strategies/daytrade/tokyo_nakane_momentum.py:122`, `strategies/daytrade/tokyo_nakane_momentum.py:123`, `strategies/daytrade/tokyo_nakane_momentum.py:124`, `strategies/daytrade/tokyo_nakane_momentum.py:125`, `strategies/daytrade/tokyo_nakane_momentum.py:126`, `strategies/daytrade/tokyo_nakane_momentum.py:175`, `strategies/daytrade/tokyo_nakane_momentum.py:177`, `strategies/daytrade/tokyo_nakane_momentum.py:181`, `strategies/daytrade/tokyo_nakane_momentum.py:182` |
| 5 (stop/TP geometry) | ALIGNED | MR/fixing reversal に対し、SL は pre-fix 安値の外側 `prefix_low - ATR*0.3`、TP は pre-fix 下落幅の 50% 戻し `entry + max(abs(prefix_move)*0.5, ATR*1.5)`。R:R は `reward / risk = max(0.5*abs(prefix_move), 1.5*ATR) / (entry - prefix_low + 0.3*ATR)` で動的。小さい pre-fix 下落では `1.5ATR` の最低 TP がやや遠いが、構造上は「下落の半値戻しを取り、安値割れで撤退」なので thesis と整合する。`strategies/daytrade/tokyo_nakane_momentum.py:51`, `strategies/daytrade/tokyo_nakane_momentum.py:52`, `strategies/daytrade/tokyo_nakane_momentum.py:53`, `strategies/daytrade/tokyo_nakane_momentum.py:54`, `strategies/daytrade/tokyo_nakane_momentum.py:96`, `strategies/daytrade/tokyo_nakane_momentum.py:107`, `strategies/daytrade/tokyo_nakane_momentum.py:108`, `strategies/daytrade/tokyo_nakane_momentum.py:137`, `strategies/daytrade/tokyo_nakane_momentum.py:138`, `strategies/daytrade/tokyo_nakane_momentum.py:140`, `strategies/daytrade/tokyo_nakane_momentum.py:141`, `strategies/daytrade/tokyo_nakane_momentum.py:142` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。Thesis はコードコメント上 USD/JPY の輸入企業ドル買いに依存するが、実装は `ctx.is_jpy` で JPY cross 全般を許可し、task scope は ALL。USD/JPY は FIT、それ以外の JPY cross と non-JPY は FORCED/blocked。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 365d BT EV は prompt input で `—`。KB の strategy page も 365d BT data not available。55d 参考値は N=10, WR=70.0%, EV=+0.086 と古い USD_JPY BT の WR=100%, EV=+1.719 があるが、PF/WF folds/Bonferroni-adjusted p/Kelly が揃わない。`feedback_partial_quant_trap.md` 準拠では N/WR/EV だけでは不可。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT | コードコメントは USD/JPY 専用・BUY 専用、構造メカニズムは本邦輸入企業のドル買い需要。`strategies/daytrade/tokyo_nakane_momentum.py:15`, `strategies/daytrade/tokyo_nakane_momentum.py:17`, `strategies/daytrade/tokyo_nakane_momentum.py:21` |
| EURJPY / GBPJPY / other JPY crosses | FORCED | 実装は `ctx.is_jpy` だけで通すため JPY cross へ拡張されるが、コード内 thesis は USD/JPY fixing flow であり、cross-specific な仲値フロー根拠はない。`strategies/daytrade/tokyo_nakane_momentum.py:60`, `strategies/daytrade/tokyo_nakane_momentum.py:61` |
| EURUSD / GBPUSD / other non-JPY | FORCED / BLOCKED | `not ctx.is_jpy` で不発。ALL scope に対して実際は non-JPY を対象外にしている。`strategies/daytrade/tokyo_nakane_momentum.py:60`, `strategies/daytrade/tokyo_nakane_momentum.py:61`, `strategies/daytrade/tokyo_nakane_momentum.py:62` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow であり、tier-master 365d evidence が `—` のため昇格根拠は不足している。破綻軸は Axis 4 が主、Axis 6 と Axis 7 が補助。Axis 2 の DOWN→BUY trigger と Axis 5 の pre-fix low / half-retracement geometry は thesis と概ね整合する。一方で、USD/JPY 固有の実需フローを `ctx.is_jpy` で JPY cross 全体へ広げ、さらに HTF bearish agreement を hard block しているため、event-driven MR の tail を削る可能性が高い。

再設計案は「USDJPY-only thin fixing reversal」。`ctx.is_jpy` gate を USDJPY 明示 gate に置換し、HTF bear hard return は削除して score penalty へ降格する。entry は post-fix bar-close に固定し、00:45/01:00/01:15 の timestamp 解釈を backtest/router と合わせて 1 回だけ発火する形にする。既存 BT は不要条件だが、採用判断には 365d USDJPY-only で Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly を出し直す必要がある。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想と中核 trigger は復活 candidate として残す価値がある。最優先は filter/pair gate の修正で、`ctx.is_jpy` を USDJPY 明示条件へ狭め、`_agreement == "bear"` の hard block を削除または `score -= 0.5` 程度の soft penalty に落とす。これはコードコメントの「HTF は soft penalty/bonus」「実需フローはトレンドに逆行可能」とも整合する。

次に timing を明文化する。仲値 00:55 UTC 後の最初の確定 15m 足だけを対象にし、bar timestamp が open-time なら 00:45 足 close、close-time なら 01:00 足に統一する。strategy 内または router 側で `(strategy, pair, bar_time)` の dedup を保証し、同一 bar の再評価で複数 candidate が出ないことを監査条件に入れる。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 365d tier-master: `—`; 55d reference: JPY N=10; old USD_JPY DT 55d comparison: N not listed, PnL +3.44 / EV +1.719 implies very small N | prompt input; `knowledge-base/wiki/analyses/system-reference.md:45`; `knowledge-base/raw/bt-results/bt-grand-audit-2026-04-12.md:45`; `knowledge-base/raw/bt-results/bt-v85-new-edges-2026-04-12.md:20` |
| Win rate | 365d tier-master: `—`; 55d reference: 70.0%; old USD_JPY DT 55d comparison: 100% | prompt input; `knowledge-base/wiki/analyses/system-reference.md:45`; `knowledge-base/raw/bt-results/bt-grand-audit-2026-04-12.md:45`; `knowledge-base/raw/bt-results/bt-v85-new-edges-2026-04-12.md:20` |
| Wilson lo (95%) | 39.68% derived from 55d reference N=10, WR=70.0%; 365d decision-grade Wilson unavailable | derived from `knowledge-base/wiki/analyses/system-reference.md:45` |
| PF | INSUFFICIENT_EVIDENCE: strategy-specific PF unavailable in tier-master/audit DB; only portfolio-level PF exists and cannot be assigned to this strategy | prompt input; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:10`; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:11` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: strategy-specific walk-forward folds unavailable | prompt input; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:10`; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:11` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: no strategy-specific multiple-testing adjusted p found in tier-master/audit DB | prompt input; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:10`; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:11` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: PF / avg win-loss unavailable, so Kelly cannot be defensibly derived from N/WR/EV only | prompt input; `knowledge-base/wiki/analyses/system-reference.md:45`; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:10`; `knowledge-base/wiki/strategies/tokyo-nakane-momentum.md:11` |
