"""
Daily Review Engine — 毎日自動でトレード結果を分析し、
アルゴリズムの微調整が必要かどうかを判断・記録する。

スケジュール: UTC 00:00（日本時間09:00）に自動実行
分析対象: 前日のデモトレード結果（モード別）
出力: daily_reviews テーブルに記録 + 必要に応じてパラメータ調整
"""
import threading
import time
import json
from datetime import datetime, timezone, timedelta

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine

# デイリーレビューの判定基準
DAILY_THRESHOLDS = {
    "min_trades_for_review": 5,      # 最低5トレードで分析実行
    "danger_wr": 25.0,               # WR < 25% → 即座に閾値引上げ
    "warning_wr": 30.0,              # WR < 30% → 注意
    "good_wr": 40.0,                 # WR >= 40% → 良好
    "excellent_wr": 50.0,            # WR >= 50% → 優秀
    "danger_ev": -0.5,              # EV < -0.5 → 即座に対処
    "min_daily_pips_target": 100.0,  # 日次目標 100 pips
    "consecutive_loss_days": 3,      # 3日連続マイナスで緊急調整
}

MODE_CONFIG = {
    "daytrade": {"label": "デイトレード", "icon": "📊"},
    "scalp": {"label": "スキャルピング", "icon": "⚡"},
    "swing": {"label": "スイング", "icon": "🌊"},
}


class DailyReviewEngine:
    """デイリー自動レビューエンジン"""

    def __init__(self, db: DemoDB, learning_engine: LearningEngine):
        self._db = db
        self._learning = learning_engine
        self._running = False
        self._thread = None
        self._last_review_date = None

    # ── Public API ────────────────────────────────────

    def start(self):
        """バックグラウンドスケジューラーを起動"""
        if self._running:
            return {"status": "already_running"}
        self._running = True
        self._thread = threading.Thread(
            target=self._scheduler_loop, daemon=True,
            name="DailyReviewEngine"
        )
        self._thread.start()
        return {"status": "started"}

    def stop(self):
        """スケジューラーを停止"""
        self._running = False
        return {"status": "stopped"}

    def is_running(self) -> bool:
        return self._running

    def run_review_now(self, target_date: str = None, params: dict = None) -> dict:
        """手動で即時レビュー実行"""
        if target_date is None:
            # 前日を対象
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        return self._execute_daily_review(target_date, params or {})

    def get_review_history(self, limit: int = 30, mode: str = None) -> list:
        """デイリーレビュー履歴を取得"""
        return self._db.get_daily_reviews(limit=limit, mode=mode)

    def get_algo_changes(self, limit: int = 50) -> list:
        """アルゴリズム変更ログを取得"""
        return self._db.get_algo_changes(limit=limit)

    # ── Scheduler ─────────────────────────────────────

    def _scheduler_loop(self):
        """毎日 UTC 00:00 にレビューを実行するループ"""
        while self._running:
            now = datetime.now(timezone.utc)
            today_str = now.strftime("%Y-%m-%d")

            # UTC 00:00-00:30 の間に前日レビューを実行
            if now.hour == 0 and self._last_review_date != today_str:
                yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                try:
                    self._execute_daily_review(yesterday)
                    self._last_review_date = today_str
                    print(f"[DailyReview] Completed review for {yesterday}")
                except Exception as e:
                    print(f"[DailyReview] Error: {e}")

            # 60秒ごとにチェック
            time.sleep(60)

    # ── Core Review Logic ─────────────────────────────

    def _execute_daily_review(self, review_date: str, params: dict = None) -> dict:
        """指定日のデイリーレビューを実行"""
        results = {}
        all_insights = []

        for mode, cfg in MODE_CONFIG.items():
            result = self._review_mode(review_date, mode, cfg, params)
            results[mode] = result
            all_insights.extend(result.get("insights", []))

        # 全モード横断分析
        cross_mode = self._cross_mode_analysis(review_date, results)
        results["_cross_mode"] = cross_mode
        all_insights.extend(cross_mode.get("insights", []))

        # ログに記録
        try:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            summary_lines = [f"📅 デイリーレビュー完了 ({review_date})"]
            for mode, r in results.items():
                if mode.startswith("_"):
                    continue
                icon = MODE_CONFIG.get(mode, {}).get("icon", "")
                label = MODE_CONFIG.get(mode, {}).get("label", mode)
                n = r.get("trades_today", 0)
                wr = r.get("wr_today", 0)
                pnl = r.get("pnl_today", 0)
                adj_count = len(r.get("adjustments", []))
                summary_lines.append(
                    f"  {icon} {label}: {n}件, WR {wr}%, PnL {pnl:+.1f}pips"
                    + (f", {adj_count}件調整" if adj_count else "")
                )
            for line in summary_lines:
                self._db.add_log(ts, line)
        except Exception:
            pass

        return results

    def _review_mode(self, review_date: str, mode: str, cfg: dict,
                     params: dict = None) -> dict:
        """モード別のデイリーレビュー"""
        label = cfg["label"]
        icon = cfg["icon"]

        # 当日のトレード取得
        trades = self._db.get_trades_by_date(review_date, mode=mode)
        insights = []
        adjustments = []

        trades_today = len(trades)
        wins_today = sum(1 for t in trades if t.get("outcome") == "WIN")
        pnl_today = sum(t.get("pnl_pips", 0) for t in trades)
        wr_today = round(wins_today / trades_today * 100, 1) if trades_today > 0 else 0
        ev_today = round(pnl_today / trades_today, 3) if trades_today > 0 else 0

        # 累積データ取得
        learning_data = self._db.get_trades_for_learning(min_trades=1, mode=mode)
        cumulative_trades = learning_data.get("sample", 0)
        cumulative_wr = learning_data.get("overall_wr", 0)
        cumulative_ev = learning_data.get("overall_ev", 0)

        # ── 分析 ──
        if trades_today < DAILY_THRESHOLDS["min_trades_for_review"]:
            insights.append(f"{icon} {label}: {trades_today}件（分析最低件数未満）")
        else:
            # 1. 当日パフォーマンス評価
            if wr_today >= DAILY_THRESHOLDS["excellent_wr"]:
                insights.append(f"✅ {label}: WR {wr_today}% 優秀")
            elif wr_today >= DAILY_THRESHOLDS["good_wr"]:
                insights.append(f"✅ {label}: WR {wr_today}% 良好")
            elif wr_today >= DAILY_THRESHOLDS["warning_wr"]:
                insights.append(f"⚠️ {label}: WR {wr_today}% 注意")
            else:
                insights.append(f"🚨 {label}: WR {wr_today}% 危険水準")

            # 2. PnL評価
            if pnl_today > 0:
                insights.append(f"📈 {label}: 当日 +{pnl_today:.1f} pips")
            else:
                insights.append(f"📉 {label}: 当日 {pnl_today:.1f} pips")

            # 3. エントリータイプ別の当日パフォーマンス
            by_type = {}
            for t in trades:
                et = t.get("entry_type", "unknown")
                by_type.setdefault(et, {"wins": 0, "total": 0, "pnl": 0})
                by_type[et]["total"] += 1
                if t.get("outcome") == "WIN":
                    by_type[et]["wins"] += 1
                by_type[et]["pnl"] += t.get("pnl_pips", 0)

            for et, stats in by_type.items():
                et_wr = round(stats["wins"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
                if stats["total"] >= 3 and et_wr < 20:
                    insights.append(f"🚫 {label}/{et}: 当日WR {et_wr}% → 要監視")
                elif stats["total"] >= 3 and et_wr >= 50:
                    insights.append(f"🎯 {label}/{et}: 当日WR {et_wr}% 好調")

            # 4. 連続負け日チェック
            recent_reviews = self._db.get_daily_reviews(limit=5, mode=mode)
            consecutive_loss = 0
            for rev in recent_reviews:
                if rev.get("pnl_today", 0) < 0:
                    consecutive_loss += 1
                else:
                    break

            if pnl_today < 0:
                consecutive_loss += 1  # 今日も含める

            if consecutive_loss >= DAILY_THRESHOLDS["consecutive_loss_days"]:
                insights.append(
                    f"🚨 {label}: {consecutive_loss}日連続マイナス → 緊急パラメータ見直し推奨"
                )

            # 5. 当日のクローズ理由分析
            close_reasons = {}
            for t in trades:
                cr = t.get("close_reason", "unknown")
                close_reasons[cr] = close_reasons.get(cr, 0) + 1

            sl_hits = close_reasons.get("SL_HIT", 0)
            tp_hits = close_reasons.get("TP_HIT", 0)
            if trades_today > 0:
                sl_rate = sl_hits / trades_today * 100
                if sl_rate > 70:
                    insights.append(
                        f"🛑 {label}: SLヒット率 {sl_rate:.0f}% → SL幅拡大検討"
                    )
                tp_rate = tp_hits / trades_today * 100
                if tp_rate > 0 and tp_rate < 15:
                    insights.append(
                        f"🎯 {label}: TPヒット率 {tp_rate:.0f}% → TP縮小検討"
                    )

        # 累積学習エンジン実行（サンプル十分なら）
        if cumulative_trades >= 10 and params:
            learning_result = self._learning.evaluate(params, mode=mode)
            adjustments = learning_result.get("adjustments", [])
            if adjustments:
                insights.append(
                    f"🧠 {label}: 学習エンジンが{len(adjustments)}件の調整を提案"
                )
                # アルゴリズム変更ログに記録
                for adj in adjustments:
                    try:
                        self._db.save_algo_change(
                            change_type="param_adjustment",
                            description=adj.get("reason", ""),
                            params_before={adj["param"]: adj["old"]},
                            params_after={adj["param"]: adj["new"]},
                            triggered_by=f"daily_review_{review_date}_{mode}",
                        )
                    except Exception:
                        pass

        # DB保存
        try:
            self._db.save_daily_review(
                review_date=review_date,
                mode=mode,
                trades_today=trades_today,
                wins_today=wins_today,
                pnl_today=pnl_today,
                wr_today=wr_today,
                ev_today=ev_today,
                cumulative_trades=cumulative_trades,
                cumulative_wr=cumulative_wr,
                cumulative_ev=cumulative_ev,
                adjustments=adjustments,
                insights=insights,
                params_snapshot=params or {},
            )
        except Exception as e:
            print(f"[DailyReview] DB save error: {e}")

        return {
            "mode": mode,
            "review_date": review_date,
            "trades_today": trades_today,
            "wins_today": wins_today,
            "pnl_today": pnl_today,
            "wr_today": wr_today,
            "ev_today": ev_today,
            "cumulative_trades": cumulative_trades,
            "cumulative_wr": cumulative_wr,
            "cumulative_ev": cumulative_ev,
            "adjustments": adjustments,
            "insights": insights,
        }

    def _cross_mode_analysis(self, review_date: str, mode_results: dict) -> dict:
        """全モード横断の分析"""
        insights = []

        total_pnl = sum(
            r.get("pnl_today", 0) for m, r in mode_results.items()
            if not m.startswith("_")
        )
        total_trades = sum(
            r.get("trades_today", 0) for m, r in mode_results.items()
            if not m.startswith("_")
        )

        target = DAILY_THRESHOLDS["min_daily_pips_target"]
        if total_trades > 0:
            if total_pnl >= target:
                insights.append(f"🎉 全モード合計: +{total_pnl:.1f} pips (目標{target}達成)")
            elif total_pnl > 0:
                pct = total_pnl / target * 100
                insights.append(
                    f"📊 全モード合計: +{total_pnl:.1f} pips (目標の{pct:.0f}%)"
                )
            else:
                insights.append(f"📉 全モード合計: {total_pnl:.1f} pips (目標未達)")

            # モード間の比較
            best_mode = max(
                ((m, r) for m, r in mode_results.items() if not m.startswith("_") and r.get("trades_today", 0) > 0),
                key=lambda x: x[1].get("pnl_today", 0),
                default=None
            )
            if best_mode:
                m, r = best_mode
                cfg = MODE_CONFIG.get(m, {})
                insights.append(
                    f"👑 最優秀: {cfg.get('label', m)} "
                    f"(+{r['pnl_today']:.1f} pips, WR {r['wr_today']}%)"
                )

        return {
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "target_pips": target,
            "target_achieved": total_pnl >= target,
            "insights": insights,
        }
