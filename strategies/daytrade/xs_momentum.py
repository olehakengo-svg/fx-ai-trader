"""
Cross-Sectional Currency Momentum (XS Momentum)
    — 通貨ペア内モメンタム正規化による順張りエントリー

学術的根拠:
  - Menkhoff et al (2012, JFE): 通貨モメンタムは株式と同様に
    統計的に有意なリターンを持つ。Winner通貨は継続的に上昇。
  - Eriksen (2019, JEF): 通貨間ディスパージョン(分散)が高い
    期間でモメンタム戦略のリターンが向上 (タイミングフィルター)。

実装背景:
  - 本来はクロスセクション(複数ペア比較)だが、StrategyBase の
    evaluate() は単一ペア ctx を受け取るため、ペア内正規化版を実装。
  - 20バーリターンを ATR で正規化 → 1.0 ATR 超 = 強モメンタム。
  - ディスパージョンフィルター: 20バー High-Low レンジ / ATR > 3.0
    → 市場分散が大きい = モメンタム環境。

数学的定義:
  Normalized Momentum:
    mom = (Close[-1] - Close[-21]) / ATR(14)

  Entry:
    BUY:  mom > 1.0 AND EMA9 > EMA21 AND Close > Open (confirmation)
    SELL: mom < -1.0 AND EMA9 < EMA21 AND Close < Open (confirmation)

  Dispersion Filter:
    disp = (max(High[-20:]) - min(Low[-20:])) / ATR(14)
    disp > 3.0 → signal quality bonus

  Trend Filter:
    ADX >= 20 (need directional trend for momentum)

  SL: ATR(15m) x 1.5
  TP: ATR(15m) x 3.0  (momentum = higher RR)
  MIN_RR: 1.5
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class XsMomentum(StrategyBase):
    name = "xs_momentum"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── モメンタム計算 ──
    MOM_LOOKBACK     = 20       # 20バーリターン計測期間
    MOM_THRESHOLD    = 1.0      # モメンタム閾値 (ATR単位)

    # ── ディスパージョン ──
    DISP_THRESHOLD   = 3.0      # 分散閾値 (ATR単位)

    # ── トレンドフィルター ──
    ADX_MIN          = 20       # ADX最低要件

    # ── SL/TP ──
    SL_ATR_MULT      = 1.5      # SL = ATR x 1.5
    TP_ATR_MULT      = 3.0      # TP = ATR x 3.0 (高RR)
    MIN_RR           = 1.5      # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS    = 16       # 最大16バー (4時間 @ 15m)

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    def _calc_momentum(self, df, atr: float) -> float:
        """20バー正規化モメンタムを計算。ATR単位で返す。"""
        if len(df) < self.MOM_LOOKBACK + 1:
            return 0.0
        current_close = float(df.iloc[-1]["Close"])
        past_close = float(df.iloc[-(self.MOM_LOOKBACK + 1)]["Close"])
        if atr <= 0:
            return 0.0
        return (current_close - past_close) / atr

    def _calc_dispersion(self, df, atr: float) -> float:
        """20バーのHigh-Lowレンジ / ATR でディスパージョンを計算。"""
        if len(df) < self.MOM_LOOKBACK:
            return 0.0
        recent = df.iloc[-self.MOM_LOOKBACK:]
        range_hl = float(recent["High"].max()) - float(recent["Low"].min())
        if atr <= 0:
            return 0.0
        return range_hl / atr

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター (主要3ペア) ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("EURUSD", "USDJPY", "GBPUSD"):
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < self.MOM_LOOKBACK + 5:
            return None

        # ── ATR ガード ──
        if ctx.atr <= 0:
            return None

        # ── ADX トレンドフィルター ──
        if ctx.adx < self.ADX_MIN:
            return None

        # v8.6: 金曜ブロック撤去 — Menkhoff (2012): モメンタムは曜日非依存

        # ═══════════════════════════════════════════════════
        # モメンタム計算
        # ═══════════════════════════════════════════════════
        _mom = self._calc_momentum(ctx.df, ctx.atr)

        # モメンタム閾値チェック
        if abs(_mom) < self.MOM_THRESHOLD:
            return None

        # ═══════════════════════════════════════════════════
        # ディスパージョン計算
        # ═══════════════════════════════════════════════════
        _disp = self._calc_dispersion(ctx.df, ctx.atr)
        _high_disp = _disp > self.DISP_THRESHOLD

        # ═══════════════════════════════════════════════════
        # 方向判定 + EMAフィルター
        # ═══════════════════════════════════════════════════
        signal = None
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        if _mom > self.MOM_THRESHOLD:
            # BUY: 上昇モメンタム
            if ctx.ema9 <= ctx.ema21:
                return None  # EMAトレンド不一致
            if ctx.entry <= ctx.open_price:
                return None  # 確認足不成立 (陰線)
            signal = "BUY"
        elif _mom < -self.MOM_THRESHOLD:
            # SELL: 下降モメンタム
            if ctx.ema9 >= ctx.ema21:
                return None  # EMAトレンド不一致
            if ctx.entry >= ctx.open_price:
                return None  # 確認足不成立 (陽線)
            signal = "SELL"
        else:
            return None

        # ═══════════════════════════════════════════════════
        # SL/TP 計算
        # ═══════════════════════════════════════════════════
        _sl_dist = ctx.atr * self.SL_ATR_MULT
        _tp_dist = ctx.atr * self.TP_ATR_MULT

        if signal == "BUY":
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + _tp_dist
        else:
            sl = ctx.entry + _sl_dist
            tp = ctx.entry - _tp_dist

        # ═══════════════════════════════════════════════════
        # RR 検証
        # ═══════════════════════════════════════════════════
        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None

        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # スコア & Reasons
        # ═══════════════════════════════════════════════════
        score = 4.0
        reasons = []

        # モメンタム強度ボーナス (+0.3 per ATR unit)
        _mom_bonus = abs(_mom) * 0.3
        score += _mom_bonus
        reasons.append(
            f"{'BUY' if signal == 'BUY' else 'SELL'} "
            f"XS Momentum: mom={_mom:+.2f}ATR "
            f"(lookback={self.MOM_LOOKBACK}bars)"
        )

        # ディスパージョンボーナス
        if _high_disp:
            score += 0.5
            reasons.append(
                f"Dispersion={_disp:.1f}ATR > {self.DISP_THRESHOLD} "
                f"(Eriksen 2019: momentum timing)"
            )

        # EMAアライメントボーナス
        score += 0.5
        reasons.append(
            f"EMA alignment: EMA9={ctx.ema9:.{_dec}f} "
            f"{'>' if signal == 'BUY' else '<'} "
            f"EMA21={ctx.ema21:.{_dec}f}"
        )

        # ADX強度ボーナス
        if ctx.adx >= 30:
            score += 0.3
            reasons.append(f"Strong trend ADX={ctx.adx:.1f}>=30")

        # HTF方向一致ボーナス
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"HTF alignment ({_agr})")

        # RR情報
        reasons.append(f"RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
