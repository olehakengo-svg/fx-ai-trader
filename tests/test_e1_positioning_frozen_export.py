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
CUTOFF1P = fx.parse_utc(fx.look_spec(1, postponed=True)["cutoff"])   # §2.5-3 +4 週
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


def make_world(n_per_inst=30, n_after_cutoff=5, step_min=20, n_after_postponed=0):
    """13 instrument × n 行 (cutoff 前) + cutoff 後 n_after 行 (postponed cutoff 以下)
    + postponed cutoff 後 n_after_postponed 行、health_log 系列。"""
    t0 = fx.parse_utc(fx.T0_ISO)
    snaps, health = [], []
    hid = 0
    for k, inst in enumerate(fx.INSTRUMENTS):
        for i in range(n_per_inst + n_after_cutoff + n_after_postponed):
            if i < n_per_inst:
                t = t0 + timedelta(minutes=step_min * i, seconds=k)
            elif i < n_per_inst + n_after_cutoff:
                t = CUTOFF1 + timedelta(minutes=step_min * (i - n_per_inst + 1))
            else:
                t = CUTOFF1P + timedelta(minutes=step_min * (i - n_per_inst - n_after_cutoff + 1))
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


def _write_full_parquets(d, cutoff=None, pairs=None, drop_tail_bars=0, start=None):
    """t0 − 1 日 〜 cutoff + 2h の M15 合成 parquet (preflight 範囲要件を満たす)。"""
    import pandas as pd
    cutoff = cutoff or CUTOFF1
    start = start or (fx.parse_utc(fx.T0_ISO) - timedelta(days=1)).replace(
        minute=0, second=0, microsecond=0)
    end = cutoff + timedelta(hours=2)
    idx = pd.date_range(start, end, freq="15min", tz="UTC")
    # 市場閉場 (NY Fri 17:00 〜 Sun 17:00) のスロットは実データ同様に存在しない
    idx = idx[np.array([ev.is_market_open(t) for t in idx.to_pydatetime()])]
    if drop_tail_bars:
        idx = idx[idx + pd.Timedelta(seconds=900) <= pd.Timestamp(cutoff)][:-drop_tail_bars]
    os.makedirs(d, exist_ok=True)
    px = 100.0 + np.arange(len(idx)) * 0.001
    for pair in (pairs or fx.INSTRUMENTS):
        pd.DataFrame({"Open": px, "High": px + 0.05, "Low": px - 0.05, "Close": px + 0.01,
                      "Volume": 1.0}, index=idx).to_parquet(os.path.join(d, f"{pair}_15m.parquet"))
    return idx


def _run(tmp_path, api, postponed=False, now=None, **kw):
    paths = fx.default_paths(1, str(tmp_path), postponed=postponed)
    import io
    buf = io.StringIO()
    if now is None:
        now = (CUTOFF1P if postponed else CUTOFF1) + timedelta(hours=2)
    rc = fx.run_freeze(api, 1, paths, api_base="https://fake.invalid", out=buf,
                       now=now, postponed=postponed, **kw)
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

    def test_postponed_spec_is_prereg_four_week_slide(self):
        """pre-reg §2.5-3 / §7: postpone = cutoff・verdict を同幅 4 週スライド (1 回限り)。"""
        assert fx.POSTPONE_WEEKS == 4
        sp = fx.look_spec(1, postponed=True)
        assert sp["cutoff"] == "2026-11-05T06:33:31Z"
        assert fx.parse_utc(sp["cutoff"]) - CUTOFF1 == timedelta(weeks=4)
        assert sp["verdict"] == "2026-11-12"
        assert sp["original_cutoff"] == fx.LOOKS[1]["cutoff"]
        assert sp["postponed"] is True and sp["slug"] == "first-look-postponed"
        base = fx.look_spec(1)
        assert base["postponed"] is False and base["cutoff"] == fx.LOOKS[1]["cutoff"]
        with pytest.raises(ValueError):
            fx.look_spec(2, postponed=True)      # second look に postpone は無い (§4.4)
        # 判定器は --cutoff 上書き + --postponed-before を受ける (2 回目不達 = DEFERRED)
        import argparse
        parser_src = open(ev.__file__, encoding="utf-8").read()
        assert "--postponed-before" in parser_src and '"--cutoff"' in parser_src
        assert ev.overall_verdict({}, True, False, 1) == "POSTPONE"
        assert ev.overall_verdict({}, True, True, 1) == "DEFERRED"

    def test_default_paths_postponed_is_distinct_marker(self):
        p = fx.default_paths(1, "/x")
        pp = fx.default_paths(1, "/x", postponed=True)
        assert pp["sha256"] == "/x/e1-first-look-postponed-freeze-2026-11-05.sha256"
        assert pp["manifest"] == "/x/e1-first-look-postponed-freeze-2026-11-05.manifest.json"
        assert pp["artifact"].endswith("e1-first-look-postponed-freeze-2026-11-05/"
                                       "e1_prereg_frozen_export_look1_postponed.json")
        assert len({p["sha256"], pp["sha256"], fx.default_paths(2, "/x")["sha256"]}) == 3

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

    def test_fetch_ledger_accounts_for_every_returned_row(self):
        """§2.5-5(b): API 返却件数 = kept + dedup + beyond_cutoff (切詰め検知の台帳)。"""
        snaps, health = make_world(n_per_inst=30, n_after_cutoff=5)
        api = FakeApi(snaps, health, page_limit=7)
        led = {}
        rows = fx.fetch_snapshots(api, "USD_JPY", CUTOFF1, page_limit=7, ledger=led)
        assert led["rows_kept"] == len(rows) == 30
        assert led["rows_dedup"] > 0                    # from= 境界の重複を数えている
        assert led["rows_beyond_cutoff"] >= 1
        assert led["rows_returned"] == led["rows_kept"] + led["rows_dedup"] + led["rows_beyond_cutoff"]
        assert led["pages"] == len(api.calls)

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

    def test_export_starts_at_prereg_t0_and_drops_pre_t0_rows(self):
        """P2 (5 巡目): 初回ページの from= は t0 (秒精度 prefix)、pre-t0 の outlook 行は panel に入れない。"""
        snaps, health = make_world(n_per_inst=5, n_after_cutoff=0)
        t0 = fx.parse_utc(fx.T0_ISO)
        pre = [dict(snaps[0], snapshot_time=_iso_us(t0 - timedelta(minutes=20 * k)))
               for k in range(1, 4)]                     # 歴史 outlook 行 (t0 前)
        api = FakeApi(pre + snaps, health)
        led = {}
        rows = fx.fetch_snapshots(api, "USD_JPY", CUTOFF1, ledger=led)
        assert api.calls[0]["from"] == "2026-07-16T06:33:31"          # Z なし prefix
        assert len(rows) == 5 and all(fx.parse_utc(r["snapshot_time"]) >= t0 for r in rows)
        assert any(fx.parse_utc(r["snapshot_time"]) == t0 for r in rows)  # t0 の行そのものは入る
        assert led["from_first"] == "2026-07-16T06:33:31"
        # サーバが from= を無視しても行単位で落ちる
        ignoring = lambda path, params: api(path, {k: v for k, v in params.items() if k != "from"})
        led2 = {}
        rows2 = fx.fetch_snapshots(ignoring, "USD_JPY", CUTOFF1, ledger=led2)
        assert len(rows2) == 5 and led2["rows_before_t0"] >= 3     # ページ毎に再カウント (恒等式が主張)
        assert all(fx.parse_utc(r["snapshot_time"]) >= t0 for r in rows2)
        assert led2["rows_returned"] == led2["rows_kept"] + led2["rows_dedup"] + \
            led2["rows_beyond_cutoff"] + led2["rows_before_t0"]

    def test_server_side_limit_rounding_does_not_truncate(self):
        """サーバが limit を要求より小さく丸めても (page_limit 未満の返却)、
        snapshots / health とも全行を取り切る (§2.5-5(b) 切詰め封鎖)。"""
        snaps, health = make_world(n_per_inst=30, n_after_cutoff=0)
        api = FakeApi(snaps, health, page_limit=7)          # 要求 20000 → 7 に丸められる
        rows = fx.fetch_snapshots(api, "USD_JPY", CUTOFF1)   # default page_limit=20000
        assert len(rows) == 30
        hrows = fx.fetch_health_log(api, CUTOFF1)
        assert len(hrows) == sum(1 for r in health if fx.parse_utc(r["value"]) <= CUTOFF1)

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
        assert len(rec) == 2                      # artifact + manifest
        art_entries = {k: v for k, v in rec.items() if k.endswith("look1.json")}
        (rel, want), = art_entries.items()
        assert want == fx.sha256_file(paths["artifact"])
        assert fx.sha256_file(paths["manifest"]) in rec.values()
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

    def test_api_to_artifact_roundtrip_recorded_in_manifest(self, tmp_path):
        """§2.5-5(b): 凍結時に API 応答 ↔ ディスク再読 artifact を突合し manifest に永続化。"""
        snaps, health = make_world()
        rc, paths, out = _run(tmp_path, FakeApi(snaps, health, page_limit=50))
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        rt = man["roundtrip_check"]
        assert rt["ok"] is True
        assert rt["snapshots"]["api_rows"] == rt["snapshots"]["artifact_rows"] == 13 * 30
        assert rt["snapshots"]["keys_match"] and rt["snapshots"]["digest_match"]
        assert rt["snapshots"]["api_digest"] == rt["snapshots"]["artifact_digest"]
        assert rt["health"]["api_rows"] == rt["health"]["artifact_rows"] == 13 * 30 + 5
        assert rt["health"]["digest_match"]
        assert rt["fetch_ledger_consistent"] is True
        assert set(rt["fetch_ledger"]) == set(fx.INSTRUMENTS)
        led = rt["fetch_ledger"]["USD_JPY"]
        assert led["rows_kept"] == 30 and led["rows_beyond_cutoff"] >= 1
        assert "roundtrip API->artifact: OK (snapshots 390/390" in out
        # --verify は記録済み roundtrip 結果を返す
        res = fx.verify_record(paths["sha256"], root="/")
        assert res["ok"] and res["roundtrip"] == {"ok": True, "snapshots_rows": 390,
                                                  "health_rows": 395}
        # digest は値ではなく行の canonical hash — 値を 1 つ変えると変わる
        alt = json.loads(json.dumps(snaps))
        alt[0]["pct_long_total"] = 12.3456
        assert fx.rows_digest(alt) != fx.rows_digest(snaps)
        assert fx.rows_digest(list(reversed(snaps))) == fx.rows_digest(snaps)   # 順序非依存

    def test_roundtrip_mismatch_refuses_and_writes_no_marker(self, tmp_path, capsys, monkeypatch):
        """artifact 直列化で 1 行落ちたら marker を書かず exit 2 (本番へ再問い合わせしない)。"""
        snaps, health = make_world(n_per_inst=4, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        real_write = fx.write_json_atomic

        def lossy_write(path, obj):
            if isinstance(obj, dict) and "snapshots" in obj:
                obj = dict(obj, snapshots=obj["snapshots"][:-1])
            real_write(path, obj)
        monkeypatch.setattr(fx, "write_json_atomic", lossy_write)
        n_calls_before = None
        rc, paths, out = _run(tmp_path, api)
        assert rc == fx.EXIT_FAIL
        err = capsys.readouterr().err
        assert "REFUSED" in err and "roundtrip" in err
        assert not os.path.exists(paths["sha256"])
        assert not os.path.exists(paths["manifest"])
        assert not os.path.exists(paths["artifact"])          # staging のまま公開されない
        assert os.path.exists(paths["artifact_staging"])
        assert out == ""
        assert not FLOAT_RE.search(err), err
        # 値の変化 (件数同一) も digest で捕まえる
        monkeypatch.setattr(fx, "write_json_atomic", real_write)

        def mutating_write(path, obj):
            if isinstance(obj, dict) and "snapshots" in obj:
                rows = json.loads(json.dumps(obj["snapshots"]))
                rows[0]["pct_long_total"] = 99.0
                obj = dict(obj, snapshots=rows)
            real_write(path, obj)
        monkeypatch.setattr(fx, "write_json_atomic", mutating_write)
        n_calls = len(api.calls)
        rc_refused, _, _ = _run(tmp_path, api)          # 台帳に失敗試行あり → --force 必須
        assert rc_refused == fx.EXIT_REFUSED_FROZEN
        assert len(api.calls) == n_calls                # 本番へ再問い合わせしない
        rc2, paths2, _ = _run(tmp_path, api, force=True)
        assert rc2 == fx.EXIT_FAIL
        assert not os.path.exists(paths2["sha256"])
        j = json.load(open(paths2["attempts"]))
        assert [a["status"] for a in j["attempts"]] == ["failed", "failed"]
        assert j["attempts"][0]["reason"] == "roundtrip_mismatch"
        assert j["attempts"][1]["force"] is True
        assert not FLOAT_RE.search(open(paths2["attempts"]).read())

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
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api)
        assert rc == fx.EXIT_FAIL
        assert not os.path.exists(paths["sha256"])
        # 台帳に「本番へ問い合わせ済み・失敗」が残り、--force なしの再実行は拒否 (P1 2 巡目)
        j = json.load(open(paths["attempts"]))
        assert len(j["attempts"]) == 1 and j["attempts"][0]["status"] == "failed"
        assert j["attempts"][0]["reason"] == "instruments_missing"
        assert j["attempts"][0]["api_queried"] is True
        n_calls = len(api.calls)
        rc_refused, _, _ = _run(tmp_path, api, allow_missing=True)
        assert rc_refused == fx.EXIT_REFUSED_FROZEN
        assert len(api.calls) == n_calls
        rc, paths, _ = _run(tmp_path, api, allow_missing=True, force=True)
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert man["snapshots_summary"]["instruments_missing"] == ["EUR_GBP"]
        assert [a["status"] for a in man["attempts"]] == ["failed", "frozen"]
        assert man["force_history"] == []            # marker は無かったので supersede ではない


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

    def test_attempt_recorded_before_first_api_request(self, tmp_path):
        """P1 (2 巡目): fetch 中の例外でも台帳に試行が残り、次回は --force 必須。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        good = FakeApi(snaps, health)
        calls = []

        def flaky(path, params):
            calls.append(params)
            if len(calls) == 3:
                raise RuntimeError("HTTP 502")
            return good(path, params)
        paths = fx.default_paths(1, str(tmp_path))
        with pytest.raises(RuntimeError, match="502"):
            fx.run_freeze(flaky, 1, paths, api_base="https://fake.invalid",
                          now=CUTOFF1 + timedelta(hours=1))
        j = json.load(open(paths["attempts"]))
        assert j["attempts"][0]["status"] == "failed"
        assert j["attempts"][0]["reason"].startswith("fetch error")
        assert not os.path.exists(paths["sha256"]) and not os.path.exists(paths["manifest"])
        n = len(good.calls)                      # flaky は good を経由して記録する
        rc = fx.run_freeze(good, 1, paths, api_base="https://fake.invalid",
                           now=CUTOFF1 + timedelta(hours=1))
        assert rc == fx.EXIT_REFUSED_FROZEN and len(good.calls) == n   # 再問い合わせなし
        rc = fx.run_freeze(good, 1, paths, api_base="https://fake.invalid",
                           now=CUTOFF1 + timedelta(hours=1), force=True)
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert [a["status"] for a in man["attempts"]] == ["failed", "frozen"]
        assert man["attempts"][1]["snapshots_rows"] == 13 * 3

    def test_preflight_ohlcv_missing_stops_before_api(self, tmp_path, capsys):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        src = tmp_path / "src"; src.mkdir()            # parquet 無し
        rc, paths, out = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(tmp_path / "dst"))
        assert rc == fx.EXIT_FAIL
        assert "preflight" in capsys.readouterr().err
        assert api.calls == []                         # API 要求前に停止
        assert not os.path.exists(paths["attempts"])   # 試行にも数えない
        rc2, _, _ = _run(tmp_path, api)                # 台帳空 → 通常実行できる
        assert rc2 == fx.EXIT_OK

    def test_force_failure_preserves_prior_freeze(self, tmp_path, monkeypatch, capsys):
        """P1 (2 巡目): --force 中に roundtrip / スライスで落ちても前回凍結は byte 不改変。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api)
        assert rc == fx.EXIT_OK
        before = {k: open(paths[k], "rb").read() for k in ("artifact", "sha256", "manifest")}
        real_write = fx.write_json_atomic

        def lossy_write(path, obj):
            if isinstance(obj, dict) and "snapshots" in obj:
                obj = dict(obj, snapshots=obj["snapshots"][:-1])
            real_write(path, obj)
        monkeypatch.setattr(fx, "write_json_atomic", lossy_write)
        rc2, _, out2 = _run(tmp_path, api, force=True)
        assert rc2 == fx.EXIT_FAIL and out2 == ""
        assert {k: open(paths[k], "rb").read() for k in before} == before
        monkeypatch.setattr(fx, "write_json_atomic", real_write)

        def boom(*a, **k):
            raise RuntimeError("parquet corrupt")
        monkeypatch.setattr(fx, "slice_ohlcv", boom)
        src = tmp_path / "src"
        _write_full_parquets(str(src))                 # preflight を通す
        with pytest.raises(RuntimeError, match="parquet corrupt"):
            _run(tmp_path, api, force=True, ohlcv_src=str(src), ohlcv_dst=str(tmp_path / "dst"))
        assert {k: open(paths[k], "rb").read() for k in before} == before
        j = json.load(open(paths["attempts"]))
        assert [a["status"] for a in j["attempts"]] == ["frozen", "failed", "failed"]
        # 前回凍結は verify OK のまま
        assert fx.verify_record(paths["sha256"], root="/")["ok"]

    def test_publish_order_manifest_before_marker(self, tmp_path, monkeypatch, capsys):
        """P2 (2 巡目): marker だけが残る状態を作らない (manifest → marker の順)。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        real_write = fx.write_json_atomic

        def fail_on_manifest(path, obj):
            if ".manifest.json" in path:
                raise OSError("disk full")
            real_write(path, obj)
        monkeypatch.setattr(fx, "write_json_atomic", fail_on_manifest)
        with pytest.raises(OSError):
            _run(tmp_path, api)
        paths = fx.default_paths(1, str(tmp_path))
        assert not os.path.exists(paths["sha256"])      # marker は manifest 無しでは存在しない
        assert not os.path.exists(paths["manifest"])
        assert not os.path.exists(paths["artifact"])    # 公開途中の失敗はロールバック
        assert not os.path.exists(paths["lock"])        # lock は解放
        j = json.load(open(paths["attempts"]))
        assert j["attempts"][-1]["status"] == "failed"
        assert j["attempts"][-1]["reason"].startswith("publish error")

    def test_publish_failure_rolls_back_prior_freeze(self, tmp_path, monkeypatch):
        """P1 (3 巡目): 公開フェーズ途中 (artifact/parquet 差し替え後、marker 書込みで失敗) でも
        前回凍結の全ファイルが byte 単位で復元され、.bak が残らない。"""
        src = tmp_path / "src"; dst = tmp_path / "dst"
        _write_full_parquets(str(src))
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst))
        assert rc == fx.EXIT_OK
        files = [paths["artifact"], paths["sha256"], paths["manifest"]] + \
                [str(dst / f"{p}_15m.parquet") for p in fx.INSTRUMENTS]
        before = {f: open(f, "rb").read() for f in files}
        listing_before = sorted(os.listdir(dst))

        def boom(*a, **k):
            raise OSError("disk full at marker")
        monkeypatch.setattr(fx, "write_sha256_record", boom)
        # 新しい行を 1 本足して artifact bytes が確実に変わる状態で --force
        snaps2 = snaps + [dict(snaps[0], snapshot_time=_iso_us(CUTOFF1 - timedelta(minutes=1)))]
        api2 = FakeApi(snaps2, health)
        with pytest.raises(OSError, match="disk full"):
            _run(tmp_path, api2, force=True, ohlcv_src=str(src), ohlcv_dst=str(dst))
        assert {f: open(f, "rb").read() for f in files} == before
        assert sorted(os.listdir(dst)) == listing_before          # .bak / .staging 残置なし
        assert not any(n.endswith(".bak") for n in os.listdir(tmp_path))
        assert not os.path.exists(paths["lock"])
        assert fx.verify_record(paths["sha256"], root="/")["ok"]
        j = json.load(open(paths["attempts"]))
        assert [a["status"] for a in j["attempts"]] == ["frozen", "failed"]

    def test_lock_serializes_concurrent_invocations(self, tmp_path, capsys):
        """P1 (3 巡目): lock 保持中の 2 本目は API 要求も台帳登録もせず exit 3。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        paths = fx.default_paths(1, str(tmp_path))
        # 1 本目が lock を持っている最中に 2 本目が走る状況を fetcher 内から再現
        inner = {}

        def racing(path, params):
            if not inner:
                inner["rc"] = fx.run_freeze(FakeApi(snaps, health), 1, paths,
                                            api_base="https://fake.invalid",
                                            now=CUTOFF1 + timedelta(hours=1))
                inner["calls_at"] = len(api.calls)
            return api(path, params)
        rc = fx.run_freeze(racing, 1, paths, api_base="https://fake.invalid",
                           now=CUTOFF1 + timedelta(hours=1))
        assert rc == fx.EXIT_OK
        assert inner["rc"] == fx.EXIT_REFUSED_FROZEN
        assert "lock" in capsys.readouterr().err
        j = json.load(open(paths["attempts"]))
        assert len(j["attempts"]) == 1                    # 2 本目は試行にならない
        assert not os.path.exists(paths["lock"])          # 終了後は解放
        # 異常終了で残った lock も手で消すまで拒否 (自動削除しない)
        open(paths["lock"], "w").write("pid=0 started=stale\n")
        rc2 = fx.run_freeze(api, 1, paths, api_base="https://fake.invalid",
                            now=CUTOFF1 + timedelta(hours=1), force=True)
        assert rc2 == fx.EXIT_REFUSED_FROZEN
        assert os.path.exists(paths["lock"])

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


# ── postpone (§2.5-3 family gate 不成立 → 4 週スライド、元凍結は不改変) ─────

class TestPostponedLook:
    def test_postponed_requires_original_freeze(self, tmp_path, capsys):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=2)
        api = FakeApi(snaps, health)
        rc, paths, out = _run(tmp_path, api, postponed=True)
        assert rc == fx.EXIT_FAIL
        assert "REFUSED" in capsys.readouterr().err
        assert api.calls == []                       # API へ問い合わせもしない
        assert not os.path.exists(paths["sha256"]) and out == ""

    def test_postponed_freeze_preserves_original_and_extends_cutoff(self, tmp_path):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=4, n_after_postponed=3)
        api = FakeApi(snaps, health)
        rc, p1, _ = _run(tmp_path, api)
        assert rc == fx.EXIT_OK
        orig_art = open(p1["artifact"], "rb").read()
        orig_sha = open(p1["sha256"]).read()
        orig_man = open(p1["manifest"]).read()

        rc2, p1p, out = _run(tmp_path, api, postponed=True)
        assert rc2 == fx.EXIT_OK
        assert p1p["sha256"] != p1["sha256"] and os.path.exists(p1p["sha256"])
        # 元凍結は byte 単位で不改変
        assert open(p1["artifact"], "rb").read() == orig_art
        assert open(p1["sha256"]).read() == orig_sha
        assert open(p1["manifest"]).read() == orig_man
        # postponed artifact: 10-08 < t ≤ 11-05 の行が入り、11-05 超は入らない
        art = ev.load_artifact(p1p["artifact"])
        ts = [fx.parse_utc(r["snapshot_time"]) for r in art["snapshots"]]
        assert len(art["snapshots"]) == 13 * (3 + 4)
        assert sum(1 for t in ts if t > CUTOFF1) == 13 * 4
        assert all(t <= CUTOFF1P for t in ts)
        assert art["synthetic"] is False
        raw = json.load(open(p1p["artifact"]))
        assert raw["meta"]["postponed"] is True
        assert raw["meta"]["cutoff"] == "2026-11-05T06:33:31Z"
        assert raw["meta"]["original_cutoff"] == fx.LOOKS[1]["cutoff"]
        man = json.load(open(p1p["manifest"]))
        assert man["postponed"] is True and man["postpone_weeks"] == 4
        assert man["cutoff"] == "2026-11-05T06:33:31Z"
        assert man["verdict_deadline"] == "2026-11-12"
        assert man["force_history"] == []
        assert man["roundtrip_check"]["ok"] is True
        assert "postponed +4w from 2026-10-08T06:33:31Z" in out
        assert not FLOAT_RE.search(out), out
        # 判定器は postponed cutoff + --postponed-before を受理して (synthetic=false →) 拒否
        rc3 = ev.main(["--artifact", p1p["artifact"], "--ohlcv-dir", str(tmp_path),
                       "--cutoff", man["cutoff"], "--look", "1", "--postponed-before",
                       "--n-boot", "5"])
        assert rc3 == 2

    def test_postponed_before_its_cutoff_refused(self, tmp_path, capsys):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        rc, _, _ = _run(tmp_path, api)
        assert rc == fx.EXIT_OK
        rc2, p, _ = _run(tmp_path, api, postponed=True, now=CUTOFF1P - timedelta(days=1))
        assert rc2 == fx.EXIT_FAIL
        assert "REFUSED" in capsys.readouterr().err
        assert not os.path.exists(p["sha256"])

    def test_postponed_is_once_only_too(self, tmp_path, capsys):
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        assert _run(tmp_path, api)[0] == fx.EXIT_OK
        assert _run(tmp_path, api, postponed=True)[0] == fx.EXIT_OK
        rc, _, _ = _run(tmp_path, api, postponed=True)
        assert rc == fx.EXIT_REFUSED_FROZEN

    def test_cli_postponed_only_for_look1(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(fx, "http_fetcher", lambda base, timeout=0: FakeApi([], []))
        rc = fx.main(["--look", "2", "--postponed", "--out-dir", str(tmp_path),
                      "--api-base", "https://fake.invalid"])
        assert rc == fx.EXIT_FAIL
        assert "--postponed" in capsys.readouterr().err
        assert list(tmp_path.iterdir()) == []


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
        for p in (paths["manifest"], paths["sha256"], paths["attempts"]):
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
    """合成 parquet のみ (data/cache/massive 非依存)。index の datetime 分解能を
    ns / us で明示して書く — pandas 3 + pyarrow の roundtrip は datetime64[us] を返し、
    旧 load_bars (`view("int64") // 10**9`) が CI で epoch を 1/1000 に潰した
    (PR #286 CI: `assert 26 == 32`)。"""

    def _write_parquets(self, d, n_after=8, unit="ns"):
        import pandas as pd
        base = CUTOFF1.replace(minute=0, second=0, microsecond=0) - timedelta(hours=6)
        idx = pd.date_range(base, periods=24 + n_after, freq="15min", tz="UTC").as_unit(unit)
        for pair in fx.INSTRUMENTS:
            px = 100.0 + np.arange(len(idx)) * 0.01
            df = pd.DataFrame({"Open": px, "High": px + 0.05, "Low": px - 0.05,
                               "Close": px + 0.01, "Volume": 1.0, "vwap": px}, index=idx)
            df.to_parquet(os.path.join(d, f"{pair}_15m.parquet"))
        return idx

    @pytest.mark.parametrize("unit", ["ns", "us"])
    def test_slice_matches_evaluator_clip(self, tmp_path, unit):
        src = tmp_path / "src"; dst = tmp_path / "dst"
        src.mkdir()
        idx = self._write_parquets(str(src), unit=unit)
        meta = fx.slice_ohlcv(str(src), str(dst), CUTOFF1)
        assert set(meta) == set(fx.INSTRUMENTS)
        m = meta["USD_JPY"]
        # 判定器 load_bars の epoch は index の epoch 秒に一致 (分解能非依存)
        bars = ev.load_bars(str(src), "USD_JPY")
        expected_ep = np.array([t.timestamp() for t in idx.to_pydatetime()])
        np.testing.assert_array_equal(bars["ep"], expected_ep)
        # 判定器の clip_bars_to_cutoff と同じ本数、合成の期待値 (完結 bar のみ) とも一致
        clipped, n_drop = ev.clip_bars_to_cutoff(bars, CUTOFF1)
        n_expected = int(sum(1 for t in idx.to_pydatetime()
                             if t + timedelta(seconds=900) <= CUTOFF1))
        assert m["rows"] == len(clipped["ep"]) == n_expected == 26
        assert m["rows_dropped"] == n_drop == len(idx) - 26
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
        _write_full_parquets(str(src))
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, out = _run(tmp_path, FakeApi(snaps, health),
                              ohlcv_src=str(src), ohlcv_dst=str(dst))
        assert rc == fx.EXIT_OK
        rec = fx.read_sha256_record(paths["sha256"])
        assert len(rec) == 2 + 13                 # artifact + manifest + 13 parquet
        assert not FLOAT_RE.search(out), out
        man = json.load(open(paths["manifest"]))
        assert set(man["ohlcv_slice"]) == set(fx.INSTRUMENTS)
        assert all(c["ok"] for c in man["ohlcv_coverage"].values())
        assert man["ohlcv_coverage"]["USD_JPY"]["last_complete_bar_open"] == "2026-10-08T06:15:00Z"
        assert man["ohlcv_coverage"]["USD_JPY"]["lag_bars"] == 0
        assert man["ohlcv_max_lag_bars"] == 0
        # スライス後の末尾 = 完結 bar の最後
        assert man["ohlcv_slice"]["USD_JPY"]["last_bar_open"] == "2026-10-08T06:15:00Z"
        res = fx.verify_record(paths["sha256"], root="/")
        assert res["ok"], res

    def test_preflight_rejects_stale_or_short_ohlcv(self, tmp_path, capsys):
        """P1 (4 巡目): 末尾が欠けた / 開始が遅い parquet は API 要求前に exit 2。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        api = FakeApi(snaps, health)
        src = tmp_path / "src"; dst = tmp_path / "dst"
        _write_full_parquets(str(src))
        _write_full_parquets(str(src), pairs=["EUR_GBP"], drop_tail_bars=3)   # stale tail
        rc, paths, out = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst))
        err = capsys.readouterr().err
        assert rc == fx.EXIT_FAIL and api.calls == [] and out == ""
        assert "preflight" in err and "EUR_GBP" in err and "stale_tail" in err
        assert "lag 3 bars" in err
        assert not os.path.exists(paths["attempts"])
        # lag 許容を 3 に上げれば通り、manifest に記録される
        rc, paths, _ = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst),
                            ohlcv_max_lag_bars=3)
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert man["ohlcv_coverage"]["EUR_GBP"]["lag_bars"] == 3
        assert man["ohlcv_max_lag_bars"] == 3
        # 開始が t0 より後 → start_too_late
        src2 = tmp_path / "src2"
        _write_full_parquets(str(src2))
        _write_full_parquets(str(src2), pairs=["USD_JPY"],
                             start=fx.parse_utc(fx.T0_ISO) + timedelta(hours=1))
        api2 = FakeApi(snaps, health)
        rc2, _, _ = _run(tmp_path / "o2", api2, ohlcv_src=str(src2), ohlcv_dst=str(tmp_path / "d2"))
        assert rc2 == fx.EXIT_FAIL and api2.calls == []
        assert "start_too_late" in capsys.readouterr().err

    def test_preflight_rejects_interior_gaps_duplicates_unsorted(self, tmp_path, capsys):
        """P1 (5 巡目): 端点が正しくても内部の市場時間欠落 / 重複 / 非単調は API 要求前に exit 2。
        週末 (市場閉場) の不在は欠落に数えない。"""
        import pandas as pd
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        src = tmp_path / "src"; dst = tmp_path / "dst"
        full = _write_full_parquets(str(src))
        # 市場閉場スロットを落とした「現実的」parquet → gap 0
        open_mask = np.array([ev.is_market_open(t) for t in full.to_pydatetime()])
        realistic = full[open_mask]
        px = 100.0 + np.arange(len(realistic)) * 0.001
        for pair in fx.INSTRUMENTS:
            pd.DataFrame({"Open": px, "High": px, "Low": px, "Close": px}, index=realistic
                         ).to_parquet(src / f"{pair}_15m.parquet")
        cov = fx.check_ohlcv_coverage(str(src), CUTOFF1)
        assert all(c["ok"] for c in cov.values())
        assert cov["USD_JPY"]["gap_bars"] == 0 and cov["USD_JPY"]["expected_market_slots"] > 5000
        t0_floor = datetime.fromtimestamp(int(fx.parse_utc(fx.T0_ISO).timestamp()) // 900 * 900,
                                          tz=timezone.utc)                     # 06:30:00Z
        assert cov["USD_JPY"]["expected_market_slots"] == len(
            [t for t in realistic.to_pydatetime()
             if t0_floor <= t <= fx.expected_last_bar_open(CUTOFF1)])
        # 内部 2 本 (市場時間、10-01 火曜 10:00/10:15) を抜く → interior_gaps
        gap_at = [pd.Timestamp("2026-10-01T10:00:00Z"), pd.Timestamp("2026-10-01T10:15:00Z")]
        gapped = realistic[~realistic.isin(gap_at)]
        assert len(gapped) == len(realistic) - 2
        pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=gapped
                     ).to_parquet(src / "EUR_GBP_15m.parquet")
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst))
        err = capsys.readouterr().err
        assert rc == fx.EXIT_FAIL and api.calls == []
        assert "EUR_GBP" in err and "interior_gaps" in err and "gaps 2 bars" in err
        assert fx.OHLCV_REFRESH_CMD in err
        c = fx.check_ohlcv_coverage(str(src), CUTOFF1)["EUR_GBP"]
        assert (c["gap_bars"], c["gap_runs"], c["gap_max_run_bars"]) == (2, 1, 2)
        assert c["gap_first"] == "2026-10-01T10:00:00Z"
        # 明示許容で通り、manifest に閾値と欠落統計が残る
        rc, paths, _ = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst),
                            ohlcv_max_gap_bars=2)
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert man["ohlcv_max_gap_bars"] == 2 and man["ohlcv_coverage"]["EUR_GBP"]["gap_bars"] == 2
        # 重複 / 非単調
        dup = realistic.append(realistic[100:101])
        pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=dup
                     ).to_parquet(src / "EUR_GBP_15m.parquet")
        c = fx.check_ohlcv_coverage(str(src), CUTOFF1)["EUR_GBP"]
        assert not c["ok"] and "duplicate_timestamps" in c["reason"] and c["duplicates"] == 1
        shuffled = realistic[list(range(1, len(realistic))) + [0]]
        pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=shuffled
                     ).to_parquet(src / "EUR_GBP_15m.parquet")
        c = fx.check_ohlcv_coverage(str(src), CUTOFF1)["EUR_GBP"]
        assert not c["ok"] and "unsorted" in c["reason"]

    def test_preflight_rejects_extra_off_grid_or_closed_bars(self, tmp_path, capsys):
        """P1 (6 巡目): 欠落ゼロでも off-grid (10:07) / 閉場 (土曜) の余分な行は exit 2。
        --ohlcv-drop-extra-bars を明示すればスライス時に落として件数を記録する。"""
        import pandas as pd
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        src = tmp_path / "src"; dst = tmp_path / "dst"
        full = _write_full_parquets(str(src))
        realistic = full[np.array([ev.is_market_open(t) for t in full.to_pydatetime()])]
        extras = pd.DatetimeIndex([pd.Timestamp("2026-10-01T10:07:00Z"),     # off-grid
                                   pd.Timestamp("2026-09-26T12:00:00Z")])    # 土曜 (閉場)
        assert not ev.is_market_open(extras[1].to_pydatetime())
        with_extra = realistic.append(extras).sort_values()
        for pair in fx.INSTRUMENTS:
            idx = with_extra if pair == "GBP_JPY" else realistic
            pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=idx
                         ).to_parquet(src / f"{pair}_15m.parquet")
        c = fx.check_ohlcv_coverage(str(src), CUTOFF1)["GBP_JPY"]
        assert not c["ok"] and c["reason"] == "extra_off_grid_or_closed_bars"
        assert c["gap_bars"] == 0 and c["extra_bars"] == 2 and c["extra_first"] == "2026-09-26T12:00:00Z"
        api = FakeApi(snaps, health)
        rc, paths, _ = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst))
        err = capsys.readouterr().err
        assert rc == fx.EXIT_FAIL and api.calls == []
        assert "GBP_JPY" in err and "extra_off_grid_or_closed_bars" in err and "extra 2" in err
        # 明示して落とす → 通り、スライス結果は期待スロット集合と一致
        rc, paths, out = _run(tmp_path, api, ohlcv_src=str(src), ohlcv_dst=str(dst),
                              ohlcv_drop_extra=True)
        assert rc == fx.EXIT_OK
        man = json.load(open(paths["manifest"]))
        assert man["ohlcv_drop_extra_bars"] is True
        assert man["ohlcv_coverage"]["GBP_JPY"]["extra_dropped_at_slice"] is True
        assert man["ohlcv_slice"]["GBP_JPY"]["rows_dropped_extra"] == 2
        assert man["ohlcv_slice"]["USD_JPY"]["rows_dropped_extra"] == 0
        sliced = ev.load_bars(str(dst), "GBP_JPY")
        base = ev.load_bars(str(dst), "USD_JPY")
        np.testing.assert_array_equal(sliced["ep"], base["ep"])
        assert all(int(e) % 900 == 0 and ev.is_market_open(datetime.fromtimestamp(e, tz=timezone.utc))
                   for e in sliced["ep"])
        assert "of which extra 2" in out and not FLOAT_RE.search(out)

    def test_preflight_only_cli_touches_nothing(self, tmp_path, capsys, monkeypatch):
        src = tmp_path / "src"
        _write_full_parquets(str(src))
        monkeypatch.setattr(fx, "http_fetcher", lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("API fetcher must not be constructed")))
        rc = fx.main(["--preflight-only", "--ohlcv-src", str(src), "--out-dir", str(tmp_path / "o")])
        cap = capsys.readouterr()
        assert rc == fx.EXIT_OK
        assert "13/13 pair OK" in cap.out and "expected last bar 2026-10-08T06:15:00Z" in cap.out
        assert not FLOAT_RE.search(cap.out + cap.err), cap.out
        assert not (tmp_path / "o").exists()
        assert sorted(os.listdir(tmp_path)) == ["src"]
        # postponed cutoff (11-05) に対しては 10-08 までの parquet は全 pair stale_tail
        rc = fx.main(["--preflight-only", "--ohlcv-src", str(src), "--look", "1", "--postponed"])
        cap = capsys.readouterr()
        assert rc == fx.EXIT_FAIL and "0/13 pair OK" in cap.out
        assert "expected last bar 2026-11-05T06:15:00Z" in cap.out    # postponed cutoff
        assert cap.out.count("stale_tail") == 13
        # 1 pair 欠落 → 12/13、missing と表示
        os.remove(src / "NZD_JPY_15m.parquet")
        rc = fx.main(["--preflight-only", "--ohlcv-src", str(src)])
        cap = capsys.readouterr()
        assert rc == fx.EXIT_FAIL and "12/13 pair OK (missing 1)" in cap.out
        assert "FAIL NZD_JPY" in cap.out and "<- missing" in cap.out

    def test_runbook_refresh_command_lists_all_13_pairs(self):
        """P1 (5 巡目、docs): bt_data_cache.py の既定 PAIRS は 6 pair — 手順書の refresh コマンドは
        tool の OHLCV_REFRESH_CMD と同一文字列 (13 pair 明示) であること。"""
        from tools import bt_data_cache as bdc
        assert len(bdc.PAIRS) < len(fx.INSTRUMENTS)          # 既定では足りない (前提の pin)
        assert set(bdc.PAIRS) <= set(fx.INSTRUMENTS)
        assert all(p in fx.OHLCV_REFRESH_CMD for p in fx.INSTRUMENTS)
        rb = os.path.join(fx.repo_root(), "knowledge-base", "wiki", "decisions",
                          "e1-first-look-runbook-2026-09-22.md")
        text = open(rb, encoding="utf-8").read()
        assert fx.OHLCV_REFRESH_CMD in text
        assert "python3 tools/bt_data_cache.py refresh 15m\n" not in text   # 6 pair 版の残置なし
        assert "refresh 15m`" not in text

    def test_expected_last_bar_open_for_fixed_cutoffs(self):
        """3 つの固定 cutoff (10-08 / 11-05 / 12-30、06:33:31Z、平日場中) の期待末尾 bar = 06:15。"""
        for look, pp in ((1, False), (1, True), (2, False)):
            c = fx.parse_utc(fx.look_spec(look, pp)["cutoff"])
            e = fx.expected_last_bar_open(c)
            assert e.strftime("%H:%M:%S") == "06:15:00" and e.date() == c.date()
            assert ev.is_market_open(c)
        # 週末に跨る cutoff は直前の金曜 close 前の bar まで遡る
        sat = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
        e = fx.expected_last_bar_open(sat)
        assert not ev.is_market_open(sat) and ev.is_market_open(e)
        assert e < sat


# ── verify (§2.5-5(b) roundtrip 突合) ─────────────────────────────────

class TestVerify:
    def test_verify_fails_when_manifest_missing_or_roundtrip_not_ok(self, tmp_path):
        """P2 (2 巡目): marker だけの凍結 (manifest 不在 / roundtrip 未記録) は FAIL。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        assert rc == fx.EXIT_OK
        assert fx.verify_record(paths["sha256"], root="/")["manifest"] == "OK"
        man = json.load(open(paths["manifest"]))
        man["roundtrip_check"]["ok"] = False
        json.dump(man, open(paths["manifest"], "w"))
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"] and res["manifest"] == "ROUNDTRIP_FAIL"
        os.remove(paths["manifest"])
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"] and res["manifest"] == "MISSING"
        # artifact は無傷 (OK)、manifest エントリは MISSING → 凍結不完全
        assert {v for k, v in res["files"].items() if k.endswith("look1.json")} == {"OK"}
        assert {v for k, v in res["files"].items() if k.endswith(".manifest.json")} == {"MISSING"}
        rc = fx.main(["--verify", paths["sha256"]])
        assert rc == fx.EXIT_FAIL

    def test_verify_detects_manifest_tamper_or_missing_manifest_entry(self, tmp_path):
        """P2 (4 巡目): manifest は marker に載る — 編集 (roundtrip ok 偽装等) は MISMATCH、
        marker から manifest エントリを抜いた記録は MANIFEST_ENTRY_MISSING。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        assert rc == fx.EXIT_OK
        assert fx.verify_record(paths["sha256"], root="/")["ok"]
        man_text = open(paths["manifest"]).read()
        man = json.loads(man_text)
        man["api_base"] = "https://elsewhere.invalid"     # 出所の書き換え
        json.dump(man, open(paths["manifest"], "w"), sort_keys=True)
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"]
        assert any(k.endswith(".manifest.json") and v == "MISMATCH" for k, v in res["files"].items())
        open(paths["manifest"], "w").write(man_text)
        assert fx.verify_record(paths["sha256"], root="/")["ok"]
        rec = fx.read_sha256_record(paths["sha256"])
        rec = {k: v for k, v in rec.items() if not k.endswith(".manifest.json")}
        fx.write_sha256_record(paths["sha256"], rec)
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"] and res["marker"] == "MANIFEST_ENTRY_MISSING"

    def test_verify_rejects_empty_or_incomplete_marker(self, tmp_path):
        """P2 (3 巡目): 0 byte marker / artifact エントリ欠落 / manifest 宣言 parquet 欠落は FAIL。"""
        snaps, health = make_world(n_per_inst=3, n_after_cutoff=0)
        rc, paths, _ = _run(tmp_path, FakeApi(snaps, health))
        assert rc == fx.EXIT_OK
        good = open(paths["sha256"]).read()
        open(paths["sha256"], "w").close()                       # truncate → 0 byte
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"] and res["marker"] == "EMPTY" and res["n"] == 0
        assert fx.main(["--verify", paths["sha256"]]) == fx.EXIT_FAIL
        # artifact 以外のエントリだけ → ARTIFACT_ENTRY_MISSING
        open(paths["sha256"], "w").write("0" * 64 + "  some/other.parquet\n")
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"] and res["marker"] == "ARTIFACT_ENTRY_MISSING"
        # manifest が parquet を宣言しているのに marker に無い → ENTRIES_MISSING_VS_MANIFEST
        open(paths["sha256"], "w").write(good)
        man = json.load(open(paths["manifest"]))
        man["ohlcv_slice"] = {"USD_JPY": {"path": "data/cache/x/USD_JPY_15m.parquet"}}
        json.dump(man, open(paths["manifest"], "w"))
        res = fx.verify_record(paths["sha256"], root="/")
        assert not res["ok"] and res["marker"] == "ENTRIES_MISSING_VS_MANIFEST"

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
