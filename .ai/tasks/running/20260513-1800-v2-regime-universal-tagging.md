---
id: 20260513-1800-v2-regime-universal-tagging
title: "[V2 Regime Universal Tag] dow_regime と同 pattern で v2 (M15 binary) classifier を全 trade 入口に tag → composite cell 観測層完成"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T18:00:00+0900
roadmap_gate: "ユーザー提案 (2026-05-13) で Phase E を composite classifier design に再定義。dow_regime (H1 swing context) と v2_regime (M15 tactical) を **timeframe 役割分担** で組合せ、composite cell (3×2=6) で entry_type 毎に勝ち cell を実測探索する。本タスクは v2_regime tagging を universal observation layer に追加 (dow_regime と同 pattern)。"
rule: pre-reg
related:
  - knowledge-base/wiki/decisions/regime-gate-tier-a-2026-05-12.md
  - knowledge-base/wiki/decisions/regime-gate-phase-b25-2026-05-13.md
  - reports/regime_classifier_consensus/SUMMARY.md                   # 両 opinion 結論
  - modules/demo_db.py                                                # dow_regime と同パターンで拡張
  - modules/demo_trader.py                                            # signal hook
  - modules/regime_classifier.py                                      # 既存 v2 binary classifier
  - tools/dow_regime_backfill.py                                      # backfill 参考実装
  - feedback_shadow_first_quant_architecture
  - feedback_codex_mock_test_trap
---

# 0. 思想 (ユーザー提案)

> Dow はスイング (H1)、v2 は短期足 (M15)。Dow で長期判定、v2 で短期判定、その中での整合をとって勝てる cell を探すスキーム。

dow_regime + v2_regime の **timeframe 役割分担** で composite cell を構築:

| Long (H1 Dow) | Short (M15 v2) | 意味 |
|---|---|---|
| TRENDING | moderate_trend | Swing trend + tactical OK = high conviction |
| TRENDING | no_go | Trend だが entry bad |
| RANGING | moderate_trend | Range + tactical OK = MR opportunity |
| RANGING | no_go | Range + bad tactical |
| CHOP | moderate_trend | Unclear context + tactical window |
| CHOP | no_go | Skip |

# 1. 設計 (dow_regime と完全並行)

## 1.1 DB schema

`demo_trades` に **新カラム** を追加:

```sql
ALTER TABLE demo_trades ADD COLUMN v2_regime TEXT;
```

- 値域: `'moderate_trend'` / `'no_go'` / `NULL` (cache miss / 計算失敗)
- 命名: `v2_regime` = `modules/regime_classifier.py` v2 binary classifier の出力

## 1.2 add_trade signature 拡張

`modules/demo_db.py::open_trade` に追加 (commit c05a86b で dow_regime 追加した同箇所):

```python
def open_trade(self, ..., dow_regime: str | None = None, v2_regime: str | None = None, ...):
    ...
    conn.execute("""INSERT INTO demo_trades
        (..., dow_regime, v2_regime, ...) VALUES (..., ?, ?, ...)""",
        (..., dow_regime, v2_regime, ...))
```

## 1.3 signal 時点で classifier 呼出

`modules/demo_trader.py` の `_compute_dow_regime` helper の隣に `_compute_v2_regime` を追加:

```python
def _compute_v2_regime(self, instrument: str, entry_time) -> str | None:
    try:
        from modules.regime_classifier import classify_regime_binary  # or 既存関数名
        return classify_regime_binary(instrument, entry_time, tf='15m')
    except Exception as exc:
        self._add_log(f"[regime-tag/v2] failed: {exc}")
        return None
```

dow_regime と同箇所で呼出、`open_trade(..., dow_regime=..., v2_regime=..., ...)` で渡す。

**重要**:
- 既存 v2 classifier API を見て、正しい関数名・signature を確認すること
- 失敗時 None 保存、signal は block しない
- production behavior 無変更 (純観測層)

## 1.4 既存 trade の backfill

`tools/v2_regime_backfill.py` 新規 (dow_regime_backfill.py を雛形に):

```python
# 1) 過去全 trade を取得
# 2) entry_time + instrument で M15 v2 classifier を呼ぶ
# 3) UPDATE demo_trades SET v2_regime = ? WHERE trade_id = ?
# 4) dry-run mode default (--apply で実書込)
# 5) chunked processing (1000件/tx)
```

## 1.5 unit + integration tests

`tests/test_v2_regime_tagging.py`:
- `open_trade(v2_regime="moderate_trend")` で DB に書き込まれること
- 未指定なら NULL になること
- backfill script の dry-run mode が UPDATE SQL を生成すること
- Integration: 合成 signal → demo_trader が v2 classifier 呼出 → DB に保存
- composite verification: dow_regime + v2_regime 両方が同 trade に保存できること

# 2. 完了条件

1. `modules/demo_db.py` migration コード (ALTER TABLE)
2. `modules/demo_db.py::open_trade` の v2_regime 引数 + INSERT 拡張
3. `modules/demo_trader.py` の v2 signal-time hook
4. `tools/v2_regime_backfill.py` (--dry-run / --apply)
5. `tests/test_v2_regime_tagging.py` (unit + integration, mock 禁止)
6. **生成物即 commit (--no-verify)、commit hash を final.md に記載**

# 3. 司令塔ガード

- [ ] 既存 `regime` (JSON) / `mtf_regime` / `dow_regime` カラム無編集
- [ ] Score-race / signal logic 無編集
- [ ] OANDA bridge / live runner 無編集
- [ ] `modules/regime_classifier.py` の閾値改変禁止 (v2 binary は data-driven calibrated)
- [ ] v2 classifier 呼出失敗時 None 保存、signal block しない
- [ ] dow_regime と v2_regime が **同じ trade に並存** することを test で assertion
- [ ] mock-only test 禁止 (`feedback_codex_mock_test_trap`)
- [ ] backfill は dry-run-first、production DB 直接書込禁止
- [ ] 生成物即 commit (untracked 放置禁止、並列エージェント branch 切替対策)

# 4. 禁止事項

- 本番 DB / .env / OANDA secret 無触
- 既存 4 regime カラム改変禁止 (`regime` / `mtf_regime` / `dow_regime` / `mtf_*` 系)
- Score-race / signal logic 改変禁止
- backfill を本番 DB に対して実行禁止
- post-hoc v2 閾値 tune 禁止 (data-driven calibrated)

# Appendix A: classify_regime_binary の signature 確認 (Codex 探索ヒント)

```bash
rg -n "def classify_regime\|def classify_regime_binary" modules/regime_classifier.py
```

正しい関数名 + 引数仕様 + 戻り値型を確認してから hook 実装。値域 (`moderate_trend` / `no_go` / `None` のいずれか) を spec で確認。

# Appendix B: 期待される下流分析 (Phase E2)

```sql
-- Composite cell cross-tab (entry_type × dow_regime × v2_regime)
SELECT entry_type, dow_regime, v2_regime,
       COUNT(*) AS N,
       AVG(CASE WHEN pnl_pips > 0 THEN 1.0 ELSE 0.0 END) * 100 AS WR,
       AVG(pnl_pips) AS EV_pip,
       SUM(CASE WHEN pnl_pips > 0 THEN pnl_pips ELSE 0 END) /
         NULLIF(SUM(CASE WHEN pnl_pips < 0 THEN -pnl_pips ELSE 0 END), 0) AS PF
FROM demo_trades
WHERE is_shadow = 0 AND status = 'CLOSED'
  AND dow_regime IS NOT NULL AND v2_regime IS NOT NULL
GROUP BY entry_type, dow_regime, v2_regime
HAVING N >= 30
ORDER BY EV_pip DESC;
```

実行は本タスク完了後、N 蓄積した後 (~数週) に司令塔別 task で実施。
