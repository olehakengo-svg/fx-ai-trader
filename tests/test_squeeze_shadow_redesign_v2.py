from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.squeeze import BBSqueezeBreakout


def _df(*, n=60, signal_at=-2, actual_breakout=True) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="5min", tz="UTC")
    open_ = np.full(n, 1.1000)
    close = np.full(n, 1.1000)
    high = np.full(n, 1.1006)
    low = np.full(n, 1.0994)
    bb_width = np.linspace(0.020, 0.030, n)
    bb_width[-51:] = 0.010
    bb_width[-3] = 0.004
    bb_width[-2] = 0.006

    sig_idx = signal_at if signal_at >= 0 else n + signal_at
    prev_idx = sig_idx - 1
    close[prev_idx] = 1.1004
    open_[sig_idx] = 1.1004
    close[sig_idx] = 1.1014 if actual_breakout else 1.1007
    high[sig_idx] = close[sig_idx] + 0.0002
    low[sig_idx] = 1.1001
    open_[-1] = 1.1012
    close[-1] = 1.1013

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1008),
            "ema21": np.full(n, 1.1002),
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.0990),
            "adx": np.linspace(17.0, 19.0, n),
            "adx_pos": np.full(n, 30.0),
            "adx_neg": np.full(n, 15.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 55.0),
            "macd": np.full(n, 0.0001),
            "macd_sig": np.full(n, 0.00005),
            "macd_hist": np.linspace(0.0001, 0.0020, n),
            "bb_pband": np.full(n, 0.80),
            "bb_upper": np.full(n, 1.1010),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0990),
            "bb_width": bb_width,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode=True, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        rsi9=float(row["rsi9"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        bb_width=float(row["bb_width"]),
        bb_width_pct=0.05,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="EURUSD=X",
        tf="5m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_default_off_uses_existing_bbpb_proxy_path(monkeypatch):
    monkeypatch.delenv("SQUEEZE_REDESIGN_V2", raising=False)
    BBSqueezeBreakout.reset_dedup_state()
    df = _df(signal_at=-1, actual_breakout=False)
    df.iloc[-1, df.columns.get_loc("adx")] = 25.0
    df.iloc[-1, df.columns.get_loc("bb_width")] = 0.007

    got = BBSqueezeBreakout().evaluate(_ctx(df, bar_time=df.index[-1]))

    assert got is not None
    assert got.signal == "BUY"
    assert not any("SQUEEZE_REDESIGN_V2" in reason for reason in got.reasons)


def test_v2_uses_last_closed_bar_actual_breakout(monkeypatch):
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    BBSqueezeBreakout.reset_dedup_state()
    df = _df(signal_at=-2, actual_breakout=True)

    got = BBSqueezeBreakout().evaluate(_ctx(df, bar_time=df.index[-1]))

    assert got is not None
    assert got.signal == "BUY"
    assert round(got.sl, 5) == 1.10010
    assert round(got.tp, 5) == 1.10430
    assert any("SQUEEZE_REDESIGN_V2" in reason for reason in got.reasons)


def test_v2_rejects_bbpb_quartile_without_actual_breakout(monkeypatch):
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    BBSqueezeBreakout.reset_dedup_state()

    got = BBSqueezeBreakout().evaluate(_ctx(_df(signal_at=-2, actual_breakout=False)))

    assert got is None


def test_v2_rejects_current_intrabar_breakout(monkeypatch):
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    BBSqueezeBreakout.reset_dedup_state()

    got = BBSqueezeBreakout().evaluate(
        _ctx(_df(signal_at=-1, actual_breakout=True), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))
    )

    assert got is None


def test_v2_live_call_convention_returns_candidate(monkeypatch):
    """修復 pin 層① (2026-09-10 rule:R3, e2-silent-cells-triage-2026-09-10 §2.2)。

    live のシグナル呼び出し規約 (demo_trader._tick → compute_fn(df, tf, sr,
    symbol)) は backtest_mode=False / bar_time=None。旧 v2 はこの規約で
    hard-guard により恒久 None (127 日間 行ゼロ) — 本テストは旧挙動の pin
    (test_v2_live_without_bar_time_is_blocked) を意図的に反転した修復 pin。
    counterfactual: fallback を消して hard-guard を戻すと本テストが落ちる。
    """
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    BBSqueezeBreakout.reset_dedup_state()

    got = BBSqueezeBreakout().evaluate(_ctx(_df(), backtest_mode=False, bar_time=None))

    assert got is not None
    assert got.signal == "BUY"


def test_v2_live_and_bt_same_df_evaluate_identically(monkeypatch):
    """BT/本番統一原則 pin: 同一 df に対し live 規約 (backtest_mode=False,
    bar_time=None) と BT 規約 (backtest_mode=True, bar_time=index[-1]) で
    signal/sl/tp/score が一致する (評価 parity)。"""
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    df = _df()

    BBSqueezeBreakout.reset_dedup_state()
    live = BBSqueezeBreakout().evaluate(_ctx(df, backtest_mode=False, bar_time=None))
    BBSqueezeBreakout.reset_dedup_state()
    bt = BBSqueezeBreakout().evaluate(_ctx(df, backtest_mode=True, bar_time=df.index[-1]))

    assert live is not None and bt is not None
    assert (live.signal, live.sl, live.tp, live.score) == (bt.signal, bt.sl, bt.tp, bt.score)
    assert live.reasons == bt.reasons


def test_v2_reasons_carry_confirm_mark_for_no_confirm_gate(monkeypatch):
    """修復 pin 層② (2026-09-10 rule:R3)。

    bb_squeeze_breakout は QUALIFIED_TYPES (modules/demo_trader.py no_confirm
    gate) / SCALP_BT_QUALIFIED (app.py run_scalp_backtest) の両方で
    `sum(1 for r in reasons if "✅" in r) >= 1` を要求される。旧 v2 reasons は
    ✅ ゼロで、発火しても no_confirm:bb_squeeze_breakout で live/shadow/BT
    すべて死んでいた。counterfactual: ✅ を消すと本テストが落ちる。
    """
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    BBSqueezeBreakout.reset_dedup_state()

    got = BBSqueezeBreakout().evaluate(_ctx(_df(), backtest_mode=False, bar_time=None))

    assert got is not None
    # demo_trader.py L5597 / app.py L6066 と同一述語
    confirmed_count = sum(1 for r in got.reasons if "✅" in r)
    assert confirmed_count >= 1, f"no_confirm gate would block: {got.reasons}"


def test_v2_live_loser_reaches_shadow_promote_path(monkeypatch):
    """修復 pin 層③ (2026-09-10 rule:R3)。

    loser-shadow (split_shadow_always) 配線は strategies/scalp/__init__.py に
    既存 (SQUEEZE_REDESIGN_V2 + SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE の 2 lever)
    だが、旧 v2 評価器が live で None を返すため候補が永遠に到達しなかった。
    live 呼び出し規約で生成された候補が score 敗北時に shadow promote へ
    届くことを end-to-end で pin する。counterfactual: 層① の fallback を
    戻すと候補が生成されず本テストが落ちる。
    """
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    BBSqueezeBreakout.reset_dedup_state()

    squeeze = BBSqueezeBreakout().evaluate(_ctx(_df(), backtest_mode=False, bar_time=None))
    assert squeeze is not None

    engine = ScalperEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "ema_trend_scalp", 99.0)
    assert engine.split_shadow_always([best, squeeze], best) == [squeeze]


def test_v2_dedups_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    BBSqueezeBreakout.reset_dedup_state()
    ctx = _ctx(_df(), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = BBSqueezeBreakout().evaluate(ctx)
    second = BBSqueezeBreakout().evaluate(ctx)

    assert first is not None
    assert second is None


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "ema_trend_scalp", 5.5)
    squeeze = Candidate("BUY", 60, 1.0, 1.2, ["squeeze"], "bb_squeeze_breakout", 5.0)

    monkeypatch.delenv("SQUEEZE_REDESIGN_V2", raising=False)
    monkeypatch.delenv("SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, squeeze], best) == []

    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, squeeze], best) == [squeeze]
