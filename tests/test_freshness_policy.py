"""modules/freshness_policy.py の判定と、その **読み手が実際に配線されているか** の pin.

rule:R3 (2026-08-29).

本ファイルは 2 種類のテストを持つ:

1. **判定テスト** — level が閾値どおりに付くか、時計 (実時間 / 市場オープン
   時間) を系列ごとに正しく使い分けているか。
2. **配線 pin** — 判定を呼ぶ側が存在するか。本プロジェクトは「計装を書いた
   が読み手が居ない / 呼ばれていない」を 5 回踏んでいる (PR #168 hour_utc /
   PR #204 bar_time / PR #199 guard regex / C1 candidate 4ヶ月 write-only /
   PR #208 の counterfactual ⑥ で検知器の main 配線削除が初回素通り)。
   判定関数を書いても status payload に載らなければ、あるいは画面が読ま
   なければ、**全テスト green のまま無音**になる。だから「呼ばれているか」
   をテキストレベルで pin する。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules import freshness_policy as fp

ROOT = Path(__file__).resolve().parent.parent

# 2026-08-26 は水曜。週末閉場をまたがない基準時刻。
WED = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
# 2026-08-29 は土曜 = 閉場中。金 21:00 UTC 以降。
SAT = datetime(2026, 8, 29, 3, 30, tzinfo=timezone.utc)


def _status(**over):
    base = {
        "engine_tick_status": "ok",
        "engine_tick_age_sec": 18.0,
        "engine_tick_running_modes": 24,
        "engine_tick_stalest_mode": "daytrade_1h",
        "engine_tick_stalest_age_sec": 55.0,
        "last_candidate_row_status": "ok",
        "last_candidate_row_at": (WED - timedelta(minutes=5)).isoformat(),
        "last_trade_row_status": "ok",
        "last_trade_row_at": (WED - timedelta(hours=2)).isoformat(),
    }
    base.update(over)
    return base


def _fam(result, key):
    return next(f for f in result["families"] if f["key"] == key)


# ── 時計 ────────────────────────────────────────────────────────────────
def test_market_open_hours_excludes_weekend():
    mon = datetime(2026, 8, 24, tzinfo=timezone.utc)
    assert fp.market_open_hours(mon, mon + timedelta(days=7)) == pytest.approx(120.0)
    sat = datetime(2026, 8, 29, tzinfo=timezone.utc)
    assert fp.market_open_hours(sat, sat + timedelta(days=1)) == pytest.approx(0.0)
    tue = datetime(2026, 8, 25, tzinfo=timezone.utc)
    assert fp.market_open_hours(tue, tue + timedelta(days=1)) == pytest.approx(24.0)


# ── engine tick: 実時間。週末で緩めてはならない ──────────────────────────
def test_engine_ok_and_stale():
    assert _fam(fp.classify_freshness(_status(), now=WED), "engine_tick")["level"] == fp.LEVEL_OK
    stale = fp.classify_freshness(
        _status(engine_tick_age_sec=fp.ENGINE_TICK_STALL_MINUTES * 60), now=WED
    )
    assert _fam(stale, "engine_tick")["level"] == fp.LEVEL_STALE
    assert stale["worst_level"] == fp.LEVEL_STALE


def test_engine_deploy_ramp_is_not_stale():
    """PR #199 実測のデプロイ ramp 3.6 分は正常でなければならない."""
    r = fp.classify_freshness(_status(engine_tick_age_sec=3.6 * 60), now=WED)
    assert _fam(r, "engine_tick")["level"] == fp.LEVEL_OK


def test_engine_does_not_get_weekend_credit():
    """**週末でも tick は前進する。** 実時間で判定しないと本物の週末停止を
    毎週見逃す (freshness_policy docstring の中核契約)。"""
    r = fp.classify_freshness(
        _status(engine_tick_age_sec=30 * 60), now=SAT  # 閉場中に 30 分停止
    )
    assert _fam(r, "engine_tick")["level"] == fp.LEVEL_STALE


def test_engine_not_running_is_idle_not_stale():
    """全モード停止中は「止まっている」でなく「止められている」."""
    r = fp.classify_freshness(
        _status(engine_tick_status="not_running", engine_tick_age_sec=None), now=WED
    )
    assert _fam(r, "engine_tick")["level"] == fp.LEVEL_IDLE


def test_engine_never_ticked_without_age_is_stale():
    """モードは running なのに tick ゼロ + 経過秒不明 = 最悪ケース。
    版ずれと同じ袋 (unknown) に入れて沈黙させない."""
    r = fp.classify_freshness(
        _status(engine_tick_status="never_ticked", engine_tick_age_sec=None), now=WED
    )
    assert _fam(r, "engine_tick")["level"] == fp.LEVEL_STALE


def test_engine_missing_field_is_unknown_not_ok():
    r = fp.classify_freshness({"last_candidate_row_status": "no_rows"}, now=WED)
    assert _fam(r, "engine_tick")["level"] == fp.LEVEL_UNKNOWN


# ── 行系列: 市場オープン時間 ────────────────────────────────────────────
def test_candidate_stale_after_threshold_in_open_market():
    at = WED - timedelta(hours=fp.CANDIDATE_STAGNATION_HOURS + 1)
    r = fp.classify_freshness(
        _status(last_candidate_row_at=at.isoformat()), now=WED
    )
    assert _fam(r, "candidate_row")["level"] == fp.LEVEL_STALE


def test_weekend_old_rows_stay_ok():
    """土曜に金曜終値の行を見ても正常。実時間で数えると毎週末誤発火する。

    金 20:54 UTC (閉場 21:00 の 6 分前) の最終行を土 03:30 に見る状況 =
    2026-08-29 の本番実測そのもの。
    """
    fri = datetime(2026, 8, 28, 20, 54, tzinfo=timezone.utc)
    r = fp.classify_freshness(
        _status(
            last_candidate_row_at=fri.isoformat(),
            last_trade_row_at=fri.isoformat(),
        ),
        now=SAT,
    )
    cand = _fam(r, "candidate_row")
    assert cand["level"] == fp.LEVEL_OK
    # 実時間では 6.6h 経っているが、市場オープン換算では 0.1h
    assert cand["age_sec"] > 6 * 3600
    assert cand["market_open_hours"] < 0.5
    assert r["worst_level"] == fp.LEVEL_OK
    # 「なぜ古くて正常なのか」が画面に出ること (次に見る人の誤読を防ぐ)
    assert "閉場" in cand["detail"] or "市場オープン" in cand["detail"]


def test_row_error_and_no_rows_are_distinguished():
    """no_rows (初期状態) と error (本物の異常) を折り畳まない — PR #207 の設計罠."""
    err = fp.classify_freshness(
        _status(last_candidate_row_status="error", row_freshness_error="disk full"), now=WED
    )
    assert _fam(err, "candidate_row")["level"] == fp.LEVEL_UNKNOWN
    empty = fp.classify_freshness(_status(last_candidate_row_status="no_rows"), now=WED)
    assert _fam(empty, "candidate_row")["level"] == fp.LEVEL_IDLE


def test_unparseable_timestamp_is_unknown():
    r = fp.classify_freshness(_status(last_trade_row_at="not-a-date"), now=WED)
    assert _fam(r, "trade_row")["level"] == fp.LEVEL_UNKNOWN


def test_worst_level_prefers_stale_over_unknown():
    r = fp.classify_freshness(
        _status(
            engine_tick_age_sec=fp.ENGINE_TICK_STALL_MINUTES * 60,
            last_trade_row_at="not-a-date",
        ),
        now=WED,
    )
    assert r["worst_level"] == fp.LEVEL_STALE


def test_all_three_families_always_present():
    r = fp.classify_freshness({}, now=WED)
    assert [f["key"] for f in r["families"]] == ["engine_tick", "candidate_row", "trade_row"]


# ── SSOT pin: 検知器と画面が同じ定数を見ているか ─────────────────────────
def test_watcher_constants_are_the_shared_ones():
    """anomaly_watcher が閾値を再定義していないこと.

    counterfactual: watcher 側で ``ENGINE_TICK_STALL_MINUTES = 15`` と
    直書きに戻すと、freshness_policy 側の値を変えてもこのテストが落ちる。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "aw_ssot", ROOT / "scripts" / "anomaly_watcher.py"
    )
    aw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aw)

    assert aw.ENGINE_TICK_STALL_MINUTES is fp.ENGINE_TICK_STALL_MINUTES
    assert aw.CANDIDATE_STAGNATION_HOURS is fp.CANDIDATE_STAGNATION_HOURS
    assert aw.N_STAGNATION_HOURS is fp.N_STAGNATION_HOURS
    assert aw.FX_WEEKEND_CLOSE_HOURS is fp.FX_WEEKEND_CLOSE_HOURS
    # 週末除外も 1 実装であること (2 実装あると片方だけ直る)
    mon = datetime(2026, 8, 24, tzinfo=timezone.utc)
    assert aw._market_open_hours(mon, mon + timedelta(days=3)) == fp.market_open_hours(
        mon, mon + timedelta(days=3)
    )

    src = (ROOT / "scripts" / "anomaly_watcher.py").read_text()
    assert not re.search(r"^ENGINE_TICK_STALL_MINUTES\s*=\s*\d", src, re.M), (
        "watcher が閾値を直書きに戻している (SSOT 破れ)"
    )


# ── 配線 pin: 読み手が実在し、呼ばれているか ────────────────────────────
def test_status_payload_wires_classify_freshness():
    """demo_trader の status が freshness_ui を **実際に載せる** こと.

    判定関数を書いただけでは無音。PR #208 の counterfactual ⑥ (検知器の
    main 配線削除) が初回素通りした教訓の適用。
    """
    src = (ROOT / "modules" / "demo_trader.py").read_text()
    assert "classify_freshness" in src, "status payload が判定関数を呼んでいない"
    assert '"freshness_ui"' in src, "status payload に freshness_ui キーが無い"


def test_dashboard_reads_freshness_ui():
    """画面が freshness_ui を **描画する** こと。

    ここが無いと「API は出るが画面は blind」= 2026-08-21 の事故と同じ状態に
    戻る。本 PR の存在理由そのものなので pin する。
    """
    html = (ROOT / "templates" / "index.html").read_text()
    assert "freshness_ui" in html, "画面が freshness_ui を読んでいない"
    assert "renderFreshness(" in html, "renderFreshness が呼ばれていない"
    assert 'id="demo-freshness"' in html, "描画先の DOM ノードが無い"


def test_dashboard_does_not_hardcode_thresholds():
    """JS 側に閾値を書き写していないこと.

    書き写すと閾値変更時に画面だけ古い判定で色を塗り続け、しかも全テスト
    green のまま検査が無力化する (PR #199 で実際に踏んだ型)。
    """
    html = (ROOT / "templates" / "index.html").read_text()
    fn_start = html.index("function renderFreshness(")
    fn_body = html[fn_start : html.index("async function loadDemoStatus(")]
    for bad in ("15 * 60", "900", "* 3600", "STALL_MINUTES", "STAGNATION_HOURS"):
        assert bad not in fn_body, f"renderFreshness に閾値らしき値 {bad!r} がある"
