"""
Inducement & Order Block Trap — SMCの極致

学術的根拠:
  - Kyle (1985): Informed traders absorb liquidity at specific price zones
  - Easley & O'Hara (2004): Order flow toxicity and institutional footprint
  - Osler (2003): Retail stop clustering at minor S/R levels
  - Gabaix et al. (2006): Institutional block trades create price dislocations

戦略コンセプト:
  大口が建玉を集中させた価格帯（Order Block = OB）は、
  再度価格が到達した際に強力な需給反転ポイントとなる。
  個人投資家は OB手前のマイナーなスイング（Inducement）を
  本物のSRと誤認しストップを設置する。価格がInducementを
  ブレイクし個人のストップを狩った後、OBゾーンで反発する。

Order Block 検出:
  ■ Bullish OB:
    陰線(Close < Open)の直後に、IMPULSE_MIN_BARS本以上の連続陽線が続き、
    合計range ≥ ATR × IMPULSE_ATR_MULT。
    その陰線のレンジ = Bullish OB ゾーン。

  ■ Bearish OB:
    陽線の直後にN本連続陰線のインパルス。
    その陽線 = Bearish OBゾーン。

Inducement:
  OB形成後の戻り局面で生まれたマイナー・スイング（Williams Fractal n=2）。
  個人がSRと誤認 → ストップ集中帯。

エントリー:
  1. 価格がInducementをブレイク（ストップ狩り）
  2. 価格がOBゾーンに到達（margin以内）
  3. 反転足（body_ratio >= 30%, OB方向へのClose確認）

SL: OBゾーン反対端 ± ATR × SL_ATR_BUFFER
TP: インパルスの50%戻し or ATR × TP_ATR_MULT
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class InducementOrderBlock(StrategyBase):
    name = "inducement_ob"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ
    # ══════════════════════════════════════════════════

    # ── Order Block 検出 ──
    IMPULSE_MIN_BARS = 3        # インパルス: 最低3本の連続同方向バー
    IMPULSE_ATR_MULT = 2.0      # インパルス合計range ≥ ATR × 2.0
    OB_LOOKBACK = 60            # OB検索: 過去60本 (15m × 60 = 15H ≈ 1営業日)
    OB_MAX_WIDTH_ATR = 2.0      # OBキャンドルのrange上限 (ATR × 2.0)
    OB_FRESHNESS = 50           # OB有効期限: 形成から50本以内

    # ── Inducement ──
    INDUCEMENT_FRACTAL_N = 2    # マイナーSwing: 両側2本 (5バー窓)
    MIN_INDUCEMENTS = 1         # 最低1個のInducementが必要

    # ── エントリー ──
    OB_TOUCH_MARGIN = 0.5       # OBゾーンへの近接判定: ATR × 0.5
    REVERSAL_BODY_RATIO = 0.30  # 反転足の実体/レンジ ≥ 30%
    SWEEP_MARGIN_ATR = 0.05     # Inducement sweep: margin ATR × 0.05

    # ── ADX ──
    ADX_MIN = 12
    ADX_MAX = 45

    # ── SL/TP ──
    SL_ATR_BUFFER = 0.3
    TP_ATR_MULT = 2.5
    MIN_RR = 1.5

    # ── 時間帯 ──
    ACTIVE_HOURS_START = 6
    ACTIVE_HOURS_END = 20
    FRIDAY_BLOCK_HOUR = 16

    # ── ペアフィルター ──
    ALLOWED_PAIRS = {
        "USDJPY", "EURUSD", "GBPUSD", "EURGBP", "XAUUSD",
    }
    # USD/JPY: SELL WR=49% → BUY-only
    BUY_ONLY_PAIRS = {"USDJPY"}
    # EUR/USD: BUY WR=45% → SELL-only
    SELL_ONLY_PAIRS = {"EURUSD"}

    def _normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().replace("=X", "").replace("=F", "").replace("/", "").replace("_", "")
        if s in ("GC", "GCF"):
            return "XAUUSD"
        return s

    # ══════════════════════════════════════════════════
    # Order Block 検出
    # ══════════════════════════════════════════════════

    def _find_order_blocks(self, df, atr, cur_idx):
        """過去のインパルスを走査し、Order Block を検出。

        Returns:
            list of dict: {type, ob_high, ob_low, ob_idx,
                           impulse_end_idx, impulse_peak}
        """
        highs = df["High"].values
        lows = df["Low"].values
        opens = df["Open"].values
        closes = df["Close"].values

        obs = []
        _start = max(0, cur_idx - self.OB_LOOKBACK)

        for i in range(_start, cur_idx - self.IMPULSE_MIN_BARS):
            # OBの鮮度チェック
            if cur_idx - i > self.OB_FRESHNESS:
                continue

            ob_open = opens[i]
            ob_close = closes[i]
            ob_high = highs[i]
            ob_low = lows[i]
            ob_range = ob_high - ob_low

            # OBキャンドルのサイズ制限
            if atr > 0 and ob_range > atr * self.OB_MAX_WIDTH_ATR:
                continue

            # ── Bullish OB: 陰線 + 後続bullishインパルス ──
            if ob_close < ob_open:
                _impulse_total = 0
                _impulse_bars = 0
                _impulse_peak = ob_high

                for j in range(i + 1, min(i + 1 + self.IMPULSE_MIN_BARS + 4, cur_idx)):
                    if closes[j] > opens[j]:  # bullish bar
                        _impulse_total += highs[j] - lows[j]
                        _impulse_bars += 1
                        _impulse_peak = max(_impulse_peak, highs[j])
                    else:
                        break  # 連続性途切れ

                if (_impulse_bars >= self.IMPULSE_MIN_BARS and
                        atr > 0 and _impulse_total >= atr * self.IMPULSE_ATR_MULT):
                    obs.append({
                        "type": "bullish",
                        "ob_high": float(ob_high),
                        "ob_low": float(ob_low),
                        "ob_idx": i,
                        "impulse_end_idx": i + _impulse_bars,
                        "impulse_peak": float(_impulse_peak),
                    })

            # ── Bearish OB: 陽線 + 後続bearishインパルス ──
            elif ob_close > ob_open:
                _impulse_total = 0
                _impulse_bars = 0
                _impulse_trough = ob_low

                for j in range(i + 1, min(i + 1 + self.IMPULSE_MIN_BARS + 4, cur_idx)):
                    if closes[j] < opens[j]:  # bearish bar
                        _impulse_total += highs[j] - lows[j]
                        _impulse_bars += 1
                        _impulse_trough = min(_impulse_trough, lows[j])
                    else:
                        break

                if (_impulse_bars >= self.IMPULSE_MIN_BARS and
                        atr > 0 and _impulse_total >= atr * self.IMPULSE_ATR_MULT):
                    obs.append({
                        "type": "bearish",
                        "ob_high": float(ob_high),
                        "ob_low": float(ob_low),
                        "ob_idx": i,
                        "impulse_end_idx": i + _impulse_bars,
                        "impulse_trough": float(_impulse_trough),
                    })

        # 最新のOBを優先（鮮度順）
        obs.sort(key=lambda x: x["ob_idx"], reverse=True)
        return obs

    # ══════════════════════════════════════════════════
    # Inducement 検出
    # ══════════════════════════════════════════════════

    def _find_inducements(self, df, ob, cur_idx):
        """OB形成後の戻りで生まれたマイナー・スイングを検出。

        Bullish OB → 戻りのSwing Low (Inducement: 個人がサポートと誤認)
        Bearish OB → 戻りのSwing High (Inducement: 個人がレジスタンスと誤認)

        Returns:
            list of (price, index)
        """
        highs = df["High"].values
        lows = df["Low"].values
        n = self.INDUCEMENT_FRACTAL_N
        inducements = []

        _start = ob["impulse_end_idx"] + 1
        _end = cur_idx - n

        if _start >= _end:
            return []

        for i in range(max(_start, n), _end):
            if ob["type"] == "bullish":
                # マイナーSwing Low = Inducement for bullish OB
                _l = lows[i]
                if (all(_l < lows[j] for j in range(i - n, i)) and
                        all(_l < lows[j] for j in range(i + 1, i + n + 1))):
                    inducements.append((float(_l), i))

            elif ob["type"] == "bearish":
                # マイナーSwing High = Inducement for bearish OB
                _h = highs[i]
                if (all(_h > highs[j] for j in range(i - n, i)) and
                        all(_h > highs[j] for j in range(i + 1, i + n + 1))):
                    inducements.append((float(_h), i))

        return inducements

    # ══════════════════════════════════════════════════
    # Sweep + OB到達 + 反転 検出
    # ══════════════════════════════════════════════════

    def _check_entry(self, df, ob, inducements, atr, cur_idx):
        """エントリー条件をチェック。

        1. 最近のバーでInducementをsweep
        2. 価格がOBゾーンに到達
        3. 現在足が反転足

        Returns:
            dict or None: {signal, sweep_level, ob_zone}
        """
        cur_close = float(df["Close"].iloc[cur_idx])
        cur_open = float(df["Open"].iloc[cur_idx])
        cur_high = float(df["High"].iloc[cur_idx])
        cur_low = float(df["Low"].iloc[cur_idx])
        prev_close = float(df["Close"].iloc[cur_idx - 1])
        _bar_range = cur_high - cur_low
        _body = abs(cur_close - cur_open)
        _body_ratio = _body / _bar_range if _bar_range > 0 else 0
        _margin = atr * self.OB_TOUCH_MARGIN
        _sweep_margin = atr * self.SWEEP_MARGIN_ATR

        if ob["type"] == "bullish":
            # ── Bullish OB: 価格が下落してOBに到達 → BUY ──

            # 1. Inducement sweep: 最近6本でSwing Lowを下抜け
            _swept = False
            for ind_price, ind_idx in inducements:
                for lb in range(1, 7):
                    _bi = cur_idx - lb
                    if _bi < 0:
                        break
                    if float(df["Low"].iloc[_bi]) < ind_price - _sweep_margin:
                        _swept = True
                        break
                if _swept:
                    break

            if not _swept:
                return None

            # 2. OBゾーン到達: 現在足のLowがOB high + margin以下
            if cur_low > ob["ob_high"] + _margin:
                return None

            # 3. 反転足: 陽線 + body_ratio確認 + Close > OB_high
            if cur_close <= cur_open:
                return None
            if _body_ratio < self.REVERSAL_BODY_RATIO:
                return None
            # Close はOB上端以上（OB内で反発完了）
            if cur_close < ob["ob_low"]:
                return None
            # 前足はOBゾーン内 or 下方（fresh touch確認）
            if prev_close > ob["ob_high"] + _margin:
                return None

            return {
                "signal": "BUY",
                "ob": ob,
                "sweep_level": inducements[0][0] if inducements else 0,
            }

        elif ob["type"] == "bearish":
            # ── Bearish OB: 価格が上昇してOBに到達 → SELL ──

            _swept = False
            for ind_price, ind_idx in inducements:
                for lb in range(1, 7):
                    _bi = cur_idx - lb
                    if _bi < 0:
                        break
                    if float(df["High"].iloc[_bi]) > ind_price + _sweep_margin:
                        _swept = True
                        break
                if _swept:
                    break

            if not _swept:
                return None

            # OBゾーン到達: 現在足のHighがOB low - margin以上
            if cur_high < ob["ob_low"] - _margin:
                return None

            # 反転足: 陰線 + body_ratio確認
            if cur_close >= cur_open:
                return None
            if _body_ratio < self.REVERSAL_BODY_RATIO:
                return None
            if cur_close > ob["ob_high"]:
                return None
            if prev_close < ob["ob_low"] - _margin:
                return None

            return {
                "signal": "SELL",
                "ob": ob,
                "sweep_level": inducements[0][0] if inducements else 0,
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
        _min_bars = self.OB_LOOKBACK + self.IMPULSE_MIN_BARS + 10
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

        cur_idx = len(ctx.df) - 1

        # ═══════════════════════════════════════════════════
        # STEP 1: Order Block 検出
        # ═══════════════════════════════════════════════════
        order_blocks = self._find_order_blocks(ctx.df, ctx.atr, cur_idx)
        if not order_blocks:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2 & 3: 各OBに対してInducement + Entry検出
        # ═══════════════════════════════════════════════════
        _best = None
        _best_ob = None

        for ob in order_blocks[:5]:  # 上位5 OBのみ評価
            inducements = self._find_inducements(ctx.df, ob, cur_idx)
            if len(inducements) < self.MIN_INDUCEMENTS:
                continue

            result = self._check_entry(ctx.df, ob, inducements, ctx.atr, cur_idx)
            if result:
                _best = result
                _best_ob = ob
                break  # 最新のOBを優先

        if _best is None:
            return None

        # ── 方向フィルター ──
        if _sym in self.BUY_ONLY_PAIRS and _best["signal"] == "SELL":
            return None
        if _sym in self.SELL_ONLY_PAIRS and _best["signal"] == "BUY":
            return None

        # ═══════════════════════════════════════════════════
        # STEP 4: SL/TP
        # ═══════════════════════════════════════════════════
        signal = _best["signal"]
        ob = _best["ob"]
        _is_buy = signal == "BUY"

        # SL: OBゾーンの反対端 ± ATR × buffer
        if _is_buy:
            sl = ob["ob_low"] - ctx.atr * self.SL_ATR_BUFFER
        else:
            sl = ob["ob_high"] + ctx.atr * self.SL_ATR_BUFFER

        # TP: インパルスの50%戻し or ATR × TP_ATR_MULT
        if _is_buy:
            _impulse_peak = ob.get("impulse_peak", ctx.entry + ctx.atr * self.TP_ATR_MULT)
            _tp_impulse = ob["ob_low"] + (_impulse_peak - ob["ob_low"]) * 0.5
            _tp_atr = ctx.entry + ctx.atr * self.TP_ATR_MULT
            tp = max(_tp_impulse, _tp_atr)
        else:
            _impulse_trough = ob.get("impulse_trough", ctx.entry - ctx.atr * self.TP_ATR_MULT)
            _tp_impulse = ob["ob_high"] - (ob["ob_high"] - _impulse_trough) * 0.5
            _tp_atr = ctx.entry - ctx.atr * self.TP_ATR_MULT
            tp = min(_tp_impulse, _tp_atr)

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
        # OBの鮮度ボーナス
        _freshness = cur_idx - ob["ob_idx"]
        if _freshness <= 20:
            _score += 1.5
        elif _freshness <= 35:
            _score += 0.5
        # RRボーナス
        if _rr >= 2.5:
            _score += 1.0
        # ADXスイートスポット
        if 18 <= ctx.adx <= 30:
            _score += 0.5

        _reasons = [
            f"✅ OB Trap: {signal} — {ob['type']} OB (age={_freshness})",
            f"✅ Inducement swept, OB zone [{ob['ob_low']:.5f}-{ob['ob_high']:.5f}]",
            f"RR={_rr:.1f}, ADX={ctx.adx:.1f}",
        ]

        return Candidate(
            signal=signal,
            confidence=min(85, 50 + int(_rr * 5) + max(0, 20 - _freshness)),
            sl=round(sl, 5 if not ctx.is_jpy else 3),
            tp=round(tp, 5 if not ctx.is_jpy else 3),
            reasons=_reasons,
            entry_type=self.name,
            score=_score,
        )
