"""
SignalContext — 全戦略が共有する市場状態のスナップショット。

_compute_scalp_signal_v2 の共通前処理部分を構造化。
各戦略は ctx.entry, ctx.rsi5 等でアクセスする。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import pandas as pd


@dataclass
class SignalContext:
    """全戦略に渡される市場状態。一度だけ計算し、全戦略で再利用。"""

    # ── 価格 ──
    entry: float = 0.0
    open_price: float = 0.0        # 現在足のOpen

    # ── ATR ──
    atr: float = 0.0
    atr7: float = 0.0

    # ── EMA ──
    ema9: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    ema9_prev: float = 0.0
    ema21_prev: float = 0.0

    # ── RSI ──
    rsi: float = 50.0
    rsi5: float = 50.0
    rsi9: float = 50.0

    # ── Stochastic ──
    stoch_k: float = 50.0
    stoch_d: float = 50.0

    # ── ADX ──
    adx: float = 25.0

    # ── MACD ──
    macdh: float = 0.0             # macd_hist 現在
    macdh_prev: float = 0.0        # macd_hist 1本前
    macdh_prev2: float = 0.0       # macd_hist 2本前

    # ── Bollinger Bands ──
    bbpb: float = 0.5              # %B (bb_pband)
    bb_upper: float = 0.0
    bb_mid: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.01
    bb_width_pct: float = 0.5      # 50バー中のパーセンタイル

    # ── 前バー ──
    prev_close: float = 0.0
    prev_open: float = 0.0
    prev_high: float = 0.0
    prev_low: float = 0.0

    # ── EMA200 分析 ──
    ema200_dist: float = 0.0       # ATR正規化距離
    ema200_slope: float = 0.0      # 20バー勾配
    ema200_bull: bool = False       # price > EMA200
    ema200_proximity: bool = False  # |dist| < 0.3

    # ── レイヤー情報 ──
    layer0: dict = field(default_factory=dict)
    layer1: dict = field(default_factory=dict)
    regime: dict = field(default_factory=dict)
    layer2: dict = field(default_factory=dict)
    layer3: dict = field(default_factory=dict)
    htf: dict = field(default_factory=dict)
    session: dict = field(default_factory=dict)

    # ── ADX DI ──
    adx_pos: float = 25.0           # +DI
    adx_neg: float = 25.0           # -DI

    # ── DT用EMAスコア ──
    ema_score: float = 0.0          # EMAスプレッドベースの方向スコア

    # ── メタ情報 ──
    symbol: str = "USDJPY=X"
    tf: str = "1m"
    is_friday: bool = False
    tokyo_mode: bool = False
    hour_utc: int = 12
    is_jpy: bool = True
    pip_mult: int = 100             # 100 for JPY, 10000 for EUR

    # ── DataFrame + SR（戦略が直接参照する場合用）──
    df: Any = None                  # pd.DataFrame
    sr_levels: list = field(default_factory=list)

    # ── backtest ──
    backtest_mode: bool = False
    bar_time: Any = None

    @classmethod
    def from_df(cls, df: pd.DataFrame, row, symbol: str, tf: str,
                sr_levels: list, layer0: dict, layer1: dict,
                regime: dict, layer2: dict, layer3: dict,
                htf: dict, session: dict,
                backtest_mode: bool = False, bar_time=None) -> "SignalContext":
        """DataFrame の最終行 + 各レイヤー結果から SignalContext を構築。"""
        from datetime import datetime, timezone

        _is_jpy = "JPY" in symbol.upper()
        entry = float(row["Close"])
        atr = float(row["atr"])
        atr7 = float(row["atr7"]) if "atr7" in row.index else atr
        ema200 = float(row.get("ema200", row.get("ema50", entry)))

        # EMA200 分析
        _ema200_dist = (entry - ema200) / atr if atr > 0 else 0
        _ema200_slope = 0.0
        if "ema200" in df.columns and len(df) >= 2:
            _ema200_slope = ema200 - float(df["ema200"].iloc[-min(20, len(df) - 1)])

        # セッション時間
        if bar_time:
            _bt = bar_time
        elif hasattr(row.name, 'hour'):
            _bt = row.name
        else:
            _bt = datetime.now(timezone.utc)
        if hasattr(_bt, 'tzinfo') and _bt.tzinfo is None:
            _bt = _bt.replace(tzinfo=timezone.utc)

        # BB width percentile
        bb_width_val = float(row.get("bb_width", 0.01))
        if "bb_width" in df.columns and len(df) >= 50:
            _bw_series = df["bb_width"].iloc[-50:]
            bb_width_pct = float((_bw_series < bb_width_val).sum()) / 50.0
        else:
            bb_width_pct = 0.5

        # MACD history
        macdh = float(row["macd_hist"])
        macdh_prev = float(df.iloc[-2]["macd_hist"]) if len(df) >= 2 else 0.0
        macdh_prev2 = float(df.iloc[-3]["macd_hist"]) if len(df) >= 3 else 0.0

        # 前バー
        prev_row = df.iloc[-2] if len(df) >= 2 else row

        return cls(
            entry=entry,
            open_price=float(row["Open"]),
            atr=atr,
            atr7=atr7,
            ema9=float(row["ema9"]),
            ema21=float(row["ema21"]),
            ema50=float(row["ema50"]),
            ema200=ema200,
            ema9_prev=float(df["ema9"].iloc[-2]) if len(df) >= 2 else float(row["ema9"]),
            ema21_prev=float(df["ema21"].iloc[-2]) if len(df) >= 2 else float(row["ema21"]),
            rsi=float(row["rsi"]),
            rsi5=float(row.get("rsi5", row["rsi"])),
            rsi9=float(row.get("rsi9", row["rsi"])),
            stoch_k=float(row.get("stoch_k", 50.0)),
            stoch_d=float(row.get("stoch_d", 50.0)),
            adx=float(row.get("adx", 25.0)),
            macdh=macdh,
            macdh_prev=macdh_prev,
            macdh_prev2=macdh_prev2,
            bbpb=float(row["bb_pband"]),
            bb_upper=float(row.get("bb_upper", entry + atr)),
            bb_mid=float(row.get("bb_mid", entry)),
            bb_lower=float(row.get("bb_lower", entry - atr)),
            bb_width=bb_width_val,
            bb_width_pct=bb_width_pct,
            prev_close=float(prev_row["Close"]),
            prev_open=float(prev_row["Open"]),
            prev_high=float(prev_row["High"]),
            prev_low=float(prev_row["Low"]),
            ema200_dist=_ema200_dist,
            ema200_slope=_ema200_slope,
            ema200_bull=entry > ema200,
            ema200_proximity=abs(_ema200_dist) < 0.3,
            layer0=layer0,
            layer1=layer1,
            regime=regime,
            layer2=layer2,
            layer3=layer3,
            htf=htf,
            session=session,
            symbol=symbol,
            tf=tf,
            is_friday=_bt.weekday() == 4,
            tokyo_mode=layer0.get("tokyo_mode", False),
            hour_utc=_bt.hour,
            is_jpy=_is_jpy,
            pip_mult=100 if _is_jpy else 10000,
            df=df,
            sr_levels=sr_levels,
            backtest_mode=backtest_mode,
            bar_time=bar_time,
        )
