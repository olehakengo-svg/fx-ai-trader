"""
Volume Surge Detector — 出来高急増クライマックス反転 / モメンタム初動

概要:
  出来高（or バーレンジ代替）が直近20本平均の200%以上に急増した瞬間を検出。
  BB極端+RSI過熱 → クライマックス反転 (mean-reversion)
  ADX+DI方向+トレンド → モメンタム初動乗り (trend-following)

学術的根拠:
  - Volume Climax: Harris & Gurel (1986) — 異常出来高後の平均回帰効果
  - Volume Breakout: Blume, Easley & O'Hara (1994, JoF) — 出来高は情報の精度を伝達
  - Bar Range proxy: Parkinson (1980) — High-Low range ≈ realized vol

エントリー:
  CLIMAX BUY:  vol_surge + bbpb<=0.10 + rsi5<30 + 陽線 (跳ね返り)
  CLIMAX SELL: vol_surge + bbpb>=0.90 + rsi5>70 + 陰線 (跳ね返り)
  MOMENTUM BUY:  vol_surge + ADX>=22 + +DI>-DI + EMA9>21 + 陽線
  MOMENTUM SELL: vol_surge + ADX>=22 + -DI>+DI + EMA9<21 + 陰線

決済:
  Climax: TP=ATR7×1.0 (短命反転), SL=ATR7×0.6
  Momentum: TP=ATR7×2.0 (トレンド追随), SL=ATR7×0.8
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class VolSurgeDetector(StrategyBase):
    name = "vol_surge_detector"
    mode = "scalp"
    enabled = True

    # ── パラメータ ──
    vol_surge_mult = 2.0      # 平均の200%以上で急増判定
    vol_lookback = 20         # 出来高平均算出期間
    # Climax parameters
    climax_bbpb_buy = 0.10    # BB下限近接
    climax_bbpb_sell = 0.90   # BB上限近接
    climax_rsi_buy = 30       # RSI過売
    climax_rsi_sell = 70      # RSI過買
    climax_tp_mult = 1.0      # 短命反転TP
    climax_sl_mult = 0.6      # 短命反転SL
    # Momentum parameters
    momentum_adx_min = 22     # トレンド確認
    momentum_tp_mult = 2.0    # トレンド追随TP
    momentum_sl_mult = 0.8    # トレンド追随SL

    # ── セッションフィルター (2026-04-06 Session Matrix BT) ──
    # USD/JPY: Tokyo PF=2.17 ✅, NY_Overlap PF=0.67 ❌, NY_Late PF=0.54 ❌
    # EUR/GBP: Tokyo PF=0.52 ❌, NY_Overlap PF=2.10 ✅, NY_Late PF=1.39 ✅
    # → USD/JPY = Tokyo+Londonのみ, EUR/GBP = NY以降のみ
    _blocked_hours_by_pair = {
        "USDJPY": frozenset(range(12, 24)),  # NY時間帯ブロック
    }

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < self.vol_lookback + 5:
            return None

        # ── 通貨ペア×セッション フィルター ──
        _sym_check = ctx.symbol.upper().replace("=X", "").replace("_", "")
        _blocked = self._blocked_hours_by_pair.get(_sym_check)
        if _blocked and ctx.hour_utc in _blocked:
            return None

        # ── 出来高急増判定 ──
        # Volume列がない or 0ばかりの場合はバーレンジ(H-L)で代替
        _use_volume = False
        if "Volume" in ctx.df.columns:
            _vol_series = ctx.df["Volume"].iloc[-(self.vol_lookback + 1):]
            _vol_mean = float(_vol_series.iloc[:-1].mean())
            _vol_cur = float(_vol_series.iloc[-1])
            if _vol_mean > 0 and _vol_cur > 0:
                _use_volume = True

        if _use_volume:
            _surge = _vol_cur >= _vol_mean * self.vol_surge_mult
            _surge_ratio = round(_vol_cur / max(_vol_mean, 1), 1)
        else:
            # バーレンジ代替: (High-Low) / ATR7 で正規化
            _ranges = (ctx.df["High"] - ctx.df["Low"]).iloc[-(self.vol_lookback + 1):]
            _range_mean = float(_ranges.iloc[:-1].mean())
            _range_cur = float(_ranges.iloc[-1])
            if _range_mean <= 0:
                return None
            _surge = _range_cur >= _range_mean * self.vol_surge_mult
            _surge_ratio = round(_range_cur / max(_range_mean, 1e-8), 1)

        if not _surge:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030 if ctx.is_jpy else 0.00030
        _mode = None  # "climax" or "momentum"

        # ── A: クライマックス反転 (BB極端 + RSI過熱 + 反転足) ──
        if (ctx.bbpb <= self.climax_bbpb_buy
                and ctx.rsi5 < self.climax_rsi_buy
                and ctx.entry > ctx.open_price):
            signal = "BUY"
            _mode = "climax"
            score = 3.5
            reasons.append(f"✅ 出来高急増({_surge_ratio}x≥{self.vol_surge_mult}x) — クライマックス")
            reasons.append(f"✅ BB下限圏(%B={ctx.bbpb:.2f}≤{self.climax_bbpb_buy}) + RSI過売({ctx.rsi5:.1f})")
            reasons.append(f"✅ 陽線反転(C={ctx.entry:.5g}>O={ctx.open_price:.5g})")
            tp = ctx.entry + ctx.atr7 * self.climax_tp_mult
            sl = ctx.entry - max(ctx.atr7 * self.climax_sl_mult, _min_sl)

        elif (ctx.bbpb >= self.climax_bbpb_sell
              and ctx.rsi5 > self.climax_rsi_sell
              and ctx.entry < ctx.open_price):
            signal = "SELL"
            _mode = "climax"
            score = 3.5
            reasons.append(f"✅ 出来高急増({_surge_ratio}x≥{self.vol_surge_mult}x) — クライマックス")
            reasons.append(f"✅ BB上限圏(%B={ctx.bbpb:.2f}≥{self.climax_bbpb_sell}) + RSI過買({ctx.rsi5:.1f})")
            reasons.append(f"✅ 陰線反転(C={ctx.entry:.5g}<O={ctx.open_price:.5g})")
            tp = ctx.entry - ctx.atr7 * self.climax_tp_mult
            sl = ctx.entry + max(ctx.atr7 * self.climax_sl_mult, _min_sl)

        # ── B: モメンタム初動乗り (ADX + DI方向 + EMA整列) ──
        elif (ctx.adx >= self.momentum_adx_min
              and ctx.adx_pos > ctx.adx_neg
              and ctx.ema9 > ctx.ema21
              and ctx.entry > ctx.open_price):
            signal = "BUY"
            _mode = "momentum"
            score = 3.0
            reasons.append(f"✅ 出来高急増({_surge_ratio}x) — モメンタム初動")
            reasons.append(f"✅ ADX={ctx.adx:.1f}≥{self.momentum_adx_min} +DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f}")
            reasons.append(f"✅ EMA整列(9>{ctx.ema9:.5g}>21>{ctx.ema21:.5g}) + 陽線")
            tp = ctx.entry + ctx.atr7 * self.momentum_tp_mult
            sl = ctx.entry - max(ctx.atr7 * self.momentum_sl_mult, _min_sl)

        elif (ctx.adx >= self.momentum_adx_min
              and ctx.adx_neg > ctx.adx_pos
              and ctx.ema9 < ctx.ema21
              and ctx.entry < ctx.open_price):
            signal = "SELL"
            _mode = "momentum"
            score = 3.0
            reasons.append(f"✅ 出来高急増({_surge_ratio}x) — モメンタム初動")
            reasons.append(f"✅ ADX={ctx.adx:.1f}≥{self.momentum_adx_min} -DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f}")
            reasons.append(f"✅ EMA整列(9<{ctx.ema9:.5g}<21<{ctx.ema21:.5g}) + 陰線")
            tp = ctx.entry - ctx.atr7 * self.momentum_tp_mult
            sl = ctx.entry + max(ctx.atr7 * self.momentum_sl_mult, _min_sl)

        if signal is None:
            return None

        # ── スコアボーナス ──
        # 出来高倍率ボーナス
        if _surge_ratio >= 3.0:
            score += 0.8
            reasons.append(f"✅ 極端な出来高急増({_surge_ratio}x≥3.0) +0.8")
        elif _surge_ratio >= 2.5:
            score += 0.4

        # Stoch確認
        if _mode == "climax":
            if signal == "BUY" and ctx.stoch_k < 25 and ctx.stoch_k > ctx.stoch_d:
                score += 0.4
                reasons.append(f"✅ Stochゴールデンクロス(K={ctx.stoch_k:.0f})")
            elif signal == "SELL" and ctx.stoch_k > 75 and ctx.stoch_k < ctx.stoch_d:
                score += 0.4
                reasons.append(f"✅ Stochデッドクロス(K={ctx.stoch_k:.0f})")

        # EMA200方向一致ボーナス (momentum)
        if _mode == "momentum":
            if signal == "BUY" and ctx.ema200_bull:
                score += 0.3
            elif signal == "SELL" and not ctx.ema200_bull:
                score += 0.3

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
