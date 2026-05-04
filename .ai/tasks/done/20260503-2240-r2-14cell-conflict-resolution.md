---
id: 20260503-2240-r2-14cell-conflict-resolution
title: R2 14-cell pair_promoted ↔ pair_demoted conflict resolution + LOCK 実装
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T22:40:00+0900
roadmap_gate: Gate 0 復帰実装 (87% 即時止血)
rule: R2
prerequisite_decision:
  - 2026-05-03-2230-r2-14cell-blocked-pair-promoted-conflict (BLOCKED 先行 task)
  - 2026-05-03-1815-r2-strategy-instrument-counterfactual (TRUE_LIVE re-run, 14-cell SSOT)
  - 2026-05-03-1722-gate-progression-audit (REJECT, Live N=917 baseline)
---

## 0. なぜ今このタスクか

直前の R2 14-cell pair_demoted LOCK 実装 task (`20260503-2225-r2-implement-14cell-stop-pair-demoted-lock`) が **BLOCKED** で帰還:

- 14 cell 中 2 cell が **既に `pair_promoted` 内に存在**:
  - `vix_carry_unwind × USD_JPY` (TRUE_LIVE N=7, EV=-6.04, Wilson_lo=8.22%, Kelly raw=-0.41)
  - `bb_squeeze_breakout × USD_JPY` (TRUE_LIVE N=9, EV=-1.40, Wilson_lo=12.06%, Kelly raw=-0.64)
- 旧 task は `pair_promoted` 編集禁止だったため partial 実装拒否
- これは **tier-state 矛盾** (PROMOTED tier でありながら Live 大幅出血)

本 task は scope を拡張して `pair_promoted` から 2 cell 削除 + `pair_demoted` に 12 cell 追加を 1 commit で行い、**tier_integrity_check ERROR=0** を維持する。

counterfactual 推定: aggregate raw Kelly -0.1326 → -0.0028, MC60d 86.5% → **0.9%** (87% 出血停止)。

## 1. 仮説

**H1**: 2 cell を `pair_promoted` から削除 + 12 cell を `pair_demoted` に追加すると `tier_integrity_check.py --check` が ERROR=0 / WARN=0 で pass。

**H2**: `tier_master.json` の単一 commit 編集で Render auto-deploy 後 OANDA bridge gate (`modules/demo_trader.py:5009` の `pair_demoted` 判定) が 14 cell すべてを SHADOW dispatch に切替。`app.py`/`modules/`/`strategies/` 編集不要。

**H3**: post-merge 7d 後の Live audit で aggregate raw Kelly が -0.1854 → -0.10 程度まで改善 (counterfactual -0.0028 と完全一致は期待しないが方向は確実)。

## 2. 対象データ / 分離

| 用途 | 出典 | 混入禁止 |
|---|---|---|
| 編集対象 | `knowledge-base/wiki/tier-master.json` の `pair_promoted` (2 削除) + `pair_demoted` (12 追加) | `elite_live` / `force_demoted` / `strategy_lot_boost` 不変 |
| Drift check | TRUE_LIVE bucket = `is_shadow=0 AND oanda_trade_id != '' AND status='CLOSED' AND outcome IN (WIN/LOSS/BE) AND instrument NOT IN (XAU_USD, EUR_GBP) AND entry_time >= '2026-04-08'` | `is_shadow=1`, FLAG_DRIFT, XAU/EURGBP, mode フィルタ暗黙適用禁止 |
| Integrity | `tools/tier_integrity_check.py` 実行で `tier-master.md` 自動再生成 | 手動編集 |

## 3. 14 cell 確定 list (counterfactual SSOT, immutable)

`r2-strategy-instrument-counterfactual-2026-05-03.md` の Min demote set rank 1-14:

```python
DEMOTE_LOCK_14 = [
    ("vwap_mean_reversion", "GBP_USD"),
    ("vix_carry_unwind", "USD_JPY"),         # ★ pair_promoted から削除必要
    ("sr_channel_reversal", "USD_JPY"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("session_time_bias", "GBP_USD"),
    ("bb_squeeze_breakout", "USD_JPY"),       # ★ pair_promoted から削除必要
    ("bb_rsi_reversion", "EUR_USD"),          # already in pair_demoted (no-op)
    ("vol_surge_detector", "USD_JPY"),
    ("engulfing_bb", "USD_JPY"),              # already in pair_demoted (no-op)
    ("engulfing_bb", "EUR_USD"),              # already in pair_demoted (no-op)
    ("v_reversal", "USD_JPY"),
    ("trend_rebound", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("stoch_trend_pullback", "USD_JPY"),     # already in pair_demoted (no-op)
]
```

実 append 対象: 10 cell (already 4 cell)。pair_promoted 削除: 2 cell。Net change: +10 / -2。

## 4. ACCEPT / REJECT / NEEDS_MORE 条件

- **ACCEPT**: 2 cell 削除 + 10 cell 追加が単一 commit で完了 AND `tier_integrity_check --check` ERROR=0 WARN=0 AND drift check で 14 cell 全て DEMOTE_OK 維持
- **CHANGES_REQUESTED**: 上記の partial subset 達成、明確な改善経路あり
- **REJECT**: integrity check で ERROR 検出、または drift で 14 cell の 1 つ以上が WR > BEV になっている (= 損失停止根拠を失った)

## 5. Scope

Codex MAY change:

- `knowledge-base/wiki/tier-master.json` (`pair_promoted` から 2 cell 削除, `pair_demoted` に 10 cell 追加)
- `knowledge-base/wiki/tier-master.md` (auto-regenerate via `tier_integrity_check.py --write`)
- `.ai/runs/<run-dir>/final.md`
- 単一 commit を作成 (push しない、Claude review 後に手動 push)

Codex MAY NOT change:

- `app.py`, `modules/`, `strategies/`, `tools/` の既存ファイル
- `tier-master.json` の `elite_live`, `force_demoted`, `pair_promoted` (★ 14 cell 以外), `pair_demoted` (★ 既存 21 cell 以外を勝手に削らない), `strategy_lot_boost`
- `wiki/decisions/` の既存ファイル (本 task の decision doc 新規作成は OK)
- `.env`, OANDA secrets, production credentials, `live_ng_cells` SQLite
- 既存未コミット変更

## 6. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive 節, KB 運用ルール)
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (14-cell SSOT)
- `.ai/decisions/2026-05-03-2230-r2-14cell-blocked-pair-promoted-conflict.md` (Claude review、本 task の根拠)
- `wiki/decisions/gate-progression-audit-2026-05-03.md` (Live aggregate baseline)
- `knowledge-base/wiki/tier-master.json` (現状, 14 cell 衝突箇所)
- `tools/tier_integrity_check.py` (regenerator)
- `modules/demo_trader.py:5009` (`pair_demoted` gate 確認、編集なし)
- `wiki/lessons/index.md` の `feedback_ma_filter_breaks_mr`, `feedback_label_empirical_audit`, `feedback_live_shadow_separation`

## 7. Acceptance Criteria

- [ ] `tier-master.json` の `pair_promoted` から `vix_carry_unwind × USD_JPY`, `bb_squeeze_breakout × USD_JPY` の 2 cell が削除されている
- [ ] `tier-master.json` の `pair_demoted` に 10 cell が追加されている (重複追加なし)
- [ ] `python3 tools/tier_integrity_check.py --check` exit 0, ERROR=0, WARN=0
- [ ] `tier-master.md` が `--write` で自動再生成され、表記と JSON が一致
- [ ] Drift check 14 cell 全て DEMOTE_OK 維持 (前回 task 表と完全一致)
- [ ] 単一 commit 作成、message に `rule:R2 type:lock cells:14 ref:r2-counterfactual-2026-05-03 conflict-resolved` を含む
- [ ] `app.py`, `modules/`, `strategies/`, `tools/` の既存ファイル touched=0
- [ ] `.ai/runs/<run-dir>/final.md` に: status, files changed, drift table, integrity check 出力, commit hash, residual risks, 次タスク

## 8. Verification Commands

```bash
# 1. Drift check (14 cell 全て DEMOTE_OK 維持確認)
python3 tools/r2_strategy_instrument_counterfactual.py --dry-run --trades /tmp/live-trades-20260503.json --mc-iterations 1000

# 2. Integrity check
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check

# 3. JSON / MD 整合確認
diff <(python3 -c "import json; d=json.load(open('knowledge-base/wiki/tier-master.json')); print(sorted(d.get('pair_demoted', [])))") /tmp/expected_pair_demoted.txt

# 4. Git diff 確認 (touched files が許可リストのみ)
git diff --name-only HEAD~1..HEAD

# 5. modules/strategies/app.py 不変確認
git diff HEAD~1..HEAD -- app.py modules/ strategies/ tools/ | wc -l  # → 0 expected
```

## 9. Codex Instructions

これは **Rule 2 Fast & Reactive** タスク。365日 BT 不要、損失停止が目的。

**重要な scope 拡張**: 旧 task で `pair_promoted` 編集を禁止したのは保守的設計だったが、tier-state 矛盾 (PAIR_PROMOTED で Live 出血) は **tier-state 自体の bug** であり、解消が必要。memory `feedback_label_empirical_audit` 通り、Live 実測 (TRUE_LIVE Kelly raw -0.41 / -0.64) を tier promotion の上位真実とする。

`feedback_success_until_achieved` 通り、partial 実装で closure 短絡禁止。conflict 全解消で 14 cell LOCK 完了が ACCEPT。

PR は **本タスクで作成しない**。1 commit を作成、push しない。Claude review (司令塔) 後に user が push 判断。

DNS 失敗で Render snapshot 取れない場合、`/tmp/live-trades-20260503.json` フォールバック (前回 task と同じ SSOT)。

最終レポートには status, files changed, 14 cell drift table 再掲, integrity check 出力, commit hash, 7d 後の post-merge audit 計画, 次タスク。

ACCEPT 達成後の次タスク:
- 7d 後 `r2-postmerge-audit-2026-05-10.md` (Live N 蓄積後の aggregate Kelly 改善幅実測)
- 並行 `r2-tier1-hour-bucket-extension` (queue 既起草、+0.003 Kelly 補完)
- 並行 `a3-simple-sr-channel-reversal-shadow-register` (Gate 0 ACCEPT 確認後)
