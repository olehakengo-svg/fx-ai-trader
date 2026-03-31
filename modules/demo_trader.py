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


class _NoPriceError(Exception):
    """価格取得不可を示す内部例外"""
    pass


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
            "daily_loss_limit_pips": -30,  # 日次損失上限（pip）
            "max_drawdown_pips": -100,     # 最大DD上限（pip）
        }
        self._trade_count_since_learn = 0
        self._last_signals = {}   # mode -> last signal dict
        # 連敗トラッカー: mode -> {"direction": str, "count": int}
        self._consec_losses = {}  # mode -> {dir -> consecutive_loss_count}
        # SL後クールダウン: mode -> {"price": float, "time": datetime, "direction": str}
        self._last_exit = {}      # mode -> last exit info
        # 起動済みモード追跡（ヘルスチェッカー用）
        self._started_modes = set()
        self._health_thread = None

    # ── Public API ────────────────────────────────────

    def start(self, mode: str = "daytrade"):
        """指定モードのデモトレーダーを起動"""
        if mode not in MODE_CONFIG:
            return {"status": "error", "message": f"Unknown mode: {mode}"}

        with self._lock:
            # 既に起動中ならスキップ（多重起動防止）
            runner = self._runners.get(mode, {})
            if runner.get("running", False):
                return {"status": "already_running", "mode": mode}

            # モードを有効化
            self._runners[mode] = {"running": True, "thread": None}
            self._started_modes.add(mode)

            # メインループスレッドが未起動なら起動
            self._ensure_main_loop()
            # SL/TPチェッカーが未起動なら起動
            self._ensure_sltp_checker()

            cfg = MODE_CONFIG[mode]
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
        # メインループが生きていて、かつモードがrunning=Trueならば動作中
        _loop_alive = self._health_thread and self._health_thread.is_alive()
        if mode:
            return _loop_alive and self._runners.get(mode, {}).get("running", False)
        return _loop_alive and any(r.get("running", False) for r in self._runners.values())

    def get_status(self) -> dict:
        open_trades = self._db.get_open_trades()
        stats = self._db.get_stats()
        modes_status = {}
        for m, cfg in MODE_CONFIG.items():
            runner = self._runners.get(m, {})
            _loop_alive = self._health_thread and self._health_thread.is_alive()
            _actually_running = runner.get("running", False) and _loop_alive
            modes_status[m] = {
                "running": _actually_running,
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

    def _ensure_main_loop(self):
        """メインループスレッドを起動（未起動の場合のみ）"""
        if self._health_thread and self._health_thread.is_alive():
            return
        self._health_thread = threading.Thread(
            target=self._main_loop, daemon=True,
            name="DemoTrader-MainLoop"
        )
        self._health_thread.start()

    def _sltp_loop(self):
        """高頻度でリアルタイム価格を取得してSL/TPチェック"""
        _no_price_count = 0
        while self._sltp_running:
            try:
                self._check_sltp_realtime()
                _no_price_count = 0
            except _NoPriceError:
                _no_price_count += 1
                # 30回連続失敗（15秒間）で警告ログ
                if _no_price_count == 30:
                    self._add_log("⚠️ [SLTP] 価格取得不可が15秒継続 — API障害の可能性")
                if _no_price_count % 120 == 0:  # 60秒ごとに再警告
                    print(f"[SLTP-Checker] No price for {_no_price_count * SLTP_CHECK_INTERVAL:.0f}s")
            except Exception as e:
                print(f"[SLTP-Checker] Error: {e}")
            time.sleep(SLTP_CHECK_INTERVAL)
        print("[SLTP-Checker] Thread terminated cleanly")

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
        """全オープントレードをリアルタイム価格でSL/TPチェック + 最大保持時間 + 週末クローズ"""
        open_trades = self._db.get_open_trades()
        if not open_trades:
            return

        price = self._get_realtime_price()
        if price <= 0:
            raise _NoPriceError("realtime price unavailable")

        # 最大保持時間（秒）: scalp=30分, daytrade=8時間, swing=72時間
        MAX_HOLD_SEC = {"scalp": 1800, "daytrade": 28800, "swing": 259200}

        # 週末クローズ判定（金曜21:45 UTC以降 = 閉場15分前に全ポジクローズ）
        _now_utc = datetime.now(timezone.utc)
        _is_pre_weekend = (_now_utc.weekday() == 4 and _now_utc.hour >= 21 and _now_utc.minute >= 45)

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

            # ── 週末前クローズ（金曜21:45 UTC以降に全ポジ強制クローズ）──
            if not close_reason and _is_pre_weekend:
                close_reason = "WEEKEND_CLOSE"

            # ── 最大保持時間チェック（SL/TPに到達していなくても強制クローズ）──
            if not close_reason:
                try:
                    entry_time = datetime.fromisoformat(trade.get("entry_time", ""))
                    if entry_time.tzinfo is None:
                        entry_time = entry_time.replace(tzinfo=timezone.utc)
                    hold_sec = (datetime.now(timezone.utc) - entry_time).total_seconds()
                    _mode = mode or {"1m": "scalp", "15m": "daytrade", "4h": "swing"}.get(tf, "")
                    max_hold = MAX_HOLD_SEC.get(_mode, 259200)
                    if hold_sec > max_hold:
                        close_reason = "MAX_HOLD_TIME"
                except Exception:
                    pass

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

                # ── クールダウン記録（SL後の即再エントリー防止、WINは除外）──
                if outcome != "WIN":
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

    # ── Main Loop (全モード統合・シングルスレッド) ──────────────────────────

    def _main_loop(self):
        """全モードを1つのスレッドで順次処理（メモリ安全）。
        scalp=10s, daytrade=30s, swing=300s の間隔で各モードをtick。"""
        print("[DemoTrader] MainLoop started")
        _last_tick = {}  # mode -> last tick time
        _consecutive_errors = {}  # mode -> error count
        import gc

        while True:
            # ── B4: 全モード停止ならループ終了 ──
            any_active = any(
                self._runners.get(m, {}).get("running", False)
                for m in self._started_modes
            )
            if not any_active and self._started_modes:
                print("[MainLoop] All modes stopped — exiting loop")
                break
            if not self._started_modes:
                # まだモード未登録の場合は待機
                time.sleep(2)
                continue

            try:
                now = time.time()
                for mode in list(self._started_modes):
                    runner = self._runners.get(mode, {})
                    if not runner.get("running", False):
                        continue

                    cfg = MODE_CONFIG[mode]
                    interval = cfg["interval_sec"]
                    last = _last_tick.get(mode, 0)

                    if now - last < interval:
                        continue  # まだ間隔に達していない

                    # ── このモードのtickを実行 ──
                    try:
                        self._tick(mode)
                        _consecutive_errors[mode] = 0
                        _last_tick[mode] = time.time()
                    except Exception as e:
                        errs = _consecutive_errors.get(mode, 0) + 1
                        _consecutive_errors[mode] = errs
                        try:
                            self._add_log(f"❌ [{cfg['label']}] エラー({errs}): {e}")
                        except Exception:
                            pass
                        print(f"[MainLoop/{mode}] Error #{errs}: {e}")
                        import traceback; traceback.print_exc()
                        _last_tick[mode] = time.time()  # エラー時もインターバルリセット

                    # モード間でメモリ解放
                    gc.collect()
                    time.sleep(1)  # モード間の間隔

            except Exception as e:
                print(f"[MainLoop] Outer error: {e}")
                import traceback; traceback.print_exc()

            time.sleep(2)  # メインループの最小間隔

        print("[MainLoop] Thread terminated cleanly")

    def _check_drawdown(self) -> bool:
        """日次損失・最大DD制限チェック。制限到達ならTrue（トレード禁止）"""
        try:
            stats = self._db.get_stats()
            total_pnl = stats.get("total_pnl", 0)

            # 最大DD制限
            if total_pnl <= self._params["max_drawdown_pips"]:
                return True

            # 日次損失制限
            today_trades = self._db.get_closed_trades(limit=100)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            daily_pnl = sum(
                t.get("pnl_pips", 0) for t in today_trades
                if t.get("exit_time", "").startswith(today)
            )
            if daily_pnl <= self._params["daily_loss_limit_pips"]:
                return True

            return False
        except Exception:
            return False

    @staticmethod
    def _is_fx_market_closed() -> bool:
        """FX市場が閉場中か判定（金曜22:00 UTC 〜 日曜22:00 UTC）"""
        now = datetime.now(timezone.utc)
        wd = now.weekday()  # 0=Mon ... 6=Sun
        h = now.hour
        # 土曜 全日
        if wd == 5:
            return True
        # 日曜 22:00 UTCまで閉場
        if wd == 6 and h < 22:
            return True
        # 金曜 22:00以降閉場
        if wd == 4 and h >= 22:
            return True
        return False

    def _tick(self, mode: str):
        """One cycle for a specific mode — シグナル計算 + 新規エントリー判定のみ。
        SL/TPチェックは _sltp_loop が2秒間隔で独立実行。"""
        cfg = MODE_CONFIG[mode]

        # FX市場閉場中はスキップ（週末ギャップ回避）
        if self._is_fx_market_closed():
            return

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
        print(f"[DemoTrader/{mode}] _tick start: tf={tf}, period={period}")

        # 1. データ取得 + シグナル計算
        try:
            # scalp(1m)はperiod拡大でEMA200を確保
            fetch_period = "5d" if tf == "1m" else period
            df = fetch_ohlcv("USDJPY=X", period=fetch_period, interval=tf)
            print(f"[DemoTrader/{mode}] fetched {len(df)} bars")
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
        mode_trades = [t for t in open_trades
                       if t.get("mode") == mode or (not t.get("mode") and t.get("tf") == tf)]
        for trade in mode_trades:
            self._check_signal_reverse(trade, current_price, signal, confidence, mode)

        # 3. 新規エントリー判定
        # 再取得（SIGNAL_REVERSEでクローズされた可能性）
        open_trades = self._db.get_open_trades()
        mode_trades = [t for t in open_trades
                       if t.get("mode") == mode or (not t.get("mode") and t.get("tf") == tf)]

        # 全モード合計ポジション上限
        if len(open_trades) >= self._params["max_open_trades"]:
            return
        if signal == "WAIT":
            return
        if self._check_drawdown():
            return  # 日次損失 or 最大DD制限到達
        if confidence < self._params["confidence_threshold"]:
            return

        # ── 重複エントリー防止（同価格帯の重複のみブロック）──
        for t in mode_trades:
            if abs(t["entry_price"] - current_price) < 0.03:  # 3pips以内
                return

        # ══════════════════════════════════════════════════════════════
        # ── エントリー理由の品質ゲート ──
        # 「なぜここでエントリーするのか」が明確な場合のみ通す
        # ══════════════════════════════════════════════════════════════
        reasons = sig.get("reasons", [])

        # 明確な技術的根拠を持つエントリータイプ
        QUALIFIED_TYPES = {
            # スキャルプ v2: レジーム選択型
            "bb_rsi_reversion",      # BB+RSI平均回帰（レンジ用）
            "bb_squeeze_breakout",   # BBスクイーズブレイクアウト
            "rsi_divergence_sr",     # RSIダイバージェンス + S/R
            "london_breakout",       # ロンドンブレイクアウト
            "stoch_trend_pullback",  # Stochトレンドプルバック（トレンド用）
            "macdh_reversal",        # MACD-H反転 at BB極端
            "engulfing_bb",          # 包み足 at BB極端
            "three_bar_reversal",    # 3本足反転パターン
            # スキャルプ v1互換
            "tokyo_bb", "sr_bounce", "ob_retest", "bb_bounce",
            "donchian", "reg_channel", "ema_pullback",
            # デイトレ: 構造的なセットアップ
            "dual_sr_bounce",    # 上下SR確認 + バウンス
            "dual_sr_breakout",  # 強いSRブレイクアウト
            "sr_fib_confluence", # SR + フィボナッチ合流
        }

        # 弱い理由のエントリータイプ（追加条件が必要）
        CONDITIONAL_TYPES = {
            "ema_cross",      # EMAクロスだけでは不十分 → 追加確認必要
        }

        # 完全ブロック（理由なしエントリー）
        BLOCKED_TYPES = {
            "unknown",        # 理由不明
            "momentum",       # スコアのみ、具体的根拠なし
            "wait",           # WAITシグナル
        }

        if entry_type in BLOCKED_TYPES:
            return  # 理由不明 → エントリー禁止

        if entry_type in CONDITIONAL_TYPES:
            # ema_cross: ADX≥20 かつ ✅理由が2つ以上ある場合のみ許可
            sig_adx = sig.get("indicators", {}).get("adx", 0)
            confirmed_count = sum(1 for r in reasons if "✅" in r)
            if not sig_adx or sig_adx < 20:
                return  # トレンド弱い → ema_crossは信頼性低い
            if confirmed_count < 2:
                return  # 確認シグナル不足

        if entry_type in QUALIFIED_TYPES:
            # 明確な理由あり → ✅が最低1つあることを確認
            confirmed_count = sum(1 for r in reasons if "✅" in r)
            if confirmed_count < 1:
                return  # テクニカル確認なし

        if entry_type not in QUALIFIED_TYPES and entry_type not in CONDITIONAL_TYPES:
            return  # 未知のタイプ → 安全側でブロック

        if entry_type in self._params["entry_type_blacklist"]:
            return

        # ── SL後クールダウン: 直近のSL/LOSSと同一価格帯・同方向なら再エントリー禁止 ──
        last_ex = self._last_exit.get(mode)
        if last_ex:
            _cooldown_sec = {"scalp": 120, "daytrade": 600, "swing": 7200}.get(mode, 120)
            _ex_age = (datetime.now(timezone.utc) - last_ex["time"]).total_seconds()
            if _ex_age < _cooldown_sec:
                if last_ex["direction"] == signal:
                    return
                if abs(last_ex["price"] - current_price) < 0.05:
                    return

        # ── 時間帯フィルター（UTC 00,01,21時禁止）──
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
            return

        layer_status = sig.get("layer_status", {})
        if not layer_status.get("trade_ok", True):
            return

        # ── Layer1（COT/機関バイアス）方向チェック — スイングのみ ──
        if mode == "swing":
            _l1 = layer_status.get("layer1", {})
            _l1_dir = _l1.get("direction", "neutral") if isinstance(_l1, dict) else "neutral"
            if _l1_dir == "bull" and signal == "SELL":
                return
            if _l1_dir == "bear" and signal == "BUY":
                return

        # ══════════════════════════════════════════════════════════════
        # ── TP固定 / SLエントリーから逆算 ──
        # TPは技術的ターゲット（SR/Fib/BB等）で固定。
        # SLはエントリー価格からRR比で逆算（TPが遠ければSLも余裕あり）。
        # ══════════════════════════════════════════════════════════════
        tp = sig.get("tp", 0)  # シグナル関数が算出した技術的ターゲット（固定）

        tp_dist = abs(tp - current_price)
        # 最小RR比: リスクに対してリワードが十分あることを保証
        MIN_RR = {"scalp": 1.5, "daytrade": 1.8, "swing": 2.0}.get(mode, 1.5)
        # SL = エントリーからTP距離 / RR比
        sl_dist = tp_dist / MIN_RR
        # 最低SL距離保証（スプレッド+ノイズ対策）
        MIN_SL_DIST = {"scalp": 0.030, "daytrade": 0.050, "swing": 0.100}.get(mode, 0.030)
        sl_dist = max(sl_dist, MIN_SL_DIST)

        if signal == "BUY":
            sl = round(current_price - sl_dist, 3)
        else:
            sl = round(current_price + sl_dist, 3)

        # TP距離がSL距離より小さい場合はRR不足 → エントリー見送り
        if tp_dist < sl_dist:
            return

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

        # エントリー理由の要約（✅マーク付きの理由を抽出）
        _confirmed_reasons = [r for r in reasons if "✅" in r]
        _reason_summary = " / ".join(_confirmed_reasons[:3]) if _confirmed_reasons else entry_type

        rr_actual = round(tp_dist / sl_dist, 1) if sl_dist > 0 else 0
        self._add_log(
            f"{cfg['icon']} 📥 IN [{cfg['label']}]: {signal} @ {current_price:.3f} | "
            f"SL {sl:.3f}({sl_dist*100:.1f}p) TP {tp:.3f}({tp_dist*100:.1f}p) RR1:{rr_actual} | "
            f"Type: {entry_type} | Conf: {confidence}% | "
            f"理由: {_reason_summary} | ID: {trade_id}"
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

            # ── クールダウン記録（WINは除外）──
            if outcome != "WIN":
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
