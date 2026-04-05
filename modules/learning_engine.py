"""
Self-Learning Engine — Analyzes closed demo trades and adjusts DemoTrader parameters.

調整対象:
  - confidence_threshold: エントリー最低確度
  - entry_type_blacklist: 低勝率エントリータイプの除外
  - session_blacklist: 低勝率時間帯の除外

NOTE: sl_adjust / tp_adjust は廃止。SMC戦略(turtle_soup, trendline_sweep等)は
      独自の精密SL/TPを計算しており、グローバル乗数で上書きすると
      エッジが破壊される。(2026-04-05 audit fix)
"""
from modules.demo_db import DemoDB


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
}


class LearningEngine:
    def __init__(self, db: DemoDB):
        self._db = db

    def evaluate(self, current_params: dict, mode: str = None) -> dict:
        """
        過去トレードを分析し、パラメータ調整提案を返す。
        mode を指定するとそのモードのトレードのみ分析。

        Returns:
            {
                "adjustments": [{"param": str, "old": float, "new": float, "reason": str}],
                "insights": [str],
                "data": dict,
                "mode": str
            }
        """
        data = self._db.get_trades_for_learning(min_trades=MIN_SAMPLE, mode=mode)
        if not data["ready"]:
            return {
                "adjustments": [],
                "insights": [f"学習データ不足: {data['sample']}/{data['min_required']}件"],
                "data": data,
            }

        adjustments = []
        insights = []
        cur_conf = current_params.get("confidence_threshold", 55)

        overall_wr = data["overall_wr"]
        overall_ev = data["overall_ev"]
        sample = data["sample"]

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

        # ── 2. エントリータイプフィルター ──
        cur_blacklist = current_params.get("entry_type_blacklist", [])
        for et, stats in data["by_type"].items():
            # SMC保護: BT検証済み戦略はブラックリスト化禁止
            if et in SMC_PROTECTED:
                continue
            if stats["n"] >= 15 and stats["wr"] < BREAKEVEN_WR and stats["ev"] < -0.5:
                if et not in cur_blacklist:
                    adjustments.append({
                        "param": "entry_type_blacklist_add",
                        "old": 0, "new": 1,
                        "reason": f"{et}: WR {stats['wr']}%, EV {stats['ev']} → 除外"
                    })
                    insights.append(f"🚫 {et} を除外推奨 (WR{stats['wr']}%, {stats['n']}件)")
            elif et in cur_blacklist and stats["n"] >= 10 and stats["wr"] > 40:
                adjustments.append({
                    "param": "entry_type_blacklist_remove",
                    "old": 1, "new": 0,
                    "reason": f"{et}: WR {stats['wr']}%に改善 → 復活"
                })
                insights.append(f"✅ {et} 復活推奨 (WR{stats['wr']}%に改善)")

        # ── 3. 時間帯フィルター — Advisory only (2026-04-05 audit) ──
        # session_blacklistはデッドコード（適用先なし）だったため廃止。
        # 低WR時間帯はインサイトのみ出力。
        for hour, stats in data["by_hour"].items():
            if stats["n"] >= 8 and stats["wr"] < 20:
                insights.append(f"⏰ {hour}:00 UTC: WR{stats['wr']}% (観測のみ)")

        # ── 4. SL幅 — Advisory only (2026-04-05 audit fix) ──
        # sl_adjust/tp_adjustはグローバル乗数であり、SMC戦略の精密SL/TPを
        # 破壊するリスクがある。SL/TPは各戦略が独自に計算済みのため廃止。
        # インサイトのみ出力（パラメータ変更なし）。
        if sample >= 20:
            closed = self._db.get_all_closed()
            sl_losses = [t for t in closed if t["close_reason"] == "SL_HIT"]
            if len(sl_losses) >= 10:
                sl_hit_rate = len(sl_losses) / sample * 100
                if sl_hit_rate > 60:
                    insights.append(f"🛑 SLヒット率{sl_hit_rate:.0f}% (観測のみ・自動調整なし)")
                elif sl_hit_rate < 30:
                    insights.append(f"✅ SLヒット率{sl_hit_rate:.0f}% 良好")

        # ── 5. TP幅調整 — 廃止 (2026-04-05 audit fix) ──
        if sample >= 20:
            closed = self._db.get_all_closed()
            tp_wins = [t for t in closed if t["close_reason"] == "TP_HIT"]
            sig_rev = [t for t in closed if t["close_reason"] == "SIGNAL_REVERSE" and t["outcome"] == "WIN"]
            if tp_wins and sig_rev:
                rev_ratio = len(sig_rev) / (len(tp_wins) + len(sig_rev))
                if rev_ratio > 0.5:
                    insights.append(f"🎯 TP前反転率{rev_ratio:.0%} (観測のみ・自動調整なし)")

        # ── 6. レジーム別パフォーマンス insight ──
        for regime, stats in data["by_regime"].items():
            if stats["n"] >= 8:
                if stats["wr"] > 50:
                    insights.append(f"📊 {regime}レジームが好調: WR{stats['wr']}%, EV{stats['ev']}")
                elif stats["wr"] < BREAKEVEN_WR:
                    insights.append(f"⚠️ {regime}レジームが低調: WR{stats['wr']}%, EV{stats['ev']}")

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
        }
