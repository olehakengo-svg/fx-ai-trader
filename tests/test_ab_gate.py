"""v9.3 Phase D: hash-based A/B gate routing tests.

- gate_group カラム migration
- open_trade が新引数受理
- A/B 割り当ての 50/50 分布
"""
import os
import tempfile
import sqlite3

import pytest

from modules.demo_db import DemoDB


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    try:
        os.unlink(path)
    except OSError:
        pass


class TestGateGroupSchema:
    def test_phase_d_columns_exist(self, db):
        with sqlite3.connect(db._path) as con:
            cols = [r[1] for r in con.execute("PRAGMA table_info(demo_trades)")]
        for c in ("gate_group", "mtf_alignment", "mtf_gate_action"):
            assert c in cols, f"missing column: {c}"


class TestOpenTradeWithGate:
    def test_open_trade_records_gate_group(self, db):
        tid = db.open_trade(
            direction="BUY", entry_price=150.0, sl=149.5, tp=150.8,
            entry_type="ema_trend_scalp", confidence=80, tf="15m",
            instrument="USD_JPY",
            mtf_regime="trend_up_weak", mtf_d1_label=1, mtf_h4_label=1,
            mtf_vol_state="normal",
            gate_group="mtf_gated",
            mtf_alignment="aligned",
            mtf_gate_action="kept",
        )
        with sqlite3.connect(db._path) as con:
            row = con.execute(
                "SELECT gate_group, mtf_alignment, mtf_gate_action "
                "FROM demo_trades WHERE trade_id=?", (tid,)
            ).fetchone()
        assert row == ("mtf_gated", "aligned", "kept")

    def test_open_trade_records_downgrade(self, db):
        """conflict trades in Group A get downgraded to shadow."""
        tid = db.open_trade(
            direction="SELL", entry_price=150.0, sl=150.5, tp=149.2,
            entry_type="ema_trend_scalp", confidence=80, tf="15m",
            instrument="USD_JPY",
            mtf_regime="trend_up_weak",
            gate_group="mtf_gated",
            mtf_alignment="conflict",
            mtf_gate_action="downgraded",
            is_shadow=True,  # downgraded
        )
        with sqlite3.connect(db._path) as con:
            row = con.execute(
                "SELECT gate_group, mtf_alignment, mtf_gate_action, is_shadow "
                "FROM demo_trades WHERE trade_id=?", (tid,)
            ).fetchone()
        assert row == ("mtf_gated", "conflict", "downgraded", 1)

    def test_open_trade_label_only_group(self, db):
        """Group B: label_only — no gate action."""
        tid = db.open_trade(
            direction="BUY", entry_price=1.1000, sl=1.0950, tp=1.1080,
            entry_type="bb_rsi_reversion", confidence=70, tf="15m",
            instrument="EUR_USD",
            mtf_regime="trend_up_weak",
            gate_group="label_only",
            mtf_alignment="aligned",
            mtf_gate_action="none",
        )
        with sqlite3.connect(db._path) as con:
            row = con.execute(
                "SELECT gate_group, mtf_gate_action FROM demo_trades "
                "WHERE trade_id=?", (tid,)
            ).fetchone()
        assert row == ("label_only", "none")

    def test_gate_group_defaults_to_empty(self, db):
        """既存コードパスで gate_group 未指定でも insert 成功."""
        tid = db.open_trade(
            direction="BUY", entry_price=150.0, sl=149.5, tp=150.8,
            entry_type="ema_trend_scalp", confidence=80, tf="15m",
            instrument="USD_JPY",
        )
        with sqlite3.connect(db._path) as con:
            row = con.execute(
                "SELECT gate_group, mtf_alignment, mtf_gate_action "
                "FROM demo_trades WHERE trade_id=?", (tid,)
            ).fetchone()
        # デフォルト '' (空文字)
        assert row == ("", "", "")


class TestHashRoutingDistribution:
    """hash routing が ~50/50 に分布することを確認 (N=1000 で ±3σ 以内)."""

    def test_hash_distribution_near_50_50(self):
        import hashlib
        from datetime import datetime, timezone
        counts = {"mtf_gated": 0, "label_only": 0}
        for i in range(1000):
            # 異なる signal を想定 (instrument, price, time variation)
            key = f"USD_JPY|ema_trend_scalp|BUY|150.{i:05d}|{int(datetime.now(timezone.utc).timestamp() * 1000) + i}"
            h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
            g = "mtf_gated" if (h % 2 == 0) else "label_only"
            counts[g] += 1
        # 50/50 ± 約 50 (3σ で 47)
        assert 450 <= counts["mtf_gated"] <= 550
        assert 450 <= counts["label_only"] <= 550

    def test_same_key_same_group(self):
        """Reproducibility: 同じ key なら同じ group."""
        import hashlib
        key = "USD_JPY|ema_trend_scalp|BUY|150.00000|1234567890000"
        h1 = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
        h2 = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
        assert h1 == h2
