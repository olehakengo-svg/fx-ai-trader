"""
Strategy Framework — 戦略を個別管理し、アルゴリズム最適化を加速する。

構造:
  strategies/
  ├── base.py          # StrategyBase, Candidate
  ├── context.py       # SignalContext (共通インジケータ)
  ├── scalp/           # スキャルプ戦略群 + ScalperEngine
  └── daytrade/        # デイトレ戦略群 + DaytradeEngine
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.daytrade import DaytradeEngine
