"""
HMM Regime Detector — 2状態HMMによるFXボラティリティレジーム検出。

学術的根拠:
  - Nystrup et al (2024, JAM): HMMレジーム検出により MaxDD を50%削減。
  - Hamilton (1989): Markov-switching model の金融市場適用。
  - Ang & Bekaert (2002): レジーム依存リスクプレミアム。

設計:
  - State 0: calm (低ボラ) → フルポジション (1.0x)
  - State 1: turbulent (高ボラ) → 縮小ポジション (0.3x)

  依存ライブラリ不要の簡易HMM代理実装:
  - hmmlearn等のHMMライブラリに依存せず、閾値ベースで近似。
  - ローリング20バー実現ボラティリティ vs 60バー中央値ボラティリティの比率で判定。
  - ヒステリシス: 閾値を超えない限り現在状態を維持 (状態遷移のチャタリング防止)。
"""
import numpy as np
from typing import List, Tuple


class HMMRegimeDetector:
    """2-state HMM proxy for FX volatility regime detection.

    State 0: calm (low vol)   -> full position (1.0x)
    State 1: turbulent (high vol) -> reduced position (0.3x)

    Uses threshold-based detection as a lightweight HMM approximation
    without requiring hmmlearn or scipy dependencies.
    """

    # ── レジーム閾値 ──
    TURBULENT_THRESHOLD = 1.5   # current_vol > 1.5x median -> turbulent
    CALM_THRESHOLD      = 1.0   # current_vol < 1.0x median -> calm
    # ヒステリシス帯: 1.0 < ratio < 1.5 では状態維持

    # ── ポジションサイジング ──
    CALM_MULTIPLIER     = 1.0
    TURBULENT_MULTIPLIER = 0.3

    def __init__(self, lookback: int = 60):
        """
        Args:
            lookback: ベースラインボラティリティ計算期間 (デフォルト60バー)
        """
        self.lookback = lookback
        self._current_state: int = 0       # 0=calm, 1=turbulent
        self._state_probs: List[float] = [1.0, 0.0]  # [P(calm), P(turbulent)]
        self._vol_ratio: float = 1.0       # 直近の vol ratio (診断用)

    def update(self, returns: list) -> int:
        """レジーム状態を更新。

        Args:
            returns: リターン系列 (log return or simple return)。
                     最低 lookback 期間必要。

        Returns:
            0 (calm) or 1 (turbulent)
        """
        if len(returns) < self.lookback:
            return self._current_state

        recent = np.array(returns[-20:])
        full = np.array(returns[-self.lookback:])

        # 現在の20バー実現ボラティリティ
        current_vol = np.std(recent) if len(recent) > 1 else 0.0

        # 60バー中の5バーステップ移動ウィンドウでボラティリティ中央値を計算
        rolling_vols = []
        for i in range(0, len(full) - 20 + 1, 5):
            window = full[i:i + 20]
            if len(window) > 1:
                rolling_vols.append(np.std(window))

        if not rolling_vols:
            return self._current_state

        median_vol = np.median(rolling_vols)

        # ボラティリティ比率
        ratio = current_vol / median_vol if median_vol > 0 else 1.0
        self._vol_ratio = ratio

        # ── 閾値ベースの状態遷移 (ヒステリシス付き) ──
        if ratio > self.TURBULENT_THRESHOLD:
            self._current_state = 1  # turbulent
        elif ratio < self.CALM_THRESHOLD:
            self._current_state = 0  # calm
        # else: ヒステリシス帯 → 現在状態を維持

        # 擬似確率 (連続値の状態推定)
        # ratio=0 → P(turbulent)=0, ratio=2 → P(turbulent)=1.0
        p_turb = min(ratio / 2.0, 1.0)
        self._state_probs = [1.0 - p_turb, p_turb]

        return self._current_state

    @property
    def current_state(self) -> int:
        """現在のレジーム状態。0=calm, 1=turbulent。"""
        return self._current_state

    @property
    def state_probs(self) -> Tuple[float, float]:
        """(P(calm), P(turbulent)) の擬似確率。"""
        return tuple(self._state_probs)

    @property
    def is_turbulent(self) -> bool:
        """乱流レジームかどうか。"""
        return self._current_state == 1

    @property
    def is_calm(self) -> bool:
        """穏やかなレジームかどうか。"""
        return self._current_state == 0

    @property
    def lot_multiplier(self) -> float:
        """レジームに基づくロット乗数。calm=1.0, turbulent=0.3。"""
        return self.TURBULENT_MULTIPLIER if self.is_turbulent else self.CALM_MULTIPLIER

    @property
    def vol_ratio(self) -> float:
        """直近の vol ratio (current_vol / median_vol)。診断用。"""
        return self._vol_ratio

    def get_regime_label(self) -> str:
        """人間可読なレジームラベルを返す。"""
        if self.is_turbulent:
            return f"TURBULENT (vol_ratio={self._vol_ratio:.2f}, lot={self.lot_multiplier:.1f}x)"
        return f"CALM (vol_ratio={self._vol_ratio:.2f}, lot={self.lot_multiplier:.1f}x)"

    def reset(self):
        """状態をデフォルト (calm) にリセット。"""
        self._current_state = 0
        self._state_probs = [1.0, 0.0]
        self._vol_ratio = 1.0
