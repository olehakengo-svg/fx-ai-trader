"""
Myfxbook Community Outlook API client — E1 positioning aggregate source.

背景 (knowledge-base/wiki/analyses/e1-positioning-ingest-2026-07-14.md §8c):
  OANDA v20 book は 2024-09-14 に retail API 全体で提供終了 (oanda.jp/info/1193)。
  E1 の代替決裁オプション A = Myfxbook Community Outlook への aggregate 転換。
  bucket 級 (near_imbalance) は放棄し、全体 long/short skew + avgLong/ShortPrice
  距離を一次統計に再定義する。

API 契約 (https://www.myfxbook.com/api):
  - GET /api/login.json?email=&password= → {"error":bool,"message":str,"session":str}
  - GET /api/get-community-outlook.json?session= →
      {"error":bool,"message":str,"symbols":[{"name":"EURUSD",
       "shortPercentage":..,"longPercentage":..,"longVolume":..,"shortVolume":..,
       "longPositions":..,"shortPositions":..,"totalPositions":..,
       "avgShortPrice":..,"avgLongPrice":..}, ...]}
  - rate limit 100 req/24h — 呼び出し側 (positioning_ingest) が poll≥900s で
    ≤96 req/日に抑える。login は session 失効時のみ。
  - session は IP-bound (Render egress 変動で失効し得る) → 失効検知で再 login。

Secrets 契約: email/password は env からのみ読み、レスポンス/ログ/status/例外
メッセージに一切含めない (OandaClient と同じ pin をテストで固定)。

2026-07-16 本番実証 2 バグ修正 (rule:R3):
  (a) session は Myfxbook が発行時点で URL-encoded 済み ('%' を含む) —
      params= 経由の再エンコードは二重化になり全 API が "Invalid session." を
      返す。session は raw のまま query に付加する (_get は組立済み query を受ける)。
  (b) requests.Session は fork-safe ではない — gunicorn master で作られた
      Session の urllib3 pool lock が locked のまま子プロセスに複製され、
      self-heal 後の thread が無期限ブロックした (timeout はソケット待ち専用で
      lock 待ちには効かない)。pid 変化検知で Session を作り直す。
All methods return (success: bool, data: dict) tuples (OandaClient 契約準拠)。
モジュールトップ副作用禁止 — env 読みは __init__ 内で解決。
"""
import logging
import os

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:  # pragma: no cover - CI/本番には requests がある
    # urllib fallback は持たない (semgrep: urllib は file:// 等を開けるため)。
    # requests 不在は _get() が fail-loud に transport エラーを返す。
    _HAS_REQUESTS = False

logger = logging.getLogger(__name__)

BASE_URL = "https://www.myfxbook.com/api"
_TIMEOUT_SEC = 20
# session 失効を示す message 断片 (Myfxbook は HTTP 200 + error:true で返す)
_INVALID_SESSION_MARKERS = ("invalid session", "please login")


class MyfxbookClient:
    """Myfxbook Community Outlook 用 thin client (read-only)。"""

    def __init__(self, email: str = None, password: str = None,
                 base_url: str = None):
        self._email = email if email is not None else os.environ.get(
            "MYFXBOOK_EMAIL", "")
        self._password = password if password is not None else os.environ.get(
            "MYFXBOOK_PASSWORD", "")
        self._base_url = (base_url or os.environ.get("MYFXBOOK_BASE_URL", "")
                          or BASE_URL).rstrip("/")
        self._session_id = ""
        # 可観測カウンタ (positioning status で露出 — secrets は含めない)
        self.logins_total = 0
        self.last_login_at = None
        self.requests_total = 0
        # HTTP Session は fork-safe でないため lazy + pid 追跡で生成 (docstring (b))
        self._http = None
        self._http_pid = None

    @property
    def configured(self) -> bool:
        return bool(self._email and self._password)

    @property
    def logged_in(self) -> bool:
        return bool(self._session_id)

    # ── transport ──────────────────────────────────────────────────

    def _http_session(self):
        """fork-safe な requests.Session を返す (pid 変化で作り直し)。

        gunicorn master で生成した Session を fork 継承すると urllib3 pool
        lock が locked のまま複製され、子プロセスの request が無期限ブロック
        する (2026-07-16 本番実証、worker thread 死 §8b と同族の fork 問題)。
        """
        pid = os.getpid()
        if self._http is None or self._http_pid != pid:
            self._http = _requests.Session()
            self._http_pid = pid
        return self._http

    def _get(self, endpoint: str, query: str) -> tuple:
        """GET → (ok, data)。query は呼び出し側で組立済みの文字列。

        session は Myfxbook が発行時点で URL-encoded 済みのため、dict params
        経由の再エンコード (二重化) をしてはならない — "Invalid session." になる
        (2026-07-16 本番実証)。query は URL に載るため絶対にログへ出さない。
        """
        if not _HAS_REQUESTS:  # pragma: no cover
            return False, {"error": "transport",
                           "message": "requests library unavailable"}
        url = f"{self._base_url}/{endpoint}?{query}"
        self.requests_total += 1
        try:
            resp = self._http_session().get(url, timeout=_TIMEOUT_SEC)
            status = resp.status_code
            body = resp.text
        except Exception as exc:
            # URL/query を含めない (credentials 保護)
            return False, {"error": "transport",
                           "message": f"{endpoint}: {type(exc).__name__}"}
        if status != 200:
            return False, {"error": status,
                           "message": f"{endpoint}: http={status}"}
        try:
            import json as _json
            data = _json.loads(body)
        except ValueError:
            return False, {"error": "parse",
                           "message": f"{endpoint}: non-JSON response "
                                      f"({len(body)}B)"}
        if not isinstance(data, dict):
            return False, {"error": "parse",
                           "message": f"{endpoint}: unexpected payload type "
                                      f"{type(data).__name__}"}
        if data.get("error"):
            # Myfxbook は業務エラーを HTTP 200 + error:true で返す
            return False, {"error": "api",
                           "message": str(data.get("message", ""))[:200]}
        return True, data

    # ── API ────────────────────────────────────────────────────────

    def login(self) -> tuple:
        """login.json → session 取得。credentials 未設定は fail-loud。"""
        if not self.configured:
            return False, {"error": "config",
                           "message": "MYFXBOOK_EMAIL/MYFXBOOK_PASSWORD "
                                      "not configured"}
        from urllib.parse import urlencode
        ok, data = self._get("login.json",
                             urlencode({"email": self._email,
                                        "password": self._password}))
        if not ok:
            self._session_id = ""
            return False, data
        session = str(data.get("session", "") or "")
        if not session:
            self._session_id = ""
            return False, {"error": "api",
                           "message": "login ok but empty session"}
        self._session_id = session
        self.logins_total += 1
        from datetime import datetime, timezone
        self.last_login_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        logger.info("myfxbook login ok (logins_total=%d)", self.logins_total)
        return True, {"session": "***"}  # session 値も外へ出さない

    def get_community_outlook(self, auto_login: bool = True) -> tuple:
        """get-community-outlook.json → 全 symbol の aggregate positioning。

        session 未取得/失効時は 1 回だけ login を挟んで再試行する
        (auto_login=False で無効化 — テスト/probe 用)。
        """
        if not self._session_id:
            if not auto_login:
                return False, {"error": "session",
                               "message": "not logged in"}
            ok, data = self.login()
            if not ok:
                return False, data
        # session は再エンコード禁止 (発行時点で encoded 済み) — raw で付加
        ok, data = self._get("get-community-outlook.json",
                             "session=" + self._session_id)
        if not ok and auto_login and _looks_like_invalid_session(data):
            self._session_id = ""
            ok2, login_data = self.login()
            if not ok2:
                return False, login_data
            ok, data = self._get("get-community-outlook.json",
                                 "session=" + self._session_id)
        return ok, data


def _looks_like_invalid_session(data: dict) -> bool:
    msg = str((data or {}).get("message", "")).lower()
    return any(marker in msg for marker in _INVALID_SESSION_MARKERS)
