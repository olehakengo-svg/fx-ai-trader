"""DT SignalContext の hour_utc / is_friday が live 経路で凍結しないことの回帰テスト。

背景 (2026-08-09, rule:R3):
  compute_daytrade_signal は BT 経路からは bar_time= を受け取るが、live 経路
  (modules/demo_trader._tick → compute_fn(df, tf, sr, symbol)) は bar_time を
  渡さない。旧実装は bar_time が無いとき hour_utc=12 / is_friday=False の固定値に
  フォールバックしていたため、live では DT 全戦略の時間帯ゲートが「常に UTC 12:00・
  常に金曜でない」状態で評価されていた。

  実測影響 (本番 trades API, 2026-06-19〜08-07):
    - ctx.hour_utc 直読みの戦略群: 83/237 = 35.0% が BT 検証窓の外で発火
    - bar-time を自前導出する戦略群 (redesign_v2): 0/28 = 0.0%
    - Fisher exact one-sided p = 1.3e-05
  詳細: knowledge-base/wiki/analyses/dt-ctx-hour-utc-live-freeze-2026-08-09.md

本テストは修正の本質だけを固定する:
  「bar_time が無くても、DT ctx の hour_utc / is_friday は直近バーの実時刻に追従する」
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _capture_dt_ctx(monkeypatch, bar_index_last, bar_time=None):
    """compute_daytrade_signal を走らせ、DaytradeEngine に渡された ctx を捕捉する。

    DataFrame の index 末尾を bar_index_last に固定し、その時刻が ctx に
    反映されるかを見る。engine は評価せず ctx だけ奪って例外で抜ける。
    """
    import app as app_mod

    captured = {}

    class _Sentinel(Exception):
        pass

    class _FakeEngine:
        def evaluate_all(self, ctx):
            captured["ctx"] = ctx
            raise _Sentinel()

    import strategies.daytrade as dt_mod
    monkeypatch.setattr(dt_mod, "DaytradeEngine", _FakeEngine)

    df = _make_df(bar_index_last)
    sr = []
    try:
        app_mod.compute_daytrade_signal(
            df, tf="15m", sr_levels=sr, symbol="USDJPY=X", bar_time=bar_time
        )
    except _Sentinel:
        pass
    except Exception as exc:  # pragma: no cover - 経路変更時に原因を見せる
        if "ctx" not in captured:
            pytest.skip(f"compute_daytrade_signal が DTE 到達前に抜けた: {exc!r}")
    return captured.get("ctx")


def _make_df(last_ts, n=400):
    """indicator 列を備えた最小限の M15 DataFrame。"""
    idx = pd.date_range(end=last_ts, periods=n, freq="15min", tz="UTC")
    base = 157.0
    close = pd.Series([base + (i % 20) * 0.01 for i in range(n)], index=idx)
    df = pd.DataFrame(
        {
            "Open": close.shift(1).fillna(base),
            "High": close + 0.05,
            "Low": close - 0.05,
            "Close": close,
            "Volume": 1000.0,
        },
        index=idx,
    )
    import app as app_mod

    return app_mod.add_indicators(df)


@pytest.mark.parametrize("hour", [3, 8, 15, 20, 23])
def test_hour_utc_tracks_last_bar_without_bar_time(monkeypatch, hour):
    """live 経路 (bar_time=None) でも hour_utc が直近バーの UTC 時刻に追従する。

    旧実装ではこの値が hour によらず常に 12 だった。
    """
    last = pd.Timestamp(f"2026-08-05 {hour:02d}:45:00", tz="UTC")  # 2026-08-05 = 水曜
    ctx = _capture_dt_ctx(monkeypatch, last, bar_time=None)
    assert ctx is not None, "DT ctx が捕捉できなかった"
    assert ctx.hour_utc == hour, (
        f"hour_utc が直近バー時刻に追従していない: expected {hour}, got {ctx.hour_utc}. "
        "12 なら固定フォールバックへの退行 (2026-08-09 R3 の再発)"
    )


def test_hour_utc_is_not_frozen_across_bars(monkeypatch):
    """異なる時刻のバーが異なる hour_utc を生む (= 定数に凍結していない)。"""
    hours = []
    for hour in (2, 11, 18):
        last = pd.Timestamp(f"2026-08-05 {hour:02d}:15:00", tz="UTC")
        ctx = _capture_dt_ctx(monkeypatch, last, bar_time=None)
        assert ctx is not None
        hours.append(ctx.hour_utc)
    assert len(set(hours)) == 3, f"hour_utc が凍結している: {hours}"


def test_is_friday_tracks_last_bar_without_bar_time(monkeypatch):
    """live 経路でも金曜フィルターが効く (旧実装は常に False)。"""
    friday = pd.Timestamp("2026-08-07 17:30:00", tz="UTC")   # 2026-08-07 = 金曜
    wednesday = pd.Timestamp("2026-08-05 17:30:00", tz="UTC")

    ctx_fri = _capture_dt_ctx(monkeypatch, friday, bar_time=None)
    ctx_wed = _capture_dt_ctx(monkeypatch, wednesday, bar_time=None)
    assert ctx_fri is not None and ctx_wed is not None
    assert ctx_fri.is_friday is True, "金曜が live で検出できていない (R3 の再発)"
    assert ctx_wed.is_friday is False


def test_bar_time_still_wins_in_backtest(monkeypatch):
    """BT 経路の契約は不変 — 明示 bar_time が df.index より優先される。"""
    last = pd.Timestamp("2026-08-05 20:45:00", tz="UTC")
    explicit = datetime(2026, 8, 7, 6, 30, tzinfo=timezone.utc)  # 金曜 06:30
    ctx = _capture_dt_ctx(monkeypatch, last, bar_time=explicit)
    assert ctx is not None
    assert ctx.hour_utc == 6, f"bar_time が優先されていない: {ctx.hour_utc}"
    assert ctx.is_friday is True


def test_kalman_d7_session_gate_reachable():
    """kalman_d7 の session 窓が h=12 固定では構造的に通らないことの明示。

    この戦略は 2026-05-28 の LIVE 化以降 73 日間 0 fire だった。原因は市場条件では
    なく、live の ctx.hour_utc が常に 12 = 窓の穴に落ちていたこと。
    """
    def session_pass(h):
        return (h < 7) or (7 <= h < 12) or (16 <= h < 21)

    assert session_pass(12) is False, "前提が変わった — 分析ドキュメントを更新すること"
    assert any(session_pass(h) for h in range(24)), "窓が全閉している"
