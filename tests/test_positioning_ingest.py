"""E1 positioning ingest — offline/deterministic tests (network なし)。

対象: modules/positioning_ingest.py (user GO 2026-07-14)
  (a) parse + trim + 集計 (fixture レスポンス JSON)
  (b) dedup (book time 同一なら skip)
  (c) schema / UNIQUE 制約
  (d) POSITIONING_INGEST_ENABLE=0 で thread 不起動
  (e) 4xx → unsupported マップ登録 + 以後 skip / 失敗カウント fail-loud
  (f) 検証 API の契約 (/api/positioning/status, /api/positioning/export)
"""
import json
import sqlite3
import threading

import pytest

from modules.positioning_ingest import (
    BOOK_TYPES,
    DEFAULT_INSTRUMENTS,
    PositioningIngestWorker,
    THREAD_NAME,
    db_book_stats,
    ensure_positioning_schema,
    export_snapshots,
    extract_book_payload,
    parse_book,
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
