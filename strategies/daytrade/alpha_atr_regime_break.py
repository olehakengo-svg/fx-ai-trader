"""
Alpha #3: ATR Regime Break (ボラティリティ・レジーム転換ブレイクアウト)
══════════════════════════════════════════════════════════════════════

■ 仮説
  ATRには自己相関がある（ボラティリティ・クラスタリング: Mandelbrot 1963,
  ARCH効果: Engle 1982）。低ボラティリティ期間が一定以上続いた後に
  ATRが急伸した瞬間は、新たなボラティリティ・レジームの開始であり、
  その最初のバーの方向に短期的なモメンタムが継続しやすい。

  教科書的なBB Squeezeとの違い:
  - BBバンド幅ではなくATR自体のパーセンタイル推移を使用
  - 「圧縮→解放」の判定をバンド幅ではなく、ATRの対数リターンの
    標準偏差で定義（ATRの変化率のボラティリティ）
  - エントリーは「ATRの急伸 + バーの方向」のみ。インジケーター閾値不使用

■ ロジック
  1. 直前 quiet_window 本（パラメータ1）の ATR の変動係数 (CV) を計算:
     CV = std(ATR) / mean(ATR)
  2. CV が全体のヒストリカル分布の下位 quiet_pctl パーセンタイル以下
     → 「静穏期」と判定
  3. 現在バーの ATR が直前バーの ATR を surge_mult 倍（パラメータ2）
     以上 上回った場合 → 「レジームブレイク」と判定
  4. 静穏期 AND レジームブレイク → 現在バーの方向にエントリー

■ パラメータ（2つ）
  - quiet_window: 静穏期判定ウィンドウ（デフォルト12）
  - surge_mult: ATR急伸倍率（デフォルト1.5）

■ Look-ahead bias防止
  - CV計算は iloc[-quiet_window-1:-1]（現在バー除外）
  - ATR急伸判定は現在バーATR vs 直前バーATR のみ
  - パーセンタイル計算は現在バー除外した全履歴

■ 学術根拠
  - Engle (1982) "Autoregressive conditional heteroscedasticity" (ARCH)
  - Mandelbrot (1963) "The variation of certain speculative prices"
  - Corsi (2009) "A simple approximate long-memory model of realized volatility" (HAR-RV)
"""
from __future__ import annotations
import math
from typing import Optional
import numpy as np
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class AtrRegimeBreak(StrategyBase):
    name = "atr_regime_break"
    mode = "daytrade"
    enabled = True
    params = {
        "quiet_window": 12,   # 静穏期判定ウィンドウ（バー数）
        "surge_mult": 1.5,    # ATR急伸倍率
    }

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        df = ctx.df
        if df is None:
            return None

        quiet_window = self.params.get("quiet_window", 12)
        surge_mult = self.params.get("surge_mult", 1.5)

        # 十分な履歴が必要: quiet_window + 余裕（CV分布構築用）+ 現在バー
        min_bars = max(quiet_window * 5, 100)
        if len(df) < min_bars:
            return None

        if ctx.atr <= 0:
            return None

        # ── ATR列の取得 ──
        atr_col = None
        for col_name in ("atr", "ATR", "atr14"):
            if col_name in df.columns:
                atr_col = col_name
                break
        if atr_col is None:
            return None

        atr_series = df[atr_col]

        # ── 現在バーのATR急伸チェック ──
        current_atr = atr_series.iloc[-1]
        prev_atr = atr_series.iloc[-2]

        if prev_atr <= 0 or current_atr <= 0:
            return None

        surge_ratio = current_atr / prev_atr
        if surge_ratio < surge_mult:
            return None  # 急伸していない

        # ── 直前 quiet_window 本の CV（現在バー除外） ──
        atr_window = atr_series.iloc[-(quiet_window + 1):-1]
        if len(atr_window) < quiet_window:
            return None

        atr_vals = atr_window.values
        mean_atr = sum(atr_vals) / len(atr_vals)
        if mean_atr <= 0:
            return None

        variance = sum((v - mean_atr) ** 2 for v in atr_vals) / (len(atr_vals) - 1)
        std_atr = math.sqrt(variance) if variance > 0 else 0
        cv_current = std_atr / mean_atr

        # ── CV分布を構築し、パーセンタイルを計算（現在ウィンドウ除外） ──
        # ベクトル化: pandas rolling で CV を一括計算 (O(N) vs O(N×W) loop)
        _atr_hist = atr_series.iloc[:-1]  # 現在バー除外
        if len(_atr_hist) < quiet_window + 30:
            return None
        _rolling_mean = _atr_hist.rolling(window=quiet_window).mean()
        _rolling_std = _atr_hist.rolling(window=quiet_window).std(ddof=1)
        _rolling_cv = (_rolling_std / _rolling_mean).dropna()
        _valid_cv = _rolling_cv[_rolling_cv > 0]

        if len(_valid_cv) < 30:
            return None

        hist_cvs = _valid_cv.values
        # パーセンタイル計算: 現在CVが全履歴CVの何パーセンタイルか
        below_count = int(np.sum(hist_cvs <= cv_current))
        cv_pctl = below_count / len(hist_cvs)

        # 「静穏期」判定: CVが下位25%以下
        quiet_pctl = 0.25
        if cv_pctl > quiet_pctl:
            return None  # 静穏期ではない

        # ── エントリー方向: 現在バーの方向 ──
        current_close = df.iloc[-1]["Close"]
        current_open = df.iloc[-1]["Open"]
        bar_body = current_close - current_open

        # body が ATR の 10% 未満 → 方向不明確、スキップ
        if abs(bar_body) < ctx.atr * 0.10:
            return None

        signal = "BUY" if bar_body > 0 else "SELL"

        # ── HTF Hard Block (v9.1) ──
        _htf = ctx.htf or {}
        _htf_agreement = _htf.get("agreement", "mixed")
        if _htf_agreement == "bull" and signal == "SELL":
            return None
        if _htf_agreement == "bear" and signal == "BUY":
            return None

        # ── 追加フィルタ: 急伸バーのレンジが十分大きいこと ──
        bar_range = df.iloc[-1]["High"] - df.iloc[-1]["Low"]
        if bar_range < ctx.atr * 0.8:
            return None  # ATRは急伸したがバーのレンジが伴っていない

        # ── SL/TP: ATRベース ──
        atr = ctx.atr
        # SLは直前の静穏期のATR（小さい）ではなく現在ATR基準
        sl_mult = 1.2  # レジームブレイク後はSLをタイトに
        # TPはsurge_ratioに応じて拡大（勢いが強いほど伸ばす）
        tp_mult = min(3.0, 1.5 + (surge_ratio - surge_mult) * 1.5)

        if signal == "BUY":
            sl = ctx.entry - atr * sl_mult
            tp = ctx.entry + atr * tp_mult
        else:
            sl = ctx.entry + atr * sl_mult
            tp = ctx.entry - atr * tp_mult

        # ── スコアリング ──
        base_score = 5.5
        # surge強度ボーナス
        surge_bonus = min(1.0, (surge_ratio - surge_mult) / 1.0)
        # 静穏度ボーナス（CVパーセンタイルが低いほど良い）
        quiet_bonus = min(0.5, (quiet_pctl - cv_pctl) / quiet_pctl)
        # バー方向の明確さ
        body_bonus = min(0.3, abs(bar_body) / (atr * 0.5))
        score = base_score + surge_bonus + quiet_bonus + body_bonus

        confidence = int(min(85, 50 + score * 3))

        reasons = [
            f"⚡ [ATRRegime] surge={surge_ratio:.2f}x (thr={surge_mult}x) "
            f"CV_pctl={cv_pctl:.0%} (quiet<{quiet_pctl:.0%})",
            f"bar_body={bar_body/atr:.2f}ATR range={bar_range/atr:.2f}ATR",
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
