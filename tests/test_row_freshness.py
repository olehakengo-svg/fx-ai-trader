"""行鮮度 (row freshness) の読み出し経路のテスト (rule:R3, 2026-08-27).

背景: 2026-08-21〜08-25 の Render Disk 満杯事故では全 SQLite 書込みが
3.5 日停止したが、ダッシュボードは「凍結」を「静かな相場」と区別できず
正常に見えた。PR #205/#206 で alert 経路 (anomaly_watcher) は塞いだが、
`/api/demo/status` 自身は依然として最終書込み時刻を持たない。

本テストは `DemoDB.get_row_freshness()` の契約を固定する:
- 「行が無い」「値が壊れている」「クエリが落ちた」を **別々の status** で
  返す (silent except で潰さない — MEMORY の教訓「silent except は不発と
  ゼロ件を区別不能にする」)。
- age は単調に増加し、書込みで戻る = 値が意味を持つ (観測基盤の第3段階)。
"""
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from modules.demo_db import DemoDB


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    os.unlink(path)


def _now():
    return datetime.now(timezone.utc)


class TestRowFreshnessContract:
    def test_empty_db_reports_no_rows_not_error(self, db):
        """空 DB は error ではなく no_rows。両者の混同が事故検知を殺す。"""
        f = db.get_row_freshness()
        assert f["last_trade_row_status"] == "no_rows"
        assert f["last_trade_row_age_sec"] is None
        assert f["last_trade_row_at"] is None
        assert f["error"] is None

    def test_keys_are_present_even_when_empty(self, db):
        """契約 key は常に存在する。欠落 key は下流で silent skip を生む
        (live_n_stagnation が 126 日 no-op だった直接原因)。"""
        f = db.get_row_freshness()
        for key in (
            "last_trade_row_at",
            "last_trade_row_age_sec",
            "last_trade_row_status",
            "last_candidate_row_at",
            "last_candidate_row_age_sec",
            "last_candidate_row_status",
            "error",
            "now",
        ):
            assert key in f, f"missing contract key: {key}"

    def test_trade_write_makes_age_small(self, db):
        """書込み直後は age ≈ 0。値が実際に動くことの確認。"""
        db.open_trade("BUY", 150.500, 150.200, 151.000, "dual_sr_bounce", 65)
        f = db.get_row_freshness()
        assert f["last_trade_row_status"] == "ok"
        assert f["last_trade_row_at"] is not None
        assert 0 <= f["last_trade_row_age_sec"] < 120

    def test_age_grows_with_wall_clock(self, db):
        """age は now の前進とともに単調増加する (定数固着の検出)。

        MEMORY 教訓: 「本来変動する量が N バー連続同値なら市場ではなく
        コードを疑う」。ここでは注入 now で単調性を pin する。
        """
        db.open_trade("BUY", 150.5, 150.2, 151.0, "dual_sr_bounce", 65)
        base = _now()
        a = db.get_row_freshness(now=base)["last_trade_row_age_sec"]
        b = db.get_row_freshness(now=base + timedelta(hours=3))["last_trade_row_age_sec"]
        assert b - a == pytest.approx(3 * 3600, abs=2)

    def test_frozen_writes_surface_as_large_age(self, db):
        """3.5 日書込み停止 = 08-21 事故の再現。age がその実時間を示す。"""
        db.open_trade("BUY", 150.5, 150.2, 151.0, "dual_sr_bounce", 65)
        outage = _now() + timedelta(days=3, hours=12)
        f = db.get_row_freshness(now=outage)
        assert f["last_trade_row_status"] == "ok"
        assert f["last_trade_row_age_sec"] > 3 * 86400

    def test_candidate_rows_tracked_independently(self, db):
        """trade と candidate は別系列。candidate だけ生きている状態
        (= シグナルは出ているが約定していない = 静かな相場) を
        「凍結」と区別できることが本 PR の目的。"""
        from dataclasses import dataclass

        from modules.candidate_logger import init_candidates_table, log_candidates

        @dataclass
        class _Cand:
            entry_type: str
            signal: str
            confidence: int
            score: float

        cand = _Cand("dual_sr_bounce", "BUY", 70, 1.0)
        init_candidates_table(db._path)
        assert log_candidates(
            db._path, [cand], cand,
            instrument="USD_JPY", tf="15m",
            bar_time="2026-08-27T03:00:00+00:00",
        ) is True
        f = db.get_row_freshness()
        assert f["last_candidate_row_status"] == "ok"
        assert 0 <= f["last_candidate_row_age_sec"] < 120
        # trade 側は空のまま = 2 系列が独立していること
        assert f["last_trade_row_status"] == "no_rows"

    def test_missing_candidate_table_is_not_an_error(self, db):
        """candidate テーブル未作成は no_rows 相当 (旧 DB 互換)。
        error に落とすと本物の障害が埋もれる。"""
        f = db.get_row_freshness()
        assert f["last_candidate_row_status"] in ("no_rows", "no_table")
        assert f["error"] is None

    def test_unparseable_timestamp_is_reported_not_swallowed(self, db):
        """壊れた時刻は unparseable として明示。黙って None にしない。"""
        db.open_trade("BUY", 150.5, 150.2, 151.0, "dual_sr_bounce", 65)
        with sqlite3.connect(db._path) as conn:
            conn.execute("UPDATE demo_trades SET created_at = 'not-a-date'")
            conn.commit()
        f = db.get_row_freshness()
        assert f["last_trade_row_status"] == "unparseable"
        assert f["last_trade_row_age_sec"] is None
        assert f["last_trade_row_at"] == "not-a-date"

    def test_query_failure_reports_error_status(self, db):
        """DB 破損時は error を立てる (no_rows と混同しない)。"""
        broken = DemoDB.__new__(DemoDB)
        broken._path = "/nonexistent-dir/does-not-exist.db"

        f = DemoDB.get_row_freshness(broken)
        assert f["last_trade_row_status"] == "error"
        assert f["error"] is not None


class TestStatusEndpointExposure:
    def test_get_status_includes_row_freshness(self, db):
        """`/api/demo/status` の payload に鮮度が載ることを pin する。
        ダッシュボードが「凍結」を判定できる唯一の経路。"""
        import modules.demo_trader as dt

        trader = dt.DemoTrader.__new__(dt.DemoTrader)
        trader._db = db
        out = dt.DemoTrader._row_freshness_payload(trader)
        assert out["last_trade_row_status"] == "no_rows"
        assert "last_candidate_row_age_sec" in out
