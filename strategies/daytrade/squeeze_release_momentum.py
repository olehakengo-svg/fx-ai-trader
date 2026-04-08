"""
Squeeze Release Momentum (SRM-DT) — BB圧縮→解放のトレンド初動を捕捉

学術的根拠:
  - Bollinger (2001): Bollinger Bandwidth squeeze → volatility expansion cycle
  - KSB (Keltner Squeeze Breakout, 1H) の成功原理を 15m足に降格適用
  - bb_squeeze_breakout (1m WR=36.8%) の失敗分析:
    1m足のスクイーズはノイズ圧縮にすぎない → 15m足で機関の蓄積を捕捉

戦略コンセプト:
  BB幅が長時間圧縮(SQUEEZE)された後のRelease(拡大)をトリガーとし、
  5段フィルターで偽ブレイクアウトを排除してトレンド第1波に乗る。

  Phase 0 で追加した squeeze_bars (圧縮持続本数) をエネルギー充填度として使用。
  KSB の全フィルター体系 (ADX上昇, body_ratio, MACD-H拡大, freshness) を継承。

  MR(平均回帰)戦略ではないため:
  - _RANGE_MR_STRATEGIES に含めない
  - BB_mid TP 強制・SL widening・RR floor 0.8 の対象外
  - Quick-Harvest (×0.70) は通常適用
  - Profit Extender / Pyramiding 完全対応 (_PE_50PCT_ELIGIBLE)

エントリーロジック (5段フィルター):
  ■ Pre-condition: squeeze_bars >= 3 (45分以上の圧縮蓄積)
  ■ Trigger:       BB拡大開始 + bbpb > 0.80 (BUY) / < 0.20 (SELL) + body_ratio >= 0.35
  ■ Momentum:      MACD-H方向一致+拡大 + ADX >= 18 OR ADX上昇 +2.0
  ■ HTF:           4H/1D バイアス非逆行
  ■ Freshness:     前足がBB 2σ外に完全ブレイク済みでないこと

SL/TP:
  SL = Swing H/L (8本) ± ATR×0.3, max ATR×1.5, min ATR×0.8
  TP = ATR×2.5 (MIN_RR=1.5 保証)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class SqueezeReleaseMomentum(StrategyBase):
    name = "squeeze_release_momentum"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── Pre-condition: SQUEEZE蓄積 ──
    MIN_SQUEEZE_BARS = 3          # 15m × 3 = 45分以上の圧縮
    MAX_SQUEEZE_BARS = 40         # 40本超 = デッドマーケット排除

    # ── Trigger: Release + Breakout ──
    BBPB_BUY_THRES = 0.80        # BB上方離脱
    BBPB_SELL_THRES = 0.20       # BB下方離脱
    BODY_RATIO_MIN = 0.35        # 実体/レンジ比率 (ヒゲ抜け排除)

    # ── Momentum: ADX + MACD-H ──
    ADX_MIN = 18                  # トレンド開始
    ADX_RISE_THRES = 2.0          # ADX急上昇 (KSB準拠)

    # ── Freshness: 前足BB外排除 ──
    PREV_BAR_BBPB_MAX = 0.85     # BUY: 前足bbpb < 0.85 (未ブレイク)
    PREV_BAR_BBPB_MIN = 0.15     # SELL: 前足bbpb > 0.15

    # ── SL/TP ──
    SL_SWING_LOOKBACK = 8         # スイングH/L検出バー数
    SL_ATR_BUFFER = 0.3           # SL = Swing ± ATR×0.3
    SL_ATR_MAX = 1.5              # SL最大 = ATR×1.5
    SL_ATR_MIN = 0.8              # SL最小 = ATR×0.8
    TP_ATR_MULT = 2.5             # TP = ATR×2.5
    MIN_RR = 1.5                  # 最低RR

    # ── Bar Range (偽BK排除) ──
    BAR_RANGE_ATR_MIN = 1.3       # バーレンジ >= ATR×1.3

    # ── Spread Guard ──
    ATR_SPREAD_MIN = 8            # ATR/Spread >= 8

    # ── Session Filter ──
    ACTIVE_HOURS_START = 7        # UTC 07:00 (London open)
    ACTIVE_HOURS_END = 17         # UTC 17:00 (NY afternoon)
    FRIDAY_BLOCK_AFTER = 13       # 金曜 UTC 13:00以降ブロック

    # ── Score ──
    SCORE_BASE = 4.5

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        """5段フィルターによるSqueeze Release Momentum検出。"""

        # ══════════════════════════════════════════════════
        # ペアフィルター: 暫定 EUR/USD 優先, GBP/USD, USD/JPY
        # ══════════════════════════════════════════════════
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        _allowed_pairs = ("EURUSD", "GBPUSD", "USDJPY")
        if _sym not in _allowed_pairs:
            return None

        # ══════════════════════════════════════════════════
        # DataFrame十分性チェック
        # ══════════════════════════════════════════════════
        _min_bars = max(self.SL_SWING_LOOKBACK, self.MIN_SQUEEZE_BARS) + 5
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        # ══════════════════════════════════════════════════
        # セッションフィルター
        # ══════════════════════════════════════════════════
        if ctx.hour_utc < self.ACTIVE_HOURS_START or ctx.hour_utc >= self.ACTIVE_HOURS_END:
            return None
        if ctx.is_friday and ctx.hour_utc >= self.FRIDAY_BLOCK_AFTER:
            return None

        # ══════════════════════════════════════════════════
        # FILTER 1: Pre-condition — SQUEEZE蓄積
        # squeeze_bars >= 3 (15m×3=45分以上の圧縮ゾーン滞在)
        # ══════════════════════════════════════════════════
        _regime = ctx.regime or {}
        _squeeze_bars = _regime.get("squeeze_bars", 0)
        _range_sub = _regime.get("range_sub")
        _bb_width_pct = _regime.get("bb_width_pct", 50.0)

        # SQUEEZE判定: range_sub=="SQUEEZE" (bb_pct<10) OR
        # 直近がSQUEEZEから脱出直後(bb_pct 10-15 & squeeze_bars残存)
        # → squeeze_bars > 0 が充分条件
        if _squeeze_bars < self.MIN_SQUEEZE_BARS:
            return None
        if _squeeze_bars > self.MAX_SQUEEZE_BARS:
            return None  # デッドマーケット排除

        # ══════════════════════════════════════════════════
        # FILTER 2: Trigger — Release + Breakout
        # BB拡大開始 + bbpb方向 + body_ratio
        # ══════════════════════════════════════════════════

        # ── BB拡大検出 (Release) ──
        _prev_row = ctx.df.iloc[-2] if len(ctx.df) >= 2 else None
        if _prev_row is None:
            return None
        _prev_bb_width = float(_prev_row.get("bb_width", 0))
        if _prev_bb_width <= 0 or ctx.bb_width <= _prev_bb_width:
            return None  # BB拡大していない → Release未発生

        # ── 方向判定 (bbpb) ──
        _is_buy = ctx.bbpb > self.BBPB_BUY_THRES
        _is_sell = ctx.bbpb < self.BBPB_SELL_THRES
        if not _is_buy and not _is_sell:
            return None

        # ── 陽線/陰線確認 ──
        if _is_buy and ctx.entry <= ctx.open_price:
            return None  # BUYなのに陰線
        if _is_sell and ctx.entry >= ctx.open_price:
            return None  # SELLなのに陽線

        # ── Body Ratio (実体/レンジ比率) ──
        _bar_range = abs(float(ctx.df.iloc[-1].get("High", ctx.entry))
                         - float(ctx.df.iloc[-1].get("Low", ctx.entry)))
        _body = abs(ctx.entry - ctx.open_price)
        _body_ratio = _body / _bar_range if _bar_range > 0 else 0
        if _body_ratio < self.BODY_RATIO_MIN:
            return None

        # ── Bar Range vs ATR (vol_surge概念: ノイズではなく有意な動き) ──
        if _bar_range < ctx.atr * self.BAR_RANGE_ATR_MIN:
            return None

        # ══════════════════════════════════════════════════
        # FILTER 3: Momentum — MACD-H + ADX
        # ══════════════════════════════════════════════════

        # ── MACD-H 方向一致 + 拡大 ──
        if _is_buy and ctx.macdh <= 0:
            return None
        if _is_sell and ctx.macdh >= 0:
            return None
        if abs(ctx.macdh) <= abs(ctx.macdh_prev):
            return None  # MACD-H拡大していない

        # ── ADX >= 18 OR ADX上昇 +2.0 ──
        # 前足のADXを取得
        _prev_adx = float(_prev_row.get("adx", 0)) if "adx" in _prev_row.index else 0
        _adx_rising = (ctx.adx - _prev_adx) >= self.ADX_RISE_THRES if _prev_adx > 0 else False
        if ctx.adx < self.ADX_MIN and not _adx_rising:
            return None

        # ── DI方向一致 ──
        if _is_buy and ctx.adx_pos <= ctx.adx_neg:
            return None
        if _is_sell and ctx.adx_neg <= ctx.adx_pos:
            return None

        # ══════════════════════════════════════════════════
        # FILTER 4: HTF — 上位足非逆行
        # ══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if _is_buy and _agreement == "bear":
            return None
        if _is_sell and _agreement == "bull":
            return None

        # ══════════════════════════════════════════════════
        # FILTER 5: Freshness — 前足BB外ブレイク済みでないこと
        # 「すでに発車したバス」への飛び乗り禁止
        # ══════════════════════════════════════════════════
        _prev_bbpb = float(_prev_row.get("bb_pband", 0.5))
        if _is_buy and _prev_bbpb >= self.PREV_BAR_BBPB_MAX:
            return None  # 前足ですでにBB上方ブレイク済み
        if _is_sell and _prev_bbpb <= self.PREV_BAR_BBPB_MIN:
            return None  # 前足ですでにBB下方ブレイク済み

        # ══════════════════════════════════════════════════
        # Spread Guard: ATR/Spread >= 8
        # ══════════════════════════════════════════════════
        if ctx.atr > 0 and hasattr(ctx, "df") and ctx.df is not None:
            _spread_col = "spread" if "spread" in ctx.df.columns else None
            if _spread_col:
                _spread = float(ctx.df.iloc[-1].get(_spread_col, 0))
                if _spread > 0 and (ctx.atr / _spread) < self.ATR_SPREAD_MIN:
                    return None

        # ══════════════════════════════════════════════════
        # USD/JPY SELL 非対称フィルター (DMB準拠)
        # 金利差逆行: ADX>=25 + 1D EMA50 falling required
        # ══════════════════════════════════════════════════
        if _sym == "USDJPY" and _is_sell:
            if ctx.adx < 25:
                return None  # 弱トレンドでのJPY SELL禁止

        # ═══════════════════════════════════════════════════
        # 全フィルター通過 — シグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        score = self.SCORE_BASE
        reasons = []

        # ── SL計算: Swing H/L ± ATR×0.3 ──
        _lookback = min(self.SL_SWING_LOOKBACK, len(ctx.df) - 1)
        if _is_buy:
            _swing_val = float(ctx.df["Low"].iloc[-_lookback:].min())
            sl = _swing_val - ctx.atr * self.SL_ATR_BUFFER
        else:
            _swing_val = float(ctx.df["High"].iloc[-_lookback:].max())
            sl = _swing_val + ctx.atr * self.SL_ATR_BUFFER

        # SLキャップ: ATR×0.8 ≤ SL距離 ≤ ATR×1.5
        _sl_dist = abs(ctx.entry - sl)
        _sl_max_dist = ctx.atr * self.SL_ATR_MAX
        _sl_min_dist = ctx.atr * self.SL_ATR_MIN
        if _sl_dist > _sl_max_dist:
            sl = ctx.entry - _sl_max_dist if _is_buy else ctx.entry + _sl_max_dist
            _sl_dist = _sl_max_dist
        elif _sl_dist < _sl_min_dist:
            sl = ctx.entry - _sl_min_dist if _is_buy else ctx.entry + _sl_min_dist
            _sl_dist = _sl_min_dist

        # ── TP計算: ATR×2.5 (MIN_RR保証) ──
        _tp_target = ctx.atr * self.TP_ATR_MULT
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        if _is_buy:
            tp = ctx.entry + _tp_dist
        else:
            tp = ctx.entry - _tp_dist

        # ── RR最低保証チェック ──
        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0
        if _rr < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # Reasons (テレメトリ)
        # ═══════════════════════════════════════════════════
        _adx_delta = ctx.adx - _prev_adx if _prev_adx > 0 else 0
        _pip_label = "JPY" if ctx.is_jpy else "EUR"
        _prec = 3 if ctx.is_jpy else 5

        reasons.append(
            f"✅ SRM {signal}: Squeeze Release Momentum | "
            f"squeeze_bars={_squeeze_bars} (≥{self.MIN_SQUEEZE_BARS}) "
            f"bb_width_pct={_bb_width_pct:.1f}"
        )
        reasons.append(
            f"✅ Release: bb_width {_prev_bb_width:.{_prec}f}→{ctx.bb_width:.{_prec}f} (拡大) | "
            f"bbpb={ctx.bbpb:.2f} body_ratio={_body_ratio:.0%}"
        )
        reasons.append(
            f"✅ Momentum: MACD-H={ctx.macdh:.{_prec}f}(prev={ctx.macdh_prev:.{_prec}f}) | "
            f"ADX={ctx.adx:.1f}(Δ{_adx_delta:+.1f}) "
            f"+DI={ctx.adx_pos:.1f} -DI={ctx.adx_neg:.1f}"
        )
        reasons.append(
            f"✅ HTF={_agreement} | Freshness: prev_bbpb={_prev_bbpb:.2f}"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.{_prec}f} TP={tp:.{_prec}f} "
            f"(Swing={'L' if _is_buy else 'H'}={_swing_val:.{_prec}f}) ({_pip_label})"
        )

        # ═══════════════════════════════════════════════════
        # スコアボーナス
        # ═══════════════════════════════════════════════════

        # squeeze_bars 長期蓄積ボーナス (6本=1.5h以上 → エネルギー大)
        if _squeeze_bars >= 6:
            score += 0.5
            reasons.append(f"✅ 長期圧縮({_squeeze_bars}本≥6)")

        # ADX強度ボーナス (≥25: 明確なトレンド)
        if ctx.adx >= 25:
            score += 0.5
            reasons.append(f"✅ 強ADX({ctx.adx:.1f}≥25)")

        # ADX急上昇ボーナス
        if _adx_rising:
            score += 0.3
            reasons.append(f"✅ ADX急上昇(Δ{_adx_delta:+.1f}≥{self.ADX_RISE_THRES})")

        # HTF方向一致ボーナス
        if (_is_buy and _agreement == "bull") or (_is_sell and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF完全一致({_agreement})")

        # EMA200方向一致ボーナス
        if (_is_buy and ctx.entry > ctx.ema200) or (_is_sell and ctx.entry < ctx.ema200):
            score += 0.3
            reasons.append("✅ EMA200方向一致")

        # EMA整列ボーナス (パーフェクトオーダー)
        if _is_buy and ctx.ema9 > ctx.ema21 > ctx.ema50:
            score += 0.3
            reasons.append("✅ EMA PO (9>21>50)")
        elif _is_sell and ctx.ema9 < ctx.ema21 < ctx.ema50:
            score += 0.3
            reasons.append("✅ EMA PO (9<21<50)")

        # Body Ratio強度ボーナス (≥0.60 = 非常に強い確信足)
        if _body_ratio >= 0.60:
            score += 0.3
            reasons.append(f"✅ 強確信足(body_ratio={_body_ratio:.0%}≥60%)")

        conf = int(min(85, 50 + score * 4))

        return Candidate(
            signal=signal,
            confidence=conf,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
