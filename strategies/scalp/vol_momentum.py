"""
Vol Momentum Scalp — 順張りブレイクアウト戦略 (Trend-Following Scalp)

概要:
  ADX >= 30（強トレンド環境）かつ、ローソク足実体がBBの2σを突き抜けた瞬間に
  その方向へ順張りエントリー。既存の逆張り戦略群(bb_rsi等)を補完する。

学術的根拠:
  - ADX >= 30 はトレンド発生の定量的閾値 (Wilder 1978, "New Concepts in Technical Trading")
  - BB σ2 ブレイクはボラティリティ拡大の初動を捕捉 (Bollinger 2001, "Bollinger on BB")
  - 順張り × 高ADX は逆張りの苦手な相場環境で正のEVを持つ (Jegadeesh & Titman 1993)

エントリー:
  BUY:  ADX >= 22 AND +DI > -DI AND %B >= 0.90 (≈σ1.8) AND Close > Open (陽線)
  SELL: ADX >= 22 AND -DI > +DI AND %B <= 0.10 (≈σ1.8) AND Close < Open (陰線)

決済:
  TP: ATR7 × 1.8 (モメンタム継続分を取る)
  SL: ATR7 × 0.8 (トレンド中はSL浅めでOK)
  システム側: ADX低下 or 5分足反転でSIGNAL_REVERSE

安全装置:
  - BB幅パーセンタイル > 40% 必須（レンジ内ノイズブレイクを排除）
  - RSI 極端値ブロック（RSI > 85 or < 15 は過熱 → 見送り）
  - スクイーズ直後は見送り（解放直後1本目は方向不定）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class VolMomentumScalp(StrategyBase):
    name = "vol_momentum_scalp"
    mode = "scalp"
    enabled = True

    # ── チューナブルパラメータ (2026-04-06 BT最適化) ──
    # ADX: 30→22 (5m/1m足で発火率改善、トレンド初動も捕捉)
    # BB %B: 1.0/0.0→0.90/0.10 (σ2.0→σ1.8相当、エントリー機会拡大)
    adx_min = 20            # トレンド強度の最低要件 (30→22→20: 初動捕捉)
    bbpb_buy = 0.90         # %B >= 0.90 ≈ σ1.8 上方ブレイク (1.0→0.90)
    bbpb_sell = 0.10        # %B <= 0.10 ≈ σ1.8 下方ブレイク (0.0→0.10)
    rsi_overbought = 85     # 過熱ブロック上限
    rsi_oversold = 15       # 過熱ブロック下限
    bb_width_pct_min = 0.35 # BBバンド幅パーセンタイル最低値 (0.40→0.35)
    tp_mult = 1.8           # TP = ATR7 × tp_mult
    sl_mult = 0.8           # SL = ATR7 × sl_mult

    # ── 通貨ペアフィルター (BT検証 2026-04-06, 14d/5m) ──
    # EUR/JPY EV=+0.362, GBP/USD EV=+0.160, XAU/USD EV=+0.179 → 有効
    # USD/JPY EV=-0.028 → 損益分岐点 (scalp主力ペアで発火機会確保、トレンド時のみ発火)
    # EUR/USD EV=-0.110, EUR/GBP EV=-0.070 → 無効
    _enabled_symbols = frozenset({
        "USDJPY", "EURJPY", "GBPUSD", "XAUUSD",
    })

    # ── セッションフィルター (2026-04-06 Session Matrix BT) ──
    # XAU/USD: Tokyo PF=1.65 ✅, London PF=∞ ✅, NY_Overlap PF=0.67 ❌, NY_Late PF=0.54 ❌
    # EUR/JPY: NY_Late PF=0.42 ❌
    # → XAU/USD NY時間帯ブロック, EUR/JPY NY_Late ブロック
    _blocked_hours_by_pair = {
        "XAUUSD": frozenset(range(12, 24)),  # NY全体ブロック
        "EURJPY": frozenset(range(16, 24)),  # NY_Lateブロック
    }

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── 通貨ペアフィルター: BT正EVペアのみ発火 ──
        _sym_clean = ctx.symbol.upper().replace("=X", "").replace("_", "")
        if _sym_clean not in self._enabled_symbols:
            return None

        # ── セッションフィルター: 特定ペア×時間帯のEV壊滅ゾーンをブロック ──
        _blocked = self._blocked_hours_by_pair.get(_sym_clean)
        if _blocked and ctx.hour_utc in _blocked:
            return None

        # ── 前提条件: ADX >= 22 (トレンド存在の確認) ──
        if ctx.adx < self.adx_min:  # ADX 20 (2026-04-07: 22→20, トレンド初動捕捉)
            return None

        # ── BB幅チェック: レンジ内のノイズブレイクを排除 ──
        if ctx.bb_width_pct < self.bb_width_pct_min:
            return None

        # ── RSI過熱ブロック: 極端な過熱状態は飛び乗り危険 ──
        if ctx.rsi5 > self.rsi_overbought or ctx.rsi5 < self.rsi_oversold:
            return None

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        _min_sl = 0.030 if ctx.is_jpy else 0.00030

        # ── BUY: 上方ブレイクアウト ──
        if (ctx.bbpb >= self.bbpb_buy
                and ctx.adx_pos > ctx.adx_neg
                and ctx.entry > ctx.open_price):         # 陽線実体
            signal = "BUY"
            score = 3.5

            reasons.append(f"✅ BB+2σ突破(%B={ctx.bbpb:.2f}≥1.0) — モメンタムブレイク")
            reasons.append(f"✅ ADX強トレンド({ctx.adx:.1f}≥{self.adx_min}, +DI={ctx.adx_pos:.1f}>-DI={ctx.adx_neg:.1f})")
            reasons.append(f"✅ 陽線実体確認(C={ctx.entry:.5g}>O={ctx.open_price:.5g})")

            # TP/SL
            tp = ctx.entry + ctx.atr7 * self.tp_mult
            sl_dist = max(ctx.atr7 * self.sl_mult, _min_sl)
            sl = ctx.entry - sl_dist

        # ── SELL: 下方ブレイクアウト ──
        elif (ctx.bbpb <= self.bbpb_sell
              and ctx.adx_neg > ctx.adx_pos
              and ctx.entry < ctx.open_price):            # 陰線実体
            signal = "SELL"
            score = 3.5

            reasons.append(f"✅ BB-2σ突破(%B={ctx.bbpb:.2f}≤0.0) — モメンタムブレイク")
            reasons.append(f"✅ ADX強トレンド({ctx.adx:.1f}≥{self.adx_min}, -DI={ctx.adx_neg:.1f}>+DI={ctx.adx_pos:.1f})")
            reasons.append(f"✅ 陰線実体確認(C={ctx.entry:.5g}<O={ctx.open_price:.5g})")

            # TP/SL
            tp = ctx.entry - ctx.atr7 * self.tp_mult
            sl_dist = max(ctx.atr7 * self.sl_mult, _min_sl)
            sl = ctx.entry + sl_dist

        if signal is None:
            return None

        # ── スコアボーナス ──

        # ADX 強度ボーナス (40超で追加)
        if ctx.adx >= 40:
            score += 0.8
            reasons.append(f"✅ ADX超強トレンド({ctx.adx:.1f}≥40) +0.8")
        elif ctx.adx >= 35:
            score += 0.4
            reasons.append(f"✅ ADX中強トレンド({ctx.adx:.1f}≥35) +0.4")

        # DI乖離ボーナス (方向の確信度)
        di_gap = abs(ctx.adx_pos - ctx.adx_neg)
        if di_gap >= 15:
            score += 0.5
            reasons.append(f"✅ DI乖離大({di_gap:.1f}≥15) +0.5")
        elif di_gap >= 8:
            score += 0.3

        # EMA200方向一致ボーナス
        if signal == "BUY" and ctx.ema200_bull:
            score += 0.3
            reasons.append("✅ EMA200上(トレンド方向一致)")
        elif signal == "SELL" and not ctx.ema200_bull:
            score += 0.3
            reasons.append("✅ EMA200下(トレンド方向一致)")

        # MACD方向一致ボーナス
        if signal == "BUY" and ctx.macdh > 0:
            score += 0.2
        elif signal == "SELL" and ctx.macdh < 0:
            score += 0.2

        # Confidence計算
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
