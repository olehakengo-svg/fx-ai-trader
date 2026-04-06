"""
EMA Ribbon Ride — パーフェクトオーダー押し目戦略 (Trend Pullback Scalp)

概要:
  EMA 20/50/200 がパーフェクトオーダー（完全順列）の時のみ、
  1分足の短い押し目でエントリー。逆張りが負けやすい 12:00-17:00 UTC に
  優先的に発火する「時間帯特化型順張りエンジン」。

学術的根拠:
  - パーフェクトオーダー: 短期EMA > 中期EMA > 長期EMA の完全順列はトレンドの
    成熟期を示す (Murphy 1999, "Technical Analysis of the Financial Markets")
  - 押し目買い/戻り売り: トレンドフォローの最高効率エントリーポイント
    (Jegadeesh & Titman 1993, "Returns to Buying Winners and Selling Losers")
  - 12-17 UTC: London/NY overlap セッションで逆張り戦略のWR低下が顕著
    → 同時間帯を順張り側で活用する補完設計

エントリー:
  BUY:  EMA9 > EMA21 > EMA50 > EMA200 (Bull PO)
        AND Close が EMA9 まで押し戻された (EMA9 近接 within 0.5 ATR)
        AND RSI5 < 55 (過熱でない)
        AND 現在足が陽線 (押し目反転確認)
  SELL: EMA9 < EMA21 < EMA50 < EMA200 (Bear PO)
        AND Close が EMA9 まで戻した
        AND RSI5 > 45
        AND 現在足が陰線

時間帯フィルター:
  - 12:00-17:00 UTC: スコア +1.0 ボーナス（最優先発火域）
  - 08:00-11:00 / 18:00-21:00 UTC: 標準スコア
  - その他 (00-07, 22-23): スコア -0.5 ペナルティ（低ボラ帯）

決済:
  TP: ATR7 × 1.5 (トレンド方向に乗る)
  SL: EMA21 の反対側 + ATR7 × 0.3 (PO崩壊 = 撤退)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class EmaRibbonRide(StrategyBase):
    name = "ema_ribbon_ride"
    mode = "scalp"
    enabled = True

    # ── チューナブルパラメータ ──
    ema_proximity_atr = 0.5    # EMA9近接判定 (ATR7 × この値以内)
    rsi_buy_max = 55           # BUY時のRSI上限
    rsi_sell_min = 45          # SELL時のRSI下限
    tp_mult = 1.5              # TP = ATR7 × tp_mult (デフォルト)
    adx_min = 18               # 最低ADX（トレンド存在の最低証拠）

    # ── ペア別TP倍率 (BT最適化 2026-04-06) ──
    # EUR/JPY: WR=59.3% → TP短縮で勝率安定化
    _tp_mult_by_pair = {
        "EURJPY": 1.3,
    }

    # ── 通貨ペアフィルター (BT検証 2026-04-06) ──
    # USD/JPY EV=+0.353, EUR/JPY EV=+0.206, XAU/USD EV=+0.262 → 有効
    # EUR/USD EV=-0.086, GBP/USD EV=-0.571, EUR/GBP EV=-0.290 → 無効
    _enabled_symbols = frozenset({
        "USDJPY", "EURJPY", "XAUUSD",        # yfinance形式 (=X除去後)
    })

    # ── 時間帯スコア調整 ──
    _prime_hours = frozenset(range(12, 18))      # 12-17 UTC: +1.0
    _ok_hours = frozenset(range(8, 12)) | frozenset(range(18, 22))  # 8-11, 18-21 UTC: 0
    # それ以外: -0.5 penalty

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── 通貨ペアフィルター: BT正EVペアのみ発火 ──
        _sym_clean = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym_clean not in self._enabled_symbols:
            return None

        # ── 最低ADX要件: トレンドが存在しない環境を排除 ──
        if ctx.adx < self.adx_min:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _min_sl = 0.030 if ctx.is_jpy else 0.00030

        # ── パーフェクトオーダー判定 ──
        bull_po = (ctx.ema9 > ctx.ema21 > ctx.ema50 > ctx.ema200)
        bear_po = (ctx.ema9 < ctx.ema21 < ctx.ema50 < ctx.ema200)

        if not bull_po and not bear_po:
            return None

        # ── EMA9近接判定: 押し目/戻りが発生しているか ──
        ema9_dist = abs(ctx.entry - ctx.ema9)
        proximity_threshold = ctx.atr7 * self.ema_proximity_atr

        if ema9_dist > proximity_threshold:
            return None  # EMA9から遠すぎる = 押し目ではなく乖離中

        # ── BUY: Bull Perfect Order + 押し目反転 ──
        if bull_po and ctx.rsi5 < self.rsi_buy_max:
            # 現在足が陽線 = 押し目からの反転確認
            if ctx.entry > ctx.open_price:
                signal = "BUY"
                score = 3.0

                reasons.append(f"✅ パーフェクトオーダー(EMA9>{ctx.ema9:.5g}>21>{ctx.ema21:.5g}>50>200)")
                reasons.append(f"✅ EMA9押し目(距離={ema9_dist/ctx.atr7:.2f}ATR≤{self.ema_proximity_atr})")
                reasons.append(f"✅ 陽線反転(C={ctx.entry:.5g}>O={ctx.open_price:.5g})")
                reasons.append(f"✅ RSI5非過熱({ctx.rsi5:.1f}<{self.rsi_buy_max})")

                # TP: トレンド方向にATR分
                tp = ctx.entry + ctx.atr7 * self.tp_mult
                # SL: EMA21の下 + バッファ（PO崩壊 = 撤退）
                sl_base = ctx.ema21 - ctx.atr7 * 0.3
                sl = min(sl_base, ctx.entry - _min_sl)

        # ── SELL: Bear Perfect Order + 戻り反転 ──
        elif bear_po and ctx.rsi5 > self.rsi_sell_min:
            if ctx.entry < ctx.open_price:
                signal = "SELL"
                score = 3.0

                reasons.append(f"✅ パーフェクトオーダー(EMA9<{ctx.ema9:.5g}<21<{ctx.ema21:.5g}<50<200)")
                reasons.append(f"✅ EMA9戻り(距離={ema9_dist/ctx.atr7:.2f}ATR≤{self.ema_proximity_atr})")
                reasons.append(f"✅ 陰線反転(C={ctx.entry:.5g}<O={ctx.open_price:.5g})")
                reasons.append(f"✅ RSI5非過冷({ctx.rsi5:.1f}>{self.rsi_sell_min})")

                tp = ctx.entry - ctx.atr7 * self.tp_mult
                sl_base = ctx.ema21 + ctx.atr7 * 0.3
                sl = max(sl_base, ctx.entry + _min_sl)

        if signal is None:
            return None

        # ── ペア別TP倍率適用 ──
        _effective_tp_mult = self._tp_mult_by_pair.get(_sym_clean, self.tp_mult)
        if tp != 0.0:
            if signal == "BUY":
                tp = ctx.entry + ctx.atr7 * _effective_tp_mult
            else:
                tp = ctx.entry - ctx.atr7 * _effective_tp_mult

        # ── 時間帯スコア調整 (12-17 UTC 最優先) ──
        if ctx.hour_utc in self._prime_hours:
            score += 1.0
            reasons.append(f"✅ プライムタイム(UTC {ctx.hour_utc}:00) — 逆張り弱体時間帯補完 +1.0")
        elif ctx.hour_utc in self._ok_hours:
            pass  # 標準スコア
        else:
            score -= 0.5
            reasons.append(f"⚠️ 低ボラ時間帯(UTC {ctx.hour_utc}:00) — スコア -0.5")

        # ── スコアボーナス ──

        # ADX強度ボーナス
        if ctx.adx >= 30:
            score += 0.6
            reasons.append(f"✅ ADX強トレンド({ctx.adx:.1f}≥30) +0.6")
        elif ctx.adx >= 25:
            score += 0.3

        # EMA9-21 乖離方向ボーナス (EMA9がEMA21からどれだけ離れているか)
        ema_spread = abs(ctx.ema9 - ctx.ema21) / ctx.atr7 if ctx.atr7 > 0 else 0
        if ema_spread >= 0.5:
            score += 0.3
            reasons.append(f"✅ EMAスプレッド良好({ema_spread:.2f}ATR≥0.5)")

        # Stochastic 押し目確認ボーナス
        if signal == "BUY" and ctx.stoch_k < 40 and ctx.stoch_k > ctx.stoch_d:
            score += 0.4
            reasons.append(f"✅ Stoch押し目圏(K={ctx.stoch_k:.0f}<40)&ゴールデンクロス")
        elif signal == "SELL" and ctx.stoch_k > 60 and ctx.stoch_k < ctx.stoch_d:
            score += 0.4
            reasons.append(f"✅ Stoch戻り圏(K={ctx.stoch_k:.0f}>60)&デッドクロス")

        # MACD方向一致
        if signal == "BUY" and ctx.macdh > 0 and ctx.macdh > ctx.macdh_prev:
            score += 0.2
        elif signal == "SELL" and ctx.macdh < 0 and ctx.macdh < ctx.macdh_prev:
            score += 0.2

        # ── Confidence ──
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
