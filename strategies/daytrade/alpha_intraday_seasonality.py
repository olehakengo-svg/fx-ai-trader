"""
Alpha #1: Intraday Return Seasonality (日中リターン季節性)
══════════════════════════════════════════════════════════

■ 仮説
  FX市場の各1時間バーのリターンには、曜日×時間帯に固有の統計的偏り
  （日中季節性）が存在する。この偏りは流動性供給者の在庫管理行動と
  機関投資家のフロー集中に起因し、少なくとも短期的に持続する。
  (Cornett et al. 2007, Breedon & Ranaldo 2013)

■ ロジック
  1. 直近N日間（パラメータ1: lookback_days）の同一曜日×同一時間帯の
     リターン分布を構築
  2. その分布の平均リターンが統計的に有意に非ゼロ（t検定 p < 0.05）
     であれば、偏りの方向にエントリー
  3. 効果量（Cohen's d）が閾値（パラメータ2: min_effect_size）以上で
     あることを追加フィルターとする

■ パラメータ（最大2つ）
  - lookback_days: 季節性計算の遡及日数（デフォルト60）
  - min_effect_size: Cohen's d 最低閾値（デフォルト0.3）

■ Look-ahead bias防止
  - 現在バー（iloc[-1]）のリターンは計算に使用しない
  - 統計量はすべて過去データ（iloc[:-1]）から算出

■ 学術根拠
  - Breedon & Ranaldo (2013) "Intraday patterns in FX returns and order flow"
  - Cornett et al. (2007) "Seasonality in stock returns and volatility"
"""
from __future__ import annotations
import math
from typing import Optional
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class IntradaySeasonality(StrategyBase):
    name = "intraday_seasonality"
    mode = "daytrade"
    enabled = True
    params = {
        "lookback_days": 60,      # 季節性計算の遡及日数
        "min_effect_size": 0.3,   # Cohen's d 最低閾値
    }

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        df = ctx.df
        if df is None or len(df) < 200:
            return None

        # ── 現在バーの曜日・時間帯を取得 ──
        bar_time = ctx.bar_time
        if bar_time is None:
            try:
                bar_time = df.index[-1]
            except Exception:
                return None

        try:
            current_dow = bar_time.weekday()   # 0=Mon ... 4=Fri
            current_hour = bar_time.hour
        except Exception:
            return None

        # 週末は除外
        if current_dow > 4:
            return None

        # ── 過去データから同一曜日×同一時間帯のリターン分布を構築 ──
        # 現在バーを含めない (look-ahead bias防止)
        hist = df.iloc[:-1]
        if len(hist) < 100:
            return None

        lookback_days = self.params.get("lookback_days", 60)
        min_effect = self.params.get("min_effect_size", 0.3)

        # ベクトル化: pandas Index属性で一括フィルタ (O(N) loop回避)
        try:
            _idx = hist.index
            _mask = (_idx.weekday == current_dow) & (_idx.hour == current_hour)
            matched = hist.loc[_mask]
        except Exception:
            return None

        if len(matched) < 8:
            return None

        # リターン計算（ベクトル化）
        _open = matched["Open"].values
        _close = matched["Close"].values
        _valid = _open > 0
        if _valid.sum() < 8:
            return None
        _rets = (_close[_valid] - _open[_valid]) / _open[_valid]

        # 直近lookback_days分のサンプルに限定
        max_samples = lookback_days
        if len(_rets) > max_samples:
            _rets = _rets[-max_samples:]

        returns = _rets.tolist()

        # 最低サンプル数チェック（統計的信頼性）
        n = len(returns)
        if n < 8:
            return None

        # ── t検定: 平均リターンが0と有意に異なるか ──
        mean_ret = sum(returns) / n
        variance = sum((r - mean_ret) ** 2 for r in returns) / (n - 1)
        std_ret = math.sqrt(variance) if variance > 0 else 0

        if std_ret == 0:
            return None

        t_stat = mean_ret / (std_ret / math.sqrt(n))
        cohens_d = abs(mean_ret) / std_ret

        # 有意性チェック: |t| > 2.0 (≈ p < 0.05 for df ≥ 8)
        if abs(t_stat) < 2.0:
            return None

        # 効果量フィルター
        if cohens_d < min_effect:
            return None

        # ── シグナル生成 ──
        signal = "BUY" if mean_ret > 0 else "SELL"

        # ── HTF Hard Block (v9.1) ──
        _htf = ctx.htf or {}
        _htf_agreement = _htf.get("agreement", "mixed")
        if _htf_agreement == "bull" and signal == "SELL":
            return None
        if _htf_agreement == "bear" and signal == "BUY":
            return None

        # ── SL/TP: ATRベース ──
        atr = ctx.atr
        if atr <= 0:
            return None

        sl_mult = 1.5
        # TP倍率: 効果量が大きいほどTPを広げる（最大2.5ATR）
        tp_mult = min(2.5, 1.5 + cohens_d)

        if signal == "BUY":
            sl = ctx.entry - atr * sl_mult
            tp = ctx.entry + atr * tp_mult
        else:
            sl = ctx.entry + atr * sl_mult
            tp = ctx.entry - atr * tp_mult

        # ── スコアリング ──
        # t統計量の絶対値と効果量で重み付け
        base_score = 5.0
        t_bonus = min(1.0, (abs(t_stat) - 2.0) / 3.0)  # t=2→0, t=5→1.0
        d_bonus = min(0.5, (cohens_d - min_effect) / 0.5)
        n_bonus = min(0.3, (n - 8) / 30)  # サンプル数ボーナス
        score = base_score + t_bonus + d_bonus + n_bonus

        confidence = int(min(85, 50 + score * 3))

        reasons = [
            f"📊 [IntradaySeason] dow={current_dow} h={current_hour} "
            f"mean={mean_ret*10000:.1f}bp σ={std_ret*10000:.1f}bp",
            f"t={t_stat:.2f} d={cohens_d:.2f} N={n}",
        ]

        return Candidate(
            signal=signal,
            confidence=confidence,
            sl=sl,
            tp=tp,
            reasons=reasons,
            entry_type=self.name,
            score=score,
        )
