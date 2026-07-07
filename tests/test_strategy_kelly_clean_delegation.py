"""P1-1 (fable5 audit 2026-07-03, rule:R3): _get_strategy_kelly の汚染除去
回帰テスト。

修正前は all-time 無フィルタ (pre-cutoff / XAU / shadow 混入) で、実弾サイジング
2 経路 (dynamic Kelly boost / half-Kelly lot cap) + shadow promotion が汚染
データで駆動されていた。本番 API では T10 KILL 済み bb_rsi_reversion に
Kelly 0.134 が推奨される実害を確認 (2026-07-03)。修正後は
_get_strategy_kelly_clean へ委譲し、FIDELITY_CUTOFF / XAU / is_shadow
フィルタが適用される。

ref: knowledge-base/wiki/decisions/fable5-phase-a-p0-fixes-2026-07-03.md
"""
from __future__ import annotations

from modules.demo_trader import DemoTrader
from modules.stats_utils import kelly_criterion

# _FIDELITY_CUTOFF = "2026-04-16T08:00:00+00:00" (class attr)
_POST_CUTOFF = "2026-06-01T00:00:00+00:00"
_PRE_CUTOFF = "2026-01-01T00:00:00+00:00"


class _Db:
    def __init__(self, trades):
        self._trades = trades

    def get_all_closed(self):
        return self._trades


def _trade(et, pnl, *, exit_time=_POST_CUTOFF, is_shadow=0, instrument="EUR_USD"):
    return {
        "entry_type": et,
        "status": "CLOSED",
        "pnl_pips": pnl,
        "exit_time": exit_time,
        "is_shadow": is_shadow,
        "instrument": instrument,
    }


def _make_trader(trades):
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = _Db(trades)
    return trader


def _clean_base(et, n_win=6, n_loss=6):
    """クリーン基底: post-cutoff / live / 非XAU の +10p × n_win, -5p × n_loss。"""
    return ([_trade(et, 10.0) for _ in range(n_win)]
            + [_trade(et, -5.0) for _ in range(n_loss)])


def test_contaminated_trades_are_excluded():
    """pre-cutoff / shadow / XAU の勝ちトレードが Kelly を吊り上げないこと。

    旧実装では +50p 勝ち 60 件の混入で Kelly が大幅に過大評価された
    (bb_rsi_reversion 汚染と同型)。新実装はクリーン基底のみで計算する。
    """
    et = "test_strat"
    contamination = (
        [_trade(et, 50.0, exit_time=_PRE_CUTOFF) for _ in range(30)]
        + [_trade(et, 50.0, is_shadow=1) for _ in range(20)]
        + [_trade(et, 50.0, instrument="XAU_USD") for _ in range(10)]
    )
    trader = _make_trader(_clean_base(et) + contamination)

    expected = kelly_criterion(0.5, 10.0, 5.0).get("full_kelly", 0.0)
    got = trader._get_strategy_kelly(et, "EUR_USD")

    assert got is not None
    assert abs(got - expected) < 1e-9, (
        f"contamination leaked into strategy Kelly: got={got} expected={expected}"
    )


def test_delegates_to_clean_variant():
    """_get_strategy_kelly は _get_strategy_kelly_clean と常に一致する。"""
    et = "test_strat"
    trader = _make_trader(
        _clean_base(et) + [_trade(et, 50.0, exit_time=_PRE_CUTOFF) for _ in range(30)]
    )
    assert trader._get_strategy_kelly(et, "USD_JPY") == \
        trader._get_strategy_kelly_clean(et)


def test_insufficient_clean_n_returns_none():
    """クリーン基底 N<10 なら、all-time N が大きくても None (boost/cap 不発)。

    T10 KILL 済み戦略が pre-cutoff 遺産だけで Kelly 推奨を得る経路の封鎖。
    """
    et = "test_strat"
    trader = _make_trader(
        _clean_base(et, n_win=4, n_loss=4)  # clean N=8 < 10
        + [_trade(et, 50.0, exit_time=_PRE_CUTOFF) for _ in range(100)]
    )
    assert trader._get_strategy_kelly(et, "EUR_USD") is None


def test_other_strategy_trades_do_not_bleed():
    """entry_type スコープが維持されること (委譲での退行なし)。"""
    trader = _make_trader(
        _clean_base("strat_a") + [_trade("strat_b", 99.0) for _ in range(50)]
    )
    expected = kelly_criterion(0.5, 10.0, 5.0).get("full_kelly", 0.0)
    got = trader._get_strategy_kelly("strat_a", "EUR_USD")
    assert got is not None and abs(got - expected) < 1e-9
