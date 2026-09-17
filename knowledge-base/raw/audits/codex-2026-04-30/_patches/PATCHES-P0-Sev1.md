# P0 Sev1 修正パッチ提案書 (Decision 3)

> 作成日: 2026-04-30
> 対象: LIVE 経路に直接影響する Sev1 6 件 (S1, S2, S5, S6, S7, S8)
> ステータス: **提案のみ**。適用は user 承認 + staging 検証後

各パッチは独立に適用可能で、適用順序は依存関係に従う。

## 適用順序とリスク

| 順 | ID | 対象ファイル | 推定 LoC | リスク | 依存 |
|---:|---|---|---:|---|---|
| 1 | S8 | `app.py` (auth) | ~30 | 低 | なし |
| 2 | S6 | `modules/demo_db.py` + `modules/demo_trader.py` | ~50 | 中 | なし |
| 3 | S5 | `modules/oanda_bridge.py` + `modules/oanda_client.py` | ~80 | 中 | S6 (units 列が必要) |
| 4 | S2 | `app.py` + `modules/demo_trader.py` | ~40 | 中 | なし |
| 5 | S1 | `modules/demo_trader.py` + `modules/oanda_bridge.py` | ~30 | 低 | なし |
| 6 | S7 | `modules/demo_trader.py` | ~80 | 高 | S6 |

---

## Patch 1: S8 — 認証ポリシーの逆転 (allowlist → denylist)

### 問題
`app.py:118-145` の `_require_auth()` は GET をスキップし、`_PROTECTED_PREFIXES` allowlist 方式。
結果として以下の状態変更が unauthenticated:
- `POST /api/strategy-mode` — リスト未掲載
- `GET /api/ml-train` — GET なのでスキップ
- `GET /api/cron` — GET スキップ
- `GET /api/demo/learning?run=true` — 副作用あるが GET スキップ
- `GET /api/demo/daily-review?run=true` — 同上
- `GET /healthz` (request_tick) — GET スキップ

### 修正方針
**denylist + safe-by-default**: 全 mutation 対象を明示的に protect、その他は default で要認証。
読み取り専用ルートのみ explicit allowlist。

### 変更箇所 (app.py)
```diff
-_PROTECTED_PREFIXES = (
-    "/api/emergency/", "/api/demo/start", "/api/demo/stop",
-    "/api/demo/restart", "/api/demo/close", "/api/oanda/modes",
-    "/api/oanda/sync", "/api/config/oanda_control",
-    "/api/config/toggle_oanda",
-    "/api/demo/params", "/api/db/backup", "/api/performance/record",
-    "/api/hmm/train", "/api/bt-pipeline", "/api/backtest-long",
-    "/api/admin/",
-)
+# 認証不要 (読み取り専用) ルートの explicit allowlist
+_PUBLIC_PREFIXES = (
+    "/api/demo/status",
+    "/api/demo/logs",
+    "/api/demo/trades",
+    "/api/demo/stats",
+    "/api/demo/equity",
+    "/api/demo/factors",
+    "/api/demo/trade-log",
+    "/api/demo/algo-changes",
+    "/api/oanda/accounts",
+    "/api/oanda/status",
+    "/api/oanda/heartbeat",
+    "/api/oanda/trades",
+    "/api/oanda/stats",
+    "/api/oanda/equity",
+    "/api/oanda/live",
+    "/api/oanda/audit",
+    "/api/performance",
+    "/api/layer-status",
+    "/api/regime-status",
+    "/api/strategies/status",
+    "/api/signal",
+    "/api/day_plan",
+    "/api/chart",
+    "/api/chart-data",
+    "/api/news",
+    "/api/price",
+    "/api/phase-gate",
+    "/api/risk/dashboard",
+    "/api/risk/slippage",
+    "/api/market/regime",
+    "/api/massive/signal-quality",
+    "/api/sentinel/stats",
+    "/api/portfolio/correlation",
+    "/api/trend-status",
+    "/api/money-management",
+    "/api/cron",  # NOTE: BT cache clear だが読み取り扱い (要レビュー)
+    "/api/emergency/status",
+    "/api/hmm/status",
+    "/api/evaluation",
+    "/api/pattern-analysis",
+    "/api/analyst-opinion",
+    "/api/scalp-bt-lab",
+    "/api/analysis/consolidation",
+    "/api/portfolio/optimize",
+    "/api/config/",  # config 系は要 GET 許可、POST は必ず認証 (下記で個別判定)
+    "/api/demo/params",  # GET のみ allow、POST は別判定
+    "/api/demo/learning",  # GET のみ allow (?run=true は denylist 対象、別判定)
+    "/api/demo/daily-review",  # 同上
+    "/api/demo/rules",
+    "/healthz",
+)
+
+# 読み取り扱いだが特定パラメータ付きで mutating になるルートの追加判定
+def _is_mutating_get(path: str, args) -> bool:
+    """GET でも副作用を起こすパターンを検出"""
+    if path.startswith("/api/demo/learning") and args.get("run", "").lower() in ("true", "1"):
+        return True
+    if path.startswith("/api/demo/daily-review") and args.get("run", "").lower() in ("true", "1"):
+        return True
+    if path.startswith("/api/ml-train"):
+        return True
+    if path.startswith("/api/cron") and args.get("force", "").lower() in ("true", "1"):
+        return True
+    return False
+

 def _require_auth():
-    """Before-request hook: protect destructive endpoints with Bearer token."""
+    """Before-request hook: deny by default, allow read-only public routes."""
     if not _API_AUTH_TOKEN:
-        return  # 未設定時はスキップ（後方互換）
-    if request.method == "GET":
-        return  # 読み取りは認証不要
-    if not any(request.path.startswith(p) for p in _PROTECTED_PREFIXES):
-        return  # 対象外のエンドポイント
+        # 旧後方互換は脆弱性の温床。token 未設定時はサーバ起動を fail-fast に変えるべきだが、
+        # 今は警告ログのみ出して全許可 (運用停止を防ぐため)。
+        return
+    # 静的アセットはスルー
+    if request.path.startswith("/static/") or request.path == "/" or request.path == "/healthz":
+        if request.path == "/healthz" and request.method == "GET":
+            return
+        if request.path == "/" and request.method == "GET":
+            return
+    # 公開 GET の判定
+    if request.method == "GET":
+        path = request.path
+        if any(path.startswith(p) for p in _PUBLIC_PREFIXES) and not _is_mutating_get(path, request.args):
+            return
+        # 上記に該当しない GET は認証必須 (denylist by default)
+    # 認証実施
     auth = request.headers.get("Authorization", "")
     expected = f"Bearer {_API_AUTH_TOKEN}"
     import hmac as _hmac
     if _hmac.compare_digest(auth.encode("utf-8"), expected.encode("utf-8")):
-        return  # 認証成功
+        return
     return jsonify({"error": "Unauthorized", "message": "Valid Bearer token required"}), 401
```

### 検証
1. staging deploy 後、各 public ルートを curl で 200 確認
2. POST/PUT/DELETE で認証なし→401 確認
3. `GET /api/demo/learning?run=true` で 401 確認 (mutating GET)
4. UI 動作確認 (templates 内の fetch wrapper が token 付与しているはず)

---

## Patch 2: S6 — ロット永続化 (units 列追加)

### 問題
`modules/demo_trader.py:4437,4632,571` で `_adjusted_units` を計算して OANDA に渡すが、
`demo_trades` テーブルに `units` 列がなく、永続化されない。
結果: 再起動時の `_resend_pending_oanda_trades()` が default units で再送 → 増量実行が消える。

### 修正方針
1. `demo_trades` に `units` 列 (REAL DEFAULT 0) を追加
2. `open_trade()` 呼び出し時に units を渡し永続化
3. `_resend_pending_oanda_trades()` は永続化された units を読み出す
4. `ExposureManager` 登録も永続化された units を使用

### 変更箇所 1: modules/demo_db.py
```diff
 # スキーマ migration セクション (既存)
+# units 列 — 2026-04-30 追加: 増量実行時のロット永続化
+try:
+    cur.execute("ALTER TABLE demo_trades ADD COLUMN units REAL DEFAULT 0")
+    conn.commit()
+except sqlite3.OperationalError:
+    pass  # 既存
```

### 変更箇所 2: modules/demo_db.py の open_trade() 関数シグネチャ
```diff
-def open_trade(self, trade_id, ..., is_shadow=0, ...):
+def open_trade(self, trade_id, ..., is_shadow=0, units=0.0, ...):
     ...
     cur.execute(
-        "INSERT INTO demo_trades (trade_id, ..., is_shadow, ...) VALUES (?, ..., ?, ...)",
-        (trade_id, ..., is_shadow, ...)
+        "INSERT INTO demo_trades (trade_id, ..., is_shadow, units, ...) VALUES (?, ..., ?, ?, ...)",
+        (trade_id, ..., is_shadow, units, ...)
     )
```

### 変更箇所 3: modules/demo_trader.py の発注経路
```diff
 # entry 確定後
 _adjusted_units = self._compute_units(...)
+# units を永続化 (2026-04-30 P0 fix S6)
 self._db.open_trade(
     trade_id=trade_id,
     ...,
     is_shadow=_is_shadow,
+    units=_adjusted_units,
 )
 self._exposure_mgr.register(trade_id, instrument, direction, _adjusted_units)
 # OANDA bridge 呼び出し
 self._oanda_bridge.open(..., units=_adjusted_units)
```

### 変更箇所 4: _resend_pending_oanda_trades()
```diff
-pending = self._db.get_open_trades_without_oanda_id()
-for trade in pending:
-    self._oanda_bridge.open(..., units=OANDA_UNITS)  # ← bug: 常に default
+pending = self._db.get_open_trades_without_oanda_id()
+for trade in pending:
+    units = trade.get("units") or OANDA_UNITS  # 既存行は default fallback
+    self._oanda_bridge.open(..., units=units)
```

### 検証
- migration 後、新規 trade で `SELECT trade_id, units FROM demo_trades ORDER BY created_at DESC LIMIT 5;` で値確認
- 既存行は units=0 → resend 時 fallback 動作確認

---

## Patch 3: S5 — OANDA 発注の冪等性

### 問題
`modules/oanda_bridge.py:400-419` `market_order()` に `client_order_id` がない。
timeout/network/503 後の retry、deploy 後の resend で broker 側に約定済み注文があっても重複発注。

### 修正方針
1. `demo_trade_id` から決定的な `client_order_id` を生成 (例: `fxa-{trade_id_first_16}`)
2. OANDA `clientExtensions.id` フィールドに埋め込み
3. retry/resend 前に `GET /v3/accounts/{accountID}/trades?ids=...&state=ALL` で重複照会
4. 既存約定があれば `oanda_trade_id` を DB に書き戻して新規発注スキップ

### 変更箇所 1: modules/oanda_client.py
```diff
-def market_order(self, instrument, units, sl_price=None, tp_price=None):
+def market_order(self, instrument, units, sl_price=None, tp_price=None, client_order_id=None):
     order_data = {
         "order": {
             "type": "MARKET",
             "instrument": instrument,
             "units": str(units),
             "timeInForce": "FOK",
             "positionFill": "DEFAULT",
+            "clientExtensions": {
+                "id": client_order_id,
+                "tag": "fxa-trader",
+                "comment": f"client_order_id={client_order_id}",
+            } if client_order_id else None,
         }
     }
+    # None 値を持つ clientExtensions は削除
+    if order_data["order"].get("clientExtensions") is None:
+        del order_data["order"]["clientExtensions"]
     return self._post("/orders", order_data)

+def get_trade_by_client_id(self, client_order_id):
+    """clientExtensions.id で既存約定を照会 (idempotency check)"""
+    res = self._get(f"/trades", params={"state": "ALL", "count": 50})
+    for t in res.get("trades", []):
+        ce = t.get("clientExtensions", {})
+        if ce.get("id") == client_order_id:
+            return t
+    return None
```

### 変更箇所 2: modules/oanda_bridge.py
```diff
-def open(self, trade_id, instrument, direction, units, sl, tp):
+def open(self, trade_id, instrument, direction, units, sl, tp):
+    # idempotency key: 決定的に trade_id から生成
+    client_order_id = f"fxa-{trade_id[:16]}"
+    # 既存約定の照会 (retry/resend 時の重複防止)
+    existing = self._client.get_trade_by_client_id(client_order_id)
+    if existing:
+        log.info(f"[oanda_bridge] Existing trade found for client_order_id={client_order_id}, skipping new order")
+        return {"tradeOpened": {"tradeID": existing["id"]}, "_idempotent": True}
     signed_units = units if direction == "BUY" else -units
     ...
-    res = self._client.market_order(instrument, signed_units, sl, tp)
+    res = self._client.market_order(instrument, signed_units, sl, tp, client_order_id=client_order_id)
     return res
```

### 検証
- staging で同じ trade_id を 2 回 open() 呼び出して 2 回目が `_idempotent=True` で返る
- OANDA Practice 環境で実 API 検証

---

## Patch 4: S2 — Auto-start single-owner 化

### 問題
`app.py:14025-14105` `_auto_start_done` はプロセスローカル。Gunicorn worker=4 等で起動すると 4 つの DemoTrader が並列起動 → 二重発注。

### 修正方針
DB-level lock または PID-file lease でリーダー選出。

### 変更箇所 (app.py)
```diff
-_auto_start_done = False

 def _auto_start_trader():
-    global _auto_start_done
-    if _auto_start_done:
-        print("[AutoStart] Already executed — skipping duplicate", flush=True)
-        return
-    _auto_start_done = True
+    # DB-level leader election (2026-04-30 P0 fix S2)
+    import sqlite3, time as _time, os as _os
+    LOCK_PATH = _os.path.expanduser("~/.fxa-trader-autostart.lock")
+    try:
+        # SQLite-based exclusive lock
+        conn = sqlite3.connect(LOCK_PATH, timeout=0.5)
+        conn.execute("CREATE TABLE IF NOT EXISTS lock (pid INTEGER, acquired_at REAL)")
+        # 既存ロックチェック
+        cur = conn.execute("SELECT pid, acquired_at FROM lock LIMIT 1")
+        existing = cur.fetchone()
+        if existing:
+            existing_pid, acquired_at = existing
+            # 60秒以内かつ別 PID なら別プロセスがリーダー
+            if (_time.time() - acquired_at) < 60 and existing_pid != _os.getpid():
+                # 別プロセスのリーダーがまだ生きているか確認
+                try:
+                    _os.kill(existing_pid, 0)  # signal 0 = process exists check
+                    print(f"[AutoStart] Another worker (PID={existing_pid}) is leader — skipping", flush=True)
+                    conn.close()
+                    return
+                except OSError:
+                    pass  # 死んだ leader、引き継ぐ
+            # 古いロック削除
+            conn.execute("DELETE FROM lock")
+        # リーダー登録
+        conn.execute("INSERT INTO lock (pid, acquired_at) VALUES (?, ?)", (_os.getpid(), _time.time()))
+        conn.commit()
+        conn.close()
+        print(f"[AutoStart] Acquired leadership (PID={_os.getpid()})", flush=True)
+    except sqlite3.OperationalError:
+        print(f"[AutoStart] Failed to acquire lock — another worker is leader", flush=True)
+        return
```

### 検証
- `gunicorn -w 4 app:app` で 4 worker 起動、AutoStart ログが 1 つだけ出ることを確認
- 1 worker kill 後、別 worker が takeover することを確認 (60s 後)

---

## Patch 5: S1 — OANDA kill 強制化

### 問題
`modules/oanda_bridge.py:323-327` `_oanda_kill()` は `_allowed_modes` を空にするが、
`is_mode_allowed()` (modules/demo_trader.py:2369-2383, 4647-4725) が常に True を返す → 停止できない。

### 修正方針
別途 `_kill_active` フラグを設けて、`open_trade()` 冒頭で必ずチェックする。

### 変更箇所 (modules/demo_trader.py)
```diff
 class DemoTrader:
     def __init__(self):
         ...
+        self._kill_active = False  # 2026-04-30 P0 fix S1
         self._allowed_modes = set()
         ...

+    def is_killed(self) -> bool:
+        """Hard kill check — bypass all other gates"""
+        return self._kill_active

     def is_mode_allowed(self, mode):
+        if self._kill_active:
+            return False  # P0 fix S1: kill is authoritative
         return ...

+    def kill(self):
+        """Hard kill: stop all entries immediately"""
+        self._kill_active = True
+        self._allowed_modes.clear()
+        log.warning("[DemoTrader] HARD KILL activated")
+
+    def resume(self):
+        """Resume after kill"""
+        self._kill_active = False
+        log.info("[DemoTrader] Kill flag cleared")

     def open_trade(self, ...):
+        if self._kill_active:
+            log.warning(f"[open_trade] Blocked by kill flag")
+            return None
         ...
```

### 変更箇所 (modules/oanda_bridge.py)
```diff
 def _oanda_kill(self):
-    self._allowed_modes.clear()
+    self._allowed_modes.clear()
+    # P0 fix S1: hard kill the demo trader
+    if hasattr(self, "_demo_trader_ref"):
+        self._demo_trader_ref.kill()
```

### 検証
- staging で `POST /api/emergency/kill` 後、新規 entry が出ないことを確認
- `POST /api/emergency/resume` で復帰できることを確認

---

## Patch 6: S7 — Gate-first INSERT (deferred、最も慎重に扱う)

### 問題
`modules/demo_trader.py:4231,4617,4710` で OPEN 行を INSERT 後に shadow/live 判定を後追い更新。
途中クラッシュで `is_shadow=0` のままの孤児行が残り、再起動時 resend で実弾発注される。

### 修正方針
OPEN INSERT を **最終 gate 判定後** に移すか、`pending_live_decision` 中間状態を導入。

これは **最もデリケートな変更**。state machine 全体に影響するため、独立 PR + 詳細レビュー必須。

### 暫定対策 (より小さい変更)
`_resend_pending_oanda_trades()` に safety check を追加:
```diff
 pending = self._db.get_open_trades_without_oanda_id()
 for trade in pending:
+    # P0 fix S7 暫定: gate 判定が完了していない可能性のある行は resend しない
+    if (trade.get("created_at") or "") and trade.get("is_shadow") is None:
+        log.warning(f"[resend] Skipping trade {trade['trade_id']} with NULL is_shadow (gate decision pending)")
+        continue
+    # 24時間以上前の OPEN は手動レビュー対象
+    age_h = (datetime.now(timezone.utc) - parse_iso(trade["created_at"])).total_seconds() / 3600
+    if age_h > 24:
+        log.warning(f"[resend] Skipping stale trade {trade['trade_id']} ({age_h:.1f}h old)")
+        continue
     self._oanda_bridge.open(...)
```

### 本格対策 (別 PR)
state machine を `pending_gate_decision → shadow / live` の 2 段に変更。
これは別タスクとして spawn 推奨。

---

## 適用後の統合検証

1. **staging で 24h 観察**:
   - 二重発注 0 件
   - kill が即時効く
   - resend が正しく units を復元
2. **本番 staged rollout**:
   - 認証強化後、UI fetch が動作することを確認
   - emergency kill/resume の動作確認
   - 発注ログで `client_order_id` が記録されることを確認
3. **monitoring dashboard 追加**:
   - `oanda_trade_id` 空かつ `is_shadow=0` の行カウント (= broken state 検出)
   - `units` 列のヒストグラム (= 増量実行の追跡)
