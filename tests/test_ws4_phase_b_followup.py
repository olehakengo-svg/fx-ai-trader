"""WS4 Phase B follow-up (PR #59 の敵対的レビュー起点、2026-07-07 rule:R3)。

10-agent workflow による PR #59 (P1-3/P1-9) の敵対的検証で confirmed された
3 欠陥の回帰:

1. oscillation: SHADOW_DRIFT_BACKFILL (2026-05-03) が leak backfill の shadow
   分類 (pre-RULE_TS の OANDA-filled リーク行) を次 restart で無条件に live へ
   巻き戻し、冪等マーカーが再修復を恒久ブロック → 不可視の live 再汚染。
   修正 = drift rollback の WHERE に marker 除外を追加。
2. 経路帰属: oanda_trade_id 空のリーク行は flag_drift backfill でも flip される
   ため、is_shadow だけの assert では後継 leak backfill を pin できない
   (force-demoted 側を無効化しても green) → マーカー列で経路を特定する。
3. fill callback 喪失行 (oanda_audit=filled ∧ oanda_trade_id 空) の保護:
   旧 stale ブロック固有の恒久汚染ケース。後継 flag_drift backfill は
   audit=filled を検出すると unsafe-pause して live を保持する。

+ ゼロ境界規約: kelly ゲートは厳密 `< 0` が仕様 (ゼロ/−0.0/None は通過 —
  escape window は統計的に空で EV>friction / Wilson_BF が防御層)。

ref: knowledge-base/wiki/decisions/fable5-system-audit-2026-07-02.md
     (P1-3 follow-up / P2-3 / P2-10 / P2-11)
"""
from __future__ import annotations

import sqlite3

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader

_POST_RULE = "2026-06-01T00:00:00+00:00"
_PRE_RULE = "2026-04-20T00:00:00+00:00"


def _insert_trade(conn, trade_id, *, entry_type, oanda_trade_id="",
                  entry_time=_POST_RULE, instrument="USD_JPY",
                  is_shadow=0, pnl=1.0):
    conn.execute(
        """INSERT INTO demo_trades
           (trade_id, status, direction, entry_price, entry_time, exit_price,
            exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
            confidence, is_shadow, oanda_trade_id, instrument)
           VALUES (?, 'CLOSED', 'BUY', 150.0, ?, 150.01, ?, 149.5, 150.5,
                   ?, 0.1, 'WIN', ?, 80, ?, ?, ?)""",
        (trade_id, entry_time, entry_time, pnl, entry_type,
         is_shadow, oanda_trade_id, instrument),
    )


def _insert_filled_audit(conn, trade_id, entry_type):
    conn.execute(
        """INSERT INTO oanda_audit
           (timestamp, demo_trade_id, entry_type, bridge_status, oanda_trade_id)
           VALUES (?, ?, ?, 'filled', 'OANDA-AUDIT-1')""",
        (_POST_RULE, trade_id, entry_type),
    )


def _fetch_row(db_path, trade_id):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            """SELECT is_shadow, force_demoted_live_leak, flag_drift_backfilled
               FROM demo_trades WHERE trade_id=?""",
            (trade_id,),
        ).fetchone()
    finally:
        conn.close()


def test_filled_leak_row_shadow_classification_survives_restarts(tmp_path):
    """oscillation 修正: pre-RULE_TS の OANDA-filled リーク行の shadow 分類が
    restart を越えて安定する。

    修正前 (敵対的レビューが空 DB 4-init で再現): init#2 で leak backfill が
    shadow 化 (marker=1) → init#3 で SHADOW_DRIFT_BACKFILL が無条件に live へ
    巻き戻し、marker が再修復を恒久ブロック = status 上不可視の live 再汚染。
    """
    db_path = tmp_path / "osc.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "filled-leak",
                      entry_type=sorted(DemoTrader._FORCE_DEMOTED)[0],
                      entry_time=_PRE_RULE,
                      oanda_trade_id="OANDA-FILLED-1")
        conn.commit()

    DemoDB(str(db_path))   # init#2: leak backfill → shadow + marker
    DemoDB(str(db_path))   # init#3: 修正前はここで live へ巻き戻り
    DemoDB(str(db_path))   # init#4: 安定性確認

    row = _fetch_row(db_path, "filled-leak")
    assert row["force_demoted_live_leak"] == 1
    assert row["is_shadow"] == 1, (
        "SHADOW_DRIFT_BACKFILL が leak marker 行を live に巻き戻している "
        "(oscillation 退行)"
    )


def test_drift_backfill_still_restores_ordinary_filled_rows(tmp_path):
    """marker 除外の副作用なし: marker=0 の通常 OANDA-filled 行は従来どおり
    drift rollback が is_shadow=1→0 に復元する。"""
    db_path = tmp_path / "drift.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "ordinary-fill", entry_type="trendline_sweep",
                      is_shadow=1, oanda_trade_id="OANDA-OK-1")
        conn.commit()

    DemoDB(str(db_path))
    row = _fetch_row(db_path, "ordinary-fill")
    assert row["is_shadow"] == 0
    assert (row["force_demoted_live_leak"] or 0) == 0


def test_true_leak_reclassification_attributed_to_successor(tmp_path):
    """後継 leak backfill の経路帰属を marker 列で pin する。

    oanda_trade_id 空の行は flag_drift backfill も flip できるため、
    is_shadow==1 だけの assert では後継を pin できない (敵対的レビューが
    force-demoted 側の monkeypatch 無効化で実証)。"""
    et = sorted(DemoTrader._FORCE_DEMOTED)[0]
    db_path = tmp_path / "leak.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "true-leak", entry_type=et, entry_time=_PRE_RULE)
        conn.commit()

    DemoDB(str(db_path))
    row = _fetch_row(db_path, "true-leak")
    assert row["is_shadow"] == 1
    assert row["force_demoted_live_leak"] == 1, (
        "後継 force-demoted leak backfill が経路として機能していない"
    )
    assert (row["flag_drift_backfilled"] or 0) == 0


def test_fill_callback_lost_live_rows_survive_restart(tmp_path):
    """fill callback 喪失行 (audit=filled ∧ oanda_trade_id 空) は restart 後も
    live (is_shadow=0) を維持する — 旧 stale SHADOW_MIGRATION 固有の恒久汚染
    ケース。後継 flag_drift backfill は audit=filled を検出すると unsafe-pause
    して flip しない。結果はロスター不変 (仮に両戦略が _FORCE_DEMOTED 入り
    しても post-RULE_TS + audit=filled は leak backfill の unsafe-abort が守る
    — 敵対的レビューで monkeypatch 実証済み)。"""
    db_path = tmp_path / "cb-lost.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "bbrsi-live", entry_type="dt_bb_rsi_mr")
        _insert_filled_audit(conn, "bbrsi-live", "dt_bb_rsi_mr")
        _insert_trade(conn, "bbsq-live", entry_type="bb_squeeze_breakout",
                      instrument="EUR_USD")
        _insert_filled_audit(conn, "bbsq-live", "bb_squeeze_breakout")
        conn.commit()

    DemoDB(str(db_path))
    assert _fetch_row(db_path, "bbrsi-live")["is_shadow"] == 0
    assert _fetch_row(db_path, "bbsq-live")["is_shadow"] == 0


def test_shadow_promotion_decision_kelly_boundary_semantics():
    """production 述語のゼロ境界規約を直接 pin する (mirror ではなく本体)。

    block は負のみ。ゼロ (-0.0 含む、full_kelly_raw の 4dp 丸め産物) と
    None (データ不足) は通過 — EV>friction / Wilson_BF ゲートが防御層
    (敵対的レビュー 2026-07-07 の裁定: `<= 0` 化は (0, 5e-5) の正エッジを
    対称に誤 block するため不採用)。"""
    base = dict(n=60, wins=45, num_tests=1)

    assert DemoTrader._shadow_promotion_decision(
        **base, kelly_f=-0.0001)["kelly_blocked"] is True
    assert DemoTrader._shadow_promotion_decision(
        **base, kelly_f=0.0)["kelly_blocked"] is False
    assert DemoTrader._shadow_promotion_decision(
        **base, kelly_f=-0.0)["kelly_blocked"] is False
    assert DemoTrader._shadow_promotion_decision(
        **base, kelly_f=None)["kelly_blocked"] is False
