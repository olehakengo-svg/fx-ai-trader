# -*- coding: utf-8 -*-
"""tools/e1_ohlcv_gap_backfill.py の性質 pin (全てオフライン、fetch_fn は fake)。

pin する性質:
  - 追加するのは窓内 [t0, min(last_complete, expected_last)] の市場時間 15m スロットのうち
    src に無い bar だけ。fake が返した欠落外の bar / 窓外の bar は捨てる。
  - 既存行は値・順序・dtype とも不改変 (src と dst の共通 index で equals)。
  - gaps 0 の pair は byte copy (sha256 一致)。
  - dry-run は fetch_fn を呼ばず、dst も audit も書かない。
  - 埋め残しは unfilled_bars に残り黙って受容しない。
  - stdout / audit に価格値 (\\d+\\.\\d+) が出ない。
  - 既定 t0 / cutoff は凍結 export tool の定数と同一 (手順書との同一性)。
  - 補填後は凍結 export tool の check_ohlcv_coverage で interior_gaps が消える
    (extras は t0 以前の履歴行として drop_extra=True で通す運用)。
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools import e1_ohlcv_gap_backfill as gb
from tools.e1_positioning_frozen_export import (
    BAR_SEC, LOOKS, T0_ISO, check_ohlcv_coverage, expected_market_slots, parse_utc,
)

T0 = parse_utc(T0_ISO)
CUTOFF = parse_utc(LOOKS[1]["cutoff"])
# t0 (2026-07-16T06:33:31Z) を含む 15m 境界 (木 06:30Z) から 150 本 = 金 19:45Z まで (全て市場時間内、
# 金曜 21:00Z クローズ前)。src は t0 以前から始まる必要があるので履歴行を 1 本足す (下記)
BASE = datetime(2026, 7, 16, 6, 30, tzinfo=timezone.utc)
N_BARS = 150
FLOAT_RE = re.compile(r"\d+\.\d+")


def _grid(start: datetime, n: int):
    return [start + timedelta(seconds=BAR_SEC * i) for i in range(n)]


def _frame(times, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.DatetimeIndex(times)
    close = 150.0 + rng.normal(0, 0.1, len(idx)).cumsum()
    return pd.DataFrame({
        "Open": close - 0.01, "High": close + 0.05, "Low": close - 0.05, "Close": close,
        "Volume": rng.integers(100, 1000, len(idx)).astype("float64"), "vwap": close,
    }, index=idx)


def _src_with_holes(hole_slots):
    """BASE から N_BARS 本の連続グリッドから hole_slots を抜いた src frame。
    さらに t0 以前の履歴行 (2014 年、閉場の日曜) を 1 本足して「ファイル全体の extra」を再現する。"""
    full = _grid(BASE, N_BARS)
    keep = [t for i, t in enumerate(full) if i not in set(hole_slots)]
    hist = datetime(2014, 8, 24, 3, 45, tzinfo=timezone.utc)   # 日曜 03:45Z = 閉場 (extra)
    return _frame([hist] + keep)


class FakeFetch:
    """fetch_fn(pair, ws, we) → o/h/l/c/volume frame。呼び出しを記録し、欠落外の bar も混ぜて返す。"""

    def __init__(self, provide_missing=True, stray=True):
        self.calls = []
        self.provide_missing = provide_missing
        self.stray = stray

    def __call__(self, pair, ws, we):
        self.calls.append((pair, ws, we))
        times = []
        t = ws - timedelta(seconds=BAR_SEC)           # 欠落外 (直前の既存 bar) を 1 本混ぜる
        if self.stray:
            times.append(t)
        if self.provide_missing:
            t = ws
            while t < we:
                times.append(t)
                t += timedelta(seconds=BAR_SEC)
        if not times:
            return pd.DataFrame(columns=["o", "h", "l", "c", "volume"])
        idx = pd.DatetimeIndex(times)
        base = np.linspace(149.0, 149.5, len(idx))
        return pd.DataFrame({"o": base, "h": base + 0.02, "l": base - 0.02, "c": base + 0.01,
                             "volume": np.full(len(idx), 7.0)}, index=idx)


@pytest.fixture
def dirs(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    return src, dst


def _write(src: Path, pair: str, df: pd.DataFrame):
    df.to_parquet(src / f"{pair}_15m.parquet", engine="pyarrow")


def test_defaults_match_export_tool_constants():
    assert gb.T0_ISO == T0_ISO
    assert gb.LOOKS[1]["cutoff"] == LOOKS[1]["cutoff"]
    assert gb.DEFAULT_SRC != gb.DEFAULT_DST


def test_plan_counts_only_window_gaps_and_in_window_extras(dirs):
    src, _ = dirs
    holes = [10, 11, 12, 50]                      # run 3 本 + 単発 1 本
    df = _src_with_holes(holes)
    plan = gb.plan_pair(df, T0, CUTOFF)
    assert plan["gap_bars"] == 4
    assert plan["gap_runs"] == 2
    assert plan["gap_max_run_bars"] == 3
    assert plan["gap_first"] == "2026-07-16T09:00:00Z"
    # 2014 年の閉場行はファイル全体の extra だが窓内 extra には数えない
    assert plan["extra_in_window"] == 0
    assert plan["duplicates"] == 0 and plan["monotonic"] is True


def test_fill_adds_only_missing_slots_and_keeps_existing_rows(dirs):
    src, dst = dirs
    holes = [10, 11, 12, 50]
    df = _src_with_holes(holes)
    _write(src, "EUR_JPY", df)
    fake = FakeFetch()
    out = io.StringIO()
    audit = gb.run(src, dst, T0, CUTOFF, pairs=("EUR_JPY",), fetch_fn=fake,
                   audit_out=dst / "audit.json", out=out)
    rec = audit["pairs"]["EUR_JPY"]
    assert rec["status"] == "filled"
    assert rec["filled_bars"] == 4 and rec["unfilled_bars"] == 0
    assert len(fake.calls) == 2                     # run 単位で 1 回ずつ
    back = pd.read_parquet(dst / "EUR_JPY_15m.parquet")
    assert len(back) == len(df) + 4
    bidx = back.index.tz_localize("UTC") if back.index.tz is None else back.index.tz_convert("UTC")
    sidx = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    # 既存行は値・dtype とも不改変
    src_norm = df.copy(); src_norm.index = sidx
    back_norm = back.copy(); back_norm.index = bidx
    pd.testing.assert_frame_equal(back_norm.loc[sidx], src_norm)
    # 追加されたのは欠落スロットだけ (fake が混ぜた欠落外 bar は捨てられている)
    added = sorted(set(bidx) - set(sidx))
    full = _grid(BASE, N_BARS)
    assert [t.to_pydatetime() for t in added] == [full[i] for i in holes]
    assert list(back.columns) == list(df.columns)
    # 補填後は凍結 export の coverage 検査で interior_gaps が消える (extras は履歴行、drop で通す)
    cov = check_ohlcv_coverage(str(dst), CUTOFF, max_lag_bars=10 ** 6, drop_extra=True,
                               pairs=("EUR_JPY",))
    assert cov["EUR_JPY"]["gap_bars"] == 0
    assert "interior_gaps" not in (cov["EUR_JPY"]["reason"] or "")
    # stdout / audit に価格値が出ない
    text = out.getvalue()
    assert not FLOAT_RE.search(text), text
    raw = (dst / "audit.json").read_text(encoding="utf-8")
    assert not FLOAT_RE.search(raw)
    assert json.loads(raw)["totals"] == {"gap_bars": 4, "filled_bars": 4, "unfilled_bars": 0}


def test_pair_without_gaps_is_byte_copied(dirs):
    src, dst = dirs
    df = _src_with_holes([])
    _write(src, "EUR_USD", df)
    fake = FakeFetch()
    audit = gb.run(src, dst, T0, CUTOFF, pairs=("EUR_USD",), fetch_fn=fake, out=io.StringIO())
    rec = audit["pairs"]["EUR_USD"]
    assert rec["status"] == "copied_unchanged"
    assert rec["src_sha256"] == rec["dst_sha256"]
    assert fake.calls == []


def test_dry_run_never_fetches_or_writes(dirs):
    src, dst = dirs
    _write(src, "EUR_JPY", _src_with_holes([10, 11]))
    fake = FakeFetch()
    audit = gb.run(src, dst, T0, CUTOFF, pairs=("EUR_JPY",), dry_run=True, fetch_fn=fake,
                   audit_out=dst / "audit.json", out=io.StringIO())
    assert audit["pairs"]["EUR_JPY"]["status"] == "planned"
    assert audit["pairs"]["EUR_JPY"]["gap_bars"] == 2
    assert fake.calls == []
    assert not dst.exists()


def test_unfilled_bars_are_reported_not_silently_accepted(dirs):
    src, dst = dirs
    _write(src, "GBP_JPY", _src_with_holes([20, 21, 22]))
    fake = FakeFetch(provide_missing=False)         # OANDA にも無い
    audit = gb.run(src, dst, T0, CUTOFF, pairs=("GBP_JPY",), fetch_fn=fake, out=io.StringIO())
    rec = audit["pairs"]["GBP_JPY"]
    assert rec["status"] == "filled_partial"
    assert rec["filled_bars"] == 0 and rec["unfilled_bars"] == 3
    assert rec["unfilled_first"] == "2026-07-16T11:30:00Z"
    back = pd.read_parquet(dst / "GBP_JPY_15m.parquet")
    assert len(back) == len(_src_with_holes([20, 21, 22]))


def test_src_index_defects_are_refused(dirs):
    src, dst = dirs
    df = _src_with_holes([5])
    dup = pd.concat([df, df.iloc[[3]]])             # 重複 timestamp
    _write(src, "AUD_USD", dup)
    fake = FakeFetch()
    audit = gb.run(src, dst, T0, CUTOFF, pairs=("AUD_USD",), fetch_fn=fake, out=io.StringIO())
    assert audit["pairs"]["AUD_USD"]["status"] == "refused_src_index"
    assert fake.calls == []
    assert not (dst / "AUD_USD_15m.parquet").exists()


def test_refusal_removes_stale_dst_and_main_exits_2(dirs, monkeypatch):
    """Codex P2 4191149514: 前回成功分の dst が残ると、今回の入力から作られていない複製が
    preflight を通って凍結される。missing_src / refused_src_index は古い dst を消し、main は exit 2。"""
    src, dst = dirs
    _write(src, "EUR_JPY", _src_with_holes([5]))
    _write(src, "GBP_JPY", _src_with_holes([]))
    gb.run(src, dst, T0, CUTOFF, pairs=("EUR_JPY", "GBP_JPY"), fetch_fn=FakeFetch(), out=io.StringIO())
    assert (dst / "EUR_JPY_15m.parquet").exists() and (dst / "GBP_JPY_15m.parquet").exists()
    # 2 回目: EUR_JPY の src が消え、GBP_JPY の src が壊れる
    (src / "EUR_JPY_15m.parquet").unlink()
    bad = _src_with_holes([])
    _write(src, "GBP_JPY", pd.concat([bad, bad.iloc[[3]]]))
    out = io.StringIO()
    audit = gb.run(src, dst, T0, CUTOFF, pairs=("EUR_JPY", "GBP_JPY"), fetch_fn=FakeFetch(), out=out)
    assert audit["pairs"]["EUR_JPY"]["status"] == "missing_src"
    assert audit["pairs"]["EUR_JPY"]["dst_removed"] is True
    assert audit["pairs"]["GBP_JPY"]["status"] == "refused_src_index"
    assert audit["pairs"]["GBP_JPY"]["dst_removed"] is True
    assert not (dst / "EUR_JPY_15m.parquet").exists()
    assert not (dst / "GBP_JPY_15m.parquet").exists()
    assert audit["ok"] is False and audit["failed_pairs"] == ["EUR_JPY", "GBP_JPY"]
    assert "FAILED pairs" in out.getvalue()
    # dry-run は消さない (有無だけ報告)
    _write(src, "EUR_JPY", _src_with_holes([]))
    gb.run(src, dst, T0, CUTOFF, pairs=("EUR_JPY",), fetch_fn=FakeFetch(), out=io.StringIO())
    (src / "EUR_JPY_15m.parquet").unlink()
    a2 = gb.run(src, dst, T0, CUTOFF, pairs=("EUR_JPY",), dry_run=True, out=io.StringIO())
    assert a2["pairs"]["EUR_JPY"]["dst_removed"] is True and (dst / "EUR_JPY_15m.parquet").exists()
    # main: 失敗 pair があれば exit 2 (dry-run でも)
    rc = gb.main(["--src", str(src), "--dst", str(dst), "--pairs", "EUR_JPY", "--dry-run"])
    assert rc == 2


def test_postponed_uses_slid_cutoff_and_separate_dst(tmp_path, monkeypatch):
    """Codex P2 4191149521: POSTPONE 時は cutoff が 4 週スライド (11-05) し、first look の複製を
    上書きしない別 dst / 別 audit 名で作る。"""
    from tools.e1_positioning_frozen_export import look_spec
    assert gb.default_dst(1) == gb.DEFAULT_DST
    assert gb.default_dst(1, postponed=True) != gb.DEFAULT_DST
    assert gb.default_dst(2) not in (gb.DEFAULT_DST, gb.default_dst(1, postponed=True))
    captured = {}

    def fake_run(src, dst, t0, cutoff, **kw):
        captured.update({"dst": dst, "cutoff": cutoff, "audit_out": kw.get("audit_out")})
        return {"ok": True, "failed_pairs": []}
    monkeypatch.setattr(gb, "run", fake_run)
    src = tmp_path / "src"; src.mkdir()
    assert gb.main(["--src", str(src), "--look", "1", "--postponed", "--dry-run"]) == 0
    assert captured["cutoff"] == parse_utc(look_spec(1, True)["cutoff"])
    assert captured["cutoff"] == CUTOFF + timedelta(weeks=4)
    assert captured["dst"] == gb.default_dst(1, postponed=True)
    assert "first-look-postponed" in captured["audit_out"].name
    assert gb.main(["--src", str(src), "--look", "1", "--dry-run"]) == 0
    assert captured["cutoff"] == CUTOFF and captured["dst"] == gb.DEFAULT_DST
    with pytest.raises(ValueError):
        gb.main(["--src", str(src), "--look", "2", "--postponed", "--dry-run"])


def test_main_refuses_same_src_and_dst(tmp_path, capsys):
    rc = gb.main(["--src", str(tmp_path), "--dst", str(tmp_path), "--dry-run"])
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().err


def test_window_slots_follow_market_calendar():
    # 窓の終端が last_complete と expected_last の小さい方 (末尾の遅れは lag、欠落に数えない)
    df = _src_with_holes([])
    plan = gb.plan_pair(df, T0, CUTOFF)
    assert plan["window_end"] == "2026-07-17T19:45:00Z"
    assert plan["window_slots"] == len(expected_market_slots(T0, datetime(2026, 7, 17, 19, 45, tzinfo=timezone.utc)))
    # expected_market_slots は t0 を含む 15m 境界 (06:30Z) から数える → 連続グリッドなら欠落 0
    assert plan["window_slots"] == N_BARS
    assert plan["gap_bars"] == 0
