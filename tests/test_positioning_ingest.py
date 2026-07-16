"""E1 positioning ingest — offline/deterministic tests (network なし)。

対象: modules/positioning_ingest.py (user GO 2026-07-14)
  (a) parse + trim + 集計 (fixture レスポンス JSON)
  (b) dedup (book time 同一なら skip)
  (c) schema / UNIQUE 制約
  (d) POSITIONING_INGEST_ENABLE=0 で thread 不起動
  (e) 4xx → unsupported マップ登録 + 以後 skip / 失敗カウント fail-loud
  (f) 検証 API の契約 (/api/positioning/status, /api/positioning/export)
  (g) self-heal: start() 済み worker の thread 死 → is_alive 検知で再起動
      (2026-07-14 本番実証: import 時起動 thread は request-serving process に
       生き残らない。demo_trader StatusHeal パターン準拠、rule:R3)
  (h) 可用性 probe: 本番 token での 401 帰属確定用 (/api/positioning/probe)
      — token / 口座 ID をレスポンスに一切含めない契約を含む
"""
import json
import sqlite3
import threading

import pytest

from modules.positioning_ingest import (
    BOOK_TYPES,
    DEFAULT_INSTRUMENTS,
    PROBE_CHECKS,
    PositioningIngestWorker,
    THREAD_NAME,
    db_book_stats,
    ensure_positioning_schema,
    ensure_worker_running,
    export_snapshots,
    extract_book_payload,
    parse_book,
    probe_availability,
    save_snapshot,
    start_positioning_ingest,
)
import modules.positioning_ingest as pi


# ── fixture book (OANDA v20 positionBook 形状) ──────────────────────
# mid=150.000 / trim 帯 ±3% = [145.50, 154.50] / near 帯 ±0.5% = [149.25, 150.75]

def make_book(time="2026-07-14T12:00:00Z"):
    buckets = [
        # (price, long%, short%)
        ("140.000", "1.0", "2.0"),   # trim 外 (集計のみ寄与)
        ("146.000", "3.0", "1.0"),   # trim 内 / near 外
        ("149.500", "5.0", "1.5"),   # near 内
        ("150.000", "4.0", "2.5"),   # near 内 (mid)
        ("150.500", "2.0", "6.0"),   # near 内
        ("152.000", "1.5", "0.5"),   # trim 内 / near 外
        ("155.000", "0.5", "3.5"),   # trim 外 (集計のみ寄与)
    ]
    return {
        "price": "150.000",
        "bucketWidth": "0.050",
        "time": time,
        "unixTime": "1789041600",
        "buckets": [
            {"price": p, "longCountPercent": l, "shortCountPercent": s}
            for (p, l, s) in buckets
        ],
    }


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "positioning_test.db")
    ensure_positioning_schema(path)
    return path


class FakeClient:
    """book_type×instrument 毎に scripted レスポンスを返す offline client。"""
    _token = "fake-token"

    def __init__(self, responses):
        # responses: {(book_type, instrument): [ (ok, data), ... ]}
        self.responses = {k: list(v) for k, v in responses.items()}
        self.calls = []

    def _pop(self, book_type, instrument):
        self.calls.append((book_type, instrument))
        seq = self.responses.get((book_type, instrument), [])
        if not seq:
            return False, {"error": "exhausted", "message": "no scripted response"}
        return seq.pop(0) if len(seq) > 1 else seq[0]

    def get_position_book(self, instrument):
        return self._pop("position", instrument)

    def get_order_book(self, instrument):
        return self._pop("order", instrument)


# ── (a) parse + trim + 集計 ─────────────────────────────────────────

def test_parse_book_trim_and_aggregates():
    parsed = parse_book(make_book())
    assert parsed["snapshot_time"] == "2026-07-14T12:00:00Z"
    assert parsed["price"] == 150.0
    assert parsed["bucket_width"] == 0.05

    # 集計は trim 前の全帯域: long = 1+3+5+4+2+1.5+0.5, short = 2+1+1.5+2.5+6+0.5+3.5
    assert parsed["pct_long_total"] == pytest.approx(17.0)
    assert parsed["pct_short_total"] == pytest.approx(17.0)
    # near ±0.5% (149.25–150.75): long 5+4+2=11, short 1.5+2.5+6=10 → +1.0
    assert parsed["near_imbalance"] == pytest.approx(1.0)

    # trim ±3% (145.50–154.50): 140.000 / 155.000 が落ちて 5 buckets
    prices = [b[0] for b in parsed["buckets"]]
    assert prices == [146.0, 149.5, 150.0, 150.5, 152.0]
    assert parsed["buckets"][1] == [149.5, 5.0, 1.5]


def test_parse_book_missing_key_raises():
    """必須キー欠落は ValueError — silent 破損保存を防ぐ (fail-loud)。"""
    broken = make_book()
    del broken["price"]
    with pytest.raises(ValueError, match="price"):
        parse_book(broken)


def test_extract_book_payload_accepts_v20_shapes():
    book = make_book()
    assert extract_book_payload({"positionBook": book}) is book
    assert extract_book_payload({"orderBook": book}) is book
    assert extract_book_payload({"book": book}) is book
    assert extract_book_payload({"unexpected": 1}) is None
    assert extract_book_payload(None) is None


# ── (b) dedup ───────────────────────────────────────────────────────

def test_dedup_same_book_time_skips_insert(db_path):
    t1 = "2026-07-14T12:00:00Z"
    t2 = "2026-07-14T12:20:00Z"
    client = FakeClient({
        ("position", "USD_JPY"): [
            (True, {"positionBook": make_book(t1)}),
            (True, {"positionBook": make_book(t1)}),   # 同一 time → skip
            (True, {"positionBook": make_book(t2)}),   # 更新 → insert
        ],
    })
    w = PositioningIngestWorker(db_path, client, instruments=["USD_JPY"],
                                book_types=("position",))
    assert w.poll_once() == {"saved": 1, "skipped": 0, "failed": 0}
    assert w.poll_once() == {"saved": 0, "skipped": 1, "failed": 0}
    assert w.poll_once() == {"saved": 1, "skipped": 0, "failed": 0}

    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM positioning_snapshots").fetchone()[0]
    conn.close()
    assert n == 2
    assert w._dedup_skips == 1


def test_dedup_survives_restart_via_db_seed(db_path):
    """プロセス再起動 (メモリ dedup 消失) でも DB seed + UNIQUE で二重保存しない。"""
    t1 = "2026-07-14T12:00:00Z"
    client = FakeClient({("position", "USD_JPY"):
                         [(True, {"positionBook": make_book(t1)})]})
    w1 = PositioningIngestWorker(db_path, client, instruments=["USD_JPY"],
                                 book_types=("position",))
    w1.poll_once()

    # 新 worker (再起動相当) — _seed_last_saved で DB から dedup を温める
    w2 = PositioningIngestWorker(db_path, client, instruments=["USD_JPY"],
                                 book_types=("position",))
    w2._seed_last_saved()
    assert w2._last_saved[("USD_JPY", "position")] == t1
    assert w2.poll_once() == {"saved": 0, "skipped": 1, "failed": 0}


# ── (c) schema / UNIQUE ─────────────────────────────────────────────

def test_schema_unique_constraint(db_path):
    parsed = parse_book(make_book())
    assert save_snapshot(db_path, "USD_JPY", "position", parsed) is True
    # INSERT OR IGNORE 経由は False (新規行なし)
    assert save_snapshot(db_path, "USD_JPY", "position", parsed) is False
    # 生 INSERT は IntegrityError
    conn = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO positioning_snapshots"
            " (instrument, book_type, snapshot_time) VALUES (?, ?, ?)",
            ("USD_JPY", "position", parsed["snapshot_time"]))
    conn.close()
    # 別 book_type / 別 instrument は同一 time でも保存できる
    assert save_snapshot(db_path, "USD_JPY", "order", parsed) is True
    assert save_snapshot(db_path, "EUR_USD", "position", parsed) is True


def test_ensure_schema_idempotent(db_path):
    ensure_positioning_schema(db_path)  # 2 回目も例外なし
    conn = sqlite3.connect(db_path)
    ensure_positioning_schema(conn)     # Connection 渡しも可 (demo_db 経路)
    cols = [r[1] for r in conn.execute(
        "PRAGMA table_info(positioning_snapshots)").fetchall()]
    conn.close()
    assert cols == ["id", "instrument", "book_type", "snapshot_time", "price",
                    "bucket_width", "buckets_json", "pct_long_total",
                    "pct_short_total", "near_imbalance", "fetched_at"]


# ── (d) ENABLE flag off → thread 不起動 ─────────────────────────────

def test_enable_flag_off_no_worker_no_thread(db_path, monkeypatch):
    monkeypatch.setenv("POSITIONING_INGEST_ENABLE", "0")
    monkeypatch.setattr(pi, "_worker", None)
    assert start_positioning_ingest(db_path) is None
    assert pi.get_worker() is None
    assert not any(t.name == THREAD_NAME for t in threading.enumerate())


def test_enable_flag_default_on_env_instruments_override(db_path, monkeypatch):
    monkeypatch.delenv("POSITIONING_INGEST_ENABLE", raising=False)
    monkeypatch.setenv("POSITIONING_INSTRUMENTS", "USD_JPY, EUR_USD")
    monkeypatch.setattr(pi, "_worker", None)
    client = FakeClient({})
    w = start_positioning_ingest(db_path, client=client, start_thread=False)
    try:
        assert w is not None
        assert w.instruments == ["USD_JPY", "EUR_USD"]
        assert list(w.book_types) == list(BOOK_TYPES)
        assert pi.get_worker() is w
        # start_thread=False では thread を作らない (テスト用の決定論性)
        assert not any(t.name == THREAD_NAME for t in threading.enumerate())
    finally:
        monkeypatch.setattr(pi, "_worker", None)


def test_default_instruments_contract():
    assert DEFAULT_INSTRUMENTS == ("USD_JPY", "EUR_USD", "GBP_USD",
                                   "EUR_JPY", "GBP_JPY", "AUD_JPY")


# ── (e) 失敗系: 4xx unsupported / 連続失敗カウント ───────────────────

def test_4xx_marks_unsupported_and_skips_forever(db_path):
    client = FakeClient({
        ("position", "XAU_USD"): [(False, {"error": 400,
                                           "message": "book not available"})],
        ("order", "XAU_USD"): [(True, {"orderBook": make_book()})],
    })
    w = PositioningIngestWorker(db_path, client, instruments=["XAU_USD"])
    w.poll_once()
    w.poll_once()
    # position は初回 4xx 後 skip → client 呼び出しは 1 回だけ
    assert client.calls.count(("position", "XAU_USD")) == 1
    assert client.calls.count(("order", "XAU_USD")) == 2

    st = w.status()
    assert st["books"]["XAU_USD:position"]["available"] is False
    assert st["books"]["XAU_USD:position"]["unsupported"]["code"] == 400
    assert st["books"]["XAU_USD:order"]["available"] is True


def test_consecutive_failures_counted_and_reset(db_path):
    client = FakeClient({
        ("position", "USD_JPY"): [
            (False, {"error": "timeout", "message": "Timeout after 30s"}),
            (False, {"error": 503, "message": "unavailable"}),
            (True, {"positionBook": make_book()}),
        ],
    })
    w = PositioningIngestWorker(db_path, client, instruments=["USD_JPY"],
                                book_types=("position",))
    w.poll_once()
    assert w.status()["books"]["USD_JPY:position"]["consecutive_failures"] == 1
    assert w.status()["consecutive_cycle_failures"] == 1
    w.poll_once()
    assert w.status()["books"]["USD_JPY:position"]["consecutive_failures"] == 2
    assert "503" in w.status()["last_error"]
    w.poll_once()  # 成功でリセット
    st = w.status()
    assert st["books"]["USD_JPY:position"]["consecutive_failures"] == 0
    assert st["consecutive_cycle_failures"] == 0
    assert st["saved_total"] == 1


def test_429_is_failure_not_unsupported(db_path):
    """429 (rate limit) は一時障害 — unsupported マップに入れて永久 skip しない。"""
    client = FakeClient({
        ("position", "USD_JPY"): [
            (False, {"error": 429, "message": "rate limited"}),
            (True, {"positionBook": make_book()}),
        ],
    })
    w = PositioningIngestWorker(db_path, client, instruments=["USD_JPY"],
                                book_types=("position",))
    w.poll_once()
    assert w.status()["books"]["USD_JPY:position"]["available"] is True
    assert w.poll_once()["saved"] == 1


def test_missing_token_skips_cycle_loudly(db_path):
    client = FakeClient({})
    client._token = ""
    w = PositioningIngestWorker(db_path, client, instruments=["USD_JPY"])
    assert w.poll_once() == {"saved": 0, "skipped": 0, "failed": 0}
    assert client.calls == []  # token なしで API を叩かない
    assert "token not configured" in w.status()["last_error"]
    assert w.status()["consecutive_cycle_failures"] == 1


# ── export / db stats ───────────────────────────────────────────────

def test_export_filters_and_bucket_roundtrip(db_path):
    for t in ("2026-07-14T10:00:00Z", "2026-07-14T12:00:00Z"):
        save_snapshot(db_path, "USD_JPY", "position", parse_book(make_book(t)))
    save_snapshot(db_path, "EUR_USD", "position",
                  parse_book(make_book("2026-07-14T11:00:00Z")))

    rows = export_snapshots(db_path, instrument="USD_JPY",
                            book_type="position",
                            since="2026-07-14T11:00:00Z")
    assert len(rows) == 1
    assert rows[0]["snapshot_time"] == "2026-07-14T12:00:00Z"
    assert rows[0]["buckets"][1] == [149.5, 5.0, 1.5]  # JSON roundtrip
    assert rows[0]["near_imbalance"] == pytest.approx(1.0)

    assert len(export_snapshots(db_path)) == 3
    assert len(export_snapshots(db_path, limit=2)) == 2


def test_db_book_stats_shape(db_path):
    save_snapshot(db_path, "USD_JPY", "position", parse_book(make_book()))
    stats = db_book_stats(db_path)
    entry = stats["USD_JPY:position"]
    assert entry["rows"] == 1
    assert entry["latest_snapshot_time"] == "2026-07-14T12:00:00Z"
    assert isinstance(entry["stale_seconds"], int)


def test_db_book_stats_fail_loud_on_missing_table(tmp_path):
    empty = str(tmp_path / "no_schema.db")
    sqlite3.connect(empty).close()
    stats = db_book_stats(empty)
    assert "_error" in stats  # silent 空 dict にしない


# ── (f) 検証 API 契約 ───────────────────────────────────────────────

def test_api_positioning_status_worker_not_started(flask_client):
    """テスト環境 (TESTING=1, autostart skip) では worker 未起動 —
    その場合も DB 側の books を返し、未起動理由を明示する契約。"""
    resp = flask_client.get("/api/positioning/status")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["enabled"] is False
    assert body["running"] is False
    assert "books" in body
    assert "reason" in body


def test_api_positioning_export_contract(flask_client):
    resp = flask_client.get("/api/positioning/export?instrument=USD_JPY"
                            "&book=position&limit=5")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert set(body.keys()) == {"count", "filters", "rows"}
    assert body["filters"]["instrument"] == "USD_JPY"

    bad = flask_client.get("/api/positioning/export?book=nonsense")
    assert bad.status_code == 400
    bad2 = flask_client.get("/api/positioning/export?limit=abc")
    assert bad2.status_code == 400


# ── (g) self-heal: thread 死 → is_alive 検知で再起動 ─────────────────
# 本番実証 (2026-07-14, Render srv-d6va1of5r7bs73en10vg): import 時に起動した
# thread は request-serving process に生き残らない (started_at は fork copy で
# 残るが is_alive=False / poll_cycles=0)。demo_trader StatusHeal パターン準拠。

def _dead_thread():
    """終了済み thread — fork 後の「started_at あり・thread 死」状態の再現用。"""
    t = threading.Thread(target=lambda: None)
    t.start()
    t.join()
    assert not t.is_alive()
    return t


def _fork_orphan_worker(db_path, client=None, **kw):
    """start() 済みなのに thread が死んでいる worker (本番で観測した状態)。"""
    w = PositioningIngestWorker(
        db_path, client or FakeClient({}), instruments=["USD_JPY"],
        book_types=("position",), **kw)
    w._started_at = "2026-07-14T08:20:17Z"
    w._thread = _dead_thread()
    return w


def _stop_and_join(w):
    w.stop()
    if w._thread is not None:
        w._thread.join(timeout=5)
        assert not w._thread.is_alive()


def test_ensure_running_restarts_dead_thread(db_path):
    w = _fork_orphan_worker(db_path)
    try:
        result = w.ensure_running()
        assert result["healed"] is True
        assert w._thread.is_alive()
        assert w._thread.name == THREAD_NAME
        assert w._restarts == 1
        assert w._last_restart_at is not None
    finally:
        _stop_and_join(w)


def test_ensure_running_noop_when_alive(db_path):
    w = _fork_orphan_worker(db_path)
    try:
        w.ensure_running()
        alive_thread = w._thread
        result = w.ensure_running()
        assert result["healed"] is False
        assert result["reason"] == "alive"
        assert w._thread is alive_thread  # 二重起動しない
        assert w._restarts == 1
    finally:
        _stop_and_join(w)


def test_ensure_running_respects_stop(db_path):
    """明示 stop() 後は復活させない (demo_trader emergency-kill と同じ規律)。"""
    w = _fork_orphan_worker(db_path)
    w.stop()
    result = w.ensure_running()
    assert result["healed"] is False
    assert result["reason"] == "stopped"
    assert w._thread is None or not w._thread.is_alive()


def test_ensure_running_never_started_is_noop(db_path):
    """start() 前 (started_at なし) は heal 対象外 —
    既存 unit テストの決定論性 (poll_once 手動駆動) を壊さない。"""
    w = PositioningIngestWorker(db_path, FakeClient({}),
                                instruments=["USD_JPY"],
                                book_types=("position",))
    result = w.ensure_running()
    assert result["healed"] is False
    assert result["reason"] == "never started"
    assert w._thread is None


def test_status_self_heals_dead_thread(db_path):
    """status() 呼び出し (API 経由) が heal 経路になる — StatusHeal 準拠。"""
    client = FakeClient({("position", "USD_JPY"):
                         [(True, {"positionBook": make_book()})]})
    w = _fork_orphan_worker(db_path, client=client)
    try:
        st = w.status()
        assert st["running"] is True
        assert st["restarts"] == 1
        assert st["last_restart_at"] is not None
        assert w._thread.is_alive()
    finally:
        _stop_and_join(w)


def test_status_restart_observability_defaults(db_path):
    """未 heal 時は restarts=0 / last_restart_at=None を露出する。"""
    w = PositioningIngestWorker(db_path, FakeClient({}),
                                instruments=["USD_JPY"],
                                book_types=("position",))
    st = w.status()
    assert st["restarts"] == 0
    assert st["last_restart_at"] is None
    assert w._thread is None  # never-started は status() でも起動しない


def test_ensure_worker_running_module_helper(db_path, monkeypatch):
    monkeypatch.setattr(pi, "_worker", None)
    assert ensure_worker_running() is None  # worker なしは no-op

    w = _fork_orphan_worker(db_path)
    monkeypatch.setattr(pi, "_worker", w)
    try:
        result = ensure_worker_running()
        assert result["healed"] is True
        assert w._thread.is_alive()
    finally:
        _stop_and_join(w)
        monkeypatch.setattr(pi, "_worker", None)


def test_before_request_heartbeat_heals_dead_worker(flask_client, db_path,
                                                    monkeypatch):
    """任意の request が throttled heartbeat 経由で worker を復活させる —
    Render health check を外部監視に依存しない恒常 heal 経路にする設計。"""
    import app as app_module
    w = _fork_orphan_worker(db_path)
    monkeypatch.setattr(pi, "_worker", w)
    app_module._positioning_heartbeat_last[0] = 0.0  # throttle 窓を開ける
    try:
        flask_client.get("/api/positioning/export?limit=1")
        assert w._thread.is_alive()
        assert w._restarts == 1
    finally:
        _stop_and_join(w)
        monkeypatch.setattr(pi, "_worker", None)


# ── (h) 可用性 probe: 401 帰属確定 (token は一切レスポンスに出さない) ──

class FakeProbeClient:
    _token = "fake-secret-token-must-never-leak"

    def __init__(self, accounts, position_book, order_book, labs):
        self._responses = {
            "accounts": accounts, "position": position_book,
            "order": order_book, "labs": labs,
        }
        self.calls = []

    def get_accounts(self):
        self.calls.append("accounts")
        return self._responses["accounts"]

    def get_position_book(self, instrument):
        self.calls.append(("position", instrument))
        return self._responses["position"]

    def get_order_book(self, instrument):
        self.calls.append(("order", instrument))
        return self._responses["order"]

    def get_labs_orderbook_data(self, instrument="EUR_USD", period=3600):
        self.calls.append(("labs", instrument, period))
        return self._responses["labs"]


_401 = (False, {"error": 401,
                "message": "Insufficient authorization to perform request."})
# labs は 2020 年廃止 — 現在は WAF の 403 HTML が返る (2026-07-14 実測)
_403_HTML = (False, {"error": 403, "message": "<!DOCTYPE html>\n<html ..."})


def test_probe_availability_retirement_attribution():
    """accounts 200 + v20 book 401 → OANDA retail API の book 提供終了
    (2024-09-14, oanda.jp/info/1193) と帰属する — token/区分の問題ではない。"""
    client = FakeProbeClient(
        accounts=(True, {"accounts": [{"id": "001-011-XXXX-001"}]}),
        position_book=_401, order_book=_401, labs=_403_HTML)
    report = probe_availability(client)
    assert report["token_configured"] is True
    assert set(report["checks"].keys()) == set(PROBE_CHECKS)
    assert report["checks"]["v3_accounts"]["ok"] is True
    assert report["checks"]["v3_accounts"]["message"] == "accounts=1"
    assert report["checks"]["v3_position_book"]["http"] == 401
    assert report["checks"]["labs_v1_orderbook_data"]["http"] == 403
    assert "Insufficient authorization" in \
        report["checks"]["v3_position_book"]["message"]
    assert "提供終了" in report["interpretation"]

    dumped = json.dumps(report, ensure_ascii=False)
    assert FakeProbeClient._token not in dumped   # token を print しない契約
    assert "001-011" not in dumped                # 口座 ID も返さない


def test_probe_availability_token_invalid_attribution():
    client = FakeProbeClient(accounts=_401, position_book=_401,
                             order_book=_401, labs=_401)
    report = probe_availability(client)
    assert report["checks"]["v3_accounts"]["ok"] is False
    assert "token" in report["interpretation"]


def test_probe_availability_labs_fallback_attribution():
    """v20 book のみ 401 で labs が取れるなら labs 代替可と報告する。"""
    client = FakeProbeClient(
        accounts=(True, {"accounts": []}),
        position_book=_401, order_book=_401,
        labs=(True, {"data": []}))
    report = probe_availability(client)
    assert report["checks"]["labs_v1_orderbook_data"]["ok"] is True
    assert "labs" in report["interpretation"]


def test_probe_availability_no_token_makes_no_calls():
    client = FakeProbeClient(accounts=_401, position_book=_401,
                             order_book=_401, labs=_401)
    client._token = ""
    report = probe_availability(client)
    assert report["token_configured"] is False
    assert client.calls == []


def test_api_positioning_probe_dry_by_default(flask_client):
    """?run=1 なしでは OANDA を叩かない (CI/誤操作でのネットワーク発火防止)。"""
    resp = flask_client.get("/api/positioning/probe")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["run"] is False
    assert set(body["checks"]) == set(PROBE_CHECKS)
    assert "run=1" in body["hint"]


def test_api_positioning_probe_run_uses_client(flask_client, monkeypatch):
    import modules.oanda_client as oc
    fake = FakeProbeClient(
        accounts=(True, {"accounts": [{"id": "001-011-XXXX-001"}]}),
        position_book=_401, order_book=_401, labs=_401)
    monkeypatch.setattr(oc, "OandaClient", lambda: fake)
    resp = flask_client.get("/api/positioning/probe?run=1")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["token_configured"] is True
    assert body["checks"]["v3_position_book"]["http"] == 401
    assert FakeProbeClient._token not in resp.data.decode("utf-8")


def test_oanda_client_probe_paths():
    """probe 用 read-only メソッドの path 契約 (network なし)。"""
    from modules.oanda_client import OandaClient
    client = OandaClient(token="t", account_id="a")
    captured = []

    def fake_request(method, path, data=None, timeout=10):
        captured.append((method, path))
        return True, {}

    client._request = fake_request
    client.get_accounts()
    client.get_labs_orderbook_data("EUR_USD", 3600)
    assert captured == [
        ("GET", "/v3/accounts"),
        ("GET", "/labs/v1/orderbook_data?instrument=EUR_USD&period=3600"),
    ]


# ══════════════════════════════════════════════════════════════════
# (i) Myfxbook aggregate source — 2026-07-15 ソース転換 (§8c オプション A)
#     OANDA v20 book 提供終了 (2024-09-14) に伴う E1 データソース交換。
# ══════════════════════════════════════════════════════════════════

from modules.positioning_ingest import (
    MYFXBOOK_MIN_POLL_SEC,
    OUTLOOK_BOOK_TYPE,
    myfxbook_symbol,
    outlook_content_key,
    parse_outlook_symbol,
    run_probe_myfxbook,
)
from modules.myfxbook_client import MyfxbookClient


def make_outlook_symbol(name="USDJPY", long_pct=55.0, short_pct=45.0, **extra):
    sym = {
        "name": name,
        "longPercentage": long_pct,
        "shortPercentage": short_pct,
        "longVolume": 120.5, "shortVolume": 98.4,
        "longPositions": 2100, "shortPositions": 1800,
        "totalPositions": 3900,
        "avgLongPrice": 150.123, "avgShortPrice": 149.876,
    }
    sym.update(extra)
    return sym


def make_outlook_response(symbols=None):
    if symbols is None:
        symbols = [make_outlook_symbol(myfxbook_symbol(i))
                   for i in DEFAULT_INSTRUMENTS]
    return {"error": False, "message": "", "symbols": symbols}


class FakeMyfxbookClient:
    """scripted (ok, data) を返す offline client。最後の要素を繰り返す。"""
    logged_in = True
    logins_total = 1
    last_login_at = "2026-07-15T00:00:00Z"

    def __init__(self, responses, configured=True):
        self.responses = list(responses)
        self.configured = configured
        self.requests_total = 0

    def get_community_outlook(self, auto_login=True):
        self.requests_total += 1
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def make_myfx_worker(db_path, responses, instruments=None, configured=True):
    client = FakeMyfxbookClient(responses, configured=configured)
    w = PositioningIngestWorker(
        db_path, client, instruments=list(instruments or DEFAULT_INSTRUMENTS),
        source="myfxbook")
    return w, client


# ── parse ───────────────────────────────────────────────────────────

def test_parse_outlook_symbol_contract():
    sym = make_outlook_symbol("EURUSD", 61.2, 38.8)
    parsed = parse_outlook_symbol(sym)
    assert parsed["symbol"] == "EURUSD"
    assert parsed["pct_long_total"] == pytest.approx(61.2)
    assert parsed["pct_short_total"] == pytest.approx(38.8)
    assert parsed["raw"] is sym
    # content key は決定的 (dict 順序に依存しない)
    reordered = dict(reversed(list(sym.items())))
    assert parsed["content_key"] == outlook_content_key(reordered)


def test_parse_outlook_symbol_missing_key_raises():
    for missing in ("name", "longPercentage", "shortPercentage"):
        sym = make_outlook_symbol()
        del sym[missing]
        with pytest.raises(ValueError):
            parse_outlook_symbol(sym)
    with pytest.raises(ValueError):
        parse_outlook_symbol(["not", "a", "dict"])


def test_myfxbook_symbol_mapping():
    assert myfxbook_symbol("EUR_USD") == "EURUSD"
    assert myfxbook_symbol("USD_JPY") == "USDJPY"


# ── poll / 保存 / dedup ─────────────────────────────────────────────

def test_myfxbook_poll_saves_outlook_rows(db_path):
    w, client = make_myfx_worker(db_path, [(True, make_outlook_response())])
    assert w.book_types == (OUTLOOK_BOOK_TYPE,)
    counters = w.poll_once()
    assert counters == {"saved": len(DEFAULT_INSTRUMENTS), "skipped": 0,
                        "failed": 0}
    rows = export_snapshots(db_path, instrument="USD_JPY",
                            book_type=OUTLOOK_BOOK_TYPE)
    assert len(rows) == 1
    row = rows[0]
    assert row["book_type"] == OUTLOOK_BOOK_TYPE
    assert row["pct_long_total"] == pytest.approx(55.0)
    assert row["pct_short_total"] == pytest.approx(45.0)
    assert row["near_imbalance"] is None      # bucket 級放棄を NULL で明示
    assert row["price"] is None
    # raw payload が JSON object のまま温存される (avg 価格を含む)
    assert isinstance(row["buckets"], dict)
    assert row["buckets"]["avgLongPrice"] == pytest.approx(150.123)


def test_myfxbook_content_dedup_and_change(db_path):
    resp1 = make_outlook_response()
    changed = make_outlook_response(
        [make_outlook_symbol(myfxbook_symbol(i),
                             long_pct=60.0 if i == "USD_JPY" else 55.0)
         for i in DEFAULT_INSTRUMENTS])
    w, _ = make_myfx_worker(db_path, [(True, resp1), (True, resp1),
                                      (True, changed)])
    assert w.poll_once()["saved"] == len(DEFAULT_INSTRUMENTS)
    second = w.poll_once()   # 内容同一 → 全 skip
    assert second == {"saved": 0, "skipped": len(DEFAULT_INSTRUMENTS),
                      "failed": 0}
    third = w.poll_once()    # USD_JPY のみ変化 → 1 saved
    assert third["saved"] == 1
    assert third["skipped"] == len(DEFAULT_INSTRUMENTS) - 1


def test_myfxbook_dedup_survives_restart(db_path):
    resp = make_outlook_response()
    w1, _ = make_myfx_worker(db_path, [(True, resp)])
    assert w1.poll_once()["saved"] == len(DEFAULT_INSTRUMENTS)
    # 再起動相当: 新 worker が DB の raw payload から content key を再計算
    w2, _ = make_myfx_worker(db_path, [(True, resp)])
    w2._seed_last_saved()
    counters = w2.poll_once()
    assert counters == {"saved": 0, "skipped": len(DEFAULT_INSTRUMENTS),
                        "failed": 0}


def test_myfxbook_missing_credentials_skips_cycle_loudly(db_path):
    w, _ = make_myfx_worker(db_path, [(True, make_outlook_response())],
                            configured=False)
    counters = w.poll_once()
    assert counters == {"saved": 0, "skipped": 0, "failed": 0}
    assert w._poll_cycles == 1
    assert "credentials" in w._last_error
    assert w._consec_cycle_all_fail == 1
    st = w.status()
    assert st["myfxbook"]["waiting_for_credentials"] is True


def test_myfxbook_fetch_failure_counts_then_reset(db_path):
    w, _ = make_myfx_worker(
        db_path,
        [(False, {"error": "api", "message": "Invalid session"}),
         (True, make_outlook_response())])
    counters = w.poll_once()
    assert counters["failed"] == len(DEFAULT_INSTRUMENTS)
    assert w._consec_cycle_all_fail == 1
    key = ("USD_JPY", OUTLOOK_BOOK_TYPE)
    assert w._consec_fail[key] == 1
    counters = w.poll_once()
    assert counters["saved"] == len(DEFAULT_INSTRUMENTS)
    assert w._consec_cycle_all_fail == 0
    assert w._consec_fail[key] == 0


def test_myfxbook_missing_symbol_counts_failure(db_path):
    symbols = [make_outlook_symbol(myfxbook_symbol(i))
               for i in DEFAULT_INSTRUMENTS if i != "AUD_JPY"]
    w, _ = make_myfx_worker(db_path,
                            [(True, make_outlook_response(symbols))])
    counters = w.poll_once()
    assert counters["saved"] == len(DEFAULT_INSTRUMENTS) - 1
    assert counters["failed"] == 1
    assert w._consec_fail[("AUD_JPY", OUTLOOK_BOOK_TYPE)] == 1


def test_myfxbook_poll_sec_clamped_to_rate_limit(db_path):
    w, _ = make_myfx_worker(db_path, [(True, make_outlook_response())])
    assert w.poll_sec >= MYFXBOOK_MIN_POLL_SEC or w.poll_sec == 1200
    w2 = PositioningIngestWorker(
        db_path, FakeMyfxbookClient([(True, {})]), poll_sec=60,
        source="myfxbook")
    assert w2.poll_sec == MYFXBOOK_MIN_POLL_SEC


# ── source 解決 ─────────────────────────────────────────────────────

def test_resolve_source_autodetect_and_override(monkeypatch):
    monkeypatch.delenv("POSITIONING_SOURCE", raising=False)
    monkeypatch.delenv("MYFXBOOK_EMAIL", raising=False)
    monkeypatch.delenv("MYFXBOOK_PASSWORD", raising=False)
    assert pi._resolve_source() == "oanda"
    monkeypatch.setenv("MYFXBOOK_EMAIL", "qa@example.com")
    monkeypatch.setenv("MYFXBOOK_PASSWORD", "pw")
    assert pi._resolve_source() == "myfxbook"
    monkeypatch.setenv("POSITIONING_SOURCE", "oanda")   # 明示が勝つ
    assert pi._resolve_source() == "oanda"
    monkeypatch.setenv("POSITIONING_SOURCE", "bogus")   # 不正値は auto-detect
    assert pi._resolve_source() == "myfxbook"


def test_start_positioning_ingest_myfxbook_source(db_path, monkeypatch):
    monkeypatch.delenv("POSITIONING_INGEST_ENABLE", raising=False)
    monkeypatch.delenv("POSITIONING_SOURCE", raising=False)
    monkeypatch.setenv("MYFXBOOK_EMAIL", "qa@example.com")
    monkeypatch.setenv("MYFXBOOK_PASSWORD", "pw")
    monkeypatch.setattr(pi, "_worker", None)
    try:
        w = start_positioning_ingest(db_path, start_thread=False)
        assert w is not None
        assert w.source == "myfxbook"
        assert w.book_types == (OUTLOOK_BOOK_TYPE,)
        assert isinstance(w._client, MyfxbookClient)
    finally:
        monkeypatch.setattr(pi, "_worker", None)


# ── secrets 契約 ────────────────────────────────────────────────────

def test_myfxbook_status_and_probe_contain_no_secrets(db_path, monkeypatch):
    email = "secret-email@example.com"
    password = "super-secret-pw"
    monkeypatch.setenv("MYFXBOOK_EMAIL", email)
    monkeypatch.setenv("MYFXBOOK_PASSWORD", password)
    client = MyfxbookClient()
    w = PositioningIngestWorker(db_path, client, source="myfxbook")
    blob = json.dumps(w.status())
    assert email not in blob
    assert password not in blob
    assert '"source": "myfxbook"' in blob

    # probe (未 login 経路): login を偽装して secrets 非漏出を確認
    fake = MyfxbookClient(email=email, password=password)

    def fake_get(endpoint, query):
        if endpoint == "login.json":
            return True, {"error": False, "session": "SESSION123"}
        return True, make_outlook_response()

    monkeypatch.setattr(fake, "_get", fake_get)
    result = run_probe_myfxbook(client=fake)
    blob = json.dumps(result)
    assert email not in blob and password not in blob
    assert "SESSION123" not in blob
    assert result["outlook_ok"] is True
    assert result["instruments_missing"] == []


def test_myfxbook_client_relogin_on_invalid_session(monkeypatch):
    client = MyfxbookClient(email="a@example.com", password="pw")
    calls = []

    def fake_get(endpoint, query):
        calls.append(endpoint)
        if endpoint == "login.json":
            return True, {"error": False, "session": f"S{len(calls)}"}
        # 1 回目の outlook は session 失効、2 回目は成功
        if calls.count("get-community-outlook.json") == 1:
            return False, {"error": "api", "message": "Invalid session."}
        return True, make_outlook_response()

    monkeypatch.setattr(client, "_get", fake_get)
    ok, data = client.get_community_outlook()
    assert ok
    assert client.logins_total == 2  # 初回 login + relogin
    assert calls == ["login.json", "get-community-outlook.json",
                     "login.json", "get-community-outlook.json"]


def test_myfxbook_client_unconfigured_login_fails_loud():
    client = MyfxbookClient(email="", password="")
    ok, data = client.login()
    assert not ok
    assert "not configured" in data["message"]


# ── API 契約 ────────────────────────────────────────────────────────

def test_api_positioning_probe_myfxbook_dispatch(flask_client, monkeypatch):
    monkeypatch.setattr(pi, "run_probe_myfxbook",
                        lambda: {"configured": False, "marker": "mfb"})
    resp = flask_client.get("/api/positioning/probe?run=1&source=myfxbook")
    assert resp.status_code == 200
    assert resp.get_json()["marker"] == "mfb"


def test_api_positioning_export_accepts_outlook_book(flask_client):
    resp = flask_client.get("/api/positioning/export?book=outlook")
    assert resp.status_code == 200
    resp = flask_client.get("/api/positioning/export?book=bogus")
    assert resp.status_code == 400


# ── 2026-07-16 本番実証 2 バグの回帰 pin ────────────────────────────

def test_myfxbook_session_passed_raw_not_double_encoded(monkeypatch):
    """session は Myfxbook 発行時点で URL-encoded 済み ('%' を含む)。
    再エンコード (%→%25) すると全 API が Invalid session になる — raw 付加を pin。"""
    client = MyfxbookClient(email="a@example.com", password="pw")
    client._session_id = "AbC%2F123%3D%3D"  # '%' を含む encoded 済み session
    seen = []

    def fake_get(endpoint, query):
        seen.append((endpoint, query))
        return True, make_outlook_response()

    monkeypatch.setattr(client, "_get", fake_get)
    ok, _ = client.get_community_outlook(auto_login=False)
    assert ok
    assert seen == [("get-community-outlook.json",
                     "session=AbC%2F123%3D%3D")]  # %25 への二重化がない


def test_myfxbook_login_query_urlencodes_credentials(monkeypatch):
    """login の email/password は raw 値なので通常の urlencode を通す
    (特殊文字 '+ @ # .' を含む password が正しく %XX 化される)。"""
    client = MyfxbookClient(email="a+b@example.com", password="X+@R#.pw")
    seen = []

    def fake_get(endpoint, query):
        seen.append((endpoint, query))
        return True, {"error": False, "session": "S1"}

    monkeypatch.setattr(client, "_get", fake_get)
    ok, _ = client.login()
    assert ok
    endpoint, query = seen[0]
    assert endpoint == "login.json"
    assert "password=X%2B%40R%23.pw" in query
    assert "email=a%2Bb%40example.com" in query


def test_myfxbook_http_session_rebuilt_on_pid_change():
    """fork 継承した requests.Session は pool lock ごと複製されハングする —
    pid 変化検知で作り直す契約を pin (§8b と同族の fork 問題)。"""
    client = MyfxbookClient(email="a@example.com", password="pw")
    s1 = client._http_session()
    assert client._http_session() is s1        # 同一 pid では再利用
    client._http_pid = client._http_pid - 1    # fork 相当 (pid 変化を偽装)
    s2 = client._http_session()
    assert s2 is not s1                        # 作り直し
    assert client._http_session() is s2


# ── (j) defer_thread — import 時に thread を起動しない fork-safety (§11) ──

def test_defer_thread_arms_heal_without_spawning(db_path, monkeypatch):
    """defer_thread=True: thread は起動しないが started_at が set され、
    ensure_running (serving プロセス側の heal) が起動経路になる。"""
    monkeypatch.delenv("POSITIONING_INGEST_ENABLE", raising=False)
    monkeypatch.delenv("POSITIONING_SOURCE", raising=False)
    monkeypatch.delenv("MYFXBOOK_EMAIL", raising=False)
    monkeypatch.delenv("MYFXBOOK_PASSWORD", raising=False)
    monkeypatch.setattr(pi, "_worker", None)
    try:
        w = start_positioning_ingest(db_path, defer_thread=True)
        assert w is not None
        assert w._thread is None                  # thread 未起動
        assert w._started_at is not None          # heal は arm 済み
        result = w.ensure_running()
        assert result["healed"] is True           # 初回 heal が起動経路
        assert w._thread is not None and w._thread.is_alive()
        w.stop()
    finally:
        monkeypatch.setattr(pi, "_worker", None)


def test_status_exposes_poll_phase(db_path):
    """current_phase/phase_since が status に出る (ハング位置の特定用)。"""
    w, _ = make_myfx_worker(db_path, [(True, make_outlook_response())])
    st = w.status()
    assert st["current_phase"] == "idle"
    w.poll_once()
    st = w.status()
    assert st["current_phase"] == "idle"          # cycle 完了後は idle に戻る
    assert st["phase_since"] is not None
