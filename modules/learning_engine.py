"""
Self-Learning Engine — Analyzes closed demo trades and adjusts DemoTrader parameters.

v6.5 拡張:
  - 統計的有意性検定 (二項検定 + ベイズ事後分布 + Bootstrap CI)
  - MAFE分布分析 (SL/TP最適化推奨)
  - Kelly Criterion 推定
  - 指数減衰ウェイト (直近トレード重視)
  - レジーム条件付き評価

調整対象:
  - confidence_threshold: エントリー最低確度
  - entry_type_blacklist: 低勝率エントリータイプの除外

NOTE: sl_adjust / tp_adjust は廃止。SMC戦略(turtle_soup, trendline_sweep等)は
      独自の精密SL/TPを計算しており、グローバル乗数で上書きすると
      エッジが破壊される。(2026-04-05 audit fix)
"""
from modules.demo_db import DemoDB
from modules import stats_utils


# Strategy Aの損益分岐WR（RR 1:2.4 → WR 29.4%が理論損益分岐）
BREAKEVEN_WR = 30.0
MIN_SAMPLE = 10

# ── SMC保護: 学習エンジンが変更してはならない戦略 ──
# これらの戦略は独自のSL/TP/ペアフィルター/方向フィルターを持ち、
# BT検証済みのパラメータで稼働する。学習エンジンによるブラックリスト化・
# パラメータ上書きを禁止。(2026-04-05 audit fix)
SMC_PROTECTED = {
    "turtle_soup",       # Liquidity Grab Reversal (Connors 1995)
    "trendline_sweep",   # Trendline Sweep Trap (Edwards & Magee)
    "inducement_ob",     # Inducement & Order Block Trap (Kyle 1985)
    "post_news_vol",     # Post-News Volatility Run (Ederington 1993) — DISABLED
}


class LearningEngine:
    # v6.4: Fidelity Cutoff — v6.3パラメータ変更後のトレードのみ学習対象
    FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"

    def __init__(self, db: DemoDB):
        self._db = db

    def evaluate(self, current_params: dict, mode: str = None) -> dict:
        """
        過去トレードを分析し、パラメータ調整提案を返す。
        mode を指定するとそのモードのトレードのみ分析。

        Returns:
            {
                "adjustments": [...],
                "insights": [...],
                "data": dict,
                "mode": str,
                "quant_analysis": dict  # v6.5: 統計分析結果
            }
        """
        data = self._db.get_trades_for_learning(
            min_trades=MIN_SAMPLE, mode=mode,
            after_date=self.FIDELITY_CUTOFF,
        )
        if not data["ready"]:
            return {
                "adjustments": [],
                "insights": [f"学習データ不足: {data['sample']}/{data['min_required']}件"],
                "data": data,
            }

        adjustments = []
        insights = []
        quant_analysis = {}
        cur_conf = current_params.get("confidence_threshold", 55)

        overall_wr = data["overall_wr"]
        overall_ev = data["overall_ev"]
        sample = data["sample"]

        # ══════════════════════════════════════════════════
        # v6.5: 統計的有意性検定 (全体WR)
        # ══════════════════════════════════════════════════
        wins_total = int(round(overall_wr / 100 * sample))
        wr_test = stats_utils.binomial_test_wr(wins_total, sample, null_wr=0.45)
        wr_bayes = stats_utils.bayesian_wr_posterior(wins_total, sample)
        quant_analysis["wr_significance"] = wr_test
        quant_analysis["wr_bayesian"] = wr_bayes

        if sample >= 15:
            if wr_test["significant"]:
                insights.append(
                    f"📊 [STATS] WR {overall_wr}% は統計的に有意 "
                    f"(p={wr_test['p_value']:.3f}, N={sample})")
            else:
                insights.append(
                    f"📊 [STATS] WR {overall_wr}% は統計的に有意でない "
                    f"(p={wr_test['p_value']:.3f}, N={sample}, "
                    f"90%CI=[{wr_bayes['ci_90'][0]:.0%}-{wr_bayes['ci_90'][1]:.0%}])")

        # ── 1. Confidence threshold調整 ──
        if sample >= 15:
            if overall_wr < BREAKEVEN_WR and cur_conf < 80:
                new_conf = min(80, cur_conf + 5)
                reason = f"WR {overall_wr}% < 損益分岐{BREAKEVEN_WR}% → 確度閾値引上げ"
                adjustments.append({"param": "confidence_threshold",
                                    "old": cur_conf, "new": new_conf, "reason": reason})
                insights.append(f"📈 {reason}")
            elif overall_wr > 45 and overall_ev > 0.3 and cur_conf > 50:
                new_conf = max(45, cur_conf - 3)
                reason = f"WR {overall_wr}% & EV +{overall_ev} 好調 → 確度閾値緩和"
                adjustments.append({"param": "confidence_threshold",
                                    "old": cur_conf, "new": new_conf, "reason": reason})
                insights.append(f"📉 {reason}")

        # ── 2. エントリータイプフィルター (v6.5: 統計的有意性考慮) ──
        cur_blacklist = current_params.get("entry_type_blacklist", [])
        strategy_quant = {}
        for et, stats in data["by_type"].items():
            _et_n = stats["n"]
            _et_wr = stats["wr"]
            _et_ev = stats["ev"]

            # v6.5: 戦略別統計分析
            if _et_n >= 10:
                _et_wins = int(round(_et_wr / 100 * _et_n))
                _et_wr_test = stats_utils.binomial_test_wr(_et_wins, _et_n, null_wr=0.45)
                _et_bayes = stats_utils.bayesian_wr_posterior(_et_wins, _et_n)

                # v6.5: Kelly Criterion (戦略別)
                _et_losses = _et_n - _et_wins
                _et_avg_win = stats.get("avg_win", abs(_et_ev) if _et_ev > 0 else 1.0)
                _et_avg_loss = stats.get("avg_loss", abs(_et_ev) if _et_ev < 0 else 1.0)
                if _et_avg_win <= 0:
                    _et_avg_win = 1.0
                if _et_avg_loss <= 0:
                    _et_avg_loss = 1.0
                _et_kelly = stats_utils.kelly_criterion(
                    _et_wr / 100, _et_avg_win, _et_avg_loss)
                _et_ror = stats_utils.risk_of_ruin(
                    _et_wr / 100, _et_avg_win, _et_avg_loss)

                strategy_quant[et] = {
                    "n": _et_n, "wr": _et_wr, "ev": _et_ev,
                    "significance": _et_wr_test,
                    "bayesian": _et_bayes,
                    "kelly": _et_kelly,
                    "risk_of_ruin": _et_ror,
                }

            # SMC保護: BT検証済み戦略はブラックリスト化禁止
            if et in SMC_PROTECTED:
                continue
            if _et_n >= 15 and _et_wr < BREAKEVEN_WR and _et_ev < -0.5:
                if et not in cur_blacklist:
                    adjustments.append({
                        "param": "entry_type_blacklist_add",
                        "old": 0, "new": 1,
                        "reason": f"{et}: WR {_et_wr}%, EV {_et_ev} → 除外"
                    })
                    insights.append(f"🚫 {et} を除外推奨 (WR{_et_wr}%, {_et_n}件)")
            elif et in cur_blacklist and _et_n >= 10 and _et_wr > 40:
                adjustments.append({
                    "param": "entry_type_blacklist_remove",
                    "old": 1, "new": 0,
                    "reason": f"{et}: WR {_et_wr}%に改善 → 復活"
                })
                insights.append(f"✅ {et} 復活推奨 (WR{_et_wr}%に改善)")

        quant_analysis["by_strategy"] = strategy_quant

        # ── 3. 時間帯フィルター — Advisory only (2026-04-05 audit) ──
        for hour, stats in data["by_hour"].items():
            if stats["n"] >= 8 and stats["wr"] < 20:
                insights.append(f"⏰ {hour}:00 UTC: WR{stats['wr']}% (観測のみ)")

        # ── 4. SL幅 / 5. TP幅 — Advisory only (2026-04-05 audit fix) ──
        if sample >= 20:
            closed = self._db.get_all_closed()
            sl_losses = [t for t in closed if t["close_reason"] == "SL_HIT"]
            total_closed = len(closed)
            if len(sl_losses) >= 10 and total_closed > 0:
                # BUG FIX: denominator must be total_closed (same population as
                # sl_losses), NOT sample (which is filtered by mode/cutoff/shadow).
                # Using sample caused rates >100% (e.g. 234%, 327%) when
                # len(sl_losses from all trades) > sample (filtered subset).
                sl_hit_rate = len(sl_losses) / total_closed * 100
                assert 0 <= sl_hit_rate <= 100, f"SL hit rate out of range: {sl_hit_rate}"
                if sl_hit_rate > 60:
                    insights.append(f"🛑 SLヒット率{sl_hit_rate:.0f}% (観測のみ・自動調整なし)")
                elif sl_hit_rate < 30:
                    insights.append(f"✅ SLヒット率{sl_hit_rate:.0f}% 良好")

            # TP前反転率（同じ closed を再利用）
            tp_wins = [t for t in closed if t["close_reason"] == "TP_HIT"]
            sig_rev = [t for t in closed if t["close_reason"] == "SIGNAL_REVERSE"
                       and t["outcome"] == "WIN"]
            if tp_wins and sig_rev:
                rev_ratio = len(sig_rev) / (len(tp_wins) + len(sig_rev))
                if rev_ratio > 0.5:
                    insights.append(
                        f"🎯 TP前反転率{rev_ratio:.0%} (観測のみ・自動調整なし)")

            # ══════════════════════════════════════════════════
            # v6.5: MAFE分布分析 (SL/TP最適化推奨)
            # ══════════════════════════════════════════════════
            mafe_analysis = stats_utils.analyze_mafe(closed)
            if not mafe_analysis.get("insufficient"):
                quant_analysis["mafe"] = mafe_analysis
                _sl_rec = mafe_analysis.get("sl_recommendation", {})
                _tp_rec = mafe_analysis.get("tp_recommendation", {})
                _tp_eff = mafe_analysis.get("tp_efficiency")
                insights.append(
                    f"📐 [MAFE] SL推奨={_sl_rec.get('value', '?')} "
                    f"TP推奨={_tp_rec.get('value', '?')} "
                    f"(MAE P75={mafe_analysis['mae']['p75']}, "
                    f"MFE P50={mafe_analysis['mfe']['median']})")
                if _tp_eff is not None:
                    insights.append(
                        f"📐 [MAFE] TP効率={_tp_eff:.0%} "
                        f"(実現利益/利用可能MFE)")

            # ══════════════════════════════════════════════════
            # v6.5: 指数減衰加重EV (直近トレード重視)
            # ══════════════════════════════════════════════════
            _pnl_list = [t.get("pnl_pips", 0) for t in closed[-100:]]
            if len(_pnl_list) >= 10:
                _weights = stats_utils.exponential_decay_weights(
                    len(_pnl_list), half_life=30)
                _w_stats = stats_utils.weighted_stats(_pnl_list, _weights)
                quant_analysis["decay_weighted_ev"] = _w_stats
                insights.append(
                    f"📉 [DECAY] 減衰加重EV={_w_stats['mean']:+.3f} "
                    f"(均等EV={sum(_pnl_list)/len(_pnl_list):+.3f})")

            # ══════════════════════════════════════════════════
            # v6.5: Bootstrap EV信頼区間
            # ══════════════════════════════════════════════════
            if len(_pnl_list) >= 15:
                _ev_ci = stats_utils.bootstrap_ev_ci(_pnl_list, n_boot=3000)
                quant_analysis["ev_confidence_interval"] = _ev_ci
                if not _ev_ci.get("insufficient"):
                    insights.append(
                        f"📊 [STATS] EV 90%CI=[{_ev_ci['ci_low']:+.3f}, "
                        f"{_ev_ci['ci_high']:+.3f}] "
                        f"{'✅正EV確認' if _ev_ci['ev_significantly_positive'] else '⚠️負EV含む'}")

            # ══════════════════════════════════════════════════
            # v6.5: リスク調整済みパフォーマンス指標
            # ══════════════════════════════════════════════════
            if len(_pnl_list) >= 10:
                _sortino = stats_utils.sortino_ratio(_pnl_list, annualize=252)
                _calmar = stats_utils.calmar_ratio(_pnl_list, annualize=252)
                _pf = stats_utils.profit_factor(_pnl_list)
                quant_analysis["risk_metrics"] = {
                    "sortino": _sortino,
                    "calmar": _calmar,
                    "profit_factor": _pf,
                }
                insights.append(
                    f"📊 [RISK] Sortino={_sortino:.2f} "
                    f"Calmar={_calmar:.2f} PF={_pf:.2f}")

        # ── 6. レジーム別パフォーマンス insight (v6.5: 条件付き評価) ──
        regime_quant = {}
        for regime, stats in data["by_regime"].items():
            if stats["n"] >= 8:
                _r_wins = int(round(stats["wr"] / 100 * stats["n"]))
                _r_bayes = stats_utils.bayesian_wr_posterior(_r_wins, stats["n"])
                regime_quant[regime] = {
                    "n": stats["n"], "wr": stats["wr"], "ev": stats["ev"],
                    "bayesian": _r_bayes,
                }
                if stats["wr"] > 50:
                    insights.append(
                        f"📊 {regime}レジーム好調: WR{stats['wr']}%, "
                        f"EV{stats['ev']} (P(WR>45%)={_r_bayes['p_wr_above_45']:.0%})")
                elif stats["wr"] < BREAKEVEN_WR:
                    insights.append(
                        f"⚠️ {regime}レジーム低調: WR{stats['wr']}%, EV{stats['ev']}")
        quant_analysis["by_regime"] = regime_quant

        # 全体サマリー insight
        insights.insert(0, f"📋 全体: {sample}件, WR {overall_wr}%, EV {overall_ev}")

        mode_label = mode or "all"

        # DB記録 — 調整履歴
        for adj in adjustments:
            self._db.save_adjustment(
                parameter=adj["param"],
                old_val=adj["old"],
                new_val=adj["new"],
                reason=adj["reason"],
                win_rate=overall_wr,
                ev=overall_ev,
                sample=sample,
                mode=mode_label,
            )

        # DB記録 — 学習分析結果を永続保存
        try:
            self._db.save_learning_result(
                mode=mode_label,
                sample=sample,
                wr=overall_wr,
                ev=overall_ev,
                data=data,
                insights=insights,
                adjustments=adjustments,
            )
        except Exception:
            pass

        return {
            "adjustments": adjustments,
            "insights": insights,
            "data": data,
            "mode": mode_label,
            "quant_analysis": quant_analysis,
        }
