"""
LCR (London Close Reversal) — ロンドンクローズ反転戦略

学術的根拠:
  - Andersen & Bollerslev (1998): FX intraday volatility U-shape — セッション境界に集中
  - Evans & Lyons (2002): 16:00 WMR/London fixing前のフロー → 反転効果
  - Melvin & Prins (2015): Fixing flow による30分間の方向性→直後の平均回帰

実装背景:
  - EUR/JPY scalp BT: UTC 15 = London fixing時間帯 WR最高, EV=+3.14/trade
  - London close (UTC 15:30-16:00) にフロー集中 → wick主導の反転キャンドル
  - Volume data不可 (yfinance cross pair = 0) → Bar range/ATR比でvolume代替

コンセプト:
  UTC 15:30-16:00 (London fixing前後) で以下の条件を検出:
    1. Bar range ≥ ATR × 1.2 (活発な値動き = volume climax proxy)
    2. Dominant wick ≥ 60% of bar range (wick主導 = rejection/reversal)
    3. 反転方向へエントリー (upper wick → SELL, lower wick → BUY)

  SL: Wick極値 (rejection high/low) + ATR × 0.3
  TP: ATR × 1.5 (反転方向)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class LondonCloseReversal(StrategyBase):
    name = "london_close_reversal"
    mode = "daytrade"
    enabled = False  # DISABLED: 15m BT 44t avg EV≈0 (N不足, edge不十分)

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── 時間帯 (UTC 通算分) ──
    ENTRY_START      = 900      # UTC 15:00
    ENTRY_END        = 975      # UTC 16:15

    # ── Volume proxy (bar range/ATR) ──
    MIN_RANGE_ATR    = 0.8      # Bar range ≥ ATR × 0.8 (volume climax proxy)
    VOL_LOOKBACK     = 20       # Volume平均のルックバック (volume利用時)
    VOL_MULT         = 2.0      # Volume ≥ avg × 2.0 (volume利用時)

    # ── Wick条件 ──
    MIN_WICK_RATIO   = 0.60     # Dominant wick ≥ 60% of bar range
    MIN_BODY_RATIO   = 0.05     # 最低実体比率 (doji判定排除)

    # ── SL/TP ──
    SL_ATR_BUFFER    = 0.3      # SL = wick extreme + ATR × 0.3
    TP_ATR_MULT      = 1.5      # TP = entry ± ATR × 1.5
    MIN_RR           = 1.3      # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS    = 8        # 最大8バー (2時間 @ 15m)

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    @staticmethod
    def _bar_minutes(bar_dt) -> int:
        if hasattr(bar_dt, 'hour') and hasattr(bar_dt, 'minute'):
            return bar_dt.hour * 60 + bar_dt.minute
        return -1

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < self.VOL_LOOKBACK + 5:
            return None

        # ── バータイム取得 ──
        _bt = ctx.bar_time
        if _bt is None and hasattr(ctx.df.index[-1], 'minute'):
            _bt = ctx.df.index[-1]
        if _bt is None:
            return None

        _cur_min = self._bar_minutes(_bt)
        if _cur_min < 0:
            return None

        # ── 時間帯フィルター: UTC 15:30-16:00 ──
        if not (self.ENTRY_START <= _cur_min < self.ENTRY_END):
            return None

        # ── 金曜ブロック (London close前のポジション解消で逆効果) ──
        if ctx.is_friday:
            return None

        # ═══════════════════════════════════════════════════
        # キャンドル分析
        # ═══════════════════════════════════════════════════
        _row = ctx.df.iloc[-1]
        _high = float(_row["High"])
        _low = float(_row["Low"])
        _open = ctx.open_price
        _close = ctx.entry

        _bar_range = _high - _low
        if _bar_range <= 0:
            return None

        # ── Volume proxy: Bar range ≥ ATR × 1.2 ──
        if ctx.atr > 0:
            _range_atr = _bar_range / ctx.atr
            if _range_atr < self.MIN_RANGE_ATR:
                return None
        else:
            return None

        # ── 実Volume チェック (利用可能な場合) ──
        _has_vol = False
        if "Volume" in ctx.df.columns:
            _vol = float(_row.get("Volume", 0))
            if _vol > 0:
                _has_vol = True
                _vol_avg = float(ctx.df["Volume"].iloc[
                    -(self.VOL_LOOKBACK + 1):-1
                ].mean())
                if _vol_avg > 0 and _vol < _vol_avg * self.VOL_MULT:
                    return None  # Volume不足

        # ═══════════════════════════════════════════════════
        # Wick分析
        # ═══════════════════════════════════════════════════
        _upper_wick = _high - max(_open, _close)
        _lower_wick = min(_open, _close) - _low
        _body = abs(_close - _open)

        _dominant_wick = max(_upper_wick, _lower_wick)
        _wick_ratio = _dominant_wick / _bar_range

        # ── Wick比率チェック ──
        if _wick_ratio < self.MIN_WICK_RATIO:
            return None

        # ── 最低実体比率 (完全doji排除) ──
        if _body / _bar_range < self.MIN_BODY_RATIO:
            return None

        # ═══════════════════════════════════════════════════
        # 反転方向決定
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")

        signal = None
        score = 4.5
        reasons = []
        sl = tp = 0.0
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        if _upper_wick > _lower_wick:
            # 上ヒゲ優勢 → 高値拒否 → SELL
            if _agr == "bull":
                return None
            signal = "SELL"
            sl = _high + ctx.atr * self.SL_ATR_BUFFER
            tp = _close - ctx.atr * self.TP_ATR_MULT
            reasons.append(
                f"✅ LCR SELL: London Close上ヒゲ反転 "
                f"(wick={_wick_ratio:.0%}, range/ATR={_range_atr:.1f})"
            )
        elif _lower_wick > _upper_wick:
            # 下ヒゲ優勢 → 安値拒否 → BUY
            if _agr == "bear":
                return None
            signal = "BUY"
            sl = _low - ctx.atr * self.SL_ATR_BUFFER
            tp = _close + ctx.atr * self.TP_ATR_MULT
            reasons.append(
                f"✅ LCR BUY: London Close下ヒゲ反転 "
                f"(wick={_wick_ratio:.0%}, range/ATR={_range_atr:.1f})"
            )

        if signal is None:
            return None

        # ═══════════════════════════════════════════════════
        # RR検証
        # ═══════════════════════════════════════════════════
        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None

        if _tp_d / _sl_d < self.MIN_RR:
            _tp_d = _sl_d * self.MIN_RR
            tp = ctx.entry - _tp_d if signal == "SELL" else ctx.entry + _tp_d

        if _sl_d <= 0 or _tp_d / _sl_d < self.MIN_RR:
            return None

        _rr = _tp_d / _sl_d

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

        # Volume確認ボーナス
        if _has_vol:
            score += 0.5
            reasons.append("✅ Volume climax確認")

        # HTF一致ボーナス
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # EMA一致ボーナス
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        # RSI極値ボーナス (過買/過売からの反転)
        if (signal == "SELL" and ctx.rsi > 70) or \
           (signal == "BUY" and ctx.rsi < 30):
            score += 0.5
            reasons.append(f"✅ RSI極値反転(RSI={ctx.rsi:.0f})")

        # 強wick (≥75%) ボーナス
        if _wick_ratio >= 0.75:
            score += 0.3
            reasons.append(f"✅ 強wick({_wick_ratio:.0%}≥75%)")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
