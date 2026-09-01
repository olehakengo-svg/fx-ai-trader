"""候補行の書込みギャップ readout — ``candidate_stagnation`` 閾値較正の契約固定.

2026-09-01 (rule:R3)。背景: 閾値 6h の較正は 2026-08-27 以来「1〜2 週の実運用
後に取り直す」として未解決だったが、``query_candidate_rows`` の ``LIMIT 2000``
が本番で **9.9 時間**しか遡れない (テーブルは 90 日 / 317,542 行を保持) ため、
待っても標本は増えない — 律速は経過時間ではなく読み経路の天井だった。

本 test が固定するのは主に **時計**である。ギャップを実時間で数えると毎週末
48h の巨大ギャップが立ち、裾が週末で埋まって較正が無意味になる。したがって
「週末だけのギャップは発火しない」「週末をまたいでも実停止ぶんだけが数えられる」
の 2 点を数値で pin する — ここが壊れると readout は静かに嘘をつく。
"""

import json
import sqlite3

import pytest

from modules.candidate_logger import (
    init_candidates_table,
    query_candidate_write_gaps,
)

# 2026-08-28 は金曜。FX 週末閉場は金 21:00 UTC → 日 21:00 UTC。
_A_WEEKEND_ONLY = ("2026-08-28 20:59:00", "2026-08-30 21:30:00")  # wall 48.517 / open 0.517
_B_WEEKEND_PLUS_STALL = ("2026-08-28 17:00:00", "2026-08-31 01:00:00")  # wall 56.0 / open 8.0
_C_DAILY_BLOCK = ("2026-08-31 22:00:00", "2026-09-01 00:00:00")  # wall 2.0 / open 2.0
_D_TINY = ("2026-08-31 10:00:00", "2026-08-31 10:05:00")  # wall 0.083 (floor 未満)


def _make_db(tmp_path, timestamps):
    db = str(tmp_path / "cand.db")
    assert init_candidates_table(db)
    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT INTO evaluated_candidates"
        " (bar_time, instrument, tf, strategy_name, signal, created_at)"
        " VALUES ('b','USD_JPY','15m','s','BUY', ?)",
        [(t,) for t in timestamps],
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def gap_db(tmp_path):
    """6 タイムスタンプ = 5 ギャップの合成 DB.

    昇順に並べたとき生じるギャップ (market_open 時間) は
    8.0 / 9.0 / 0.083 / 11.917 / 2.0 の 5 本。うち floor 30 分未満は
    0.083 の 1 本だけなので over_floor は 4 本、最大は 11.917 になる。
    "繋ぎ" のギャップも実在のギャップなので数える — 落とすと n_gaps_total と
    の突き合わせができなくなる。A (週末のみ) は順序が崩れるため別 DB。
    """
    ts = [
        _B_WEEKEND_PLUS_STALL[0], _B_WEEKEND_PLUS_STALL[1],
        _D_TINY[0], _D_TINY[1],
        _C_DAILY_BLOCK[0], _C_DAILY_BLOCK[1],
    ]
    return _make_db(tmp_path, sorted(ts))


def test_weekend_only_gap_does_not_fire(tmp_path):
    """週末だけのギャップは実時間 48.5h でも発火してはならない.

    これが最重要の pin。実時間で数える実装に差し替わると wall 48.517h >= 6 で
    発火し、**毎週末必ず誤発火する**検知器になる。
    """
    db = _make_db(tmp_path, list(_A_WEEKEND_ONLY))
    out = query_candidate_write_gaps(db, days=400, min_gap_minutes=30,
                                     threshold_hours=6.0)
    assert out["n_gaps_over_floor"] == 1
    g = out["top_gaps"][0]
    assert g["wall_hours"] == pytest.approx(48.517, abs=0.01)
    assert g["market_open_hours"] == pytest.approx(0.517, abs=0.01)
    assert g["would_fire"] is False
    assert out["would_fire"]["count"] == 0


def test_weekend_spanning_gap_counts_only_open_hours(tmp_path):
    """週末をまたぐ実停止は、閉場ぶんを引いた 8h だけが数えられる."""
    db = _make_db(tmp_path, list(_B_WEEKEND_PLUS_STALL))
    out = query_candidate_write_gaps(db, days=400, min_gap_minutes=30,
                                     threshold_hours=6.0)
    g = out["top_gaps"][0]
    assert g["wall_hours"] == pytest.approx(56.0, abs=0.01)
    assert g["market_open_hours"] == pytest.approx(8.0, abs=0.01)
    assert g["would_fire"] is True
    assert out["would_fire"]["count"] == 1
    # 同じギャップが閾値 24h では発火しない = 閾値が実際に効いている
    out24 = query_candidate_write_gaps(db, days=400, min_gap_minutes=30,
                                       threshold_hours=24.0)
    assert out24["would_fire"]["count"] == 0
    assert out24["top_gaps"][0]["would_fire"] is False


def test_daily_two_hour_block_is_below_threshold(tmp_path):
    """本番に実在する 22:00→00:00 UTC の決定論的 2h 空白は発火域に入らない."""
    db = _make_db(tmp_path, list(_C_DAILY_BLOCK))
    out = query_candidate_write_gaps(db, days=400, min_gap_minutes=30,
                                     threshold_hours=6.0)
    g = out["top_gaps"][0]
    assert g["market_open_hours"] == pytest.approx(2.0, abs=0.01)
    assert g["would_fire"] is False


def test_floor_excludes_small_gaps_but_not_totals(gap_db):
    """floor 未満は分位母集団から外れるが、総ギャップ数は縮まない.

    バースト内間隔 (本番 median 0.15 分) を分位に混ぜると停止判定と無関係な
    数字になる。一方 ``n_gaps_total`` を同時に縮めると「落とした量」が
    見えなくなるので、両方を別々に出す契約を固定する。
    """
    out = query_candidate_write_gaps(gap_db, days=400, min_gap_minutes=30)
    assert out["n_gaps_total"] == 5           # 6 タイムスタンプ → 5 ギャップ
    assert out["n_gaps_over_floor"] == 4      # 5 分ギャップだけが落ちる
    assert all(g["wall_hours"] * 60 >= 30 for g in out["top_gaps"])
    # 分位は over-floor 母集団のみ。全 5 本なら中央値は 2.0 に落ちるが、
    # over-floor 4 本の順序統計はここに pin した値になる。
    q = out["over_floor_market_open_hours"]
    assert q["max"] == pytest.approx(11.917, abs=0.01)
    assert [round(g["market_open_hours"], 3) for g in out["top_gaps"]] == [
        11.917, 9.0, 8.0, 2.0]


def test_threshold_defaults_to_policy_ssot(tmp_path, monkeypatch):
    """閾値の既定値は SSOT を読む — ここに 6 をリテラルで書いてはならない.

    counterfactual: SSOT の定数を 3h に差し替えたら既定の判定も 3h になる。
    リテラル 6 が焼き込まれていればこの test は落ちる (PR #209 で踏んだ
    「閾値を 2 箇所に書き、片方だけ更新される」型の予防)。
    """
    import modules.freshness_policy as fp

    db = _make_db(tmp_path, list(_C_DAILY_BLOCK))  # market_open 2.0h
    out6 = query_candidate_write_gaps(db, days=400, min_gap_minutes=30)
    assert out6["threshold_hours"] == float(fp.CANDIDATE_STAGNATION_HOURS)
    assert out6["would_fire"]["count"] == 0

    monkeypatch.setattr(fp, "CANDIDATE_STAGNATION_HOURS", 1)
    out1 = query_candidate_write_gaps(db, days=400, min_gap_minutes=30)
    assert out1["threshold_hours"] == 1.0
    assert out1["would_fire"]["count"] == 1


def test_empty_table_is_not_an_error(tmp_path):
    """行ゼロは「壊れている」ではない — 沈黙もしない (unknown を返さず 0 を返す)."""
    db = str(tmp_path / "empty.db")
    assert init_candidates_table(db)
    out = query_candidate_write_gaps(db, days=90)
    assert out["n_gaps_total"] == 0
    assert out["n_gaps_over_floor"] == 0
    assert out["over_floor_market_open_hours"]["max"] is None
    assert out["would_fire"]["count"] == 0
    assert out["coverage"]["n_write_timestamps"] == 0


def test_gaps_view_is_reachable_from_the_endpoint(flask_client):
    """readout は route から到達できて初めて読み手になる.

    counterfactual pin: view=gaps の分岐を消すと summary にフォールバックし、
    ``body["view"] == "gaps"`` が落ちる (「検知器を書いても呼ばれなければ
    全テスト green のまま無音」= PR #208 の 5 例目を繰り返さないため)。
    """
    body = json.loads(flask_client.get(
        "/api/demo/evaluated-candidates?view=gaps&gap_days=30"
        "&min_gap_minutes=45&threshold_hours=9&limit=5").data)
    assert body["view"] == "gaps"
    g = body["gaps"]
    assert g["window_days"] == 30
    assert g["min_gap_minutes"] == 45.0
    assert g["threshold_hours"] == 9.0
    assert set(g) >= {"coverage", "n_gaps_total", "n_gaps_over_floor",
                      "over_floor_market_open_hours", "would_fire", "top_gaps"}
    assert len(g["top_gaps"]) <= 5


def test_gaps_view_bad_params_fall_back(flask_client):
    body = json.loads(flask_client.get(
        "/api/demo/evaluated-candidates?view=gaps"
        "&gap_days=xx&min_gap_minutes=yy&threshold_hours=zz").data)
    g = body["gaps"]
    assert g["window_days"] == 90
    assert g["min_gap_minutes"] == 30.0
    import modules.freshness_policy as fp
    assert g["threshold_hours"] == float(fp.CANDIDATE_STAGNATION_HOURS)


# ── 較正が依存している「構造的ギャップ」の前提を pin する ────────────────────
#
# 上の分布 readout は数字を出すだけで、その数字が**なぜその形なのか**は
# コード側の 2 つの事実に依存している。ここが変わると較正の根拠が黙って
# 陳腐化するので、構文ではなく**性質**を pin する (PR #209 教訓)。

def test_late_utc_hours_are_layer0_prohibited():
    """22:00-23:59 UTC は Layer-0 で取引禁止 = 候補行が書かれない前提.

    観測された「ちょうど 120.0 分」の日次空白の実体。この性質が消えたら
    日次 2h ブロックという較正の前提が崩れる。
    """
    from datetime import datetime, timezone

    from app import is_trade_prohibited

    for hour in (22, 23):
        r = is_trade_prohibited(
            bar_time=datetime(2026, 9, 1, hour, 30, tzinfo=timezone.utc))
        assert r["prohibited"] is True, hour
        assert r["check"] == "session"
        # tokyo_mode は hour<7 のときだけ。ここで立つと早期 return が
        # 回避され前提が崩れる
        assert not r.get("tokyo_mode", False), hour

    # 00:00 では解除される (東京セッションで稼働) = 空白が 2h で終わる根拠
    r0 = is_trade_prohibited(
        bar_time=datetime(2026, 9, 1, 0, 30, tzinfo=timezone.utc))
    assert r0["prohibited"] is False


def test_weekly_reopen_gap_is_three_market_open_hours():
    """週次の再開ギャップ = 市場オープン換算 3.00h — 日次 2h より大きい.

    3 つの境界が重なって決まる:
      市場オープン計上の再開  日 21:00 UTC  (freshness_policy)
      エンジンの再開          日 22:00 UTC  (_is_fx_market_closed)
      Layer-0 解除            月 00:00 UTC  (hour_utc >= 22)

    したがって閾値 6h の余裕は「日次 max 2h の 3 倍」ではなく **約 2 倍**。
    ここが崩れたら較正メモの結論も書き換える必要がある。
    """
    from datetime import datetime, timezone

    from modules.freshness_policy import (
        CANDIDATE_STAGNATION_HOURS,
        market_open_hours,
    )

    last_fri = datetime(2026, 8, 28, 21, 59, tzinfo=timezone.utc)
    first_mon = datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc)
    weekly = market_open_hours(last_fri, first_mon)
    assert weekly == pytest.approx(3.0, abs=0.05)
    # 実時間では 50h — 実時間で判定していたら毎週誤発火する
    assert (first_mon - last_fri).total_seconds() / 3600 == pytest.approx(50.0, abs=0.05)

    daily = market_open_hours(
        datetime(2026, 8, 31, 21, 59, tzinfo=timezone.utc),
        datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))
    assert daily == pytest.approx(2.0, abs=0.05)
    assert weekly > daily  # 構造的な最大は週次であって日次ではない
    # 閾値はこの週次ギャップより大きくなければ毎週誤発火する
    assert CANDIDATE_STAGNATION_HOURS > weekly
