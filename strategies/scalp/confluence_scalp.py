"""
Confluence Scalp v2 — Triple Confluence + MSS (Market Structure Shift)

学術根拠:
  - Triple Confluence Gate: 3理論族（トレンド+オシレーター+モメンタム）の合意要求
    → 単一指標のノイズエントリーを排除 (Menkhoff 2010, JoF)
  - CHoCH (Change of Character): ICT/SMC概念のスイング構造分析
    → トレンド転換の初動を構造的に検出 (Wyckoff 1931)
  - Session Gate (UTC 12-17): London/NY重複セッション限定
    → 摩擦分析で唯一 instant death < 50%% の時間帯 (461t本番監査)
  - MFE Guard (ATR/Spread >= 10): スプレッド吸収余地の確保
    → SAR < 1.0 (摩擦死) を構造的に回避

設計:
  - 既存Sentinel戦略(bb_rsi等)のSoft HTFペナルティとは異なり、HTF Hard Block適用
  - Session Gate + MFE Guard → エントリーの母集団を「摩擦耐性あり」に限定
  - Triple Confluence → 3理論族の合意で false signal を排除
  - CHoCH → 構造的トレンド転換を検出（単純な指標クロスではなく市場構造の変化）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import logging

logger = logging.getLogger("confluence_scalp")


# ══════════════════════════════════════════════════════════════
# Market Structure Shift (MSS) 検出関数
# ══════════════════════════════════════════════════════════════

def _find_swing_points(df, n: int = 3) -> tuple:
    """n-bar fractal によるスイングポイント検出。

    Fractal定義 (Williams 1995): n本前後の全バーより高い(低い)バー。
    n=3: 前後3本 = 合計7本ウィンドウ → 1m足で7分の構造を捉える。

    Returns: (swing_highs, swing_lows) — 各 list of (index, price)
    """
    highs = []
    lows = []
    _len = len(df)
    if _len < n * 2 + 1:
        return highs, lows
    for i in range(n, _len - n):
        h_i = float(df.iloc[i]["High"])
        l_i = float(df.iloc[i]["Low"])
        is_swing_high = True
        is_swing_low = True
        for j in range(1, n + 1):
            if h_i < float(df.iloc[i - j]["High"]) or h_i < float(df.iloc[i + j]["High"]):
                is_swing_high = False
            if l_i > float(df.iloc[i - j]["Low"]) or l_i > float(df.iloc[i + j]["Low"]):
                is_swing_low = False
            if not is_swing_high and not is_swing_low:
                break
        if is_swing_high:
            highs.append((i, h_i))
        if is_swing_low:
            lows.append((i, l_i))
    return highs, lows


def detect_choch(df, lookback: int = 30) -> Optional[dict]:
    """CHoCH (Change of Character) 検出。

    Wyckoff (1931) / ICT理論: 市場構造の転換を検出する。
    上昇構造 (HH+HL連続) 中にスイングローを実体で下抜け → ベアリッシュCHoCH
    下降構造 (LL+LH連続) 中にスイングハイを実体で上抜け → ブリッシュCHoCH

    重要: ヒゲ(wick)ではなく実体(body)で判定 → ノイズ耐性。

    Returns:
        {"direction": "BUY"/"SELL", "level": float, "type": "CHoCH"} or None
    """
    if len(df) < lookback:
        return None
    recent = df.iloc[-lookback:]
    swing_highs, swing_lows = _find_swing_points(recent, n=3)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return None

    last_bar = recent.iloc[-1]
    body_low = min(float(last_bar["Close"]), float(last_bar["Open"]))
    body_high = max(float(last_bar["Close"]), float(last_bar["Open"]))

    # ── ベアリッシュCHoCH ──
    # 前提: 上昇構造 (HL+HH) → 最新スイングローを実体で下抜け
    last_sl = swing_lows[-1][1]
    prev_sl = swing_lows[-2][1]
    last_sh = swing_highs[-1][1]
    prev_sh = swing_highs[-2][1]

    if last_sl > prev_sl and last_sh > prev_sh:
        # 上昇構造確認 → スイングロー割れ = ベアリッシュCHoCH
        if body_low < last_sl:
            return {"direction": "SELL", "level": last_sl, "type": "CHoCH"}

    # ── ブリッシュCHoCH ──
    # 前提: 下降構造 (LH+LL) → 最新スイングハイを実体で上抜け
    if last_sl < prev_sl and last_sh < prev_sh:
        # 下降構造確認 → スイングハイ超え = ブリッシュCHoCH
        if body_high > last_sh:
            return {"direction": "BUY", "level": last_sh, "type": "CHoCH"}

    return None


def detect_msb(df, choch_dir: str, lookback: int = 15) -> bool:
    """MSB (Market Structure Break) — CHoCH後の継続確認。

    CHoCH = 転換の初動。MSB = 新トレンド方向の確認。
    ブリッシュCHoCH後: HH (Higher High) 更新 → 新上昇構造の確認
    ベアリッシュCHoCH後: LL (Lower Low) 更新 → 新下降構造の確認

    n=2 (5バーウィンドウ) で高感度検出 — MSBは初動確認なので早期検出重視。

    Returns: True if MSB confirmed, False otherwise
    """
    if len(df) < lookback:
        return False
    recent = df.iloc[-lookback:]
    swing_highs, swing_lows = _find_swing_points(recent, n=2)

    if choch_dir == "BUY" and len(swing_highs) >= 2:
        # HH 更新チェック (最新スイングハイ > 前のスイングハイ)
        return swing_highs[-1][1] > swing_highs[-2][1]
    elif choch_dir == "SELL" and len(swing_lows) >= 2:
        # LL 更新チェック (最新スイングロー < 前のスイングロー)
        return swing_lows[-1][1] < swing_lows[-2][1]
    return False


def detect_mss_state(df, lookback: int = 30) -> dict:
    """MSS (Market Structure Shift) 総合状態を検出。

    CHoCH + MSB を組み合わせた構造転換の完全な状態を返す。

    Returns:
        {
            "choch": {"direction": "BUY"/"SELL", "level": float} or None,
            "msb": bool,
            "direction": "BUY"/"SELL"/None  (MSS確認済みの方向)
        }
    """
    result = {"choch": None, "msb": False, "direction": None}
    if df is None or len(df) < lookback:
        return result

    choch = detect_choch(df, lookback=lookback)
    if choch is None:
        return result

    result["choch"] = choch
    msb = detect_msb(df, choch["direction"], lookback=min(lookback, 15))
    result["msb"] = msb
    if msb:
        result["direction"] = choch["direction"]
    return result


def compute_limit_entry_price(df, signal: str) -> Optional[float]:
    """Friction Minimizer: 直近3本のウィック中間点で指値エントリー価格を計算。

    市場注文(ask/bid)よりも有利な価格を得るための指値位置を計算。
    BUY: 直近3本の下ウィック中間点 = (Low + body_low) / 2 の平均
    SELL: 直近3本の上ウィック中間点 = (High + body_high) / 2 の平均

    ウィックが存在しないバーはスキップ。有効なウィックがない場合はNone。

    Returns: limit entry price or None
    """
    if len(df) < 3:
        return None
    last3 = df.iloc[-3:]
    if signal == "BUY":
        wick_mids = []
        for _, bar in last3.iterrows():
            body_low = min(float(bar["Open"]), float(bar["Close"]))
            low = float(bar["Low"])
            _wick = body_low - low
            if _wick > 0:  # 下ウィックが存在
                wick_mids.append((low + body_low) / 2)
        if not wick_mids:
            return None
        return sum(wick_mids) / len(wick_mids)
    else:  # SELL
        wick_mids = []
        for _, bar in last3.iterrows():
            body_high = max(float(bar["Open"]), float(bar["Close"]))
            high = float(bar["High"])
            _wick = high - body_high
            if _wick > 0:  # 上ウィックが存在
                wick_mids.append((high + body_high) / 2)
        if not wick_mids:
            return None
        return sum(wick_mids) / len(wick_mids)


# ══════════════════════════════════════════════════════════════
# Climax Detection (Profit Extender用)
# ══════════════════════════════════════════════════════════════

def detect_climax(df, direction: str, lookback: int = 10) -> bool:
    """クライマックス (トレンド疲弊) 検出。

    上昇トレンド中のクライマックス (SELL climax for BUY position):
      1. RSI divergence: 価格新高値 but RSI低下
      2. 上ウィック > 実体 (buying pressure exhaustion)
    下降トレンド中のクライマックス (BUY climax for SELL position):
      1. RSI divergence: 価格新安値 but RSI上昇
      2. 下ウィック > 実体 (selling pressure exhaustion)

    Returns: True if climax detected
    """
    if df is None or len(df) < lookback:
        return False
    recent = df.iloc[-lookback:]
    last = recent.iloc[-1]
    prev = recent.iloc[-2]

    _close = float(last["Close"])
    _open = float(last["Open"])
    _high = float(last["High"])
    _low = float(last["Low"])
    _body = abs(_close - _open)
    _range = _high - _low
    if _range <= 0 or _body <= 0:
        return False

    # RSI check (if available)
    _has_rsi = "rsi5" in last.index or "rsi" in last.index
    _rsi_col = "rsi5" if "rsi5" in last.index else "rsi"

    if direction == "BUY":
        # BUYポジ → 上昇クライマックス検出
        _upper_wick = _high - max(_close, _open)
        _wick_ratio = _upper_wick / _range
        # 大きな上ウィック (60%以上)
        if _wick_ratio >= 0.60:
            # RSI divergence: 価格は高いがRSI低下
            if _has_rsi and len(recent) >= 3:
                _rsi_now = float(last[_rsi_col]) if last[_rsi_col] == last[_rsi_col] else 50
                _rsi_prev = float(prev[_rsi_col]) if prev[_rsi_col] == prev[_rsi_col] else 50
                if _high > float(prev["High"]) and _rsi_now < _rsi_prev:
                    return True
            # ウィックだけでも強いシグナル (70%以上)
            if _wick_ratio >= 0.70:
                return True
    else:
        # SELLポジ → 下降クライマックス検出
        _lower_wick = min(_close, _open) - _low
        _wick_ratio = _lower_wick / _range
        if _wick_ratio >= 0.60:
            if _has_rsi and len(recent) >= 3:
                _rsi_now = float(last[_rsi_col]) if last[_rsi_col] == last[_rsi_col] else 50
                _rsi_prev = float(prev[_rsi_col]) if prev[_rsi_col] == prev[_rsi_col] else 50
                if _low < float(prev["Low"]) and _rsi_now > _rsi_prev:
                    return True
            if _wick_ratio >= 0.70:
                return True
    return False


# ══════════════════════════════════════════════════════════════
# Confluence Scalp Strategy
# ══════════════════════════════════════════════════════════════

class ConfluenceScalp(StrategyBase):
    """Triple Confluence + MSS スキャルプ戦略。

    === 防御層 ===
    1. Session Gate: UTC 12-17 のみ (London/NY overlap)
    2. MFE Guard: ATR/Spread >= 10 (摩擦吸収余地)
    3. HTF Hard Block: HTF方向に逆行するエントリーを完全ブロック

    === 攻撃層 ===
    4. Triple Confluence Gate:
       Family A (Trend):      EMA9/21 クロスまたは整列
       Family B (Oscillator): RSI5極端 + BB%B極端
       Family C (Momentum):   MACD-H 方向転換
    5. CHoCH (Change of Character): 市場構造転換ボーナス
    6. MSB (Market Structure Break): 構造継続確認ボーナス
    """
    name = "confluence_scalp"
    mode = "scalp"
    enabled = True

    # ── Session Gate: UTC 12-17 (London/NY overlap) ──
    _SESSION_START = 12
    _SESSION_END = 17

    # ── MFE Guard: ATR/Spread ratio minimum ──
    _MFE_GUARD_RATIO = 10

    # ── Triple Confluence thresholds ──
    _RSI5_BUY_EXTREME = 42      # RSI5 < this for BUY
    _RSI5_SELL_EXTREME = 58     # RSI5 > this for SELL
    _BBPB_BUY_EXTREME = 0.30   # BB%B < this for BUY
    _BBPB_SELL_EXTREME = 0.70   # BB%B > this for SELL

    # ── SL/TP multipliers ──
    _SL_ATR_MULT = 1.2    # SL = ATR7 x 1.2 (構造エントリーなので広め)
    _TP_ATR_MULT = 2.5    # TP = ATR7 x 2.5 (高RR: 利益延伸の余地)

    # ── EUR/GBP disabled ──
    _disabled_symbols = frozenset({"EURGBP"})

    def _estimate_spread_pips(self, ctx: SignalContext) -> float:
        """ペア別スプレッド推定 (BT spread v2ベース)。"""
        sym = ctx.symbol.upper()
        h = ctx.hour_utc
        if "GBP" in sym and "JPY" not in sym:
            # GBP/USD: 0.8-1.8pip
            return 1.0 if 7 <= h <= 16 else 1.5
        elif "EUR" in sym and "GBP" not in sym and "JPY" not in sym:
            # EUR/USD: 0.3-1.0pip
            return 0.5 if 7 <= h <= 16 else 0.8
        elif "JPY" in sym and "EUR" in sym:
            # EUR/JPY: 0.5-1.5pip
            return 0.8 if 7 <= h <= 16 else 1.2
        elif "JPY" in sym:
            # USD/JPY: 0.3-1.0pip
            return 0.5 if 7 <= h <= 16 else 0.8
        else:
            return 1.0  # conservative default

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペア無効化 ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym in self._disabled_symbols:
            return None

        # ══════════════════════════════════════════════════
        # 防御層 1: Session Gate (UTC 12-17)
        # ══════════════════════════════════════════════════
        if not (self._SESSION_START <= ctx.hour_utc <= self._SESSION_END):
            return None

        # ══════════════════════════════════════════════════
        # 防御層 2: MFE Guard (ATR/Spread >= 10)
        # ══════════════════════════════════════════════════
        _atr_pips = ctx.atr7 * ctx.pip_mult
        _spread_pips = self._estimate_spread_pips(ctx)
        _mfe_ratio = _atr_pips / max(_spread_pips, 0.1)
        if _mfe_ratio < self._MFE_GUARD_RATIO:
            return None

        # ══════════════════════════════════════════════════
        # 防御層 3: HTF Hard Block
        # ══════════════════════════════════════════════════
        _htf_dir = ctx.htf.get("agreement", "neutral")

        # ══════════════════════════════════════════════════
        # 攻撃層: Triple Confluence Gate
        # 3理論族が全て同方向に合意した場合のみエントリー
        # ══════════════════════════════════════════════════
        signal = None
        score = 0.0
        reasons = []

        # ── Family A: Trend (EMA9/21) ──
        _ema_bull = ctx.ema9 > ctx.ema21
        _ema_bear = ctx.ema9 < ctx.ema21
        _ema_cross_bull = (ctx.ema9 > ctx.ema21 and ctx.ema9_prev <= ctx.ema21_prev)
        _ema_cross_bear = (ctx.ema9 < ctx.ema21 and ctx.ema9_prev >= ctx.ema21_prev)

        # ── Family B: Oscillator (RSI5 extreme + BB%B extreme) ──
        _osc_buy = (ctx.rsi5 < self._RSI5_BUY_EXTREME
                    and ctx.bbpb < self._BBPB_BUY_EXTREME)
        _osc_sell = (ctx.rsi5 > self._RSI5_SELL_EXTREME
                     and ctx.bbpb > self._BBPB_SELL_EXTREME)

        # ── Family C: Momentum (MACD-H reversal) ──
        _macdh_bull = (ctx.macdh > ctx.macdh_prev
                       and ctx.macdh_prev <= ctx.macdh_prev2)
        _macdh_bear = (ctx.macdh < ctx.macdh_prev
                       and ctx.macdh_prev >= ctx.macdh_prev2)

        # ══════════════════════════════════════════════════
        # BUY: 3族合意 + HTF Hard Block
        # ══════════════════════════════════════════════════
        if (_ema_bull or _ema_cross_bull) and _osc_buy and _macdh_bull:
            if _htf_dir == "bear":
                return None  # HTF Hard Block
            signal = "BUY"
            score = 5.0  # High base score (triple confluence)
            _cross_tag = "(クロス)" if _ema_cross_bull else ""
            reasons.append(
                f"✅ Triple Confluence BUY: "
                f"EMA9>21{_cross_tag} + "
                f"RSI5={ctx.rsi5:.1f}<{self._RSI5_BUY_EXTREME} + "
                f"BB%B={ctx.bbpb:.2f}<{self._BBPB_BUY_EXTREME} + "
                f"MACD-H反転上昇"
            )

        # ══════════════════════════════════════════════════
        # SELL: 3族合意 + HTF Hard Block
        # ══════════════════════════════════════════════════
        elif (_ema_bear or _ema_cross_bear) and _osc_sell and _macdh_bear:
            if _htf_dir == "bull":
                return None  # HTF Hard Block
            signal = "SELL"
            score = 5.0
            _cross_tag = "(クロス)" if _ema_cross_bear else ""
            reasons.append(
                f"✅ Triple Confluence SELL: "
                f"EMA9<21{_cross_tag} + "
                f"RSI5={ctx.rsi5:.1f}>{self._RSI5_SELL_EXTREME} + "
                f"BB%B={ctx.bbpb:.2f}>{self._BBPB_SELL_EXTREME} + "
                f"MACD-H反転下落"
            )
        else:
            return None

        # ══════════════════════════════════════════════════
        # CHoCH (Change of Character) ボーナス
        # ══════════════════════════════════════════════════
        _choch = None
        if ctx.df is not None and len(ctx.df) >= 30:
            _choch = detect_choch(ctx.df, lookback=30)
            if _choch and _choch["direction"] == signal:
                score += 2.0
                reasons.append(
                    f"✅ CHoCH検出: {_choch['direction']}方向の構造転換 "
                    f"(level={_choch['level']:.5f})"
                )
                # MSB confirmation
                if detect_msb(ctx.df, signal, lookback=15):
                    score += 1.0
                    reasons.append("✅ MSB確認: 構造継続 (HH/LL更新)")

        # ══════════════════════════════════════════════════
        # Additional Score Bonuses
        # ══════════════════════════════════════════════════
        # ADX > 25: trending environment bonus
        if ctx.adx > 25:
            score += 0.5
            reasons.append(f"✅ トレンド環境(ADX={ctx.adx:.1f}>25)")

        # HTF alignment bonus
        if (_htf_dir == "bull" and signal == "BUY") or \
           (_htf_dir == "bear" and signal == "SELL"):
            score += 1.0
            reasons.append(f"✅ HTF方向一致({_htf_dir})")

        # Peak overlap bonus (UTC 13-16)
        if 13 <= ctx.hour_utc <= 16:
            score += 0.5
            reasons.append(f"✅ London/NY重複ピーク(UTC {ctx.hour_utc})")

        # MFE ratio quality bonus
        if _mfe_ratio >= 15:
            score += 0.5
            reasons.append(f"✅ 高MFE余地(ATR/Spread={_mfe_ratio:.1f})")

        # Stoch confirmation bonus
        if signal == "BUY" and ctx.stoch_k < 30 and ctx.stoch_k > ctx.stoch_d:
            score += 0.5
            reasons.append(
                f"✅ Stochゴールデンクロス(K={ctx.stoch_k:.0f})")
        elif signal == "SELL" and ctx.stoch_k > 70 and ctx.stoch_k < ctx.stoch_d:
            score += 0.5
            reasons.append(
                f"✅ Stochデッドクロス(K={ctx.stoch_k:.0f})")

        # ══════════════════════════════════════════════════
        # SL / TP
        # ══════════════════════════════════════════════════
        _min_sl = 0.030 if ctx.is_jpy else 0.00030
        sl_dist = max(ctx.atr7 * self._SL_ATR_MULT, _min_sl)
        tp_dist = ctx.atr7 * self._TP_ATR_MULT
        if signal == "BUY":
            sl = ctx.entry - sl_dist
            tp = ctx.entry + tp_dist
        else:
            sl = ctx.entry + sl_dist
            tp = ctx.entry - tp_dist

        # ══════════════════════════════════════════════════
        # Friction Minimizer: 指値エントリー価格 (optional)
        # ══════════════════════════════════════════════════
        _limit_price = None
        if ctx.df is not None and len(ctx.df) >= 3:
            _limit_price = compute_limit_entry_price(ctx.df, signal)

        # ══════════════════════════════════════════════════
        # Confidence & Result
        # ══════════════════════════════════════════════════
        conf = int(min(90, 55 + score * 3.5))
        reasons.append(
            f"📊 Session Gate: UTC {ctx.hour_utc} | "
            f"MFE Ratio: {_mfe_ratio:.1f} | "
            f"HTF: {_htf_dir}"
        )

        # ── 特殊マーカー: demo_trader 連携 ──
        # __LIMIT_ENTRY__: Friction Minimizer の指値価格
        # __CHOCH__: CHoCH情報 (Profit Extender用)
        if _limit_price is not None:
            _prec = 3 if ctx.is_jpy else 5
            reasons.append(f"__LIMIT_ENTRY__:{_limit_price:.{_prec}f}")

        if _choch is not None:
            _prec = 3 if ctx.is_jpy else 5
            reasons.append(
                f"__CHOCH__:{_choch['direction']}:"
                f"{_choch['level']:.{_prec}f}"
            )

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
