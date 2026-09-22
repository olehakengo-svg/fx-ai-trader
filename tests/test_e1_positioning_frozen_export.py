"""E1 凍結 export tool (tools/e1_positioning_frozen_export.py) の pin テスト。

spec: knowledge-base/wiki/decisions/e1-positioning-contrarian-prereg-2026-07-16.md
§2.5-6 (1 回だけ export + sha256) / §6-1 (artifact 経由のみ) / §6-2 (値の非表示)。

**全テストはオフライン・合成データのみ (§6-2)** — fetcher は fake、ネットワーク・
本番 DB・本番 positioning データへの接触は一切ない。
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from tools import e1_positioning_frozen_export as fx
from tools import e1_positioning_prereg_eval as ev

CUTOFF1 = fx.parse_utc(fx.LOOKS[1]["cutoff"])
# 合成データにだけ現れる「値」— stdout に漏れないことの pin に使う
SENTINEL_LONG = 61.2345
SENTINEL_PX = 157.6189
FLOAT_RE = re.compile(r"\d+\.\d+")


# ── 合成本番 (fake API) ────────────────────────────────────────────────

class FakeApi:
    """/api/positioning/export の from= / since_id / limit セマンティクスを再現。"""

    def __init__(self, snapshots, health, page_limit=None):
        self.snapshots = sorted(snapshots, key=lambda r: r["snapshot_time"])
        self.health = sorted(health, key=lambda r: r["id"])
        self.page_limit = page_limit
        self.calls = []

    def __call__(self, path, params):
        assert path == "/api/positioning/export"
        self.calls.append(dict(params))
        limit = int(params.get("limit", 5000))
        if self.page_limit:
            limit = min(limit, self.page_limit)
        if params.get("table") == "health_log":
            since_id = int(params.get("since_id", 0))
            rows = [r for r in self.health if r["id"] > since_id][:limit]
            return {"count": len(rows), "rows": rows}
        inst = params.get("instrument", "")
        book = params.get("book", "")
        since = params.get("from", "")
        rows = [r for r in self.snapshots
                if (not inst or r["instrument"] == inst)
                and (not book or r["book_type"] == book)
                and (not since or r["snapshot_time"] >= since)][:limit]
        return {"count": len(rows), "rows": rows}


def _iso_us(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def make_world(n_per_inst=30, n_after_cutoff=5, step_min=20):
    """13 instrument × n 行 (cutoff 前) + cutoff 後 n_after 行、health_log 系列。"""
    t0 = fx.parse_utc(fx.T0_ISO)
    snaps, health = [], []
    hid = 0
    for k, inst in enumerate(fx.INSTRUMENTS):
        for i in range(n_per_inst + n_after_cutoff):
            if i < n_per_inst:
                t = t0 + timedelta(minutes=step_min * i, seconds=k)
            else:
                t = CUTOFF1 + timedelta(minutes=step_min * (i - n_per_inst + 1))
            long_pct = SENTINEL_LONG if i == 3 else 50.0 + (i % 7) - 3.0
            snaps.append({
                "instrument": inst, "book_type": "outlook",
                "snapshot_time": _iso_us(t),
                "price": None, "bucket_width": None,
                "buckets": {"avgLongPrice": SENTINEL_PX, "avgShortPrice": SENTINEL_PX + 0.2,
                            "longPercentage": long_pct, "shortPercentage": 100.0 - long_pct},
                "pct_long_total": long_pct, "pct_short_total": round(100.0 - long_pct, 4),
                "near_imbalance": None,
                "fetched_at": t.strftime("%Y-%m-%d %H:%M:%S"),
            })
            hid += 1
            health.append({"id": hid, "key": f"verified:{inst}:outlook",
                           "value": _iso_us(t)})
    # cycle heartbeat (cutoff 前後)
    for j in range(5):
        hid += 1
        health.append({"id": hid, "key": "last_cycle_at",
                       "value": _iso_us(t0 + timedelta(hours=j))})
    hid += 1
    health.append({"id": hid, "key": "last_cycle_at",
                   "value": _iso_us(CUTOFF1 + timedelta(hours=1))})
    return snaps, health


def _run(tmp_path, api, **kw):
    paths = fx.default_paths(1, str(tmp_path))
    import io
    buf = io.StringIO()
    rc = fx.run_freeze(api, 1, paths, api_base="https://fake.invalid", out=buf,
                       now=CUTOFF1 + timedelta(hours=2), **kw)
    return rc, paths, buf.getvalue()


# ── 定数 pin (判定器 / ingest と同値) ─────────────────────────────────

class TestConstantsPinnedToEvaluator:
    def test_instruments_match_evaluator_and_ingest(self):
        assert fx.PRIMARY == ev.PRIMARY
        assert fx.CONFIRMATORY == ev.CONFIRMATORY
        from modules.positioning_ingest import DEFAULT_INSTRUMENTS, OUTLOOK_BOOK_TYPE
        assert set(fx.INSTRUMENTS) == set(DEFAULT_INSTRUMENTS)
        assert len(fx.INSTRUMENTS) == 13
        assert fx.BOOK_TYPE == OUTLOOK_BOOK_TYPE

    def test_cutoffs_match_evaluator(self):
        assert fx.LOOKS[1]["cutoff"] == ev.DEFAULT_CUTOFF_LOOK1
        assert fx.LOOKS[2]["cutoff"] == ev.DEFAULT_CUTOFF_LOOK2

    def test_default_paths_first_look(self):
        p = fx.default_paths(1, "/x")
        assert p["sha256"] == "/x/e1-first-look-freeze-2026-10-08.sha256"
        assert p["manifest"] == "/x/e1-first-look-freeze-2026-10-08.manifest.json"
        assert p["artifact"].endswith("e1-first-look-freeze-2026-10-08/"
                                      "e1_prereg_frozen_export_look1.json")
        p2 = fx.default_paths(2, "/x")
        assert p2["sha256"] == "/x/e1-second-look-freeze-2026-12-30.sha256"

    def test_http_fetcher_rejects_non_http_scheme(self):
        with pytest.raises(ValueError):
            fx.http_fetcher("file:///etc/passwd")
        f = fx.http_fetcher("https://example.invalid")
        with pytest.raises(ValueError):
            f("/api/demo/trades", {})


# ── 取得: cutoff フィルタ / ページング / dedup ───────────────────────

class TestFetch:
    def test_cutoff_filter_and_dedup_across_pages(self):
        snaps, health = make_world(n_per_inst=30, n_after_cutoff=5)
        api = FakeApi(snaps, health, page_limit=7)   # 小ページで from= 重複を強制
        rows = fx.fetch_snapshots(api, "USD_JPY", CUTOFF1, page_limit=7)
        assert len(rows) == 30                          # cutoff 後 5 行は落ちる
        assert all(fx.parse_utc(r["snapshot_time"]) <= CUTOFF1 for r in rows)
        assert len({r["snapshot_time"] for r in rows}) == 30  # dedup
        assert all(c.get("book") == "outlook" for c in api.calls)

    def test_health_pagination_and_cutoff(self):
        snaps, health = make_world(n_per_inst=4, n_after_cutoff=2)
        api = FakeApi(snaps, health, page_limit=10)
        rows = fx.fetch_health_log(api, CUTOFF1, page_limit=10)
        n_before = sum(1 for r in health if fx.parse_utc(r["value"]) <= CUTOFF1)
        assert len(rows) == n_before
        assert len(rows) < len(health)
        ids = [r["id"] for r in rows]
        assert ids == sorted(ids)
        ver, cyc = ev.extract_health_events(rows, list(fx.INSTRUMENTS))
        assert all(len(ver[i]) == 4 for i in fx.INSTRUMENTS)
        assert len(cyc) == 5

    def test_pagination_guard_fail_loud(self):
        def bad(path, params):       # 常に同じ 1 ページを返す (進まない)
            return {"rows": [{"instrument": "USD_JPY", "book_type": "outlook",
                              "snapshot_time": "2026-08-01T00:00:00Z"}] * 2}
        # new == 0 で停止する (無限ループしない)
        rows = fx.fetch_snapshots(bad, "USD_JPY", CUTOFF1, page_limit=2)
        assert len(rows) == 1


# ── roundtrip: 書く → 判定器で読む → sha256 一致 ─────────────────────

class TestRoundtrip:
    def test_freeze_roundtrip_sha256_and_evaluator_load(self, tmp_path):
        snaps, health = make_world()
        api = FakeApi(snaps, health)
        rc, paths, out = _run(tmp_path, api)
        assert rc == fx.EXIT_OK
        assert os.path.exists(paths["artifact"])
        assert os.path.exists(paths["sha256"])
        assert os.path.exists(paths["manifest"])

        rec = fx.read_sha256_record(paths["sha256"])
        assert len(rec) == 1
        (rel, want), = rec.items()
        assert want == fx.sha256_file(paths["artifact"])
        assert fx.verify_record(paths["sha256"], root=str(tmp_path))["ok"] or \
            fx.verify_record(paths["sha256"], root=fx.repo_root())["ok"]

        # 判定器の入力契約そのまま
        art = ev.load_artifact(paths["artifact"])
        assert art["synthetic"] is False           # 実データ → --verdict-run 必須
        assert len(art["snapshots"]) == 13 * 30
        assert all(r["book_type"] == "outlook" for r in art["snapshots"])
        assert all(fx.parse_utc(r["snapshot_time"]) <= CUTOFF1 for r in art["snapshots"])
        ver, cyc = ev.extract_health_events(art["health"], list(ev.PRIMARY) + list(ev.CONFIRMATORY))
        assert all(len(ver[i]) == 30 for i in ev.PRIMARY)
        assert len(cyc) == 5

        man = json.load(open(paths["manifest"]))
        assert man["cutoff"] == fx.LOOKS[1]["cutoff"]
        assert man["snapshots_summary"]["rows_total"] == 13 * 30
        assert man["snapshots_summary"]["instruments_missing"] == []
        assert man["health_summary"]["rows_total"] == 13 * 30 + 5
        assert man["force_history"] == []

    def test_evaluator_refuses_real_artifact_without_verdict_run(self, tmp_path):
        """§6-2: 凍結 artifact (synthetic=false) は --verdict-run なしで判定器が拒否。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        assert rc == fx.EXIT_OK
        rc2 = ev.main(["--artifact", paths["artifact"], "--ohlcv-dir", str(tmp_path),
                       "--n-boot", "5"])
        assert rc2 == 2

    def test_missing_instrument_fail_loud(self, tmp_path):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        snaps = [r for r in snaps if r["instrument"] != "EUR_GBP"]
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        assert rc == fx.EXIT_FAIL
        assert not os.path.exists(paths["sha256"])
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health), allow_missing=True)
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert man["snapshots_summary"]["instruments_missing"] == ["EUR_GBP"]


# ── 「1 回だけ」ガード ─────────────────────────────────────────────

class TestOnceOnlyGuard:
    def test_before_cutoff_refused_unless_force(self, tmp_path, capsys):
        """cutoff 前の凍結は評価窓を切り捨てた artifact が marker を占有する → 拒否。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        paths = fx.default_paths(1, str(tmp_path))
        rc = fx.run_freeze(api, 1, paths, api_base="https://fake.invalid",
                           now=CUTOFF1 - timedelta(days=1))
        assert rc == fx.EXIT_FAIL
        assert "REFUSED" in capsys.readouterr().err
        assert not os.path.exists(paths["sha256"])
        assert api.calls == []                        # 取得前に止まる
        rc = fx.run_freeze(api, 1, paths, api_base="https://fake.invalid",
                           now=CUTOFF1 - timedelta(days=1), force=True)
        assert rc == fx.EXIT_OK

    def test_second_run_refused_without_force(self, tmp_path, capsys):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api)
        assert rc == fx.EXIT_OK
        sha_before = fx.sha256_file(paths["artifact"])
        rec_before = open(paths["sha256"]).read()
        n_calls = len(api.calls)

        rc2, _, out2 = _run(tmp_path, api)
        err = capsys.readouterr().err
        assert rc2 == fx.EXIT_REFUSED_FROZEN
        assert "REFUSED" in err and "--force" in err
        assert len(api.calls) == n_calls              # API へ再問い合わせしない
        assert fx.sha256_file(paths["artifact"]) == sha_before
        assert open(paths["sha256"]).read() == rec_before
        assert out2 == ""

    def test_force_records_previous_sha256(self, tmp_path):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api)
        prev = fx.read_sha256_record(paths["sha256"])
        rc2, _, _ = _run(tmp_path, api, force=True)
        assert rc2 == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert len(man["force_history"]) == 1
        assert man["force_history"][0]["previous_sha256"] == prev
        assert man["force_history"][0]["previous_frozen_at"] is not None


# ── 値の非表示 (§6-2) ─────────────────────────────────────────────────

class TestNoValueLeak:
    def test_stdout_has_no_float_and_no_sentinel(self, tmp_path, capsys, monkeypatch):
        snaps, health = make_world()
        api = FakeApi(snaps, health)
        monkeypatch.setattr(fx, "http_fetcher", lambda base, timeout=0: api)
        monkeypatch.setattr(fx, "utc_now", lambda: CUTOFF1 + timedelta(hours=1))
        rc = fx.main(["--look", "1", "--out-dir", str(tmp_path),
                      "--api-base", "https://fake.invalid"])
        cap = capsys.readouterr()
        assert rc == fx.EXIT_OK
        text = cap.out + cap.err
        assert "snapshots: 390 rows, 13/13 instruments" in cap.out
        assert not FLOAT_RE.search(text), text
        for s in (str(SENTINEL_LONG), str(SENTINEL_PX), "avgLongPrice",
                  "pct_long", "longPercentage", "buckets"):
            assert s not in text
        # sha256 / 時刻範囲 / パスは出る
        assert re.search(r"sha256 [0-9a-f]{64}", cap.out)
        assert "2026-07-16T06:33:31Z" in cap.out

    def test_manifest_and_sha_record_carry_no_values(self, tmp_path):
        snaps, health = make_world()
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        for p in (paths["manifest"], paths["sha256"]):
            text = open(p).read()
            for s in (str(SENTINEL_LONG), str(SENTINEL_PX), "avgLongPrice",
                      "pct_long_total", "longPercentage"):
                assert s not in text, p

    def test_dry_run_health_writes_nothing_and_no_floats(self, tmp_path, capsys, monkeypatch):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        monkeypatch.setattr(fx, "http_fetcher", lambda base, timeout=0: api)
        monkeypatch.chdir(tmp_path)
        rc = fx.main(["--dry-run-health", "--limit", "5", "--out-dir", str(tmp_path),
                      "--api-base", "https://fake.invalid"])
        cap = capsys.readouterr()
        assert rc == fx.EXIT_OK
        assert "dry-run health_log: 5 rows" in cap.out
        assert not FLOAT_RE.search(cap.out + cap.err)
        assert list(tmp_path.iterdir()) == []
        assert all(c.get("table") == "health_log" for c in api.calls)
        assert all(int(c.get("limit", 0)) <= 50 for c in api.calls)


# ── M15 parquet cutoff スライス (§2.3、判定器 clip と同一規約) ───────

class TestOhlcvSlice:
    def _write_parquets(self, d, n_after=8):
        import pandas as pd
        base = CUTOFF1.replace(minute=0, second=0, microsecond=0) - timedelta(hours=6)
        idx = pd.date_range(base, periods=24 + n_after, freq="15min", tz="UTC")
        for pair in fx.INSTRUMENTS:
            px = 100.0 + np.arange(len(idx)) * 0.01
            df = pd.DataFrame({"Open": px, "High": px + 0.05, "Low": px - 0.05,
                               "Close": px + 0.01, "Volume": 1.0, "vwap": px}, index=idx)
            df.to_parquet(os.path.join(d, f"{pair}_15m.parquet"))
        return idx

    def test_slice_matches_evaluator_clip(self, tmp_path):
        src = tmp_path / "src"; dst = tmp_path / "dst"
        src.mkdir()
        idx = self._write_parquets(str(src))
        meta = fx.slice_ohlcv(str(src), str(dst), CUTOFF1)
        assert set(meta) == set(fx.INSTRUMENTS)
        m = meta["USD_JPY"]
        # 判定器の clip_bars_to_cutoff と同じ本数
        bars = ev.load_bars(str(src), "USD_JPY")
        clipped, n_drop = ev.clip_bars_to_cutoff(bars, CUTOFF1)
        assert m["rows"] == len(clipped["ep"])
        assert m["rows_dropped"] == n_drop
        assert m["rows"] < len(idx)
        # 切詰め後は判定器で読めて、全 bar が完結 (open + 900 ≤ cutoff)
        sliced = ev.load_bars(str(dst), "USD_JPY")
        assert (sliced["ep"] + 900 <= ev._ep(CUTOFF1)).all()
        assert m["sha256"] == fx.sha256_file(m["path"])
        assert "Open" not in json.dumps({k: v for k, v in m.items()})

    def test_slice_missing_pair_fail_loud(self, tmp_path):
        src = tmp_path / "src"; dst = tmp_path / "dst"
        src.mkdir()
        self._write_parquets(str(src))
        os.remove(src / "EUR_GBP_15m.parquet")
        with pytest.raises(RuntimeError, match="parquet 欠落"):
            fx.slice_ohlcv(str(src), str(dst), CUTOFF1)

    def test_freeze_with_slice_records_parquet_sha(self, tmp_path):
        src = tmp_path / "src"; dst = tmp_path / "dst"
        src.mkdir()
        self._write_parquets(str(src))
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, out = _run(tmp_path, FakeApi(snaps, health),
                              ohlcv_src=str(src), ohlcv_dst=str(dst))
        assert rc == fx.EXIT_OK
        rec = fx.read_sha256_record(paths["sha256"])
        assert len(rec) == 1 + 13
        assert not FLOAT_RE.search(out), out
        man = json.load(open(paths["manifest"]))
        assert set(man["ohlcv_slice"]) == set(fx.INSTRUMENTS)
        res = fx.verify_record(paths["sha256"], root="/")
        assert res["ok"], res


# ── verify (§2.5-5(b) roundtrip 突合) ─────────────────────────────────

class TestVerify:
    def test_verify_detects_tamper(self, tmp_path):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        root = fx.repo_root()
        assert fx.verify_record(paths["sha256"], root=root)["ok"] or \
            fx.verify_record(paths["sha256"], root="/")["ok"]
        with open(paths["artifact"], "a") as f:
            f.write("\n")
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"]
        assert "MISMATCH" in res["files"].values()
