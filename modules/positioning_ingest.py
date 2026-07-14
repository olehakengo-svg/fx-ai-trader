"""
E1 positioning ingest — OANDA positionBook/orderBook 定期 snapshot 蓄積。

目的 (user GO 2026-07-14, rule:R3 データ基盤):
  retail-positioning contrarian (E1, WS3 供給ラインの主戦線) の検証には
  建玉/注文比率の **時系列** が必須だが、broker 建玉の過去分は非公開のため
  「今から蓄積する」以外に入手経路がない。本モジュールはその read-only
  ingest job。live 発注・戦略・Kelly には一切関与しない。

設計 (knowledge-base/wiki/analyses/e1-positioning-ingest-2026-07-14.md):
  - OANDA v20 `GET /v3/instruments/{instrument}/positionBook` / `orderBook`
    を約 20 分毎 (+jitter) に poll。book の `time` が前回保存と同一なら skip
    (OANDA 側更新が ~20 分毎のため)。
  - 永続化は既存 SQLite (Render `/var/data/demo_trades.db`) の新テーブル
    `positioning_snapshots`。UNIQUE(instrument, book_type, snapshot_time)。
  - サイズ抑制: buckets は mid ±3% 帯へ trim して保存。集計列
    (pct_long_total / pct_short_total / near_imbalance = ±0.5% 帯 long−short)
    は trim **前** の全帯域から計算する。
  - fail-loud: 連続失敗カウント/最終エラーを status に露出。silent except 禁止
    (lesson: watchdog DECREMENT / spike-gate 0-price ガード)。
  - エンドポイント非対応 instrument は初回 4xx (429 以外) を記録して以後 skip
    (可用性マップを status に出す)。
  - モジュールトップ副作用禁止 — env 読み・client 生成は全て関数内。

検証 API (app.py): /api/positioning/status, /api/positioning/export
テスト: tests/test_positioning_ingest.py (offline/deterministic)
"""
from __future__ import annotations

import json
import logging
import os
import random
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("positioning_ingest")

# ── 定数 (env override は start_positioning_ingest 内で解決) ──
DEFAULT_INSTRUMENTS: Tuple[str, ...] = (
    "USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY", "AUD_JPY",
)
BOOK_TYPES: Tuple[str, ...] = ("position", "order")
DEFAULT_POLL_SEC = 1200        # 20 分 (OANDA book 更新間隔に整合)
DEFAULT_JITTER_SEC = 120
TRIM_PCT = 0.03                # buckets 保存帯: mid ±3%
NEAR_PCT = 0.005               # near_imbalance 帯: mid ±0.5%
STALE_ALERT_SEC = 2 * 3600     # 監視基準: 2h 超 stale で要調査 (registry 連携)

THREAD_NAME = "positioning-ingest"

# ── Schema (単一ソース — modules/demo_db.py の _init_tables からも呼ばれる) ──
_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS positioning_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument      TEXT NOT NULL,
    book_type       TEXT NOT NULL,          -- 'position' | 'order'
    snapshot_time   TEXT NOT NULL,          -- OANDA book.time (RFC3339)
    price           REAL,                   -- book anchor price
    bucket_width    REAL,
    buckets_json    TEXT,                   -- [[price, longPct, shortPct], ...] mid±3% trim
    pct_long_total  REAL,                   -- 全帯域 long% 合計 (trim 前)
    pct_short_total REAL,                   -- 全帯域 short% 合計 (trim 前)
    near_imbalance  REAL,                   -- mid±0.5% 帯の long−short
    fetched_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(instrument, book_type, snapshot_time)
);
CREATE INDEX IF NOT EXISTS idx_pos_snap_time ON positioning_snapshots(snapshot_time);
"""


def ensure_positioning_schema(conn_or_path) -> None:
    """positioning_snapshots テーブルを冪等作成。

    conn_or_path: sqlite3.Connection または db_path 文字列。
    demo_db.py の migration パターン (CREATE TABLE IF NOT EXISTS) に従う。
    失敗は呼び出し側で fail-loud に処理する (ここでは握り潰さない)。
    """
    if hasattr(conn_or_path, "executescript"):
        conn_or_path.executescript(_TABLE_DDL)
        return
    conn = sqlite3.connect(conn_or_path)
    try:
        conn.executescript(_TABLE_DDL)
        conn.commit()
    finally:
        conn.close()


# ── parse / trim / 集計 (純関数 — テスト対象) ──────────────────────────

def parse_book(book: Dict[str, Any],
               trim_pct: float = TRIM_PCT,
               near_pct: float = NEAR_PCT) -> Dict[str, Any]:
    """OANDA book dict → 保存用 dict (trim + 集計)。

    book: {"price": "150.000", "bucketWidth": "0.050", "time": RFC3339,
           "buckets": [{"price","longCountPercent","shortCountPercent"}, ...]}

    集計列 (pct_long_total / pct_short_total / near_imbalance) は trim 前の
    全 buckets から計算し、保存する buckets のみ mid ±trim_pct に切る。
    必須キー欠落は ValueError (呼び出し側が失敗カウント) — silent 破損保存を防ぐ。
    """
    if not isinstance(book, dict):
        raise ValueError(f"book is not a dict: {type(book).__name__}")
    for key in ("price", "bucketWidth", "time"):
        if key not in book:
            raise ValueError(f"book missing required key: {key}")
    mid = float(book["price"])
    bucket_width = float(book["bucketWidth"])
    snapshot_time = str(book["time"])

    long_total = 0.0
    short_total = 0.0
    near_long = 0.0
    near_short = 0.0
    trimmed: List[List[float]] = []
    trim_band = mid * trim_pct
    near_band = mid * near_pct
    for b in book.get("buckets", []) or []:
        p = float(b["price"])
        lp = float(b.get("longCountPercent", 0) or 0)
        sp = float(b.get("shortCountPercent", 0) or 0)
        long_total += lp
        short_total += sp
        dist = abs(p - mid)
        if dist <= near_band:
            near_long += lp
            near_short += sp
        if dist <= trim_band:
            trimmed.append([p, lp, sp])

    return {
        "snapshot_time": snapshot_time,
        "price": mid,
        "bucket_width": bucket_width,
        "buckets": trimmed,
        "pct_long_total": round(long_total, 4),
        "pct_short_total": round(short_total, 4),
        "near_imbalance": round(near_long - near_short, 4),
    }


def extract_book_payload(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """API レスポンスから book 本体を取り出す。

    OANDA v20 実レスポンスは {"positionBook": {...}} / {"orderBook": {...}}。
    防御的に "book" キーも受ける。見つからなければ None (呼び出し側が失敗扱い)。
    """
    if not isinstance(data, dict):
        return None
    for key in ("positionBook", "orderBook", "book"):
        payload = data.get(key)
        if isinstance(payload, dict):
            return payload
    return None


# ── 永続化 ──────────────────────────────────────────────────────────

def save_snapshot(db_path: str, instrument: str, book_type: str,
                  parsed: Dict[str, Any]) -> bool:
    """1 snapshot を INSERT OR IGNORE で保存。新規行なら True。

    UNIQUE(instrument, book_type, snapshot_time) が DB 層の dedup
    (プロセス再起動でメモリ上の前回 time が消えても二重保存しない)。
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO positioning_snapshots"
            " (instrument, book_type, snapshot_time, price, bucket_width,"
            "  buckets_json, pct_long_total, pct_short_total, near_imbalance,"
            "  fetched_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                instrument,
                book_type,
                parsed["snapshot_time"],
                parsed["price"],
                parsed["bucket_width"],
                json.dumps(parsed["buckets"], separators=(",", ":")),
                parsed["pct_long_total"],
                parsed["pct_short_total"],
                parsed["near_imbalance"],
                _utcnow_iso(),
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def db_book_stats(db_path: str) -> Dict[str, Dict[str, Any]]:
    """instrument×book_type 毎の行数と最新 snapshot_time (status API 用)。

    テーブル未作成/DB 不在は空 dict ではなく {"_error": ...} で fail-loud に返す。
    """
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT instrument, book_type, COUNT(*) AS n,"
                " MAX(snapshot_time) AS latest"
                " FROM positioning_snapshots GROUP BY instrument, book_type"
            ).fetchall()
        finally:
            conn.close()
    except Exception as exc:
        return {"_error": {"message": f"{type(exc).__name__}: {exc}"}}
    out: Dict[str, Dict[str, Any]] = {}
    for instrument, book_type, n, latest in rows:
        out[f"{instrument}:{book_type}"] = {
            "rows": int(n),
            "latest_snapshot_time": latest,
            "stale_seconds": _age_seconds(latest),
        }
    return out


def export_snapshots(db_path: str, instrument: str = "", book_type: str = "",
                     since: str = "", limit: int = 5000) -> List[Dict[str, Any]]:
    """研究用 export (JSON API バックエンド)。snapshot_time 昇順。"""
    sql = ("SELECT instrument, book_type, snapshot_time, price, bucket_width,"
           " buckets_json, pct_long_total, pct_short_total, near_imbalance,"
           " fetched_at FROM positioning_snapshots WHERE 1=1")
    params: List[Any] = []
    if instrument:
        sql += " AND instrument = ?"
        params.append(instrument)
    if book_type:
        sql += " AND book_type = ?"
        params.append(book_type)
    if since:
        sql += " AND snapshot_time >= ?"
        params.append(since)
    sql += " ORDER BY snapshot_time ASC LIMIT ?"
    params.append(max(1, int(limit)))
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    out = []
    for (inst, bt, st, price, bw, buckets_json, lt, sh, ni, fa) in rows:
        try:
            buckets = json.loads(buckets_json) if buckets_json else []
        except Exception:
            buckets = None  # 破損 JSON はそのまま可視化 (silent 修復しない)
        out.append({
            "instrument": inst, "book_type": bt, "snapshot_time": st,
            "price": price, "bucket_width": bw, "buckets": buckets,
            "pct_long_total": lt, "pct_short_total": sh,
            "near_imbalance": ni, "fetched_at": fa,
        })
    return out


# ── Worker ──────────────────────────────────────────────────────────

class PositioningIngestWorker:
    """background poller。app.py 起動時に start_positioning_ingest() 経由で生成。"""

    def __init__(self, db_path: str, client: Any,
                 instruments: Optional[List[str]] = None,
                 book_types: Tuple[str, ...] = BOOK_TYPES,
                 poll_sec: int = DEFAULT_POLL_SEC,
                 jitter_sec: int = DEFAULT_JITTER_SEC):
        self._db_path = db_path
        self._client = client
        self.instruments = list(instruments or DEFAULT_INSTRUMENTS)
        self.book_types = tuple(book_types)
        self.poll_sec = int(poll_sec)
        self.jitter_sec = int(jitter_sec)
        # 可観測状態 (status() で露出)
        self._last_saved: Dict[Tuple[str, str], str] = {}
        self._consec_fail: Dict[Tuple[str, str], int] = {}
        self._unsupported: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._dedup_skips = 0
        self._saved_total = 0
        self._poll_cycles = 0
        self._consec_cycle_all_fail = 0
        self._last_cycle_at: Optional[str] = None
        self._last_error = ""
        self._started_at: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._heal_lock = threading.Lock()
        self._restarts = 0
        self._last_restart_at: Optional[str] = None

    # -- lifecycle --

    def start(self) -> None:
        ensure_positioning_schema(self._db_path)
        self._seed_last_saved()
        self._started_at = _utcnow_iso()
        self._thread = threading.Thread(
            target=self._run_forever, name=THREAD_NAME, daemon=True)
        self._thread.start()
        _log(f"worker started: instruments={self.instruments} "
             f"books={list(self.book_types)} poll={self.poll_sec}s"
             f"+jitter<{self.jitter_sec}s db={self._db_path}")

    def stop(self) -> None:
        self._stop.set()

    def ensure_running(self) -> Dict[str, Any]:
        """thread 死を検知したら再起動する (demo_trader StatusHeal パターン)。

        本番実証 (2026-07-14): app.py import 時に起動した thread は gunicorn
        の process ライフサイクル (fork) で request-serving process に生き
        残らない — started_at は copy されるが is_alive=False / poll_cycles=0。
        request 駆動のここが serving process 側での唯一の復活経路。

        heal 条件は「start() 済み (started_at あり) なのに thread が生きて
        いない」に限定する — 未 start の worker (テスト/start_thread=False)
        を勝手に起動しない。明示 stop() 後も復活させない。
        """
        if self._stop.is_set():
            return {"healed": False, "reason": "stopped"}
        if self._started_at is None:
            return {"healed": False, "reason": "never started"}
        if self._thread is not None and self._thread.is_alive():
            return {"healed": False, "reason": "alive"}
        with self._heal_lock:
            if self._thread is not None and self._thread.is_alive():
                return {"healed": False, "reason": "alive"}
            ensure_positioning_schema(self._db_path)
            self._seed_last_saved()  # fork copy のメモリ dedup を DB で温め直す
            self._restarts += 1
            self._last_restart_at = _utcnow_iso()
            _log(f"SELF-HEAL: worker thread dead (process lifecycle) — "
                 f"restarting (restarts={self._restarts})")
            self._thread = threading.Thread(
                target=self._run_forever, name=THREAD_NAME, daemon=True)
            self._thread.start()
        return {"healed": True, "restarts": self._restarts}

    def _seed_last_saved(self) -> None:
        """再起動時、DB の最新 snapshot_time でメモリ dedup を温める。"""
        for key, stats in db_book_stats(self._db_path).items():
            if key == "_error":
                _log(f"seed_last_saved: db_book_stats error: {stats}")
                continue
            instrument, book_type = key.split(":", 1)
            latest = stats.get("latest_snapshot_time")
            if latest:
                self._last_saved[(instrument, book_type)] = latest

    def _run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # fail-loud: 記録して thread は生かす
                self._last_error = f"{_utcnow_iso()} cycle: {type(exc).__name__}: {exc}"
                _log(f"POLL CYCLE FAILED: {self._last_error}")
            delay = self.poll_sec + random.uniform(0, max(0, self.jitter_sec))
            self._stop.wait(delay)

    # -- polling --

    def _fetch(self, instrument: str, book_type: str) -> Tuple[bool, Dict[str, Any]]:
        if book_type == "position":
            return self._client.get_position_book(instrument)
        return self._client.get_order_book(instrument)

    def poll_once(self) -> Dict[str, int]:
        """全 instrument×book を 1 巡。counters を返す (テスト/診断用)。"""
        saved = skipped = failed = 0
        if not getattr(self._client, "_token", ""):
            # token 未設定は全 key 共通の構成エラー — 毎 cycle 1 行だけ loud に出す
            self._last_error = f"{_utcnow_iso()} OANDA token not configured"
            self._consec_cycle_all_fail += 1
            _log("SKIP CYCLE: OANDA token not configured "
                 f"(consecutive={self._consec_cycle_all_fail})")
            self._poll_cycles += 1
            self._last_cycle_at = _utcnow_iso()
            return {"saved": 0, "skipped": 0, "failed": 0}

        for instrument in self.instruments:
            for book_type in self.book_types:
                key = (instrument, book_type)
                if key in self._unsupported:
                    continue
                ok, data = self._fetch(instrument, book_type)
                if not ok:
                    code = (data or {}).get("error")
                    if isinstance(code, int) and 400 <= code < 500 and code != 429:
                        # エンドポイント非対応 (初回 4xx を記録して以後 skip)
                        self._unsupported[key] = {
                            "code": code,
                            "at": _utcnow_iso(),
                            "message": str((data or {}).get("message", ""))[:200],
                        }
                        _log(f"UNSUPPORTED {instrument}/{book_type}Book: "
                             f"http={code} — 以後 skip (可用性マップに記録)")
                        continue
                    failed += 1
                    self._consec_fail[key] = self._consec_fail.get(key, 0) + 1
                    self._last_error = (f"{_utcnow_iso()} {instrument}/{book_type}: "
                                        f"{code}: {str((data or {}).get('message', ''))[:200]}")
                    _log(f"FETCH FAILED {instrument}/{book_type}Book: {code} "
                         f"(consecutive={self._consec_fail[key]})")
                    continue
                payload = extract_book_payload(data)
                if payload is None:
                    failed += 1
                    self._consec_fail[key] = self._consec_fail.get(key, 0) + 1
                    self._last_error = (f"{_utcnow_iso()} {instrument}/{book_type}: "
                                        f"unexpected response shape "
                                        f"keys={sorted((data or {}).keys())[:8]}")
                    _log(f"PARSE FAILED {instrument}/{book_type}Book: no book payload "
                         f"(consecutive={self._consec_fail[key]})")
                    continue
                try:
                    parsed = parse_book(payload)
                except Exception as exc:
                    failed += 1
                    self._consec_fail[key] = self._consec_fail.get(key, 0) + 1
                    self._last_error = (f"{_utcnow_iso()} {instrument}/{book_type}: "
                                        f"parse: {type(exc).__name__}: {exc}")
                    _log(f"PARSE FAILED {instrument}/{book_type}Book: {exc} "
                         f"(consecutive={self._consec_fail[key]})")
                    continue
                if self._last_saved.get(key) == parsed["snapshot_time"]:
                    # OANDA 側未更新 (book time 同一) — 正常系 skip
                    skipped += 1
                    self._dedup_skips += 1
                    self._consec_fail[key] = 0
                    continue
                try:
                    inserted = save_snapshot(self._db_path, instrument,
                                             book_type, parsed)
                except Exception as exc:
                    failed += 1
                    self._consec_fail[key] = self._consec_fail.get(key, 0) + 1
                    self._last_error = (f"{_utcnow_iso()} {instrument}/{book_type}: "
                                        f"db: {type(exc).__name__}: {exc}")
                    _log(f"DB WRITE FAILED {instrument}/{book_type}: {exc} "
                         f"(consecutive={self._consec_fail[key]})")
                    continue
                self._last_saved[key] = parsed["snapshot_time"]
                self._consec_fail[key] = 0
                if inserted:
                    saved += 1
                    self._saved_total += 1
                else:
                    # UNIQUE ignore (再起動直後の再取得など) — dedup 扱い
                    skipped += 1
                    self._dedup_skips += 1

        attempted = saved + skipped + failed
        if attempted > 0 and failed == attempted:
            self._consec_cycle_all_fail += 1
        else:
            self._consec_cycle_all_fail = 0
        self._poll_cycles += 1
        self._last_cycle_at = _utcnow_iso()
        if saved or failed:
            _log(f"cycle done: saved={saved} dedup_skipped={skipped} failed={failed}")
        return {"saved": saved, "skipped": skipped, "failed": failed}

    # -- observability --

    def status(self) -> Dict[str, Any]:
        # StatusHeal (demo_trader 準拠): 観測経路そのものを復活経路にする。
        # 未 start / 明示 stop はヘルパー側の条件で no-op。
        self.ensure_running()
        db_stats = db_book_stats(self._db_path)
        books: Dict[str, Dict[str, Any]] = {}
        for instrument in self.instruments:
            for book_type in self.book_types:
                key = (instrument, book_type)
                skey = f"{instrument}:{book_type}"
                stats = db_stats.get(skey, {})
                books[skey] = {
                    "rows": stats.get("rows", 0),
                    "latest_snapshot_time": stats.get("latest_snapshot_time"),
                    "stale_seconds": stats.get("stale_seconds"),
                    "consecutive_failures": self._consec_fail.get(key, 0),
                    "available": key not in self._unsupported,
                    "unsupported": self._unsupported.get(key),
                }
        return {
            "enabled": True,
            "running": bool(self._thread and self._thread.is_alive()),
            "started_at": self._started_at,
            "instruments": self.instruments,
            "book_types": list(self.book_types),
            "poll_sec": self.poll_sec,
            "jitter_sec": self.jitter_sec,
            "poll_cycles": self._poll_cycles,
            "last_cycle_at": self._last_cycle_at,
            "saved_total": self._saved_total,
            "dedup_skips": self._dedup_skips,
            "consecutive_cycle_failures": self._consec_cycle_all_fail,
            "last_error": self._last_error,
            "restarts": self._restarts,
            "last_restart_at": self._last_restart_at,
            "stale_alert_sec": STALE_ALERT_SEC,
            "db_error": db_stats.get("_error"),
            "books": books,
        }


# ── 可用性 probe (401 帰属確定用、read-only) ─────────────────────────
# 本番実証 (2026-07-14): 全 12 book が HTTP 401。調査で確定した帰属:
# OANDA は 2024-09-14 に retail API での book 提供を終了 (公式告知
# oanda.jp/info/1193、2024-08-30)。v20 book は no-token でも同一の generic
# 401 を返すため、401 単体では token 有効性と判別できない — 本 probe は
# v3/accounts (発注系と同じ認証) を統制にして帰属を機械確認する。
# legacy labs (/labs/v1/orderbook_data) は 2020 年廃止 (現在 WAF の 403 HTML)。
# レスポンスに token / 口座 ID を一切含めないこと (契約、テストで pin)。

PROBE_CHECKS: Tuple[str, ...] = (
    "v3_accounts",             # token 有効性 baseline (発注系と同じ認証)
    "v3_position_book",        # 401 再現 (ingest が使う endpoint)
    "v3_order_book",
    "labs_v1_orderbook_data",  # legacy fxLabs — 区分制限の範囲確定
)


def probe_availability(client: Any, instrument: str = "USD_JPY",
                       labs_instrument: str = "EUR_USD") -> Dict[str, Any]:
    """OANDA book 可用性を本番 token で検証し、401 の帰属を返す。

    返り値に secret を含めない: ok/http/message (OANDA エラー本文 300 字) のみ。
    v3_accounts 成功時も口座 ID は返さず件数だけにする。
    """
    if not getattr(client, "_token", ""):
        return {"token_configured": False, "checks": {},
                "interpretation": "OANDA token 未設定 — probe 実行不可"}

    def _entry(ok: bool, data: Dict[str, Any], ok_summary: str) -> Dict[str, Any]:
        if ok:
            return {"ok": True, "http": 200, "message": ok_summary}
        return {"ok": False, "http": (data or {}).get("error"),
                "message": str((data or {}).get("message", ""))[:300]}

    checks: Dict[str, Dict[str, Any]] = {}
    ok, data = client.get_accounts()
    n_accounts = len((data or {}).get("accounts", [])) if ok else 0
    checks["v3_accounts"] = _entry(ok, data, f"accounts={n_accounts}")
    ok, data = client.get_position_book(instrument)
    checks["v3_position_book"] = _entry(ok, data, "position book 取得可")
    ok, data = client.get_order_book(instrument)
    checks["v3_order_book"] = _entry(ok, data, "order book 取得可")
    ok, data = client.get_labs_orderbook_data(labs_instrument, 3600)
    checks["labs_v1_orderbook_data"] = _entry(
        ok, data, f"labs orderbook 取得可 keys={sorted((data or {}).keys())[:5]}")

    return {
        "token_configured": True,
        "instrument": instrument,
        "labs_instrument": labs_instrument,
        "checks": checks,
        "interpretation": _interpret_probe(checks),
        "probed_at": _utcnow_iso(),
    }


def _interpret_probe(checks: Dict[str, Dict[str, Any]]) -> str:
    accounts_ok = checks["v3_accounts"]["ok"]
    books_401 = all(checks[k]["http"] == 401
                    for k in ("v3_position_book", "v3_order_book"))
    labs = checks["labs_v1_orderbook_data"]
    if not accounts_ok:
        return (f"v3/accounts が {checks['v3_accounts']['http']} — "
                "token 失効/無効の可能性。401 帰属は token 側")
    if books_401 and labs["ok"]:
        return ("token 有効 (v3/accounts 200)。v20 book のみ 401 で "
                "labs は取得可 → labs 経由の代替取得が可能")
    if books_401:
        return ("token 有効 (v3/accounts 200) だが v20 book が 401 → "
                "OANDA の retail API book 提供終了 (2024-09-14, "
                "oanda.jp/info/1193) に合致。token/口座区分の問題ではなく "
                f"データ製品自体が API から撤収済み (labs={labs['http']}, "
                "2020 年廃止)")
    return "v20 book 取得可 — 401 は解消している (提供終了の巻き戻し?)"


def run_probe(instrument: str = "USD_JPY",
              labs_instrument: str = "EUR_USD") -> Dict[str, Any]:
    """env の本番 token で probe を実行 (app.py /api/positioning/probe 用)。"""
    from modules.oanda_client import OandaClient
    return probe_availability(OandaClient(), instrument=instrument,
                              labs_instrument=labs_instrument)


# ── module-level singleton (app.py 起動時に設定、API から参照) ──────────

_worker: Optional[PositioningIngestWorker] = None


def get_worker() -> Optional[PositioningIngestWorker]:
    return _worker


def ensure_worker_running() -> Optional[Dict[str, Any]]:
    """singleton worker の self-heal (app.py before_request heartbeat 用)。

    worker 未生成 (ENABLE=0 / 非 Render / 起動失敗) は None — ここで勝手に
    生成はしない (起動判断は start_positioning_ingest の env gate に一元化)。
    """
    if _worker is None:
        return None
    return _worker.ensure_running()


def start_positioning_ingest(db_path: str, client: Any = None,
                             start_thread: bool = True
                             ) -> Optional[PositioningIngestWorker]:
    """env を解決して worker を生成・開始する (app.py 起動フックから呼ぶ)。

    POSITIONING_INGEST_ENABLE   default "1" — "1" 以外で無効
    POSITIONING_INSTRUMENTS     カンマ区切り override (例 "USD_JPY,EUR_USD")
    POSITIONING_POLL_SEC        poll 間隔 (default 1200)
    """
    global _worker
    if os.environ.get("POSITIONING_INGEST_ENABLE", "1") != "1":
        _log("disabled via POSITIONING_INGEST_ENABLE — worker not started")
        return None
    if _worker is not None:
        _log("already started — reusing existing worker")
        return _worker

    instruments_env = os.environ.get("POSITIONING_INSTRUMENTS", "")
    instruments = ([s.strip() for s in instruments_env.split(",") if s.strip()]
                   if instruments_env else list(DEFAULT_INSTRUMENTS))
    try:
        poll_sec = int(os.environ.get("POSITIONING_POLL_SEC", DEFAULT_POLL_SEC))
    except ValueError:
        _log(f"invalid POSITIONING_POLL_SEC="
             f"{os.environ.get('POSITIONING_POLL_SEC')!r} — using default")
        poll_sec = DEFAULT_POLL_SEC

    if client is None:
        from modules.oanda_client import OandaClient
        client = OandaClient()

    worker = PositioningIngestWorker(
        db_path, client, instruments=instruments, poll_sec=poll_sec)
    if start_thread:
        worker.start()
    else:
        ensure_positioning_schema(db_path)
        worker._seed_last_saved()
    _worker = worker
    return worker


# ── helpers ─────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_seconds(rfc3339: Optional[str]) -> Optional[int]:
    """RFC3339 (ナノ秒付き可) → 経過秒。parse 不能は None。"""
    if not rfc3339:
        return None
    txt = str(rfc3339).strip()
    if txt.endswith("Z"):
        txt = txt[:-1]
    if "." in txt:  # OANDA はナノ秒精度を返すことがある
        txt = txt.split(".", 1)[0]
    try:
        dt = datetime.strptime(txt, "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None
    return int((datetime.now(timezone.utc) - dt).total_seconds())


def _log(msg: str) -> None:
    """Render ログ (stdout) と logging の両方へ fail-loud 出力。"""
    print(f"[positioning] {msg}", flush=True)
    logger.info(msg)
