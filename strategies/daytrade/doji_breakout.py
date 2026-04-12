"""
Doji Breakout — 連続Doji後のボラティリティ解放ブレイクアウト

学術的根拠:
  - Mandelbrot (1963): ボラティリティクラスタリング — 低ボラ圧縮 → 解放
  - Bollinger (2002): 圧縮フェーズはブレイクアウトの前兆
  - BT検証: USD_JPY N=29 WR=48.3% PF=1.28, EUR_USD N=23 WR=39.1%
  - NOTE: vol_spike_mrより優先度低。Sentinel運用

数学的定義:
  Doji Detection:
    body_ratio = abs(Close - Open) / (High - Low)
    doji = body_ratio < DOJI_THRESHOLD (0.20)

  Compression Detection:
    連続3本がdoji (CONSECUTIVE_DOJIS = 3)

  Breakout Detection:
    breakout_bar: abs(Close - Open) > ATR × BREAK_SIZE_MIN (0.5)
    → ブレイクアウト方向にフォロー

  Entry:
    ブレイクアウト足の次の足でエントリー (確認)
    BUY: bullish breakout (Close > Open で大陽線)
    SELL: bearish breakout (Close < Open で大陰線)

  SL: Dojiレンジの反対端 + ATR × 0.3
  TP: ATR × 2.0
  MIN_RR: 1.2

制約:
  USD/JPY, EUR/USD, GBP/USD (3ペア対応)
  MAX_HOLD: 6バー (1.5時間 @ 15m)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class DojiBreakout(StrategyBase):
    name = "doji_breakout"
    mode = "daytrade"
    enabled = True
    _enabled_symbols = {"USDJPY", "EURUSD", "GBPUSD"}

    # ══════════════════════════════════════════════════
    # パラメータ定数 (BT検証済み)
    # ══════════════════════════════════════════════════
    DOJI_THRESHOLD = 0.20      # body_ratio < 20% = doji
    CONSECUTIVE_DOJIS = 3      # 連続3本doji必要
    BREAK_SIZE_MIN = 0.5       # ブレイクアウト足: abs(C-O) > ATR × 0.5
    SL_ATR_MULT = 1.2          # SL = ATR × 1.2
    SL_BUFFER = 0.3            # SL = dojiレンジ反対端 + ATR × 0.3
    TP_ATR_MULT = 2.0          # TP = ATR × 2.0 (低WR補償で広TP)
    MIN_RR = 1.2               # 最低リスクリワード比
    MAX_HOLD_BARS = 6          # 6バー = 1.5時間 @ 15m

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    @staticmethod
    def _body_ratio(open_p: float, close_p: float, high_p: float, low_p: float) -> float:
        """足のボディ比率を計算。High==Lowの場合は0を返す。"""
        bar_range = high_p - low_p
        if bar_range <= 0:
            return 0.0
        return abs(close_p - open_p) / bar_range

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("USDJPY", "EURUSD", "GBPUSD"):
            return None

        # ── データ十分性: 3 doji + 1 breakout + 1 current = 最低5本 ──
        if ctx.df is None or len(ctx.df) < self.CONSECUTIVE_DOJIS + 2:
            return None

        # ── ATRガード ──
        if ctx.atr <= 0:
            return None

        df = ctx.df

        # ══════════════════════════════════════════════════
        # Step 1: 連続Doji検出
        #   df.iloc[-5], df.iloc[-4], df.iloc[-3] = 3本のdoji候補
        #   df.iloc[-2] = ブレイクアウト足候補
        #   df.iloc[-1] = 現在足 (エントリー足)
        # ══════════════════════════════════════════════════

        # 3本のdoji検出 (ブレイクアウト足の前3本)
        doji_start = len(df) - 2 - self.CONSECUTIVE_DOJIS  # -5
        doji_end = len(df) - 2                               # -2 (exclusive)

        if doji_start < 0:
            return None

        doji_high = None
        doji_low = None

        for i in range(doji_start, doji_end):
            o = float(df.iloc[i]["Open"])
            c = float(df.iloc[i]["Close"])
            h = float(df.iloc[i]["High"])
            l = float(df.iloc[i]["Low"])

            br = self._body_ratio(o, c, h, l)
            if br >= self.DOJI_THRESHOLD:
                return None  # doji条件不成立

            # Dojiレンジの上下端を追跡
            doji_high = max(doji_high, h) if doji_high is not None else h
            doji_low = min(doji_low, l) if doji_low is not None else l

        if doji_high is None or doji_low is None:
            return None

        # ══════════════════════════════════════════════════
        # Step 2: ブレイクアウト足検出 (df.iloc[-2])
        # ══════════════════════════════════════════════════
        bo_open = float(df.iloc[-2]["Open"])
        bo_close = float(df.iloc[-2]["Close"])
        bo_high = float(df.iloc[-2]["High"])
        bo_low = float(df.iloc[-2]["Low"])

        bo_body = abs(bo_close - bo_open)
        if bo_body <= ctx.atr * self.BREAK_SIZE_MIN:
            return None  # ブレイクアウト足のボディが不十分

        # ブレイクアウト方向
        if bo_close > bo_open:
            signal = "BUY"
            bo_dir = "UP"
        elif bo_close < bo_open:
            signal = "SELL"
            bo_dir = "DOWN"
        else:
            return None

        # ══════════════════════════════════════════════════
        # Step 3: SL/TP計算
        # ══════════════════════════════════════════════════
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5
        entry = ctx.entry

        if signal == "BUY":
            # BUY: SL = dojiレンジ下端 - ATR×0.3
            sl = doji_low - ctx.atr * self.SL_BUFFER
            tp = entry + ctx.atr * self.TP_ATR_MULT
        else:
            # SELL: SL = dojiレンジ上端 + ATR×0.3
            sl = doji_high + ctx.atr * self.SL_BUFFER
            tp = entry - ctx.atr * self.TP_ATR_MULT

        # ══════════════════════════════════════════════════
        # Step 4: RR検証
        # ══════════════════════════════════════════════════
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        if sl_dist <= 0:
            return None

        rr = tp_dist / sl_dist

        # RR不足時のTP補正
        if rr < self.MIN_RR:
            tp_dist = sl_dist * self.MIN_RR
            tp = entry + tp_dist if signal == "BUY" else entry - tp_dist
            rr = tp_dist / sl_dist

        if rr < self.MIN_RR:
            return None

        # ══════════════════════════════════════════════════
        # Step 5: Reasons & スコア
        # ══════════════════════════════════════════════════
        doji_range_pip = (doji_high - doji_low) * ctx.pip_mult
        bo_body_pip = bo_body * ctx.pip_mult

        score = 4.0  # ベーススコア (vol_spike_mrより低い: 優先度低)
        reasons = []

        reasons.append(
            f"✅ Doji Breakout {signal}: "
            f"{self.CONSECUTIVE_DOJIS}連続Doji → {bo_dir}ブレイク "
            f"(dojiレンジ={doji_range_pip:.1f}pip, BO実体={bo_body_pip:.1f}pip)"
        )

        # ── HTF方向一致ボーナス ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # ── EMA方向一致ボーナス ──
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        # ── ADXボーナス (ブレイクアウト直後のトレンド強度) ──
        if ctx.adx >= 20:
            score += 0.3
            reasons.append(f"✅ ADXトレンド確認(ADX={ctx.adx:.1f}≥20)")

        # ── ブレイクアウト足の強度ボーナス ──
        if bo_body > ctx.atr * 0.8:
            score += 0.3
            reasons.append(f"✅ 強ブレイクアウト(実体>{0.8}ATR)")

        # ── Dojiレンジ圧縮度ボーナス (タイトレンジ = 強ブレイク期待) ──
        if doji_range_pip < ctx.atr * ctx.pip_mult * 0.5:
            score += 0.3
            reasons.append("✅ タイト圧縮(dojiレンジ<0.5ATR)")

        reasons.append(
            f"📊 RR={rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

        conf = int(min(80, 45 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
