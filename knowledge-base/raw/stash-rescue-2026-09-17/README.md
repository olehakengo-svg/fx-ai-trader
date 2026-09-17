# stash-rescue-2026-09-17 — 検疫アーカイブ (引用前に estimand 監査必須)

## これは何か

ローカル main checkout の `git stash` 183 件 (2026-04-22〜09-10 起票) の triage で発見された、
**一度も origin に到達していない** wiki 系文書 28 件の検疫保管場所。
元パスは `knowledge-base/` 以下の相対パスをそのまま保持している
(例: `wiki/decisions/structural-flow-tier-2026-05-04.md`)。

## ⚠️ 引用ルール (重要)

これらの文書は **KB 正史の一部になったことが無い**。大半は 2026-04-27〜05-18 の
stash 嵐期の WIP で、その後の canon (w4 shadow redesign / BE-Trail ablation 発見 /
tier 再編) によって **superseded または falsified された可能性が高い**。

- **verdict / tier / EV 数値の引用は禁止** — 引用したい場合は
  `feedback_audit_past_verdicts_2026_08_05` (過去 verdict 自体を疑え) に従い、
  原本 decision doc + 当時のハーネスコードで estimand 一致を監査してから
- 特に BE/Trail 込みの Python BT 数値 (05 月期) は
  `project_be_trail_inflates_python_bt_wr` (WR +20pp 水増し) の対象
- ここから wiki/ 本体へ昇格させる場合は個別に判断し、昇格理由をコミットに記録する

## 同時に実パスへ復活させたもの (このコミット)

- `raw/audits/` `raw/bt-results/` `raw/cell_deepdive/` `raw/trade-logs/` の stash 専有分
  (アーカイブ性データ、canon リスクなし)
- `wiki/sessions/` の欠落 session log 8 件 (時系列作業記録)
- `wiki/lessons/` の欠落 lesson 5 件 (institutional memory、うち 2 件は現行 KB から
  [[wikilink]] 参照されていた = 破損リンクの実体)
- `raw/hunt_events/*.jsonl` へ stash 専有 shadow 行 16,201 行を line-union (4原則#3)

## 検疫対象 (28 件)

- `wiki/decisions/` 13 件 — 未 ratify の判断文書 (cad1 / fib_reversal / fx-option-skew /
  holdout-isolation / kb-update / kelly-recompute / memory-system-audit /
  pre-reg-regime-cascade / r2-tier1-hour-bucket / s6-w2a / s6-w2b / structural-flow-tier /
  vfo1-phase1-qlike / vol-forecast-overlay / vwap-session-revert)
- `wiki/analyses/` 4 件 — all-strategies-sanity ×2 / macd-1m-scalp-v3 / pyr-mechanism-live-audit
- `wiki/learning/` 6 件 — b3-turtle-soup / fx-fundamentals ×3 / sft1-research-summary /
  wave2-phase-gamma-prime
- `wiki/strategies/` 3 件 — mqe_gbpusd_fix / rsk_gbpjpy_reversion / vsg_jpy_reversal
  (現行の w4 shadow redesign queue と同名の戦略。カード再整備するならここを種に新規監査で)

## 出所の完全性

stash 183 件は drop 前に全 SHA を `refs/stash-archive/` (ローカル) に保全済み。
本 README 起票セッション: 座礁分救済 PR #264 (2026-09-17)。
