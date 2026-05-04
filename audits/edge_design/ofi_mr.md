---
strategy: ofi_mr
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

3分窓の OFI が過去分布から見て極端で、同時に価格が micro-VWAP から OFI 方向へ乖離した場合、その偏りを流動性枯渇・在庫不均衡として fade し、micro-VWAP 方向への短期平均回帰を取る。コード内でも「大きすぎる偏り -> 反転」であり「偏り発生 -> 順張り」ではないと明示されている。`strategies/micro_scalp/ofi_mr.py:5`, `strategies/micro_scalp/ofi_mr.py:7`, `strategies/micro_scalp/ofi_mr.py:8`, `strategies/micro_scalp/ofi_mr.py:10`, `strategies/micro_scalp/ofi_mr.py:18`, `strategies/micro_scalp/ofi_mr.py:20`, `strategies/micro_scalp/ofi_mr.py:30`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `z_ofi = (ofi_now - mu) / sigma`、`abs(z_ofi) >= z_thresh`、かつ `z_ofi > 0 and displacement > 1.0ATR -> SELL` / `z_ofi < 0 and displacement < -1.0ATR -> BUY`。OFI 極端値と VWAP 乖離を同方向に要求してから逆方向へ fade するため、MR thesis の extension/overshoot 条件を直接捕捉している。`strategies/micro_scalp/ofi_mr.py:85`, `strategies/micro_scalp/ofi_mr.py:91`, `strategies/micro_scalp/ofi_mr.py:101`, `strategies/micro_scalp/ofi_mr.py:105`, `strategies/micro_scalp/ofi_mr.py:106`, `strategies/micro_scalp/ofi_mr.py:110`, `strategies/micro_scalp/ofi_mr.py:112`, `strategies/micro_scalp/ofi_mr.py:127`, `strategies/micro_scalp/ofi_mr.py:129` |
| 3 (timing window) | LOOKAHEAD | OFI 分布は `bars[-(DIST_BARS + W):-W]` で現在窓を除外しており、この部分は OK。一方で signal 用の `current_window = bars[-W:]` と `vwap = self._vwap(current_window)` は `bars[-1]` を含み、その同じ `bars[-1].close` を `mid` として entry を作る。コードコメントは VWAP/ATR を現在バー除外と書くが、VWAP は現在バーを含むため、bar-close 確定後に同一 close で入る latency 楽観が残る。戦略クラス内に bar timestamp dedup 状態もないため、live 側が抑止しない場合は同一バー再評価で多重 signal のリスクがある。`strategies/micro_scalp/ofi_mr.py:39`, `strategies/micro_scalp/ofi_mr.py:41`, `strategies/micro_scalp/ofi_mr.py:86`, `strategies/micro_scalp/ofi_mr.py:91`, `strategies/micro_scalp/ofi_mr.py:110`, `strategies/micro_scalp/ofi_mr.py:111`, `strategies/micro_scalp/ofi_mr.py:139`, `strategies/micro_scalp/ofi_mr.py:140`, `strategies/micro_scalp/ofi_mr.py:150`, `strategies/micro_scalp/ofi_mr.py:151` |
| 4 (filter coherence) | STRENGTHENS | `sigma <= 0` と `atr <= 0` は NEUTRAL。`abs(z_ofi) >= z_thresh` と OFI 方向・VWAP 乖離方向の一致確認は trigger 本体。`atr >= 2.0 * entry_slip_price` の cost-aware volatility gate は、VWAP 到達距離がコストに負ける低ボラ局面を捨てるため STRENGTHENS。MA filter on MR strategy や HMM regime gate same trap と同型の trend/regime hard block はこの実装には無い。`strategies/micro_scalp/ofi_mr.py:101`, `strategies/micro_scalp/ofi_mr.py:102`, `strategies/micro_scalp/ofi_mr.py:105`, `strategies/micro_scalp/ofi_mr.py:106`, `strategies/micro_scalp/ofi_mr.py:114`, `strategies/micro_scalp/ofi_mr.py:115`, `strategies/micro_scalp/ofi_mr.py:118`, `strategies/micro_scalp/ofi_mr.py:121`, `strategies/micro_scalp/ofi_mr.py:127`, `strategies/micro_scalp/ofi_mr.py:129` |
| 5 (stop/TP geometry) | MISALIGNED | SL は直近 `W` 秒の極値に `0.3ATR` と cost buffer を加えた外側、TP は micro-VWAP 目標だが `max(VWAP距離, min_tp_pips)` で最低 8pips に引き上げられる。さらに `tp_dist >= 0.7 * sl_dist` を要求するため、平均回帰の自然目標である VWAP が近い局面ほど拒否され、通過時も TP が VWAP を越えることがある。MR としては target は mean、stop は mean 到達前の noise を許容する構造が自然だが、現設計は minimum TP と R:R gate が micro-VWAP 回帰 thesis を歪めている。`strategies/micro_scalp/ofi_mr.py:31`, `strategies/micro_scalp/ofi_mr.py:32`, `strategies/micro_scalp/ofi_mr.py:135`, `strategies/micro_scalp/ofi_mr.py:136`, `strategies/micro_scalp/ofi_mr.py:142`, `strategies/micro_scalp/ofi_mr.py:144`, `strategies/micro_scalp/ofi_mr.py:146`, `strategies/micro_scalp/ofi_mr.py:152`, `strategies/micro_scalp/ofi_mr.py:154`, `strategies/micro_scalp/ofi_mr.py:156`, `strategies/micro_scalp/ofi_mr.py:161`, `strategies/micro_scalp/ofi_mr.py:162` |
| 6 (pair-regime fit) | FORCED | `pairs: ALL` に対し、strategy 側は `window_sec=180` と `z_thresh=2.0` の単一パラメータで、pair/session/spread regime ごとの calibration を持たない。OFI proxy と retail cost は pair 依存が強いので、ALL 一括適用は forced。per-pair evidence が audit DB / tier-master に無いため、`USD_JPY=FORCED`, `EUR_USD=FORCED`, `GBP_USD=FORCED`, `EUR_JPY=FORCED`, `GBP_JPY=FORCED`, `EUR_GBP=FORCED`。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master の 365d BT EV は `—`。`knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite` は `chart_pattern_outcomes` のみで strategy 列がなく、`ofi_mr` 行は存在しない。Wilson lower / PF / WF folds / Bonferroni-adjusted p / Kelly fraction を audit DB または tier-master から復元できないため、N/WR/EV 以前に decision-grade evidence が不足している。下表参照。 |

## Axis 8: failure mode 診断

`ofi_mr` は Tier 2 (Shadow) / phase0_shadow で、tier-master 由来の 365d BT EV は欠落している。設計破綻の主軸は Axis 3 と Axis 5。Axis 2 の OFI 極端値 + VWAP 乖離 + fade trigger は thesis と整合しており、Axis 4 も trend hard block を持たないため壊していない。

再設計案は、まず timing を closed-bar / next-bar execution に固定すること。`current_window` と VWAP 計算を signal 判定用には `bars[-W-1:-1]` へずらし、entry reference は `bars[-1].close` ではなく次 tick/次 bar の約定として扱う。次に stop/TP を MR geometry に戻し、TP は原則 `vwap` まで、`min_tp_pips` で VWAP を越える場合は entry を拒否する。R:R gate は固定 `0.7` ではなく、cost-adjusted expected reversion distance と Wilson/PF 検証に移すべき。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

Trigger の骨格は維持する。`abs(z_ofi) >= z_thresh` と `displacement` 同方向確認は、OFI 過剰偏りが価格に反映された後に fade するという thesis を直接表しているため、最初に壊すべき箇所ではない。

優先修正は timing と stop/TP geometry。コードレベルでは、signal features を `feature_window = bars[-W-1:-1]` で計算し、`signal_bar = bars[-1]` close 確定後、execution は next tick/bar fill として記録する variant を pre-register する。TP は `tp = vwap` を基本とし、`abs(vwap - entry) < min_tp_pips * pip` なら TP を伸ばさず `return None` にする。SL は直近極値 + cost buffer を維持してよいが、`tp_dist >= 0.7 * sl_dist` の固定 gate は MR の mean target を歪めるため、redesign BT では削除または別 cohort として比較する。

実データ evidence が無いため、この redesign は即昇格ではなく Shadow 再検証候補。必要 BT は pair 別・session 別の実 tick/1秒足 30日以上、最低 N>=30、Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction 付きで、現行版と closed-bar mean-target 版を同一データで比較する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE: audit DB に `ofi_mr` strategy 行なし。tier-master も N 未記載 | `knowledge-base/raw/bt-results/s6-w1p0-production-2026-05-04.sqlite`; `knowledge-base/wiki/tier-master.md` |
| Win rate | INSUFFICIENT_EVIDENCE: audit DB / tier-master から復元不可 | same sources |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE: N と wins が無いため算出不可 | same sources |
| PF | INSUFFICIENT_EVIDENCE: gross profit/loss または PF 欄なし | same sources |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: ofi_mr の walk-forward folds 記録なし | tier-master / audit DB search |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: ofi_mr の hypothesis family / raw p / correction count 記録なし | tier-master / audit DB search |
| Kelly fraction | INSUFFICIENT_EVIDENCE: WR と payoff または trade-level PnL が無いため算出不可 | same sources |
