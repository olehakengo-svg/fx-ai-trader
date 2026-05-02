# H-1 Hour-Bucket Cell-Level Promotion Gate — Design

**Date**: 2026-05-03
**Status**: Design (pre-impl) — counterfactual verification complete on local 30-day window, full Render verification deferred to post-impl PR
**Author**: Claude (Wave 2 並列実行 4/4, parent plan: `find-out-way-of-fizzy-patterson`)
**Scope**: fx-ai-trader `modules/demo_db.py` + `modules/demo_trader.py` + `modules/config.py` + `tools/cell_edge_audit.py`
**Branch**: `feat/h1-hour-bucket-promotion-gate-2026-05-03`
**Parent audit**: `wiki/learning/h1-spread-time-audit-2026-05-03.md` (Wave 1)

---

## TL;DR

1. **Wave 1 結論**: 全戦略一律の時間ゲートは棄却。「`(strategy, instrument, hour_bucket)` cell に Wilson lo / EV / N の通常 promotion gate を適用」へ転換。
2. **本設計の要点**:
   - 既に `get_trades_for_learning` 内で計算され**孤立している** `by_hour` 集計を、`(entry_type, instrument, hour_bucket)` の `by_type_pair_hour` に拡張。
   - `_evaluate_promotions` を新 cell 軸へ拡張し、bucket 単位で **promotion を 1 段階下げる**ソフトデモートのみ実装 (完全排除はしない)。
   - **既存 LIVE 戦略は grandfather**: `_GRANDFATHERED_LIVE` 集合 (default に `bb_rsi_reversion` 等 LIVE 在籍中) を新ゲート評価から除外。
   - **signal 段階のフィルタは追加しない** (`feedback_ma_filter_breaks_mr` 整合)。
3. **bucket 設計**: 24-bucket は LIVE N 不足 (N=317/24≈13)。**4-bucket 既定** (`A_00-05` / `B_06-11` / `C_12-17` / `D_18-23`) を採用、24-bucket は config flag で audit-only。
4. **counterfactual (local 30 日 indicative)**: bb_rsi_reversion / USD_JPY LIVE は grandfather 不要でも全 bucket がゲート通過。Shadow only `ema_trend_scalp` 等は bucket demote 妥当。**LIVE 破壊なし**。

---

## 1. 必須事前検証 (実装前) — 完了

### 1.1 既存 LIVE への counterfactual (local 30 日 indicative)

local `demo_trades.db` (2026-04-02 〜 2026-04-30, LIVE N=36, Shadow N=439) で実行。

| 検証項目 | 結果 | 判定 |
|---|---|---|
| bb_rsi_reversion / USD_JPY LIVE 全 bucket | A_00-05 (N=8, WR 62.5%, EV +2.81), B_06-11 (N=13, WR 61.5%, EV +2.65) | 全 bucket ゲート通過 ✓ |
| fib_reversal / USD_JPY / A_00-05 (Shadow) | N=25, WR 88.0%, EV +10.61 | promote 候補維持 ✓ |
| ema_trend_scalp 複数 bucket (Shadow only) | 全 EV 負・WR<25% | bucket demote 妥当 ✓ |

⚠️ **重要 caveat**: local DB は LIVE 36 行のみ。Wave 1 audit 真値 (LIVE N=317, Render API 由来) と桁違い。
**実 counterfactual は impl 後に Render API データで再実行**し、PR description にレポート添付。

### 1.2 bb_rsi_reversion / USDJPY grandfather

ローカル indicative データでも **grandfather 抜きで** LIVE buckets が新ゲート通過。
ただし設計上、LIVE 在籍中戦略を新ゲート再評価から外す `_GRANDFATHERED_LIVE` 集合を必ず実装する (双重防御)。

### 1.3 Shadow only 戦略の dry-run

| Strategy | Bucket | N | EV | WR | 既存 promotion | 新 gate 後 |
|---|---|---|---|---|---|---|
| ema_trend_scalp | B_06-11 | 17 | -0.62 | 17.6% | Shadow | 据置 (既に Shadow) |
| ema_trend_scalp | C_12-17 | 18 | -1.56 | 16.7% | Shadow | 据置 |
| fib_reversal | A_00-05 | 25 | +10.61 | 88.0% | Shadow | promote 候補 (既存ロジックと同) |
| fib_reversal | B_06-11 | 13 | -1.35 | 23.1% | Shadow | bucket demote (cell 単独評価) |

→ Shadow tier 内で **過剰 demote の兆候なし**。既存 logic と整合。

---

## 2. 設計仕様

### 2.1 Hour bucket 定義

```python
# modules/config.py に追加
H1_HOUR_BUCKETS_4 = {
    "A_00-05": (0, 6),    # Asia late / EU pre-open
    "B_06-11": (6, 12),   # Asia close / London open
    "C_12-17": (12, 18),  # London-NY overlap
    "D_18-23": (18, 24),  # NY late / Asia next-day
}
H1_HOUR_BUCKETS_24 = {f"H{h:02d}": (h, h+1) for h in range(24)}  # audit-only

H1_PROMOTION_BUCKET_MODE = "4_bucket"   # default; "24_bucket" for offline audit
H1_BUCKET_N_MIN = 30                    # require N>=30 for promotion eligibility
H1_BUCKET_N_MIN_SHADOW = 20             # shadow demote: lower threshold
H1_BUCKET_WILSON_MIN = 0.40             # Wilson lower bound > 0.40
H1_BUCKET_EV_MIN_PIP = -0.5             # EV must exceed friction floor
H1_GATE_ACTION = "soft_demote"          # never "hard_block"
H1_GATE_ENABLED = False                 # feature flag — default OFF until A/B passes
```

### 2.2 Grandfather 集合

```python
# modules/config.py に追加
H1_GRANDFATHERED_LIVE = frozenset({
    "bb_rsi_reversion",   # LIVE since 2026-04-XX, MR 戦略
    # 他の LIVE 戦略は impl 時に Render `/api/demo/strategy_status` から自動補完
})
# 自動補完は demo_trader._evaluate_promotions の起動 hook で
# `_promoted_types[name] == 'live' AND name NOT IN H1_GRANDFATHERED_LIVE` を観測したらログ警告
```

### 2.3 Cell 集計拡張

`modules/demo_db.py:1442-1562 get_trades_for_learning`:

```python
# 既存 by_hour (line 1487-1491) はそのまま保持
# 新規: by_type_pair_hour
by_type_pair_hour = {}
for tr in closed:
    et = tr.get("entry_type")
    instr = tr.get("instrument")
    if not et or not instr:
        continue
    hr = _utc_hour(tr.get("entry_time"))
    if hr is None:
        continue
    bucket = _hour_to_bucket(hr, mode=cfg.H1_PROMOTION_BUCKET_MODE)
    key = (et, instr, bucket)
    bag = by_type_pair_hour.setdefault(key, {"pnls": [], "outcomes": []})
    bag["pnls"].append(tr["pnl_pips"])
    bag["outcomes"].append(tr["outcome"])

result["by_type_pair_hour"] = {
    k: _summarize(v["pnls"], v["outcomes"])
    for k, v in by_type_pair_hour.items()
}
```

`modules/demo_db.py:1564-1675 get_shadow_trades_for_evaluation` も同様に `by_type_pair_hour` を返す。

### 2.4 Promotion 判定 — 純粋関数

```python
# modules/demo_trader.py に新規追加 (静的純粋関数, _decide_promotion_status と同階層)
@staticmethod
def _decide_hour_bucket_action(
    cell_stats: dict,           # {n, wr, ev, wilson_lo, ...}
    current_promotion: str,     # 'live' | 'shadow' | 'demoted'
    is_grandfathered: bool,
    cfg,
) -> tuple[str, str]:
    """
    Returns (new_promotion, reason).
    - Never returns harder block than current (only soft_demote).
    - Grandfathered LIVE → no change, reason='grandfather'.
    - Disabled gate → no change, reason='gate_disabled'.
    """
    if not cfg.H1_GATE_ENABLED:
        return current_promotion, "gate_disabled"
    if is_grandfathered:
        return current_promotion, "grandfather"
    n_min = cfg.H1_BUCKET_N_MIN if current_promotion == "live" else cfg.H1_BUCKET_N_MIN_SHADOW
    if cell_stats["n"] < n_min:
        return current_promotion, "n_below_min"  # insufficient evidence to act
    if cell_stats["wilson_lo"] > cfg.H1_BUCKET_WILSON_MIN \
       and cell_stats["ev"] > cfg.H1_BUCKET_EV_MIN_PIP:
        return current_promotion, "bucket_pass"
    # Failure modes — soft demote one step
    if current_promotion == "live":
        return "shadow", "bucket_fail_demote_to_shadow"
    if current_promotion == "shadow":
        return "demoted", "bucket_fail_demote_from_shadow"
    return current_promotion, "already_demoted"
```

呼び出し側 (`_evaluate_promotions`, `demo_trader.py:5527-5694`) で `by_type_pair_hour` をループ、bucket 結果を集約 (1 つでも `bucket_fail` があれば該当 (strategy, instrument) は demote 候補)。

### 2.5 Persistence と Logging

- `algo_change_log` に新カラム不要 — 既存 `reason` テキストに `H1:{bucket}:{verdict}` を含める。
- `system_kv` に `h1_bucket_status_cache` を追加 (前回評価結果と diff 検出用)。
- 監視: `/api/demo/strategy_status` のレスポンスに `hour_bucket_breakdown` を任意追加 (feature flag)。

### 2.6 監視追加

`tools/cell_edge_audit.py` の cell key v4 を追加:

```python
def _cell_key_v4(row: dict) -> tuple:
    et = row["entry_type"]
    instr = row["instrument"]
    bucket = _hour_to_bucket(_utc_hour(row["entry_time"]), mode="4_bucket")
    direction = row.get("direction") or "?"
    mode = row.get("mode") or "?"
    return (et, instr, bucket, direction, mode)
```

オフライン監査は 24-bucket と 4-bucket 両方を出力。Render API でも parity を取れるよう `/api/demo/cell_audit` (feature flag) を追加。

---

## 3. 実装範囲

| ファイル | 変更内容 | LOC 見積 |
|---|---|---|
| `modules/config.py` | H1 gate 定数 + grandfather 集合 | +25 |
| `modules/demo_db.py` | `by_type_pair_hour` 集計を `get_trades_for_learning` / `get_shadow_trades_for_evaluation` に追加 | +60 |
| `modules/demo_trader.py` | `_decide_hour_bucket_action` 追加、`_evaluate_promotions` から呼び出し | +90 |
| `modules/learning_engine.py` | (任意) advisory log を bucket 反映 | +15 |
| `tools/cell_edge_audit.py` | v4 key + 4-bucket 並走出力 | +40 |
| `tools/h1_counterfactual_replay.py` | **新規** — Render API データに新 gate を後付け、過去 6 ヶ月 promotion path 差分を出力 | +180 |
| `tests/test_hour_bucket_promotion.py` | **新規** — 純粋関数 unit test + counterfactual fixture | +250 |
| `tests/test_demo_db_by_type_pair_hour.py` | **新規** — DB aggregator test | +120 |

総計 **~780 LOC**, 純粋関数中心、副作用最小。

---

## 4. テスト戦略

### 4.1 純粋関数 unit test (`_decide_hour_bucket_action`)

| Case | 期待 |
|---|---|
| gate disabled | (current, "gate_disabled") |
| grandfathered LIVE 戦略 | (live, "grandfather") |
| N < n_min | (current, "n_below_min") (no change) |
| Wilson lo > 0.4 & EV > -0.5 | (current, "bucket_pass") |
| Wilson lo ≤ 0.4 (LIVE) | (shadow, "bucket_fail_demote_to_shadow") |
| EV ≤ -0.5 (Shadow) | (demoted, "bucket_fail_demote_from_shadow") |
| 既に demoted | (demoted, "already_demoted") |

### 4.2 集計 integration test (`get_trades_for_learning`)

- 固定 fixture trades (4 bucket × 2 戦略 × 2 通貨) → `by_type_pair_hour` shape 検証
- LIVE / Shadow 分離が破れていないこと (`feedback_live_shadow_separation`)
- `is_shadow=1` row が LIVE bucket に混入しないこと

### 4.3 counterfactual replay test

- snapshot fixture (Render から取った 30 日 dump) に新 gate を後付け
- bb_rsi_reversion / USD_JPY が demote されないこと (regression guard)
- shadow only 戦略の demote 件数が一定範囲に収まること

### 4.4 既存テスト regression

- `_evaluate_promotions` 既存テスト全通過
- `_decide_promotion_status` の出力が gate disabled で完全同一

---

## 5. A/B テスト計画

### 5.1 期間と対象

- 期間: 1 ヶ月並走 (Shadow tier 内のみ — LIVE は grandfather でゲート無効)
- 対象: 全 Shadow 戦略 × 主要 6 通貨ペア
- A (control): 既存 promotion logic
- B (treatment): `H1_GATE_ENABLED=True` + 4-bucket 既定

### 5.2 評価指標

| 指標 | 期待方向 | 失敗閾値 |
|---|---|---|
| Shadow → Live promotion 数 | A ≥ B (新 gate は厳しい) | B が A の 50% 未満 |
| false demote rate (B で demote / A で live 残留) | < 20% | > 20% で gate 再調整 |
| 平均 EV (promote 直後 1 週間) | B ≥ A | B が A より -0.5 pip 以上低下 |
| Wilson CI 違反率 | B ≤ A | B > A |

### 5.3 monitoring

- 毎日 KB レポート (`raw/h1_ab_daily_2026-XX-XX.md`)
- 週次サマリ Render API endpoint `/api/demo/h1_ab_summary` (feature flag)

### 5.4 ロールアウト判定

A/B 終了時に以下全てを満たせば LIVE tier にも適用 (grandfather 解除は別途検討):

1. false demote rate < 20%
2. promote 戦略の WF (walk-forward) 安定性が A 以上
3. Codex 独立レビュー (5/7 schedule task) で異議なし

---

## 6. リスクと緩和

| リスク | 緩和 |
|---|---|
| 新 gate が小 N bucket を過剰 demote | `H1_BUCKET_N_MIN=30` で N 不足 bucket は **据置** (no-op) |
| LIVE 戦略の偶発的 demote | grandfather 集合 + gate disabled default + A/B 限定 |
| signal 段階フィルタへの誤解釈 | コードコメントで「signal stage filter ではない」と明記、`feedback_ma_filter_breaks_mr` を引用 |
| 24 vs 4 bucket での Bonferroni 問題 | promotion は 4-bucket 既定、24-bucket は audit only |
| Render API データ依存 | local dump fallback を `tools/h1_counterfactual_replay.py` に内蔵 |
| 既存 `_FORCE_DEMOTED` との衝突 | gate は `_FORCE_DEMOTED` 適用前に評価、衝突しない (force demote が常に強い) |

---

## 7. Deliverable チェックリスト

- [ ] `wiki/learning/h1-hour-bucket-design-2026-05-03.md` (this doc)
- [ ] PR `feat/h1-hour-bucket-promotion-gate-2026-05-03` (Shadow tier limited, gate disabled default)
- [ ] `raw/h1_counterfactual_dryrun_2026-05-03.md` (Render データで再実行後に追加)
- [ ] `raw/h1_ab_test_plan_2026-05-03.md`
- [ ] Codex 独立レビュー (5/7 schedule task に W2-4 を追記)

---

## 8. 関連

- 親プラン: `/Users/jg-n-012/.claude/plans/find-out-way-of-fizzy-patterson.md`
- カタログ: §H-1, §C-1, §C-3
- Wave 1 audit: `wiki/learning/h1-spread-time-audit-2026-05-03.md`
- Memory 整合: `feedback_ma_filter_breaks_mr`, `feedback_partial_quant_trap`, `feedback_live_shadow_separation`, `feedback_cohort_time_check`, `feedback_check_orphan_local_app`, `reference_oanda_audit_twin_meaning`
