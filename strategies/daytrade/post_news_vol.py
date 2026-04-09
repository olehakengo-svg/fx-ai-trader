"""
Post-News Volatility Run — 指標後の流動性空白狙い

学術的根拠:
  - Ederington & Lee (1993): News releases create abnormal volatility clusters
  - Engle (1982): ARCH effect — volatility clustering post-event
  - Biais et al. (2005): Liquidity vacuum after institutional sweep
  - Andersen et al. (2003): High-frequency price discovery post-news

戦略コンセプト:
  重要経済指標発表時、大口は上下両方のストップを狩る「ウィップソー」を
  仕掛ける。この激しい上下動でリテールの大半がストップアウトした後、
  流動性の真空地帯が形成される。その後、価格は異常足の実体方向へ
  「走り続ける」傾向がある（流動性のない方向への一方的な動き）。

異常足検出:
  ■ True Range ≥ ATR(20) × SPIKE_MULT (3.0)
  ■ 上下ヒゲ合計 ≥ range × WICK_RATIO_MIN (0.30)
    → 激しい上下動 = ストップ狩り完了の証拠
  ■ または: body_ratio ≥ BODY_RATIO_ALT (0.70) かつ TR ≥ ATR × 2.5
    → 一方向の強烈なモメンタム（ヒゲなし大陽線/大陰線）

エントリー:
  1. 異常足確定後、COOLDOWN_BARS (1-2本) 待機
  2. フォロー足の Close が異常足の実体方向と一致
  3. フォロー足の body_ratio ≥ FOLLOW_BODY_RATIO (0.35)
  4. フォロー足のCloseが異常足のClose方向を超過（モメンタム確認）

SL: 異常足のスイングエクストリーム ± ATR × SL_ATR_BUFFER
TP: 異常足range × TP_RANGE_MULT or ATR × TP_ATR_MULT
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class PostNewsVol(StrategyBase):
    name = "post_news_vol"
    mode = "daytrade"
    # DISABLED: 15m足のみではニューススパイクとランダムボラの区別不可
    # N=92 WR=42.4% EV=-0.069 — エッジ不在
    # 経済カレンダーAPI統合後に再評価 (2026-04-05)
    enabled = True   # v7.0: Sentinel再有効化 — デモデータ蓄積で再検証

    # ══════════════════════════════════════════════════
    # パラメータ
    # ══════════════════════════════════════════════════

    # ── 異常足検出 ──
    SPIKE_ATR_MULT = 2.0        # TR ≥ ATR(20) × 2.0 (閾値緩和: N確保)
    SPIKE_ALT_MULT = 1.8        # 代替: TR ≥ ATR × 1.8 (高body_ratio時)
    WICK_RATIO_MIN = 0.30       # 上下ヒゲ合計 / range ≥ 30% (ウィップソー)
    BODY_RATIO_ALT = 0.70       # 代替トリガー: 純モメンタム足
    ATR_LOOKBACK = 20           # ATR計算用ルックバック

    # ── クールダウン ──
    COOLDOWN_BARS = 1           # 異常足確定後1本待機
    MAX_FOLLOW_DELAY = 3        # 異常足からmax 3本以内にフォロー必要

    # ── フォロー足 ──
    FOLLOW_BODY_RATIO = 0.35    # フォロー足のbody/range ≥ 35%

    # ── スパイク鮮度 ──
    SPIKE_LOOKBACK = 6          # 過去6本以内のスパイクを検索

    # ── ADX ──
    ADX_MIN = 15
    ADX_MAX = 50                # 極端ボラも許容（指標後はADX高い）

    # ── SL/TP ──
    SL_ATR_BUFFER = 0.3
    TP_RANGE_MULT = 0.8         # 異常足range × 0.8 がTP
    TP_ATR_MULT = 2.5           # 最低: ATR × 2.5
    MIN_RR = 1.5

    # ── 時間帯 ──
    ACTIVE_HOURS_START = 6
    ACTIVE_HOURS_END = 21       # 指標は21:30等の遅い時間もある
    FRIDAY_BLOCK_HOUR = 18

    # ── ペアフィルター ──
    ALLOWED_PAIRS = {
        "USDJPY", "EURUSD", "GBPUSD", "EURGBP", "XAUUSD",
    }

    def _normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().replace("=X", "").replace("=F", "").replace("/", "").replace("_", "")
        if s in ("GC", "GCF"):
            return "XAUUSD"
        return s

    # ══════════════════════════════════════════════════
    # 異常足検出
    # ══════════════════════════════════════════════════

    def _find_spike_bars(self, df, atr, cur_idx):
        """過去SPIKE_LOOKBACK本を走査し、異常足を検出。

        Returns:
            list of dict: {idx, direction, spike_high, spike_low,
                           spike_range, spike_close}
        """
        highs = df["High"].values
        lows = df["Low"].values
        opens = df["Open"].values
        closes = df["Close"].values

        spikes = []

        for i in range(max(0, cur_idx - self.SPIKE_LOOKBACK), cur_idx):
            _h = float(highs[i])
            _l = float(lows[i])
            _o = float(opens[i])
            _c = float(closes[i])
            _range = _h - _l
            _tr = _range  # True Range (simplified: H-L on same bar)

            if _range <= 0 or atr <= 0:
                continue

            _body = abs(_c - _o)
            _body_ratio = _body / _range
            _upper_wick = _h - max(_o, _c)
            _lower_wick = min(_o, _c) - _l
            _wick_sum_ratio = (_upper_wick + _lower_wick) / _range

            _is_spike = False

            # Pattern A: 高TR + 長ヒゲ（ウィップソー型）
            if _tr >= atr * self.SPIKE_ATR_MULT and _wick_sum_ratio >= self.WICK_RATIO_MIN:
                _is_spike = True

            # Pattern B: 高TR + 大実体（純モメンタム型）
            if _tr >= atr * self.SPIKE_ALT_MULT and _body_ratio >= self.BODY_RATIO_ALT:
                _is_spike = True

            if _is_spike:
                _direction = "BUY" if _c > _o else "SELL"
                spikes.append({
                    "idx": i,
                    "direction": _direction,
                    "spike_high": _h,
                    "spike_low": _l,
                    "spike_range": _range,
                    "spike_close": _c,
                    "spike_open": _o,
                })

        return spikes

    # ══════════════════════════════════════════════════
    # フォロースルー検出
    # ══════════════════════════════════════════════════

    def _check_follow_through(self, df, spike, atr, cur_idx):
        """異常足後のフォロースルーを検出。

        Returns:
            dict or None: {signal}
        """
        _delay = cur_idx - spike["idx"]

        # クールダウン: 異常足の直後はブロック
        if _delay < self.COOLDOWN_BARS + 1:
            return None
        # 最大遅延チェック
        if _delay > self.MAX_FOLLOW_DELAY + 1:
            return None

        cur_close = float(df["Close"].iloc[cur_idx])
        cur_open = float(df["Open"].iloc[cur_idx])
        cur_high = float(df["High"].iloc[cur_idx])
        cur_low = float(df["Low"].iloc[cur_idx])
        _bar_range = cur_high - cur_low
        _body = abs(cur_close - cur_open)
        _body_ratio = _body / _bar_range if _bar_range > 0 else 0

        # フォロー足のbody_ratio チェック
        if _body_ratio < self.FOLLOW_BODY_RATIO:
            return None

        direction = spike["direction"]

        if direction == "BUY":
            # BUYフォロー: 陽線 + Closeがスパイク足のClose以上
            if cur_close <= cur_open:
                return None
            if cur_close <= spike["spike_close"]:
                return None
            return {"signal": "BUY"}

        else:
            # SELLフォロー: 陰線 + Closeがスパイク足のClose以下
            if cur_close >= cur_open:
                return None
            if cur_close >= spike["spike_close"]:
                return None
            return {"signal": "SELL"}

    # ══════════════════════════════════════════════════
    # メイン評価
    # ══════════════════════════════════════════════════

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = self._normalize_symbol(ctx.symbol)
        if _sym not in self.ALLOWED_PAIRS:
            return None

        # ── DataFrame十分性 ──
        if ctx.df is None or len(ctx.df) < self.ATR_LOOKBACK + self.SPIKE_LOOKBACK + 5:
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
        # STEP 1: 異常足検出
        # ═══════════════════════════════════════════════════
        spikes = self._find_spike_bars(ctx.df, ctx.atr, cur_idx)
        if not spikes:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2: フォロースルー検出（最新スパイク優先）
        # ═══════════════════════════════════════════════════
        _best = None
        _best_spike = None

        for spike in reversed(spikes):  # 最新のスパイクから評価
            result = self._check_follow_through(ctx.df, spike, ctx.atr, cur_idx)
            if result:
                _best = result
                _best_spike = spike
                break

        if _best is None:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 3: SL/TP
        # ═══════════════════════════════════════════════════
        signal = _best["signal"]
        spike = _best_spike
        _is_buy = signal == "BUY"

        # SL: スパイク足のスイングエクストリーム ± ATR × buffer
        if _is_buy:
            sl = spike["spike_low"] - ctx.atr * self.SL_ATR_BUFFER
        else:
            sl = spike["spike_high"] + ctx.atr * self.SL_ATR_BUFFER

        # TP: スパイクrange × 0.8 or ATR × 2.5 の大きい方
        _tp_range = spike["spike_range"] * self.TP_RANGE_MULT
        _tp_atr = ctx.atr * self.TP_ATR_MULT
        _tp_dist = max(_tp_range, _tp_atr)
        tp = ctx.entry + _tp_dist if _is_buy else ctx.entry - _tp_dist

        # RR
        _sl_dist = abs(ctx.entry - sl)
        _tp_dist_final = abs(tp - ctx.entry)
        if _sl_dist <= 0:
            return None

        if _tp_dist_final / _sl_dist < self.MIN_RR:
            _tp_dist_final = _sl_dist * self.MIN_RR
            tp = ctx.entry + _tp_dist_final if _is_buy else ctx.entry - _tp_dist_final

        _rr = _tp_dist_final / _sl_dist

        # SL方向チェック
        if _is_buy and sl >= ctx.entry:
            return None
        if not _is_buy and sl <= ctx.entry:
            return None

        # ═══════════════════════════════════════════════════
        # スコア
        # ═══════════════════════════════════════════════════
        _score = 5.0
        # スパイクの大きさボーナス
        _spike_mult = spike["spike_range"] / ctx.atr if ctx.atr > 0 else 1
        if _spike_mult >= 4.0:
            _score += 2.0
        elif _spike_mult >= 3.0:
            _score += 1.0
        # RRボーナス
        if _rr >= 2.5:
            _score += 1.0
        # 即時フォロー（delay=2=最速）
        _delay = len(ctx.df) - 1 - spike["idx"]
        if _delay <= 2:
            _score += 0.5

        _reasons = [
            f"✅ Post-News Vol: {signal} — spike TR/ATR={_spike_mult:.1f}x",
            f"✅ Follow-through confirmed (delay={_delay} bars)",
            f"RR={_rr:.1f}, ADX={ctx.adx:.1f}",
        ]

        return Candidate(
            signal=signal,
            confidence=min(85, 50 + int(_spike_mult * 5) + int(_rr * 3)),
            sl=round(sl, 5 if not ctx.is_jpy else 3),
            tp=round(tp, 5 if not ctx.is_jpy else 3),
            reasons=_reasons,
            entry_type=self.name,
            score=_score,
        )
