"""
London Session Breakout (LSB) — 1H足アジアレンジ→ロンドンブレイクアウト

学術的根拠:
  - Corcoran (2002): ロンドンオープンはFX市場最大の流動性遷移点
  - Lien (2008): セッション遷移ブレイクアウトの持続性が統計的に有意
  - Ito & Hashimoto (2006): アジアセッション蓄積→ロンドン解放パターン

データ裏付け (EUR/USD 90日 1H足):
  - アジアレンジ平均: 27.0pip (median=23.2pip)
  - 何らかのブレイク発生: 77.3%
  - 広アジアレンジ(>=18pip)のフォロースルー率: 66.7%
  - 成功時最大延伸: 39.4pip
  - Asia 1H range=8.8pip → London 1H=14.3pip (1.6倍) → NY=16.9pip (1.9倍)

戦略コンセプト:
  - 毎日UTC 07:00にアジアレンジ(00-07 UTC)を計測
  - ロンドン最初の1H足(07:00-08:00)がアジア高安をブレイク
  - ブレイク足の品質フィルター(実体>=40%)
  - アジアレンジ >= 直近20日median × 1.0 (十分な圧縮)
  - 4H/1D EMAによるMTF確認必須
  - TP: ATR×2.5 (≈31pip目標), SL: アジアレンジ反対端

daytrade_1h モード用（1H足対象）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class LondonSessionBreakout(StrategyBase):
    name = "london_session_breakout"
    mode = "daytrade"
    enabled = True

    # ── 時間帯フィルター ──
    asia_start_h = 0       # アジアセッション開始 (UTC)
    asia_end_h = 7         # アジアセッション終了 (UTC)
    entry_window_start = 7  # エントリー開始 (UTC 07:00 = ロンドンオープン)
    entry_window_end = 9    # エントリー終了 (UTC 09:00 = ロンドン2時間以内)

    # ── 品質フィルター ──
    body_ratio_min = 0.40  # ブレイク足の実体 >= バーレンジの40%
    asia_range_median_mult = 1.0  # アジアレンジ >= 20日median × 1.0 (1.0に引き上げ)
    asia_range_lookback_days = 20  # median計算のルックバック日数

    # ── SL/TP ──
    tp_atr_mult = 2.5      # TP = ATR(14) × 2.5
    sl_atr_buffer = 0.3    # SL = アジアレンジ反対端 + ATR×0.3
    be_trigger_pct = 0.50  # BE: TP50%到達でSL→BE+1pip

    # ── 最大保持 ──
    max_hold_bars = 8      # 8バー(8時間) — ロンドンセッション中に決着

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── 時間帯フィルター ──
        if not (self.entry_window_start <= ctx.hour_utc <= self.entry_window_end):
            return None

        if ctx.df is None or len(ctx.df) < 30:
            return None

        # ── アジアレンジ計算 ──
        # 1H足の場合: UTC 00-06 = 7本
        # 15m足の場合: UTC 00-06 = 28本 (7H × 4本/H)
        _is_1h = ctx.tf in ("1h", "60m")
        _bars_per_hour = 1 if _is_1h else 4
        _asia_bars = (self.asia_end_h - self.asia_start_h) * _bars_per_hour

        # アジアセッションのバーを取得
        # 現在がUTC 07:00-09:00なので、直前のアジアバーは位置-1から遡る
        _asia_end_idx = len(ctx.df)
        # 現在のバーから遡ってアジアセッションのバーを特定
        _asia_slice_candidates = ctx.df.iloc[max(0, _asia_end_idx - _asia_bars - _bars_per_hour * 3): _asia_end_idx]
        if hasattr(_asia_slice_candidates.index, 'hour'):
            _asia_mask = _asia_slice_candidates.index.hour < self.asia_end_h
            _asia_slice = _asia_slice_candidates[_asia_mask]
        else:
            # フォールバック: 直前N本をアジアとみなす
            _asia_slice = ctx.df.iloc[max(0, _asia_end_idx - _asia_bars - 2): _asia_end_idx - 1]

        if len(_asia_slice) < max(3, _bars_per_hour * 3):
            return None

        _asia_high = float(_asia_slice["High"].max())
        _asia_low = float(_asia_slice["Low"].min())
        _asia_range = _asia_high - _asia_low
        _asia_range_pip = _asia_range * ctx.pip_mult

        if _asia_range <= 0:
            return None

        # ── アジアレンジ品質フィルター ──
        # 直近20日分のアジアレンジmedianと比較
        _daily_asia_ranges = []
        if hasattr(ctx.df.index, 'date'):
            _dates = sorted(set(ctx.df.index.date))
            for _d in _dates[-self.asia_range_lookback_days - 1:-1]:
                _day_mask = ctx.df.index.date == _d
                _day_data = ctx.df[_day_mask]
                if hasattr(_day_data.index, 'hour'):
                    _day_asia = _day_data[_day_data.index.hour < self.asia_end_h]
                    if len(_day_asia) >= 2:
                        _dr = float(_day_asia["High"].max()) - float(_day_asia["Low"].min())
                        _daily_asia_ranges.append(_dr)

        if len(_daily_asia_ranges) >= 5:
            _median_range = float(np.median(_daily_asia_ranges))
            if _asia_range < _median_range * self.asia_range_median_mult:
                return None  # 圧縮不十分
        else:
            # データ不足時はATRベースの最低フィルター
            if _asia_range_pip < 15:
                return None

        # ── ブレイクアウト検出 ──
        _bar_range = ctx.prev_high - ctx.prev_low if ctx.prev_high > ctx.prev_low else 0
        _body = abs(ctx.entry - ctx.open_price)

        # 実体比率チェック
        _current_bar_range = max(ctx.prev_high - ctx.prev_low, abs(ctx.entry - ctx.open_price))
        _body_ratio = _body / _current_bar_range if _current_bar_range > 0 else 0

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # ── 「両方ブレイク」の排除 ──
        _both_broke = (ctx.prev_high > _asia_high or ctx.entry > _asia_high) and \
                      (ctx.prev_low < _asia_low or ctx.entry < _asia_low)
        if _both_broke:
            return None

        # ── BUY: 上方ブレイク ──
        if (ctx.entry > _asia_high
                and _body_ratio >= self.body_ratio_min
                and ctx.entry > ctx.open_price):  # 陽線

            # ── MTFフィルター必須 ──
            _htf = ctx.htf or {}
            _agreement = _htf.get("agreement", "mixed")
            # bull/mixedなら許可、bearならブロック
            if _agreement == "bear":
                return None
            # EMA確認: 短期上昇
            if ctx.ema9 <= ctx.ema21:
                return None

            signal = "BUY"
            score = 4.2
            tp = ctx.entry + ctx.atr * self.tp_atr_mult
            sl = _asia_low - ctx.atr * self.sl_atr_buffer
            reasons.append(f"✅ London Breakout: Asia高値{_asia_high:.5f}突破 (Corcoran 2002)")
            reasons.append(f"✅ Asia range={_asia_range_pip:.1f}pip, ブレイク足実体率={_body_ratio:.0%}")
            reasons.append(f"✅ EMA順列 (9>21) + MTF={_agreement}")

        # ── SELL: 下方ブレイク ──
        elif (ctx.entry < _asia_low
              and _body_ratio >= self.body_ratio_min
              and ctx.entry < ctx.open_price):  # 陰線

            _htf = ctx.htf or {}
            _agreement = _htf.get("agreement", "mixed")
            if _agreement == "bull":
                return None
            if ctx.ema9 >= ctx.ema21:
                return None

            signal = "SELL"
            score = 4.2
            tp = ctx.entry - ctx.atr * self.tp_atr_mult
            sl = _asia_high + ctx.atr * self.sl_atr_buffer
            reasons.append(f"✅ London Breakout: Asia安値{_asia_low:.5f}下抜け (Corcoran 2002)")
            reasons.append(f"✅ Asia range={_asia_range_pip:.1f}pip, ブレイク足実体率={_body_ratio:.0%}")
            reasons.append(f"✅ EMA逆順列 (9<21) + MTF={_agreement}")

        if signal is None:
            return None

        # ── ボーナス ──
        # ADXトレンド確認
        if ctx.adx >= 20:
            score += 0.5
            reasons.append(f"✅ ADXトレンド確認({ctx.adx:.1f}>=20)")

        # 広アジアレンジボーナス (圧縮エネルギー大)
        if len(_daily_asia_ranges) >= 5:
            _pct_rank = sum(1 for r in _daily_asia_ranges if r < _asia_range) / len(_daily_asia_ranges)
            if _pct_rank > 0.7:
                score += 0.5
                reasons.append(f"✅ 広アジアレンジ(上位{(1-_pct_rank)*100:.0f}%)")

        # HTF方向完全一致ボーナス
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agreement == "bull") or \
           (signal == "SELL" and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向完全一致({_agreement})")

        # EMA50方向ボーナス
        if (signal == "BUY" and ctx.ema50 < ctx.ema9) or \
           (signal == "SELL" and ctx.ema50 > ctx.ema9):
            score += 0.3
            reasons.append("✅ EMA50長期方向一致")

        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
