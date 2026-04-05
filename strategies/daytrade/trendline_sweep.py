"""
Trendline Sweep Trap — 斜めの流動性ハント

学術的根拠:
  - Edwards & Magee (1948): Trendline = 需給の均衡点の軌跡
  - Osler (2003): Retail stop-loss orders cluster below trendlines
  - Kyle (1985): Informed traders exploit predictable order flow
  - Connors & Raschke (1995): False breakout of diagonal support

戦略コンセプト:
  個人投資家は「きれいなトレンドライン」のブレイクでストップロスを置く。
  大口はこのSL集中帯を狙って一時的にトレンドラインを突き抜けさせ（Sweep）、
  個人の順張り売り（買い）を誘い込む。流動性を獲得した後、価格は急速にTL内に
  回帰し、元のトレンド方向へ継続する。

  Turtle Soup（水平フラクタル）の斜め版。
  水平SR vs 斜めTL = 異なる流動性クラスターを狙うため、負相関で分散効果。

トレンドライン定義（Swing Point 接線法）:

  ■ 上昇トレンドライン (Ascending TL):
    直近2つのSwing Low (L1, L2) を通る直線。
    条件: L2_price > L1_price (Higher Low) かつ L2_idx > L1_idx
    slope = (L2 - L1) / (idx2 - idx1)
    TL(bar_idx) = L1 + slope * (bar_idx - idx1)

  ■ 下降トレンドライン (Descending TL):
    直近2つのSwing High (H1, H2) を通る直線。
    条件: H2_price < H1_price (Lower High) かつ H2_idx > H1_idx
    slope = (H2 - H1) / (idx2 - idx1)
    TL(bar_idx) = H1 + slope * (bar_idx - idx1)

エントリーロジック（3段階）:

  ■ STEP1: トレンドライン構築
    Williams Fractal (n=FRACTAL_N) でSwing High/Low検出。
    直近のHL or LH ペアから上昇/下降TLを構築。
    TLの傾きが穏やか（|slope| / ATR ∈ [MIN_SLOPE, MAX_SLOPE]）であること。

  ■ STEP2: Sweep 検出
    過去 SWEEP_LOOKBACK 本以内で、TL値を超過するバーが存在。
    上昇TL sweep: Low < TL - margin (下方突き抜け)
    下降TL sweep: High > TL + margin (上方突き抜け)
    大口介入: sweep足の bar_range / ATR ≥ VOL_RATIO_MIN

  ■ STEP3: Reclaim（急速回帰）— 現在足
    上昇TL sweep後: Close > TL（TL上方に回帰）+ 陽線確認
    下降TL sweep後: Close < TL（TL下方に回帰）+ 陰線確認
    前足Closeは外側（fresh return保証）。

  SL: sweep extreme ± ATR × SL_ATR_BUFFER
  TP: TLの延長方向 ATR × TP_ATR_MULT、またはATR-based
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class TrendlineSweep(StrategyBase):
    name = "trendline_sweep"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ
    # ══════════════════════════════════════════════════

    # ── Fractal / Swing Point ──
    FRACTAL_N = 4               # Williams Fractal: 両側4本 (9バー窓 = 2.25H on 15m)
    FRACTAL_LOOKBACK = 100      # ルックバック100本 (15m × 100 = 25H ≈ 1.5営業日)

    # ── Trendline品質 ──
    MIN_TL_BARS = 8             # L1-L2間の最低距離: 8本 (2H)
    MAX_TL_BARS = 60            # L1-L2間の最大距離: 60本 (15H)
    MIN_SLOPE_ATR = 0.003       # |slope| ≥ ATR × 0.003 per bar (ほぼ水平を除外)
    MAX_SLOPE_ATR = 0.08        # |slope| ≤ ATR × 0.08 per bar (急傾斜を除外)
    MIN_TL_RESPECT = 1          # TL構築後、追加で1回以上TLにタッチ（信頼性）

    # ── Sweep ──
    SWEEP_LOOKBACK = 6          # sweep検出: 最大6本前 (= 1.5H)
    SWEEP_MARGIN_ATR = 0.1      # sweep: TLから ≥ 0.1ATR 超過
    VOL_RATIO_MIN = 1.0         # sweep足の bar_range/ATR ≥ 1.0

    # ── Reclaim ──
    RECLAIM_BODY_RATIO = 0.35   # 回帰足の実体/レンジ ≥ 35% (大陽線/大陰線)

    # ── ADX ──
    ADX_MIN = 15                # モメンタム最低閾値
    ADX_MAX = 45                # 極端なトレンド除外

    # ── SL/TP ──
    SL_ATR_BUFFER = 0.3
    TP_ATR_MULT = 2.5
    MIN_RR = 1.5

    # ── 時間帯 ──
    ACTIVE_HOURS_START = 6
    ACTIVE_HOURS_END = 20
    FRIDAY_BLOCK_HOUR = 16

    # ── ペアフィルター ──
    # USD/JPY: 30t WR=36.7% EV=-0.197 → 除外（macro trend方向に本物のTL break）
    ALLOWED_PAIRS = {
        "EURUSD", "GBPUSD", "EURGBP", "XAUUSD",
    }
    # BUY WR不足ペア: SELL方向のみ許可
    # EUR/USD: BUY WR=12% vs SELL WR=64%
    # EUR/GBP: BUY WR=42% vs SELL WR=58%
    # XAU/USD: BUY WR=46% vs SELL WR=73%
    SELL_ONLY_PAIRS = {"EURUSD", "EURGBP", "XAUUSD"}

    def _normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().replace("=X", "").replace("=F", "").replace("/", "").replace("_", "")
        if s in ("GC", "GCF"):
            return "XAUUSD"
        return s

    # ══════════════════════════════════════════════════
    # Swing Point 検出
    # ══════════════════════════════════════════════════

    def _find_swing_points(self, df, n: int, lookback: int):
        """Williams Fractal でSwing High/Low を検出。

        Returns:
            (swing_highs, swing_lows): list of (price, bar_index)
        """
        _start = max(0, len(df) - lookback)
        _end = len(df) - n
        highs = df["High"].values
        lows = df["Low"].values

        sh = []
        sl = []

        for i in range(_start + n, _end):
            _h = highs[i]
            if all(_h > highs[j] for j in range(i - n, i)) and \
               all(_h > highs[j] for j in range(i + 1, i + n + 1)):
                sh.append((float(_h), i))

            _l = lows[i]
            if all(_l < lows[j] for j in range(i - n, i)) and \
               all(_l < lows[j] for j in range(i + 1, i + n + 1)):
                sl.append((float(_l), i))

        return sh, sl

    # ══════════════════════════════════════════════════
    # Trendline 構築
    # ══════════════════════════════════════════════════

    def _build_trendlines(self, swing_highs, swing_lows, atr, df, lows_arr, highs_arr):
        """Swing PointからTrendlineを構築。

        TL respect count は全バーのタッチ（Lowがascending TLに接近 / Highが
        descending TLに接近）で判定。Swing Pointのみだと過少判定になる。

        Returns:
            list of dict: {type, slope, intercept, p1, p2, idx1, idx2, respect_count}
        """
        trendlines = []
        _df_len = len(df)
        _tl_touch_zone = atr * 0.3

        # ── 上昇TL: Swing Low 2点 (Higher Low) ──
        if len(swing_lows) >= 2:
            sorted_lows = sorted(swing_lows, key=lambda x: x[1])
            for i in range(len(sorted_lows) - 1):
                for j in range(i + 1, len(sorted_lows)):
                    p1, idx1 = sorted_lows[i]
                    p2, idx2 = sorted_lows[j]

                    if p2 <= p1:
                        continue

                    _dist = idx2 - idx1
                    if _dist < self.MIN_TL_BARS or _dist > self.MAX_TL_BARS:
                        continue

                    _slope = (p2 - p1) / _dist
                    _slope_norm = abs(_slope) / atr if atr > 0 else 0

                    if _slope_norm < self.MIN_SLOPE_ATR or _slope_norm > self.MAX_SLOPE_ATR:
                        continue

                    _intercept = p1 - _slope * idx1

                    # TL respect: 全バーのLowがTL±0.3ATRにタッチした回数
                    _respect = 0
                    for _bi in range(idx2 + 1, _df_len):
                        _tl_val = _slope * _bi + _intercept
                        if abs(lows_arr[_bi] - _tl_val) <= _tl_touch_zone:
                            _respect += 1

                    if _respect < self.MIN_TL_RESPECT:
                        continue

                    trendlines.append({
                        "type": "ascending",
                        "slope": _slope,
                        "intercept": _intercept,
                        "p1": p1, "p2": p2,
                        "idx1": idx1, "idx2": idx2,
                        "respect_count": _respect,
                    })

        # ── 下降TL: Swing High 2点 (Lower High) ──
        if len(swing_highs) >= 2:
            sorted_highs = sorted(swing_highs, key=lambda x: x[1])
            for i in range(len(sorted_highs) - 1):
                for j in range(i + 1, len(sorted_highs)):
                    p1, idx1 = sorted_highs[i]
                    p2, idx2 = sorted_highs[j]

                    if p2 >= p1:
                        continue

                    _dist = idx2 - idx1
                    if _dist < self.MIN_TL_BARS or _dist > self.MAX_TL_BARS:
                        continue

                    _slope = (p2 - p1) / _dist
                    _slope_norm = abs(_slope) / atr if atr > 0 else 0

                    if _slope_norm < self.MIN_SLOPE_ATR or _slope_norm > self.MAX_SLOPE_ATR:
                        continue

                    _intercept = p1 - _slope * idx1

                    # TL respect: 全バーのHighがTL±0.3ATRにタッチした回数
                    _respect = 0
                    for _bi in range(idx2 + 1, _df_len):
                        _tl_val = _slope * _bi + _intercept
                        if abs(highs_arr[_bi] - _tl_val) <= _tl_touch_zone:
                            _respect += 1

                    if _respect < self.MIN_TL_RESPECT:
                        continue

                    trendlines.append({
                        "type": "descending",
                        "slope": _slope,
                        "intercept": _intercept,
                        "p1": p1, "p2": p2,
                        "idx1": idx1, "idx2": idx2,
                        "respect_count": _respect,
                    })

        # respect_count降順でソート（最も信頼性の高いTL優先）
        trendlines.sort(key=lambda x: x["respect_count"], reverse=True)
        return trendlines

    # ══════════════════════════════════════════════════
    # Sweep + Reclaim
    # ══════════════════════════════════════════════════

    def _detect_sweep_reclaim(self, df, tl, atr):
        """TLに対するSweep + Reclaim を検出。

        Args:
            df: DataFrame
            tl: trendline dict
            atr: ATR(14)

        Returns:
            dict or None
        """
        _cur_idx = len(df) - 1
        _prev_idx = _cur_idx - 1
        _margin = atr * self.SWEEP_MARGIN_ATR
        _slope = tl["slope"]
        _intercept = tl["intercept"]

        cur_close = float(df["Close"].iloc[_cur_idx])
        cur_open = float(df["Open"].iloc[_cur_idx])
        cur_high = float(df["High"].iloc[_cur_idx])
        cur_low = float(df["Low"].iloc[_cur_idx])
        prev_close = float(df["Close"].iloc[_prev_idx])

        # 現在足のTL値
        _tl_cur = _slope * _cur_idx + _intercept
        _tl_prev = _slope * _prev_idx + _intercept

        # 実体/レンジ比（大陽線/大陰線確認）
        _bar_range = cur_high - cur_low
        _body = abs(cur_close - cur_open)
        _body_ratio = _body / _bar_range if _bar_range > 0 else 0

        if tl["type"] == "ascending":
            # 上昇TL sweep: 過去N本でLow < TL - margin
            _sweep_extreme = None
            _sweep_found = False

            for lb in range(1, self.SWEEP_LOOKBACK + 1):
                _idx = _cur_idx - lb
                if _idx < 0:
                    break
                _bar_l = float(df["Low"].iloc[_idx])
                _bar_h = float(df["High"].iloc[_idx])
                _tl_val = _slope * _idx + _intercept
                _br = _bar_h - _bar_l

                if _bar_l < _tl_val - _margin:
                    if atr > 0 and _br / atr >= self.VOL_RATIO_MIN:
                        if _sweep_extreme is None or _bar_l < _sweep_extreme:
                            _sweep_extreme = _bar_l
                            _sweep_found = True

            if not _sweep_found:
                return None

            # Reclaim: Close > TL (上方回帰) + prev Close < TL + 陽線
            if cur_close > _tl_cur and prev_close <= _tl_prev:
                if _body_ratio >= self.RECLAIM_BODY_RATIO and cur_close > cur_open:
                    return {
                        "signal": "BUY",
                        "sweep_extreme": _sweep_extreme,
                        "tl_value": _tl_cur,
                        "respect": tl["respect_count"],
                    }

        elif tl["type"] == "descending":
            # 下降TL sweep: 過去N本でHigh > TL + margin
            _sweep_extreme = None
            _sweep_found = False

            for lb in range(1, self.SWEEP_LOOKBACK + 1):
                _idx = _cur_idx - lb
                if _idx < 0:
                    break
                _bar_h = float(df["High"].iloc[_idx])
                _bar_l = float(df["Low"].iloc[_idx])
                _tl_val = _slope * _idx + _intercept
                _br = _bar_h - _bar_l

                if _bar_h > _tl_val + _margin:
                    if atr > 0 and _br / atr >= self.VOL_RATIO_MIN:
                        if _sweep_extreme is None or _bar_h > _sweep_extreme:
                            _sweep_extreme = _bar_h
                            _sweep_found = True

            if not _sweep_found:
                return None

            # Reclaim: Close < TL (下方回帰) + prev Close > TL + 陰線
            if cur_close < _tl_cur and prev_close >= _tl_prev:
                if _body_ratio >= self.RECLAIM_BODY_RATIO and cur_close < cur_open:
                    return {
                        "signal": "SELL",
                        "sweep_extreme": _sweep_extreme,
                        "tl_value": _tl_cur,
                        "respect": tl["respect_count"],
                    }

        return None

    # ══════════════════════════════════════════════════
    # メイン評価
    # ══════════════════════════════════════════════════

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = self._normalize_symbol(ctx.symbol)
        if _sym not in self.ALLOWED_PAIRS:
            return None

        # ── DataFrame十分性 ──
        _min_bars = self.FRACTAL_LOOKBACK + self.FRACTAL_N + 2
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        # ── 時間帯 ──
        if ctx.hour_utc < self.ACTIVE_HOURS_START or ctx.hour_utc >= self.ACTIVE_HOURS_END:
            return None
        if ctx.is_friday and ctx.hour_utc >= self.FRIDAY_BLOCK_HOUR:
            return None

        # ── ADX ──
        if ctx.adx < self.ADX_MIN or ctx.adx > self.ADX_MAX:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 1: Swing Point 検出 + TL構築
        # ═══════════════════════════════════════════════════
        _sh, _sl = self._find_swing_points(
            ctx.df, n=self.FRACTAL_N, lookback=self.FRACTAL_LOOKBACK
        )

        _lows_arr = ctx.df["Low"].values
        _highs_arr = ctx.df["High"].values
        trendlines = self._build_trendlines(
            _sh, _sl, ctx.atr, ctx.df, _lows_arr, _highs_arr
        )
        if not trendlines:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2 & 3: 各TLに対してSweep + Reclaim検出
        # ═══════════════════════════════════════════════════
        _best = None
        _best_respect = 0

        for tl in trendlines[:5]:  # 上位5TLのみ評価（計算量制限）
            result = self._detect_sweep_reclaim(ctx.df, tl, ctx.atr)
            if result and result["respect"] > _best_respect:
                _best = result
                _best_respect = result["respect"]

        if _best is None:
            return None

        # ── SELL-only フィルター ──
        if _sym in self.SELL_ONLY_PAIRS and _best["signal"] == "BUY":
            return None

        # ═══════════════════════════════════════════════════
        # STEP 4: SL/TP
        # ═══════════════════════════════════════════════════
        signal = _best["signal"]
        _extreme = _best["sweep_extreme"]
        _respect = _best["respect"]
        _is_buy = signal == "BUY"

        # SL
        if _is_buy:
            sl = _extreme - ctx.atr * self.SL_ATR_BUFFER
        else:
            sl = _extreme + ctx.atr * self.SL_ATR_BUFFER

        # TP: ATRベース
        tp = ctx.entry + ctx.atr * self.TP_ATR_MULT * (1 if _is_buy else -1)

        # RR
        _sl_dist = abs(ctx.entry - sl)
        _tp_dist = abs(tp - ctx.entry)
        if _sl_dist <= 0:
            return None

        if _tp_dist / _sl_dist < self.MIN_RR:
            _tp_dist = _sl_dist * self.MIN_RR
            tp = ctx.entry + _tp_dist if _is_buy else ctx.entry - _tp_dist

        _rr = _tp_dist / _sl_dist

        # SL方向チェック
        if _is_buy and sl >= ctx.entry:
            return None
        if not _is_buy and sl <= ctx.entry:
            return None

        # ═══════════════════════════════════════════════════
        # スコア
        # ═══════════════════════════════════════════════════
        _score = 5.0
        if _respect >= 3:
            _score += 2.0
        elif _respect >= 2:
            _score += 1.0
        if _rr >= 2.5:
            _score += 1.0
        if 18 <= ctx.adx <= 30:
            _score += 0.5

        _reasons = [
            f"TL Sweep Trap: {signal} — TL respect={_respect}",
            f"Sweep extreme={_extreme:.5f}, reclaim to TL confirmed",
            f"RR={_rr:.1f}, ADX={ctx.adx:.1f}",
        ]

        return Candidate(
            signal=signal,
            confidence=min(85, 50 + _respect * 8 + int(_rr * 5)),
            sl=round(sl, 5 if not ctx.is_jpy else 3),
            tp=round(tp, 5 if not ctx.is_jpy else 3),
            reasons=_reasons,
            entry_type=self.name,
            score=_score,
        )
