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
