"""gate_block_daily の magnitude 記録 (rule:R3, 2026-09-21).

背景 — 2026-09-21 ps 席 C1 readout (registry ps-seat-supply-hourly-c1-coverage):
NZD_JPY / EUR_AUD / USD_CAD の 3 席は distinct bar 6/6 すべてが `spread_wide`
で落ちていたと帰属できたが、**閾値をどれだけ超えたのかが永続面に無かった**ため
「marginal (3.1p vs 3.0p limit = 調整可能)」と「absolute (15p = 構造的)」を
区別できず、席の disposition を決められなかった。in-memory counter が
`reason.split('(')[0]` でキー空間を絞るのは正しいが、永続 rollup まで同じ
正規化で数値を捨てていたのが欠陥。

counterfactual pin (= 配線を revert すると落ちる、恒真にならない):
  * test_parse_reason_metric_returns_none_for_known_unmeasured — 「NG を返す
    既知の入力」。全入力で数値を返す実装 (例: 括弧の無い reason から適当に
    拾う) はここで落ちる。
  * test_spread_wide_magnitude_survives_entry_block_path — parser 単体ではなく
    _record_entry_block → 永続面までの経路 pin。metric passthrough を外すと落ちる。
挙動不変 pin:
  * test_count_accounting_unchanged_by_metric — count / キー空間が magnitude
    導入前と同一であること (キー爆発の再発防止)。
"""
from __future__ import annotations

import sqlite3
import threading
import types

from modules.block_event_logger import (
    init_block_table,
    parse_reason_metric,
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


# ── parser ──────────────────────────────────────────────────────────────


def test_parse_reason_metric_extracts_measured_value():
    # 実際に本番 _block() が生成する文字列そのまま
    assert parse_reason_metric("spread_wide(4.2pip>3.0)") == 4.2
    assert parse_reason_metric("spread_wide(15.0pip>1.5)") == 15.0
    assert parse_reason_metric("cooldown(45s)") == 45.0
    assert parse_reason_metric("velocity_down(-3.5pip)") == -3.5
    assert parse_reason_metric("spread_sl_gate(0.35>0.20)") == 0.35


def test_parse_reason_metric_returns_none_for_known_unmeasured():
    """NG を返す既知の入力 — 数値を持たない reason で None を返すこと.

    ここが恒真 (常に数値を返す) だと metric_n が測っていない gate まで
    数え上げ、mean が別物になる。
    """
    assert parse_reason_metric("order_bar_dedup") is None
    assert parse_reason_metric("no_confirm:macd_rsi_pullback") is None
    assert parse_reason_metric("r2_shadow_demoted_cell") is None
    assert parse_reason_metric("hedge_block") is None
    assert parse_reason_metric("") is None
    assert parse_reason_metric(None) is None
    # 括弧の中に数値が無いケース (本番 hedge_block の実形)
    assert parse_reason_metric("hedge_block(daytrade/EUR_USD:BUY)") is None


# ── 集計 ────────────────────────────────────────────────────────────────


def _row(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    r = conn.execute(
        "SELECT count, metric_n, metric_sum, metric_min, metric_max"
        " FROM gate_block_daily"
    ).fetchone()
    conn.close()
    return dict(r)


def test_metric_min_mean_max_aggregate_per_key(tmp_path):
    path = _db_file(tmp_path)
    for m in (4.2, 3.1, 9.8):
        assert record_block(path, mode="daytrade_1h_nzdjpy",
                            entry_type="price_shock_rev_nzd_jpy_h1_long",
                            instrument="NZD_JPY", reason_key="spread_wide",
                            metric=m)
    r = _row(path)
    assert r["count"] == 3
    assert r["metric_n"] == 3
    assert r["metric_min"] == 3.1
    assert r["metric_max"] == 9.8
    assert abs(r["metric_sum"] - 17.1) < 1e-9
    out = query_block_counts(path, days=7)
    cell = out["per_cell_metrics"][
        "price_shock_rev_nzd_jpy_h1_long|NZD_JPY:spread_wide"]
    assert cell["n"] == 3
    assert cell["min"] == 3.1
    assert cell["max"] == 9.8
    assert cell["mean"] == 5.7  # 17.1/3


def test_unmeasured_gate_keeps_metric_null(tmp_path):
    """metric=None は「測っていない」— 0 として記録してはいけない."""
    path = _db_file(tmp_path)
    record_block(path, mode="daytrade", entry_type="hull_donchian_fade",
                 instrument="EUR_USD", reason_key="order_bar_dedup")
    r = _row(path)
    assert r["count"] == 1
    assert r["metric_n"] == 0
    assert r["metric_sum"] is None
    assert r["metric_min"] is None
    assert r["metric_max"] is None
    # 読み手側にも現れない (mean=0 のような偽の数字を出さない)
    out = query_block_counts(path, days=7)
    assert out["per_cell_metrics"] == {}
    assert out["per_cell_counts"] == {
        "hull_donchian_fade|EUR_USD:order_bar_dedup": 1}


def test_mixed_measured_and_unmeasured_same_key(tmp_path):
    """同一キーに測定あり/なしが混ざっても mean の分母は測定ぶんだけ."""
    path = _db_file(tmp_path)
    kw = dict(mode="daytrade", entry_type="x", instrument="EUR_USD",
              reason_key="spread_wide")
    record_block(path, **kw, metric=None)
    record_block(path, **kw, metric=2.0)
    record_block(path, **kw, metric=4.0)
    r = _row(path)
    assert r["count"] == 3
    assert r["metric_n"] == 2
    assert abs(r["metric_sum"] - 6.0) < 1e-9
    assert query_block_counts(path, days=7)["per_cell_metrics"][
        "x|EUR_USD:spread_wide"]["mean"] == 3.0


def test_count_accounting_unchanged_by_metric(tmp_path):
    """挙動不変 pin: キー空間は magnitude 導入前と同一 (爆発しない)."""
    path = _db_file(tmp_path)
    for m in (1.1, 2.2, 3.3, 4.4):
        record_block(path, mode="daytrade", entry_type="x", instrument="EUR_USD",
                     reason_key="spread_wide", metric=m)
    conn = sqlite3.connect(path)
    n_rows = conn.execute("SELECT COUNT(*) FROM gate_block_daily").fetchone()[0]
    conn.close()
    assert n_rows == 1, "magnitude 別に行が増えてはいけない (PK は不変)"
    assert query_block_counts(path, days=7)["total"] == 4


# ── 既存 DB のマイグレーション ──────────────────────────────────────────


def test_legacy_table_is_migrated_in_place(tmp_path):
    """2026-09-21 より前に作られた本番テーブルに列を足しても既存行は残る."""
    path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE gate_block_daily ("
        " day TEXT NOT NULL, mode TEXT NOT NULL, entry_type TEXT NOT NULL,"
        " instrument TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL,"
        " count INTEGER NOT NULL DEFAULT 0, first_ts TEXT, last_ts TEXT,"
        " PRIMARY KEY (day, mode, entry_type, instrument, reason))"
    )
    conn.execute(
        "INSERT INTO gate_block_daily VALUES"
        " (date('now'), 'daytrade', 'legacy_strat', 'EUR_USD', 'spread_wide',"
        "  7, '2026-09-11T00:00:00+00:00', '2026-09-11T00:00:00+00:00')"
    )
    conn.commit()
    conn.close()

    assert init_block_table(path)  # migration here

    conn = sqlite3.connect(path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gate_block_daily)")}
    conn.close()
    assert {"metric_n", "metric_sum", "metric_min", "metric_max"} <= cols

    out = query_block_counts(path, days=7)
    assert out["per_cell_counts"]["legacy_strat|EUR_USD:spread_wide"] == 7
    assert out["per_cell_metrics"] == {}  # 過去行は未測定のまま (捏造しない)

    # 以後の書込みは magnitude を持つ
    record_block(path, mode="daytrade", entry_type="legacy_strat",
                 instrument="EUR_USD", reason_key="spread_wide", metric=5.5)
    m = query_block_counts(path, days=7)["per_cell_metrics"][
        "legacy_strat|EUR_USD:spread_wide"]
    assert m == {"n": 1, "sum": 5.5, "min": 5.5, "max": 5.5, "mean": 5.5}


def test_init_block_table_is_idempotent(tmp_path):
    path = _db_file(tmp_path)
    assert init_block_table(path)
    assert init_block_table(path)


# ── 経路 pin (parser 単体ではなく _tick_entry からの配線) ────────────────


def test_spread_wide_magnitude_survives_entry_block_path(tmp_path):
    """_record_entry_block の raw reason から永続面まで magnitude が届くこと.

    _persist_gate_block の metric passthrough を外すと落ちる。
    """
    path = _db_file(tmp_path)
    trader = _light_trader(path)
    trader._UNIVERSAL_SENTINEL = set()
    trader._SCALP_SENTINEL = set()
    trader._SILENT_DROP_DIAG_TYPES = set()

    trader._record_entry_block(
        "daytrade_1h_nzdjpy", "price_shock_rev_nzd_jpy_h1_long", "NZD_JPY",
        "spread_wide(4.2pip>3.0)")
    trader._record_entry_block(
        "daytrade_1h_nzdjpy", "price_shock_rev_nzd_jpy_h1_long", "NZD_JPY",
        "spread_wide(6.8pip>3.0)")

    # in-memory キーは旧挙動どおり '(' 前で正規化 (挙動不変)
    assert trader._block_counts == {"daytrade_1h_nzdjpy:spread_wide": 2}
    assert trader._block_counts_per_strategy == {
        "price_shock_rev_nzd_jpy_h1_long:spread_wide": 2}

    m = query_block_counts(path, days=7)["per_cell_metrics"][
        "price_shock_rev_nzd_jpy_h1_long|NZD_JPY:spread_wide"]
    assert m["n"] == 2
    assert m["min"] == 4.2
    assert m["max"] == 6.8
    assert m["mean"] == 5.5


def test_unmeasured_reason_via_entry_block_stays_null(tmp_path):
    path = _db_file(tmp_path)
    trader = _light_trader(path)
    trader._UNIVERSAL_SENTINEL = set()
    trader._SCALP_SENTINEL = set()
    trader._SILENT_DROP_DIAG_TYPES = set()
    trader._record_entry_block(
        "daytrade", "hull_donchian_fade", "EUR_USD",
        "hedge_block(daytrade/EUR_USD:BUY)")
    out = query_block_counts(path, days=7)
    assert out["per_cell_counts"] == {
        "hull_donchian_fade|EUR_USD:hedge_block": 1}
    assert out["per_cell_metrics"] == {}


# ── 単位の非可換性 + 明示読み手 ─────────────────────────────────────────


def test_metric_unit_is_per_reason_not_global():
    """magnitude の単位は reason ごとに違う — 跨いで平均してはいけない.

    同一 reason 内では一貫する (spread_wide は常に pip) が、
    `gbp_asia_flash_crash(UTC21)` は「21 pip」ではなく **UTC 時刻 21 時**。
    per_cell_metrics のキーが reason を含むのはこのため。ここは仕様の
    文書化であって欠陥ではない — 将来の読み手が 21 を pip と誤読しないよう pin する。
    """
    assert parse_reason_metric("spread_wide(4.2pip>3.0)") == 4.2        # pip
    assert parse_reason_metric("cooldown(45s)") == 45.0                 # 秒
    assert parse_reason_metric("gbp_asia_flash_crash(UTC21)") == 21.0   # UTC 時
    # → 同じ metric 列に入るが、キーが reason で分かれるので混ざらない
    assert parse_reason_metric("velocity_down(-3.5pip)") == -3.5        # pip (符号つき)


def test_app_exposes_per_cell_metrics_explicitly():
    """読み手が app.py に**名前で**現れること (暗黙の dict 透過にしない).

    estimand 宣言 gate_block_attribution の reader 配線検査
    (`app.py :: per_cell_metrics`) と同じ不変条件をテスト側にも置く。
    persisted 経由の透過だけに戻すとここが落ちる。
    """
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "app.py").read_text()
    assert '"per_cell_metrics": _persisted_metrics' in src, (
        "block-counts エンドポイントが per_cell_metrics を明示的に露出していない"
    )
    assert 'persisted.get("per_cell_metrics")' in src
