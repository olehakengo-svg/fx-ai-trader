---
date: 2026-05-03
task: 20260503-2225-r2-implement-14cell-stop-pair-demoted-lock
verdict: ACCEPT (Codex deliverable: 規律遵守) / **BLOCKED** (実装) — pair_promoted 衝突
rule: R2
gate: Gate 0 復帰実装 — 衝突解消 task で再走必要
---

# R2 14-Cell pair_demoted LOCK Implementation — Codex 正しく BLOCKED 判定

## Verdict (Codex deliverable)

**ACCEPT** — Codex は task §6 (`pair_promoted` 編集禁止) を厳密に解釈、衝突発見時に partial 実装を拒否。`tier_integrity_check.py --check` で ERROR=0 を維持、ambiguous lifecycle state 発生を防止。`feedback_label_empirical_audit` 規律遵守の模範。

## Verdict (実装)

**BLOCKED** — 14 target cell のうち 2 cell が既に `pair_promoted` 内で、scope 制約下で実装不可能。

## Blocking conflicts

- `vix_carry_unwind × USD_JPY` (PAIR_PROMOTED かつ TRUE_LIVE で N=7 EV=-6.04 Wilson_lo=8.22% Kelly=-0.41 = **明らかな bleeding**)
- `bb_squeeze_breakout × USD_JPY` (PAIR_PROMOTED かつ TRUE_LIVE で N=9 EV=-1.40 Wilson_lo=12.06% Kelly=-0.64 = **明らかな bleeding**)

これは **tier-state 自体の矛盾**: PAIR_PROMOTED tier 表記と Live 出血実績が両立。promotion 判断時の BT が現状の Live 摩擦を反映していなかった可能性。

## Already in pair_demoted (no-op)

- bb_rsi_reversion × EUR_USD
- engulfing_bb × USD_JPY
- engulfing_bb × EUR_USD
- stoch_trend_pullback × USD_JPY

## Would append if conflicts resolved (10 cells)

- vwap_mean_reversion × GBP_USD
- vix_carry_unwind × USD_JPY ⚠️ promoted conflict
- sr_channel_reversal × USD_JPY
- bb_rsi_reversion × USD_JPY
- session_time_bias × GBP_USD
- bb_squeeze_breakout × USD_JPY ⚠️ promoted conflict
- vol_surge_detector × USD_JPY
- v_reversal × USD_JPY
- trend_rebound × USD_JPY
- sr_channel_reversal × EUR_USD

## Drift check (14 cell 全て DEMOTE_OK)

snapshot `/tmp/live-trades-20260503.json` (DNS 失敗で fresh fetch 不可、SSOT と同じ) で再計算、14 cell 全て:
- WR < BEV_WR + 5pp
- Wilson_lo < BEV_WR
- Kelly raw < 0

→ statistical evidence は demote 維持。aggregate raw Kelly 推定 -0.1326 → -0.0028、MC60d 86.5% → 0.9%。

## Roadmap impact

Gate 0 救済 PR 化 path A は **conflict resolution task** で 1 段階増えた。実装サイクル:
1. **R2 conflict resolution** (本 verdict 受け新規 task) — `pair_promoted` から 2 cell 移動 + その他 10 cell 追加を 1 commit で
2. 7d Live N 蓄積 + 再 audit で aggregate Kelly 改善幅実測
3. raw Kelly +0.003 不足を埋める R2 拡張 (task #3 既起草) を必要なら投入

## Next task

**`20260503-2240-r2-14cell-conflict-resolution-2026-05-03`** (新規起草必要):
1. `tier-master.json` の `pair_promoted` から `vix_carry_unwind × USD_JPY`, `bb_squeeze_breakout × USD_JPY` を削除
2. 同 commit で `pair_demoted` に 12 cell (上記 10 + 2 conflict-resolved) 追加
3. `tier_integrity_check.py --write` で `tier-master.md` 自動再生成
4. Claude review 後 PR merge → Render auto-deploy で 14-cell OANDA 転送停止 87% 即時止血

Codex の REJECT/BLOCKED 判定は **次 task の scope 拡大要求**として正しく機能した。
