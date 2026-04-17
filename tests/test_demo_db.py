"""Tests for Demo Trading DB and Learning Engine."""
import os
import tempfile
import pytest

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    os.unlink(path)


class TestDemoDB:
    def test_open_trade(self, db):
        tid = db.open_trade("BUY", 150.500, 150.200, 151.000,
                            "dual_sr_bounce", 65)
        assert tid is not None
        assert len(tid) == 12

    def test_open_and_close_trade_win(self, db):
        tid = db.open_trade("BUY", 150.500, 150.200, 151.000,
                            "dual_sr_bounce", 65)
        result = db.close_trade(tid, 151.000, "TP_HIT")
        assert result["outcome"] == "WIN"
        assert result["pnl_pips"] == 50.0  # (151.0 - 150.5) * 100
        assert result["close_reason"] == "TP_HIT"

    def test_open_and_close_trade_loss(self, db):
        tid = db.open_trade("BUY", 150.500, 150.200, 151.000,
                            "ema_cross", 60)
        result = db.close_trade(tid, 150.200, "SL_HIT")
        assert result["outcome"] == "LOSS"
        assert result["pnl_pips"] == -30.0

    def test_sell_trade_pnl(self, db):
        tid = db.open_trade("SELL", 150.500, 150.800, 150.000,
                            "dual_sr_bounce", 70)
        result = db.close_trade(tid, 150.000, "TP_HIT")
        assert result["outcome"] == "WIN"
        assert result["pnl_pips"] == 50.0

    def test_close_nonexistent_trade(self, db):
        result = db.close_trade("nonexistent", 150.0)
        assert "error" in result

    def test_get_open_trades(self, db):
        db.open_trade("BUY", 150.0, 149.5, 150.5, "ema_cross", 60)
        opens = db.get_open_trades()
        assert len(opens) == 1
        assert opens[0]["direction"] == "BUY"

    def test_get_closed_trades(self, db):
        tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "ema_cross", 60)
        db.close_trade(tid, 150.5, "TP_HIT")
        closed = db.get_closed_trades()
        assert len(closed) == 1
        assert closed[0]["outcome"] == "WIN"

    def test_stats(self, db):
        # 3 wins, 2 losses
        for i in range(3):
            tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "sr_bounce", 60)
            db.close_trade(tid, 150.5, "TP_HIT")
        for i in range(2):
            tid = db.open_trade("SELL", 150.0, 150.5, 149.5, "ema_cross", 55)
            db.close_trade(tid, 150.5, "SL_HIT")
        stats = db.get_stats()
        assert stats["total"] == 5
        assert stats["wins"] == 3
        assert stats["win_rate"] == 60.0
        assert "sr_bounce" in stats["by_type"]
        assert "ema_cross" in stats["by_type"]

    def test_learning_data(self, db):
        # Need 10+ trades
        for i in range(12):
            tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "sr_bounce", 60 + i)
            db.close_trade(tid, 150.3 if i % 3 == 0 else 149.5,
                           "TP_HIT" if i % 3 == 0 else "SL_HIT")
        data = db.get_trades_for_learning()
        assert data["ready"] is True
        assert data["sample"] == 12
        assert "by_type" in data
        assert "by_conf" in data

    def test_stats_excludes_xau_by_default(self, db):
        """v9.1: CLAUDE.md memory 'XAU除外' — default exclude_xau=True."""
        # 2 FX wins
        for _ in range(2):
            tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "ema_cross", 60,
                                instrument="USD_JPY")
            db.close_trade(tid, 150.5, "TP_HIT")
        # 1 XAU trade (huge loss in XAU "pips" — the whole reason we exclude)
        tid = db.open_trade("BUY", 2500.0, 2400.0, 2600.0, "gold_trend_momentum",
                            60, instrument="XAU_USD")
        db.close_trade(tid, 2400.0, "SL_HIT")

        # Default: XAU excluded
        s = db.get_stats()
        assert s["total"] == 2, "XAU should be excluded by default"
        assert s["wins"] == 2
        assert s["win_rate"] == 100.0
        assert "gold_trend_momentum" not in s["by_type"]

        # Explicit include
        s2 = db.get_stats(exclude_xau=False)
        assert s2["total"] == 3
        assert "gold_trend_momentum" in s2["by_type"]

    def test_stats_instrument_filter(self, db):
        """v9.1: instrument param scopes stats to a specific pair."""
        # 3 USD_JPY (2 wins 1 loss), 2 EUR_USD (both wins)
        for _ in range(2):
            tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "ema_cross", 60,
                                instrument="USD_JPY")
            db.close_trade(tid, 150.5, "TP_HIT")
        tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "ema_cross", 60,
                            instrument="USD_JPY")
        db.close_trade(tid, 149.5, "SL_HIT")
        for _ in range(2):
            tid = db.open_trade("BUY", 1.10, 1.09, 1.11, "fib_reversal", 60,
                                instrument="EUR_USD")
            db.close_trade(tid, 1.11, "TP_HIT")

        sj = db.get_stats(instrument="USD_JPY")
        assert sj["total"] == 3
        assert sj["wins"] == 2

        se = db.get_stats(instrument="EUR_USD")
        assert se["total"] == 2
        assert se["wins"] == 2

        # Comma-separated
        sboth = db.get_stats(instrument="USD_JPY,EUR_USD")
        assert sboth["total"] == 5

        # Unknown pair → zeros without crash
        sx = db.get_stats(instrument="XXX_YYY")
        assert sx["total"] == 0
        assert sx["decided_win_rate"] == 0

    def test_stats_decided_win_rate_excludes_be(self, db):
        """v9.1: decided_win_rate = wins / (wins+losses), BE が分母から除外される。"""
        # 2 wins, 1 loss, 1 BE
        for _ in range(2):
            tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "sr_bounce", 60)
            db.close_trade(tid, 150.5, "TP_HIT")
        tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "sr_bounce", 60)
        db.close_trade(tid, 149.5, "SL_HIT")
        tid = db.open_trade("BUY", 150.0, 149.5, 150.5, "sr_bounce", 60)
        db.close_trade(tid, 150.0, "MAX_HOLD")  # BE

        s = db.get_stats()
        assert s["total"] == 4
        assert s["wins"] == 2
        assert s["losses"] == 1
        assert s["breakevens"] == 1
        assert s["win_rate"] == 50.0  # 2/4
        # decided = 2/(2+1) = 66.7%
        assert s["decided_win_rate"] == 66.7

    def test_stats_by_type_pnl_rounded(self, db):
        """v9.1: by_type[strategy]['pnl'] must not leak float precision artifacts."""
        # Two small wins that famously trigger -17.9999... style sums
        for px in [1.00018, 1.00018, 1.00018]:
            tid = db.open_trade("BUY", 1.0, 0.999, 1.001, "fib_reversal", 60,
                                instrument="EUR_USD")
            db.close_trade(tid, px, "TP_HIT")
        s = db.get_stats()
        pnl = s["by_type"]["fib_reversal"]["pnl"]
        # Must be rounded to <=1 decimal place (not 18.00000000003 etc.)
        assert abs(pnl - round(pnl, 1)) < 1e-9

    def test_save_adjustment(self, db):
        db.save_adjustment("confidence_threshold", 55, 60,
                           "WR too low", 30.0, -0.5, 20)
        adjs = db.get_adjustments()
        assert len(adjs) == 1
        assert adjs[0]["parameter"] == "confidence_threshold"


class TestLearningEngine:
    def test_insufficient_data(self, db):
        engine = LearningEngine(db)
        result = engine.evaluate({"confidence_threshold": 55})
        assert len(result["adjustments"]) == 0
        assert "不足" in result["insights"][0]

    def test_with_enough_data(self, db):
        engine = LearningEngine(db)
        # Create 15 trades (all losses → should raise confidence)
        for i in range(15):
            tid = db.open_trade("BUY", 150.0, 149.5, 151.0,
                                "ema_cross", 55, regime='{"regime":"TREND"}')
            db.close_trade(tid, 149.5, "SL_HIT")
        result = engine.evaluate({"confidence_threshold": 55})
        # Should suggest raising confidence threshold
        conf_adj = [a for a in result["adjustments"]
                    if a["param"] == "confidence_threshold"]
        assert len(conf_adj) > 0
        assert conf_adj[0]["new"] > 55
