"""
Backtest Engine — 共通BT統計基盤 + Walk-Forward Optimization
═══════════════════════════════════════════════════════════════

目的:
  1. 5つのBT関数で重複する統計計算(~667行)を共通化
  2. 真のWalk-Forward安定性検証 (3窓→Anchored 5窓)
  3. Monte Carlo CIによるパフォーマンス信頼区間
  4. In-Sample vs Out-of-Sample 比較による過適合検出

設計方針:
  - 既存BT関数の内部ロジック(シグナル生成/トレードシミュレーション)は変更しない
  - 統計計算のみ共通化し、既存関数から呼び出す形で段階的に移行
  - WFOはDataFrame分割 + 既存BT関数の _df_override で実現

使用方法:
  from modules.backtest_engine import BacktestEngine
  # 既存BT関数の結果から:
  result = BacktestEngine.compute_results(trades, pnl_fn=my_pnl)
  # WFO:
  wfo = BacktestEngine.walk_forward_anchored(trades, n_windows=5)
  # Monte Carlo:
  mc = BacktestEngine.monte_carlo_confidence(returns, n_sims=2000)
"""
import math
import random
from typing import List, Dict, Callable, Optional, Tuple
from modules.stats_utils import (
    sortino_ratio, calmar_ratio, profit_factor,
    kelly_criterion, risk_of_ruin,
    binomial_test_wr, bootstrap_ev_ci,
)


class BacktestEngine:
    """共通BT統計エンジン + Walk-Forward Optimization"""

    # ══════════════════════════════════════════════════════
    #  1. 統合統計計算 (5つのBT関数の重複コードを一本化)
    # ══════════════════════════════════════════════════════

    @staticmethod
    def compute_results(
        trades: List[dict],
        pnl_fn: Optional[Callable] = None,
        min_trades: int = 10,
        wf_windows: int = 3,
        annualize: int = 252,
    ) -> dict:
        """
        トレードリストから包括的な統計を計算する。

        既存の5つのBT関数で ~100行ずつ重複していた以下を統合:
          - WR / EV / Avg Hold
          - MaxDD (pip + R)
          - Sharpe / Sortino / Calmar / PF
          - Walk-Forward 3窓安定性
          - エントリータイプ別統計
          - Kelly / Risk of Ruin

        Args:
            trades: BT結果のトレード辞書リスト
                    期待キー: outcome, entry_type, bars_held
                    + pnl_fn が使う追加キー
            pnl_fn: trade dict → float の PnL 計算関数
                    None の場合はデフォルト (pnl_pips or pnl_r)
            min_trades: 最低トレード数 (未満はエラー)
            wf_windows: Walk-Forward 窓数 (default: 3)
            annualize: Sharpe年率化係数

        Returns:
            dict with: stats, walk_forward, entry_breakdown, quant, error
        """
        if len(trades) < min_trades:
            return {
                "error": f"サンプル数不足 ({len(trades)}/{min_trades})",
                "trades": len(trades),
            }

        # ── デフォルト PnL 関数 ──
        if pnl_fn is None:
            def pnl_fn(t):
                if "pnl_r" in t:
                    return t["pnl_r"]
                _ef = t.get("exit_friction_m", 0)
                if t.get("outcome") == "WIN":
                    return t.get("tp_m", 1.5) - _ef
                else:
                    return -(t.get("actual_sl_m", t.get("sl_m", 1.0)) + _ef)

        # ── 基本統計 ──
        total = len(trades)
        wins = sum(1 for t in trades if t.get("outcome") == "WIN")
        wr = round(wins / total * 100, 1)
        avg_hold = round(
            sum(t.get("bars_held", 0) for t in trades) / total, 1)

        rets = [pnl_fn(t) for t in trades]
        ev = round(sum(rets) / total, 4)

        # ── リスク指標 ──
        std_r = _std(rets)
        sharpe = round(
            (ev / std_r * math.sqrt(annualize)) if std_r > 0 else 0.0, 3)
        _sortino = sortino_ratio(rets, annualize=annualize)
        _calmar = calmar_ratio(rets, annualize=annualize)
        _pf = profit_factor(rets)

        # ── MaxDD ──
        eq, peak, mdd = 0.0, 0.0, 0.0
        dd_start = 0
        dd_max_duration = 0
        dd_cur_start = 0
        for i, r in enumerate(rets):
            eq += r
            if eq > peak:
                peak = eq
                dd_cur_start = i
            dd = peak - eq
            if dd > mdd:
                mdd = dd
                dd_start = dd_cur_start
                dd_max_duration = i - dd_cur_start
        mdd = round(mdd, 4)

        # ── Walk-Forward ──
        wf_result = BacktestEngine._walk_forward_split(
            trades, pnl_fn, wf_windows)

        # ── エントリータイプ別統計 ──
        entry_breakdown = BacktestEngine._entry_type_breakdown(
            trades, pnl_fn)

        # ── Quant指標 (v6.5) ──
        win_rets = [r for r in rets if r > 0]
        loss_rets = [abs(r) for r in rets if r < 0]
        avg_win = sum(win_rets) / len(win_rets) if win_rets else 0
        avg_loss = sum(loss_rets) / len(loss_rets) if loss_rets else 0
        _kelly = kelly_criterion(wr / 100, avg_win, avg_loss)
        _ror = risk_of_ruin(wr / 100, avg_win, avg_loss)
        _wr_test = binomial_test_wr(wins, total, null_wr=0.45)

        return {
            "stats": {
                "trades": total,
                "wins": wins,
                "win_rate": wr,
                "ev": ev,
                "avg_hold": avg_hold,
                "sharpe": sharpe,
                "sortino": _sortino,
                "calmar": _calmar,
                "profit_factor": _pf,
                "max_dd": mdd,
                "max_dd_duration": dd_max_duration,
                "avg_win": round(avg_win, 4),
                "avg_loss": round(avg_loss, 4),
                "rr_ratio": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
            },
            "walk_forward": wf_result,
            "entry_breakdown": entry_breakdown,
            "quant": {
                "kelly": _kelly,
                "risk_of_ruin": _ror,
                "wr_significance": _wr_test,
            },
        }

    # ══════════════════════════════════════════════════════
    #  2. Walk-Forward Analysis
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _walk_forward_split(
        trades: List[dict],
        pnl_fn: Callable,
        n_windows: int = 3,
    ) -> dict:
        """
        N窓安定性チェック (既存の3窓WFと互換)。
        同一パラメータが全窓で正EVか検証。
        """
        total = len(trades)
        window_size = total // n_windows
        if window_size < 5:
            return {"windows": [], "consistency": "N/A", "n_windows": 0}

        windows = []
        for wi in range(n_windows):
            wt = trades[wi * window_size: (wi + 1) * window_size]
            if len(wt) < 5:
                continue
            ww = sum(1 for t in wt if t.get("outcome") == "WIN")
            w_rets = [pnl_fn(t) for t in wt]
            wwr = round(ww / len(wt) * 100, 1)
            wev = round(sum(w_rets) / len(wt), 4)
            w_sharpe = 0.0
            _s = _std(w_rets)
            if _s > 0 and len(w_rets) > 1:
                w_sharpe = round(
                    (sum(w_rets) / len(w_rets)) / _s * math.sqrt(252), 3)
            windows.append({
                "window": wi + 1,
                "trades": len(wt),
                "win_rate": wwr,
                "ev": wev,
                "sharpe": w_sharpe,
            })

        profitable = sum(1 for w in windows if w.get("ev", -1) > 0)
        return {
            "windows": windows,
            "n_windows": len(windows),
            "profitable_windows": profitable,
            "consistency": f"{profitable}/{len(windows)}",
            "all_positive": profitable == len(windows),
        }

    @staticmethod
    def walk_forward_anchored(
        trades: List[dict],
        pnl_fn: Optional[Callable] = None,
        n_splits: int = 5,
        train_ratio: float = 0.7,
    ) -> dict:
        """
        Anchored Walk-Forward Optimization (真のWFO)。

        方式: Expanding Window (Anchored)
          Split 1: [====TRAIN====][=TEST=]
          Split 2: [======TRAIN======][=TEST=]
          Split 3: [========TRAIN========][=TEST=]
          ...

        各splitで:
          - Train期間のパフォーマンスを計算 (In-Sample)
          - Test期間のパフォーマンスを計算 (Out-of-Sample)
          - IS vs OOS の乖離を測定 (過適合シグナル)

        Returns:
            splits: [{train_stats, test_stats, degradation}]
            summary: IS avg vs OOS avg, overfitting_score
        """
        if pnl_fn is None:
            def pnl_fn(t):
                if "pnl_r" in t:
                    return t["pnl_r"]
                _ef = t.get("exit_friction_m", 0)
                if t.get("outcome") == "WIN":
                    return t.get("tp_m", 1.5) - _ef
                else:
                    return -(t.get("actual_sl_m", t.get("sl_m", 1.0)) + _ef)

        total = len(trades)
        test_size = total // (n_splits + 1)  # 各テスト窓のサイズ
        if test_size < 5:
            return {"error": "データ不足", "n": total,
                    "min_required": 5 * (n_splits + 1)}

        splits = []
        is_sharpes = []
        oos_sharpes = []

        for si in range(n_splits):
            # Anchored: train always starts at 0
            train_end = total - (n_splits - si) * test_size
            test_start = train_end
            test_end = test_start + test_size

            if train_end < 10 or test_end > total:
                continue

            train_trades = trades[:train_end]
            test_trades = trades[test_start:test_end]

            if len(train_trades) < 10 or len(test_trades) < 5:
                continue

            # ── Train (IS) stats ──
            train_rets = [pnl_fn(t) for t in train_trades]
            train_wins = sum(1 for t in train_trades
                             if t.get("outcome") == "WIN")
            train_wr = round(train_wins / len(train_trades) * 100, 1)
            train_ev = round(sum(train_rets) / len(train_rets), 4)
            train_std = _std(train_rets)
            train_sharpe = round(
                (train_ev / train_std * math.sqrt(252))
                if train_std > 0 else 0.0, 3)

            # ── Test (OOS) stats ──
            test_rets = [pnl_fn(t) for t in test_trades]
            test_wins = sum(1 for t in test_trades
                            if t.get("outcome") == "WIN")
            test_wr = round(test_wins / len(test_trades) * 100, 1)
            test_ev = round(sum(test_rets) / len(test_rets), 4)
            test_std = _std(test_rets)
            test_sharpe = round(
                (test_ev / test_std * math.sqrt(252))
                if test_std > 0 else 0.0, 3)

            # ── 劣化度 (OOS vs IS) ──
            ev_degradation = (
                round((test_ev - train_ev) / max(abs(train_ev), 0.001), 3)
                if train_ev != 0 else 0)
            sharpe_degradation = (
                round((test_sharpe - train_sharpe)
                      / max(abs(train_sharpe), 0.001), 3)
                if train_sharpe != 0 else 0)

            is_sharpes.append(train_sharpe)
            oos_sharpes.append(test_sharpe)

            splits.append({
                "split": si + 1,
                "train": {
                    "n": len(train_trades), "wr": train_wr,
                    "ev": train_ev, "sharpe": train_sharpe,
                },
                "test": {
                    "n": len(test_trades), "wr": test_wr,
                    "ev": test_ev, "sharpe": test_sharpe,
                },
                "ev_degradation_pct": ev_degradation,
                "sharpe_degradation_pct": sharpe_degradation,
            })

        if not splits:
            return {"error": "有効なsplitなし", "n": total}

        # ── サマリー ──
        avg_is_sharpe = sum(is_sharpes) / len(is_sharpes)
        avg_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes)
        oos_positive = sum(1 for s in splits if s["test"]["ev"] > 0)

        # 過適合スコア: IS-OOS Sharpe 比率
        # 1.0 = 完全一致(理想), >1.5 = IS >> OOS(過適合疑い)
        overfit_ratio = (
            round(avg_is_sharpe / max(avg_oos_sharpe, 0.001), 2)
            if avg_oos_sharpe > 0
            else (999.0 if avg_is_sharpe > 0 else 1.0))

        return {
            "splits": splits,
            "summary": {
                "n_splits": len(splits),
                "avg_is_sharpe": round(avg_is_sharpe, 3),
                "avg_oos_sharpe": round(avg_oos_sharpe, 3),
                "oos_positive_windows": oos_positive,
                "oos_consistency": f"{oos_positive}/{len(splits)}",
                "overfit_ratio": overfit_ratio,
                "overfit_assessment": (
                    "LOW" if overfit_ratio <= 1.3
                    else "MODERATE" if overfit_ratio <= 2.0
                    else "HIGH"),
            },
        }

    # ══════════════════════════════════════════════════════
    #  3. Monte Carlo Simulation
    # ══════════════════════════════════════════════════════

    @staticmethod
    def monte_carlo_confidence(
        trades: List[dict],
        pnl_fn: Optional[Callable] = None,
        n_sims: int = 2000,
        ci_level: float = 0.95,
    ) -> dict:
        """
        Monte Carlo + Bootstrap によるパフォーマンス信頼区間。

        手法の使い分け (v6.5 bugfix):
          EV / WR / PF: Bootstrap（復元抽出）→ サンプリング不確実性を測定
            旧実装はシャッフル(順序入替)のみで、EV=sum/N が不変 → CI幅=0 バグ
          MaxDD: シャッフル（順序入替）→ 順序リスクを測定
            MaxDDは到着順序に依存するため、シャッフルが正しい

        Purpose:
          Bootstrap: 「このサンプルから推定される母集団のEV/WR/PFの不確実性」
          Shuffle:   「たまたまこの順番だったから良いDD/悪いDDだった」リスク
        """
        if pnl_fn is None:
            def pnl_fn(t):
                if "pnl_r" in t:
                    return t["pnl_r"]
                _ef = t.get("exit_friction_m", 0)
                if t.get("outcome") == "WIN":
                    return t.get("tp_m", 1.5) - _ef
                else:
                    return -(t.get("actual_sl_m", t.get("sl_m", 1.0)) + _ef)

        if len(trades) < 10:
            return {"error": "データ不足", "n": len(trades)}

        rets = [pnl_fn(t) for t in trades]
        outcomes = [t.get("outcome", "LOSS") for t in trades]
        n = len(rets)

        sim_evs = []
        sim_mdds = []
        sim_pfs = []
        sim_wrs = []

        for _ in range(n_sims):
            # ── Bootstrap (復元抽出) → EV, WR, PF ──
            # random.choices: 重複を許してN個をサンプリング
            boot_idx = random.choices(range(n), k=n)
            boot_rets = [rets[i] for i in boot_idx]
            boot_outcomes = [outcomes[i] for i in boot_idx]

            # EV (Bootstrap)
            sim_evs.append(sum(boot_rets) / len(boot_rets))

            # WR (Bootstrap)
            sim_wrs.append(
                sum(1 for o in boot_outcomes if o == "WIN")
                / len(boot_outcomes) * 100)

            # PF (Bootstrap)
            gp = sum(r for r in boot_rets if r > 0)
            gl = abs(sum(r for r in boot_rets if r < 0))
            sim_pfs.append(gp / gl if gl > 0 else 0)

            # ── Shuffle (順序入替) → MaxDD ──
            # MaxDDは到着順序に依存 → シャッフルで順序リスクを測定
            shuf_idx = list(range(n))
            random.shuffle(shuf_idx)
            shuf_rets = [rets[i] for i in shuf_idx]
            eq, peak, mdd = 0.0, 0.0, 0.0
            for r in shuf_rets:
                eq += r
                if eq > peak:
                    peak = eq
                dd = peak - eq
                if dd > mdd:
                    mdd = dd
            sim_mdds.append(mdd)

        # ── 信頼区間 ──
        alpha = (1 - ci_level) / 2

        def _ci(data):
            s = sorted(data)
            low_idx = int(alpha * len(s))
            high_idx = int((1 - alpha) * len(s))
            return {
                "mean": round(sum(s) / len(s), 4),
                "median": round(s[len(s) // 2], 4),
                "ci_low": round(s[low_idx], 4),
                "ci_high": round(s[high_idx], 4),
                "p5": round(s[int(0.05 * len(s))], 4),
                "p95": round(s[int(0.95 * len(s))], 4),
            }

        # 実績値 (元のトレード順序)
        actual_mdd = 0.0
        eq, peak = 0.0, 0.0
        for r in rets:
            eq += r
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > actual_mdd:
                actual_mdd = dd

        return {
            "n_sims": n_sims,
            "n_trades": len(trades),
            "ci_level": ci_level,
            "ev": _ci(sim_evs),
            "win_rate": _ci(sim_wrs),
            "max_dd": _ci(sim_mdds),
            "profit_factor": _ci(sim_pfs),
            "actual": {
                "ev": round(sum(rets) / len(rets), 4),
                "max_dd": round(actual_mdd, 4),
                "win_rate": round(
                    sum(1 for o in outcomes if o == "WIN")
                    / len(outcomes) * 100, 1),
            },
            # 実績MaxDD vs シミュレーション中央値の比較
            # 実績がP95より悪い = "運が悪かった" (本来はもっと良い)
            # 実績がP5より良い = "運が良かった" (本来はもっと悪い)
            "mdd_luck_assessment": (
                "UNLUCKY" if actual_mdd > sorted(sim_mdds)[int(0.95 * n_sims)]
                else "LUCKY" if actual_mdd < sorted(sim_mdds)[int(0.05 * n_sims)]
                else "NORMAL"),
        }

    # ══════════════════════════════════════════════════════
    #  4. エントリータイプ別統計 (共通化)
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _entry_type_breakdown(
        trades: List[dict],
        pnl_fn: Callable,
    ) -> dict:
        """エントリータイプ別の WR/EV/N を計算"""
        stats: Dict[str, dict] = {}
        for t in trades:
            et = t.get("entry_type", "unknown")
            if et not in stats:
                stats[et] = {"wins": 0, "total": 0, "pnl_sum": 0.0,
                             "hold_sum": 0}
            stats[et]["total"] += 1
            stats[et]["pnl_sum"] += pnl_fn(t)
            stats[et]["hold_sum"] += t.get("bars_held", 0)
            if t.get("outcome") == "WIN":
                stats[et]["wins"] += 1

        result = {}
        for et, s in sorted(stats.items(), key=lambda x: -x[1]["total"]):
            n = s["total"]
            result[et] = {
                "trades": n,
                "wins": s["wins"],
                "win_rate": round(s["wins"] / n * 100, 1),
                "ev": round(s["pnl_sum"] / n, 4),
                "avg_hold": round(s["hold_sum"] / n, 1),
            }
        return result


# ── ヘルパー ──

def _std(values: list) -> float:
    """標準偏差 (numpy非依存)"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)
