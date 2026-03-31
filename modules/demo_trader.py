"""
Auto Demo Trader — Background threads that monitor daytrade/scalp signals
and execute virtual trades with full IN/OUT recording.
Supports simultaneous daytrade + scalp mode operation.

v2: SL/TP判定をリアルタイム価格で高頻度チェック（2秒間隔）
    シグナル計算とは分離し、判定遅延を解消
"""
import threading
import time
import json
from datetime import datetime, timezone

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine
from modules.daily_review import DailyReviewEngine

# モード別設定
MODE_CONFIG = {
    "daytrade": {
        "interval_sec": 30,       # 30秒ごとにシグナルチェック
        "tf": "15m",
        "period": "5d",
        "signal_fn": "compute_daytrade_signal",
        "label": "デイトレード",
        "icon": "📊",
    },
    "scalp": {
        "interval_sec": 10,       # 10秒ごとにシグナルチェック
        "tf": "1m",
        "period": "1d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルピング",
        "icon": "⚡",
    },
    "swing": {
        "interval_sec": 300,      # 5分ごとにチェック（スイングは低頻度）
        "tf": "4h",
        "period": "60d",
        "signal_fn": "compute_swing_signal",
        "label": "スイング",
        "icon": "🌊",
    },
}

# SL/TPチェック間隔（秒）— シグナル計算とは独立して高頻度実行
# 旧2秒 → 0.5秒: スリッページ削減（本番で50%のSL_HITが0.5p超過していた）
SLTP_CHECK_INTERVAL = 0.5


class DemoTrader:
    def __init__(self, db: DemoDB):
        self._db = db
        self._engine = LearningEngine(db)
        self._daily_review = DailyReviewEngine(db, self._engine)
        self._lock = threading.Lock()

        # モード別ランナー管理
        self._runners = {}   # mode -> {"running": bool, "thread": Thread}

        # SL/TPチェッカー（全モード共通、高頻度）
        self._sltp_running = False
        self._sltp_thread = None

        # デイリーレビューエンジンを自動起動
        self._daily_review.start()

        # チューナブルパラメータ（学習エンジンが調整、全モード共通）
        self._params = {
            "confidence_threshold": 40,
            "max_open_trades": 3,
            "sl_adjust": 1.0,
            "tp_adjust": 1.0,
            "entry_type_blacklist": [],
            # 時間帯フィルター: UTC 00,01,21時を禁止（本番で全損失の94%を占める）
            "session_blacklist": [0, 1, 21],
            "learn_every_n": 10,
            # 同方向連敗制御: N連敗で同方向エントリーを一時停止
            "max_consecutive_losses": 5,
        }
        self._trade_count_since_learn = 0
        self._last_signals = {}   # mode -> last signal dict
        # 連敗トラッカー: mode -> {"direction": str, "count": int}
        self._consec_losses = {}  # mode -> {dir -> consecutive_loss_count}
        # SL後クールダウン: mode -> {"price": float, "time": datetime, "direction": str}
        self._last_exit = {}      # mode -> last exit info

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

            # SL/TPチェッカーが未起動なら起動
            self._ensure_sltp_checker()

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

            # 全モード停止ならSL/TPチェッカーも停止
            if not self.is_running():
                self._sltp_running = False

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
        # ログ件数のみ返す（全件はログ専用APIから取得）
        try:
            log_count = self._db.get_log_count()
        except Exception:
            log_count = 0

        return {
            "running": self.is_running(),
            "modes": modes_status,
            "params": self._params.copy(),
            "open_trades": open_trades,
            "stats": stats,
            "log_count": log_count,
            "trades_since_learn": self._trade_count_since_learn,
            "daily_review_active": self._daily_review.is_running(),
            "sltp_checker_active": self._sltp_running,
        }

    def get_all_logs(self) -> list:
        """DBから全ログを古い順で取得"""
        try:
            db_logs = self._db.get_logs(9999)
            return list(reversed(db_logs))
        except Exception:
            return []

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

    def run_daily_review(self, target_date: str = None) -> dict:
        """手動でデイリーレビューを実行"""
        return self._daily_review.run_review_now(
            target_date=target_date, params=self._params
        )

    def get_daily_reviews(self, limit: int = 30, mode: str = None) -> list:
        """デイリーレビュー履歴を取得"""
        return self._daily_review.get_review_history(limit=limit, mode=mode)

    def get_algo_changes(self, limit: int = 50) -> list:
        """アルゴリズム変更ログを取得"""
        return self._daily_review.get_algo_changes(limit=limit)

    def run_learning(self, mode: str = None) -> dict:
        """手動学習トリガー。modeなしで全モード実行、指定で個別実行"""
        if mode:
            result = self._engine.evaluate(self._params, mode=mode)
            self._apply_adjustments(result.get("adjustments", []))
            return result
        # 全モード分析
        all_results = {}
        for m in MODE_CONFIG.keys():
            r = self._engine.evaluate(self._params, mode=m)
            self._apply_adjustments(r.get("adjustments", []))
            all_results[m] = r
        return all_results

    # ── SL/TP Realtime Checker ────────────────────────
    # シグナル計算とは独立して、リアルタイム価格で2秒ごとにSL/TPチェック

    def _ensure_sltp_checker(self):
        """SL/TPリアルタイムチェッカーを起動（未起動の場合のみ）"""
        if self._sltp_running:
            return
        self._sltp_running = True
        self._sltp_thread = threading.Thread(
            target=self._sltp_loop, daemon=True,
            name="DemoTrader-SLTP-Checker"
        )
        self._sltp_thread.start()

    def _sltp_loop(self):
        """2秒ごとにリアルタイム価格を取得してSL/TPチェック"""
        while self._sltp_running:
            try:
                self._check_sltp_realtime()
            except Exception as e:
                print(f"[SLTP-Checker] Error: {e}")
            time.sleep(SLTP_CHECK_INTERVAL)

    def _get_realtime_price(self) -> float:
        """
        リアルタイム価格を最速で取得:
        1. _price_cache（TwelveData/yfinance）が10秒以内なら使用
        2. フォールバック: 1m足の最新Close
        """
        try:
            from modules.data import _price_cache, _cache_lock
            with _cache_lock:
                pc = dict(_price_cache)
            if pc.get("ts"):
                ts = pc["ts"]
                now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
                age = (now - ts).total_seconds()
                if age < 15:  # 15秒以内のキャッシュなら使用
                    return float(pc["data"]["price"])
        except Exception:
            pass

        # フォールバック: 1m足のキャッシュ済み最新Close
        try:
            from app import fetch_ohlcv
            df = fetch_ohlcv("USDJPY=X", period="1d", interval="1m")
            if df is not None and len(df) > 0:
                return float(df.iloc[-1]["Close"])
        except Exception:
            pass

        return 0

    def _check_sltp_realtime(self):
        """全オープントレードをリアルタイム価格でSL/TPチェック"""
        open_trades = self._db.get_open_trades()
        if not open_trades:
            return

        price = self._get_realtime_price()
        if price <= 0:
            return

        for trade in open_trades:
            direction = trade["direction"]
            sl = trade["sl"]
            tp = trade["tp"]
            trade_id = trade["trade_id"]
            tf = trade.get("tf", "")
            mode = trade.get("mode", "")

            close_reason = None

            if direction == "BUY":
                if price <= sl:
                    close_reason = "SL_HIT"
                elif price >= tp:
                    close_reason = "TP_HIT"
            else:
                if price >= sl:
                    close_reason = "SL_HIT"
                elif price <= tp:
                    close_reason = "TP_HIT"

            if close_reason:
                # モード判定
                if not mode:
                    mode = {"1m": "scalp", "15m": "daytrade", "4h": "swing"}.get(tf, "")
                cfg = MODE_CONFIG.get(mode, {})

                result = self._db.close_trade(trade_id, price, close_reason)
                pnl = result.get("pnl_pips", 0)
                outcome = result.get("outcome", "?")
                icon = "✅" if outcome == "WIN" else "❌"

                self._add_log(
                    f"{cfg.get('icon','')} 📤 OUT [{cfg.get('label','?')}]: {icon} {outcome} | "
                    f"{direction} @ {trade['entry_price']:.3f} → {price:.3f} | "
                    f"PnL: {pnl:+.1f} pips | "
                    f"Reason: {close_reason} | ID: {trade_id}"
                )

                # ── クールダウン記録（SL後の即再エントリー防止）──
                self._last_exit[mode] = {
                    "price": trade["entry_price"],
                    "exit_price": price,
                    "time": datetime.now(timezone.utc),
                    "direction": direction,
                    "reason": close_reason,
                    "outcome": outcome,
                }

                # ── 連敗カウンター更新 ──
                if mode not in self._consec_losses:
                    self._consec_losses[mode] = {}
                if outcome == "WIN":
                    # 勝ち → 同方向のカウンターリセット
                    self._consec_losses[mode][direction] = 0
                else:
                    # 負け → 同方向のカウンターを+1
                    self._consec_losses[mode][direction] = \
                        self._consec_losses[mode].get(direction, 0) + 1

                self._trade_count_since_learn += 1
                if self._trade_count_since_learn >= self._params["learn_every_n"]:
                    self._trigger_learning(current_mode=mode)

    # ── Main Loop (per mode) ──────────────────────────

    def _run(self, mode: str):
        """Background thread main loop for a specific mode."""
        cfg = MODE_CONFIG[mode]
        interval = cfg["interval_sec"]
        _consecutive_errors = 0
        while self._runners.get(mode, {}).get("running", False):
            try:
                self._tick(mode)
                _consecutive_errors = 0  # 成功したらリセット
            except Exception as e:
                _consecutive_errors += 1
                self._add_log(f"❌ [{cfg['label']}] エラー({_consecutive_errors}): {e}")
                print(f"[DemoTrader/{mode}] Error #{_consecutive_errors}: {e}")
                import traceback; traceback.print_exc()
                # エラー連続時は待ち時間を延長して回復を待つ
                if _consecutive_errors >= 5:
                    time.sleep(min(interval * 3, 300))
                else:
                    time.sleep(interval)
                continue  # sleepが重複しないようにcontinue
            time.sleep(interval)

    def _tick(self, mode: str):
        """One cycle for a specific mode — シグナル計算 + 新規エントリー判定のみ。
        SL/TPチェックは _sltp_loop が2秒間隔で独立実行。"""
        cfg = MODE_CONFIG[mode]

        # Import here to avoid circular imports
        from app import fetch_ohlcv, add_indicators, find_sr_levels

        if mode == "daytrade":
            from app import compute_daytrade_signal as compute_fn
        elif mode == "swing":
            from app import compute_swing_signal as compute_fn
        else:
            from app import compute_scalp_signal as compute_fn

        tf = cfg["tf"]
        period = cfg["period"]

        # 1. データ取得 + シグナル計算
        try:
            # scalp(1m)はperiod拡大でEMA200を確保
            fetch_period = "5d" if tf == "1m" else period
            df = fetch_ohlcv("USDJPY=X", period=fetch_period, interval=tf)
            df = add_indicators(df)
            # EMA200がNaNの行のみ除去（全列dropnaだと必要な行まで消える）
            essential_cols = [c for c in ["Close", "EMA9", "EMA21", "RSI", "ADX", "ATR"]
                             if c.lower() in [x.lower() for x in df.columns]]
            # 大文字小文字を実際のカラム名に合わせる
            actual_cols = []
            lower_map = {c.lower(): c for c in df.columns}
            for c in ["close", "ema9", "ema21", "rsi", "adx", "atr"]:
                if c in lower_map:
                    actual_cols.append(lower_map[c])
            if actual_cols:
                df = df.dropna(subset=actual_cols)
            else:
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

        # 2. シグナル反転によるクローズ判定（SL/TPは _sltp_loop が処理）
        open_trades = self._db.get_open_trades()
        mode_trades = [t for t in open_trades if t.get("tf") == tf]
        for trade in mode_trades:
            self._check_signal_reverse(trade, current_price, signal, confidence, mode)

        # 3. 新規エントリー判定
        # 再取得（SIGNAL_REVERSEでクローズされた可能性）
        open_trades = self._db.get_open_trades()
        mode_trades = [t for t in open_trades if t.get("tf") == tf]

        if len(mode_trades) >= self._params["max_open_trades"]:
            return
        if signal == "WAIT":
            return
        if confidence < self._params["confidence_threshold"]:
            return
        if entry_type in self._params["entry_type_blacklist"]:
            return

        # ── 重複エントリー防止 ──
        # 直近エントリー価格と近すぎる場合スキップ（ノイズ防止）
        for t in mode_trades:
            if abs(t["entry_price"] - current_price) < 0.03:  # 3pips以内
                return

        # ── SL後クールダウン: 直近のSL/LOSSと同一価格帯・同方向なら再エントリー禁止 ──
        last_ex = self._last_exit.get(mode)
        if last_ex:
            _cooldown_sec = {"scalp": 120, "daytrade": 600, "swing": 7200}.get(mode, 120)
            _ex_age = (datetime.now(timezone.utc) - last_ex["time"]).total_seconds()
            if _ex_age < _cooldown_sec:
                # クールダウン期間中: 同方向 or 同価格帯なら禁止
                if last_ex["direction"] == signal:
                    return  # 同方向は必ずブロック
                if abs(last_ex["price"] - current_price) < 0.05:  # 5pips以内
                    return  # 近接価格もブロック

        # ── 時間帯フィルター（UTC 00,01,21時禁止: 本番損失の94%がここ）──
        try:
            hour_now = datetime.now(timezone.utc).hour
            if hour_now in self._params["session_blacklist"]:
                return
        except Exception:
            pass

        # ── 連敗制御: 同方向N連敗で一時停止 ──
        max_cl = self._params.get("max_consecutive_losses", 3)
        mode_cl = self._consec_losses.get(mode, {})
        if mode_cl.get(signal, 0) >= max_cl:
            return  # 同方向で連敗上限に達した → スキップ

        # ── ema_cross品質フィルター ──
        # 本番データ: ema_cross WR26.7% EV-1.0 → ADX低い時は禁止
        # scalp: ADX<15で禁止（15-20はロンドン/NY時間に必要）
        # daytrade: ADX<15で禁止（15m足はADX低めでも機能する）
        if entry_type == "ema_cross":
            sig_adx = sig.get("indicators", {}).get("adx", 0)
            adx_min = 15  # 旧20→15に緩和（ロンドン/NY帯の取引確保）
            if sig_adx and sig_adx < adx_min:
                return

        layer_status = sig.get("layer_status", {})
        if not layer_status.get("trade_ok", True):
            return

        # ── Layer1（上位足バイアス）方向チェック ──
        # layer1_dir が bull なら SELL 禁止、bear なら BUY 禁止
        _l1 = layer_status.get("layer1", {})
        _l1_dir = _l1.get("direction", "neutral") if isinstance(_l1, dict) else "neutral"
        if _l1_dir == "bull" and signal == "SELL":
            return  # 上位足上昇バイアスにSELL逆行 → スキップ
        if _l1_dir == "bear" and signal == "BUY":
            return  # 上位足下降バイアスにBUY逆行 → スキップ

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
            mode=mode,
        )

        self._add_log(
            f"{cfg['icon']} 📥 IN [{cfg['label']}]: {signal} @ {current_price:.3f} | "
            f"SL {sl:.3f} TP {tp:.3f} | "
            f"Type: {entry_type} | Conf: {confidence}% | "
            f"ID: {trade_id}"
        )

    def _check_signal_reverse(self, trade: dict, current_price: float,
                               new_signal: str, new_conf: int, mode: str):
        """シグナル反転によるクローズ判定のみ（SL/TPは _sltp_loop が処理）"""
        cfg = MODE_CONFIG.get(mode, {})
        direction = trade["direction"]
        trade_id = trade["trade_id"]

        # 最低保持時間チェック（scalp:3分, daytrade:10分, swing:1時間）
        min_hold_sec = {"scalp": 180, "daytrade": 600, "swing": 3600}.get(mode, 180)
        try:
            entry_time = datetime.fromisoformat(trade["entry_time"])
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - entry_time).total_seconds()
            if age < min_hold_sec:
                return  # 最低保持時間未達 → SIGNAL_REVERSE しない
        except Exception:
            pass

        close_reason = None

        # SIGNAL_REVERSE は confidence が閾値より高い場合のみ
        reverse_threshold = max(self._params["confidence_threshold"] + 10, 50)
        if (direction == "BUY" and new_signal == "SELL" and
                new_conf >= reverse_threshold):
            close_reason = "SIGNAL_REVERSE"
        elif (direction == "SELL" and new_signal == "BUY" and
              new_conf >= reverse_threshold):
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

            # ── クールダウン記録 ──
            self._last_exit[mode] = {
                "price": trade["entry_price"],
                "exit_price": current_price,
                "time": datetime.now(timezone.utc),
                "direction": direction,
                "reason": close_reason,
                "outcome": outcome,
            }

            # ── 連敗カウンター更新（SIGNAL_REVERSE分）──
            if mode not in self._consec_losses:
                self._consec_losses[mode] = {}
            if outcome == "WIN":
                self._consec_losses[mode][direction] = 0
            else:
                self._consec_losses[mode][direction] = \
                    self._consec_losses[mode].get(direction, 0) + 1

            self._trade_count_since_learn += 1
            if self._trade_count_since_learn >= self._params["learn_every_n"]:
                self._trigger_learning(current_mode=mode)

    def _trigger_learning(self, current_mode: str = None):
        self._trade_count_since_learn = 0
        # モード別に学習分析を実行
        modes_to_learn = [current_mode] if current_mode else list(MODE_CONFIG.keys())
        for mode in modes_to_learn:
            try:
                cfg = MODE_CONFIG.get(mode, {})
                label = cfg.get("label", mode)
                result = self._engine.evaluate(self._params, mode=mode)
                adjustments = result.get("adjustments", [])
                insights = result.get("insights", [])

                if adjustments:
                    self._apply_adjustments(adjustments)
                    self._add_log(f"🧠 [{label}] 学習完了: {len(adjustments)}件の調整を適用")
                    for ins in insights[:3]:
                        self._add_log(f"   {ins}")
                else:
                    wr = result['data'].get('overall_wr', 0)
                    sample = result['data'].get('sample', 0)
                    self._add_log(f"🧠 [{label}] 学習完了: 調整なし (WR {wr}%, {sample}件)")
            except Exception as e:
                self._add_log(f"⚠️ [{mode}] 学習エラー: {e}")

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
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")
        try:
            self._db.add_log(ts, msg)
        except Exception:
            pass
        print(f"[DemoTrader] {msg}")
