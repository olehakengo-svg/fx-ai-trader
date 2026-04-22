# Daily Tier B Protocol — 仮説生成→候補→LIVE昇格の自動化手続き

**Created**: 2026-04-22
**Author**: Claude (quant-first mode)
**Status**: PRE-REGISTERED (実行前に確定した decision rule)
**Related**: `claude-harness-design.md`, `pre-registration-2026-04-21.md`, `auto-improvement-pipeline.md`

---

## 1. 目的

Claudeを **quant-workflow オーケストレータ** として組み込み、仮説生成→BT検証→pre-register→LIVE昇格のパイプラインを日次自動実行する。ただし **LIVE変更は必ず人間承認ゲート** を通す。

**達成したい状態**:
- 仮説発見サイクル = 1日 (現在の "人間が気付いた時" から脱却)
- LIVE変更頻度 = 週次 (現行運用と同じ、statistical rigor維持)
- α予算管理で多重検定バイアスを事前統制

## 2. 3層アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│ Tier A (daily): quant report + gate status              │
│   既存 daily_report.py を quant_readiness.py と統合      │
│   LIVE判断 = 人間                                        │
├─────────────────────────────────────────────────────────┤
│ Tier B-daily: 仮説生成 + BT検証 + candidate queueing    │
│   Claude生成 → 自動BT → α予算Gate → candidate.md        │
│   LIVE昇格しない (候補プールに追加のみ)                  │
├─────────────────────────────────────────────────────────┤
│ Tier B-weekly: candidate promotion審議                   │
│   5営業日連続 BT+Shadow 両方pass → pre-register PR生成   │
│   LIVE昇格判断 = 人間承認                                │
├─────────────────────────────────────────────────────────┤
│ Tier C (15min interval): 異常検知・通知                  │
│   spread spike / OANDA latency / session drift           │
│   判断せず通知のみ (人間が介入するか判断)                 │
└─────────────────────────────────────────────────────────┘
```

## 3. α予算配分 (pre-committed)

**月間 family-wise α = 0.05** を以下に事前配分:

| 用途 | 月間α予算 | 内訳 |
|---|---|---|
| Tier B-daily 探索 | 0.020 | 30日 × α=0.000667/day (当日テスト数で Bonferroni 分割) |
| Tier B-weekly 審議 | 0.020 | 4週 × α=0.005/week (より重い仮説用) |
| Tier C 異常起因の臨時仮説 | 0.005 | regime shift検出時の早期adaptation用 |
| Reserve | 0.005 | 月末にユーザー指名の仮説用 |

**消費ルール**:
- daily scan が 1日に M 個の候補を出したら、各候補は α=0.000667/M でBonferroni判定
- 月間budgetを使い切った場合、新規候補の pre-register は翌月まで stop (shadow観察のみ継続)
- `tools/alpha_budget_tracker.py` で月次状態管理、`knowledge-base/raw/alpha_budget/YYYY-MM.json` に保存

**重要**: α予算は **消費すれば尽きる**。これは多重検定バイアスの物理的上限で、LLMが仮説を量産しても緩和されない。

## 4. Tier B-daily 詳細

### 4.1 パイプライン

| 時刻 (UTC) | 処理 | 出力 |
|---|---|---|
| 00:00 | 前日 Live trade ingest (既存) | `/api/demo/trades` DB更新 |
| 00:30 | **仮説生成**: Claude が前日trade + shadow pool + anomaly feed を読む | `candidates/YYYY-MM-DD.json` (仮説配列) |
| 01:00 | 各仮説を **365d BT + WF 3-bucket** で検証 | `bt-results/candidates/YYYY-MM-DD/` |
| 01:30 | **Gate自動判定** (下記5条件) | pass/fail 分類 |
| 02:00 | Pass候補を `shadow_queue.jsonl` に追加 + `candidates/YYYY-MM-DD.md` 要約 | Discord通知 |

### 4.2 Gate判定 (全条件AND)

1. **PF > 1.3** (tp_m総和 / |sl_m総和|)
2. **Wilson 95% CI 下限 > BEV_WR** (pair別BEVテーブル参照)
3. **WF 3-bucket all positive** (regime遷移耐性、負bucket=1つでもあれば regime-dependent扱い)
4. **N ≥ 30** per WF bucket (小-N禁止ルール遵守、feedback_partial_quant_trap)
5. **Bonferroni corrected p < α_daily/M** (当日M候補で補正)

### 4.3 Pass後の扱い

**Pass候補は即LIVE昇格しない**。以下の追加観察期間:
- Shadow mode で5営業日稼働 (モジュール実装は `is_shadow=True` フラグ)
- 5営業日のShadow EV/WR drift が BT期待値から σ以内を確認
- drift OK → Tier B-weekly審議にエスカレーション

### 4.4 Fail候補の扱い

- 1回のfailでは捨てない (N不足の可能性)
- `shadow_queue.jsonl` に "shadow_only" タグで追加
- 次週のBTスキャンで再評価 (N蓄積による合格待ち)
- 3週連続failならqueue除外

## 5. Tier B-weekly 詳細

### 5.1 パイプライン (毎週日曜 UTC 12:00)

| Step | 処理 | 出力 |
|---|---|---|
| 1 | Candidate pool から "5営業日連続pass" を抽出 | promotion候補リスト |
| 2 | 各候補の **Kelly fraction** (full + Half) 計算 | ロットサイズ根拠 |
| 3 | **Walk-Forward再検証** (前週分のLive 込みで再走) | drift確認 |
| 4 | Pre-register document 自動生成 | `pre-registration-YYYY-WW.md` |
| 5 | GitHub PR作成 (LIVE gateは人間承認) | PR link → Discord |

### 5.2 Pre-register の binding基準

PR本文に必ず含める (post-hoc bias排除):
- **LIVE昇格条件**: `Live N ≥ 20 AND Live EV > Wilson下限` (事前固定)
- **LIVE降格条件**: `Live N ≥ 30 AND Live EV < BT期待値 - 1σ` (事前固定)
- **監視期間**: 30日 (延長禁止、lesson-extend-trial遵守)

### 5.3 人間承認のチェックリスト

PR reviewer (=ユーザー) は以下を確認:
- [ ] 仮説の学術的根拠が書かれているか (maginical number禁止)
- [ ] α予算残が十分か (alpha_budget.json確認)
- [ ] 既存PAIR_PROMOTED戦略と相関が低いか (0.3以下目安)
- [ ] 4原則と矛盾しないか (static time block等)

## 6. Tier C 詳細

### 6.1 監視項目 (15分毎)

| Signal | 閾値 | アクション |
|---|---|---|
| Spread > 2×30d median | 当該ペア | Discord notify (BT-live divergence監視) |
| OANDA order latency > 3s | - | Discord notify (execution slippage risk) |
| Session drift (Tokyo volume < 50% median) | - | Discord notify (regime shift早期警告) |
| Live N停滞 (24h増加0件) | - | Discord notify (pipeline障害疑い) |

### 6.2 禁止事項

- **判断しない**: "降格推奨" 等の提案は Tier A/B の役割
- **自動変更しない**: パラメータ自動調整は lesson-reactive-changes 違反
- **仮説生成しない**: Tier B の α予算枠を使う場合のみ、`--from-anomaly` フラグで reserve枠消費

## 7. 失敗モード と セーフガード

| 失敗モード | セーフガード |
|---|---|
| Claude が幻覚仮説を量産 | α予算で物理上限、BT Gateで統計Gate |
| BT/Live divergence再発 | Shadow 5営業日観察、Walk-Forward 再検証 |
| α予算使い切り | 月次でreset、reserve枠は独立管理 |
| LLM API outage | daily scan スキップ、翌日リトライ (データ蓄積に害なし) |
| Cron実行失敗 | `check_kb_pipeline_health` が3日以上古いレポート検出で通知 |

## 8. 実装ファイル (新規)

```
tools/alpha_budget_tracker.py             # α予算管理
modules/claude_client.py                  # 共通Claude API client
scripts/daily_hypothesis_scan.py          # Tier B-daily 本体
scripts/weekly_promotion_gate.py          # Tier B-weekly 本体
scripts/anomaly_watcher.py                # Tier C 本体
scripts/agents/hypothesis-generator.md    # Claude prompt
knowledge-base/raw/alpha_budget/          # 月次α予算状態
knowledge-base/raw/candidates/            # 日次candidateプール
knowledge-base/raw/anomalies/             # Tier C event log
knowledge-base/wiki/analyses/candidates/  # 承認候補要約
```

## 9. Scheduling (Render Cron / Scheduled Tasks)

```yaml
# Tier A  — 既存 daily_report.py (4セッション × 日次)
# Tier B-daily — UTC 00:30 (daily_hypothesis_scan.py)
# Tier B-weekly — UTC 日曜 12:00 (weekly_promotion_gate.py)
# Tier C  — UTC */15 (anomaly_watcher.py)
```

## 9.1. Phase展開計画 (pre-committed)

リスクを段階的に開放するため、以下のPhase順序で有効化する。

### Phase 1 (2026-04-22〜): LLM不要・α予算ゼロ

**有効**:
- Tier C (anomaly watcher, 15min): spread/latency/session drift 通知
- Tier A (quant_gate_status, daily UTC 00:20): gate + α予算 要約をDiscordに通知
- Alpha budget monthly reset

**無効** (render.yaml でコメントアウト):
- Tier B-daily
- Tier B-weekly

**成功基準**:
- 7日間 Tier C が false alert <3件/日
- Tier A レポートが daily_report.py と整合
- α予算 state file が月初reset される

### Phase 2 (Phase 1 成功後、目安 2026-05-01〜): LLM仮説生成 dry-run

**追加有効** (手動実行のみ、cron OFF):
- `python3 scripts/daily_hypothesis_scan.py --dry-run` を人間がトリガ
- 7日間で仮説JSONを累積 → 人間review

**成功基準** (Phase 3開放条件):
- 幻覚率 <30% (仮説内容がKB知見と整合)
- 既存PAIR_PROMOTED 戦略との重複 <30%
- academic_basis の品質 (著者+年の実在性) 90%以上
- α予算尚未消費 (dry-runは消費しない)

### Phase 3 (Phase 2 成功後): BT bridge 完全実装

**前提実装**:
- `run_bt_for_hypothesis()` で仮説 → 一時strategy file 生成 (strategy-dev agent 委譲)
- 365d BT + WF 3-bucket auto-split
- PF, Wilson CI, Bonferroni p値 計算

**有効化**:
- Tier B-daily cron (UTC 00:30)
- Tier B-weekly cron (日曜 UTC 12:00)

### Phase 4 (Phase 3 成功後、目安 2026-06-01〜): 本格運用

30日運用レビュー (§10 指標) 合格後、以下検討:
- candidate queue のBT再走頻度UP (現 1回/日 → 2回/日)
- α予算再配分 (実消費率に応じて)
- 新カテゴリ追加 (e.g. macro-event-driven hypotheses)

---

## 10. 評価指標 (プロトコル自体の成功/失敗判定)

**30日後レビュー** (2026-05-22) で以下を確認:

| 指標 | 目標 | 失敗時アクション |
|---|---|---|
| α予算消費率 | 70-100% | <50%なら仮説生成が弱い、>100%なら Bonferroni 破綻 |
| LIVE昇格数 | 2-5件 | 0件ならpipeline機能せず、>10件なら Gate緩すぎ |
| 昇格後のLive EV vs BT | -1σ以内 | 外れたら divergence報告、pipeline再設計 |
| False positive率 | <20% | 超過したらα予算再配分 |

**失敗判定** = 3指標以上が目標外 → プロトコル改訂 or ロールバック。

---

## Appendix A: クオンツファースト原則との整合

本プロトコルは以下の制約を遵守:
- ✅ pre-register (§5.2): LIVE変更前に binding基準確定
- ✅ Bonferroni (§3): α予算で family-wise error制御
- ✅ WF 3-bucket (§4.2): regime遷移耐性
- ✅ Wilson CI (§4.2): 小-N bias補正
- ✅ Kelly (§5.1): ロットサイズ根拠
- ✅ 小-N禁止 (§4.2): N≥30 per bucket

feedback_partial_quant_trap の5要素を全て満たす。
