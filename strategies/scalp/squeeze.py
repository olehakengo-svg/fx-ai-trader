"""BB Squeeze Breakout — 圧縮→拡大ブレイクアウト (BLL 1992 JoF)"""
import os

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class BBSqueezeBreakout(StrategyBase):
    name = "bb_squeeze_breakout"
    mode = "scalp"

    # チューナブルパラメータ（緩和済み）
    bb_width_pct_max = 0.10  # BB幅パーセンタイル閾値（5→10%緩和）
    adx_min = 20             # ADXトレンド確認（15→20: 学術水準復元）
    vol_mult = 1.2           # ボリューム倍率閾値
    tp_mult = 3.0
    sl_mult = 1.2
    breakout_range_bars = 12
    _v2_seen_bars: set[tuple] = set()

    @classmethod
    def reset_dedup_state(cls):
        cls._v2_seen_bars = set()

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if os.environ.get("SQUEEZE_REDESIGN_V2") == "1":
            return self._evaluate_v2(ctx)

        if ctx.bb_width_pct >= self.bb_width_pct_max:
            return None
        if ctx.adx < self.adx_min:
            return None
        if ctx.df is None or len(ctx.df) < 2:
            return None

        signal = None
        score = 0.0
        reasons = []

        # スクイーズ中に方向を判定
        _prev_bb_width = float(ctx.df["bb_width"].iloc[-2]) if "bb_width" in ctx.df.columns else ctx.bb_width
        _bb_expanding = ctx.bb_width > _prev_bb_width

        if not _bb_expanding:
            return None

        # ボリューム確認（ボーナスに緩和、ブロックしない）
        _vol_bonus = False
        if "Volume" in ctx.df.columns:
            _vol = float(ctx.df.iloc[-1]["Volume"])
            _vol_avg = float(ctx.df["Volume"].iloc[-20:].mean()) if len(ctx.df) >= 20 else _vol
            _vol_bonus = _vol > _vol_avg * self.vol_mult

        # ブレイクアウト方向判定
        if ctx.bbpb > 0.75 and ctx.entry > ctx.ema9 and ctx.ema9 > ctx.ema21:
            signal = "BUY"
            score = 3.5
            reasons.append("✅ BBスクイーズブレイクアウト上抜け (BLL 1992 JoF)")
            reasons.append(f"✅ BB幅{ctx.bb_width_pct*100:.0f}%ile → 拡大開始")
            reasons.append("✅ EMA順列 (9>21) + 価格>EMA9")
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl = ctx.entry - ctx.atr7 * self.sl_mult
        elif ctx.bbpb < 0.25 and ctx.entry < ctx.ema9 and ctx.ema9 < ctx.ema21:
            signal = "SELL"
            score = 3.5
            reasons.append("✅ BBスクイーズブレイクアウト下抜け (BLL 1992 JoF)")
            reasons.append(f"✅ BB幅{ctx.bb_width_pct*100:.0f}%ile → 拡大開始")
            reasons.append("✅ EMA逆順列 (9<21) + 価格<EMA9")
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl = ctx.entry + ctx.atr7 * self.sl_mult

        if signal is None:
            return None

        if _vol_bonus:
            score += 0.5
            reasons.append("✅ 出来高急増")
        if ctx.adx > 20:
            score += 1.0
            reasons.append(f"✅ ADXトレンド確認({ctx.adx:.1f}>20)")

        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)

    def _evaluate_v2(self, ctx: SignalContext) -> Optional[Candidate]:
        df = ctx.df
        if df is None or len(df) < max(55, self.breakout_range_bars + 3):
            return None
        # 2026-09-10 (rule:R3 配線修復, e2-silent-cells-triage-2026-09-10 §2.2):
        # 旧実装は `if not ctx.backtest_mode and ctx.bar_time is None: return None`
        # の hard-guard を持っていたが、live のシグナル呼び出し規約
        # (modules/demo_trader.py _tick → compute_fn(df, tf, sr, symbol)) は
        # bar_time を渡さない (常に None) ため、v2 は live で構造的に恒久 None
        # だった (2026-05-06 commit 942e3800 以降 127 日間 行ゼロ)。
        # 同 wave の xs_momentum / macd_rsi_pullback と同じく「bar_time が無ければ
        # 最終確定バーの index を代用する」fallback に置換する。評価本体は
        # closed signal bar (df.iloc[-2] / df.index[-2]) のみを参照するため
        # BT (backtest_mode=True, 旧 guard 非適用) との評価 parity は不変。
        _bar_time = ctx.bar_time
        if _bar_time is None:
            try:
                _bar_time = df.index[-1]
            except Exception:
                _bar_time = None
        if not ctx.backtest_mode and _bar_time is None:
            return None  # index も無い df では dedup key が作れない (安全側)

        signal_row = df.iloc[-2]
        prev_row = df.iloc[-3]
        signal_time = df.index[-2] if getattr(df, "index", None) is not None else _bar_time
        dedup_key = (ctx.symbol, self.name, signal_time)
        if dedup_key in self._v2_seen_bars:
            return None

        sig_close = float(signal_row["Close"])
        prev_close = float(prev_row["Close"])
        sig_atr = float(signal_row.get("atr7", signal_row.get("atr", ctx.atr7 or ctx.atr)))
        if sig_atr <= 0:
            return None

        sig_width = float(signal_row.get("bb_width", ctx.bb_width))
        prev_width = float(prev_row.get("bb_width", sig_width))
        width_window = df["bb_width"].iloc[-51:-1] if "bb_width" in df.columns else None
        if width_window is not None and len(width_window) >= 20:
            sig_width_pct = float((width_window < sig_width).sum()) / float(len(width_window))
        else:
            sig_width_pct = ctx.bb_width_pct
        if sig_width_pct >= self.bb_width_pct_max:
            return None
        if sig_width <= prev_width:
            return None

        sig_upper = float(signal_row.get("bb_upper", ctx.bb_upper))
        sig_lower = float(signal_row.get("bb_lower", ctx.bb_lower))
        prev_upper = float(prev_row.get("bb_upper", sig_upper))
        prev_lower = float(prev_row.get("bb_lower", sig_lower))
        range_slice = df.iloc[-(self.breakout_range_bars + 2):-2]
        range_high = float(range_slice["High"].max())
        range_low = float(range_slice["Low"].min())

        ema9 = float(signal_row.get("ema9", ctx.ema9))
        ema21 = float(signal_row.get("ema21", ctx.ema21))
        buy_breakout = (prev_close <= prev_upper and sig_close > sig_upper) or sig_close > range_high
        sell_breakout = (prev_close >= prev_lower and sig_close < sig_lower) or sig_close < range_low

        signal = None
        score = 0.0
        reasons = []
        entry = float(ctx.entry)
        if buy_breakout and sig_close > ema9 and ema9 > ema21:
            signal = "BUY"
            score = 3.5
            sl = entry - sig_atr * self.sl_mult
            tp = entry + sig_atr * self.tp_mult
            # ✅ prefix は必須: bb_squeeze_breakout は QUALIFIED_TYPES / SCALP_BT_QUALIFIED
            # で `sum(1 for r in reasons if "✅" in r) >= 1` gate を通る (demo_trader.py
            # no_confirm / app.py run_scalp_backtest — 同一述語で BT/本番 parity)。
            # 旧 v2 は ✅ ゼロで、発火しても no_confirm:bb_squeeze_breakout で死んでいた
            # (2026-09-10 rule:R3 配線修復 層②)。
            reasons.extend([
                "✅ SQUEEZE_REDESIGN_V2: closed-bar BB/range breakout BUY",
                f"BB width {sig_width_pct*100:.0f}%ile expanding on closed signal bar",
                "EMA9>EMA21 trend-continuation filter",
            ])
        elif sell_breakout and sig_close < ema9 and ema9 < ema21:
            signal = "SELL"
            score = 3.5
            sl = entry + sig_atr * self.sl_mult
            tp = entry - sig_atr * self.tp_mult
            reasons.extend([
                "✅ SQUEEZE_REDESIGN_V2: closed-bar BB/range breakout SELL",
                f"BB width {sig_width_pct*100:.0f}%ile expanding on closed signal bar",
                "EMA9<EMA21 trend-continuation filter",
            ])
        if signal is None:
            return None

        if "Volume" in df.columns:
            vol = float(signal_row.get("Volume", 0.0))
            vol_avg = float(df["Volume"].iloc[-21:-1].mean()) if len(df) >= 21 else vol
            if vol_avg > 0 and vol > vol_avg * self.vol_mult:
                score += 0.5
                reasons.append("Volume expansion bonus")

        sig_adx = float(signal_row.get("adx", ctx.adx))
        prev_adx = float(prev_row.get("adx", sig_adx))
        if sig_adx >= self.adx_min or sig_adx > prev_adx:
            score += 0.5
            reasons.append(f"ADX soft confirmation ({sig_adx:.1f})")

        self._v2_seen_bars.add(dedup_key)
        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
