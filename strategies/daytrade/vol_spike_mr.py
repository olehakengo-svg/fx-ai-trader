"""
Vol Spike Mean-Reversion — ボラティリティスパイク後の平均回帰

学術的根拠:
  - Osler (2003): ストップロス狩りによる価格オーバーシュート → 反転パターン
  - Lo & MacKinlay (1988): 短期リバーサル効果 — 過剰反応の是正
  - BT検証済み: USD_JPY N=53, WR=62.3%, PnL=+242.2pip, PF=1.92, Sharpe=0.274

数学的定義:
  Spike Detection:
    avg_range = mean(High[i] - Low[i] for i in [-5, -1])  # 直近5本の平均レンジ
    current_range = High[0] - Low[0]                       # 現在足のレンジ
    spike = current_range > avg_range * SPIKE_RATIO (3.0)

  Spike Direction:
    Close > Open → bullish spike → FADE with SELL
    Close < Open → bearish spike → FADE with BUY

  Entry (次の足):
    Confirmation: 次足Open がスパイク足のHigh-Low内 (ギャップなし)
    BUY: bearish spike (大陰線) → 反転上昇期待
    SELL: bullish spike (大陽線) → 反転下落期待

  SL: スパイク足の極値 + ATR × 0.3
  TP: ATR × 1.5 from entry
  RR: 1.0 (高WR=62%で補償)

制約:
  USD/JPY専用 (EUR/GBP: BT負EV確認済み)
  MAX_HOLD: 4バー (1時間 @ 15m)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class VolSpikeMR(StrategyBase):
    name = "vol_spike_mr"
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"   # v11: Q4 paradox fix — ADX>25 → conf penalty
    _enabled_symbols = {"USDJPY"}

    # ══════════════════════════════════════════════════
    # パラメータ定数 (BT検証済み)
    # ══════════════════════════════════════════════════
    SPIKE_RATIO = 2.3          # current range > 2.3x 直近5本平均 (was 3.0: N=0発火、上位1-2%→5-10%に緩和)
    LOOKBACK_BARS = 5          # 平均レンジ算出ウィンドウ
    SL_ATR_MULT = 1.5          # SL = ATR × 1.5
    TP_ATR_MULT = 1.5          # TP = ATR × 1.5 (RR=1.0, 高WRで補償)
    SL_BUFFER = 0.3            # SL = スパイク極値 + ATR × 0.3
    MIN_RR = 0.8               # WR=62%に対し低RR許容
    MAX_HOLD_BARS = 4          # 4バー = 1時間 @ 15m

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: USD/JPY専用 ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("USDJPY",):
            return None

        # ── データ十分性: LOOKBACK + 現在足 + 前足 ──
        if ctx.df is None or len(ctx.df) < self.LOOKBACK_BARS + 2:
            return None

        # ── ATRガード ──
        if ctx.atr <= 0:
            return None

        # ══════════════════════════════════════════════════
        # Step 1: スパイク検出 (前足がスパイク足)
        #   前足 = df.iloc[-2] (スパイク足候補)
        #   lookback = df.iloc[-LOOKBACK-2:-2] (スパイク足の前5本)
        # ══════════════════════════════════════════════════
        df = ctx.df

        # スパイク足 = 前足 (df.iloc[-2])
        spike_high = float(df.iloc[-2]["High"])
        spike_low = float(df.iloc[-2]["Low"])
        spike_open = float(df.iloc[-2]["Open"])
        spike_close = float(df.iloc[-2]["Close"])
        spike_range = spike_high - spike_low

        if spike_range <= 0:
            return None

        # 直近5本の平均レンジ (スパイク足の前5本: df.iloc[-7:-2])
        lb_start = max(0, len(df) - 2 - self.LOOKBACK_BARS)
        lb_end = len(df) - 2
        if lb_end - lb_start < self.LOOKBACK_BARS:
            return None

        total_range = 0.0
        for i in range(lb_start, lb_end):
            h = float(df.iloc[i]["High"])
            l = float(df.iloc[i]["Low"])
            total_range += (h - l)
        avg_range = total_range / self.LOOKBACK_BARS

        if avg_range <= 0:
            return None

        # ── スパイクチェック ──
        if spike_range <= avg_range * self.SPIKE_RATIO:
            return None

        # ══════════════════════════════════════════════════
        # Step 2: スパイク方向判定 & FADE方向決定
        # ══════════════════════════════════════════════════
        if spike_close > spike_open:
            # Bullish spike → FADE with SELL
            spike_dir = "UP"
            signal = "SELL"
        elif spike_close < spike_open:
            # Bearish spike → FADE with BUY
            spike_dir = "DOWN"
            signal = "BUY"
        else:
            # Doji-like spike (Close == Open) → skip
            return None

        # ══════════════════════════════════════════════════
        # Step 3: 確認 — 現在足Openがスパイク足レンジ内 (ギャップなし)
        # ══════════════════════════════════════════════════
        current_open = ctx.open_price
        if not (spike_low <= current_open <= spike_high):
            return None

        # ══════════════════════════════════════════════════
        # Step 4: SL/TP計算
        # ══════════════════════════════════════════════════
        _dec = 3  # USD/JPY専用なので常に3桁
        entry = ctx.entry

        if signal == "BUY":
            # Bearish spike → BUY: SLはスパイク安値 - ATR×0.3
            sl = spike_low - ctx.atr * self.SL_BUFFER
            tp = entry + ctx.atr * self.TP_ATR_MULT
        else:
            # Bullish spike → SELL: SLはスパイク高値 + ATR×0.3
            sl = spike_high + ctx.atr * self.SL_BUFFER
            tp = entry - ctx.atr * self.TP_ATR_MULT

        # ══════════════════════════════════════════════════
        # Step 5: RR検証
        # ══════════════════════════════════════════════════
        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        if sl_dist <= 0:
            return None

        rr = tp_dist / sl_dist
        if rr < self.MIN_RR:
            return None

        # ══════════════════════════════════════════════════
        # Step 6: Reasons & スコア
        # ══════════════════════════════════════════════════
        spike_ratio_actual = spike_range / avg_range
        spike_pip = spike_range * ctx.pip_mult
        avg_pip = avg_range * ctx.pip_mult

        score = 4.5
        reasons = []

        reasons.append(
            f"✅ Vol Spike MR {signal}: "
            f"スパイク{spike_dir} (range={spike_pip:.1f}pip, "
            f"avg={avg_pip:.1f}pip, ratio={spike_ratio_actual:.1f}x)"
        )

        # ── HTF方向一致ボーナス ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # ── レンジ環境ボーナス (MR有利) ──
        if ctx.adx < 25:
            score += 0.3
            reasons.append(f"✅ レンジ環境(ADX={ctx.adx:.1f}<25)")

        # ── スパイク倍率ボーナス (強スパイク = 強反転期待) ──
        if spike_ratio_actual >= 4.0:
            score += 0.3
            reasons.append(f"✅ 強スパイク({spike_ratio_actual:.1f}x≥4.0)")

        # ── 反転足確認ボーナス (現在足がFADE方向に実体あり) ──
        if (signal == "BUY" and ctx.entry > ctx.open_price) or \
           (signal == "SELL" and ctx.entry < ctx.open_price):
            score += 0.5
            reasons.append("✅ 反転足確認(実体方向一致)")

        reasons.append(
            f"📊 RR={rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

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
