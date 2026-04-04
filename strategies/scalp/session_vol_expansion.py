"""
Session Volatility Expansion (SVE) — EUR/USD ロンドンオープン圧縮ブレイクアウト

学術的根拠:
  - Andersen & Bollerslev (1998): FXボラティリティのセッション遷移予測可能性
  - Ito & Hashimoto (2006): 欧州通貨ロンドンオープン30-60分でデイリーレンジの30-40%形成

データ裏付け (EUR/USD 60日分析):
  - Asia 15m range: 4.5pip (市場が「死んでいる」)
  - London 15m range: 6.6pip (1.47倍)
  - NY 15m range: 8.3pip (1.84倍)
  - セッション遷移時のボラティリティ急拡大は日次で再現

戦略コンセプト:
  - アジアセッション中の圧縮（低ボラ蓄積）を検出
  - ロンドンオープン直後(UTC 07:00-08:30)のレンジブレイクにエントリー
  - 15m足EMA方向による上位足確認
  - OANDAリアルスプレッド<=0.5pipのハードフィルター

EUR/USD専用: is_jpyではなくEUR/USDの特性に合わせた設計
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class SessionVolExpansion(StrategyBase):
    name = "session_vol_expansion"
    mode = "scalp"
    enabled = True

    # ── 時間帯フィルター ──
    hour_start = 7         # UTC 07:00 (ロンドンオープン)
    hour_end_minute = 510  # UTC 08:30 = 8*60+30 = 510分

    # ── 圧縮検出パラメータ ──
    compress_window = 30   # 直近30本(30分)の平均range
    baseline_window = 60   # 比較基準: 前60本(1時間)の平均range
    compress_ratio = 0.6   # 圧縮閾値: 直近/基準 <= 0.6

    # ── ブレイクアウトパラメータ ──
    lookback_range = 30    # ブレイク判定の高安ルックバック(30本=30分)
    body_ratio_min = 0.50  # 実体 >= バーレンジの50%
    asia_range_min_pip = 10.0  # アジアレンジ最低10pip (十分な圧縮エネルギー)

    # ── SL/TP ──
    tp_atr_mult = 3.0      # TP = ATR(14) × 3.0
    sl_atr_buffer = 0.3    # SL = アジアレンジ反対端 + ATR×0.3

    # ── スプレッドフィルター ──
    max_spread_pip = 0.5   # OANDAリアルスプレッド上限 (ロンドンオープン時のスリッページ対策)

    # ── 最大保持 ──
    max_hold_bars = 30     # 30分

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── EUR/USD専用 ──
        if ctx.is_jpy:
            return None

        # ── 時間帯フィルター: UTC 07:00 - 08:30 のみ ──
        _current_minute = ctx.hour_utc * 60
        if ctx.bar_time is not None and hasattr(ctx.bar_time, 'minute'):
            _current_minute = ctx.hour_utc * 60 + ctx.bar_time.minute
        if _current_minute < self.hour_start * 60 or _current_minute > self.hour_end_minute:
            return None

        if ctx.df is None or len(ctx.df) < self.compress_window + self.baseline_window + 10:
            return None

        # ── スプレッドフィルター (本番のみ) ──
        if not ctx.backtest_mode:
            _session = ctx.session if ctx.session else {}
            _spread = _session.get("spread_pip", 0)
            if _spread > self.max_spread_pip and _spread > 0:
                return None

        # ── アジアレンジ計算 (直前のアジアセッション) ──
        # UTC 00:00-07:00 の7H = 420本(1m)
        _asia_lookback = min(420, len(ctx.df) - 10)
        _asia_slice = ctx.df.iloc[-_asia_lookback - self.lookback_range: -self.lookback_range]
        if len(_asia_slice) < 60:
            return None
        _asia_high = float(_asia_slice["High"].max())
        _asia_low = float(_asia_slice["Low"].min())
        _asia_range_pip = (_asia_high - _asia_low) * ctx.pip_mult

        if _asia_range_pip < self.asia_range_min_pip:
            return None  # エネルギー蓄積不十分

        # ── 圧縮検出: 直近30本 vs 前60本 ──
        _recent = ctx.df.iloc[-self.compress_window:]
        _baseline_start = -(self.compress_window + self.baseline_window)
        _baseline_end = -self.compress_window
        _baseline = ctx.df.iloc[_baseline_start:_baseline_end]

        _recent_avg_range = float((_recent["High"] - _recent["Low"]).mean())
        _baseline_avg_range = float((_baseline["High"] - _baseline["Low"]).mean())

        if _baseline_avg_range <= 0:
            return None
        _compression = _recent_avg_range / _baseline_avg_range

        # 圧縮不十分 → 既にブレイクしている or レンジが安定
        if _compression > self.compress_ratio:
            return None

        # ── ブレイクアウト検出 ──
        _range_slice = ctx.df.iloc[-self.lookback_range:]
        _range_high = float(_range_slice["High"].max())
        _range_low = float(_range_slice["Low"].min())
        _bar_range = ctx.prev_high - ctx.prev_low if ctx.prev_high > ctx.prev_low else 0
        _body = abs(ctx.entry - ctx.open_price)
        _body_ok = (_body / _bar_range >= self.body_ratio_min) if _bar_range > 0 else False

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # ── BUY: 上方ブレイク ──
        if (ctx.entry > _range_high
                and _body_ok
                and ctx.ema9 > ctx.ema21):  # 15m EMA方向一致
            signal = "BUY"
            score = 4.0
            reasons.append(f"✅ SVEブレイクアウト: 圧縮{_compression:.2f}→上抜け({ctx.entry:.5f}>{_range_high:.5f})")
            reasons.append(f"✅ Asia range={_asia_range_pip:.1f}pip (>={self.asia_range_min_pip})")
            reasons.append(f"✅ EMA順列確認 (9>21)")
            tp = ctx.entry + ctx.atr * self.tp_atr_mult
            sl = _asia_low - ctx.atr * self.sl_atr_buffer

        # ── SELL: 下方ブレイク ──
        elif (ctx.entry < _range_low
              and _body_ok
              and ctx.ema9 < ctx.ema21):
            signal = "SELL"
            score = 4.0
            reasons.append(f"✅ SVEブレイクアウト: 圧縮{_compression:.2f}→下抜け({ctx.entry:.5f}<{_range_low:.5f})")
            reasons.append(f"✅ Asia range={_asia_range_pip:.1f}pip (>={self.asia_range_min_pip})")
            reasons.append(f"✅ EMA逆順列確認 (9<21)")
            tp = ctx.entry - ctx.atr * self.tp_atr_mult
            sl = _asia_high + ctx.atr * self.sl_atr_buffer

        if signal is None:
            return None

        # ── ボーナス ──
        # 強圧縮ボーナス
        if _compression < 0.4:
            score += 0.5
            reasons.append(f"✅ 強圧縮({_compression:.2f}<0.4)")

        # ADXモメンタムボーナス
        if ctx.adx > 20:
            score += 0.3
            reasons.append(f"✅ ADXモメンタム({ctx.adx:.1f}>20)")

        # HTF方向一致ボーナス
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agreement == "bull") or \
           (signal == "SELL" and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
