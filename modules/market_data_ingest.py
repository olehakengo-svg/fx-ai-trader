"""
R3 market-data ingest — 外部仮説スキャン round-2 (E7/E12) の read-only データ基盤。

目的 (2026-07-18, rule:R3 — E1 positioning ingest 2026-07-14 と同じ決裁枠):
  external-hypothesis-scan-round2-2026-07-18 の「今から始めないと不可逆な
  インフラ」のうち、コンプライアンス検証を通過した 2 系統の go-forward
  capture を開始する。live 発注・戦略・Kelly には一切関与しない。

  (1) ForexFactory 経済カレンダー (E7 event-surprise の clean OOS 蓄積):
      faireconomy 週次 JSON (FF 公式配信 feed) には Actual フィールドが無い
      (2026-07-18 実 fetch 確認: keys = country/date/forecast/impact/
      previous/title のみ)。本 job は feed を 6h 毎 capture し、
      **翌期 previous 逆引き** (次回発表行の previous = 前回の actual) で
      actual を補完する。FF 本体ページの scrape は Cloudflare challenge
      (403 実測) のため実装しない — bypass 構築は行わない方針。
      歴史 gap (2023-04〜) は tools/ff_calendar_import.py の import 経路で
      正規入手データを同テーブルに合流させる。
      注意 (E7 pre-reg で宣言必須): previous 逆引きの actual は「次回発表
      時点の改定値」であり first print ではない。US 系は ALFRED vintage で
      first print を別途復元可能 (research 時タスク)。
  (2) CME FX 先物 1h volume (E12 flow proxy の検証歴史延伸):
      yfinance 60m は 730d rolling 窓 (2026-07-18 実測: 左端 2024-02-23) —
      今日から SQLite に追記しないと検証歴史が 2y 固定のまま毎日 1 日ずつ
      消える。日次 capture で単調延伸させる。
  (3) CME settlement/OI scrape は**不実装** — probe (2026-07-18) が
      「scraping は CME Data Terms of Use で禁止」の明示 403 を返した。
      代替 = Databento (licensed distributor、歴史も保持するため
      「今から貯めないと不可逆」は item (3) には当てはまらない)。
      詳細: knowledge-base/wiki/analyses/market-data-ingest-2026-07-18.md

設計 (modules/positioning_ingest.py のパターンに準拠):
  - fail-loud: 連続失敗カウント/最終エラーを status に露出。silent except 禁止
  - モジュールトップ副作用禁止 — env 読み・fetch は全て関数内
  - defer_thread: gunicorn master では thread を起動しない (fork-safety §11)
  - health 記録: market_ingest_health (upsert) + market_ingest_health_log
    (append、同一トランザクション) — 「dedup skip」と「fetch 失敗」を
    DB の行だけから識別可能にする
  - dedup: DB UNIQUE 制約 + feed content-hash (プロセス再起動に耐える)
  - forecast 凍結: event_time 通過後は forecast/previous/impact を更新しない
    (発表前の最終 forecast が E7 surprise の estimand — 事後改変を構造で防ぐ)

検証 API (app.py): /api/marketdata/status, /api/marketdata/export
テスト: tests/test_market_data_ingest.py (offline/deterministic)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:  # pragma: no cover - CI/本番には requests がある
    _HAS_REQUESTS = False

logger = logging.getLogger("market_data_ingest")

# ── 定数 (env override は start_market_data_ingest 内で解決) ──
FF_FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
DEFAULT_FF_POLL_SEC = 21600        # 6h — 週内の forecast 改定/日程変更を capture
MIN_FF_POLL_SEC = 3600             # feed 提供元への配慮 (≤24 req/日)
DEFAULT_CME_POLL_SEC = 86400       # 24h — 730d rolling 窓に対し十分な余裕
MIN_CME_POLL_SEC = 21600
RETRY_SEC = 1800                   # 失敗時の再試行間隔 (通常間隔より短く)
DEFAULT_TICK_SEC = 300             # worker の起床間隔 (job due 判定)
DEFAULT_JITTER_SEC = 60
FETCH_TIMEOUT_SEC = 20
STALE_ALERT_FF_SEC = 24 * 3600     # 監視基準: verified が 24h 超 stale で要調査
STALE_ALERT_CME_SEC = 3 * 24 * 3600  # 週末 (市場閉鎖 ~2.5d) を跨いでも誤警報しない

# CME FX 先物 (USD 建て 7 通貨 = 13 ペア universe の base 通貨を網羅)
DEFAULT_CME_SYMBOLS: Tuple[str, ...] = (
    "6E=F", "6J=F", "6B=F", "6A=F", "6C=F", "6S=F", "6N=F",
)
YF_PERIOD = "8d"                   # 日次 capture + 週末跨ぎの overlap
BAR_SEC = 3600

THREAD_NAME = "market-data-ingest"
JOB_FF = "ff_calendar"
JOB_CME = "cme_bars"

_ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"

# ── Schema (単一ソース — modules/demo_db.py の _init_tables からも呼ばれる) ──
# ff_calendar_events: UNIQUE(country, title, event_time_utc) が event の識別子。
#   actual は後段 (reconcile / import) が埋める — actual_source で来歴を明示。
# ff_feed_snapshots: 生 feed の content-hash dedup 保存 (parse バグからの
#   全量リカバリ経路。feed は ~13KB、内容変化時のみ 1 行)。
# cme_fx_bars_1h: UNIQUE(symbol, bar_time_utc)。INSERT OR IGNORE で初回 capture
#   値を凍結 (yfinance の事後補正で歴史が動くのを防ぐ — BT 再現性優先)。
_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ff_calendar_events (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    country            TEXT NOT NULL,
    title              TEXT NOT NULL,
    event_time_utc     TEXT NOT NULL,
    impact             TEXT,
    forecast           TEXT,
    previous           TEXT,
    actual             TEXT,
    actual_source      TEXT,       -- 'next_previous' | 'import:<tag>'
    actual_recorded_at TEXT,
    first_seen_at      TEXT,
    last_seen_at       TEXT,
    UNIQUE(country, title, event_time_utc)
);
CREATE INDEX IF NOT EXISTS idx_ff_cal_time
    ON ff_calendar_events(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_ff_cal_series
    ON ff_calendar_events(country, title, event_time_utc);
CREATE TABLE IF NOT EXISTS ff_feed_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content_key TEXT NOT NULL UNIQUE,   -- sha256(canonical JSON)
    payload_json TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cme_fx_bars_1h (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    bar_time_utc TEXT NOT NULL,
    open         REAL,
    high         REAL,
    low          REAL,
    close        REAL,
    volume       INTEGER,
    fetched_at   TEXT,
    UNIQUE(symbol, bar_time_utc)
);
CREATE INDEX IF NOT EXISTS idx_cme_bars
    ON cme_fx_bars_1h(symbol, bar_time_utc);
CREATE TABLE IF NOT EXISTS market_ingest_health (
    key   TEXT PRIMARY KEY,     -- 'verified:{job}' | 'last_cycle_at'
    value TEXT NOT NULL         -- ISO8601 UTC
);
CREATE TABLE IF NOT EXISTS market_ingest_health_log (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    key   TEXT NOT NULL,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mkt_health_log_key
    ON market_ingest_health_log(key, id);
"""


def ensure_market_data_schema(conn_or_path) -> None:
    """market-data ingest 系テーブルを冪等作成 (ensure_positioning_schema 準拠)。"""
    if hasattr(conn_or_path, "executescript"):
        conn_or_path.executescript(_TABLE_DDL)
        return
    conn = sqlite3.connect(conn_or_path)
    try:
        conn.executescript(_TABLE_DDL)
        conn.commit()
    finally:
        conn.close()


# ── FF calendar: parse / upsert / reconcile (純関数系 — テスト対象) ────

def parse_ff_event(ev: Dict[str, Any]) -> Dict[str, Any]:
    """faireconomy feed の 1 event → 保存用 dict (UTC 正規化)。

    feed 実測 schema (2026-07-18): {"title","country","date"(ISO+offset),
    "impact","forecast","previous"} — Actual フィールドは存在しない。
    必須キー欠落/naive date は ValueError (呼び出し側が失敗カウント)。
    """
    if not isinstance(ev, dict):
        raise ValueError(f"ff event is not a dict: {type(ev).__name__}")
    for key in ("title", "country", "date"):
        if not ev.get(key):
            raise ValueError(f"ff event missing required key: {key}")
    dt = _parse_iso(str(ev["date"]))
    return {
        "country": str(ev["country"]).strip().upper(),
        "title": str(ev["title"]).strip(),
        "event_time_utc": dt.astimezone(timezone.utc).strftime(_ISO_FMT),
        "impact": str(ev.get("impact") or ""),
        "forecast": str(ev.get("forecast") or ""),
        "previous": str(ev.get("previous") or ""),
    }


def feed_content_key(raw: Any) -> str:
    """feed 全体の content dedup 用の決定的 key (outlook_content_key 準拠)。"""
    blob = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def save_feed_snapshot(conn: sqlite3.Connection, raw: Any,
                       fetched_at: str) -> bool:
    """生 feed を content-hash dedup で保存。新規行なら True。"""
    cur = conn.execute(
        "INSERT OR IGNORE INTO ff_feed_snapshots"
        " (content_key, payload_json, fetched_at) VALUES (?, ?, ?)",
        (feed_content_key(raw),
         json.dumps(raw, separators=(",", ":"), ensure_ascii=False),
         fetched_at),
    )
    return cur.rowcount > 0


def upsert_ff_event(conn: sqlite3.Connection, parsed: Dict[str, Any],
                    now_iso: str) -> str:
    """event を UNIQUE(country,title,event_time_utc) キーで upsert。

    返り値: 'inserted' | 'revised' | 'seen'。
    forecast 凍結ルール: event_time_utc が now を過ぎた行は forecast/previous/
    impact を**更新しない** (発表前の最終 forecast = E7 surprise の estimand。
    事後の feed 側改変が estimand を汚染しないよう構造で防ぐ)。
    """
    row = conn.execute(
        "SELECT id, forecast, previous, impact FROM ff_calendar_events"
        " WHERE country = ? AND title = ? AND event_time_utc = ?",
        (parsed["country"], parsed["title"], parsed["event_time_utc"]),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO ff_calendar_events"
            " (country, title, event_time_utc, impact, forecast, previous,"
            "  first_seen_at, last_seen_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (parsed["country"], parsed["title"], parsed["event_time_utc"],
             parsed["impact"], parsed["forecast"], parsed["previous"],
             now_iso, now_iso),
        )
        return "inserted"
    eid, f0, p0, i0 = row
    if parsed["event_time_utc"] > now_iso and (
            (f0 or "", p0 or "", i0 or "") !=
            (parsed["forecast"], parsed["previous"], parsed["impact"])):
        conn.execute(
            "UPDATE ff_calendar_events SET forecast = ?, previous = ?,"
            " impact = ?, last_seen_at = ? WHERE id = ?",
            (parsed["forecast"], parsed["previous"], parsed["impact"],
             now_iso, eid),
        )
        return "revised"
    conn.execute(
        "UPDATE ff_calendar_events SET last_seen_at = ? WHERE id = ?",
        (now_iso, eid))
    return "seen"


def reconcile_actuals(conn: sqlite3.Connection, now_iso: str) -> int:
    """翌期 previous 逆引き: 同一系列 (country,title) の次回発表行の previous を
    直前回の actual として補完する。埋めた行数を返す (冪等)。

    制約 (E7 pre-reg で宣言必須):
      - 得られる actual は「次回発表時点の改定値」— first print ではない
      - 補完対象は actual IS NULL かつ event_time 通過済みの行のみ
      - 既に actual を持つ行 (import 済み等) は上書きしない
    """
    rows = conn.execute(
        "SELECT id, country, title, event_time_utc, previous, actual"
        " FROM ff_calendar_events"
        " ORDER BY country, title, event_time_utc",
    ).fetchall()
    filled = 0
    prev_row: Optional[Tuple] = None
    for row in rows:
        rid, country, title, etime, previous, actual = row
        if (prev_row is not None
                and prev_row[1] == country and prev_row[2] == title):
            p_id, _, _, p_etime, _, p_actual = prev_row
            if (p_actual is None and p_etime < now_iso
                    and previous not in (None, "")):
                conn.execute(
                    "UPDATE ff_calendar_events SET actual = ?,"
                    " actual_source = 'next_previous',"
                    " actual_recorded_at = ? WHERE id = ? AND actual IS NULL",
                    (previous, now_iso, p_id),
                )
                filled += 1
        prev_row = row
    return filled


def http_fetch_ff_feed(url: str = FF_FEED_URL) -> Tuple[bool, Dict[str, Any]]:
    """faireconomy 週次 JSON を fetch。(ok, {"events": [...]}) を返す。

    FF 公式配信 feed (widget 用に公開されているもの) のみを叩く —
    FF 本体ページ (Cloudflare challenge) への scrape は行わない。
    """
    if not _HAS_REQUESTS:  # pragma: no cover
        return False, {"error": "transport", "message": "requests not installed"}
    try:
        resp = _requests.get(
            url, timeout=FETCH_TIMEOUT_SEC,
            headers={"User-Agent": "fx-ai-trader-research/1.0 (read-only)"})
    except Exception as exc:
        return False, {"error": "transport",
                       "message": f"{type(exc).__name__}: {exc}"}
    if resp.status_code != 200:
        return False, {"error": resp.status_code,
                       "message": str(resp.text)[:200]}
    try:
        data = resp.json()
    except Exception as exc:
        return False, {"error": "parse",
                       "message": f"{type(exc).__name__}: {exc}"}
    if not isinstance(data, list):
        return False, {"error": "shape",
                       "message": f"expected list, got {type(data).__name__}"}
    return True, {"events": data}


# ── CME 1h bars: fetch / filter / save (fetch は injectable) ──────────

def yf_fetch_bars(symbol: str, period: str = YF_PERIOD) -> List[Dict[str, Any]]:
    """yfinance 60m bars → 行 dict list (UTC 正規化)。失敗は例外 (fail-loud)。

    yfinance import は関数内 (BT/テスト経路のモジュール import を汚さない)。
    """
    import yfinance as yf
    df = yf.download(symbol, interval="60m", period=period, progress=False,
                     auto_adjust=False, threads=False)
    if df is None or len(df) == 0:
        raise ValueError(f"yfinance empty response for {symbol}")
    if getattr(df.columns, "nlevels", 1) > 1:  # 単一 ticker でも MultiIndex
        df.columns = df.columns.get_level_values(0)
    out: List[Dict[str, Any]] = []
    for ts, row in df.iterrows():
        close = row.get("Close")
        if close is None or close != close:  # NaN 行 (取引なし) は skip
            continue
        ts_utc = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
        vol = row.get("Volume")
        out.append({
            "bar_time_utc": ts_utc.strftime(_ISO_FMT),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(close),
            "volume": int(vol) if vol == vol else 0,
        })
    return out


def filter_closed_bars(rows: List[Dict[str, Any]], now_iso: str,
                       bar_sec: int = BAR_SEC) -> List[Dict[str, Any]]:
    """形成中 bar (bar_time + bar_sec > now) を除外 — 部分 volume の凍結を防ぐ。

    INSERT OR IGNORE は初回 capture 値を凍結するため、閉じていない bar を
    入れると partial volume が永久保存される。ここで構造的に防ぐ。
    """
    now_dt = _parse_iso(now_iso)
    out = []
    for r in rows:
        try:
            bar_dt = _parse_iso(r["bar_time_utc"])
        except (ValueError, KeyError):
            continue  # 呼び出し側 fetcher が既に正規化済み — 異常行は落とす
        if (now_dt - bar_dt).total_seconds() >= bar_sec:
            out.append(r)
    return out


def save_bars(db_path: str, symbol: str,
              rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    """bars を INSERT OR IGNORE で保存。(新規, dedup) 件数を返す。"""
    saved = dup = 0
    conn = sqlite3.connect(db_path)
    try:
        for r in rows:
            cur = conn.execute(
                "INSERT OR IGNORE INTO cme_fx_bars_1h"
                " (symbol, bar_time_utc, open, high, low, close, volume,"
                "  fetched_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (symbol, r["bar_time_utc"], r["open"], r["high"], r["low"],
                 r["close"], r["volume"], _utcnow_iso()),
            )
            if cur.rowcount > 0:
                saved += 1
            else:
                dup += 1
        conn.commit()
    finally:
        conn.close()
    return saved, dup


# ── health / stats (positioning_ingest の 2 テーブルパターン準拠) ──────

def record_health(db_path: str, entries: Dict[str, str]) -> None:
    """market_ingest_health upsert + health_log append (同一トランザクション)。"""
    if not entries:
        return
    items = list(entries.items())
    conn = sqlite3.connect(db_path)
    try:
        conn.executemany(
            "INSERT INTO market_ingest_health (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            items,
        )
        conn.executemany(
            "INSERT INTO market_ingest_health_log (key, value) VALUES (?, ?)",
            items,
        )
        conn.commit()
    finally:
        conn.close()


def db_health(db_path: str) -> Dict[str, Any]:
    """market_ingest_health の全行 (status API 用)。fail-loud。"""
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT key, value FROM market_ingest_health").fetchall()
        finally:
            conn.close()
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}
    return {k: v for k, v in rows}


def db_market_stats(db_path: str) -> Dict[str, Any]:
    """各テーブルの行数・最新時刻 (status API 用)。fail-loud。"""
    try:
        conn = sqlite3.connect(db_path)
        try:
            out: Dict[str, Any] = {}
            n, latest = conn.execute(
                "SELECT COUNT(*), MAX(event_time_utc)"
                " FROM ff_calendar_events").fetchone()
            n_act = conn.execute(
                "SELECT COUNT(*) FROM ff_calendar_events"
                " WHERE actual IS NOT NULL").fetchone()[0]
            out["ff_calendar_events"] = {
                "rows": int(n), "latest_event_time": latest,
                "rows_with_actual": int(n_act),
            }
            n, latest = conn.execute(
                "SELECT COUNT(*), MAX(fetched_at)"
                " FROM ff_feed_snapshots").fetchone()
            out["ff_feed_snapshots"] = {"rows": int(n), "latest_fetched_at": latest}
            out["cme_fx_bars_1h"] = {}
            for sym, cnt, lo, hi in conn.execute(
                    "SELECT symbol, COUNT(*), MIN(bar_time_utc),"
                    " MAX(bar_time_utc) FROM cme_fx_bars_1h GROUP BY symbol"):
                out["cme_fx_bars_1h"][sym] = {
                    "rows": int(cnt), "first_bar": lo, "latest_bar": hi,
                    "stale_seconds": _age_seconds(hi),
                }
            return out
        finally:
            conn.close()
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


# ── 研究用 export (read-only、app.py /api/marketdata/export バックエンド) ──

def export_ff_events(db_path: str, country: str = "", impact: str = "",
                     since: str = "", until: str = "",
                     limit: int = 20000) -> List[Dict[str, Any]]:
    sql = ("SELECT country, title, event_time_utc, impact, forecast,"
           " previous, actual, actual_source, actual_recorded_at,"
           " first_seen_at, last_seen_at FROM ff_calendar_events WHERE 1=1")
    params: List[Any] = []
    if country:
        sql += " AND country = ?"
        params.append(country.upper())
    if impact:
        sql += " AND impact = ?"
        params.append(impact)
    if since:
        sql += " AND event_time_utc >= ?"
        params.append(since)
    if until:
        sql += " AND event_time_utc <= ?"
        params.append(until)
    sql += " ORDER BY event_time_utc ASC LIMIT ?"
    params.append(max(1, int(limit)))
    conn = sqlite3.connect(db_path)
    try:
        cols = ["country", "title", "event_time_utc", "impact", "forecast",
                "previous", "actual", "actual_source", "actual_recorded_at",
                "first_seen_at", "last_seen_at"]
        return [dict(zip(cols, r)) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def export_cme_bars(db_path: str, symbol: str = "", since: str = "",
                    limit: int = 20000) -> List[Dict[str, Any]]:
    sql = ("SELECT symbol, bar_time_utc, open, high, low, close, volume,"
           " fetched_at FROM cme_fx_bars_1h WHERE 1=1")
    params: List[Any] = []
    if symbol:
        sql += " AND symbol = ?"
        params.append(symbol)
    if since:
        sql += " AND bar_time_utc >= ?"
        params.append(since)
    sql += " ORDER BY bar_time_utc ASC LIMIT ?"
    params.append(max(1, int(limit)))
    conn = sqlite3.connect(db_path)
    try:
        cols = ["symbol", "bar_time_utc", "open", "high", "low", "close",
                "volume", "fetched_at"]
        return [dict(zip(cols, r)) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def export_health_log(db_path: str, key: str = "", since_id: int = 0,
                      limit: int = 20000) -> List[Dict[str, Any]]:
    sql = "SELECT id, key, value FROM market_ingest_health_log WHERE id > ?"
    params: List[Any] = [int(since_id)]
    if key:
        sql += " AND key = ?"
        params.append(key)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(max(1, int(limit)))
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [{"id": int(i), "key": k, "value": v} for i, k, v in rows]


# ── Worker ──────────────────────────────────────────────────────────

class MarketDataIngestWorker:
    """background poller。app.py 起動時に start_market_data_ingest() 経由で生成。

    2 job を単一 thread で回す (job 毎に due 管理):
      ff_calendar — feed capture + upsert + actual reconcile (default 6h)
      cme_bars    — yfinance 60m capture ×7 symbols (default 24h)
    """

    def __init__(self, db_path: str,
                 ff_fetch: Optional[Callable[[], Tuple[bool, Dict[str, Any]]]] = None,
                 bars_fetch: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
                 symbols: Optional[List[str]] = None,
                 ff_poll_sec: int = DEFAULT_FF_POLL_SEC,
                 cme_poll_sec: int = DEFAULT_CME_POLL_SEC,
                 tick_sec: int = DEFAULT_TICK_SEC,
                 jitter_sec: int = DEFAULT_JITTER_SEC,
                 ff_url: str = FF_FEED_URL):
        self._db_path = db_path
        self._ff_url = ff_url
        self._ff_fetch = ff_fetch or (lambda: http_fetch_ff_feed(self._ff_url))
        self._bars_fetch = bars_fetch or yf_fetch_bars
        self.symbols = list(symbols or DEFAULT_CME_SYMBOLS)
        self.ff_poll_sec = max(MIN_FF_POLL_SEC, int(ff_poll_sec))
        if int(ff_poll_sec) < MIN_FF_POLL_SEC:
            _log(f"ff_poll_sec={ff_poll_sec} < {MIN_FF_POLL_SEC}s — clamp")
        self.cme_poll_sec = max(MIN_CME_POLL_SEC, int(cme_poll_sec))
        if int(cme_poll_sec) < MIN_CME_POLL_SEC:
            _log(f"cme_poll_sec={cme_poll_sec} < {MIN_CME_POLL_SEC}s — clamp")
        self.tick_sec = int(tick_sec)
        self.jitter_sec = int(jitter_sec)
        # job due 管理 (monotonic ではなく wall clock — restart 跨ぎは health seed)
        self._next_due: Dict[str, float] = {JOB_FF: 0.0, JOB_CME: 0.0}
        # 可観測状態 (status() で露出)
        self._consec_fail: Dict[str, int] = {}
        self._counters: Dict[str, int] = {}
        self._poll_cycles = 0
        self._last_cycle_at: Optional[str] = None
        self._last_error = ""
        self._phase = "idle"
        self._phase_since: Optional[str] = None
        self._started_at: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._heal_lock = threading.Lock()
        self._restarts = 0
        self._last_restart_at: Optional[str] = None

    # -- lifecycle (positioning_ingest 準拠) --

    def start(self) -> None:
        ensure_market_data_schema(self._db_path)
        self._seed_next_due()
        self._started_at = _utcnow_iso()
        self._thread = threading.Thread(
            target=self._run_forever, name=THREAD_NAME, daemon=True)
        self._thread.start()
        _log(f"worker started: symbols={self.symbols} "
             f"ff_poll={self.ff_poll_sec}s cme_poll={self.cme_poll_sec}s "
             f"tick={self.tick_sec}s db={self._db_path}")

    def stop(self) -> None:
        self._stop.set()

    def ensure_running(self) -> Dict[str, Any]:
        """thread 死の検知と再起動 (PositioningIngestWorker.ensure_running 準拠)。

        heal 条件は「start()/defer 済み (started_at あり) なのに thread が
        生きていない」に限定 — 未 start の worker を勝手に起動しない。
        明示 stop() 後も復活させない。
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
            ensure_market_data_schema(self._db_path)
            self._seed_next_due()
            self._restarts += 1
            self._last_restart_at = _utcnow_iso()
            _log(f"SELF-HEAL: worker thread dead (process lifecycle) — "
                 f"restarting (restarts={self._restarts})")
            self._thread = threading.Thread(
                target=self._run_forever, name=THREAD_NAME, daemon=True)
            self._thread.start()
        return {"healed": True, "restarts": self._restarts}

    def _seed_next_due(self) -> None:
        """restart 跨ぎで即再実行しないよう health の verified から due を温める。

        gunicorn の頻繁な fork/restart で外部 API を叩き直すのを防ぐ。
        verified が無い/古い job は due=0 (即実行)。
        """
        health = db_health(self._db_path)
        now = time.time()
        age_ff = _age_seconds(health.get("verified:ff_calendar"))
        if age_ff is not None and age_ff < self.ff_poll_sec:
            self._next_due[JOB_FF] = now + (self.ff_poll_sec - age_ff)
        ages = [_age_seconds(health.get(f"verified:cme_bars:{s}"))
                for s in self.symbols]
        known = [a for a in ages if a is not None]
        if known and len(known) == len(ages) and max(known) < self.cme_poll_sec:
            self._next_due[JOB_CME] = now + (self.cme_poll_sec - max(known))

    def _run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # fail-loud: 記録して thread は生かす
                self._last_error = (f"{_utcnow_iso()} cycle: "
                                    f"{type(exc).__name__}: {exc}")
                _log(f"POLL CYCLE FAILED: {self._last_error}")
            delay = self.tick_sec + random.uniform(0, max(0, self.jitter_sec))
            self._stop.wait(delay)

    # -- polling --

    def poll_once(self, force: bool = False) -> Dict[str, Any]:
        """due な job を実行 (force=True で全 job 強制)。counters を返す。"""
        now = time.time()
        ran: List[str] = []
        result: Dict[str, Any] = {}
        if force or now >= self._next_due[JOB_FF]:
            result[JOB_FF] = self._run_ff_cycle()
            ran.append(JOB_FF)
        if force or now >= self._next_due[JOB_CME]:
            result[JOB_CME] = self._run_cme_cycle()
            ran.append(JOB_CME)
        self._poll_cycles += 1
        self._last_cycle_at = _utcnow_iso()
        self._record_health_safe({"last_cycle_at": self._last_cycle_at})
        result["ran"] = ran
        self._set_phase("idle")
        return result

    def _run_ff_cycle(self) -> Dict[str, int]:
        """feed fetch → snapshot 保存 → event upsert → actual reconcile。"""
        self._set_phase("fetch ff feed")
        ok, data = self._ff_fetch()
        if not ok:
            self._job_failed(JOB_FF, f"feed fetch: {(data or {}).get('error')}: "
                                     f"{str((data or {}).get('message', ''))[:200]}")
            self._next_due[JOB_FF] = time.time() + min(self.ff_poll_sec,
                                                       RETRY_SEC)
            return {"saved": 0, "revised": 0, "seen": 0, "failed": 1,
                    "actual_filled": 0}
        self._set_phase("process ff feed")
        events = data.get("events") or []
        now_iso = _utcnow_iso()
        saved = revised = seen = failed = 0
        parse_errors: List[str] = []
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                save_feed_snapshot(conn, events, now_iso)
                for ev in events:
                    try:
                        parsed = parse_ff_event(ev)
                    except Exception as exc:
                        failed += 1
                        parse_errors.append(f"{type(exc).__name__}: {exc}")
                        continue
                    outcome = upsert_ff_event(conn, parsed, now_iso)
                    if outcome == "inserted":
                        saved += 1
                    elif outcome == "revised":
                        revised += 1
                    else:
                        seen += 1
                actual_filled = reconcile_actuals(conn, now_iso)
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            # DB 層の失敗 — verified を更新しない (LOCF 汚染防止、fail-loud)
            self._job_failed(JOB_FF, f"db: {type(exc).__name__}: {exc}")
            self._next_due[JOB_FF] = time.time() + min(self.ff_poll_sec,
                                                       RETRY_SEC)
            return {"saved": saved, "revised": revised, "seen": seen,
                    "failed": failed + 1, "actual_filled": 0}
        if parse_errors:
            self._last_error = (f"{now_iso} ff parse ({failed} events): "
                                f"{parse_errors[0]}")
            _log(f"FF PARSE FAILED for {failed}/{len(events)} events: "
                 f"{parse_errors[0]}")
        self._consec_fail[JOB_FF] = 0
        self._bump("ff_saved", saved)
        self._bump("ff_revised", revised)
        self._bump("ff_actual_filled", actual_filled)
        self._record_health_safe({"verified:ff_calendar": now_iso})
        self._next_due[JOB_FF] = time.time() + self.ff_poll_sec
        if saved or revised or actual_filled or failed:
            _log(f"ff cycle: inserted={saved} revised={revised} seen={seen} "
                 f"actual_filled={actual_filled} parse_failed={failed}")
        return {"saved": saved, "revised": revised, "seen": seen,
                "failed": failed, "actual_filled": actual_filled}

    def _run_cme_cycle(self) -> Dict[str, int]:
        """全 symbol の 60m bars を capture (閉じた bar のみ)。"""
        saved_total = dup_total = failed = 0
        now_iso = _utcnow_iso()
        verified: Dict[str, str] = {}
        for sym in self.symbols:
            self._set_phase(f"fetch cme bars {sym}")
            key = f"{JOB_CME}:{sym}"
            try:
                rows = self._bars_fetch(sym)
            except Exception as exc:
                failed += 1
                self._consec_fail[key] = self._consec_fail.get(key, 0) + 1
                self._last_error = (f"{now_iso} {sym}: fetch: "
                                    f"{type(exc).__name__}: {exc}")
                _log(f"FETCH FAILED {sym}: {exc} "
                     f"(consecutive={self._consec_fail[key]})")
                continue
            closed = filter_closed_bars(rows, _utcnow_iso())
            try:
                saved, dup = save_bars(self._db_path, sym, closed)
            except Exception as exc:
                failed += 1
                self._consec_fail[key] = self._consec_fail.get(key, 0) + 1
                self._last_error = (f"{now_iso} {sym}: db: "
                                    f"{type(exc).__name__}: {exc}")
                _log(f"DB WRITE FAILED {sym}: {exc} "
                     f"(consecutive={self._consec_fail[key]})")
                continue
            self._consec_fail[key] = 0
            verified[f"verified:{JOB_CME}:{sym}"] = now_iso
            saved_total += saved
            dup_total += dup
        self._set_phase("process cme bars")
        if verified:
            self._record_health_safe(verified)
        self._bump("cme_saved", saved_total)
        if failed:
            self._consec_fail[JOB_CME] = self._consec_fail.get(JOB_CME, 0) + 1
            self._next_due[JOB_CME] = time.time() + min(self.cme_poll_sec,
                                                        RETRY_SEC)
        else:
            self._consec_fail[JOB_CME] = 0
            self._next_due[JOB_CME] = time.time() + self.cme_poll_sec
        if saved_total or failed:
            _log(f"cme cycle: saved={saved_total} dedup={dup_total} "
                 f"failed_symbols={failed}/{len(self.symbols)}")
        return {"saved": saved_total, "dedup": dup_total, "failed": failed}

    # -- helpers --

    def _job_failed(self, job: str, msg: str) -> None:
        self._consec_fail[job] = self._consec_fail.get(job, 0) + 1
        self._last_error = f"{_utcnow_iso()} {job}: {msg}"
        _log(f"JOB FAILED {job} (consecutive={self._consec_fail[job]}): "
             f"{self._last_error}")

    def _bump(self, key: str, n: int) -> None:
        if n:
            self._counters[key] = self._counters.get(key, 0) + n

    def _record_health_safe(self, entries: Dict[str, str]) -> None:
        try:
            record_health(self._db_path, entries)
        except Exception as exc:
            self._last_error = (f"{_utcnow_iso()} health: "
                                f"{type(exc).__name__}: {exc}")
            _log(f"HEALTH WRITE FAILED: {self._last_error}")

    def _set_phase(self, phase: str) -> None:
        self._phase = phase
        self._phase_since = _utcnow_iso()

    # -- observability --

    def status(self) -> Dict[str, Any]:
        # StatusHeal: 観測経路そのものを復活経路にする (positioning 準拠)
        self.ensure_running()
        now = time.time()
        return {
            "enabled": True,
            "running": bool(self._thread and self._thread.is_alive()),
            "started_at": self._started_at,
            "symbols": self.symbols,
            "ff_poll_sec": self.ff_poll_sec,
            "cme_poll_sec": self.cme_poll_sec,
            "tick_sec": self.tick_sec,
            "poll_cycles": self._poll_cycles,
            "current_phase": self._phase,
            "phase_since": self._phase_since,
            "last_cycle_at": self._last_cycle_at,
            "counters": dict(self._counters),
            "consecutive_failures": {k: v for k, v in
                                     self._consec_fail.items() if v},
            "next_due_in_sec": {
                job: max(0, int(due - now))
                for job, due in self._next_due.items()},
            "last_error": self._last_error,
            "restarts": self._restarts,
            "last_restart_at": self._last_restart_at,
            "stale_alert_sec": {JOB_FF: STALE_ALERT_FF_SEC,
                                JOB_CME: STALE_ALERT_CME_SEC},
            "tables": db_market_stats(self._db_path),
            "health": db_health(self._db_path),
        }


# ── module-level singleton (app.py 起動時に設定、API から参照) ──────────

_worker: Optional[MarketDataIngestWorker] = None


def get_worker() -> Optional[MarketDataIngestWorker]:
    return _worker


def ensure_worker_running() -> Optional[Dict[str, Any]]:
    """singleton worker の self-heal (app.py before_request heartbeat 用)。"""
    if _worker is None:
        return None
    return _worker.ensure_running()


def start_market_data_ingest(db_path: str,
                             ff_fetch: Optional[Callable] = None,
                             bars_fetch: Optional[Callable] = None,
                             start_thread: bool = True,
                             defer_thread: bool = False
                             ) -> Optional[MarketDataIngestWorker]:
    """env を解決して worker を生成・開始する (app.py 起動フックから呼ぶ)。

    MARKET_INGEST_ENABLE    default "1" — "1" 以外で無効
    FF_CALENDAR_URL         feed URL override
    FF_CALENDAR_POLL_SEC    default 21600 (≥3600 clamp)
    CME_BARS_POLL_SEC       default 86400 (≥21600 clamp)
    CME_BARS_SYMBOLS        カンマ区切り override (例 "6E=F,6J=F")

    defer_thread=True: thread をこのプロセスでは起動しない (fork-safety §11、
    positioning_ingest と同一根拠 — gunicorn master で network を動かさない)。
    """
    global _worker
    if os.environ.get("MARKET_INGEST_ENABLE", "1") != "1":
        _log("disabled via MARKET_INGEST_ENABLE — worker not started")
        return None
    if _worker is not None:
        _log("already started — reusing existing worker")
        return _worker

    symbols_env = os.environ.get("CME_BARS_SYMBOLS", "")
    symbols = ([s.strip() for s in symbols_env.split(",") if s.strip()]
               if symbols_env else list(DEFAULT_CME_SYMBOLS))
    ff_poll = _int_env("FF_CALENDAR_POLL_SEC", DEFAULT_FF_POLL_SEC)
    cme_poll = _int_env("CME_BARS_POLL_SEC", DEFAULT_CME_POLL_SEC)
    ff_url = os.environ.get("FF_CALENDAR_URL", "") or FF_FEED_URL

    worker = MarketDataIngestWorker(
        db_path, ff_fetch=ff_fetch, bars_fetch=bars_fetch, symbols=symbols,
        ff_poll_sec=ff_poll, cme_poll_sec=cme_poll, ff_url=ff_url)
    if defer_thread:
        ensure_market_data_schema(db_path)
        worker._seed_next_due()
        worker._started_at = _utcnow_iso()
        _log("thread start DEFERRED to serving process "
             "(fork-safety §11) — first heal via status/heartbeat will spawn")
    elif start_thread:
        worker.start()
    else:
        ensure_market_data_schema(db_path)
        worker._seed_next_due()
    _worker = worker
    return worker


# ── helpers ─────────────────────────────────────────────────────────

def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        _log(f"invalid {name}={raw!r} — using default {default}")
        return default


def _parse_iso(text: str) -> datetime:
    """ISO8601 (offset 付き or 'Z') → aware datetime。naive は ValueError。"""
    txt = str(text).strip()
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    dt = datetime.fromisoformat(txt)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp has no tz offset: {text!r}")
    return dt


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime(_ISO_FMT)


def _age_seconds(iso_ts: Optional[str]) -> Optional[int]:
    if not iso_ts:
        return None
    try:
        dt = _parse_iso(str(iso_ts))
    except ValueError:
        return None
    return int((datetime.now(timezone.utc) - dt).total_seconds())


def _log(msg: str) -> None:
    """Render ログ (stdout) と logging の両方へ fail-loud 出力。"""
    print(f"[market-ingest] {msg}", flush=True)
    logger.info(msg)
