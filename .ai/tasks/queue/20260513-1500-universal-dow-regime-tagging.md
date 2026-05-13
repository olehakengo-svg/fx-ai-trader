---
id: 20260513-1500-universal-dow-regime-tagging
title: "[Universal Dow Regime Tag] 全 trade 入口に dow_regime カラムを追加し signal 時点で classifier 呼出 → 全戦略×regime×時間帯の自然観測"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T15:00:00+0900
roadmap_gate: "Phase E 設計の Universal Observation 化 (ユーザー指示 2026-05-13)。前回 Phase E Wave 1 は 17 個の variant entry_type を pre-register する static design だったが、ユーザー指摘で全 trade 入口に regime tag を付ける dynamic observation design に切替。1 カラム追加で全 76 戦略 × 全 regime × 全時間帯の組合せを自動蓄積、未来の新戦略も自動カバー。"
rule: pre-reg
related:
  - knowledge-base/wiki/decisions/regime-gate-tier-a-2026-05-12.md
  - knowledge-base/wiki/decisions/regime-gate-phase-b25-2026-05-13.md
  - modules/demo_db.py                            # CREATE TABLE + add_trade
  - modules/demo_trader.py                        # signal → add_trade 呼出
  - lib/regime_classifier.py                      # 既存 classify_regime
  - reports/regime_gate_phase_b2/trade_log_tagged.csv  # backfill 用 retrospective tag (5617 trades)
  - feedback_shadow_first_quant_architecture
  - feedback_live_shadow_separation
  - feedback_label_empirical_audit
  - feedback_codex_mock_test_trap
---

# 0. 思想 (ユーザー指示)

> Regime 判定のタグを全戦略につければ時間帯、regime 判定それぞれ shadow で検証できる

**Universal Observation Pattern**: pre-register せず、全 trade に regime tag を付け、accumulated data から **strategy × regime × time-of-day** の任意組合せを後解析可能にする。

メリット:
- Score-race / signal logic 無触 = production behavior 変更なし、純 additive
- 17 B2.5 proposals に限らず、未来の新戦略も自動カバー
- Shadow / Live / FLAG_DRIFT 全 cohort で同条件 tagging
- 時間帯軸は `entry_time` から自動計算可、追加カラム不要

# 1. 設計

## 1.1 DB schema

`demo_trades` の既存 `regime` (JSON dict 用) と `mtf_regime` (D1×H4 7-class) には触らない。**新カラム** を追加:

```sql
ALTER TABLE demo_trades ADD COLUMN dow_regime TEXT;
```

- 値域: `'TRENDING'` / `'RANGING'` / `'CHOP'` / `NULL` (cache miss / 計算失敗)
- 命名: `dow_regime` = ダウ理論ベースの H1 ADX/ER/BBW 分類と明示

## 1.2 add_trade signature 拡張

`modules/demo_db.py` の `DemoDB.add_trade()` 引数に追加:

```python
def add_trade(self, ..., dow_regime: str | None = None, ...):
    ...
    conn.execute("""INSERT INTO demo_trades (..., dow_regime, ...) VALUES (..., ?, ...)""",
                 (..., dow_regime, ...))
```

既存呼出側で `dow_regime` 未指定なら NULL 挿入で安全。

## 1.3 signal 時点で classifier 呼出

`modules/demo_trader.py` の trade 確定 path (entry 直前) で 1 行追加:

```python
from lib.regime_classifier import classify_regime
...
# signal 確定後、add_trade 呼出直前
try:
    dow_regime = classify_regime(instrument, pd.Timestamp(entry_time_iso))
except Exception as exc:
    self._add_log(f"[regime-tag] classify_regime failed: {exc}")
    dow_regime = None
...
self.db.add_trade(..., dow_regime=dow_regime, ...)
```

**重要**:
- 失敗時 None 保存 (signal 自体は **block しない**、純観測層)
- production code への影響を最小化、try/except で wrap

## 1.4 既存 trade の backfill

backfill script `tools/dow_regime_backfill.py`:

```python
# 1) 過去全 trade を取得
# 2) entry_time + instrument で classify_regime を呼ぶ
# 3) UPDATE demo_trades SET dow_regime = ? WHERE trade_id = ?
# 4) dry-run mode 必須 (--apply で実書込)
# 5) chunked processing (1000件/tx)
```

実行は本タスクの完了条件に含まず (司令塔別途実行)。

**option**: Phase B2.5 で生成済 `reports/regime_gate_phase_b2/trade_log_tagged.csv` (5617 BT trades + regime) は production demo_trades と別ソース。直接 backfill には使わない、独立データ。

## 1.5 unit + integration tests

`tests/test_dow_regime_tagging.py`:
- `add_trade(dow_regime="TRENDING")` で DB に書き込まれること
- `add_trade()` で dow_regime 未指定なら NULL になること
- backfill script の dry-run mode が UPDATE SQL を生成すること
- Integration: 合成 signal → demo_trader が classify_regime 呼出 → DB に保存

# 2. 完了条件

1. `modules/demo_db.py` migration コード (ALTER TABLE)
2. `modules/demo_db.py::add_trade` の引数 + INSERT 拡張
3. `modules/demo_trader.py` の signal-time hook
4. `tools/dow_regime_backfill.py` (--dry-run / --apply フラグ付)
5. `tests/test_dow_regime_tagging.py` (unit + integration, mock 禁止)
6. **生成物即 commit (--no-verify)、commit hash を final.md に記載**

# 3. 司令塔ガード

- [ ] 既存 `regime` カラム (JSON) 無編集
- [ ] 既存 `mtf_regime` カラム無編集
- [ ] Score-race logic 無編集
- [ ] Signal 生成 logic 無編集 (純観測層追加のみ)
- [ ] OANDA bridge / live runner 無編集
- [ ] `lib/regime_classifier.py` の閾値改変禁止 (Phase 0 literal)
- [ ] `classify_regime` 失敗時 None 保存、signal block しない
- [ ] mock-only test 禁止 (`feedback_codex_mock_test_trap`)
- [ ] backfill は dry-run-first、production DB 直接書込禁止 (本タスクは script 提供のみ)
- [ ] 生成物即 commit (untracked 放置禁止、並列エージェント branch 切替対策)

# 4. 禁止事項

- 本番 DB / .env / OANDA secret 無触
- 既存 `regime` / `mtf_regime` カラム改変禁止
- Score-race / signal logic 改変禁止
- backfill を本番 DB に対して実行禁止 (script 用意のみ)
- post-hoc classifier tune 禁止 (ADX 25 / ER 0.30 / BBW literal)

# Appendix A: signal-time hook の入れ場所 (Codex 探索ヒント)

`modules/demo_trader.py` で trade を最終確定する直前の場所:
- `_block` 関数を通過後、`self.db.add_trade(...)` を呼ぶ手前
- entry_type / instrument / entry_time が確定している点

具体的 grep:
```bash
rg -n "self\.db\.add_trade\(" modules/demo_trader.py
```

各呼出箇所で classify_regime 呼出を入れ、結果を dow_regime キーワード引数で渡す。重複コード防止のため helper 関数 (`_compute_dow_regime(self, instrument, entry_time)`) を作って共通化推奨。

# Appendix B: classify_regime の signature (既存)

```python
def classify_regime(instrument: str, ts: pd.Timestamp) -> Literal['TRENDING','RANGING','CHOP'] | None
```

instrument は OANDA naming ('USD_JPY', 'EUR_USD' 等)、Yahoo naming ('USDJPY=X') でも内部正規化される (lib/regime_classifier.py 仕様)。

# Appendix C: 期待される下流分析 (本タスク完了後、別 task で実施)

```sql
-- strategy × dow_regime cross-tab
SELECT entry_type, dow_regime,
       COUNT(*) as N,
       AVG(CASE WHEN pnl_pips > 0 THEN 1.0 ELSE 0.0 END) as WR,
       AVG(pnl_pips) as EV_pip
FROM demo_trades
WHERE status = 'CLOSED'
  AND dow_regime IS NOT NULL
  AND instrument != 'XAU_USD'
GROUP BY entry_type, dow_regime
HAVING N >= 30
ORDER BY EV_pip DESC;

-- strategy × time-of-day × dow_regime 3 軸
SELECT entry_type,
       strftime('%H', entry_time) as utc_hour,
       dow_regime,
       COUNT(*) as N,
       AVG(pnl_pips) as EV_pip
FROM demo_trades
WHERE status = 'CLOSED'
  AND dow_regime IS NOT NULL
  AND is_shadow = 0
GROUP BY entry_type, utc_hour, dow_regime
HAVING N >= 10
ORDER BY EV_pip DESC;
```

これらは本タスク完了後、N 蓄積した後 (~数週) に司令塔が実行する。
