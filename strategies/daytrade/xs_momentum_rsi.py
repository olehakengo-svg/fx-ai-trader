"""
XS Momentum + H1 RSI Direction Filter (USD_JPY 専用ライブ)

xs_momentum v8.9 をベースに、TV Strategy Tester (USD_JPY 15m, 2026-05-13)
で発見した H1 RSI フィルターのエッジを上乗せした variant。

TV Phase 2 BT 結果 (friction=0, USDJPY 15m 全期間):
| Config | N | WR | PF | Net | Notes |
|---|---|---|---|---|---|
| 1 Baseline | 501 | 43.51% | 1.04 | +11.83 | xs_momentum 等価 |
| 3 RSI filter | 290 | 46.55% | 1.199 | +31.92 | London-NY + H1 RSI |

本 variant は Config 3 を完全に再現する。

ロジック:
  - xs_momentum と同一のモメンタム・ADX・EMA・確認足・SL/TP
  - London-NY session gate (UTC 12-18) は xs_momentum と同じ
  - H1 RSI direction filter:
      BUY:  rsi_h1 >= 60
      SELL: rsi_h1 <= 40
  - H1 RSI は ctx.df (15m) を 1H にリサンプルして RSI(14) を計算
    （ctx.htf["h1"] は DT context では実際には H4 を返すため使えない）

なぜ別ファイルか:
  - xs_momentum は本番ライブ稼働中で他ペア (GBP/EUR) PAIR_PROMOTED 済み。
    エッジの上乗せを本体に混ぜると既存 N の意味が変わるため variant 化。

なぜ USD_JPY 限定か:
  - TV BT は USD_JPY 15m 全期間のみで検証済み。他ペアは未検証。
  - Phase 3 で friction 反映 Python BT (3 majors) を回してから拡張判断。

Live promote 根拠 (Bonferroni 未到達、user override 2026-05-13):
  - PF=1.199, WR=46.55% の正 EV が現在の本番戦略群で希少。
  - ロードマップ目標 (月利100%) のため OANDA 転送を即時開始。
  - 詳細: wiki/decisions/xs-momentum-rsi-live-promote-override-2026-05-13.md
"""
from __future__ import annotations

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class XsMomentumRsi(StrategyBase):
    name = "xs_momentum_rsi"
    mode = "daytrade"
    enabled = True

    # ── pair scope: USD_JPY 専用 (TV BT 検証範囲) ──
    _enabled_symbols = ("USDJPY",)

    # ══════════════════════════════════════════════════
    # パラメータ定数 (xs_momentum と同期)
    # ══════════════════════════════════════════════════
    MOM_LOOKBACK   = 20
    MOM_THRESHOLD  = 1.0
    DISP_THRESHOLD = 3.0
    ADX_MIN        = 20
    SL_ATR_MULT    = 1.5
    TP_ATR_MULT    = 2.0
    MIN_RR         = 1.2
    MAX_HOLD_BARS  = 16

    # ── H1 RSI direction filter (TV Phase 2 Config 3 と一致) ──
    H1_RSI_BUY_MIN  = 60.0
    H1_RSI_SELL_MAX = 40.0
    H1_RSI_LOOKBACK_BARS = 60  # 15m bars → ≈15 H1 bars (RSI14 + margin)

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    def _calc_momentum(self, df, atr: float) -> float:
        if len(df) < self.MOM_LOOKBACK + 1:
            return 0.0
        current_close = float(df.iloc[-1]["Close"])
        past_close = float(df.iloc[-(self.MOM_LOOKBACK + 1)]["Close"])
        if atr <= 0:
            return 0.0
        return (current_close - past_close) / atr

    def _calc_dispersion(self, df, atr: float) -> float:
        if len(df) < self.MOM_LOOKBACK:
            return 0.0
        recent = df.iloc[-self.MOM_LOOKBACK:]
        range_hl = float(recent["High"].max()) - float(recent["Low"].min())
        if atr <= 0:
            return 0.0
        return range_hl / atr

    def _compute_h1_rsi(self, df) -> Optional[float]:
        """ctx.df (15m) を 1H にリサンプルして RSI(14) を返す。

        現在足は除外（look-ahead 防止）。データ不足時は None。
        """
        if df is None or len(df) < self.H1_RSI_LOOKBACK_BARS:
            return None
        try:
            from modules.data import resample_df
            from ta.momentum import RSIIndicator
            # 現在足を除外して past-only でリサンプル
            df_past = df.iloc[:-1]
            if len(df_past) < self.H1_RSI_LOOKBACK_BARS:
                return None
            df_h1 = resample_df(df_past, "1h")
            if df_h1 is None or len(df_h1) < 15:
                return None
            rsi_series = RSIIndicator(df_h1["Close"], window=14).rsi()
            rsi_val = rsi_series.iloc[-1]
            if rsi_val is None:
                return None
            rsi_float = float(rsi_val)
            if rsi_float != rsi_float:  # NaN check
                return None
            return rsi_float
        except Exception:
            return None

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── pair filter: USD_JPY のみ ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        if ctx.df is None or len(ctx.df) < self.MOM_LOOKBACK + 5:
            return None
        if ctx.atr <= 0:
            return None

        _signal_df = ctx.df
        _signal_close = ctx.entry
        _signal_open = ctx.open_price
        _atr = ctx.atr
        _adx = ctx.adx
        _ema9 = ctx.ema9
        _ema21 = ctx.ema21

        # ── ADX トレンドフィルター ──
        if _adx < self.ADX_MIN:
            return None

        # ── London-NY session gate (UTC 12-18, xs_momentum と同期) ──
        _bar_time = ctx.bar_time
        if _bar_time is None and ctx.df is not None and len(ctx.df) > 0:
            _bar_time = ctx.df.index[-1]
        if _bar_time is not None:
            try:
                _h = _bar_time.hour if hasattr(_bar_time, 'hour') else int(str(_bar_time)[11:13])
                if _h < 12 or _h >= 18:
                    return None
            except (ValueError, IndexError):
                pass

        # ── モメンタム計算 ──
        _mom = self._calc_momentum(_signal_df, _atr)
        if abs(_mom) < self.MOM_THRESHOLD:
            return None

        # ── 分散 ──
        _disp = self._calc_dispersion(_signal_df, _atr)
        _high_disp = _disp > self.DISP_THRESHOLD

        # ── 方向判定 + EMA + 確認足 ──
        signal = None
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        if _mom > self.MOM_THRESHOLD:
            if _ema9 <= _ema21:
                return None
            if _signal_close <= _signal_open:
                return None
            signal = "BUY"
        elif _mom < -self.MOM_THRESHOLD:
            if _ema9 >= _ema21:
                return None
            if _signal_close >= _signal_open:
                return None
            signal = "SELL"
        else:
            return None

        # ── H1 RSI direction filter (TV Phase 2 Config 3 の edge) ──
        _rsi_h1 = self._compute_h1_rsi(_signal_df)
        if _rsi_h1 is None:
            return None  # データ不足時はエントリーしない（fail-closed）
        if signal == "BUY" and _rsi_h1 < self.H1_RSI_BUY_MIN:
            return None
        if signal == "SELL" and _rsi_h1 > self.H1_RSI_SELL_MAX:
            return None

        # ── SL/TP ──
        _sl_dist = _atr * self.SL_ATR_MULT
        _tp_dist = _atr * self.TP_ATR_MULT
        if signal == "BUY":
            sl = ctx.entry - _sl_dist
            tp = ctx.entry + _tp_dist
        else:
            sl = ctx.entry + _sl_dist
            tp = ctx.entry - _tp_dist

        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None
        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            return None

        # ── スコア & Reasons ──
        score = 4.0
        reasons = []

        _mom_bonus = abs(_mom) * 0.3
        score += _mom_bonus
        reasons.append(
            f"{signal} XS Momentum+H1RSI: mom={_mom:+.2f}ATR "
            f"(lookback={self.MOM_LOOKBACK}bars)"
        )
        reasons.append(
            f"H1 RSI filter pass: rsi_h1={_rsi_h1:.1f} "
            f"({'>=' + str(int(self.H1_RSI_BUY_MIN)) if signal == 'BUY' else '<=' + str(int(self.H1_RSI_SELL_MAX))})"
        )

        if _high_disp:
            score += 0.5
            reasons.append(
                f"Dispersion={_disp:.1f}ATR > {self.DISP_THRESHOLD} "
                f"(Eriksen 2019: momentum timing)"
            )

        score += 0.5
        reasons.append(
            f"EMA alignment: EMA9={_ema9:.{_dec}f} "
            f"{'>' if signal == 'BUY' else '<'} EMA21={_ema21:.{_dec}f}"
        )

        if _adx >= 30:
            score += 0.3
            reasons.append(f"Strong trend ADX={_adx:.1f}>=30")

        # H1 RSI 強度ボーナス (TV BT で deep zone ほど勝率上昇傾向)
        if signal == "BUY" and _rsi_h1 >= 70:
            score += 0.2
            reasons.append(f"H1 RSI deep bull zone ({_rsi_h1:.1f}>=70)")
        elif signal == "SELL" and _rsi_h1 <= 30:
            score += 0.2
            reasons.append(f"H1 RSI deep bear zone ({_rsi_h1:.1f}<=30)")

        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"HTF alignment ({_agr})")

        reasons.append(f"RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
