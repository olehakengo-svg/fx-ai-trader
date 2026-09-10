"""P8 gate_block_daily — 永続 block 帰属のテスト (rule:R3, 2026-09-11).

estimand 宣言: monitoring/estimand_declarations.yml: gate_block_attribution
背景: [[hull-fire-rate-funnel-2026-08-24]] §8 — in-memory _block_counts は
再起動でゼロ、Render ログは ~2 週で失効するため、hull 残余 4.7x の帰属が
永続面に存在しなかった。

counterfactual pin:
  * test_restart_survival_counterfactual — 永続配線 (record_block) を no-op に
    すると再起動後の帰属が消えることを直接示す (= 配線を revert すると落ちる)。
  * test_tick_entry_block_closure_delegates — _tick_entry の _block closure が
    _record_entry_block へ委譲していること、order_bar_dedup 経路が
    _persist_gate_block を呼ぶことのソース pin。
挙動不変 pin:
  * in-memory カウンタキー (reason.split('(')[0] 正規化) と SENTINEL_BLOCK_DIAG
    条件が旧 closure と同一であること。
"""
from __future__ import annotations

import inspect
import threading
import types
from datetime import datetime, timedelta, timezone

from modules.block_event_logger import (
    init_block_table,
    query_block_counts,
    record_block,
)
from modules.demo_trader import DemoTrader


def _db_file(tmp_path):
    path = str(tmp_path / "blocks.db")
    assert init_block_table(path)
    return path


def _light_trader(db_path: str) -> DemoTrader:
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = types.SimpleNamespace(_path=db_path)
    trader._lock = threading.Lock()
    trader._logs = []
    trader._add_log = trader._logs.append
    return trader


# ── module unit ─────────────────────────────────────────────────────────


def test_record_and_query_roundtrip(tmp_path):
    path = _db_file(tmp_path)
    assert record_block(path, mode="daytrade_eur", entry_type="hull_donchian_fade",
                        instrument="EUR_USD", reason_key="spread_guard")
    assert record_block(path, mode="daytrade_eur", entry_type="hull_donchian_fade",
                        instrument="EUR_USD", reason_key="spread_guard")
    assert record_block(path, mode="daytrade_eur", entry_type="hull_donchian_fade",
                        instrument="EUR_USD", reason_key="same_price_")
    out = query_block_counts(path, days=7)
    assert out["total"] == 3
    assert out["counts"]["daytrade_eur:spread_guard"] == 2
    assert out["per_strategy_counts"]["hull_donchian_fade:spread_guard"] == 2
    assert out["per_cell_counts"]["hull_donchian_fade|EUR_USD:same_price_"] == 1


def test_strategy_filter_and_days_window(tmp_path):
    path = _db_file(tmp_path)
    old_ts = datetime.now(timezone.utc) - timedelta(days=10)
    assert record_block(path, mode="daytrade_eur", entry_type="hull_donchian_fade",
                        instrument="EUR_USD", reason_key="score_gate", ts=old_ts)
    assert record_block(path, mode="daytrade", entry_type="other_strategy",
                        instrument="USD_JPY", reason_key="hedge_block")
    recent = query_block_counts(path, days=7)
    assert "hull_donchian_fade:score_gate" not in recent["per_strategy_counts"]
    assert recent["total"] == 1
    wide = query_block_counts(path, days=30, strategy="hull_donchian_fade")
    assert wide["total"] == 1
    assert wide["per_strategy_counts"] == {"hull_donchian_fade:score_gate": 1}


def test_retention_trim_on_init(tmp_path):
    path = _db_file(tmp_path)
    ancient = datetime.now(timezone.utc) - timedelta(days=120)
    assert record_block(path, mode="daytrade", entry_type="x",
                        instrument="EUR_USD", reason_key="spread_wide", ts=ancient)
    assert query_block_counts(path, days=0)["total"] == 1
    assert init_block_table(path)  # idempotent + trims > RETENTION_DAYS
    assert query_block_counts(path, days=0)["total"] == 0


def test_record_block_is_best_effort(tmp_path):
    # table 不在でも raise しない (entry path を汚染しない契約)
    bare = str(tmp_path / "no_table.db")
    assert record_block(bare, mode="m", entry_type="e",
                        instrument="i", reason_key="r") is False


# ── DemoTrader 配線 ─────────────────────────────────────────────────────


def test_record_entry_block_persists_and_matches_inmemory(tmp_path):
    path = _db_file(tmp_path)
    trader = _light_trader(path)
    reason = "spread_guard(cost=1.6pip/profit=4.5pip=36%>20%)"
    trader._record_entry_block("daytrade_eur", "hull_donchian_fade",
                               "EUR_USD", reason)
    # in-memory キーは旧 closure と同一 (動的値は '(' 前で除去)
    assert trader._block_counts == {"daytrade_eur:spread_guard": 1}
    assert trader._block_counts_per_strategy == {
        "hull_donchian_fade:spread_guard": 1}
    # SENTINEL_BLOCK_DIAG は診断対象 (hull は _SILENT_DROP_DIAG_TYPES) のみ、
    # 生 reason 全文で出る (旧挙動と同一)
    assert any("[SENTINEL_BLOCK_DIAG] hull_donchian_fade blocked at: " + reason
               in msg for msg in trader._logs)
    # 永続面
    out = query_block_counts(path, days=7)
    assert out["per_cell_counts"] == {
        "hull_donchian_fade|EUR_USD:spread_guard": 1}


def test_record_entry_block_no_sentinel_log_for_plain_strategy(tmp_path):
    path = _db_file(tmp_path)
    trader = _light_trader(path)
    trader._record_entry_block("daytrade", "sr_fib_confluence", "USD_JPY",
                               "cooldown(30s/60s)")
    assert trader._block_counts_per_strategy == {"sr_fib_confluence:cooldown": 1}
    assert not any("SENTINEL_BLOCK_DIAG" in msg for msg in trader._logs)
    assert query_block_counts(path, days=7)["per_strategy_counts"] == {
        "sr_fib_confluence:cooldown": 1}


def test_restart_survival_counterfactual(tmp_path, monkeypatch):
    """永続配線が帰属の唯一の担い手であることの counterfactual.

    (a) 記録 → プロセス再起動 (新インスタンス) 後も query で帰属が読める。
    (b) 永続配線 (record_block) を殺すと、同じ block でも再起動後に何も残らない
        — 2026-09-11 以前の本番状態 (total=9 / per_strategy={}) の再現。
    """
    path = _db_file(tmp_path)
    trader_a = _light_trader(path)
    trader_a._record_entry_block("daytrade_eur", "hull_donchian_fade",
                                 "EUR_USD", "same_price_5pip")
    # (a) 再起動シミュレート: in-memory は空でも永続面は残る
    trader_b = _light_trader(path)
    assert not getattr(trader_b, "_block_counts", None)
    assert query_block_counts(path, days=7)["total"] == 1
    # (b) 配線を殺す → block しても永続面が増えない
    import modules.block_event_logger as bel
    monkeypatch.setattr(bel, "record_block",
                        lambda *a, **k: False)
    trader_b._record_entry_block("daytrade_eur", "hull_donchian_fade",
                                 "EUR_USD", "hedge_block(daytrade/EUR_USD:BUY)")
    assert trader_b._block_counts_per_strategy == {
        "hull_donchian_fade:hedge_block": 1}  # in-memory は増えるが…
    assert query_block_counts(path, days=7)["total"] == 1  # 永続面は増えない


def test_order_bar_dedup_block_persists(tmp_path):
    path = _db_file(tmp_path)
    trader = _light_trader(path)
    bar_ts = "2026-09-04T08:15:00+00:00"
    first = trader._maybe_reserve_order_bar_emit(
        "hull_donchian_fade", "EUR_USD", "BUY", bar_ts,
        tf="15m", mode="daytrade_eur", _path="primary")
    assert first is None  # 予約成功 (block ではない)
    second = trader._maybe_reserve_order_bar_emit(
        "hull_donchian_fade", "EUR_USD", "BUY", bar_ts,
        tf="15m", mode="daytrade_eur", _path="primary")
    assert second is not None  # dedup block
    out = query_block_counts(path, days=7)
    assert out["per_cell_counts"] == {
        "hull_donchian_fade|EUR_USD:order_bar_dedup": 1}
    # in-memory 側も旧挙動どおり両カウンタが増える
    assert trader._block_counts == {"daytrade_eur:order_bar_dedup": 1}
    assert trader._block_counts_per_strategy == {
        "hull_donchian_fade:order_bar_dedup": 1}


def test_persist_gate_block_swallow_missing_db():
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = types.SimpleNamespace()  # _path 無し → 静かに skip
    trader._persist_gate_block(mode="m", entry_type="e",
                               instrument="i", reason_key="r")


def test_tick_entry_block_closure_delegates():
    """配線ソース pin — revert すると落ちる."""
    tick_src = inspect.getsource(DemoTrader._tick_entry)
    assert "self._record_entry_block(mode, entry_type, instrument, reason)" in tick_src
    dedup_src = inspect.getsource(DemoTrader._maybe_reserve_order_bar_emit)
    assert "_persist_gate_block(" in dedup_src
    rec_src = inspect.getsource(DemoTrader._record_entry_block)
    assert "reason.split('(')[0]" in rec_src  # キー爆発ガードの継承 pin
    assert "_persist_gate_block(" in rec_src
