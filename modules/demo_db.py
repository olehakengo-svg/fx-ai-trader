"""
Demo Trading Database — SQLite storage for auto demo trades + learning adjustments.
Thread-safe with explicit locking for all writes.
"""
import sqlite3
import threading
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


class DemoDB:
    def __init__(self, db_path: str = "demo_trades.db"):
        self._path = db_path
        self._lock = threading.Lock()
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def _safe_conn(self):
        """コンテキストマネージャ: 例外時もconn.close()を保証（接続リーク防止）"""
        conn = self._conn()
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self):
        with self._lock, self._safe_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS demo_trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id        TEXT UNIQUE,
                    status          TEXT DEFAULT 'OPEN',
                    direction       TEXT,
                    entry_price     REAL,
                    entry_time      TEXT,
                    exit_price      REAL,
                    exit_time       TEXT,
                    sl              REAL,
                    tp              REAL,
                    pnl_pips        REAL,
                    pnl_r           REAL,
                    outcome         TEXT,
                    entry_type      TEXT,
                    confidence      INTEGER,
                    tf              TEXT DEFAULT '15m',
                    reasons         TEXT,
                    regime          TEXT,
                    layer1_dir      TEXT,
                    score           REAL,
                    close_reason    TEXT,
                    ema_conf        INTEGER,
                    sr_basis        REAL,
                    created_at      TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS learning_adjustments (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT DEFAULT (datetime('now')),
                    parameter       TEXT,
                    old_value       REAL,
                    new_value       REAL,
                    reason          TEXT,
                    win_rate_at     REAL,
                    ev_at           REAL,
                    sample_size     INTEGER
                );

                CREATE TABLE IF NOT EXISTS demo_logs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    message         TEXT NOT NULL,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS learning_results (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT DEFAULT (datetime('now')),
                    mode            TEXT NOT NULL,
                    sample_size     INTEGER,
                    overall_wr      REAL,
                    overall_ev      REAL,
                    data_json       TEXT,
                    insights_json   TEXT,
                    adjustments_json TEXT
                );

                CREATE TABLE IF NOT EXISTS daily_reviews (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_date     TEXT NOT NULL,
                    mode            TEXT NOT NULL,
                    trades_today    INTEGER DEFAULT 0,
                    wins_today      INTEGER DEFAULT 0,
                    pnl_today       REAL DEFAULT 0,
                    wr_today        REAL DEFAULT 0,
                    ev_today        REAL DEFAULT 0,
                    cumulative_trades INTEGER DEFAULT 0,
                    cumulative_wr   REAL DEFAULT 0,
                    cumulative_ev   REAL DEFAULT 0,
                    adjustments_json TEXT,
                    insights_json   TEXT,
                    params_snapshot TEXT,
                    created_at      TEXT DEFAULT (datetime('now')),
                    UNIQUE(review_date, mode)
                );

                CREATE TABLE IF NOT EXISTS algo_change_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT DEFAULT (datetime('now')),
                    change_type     TEXT NOT NULL,
                    description     TEXT NOT NULL,
                    params_before   TEXT,
                    params_after    TEXT,
                    triggered_by    TEXT DEFAULT 'daily_review'
                );

                CREATE INDEX IF NOT EXISTS idx_trades_status ON demo_trades(status);
                CREATE INDEX IF NOT EXISTS idx_trades_entry_type ON demo_trades(entry_type);
                CREATE INDEX IF NOT EXISTS idx_trades_created ON demo_trades(created_at);
                CREATE INDEX IF NOT EXISTS idx_trades_tf ON demo_trades(tf);
                CREATE INDEX IF NOT EXISTS idx_learning_results_mode ON learning_results(mode);
                CREATE INDEX IF NOT EXISTS idx_daily_reviews_date ON daily_reviews(review_date);
                CREATE INDEX IF NOT EXISTS idx_algo_change_log_ts ON algo_change_log(timestamp);
            """)
            # Add mode column to existing demo_trades if missing
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN mode TEXT DEFAULT ''")
            except Exception:
                pass  # column already exists
            # Add mode column to learning_adjustments if missing
            try:
                conn.execute("ALTER TABLE learning_adjustments ADD COLUMN mode TEXT DEFAULT ''")
            except Exception:
                pass
            # Add oanda_trade_id column for OANDA API integration
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN oanda_trade_id TEXT DEFAULT ''")
            except Exception:
                pass
            conn.commit()

    # ── Trade CRUD ──────────────────────────────────

    def open_trade(self, direction: str, entry_price: float, sl: float, tp: float,
                   entry_type: str, confidence: int, tf: str = "15m",
                   reasons: list = None, regime: dict = None,
                   layer1_dir: str = "", score: float = 0.0,
                   ema_conf: int = 0, sr_basis: float = 0.0,
                   mode: str = "") -> str:
        """Record a new trade open. Returns trade_id."""
        trade_id = str(uuid.uuid4())[:12]
        now_str = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO demo_trades
                        (trade_id, status, direction, entry_price, entry_time,
                         sl, tp, entry_type, confidence, tf, reasons, regime,
                         layer1_dir, score, ema_conf, sr_basis, mode)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (trade_id, "OPEN", direction, entry_price, now_str,
                      sl, tp, entry_type, confidence, tf,
                      json.dumps(reasons or [], ensure_ascii=False),
                      json.dumps(regime or {}, ensure_ascii=False),
                      layer1_dir, score, ema_conf, sr_basis, mode))
                conn.commit()
        return trade_id

    def close_trade(self, trade_id: str, exit_price: float,
                    close_reason: str = "TP_HIT") -> dict:
        """Close an open trade, compute PnL."""
        with self._lock:
            with self._safe_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM demo_trades WHERE trade_id=? AND status='OPEN'",
                    (trade_id,)
                ).fetchone()
                if not row:
                    return {"error": "Trade not found or already closed"}

                entry_p = row["entry_price"]
                direction = row["direction"]
                sl = row["sl"]
                now_str = datetime.now(timezone.utc).isoformat()

                # PnL計算 (pips: ×100 for JPY pairs)
                if direction == "BUY":
                    pnl_pips = round((exit_price - entry_p) * 100, 1)
                else:
                    pnl_pips = round((entry_p - exit_price) * 100, 1)

                sl_dist = abs(entry_p - sl)
                pnl_r = round(pnl_pips / (sl_dist * 100) if sl_dist > 0 else 0, 2)

                if pnl_pips > 0.5:
                    outcome = "WIN"
                elif pnl_pips < -0.5:
                    outcome = "LOSS"
                else:
                    outcome = "BREAKEVEN"

                # Atomic: UPDATE only if still OPEN (race condition防止)
                cursor = conn.execute("""
                    UPDATE demo_trades SET
                        status='CLOSED', exit_price=?, exit_time=?,
                        pnl_pips=?, pnl_r=?, outcome=?, close_reason=?
                    WHERE trade_id=? AND status='OPEN'
                """, (exit_price, now_str, pnl_pips, pnl_r, outcome,
                      close_reason, trade_id))
                conn.commit()

                if cursor.rowcount == 0:
                    # 別スレッドが先にクローズ済み
                    return {"error": "Trade already closed by another thread"}

        return {
            "trade_id": trade_id, "outcome": outcome,
            "pnl_pips": pnl_pips, "pnl_r": pnl_r,
            "close_reason": close_reason,
        }

    def get_open_trades(self) -> list:
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM demo_trades WHERE status='OPEN' ORDER BY entry_time DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_closed_trades(self, limit: int = 50, offset: int = 0,
                          date_from: str = None, date_to: str = None,
                          mode: str = None) -> list:
        query = "SELECT * FROM demo_trades WHERE status='CLOSED'"
        params = []
        if date_from:
            query += " AND entry_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND entry_time <= ?"
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        if mode:
            query += " AND mode = ?"
            params.append(mode)
        query += " ORDER BY exit_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_all_closed(self) -> list:
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM demo_trades WHERE status='CLOSED' ORDER BY exit_time"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self, date_from: str = None, date_to: str = None,
                  mode: str = None) -> dict:
        """Compute aggregate stats from closed trades."""
        query = ("SELECT pnl_pips, pnl_r, outcome, entry_type, confidence, close_reason "
                 "FROM demo_trades WHERE status='CLOSED'")
        params = []
        if date_from:
            query += " AND entry_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND entry_time <= ?"
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        if mode:
            query += " AND mode = ?"
            params.append(mode)
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return {"total": 0, "win_rate": 0, "total_pnl": 0, "ev": 0,
                    "avg_r": 0, "by_type": {}, "by_outcome": {}}

        total = len(rows)
        wins = sum(1 for r in rows if r["outcome"] == "WIN")
        total_pnl = sum(r["pnl_pips"] for r in rows)
        avg_r = sum(r["pnl_r"] for r in rows) / total

        # By entry type
        by_type = {}
        for r in rows:
            et = r["entry_type"] or "unknown"
            if et not in by_type:
                by_type[et] = {"trades": 0, "wins": 0, "pnl": 0}
            by_type[et]["trades"] += 1
            if r["outcome"] == "WIN":
                by_type[et]["wins"] += 1
            by_type[et]["pnl"] += r["pnl_pips"]
        for et in by_type:
            t = by_type[et]["trades"]
            by_type[et]["win_rate"] = round(by_type[et]["wins"] / t * 100, 1) if t > 0 else 0

        return {
            "total": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(wins / total * 100, 1),
            "total_pnl": round(total_pnl, 1),
            "ev": round(total_pnl / total, 2),
            "avg_r": round(avg_r, 2),
            "by_type": by_type,
        }

    def set_oanda_trade_id(self, trade_id: str, oanda_trade_id: str):
        """Link a demo trade to its OANDA trade ID."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "UPDATE demo_trades SET oanda_trade_id=? WHERE trade_id=?",
                    (oanda_trade_id, trade_id))
                conn.commit()

    def get_oanda_mappings(self) -> list:
        """Return (trade_id, oanda_trade_id) for all OPEN trades with OANDA IDs."""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT trade_id, oanda_trade_id FROM demo_trades "
                "WHERE status='OPEN' AND oanda_trade_id != '' AND oanda_trade_id IS NOT NULL"
            ).fetchall()
            return [(r["trade_id"], r["oanda_trade_id"]) for r in rows]

    # ── Learning adjustments ──────────────────────────

    def save_adjustment(self, parameter: str, old_val: float, new_val: float,
                        reason: str, win_rate: float, ev: float, sample: int,
                        mode: str = ""):
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO learning_adjustments
                        (parameter, old_value, new_value, reason, win_rate_at, ev_at, sample_size, mode)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (parameter, old_val, new_val, reason, win_rate, ev, sample, mode))
                conn.commit()

    # ── Demo Logs ──────────────────────────────────

    def add_log(self, timestamp: str, message: str):
        """Persist a demo trader log entry."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "INSERT INTO demo_logs (timestamp, message) VALUES (?, ?)",
                    (timestamp, message),
                )
                conn.commit()

    def get_logs(self, limit: int = 100) -> list:
        """Return recent logs formatted with date, newest first."""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT timestamp, message, created_at FROM demo_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for r in rows:
            ca = r['created_at'] or ''
            date_part = ca[:10] if len(ca) >= 10 else ''
            ts = r['timestamp'] or ''
            result.append(f"[{date_part} {ts}] {r['message']}")
        return result

    def get_log_count(self) -> int:
        """Return total number of log entries."""
        with self._safe_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM demo_logs").fetchone()[0]

    # ── Learning adjustments ──────────────────────────

    def get_adjustments(self, limit: int = 20) -> list:
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM learning_adjustments ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def save_learning_result(self, mode: str, sample: int, wr: float, ev: float,
                            data: dict, insights: list, adjustments: list):
        """学習分析結果をDBに永続保存"""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO learning_results
                        (mode, sample_size, overall_wr, overall_ev, data_json, insights_json, adjustments_json)
                    VALUES (?,?,?,?,?,?,?)
                """, (mode, sample, wr, ev,
                      json.dumps(data, ensure_ascii=False),
                      json.dumps(insights, ensure_ascii=False),
                      json.dumps(adjustments, ensure_ascii=False)))
                conn.commit()

    def get_learning_results(self, mode: str = None, limit: int = 50) -> list:
        """学習分析履歴を取得"""
        with self._safe_conn() as conn:
            if mode:
                rows = conn.execute(
                    "SELECT * FROM learning_results WHERE mode=? ORDER BY timestamp DESC LIMIT ?",
                    (mode, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM learning_results ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for k in ("data_json", "insights_json", "adjustments_json"):
                try:
                    d[k] = json.loads(d[k]) if d[k] else {}
                except Exception:
                    pass
            result.append(d)
        return result

    # ── Daily Review ──────────────────────────────────

    def save_daily_review(self, review_date: str, mode: str, trades_today: int,
                          wins_today: int, pnl_today: float, wr_today: float,
                          ev_today: float, cumulative_trades: int,
                          cumulative_wr: float, cumulative_ev: float,
                          adjustments: list, insights: list, params_snapshot: dict):
        """デイリーレビュー結果を保存（同日・同モードは上書き）"""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_reviews
                        (review_date, mode, trades_today, wins_today, pnl_today,
                         wr_today, ev_today, cumulative_trades, cumulative_wr,
                         cumulative_ev, adjustments_json, insights_json, params_snapshot)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (review_date, mode, trades_today, wins_today, pnl_today,
                      wr_today, ev_today, cumulative_trades, cumulative_wr,
                      cumulative_ev,
                      json.dumps(adjustments, ensure_ascii=False),
                      json.dumps(insights, ensure_ascii=False),
                      json.dumps(params_snapshot, ensure_ascii=False)))
                conn.commit()

    def get_daily_reviews(self, limit: int = 30, mode: str = None) -> list:
        """デイリーレビュー履歴を取得"""
        with self._safe_conn() as conn:
            if mode:
                rows = conn.execute(
                    "SELECT * FROM daily_reviews WHERE mode=? ORDER BY review_date DESC LIMIT ?",
                    (mode, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM daily_reviews ORDER BY review_date DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for k in ("adjustments_json", "insights_json", "params_snapshot"):
                try:
                    d[k] = json.loads(d[k]) if d[k] else {}
                except Exception:
                    pass
            result.append(d)
        return result

    def save_algo_change(self, change_type: str, description: str,
                         params_before: dict, params_after: dict,
                         triggered_by: str = "daily_review"):
        """アルゴリズム変更ログを記録"""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO algo_change_log
                        (change_type, description, params_before, params_after, triggered_by)
                    VALUES (?,?,?,?,?)
                """, (change_type, description,
                      json.dumps(params_before, ensure_ascii=False),
                      json.dumps(params_after, ensure_ascii=False),
                      triggered_by))
                conn.commit()

    def get_algo_changes(self, limit: int = 50) -> list:
        """アルゴリズム変更ログ取得"""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM algo_change_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for k in ("params_before", "params_after"):
                try:
                    d[k] = json.loads(d[k]) if d[k] else {}
                except Exception:
                    pass
            result.append(d)
        return result

    def get_trades_by_date(self, date_str: str, mode: str = None) -> list:
        """指定日のクローズドトレードを取得"""
        with self._safe_conn() as conn:
            if mode:
                tf_map = {"daytrade": "15m", "scalp": "1m", "swing": "4h"}
                target_tf = tf_map.get(mode, "")
                rows = conn.execute(
                    """SELECT * FROM demo_trades
                       WHERE status='CLOSED' AND exit_time LIKE ?
                       AND (mode=? OR (mode='' AND tf=?))
                       ORDER BY exit_time""",
                    (f"{date_str}%", mode, target_tf)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM demo_trades WHERE status='CLOSED' AND exit_time LIKE ? ORDER BY exit_time",
                    (f"{date_str}%",)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_trades_for_learning(self, min_trades: int = 10, mode: str = None) -> dict:
        """Return structured data for the learning engine. mode でフィルタ可能"""
        closed = self.get_all_closed()
        if mode:
            # modeカラムがある場合はそれで、なければtfで推定
            tf_map = {"daytrade": "15m", "scalp": "1m", "swing": "4h"}
            target_tf = tf_map.get(mode, "")
            closed = [t for t in closed if (t.get("mode") == mode) or
                      (not t.get("mode") and t.get("tf") == target_tf)]
        if len(closed) < min_trades:
            return {"ready": False, "sample": len(closed), "min_required": min_trades}

        by_type = {}
        by_conf_band = {"low": [], "mid": [], "high": []}
        by_hour = {}
        by_regime = {}
        by_layer1 = {"bull": [], "bear": [], "neutral": []}

        for t in closed:
            # By entry type
            et = t["entry_type"] or "unknown"
            by_type.setdefault(et, []).append(t)

            # By confidence band
            c = t["confidence"] or 50
            if c < 55:
                by_conf_band["low"].append(t)
            elif c < 70:
                by_conf_band["mid"].append(t)
            else:
                by_conf_band["high"].append(t)

            # By hour (extract from entry_time)
            try:
                h = datetime.fromisoformat(t["entry_time"]).hour
                by_hour.setdefault(h, []).append(t)
            except Exception:
                pass

            # By regime
            try:
                reg = json.loads(t["regime"] or "{}")
                rtype = reg.get("regime", "unknown")
                by_regime.setdefault(rtype, []).append(t)
            except Exception:
                pass

            # By layer1 direction
            l1 = t["layer1_dir"] or "neutral"
            by_layer1.setdefault(l1, []).append(t)

        def _calc_wr(trades):
            if not trades:
                return 0, 0, 0
            w = sum(1 for t in trades if t["outcome"] == "WIN")
            ev = sum(t["pnl_pips"] for t in trades) / len(trades)
            return round(w / len(trades) * 100, 1), round(ev, 2), len(trades)

        return {
            "ready": True,
            "sample": len(closed),
            "by_type":   {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_type.items()},
            "by_conf":   {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_conf_band.items()},
            "by_hour":   {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_hour.items()},
            "by_regime": {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_regime.items()},
            "by_layer1": {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_layer1.items()},
            "overall_wr": _calc_wr(closed)[0],
            "overall_ev": _calc_wr(closed)[1],
        }
