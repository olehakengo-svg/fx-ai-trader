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


def pip_multiplier(instrument: str = "USD_JPY") -> float:
    """Pip multiplier for PnL calculation.
    JPY pairs / Gold: ×100 (1 pip = 0.01), Others: ×10000 (1 pip = 0.0001)
    """
    s = instrument.upper()
    if "JPY" in s or "XAU" in s:
        return 100.0
    return 10000.0


class DemoDB:
    def __init__(self, db_path: str = "demo_trades.db"):
        self._path = db_path
        self._lock = threading.Lock()
        # ── Thread-local connection pool (2026-04-05 perf) ──
        # 毎クエリ新接続 + WAL PRAGMA → スレッドローカル接続再利用で5-10ms/query削減
        self._local = threading.local()
        self._log_write_count = 0  # ログ回転カウンタ（COUNT(*)排除用）
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        """Thread-local connection pooling: 同一スレッド内は接続再利用"""
        conn = getattr(self._local, 'conn', None)
        if conn is not None:
            try:
                conn.execute("SELECT 1")  # 接続生存確認
                return conn
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                self._local.conn = None
        conn = sqlite3.connect(self._path, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")  # 5s wait on lock instead of immediate fail
        self._local.conn = conn
        return conn

    @contextmanager
    def _safe_conn(self):
        """コンテキストマネージャ: thread-local接続を再利用（closeしない）"""
        conn = self._conn()
        try:
            yield conn
        except sqlite3.OperationalError as e:
            # DB locked等のエラー時は接続を破棄して再作成
            if "locked" in str(e).lower() or "disk" in str(e).lower():
                try:
                    conn.close()
                except Exception:
                    pass
                self._local.conn = None
            raise

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
                -- (2026-04-05 perf) 追加インデックス: 学習エンジン高速化
                CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON demo_trades(exit_time);
                CREATE INDEX IF NOT EXISTS idx_trades_mode_status ON demo_trades(mode, status);
                CREATE INDEX IF NOT EXISTS idx_logs_id ON demo_logs(id);
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
            # Add instrument column for multi-instrument support
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN instrument TEXT DEFAULT 'USD_JPY'")
            except Exception:
                pass
            # ── P0監視フィールド: スリッページ・スプレッド記録 ──
            for _col, _default in [
                ("signal_price", "0"),         # シグナル関数のmid価格（スリッページ計算用）
                ("spread_at_entry", "0"),       # エントリー時OANDAスプレッド(pip)
                ("spread_at_exit", "0"),        # 決済時OANDAスプレッド(pip)
                ("slippage_pips", "0"),         # signal_price vs entry_price の差(pip)
                ("cooldown_elapsed", "0"),      # 前回決済からの経過秒数
            ]:
                try:
                    conn.execute(f"ALTER TABLE demo_trades ADD COLUMN {_col} REAL DEFAULT {_default}")
                except Exception:
                    pass

            # ── 決済分析テキスト ──
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN close_analysis TEXT DEFAULT ''")
            except Exception:
                pass

            # ── OANDA設定永続化テーブル ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oanda_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT DEFAULT ''
                )
            """)

            # ── OANDA実取引データ保存テーブル ──
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS oanda_trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    oanda_trade_id  TEXT UNIQUE,
                    instrument      TEXT DEFAULT 'USD_JPY',
                    state           TEXT,
                    direction       TEXT,
                    initial_units   REAL,
                    current_units   REAL,
                    open_price      REAL,
                    close_price     REAL,
                    open_time       TEXT,
                    close_time      TEXT,
                    realized_pl     REAL,
                    unrealized_pl   REAL,
                    financing       REAL,
                    commission      REAL,
                    stop_loss       REAL,
                    take_profit     REAL,
                    trailing_sl     REAL,
                    pnl_pips        REAL,
                    close_reason    TEXT,
                    margin_used     REAL,
                    raw_json        TEXT,
                    synced_at       TEXT DEFAULT (datetime('now')),
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_oanda_state ON oanda_trades(state);
                CREATE INDEX IF NOT EXISTS idx_oanda_open_time ON oanda_trades(open_time);
                CREATE INDEX IF NOT EXISTS idx_oanda_close_time ON oanda_trades(close_time);
            """)
            conn.commit()

    # ── Trade CRUD ──────────────────────────────────

    def open_trade(self, direction: str, entry_price: float, sl: float, tp: float,
                   entry_type: str, confidence: int, tf: str = "15m",
                   reasons: list = None, regime: dict = None,
                   layer1_dir: str = "", score: float = 0.0,
                   ema_conf: int = 0, sr_basis: float = 0.0,
                   mode: str = "", instrument: str = "USD_JPY",
                   signal_price: float = 0.0, spread_at_entry: float = 0.0,
                   slippage_pips: float = 0.0, cooldown_elapsed: float = 0.0) -> str:
        """Record a new trade open. Returns trade_id."""
        trade_id = str(uuid.uuid4())[:12]
        now_str = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO demo_trades
                        (trade_id, status, direction, entry_price, entry_time,
                         sl, tp, entry_type, confidence, tf, reasons, regime,
                         layer1_dir, score, ema_conf, sr_basis, mode, instrument,
                         signal_price, spread_at_entry, slippage_pips, cooldown_elapsed)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (trade_id, "OPEN", direction, entry_price, now_str,
                      sl, tp, entry_type, confidence, tf,
                      json.dumps(reasons or [], ensure_ascii=False),
                      json.dumps(regime or {}, ensure_ascii=False),
                      layer1_dir, score, ema_conf, sr_basis, mode, instrument,
                      signal_price, spread_at_entry, slippage_pips, cooldown_elapsed))
                conn.commit()
        return trade_id

    def close_trade(self, trade_id: str, exit_price: float,
                    close_reason: str = "TP_HIT",
                    spread_at_exit: float = 0.0) -> dict:
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
                instrument = row["instrument"] if "instrument" in row.keys() else "USD_JPY"
                now_str = datetime.now(timezone.utc).isoformat()

                # PnL計算 (pips: ×100 for JPY, ×10000 for others)
                _pip_mult = pip_multiplier(instrument)
                if direction == "BUY":
                    pnl_pips = round((exit_price - entry_p) * _pip_mult, 1)
                else:
                    pnl_pips = round((entry_p - exit_price) * _pip_mult, 1)

                sl_dist = abs(entry_p - sl)
                pnl_r = round(pnl_pips / (sl_dist * _pip_mult) if sl_dist > 0 else 0, 2)

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
                        pnl_pips=?, pnl_r=?, outcome=?, close_reason=?,
                        spread_at_exit=?
                    WHERE trade_id=? AND status='OPEN'
                """, (exit_price, now_str, pnl_pips, pnl_r, outcome,
                      close_reason, spread_at_exit, trade_id))
                conn.commit()

                if cursor.rowcount == 0:
                    # 別スレッドが先にクローズ済み
                    return {"error": "Trade already closed by another thread"}

        return {
            "trade_id": trade_id, "outcome": outcome,
            "pnl_pips": pnl_pips, "pnl_r": pnl_r,
            "close_reason": close_reason,
        }

    def update_close_analysis(self, trade_id: str, analysis: str):
        """Update close_analysis for a recently closed trade."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "UPDATE demo_trades SET close_analysis=? WHERE trade_id=?",
                    (analysis, trade_id))
                conn.commit()

    def get_trade_log(self, limit: int = 30, date_from: str = None,
                      date_to: str = None, mode: str = None) -> list:
        """Return closed trades with compact fields for trade log UI.
        Supports date range and multi-mode filtering (comma-separated)."""
        query = """SELECT trade_id, mode, instrument, direction, entry_type,
                          pnl_pips, outcome, close_reason, close_analysis,
                          reasons, entry_time, exit_time,
                          entry_price, exit_price, sl, tp
                   FROM demo_trades WHERE status='CLOSED'"""
        params = []
        if date_from:
            query += " AND entry_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND entry_time <= ?"
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        if mode:
            modes = [m.strip() for m in mode.split(",") if m.strip()]
            if len(modes) == 1:
                query += " AND mode = ?"
                params.append(modes[0])
            else:
                query += f" AND mode IN ({','.join('?' * len(modes))})"
                params.extend(modes)
        query += " ORDER BY exit_time DESC LIMIT ?"
        params.append(limit)
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

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
            modes = [m.strip() for m in mode.split(",") if m.strip()]
            if len(modes) == 1:
                query += " AND mode = ?"
                params.append(modes[0])
            else:
                query += f" AND mode IN ({','.join('?' * len(modes))})"
                params.extend(modes)
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

        # BREAKEVEN を LOSS と区別してカウント (2026-04-05 audit fix M5)
        losses = sum(1 for r in rows if r["outcome"] == "LOSS")
        breakevens = total - wins - losses

        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "breakevens": breakevens,
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

    def get_open_trades_without_oanda(self) -> list:
        """OANDAに未連携のOPENトレードを返す（デプロイ補完用）."""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT trade_id, direction, sl, tp, mode, instrument, entry_time "
                "FROM demo_trades "
                "WHERE status='OPEN' AND (oanda_trade_id IS NULL OR oanda_trade_id = '')"
            ).fetchall()
            return [dict(r) for r in rows]

    # ── OANDA Settings Persistence ──────────────────

    def get_oanda_setting(self, key: str, default: str = "") -> str:
        """DB永続化されたOANDA設定を取得."""
        with self._safe_conn() as conn:
            row = conn.execute(
                "SELECT value FROM oanda_settings WHERE key=?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_oanda_setting(self, key: str, value: str):
        """OANDA設定をDBに永続化."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO oanda_settings (key, value) VALUES (?, ?)",
                    (key, value))
                conn.commit()

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
        """Persist a demo trader log entry. Auto-prunes via counter (every 200 writes).
        (2026-04-05 perf) 旧: 毎回SELECT COUNT(*) → 新: カウンタ方式でフルスキャン排除
        """
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "INSERT INTO demo_logs (timestamp, message) VALUES (?, ?)",
                    (timestamp, message),
                )
                # カウンタ方式プルーニング: 200回に1回だけCOUNT実行
                self._log_write_count += 1
                if self._log_write_count >= 200:
                    self._log_write_count = 0
                    count = conn.execute("SELECT COUNT(*) FROM demo_logs").fetchone()[0]
                    if count > 10000:
                        conn.execute(
                            "DELETE FROM demo_logs WHERE id NOT IN "
                            "(SELECT id FROM demo_logs ORDER BY id DESC LIMIT 8000)"
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

    @staticmethod
    def _build_tf_map() -> dict:
        """demo_trader.MODE_CONFIGから動的にtf_mapを構築 (2026-04-05 audit fix M3)"""
        try:
            from modules.demo_trader import MODE_CONFIG
            return {mode: cfg.get("tf", "") for mode, cfg in MODE_CONFIG.items()}
        except ImportError:
            return {"daytrade": "15m", "scalp": "1m", "swing": "4h"}

    def get_trades_by_date(self, date_str: str, mode: str = None) -> list:
        """指定日のクローズドトレードを取得"""
        with self._safe_conn() as conn:
            if mode:
                tf_map = self._build_tf_map()
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
            # modeカラムがある場合はそれで、なければtfで推定 (2026-04-05 audit fix M3)
            tf_map = self._build_tf_map()
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

    # ══════════════════════════════════════════════════════
    #  OANDA Real Trade Storage
    # ══════════════════════════════════════════════════════

    def upsert_oanda_trade(self, trade: dict):
        """Insert or update an OANDA trade from API response."""
        tid = str(trade.get("id", ""))
        if not tid:
            return

        instrument = trade.get("instrument", "USD_JPY")
        state = trade.get("state", "")
        # direction: positive units = BUY, negative = SELL
        initial_units_raw = trade.get("initialUnits", trade.get("currentUnits", "0"))
        initial_units = float(initial_units_raw)
        direction = "BUY" if initial_units >= 0 else "SELL"
        initial_units = abs(initial_units)
        current_units = abs(float(trade.get("currentUnits", "0")))

        open_price = float(trade.get("price", 0))
        close_price = float(trade.get("averageClosePrice", 0) or 0)
        open_time = trade.get("openTime", "")
        close_time = trade.get("closeTime", "")
        realized_pl = float(trade.get("realizedPL", 0) or 0)
        unrealized_pl = float(trade.get("unrealizedPL", 0) or 0)
        financing = float(trade.get("financing", 0) or 0)
        commission = float(trade.get("commission", 0) or 0)
        margin_used = float(trade.get("marginUsed", 0) or 0)

        # SL / TP extraction
        sl_order = trade.get("stopLossOrder") or {}
        tp_order = trade.get("takeProfitOrder") or {}
        tsl_order = trade.get("trailingStopLossOrder") or {}
        stop_loss = float(sl_order.get("price", 0) or 0)
        take_profit = float(tp_order.get("price", 0) or 0)
        trailing_sl = float(tsl_order.get("distance", 0) or 0)

        # Close reason from close transaction
        close_reason = ""
        if state == "CLOSED":
            # Determine from closing transaction type
            ct = trade.get("closingTransactionIDs", [])
            if close_price > 0 and open_price > 0:
                if stop_loss > 0 and abs(close_price - stop_loss) < 0.01:
                    close_reason = "STOP_LOSS"
                elif take_profit > 0 and abs(close_price - take_profit) < 0.01:
                    close_reason = "TAKE_PROFIT"
                else:
                    close_reason = "MARKET_CLOSE"

        # PnL in pips — price diffから算出（通貨建てPLの換算誤差を回避）
        pnl_pips = 0.0
        if state == "CLOSED" and open_price > 0 and close_price > 0:
            _pm = pip_multiplier(instrument)  # JPY=100, others=10000
            if direction and direction.upper() in ("LONG", "BUY"):
                pnl_pips = round((close_price - open_price) * _pm, 1)
            else:
                pnl_pips = round((open_price - close_price) * _pm, 1)

        raw_json = json.dumps(trade, ensure_ascii=False, default=str)

        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO oanda_trades
                        (oanda_trade_id, instrument, state, direction,
                         initial_units, current_units, open_price, close_price,
                         open_time, close_time, realized_pl, unrealized_pl,
                         financing, commission, stop_loss, take_profit,
                         trailing_sl, pnl_pips, close_reason, margin_used,
                         raw_json, synced_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
                """, (tid, instrument, state, direction,
                      initial_units, current_units, open_price, close_price,
                      open_time, close_time, realized_pl, unrealized_pl,
                      financing, commission, stop_loss, take_profit,
                      trailing_sl, pnl_pips, close_reason, margin_used,
                      raw_json))
                conn.commit()

    def get_oanda_trades(self, state: str = "CLOSED", limit: int = 200,
                         offset: int = 0, date_from: str = None,
                         date_to: str = None) -> list:
        """Query OANDA trades with filtering."""
        query = "SELECT * FROM oanda_trades"
        params = []
        conditions = []
        if state and state.upper() != "ALL":
            conditions.append("state = ?")
            params.append(state.upper())
        if date_from:
            conditions.append("open_time >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("open_time <= ?")
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY open_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_oanda_open_trades(self) -> list:
        """Return all OPEN OANDA trades."""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM oanda_trades WHERE state='OPEN' ORDER BY open_time DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_oanda_stats(self, date_from: str = None, date_to: str = None) -> dict:
        """Compute aggregate stats from closed OANDA trades."""
        query = ("SELECT direction, realized_pl, pnl_pips, financing, close_reason "
                 "FROM oanda_trades WHERE state='CLOSED'")
        params = []
        if date_from:
            query += " AND open_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND open_time <= ?"
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0,
                    "total_pl_jpy": 0, "total_pl_pips": 0, "avg_pl_jpy": 0,
                    "avg_pl_pips": 0, "total_financing": 0,
                    "by_direction": {}, "by_close_reason": {}}

        total = len(rows)
        wins = sum(1 for r in rows if r["realized_pl"] > 0)
        losses = sum(1 for r in rows if r["realized_pl"] < 0)
        be = total - wins - losses
        total_pl_jpy = sum(r["realized_pl"] for r in rows)
        total_pl_pips = sum(r["pnl_pips"] for r in rows)
        total_financing = sum(r["financing"] or 0 for r in rows)

        by_dir = {}
        for r in rows:
            d = r["direction"] or "UNKNOWN"
            if d not in by_dir:
                by_dir[d] = {"trades": 0, "wins": 0, "pnl_jpy": 0, "pnl_pips": 0}
            by_dir[d]["trades"] += 1
            if r["realized_pl"] > 0:
                by_dir[d]["wins"] += 1
            by_dir[d]["pnl_jpy"] += r["realized_pl"]
            by_dir[d]["pnl_pips"] += r["pnl_pips"]
        for d in by_dir:
            t = by_dir[d]["trades"]
            by_dir[d]["win_rate"] = round(by_dir[d]["wins"] / t * 100, 1) if t > 0 else 0
            by_dir[d]["pnl_jpy"] = round(by_dir[d]["pnl_jpy"], 0)
            by_dir[d]["pnl_pips"] = round(by_dir[d]["pnl_pips"], 1)

        by_reason = {}
        for r in rows:
            cr = r["close_reason"] or "UNKNOWN"
            if cr not in by_reason:
                by_reason[cr] = {"trades": 0, "pnl_jpy": 0}
            by_reason[cr]["trades"] += 1
            by_reason[cr]["pnl_jpy"] += r["realized_pl"]
        for cr in by_reason:
            by_reason[cr]["pnl_jpy"] = round(by_reason[cr]["pnl_jpy"], 0)

        return {
            "total": total, "wins": wins, "losses": losses, "breakeven": be,
            "win_rate": round(wins / total * 100, 1),
            "total_pl_jpy": round(total_pl_jpy, 0),
            "total_pl_pips": round(total_pl_pips, 1),
            "avg_pl_jpy": round(total_pl_jpy / total, 0),
            "avg_pl_pips": round(total_pl_pips / total, 1),
            "total_financing": round(total_financing, 0),
            "by_direction": by_dir,
            "by_close_reason": by_reason,
        }

    def get_oanda_equity_curve(self, date_from: str = None,
                               date_to: str = None) -> list:
        """Return chronological closed trades with cumulative P/L."""
        query = ("SELECT oanda_trade_id, close_time, realized_pl, pnl_pips, "
                 "direction, instrument, open_price, close_price "
                 "FROM oanda_trades WHERE state='CLOSED'")
        params = []
        if date_from:
            query += " AND close_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND close_time <= ?"
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        query += " ORDER BY close_time ASC"
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        curve = []
        cum_jpy = 0.0
        cum_pips = 0.0
        for r in rows:
            cum_jpy += r["realized_pl"]
            cum_pips += r["pnl_pips"]
            curve.append({
                "time": r["close_time"],
                "pl_jpy": round(r["realized_pl"], 0),
                "pl_pips": round(r["pnl_pips"], 1),
                "cum_jpy": round(cum_jpy, 0),
                "cum_pips": round(cum_pips, 1),
            })
        return curve

    def get_oanda_trade_count(self) -> int:
        """Return total number of OANDA trades in DB."""
        with self._safe_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM oanda_trades").fetchone()[0]

    def get_oldest_oanda_trade_id(self) -> str:
        """Return the oldest OANDA trade ID for pagination."""
        with self._safe_conn() as conn:
            row = conn.execute(
                "SELECT oanda_trade_id FROM oanda_trades ORDER BY open_time ASC LIMIT 1"
            ).fetchone()
            return row["oanda_trade_id"] if row else ""
