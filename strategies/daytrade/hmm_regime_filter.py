"""
HMM Regime Filter — HMMレジーム検出の戦略ラッパー (防御オーバーレイ)

学術的根拠:
  - Nystrup et al (2024, JAM): HMMレジーム検出により MaxDD を50%削減。
  - Hamilton (1989): Markov-switching model の金融市場適用。

設計:
  - これはアルファ生成戦略ではなく、防御オーバーレイ。
  - evaluate() は常に None を返す (トレードシグナルを生成しない)。
  - 代わりに、レジーム状態をクラス変数に保存し、他の戦略/モジュールが参照可能。
  - HMMRegimeDetector (modules/hmm_regime.py) を内部で使用。

使用方法 (他の戦略/demo_trader から):
  from strategies.daytrade.hmm_regime_filter import HmmRegimeFilter

  # レジーム状態の参照
  if HmmRegimeFilter.is_turbulent():
      lot *= 0.3  # 乱流時にロット縮小

  # ロット乗数の取得
  lot *= HmmRegimeFilter.get_lot_multiplier()

  # 詳細情報
  info = HmmRegimeFilter.get_regime_info()
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.hmm_regime import HMMRegimeDetector
from typing import Optional
import logging
import numpy as np

logger = logging.getLogger("hmm_regime_filter")


class HmmRegimeFilter(StrategyBase):
    name = "hmm_regime_filter"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # クラス変数 (全インスタンス共有 — 他コードから参照可能)
    # ══════════════════════════════════════════════════
    _detector: HMMRegimeDetector = HMMRegimeDetector(lookback=60)
    _current_regime: int = 0          # 0=calm, 1=turbulent
    _lot_mult: float = 1.0
    _vol_ratio: float = 1.0
    _regime_label: str = "CALM"
    _last_symbol: str = ""

    # ══════════════════════════════════════════════════
    # クラスメソッド (外部参照用 API)
    # ══════════════════════════════════════════════════

    @classmethod
    def is_turbulent(cls) -> bool:
        """乱流レジームかどうか。"""
        return cls._current_regime == 1

    @classmethod
    def is_calm(cls) -> bool:
        """穏やかなレジームかどうか。"""
        return cls._current_regime == 0

    @classmethod
    def get_lot_multiplier(cls) -> float:
        """レジームに基づくロット乗数。calm=1.0, turbulent=0.3。"""
        return cls._lot_mult

    @classmethod
    def get_regime_info(cls) -> dict:
        """レジーム情報の辞書を返す。"""
        return {
            "state": cls._current_regime,
            "label": cls._regime_label,
            "lot_multiplier": cls._lot_mult,
            "vol_ratio": cls._vol_ratio,
            "symbol": cls._last_symbol,
        }

    # ──────────────────────────────────────────────────
    # メインロジック (常に None を返す)
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        """レジーム状態を更新し、クラス変数に保存。

        トレードシグナルは生成しない (常に None)。
        DaytradeEngine が全戦略を順番に評価するため、
        このメソッドは毎バーで呼ばれ、レジーム状態が更新される。
        """
        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 60:
            return None

        # ── ATR ガード ──
        if ctx.atr <= 0:
            return None

        try:
            # ── リターン系列を計算 ──
            closes = ctx.df["Close"].values.astype(float)
            if len(closes) < 2:
                return None

            # 対数リターン
            returns = list(np.diff(np.log(closes)))

            # ── レジーム更新 ──
            state = self.__class__._detector.update(returns)

            # ── クラス変数更新 ──
            self.__class__._current_regime = state
            self.__class__._lot_mult = self.__class__._detector.lot_multiplier
            self.__class__._vol_ratio = self.__class__._detector.vol_ratio
            self.__class__._regime_label = (
                "TURBULENT" if state == 1 else "CALM"
            )
            self.__class__._last_symbol = ctx.symbol

            # ── ログ出力 (状態遷移時のみ) ──
            logger.debug(
                f"[HMM] {ctx.symbol} regime={self.__class__._regime_label} "
                f"vol_ratio={self.__class__._vol_ratio:.2f} "
                f"lot_mult={self.__class__._lot_mult:.1f}x"
            )

        except Exception as e:
            logger.error(f"[HMM] Error updating regime: {e}")

        # 常に None を返す (シグナル生成しない)
        return None
