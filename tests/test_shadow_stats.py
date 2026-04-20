"""Tests for get_shadow_trades_for_evaluation (v9.x Sentinel N 測定).

lesson-sentinel-n-measurement-bug:
- Sentinel (is_shadow=1) トレードの N/WR/EV を get_trades_for_learning と独立に集計.
- aggregate Kelly を汚さない.
- lesson-tool-verification-gap: 正例 + 負例 + 空DB の 3 種で「正しい出力」を検証する.
"""
import os
import tempfile
import pytest

from modules.demo_db import DemoDB


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    os.unlink(path)


def _open_close(db: DemoDB, entry_type: str, instrument: str,
                outcome_win: bool, is_shadow: bool,
                direction: str = "BUY") -> str:
    """ヘルパ: 所定条件で 1 トレードを open → close する."""
    if direction == "BUY":
        entry, sl, tp = 150.0, 149.5, 150.5
        exit_price = tp if outcome_win else sl
    else:
        entry, sl, tp = 150.0, 150.5, 149.5
        exit_price = tp if outcome_win else sl
    tid = db.open_trade(direction, entry, sl, tp, entry_type, 60,
                        instrument=instrument, is_shadow=is_shadow)
    db.close_trade(tid, exit_price, "TP_HIT" if outcome_win else "SL_HIT")
    return tid


class TestShadowStatsPositive:
    """正例: Shadow トレードが正しく集計される."""

    def test_shadow_only_counts(self, db):
        # Shadow 3 件 (bb_squeeze_breakout, USD_JPY, 2勝1敗)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", False, True)

        result = db.get_shadow_trades_for_evaluation()
        assert result["ready"] is True
        assert result["sample"] == 3
        assert "bb_squeeze_breakout" in result["by_type"]
        t = result["by_type"]["bb_squeeze_breakout"]
        assert t["n"] == 3
        assert t["wr"] == pytest.approx(66.7, abs=0.1)

    def test_by_type_pair_split(self, db):
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "EUR_USD", False, True)
        result = db.get_shadow_trades_for_evaluation()
        assert "bb_squeeze_breakout|USD_JPY" in result["by_type_pair"]
        assert "bb_squeeze_breakout|EUR_USD" in result["by_type_pair"]
        assert result["by_type_pair"]["bb_squeeze_breakout|USD_JPY"]["n"] == 1
        assert result["by_type_pair"]["bb_squeeze_breakout|USD_JPY"]["wr"] == 100.0
        assert result["by_type_pair"]["bb_squeeze_breakout|EUR_USD"]["wr"] == 0.0

    def test_entry_type_filter(self, db):
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "dt_fib_reversal",     "USD_JPY", True, True)
        result = db.get_shadow_trades_for_evaluation(entry_type="bb_squeeze_breakout")
        assert result["sample"] == 1
        assert list(result["by_type"].keys()) == ["bb_squeeze_breakout"]

    def test_instrument_filter(self, db):
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "EUR_USD", True, True)
        result = db.get_shadow_trades_for_evaluation(instrument="USD_JPY")
        assert result["sample"] == 1
        assert "USD_JPY" in result["by_instrument"]
        assert "EUR_USD" not in result["by_instrument"]


class TestShadowStatsNegative:
    """負例: Live (is_shadow=0) は除外される / XAU は除外される / フィルタ外も除外."""

    def test_live_trades_excluded(self, db):
        # Live 5 件, Shadow 2 件 → Shadow のみ集計
        for _ in range(5):
            _open_close(db, "ema_cross", "USD_JPY", True, False)  # live
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", False, True)

        result = db.get_shadow_trades_for_evaluation()
        assert result["sample"] == 2
        assert "ema_cross" not in result["by_type"]
        assert "bb_squeeze_breakout" in result["by_type"]

    def test_xau_excluded_by_default(self, db):
        # XAU Shadow 1 件 + FX Shadow 1 件
        _open_close(db, "gold_trend_momentum", "XAU_USD", True, True)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        result = db.get_shadow_trades_for_evaluation()
        assert result["sample"] == 1
        assert "gold_trend_momentum" not in result["by_type"]
        # Opt-in で XAU を含められること
        result_with_xau = db.get_shadow_trades_for_evaluation(exclude_xau=False)
        assert result_with_xau["sample"] == 2
        assert "gold_trend_momentum" in result_with_xau["by_type"]

    def test_does_not_pollute_learning(self, db):
        # Shadow 3 件 を入れても get_trades_for_learning は shadow 除外を維持する.
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", False, True)
        # Live は 1 件のみ → 学習は min_trades=10 で ready=False
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, False)

        learning = db.get_trades_for_learning(min_trades=10)
        assert learning["ready"] is False
        # sample=1 (live のみ). Shadow 3 件は混入していない.
        assert learning["sample"] == 1

        shadow = db.get_shadow_trades_for_evaluation()
        assert shadow["sample"] == 3


class TestShadowStatsEmpty:
    """空 DB・min_trades 未達・フィルタで 0 件のケース."""

    def test_empty_db(self, db):
        result = db.get_shadow_trades_for_evaluation()
        assert result["ready"] is False
        assert result["sample"] == 0
        assert result["by_type"] == {}
        assert result["by_type_pair"] == {}
        assert result["overall_wr"] == 0.0
        assert result["overall_ev"] == 0.0

    def test_min_trades_not_met(self, db):
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        result = db.get_shadow_trades_for_evaluation(min_trades=5)
        assert result["ready"] is False
        assert result["sample"] == 1
        assert result["min_required"] == 5

    def test_filter_matches_nothing(self, db):
        _open_close(db, "bb_squeeze_breakout", "USD_JPY", True, True)
        result = db.get_shadow_trades_for_evaluation(entry_type="does_not_exist")
        assert result["ready"] is False
        assert result["sample"] == 0
