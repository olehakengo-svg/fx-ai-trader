"""
Auto Demo Trader — Background threads that monitor daytrade/scalp signals
and execute virtual trades with full IN/OUT recording.
Supports simultaneous daytrade + scalp mode operation.
"""
import threading
import time
import json
from datetime import datetime, timezone

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine

# モード別設定
MODE_CONFIG = {
    "daytrade": {
        "interval_sec": 60,       # 1分ごとにチェック
        "tf": "15m",
        "period": "5d",
        "signal_fn": "compute_daytrade_signal",
        "label": "デイトレード",
        "icon": "📊",
    },
    "scalp": {
        "interval_sec": 15,       # 15秒ごとにチェック（スキャルプは高頻度）
        "tf": "1m",
        "period": "1d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルピング",
        "icon": "⚡",
    },
}


class DemoTrader:
    def __init__(self, db: DemoDB):
        self._db = db
        self._engine = LearningEngine(db)
        self._lock = threading.Lock()

        # モード別ランナー管理
        self._runners = {}   # mode -> {"running": bool, "thread": Thread}

        # チューナブルパラメータ（学習エンジンが調整、全モード共通）
        self._params = {
            "confidence_threshold": 55,
            "max_open_trades": 1,   # モードあたり最大ポジション
            "sl_adjust": 1.0,
            "tp_adjust": 1.0,
            "entry_type_blacklist": [],
            "session_blacklist": [],
            "learn_every_n": 10,
        }
        self._trade_count_since_learn = 0
        self._last_signals = {}   # mode -> last signal dict
        self._log = []

    # ── Public API ────────────────────────────────────

    def start(self, mode: str = "daytrade"):
        """指定モードのデモトレーダーを起動"""
        if mode not in MODE_CONFIG:
            return {"status": "error", "message": f"Unknown mode: {mode}"}

        with self._lock:
            runner = self._runners.get(mode, {})
            if runner.get("running"):
                return {"status": "already_running", "mode": mode}

            cfg = MODE_CONFIG[mode]
            self._runners[mode] = {"running": True, "thread": None}
            t = threading.Thread(
                target=self._run, args=(mode,), daemon=True,
                name=f"DemoTrader-{mode}"
            )
            self._runners[mode]["thread"] = t
            t.start()
            self._add_log(f"{cfg['icon']} {cfg['label']}モード起動")
            return {"status": "started", "mode": mode}

    def stop(self, mode: str = None):
        """指定モードを停止。mode=Noneなら全モード停止"""
        with self._lock:
            modes_to_stop = [mode] if mode else list(self._runners.keys())
            stopped = []
            for m in modes_to_stop:
                runner = self._runners.get(m, {})
                if runner.get("running"):
                    runner["running"] = False
                    cfg = MODE_CONFIG.get(m, {})
                    self._add_log(f"🔴 {cfg.get('label', m)}モード停止")
                    stopped.append(m)
            return {"status": "stopped", "modes": stopped}

    def is_running(self, mode: str = None) -> bool:
        if mode:
            return self._runners.get(mode, {}).get("running", False)
        return any(r.get("running", False) for r in self._runners.values())

    def get_status(self) -> dict:
        open_trades = self._db.get_open_trades()
        stats = self._db.get_stats()
        modes_status = {}
        for m, cfg in MODE_CONFIG.items():
            runner = self._runners.get(m, {})
            modes_status[m] = {
                "running": runner.get("running", False),
                "label": cfg["label"],
                "icon": cfg["icon"],
                "tf": cfg["tf"],
                "interval": cfg["interval_sec"],
                "last_signal": self._last_signals.get(m),
            }
        # Restore logs from DB if in-memory log is empty (restart recovery)
        if not self._log:
            try:
                self._log = list(reversed(self._db.get_logs(200)))
            except Exception:
                pass

        return {
            "running": self.is_running(),
            "modes": modes_status,
            "params": self._params.copy(),
            "open_trades": open_trades,
            "stats": stats,
            "recent_log": list(self._log[-200:]),
            "trades_since_learn": self._trade_count_since_learn,
        }

    def get_params(self) -> dict:
        return self._params.copy()

    def set_params(self, updates: dict) -> dict:
        allowed = {"confidence_threshold", "sl_adjust", "tp_adjust",
                    "max_open_trades", "learn_every_n"}
        applied = {}
        for k, v in updates.items():
            if k in allowed:
                self._params[k] = v
                applied[k] = v
        if applied:
            self._add_log(f"⚙️ パラメータ更新: {applied}")
        return {"applied": applied, "params": self._params.copy()}

    def run_learning(self) -> dict:
        result = self._engine.evaluate(self._params)
        self._apply_adjustments(result.get("adjustments", []))
        return result

    # ── Main Loop (per mode) ──────────────────────────

    def _run(self, mode: str):
        """Background thread main loop for a specific mode."""
        cfg = MODE_CONFIG[mode]
        interval = cfg["interval_sec"]
        while self._runners.get(mode, {}).get("running", False):
            try:
                self._tick(mode)
            except Exception as e:
                self._add_log(f"❌ [{cfg['label']}] エラー: {e}")
                print(f"[DemoTrader/{mode}] Error: {e}")
            time.sleep(interval)

    def _tick(self, mode: str):
        """One cycle for a specific mode."""
        cfg = MODE_CONFIG[mode]

        # Import here to avoid circular imports
        from app import fetch_ohlcv, add_indicators, find_sr_levels

        if mode == "daytrade":
            from app import compute_daytrade_signal as compute_fn
        else:
            from app import compute_scalp_signal as compute_fn

        tf = cfg["tf"]
        period = cfg["period"]

        # 1. データ取得 + シグナル計算
        try:
            df = fetch_ohlcv("USDJPY=X", period=period, interval=tf)
            df = add_indicators(df)
            df = df.dropna()
            if len(df) < 50:
                return

            sr = find_sr_levels(df)
            sig = compute_fn(df, tf, sr, "USDJPY=X")
        except Exception as e:
            self._add_log(f"⚠️ [{cfg['label']}] シグナル取得失敗: {e}")
            return

        self._last_signals[mode] = {
            "signal": sig.get("signal"),
            "confidence": sig.get("confidence"),
            "entry": sig.get("entry"),
            "entry_type": sig.get("entry_type"),
            "mode": mode,
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        }

        current_price = sig.get("entry", 0)
        signal = sig.get("signal", "WAIT")
        confidence = sig.get("confidence", 0)
        entry_type = sig.get("entry_type", "unknown")

        # 2. このモードのオープンポジション管理
        open_trades = self._db.get_open_trades()
        mode_trades = [t for t in open_trades if t.get("tf") == tf]
        for trade in mode_trades:
            self._manage_open_trade(trade, current_price, signal, confidence, mode)

        # 3. 新規エントリー判定
        if len(mode_trades) >= self._params["max_open_trades"]:
            return
        if signal == "WAIT":
            return
        if confidence < self._params["confidence_threshold"]:
            return
        if entry_type in self._params["entry_type_blacklist"]:
            return

        try:
            hour_now = datetime.now(timezone.utc).hour
            if hour_now in self._params["session_blacklist"]:
                return
        except Exception:
            pass

        layer_status = sig.get("layer_status", {})
        if not layer_status.get("trade_ok", True):
            return

        # ── エントリー実行 ──
        sl = sig.get("sl", 0)
        tp = sig.get("tp", 0)

        # 学習によるSL/TP調整
        if self._params["sl_adjust"] != 1.0:
            sl_dist = abs(current_price - sl)
            sl_dist *= self._params["sl_adjust"]
            sl = current_price - sl_dist if signal == "BUY" else current_price + sl_dist
            sl = round(sl, 3)
        if self._params["tp_adjust"] != 1.0:
            tp_dist = abs(tp - current_price)
            tp_dist *= self._params["tp_adjust"]
            tp = current_price + tp_dist if signal == "BUY" else current_price - tp_dist
            tp = round(tp, 3)

        # SR推奨情報
        sr_map = sig.get("sr_entry_map", {})
        rec = sr_map.get("recommended", {})
        ema_conf = rec.get("ema_confidence", confidence) if rec else confidence
        sr_basis = rec.get("sr_basis", 0) if rec else 0

        regime = sig.get("regime", {})
        layer1_dir = layer_status.get("layer1", {}).get("direction", "neutral")

        trade_id = self._db.open_trade(
            direction=signal,
            entry_price=current_price,
            sl=sl, tp=tp,
            entry_type=entry_type,
            confidence=confidence,
            tf=tf,
            reasons=sig.get("reasons", []),
            regime=regime,
            layer1_dir=layer1_dir,
            score=sig.get("score", 0),
            ema_conf=ema_conf,
            sr_basis=sr_basis,
        )

        self._add_log(
            f"{cfg['icon']} 📥 IN [{cfg['label']}]: {signal} @ {current_price:.3f} | "
            f"SL {sl:.3f} TP {tp:.3f} | "
            f"Type: {entry_type} | Conf: {confidence}% | "
            f"ID: {trade_id}"
        )

    def _manage_open_trade(self, trade: dict, current_price: float,
                           new_signal: str, new_conf: int, mode: str):
        """Check SL/TP hit or signal reversal for an open trade."""
        cfg = MODE_CONFIG.get(mode, {})
        direction = trade["direction"]
        sl = trade["sl"]
        tp = trade["tp"]
        trade_id = trade["trade_id"]

        close_reason = None

        if direction == "BUY":
            if current_price <= sl:
                close_reason = "SL_HIT"
            elif current_price >= tp:
                close_reason = "TP_HIT"
        else:
            if current_price >= sl:
                close_reason = "SL_HIT"
            elif current_price <= tp:
                close_reason = "TP_HIT"

        if not close_reason:
            if (direction == "BUY" and new_signal == "SELL" and
                    new_conf >= self._params["confidence_threshold"]):
                close_reason = "SIGNAL_REVERSE"
            elif (direction == "SELL" and new_signal == "BUY" and
                  new_conf >= self._params["confidence_threshold"]):
                close_reason = "SIGNAL_REVERSE"

        if close_reason:
            result = self._db.close_trade(trade_id, current_price, close_reason)
            pnl = result.get("pnl_pips", 0)
            outcome = result.get("outcome", "?")
            icon = "✅" if outcome == "WIN" else "❌"

            self._add_log(
                f"{cfg.get('icon','')} 📤 OUT [{cfg.get('label','?')}]: {icon} {outcome} | "
                f"{direction} @ {trade['entry_price']:.3f} → {current_price:.3f} | "
                f"PnL: {pnl:+.1f} pips | "
                f"Reason: {close_reason} | ID: {trade_id}"
            )

            self._trade_count_since_learn += 1
            if self._trade_count_since_learn >= self._params["learn_every_n"]:
                self._trigger_learning()

    def _trigger_learning(self):
        self._trade_count_since_learn = 0
        try:
            result = self._engine.evaluate(self._params)
            adjustments = result.get("adjustments", [])
            insights = result.get("insights", [])

            if adjustments:
                self._apply_adjustments(adjustments)
                self._add_log(f"🧠 学習完了: {len(adjustments)}件の調整を適用")
                for ins in insights[:3]:
                    self._add_log(f"   {ins}")
            else:
                self._add_log(f"🧠 学習完了: 調整なし (WR {result['data'].get('overall_wr',0)}%)")
        except Exception as e:
            self._add_log(f"⚠️ 学習エラー: {e}")

    def _apply_adjustments(self, adjustments: list):
        for adj in adjustments:
            p = adj["param"]
            if p == "confidence_threshold":
                self._params["confidence_threshold"] = int(adj["new"])
            elif p == "sl_adjust":
                self._params["sl_adjust"] = float(adj["new"])
            elif p == "tp_adjust":
                self._params["tp_adjust"] = float(adj["new"])
            elif p == "entry_type_blacklist_add":
                et = adj["reason"].split(":")[0].strip()
                if et not in self._params["entry_type_blacklist"]:
                    self._params["entry_type_blacklist"].append(et)
            elif p == "entry_type_blacklist_remove":
                et = adj["reason"].split(":")[0].strip()
                if et in self._params["entry_type_blacklist"]:
                    self._params["entry_type_blacklist"].remove(et)
            elif p == "session_blacklist_add":
                h = int(adj["old"])
                if h not in self._params["session_blacklist"]:
                    self._params["session_blacklist"].append(h)

    def _add_log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self._log.append(entry)
        if len(self._log) > 200:
            self._log = self._log[-200:]
        try:
            self._db.add_log(ts, msg)
        except Exception:
            pass
        print(f"[DemoTrader] {msg}")
