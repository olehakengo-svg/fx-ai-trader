"""
Demo Trading Database — SQLite storage for auto demo trades + learning adjustments.
Thread-safe with explicit locking for all writes.
"""
import sqlite3
import threading
import json
import uuid
import os
import glob as _glob_mod
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone


def pip_multiplier(instrument: str = "USD_JPY") -> float:
    """Pip multiplier for PnL calculation.
    JPY pairs / Gold: ×100 (1 pip = 0.01), Others: ×10000 (1 pip = 0.0001)
    """
    s = instrument.upper()
    if "JPY" in s or "XAU" in s:
        return 100.0
    return 10000.0


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson score interval lower bound — inlined to avoid circular import with app.py."""
    import math as _m
    if n == 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * _m.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / den)


# ─────────────────────────────────────────────────────────────────────────
# Seed/backfill replay artifact filter (2026-04-27)
# ─────────────────────────────────────────────────────────────────────────
# 観測: fib_reversal Apr 8 02:40-02:53 UTC で 16 件のトレードが entry→exit < 1秒で
# CLOSED 状態となっていた。これは backtest replay か seed data であり、リアルタイム
# Shadow とは経済的に異なる (TP まで瞬時到達 = 未来情報の漏洩)。
# 5秒未満の hold は実トレードとして成立しない (OANDA tick frequency ~1秒, 最小TP距離
# 数pip → 一般に数十秒以上要する) ため、5秒を seed/replay の判定閾値とする。
# 詳細: reports/deployment-wave-analysis-2026-04-27.md §5
SEED_HOLD_SEC_THRESHOLD = 5  # exposed for Python-side filtering / asserts
# SQL fragment is a hardcoded literal (no user input) — safe by construction.
_SEED_EXCLUSION_SQL = "(strftime('%s', exit_time) - strftime('%s', entry_time)) >= 5"


class DemoDB:
    def __init__(self, db_path: str = "demo_trades.db"):
        self._path = db_path
        self._lock = threading.Lock()
        # ── Thread-local connection pool (2026-04-05 perf) ──
        # 毎クエリ新接続 + WAL PRAGMA → スレッドローカル接続再利用で5-10ms/query削減
        self._local = threading.local()
        self._log_write_count = 0  # ログ回転カウンタ（COUNT(*)排除用）
        self._last_backfill_result = None  # populated by _backfill_dedup_violation
        self._last_flag_drift_backfill_result = None
        self._last_force_demoted_leak_backfill_result = None
        self._init_tables()
        # rule:R3 (2026-04-30): backfill dedup_violation flag for pre-fix shadow rows.
        # Idempotent (only flags rows with dedup_violation=0 in the buggy time window).
        self._last_backfill_result = self._backfill_dedup_violation()

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
                    dow_regime      TEXT,
                    v2_regime       TEXT,
                    edge_cell_id     TEXT DEFAULT '',
                    confluence_score TEXT,
                    confluence_details TEXT,
                    layer1_dir      TEXT,
                    score           REAL,
                    close_reason    TEXT,
                    ema_conf        INTEGER,
                    sr_basis        REAL,
                    created_at      TEXT DEFAULT (datetime('now'))
                );

                -- v7.0: Shadow Tracking カラム (ALTER TABLE で後方互換追加)
                -- is_shadow=1: フィルターバイパスで生成された観測専用トレード
                -- 学習エンジン・自動昇格の評価対象外

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
                    # column names / defaults are hardcoded literals from the loop above — no user input.
                    conn.execute(f"ALTER TABLE demo_trades ADD COLUMN {_col} REAL DEFAULT {_default}")  # nosem
                except Exception:
                    pass

            # ── 決済分析テキスト ──
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN close_analysis TEXT DEFAULT ''")
            except Exception:
                pass

            # ── MAFE (Max Adverse / Favorable Excursion) ──
            for _col in ["mafe_adverse_pips", "mafe_favorable_pips"]:
                try:
                    conn.execute(f"ALTER TABLE demo_trades ADD COLUMN {_col} REAL DEFAULT 0")  # nosem
                except Exception:
                    pass

            # ── v7.0: Shadow Tracking カラム ──
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN is_shadow INTEGER DEFAULT 0")
            except Exception:
                pass

            # ── 2026-04-30 (rule:R3): dedup_violation flag for contaminated rows ──
            # SHADOW_EMIT 経路に 60s dedup gate が無く tick 毎に同戦略 shadow を量産していた
            # バグ (commit 6a45bb2 で修正) の汚染レコードを post-hoc に flag するための列.
            # 詳細: knowledge-base/wiki/lessons/lesson-shadow-emit-dedup-2026-04-30.md
            # 0 = clean, 1 = duplicate (60s window 内の 2 件目以降, learning から除外対象)
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN dedup_violation INTEGER DEFAULT 0")
            except Exception:
                pass

            # ── 2026-05-11 (rule:pre-reg): FLAG_DRIFT backfill marker ──
            # Marks rows reclassified by the post-cutoff FX FLAG_DRIFT backfill
            # from is_shadow=0 to is_shadow=1, keeping rollback/auditability.
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN flag_drift_backfilled INTEGER DEFAULT 0")
            except Exception:
                pass

            # ── 2026-05-11 (rule:R3): FORCE_DEMOTED live-leak marker ──
            # Marks historical FORCE_DEMOTED rows reclassified out of clean
            # Live KPI after they leaked into OANDA/live aggregates.
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN force_demoted_live_leak INTEGER DEFAULT 0")
            except Exception:
                pass

            # ── 2026-05-13: Universal Dow regime observation tag ──
            # H1 ADX/ER/BBW based classifier label at signal time. Existing
            # regime(JSON) and mtf_regime(D1/H4 monitor) are intentionally separate.
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN dow_regime TEXT")
            except Exception:
                pass

            # ── 2026-05-13: Universal v2 M15 regime observation tag ──
            # Binary tactical classifier label at signal time. This is monitor-only
            # and intentionally separate from regime(JSON), mtf_regime, and dow_regime.
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN v2_regime TEXT")
            except Exception:
                pass

            # ── 2026-05-26: Stage-3 edge-cell direct LIVE promotion tag ──
            try:
                conn.execute("ALTER TABLE demo_trades ADD COLUMN edge_cell_id TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_edge_cell ON demo_trades(edge_cell_id)")
            except Exception:
                pass

            # ── 2026-05-13: Cross-pair confluence observation tag ──
            # Dow Theory principle #4 proxy. This is monitor-only and must not
            # alter score-race/signal logic or live routing.
            for _col in ["confluence_score", "confluence_details"]:
                try:
                    conn.execute(f"ALTER TABLE demo_trades ADD COLUMN {_col} TEXT")  # nosem
                except Exception:
                    pass

            # ── v9.3: MTF Regime Monitor カラム ──
            # D1 dominant × H4 confirm の 7-class regime を entry 時点で記録.
            # 14日蓄積後に cross-tab 分析で gate 化判断.
            # ── v9.3 Phase D: A/B test gate_group + alignment カラム ──
            #   gate_group: 'mtf_gated' = Group A (MTF gate 適用)
            #               'label_only' = Group B (現状維持, label 記録のみ)
            #   alignment:  'aligned' / 'conflict' / 'neutral' / 'unknown' / ''
            for _col, _type, _default in [
                ("mtf_regime", "TEXT", "''"),
                ("mtf_d1_label", "INTEGER", "3"),
                ("mtf_h4_label", "INTEGER", "3"),
                ("mtf_vol_state", "TEXT", "''"),
                ("gate_group", "TEXT", "''"),
                ("mtf_alignment", "TEXT", "''"),
                ("mtf_gate_action", "TEXT", "''"),  # 'kept'/'downgraded'/'none'
            ]:
                try:
                    conn.execute(f"ALTER TABLE demo_trades ADD COLUMN {_col} {_type} DEFAULT {_default}")  # nosem
                except Exception:
                    pass

            # ── OANDA設定永続化テーブル ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oanda_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT DEFAULT ''
                )
            """)

            # ── システム状態永続化テーブル (deploy survivable) ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_kv (
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
                    strategy        TEXT,
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
            # 2026-05-26 fix: idx_oanda_strategy was previously in the executescript
            # above, which fails on a pre-existing oanda_trades table that lacks the
            # `strategy` column (CREATE TABLE IF NOT EXISTS is a no-op, but the
            # following CREATE INDEX hits the missing column). _ensure_oanda_trade_strategy_column
            # adds the column AND the index idempotently, so the order is:
            # 1) base table + non-strategy indexes (executescript above)
            # 2) ALTER TABLE ADD COLUMN strategy + CREATE INDEX idx_oanda_strategy (below)
            self._ensure_oanda_trade_strategy_column(conn)

            # ── OANDA実行監査ログ永続化テーブル ──
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS oanda_audit (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    demo_trade_id   TEXT,
                    entry_type      TEXT,
                    direction       TEXT,
                    instrument      TEXT,
                    units           INTEGER DEFAULT 0,
                    is_live         INTEGER DEFAULT 0,
                    bridge_status   TEXT,
                    block_reason    TEXT DEFAULT '',
                    oanda_trade_id  TEXT DEFAULT '',
                    sr_strength     REAL,
                    sr_touches      INTEGER,
                    sr_days_span    REAL,
                    sr_is_strong    INTEGER,
                    sr_distance_atr REAL,
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_oanda_audit_ts ON oanda_audit(timestamp);
                CREATE INDEX IF NOT EXISTS idx_oanda_audit_trade ON oanda_audit(demo_trade_id);
            """)
            self._ensure_oanda_audit_sr_columns(conn)

            # ── pending_oanda_ops: persistent failure queue (audit P0-6) ──
            # Audit 2026-05-01 Pillar 1.2: OandaBridge `_fire()` retries 3 times
            # then drops the failure on the floor; demo_trades stays CLOSED while
            # OANDA may still be OPEN. We persist every transmit attempt as
            # status='pending' before the broker call and mark it 'done' (or
            # 'failed' after final retry). Recover-on-startup reads the table
            # and surfaces still-'pending' rows so an operator can reconcile.
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS pending_oanda_ops (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    op_type         TEXT NOT NULL,        -- 'open' | 'close'
                    demo_trade_id   TEXT NOT NULL,
                    instrument      TEXT,
                    direction       TEXT,
                    units           INTEGER DEFAULT 0,
                    sl              REAL,
                    tp              REAL,
                    status          TEXT NOT NULL DEFAULT 'pending',
                                                            -- pending | done | failed
                    attempts        INTEGER DEFAULT 0,
                    last_error      TEXT DEFAULT '',
                    oanda_trade_id  TEXT DEFAULT '',
                    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_oanda_ops(status);
                CREATE INDEX IF NOT EXISTS idx_pending_demo   ON pending_oanda_ops(demo_trade_id);
            """)

            # ── E1 positioning snapshots (2026-07-14 user GO, read-only ingest) ──
            # OANDA positionBook/orderBook の定期 snapshot 蓄積テーブル。
            # DDL は modules/positioning_ingest.py が単一ソース (drift 防止)。
            # 失敗は fail-loud (print) — silent except 禁止 (lesson)。
            try:
                from modules.positioning_ingest import ensure_positioning_schema
                ensure_positioning_schema(conn)
            except Exception as _pos_exc:
                print(f"[demo_db] positioning_snapshots schema init failed: "
                      f"{_pos_exc}", flush=True)

            # ── R3 market-data ingest (2026-07-18, read-only) ──
            # ff_calendar_events / cme_fx_bars_1h / market_ingest_health*。
            # DDL は modules/market_data_ingest.py が単一ソース (drift 防止)。
            try:
                from modules.market_data_ingest import ensure_market_data_schema
                ensure_market_data_schema(conn)
            except Exception as _mkt_exc:
                print(f"[demo_db] market-data ingest schema init failed: "
                      f"{_mkt_exc}", flush=True)

            # ── 遅延インデックス作成: ALTER TABLE後のカラムに依存するインデックス ──
            # mode カラムは ALTER TABLE で追加されるため、executescript 外で作成
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_mode_status ON demo_trades(mode, status)")
            except Exception:
                pass

            # ── v9.x SHADOW_MIGRATION removed (P1-3, fable5 audit 2026-07-07, rule:R3) ──
            # The old block ran a hardcoded FORCE_DEMOTED set through an
            # unconditional `is_shadow=0→1` UPDATE on every startup, with no
            # idempotency marker and no oanda_trade_id safety check. Its static
            # set had gone stale and now included CURRENTLY-ACTIVE cells
            # (dt_bb_rsi_mr edge cells E1/E3/E5/E7/E11, bb_squeeze_breakout
            # PAIR_PROMOTED), re-contaminating live rows' is_shadow flag at each
            # restart. Superseded by _backfill_force_demoted_leak_impl below
            # (dynamic FORCE_DEMOTED list + cutoff + oanda-fill safety check),
            # so the block is deleted rather than patched.
            # See knowledge-base/wiki/decisions/fable5-system-audit-2026-07-02.md P1-3

            # ── 2026-05-03 (rule:R3): OANDA-fill is_shadow drift backfill ──
            # Audit (2026-05-03 01:46 GMT+9): in a 2000-trade window, 13 of
            # 34 OANDA-executed trades (38.2%) had is_shadow=1 — `WHERE
            # is_shadow=0` aggregates were silently dropping live PnL.
            # Root cause: set_oanda_trade_id only updated oanda_trade_id,
            # not is_shadow. Forward path now flips is_shadow=0 atomically;
            # this migration corrects historical rows.
            # 2026-07-07 (P1-3 follow-up, rule:R3): exclude rows the
            # FORCE_DEMOTED leak backfill deliberately shadowed
            # (force_demoted_live_leak=1) — without this, a pre-RULE_TS
            # OANDA-filled leak row oscillates (leak backfill shadows it on
            # one restart, this rollback un-shadows it on the next) and the
            # idempotency marker then blocks re-repair forever, silently
            # re-polluting live Kelly aggregates (reproduced 4-init cycle,
            # adversarial review of PR #59).
            try:
                _drift_cur = conn.execute(
                    "UPDATE demo_trades SET is_shadow=0 "
                    "WHERE is_shadow=1 "
                    "  AND oanda_trade_id IS NOT NULL "
                    "  AND oanda_trade_id != '' "
                    "  AND COALESCE(force_demoted_live_leak, 0) = 0"
                )
                if _drift_cur.rowcount > 0:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"[SHADOW_DRIFT_BACKFILL] Fixed {_drift_cur.rowcount} "
                        f"OANDA-filled trades: is_shadow=1→0"
                    )
            except Exception:
                pass

            self._last_force_demoted_leak_backfill_result = (
                self._backfill_force_demoted_leak_impl(conn)
            )

            self._last_flag_drift_backfill_result = self._backfill_flag_drift_impl(conn)

            # P2-3 partial (2026-07-07, rule:R3): the two repair backfills
            # whole-abort on unsafe/exception with no signal anywhere —
            # production was observed paused (status=unsafe) with zero
            # visibility. Surface pauses in Render logs on every restart.
            import logging as _bf_logging
            for _bf_name, _bf_res in (
                ("FORCE_DEMOTED_LEAK", self._last_force_demoted_leak_backfill_result),
                ("FLAG_DRIFT", self._last_flag_drift_backfill_result),
            ):
                if (_bf_res or {}).get("status") in ("unsafe", "exception"):
                    _bf_logging.getLogger(__name__).warning(
                        f"[SHADOW_REPAIR_PAUSED] {_bf_name} backfill status="
                        f"{_bf_res.get('status')} — repair layer inert until "
                        f"resolved: {_bf_res}"
                    )

            conn.commit()

    @staticmethod
    def _ensure_oanda_audit_sr_columns(conn):
        """Idempotently add SR-weight audit columns to existing DBs."""
        existing = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in conn.execute("PRAGMA table_info(oanda_audit)")
        }
        for col, col_type in [
            ("sr_strength", "REAL"),
            ("sr_touches", "INTEGER"),
            ("sr_days_span", "REAL"),
            ("sr_is_strong", "INTEGER"),
            ("sr_distance_atr", "REAL"),
        ]:
            if col not in existing:
                conn.execute(f"ALTER TABLE oanda_audit ADD COLUMN {col} {col_type}")  # nosem

    @staticmethod
    def _ensure_oanda_trade_strategy_column(conn):
        """Idempotently add persisted strategy attribution to OANDA trade rows."""
        existing = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in conn.execute("PRAGMA table_info(oanda_trades)")
        }
        if "strategy" not in existing:
            conn.execute("ALTER TABLE oanda_trades ADD COLUMN strategy TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_oanda_strategy ON oanda_trades(strategy)")

    # ── 2026-04-30 (rule:R3): Pre-fix shadow contamination backfill ──
    # Phase 10 G2 で SHADOW_ALWAYS に投入された vsg_jpy_reversal /
    # rsk_gbpjpy_reversion / mqe_gbpusd_fix が 60s dedup gate 不在の状態で
    # tick 毎に量産されていた (commit 6a45bb2 で gate 修正済み)。fix commit
    # timestamp より前の 2 件目以降の emit を dedup_violation=1 で flag し
    # learning_engine / get_stats から除外可能にする。
    # 詳細: knowledge-base/wiki/lessons/lesson-shadow-emit-dedup-2026-04-30.md
    _DEDUP_BACKFILL_CUTOFF = "2026-04-30T02:42:00+00:00"  # commit 6a45bb2 timestamp
    _DEDUP_BACKFILL_TARGETS = (
        "vsg_jpy_reversal",
        "rsk_gbpjpy_reversion",
        "mqe_gbpusd_fix",
    )
    _DEDUP_BACKFILL_WINDOW_SEC = 60  # fallback when tf is unknown/empty

    # TF-aware dedup window (bar duration). Mirrors demo_trader._tf_to_window_sec.
    # rule:R3 (2026-06-08): the fixed 60s window under-flagged per-bar re-emits on
    # 5m/15m/1h/4h strategies — the emit gate routes same-bar duplicates to shadow
    # (TF-aware window up to 14400s) but the backfill only flagged sub-60s ones,
    # so 15m/4h same-bar dupes stayed dedup_violation=0 and contaminated the R2
    # audit (Claude 検証: 293 same-bar shadow dupes escaped the flag).
    _TF_WINDOW_SEC = {
        "1m": 60, "5m": 300, "15m": 900,
        "30m": 1800, "1h": 3600, "4h": 14400,
    }

    @classmethod
    def _tf_window_sec(cls, tf) -> int:
        return cls._TF_WINDOW_SEC.get((tf or "").strip(), cls._DEDUP_BACKFILL_WINDOW_SEC)

    def _backfill_dedup_violation(self):
        """One-shot post-hoc flag for contaminated SHADOW_ALWAYS rows.

        Idempotent: only scans rows with dedup_violation=0 in the buggy window,
        and after the first run those that should be flagged are flagged
        (subsequent runs find 0 candidates among un-flagged rows in the window).

        2026-04-30 (rule:R3): verbose logging added to make backfill state
        observable in production logs (previous version was silent on no-op).
        """
        # 2026-04-30: 無条件 entry log で deploy 完了確認可能にする
        print("[migration/dedup_backfill] starting...", flush=True)
        result = self._backfill_dedup_violation_impl()
        print(f"[migration/dedup_backfill] result: {result}", flush=True)
        return result

    def get_recent_signal_emits(self, *, window_sec: int = 120) -> dict:
        """Return dict {(entry_type, instrument, direction): max_entry_time_dt}
        for any rows inserted within the last `window_sec` seconds.

        Used by DemoTrader.__init__ to hydrate the in-memory dedup state
        across gunicorn restarts (rule:R3, 2026-04-30). Without this,
        each deploy clears the 60s window and lets duplicates slip through
        for the first 60s post-restart — observed as 19 leak rows during
        the 17min deploy storm @07:57-08:14 UTC.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_sec)).isoformat()
        result: dict = {}
        try:
            with self._safe_conn() as conn:
                rows = conn.execute(
                    """SELECT entry_type, instrument, direction, MAX(entry_time) AS et
                       FROM demo_trades
                       WHERE entry_time >= ?
                         AND entry_type IS NOT NULL AND entry_type != ''
                         AND instrument IS NOT NULL AND instrument != ''
                         AND direction IN ('BUY','SELL')
                       GROUP BY entry_type, instrument, direction""",
                    (cutoff,),
                ).fetchall()
                parse_errors = 0
                for r in rows:
                    try:
                        dt = datetime.fromisoformat(r["et"])
                    except Exception:
                        parse_errors += 1
                        continue
                    result[(r["entry_type"], r["instrument"], r["direction"])] = dt
                if parse_errors:
                    print(
                        f"[startup/dedup_hydrate] parse_errors={parse_errors} "
                        f"window_sec={window_sec}",
                        flush=True,
                    )
        except Exception as _e:
            print(
                f"[startup/dedup_hydrate] db query failed: "
                f"{type(_e).__name__}: {_e}",
                flush=True,
            )
            return {}
        return result

    def _get_dynamic_dedup_targets(self, conn) -> tuple:
        """Return all currently observed shadow strategy names for dedup audit.

        The original backfill/status path hard-coded the three SHADOW_ALWAYS
        strategies that existed when the gate was added. Shadow emit coverage
        has since expanded, so the audit target set must follow the DB.
        """
        rows = conn.execute(
            """SELECT DISTINCT entry_type
               FROM demo_trades
               WHERE is_shadow = 1
                 AND entry_type IS NOT NULL
                 AND entry_type != ''
               ORDER BY entry_type"""
        ).fetchall()
        targets = [r["entry_type"] for r in rows]
        for target in self._DEDUP_BACKFILL_TARGETS:
            if target not in targets:
                targets.append(target)
        return tuple(targets)

    def _backfill_dedup_violation_impl(self) -> dict:
        """Internal implementation; returns dict with detailed stats for logging.

        2026-04-30 (extended): cutoff dynamically set to NOW so that any
        sub-60s duplicates that slipped through during deploy storms also
        get flagged on subsequent startups. Idempotent because already-flagged
        rows are excluded by `dedup_violation = 0` in the WHERE clause.
        """
        # Dynamic cutoff = NOW (covers deploy-storm leak rows that came after
        # the static 02:42 UTC commit timestamp).
        dynamic_cutoff = datetime.now(timezone.utc).isoformat()
        try:
            with self._lock, self._safe_conn() as conn:
                targets = self._get_dynamic_dedup_targets(conn)
                if not targets:
                    return {"status": "no_targets", "rows_examined": 0}
                placeholders = ",".join("?" for _ in targets)
                rows = conn.execute(
                    f"""SELECT trade_id, entry_type, instrument, direction, entry_time, tf
                       FROM demo_trades
                       WHERE is_shadow = 1
                         AND dedup_violation = 0
                         AND entry_time < ?
                         AND entry_type IN ({placeholders})
                       ORDER BY entry_type, instrument, direction, entry_time""",
                    (dynamic_cutoff, *targets),
                ).fetchall()
                if not rows:
                    return {"status": "no_candidates", "rows_examined": 0,
                            "targets": list(targets)}
                last_seen: dict = {}
                flag_ids: list = []
                parse_errors = 0
                row_keys = rows[0].keys() if rows else ()
                has_tf = "tf" in row_keys
                for r in rows:
                    key = (r["entry_type"], r["instrument"], r["direction"])
                    try:
                        et = datetime.fromisoformat(r["entry_time"])
                    except Exception:
                        parse_errors += 1
                        continue
                    # TF-aware window: a 15m re-emit within the same 900s bar is a
                    # per-bar duplicate even when >60s apart (rule:R3 2026-06-08).
                    tf_val = r["tf"] if has_tf else None
                    window = timedelta(seconds=self._tf_window_sec(tf_val))
                    last = last_seen.get(key)
                    if last is not None and (et - last) < window:
                        flag_ids.append(r["trade_id"])
                    else:
                        last_seen[key] = et
                if not flag_ids:
                    return {"status": "no_flags", "rows_examined": len(rows),
                            "parse_errors": parse_errors,
                            "unique_keys": len(last_seen),
                            "targets": list(targets)}
                conn.executemany(
                    "UPDATE demo_trades SET dedup_violation = 1 WHERE trade_id = ?",
                    [(tid,) for tid in flag_ids],
                )
                conn.commit()
                return {"status": "flagged",
                        "flagged": len(flag_ids),
                        "rows_examined": len(rows),
                        "parse_errors": parse_errors,
                        "unique_keys": len(last_seen),
                        "targets": list(targets),
                        "cutoff": dynamic_cutoff}
        except Exception as _e:
            # Backfill failure must not block startup — return error info for logging.
            import traceback
            return {"status": "exception",
                    "error": str(_e),
                    "type": type(_e).__name__,
                    "traceback": traceback.format_exc()[:500]}

    def get_dedup_violation_summary(self) -> dict:
        """Diagnostic: count rows by (is_shadow, dedup_violation, target) bucket.
        Used by /api/admin/dedup_status to verify backfill ran correctly.
        """
        with self._safe_conn() as conn:
            targets = self._get_dynamic_dedup_targets(conn)
            placeholders = ",".join("?" for _ in targets) if targets else "NULL"
            rows = conn.execute(
                f"""SELECT entry_type, is_shadow, dedup_violation, COUNT(*) AS n
                   FROM demo_trades
                   WHERE entry_type IN ({placeholders})
                   GROUP BY entry_type, is_shadow, dedup_violation
                   ORDER BY entry_type, is_shadow, dedup_violation""",
                tuple(targets),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM demo_trades WHERE dedup_violation = 1"
            ).fetchone()
            # Diagnose: how many candidates the backfill SHOULD see right now
            # (cutoff = NOW so this counts all unflagged target shadows)
            now_iso = datetime.now(timezone.utc).isoformat()
            cand = conn.execute(
                f"""SELECT COUNT(*) AS n FROM demo_trades
                   WHERE is_shadow = 1 AND dedup_violation = 0
                     AND entry_time < ?
                     AND entry_type IN ({placeholders})""",
                (now_iso, *targets),
            ).fetchone()
        return {
            "by_target": [dict(r) for r in rows],
            "total_flagged": total["n"] if total else 0,
            "candidates_remaining": cand["n"] if cand else 0,
            "cutoff": now_iso,  # dynamic — reflects what backfill uses now
            "targets": list(targets),
            "last_startup_backfill_result": self._last_backfill_result,
        }

    _FLAG_DRIFT_BACKFILL_CUTOFF = "2026-04-08T00:00:00"
    _FORCE_DEMOTED_LEAK_CUTOFF = "2026-04-08T00:00:00"
    _FORCE_DEMOTED_LEAK_RULE_TS = "2026-05-11T00:00:00"

    @staticmethod
    def _force_demoted_entry_types() -> tuple:
        """Return DemoTrader's current FORCE_DEMOTED strategy set."""
        try:
            from modules.demo_trader import DemoTrader
            return tuple(sorted(DemoTrader._FORCE_DEMOTED))
        except Exception:
            return (
                "atr_regime_break",
                "donchian_momentum_breakout",
                "ema_cross",
                "ema_pullback",
                "ema_ribbon_ride",
                "ema_trend_scalp",
                "engulfing_bb",
                "fib_reversal",
                "inducement_ob",
                "intraday_seasonality",
                "lin_reg_channel",
                "macdh_reversal",
                "orb_trap",
                "post_news_vol",
                "sr_break_retest",
                "sr_channel_reversal",
                "stoch_trend_pullback",
                "v_reversal",
                "vwap_mean_reversion",
            )

    def _backfill_force_demoted_leak_impl(self, conn):
        """Reclassify historical FORCE_DEMOTED live rows as shadow KPI leaks."""
        try:
            force_demoted = self._force_demoted_entry_types()
            if not force_demoted:
                return {
                    "status": "exception",
                    "fixed_count": 0,
                    "error": "empty FORCE_DEMOTED list",
                    "cutoff": self._FORCE_DEMOTED_LEAK_CUTOFF,
                }
            placeholders = ",".join(["?"] * len(force_demoted))
            params = (
                self._FORCE_DEMOTED_LEAK_CUTOFF,
                *force_demoted,
            )
            where = (
                "entry_time >= ? "
                "AND instrument != 'XAU_USD' "
                "AND is_shadow = 0 "
                f"AND entry_type IN ({placeholders}) "
                "AND COALESCE(force_demoted_live_leak, 0) = 0"
            )
            unsafe = conn.execute(
                "SELECT COUNT(DISTINCT t.trade_id) AS n "
                "FROM demo_trades t "
                "LEFT JOIN oanda_audit a ON a.demo_trade_id = t.trade_id "
                "WHERE t.entry_time >= ? "
                "  AND t.instrument != 'XAU_USD' "
                "  AND t.is_shadow = 0 "
                f"  AND t.entry_type IN ({placeholders}) "
                "  AND COALESCE(t.force_demoted_live_leak, 0) = 0 "
                "  AND t.entry_time >= ? "
                "  AND ("
                "    (t.oanda_trade_id IS NOT NULL AND t.oanda_trade_id != '') "
                "    OR a.bridge_status = 'filled'"
                "  )",
                (*params, self._FORCE_DEMOTED_LEAK_RULE_TS),
            ).fetchone()
            unsafe_count = int(unsafe["n"] if isinstance(unsafe, sqlite3.Row) else unsafe[0])
            candidate = conn.execute(
                f"SELECT COUNT(*) AS n FROM demo_trades WHERE {where}",
                params,
            ).fetchone()
            candidate_count = int(candidate["n"] if isinstance(candidate, sqlite3.Row) else candidate[0])
            if unsafe_count > 0:
                return {
                    "status": "unsafe",
                    "fixed_count": 0,
                    "candidate_count": candidate_count,
                    "unsafe_post_rule_fill_count": unsafe_count,
                    "cutoff": self._FORCE_DEMOTED_LEAK_CUTOFF,
                    "rule_ts": self._FORCE_DEMOTED_LEAK_RULE_TS,
                    "force_demoted_count": len(force_demoted),
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                }
            if candidate_count == 0:
                return {
                    "status": "noop",
                    "fixed_count": 0,
                    "candidate_count": 0,
                    "unsafe_post_rule_fill_count": 0,
                    "cutoff": self._FORCE_DEMOTED_LEAK_CUTOFF,
                    "rule_ts": self._FORCE_DEMOTED_LEAK_RULE_TS,
                    "force_demoted_count": len(force_demoted),
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                }
            cur = conn.execute(
                "UPDATE demo_trades "
                "SET is_shadow = 1, force_demoted_live_leak = 1 "
                f"WHERE {where}",
                params,
            )
            fixed_count = int(cur.rowcount)
            return {
                "status": "backfilled",
                "fixed_count": fixed_count,
                "candidate_count": candidate_count,
                "unsafe_post_rule_fill_count": 0,
                "cutoff": self._FORCE_DEMOTED_LEAK_CUTOFF,
                "rule_ts": self._FORCE_DEMOTED_LEAK_RULE_TS,
                "force_demoted_count": len(force_demoted),
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as _e:
            import traceback
            return {
                "status": "exception",
                "fixed_count": 0,
                "error": str(_e),
                "type": type(_e).__name__,
                "traceback": traceback.format_exc()[:500],
                "cutoff": self._FORCE_DEMOTED_LEAK_CUTOFF,
            }

    def get_force_demoted_leak_backfill_status(self) -> dict:
        """Diagnostic status for FORCE_DEMOTED live-leak reclassification."""
        force_demoted = self._force_demoted_entry_types()
        placeholders = ",".join(["?"] * len(force_demoted))
        with self._safe_conn() as conn:
            if force_demoted:
                remaining = conn.execute(
                    f"""SELECT COUNT(*) AS n FROM demo_trades
                        WHERE entry_time >= ?
                          AND instrument != 'XAU_USD'
                          AND is_shadow = 0
                          AND entry_type IN ({placeholders})
                          AND COALESCE(force_demoted_live_leak, 0) = 0""",
                    (self._FORCE_DEMOTED_LEAK_CUTOFF, *force_demoted),
                ).fetchone()
            else:
                remaining = {"n": 0}
            flagged = conn.execute(
                "SELECT COUNT(*) AS n FROM demo_trades WHERE force_demoted_live_leak = 1"
            ).fetchone()
        return {
            "cutoff": self._FORCE_DEMOTED_LEAK_CUTOFF,
            "rule_ts": self._FORCE_DEMOTED_LEAK_RULE_TS,
            "force_demoted_count": len(force_demoted),
            "remaining_force_demoted_live_leaks": int(remaining["n"] if remaining else 0),
            "total_backfilled": int(flagged["n"] if flagged else 0),
            "last_startup_backfill_result": self._last_force_demoted_leak_backfill_result,
        }

    def _backfill_flag_drift_impl(self, conn):
        """Reclassify post-cutoff FX FLAG_DRIFT rows as shadow.

        FLAG_DRIFT means a row was labelled live (`is_shadow=0`) despite no
        `oanda_trade_id`. If oanda_audit says the bridge filled the trade, do
        not backfill; that row needs oanda_trade_id repair instead.
        """
        try:
            params = (self._FLAG_DRIFT_BACKFILL_CUTOFF,)
            where = (
                "entry_time >= ? "
                "AND instrument != 'XAU_USD' "
                "AND is_shadow = 0 "
                "AND (oanda_trade_id IS NULL OR oanda_trade_id = '')"
            )
            unsafe = conn.execute(
                "SELECT COUNT(*) AS n "
                "FROM demo_trades t "
                "JOIN oanda_audit a ON a.demo_trade_id = t.trade_id "
                "WHERE t.entry_time >= ? "
                "  AND t.instrument != 'XAU_USD' "
                "  AND t.is_shadow = 0 "
                "  AND (t.oanda_trade_id IS NULL OR t.oanda_trade_id = '') "
                "  AND a.bridge_status = 'filled'",
                params,
            ).fetchone()
            unsafe_count = int(unsafe["n"] if isinstance(unsafe, sqlite3.Row) else unsafe[0])
            candidate = conn.execute(
                f"SELECT COUNT(*) AS n FROM demo_trades WHERE {where}",
                params,
            ).fetchone()
            candidate_count = int(candidate["n"] if isinstance(candidate, sqlite3.Row) else candidate[0])
            if unsafe_count > 0:
                return {
                    "status": "unsafe",
                    "fixed_count": 0,
                    "candidate_count": candidate_count,
                    "unsafe_filled_audit_count": unsafe_count,
                    "cutoff": self._FLAG_DRIFT_BACKFILL_CUTOFF,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                }
            if candidate_count == 0:
                return {
                    "status": "noop",
                    "fixed_count": 0,
                    "candidate_count": 0,
                    "unsafe_filled_audit_count": 0,
                    "cutoff": self._FLAG_DRIFT_BACKFILL_CUTOFF,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                }
            cur = conn.execute(
                "UPDATE demo_trades "
                "SET is_shadow = 1, flag_drift_backfilled = 1 "
                f"WHERE {where}",
                params,
            )
            fixed_count = int(cur.rowcount)
            return {
                "status": "backfilled",
                "fixed_count": fixed_count,
                "candidate_count": candidate_count,
                "unsafe_filled_audit_count": 0,
                "cutoff": self._FLAG_DRIFT_BACKFILL_CUTOFF,
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as _e:
            import traceback
            return {
                "status": "exception",
                "fixed_count": 0,
                "error": str(_e),
                "type": type(_e).__name__,
                "traceback": traceback.format_exc()[:500],
                "cutoff": self._FLAG_DRIFT_BACKFILL_CUTOFF,
            }

    def get_flag_drift_backfill_status(self) -> dict:
        """Diagnostic status for post-cutoff FX FLAG_DRIFT reclassification."""
        with self._safe_conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) AS n FROM demo_trades
                   WHERE entry_time >= ?
                     AND instrument != 'XAU_USD'
                     AND is_shadow = 0
                     AND (oanda_trade_id IS NULL OR oanda_trade_id = '')""",
                (self._FLAG_DRIFT_BACKFILL_CUTOFF,),
            ).fetchone()
            flagged = conn.execute(
                "SELECT COUNT(*) AS n FROM demo_trades WHERE flag_drift_backfilled = 1"
            ).fetchone()
        return {
            "cutoff": self._FLAG_DRIFT_BACKFILL_CUTOFF,
            "remaining_flag_drift": int(row["n"] if row else 0),
            "total_backfilled": int(flagged["n"] if flagged else 0),
            "last_startup_backfill_result": self._last_flag_drift_backfill_result,
        }

    # ── Trade CRUD ──────────────────────────────────

    def open_trade(self, direction: str, entry_price: float, sl: float, tp: float,
                   entry_type: str, confidence: int, tf: str = "15m",
                   reasons: list = None, regime: dict = None,
                   layer1_dir: str = "", score: float = 0.0,
                   ema_conf: int = 0, sr_basis: float = 0.0,
                   mode: str = "", instrument: str = "USD_JPY",
                   signal_price: float = 0.0, spread_at_entry: float = 0.0,
                   slippage_pips: float = 0.0, cooldown_elapsed: float = 0.0,
                   is_shadow: bool = False,
                   oanda_trade_id: str = "",
                   enforce_oanda_live_invariant: bool = False,
                   dow_regime: str = None,
                   v2_regime: str = None,
                   edge_cell_id: str = "",
                   confluence_score: str = None,
                   confluence_details: str = None,
                   mtf_regime: str = "", mtf_d1_label: int = 3,
                   mtf_h4_label: int = 3, mtf_vol_state: str = "",
                   gate_group: str = "", mtf_alignment: str = "",
                   mtf_gate_action: str = "") -> str:
        """Record a new trade open. Returns trade_id.
        is_shadow=True: フィルターバイパスで生成された観測専用トレード (v7.0 Shadow Tracking)
        mtf_*: v9.3 MTF regime monitor (D1×H4×H1 engine)
        gate_group: v9.3 Phase D A/B — 'mtf_gated' or 'label_only'
        mtf_alignment: strategy_aware_alignment 結果 ('aligned'/'conflict'/'neutral')
        mtf_gate_action: 'kept' (そのまま) / 'downgraded' (conflict→shadow) / 'none'
        """
        trade_id = str(uuid.uuid4())[:12]
        oanda_trade_id = oanda_trade_id or ""
        persisted_is_shadow = bool(is_shadow) or (
            bool(enforce_oanda_live_invariant) and not bool(oanda_trade_id)
        )
        now_str = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO demo_trades
                        (trade_id, status, direction, entry_price, entry_time,
                         sl, tp, entry_type, confidence, tf, reasons, regime,
                         layer1_dir, score, ema_conf, sr_basis, mode, instrument,
                         signal_price, spread_at_entry, slippage_pips, cooldown_elapsed,
                         is_shadow, oanda_trade_id, dow_regime, v2_regime,
                         edge_cell_id, confluence_score, confluence_details,
                         mtf_regime, mtf_d1_label, mtf_h4_label, mtf_vol_state,
                         gate_group, mtf_alignment, mtf_gate_action)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (trade_id, "OPEN", direction, entry_price, now_str,
                      sl, tp, entry_type, confidence, tf,
                      json.dumps(reasons or [], ensure_ascii=False),
                      json.dumps(regime or {}, ensure_ascii=False),
                      layer1_dir, score, ema_conf, sr_basis, mode, instrument,
                      signal_price, spread_at_entry, slippage_pips, cooldown_elapsed,
                      1 if persisted_is_shadow else 0,
                      oanda_trade_id, dow_regime, v2_regime,
                      edge_cell_id or "", confluence_score, confluence_details,
                      mtf_regime, mtf_d1_label, mtf_h4_label, mtf_vol_state,
                      gate_group, mtf_alignment, mtf_gate_action))
                conn.commit()
        return trade_id

    def append_trade_reason(self, trade_id: str, reason: str) -> bool:
        """Append an audit reason to demo_trades.reasons if it is not present."""
        if not trade_id or not reason:
            return False
        with self._lock:
            with self._safe_conn() as conn:
                row = conn.execute(
                    "SELECT reasons FROM demo_trades WHERE trade_id=?",
                    (trade_id,),
                ).fetchone()
                if not row:
                    return False
                raw = row["reasons"]
                try:
                    reasons = json.loads(raw) if raw else []
                except Exception:
                    reasons = []
                if not isinstance(reasons, list):
                    reasons = [str(reasons)]
                if reason in reasons:
                    return False
                reasons.append(reason)
                conn.execute(
                    "UPDATE demo_trades SET reasons=? WHERE trade_id=?",
                    (json.dumps(reasons, ensure_ascii=False), trade_id),
                )
                conn.commit()
                return True

    def close_trade(self, trade_id: str, exit_price: float,
                    close_reason: str = "TP_HIT",
                    spread_at_exit: float = 0.0,
                    mafe_adverse_pips: float = 0.0,
                    mafe_favorable_pips: float = 0.0) -> dict:
        """Close an open trade, compute PnL. Stores MAFE excursion data."""
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
                        spread_at_exit=?,
                        mafe_adverse_pips=?, mafe_favorable_pips=?
                    WHERE trade_id=? AND status='OPEN'
                """, (exit_price, now_str, pnl_pips, pnl_r, outcome,
                      close_reason, spread_at_exit,
                      mafe_adverse_pips, mafe_favorable_pips, trade_id))
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

    def update_sl_tp(self, trade_id: str, sl: float, tp: float):
        """SL/TPを更新（Profit Extender等で動的に変更する場合用）。"""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "UPDATE demo_trades SET sl=?, tp=? WHERE trade_id=? AND status='OPEN'",
                    (sl, tp, trade_id),
                )
                conn.commit()

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

    def get_all_closed(self, exclude_shadow: bool = True,
                       exclude_seed: bool = True) -> list:
        """v8.4: exclude_shadow=True でShadowトレード除外（risk_analytics/Kelly汚染防止）

        v10 (2026-04-27): exclude_seed=True で seed/backfill replay (hold<5s)
        を除外。Apr 8 fib_reversal 16件 instant-exit が Kelly/学習エンジンを汚染
        していた構造的測定バグを修正。
        詳細: reports/deployment-wave-analysis-2026-04-27.md §5
        """
        q = "SELECT * FROM demo_trades WHERE status='CLOSED'"
        if exclude_shadow:
            q += " AND (is_shadow IS NULL OR is_shadow = 0)"
        if exclude_seed:
            q += " AND " + _SEED_EXCLUSION_SQL
        q += " ORDER BY exit_time"
        with self._safe_conn() as conn:
            rows = conn.execute(q).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self, date_from: str = None, date_to: str = None,
                  mode: str = None, exclude_shadow: bool = True,
                  exclude_xau: bool = True, instrument: str = None,
                  exclude_seed: bool = True,
                  date_field: str = "entry_time") -> dict:
        """Compute aggregate stats from closed trades.

        v8.4: exclude_shadow=True でis_shadow=1を除外（デフォルト）。
        Shadow混入によるWR/EV/Kelly汚染を防止。
        v9.1 (2026-04-17): exclude_xau=True がデフォルト。XAU は FX と pip 単位が異なり、
        少数の XAU トレードが P/L を支配するため（例: 3 trades で -1136p）。
        CLAUDE.md user memory「XAU除外」ルールに準拠。
        v9.1: instrument フィルタ追加。選択中ペアの WR/P/L のみ集計可能。
        v10 (2026-04-27): exclude_seed=True で hold<5s の seed/backfill replay を除外。
        Apr 8 fib_reversal 16件 instant-exit が WR/PF を inflate していた問題対応。
        date_field: default entry_time for historical UI compatibility. Use
        exit_time for realized-PnL risk gates such as daily-loss halts.
        """
        if date_field not in ("entry_time", "exit_time"):
            raise ValueError(f"Unsupported date_field: {date_field!r}")
        # v9.1 (2026-04-17): is_shadow を常に SELECT し、shadow/live 内訳を返す。
        # exclude_shadow はメイン統計の算出対象行をフィルタするのみ。
        # 2026-04-30 (rule:R3): dedup_violation=1 は SHADOW_EMIT 60s dedup gate
        # 不在期間の汚染レコード — Wilson/Kelly/Bonferroni を歪めるため常時除外。
        # 詳細: lesson-shadow-emit-dedup-2026-04-30.md
        query = ("SELECT pnl_pips, pnl_r, outcome, entry_type, confidence, close_reason, is_shadow, entry_time "
                 "FROM demo_trades WHERE status='CLOSED' AND dedup_violation = 0")
        if exclude_xau:
            query += " AND (instrument IS NULL OR instrument NOT LIKE '%XAU%')"
        if exclude_seed:
            query += " AND " + _SEED_EXCLUSION_SQL
        params = []
        if instrument:
            # Comma-separated list supported: "USD_JPY" or "USD_JPY,EUR_USD"
            insts = [i.strip() for i in instrument.split(",") if i.strip()]
            if len(insts) == 1:
                query += " AND instrument = ?"
                params.append(insts[0])
            else:
                query += f" AND instrument IN ({','.join('?' * len(insts))})"
                params.extend(insts)
        if date_from:
            query += f" AND {date_field} >= ?"
            params.append(date_from)
        if date_to:
            query += f" AND {date_field} <= ?"
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
            all_rows = conn.execute(query, params).fetchall()

        # v9.1: shadow/live 内訳を常に計算（exclude_shadow の値に依らず返す）
        shadow_count = sum(1 for r in all_rows if r["is_shadow"])
        live_count = sum(1 for r in all_rows if not r["is_shadow"])

        # メイン統計は exclude_shadow の指定に従って行を絞る
        rows = [r for r in all_rows if not r["is_shadow"]] if exclude_shadow else all_rows

        if not rows:
            return {"total": 0, "wins": 0, "losses": 0, "breakevens": 0,
                    "win_rate": 0, "decided_win_rate": 0, "total_pnl": 0, "ev": 0,
                    "avg_r": 0, "by_type": {}, "by_outcome": {},
                    "shadow_count": shadow_count, "live_count": live_count}

        total = len(rows)
        wins = sum(1 for r in rows if r["outcome"] == "WIN")
        total_pnl = sum(r["pnl_pips"] for r in rows)
        avg_r = sum(r["pnl_r"] for r in rows) / total

        # By entry type — accumulate pnl rows for extended quant metrics (Wilson CI + Walk-Forward)
        by_type: dict = {}
        by_type_pnls: dict = {}  # et -> [(entry_time, pnl_pips), ...] for WF h1/h2 split
        for r in rows:
            et = r["entry_type"] or "unknown"
            if et not in by_type:
                by_type[et] = {"trades": 0, "wins": 0, "pnl": 0}
                by_type_pnls[et] = []
            by_type[et]["trades"] += 1
            if r["outcome"] == "WIN":
                by_type[et]["wins"] += 1
            by_type[et]["pnl"] += r["pnl_pips"]
            by_type_pnls[et].append((r["entry_time"] or "", float(r["pnl_pips"] or 0)))
        for et in by_type:
            t = by_type[et]["trades"]
            w = by_type[et]["wins"]
            by_type[et]["win_rate"] = round(w / t * 100, 1) if t > 0 else 0
            # v9.1: float precision artifacts fix (-17.999999... → -18.0)
            by_type[et]["pnl"] = round(by_type[et]["pnl"], 1)
            # P1-2 (2026-04-29): expose Wilson CI lower bound (z=1.96) and Bonferroni-corrected (z=3.29, k≈52)
            # so the demo-analysis UI can rank strategies by statistical confidence rather than raw WR.
            by_type[et]["wilson_lower"] = round(_wilson_lower(w, t, z=1.96) * 100, 1)
            by_type[et]["wilson_bf_lower"] = round(_wilson_lower(w, t, z=3.29) * 100, 1)
            # Walk-Forward H1/H2 split — chronological halves for stability check.
            # H1>0, H2<0 with significant gap → strategy decay candidate.
            sorted_pnls = sorted(by_type_pnls[et], key=lambda x: x[0])
            half = t // 2
            h1 = [p for _, p in sorted_pnls[:half]]
            h2 = [p for _, p in sorted_pnls[half:]]
            by_type[et]["wf_h1_avg"] = round(sum(h1) / len(h1), 2) if h1 else 0.0
            by_type[et]["wf_h2_avg"] = round(sum(h2) / len(h2), 2) if h2 else 0.0

        # BREAKEVEN を LOSS と区別してカウント (2026-04-05 audit fix M5)
        losses = sum(1 for r in rows if r["outcome"] == "LOSS")
        breakevens = total - wins - losses

        # v9.1: decided_wr = BE を分母から除外した「決着勝率」(UI 表示用)
        decided = wins + losses
        decided_wr = round(wins / decided * 100, 1) if decided > 0 else 0.0

        # P1-2 (2026-04-29): overall Wilson CI lower bound on the decided WR (BE excluded).
        # Bonferroni z=3.29 corresponds to k≈52 simultaneous strategy comparisons —
        # same convention as _strategy_extended_metrics in app.py.
        overall_wilson = round(_wilson_lower(wins, decided, z=1.96) * 100, 1) if decided > 0 else 0.0
        overall_wilson_bf = round(_wilson_lower(wins, decided, z=3.29) * 100, 1) if decided > 0 else 0.0

        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "breakevens": breakevens,
            "win_rate": round(wins / total * 100, 1),
            "decided_win_rate": decided_wr,
            "wilson_lower": overall_wilson,
            "wilson_bf_lower": overall_wilson_bf,
            "total_pnl": round(total_pnl, 1),
            "ev": round(total_pnl / total, 2),
            "avg_r": round(avg_r, 2),
            "by_type": by_type,
            "shadow_count": shadow_count,
            "live_count": live_count,
        }

    def update_shadow_status(self, trade_id: str, is_shadow: bool):
        """Persist corrected is_shadow after post-open safety net evaluation."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "UPDATE demo_trades SET is_shadow=? WHERE trade_id=?",
                    (1 if is_shadow else 0, trade_id))
                conn.commit()

    def set_oanda_trade_id(self, trade_id: str, oanda_trade_id: str):
        """Link a demo trade to its OANDA trade ID.

        A non-empty oanda_trade_id means OANDA actually filled this order
        — by definition, a live execution. Flip is_shadow=0 in the same
        statement so `WHERE is_shadow=0` aggregates do not silently drop
        live PnL (was 38.2% drift in a 2000-trade window, 2026-05-03 audit).
        """
        with self._lock:
            with self._safe_conn() as conn:
                if oanda_trade_id:
                    conn.execute(
                        "UPDATE demo_trades SET oanda_trade_id=?, is_shadow=0 "
                        "WHERE trade_id=?",
                        (oanda_trade_id, trade_id))
                else:
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
        """OANDAに未連携のOPENトレードを返す（デプロイ補完用）.

        P1-6 (fable5 audit, 2026-07-09): confidence を追加 — resend 側の
        Q4 gate 再チェック (_resend_promote_gate_block_reason) が参照する。
        """
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT trade_id, direction, sl, tp, mode, instrument, entry_time, entry_type, confidence "
                "FROM demo_trades "
                "WHERE status='OPEN' AND is_shadow=0 AND (oanda_trade_id IS NULL OR oanda_trade_id = '')"
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

    # ── System KV Persistence (deploy-safe state) ──────

    def get_system_kv(self, key: str, default: str = "") -> str:
        """デプロイ永続化されたシステム状態を取得."""
        with self._safe_conn() as conn:
            row = conn.execute(
                "SELECT value FROM system_kv WHERE key=?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_system_kv(self, key: str, value: str):
        """システム状態をDBに永続化."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO system_kv (key, value) VALUES (?, ?)",
                    (key, value))
                conn.commit()

    # ── OANDA Audit Persistence ────────────────────────

    def save_oanda_audit(self, entry: dict):
        """OANDA実行監査記録をDBに永続化."""
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute("""
                    INSERT INTO oanda_audit
                    (timestamp, demo_trade_id, entry_type, direction, instrument,
                     units, is_live, bridge_status, block_reason, oanda_trade_id,
                     sr_strength, sr_touches, sr_days_span, sr_is_strong, sr_distance_atr)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.get("timestamp", ""),
                    entry.get("demo_trade_id", ""),
                    entry.get("entry_type", ""),
                    entry.get("direction", ""),
                    entry.get("instrument", ""),
                    entry.get("units", 0),
                    1 if entry.get("is_live") else 0,
                    entry.get("bridge_status", ""),
                    entry.get("block_reason", ""),
                    entry.get("oanda_trade_id", ""),
                    entry.get("sr_strength"),
                    entry.get("sr_touches"),
                    entry.get("sr_days_span"),
                    entry.get("sr_is_strong"),
                    entry.get("sr_distance_atr"),
                ))
                conn.commit()

    def get_oanda_audit(self, limit: int = 50) -> list:
        """OANDA実行監査記録をDBから取得 (新しい順→古い順に反転して返す)."""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM oanda_audit ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            result = []
            for r in reversed(rows):
                d = dict(r)
                d["is_live"] = bool(d.get("is_live", 0))
                result.append(d)
            return result

    def get_oanda_audit_count(self) -> int:
        """OANDA監査記録の総件数を返す."""
        with self._safe_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM oanda_audit").fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    def _normalize_oanda_ts(ts: str) -> str:
        """Normalize ISO timestamps for SQLite julianday comparisons."""
        if not ts:
            return ""
        return str(ts).replace("Z", "+00:00")

    @staticmethod
    def _is_strategy_label(label: str) -> bool:
        """Return True for audit `sent` labels that look like strategy ids."""
        if not label:
            return False
        mode_labels = {
            "scalp", "scalp_5m", "daytrade", "daytrade_1h", "swing",
            "daytrade_gbpusd", "daytrade_gbpjpy", "daytrade_eur",
            "daytrade_eurjpy", "daytrade_eurgbp", "daytrade_xau",
            "scalp_eur", "scalp_eurjpy", "scalp_xau",
        }
        return label not in mode_labels

    def resolve_oanda_strategy_from_audit(
        self,
        *,
        instrument: str,
        direction: str,
        open_time: str,
        window_minutes: int = 5,
        conn=None,
    ) -> str:
        """Resolve OANDA strategy from nearest `sent` audit row."""
        if not instrument or not direction or not open_time:
            return ""
        owns_conn = conn is None
        if owns_conn:
            conn_ctx = self._safe_conn()
            conn = conn_ctx.__enter__()
        try:
            rows = conn.execute(
                """
                SELECT entry_type,
                       ABS((julianday(?) - julianday(timestamp)) * 1440.0) AS delta_min
                FROM oanda_audit
                WHERE bridge_status='sent'
                  AND instrument=?
                  AND direction=?
                  AND timestamp IS NOT NULL
                  AND ABS((julianday(?) - julianday(timestamp)) * 1440.0) <= ?
                ORDER BY delta_min ASC, id DESC
                LIMIT 5
                """,
                (
                    self._normalize_oanda_ts(open_time),
                    instrument,
                    direction,
                    self._normalize_oanda_ts(open_time),
                    float(window_minutes),
                ),
            ).fetchall()
            for row in rows:
                label = row["entry_type"] if isinstance(row, sqlite3.Row) else row[0]
                if self._is_strategy_label(label):
                    return label
            return ""
        finally:
            if owns_conn:
                conn_ctx.__exit__(None, None, None)

    # ── Pending OANDA Ops (audit 2026-05-01 P0-6) ─────
    # OandaBridge fire-and-forget mode silently drops failures after 3
    # retries; demo_trades stays CLOSED while OANDA may still be OPEN.
    # The pending_oanda_ops table persists every transmit attempt so a
    # restart recovery can surface unsynced failures rather than losing
    # them.

    def pending_op_create(self, op_type: str, demo_trade_id: str,
                          *, instrument: str = "", direction: str = "",
                          units: int = 0, sl: float = 0.0,
                          tp: float = 0.0) -> int:
        """Insert a pending op row, returning its id."""
        with self._lock:
            with self._safe_conn() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO pending_oanda_ops
                        (op_type, demo_trade_id, instrument, direction,
                         units, sl, tp, status, attempts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0)
                    """,
                    (op_type, demo_trade_id, instrument, direction,
                     int(units or 0), float(sl or 0.0), float(tp or 0.0)),
                )
                conn.commit()
                return int(cur.lastrowid)

    def pending_op_mark_done(self, op_id: int, oanda_trade_id: str = "") -> None:
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    """
                    UPDATE pending_oanda_ops
                       SET status='done', oanda_trade_id=?, updated_at=datetime('now')
                     WHERE id=?
                    """,
                    (oanda_trade_id or "", int(op_id)),
                )
                conn.commit()

    def pending_op_mark_failed(self, op_id: int, error_msg: str,
                               attempts: int = 0) -> None:
        with self._lock:
            with self._safe_conn() as conn:
                conn.execute(
                    """
                    UPDATE pending_oanda_ops
                       SET status='failed', last_error=?, attempts=?,
                           updated_at=datetime('now')
                     WHERE id=?
                    """,
                    (str(error_msg)[:500], int(attempts), int(op_id)),
                )
                conn.commit()

    def pending_op_list(self, status: str = "pending", limit: int = 200) -> list:
        with self._safe_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM pending_oanda_ops
                 WHERE status = ?
                 ORDER BY id ASC LIMIT ?
                """,
                (status, int(limit)),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Learning adjustments ──────────────────────────

    # Dedup window: skip identical adjustments within this many seconds
    _ADJUSTMENT_DEDUP_SEC = 60

    def save_adjustment(self, parameter: str, old_val: float, new_val: float,
                        reason: str, win_rate: float, ev: float, sample: int,
                        mode: str = ""):
        with self._lock:
            with self._safe_conn() as conn:
                # ── Idempotency guard: skip if identical adjustment exists
                #    within the dedup window (same parameter + mode + direction)
                #    This prevents the duplicate-adjustment bug where evaluate()
                #    is called multiple times rapidly from concurrent threads.
                _direction = "up" if new_val > old_val else "down" if new_val < old_val else "same"
                dup = conn.execute("""
                    SELECT id FROM learning_adjustments
                    WHERE parameter = ?
                      AND mode = ?
                      AND CASE WHEN new_value > old_value THEN 'up'
                              WHEN new_value < old_value THEN 'down'
                              ELSE 'same' END = ?
                      AND timestamp > datetime('now', ?)
                    LIMIT 1
                """, (parameter, mode, _direction,
                      f"-{self._ADJUSTMENT_DEDUP_SEC} seconds")).fetchone()
                if dup:
                    return  # duplicate — skip silently

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

    def get_trades_for_learning(self, min_trades: int = 10, mode: str = None,
                                after_date: str = None) -> dict:
        """Return structured data for the learning engine. mode でフィルタ可能
        after_date: ISO形式の日時文字列。指定時はそれ以降のトレードのみ対象 (v6.4 Fidelity Cutoff)
        """
        closed = self.get_all_closed()
        if mode:
            # modeカラムがある場合はそれで、なければtfで推定 (2026-04-05 audit fix M3)
            tf_map = self._build_tf_map()
            target_tf = tf_map.get(mode, "")
            closed = [t for t in closed if (t.get("mode") == mode) or
                      (not t.get("mode") and t.get("tf") == target_tf)]
        # v7.0: Shadow Tracking — 観測専用トレードを学習対象から除外
        closed = [t for t in closed if not t.get("is_shadow", 0)]
        # v6.4: Fidelity Cutoff — パラメータ変更後のトレードのみ評価
        if after_date:
            closed = [t for t in closed if t.get("entry_time", "") >= after_date]
        if len(closed) < min_trades:
            return {"ready": False, "sample": len(closed), "min_required": min_trades}

        by_type = {}
        by_type_pair = {}  # v8.9: ペア×戦略別 (自動降格用)
        by_conf_band = {"low": [], "mid": [], "high": []}
        by_hour = {}
        by_regime = {}
        by_layer1 = {"bull": [], "bear": [], "neutral": []}

        for t in closed:
            # By entry type
            et = t["entry_type"] or "unknown"
            by_type.setdefault(et, []).append(t)
            # v8.9: By entry_type × instrument
            inst = t.get("instrument", "USD_JPY") or "USD_JPY"
            by_type_pair.setdefault((et, inst), []).append(t)

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

        def _calc_wf_halves(trades: list) -> tuple:
            """Phase 3.4: 50/50 split by entry_time → (h1_avg, h2_avg, p_value).

            p_value: one-sided Mann-Whitney U test for H2 > H1 (None if <3 per
            half or scipy unavailable). Used by _evaluate_promotions for both
            Walk-Forward collapse demote (H1>0, H2<0) AND recovery
            (H1≤0, H2>0, p<0.10).
            """
            if not trades or len(trades) < 4:
                return 0.0, 0.0, None
            sorted_t = sorted(trades, key=lambda r: r.get("entry_time") or "")
            half = len(sorted_t) // 2
            h1 = sorted_t[:half]
            h2 = sorted_t[half:]
            h1_pnls = [(t["pnl_pips"] or 0) for t in h1]
            h2_pnls = [(t["pnl_pips"] or 0) for t in h2]
            h1_avg = sum(h1_pnls) / len(h1_pnls) if h1_pnls else 0.0
            h2_avg = sum(h2_pnls) / len(h2_pnls) if h2_pnls else 0.0
            p_val = None
            if len(h1_pnls) >= 3 and len(h2_pnls) >= 3:
                try:
                    from scipy import stats as _sst
                    _, _p = _sst.mannwhitneyu(
                        h2_pnls, h1_pnls, alternative="greater"
                    )
                    p_val = float(_p)
                except Exception:
                    p_val = None
            return round(h1_avg, 3), round(h2_avg, 3), p_val

        def _by_type_entry(v):
            wr, ev, n = _calc_wr(v)
            h1, h2, p_val = _calc_wf_halves(v)
            return {"wr": wr, "ev": ev, "n": n,
                    "wf_h1_avg": h1, "wf_h2_avg": h2,
                    "wf_p_value": p_val}

        return {
            "ready": True,
            "sample": len(closed),
            "by_type":   {k: _by_type_entry(v) for k, v in by_type.items()},
            # v8.9: ペア×戦略別 — キーは "entry_type|instrument" 形式
            "by_type_pair": {f"{k[0]}|{k[1]}": {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v),
                             "entry_type": k[0], "instrument": k[1]} for k, v in by_type_pair.items()},
            "by_conf":   {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_conf_band.items()},
            "by_hour":   {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_hour.items()},
            "by_regime": {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_regime.items()},
            "by_layer1": {k: {"wr": _calc_wr(v)[0], "ev": _calc_wr(v)[1], "n": len(v)} for k, v in by_layer1.items()},
            "overall_wr": _calc_wr(closed)[0],
            "overall_ev": _calc_wr(closed)[1],
        }

    def get_shadow_trades_for_evaluation(self, entry_type: str = None,
                                         instrument: str = None,
                                         after_date: str = None,
                                         min_trades: int = 0,
                                         exclude_xau: bool = True,
                                         exclude_seed: bool = True) -> dict:
        """Aggregate Sentinel / Shadow (is_shadow=1) closed trades for promotion evaluation.

        v9.x (2026-04-20): lesson-sentinel-n-measurement-bug 修正の一環。
        `get_trades_for_learning` は is_shadow=0 固定で aggregate Kelly を汚さないため、
        Sentinel 戦略の N は常にゼロ扱いになっていた（構造的測定バグ）。
        この関数は **Sentinel 専用** のカウンタで、昇格評価・UI 表示に使う。

        NOTE: **`get_trades_for_learning` と混ぜない**。
        lesson-shadow-contamination に従い aggregate Kelly / 学習エンジンは
        引き続き shadow 除外のみを使う。

        Args:
            entry_type: 指定時はその entry_type のみに限定（単一戦略評価）。
            instrument: 指定時は該当ペアのみ（ペア別 Sentinel N 評価）。
            after_date: ISO 形式の日時文字列。指定時は entry_time >= after_date のみ対象
                        （Fidelity Cutoff 用）。
            min_trades: 集計結果の N が min_trades 未満なら ready=False を返す。
            exclude_xau: True (default) で XAU を除外（CLAUDE.md user memory 準拠）。

        Returns:
            {
                "ready": bool,
                "sample": int,                   # Sentinel closed trade 総数
                "by_type": {et: {"n","wr","ev"}},
                "by_type_pair": {"et|inst": {"n","wr","ev","entry_type","instrument"}},
                "by_instrument": {inst: {"n","wr","ev"}},
                "overall_wr": float,
                "overall_ev": float,
                "min_required": int,
            }
        """
        # 2026-04-30 (rule:R3): dedup_violation=1 を除外。SHADOW_EMIT 60s dedup gate
        # 不在期間 (commit 6a45bb2 以前) に量産された SHADOW_ALWAYS shadows は
        # 統計的に独立な観測ではなく、Sentinel 昇格判定 (Wilson/Bonferroni/Kelly)
        # を歪める。詳細: lesson-shadow-emit-dedup-2026-04-30.md
        query = ("SELECT pnl_pips, outcome, entry_type, instrument, entry_time "
                 "FROM demo_trades "
                 "WHERE status='CLOSED' AND is_shadow = 1 AND dedup_violation = 0")
        params: list = []
        if exclude_xau:
            query += " AND (instrument IS NULL OR instrument NOT LIKE '%XAU%')"
        if exclude_seed:
            query += " AND " + _SEED_EXCLUSION_SQL
        if entry_type:
            query += " AND entry_type = ?"
            params.append(entry_type)
        if instrument:
            insts = [i.strip() for i in instrument.split(",") if i.strip()]
            if len(insts) == 1:
                query += " AND instrument = ?"
                params.append(insts[0])
            else:
                query += f" AND instrument IN ({','.join('?' * len(insts))})"
                params.extend(insts)
        if after_date:
            query += " AND entry_time >= ?"
            params.append(after_date)

        with self._safe_conn() as conn:
            rows = [dict(r) for r in conn.execute(query, params).fetchall()]

        sample = len(rows)
        # ready=False は「評価に足る Shadow データが無い」ことを示す:
        #   - sample=0 (空DB / フィルタ不一致 / Sentinel 未発火)
        #   - sample < min_trades (呼び出し側の最低要件未達)
        if sample == 0 or sample < min_trades:
            return {"ready": False, "sample": sample, "min_required": min_trades,
                    "by_type": {}, "by_type_pair": {}, "by_instrument": {},
                    "overall_wr": 0.0, "overall_ev": 0.0}

        def _agg(trades: list) -> dict:
            if not trades:
                return {"n": 0, "wr": 0.0, "ev": 0.0}
            n = len(trades)
            wins = sum(1 for t in trades if t.get("outcome") == "WIN")
            pnl = sum((t.get("pnl_pips") or 0.0) for t in trades)
            return {
                "n": n,
                "wr": round(wins / n * 100, 1),
                "ev": round(pnl / n, 2),
            }

        by_type: dict = {}
        by_type_pair: dict = {}
        by_instrument: dict = {}
        for r in rows:
            et = r.get("entry_type") or "unknown"
            inst = r.get("instrument") or "UNKNOWN"
            by_type.setdefault(et, []).append(r)
            by_type_pair.setdefault((et, inst), []).append(r)
            by_instrument.setdefault(inst, []).append(r)

        overall = _agg(rows)
        return {
            "ready": True,
            "sample": sample,
            "min_required": min_trades,
            "by_type": {k: _agg(v) for k, v in by_type.items()},
            "by_type_pair": {
                f"{k[0]}|{k[1]}": {**_agg(v), "entry_type": k[0], "instrument": k[1]}
                for k, v in by_type_pair.items()
            },
            "by_instrument": {k: _agg(v) for k, v in by_instrument.items()},
            "overall_wr": overall["wr"],
            "overall_ev": overall["ev"],
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
                strategy = self.resolve_oanda_strategy_from_audit(
                    instrument=instrument,
                    direction=direction,
                    open_time=open_time,
                    conn=conn,
                )
                existing = conn.execute(
                    "SELECT strategy FROM oanda_trades WHERE oanda_trade_id=?",
                    (tid,),
                ).fetchone()
                if not strategy and existing:
                    strategy = existing["strategy"] or ""
                conn.execute("""
                    INSERT OR REPLACE INTO oanda_trades
                        (oanda_trade_id, instrument, state, strategy, direction,
                         initial_units, current_units, open_price, close_price,
                         open_time, close_time, realized_pl, unrealized_pl,
                         financing, commission, stop_loss, take_profit,
                         trailing_sl, pnl_pips, close_reason, margin_used,
                         raw_json, synced_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
                """, (tid, instrument, state, strategy, direction,
                      initial_units, current_units, open_price, close_price,
                      open_time, close_time, realized_pl, unrealized_pl,
                      financing, commission, stop_loss, take_profit,
                      trailing_sl, pnl_pips, close_reason, margin_used,
                      raw_json))
                conn.commit()

    def get_oanda_trades(self, state: str = "CLOSED", limit: int = 200,
                         offset: int = 0, date_from: str = None,
                         date_to: str = None, instrument: str = None) -> list:
        """Query OANDA trades with filtering. Joins audit for entry_type via demo_trade_id.

        oanda_audit stores entry_type (strategy name) + demo_trade_id.
        demo_trades stores oanda_trade_id + entry_type.
        Join path: oanda_trades.oanda_trade_id → demo_trades.oanda_trade_id → demo_trades.entry_type
        Fallback: oanda_audit via demo_trade_id (for sent status records).

        ⚠️ CRITICAL JOIN INVARIANT (audit 2026-05-01 Pillar 3.1) ⚠️
            The ON clause MUST include `AND a.bridge_status = 'sent'`. The
            `oanda_audit.entry_type` column is dual-purpose: rows with
            bridge_status='sent' carry the strategy name; rows with
            bridge_status='filled' carry the OANDA-side mode (e.g. PYR_BUY,
            PYR_SELL — pyramid child positions). Without this filter the
            COALESCE below silently substitutes a pyramid mode label for a
            strategy name and Kelly/WR aggregations are wrong (PYR children
            counted as independent strategy fires). Regression covered by
            tests/test_oanda_audit_join_invariant.py.
        """
        query = ("SELECT t.*, "
                 "COALESCE(d.entry_type, a.entry_type, t.strategy) AS strategy_resolved "
                 "FROM oanda_trades t "
                 "LEFT JOIN demo_trades d "
                 "ON t.oanda_trade_id = d.oanda_trade_id AND d.oanda_trade_id IS NOT NULL AND d.oanda_trade_id != '' "
                 "LEFT JOIN oanda_audit a "
                 "ON d.trade_id = a.demo_trade_id AND a.bridge_status = 'sent'")
        params = []
        conditions = []
        if state and state.upper() != "ALL":
            conditions.append("t.state = ?")
            params.append(state.upper())
        if date_from:
            conditions.append("t.open_time >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("t.open_time <= ?")
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        if instrument:
            conditions.append("t.instrument = ?")
            params.append(instrument)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.open_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._safe_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                resolved = d.pop("strategy_resolved", None)
                if resolved:
                    d["strategy"] = resolved
                result.append(d)
            return result

    def backfill_oanda_trade_strategy_from_audit(self, *, apply: bool = False,
                                                 window_minutes: int = 5) -> dict:
        """Backfill missing OANDA strategy labels from nearest `sent` audit rows."""
        with self._lock:
            with self._safe_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT oanda_trade_id, instrument, direction, open_time,
                           realized_pl, strategy
                    FROM oanda_trades
                    WHERE state='CLOSED'
                      AND (strategy IS NULL OR strategy='')
                    ORDER BY open_time ASC
                    """
                ).fetchall()
                updates = []
                by_strategy = {}
                for row in rows:
                    strategy = self.resolve_oanda_strategy_from_audit(
                        instrument=row["instrument"] or "",
                        direction=row["direction"] or "",
                        open_time=row["open_time"] or "",
                        window_minutes=window_minutes,
                        conn=conn,
                    )
                    if not strategy:
                        continue
                    pnl = float(row["realized_pl"] or 0.0)
                    updates.append({
                        "oanda_trade_id": row["oanda_trade_id"],
                        "strategy": strategy,
                        "realized_pl": pnl,
                    })
                    agg = by_strategy.setdefault(strategy, {
                        "count": 0,
                        "realized_pl": 0.0,
                    })
                    agg["count"] += 1
                    agg["realized_pl"] += pnl
                if apply and updates:
                    conn.executemany(
                        "UPDATE oanda_trades SET strategy=? WHERE oanda_trade_id=?",
                        [(u["strategy"], u["oanda_trade_id"]) for u in updates],
                    )
                    conn.commit()
                return {
                    "apply": bool(apply),
                    "window_minutes": window_minutes,
                    "scanned_missing": len(rows),
                    "updated_count": len(updates) if apply else 0,
                    "would_update_count": len(updates),
                    "distinct_strategies": len(by_strategy),
                    "total_realized_pl_reattributed": round(
                        sum(u["realized_pl"] for u in updates), 6
                    ),
                    "by_strategy": {
                        k: {
                            "count": v["count"],
                            "realized_pl": round(v["realized_pl"], 6),
                        }
                        for k, v in sorted(by_strategy.items())
                    },
                    "updates": updates,
                }

    def get_oanda_open_trades(self) -> list:
        """Return all OPEN OANDA trades."""
        with self._safe_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM oanda_trades WHERE state='OPEN' ORDER BY open_time DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_oanda_stats(self, date_from: str = None, date_to: str = None,
                        instrument: str = None, exclude_xau: bool = True) -> dict:
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
        if instrument:
            query += " AND instrument = ?"
            params.append(instrument)
        if exclude_xau:
            query += " AND instrument != 'XAU_USD'"
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
                               date_to: str = None, instrument: str = None,
                               exclude_xau: bool = True) -> list:
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
        if instrument:
            query += " AND instrument = ?"
            params.append(instrument)
        if exclude_xau:
            query += " AND instrument != 'XAU_USD'"
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

    # ── SQLite Daily Backup (WAL-safe) ────────────────

    def backup_database(self, keep_last: int = 3) -> dict:
        """Create a timestamped backup of the SQLite DB using sqlite3.backup() API.

        This is safe for WAL mode — it acquires a consistent snapshot without
        blocking concurrent readers/writers.

        Args:
            keep_last: Number of recent backups to keep (older ones are rotated out).

        Returns:
            dict with status, backup_path, size_bytes, rotated count.
        """
        try:
            db_dir = os.path.dirname(os.path.abspath(self._path))
            db_basename = os.path.splitext(os.path.basename(self._path))[0]
            today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            backup_name = f"{db_basename}_backup_{today_str}.db"
            backup_path = os.path.join(db_dir, backup_name)

            # Perform backup using sqlite3.backup() (WAL-safe, consistent snapshot)
            source_conn = sqlite3.connect(self._path, timeout=10)
            try:
                dest_conn = sqlite3.connect(backup_path)
                try:
                    source_conn.backup(dest_conn)
                finally:
                    dest_conn.close()
            finally:
                source_conn.close()

            backup_size = os.path.getsize(backup_path)

            # Rotate old backups: keep only the most recent `keep_last`
            pattern = os.path.join(db_dir, f"{db_basename}_backup_*.db")
            existing_backups = sorted(_glob_mod.glob(pattern))
            rotated = 0
            if len(existing_backups) > keep_last:
                for old_backup in existing_backups[:-keep_last]:
                    try:
                        os.remove(old_backup)
                        rotated += 1
                    except OSError:
                        pass

            print(f"[Backup] Created: {backup_path} ({backup_size} bytes), "
                  f"rotated {rotated} old backups", flush=True)

            return {
                "status": "ok",
                "backup_path": backup_path,
                "size_bytes": backup_size,
                "rotated": rotated,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            print(f"[Backup] FAILED: {e}", flush=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
