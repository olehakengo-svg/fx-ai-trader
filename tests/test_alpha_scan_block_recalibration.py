"""alpha_scan 静的ブロック再構成の境界値 pin.

pre-reg: knowledge-base/wiki/decisions/alpha-scan-static-block-recalibration-prereg-2026-09-02.md

**なぜ境界値を pin するのか**: 本ツールは本番 `modules/demo_trader.py` の
ブロック条件を行データ側から再構成する。再構成がズレると再較正の結論ごと無効になるが、
ズレは静かに起きる。lesson-validity-check-pins-proxy-2026-09-02 のとおり、
検証すべきは「条件の**意味**が一致していること」であって、
ファイル中に特定の構文が在ることではない。よって境界 (hour 6/7, 16/17, 20/21,
conf 64/65, 69/70) の**振る舞い**を pin する。
"""
import importlib
import json

import pytest

M = importlib.import_module("tools.alpha_scan_block_recalibration")

BLOCK_BY_ID = {bid: fn for bid, _name, fn, _cn, _ce in M.BLOCKS}


def row(instrument="USD_JPY", hour=12, direction="BUY", regime="RANGE",
        confidence=50, entry_type="some_strategy"):
    return {
        "instrument": instrument,
        "entry_time": f"2026-06-15T{hour:02d}:30:00+00:00",
        "direction": direction,
        "regime": json.dumps({"regime": regime, "range_sub": None}),
        "confidence": confidence,
        "entry_type": entry_type,
    }


# ── 時刻境界 ──────────────────────────────────────────────
@pytest.mark.parametrize("hour,expected", [(0, True), (6, True), (7, False), (12, False)])
def test_b1_eurusd_tokyo_hour_boundary(hour, expected):
    assert BLOCK_BY_ID["B1"](row(instrument="EUR_USD", hour=hour)) is expected


@pytest.mark.parametrize("hour,expected", [(16, False), (17, True), (23, True)])
def test_b2_eurusd_late_ny_hour_boundary(hour, expected):
    assert BLOCK_BY_ID["B2"](row(instrument="EUR_USD", hour=hour)) is expected


def test_b2_exempts_weekend_gap_fade():
    """pre-reg §1: weekend_gap_fade は日曜 open が定義上 Late-NY 窓内のため免除."""
    assert BLOCK_BY_ID["B2"](row(instrument="EUR_USD", hour=21)) is True
    assert BLOCK_BY_ID["B2"](
        row(instrument="EUR_USD", hour=21,
            entry_type=M.WEEKEND_GAP_FADE_ENTRY_TYPE)) is False


@pytest.mark.parametrize("hour,expected", [(10, False), (11, True), (12, False)])
def test_b6_h11_eurusd(hour, expected):
    assert BLOCK_BY_ID["B6"](row(instrument="EUR_USD", hour=hour)) is expected


@pytest.mark.parametrize("hour,expected", [(12, False), (13, True), (14, False)])
def test_b7_h13_usdjpy(hour, expected):
    assert BLOCK_BY_ID["B7"](row(instrument="USD_JPY", hour=hour)) is expected


@pytest.mark.parametrize("hour,expected",
                         [(15, False), (16, True), (20, True), (21, False)])
def test_b8_h16_20_usdjpy(hour, expected):
    assert BLOCK_BY_ID["B8"](row(instrument="USD_JPY", hour=hour)) is expected


@pytest.mark.parametrize("hour,expected",
                         [(6, False), (7, True), (8, True), (9, False)])
def test_b10_h7_8_eurusd(hour, expected):
    assert BLOCK_BY_ID["B10"](row(instrument="EUR_USD", hour=hour)) is expected


def test_hour_blocks_are_instrument_scoped():
    """H13 は USD_JPY 限定 — 他ペアに漏れない."""
    assert BLOCK_BY_ID["B7"](row(instrument="EUR_USD", hour=13)) is False
    assert BLOCK_BY_ID["B8"](row(instrument="EUR_JPY", hour=18)) is False
    assert BLOCK_BY_ID["B6"](row(instrument="USD_JPY", hour=11)) is False


# ── confidence 境界 ────────────────────────────────────────
@pytest.mark.parametrize("conf,expected", [(64, True), (65, False)])
def test_b4_range_sell_conf_boundary(conf, expected):
    assert BLOCK_BY_ID["B4"](
        row(regime="RANGE", direction="SELL", confidence=conf)) is expected


@pytest.mark.parametrize("conf,expected", [(64, True), (65, False)])
def test_b5_trend_bull_buy_conf_boundary(conf, expected):
    assert BLOCK_BY_ID["B5"](
        row(regime="TREND_BULL", direction="BUY", confidence=conf)) is expected


@pytest.mark.parametrize("conf,expected", [(69, True), (70, False)])
def test_b9_buy_trend_bear_conf_boundary(conf, expected):
    """B9 だけ閾値が 70 — 65 と取り違えると静かにズレる."""
    assert BLOCK_BY_ID["B9"](
        row(regime="TREND_BEAR", direction="BUY", confidence=conf)) is expected


def test_b5_mr_exempt_strategies_pass():
    """MR 戦略 (押し目買い) は TREND_BULL BUY ブロックの免除対象."""
    assert BLOCK_BY_ID["B5"](
        row(regime="TREND_BULL", direction="BUY", confidence=50,
            entry_type="dt_momentum")) is True
    for et in M.TREND_BULL_MR_EXEMPT:
        assert BLOCK_BY_ID["B5"](
            row(regime="TREND_BULL", direction="BUY", confidence=50,
                entry_type=et)) is False, et


# ── regime の読み出し経路 ────────────────────────────────────
def test_regime_read_path_matches_demo_db():
    """`json.loads(row['regime']).get('regime')` — demo_db.py:2135-2136 と同一経路.

    engine 側は `sig['regime']['regime']` (demo_trader.py:5139)。
    dict でも JSON 文字列でも同じ値を返すことを pin する。
    """
    as_str = row(regime="TREND_BEAR")
    as_dict = dict(as_str, regime={"regime": "TREND_BEAR"})
    assert M._regime_type(as_str) == "TREND_BEAR"
    assert M._regime_type(as_dict) == "TREND_BEAR"
    assert M._regime_type(dict(as_str, regime=None)) is None
    assert M._regime_type(dict(as_str, regime="not json")) is None


# ── データ衛生 (pre-reg §2) ─────────────────────────────────
def test_clean_rows_applies_prereg_exclusions():
    base = dict(row(), outcome="WIN", pnl_pips=1.0, dedup_violation=0)
    assert len(M.clean_rows([base])) == 1
    assert M.clean_rows([dict(base, dedup_violation=1)]) == []
    assert M.clean_rows([dict(base, instrument="XAU_USD")]) == []
    assert M.clean_rows([dict(base, outcome="OPEN")]) == []
    assert M.clean_rows([dict(base, pnl_pips=None)]) == []


def test_is_live_uses_oanda_trade_id_not_is_shadow():
    """MEMORY feedback_live_vs_shadow_strict_separation: is_shadow==0 単独では判定しない."""
    assert M.is_live({"oanda_trade_id": "12345", "is_shadow": 1}) is True
    assert M.is_live({"oanda_trade_id": "", "is_shadow": 0}) is False
    assert M.is_live({"is_shadow": 0}) is False


def test_bonferroni_alpha_matches_block_count():
    """m は実際のブロック数と一致していなければならない (片方だけ増やす事故の pin)."""
    assert len(M.BLOCKS) == M.BONFERRONI_M
    assert M.ALPHA == pytest.approx(0.05 / len(M.BLOCKS))


def test_module_import_has_no_side_effects():
    """tools/*.py はスクリプトかつライブラリ — トップレベル副作用禁止.

    MEMORY: モジュールトップの os.environ / os.chdir / parse_args / Thread.start は禁止。
    再 import しても例外なく通ることで pin する。
    """
    importlib.reload(M)
    assert M.WINDOW_FROM == "2026-04-15"
    assert M.WINDOW_TO == "2026-09-01"
