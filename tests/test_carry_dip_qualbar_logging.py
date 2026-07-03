"""usdjpy_carry_dip_accumulator — qualifying-bar 発火期待値 logging (roadmap T7).

背景 (2026-07-02 zero-fire 診断):
    USDJPY_CARRY_DIP_LIVE_ENABLE=1 なのに 06-12 以降 live fill 0 件。
    原因は CEILING=159.5 静的壁が市場 (160-162円台) に取り残され、
    RSI dip cross 22 回が全て silent drop されていたこと。
    「RSI cross は起きたが後段 filter で落ちた」ことが production ログから
    観測不能だったため、qualifying-bar (トリガー成立バー) ごとに
    filter breakdown を 1 行 log する telemetry を追加する。

仕様:
    - RSI が RSI_BUY を下抜けた closed bar (= トリガーイベント) でのみ log。
    - 同一 closed bar への 60s polling 再入では log を重複させない。
    - log 行は "QUALBAR" マーカー + ceiling/blackout/cooldown の pass/fail +
      最終 emit 判定を含む (Render ログで grep 可能な単一行)。
    - トリガー無しバーでは log しない (スパム防止)。
"""
import logging

import pandas as pd
import pytest

from strategies.hourly.usdjpy_carry_dip_accumulator import UsdjpyCarryDipAccumulator
from strategies.context import SignalContext


def _make_ctx(last_closed_close: float, start: str = "2026-07-20T00:00:00Z"):
    """H1 df を構築: 上昇トレンド (RSI高) → 急落 1 本で RSI が 45 を下抜ける。

    live 経路 (backtest_mode=False) は closed bar = iloc[-2] なので、
    急落バーの後に進行中バー 1 本を足す。
    急落幅 1.8円 (avg gain 0.1 に対し Wilder RSI ≈ 42 まで低下)。
    """
    n_up = 30
    trend_end = last_closed_close + 1.8                       # 急落幅 1.8円
    closes = [trend_end - 0.1 * (n_up - 1 - i) for i in range(n_up)]  # RSI ≈ 100
    closes.append(last_closed_close)                          # 急落 closed bar
    closes.append(last_closed_close + 0.02)                   # 進行中バー
    idx = pd.date_range(start, periods=len(closes), freq="1h", tz="UTC")
    df = pd.DataFrame({"Close": closes}, index=idx)

    # precondition: closed bar (iloc[-2]) で RSI cross-below-45 が成立していること
    rsi = UsdjpyCarryDipAccumulator._wilder_rsi(df["Close"], 14)
    assert rsi.iloc[-3] >= 45.0, "test setup: prev bar RSI must be >= 45"
    assert rsi.iloc[-2] < 45.0, "test setup: closed bar RSI must cross below 45"

    return SignalContext(
        entry=float(df["Close"].iloc[-1]),
        df=df,
        symbol="USDJPY=X",
        backtest_mode=False,
    )


def _qualbar_records(caplog):
    return [r for r in caplog.records if "QUALBAR" in r.getMessage()]


class TestCarryDipQualbarLogging:

    def test_ceiling_block_logs_qualbar_with_breakdown(self, caplog):
        """RSI cross 成立 + close >= CEILING → emit しないが QUALBAR log は残る。"""
        strat = UsdjpyCarryDipAccumulator()
        ctx = _make_ctx(last_closed_close=161.20)  # >= 159.5 → ceiling block
        with caplog.at_level(logging.INFO):
            result = strat.evaluate(ctx)
        assert result is None
        recs = _qualbar_records(caplog)
        assert len(recs) == 1
        msg = recs[0].getMessage()
        assert "ceiling_pass=False" in msg
        assert "emit=False" in msg

    def test_qualbar_logged_once_per_closed_bar(self, caplog):
        """同一 closed bar への再 evaluate (60s polling) では log を重複させない。"""
        strat = UsdjpyCarryDipAccumulator()
        ctx = _make_ctx(last_closed_close=161.20)
        with caplog.at_level(logging.INFO):
            strat.evaluate(ctx)
            strat.evaluate(ctx)
            strat.evaluate(ctx)
        assert len(_qualbar_records(caplog)) == 1

    def test_qualifying_bar_emits_and_logs_emit_true(self, caplog):
        """全 filter PASS → Candidate 返却 + QUALBAR emit=True。"""
        strat = UsdjpyCarryDipAccumulator()
        ctx = _make_ctx(last_closed_close=158.80)  # < 159.5 → qualify
        with caplog.at_level(logging.INFO):
            result = strat.evaluate(ctx)
        assert result is not None
        assert result.signal == "BUY"
        recs = _qualbar_records(caplog)
        assert len(recs) == 1
        msg = recs[0].getMessage()
        assert "ceiling_pass=True" in msg
        assert "emit=True" in msg

    def test_no_qualbar_log_without_rsi_cross(self, caplog):
        """トリガー (RSI cross) 無しのバーでは log しない (スパム防止)。"""
        strat = UsdjpyCarryDipAccumulator()
        # 単調上昇のみ: RSI は高止まりで cross しない
        closes = [150.0 + 0.1 * i for i in range(32)]
        idx = pd.date_range("2026-07-20T00:00:00Z", periods=len(closes),
                            freq="1h", tz="UTC")
        df = pd.DataFrame({"Close": closes}, index=idx)
        ctx = SignalContext(entry=float(df["Close"].iloc[-1]), df=df,
                            symbol="USDJPY=X", backtest_mode=False)
        with caplog.at_level(logging.INFO):
            result = strat.evaluate(ctx)
        assert result is None
        assert _qualbar_records(caplog) == []
