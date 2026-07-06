"""kalman_d7 — qualifying-bar 発火期待値 logging (roadmap T9)。

背景:
    2026-05-28 pre-reg は「24h 以内に発火するはず」という分母なし基準で、
    0-fire が「PO-UP transition 不成立 (市場条件)」か「後段 filter で落ちた」か
    「経路ブロック」かを区別できなかった。carry dip QUALBAR (T7) と同型の
    qualifying-bar telemetry を追加し、判定を分母付き (QUALBAR 数 vs 発火数) にする。

仕様:
    - PO-UP transition バー (ctx.regime_po=="UP" and regime_po_start_up) でのみ log
    - class 属性 dedup: Engine 再構築 (poll 毎) と 3 variant 間で同一バー 1 行
    - トリガー無しバーでは log しない (スパム防止)
"""
import pandas as pd
import pytest

from strategies.daytrade.kalman_d7_trend import (
    KalmanD7Base,
    KalmanD7PODNFlip,
)
from strategies.context import SignalContext


@pytest.fixture(autouse=True)
def _reset_state():
    KalmanD7Base._qualbar_logged.clear()
    yield
    KalmanD7Base._qualbar_logged.clear()


def _make_ctx(*, po_start: bool, rsi: float = 50.0, hour_utc: int = 8,
              bar: str = "2026-07-20T08:00:00Z"):
    """緩やかな上昇トレンド 260 本の M15 df (EMA25>EMA75>EMA200、DIST/GAP 小)。"""
    n = 260
    closes = [150.0 + 0.01 * i for i in range(n)]
    idx = pd.date_range(end=bar, periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "Close": closes,
        "High": [c + 0.03 for c in closes],
        "Low": [c - 0.03 for c in closes],
    }, index=idx)
    return SignalContext(
        entry=float(closes[-1]),
        df=df,
        symbol="USDJPY=X",
        tf="15m",
        rsi=rsi,
        hour_utc=hour_utc,
        regime_po="UP" if po_start else "RANGE",
        regime_po_start_up=po_start,
        bar_time=idx[-1],
    )


def _qualbar_lines(capsys):
    return [l for l in capsys.readouterr().out.splitlines()
            if "QUALBAR" in l and "[kalman_d7]" in l]


def test_qualifying_bar_logs_breakdown_once(capsys):
    ctx = _make_ctx(po_start=True)
    KalmanD7PODNFlip().evaluate(ctx)
    lines = _qualbar_lines(capsys)
    assert len(lines) == 1
    assert "dist_pass=" in lines[0] and "session_pass=" in lines[0]
    assert "emit=" in lines[0]


def test_non_qualifying_bar_is_silent(capsys):
    ctx = _make_ctx(po_start=False)
    KalmanD7PODNFlip().evaluate(ctx)
    assert _qualbar_lines(capsys) == []


def test_dedup_survives_engine_reconstruction_and_variants(capsys):
    """poll 毎の Engine 再構築 = 新 instance でも、class 属性 dedup で
    同一バーは 1 行に抑えられる (engine-reconstruction 教訓の検証)。"""
    ctx = _make_ctx(po_start=True)
    KalmanD7PODNFlip().evaluate(ctx)     # 1st poll
    KalmanD7PODNFlip().evaluate(ctx)     # 別 instance = engine 再構築を模擬
    from strategies.daytrade.kalman_d7_trend import KalmanD7EMA75Break
    KalmanD7EMA75Break().evaluate(ctx)   # 別 variant も共有 dedup
    assert len(_qualbar_lines(capsys)) == 1


def test_new_bar_logs_again(capsys):
    KalmanD7PODNFlip().evaluate(_make_ctx(po_start=True))
    KalmanD7PODNFlip().evaluate(
        _make_ctx(po_start=True, bar="2026-07-20T08:15:00Z"))
    assert len(_qualbar_lines(capsys)) == 2


def test_filter_fail_logged_with_emit_false(capsys):
    """RSI 過熱で filter に落ちるケース: QUALBAR は出るが emit=False、
    evaluate は None (0-fire の原因が log から判定可能になる)。"""
    ctx = _make_ctx(po_start=True, rsi=75.0)
    result = KalmanD7PODNFlip().evaluate(ctx)
    lines = _qualbar_lines(capsys)
    assert result is None
    assert len(lines) == 1
    assert "rsi_pass=False" in lines[0]
    assert "emit=False" in lines[0]
