"""
Micro-Scalp Backtest Harness
═══════════════════════════════

1秒足ベースの最小BTハーネス。look-ahead biasを徹底回避し、
コストモデル（スプレッド+遅延slippage）を明示適用。

使用:
    from strategies.micro_scalp import (
        TickVolumeSpikeMomentum, CostModel
    )
    from strategies.micro_scalp.backtest import MicroBacktester

    bars = load_1sec_bars(symbol="USD_JPY", days=30)
    cost = CostModel(spread_pips=0.8, latency_ms=150, symbol="USD_JPY")
    strat = TickVolumeSpikeMomentum(cost, spike_z=3.0, tp_atr_mult=3.0)
    bt = MicroBacktester(strat, cost)
    result = bt.run(bars)
    print(result.summary())
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from strategies.micro_scalp.base import (
    MicroStrategyBase, MicroSignal, TickBar, CostModel,
)


@dataclass
class Trade:
    entry_ts: float
    exit_ts: float
    side: str
    entry: float
    exit: float
    outcome: str           # "TP" | "SL" | "TIMEOUT"
    pnl_pips: float
    hold_sec: float
    reason: str
    same_bar_collision: bool = False   # 診断: 同バー内でTPとSL両方ヒット


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    n_bars: int = 0

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl_pips > 0)
        return wins / len(self.trades)

    @property
    def total_pnl_pips(self) -> float:
        return sum(t.pnl_pips for t in self.trades)

    @property
    def avg_pnl_pips(self) -> float:
        if not self.trades:
            return 0.0
        return self.total_pnl_pips / len(self.trades)

    @property
    def profit_factor(self) -> float:
        gross_win = sum(t.pnl_pips for t in self.trades if t.pnl_pips > 0)
        gross_loss = abs(sum(t.pnl_pips for t in self.trades if t.pnl_pips < 0))
        if gross_loss == 0:
            return float("inf") if gross_win > 0 else 0.0
        return gross_win / gross_loss

    @property
    def avg_hold_sec(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.hold_sec for t in self.trades) / len(self.trades)

    # ── 診断用メソッド ──────────────────────────────
    def outcome_breakdown(self) -> dict:
        """決済理由別の件数と平均PnL。"""
        d: dict[str, dict] = {}
        for oc in ("TP", "SL", "TIMEOUT"):
            xs = [t for t in self.trades if t.outcome == oc]
            d[oc] = {
                "n": len(xs),
                "pct": (len(xs) / len(self.trades)) if self.trades else 0.0,
                "avg_pnl": (sum(t.pnl_pips for t in xs) / len(xs)) if xs else 0.0,
                "avg_hold": (sum(t.hold_sec for t in xs) / len(xs)) if xs else 0.0,
            }
        return d

    def hold_distribution(self) -> dict:
        """保有時間の分位数（秒）。"""
        if not self.trades:
            return {"p10": 0.0, "p50": 0.0, "p90": 0.0, "max": 0.0}
        xs = sorted(t.hold_sec for t in self.trades)
        n = len(xs)

        def q(p: float) -> float:
            idx = max(0, min(n - 1, int(p * (n - 1))))
            return xs[idx]
        return {"p10": q(0.10), "p50": q(0.50), "p90": q(0.90), "max": xs[-1]}

    def realized_rr(self) -> dict:
        """実現R:R（TP平均利益 / SL平均損失）と損益分岐WR。"""
        tp = [t for t in self.trades if t.outcome == "TP"]
        sl = [t for t in self.trades if t.outcome == "SL"]
        if not tp or not sl:
            return {"r_win": 0.0, "r_loss": 0.0, "rr": 0.0, "breakeven_wr": 0.0}
        r_win = sum(t.pnl_pips for t in tp) / len(tp)
        r_loss = abs(sum(t.pnl_pips for t in sl) / len(sl))
        rr = r_win / r_loss if r_loss > 0 else 0.0
        be_wr = 1.0 / (1.0 + rr) if rr > 0 else 1.0
        return {"r_win": r_win, "r_loss": r_loss, "rr": rr, "breakeven_wr": be_wr}

    def summary(self) -> str:
        return (
            f"Trades: {self.n_trades} | "
            f"WR: {self.win_rate:.1%} | "
            f"PnL: {self.total_pnl_pips:+.1f}pips | "
            f"Avg: {self.avg_pnl_pips:+.2f}pips | "
            f"PF: {self.profit_factor:.2f} | "
            f"AvgHold: {self.avg_hold_sec:.0f}s"
        )

    def diagnostic_report(self) -> str:
        """人が読む診断レポート。"""
        if not self.trades:
            return "(No trades)"
        ob = self.outcome_breakdown()
        hd = self.hold_distribution()
        rr = self.realized_rr()
        lines = [
            f"  Outcome: TP={ob['TP']['n']} ({ob['TP']['pct']:.0%}, "
            f"avg+{ob['TP']['avg_pnl']:.2f}p, hold {ob['TP']['avg_hold']:.0f}s) | "
            f"SL={ob['SL']['n']} ({ob['SL']['pct']:.0%}, "
            f"avg{ob['SL']['avg_pnl']:.2f}p, hold {ob['SL']['avg_hold']:.0f}s) | "
            f"TO={ob['TIMEOUT']['n']} ({ob['TIMEOUT']['pct']:.0%}, "
            f"avg{ob['TIMEOUT']['avg_pnl']:+.2f}p)",
            f"  Hold: p10={hd['p10']:.0f}s p50={hd['p50']:.0f}s "
            f"p90={hd['p90']:.0f}s max={hd['max']:.0f}s",
            f"  R:R realized={rr['rr']:.2f} "
            f"(R_win={rr['r_win']:.2f}p, R_loss={rr['r_loss']:.2f}p) "
            f"→ break-even WR={rr['breakeven_wr']:.1%}",
        ]
        return "\n".join(lines)


class MicroBacktester:
    """1秒足BT。各バー evaluate→シグナルあればポジション保有→
    TP/SL/タイムアウトで決済。同時保有は1つまで。"""

    def __init__(self, strategy: MicroStrategyBase, cost: CostModel, warmup: int = 2000):
        self.strategy = strategy
        self.cost = cost
        self.warmup = warmup

    def run(self, bars: list[TickBar]) -> BacktestResult:
        result = BacktestResult(n_bars=len(bars))
        in_position = False
        current_sig: Optional[MicroSignal] = None
        entry_idx = -1

        pip = self.cost.pip

        for i in range(self.warmup, len(bars) - 1):
            bar = bars[i]

            # ── ポジション保有中 → 決済判定 ──
            if in_position and current_sig is not None:
                hold_sec = bar.ts - bars[entry_idx].ts
                hit_tp = False
                hit_sl = False
                timeout = hold_sec >= current_sig.max_hold_sec

                if current_sig.side == "BUY":
                    if bar.low <= current_sig.sl:
                        hit_sl = True
                    elif bar.high >= current_sig.tp:
                        hit_tp = True
                else:
                    if bar.high >= current_sig.sl:
                        hit_sl = True
                    elif bar.low <= current_sig.tp:
                        hit_tp = True

                if hit_tp or hit_sl or timeout:
                    # 決済価格決定（同bar内でTPとSL両方ヒット時は保守的にSL優先）
                    collision = hit_tp and hit_sl
                    if hit_sl:
                        exit_mid = current_sig.sl
                        outcome = "SL"
                    elif hit_tp:
                        exit_mid = current_sig.tp
                        outcome = "TP"
                    else:
                        exit_mid = bar.close
                        outcome = "TIMEOUT"

                    exit_px = self.cost.apply_to_exit(current_sig.side, exit_mid)
                    if current_sig.side == "BUY":
                        pnl = (exit_px - current_sig.entry) / pip
                    else:
                        pnl = (current_sig.entry - exit_px) / pip

                    result.trades.append(Trade(
                        entry_ts=bars[entry_idx].ts,
                        exit_ts=bar.ts,
                        side=current_sig.side,
                        entry=current_sig.entry,
                        exit=exit_px,
                        outcome=outcome,
                        pnl_pips=pnl,
                        hold_sec=hold_sec,
                        reason=current_sig.reason,
                        same_bar_collision=collision,
                    ))
                    in_position = False
                    current_sig = None
                    entry_idx = -1
                continue

            # ── 新規エントリー探索 ──
            history = bars[: i + 1]
            try:
                sig = self.strategy.evaluate(history)
            except Exception:
                sig = None
            if sig is not None:
                current_sig = sig
                in_position = True
                entry_idx = i

        return result


# ══════════════════════════════════════════════════
# 合成データジェネレーター（検証用）
# ══════════════════════════════════════════════════
def generate_synthetic_bars(
    n_bars: int = 10000,
    seed: int = 42,
    base_price: float = 150.00,
    symbol: str = "USD_JPY",
) -> list[TickBar]:
    """検証用1秒足を生成。trend+noise+occasional volume spike を含む。"""
    import random
    rng = random.Random(seed)
    bars = []
    price = base_price
    # JPY: 1 pip = 0.01
    pip = 0.01 if "JPY" in symbol else 0.0001

    for i in range(n_bars):
        # ベースドリフト（ランダムウォーク + たまにtrend）
        drift_cycle = (i // 300) % 5  # 5分周期でトレンド切替
        drift = {0: 0.0, 1: 0.3, 2: -0.2, 3: 0.0, 4: -0.1}[drift_cycle] * pip
        noise = rng.gauss(0, 0.4 * pip)
        dp = drift + noise

        # 2%の確率で "volume spike" イベント（大口注文想定）
        is_spike = rng.random() < 0.02
        if is_spike:
            spike_dir = rng.choice([1, -1])
            dp += spike_dir * rng.uniform(2.0, 5.0) * pip
            volume = rng.randint(80, 200)
        else:
            volume = rng.randint(5, 40)

        open_p = price
        close_p = price + dp
        high = max(open_p, close_p) + abs(rng.gauss(0, 0.2 * pip))
        low = min(open_p, close_p) - abs(rng.gauss(0, 0.2 * pip))

        bars.append(TickBar(
            ts=float(i),
            open=open_p,
            high=high,
            low=low,
            close=close_p,
            tick_volume=volume,
        ))
        price = close_p

    return bars


if __name__ == "__main__":
    # デモ実行: 3コストシナリオ × 3戦略 のマトリクス検証
    from strategies.micro_scalp import (
        TickVolumeSpikeMomentum,
        VolatilityBreakoutPullback,
        OrderFlowImbalanceMR,
    )

    print("=" * 78)
    print("  Micro-Scalp Strategy Suite — Multi-Cost-Scenario Validation")
    print("=" * 78)

    # 異なるボラティリティ構造の合成データを2つ生成して頑健性チェック
    bars_a = generate_synthetic_bars(n_bars=10000, seed=42, symbol="USD_JPY")
    bars_b = generate_synthetic_bars(n_bars=10000, seed=7, symbol="USD_JPY")

    scenarios = [
        ("OPTIMISTIC", CostModel(spread_pips=0.8, latency_ms=150, slippage_per_ms=0.001, symbol="USD_JPY")),
        ("REALISTIC",  CostModel(spread_pips=1.2, latency_ms=300, slippage_per_ms=0.003, symbol="USD_JPY")),
        ("PESSIMISTIC", CostModel(spread_pips=1.8, latency_ms=500, slippage_per_ms=0.005, symbol="USD_JPY")),
    ]

    strategy_defs = [
        (TickVolumeSpikeMomentum, {"spike_z": 3.0, "tp_atr_mult": 3.0}),
        (VolatilityBreakoutPullback, {"lookback_sec": 1800, "pullback_ratio": 0.5}),
        (OrderFlowImbalanceMR, {"window_sec": 180, "z_thresh": 2.0}),
    ]

    print(f"\nDataset A: {len(bars_a)} bars seed=42 | Dataset B: {len(bars_b)} bars seed=7\n")

    for label, cost in scenarios:
        print("─" * 78)
        print(f" Scenario: {label}  "
              f"spread={cost.spread_pips}p latency={cost.latency_ms}ms "
              f"slip/ms={cost.slippage_per_ms} → one-way={cost.total_cost_pips:.2f}p "
              f"round-trip={2*cost.total_cost_pips:.2f}p")
        print("─" * 78)

        for strat_cls, params in strategy_defs:
            # Dataset A
            strat_a = strat_cls(cost, **params)
            bt_a = MicroBacktester(strat_a, cost, warmup=2000)
            res_a = bt_a.run(bars_a)
            # Dataset B
            strat_b = strat_cls(cost, **params)
            bt_b = MicroBacktester(strat_b, cost, warmup=2000)
            res_b = bt_b.run(bars_b)

            print(f"\n[{strat_a.name}] (A) {res_a.summary()}")
            if res_a.n_trades > 0:
                print(res_a.diagnostic_report())
            print(f"[{strat_b.name}] (B) {res_b.summary()}")
            if res_b.n_trades > 0:
                print(res_b.diagnostic_report())

        print()
