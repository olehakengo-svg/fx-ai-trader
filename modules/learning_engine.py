"""
Self-Learning Engine — Analyzes closed demo trades and adjusts DemoTrader parameters.

調整対象:
  - confidence_threshold: エントリー最低確度
  - entry_type_blacklist: 低勝率エントリータイプの除外
  - session_blacklist: 低勝率時間帯の除外
  - sl_adjust: SL幅の微調整 (0.8x - 1.3x)
  - tp_adjust: TP幅の微調整 (0.8x - 1.3x)
"""
from modules.demo_db import DemoDB


# Strategy Aの損益分岐WR（RR 1:2.4 → WR 29.4%が理論損益分岐）
BREAKEVEN_WR = 30.0
MIN_SAMPLE = 10


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
        cur_sl = current_params.get("sl_adjust", 1.0)
        cur_tp = current_params.get("tp_adjust", 1.0)

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

        # ── 3. 時間帯フィルター ──
        cur_session_bl = current_params.get("session_blacklist", [])
        for hour, stats in data["by_hour"].items():
            if stats["n"] >= 8 and stats["wr"] < 20:
                if hour not in cur_session_bl:
                    adjustments.append({
                        "param": "session_blacklist_add",
                        "old": hour, "new": hour,
                        "reason": f"{hour}時UTC: WR {stats['wr']}% → 取引除外"
                    })
                    insights.append(f"⏰ {hour}:00 UTC を除外推奨 (WR{stats['wr']}%)")

        # ── 4. SL幅調整 ──
        if sample >= 20:
            closed = self._db.get_all_closed()
            sl_losses = [t for t in closed if t["close_reason"] == "SL_HIT"]
            if len(sl_losses) >= 10:
                # SLヒット率が高すぎる → SL広げる
                sl_hit_rate = len(sl_losses) / sample * 100
                if sl_hit_rate > 60 and cur_sl < 1.3:
                    new_sl = min(1.3, round(cur_sl + 0.1, 2))
                    reason = f"SLヒット率{sl_hit_rate:.0f}% > 60% → SL拡大 {cur_sl}→{new_sl}x"
                    adjustments.append({"param": "sl_adjust",
                                        "old": cur_sl, "new": new_sl, "reason": reason})
                    insights.append(f"🛑 {reason}")
                elif sl_hit_rate < 30 and cur_sl > 0.8:
                    new_sl = max(0.8, round(cur_sl - 0.05, 2))
                    reason = f"SLヒット率{sl_hit_rate:.0f}% < 30% → SL適正化 {cur_sl}→{new_sl}x"
                    adjustments.append({"param": "sl_adjust",
                                        "old": cur_sl, "new": new_sl, "reason": reason})
                    insights.append(f"✅ {reason}")

        # ── 5. TP幅調整 ──
        if sample >= 20:
            closed = self._db.get_all_closed()
            tp_wins = [t for t in closed if t["close_reason"] == "TP_HIT"]
            sig_rev = [t for t in closed if t["close_reason"] == "SIGNAL_REVERSE" and t["outcome"] == "WIN"]
            if tp_wins and sig_rev:
                # TP前にシグナル反転で利確するケースが多い → TP縮小
                rev_ratio = len(sig_rev) / (len(tp_wins) + len(sig_rev))
                if rev_ratio > 0.5 and cur_tp > 0.8:
                    new_tp = max(0.8, round(cur_tp - 0.1, 2))
                    reason = f"TP前反転{rev_ratio:.0%} > 50% → TP縮小 {cur_tp}→{new_tp}x"
                    adjustments.append({"param": "tp_adjust",
                                        "old": cur_tp, "new": new_tp, "reason": reason})
                    insights.append(f"🎯 {reason}")

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
