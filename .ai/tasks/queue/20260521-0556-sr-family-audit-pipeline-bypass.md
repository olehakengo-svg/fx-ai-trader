---
id: 20260521-0556-sr-family-audit-pipeline-bypass
priority: P1
rule: R3
status: queued
created_at: 2026-05-21T05:56:00Z
estimated_runtime_min: 30
---

# Task: SR-family signal audit pipeline bypass investigation + fix

## Context (2026-05-21 audit conversation で実測判明)

`/api/oanda/audit` (oanda_audit テーブル) に **SR-family 戦略の記録が長期間書かれていない** ことが本日 (2026-05-21 UTC ~04:50) に判明。

### 実測証拠 (production /api/oanda/audit?limit=2000 + /api/demo/status)

| 戦略 | 直近 oanda_audit 記録 | 現在 open_trades 件数 (2026-05-21 04:48 UTC) |
|---|---|---|
| `sr_fib_confluence` | **2026-05-14 13:01 UTC** (7 日前) | **9 件** (全 GBP_USD, 全 is_shadow=1) |
| `sr_anti_hunt_bounce` | **2026-05-18 10:03 UTC** (3 日前) | **8 件** (USD_JPY + GBP_JPY mix) |
| `session_time_bias` | 直近 (id=6131 02:38 UTC) | 1 件 (正常) |
| 他 (fib_reversal / engulfing_bb / vol_momentum_scalp 等) | 直近正常 | 0 件 (正常) |

→ **SR-family のみ audit パイプラインから消えている**。session_time_bias 等は正常書き込み継続。

### タイムライン仮説

- **2026-05-11**: SR-weight Phase 1 ACCEPT (commit 364027e2 `feat(audit): record SR-level quality` + sr_anti_hunt_bounce promote 等)
- **2026-05-14**: sr_fib_confluence 最終 audit (Phase 1 リリース 3 日後)
- **2026-05-18**: sr_anti_hunt_bounce 最終 audit (Phase 2 直後)
- 以降、両戦略は demo_trades には書かれ続けるが oanda_audit には書かれない

`session_time_bias` 等 SR-family 外は影響なし → SR signal generation path が **`OandaBridge._add_audit` を bypass している** 可能性が極めて高い。

## 影響範囲

- **Live/Shadow 監視盲点化**: `/api/oanda/audit` が SR-family の send/skip/block 分布を反映しない
- **Demote 判断ソース汚染**: counterfactual 分析 / R2 watchdog の補助ソースとして audit を見ている場合に誤った景色
- **2026-05-21 Post-London Report (Q1)** で「OANDA 転送率 16%」の異常値が出た一因の可能性 (audit カバレッジ自体が SR-family で欠損のため)

## 調査対象

### 必読 (production code at origin/main HEAD ≈ c7b4ab52)

- `modules/demo_trader.py`
  - `_resolve_tier(...)` / `_resolve_is_shadow_for_write(...)` — Tier 決定経路
  - line ~5347–5495 の `if _is_promoted: ... else: self._add_oanda_audit(... block_reason='shadow_tracking')` 経路
  - SR-family 専用の早期 return 経路があるか (`if entry_type.startswith('sr_'): return` 等)
- `modules/oanda_bridge.py`
  - `_add_audit(self, ...)` (line 239) — DB write 経路
  - `if self._db: self._db.save_oanda_audit(entry)` のガード — `_db` が None になる経路は?
- `modules/demo_db.py`
  - `save_oanda_audit(self, entry)` — exception を起こすパスがあるか (entry に新 column が無い等)
  - `_ensure_oanda_audit_sr_columns(conn)` — 364027e2 で追加された SR columns との整合
- SR-weight Phase 1/2 関連 commit (2026-05-08 ~ 2026-05-13 で SR を触ったもの全部)
  - 特に `tools/sr_*_shadow_*.py` / `modules/sr_*.py` 系
  - SR signal が demo_trader を経由せずに直接 demo_trades に書く path があれば本件原因

### 仮説リスト (Codex は全部検証して当てはまるものを特定)

1. **H1: SR-family signal generation が demo_trader を経由しない**
   - SR-weight Phase 1 で SR signals が `demo_db.create_trade()` を直接呼ぶ別経路を作った可能性
   - 結果: `_add_oanda_audit` が呼ばれない
2. **H2: `_add_audit` が SR-family で silent skip**
   - `if self._db:` が False になる SR path 固有のタイミング
   - または try/except で `Audit DB write failed` が抑制されている (Render logs で確認可能)
3. **H3: save_oanda_audit が schema mismatch で example で失敗**
   - 364027e2 が追加した sr_strength/sr_touches/sr_days_span/sr_is_strong/sr_distance_atr の NULL 受付エラー
   - production DB に migration が走っていない可能性
4. **H4: SR-family signal が is_shadow=1 even when promoted で entry_gate を異常通過**
   - 別パスで demo_trades には書かれるが audit には到達しない

### 検証コマンド (Codex が実機で使う)

```bash
# 1. Production audit table 直接確認 (Render shell or read-only API)
curl -s 'https://fx-ai-trader.onrender.com/api/oanda/audit?limit=200' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); from collections import Counter; print(dict(Counter(r['entry_type'] for r in d['audit'])))"

# 2. Production demo_trades vs oanda_audit 突き合わせ
# (要 Render shell or DB dump): SELECT entry_type, COUNT(*) FROM demo_trades WHERE entry_time > '2026-05-15' AND entry_type LIKE 'sr_%' GROUP BY entry_type;
# vs SELECT entry_type, COUNT(*) FROM oanda_audit WHERE timestamp > '2026-05-15' AND entry_type LIKE 'sr_%' GROUP BY entry_type;

# 3. demo_trader.py で SR signal 生成箇所を全列挙
grep -n "sr_anti_hunt_bounce\|sr_fib_confluence" modules/demo_trader.py
grep -rn "_add_oanda_audit\|_add_audit\|save_oanda_audit" modules/ | grep -v test
```

## 期待 deliverable

### Required

1. **Root cause line numbers** (modules/*.py の具体的 file:line で SR-family が audit を bypass する箇所を特定)
2. **修正 PR** (`feature/sr-audit-pipeline-fix-20260521` branch を切る or `.ai/tasks/done/` に diff を提示)
3. **Regression test** (`tests/test_sr_audit_pipeline.py` 新規):
   - sr_anti_hunt_bounce × USD_JPY shadow signal を投入
   - signal 処理後に `oanda_audit` テーブルに該当 row が存在することを assert
   - 同様に sr_fib_confluence × GBP_USD で 1 ケース

### Verdict matrix

- **ACCEPT**: root cause line numbers 特定 + fix PR + test 1+ 件 PASS
- **NEEDS_MORE_EVIDENCE**: 仮説 1 件以上は否定したが root cause 未特定 → 次の調査 task を提案
- **REJECT**: 4 仮説全て検証して原因不明 (考えにくいが宣言する場合は根拠を示す)

## 制約・禁止事項

- 本番 DB (`/var/data/demo_signals.db` on Render) に **書き込まない**。read-only 操作のみ。
- OANDA API キー、Render API キー、Discord bot token は code path 上で参照しない。
- 修正 PR には CLAUDE.md の `feat()` ルール (関連 wiki update 同 commit) を遵守。
- 修正は **最小差分**。SR-family 以外の audit 経路を変更しない。
- vix_carry_unwind の lot 倍率 (commit e085ec09 で 0.05→1.0) は **触らない**。

## Related memory

- [SR-weight Phase 1 ACCEPT 2026-05-11](knowledge-base/wiki/decisions/sr-weight-phase1-accept-2026-05-11.md)
- [SR-weight Phase 2 ACCEPT 2026-05-11](knowledge-base/wiki/decisions/sr-weight-phase2-accept-2026-05-11.md)
- 2026-05-21 audit conversation (Claude session, Q1-Q3 audit + vix_carry deploy)
- /api/oanda/stats range bug (memory 2026-05-18) — 別件だが関連する observability gap
