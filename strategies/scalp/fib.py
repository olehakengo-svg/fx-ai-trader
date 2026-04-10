"""Fibonacci Reversal — フィボナッチリトレースメント反発"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


def _calc_fibonacci_levels(df, lookback=60):
    """フィボナッチリトレースメントレベルを計算。
    df の直近 lookback バーから高値/安値を特定し、
    38.2%, 50%, 61.8% のリトレースメントレベルを返す。
    """
    if df is None or len(df) < lookback:
        return None
    _sub = df.iloc[-lookback:]
    _high = float(_sub["High"].max())
    _low = float(_sub["Low"].min())
    _high_idx = _sub["High"].idxmax()
    _low_idx = _sub["Low"].idxmin()

    if _high == _low:
        return None

    # トレンド方向: 高値が後なら上昇、低値が後なら下降
    if _high_idx > _low_idx:
        trend = "up"
        diff = _high - _low
        r382 = _high - diff * 0.382
        r500 = _high - diff * 0.500
        r618 = _high - diff * 0.618
    else:
        trend = "down"
        diff = _high - _low
        r382 = _low + diff * 0.382
        r500 = _low + diff * 0.500
        r618 = _low + diff * 0.618

    return {"trend": trend, "high": _high, "low": _low,
            "r382": r382, "r500": r500, "r618": r618}


class FibReversal(StrategyBase):
    name = "fib_reversal"
    mode = "scalp"

    # チューナブルパラメータ (v6.3 対策強化)
    min_lookback = 45
    lookbacks = [45, 60]
    fib_proximity = 0.35   # v6.3: 0.50→0.35 精度↑ (Fibレベルにより近い位置でのみエントリー)
    rsi5_buy = 48          # （45→48緩和）
    rsi5_sell = 52         # （55→52緩和）
    tp_mult = 1.8          # USD_JPYデフォルト (維持)
    sl_mult = 0.7          # v6.3: 0.5→0.7 ノイズ生存率↑
    sl_fib_offset = 0.2    # フィボレベルからのSLオフセット（ATR倍率）
    body_ratio_min = 0.60  # v8.3: 0.50→0.60 確認足強化 (即死率75.9%対策)

    # ── ペア別TP倍率 (v6.3: 非JPYは摩擦が大きいため早期利確) ──
    _tp_mult_by_pair = {
        "USDJPY": 1.8,    # 維持: USD_JPY最強ペア
        "EURUSD": 1.3,    # v6.3: 摩擦大→早期利確
        "GBPUSD": 1.3,    # v6.3: 摩擦大→早期利確
        "EURJPY": 1.5,    # v6.3: 中間
        "XAUUSD": 1.5,    # v6.3: 中間
    }

    # ── セッションフィルター (v6.3: 低ボラ時間帯ブロック) ──
    _blocked_hours_by_pair = {
        "EURUSD": frozenset(range(0, 6)),    # v6.3: アジア時間EUR ATR不足
        "GBPUSD": frozenset(range(0, 6)),    # v6.3: アジア時間GBP ATR不足
    }

    # ── ペア別無効化 (BT検証 2026-04-06) ──
    _disabled_symbols = frozenset({"EURGBP"})

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: BT負EVペアは発火停止 ──
        _sym_clean = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym_clean in self._disabled_symbols:
            return None

        # ── v6.3: セッションフィルター (低ボラ時間帯ブロック) ──
        _blocked = self._blocked_hours_by_pair.get(_sym_clean)
        if _blocked and ctx.hour_utc in _blocked:
            return None

        if ctx.df is None or len(ctx.df) < self.min_lookback:
            return None

        # 複数lookbackでフィボ検出
        _fib = None
        _lookbacks = self.lookbacks if len(ctx.df) >= max(self.lookbacks) else [self.min_lookback]
        for lb in _lookbacks:
            if len(ctx.df) < lb:
                continue
            _fib_try = _calc_fibonacci_levels(ctx.df, lookback=lb)
            if _fib_try and _fib_try.get("trend"):
                _fib = _fib_try
                break

        if not _fib or not _fib.get("trend"):
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _fib_trend = _fib["trend"]
        _fib_levels = {
            "38.2%": _fib.get("r382", 0),
            "50.0%": _fib.get("r500", 0),
            "61.8%": _fib.get("r618", 0),
        }

        # 各フィボレベルとの近接チェック
        _fib_touch = None
        for _fib_name, _fib_val in _fib_levels.items():
            if _fib_val and abs(ctx.entry - _fib_val) < ctx.atr * self.fib_proximity:
                _fib_touch = (_fib_name, _fib_val)
                break

        if not _fib_touch:
            return None

        _fn, _fv = _fib_touch
        _fib_dist = abs(ctx.entry - _fv) / ctx.atr if ctx.atr > 0 else 0

        # ── v6.3: 足の実体比率チェック (ヒゲ足排除) ──
        _bar_range = abs(ctx.high - ctx.low) if hasattr(ctx, 'high') and hasattr(ctx, 'low') else 0
        _bar_body = abs(ctx.entry - ctx.open_price)
        _body_ratio = _bar_body / _bar_range if _bar_range > 0 else 0

        # ── v6.3: ペア別TP倍率 (非JPYは摩擦大→早期利確) ──
        _effective_tp = self._tp_mult_by_pair.get(_sym_clean, self.tp_mult)

        # 上昇トレンドの押し目買い
        if _fib_trend == "up" and ctx.rsi5 < self.rsi5_buy and ctx.stoch_k > ctx.stoch_d:
            signal = "BUY"
            score = 3.5
            reasons.append(f"✅ Fib {_fn}サポート({_fv:.3f}, dist={_fib_dist:.2f}ATR)")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率リバーサルゾーン")
            elif _fn == "50.0%":
                score += 0.5
            if ctx.rsi5 < 35:
                score += 0.5
            # v6.3: 陽線 + 実体比率チェック
            if ctx.entry > ctx.open_price and _body_ratio >= self.body_ratio_min:
                score += 0.3
                reasons.append(f"✅ 陽線確認(body={_body_ratio:.0%})")
            elif ctx.entry > ctx.open_price:
                score += 0.1  # 弱い陽線(ヒゲ大)は減点
            if ctx.macdh > ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転上昇")
            else:
                # v8.3: 非Tier1極端ではMACD-H反転必須 (即死率-30%)
                if ctx.bbpb > 0.05:  # Tier1(≤0.05)はMACD-Hオプション維持
                    return None  # MACD-H不反転 → スキップ
            tp = ctx.entry + ctx.atr7 * _effective_tp
            sl = min(ctx.entry - ctx.atr7 * self.sl_mult, _fv - ctx.atr7 * self.sl_fib_offset)

        # 下降トレンドの戻り売り
        elif _fib_trend == "down" and ctx.rsi5 > self.rsi5_sell and ctx.stoch_k < ctx.stoch_d:
            signal = "SELL"
            score = 3.5
            reasons.append(f"✅ Fib {_fn}レジスタンス({_fv:.3f}, dist={_fib_dist:.2f}ATR)")
            if _fn == "61.8%":
                score += 0.8
                reasons.append("✅ Fib61.8%: 最高確率リバーサルゾーン")
            elif _fn == "50.0%":
                score += 0.5
            if ctx.rsi5 > 65:
                score += 0.5
            # v6.3: 陰線 + 実体比率チェック
            if ctx.entry < ctx.open_price and _body_ratio >= self.body_ratio_min:
                score += 0.3
                reasons.append(f"✅ 陰線確認(body={_body_ratio:.0%})")
            elif ctx.entry < ctx.open_price:
                score += 0.1
            if ctx.macdh < ctx.macdh_prev:
                score += 0.4
                reasons.append("✅ MACD-H反転下降")
            else:
                # v8.3: 非Tier1極端ではMACD-H反転必須
                if ctx.bbpb < 0.95:  # Tier1(≥0.95)はMACD-Hオプション維持
                    return None
            tp = ctx.entry - ctx.atr7 * _effective_tp
            sl = max(ctx.entry + ctx.atr7 * self.sl_mult, _fv + ctx.atr7 * self.sl_fib_offset)

        # v8.3: Fibレベル階層化 — 38.2%はスコア閾値引上げ (弱いレベル=高い確信要求)
        _score_gate = 3.0  # デフォルト (61.8%)
        if _fn and "38.2" in _fn:
            _score_gate = 4.5  # 最弱レベル → 高スコア必須
        elif _fn and "50" in _fn:
            _score_gate = 3.5
        if signal is None or score < _score_gate:
            return None

        conf = int(min(85, 45 + score * 5))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
