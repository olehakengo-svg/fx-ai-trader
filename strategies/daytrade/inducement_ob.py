"""
Inducement & Order Block Trap v2 — Liquidity Grab確認型

v1 → v2 改修要点 (2026-04-07):
  WR=11% → 構造的欠陥の排除
  ① Liquidity Grab フィルター: 20本H/L sweep + 次足reclaim必須
  ② HTF OB同期: 1H足OBゾーン内に価格が存在しない場合はブロック
  ③ SL圧縮: OB境界+スプレッド固定 (ATR×0.3 → 2pips以内)
  ④ Volume proxy: sweep足の bar_range ≥ ATR×1.5 (大口関与証拠)

学術的根拠:
  - Kyle (1985): Informed traders absorb liquidity at specific price zones
  - Easley & O'Hara (2004): Order flow toxicity and institutional footprint
  - Osler (2003): Retail stop clustering at minor S/R levels
  - Gabaix et al. (2006): Institutional block trades create price dislocations

戦略コンセプト v2:
  「誘いに引っかかる側」から「大口と共に誘う側」へ。
  1. 直近20本の最高値/最安値を「ヒゲ」で更新 (Liquidity Sweep)
  2. 次の足で始値を逆方向にブレイク (Reclaim = 大口の仕掛け確認)
  3. 1H足OBゾーン内に価格が存在 (HTF構造との整合)
  4. sweep足のbar_range ≥ ATR×1.5 (出来高プロキシ = 大口関与)
  → SLはOB境界ギリギリ + 1-2pip固定。負けを最小化し、1:10爆発を待つ設計。
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
    # パラメータ v2
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

    # ── Liquidity Grab (v2 新規) ──
    LIQ_LOOKBACK = 20           # 直近20本のH/Lを参照
    LIQ_VOL_RATIO = 1.5         # sweep足の bar_range/ATR ≥ 1.5 (大口関与プロキシ)

    # ── HTF OB Constraint (v2 新規) ──
    HTF_OB_LOOKBACK = 80        # 1H OB検出: 過去80本 (1Hリサンプル)
    HTF_OB_IMPULSE_BARS = 2     # 1Hインパルス: 最低2本
    HTF_OB_IMPULSE_ATR = 1.5    # 1H ATR × 1.5

    # ── エントリー ──
    OB_TOUCH_MARGIN = 0.3       # OBゾーンへの近接判定: ATR × 0.3 (v1: 0.5)
    REVERSAL_BODY_RATIO = 0.35  # 反転足の実体/レンジ ≥ 35% (v1: 0.30)
    SWEEP_MARGIN_ATR = 0.05     # Inducement sweep: margin ATR × 0.05

    # ── ADX ──
    ADX_MIN = 12
    ADX_MAX = 40                # v1: 45 → 40 (強トレンドは逆張り危険)

    # ── SL/TP v2: 超タイトSL ──
    SL_FIXED_PIPS = 2.0         # OB境界 + 固定2pips (v1: ATR×0.3 ≈ 3-5pips)
    TP_ATR_MULT = 3.5           # TP拡大 (v1: 2.5 → 3.5) — 爆発待ち設計
    MIN_RR = 2.0                # 最低RR (v1: 1.5 → 2.0)

    # ── 時間帯 ──
    ACTIVE_HOURS_START = 7      # v1: 6 → 7 (London前の薄商いを除外)
    ACTIVE_HOURS_END = 20
    FRIDAY_BLOCK_HOUR = 15      # v1: 16 → 15 (金曜は早めに停止)

    # ── ペアフィルター ──
    ALLOWED_PAIRS = {
        "USDJPY", "EURUSD", "GBPUSD", "EURGBP", "XAUUSD",
    }
    BUY_ONLY_PAIRS = {"USDJPY"}
    SELL_ONLY_PAIRS = {"EURUSD"}

    def _normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().replace("=X", "").replace("=F", "").replace("/", "").replace("_", "")
        if s in ("GC", "GCF"):
            return "XAUUSD"
        return s

    # ══════════════════════════════════════════════════
    # Order Block 検出 (v1と同一)
    # ══════════════════════════════════════════════════

    def _find_order_blocks(self, df, atr, cur_idx):
        """過去のインパルスを走査し、Order Block を検出。"""
        highs = df["High"].values
        lows = df["Low"].values
        opens = df["Open"].values
        closes = df["Close"].values

        obs = []
        _start = max(0, cur_idx - self.OB_LOOKBACK)

        for i in range(_start, cur_idx - self.IMPULSE_MIN_BARS):
            if cur_idx - i > self.OB_FRESHNESS:
                continue

            ob_open = opens[i]
            ob_close = closes[i]
            ob_high = highs[i]
            ob_low = lows[i]
            ob_range = ob_high - ob_low

            if atr > 0 and ob_range > atr * self.OB_MAX_WIDTH_ATR:
                continue

            # ── Bullish OB: 陰線 + 後続bullishインパルス ──
            if ob_close < ob_open:
                _impulse_total = 0
                _impulse_bars = 0
                _impulse_peak = ob_high

                for j in range(i + 1, min(i + 1 + self.IMPULSE_MIN_BARS + 4, cur_idx)):
                    if closes[j] > opens[j]:
                        _impulse_total += highs[j] - lows[j]
                        _impulse_bars += 1
                        _impulse_peak = max(_impulse_peak, highs[j])
                    else:
                        break

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
                    if closes[j] < opens[j]:
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

        obs.sort(key=lambda x: x["ob_idx"], reverse=True)
        return obs

    # ══════════════════════════════════════════════════
    # Inducement 検出 (v1と同一)
    # ══════════════════════════════════════════════════

    def _find_inducements(self, df, ob, cur_idx):
        """OB形成後の戻りで生まれたマイナー・スイングを検出。"""
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
                _l = lows[i]
                if (all(_l < lows[j] for j in range(i - n, i)) and
                        all(_l < lows[j] for j in range(i + 1, i + n + 1))):
                    inducements.append((float(_l), i))
            elif ob["type"] == "bearish":
                _h = highs[i]
                if (all(_h > highs[j] for j in range(i - n, i)) and
                        all(_h > highs[j] for j in range(i + 1, i + n + 1))):
                    inducements.append((float(_h), i))

        return inducements

    # ══════════════════════════════════════════════════
    # [v2 NEW] Liquidity Grab 検出
    # ══════════════════════════════════════════════════

    def _check_liquidity_grab(self, df, atr, cur_idx, direction):
        """直近20本のH/Lを「ヒゲ」でsweepし、次足でreclaimしたか。

        BUY: 直近20本の最安値をヒゲで更新 → 次足のCloseが更新足のOpenより上
        SELL: 直近20本の最高値をヒゲで更新 → 次足のCloseが更新足のOpenより下

        Returns:
            dict or None: {sweep_bar_idx, sweep_extreme, bar_range_ratio}
        """
        if cur_idx < self.LIQ_LOOKBACK + 2:
            return None

        highs = df["High"].values
        lows = df["Low"].values
        opens = df["Open"].values
        closes = df["Close"].values

        # 現在足 = reclaim足、前足 = sweep足
        sweep_idx = cur_idx - 1
        reclaim_idx = cur_idx

        sweep_high = highs[sweep_idx]
        sweep_low = lows[sweep_idx]
        sweep_open = opens[sweep_idx]
        sweep_range = sweep_high - sweep_low

        reclaim_close = closes[reclaim_idx]
        reclaim_open = opens[reclaim_idx]

        # sweep足のbar_range/ATR ≥ LIQ_VOL_RATIO (大口関与プロキシ)
        if atr <= 0:
            return None
        bar_range_ratio = sweep_range / atr
        if bar_range_ratio < self.LIQ_VOL_RATIO:
            return None

        # 参照区間: sweep足の前LIQ_LOOKBACK本
        ref_start = max(0, sweep_idx - self.LIQ_LOOKBACK)
        ref_end = sweep_idx

        if direction == "BUY":
            # 直近20本の最安値を sweep足のヒゲで更新
            ref_low = float(np.min(lows[ref_start:ref_end]))
            if sweep_low >= ref_low:
                return None  # 最安値を更新していない

            # reclaim: 次足(現在足)のCloseがsweep足のOpenより上
            if reclaim_close <= sweep_open:
                return None

            # 反転足確認: 現在足が陽線
            if reclaim_close <= reclaim_open:
                return None

            return {
                "sweep_bar_idx": sweep_idx,
                "sweep_extreme": float(sweep_low),
                "ref_extreme": ref_low,
                "bar_range_ratio": round(bar_range_ratio, 2),
            }

        elif direction == "SELL":
            ref_high = float(np.max(highs[ref_start:ref_end]))
            if sweep_high <= ref_high:
                return None

            if reclaim_close >= sweep_open:
                return None

            if reclaim_close >= reclaim_open:
                return None

            return {
                "sweep_bar_idx": sweep_idx,
                "sweep_extreme": float(sweep_high),
                "ref_extreme": ref_high,
                "bar_range_ratio": round(bar_range_ratio, 2),
            }

        return None

    # ══════════════════════════════════════════════════
    # [v2 NEW] HTF OB Constraint
    # ══════════════════════════════════════════════════

    def _check_htf_ob_zone(self, df, atr, cur_idx, direction):
        """15m足データを4本ずつリサンプルして疑似1H OBを検出。
        現在価格が1H OBゾーン内に存在するかチェック。

        Returns:
            dict or None: {htf_ob_high, htf_ob_low}
        """
        if cur_idx < self.HTF_OB_LOOKBACK * 4:
            return None

        highs = df["High"].values
        lows = df["Low"].values
        opens = df["Open"].values
        closes = df["Close"].values

        # 4本ずつまとめて疑似1Hバーを構築
        htf_bars = []
        _end = cur_idx
        _step = 4  # 15m × 4 = 1H
        for i in range(max(0, _end - self.HTF_OB_LOOKBACK * _step), _end, _step):
            _slice_end = min(i + _step, _end)
            if _slice_end <= i:
                continue
            h_o = opens[i]
            h_c = closes[_slice_end - 1]
            h_h = float(np.max(highs[i:_slice_end]))
            h_l = float(np.min(lows[i:_slice_end]))
            htf_bars.append({"o": h_o, "c": h_c, "h": h_h, "l": h_l})

        if len(htf_bars) < 10:
            return None

        cur_price = float(closes[cur_idx])
        htf_atr = atr * 2.0  # 1H ATR ≈ 15m ATR × 2

        # HTF OB検出
        for i in range(len(htf_bars) - self.HTF_OB_IMPULSE_BARS - 1):
            ob_bar = htf_bars[i]
            ob_h, ob_l = ob_bar["h"], ob_bar["l"]
            ob_o, ob_c = ob_bar["o"], ob_bar["c"]

            if direction == "BUY" and ob_c < ob_o:
                # Bullish 1H OB: 陰線 + 後続bullishインパルス
                imp_total = 0
                imp_bars = 0
                for j in range(i + 1, min(i + 1 + self.HTF_OB_IMPULSE_BARS + 2, len(htf_bars))):
                    if htf_bars[j]["c"] > htf_bars[j]["o"]:
                        imp_total += htf_bars[j]["h"] - htf_bars[j]["l"]
                        imp_bars += 1
                    else:
                        break
                if (imp_bars >= self.HTF_OB_IMPULSE_BARS and
                        htf_atr > 0 and imp_total >= htf_atr * self.HTF_OB_IMPULSE_ATR):
                    # 現在価格がOBゾーン付近(+margin)にあるか
                    _m = htf_atr * 0.5
                    if ob_l - _m <= cur_price <= ob_h + _m:
                        return {"htf_ob_high": ob_h, "htf_ob_low": ob_l}

            elif direction == "SELL" and ob_c > ob_o:
                imp_total = 0
                imp_bars = 0
                for j in range(i + 1, min(i + 1 + self.HTF_OB_IMPULSE_BARS + 2, len(htf_bars))):
                    if htf_bars[j]["c"] < htf_bars[j]["o"]:
                        imp_total += htf_bars[j]["h"] - htf_bars[j]["l"]
                        imp_bars += 1
                    else:
                        break
                if (imp_bars >= self.HTF_OB_IMPULSE_BARS and
                        htf_atr > 0 and imp_total >= htf_atr * self.HTF_OB_IMPULSE_ATR):
                    _m = htf_atr * 0.5
                    if ob_l - _m <= cur_price <= ob_h + _m:
                        return {"htf_ob_high": ob_h, "htf_ob_low": ob_l}

        return None

    # ══════════════════════════════════════════════════
    # Sweep + OB到達 + 反転 検出 (v2: Liq Grab統合)
    # ══════════════════════════════════════════════════

    def _check_entry(self, df, ob, inducements, atr, cur_idx):
        """エントリー条件 v2:
        1. Inducement sweep (v1)
        2. OBゾーン到達 (v1, margin圧縮)
        3. 反転足 (v1, body_ratio引き上げ)

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
            # 1. Inducement sweep
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

            # 2. OBゾーン到達
            if cur_low > ob["ob_high"] + _margin:
                return None

            # 3. 反転足: 陽線 + body_ratio + Close ≥ OB_low
            if cur_close <= cur_open:
                return None
            if _body_ratio < self.REVERSAL_BODY_RATIO:
                return None
            if cur_close < ob["ob_low"]:
                return None
            if prev_close > ob["ob_high"] + _margin:
                return None

            return {
                "signal": "BUY",
                "ob": ob,
                "sweep_level": inducements[0][0] if inducements else 0,
            }

        elif ob["type"] == "bearish":
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

            if cur_high < ob["ob_low"] - _margin:
                return None

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
    # メイン評価 v2
    # ══════════════════════════════════════════════════

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = self._normalize_symbol(ctx.symbol)
        if _sym not in self.ALLOWED_PAIRS:
            return None

        # ── DataFrame十分性 ──
        _min_bars = max(self.OB_LOOKBACK, self.HTF_OB_LOOKBACK * 4) + 20
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

        # ── ATR NaN guard (起動直後にインジケータ未計算の場合) ──
        import numpy as np
        if ctx.atr is None or np.isnan(ctx.atr) or ctx.atr <= 0:
            return None

        cur_idx = len(ctx.df) - 1

        # ═══════════════════════════════════════════════════
        # STEP 1: Order Block 検出
        # ═══════════════════════════════════════════════════
        order_blocks = self._find_order_blocks(ctx.df, ctx.atr, cur_idx)
        if not order_blocks:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2: 各OBに対してInducement + Entry検出
        # ═══════════════════════════════════════════════════
        _best = None
        _best_ob = None

        for ob in order_blocks[:5]:
            inducements = self._find_inducements(ctx.df, ob, cur_idx)
            if len(inducements) < self.MIN_INDUCEMENTS:
                continue

            result = self._check_entry(ctx.df, ob, inducements, ctx.atr, cur_idx)
            if result:
                _best = result
                _best_ob = ob
                break

        if _best is None:
            return None

        signal = _best["signal"]

        # ── 方向フィルター ──
        if _sym in self.BUY_ONLY_PAIRS and signal == "SELL":
            return None
        if _sym in self.SELL_ONLY_PAIRS and signal == "BUY":
            return None

        # ═══════════════════════════════════════════════════
        # STEP 3 [v2]: Liquidity Grab 確認
        # 直近20本H/Lのsweep + 次足reclaim + volume proxy
        # ═══════════════════════════════════════════════════
        liq_grab = self._check_liquidity_grab(ctx.df, ctx.atr, cur_idx, signal)
        if liq_grab is None:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 4 [v2]: HTF OB ゾーン整合
        # 1H足OBゾーン内に価格がなければブロック
        # ═══════════════════════════════════════════════════
        htf_ob = self._check_htf_ob_zone(ctx.df, ctx.atr, cur_idx, signal)
        if htf_ob is None:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 5 [v2]: 超タイトSL + 拡大TP
        # ═══════════════════════════════════════════════════
        ob = _best["ob"]
        _is_buy = signal == "BUY"

        # pip値
        _is_jpy_xau = ctx.is_jpy or "XAU" in ctx.symbol.upper()
        _pip_unit = 0.01 if _is_jpy_xau else 0.0001

        # SL: OB境界 + 固定SL_FIXED_PIPS (v2: 超タイト)
        if _is_buy:
            sl = ob["ob_low"] - self.SL_FIXED_PIPS * _pip_unit
        else:
            sl = ob["ob_high"] + self.SL_FIXED_PIPS * _pip_unit

        # TP: インパルスピーク/トラフ or ATR × TP_ATR_MULT (v2: 拡大)
        if _is_buy:
            _impulse_peak = ob.get("impulse_peak", ctx.entry + ctx.atr * self.TP_ATR_MULT)
            _tp_impulse = ob["ob_low"] + (_impulse_peak - ob["ob_low"]) * 0.6
            _tp_atr = ctx.entry + ctx.atr * self.TP_ATR_MULT
            tp = max(_tp_impulse, _tp_atr)
        else:
            _impulse_trough = ob.get("impulse_trough", ctx.entry - ctx.atr * self.TP_ATR_MULT)
            _tp_impulse = ob["ob_high"] - (ob["ob_high"] - _impulse_trough) * 0.6
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
        # スコア v2
        # ═══════════════════════════════════════════════════
        _score = 6.0  # v1: 5.0 → 6.0 (フィルター強化でベーススコア引上げ)

        # OBの鮮度ボーナス
        _freshness = cur_idx - ob["ob_idx"]
        if _freshness <= 15:
            _score += 2.0
        elif _freshness <= 30:
            _score += 1.0

        # RRボーナス
        if _rr >= 4.0:
            _score += 2.0
        elif _rr >= 3.0:
            _score += 1.0

        # Volume proxy ボーナス
        if liq_grab["bar_range_ratio"] >= 2.0:
            _score += 1.0

        # ADXスイートスポット
        if 15 <= ctx.adx <= 28:
            _score += 0.5

        _reasons = [
            f"✅ OB Trap v2: {signal} — {ob['type']} OB (age={_freshness})",
            f"✅ Liq Grab: 20bar sweep confirmed (vol_ratio={liq_grab['bar_range_ratio']}×ATR)",
            f"✅ HTF OB: 1H zone [{htf_ob['htf_ob_low']:.5f}-{htf_ob['htf_ob_high']:.5f}]",
            f"RR={_rr:.1f}, ADX={ctx.adx:.1f}, SL={_sl_dist/_pip_unit:.1f}pip",
        ]

        return Candidate(
            signal=signal,
            confidence=min(90, 55 + int(_rr * 4) + max(0, 20 - _freshness)),
            sl=round(sl, 5 if not ctx.is_jpy else 3),
            tp=round(tp, 5 if not ctx.is_jpy else 3),
            reasons=_reasons,
            entry_type=self.name,
            score=_score,
        )
