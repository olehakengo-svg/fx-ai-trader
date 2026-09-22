"""mof_statements_daily の per-source isolation を固定する test pin (network 不要)。

背景 (2026-09-17, rule:R3): main() が dict literal で 5 ソースを直列評価していたため、
最後段の GDELT が 429 で raise すると先に成功していた 4 ソースの成果ごとプロセスが落ち、
workflow の commit step が走らず runner の ephemeral disk ごと破棄されていた。
実害: 2026-09-16 run 35163419350 が `[daily-conf] new=1` (my20260915.html) /
`[daily-rss] new=1` / `[score] 512 conferences` まで到達して全破棄 (repo 側 511 で停止)。

固定する不変条件:
  1. soft ソース (gdelt) の失敗は raise しない — 他ソースは全て実行される
  2. hard ソース (interventions/conferences/score/rss) の失敗は raise する
  3. raise は **全ソース試行後** — 後段のソースを道連れにしない
  4. 失敗ソースも summary に error を残す (サイレント欠損の禁止)
"""
import pytest

from tools import mof_statements_daily as D
from tools import mof_statements_ingest as ing


# 2026-09-17 run 35287482585 の実ログそのまま。**作り物の文字列を使わない** —
# soft/hard は例外の形状で決まるので、pin が実物と違う文字列を使うと
# 「429 は soft」という覆域の錯覚だけが残る (2026-09-19, rule:R3)。
REAL_429 = ("fetch failed after 4 tries: "
            "https://api.gdeltproject.org/api/v2/doc/doc?query=%22yen%20intervention%22"
            ": curl: (22) The requested URL returned error: 429")
# 上流の恒久変更の署名 — GDELT が HTTP 200 + レート制限の**散文**を返した実物
REAL_UNEXPECTED = ("unexpected GDELT response for yen_intervention: "
                   "Please limit requests to one every 5 seconds or contact")


def _patch_steps(monkeypatch, failing: dict):
    """_STEPS を全てスタブ化し、failing に挙げた名前だけ raise させる。"""
    called = []

    def make(name):
        def fn():
            called.append(name)
            if name in failing:
                raise failing[name]
            return {"ok": name}
        return fn

    monkeypatch.setattr(
        D, "_STEPS", tuple((n, make(n)) for n, _ in D._STEPS)
    )
    return called


def test_soft_gdelt_failure_does_not_raise_and_others_run(monkeypatch):
    called = _patch_steps(monkeypatch, {"gdelt": RuntimeError(REAL_429)})
    summary = D.main()

    assert [n for n, _ in D._STEPS] == called          # 全ソース試行
    assert "error" in summary["gdelt"]
    assert "429" in summary["gdelt"]["error"]
    assert summary["gdelt"]["classified"] == "soft"
    for name in ("interventions", "conferences", "score", "rss"):
        assert summary[name] == {"ok": name}


def test_hard_failure_raises_but_only_after_all_sources_ran(monkeypatch):
    called = _patch_steps(monkeypatch, {"conferences": RuntimeError("mof 503")})

    with pytest.raises(RuntimeError, match="hard sources failed: conferences"):
        D.main()

    # 中断されずに後段 (score/rss/gdelt) まで到達していること = 部分成果が残る
    assert [n for n, _ in D._STEPS] == called


def test_hard_and_soft_failures_are_reported_separately(monkeypatch):
    _patch_steps(
        monkeypatch,
        {"rss": RuntimeError("rss timeout"), "gdelt": RuntimeError(REAL_429)},
    )
    with pytest.raises(RuntimeError) as exc:
        D.main()

    msg = str(exc.value)
    assert "rss" in msg
    assert "gdelt" not in msg            # soft は raise 理由に含めない


def test_gdelt_is_the_only_soft_source():
    """soft 指定の拡大は「失敗が観測されなくなる」ので pin する。"""
    assert D._SOFT_SOURCES == {"gdelt"}


# ---------------------------------------------------------------------------
# soft/hard は**ソース名ではなく例外形状**で決まる (2026-09-19, rule:R3)
# PR #261 Codex P2: 旧実装は run_gdelt の全例外を soft に落としていたため、
# 上流の恒久変更も書込み失敗も exit 0 になり `Notify failure` が走らなかった。
# ---------------------------------------------------------------------------

def test_soft_requires_a_transient_shape_not_just_the_source_name(monkeypatch):
    """NG 入力: gdelt から出た `unexpected GDELT response` は **hard**。"""
    _patch_steps(monkeypatch, {"gdelt": RuntimeError(REAL_UNEXPECTED)})
    with pytest.raises(RuntimeError, match="hard sources failed: gdelt"):
        D.main()


def test_write_failure_in_a_soft_source_is_hard(monkeypatch):
    """NG 入力: OSError (ディスク満杯等) は自己修復しないので hard。"""
    _patch_steps(monkeypatch, {"gdelt": OSError("No space left on device")})
    with pytest.raises(RuntimeError, match="hard sources failed: gdelt"):
        D.main()


def test_transient_shape_in_a_hard_source_stays_hard(monkeypatch):
    """対称性: 形状が transient でも soft 候補でないソースは hard のまま。"""
    _patch_steps(monkeypatch, {"conferences": RuntimeError(REAL_429)})
    with pytest.raises(RuntimeError, match="hard sources failed: conferences"):
        D.main()


@pytest.mark.parametrize("msg,expected", [
    (REAL_429, True),
    ("curl: (28) Operation timed out after 120001 milliseconds", True),
    ("curl: (7) Failed to connect to api.gdeltproject.org port 443", True),
    ("curl: (22) The requested URL returned error: 503", True),
    # --- 以下は hard であるべき形状 (fail-closed の確認) ---
    (REAL_UNEXPECTED, False),
    ("curl: (22) The requested URL returned error: 404", False),
    ("curl: (22) The requested URL returned error: 403", False),
    ("something entirely new from upstream", False),
])
def test_transient_classifier_is_fail_closed(msg, expected):
    assert ing.is_transient_fetch_error(RuntimeError(msg)) is expected


# ---------------------------------------------------------------------------
# 例外軸では永久に見えない第 3 の形: 成功したまま系列が進まない
# ---------------------------------------------------------------------------

def test_gdelt_freshness_flags_a_frozen_series(tmp_path, monkeypatch):
    """NG 入力 = 本番の現状 (2026-09-13 で凍結、09-18 の run は success)。"""
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text(
            "# query: x\n# mode: timelinevol\n﻿Date,Series,Value\n"
            "2026-09-12,Volume Intensity,0.001\n"
            "2026-09-13,Volume Intensity,0\n", encoding="utf-8")

    fresh = ing.gdelt_freshness(as_of=dt.date(2026, 9, 19))
    assert fresh["ok"] is False
    assert sorted(fresh["stale"]) == sorted(ing.GDELT_QUERIES)
    for slug in ing.GDELT_QUERIES:
        assert fresh["slugs"][slug]["last_data"] == "2026-09-13"
        assert fresh["slugs"][slug]["stale_days"] == 6


def test_gdelt_freshness_does_not_fire_on_the_intrinsic_lag(tmp_path, monkeypatch):
    """反対側: 実測の内在ラグ (median 0 / max 1 日) では誤発火しない。"""
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text(
            "# query: x\n﻿Date,Series,Value\n"
            "2026-09-18,Volume Intensity,0.002\n", encoding="utf-8")
    assert ing.gdelt_freshness(as_of=dt.date(2026, 9, 19))["ok"] is True


def test_gdelt_freshness_treats_a_missing_file_as_stale(tmp_path, monkeypatch):
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path / "nope"))
    fresh = ing.gdelt_freshness(as_of=dt.date(2026, 9, 19))
    assert fresh["ok"] is False
    assert all(v["last_data"] is None for v in fresh["slugs"].values())


def test_gdelt_stale_threshold_is_pinned():
    """閾値の緩め (= 検知しなくなる方向) を pin する。"""
    assert ing.GDELT_STALE_DAYS_MAX == 3


def _stub_gdelt_fetch(monkeypatch, last_date, rows=3):
    """Make run_gdelt see a syntactically valid CSV ending at `last_date`."""
    body = "﻿Date,Series,Value\n" + "".join(
        f"2026-09-{10 + i:02d},Volume Intensity,0.00{i}\n" for i in range(rows - 1))
    body += f"{last_date},Volume Intensity,0.005\n"
    monkeypatch.setattr(ing, "fetch", lambda *a, **k: body.encode())
    monkeypatch.setattr(ing, "SLEEP_GDELT", 0)
    return body


def test_stale_gdelt_response_does_not_replace_the_stored_series(tmp_path, monkeypatch):
    """KNOWN-NG INPUT: valid CSV whose last date is too old.

    The destination CSVs used to be opened with "w" BEFORE the freshness
    check, so a stale response had already overwritten the stored series; the
    raise did not undo it, and the daily workflow commits the whole data dir
    with `if: ${{ !cancelled() }}`, so the hard failure still committed the
    regression (Codex P1, PR #272).
    """
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    good = ("# query: x\n﻿Date,Series,Value\n"
            "2026-09-18,Volume Intensity,0.009\n")
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text(good, encoding="utf-8")

    _stub_gdelt_fetch(monkeypatch, "2026-09-01")       # stale by 18 days
    monkeypatch.setattr(ing, "gdelt_freshness",
                        lambda as_of=None, paths=None: ing.__dict__[
                            "gdelt_freshness"].__wrapped__(as_of, paths)
                        if False else _real_freshness(as_of, paths))

    with pytest.raises(RuntimeError, match="did not advance"):
        ing.run_gdelt()

    for slug in ing.GDELT_QUERIES:
        assert (tmp_path / f"{slug}.csv").read_text(encoding="utf-8") == good, (
            "a rejected GDELT response must leave the stored series untouched")
    leftovers = [p.name for p in tmp_path.iterdir()
                 if p.name.endswith(".tmp.csv")]
    assert leftovers == [], f"candidate files must be cleaned up: {leftovers}"


def _real_freshness(as_of, paths):
    return _ORIG_FRESHNESS(as_of=as_of, paths=paths)


_ORIG_FRESHNESS = ing.gdelt_freshness


def test_fresh_gdelt_response_is_promoted_atomically(tmp_path, monkeypatch):
    """Counter-pin: a FRESH response must still replace the series."""
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    # The stored series must be COVERED by the candidate: a full-range
    # refetch never starts later than what is already stored, and the
    # coverage gate rejects it if it does.
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text("# old\n﻿Date,Series,Value\n"
                                              "2026-09-10,Volume Intensity,0.1\n",
                                              encoding="utf-8")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    _stub_gdelt_fetch(monkeypatch, today)

    res = ing.run_gdelt()
    assert res["freshness"]["ok"] is True
    for slug in ing.GDELT_QUERIES:
        text = (tmp_path / f"{slug}.csv").read_text(encoding="utf-8")
        assert today in text, "a fresh series must be promoted"
        assert text.startswith("# query: "), "the header must be rewritten"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp.csv")] == []


def test_fresh_but_truncated_gdelt_candidate_is_rejected(tmp_path, monkeypatch):
    """KNOWN-NG INPUT: a partial series whose LAST row is recent.

    `gdelt_freshness()` only looks at the last date, so a syntactically valid
    partial response passed and then replaced the complete history; the
    workflow committed the truncation (Codex P1, PR #272 第9巡).  GDELT is
    refetched over the full range every run, so coverage must never shrink.
    """
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    full = "# query: x\n﻿Date,Series,Value\n" + "".join(
        f"2026-08-{d:02d},Volume Intensity,0.00{d % 10}\n" for d in range(1, 29))
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text(full, encoding="utf-8")

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    _stub_gdelt_fetch(monkeypatch, today, rows=2)      # 2 rows vs 28 stored

    with pytest.raises(RuntimeError, match="REGRESSES coverage"):
        ing.run_gdelt()

    for slug in ing.GDELT_QUERIES:
        assert (tmp_path / f"{slug}.csv").read_text(encoding="utf-8") == full, (
            "a truncated candidate must not replace the stored history")
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        f"{slug}.csv" for slug in ing.GDELT_QUERIES), (
        "no candidate or promotion artifact may be left in the data directory")


def test_a_later_fetch_failure_leaves_nothing_in_the_data_directory(tmp_path, monkeypatch):
    """KNOWN-NG PATH: slug 1 succeeds, slug 2 raises.

    The candidate used to be written inside the data directory and the
    cleanup was AFTER the loop, so it never ran — and the workflow does
    `git add data/external/mof_statements/` even on failure, committing the
    temporary candidate as corpus data (Codex P2, PR #272 第9巡).
    """
    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    monkeypatch.setattr(ing, "SLEEP_GDELT", 0)
    (tmp_path / "keep.csv").write_text("sentinel\n", encoding="utf-8")

    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return ("﻿Date,Series,Value\n"
                    "2026-09-20,Volume Intensity,0.1\n").encode()
        raise RuntimeError("upstream exploded")

    monkeypatch.setattr(ing, "fetch", flaky)

    with pytest.raises(RuntimeError, match="upstream exploded"):
        ing.run_gdelt()

    assert [p.name for p in tmp_path.iterdir()] == ["keep.csv"], (
        "a mid-run failure must leave NOTHING behind in the staged tree — "
        f"found {[p.name for p in tmp_path.iterdir()]}")


def test_a_candidate_that_drops_historical_dates_is_rejected(tmp_path, monkeypatch):
    """KNOWN-NG INPUT: same row count, same first date, missing middle dates.

    The aggregate gate (rows + first date) passes this: the candidate drops
    three historical dates and appends three new trailing ones, so
    `candidate_rows >= stored_rows` and `candidate_first == stored_first`
    both hold — and the complete series is replaced by one with internal gaps
    (Codex P1, PR #272 第10巡).
    """
    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    monkeypatch.setattr(ing, "SLEEP_GDELT", 0)

    stored_dates = [f"2026-08-{d:02d}" for d in range(1, 11)]        # 01..10
    full = "# query: x\n﻿Date,Series,Value\n" + "".join(
        f"{d},Volume Intensity,0.1\n" for d in stored_dates)
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text(full, encoding="utf-8")

    # Drop 04/05/06, append 11/12/13 -> 10 rows, first still 2026-08-01.
    cand_dates = ([f"2026-08-{d:02d}" for d in (1, 2, 3, 7, 8, 9, 10)]
                  + ["2026-08-11", "2026-08-12", "2026-08-13"])
    body = "﻿Date,Series,Value\n" + "".join(
        f"{d},Volume Intensity,0.2\n" for d in cand_dates)
    monkeypatch.setattr(ing, "fetch", lambda *a, **k: body.encode())

    # The aggregate checks really do pass — that is the point of this pin.
    stored_cov = ing.gdelt_coverage(str(tmp_path / f"{list(ing.GDELT_QUERIES)[0]}.csv"))
    assert len(cand_dates) == stored_cov["rows"]
    assert cand_dates[0] == stored_cov["first"].isoformat()

    monkeypatch.setattr(ing, "GDELT_STALE_DAYS_MAX", 10_000)   # isolate coverage
    with pytest.raises(RuntimeError, match="stored date\\(s\\) missing"):
        ing.run_gdelt()

    for slug in ing.GDELT_QUERIES:
        assert (tmp_path / f"{slug}.csv").read_text(encoding="utf-8") == full, (
            "the gapped candidate must not replace the stored history")


def test_a_candidate_with_duplicated_dates_is_rejected(tmp_path, monkeypatch):
    """A duplicated date inflates the row count, faking non-regression."""
    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    monkeypatch.setattr(ing, "SLEEP_GDELT", 0)
    monkeypatch.setattr(ing, "GDELT_STALE_DAYS_MAX", 10_000)

    full = ("# query: x\n﻿Date,Series,Value\n"
            "2026-08-01,Volume Intensity,0.1\n2026-08-02,Volume Intensity,0.1\n")
    for slug in ing.GDELT_QUERIES:
        (tmp_path / f"{slug}.csv").write_text(full, encoding="utf-8")

    body = ("﻿Date,Series,Value\n2026-08-01,Volume Intensity,0.2\n"
            "2026-08-01,Volume Intensity,0.2\n2026-08-02,Volume Intensity,0.2\n")
    monkeypatch.setattr(ing, "fetch", lambda *a, **k: body.encode())

    with pytest.raises(RuntimeError, match="duplicated date"):
        ing.run_gdelt()
    for slug in ing.GDELT_QUERIES:
        assert (tmp_path / f"{slug}.csv").read_text(encoding="utf-8") == full


def test_a_failed_promotion_rolls_back_the_earlier_slugs(tmp_path, monkeypatch):
    """KNOWN-NG PATH: slug 1 promoted, slug 2's replace raises.

    `os.replace` is atomic per file but not across files, so the data
    directory held a MIXED generation — and the workflow stages everything
    even after a hard failure (`if: ${{ !cancelled() }}`), committing it
    (Codex P2, PR #272 第12巡).
    """
    import os as _os
    import datetime as dt

    monkeypatch.setattr(ing, "GDELT_DIR", str(tmp_path))
    monkeypatch.setattr(ing, "SLEEP_GDELT", 0)
    monkeypatch.setattr(ing, "GDELT_STALE_DAYS_MAX", 10_000)

    slugs = list(ing.GDELT_QUERIES)
    assert len(slugs) >= 2, "this pin needs at least two slugs"
    old = ("# query: x\n﻿Date,Series,Value\n"
           "2026-08-01,Volume Intensity,0.1\n")
    for slug in slugs:
        (tmp_path / f"{slug}.csv").write_text(old, encoding="utf-8")

    body = ("﻿Date,Series,Value\n2026-08-01,Volume Intensity,0.9\n"
            "2026-08-02,Volume Intensity,0.9\n")
    monkeypatch.setattr(ing, "fetch", lambda *a, **k: body.encode())

    real_replace = _os.replace
    calls = {"n": 0}

    def flaky_replace(src, dst):
        if str(dst).endswith(f"{slugs[1]}.csv"):
            raise OSError("disk went away mid-promotion")
        return real_replace(src, dst)

    monkeypatch.setattr(_os, "replace", flaky_replace)

    with pytest.raises(OSError, match="disk went away"):
        ing.run_gdelt()

    for slug in slugs:
        assert (tmp_path / f"{slug}.csv").read_text(encoding="utf-8") == old, (
            f"{slug}.csv must be rolled back to the previous generation — a "
            f"mixed data directory gets committed by the daily workflow")
    leftovers = sorted(p.name for p in tmp_path.iterdir()
                       if not p.name.endswith(".csv")
                       or ".promoting" in p.name or ".restoring" in p.name)
    assert leftovers == [], f"no promotion artifacts may survive: {leftovers}"
