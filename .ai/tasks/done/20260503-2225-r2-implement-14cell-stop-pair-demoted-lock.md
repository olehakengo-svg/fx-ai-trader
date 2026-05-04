# R2 Implement: 14-Cell STOP_OANDA via tier-master `pair_demoted` LOCK

- **rule**: R2 (Fast & Reactive — 損失停止 / pair demotion)
- **created**: 2026-05-03T22:25+09:00
- **owner**: Codex (helper task; Claude reviews PR)
- **prereqs**: 2026-05-03 R2 strategy×instrument counterfactual (NEEDS_MORE_EVIDENCE proposal)

## 1. 背景 / なぜ今このタスクか

直近 24h の監査結果:

- `r2-strategy-instrument-counterfactual-2026-05-03.md`: 14-cell STOP_OANDA 提案で aggregate raw Kelly が `-0.1326 → -0.0028` (約 85% 出血停止)。verdict NEEDS_MORE_EVIDENCE は **集計 Kelly が 0 を跨がない** ことに由来する非ACCEPT であり、出血セル個別の demote 自体は Wilson_lo<BEV の強い負エッジ証拠を持つ Rule 2 GO 案件。
- `tier1-live-edge-audit-2026-05-03.md`: Tier 1 LIVE 5 cell は N<30 で発火わずか 7 trade、aggregate Live/OANDA 736 trade のうち 729 trade が **non-Tier1 出血セル**。これらの出血セルが counterfactual の 14 cell に集約される。
- システム実値: `DD=40.65%`, `TRUE_LIVE N=371`, `raw Kelly=-0.69` (cell 集計) / `-0.1854` (Live/OANDA 集計)。Gate 0 を保つには即時の bleeding cap が必要。
- 既存実装: `tier_master.json` には `pair_demoted` キーが既に存在し (現 21 cell)、`modules/demo_trader.py:5009` で `_block_reason = f"pair_demoted({instrument})"` の OANDA gate が稼働中。**pair_demoted に 14 cell を追記するだけで OANDA 転送が止まる**。

このタスクは **counterfactual 提案 (LOCK proposal) を実 LOCK に確定**させる Rule 2 implementation。BT は不要 (Rule 2 は Live N≥10 or 既存統計で即断可)。集計 Kelly>0 への到達は別タスク (R1 新セル追加 / Tier1 戦略再評価) で扱う。

## 2. 仮説 / 検証対象

- **H1 (主仮説)**: `pair_demoted` に counterfactual 14 cell を追加すると、新規 OANDA 転送のうちこれら 14 cell に該当する trade はゲートで `pair_demoted(...)` 理由でブロックされ、Live (`is_shadow=0 AND oanda_trade_id != ''`) 母集団から消える。
- **H2 (副仮説)**: 既存の Live KEEP_SIG (Bonferroni-significant 黒字) cell は**触らない**。すなわち本タスクは出血を止めるのみで edge 源を奪わない。
- **H3 (運用仮説)**: 7d 後の再 audit で aggregate raw Kelly が `-0.1854 → -0.1` 程度まで改善 (counterfactual 推定 -0.0028 と完全一致は期待しない: Live trade はシャドウより母数が動く)。

## 3. 対象データ / データ分離

- **対象**: 本番 SSOT である `knowledge-base/wiki/tier-master.json` の `pair_demoted` 配列のみ。`elite_live` / `force_demoted` / `pair_promoted` / `strategy_lot_boost` 等は不変。
- **検証データ**: 直近 Live snapshot (`https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000`) を `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status='CLOSED' AND instrument NOT IN ('XAU_USD','EUR_GBP') AND entry_time >= '2026-04-08'` で TRUE_LIVE バケットに絞り、14 cell が **当該バケット内** で raw Kelly < 0 かつ Wilson_lo < BEV_WR のままであることを再確認 (drift check)。
- **データ分離 (絶対遵守)**:
  - `is_shadow=1` を Live 統計に**絶対混入させない**。
  - FLAG_DRIFT (`is_shadow=1 AND oanda_trade_id != ''`) を Live と SHADOW のどちらにも数えない。
  - **XAU_USD / EUR_GBP は集計から除外**。
  - mode フィルタを暗黙適用しない (旧 N=29 バグ回避)。

## 4. 確定 demote 対象 14 cell (counterfactual SSOT)

`r2-strategy-instrument-counterfactual-2026-05-03.md` 表の rank 1〜14 を copy-pasteable list として固定する:

```
[
  ["vwap_mean_reversion", "GBP_USD"],
  ["vix_carry_unwind", "USD_JPY"],
  ["sr_channel_reversal", "USD_JPY"],
  ["bb_rsi_reversion", "USD_JPY"],
  ["session_time_bias", "GBP_USD"],
  ["bb_squeeze_breakout", "USD_JPY"],
  ["bb_rsi_reversion", "EUR_USD"],
  ["vol_surge_detector", "USD_JPY"],
  ["engulfing_bb", "USD_JPY"],
  ["engulfing_bb", "EUR_USD"],
  ["v_reversal", "USD_JPY"],
  ["trend_rebound", "USD_JPY"],
  ["sr_channel_reversal", "EUR_USD"],
  ["stoch_trend_pullback", "USD_JPY"]
]
```

実装ロジック:

1. 上記 14 tuple を読み込む。
2. `tier-master.json` 既存 `pair_demoted` と diff:
   - 既存に含まれる cell は **no-op** (idempotent)。
   - 既存に無い cell のみを append (順序保持・重複なし)。
3. 同 14 cell が `pair_promoted` または `elite_live` に存在しないか整合チェック。**衝突あればハードフェイル** (人間判断必要)。
4. KEEP_SIG 10 cell (counterfactual §6 表) を **新規に touch しないこと** を test で証明:
   - `bb_rsi_reversion × GBP_USD`, `bb_squeeze_breakout × EUR_USD`, `dt_bb_rsi_mr × USD_JPY`, `ema_trend_scalp × EUR_USD`, `fib_reversal × EUR_USD`, `fib_reversal × USD_JPY`, `stoch_trend_pullback × EUR_USD`, `trend_rebound × EUR_USD`, `vol_momentum_scalp × USD_JPY`, `vol_surge_detector × EUR_USD`
5. ELITE_FLAG (`session_time_bias × GBP_USD`) は 14 cell に含まれているので追加対応不要。

## 5. 統計条件 (採用判定の境界)

- **Pre-LOCK drift check (Rule 2 の即断条件)**: 14 cell の各々で TRUE_LIVE bucket 再計算後、
  - N >= 5 (counterfactual 当時から減少している場合は flag だけ立て、demote は強行する)
  - Wilson 95% lower bound (WR) < BEV_WR (per-pair, friction-analysis.md の値) **または** raw Kelly < 0
  - **両方とも反転している cell が 1 つ以上**あれば LOCK を中断し人間判断へエスカレーション (counterfactual SSOT が陳腐化した signal)。
- **Bonferroni 整合**: 既存 counterfactual の m=24, α'=0.002083 を踏襲。本タスクで再計算は不要。
- **OOS / WF**: 不要 (Rule 2)。

## 6. ACCEPT / NEEDS_MORE_EVIDENCE / REJECT 条件

- **ACCEPT (LOCK 完了)**:
  - tier-master.json `pair_demoted` に 14 cell 全てが含まれる (新規 + 既存 = 14)。
  - integrity check (`tools/tier_integrity_check.py --check`) ERROR=0。
  - tests pass。
  - production deploy 後、`/api/demo/status` の `force_demoted_count` が増分し、新規 OANDA trade が当該 14 cell から発火していないことを 30 分以内に確認 (Live trade `block_reason='pair_demoted(...)'` ログ確認)。
- **NEEDS_MORE_EVIDENCE**:
  - Pre-LOCK drift check で 1〜3 cell が反転している (N が極端に減った / Wilson_lo が BEV を超えた)。当該 cell のみスキップして残りを LOCK し、スキップ cell は次セッションで再判定。
- **REJECT (LOCK 中断)**:
  - 4 cell 以上が反転 (counterfactual SSOT が陳腐化)。LOCK は実行せず、counterfactual の再走 (refreshed Live snapshot) を新規タスクで提案して終了。
  - tier-master.json と `pair_demoted` 既存値 の整合違反 (例: `pair_promoted` と衝突する cell が現れた)。

## 7. 月利 100% ロードマップへの寄与

- ロードマップ Gate 0 (DT LIVE + Scalp SENTINEL + AVOID 全停止) の **AVOID 部分の実体化**。
- Gate 1 (Aggregate Kelly > 0) には到達しないが、bleeding を 85% カットすることで現 DD=40.65% の更なる悪化を防ぎ、Gate 1 達成のための「分母」を温存する。
- KEEP_SIG 10 cell は無傷で、edge 源は失われない。

## 8. Scope (Codex MAY change)

- `knowledge-base/wiki/tier-master.json` (`pair_demoted` 配列に diff append のみ。ファイル全体 sort やキー並び替えは禁止)
- `knowledge-base/wiki/tier-master.md` (`tier_integrity_check.py --write` による自動再生成)
- `knowledge-base/wiki/decisions/r2-14cell-stop-lock-2026-05-03.md` (新規 LOCK 記録: diff cell list / drift check 結果 / verdict / next task)
- `tests/test_pair_demoted_lock_14cell.py` (新規 — 後述)
- `.ai/runs/<run-dir>/final.md`

## 9. Scope (Codex MAY NOT change)

- `app.py` のゲートロジック本体 (既存 `pair_demoted` チェックは稼働中、ロジック変更は禁止)
- `modules/demo_trader.py` (gate 既稼働、本タスクは config データ追加のみ)
- `modules/demo_db.py` (FORCE_DEMOTED shadow ロジックは別関心)
- `tier_master` の他キー (`elite_live` / `force_demoted` / `pair_promoted` / `scalp_sentinel` / `strategy_lot_boost` 等)
- `.env`, OANDA 秘密情報, 本番 OANDA 残高, 本番 DB スキーマ
- 既存未コミット変更 (working tree dirty file には触らない)
- KEEP_SIG 10 cell の lot / state
- `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (immutable)
- `wiki/decisions/tier1-live-edge-audit-2026-05-03.md` (immutable)

## 10. 禁止事項 (本番安全)

- OANDA API への直接送信は一切禁止。本タスクは config データ追加のみ。
- 本番 SQLite (`fx_ai_trader.db` / Render の永続化 DB) への直接書き込み禁止。
- `tier-master.json` の既存 `pair_demoted` cell を **削除しない** (今 demote 中の cell を un-demote しない)。
- `force_demoted` / `pair_promoted` / `elite_live` の編集禁止。
- `is_shadow` 値の SQL 直接更新禁止。
- 本タスクで Render 自動 deploy をトリガーする commit を作る場合、commit message に `rule:R2 type:lock cells:14` を明示。`--no-verify` 等の hook skip 禁止。

## 11. Required Reading

- `CLAUDE.md` (Rule 2 Fast & Reactive, KB 運用ルール厳密版)
- `knowledge-base/wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md` (本タスクの SSOT)
- `knowledge-base/wiki/decisions/tier1-live-edge-audit-2026-05-03.md` (補助 — Tier1 cells が non-target に対して N<<<1 である根拠)
- `knowledge-base/wiki/decisions/aggregate-kelly-decomposition-2026-05-03-corrigendum.md` (TRUE_LIVE bucket 定義の SSOT)
- `knowledge-base/wiki/analyses/friction-analysis.md` (per-pair BEV_WR)
- `~/.claude/projects/-Users-jg-n-012-test/memory/feedback_live_shadow_separation.md`
- `~/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md`
- `~/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md`
- `app.py:9828-9920` (tier_master 読込 / pair_demoted 適用ロジックの参照のみ)
- `modules/demo_trader.py:5000-5010` (`_block_reason='pair_demoted(...)'` ゲートの参照のみ)
- `tools/tier_integrity_check.py` (整合チェック)

## 12. Acceptance Criteria

- [ ] `tier-master.json` の `pair_demoted` 配列が 14 cell を全て含む (diff append、既存 21 cell は不変、合計 N≦35)
- [ ] `tier-master.json` の他キーは byte-level 不変 (`generated_at` 以外)
- [ ] `tools/tier_integrity_check.py --write` を実行して ERROR=0、warnings は documented (existing warnings は許容)
- [ ] `pytest tests/test_pair_demoted_lock_14cell.py -v` pass。test 内容:
  - (a) 14 cell の各 tuple が `pair_demoted` に含まれる
  - (b) KEEP_SIG 10 cell は `pair_demoted` に**含まれない**
  - (c) 14 cell のいずれも `pair_promoted` または `elite_live` に**含まれない**
  - (d) (strategy, instrument) tuple の重複が `pair_demoted` 全体で 0
  - (e) `force_demoted` リストは byte-level 不変
- [ ] `knowledge-base/wiki/decisions/r2-14cell-stop-lock-2026-05-03.md` (新規):
  - SSOT 引用: counterfactual doc 名 + sha
  - Pre-LOCK drift check 結果表 (14 cell × N/WR/Wilson_lo/Kelly, refreshed snapshot)
  - 既存 `pair_demoted` との diff (新規追加 cell list)
  - 衝突チェック結果 (`pair_promoted` / `elite_live` との非交差確認)
  - KEEP_SIG 10 cell が無傷であることの証拠
  - Verdict (ACCEPT / NEEDS_MORE_EVIDENCE / REJECT)
  - Next task (post-deploy monitor or refresh counterfactual)
- [ ] `.ai/runs/<run-dir>/final.md` に: status / changed files / verdict / aggregate Kelly counterfactual 推定 / pre-LOCK drift summary / next task
- [ ] `app.py` / `modules/` / `strategies/` / `.env` 編集 0 件
- [ ] commit を作成する場合、message は `rule:R2 type:lock cells:14 ref:r2-counterfactual-2026-05-03` を含む

## 13. Verification Commands

```bash
# 0. 一次データ取得 (refreshed Live snapshot for drift check)
curl -sS --max-time 60 "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000" \
  -o /tmp/live-trades-r2lock-$(date +%Y%m%d-%H%M).json

# 1. Pre-LOCK drift check (14 cell が依然 raw Kelly<0 を保持しているか)
python3 tools/r2_strategy_instrument_counterfactual.py --dry-run \
  --trades /tmp/live-trades-r2lock-*.json \
  --cells-only "vwap_mean_reversion:GBP_USD,vix_carry_unwind:USD_JPY,sr_channel_reversal:USD_JPY,bb_rsi_reversion:USD_JPY,session_time_bias:GBP_USD,bb_squeeze_breakout:USD_JPY,bb_rsi_reversion:EUR_USD,vol_surge_detector:USD_JPY,engulfing_bb:USD_JPY,engulfing_bb:EUR_USD,v_reversal:USD_JPY,trend_rebound:USD_JPY,sr_channel_reversal:EUR_USD,stoch_trend_pullback:USD_JPY"
# (--cells-only オプションが既存 CLI に無ければ、本タスクで足してよい — counterfactual 本体ロジックは触らない)

# 2. tier-master.json edit (manually or via small script — 14 cell append, idempotent)
#    実装は Codex が判断。jq を使う場合は元順序保持に注意。

# 3. integrity
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check  # ERROR=0 必須

# 4. tests
python3 -m pytest -q tests/test_pair_demoted_lock_14cell.py

# 5. (deploy 検証 — Codex は実行しない、Claude review 後に手動で)
# git commit + push -> Render auto-deploy -> 30 min 後:
# curl https://fx-ai-trader.onrender.com/api/demo/status | jq '.force_demoted_count, .pair_demoted_count'
# curl 'https://fx-ai-trader.onrender.com/api/demo/logs?limit=2000' | grep 'pair_demoted('
```

## 14. Codex Instructions

- 本タスクは **Rule 2 (Fast & Reactive) implementation**。集計 Kelly が 0 に届かなくても individual cell 出血証拠で即 LOCK 可。
- 必ず最初に **refreshed Live snapshot** で 14 cell の drift を確認 (counterfactual から数時間〜2 日経過しているため、N がゼロに崩れた cell は flag)。
- `feedback_label_empirical_audit` 遵守: 「コードを読めばこうだ」推測で進めず、Live snapshot の SQL 集計で 14 cell の現状況を実測する。
- `feedback_live_shadow_separation` 遵守: TRUE_LIVE bucket 定義 (§3 参照) を厳密に適用。Shadow / FLAG_DRIFT を絶対混入させない。
- `feedback_partial_quant_trap` 回避: drift check 表は N/WR/EV/Wilson_lo/PF/Kelly を全列出力。N と WR だけで判定しない。
- `feedback_codex_schema_hallucination` 回避: tier-master.json schema は §13 step 0 で実際に読んで確認した keys (`elite_live`, `force_demoted`, `pair_promoted`, `pair_demoted`, ...) のみ。Codex がスキーマを推測しないこと。
- `feedback_success_until_achieved` 遵守: pre-LOCK drift で予期せぬ反転を見つけても closure 短絡せず、§6 の REJECT/NEEDS_MORE_EVIDENCE 分岐で判断。
- `feedback_check_orphan_local_app.md` 遵守: 集計実行前に `pgrep -f app.py` を実行し、orphan があれば user に報告 (本タスクでは kill しない)。
- PR 作成は Codex が判断。commit を打つ場合は `rule:R2 type:lock cells:14` を必ず含める。Render auto-deploy が走るため、commit 前に必ず `tier_integrity_check --check` ERROR=0。
- 最終レポートに必ず含める: status, changed files, verdict, drift summary, KEEP_SIG 無傷確認, ELITE_FLAG (`session_time_bias × GBP_USD`) demote 完了確認, post-LOCK 推定 aggregate Kelly, residual risks, 次タスク (post-deploy 7d monitor / Tier1 H5 戦略再評価)。
- 報告は **必ず日本語**。
