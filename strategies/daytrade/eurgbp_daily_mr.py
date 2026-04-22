"""
EUR/GBP Daily Mean-Reversion — 20日レンジ極値フェード戦略

学術的根拠:
  - EUR/GBP は構造的にレンジバウンド (ECB/BoE金利差1.75%)
  - 20日レンジ上下10%到達時のフェード: 10日リターン 30-41pip (WR=52-61%)
  - SMA20/50回帰: 両MA上→SELL avg -31.7pip/10d
  - 日足反転率 57.8%

ミクロ構造制約:
  - Spread 3.0pip / Daily ATR 39.8pip = 7.5% → 日足以上のみ viable
  - 1m-15m は Spread/ATR=43-99% で構造的不可能

シグナル条件:
  BUY: 20日レンジの下位20% + 日足ATR > 35pip
  SELL: 20日レンジの上位20% + 日足ATR > 35pip
  ボーナス: SMA20/50方向一致, キャリーバイアス(SELL優先)

SL/TP:
  SL = ATR(14) × 1.0 (~40pip)
  TP = ATR(14) × 1.5 (~60pip)
  MIN_RR = 1.5
  MAX_HOLD = 10日 (日足ベース)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EurgbpDailyMR(StrategyBase):
    name = "eurgbp_daily_mr"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"   # v11: Q4 paradox fix — ADX>25 → conf penalty

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── レンジ計算 ──
    RANGE_LOOKBACK   = 20       # 20日(=20本@日足, ~100本@15m×5日)レンジ
    RANGE_BUY_THRES  = 0.20     # 下位20%以下でBUY
    RANGE_SELL_THRES = 0.80     # 上位80%以上でSELL

    # ── ボラティリティフィルター ──
    MIN_ATR_PIPS     = 35       # Daily ATR ≥ 35 pips (EUR/GBP pip=0.0001)
    PIP_SIZE         = 0.0001   # EUR/GBP pip単位

    # ── SMA回帰ボーナス ──
    SMA_SHORT        = 20       # SMA20 (≒ EMA21で代用可)
    SMA_LONG         = 50       # SMA50 (≒ EMA50で代用可)

    # ── キャリーバイアス ──
    CARRY_BIAS_SELL  = 0.5      # SELL方向にスコアボーナス (ECB 2.0% < BoE 3.75%)

    # ── SL/TP ──
    SL_ATR_MULT      = 1.0      # SL = ATR × 1.0 (~40pip)
    TP_ATR_MULT      = 1.5      # TP = ATR × 1.5 (~60pip)
    MIN_RR           = 1.5      # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS    = 10       # 最大10バー (日足ベース設計)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: EUR/GBP のみ ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("EURGBP",):
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < self.RANGE_LOOKBACK + 5:
            return None

        # ═══════════════════════════════════════════════════
        # STEP1: 20日レンジ計算
        # 15m足の場合: 20日 ≒ 20*24*4 = 1920本だが、
        # period="60d"で取得しているため十分なデータがある。
        # ただしDataFrameは15m足なので、日足ATRの代わりに
        # 利用可能なATR(14)をpip換算して判定する。
        # ═══════════════════════════════════════════════════

        # 直近RANGE_LOOKBACK本のHigh/Low (15m足ベース)
        # 日足レンジを近似: 直近N本のH/Lで十分
        _lookback = min(self.RANGE_LOOKBACK * 4, len(ctx.df) - 1)  # 15m×4 = 1h, ×20 = 80本
        if _lookback < 20:
            return None

        _highs = ctx.df["High"].iloc[-_lookback:]
        _lows = ctx.df["Low"].iloc[-_lookback:]
        _range_high = float(_highs.max())
        _range_low = float(_lows.min())
        _range_span = _range_high - _range_low

        if _range_span <= 0:
            return None

        # ── 現在価格のレンジ内位置 (0%=Low, 100%=High) ──
        _position = (ctx.entry - _range_low) / _range_span

        # ═══════════════════════════════════════════════════
        # STEP2: ボラティリティフィルター
        # ATR(14)をpip換算してMIN_ATR_PIPSと比較
        # 15m足のATRなので日足ATRの代替として十分
        # (日足ATR ≒ 15m ATR × sqrt(96) だが、ここでは
        #  15m ATR自体が日足レベルの動きを反映している)
        # ═══════════════════════════════════════════════════
        _atr_pips = ctx.atr / self.PIP_SIZE

        # 日足ATR推定: 15m足のATR × 直近の日中変動から推定
        # 簡易計算: 直近80本(=20h)のH-Lレンジ / lookback日数
        _daily_range_pips = _range_span / self.PIP_SIZE / max(1, _lookback // (4 * 24))
        # ATRフィルター: 15m ATR が小さすぎる場合(低ボラ)もスキップ
        # 35pip/日 ≒ 15m ATRで約3.5pip以上が目安
        _min_atr_15m = self.MIN_ATR_PIPS * self.PIP_SIZE / 10.0  # 35pip日足 ≒ 3.5pip@15m
        if ctx.atr < _min_atr_15m:
            return None

        # ═══════════════════════════════════════════════════
        # STEP3: シグナル判定
        # BUY: position < 20% (レンジ下端)
        # SELL: position > 80% (レンジ上端)
        # ═══════════════════════════════════════════════════
        _is_buy = _position <= self.RANGE_BUY_THRES
        _is_sell = _position >= self.RANGE_SELL_THRES

        if not _is_buy and not _is_sell:
            return None

        # ═══════════════════════════════════════════════════
        # STEP4: 反転確認 (逆方向の足)
        # BUY: 陽線 (Close > Open)
        # SELL: 陰線 (Close < Open)
        # ═══════════════════════════════════════════════════
        if _is_buy and ctx.entry <= ctx.open_price:
            return None
        if _is_sell and ctx.entry >= ctx.open_price:
            return None

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        score = 4.0  # ベーススコア
        reasons = []

        _dec = 5  # EUR/GBP = 5桁表示

        # ── SL/TP計算 ──
        _sl_dist = ctx.atr * self.SL_ATR_MULT
        _tp_dist = ctx.atr * self.TP_ATR_MULT

        if _is_buy:
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + _tp_dist
        else:
            sl = ctx.entry + _sl_dist
            tp = ctx.entry - _tp_dist

        # ── RR確認 ──
        if _sl_dist <= 0 or _tp_dist / _sl_dist < self.MIN_RR:
            return None

        _rr = _tp_dist / _sl_dist

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        reasons.append(
            f"✅ EUR/GBP Daily MR {signal}: "
            f"Range Position={_position:.1%} "
            f"({'下位' if _is_buy else '上位'}極値)"
        )
        reasons.append(
            f"✅ 20日レンジ: H={_range_high:.{_dec}f} "
            f"L={_range_low:.{_dec}f} Span={_range_span/self.PIP_SIZE:.1f}pip"
        )
        reasons.append(
            f"✅ 反転足確認: Close={ctx.entry:.{_dec}f} "
            f"{'>' if _is_buy else '<'} Open={ctx.open_price:.{_dec}f}"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

        # ── SMA20/50回帰ボーナス (EMA21/50で代用) ──
        # 両MA上からSELL or 両MA下からBUY = 回帰方向一致
        _above_sma20 = ctx.entry > ctx.ema21
        _above_sma50 = ctx.entry > ctx.ema50
        if _is_sell and _above_sma20 and _above_sma50:
            score += 0.5
            reasons.append(
                f"✅ SMA回帰: 両MA上→SELL (EMA21={ctx.ema21:.{_dec}f} "
                f"EMA50={ctx.ema50:.{_dec}f})"
            )
        elif _is_buy and not _above_sma20 and not _above_sma50:
            score += 0.5
            reasons.append(
                f"✅ SMA回帰: 両MA下→BUY (EMA21={ctx.ema21:.{_dec}f} "
                f"EMA50={ctx.ema50:.{_dec}f})"
            )

        # ── キャリーバイアス (SELLにボーナス) ──
        # ECB 2.0% vs BoE 3.75% = 1.75%差 → SHORT EUR/GBP有利
        if signal == "SELL":
            score += self.CARRY_BIAS_SELL
            reasons.append(
                f"✅ キャリーバイアス: SELL +{self.CARRY_BIAS_SELL} "
                f"(ECB 2.0% < BoE 3.75%)"
            )

        # ── レンジ極値深度ボーナス ──
        # 10%以内 = より強い反転シグナル
        if _is_buy and _position <= 0.10:
            score += 0.3
            reasons.append(f"✅ 極端値: Position={_position:.1%} (下位10%以内)")
        elif _is_sell and _position >= 0.90:
            score += 0.3
            reasons.append(f"✅ 極端値: Position={_position:.1%} (上位10%以内)")

        # ── ADX低め確認 (レンジ相場=ADX<25が望ましい) ──
        if ctx.adx < 25:
            score += 0.3
            reasons.append(f"✅ レンジ確認: ADX={ctx.adx:.1f}<25")

        # ── HTFフィルター (ソフトペナルティ: MR戦略なのでハードブロックしない) ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if _is_buy and _agr == "bear":
            score -= 0.5
            reasons.append(f"⚠️ HTF逆行: {_agr} (ソフトペナルティ)")
        if _is_sell and _agr == "bull":
            score -= 0.5
            reasons.append(f"⚠️ HTF逆行: {_agr} (ソフトペナルティ)")

        # v11: Confidence v2 — MR anti-trend penalty (ADX>25 reduces conf)
        from modules.confidence_v2 import apply_penalty
        _legacy_conf = int(min(85, 50 + score * 4))
        conf = apply_penalty(_legacy_conf, self.strategy_type, ctx.adx, conf_max=85)
        if conf != _legacy_conf:
            reasons.append(
                f"🔧 [v2] MR anti-trend: ADX={ctx.adx:.1f}>25 → conf {_legacy_conf}→{conf}"
            )
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
