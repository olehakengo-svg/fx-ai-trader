"""
Auto Demo Trader — Background thread that monitors daytrade signals
and executes virtual trades with full IN/OUT recording.
"""
import threading
import time
import json
from datetime import datetime, timezone

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine


class DemoTrader:
    def __init__(self, db: DemoDB, interval_sec: int = 60):
        self._db = db
        self._engine = LearningEngine(db)
        self._interval = interval_sec
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # チューナブルパラメータ（学習エンジンが調整）
        self._params = {
            "confidence_threshold": 55,
            "max_open_trades": 1,
            "sl_adjust": 1.0,       # SL乗数 (0.8-1.3)
            "tp_adjust": 1.0,       # TP乗数 (0.8-1.3)
            "entry_type_blacklist": [],
            "session_blacklist": [],
            "learn_every_n": 10,    # N件ごとに学習
        }
        self._trade_count_since_learn = 0
        self._last_signal = None
        self._log = []  # 直近のログ (max 100)

    # ── Public API ────────────────────────────────────

    def start(self):
        with self._lock:
            if self._running:
                return {"status": "already_running"}
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True,
                                            name="DemoTrader")
            self._thread.start()
            self._add_log("🟢 デモトレーダー起動")
            return {"status": "started"}

    def stop(self):
        with self._lock:
            if not self._running:
                return {"status": "already_stopped"}
            self._running = False
            self._add_log("🔴 デモトレーダー停止")
            return {"status": "stopped"}

    def get_status(self) -> dict:
        open_trades = self._db.get_open_trades()
        stats = self._db.get_stats()
        return {
            "running": self._running,
            "params": self._params.copy(),
            "open_trades": open_trades,
            "stats": stats,
            "recent_log": list(self._log[-20:]),
            "last_signal": self._last_signal,
            "trades_since_learn": self._trade_count_since_learn,
        }

    def get_params(self) -> dict:
        return self._params.copy()

    def set_params(self, updates: dict) -> dict:
        """パラメータを手動で更新"""
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
        """手動で学習エンジンを実行"""
        result = self._engine.evaluate(self._params)
        self._apply_adjustments(result.get("adjustments", []))
        return result

    # ── Main Loop ─────────────────────────────────────

    def _run(self):
        """Background thread main loop."""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                self._add_log(f"❌ エラー: {e}")
                print(f"[DemoTrader] Error: {e}")
            time.sleep(self._interval)

    def _tick(self):
        """One cycle: check signal → manage positions."""
        # Import here to avoid circular imports at module level
        from app import (fetch_ohlcv, add_indicators, find_sr_levels,
                         compute_daytrade_signal)

        # 1. データ取得 + シグナル計算
        try:
            df = fetch_ohlcv("USDJPY=X", period="5d", interval="15m")
            df = add_indicators(df)
            df = df.dropna()
            if len(df) < 50:
                return

            sr = find_sr_levels(df)
            sig = compute_daytrade_signal(df, "15m", sr, "USDJPY=X")
        except Exception as e:
            self._add_log(f"⚠️ シグナル取得失敗: {e}")
            return

        self._last_signal = {
            "signal": sig.get("signal"),
            "confidence": sig.get("confidence"),
            "entry": sig.get("entry"),
            "entry_type": sig.get("entry_type"),
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        }

        current_price = sig.get("entry", 0)
        signal = sig.get("signal", "WAIT")
        confidence = sig.get("confidence", 0)
        entry_type = sig.get("entry_type", "unknown")

        # 2. オープンポジション管理
        open_trades = self._db.get_open_trades()
        for trade in open_trades:
            self._manage_open_trade(trade, current_price, signal, confidence)

        # 3. 新規エントリー判定
        if len(open_trades) >= self._params["max_open_trades"]:
            return
        if signal == "WAIT":
            return
        if confidence < self._params["confidence_threshold"]:
            return

        # エントリータイプブラックリスト
        if entry_type in self._params["entry_type_blacklist"]:
            return

        # セッションブラックリスト
        try:
            hour_now = datetime.now(timezone.utc).hour
            if hour_now in self._params["session_blacklist"]:
                return
        except Exception:
            pass

        # Layer状態チェック
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

        # レジーム・レイヤー情報
        regime = sig.get("regime", {})
        layer1_dir = layer_status.get("layer1", {}).get("direction", "neutral")

        trade_id = self._db.open_trade(
            direction=signal,
            entry_price=current_price,
            sl=sl, tp=tp,
            entry_type=entry_type,
            confidence=confidence,
            tf="15m",
            reasons=sig.get("reasons", []),
            regime=regime,
            layer1_dir=layer1_dir,
            score=sig.get("score", 0),
            ema_conf=ema_conf,
            sr_basis=sr_basis,
        )

        self._add_log(
            f"📥 IN: {signal} @ {current_price:.3f} | "
            f"SL {sl:.3f} TP {tp:.3f} | "
            f"Type: {entry_type} | Conf: {confidence}% | "
            f"ID: {trade_id}"
        )

    def _manage_open_trade(self, trade: dict, current_price: float,
                           new_signal: str, new_conf: int):
        """Check SL/TP hit or signal reversal for an open trade."""
        direction = trade["direction"]
        sl = trade["sl"]
        tp = trade["tp"]
        trade_id = trade["trade_id"]

        close_reason = None

        # SL/TPチェック
        if direction == "BUY":
            if current_price <= sl:
                close_reason = "SL_HIT"
            elif current_price >= tp:
                close_reason = "TP_HIT"
        else:  # SELL
            if current_price >= sl:
                close_reason = "SL_HIT"
            elif current_price <= tp:
                close_reason = "TP_HIT"

        # シグナル反転チェック（確度が閾値以上の反転シグナル）
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
                f"📤 OUT: {icon} {outcome} | "
                f"{direction} @ {trade['entry_price']:.3f} → {current_price:.3f} | "
                f"PnL: {pnl:+.1f} pips | "
                f"Reason: {close_reason} | ID: {trade_id}"
            )

            # トレードカウント → 学習トリガー
            self._trade_count_since_learn += 1
            if self._trade_count_since_learn >= self._params["learn_every_n"]:
                self._trigger_learning()

    def _trigger_learning(self):
        """N件ごとに自動学習"""
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
        """学習エンジンの提案を適用"""
        for adj in adjustments:
            p = adj["param"]
            if p == "confidence_threshold":
                self._params["confidence_threshold"] = int(adj["new"])
            elif p == "sl_adjust":
                self._params["sl_adjust"] = float(adj["new"])
            elif p == "tp_adjust":
                self._params["tp_adjust"] = float(adj["new"])
            elif p == "entry_type_blacklist_add":
                # reason contains the entry_type name
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
        if len(self._log) > 100:
            self._log = self._log[-100:]
        print(f"[DemoTrader] {msg}")
