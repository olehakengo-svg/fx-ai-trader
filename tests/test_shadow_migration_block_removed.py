"""P1-3 (fable5 audit 2026-07-07, rule:R3): stale SHADOW_MIGRATION 削除の回帰。

削除された旧ブロックは、ハードコードされた FORCE_DEMOTED 集合 (stale で、現役の
edge cell `dt_bb_rsi_mr` / PAIR_PROMOTED `bb_squeeze_breakout` を含んでいた) に対し
起動毎に `is_shadow=0→1` を無条件 UPDATE していた (冪等マーカー・oanda 安全チェック
なし)。後継の `_backfill_force_demoted_leak_impl` は DemoTrader._FORCE_DEMOTED の
動的リストのみを対象とするため、これら現役セルは触られない。本テストは、再起動
(=_init_tables 再実行) 後も現役セルの live is_shadow=0 行が保持されることを固定する。

ref: knowledge-base/wiki/decisions/fable5-system-audit-2026-07-02.md P1-3
"""
import sqlite3

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def _insert(conn, trade_id, entry_type, *, is_shadow=0, oanda_trade_id="OANDA-X",
            entry_time="2026-06-01T00:00:00+00:00", instrument="USD_JPY"):
    conn.execute(
        """INSERT INTO demo_trades
           (trade_id, status, direction, entry_price, entry_time, exit_price,
            exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
            confidence, is_shadow, oanda_trade_id, instrument)
           VALUES (?, 'CLOSED', 'BUY', 150.0, ?, 149.99, ?, 149.5, 150.5,
                   -1.0, -0.1, 'LOSS', ?, 80, ?, ?, ?)""",
        (trade_id, entry_time, entry_time, entry_type,
         is_shadow, oanda_trade_id, instrument),
    )


def _shadow_map(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return {
            row["trade_id"]: row["is_shadow"]
            for row in conn.execute("SELECT trade_id, is_shadow FROM demo_trades")
        }
    finally:
        conn.close()


def test_active_cells_not_in_dynamic_force_demoted():
    """テストの前提: 現役セルが動的 FORCE_DEMOTED に含まれないこと。"""
    fd = set(DemoTrader._FORCE_DEMOTED)
    assert "dt_bb_rsi_mr" not in fd
    assert "bb_squeeze_breakout" not in fd


def test_restart_does_not_recontaminate_active_edge_cells(tmp_path):
    """再起動 (DemoDB 再構築) で現役セルの live 行が保持される。

    区別ポイントは「fill callback 喪失行」(audit=filled だが oanda_trade_id 欠落)。
    旧ブロックはこれを無条件 is_shadow=1 に固定し Kelly/WR 集計から消していた。
    後継の FLAG_DRIFT backfill は audit=filled を検知して UNSAFE 扱いで backfill を
    見送る (oanda_trade_id 修復待ち) ため、削除後は is_shadow=0 が保持される。
    """
    db_path = tmp_path / "shadow-migration-removed.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert(conn, "edge-oanda", "dt_bb_rsi_mr")             # E-cell, OANDA-filled
        _insert(conn, "promoted-oanda", "bb_squeeze_breakout")  # PAIR_PROMOTED
        # lost fill-callback: filled at OANDA but oanda_trade_id missing.
        _insert(conn, "edge-lost-callback", "dt_bb_rsi_mr", oanda_trade_id="")
        conn.execute(
            """INSERT INTO oanda_audit
               (timestamp, demo_trade_id, entry_type, bridge_status, oanda_trade_id)
               VALUES ('2026-06-01T00:00:10+00:00', 'edge-lost-callback',
                       'dt_bb_rsi_mr', 'filled', 'OANDA-LOST')"""
        )
        conn.commit()

    # simulate a process restart → _init_tables runs again
    DemoDB(str(db_path))
    rows = _shadow_map(str(db_path))

    # Pre-fix the stale hardcoded block would have flipped all three to shadow=1;
    # edge-lost-callback in particular was stuck (drift backfill can't restore a
    # row with no oanda_trade_id). Post-fix all stay live.
    assert rows["edge-oanda"] == 0
    assert rows["promoted-oanda"] == 0
    assert rows["edge-lost-callback"] == 0
