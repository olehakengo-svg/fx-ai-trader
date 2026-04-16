"""
Conditional Return Analyzer
═══════════════════════════

**目的**: 「いつ/どの条件で市場は予測可能か」を system atically に探索する。

従来のBT: 仮説 → 実装 → 検証 → 結果 ≈ 0 → 新仮説 → …
本ツール: データ → 条件別 forward-return 分析 → 有意 pocket 発見 → 仮説化

**理論背景**:
- Future return Y_t,h = (P_{t+h} - P_t) / P_t
- Condition vector X_t = (hour, weekday, ATR_rank, ret_lag1, ...)
- 各 X のカテゴリ別に E[Y|X], Std[Y|X], Sharpe[Y|X] を算出
- N が十分大きく (≥30)、|E[Y|X]| > cost かつ |Sharpe| > 0.3 の cell を pocket 候補

**使い方**:
```python
analyzer = ConditionalReturnAnalyzer(
    bars_df,                          # pandas DataFrame (OHLC with DatetimeIndex)
    horizons_bars=[1, 4, 24],        # forward horizons (in bars)
    cost_bp_roundtrip=1.5,           # 往復コスト [bps]
)
analyzer.add_condition("hour", lambda df: df.index.hour)
analyzer.add_condition("atr_rank", lambda df: df["atr"].rank(pct=True).round(1))
result = analyzer.compute()
pockets = analyzer.find_pockets(min_n=30, min_sharpe=0.3)
```
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
import math


@dataclass
class EdgePocket:
    """発見された条件付きエッジ pocket."""
    condition_name: str           # e.g. "hour"
    condition_value: object        # e.g. 15 (= 15:00時台)
    horizon_bars: int
    n: int
    mean_return_bp: float         # bps単位
    std_return_bp: float
    sharpe: float                 # mean / std × sqrt(N / horizon) のような
    hit_rate: float               # P(sign(Y) = sign(mean_Y))
    break_even_bp: float          # cost相当のbreak-even return
    net_expectancy_bp: float      # mean_return - cost
    quality_score: float = 0.0    # 総合スコア (N, Sharpe, EV の合成)

    def __str__(self) -> str:
        return (
            f"[{self.condition_name}={self.condition_value!r} h={self.horizon_bars}] "
            f"N={self.n} mean={self.mean_return_bp:+.1f}bp "
            f"std={self.std_return_bp:.1f}bp sharpe={self.sharpe:+.2f} "
            f"HR={self.hit_rate:.1%} net={self.net_expectancy_bp:+.1f}bp"
        )


@dataclass
class ConditionalReturnAnalyzer:
    """条件別 forward return 分析器."""
    # bars: pandas.DataFrame を想定するが、pandas 依存を明示せず duck-typed
    bars: object
    horizons_bars: list[int] = field(default_factory=lambda: [1, 4, 24])
    cost_bp_roundtrip: float = 1.5        # 往復コスト [bps] = 0.015%
    price_col: str = "close"
    _conditions: dict = field(default_factory=dict)   # name -> callable(df) -> series

    # ──────────────────────────────────────────────
    def add_condition(self, name: str, fn: Callable) -> "ConditionalReturnAnalyzer":
        """条件を追加: fn(bars) → category series."""
        self._conditions[name] = fn
        return self

    def _forward_returns(self) -> dict:
        """各 horizon について forward return を算出. DataFrame に列追加."""
        import pandas as pd
        df = self.bars
        out = {}
        price = df[self.price_col]
        for h in self.horizons_bars:
            # 基本は log-return (bps単位で近似的に加法的に扱える)
            fwd = (price.shift(-h) / price - 1.0) * 10000.0  # bps
            out[h] = fwd
        return out

    def compute(self) -> list[EdgePocket]:
        """全条件 × 全horizon を走査し、pocket 候補を返す (閾値フィルタなし全列挙)."""
        import pandas as pd
        import numpy as np

        if not self._conditions:
            raise ValueError("条件を add_condition() で追加してください")

        fwd = self._forward_returns()
        pockets: list[EdgePocket] = []

        for cname, cfn in self._conditions.items():
            cat = cfn(self.bars)
            cat_name = cname

            for h, fret in fwd.items():
                # 有効なペアのみ使用
                df = pd.DataFrame({"cat": cat, "ret": fret}).dropna()
                if df.empty:
                    continue

                grouped = df.groupby("cat")["ret"]
                for cval, grp in grouped:
                    n = len(grp)
                    if n < 10:
                        continue
                    mean = grp.mean()
                    std = grp.std(ddof=1) if n > 1 else 0.0
                    if std == 0 or math.isnan(std):
                        continue
                    sharpe = mean / std * math.sqrt(n)   # t-stat 風
                    hr = float((np.sign(grp) == np.sign(mean)).mean())
                    be = self.cost_bp_roundtrip
                    net = abs(mean) - be   # 絶対値 — 方向に賭ければ net
                    # Quality score: N, Sharpe絶対値, net を multiplicative に統合
                    quality = (
                        math.log1p(n) * abs(sharpe) * max(net, 0.0) / (abs(mean) + 1.0)
                    )
                    pockets.append(EdgePocket(
                        condition_name=cat_name,
                        condition_value=cval,
                        horizon_bars=h,
                        n=n,
                        mean_return_bp=float(mean),
                        std_return_bp=float(std),
                        sharpe=float(sharpe),
                        hit_rate=hr,
                        break_even_bp=be,
                        net_expectancy_bp=float(abs(mean) - be),
                        quality_score=float(quality),
                    ))
        return pockets

    def find_pockets(
        self,
        min_n: int = 30,
        min_abs_sharpe: float = 0.3,
        require_positive_net: bool = True,
    ) -> list[EdgePocket]:
        """閾値を満たす pocket のみ抽出. quality_score 降順で返す."""
        all_pockets = self.compute()
        filtered = [
            p for p in all_pockets
            if p.n >= min_n
            and abs(p.sharpe) >= min_abs_sharpe
            and (not require_positive_net or p.net_expectancy_bp > 0)
        ]
        filtered.sort(key=lambda p: p.quality_score, reverse=True)
        return filtered

    def summary_report(
        self,
        min_n: int = 30,
        min_abs_sharpe: float = 0.3,
        top_k: int = 20,
    ) -> str:
        pockets = self.find_pockets(min_n=min_n, min_abs_sharpe=min_abs_sharpe)
        lines = [
            "═══ Conditional Return Edge Discovery ═══",
            f"Bars: {len(self.bars)} | Horizons: {self.horizons_bars} | "
            f"Cost: {self.cost_bp_roundtrip:.2f}bp roundtrip",
            f"Conditions tested: {list(self._conditions.keys())}",
            f"Pockets found: {len(pockets)} "
            f"(min_n={min_n}, min|Sharpe|={min_abs_sharpe})",
            "",
        ]
        if not pockets:
            lines.append("(有意 pocket なし — データ量・条件・threshold を見直し)")
            return "\n".join(lines)

        lines.append(f"Top {min(top_k, len(pockets))} by quality_score:")
        for p in pockets[:top_k]:
            lines.append("  " + str(p))
        return "\n".join(lines)
