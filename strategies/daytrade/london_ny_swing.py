"""
London-NY Swing — ロンドン高安ブレイク追随デイトレード

概要:
  ロンドンセッション(UTC 7-12)の高値・安値を計測し、
  NYセッション(UTC 13-17)でそのレンジをブレイクした場合に追随。
  H1足EMA20と同方向なら前日高安まで狙う中距離スイング。

学術的根拠:
  - London/NY handoff: Ito & Hashimoto (2006) — セッション間の方向持続性
  - Range breakout: Donchian (1960) — 高値/安値ブレイクの統計的優位性
  - Session momentum: King et al. (2012, BIS) — NY open後のモメンタム持続

対象: EUR/USD, GBP/USD のみ

エントリー:
  BUY:  Close > London High + ATR×0.1 AND H1 EMA20方向=UP
        AND ADX >= 18 AND 陽線確認
  SELL: Close < London Low - ATR×0.1 AND H1 EMA20方向=DOWN
        AND ADX >= 18 AND 陰線確認

決済:
  TP: 前日High (BUY) / 前日Low (SELL), or ATR×3.0 (fallback)
  SL: London High/Low の反対側 + ATR×0.3
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class LondonNySwing(StrategyBase):
    name = "london_ny_swing"
    mode = "daytrade"
    enabled = True

    # ── パラメータ ──
    ldn_start_utc = 7     # London session start
    ldn_end_utc = 12      # London session end
    ny_start_utc = 13     # NY entry window start
    ny_end_utc = 17       # NY entry window end
    break_buffer = 0.1    # ブレイク確認バッファ (ATR倍率)
    adx_min = 18
    tp_fallback_mult = 3.0  # 前日H/L到達不能時のTP
    sl_mult = 0.3           # SLバッファ (ATR倍率)
    min_ldn_range_atr = 0.5  # ロンドンレンジ最小幅
    max_ldn_range_atr = 4.0  # ロンドンレンジ最大幅（異常排除）

    _enabled_symbols = frozenset({"EURUSD", "GBPUSD"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        # ── NYセッション時間帯のみ ──
        if not (self.ny_start_utc <= ctx.hour_utc <= self.ny_end_utc):
            return None

        if ctx.df is None or len(ctx.df) < 50 or ctx.atr <= 0:
            return None

        if ctx.adx < self.adx_min:
            return None

        # ── ロンドンセッションの高安計算 ──
        _ldn_high = None
        _ldn_low = None
        _prev_day_high = None
        _prev_day_low = None

        for idx in range(len(ctx.df) - 2, max(0, len(ctx.df) - 200), -1):
            _row = ctx.df.iloc[idx]
            _t = ctx.df.index[idx]
            _h = _t.hour if hasattr(_t, 'hour') else 12
            _d = _t.date() if hasattr(_t, 'date') else None

            # ロンドンセッションバーを収集
            _today = ctx.bar_time.date() if ctx.bar_time and hasattr(ctx.bar_time, 'date') else None
            if _d == _today and self.ldn_start_utc <= _h < self.ldn_end_utc:
                _rh = float(_row["High"])
                _rl = float(_row["Low"])
                if _ldn_high is None or _rh > _ldn_high:
                    _ldn_high = _rh
                if _ldn_low is None or _rl < _ldn_low:
                    _ldn_low = _rl

            # 前日のH/L
            if _d and _today and _d < _today:
                _rh = float(_row["High"])
                _rl = float(_row["Low"])
                if _prev_day_high is None or _rh > _prev_day_high:
                    _prev_day_high = _rh
                if _prev_day_low is None or _rl < _prev_day_low:
                    _prev_day_low = _rl

        if _ldn_high is None or _ldn_low is None:
            return None

        _ldn_range = _ldn_high - _ldn_low
        if _ldn_range < ctx.atr * self.min_ldn_range_atr:
            return None  # レンジが狭すぎる
        if _ldn_range > ctx.atr * self.max_ldn_range_atr:
            return None  # 異常ボラ

        # ── H1 EMA20方向の簡易判定 ──
        # 15m足の4本 ≈ 1H。直近4本のEMA9トレンドで代替
        _h1_bull = ctx.ema9 > ctx.ema21 and ctx.entry > ctx.ema50
        _h1_bear = ctx.ema9 < ctx.ema21 and ctx.entry < ctx.ema50

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.00030 if "JPY" not in _sym else 0.030

        # ── BUY: London High ブレイク + H1 UP ──
        if (ctx.entry > _ldn_high + ctx.atr * self.break_buffer
                and _h1_bull
                and ctx.entry > ctx.open_price):  # 陽線
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ London High突破(C={ctx.entry:.5f}>LH={_ldn_high:.5f}+buffer)")
            reasons.append(f"✅ H1方向UP(EMA9>21>50)")
            reasons.append(f"✅ 陽線確認 + ADX={ctx.adx:.1f}")

            # TP: 前日Highまたはfallback
            if _prev_day_high and _prev_day_high > ctx.entry:
                tp = _prev_day_high
                reasons.append(f"✅ TP=前日High({_prev_day_high:.5f})")
            else:
                tp = ctx.entry + ctx.atr * self.tp_fallback_mult

            sl = _ldn_high - ctx.atr * self.sl_mult
            sl = min(sl, ctx.entry - _min_sl)

        # ── SELL: London Low ブレイク + H1 DOWN ──
        elif (ctx.entry < _ldn_low - ctx.atr * self.break_buffer
              and _h1_bear
              and ctx.entry < ctx.open_price):  # 陰線
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ London Low突破(C={ctx.entry:.5f}<LL={_ldn_low:.5f}-buffer)")
            reasons.append(f"✅ H1方向DOWN(EMA9<21<50)")
            reasons.append(f"✅ 陰線確認 + ADX={ctx.adx:.1f}")

            if _prev_day_low and _prev_day_low < ctx.entry:
                tp = _prev_day_low
                reasons.append(f"✅ TP=前日Low({_prev_day_low:.5f})")
            else:
                tp = ctx.entry - ctx.atr * self.tp_fallback_mult

            sl = _ldn_low + ctx.atr * self.sl_mult
            sl = max(sl, ctx.entry + _min_sl)

        if signal is None:
            return None

        # ── RR検証 ──
        _tp_dist = abs(tp - ctx.entry)
        _sl_dist = abs(ctx.entry - sl)
        if _tp_dist < _sl_dist * 1.3:
            return None

        # ── スコアボーナス ──
        if ctx.adx >= 30:
            score += 0.6
            reasons.append(f"✅ ADX強トレンド({ctx.adx:.1f})")
        elif ctx.adx >= 25:
            score += 0.3

        # DI方向一致
        if signal == "BUY" and ctx.adx_pos > ctx.adx_neg:
            score += 0.3
        elif signal == "SELL" and ctx.adx_neg > ctx.adx_pos:
            score += 0.3

        # HTF agreement
        _htf_ag = ctx.htf.get("agreement", "mixed") if ctx.htf else "mixed"
        if (signal == "BUY" and _htf_ag == "bull") or (signal == "SELL" and _htf_ag == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_htf_ag})")
        elif (signal == "BUY" and _htf_ag == "bear") or (signal == "SELL" and _htf_ag == "bull"):
            score -= 1.0
            reasons.append(f"⚠️ HTF逆行({_htf_ag}) — スコア-1.0")

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
        )
