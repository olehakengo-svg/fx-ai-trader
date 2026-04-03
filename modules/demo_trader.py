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
from datetime import datetime, timezone, timedelta

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine
from modules.daily_review import DailyReviewEngine
from modules.oanda_bridge import OandaBridge

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
    # "swing": DISABLED — BT WR=36.7% EV=+0.154 WF=2/3, 本番0トレード
    # 他3モード(scalp/DT/1H)の平均WR=59.4%に対し足を引っ張るため無効化
    # "swing": {
    #     "interval_sec": 300,
    #     "tf": "4h",
    #     "period": "60d",
    #     "signal_fn": "compute_swing_signal",
    #     "label": "スイング",
    #     "icon": "🌊",
    # },
    "daytrade_1h": {
        "interval_sec": 60,       # 1分ごとにチェック（1h足の補完DT）
        "tf": "1h",
        "period": "30d",
        "signal_fn": "compute_1h_zone_signal",
        "label": "デイトレ1H(Zone)",
        "icon": "🕐",
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
        self._oanda = OandaBridge()
        self._lock = threading.Lock()

        # モード別ランナー管理
        self._runners = {}   # mode -> {"running": bool, "thread": Thread}

        # SL/TPチェッカー（全モード共通、高頻度）
        self._sltp_running = False
        self._sltp_thread = None

        # デイリーレビューエンジンを自動起動
        self._daily_review.start()

        # OANDA trade mappings をDBから復元（デプロイ後のリスタート対策）
        try:
            mappings = self._db.get_oanda_mappings()
            self._oanda.restore_mappings(mappings)
        except Exception as e:
            print(f"[OandaBridge] mapping restore skipped: {e}", flush=True)

        # チューナブルパラメータ（学習エンジンが調整、全モード共通）
        self._params = {
            "confidence_threshold": 30,  # デモ: 30%（学習データ蓄積優先、本番は40推奨）
            "max_open_trades": 20,
            "sl_adjust": 1.0,
            "tp_adjust": 1.0,
            "entry_type_blacklist": [],
            # 時間帯フィルター: デモモードでは無効化（学習データ蓄積優先）
            "session_blacklist": [],
            "learn_every_n": 10,
            # 同方向連敗制御: N連敗で同方向エントリーを一時停止
            "max_consecutive_losses": 3,           # 同方向3連敗で一時停止
            "daily_loss_limit_pips": -99999,      # デモ: 制限なし
            "max_drawdown_pips": -99999,           # デモ: 制限なし
        }
        self._trade_count_since_learn = 0
        self._last_signals = {}   # mode -> last signal dict
        # 連敗トラッカー: mode -> {"direction": str, "count": int}
        self._consec_losses = {}  # mode -> {dir -> consecutive_loss_count}
        # SL後クールダウン: mode -> {"price": float, "time": datetime, "direction": str}
        self._last_exit = {}      # mode -> last exit info
        # ── リバウンド対策: 全方向連敗トラッカー + 価格ベロシティ ──
        self._total_losses_window = []  # [(timestamp, mode, pips)] 直近の全損失記録
        self._price_history = []        # [(timestamp, price)] 価格推移記録（ベロシティ計算用）
        self._trade_high_water = {}     # trade_id -> max favorable price（BE/トレーリング用）
        # ── MTF連携: 15m DT → 1m Scalp 戦略バイアス ──
        self._15m_tactical_bias = {
            "direction": None,       # "BUY" | "SELL" | None
            "entry_type": None,      # "hs_neckbreak", "ihs_neckbreak", etc.
            "confidence": 0,
            "updated_at": None,      # datetime
            "signal_price": 0,       # シグナル発生時の価格
            "strength": None,        # "strong" | "trend" | None
        }
        # 起動済みモード追跡（ヘルスチェッカー用）
        self._started_modes = set()
        self._user_stopped_modes = set()  # 明示的にstop()されたモード（ウォッチドッグ対象外）
        self._health_thread = None
        self._watchdog_thread = None
        self._last_request_tick = {}  # mode -> timestamp (リクエスト駆動tick用)

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
            self._user_stopped_modes.discard(mode)

            # メインループスレッドが未起動なら起動
            self._ensure_main_loop()
            # SL/TPチェッカーが未起動なら起動
            self._ensure_sltp_checker()
            # ウォッチドッグスレッド（独立監視）
            self._ensure_watchdog()

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
                    # ウォッチドッグ自動復旧を防止するためユーザー停止セットに記録
                    self._user_stopped_modes.add(m)
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
        # ── Self-healing FIRST: ステータス計算前に死んだスレッドを自動復旧 ──
        _healed = []

        # _started_modesが空でも全モード起動を試みる（デプロイ直後のauto_start未完了対策）
        _target_modes = list(self._started_modes) if self._started_modes else list(MODE_CONFIG.keys())

        # スレッド復旧
        if not (self._health_thread and self._health_thread.is_alive()):
            print("[StatusHeal] MainLoop dead — restarting", flush=True)
            self._ensure_main_loop()
            _healed.append("MainLoop")
        if not (self._watchdog_thread and self._watchdog_thread.is_alive()):
            print("[StatusHeal] Watchdog dead — restarting", flush=True)
            self._ensure_watchdog()
            _healed.append("Watchdog")
        if not (self._sltp_thread and self._sltp_thread.is_alive()):
            print("[StatusHeal] SLTP dead — restarting", flush=True)
            self._ensure_sltp_checker()
            _healed.append("SLTP")

        # モード復旧（_started_modesが空でも全モード起動）
        for m in _target_modes:
            if m in self._user_stopped_modes:
                continue
            runner = self._runners.get(m)
            if runner is None or not runner.get("running", False):
                print(f"[StatusHeal] Mode {m} not running — restarting", flush=True)
                self._runners[m] = {"running": True, "thread": None}
                self._started_modes.add(m)
                _healed.append(m)

        if _healed:
            print(f"[StatusHeal] Healed: {_healed} | started={list(self._started_modes)} "
                  f"user_stopped={list(self._user_stopped_modes)}", flush=True)
            try:
                self._add_log(f"🔄 StatusHeal自動復旧: {', '.join(_healed)}")
            except Exception:
                pass

        # ── ステータス計算（self-healing後の最新状態を反映） ──
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
        try:
            log_count = self._db.get_log_count()
        except Exception:
            log_count = 0

        # MTFバイアス情報
        with self._lock:
            _bias = dict(self._15m_tactical_bias)
        _bias_info = None
        if _bias["direction"] and _bias["updated_at"]:
            _age = (datetime.now(timezone.utc) - _bias["updated_at"]).total_seconds()
            _bias_info = {
                "direction": _bias["direction"],
                "entry_type": _bias["entry_type"],
                "strength": _bias.get("strength", ""),
                "age_sec": int(_age),
                "active": _age < 3600,
            }

        return {
            "running": self.is_running(),
            "modes": modes_status,
            "params": self._params.copy(),
            "open_trades": open_trades,
            "stats": stats,
            "log_count": log_count,
            "trades_since_learn": self._trade_count_since_learn,
            "daily_review_active": self._daily_review.is_running(),
            "sltp_checker_active": bool(self._sltp_thread and self._sltp_thread.is_alive()),
            "mtf_bias": _bias_info,
            "main_loop_alive": bool(self._health_thread and self._health_thread.is_alive()),
            "main_loop_status": getattr(self, '_main_loop_status', 'unknown'),
            "main_loop_error": getattr(self, '_main_loop_error', None),
            "watchdog_alive": bool(self._watchdog_thread and self._watchdog_thread.is_alive()),
            "tick_counts": getattr(self, '_tick_counts', None),
            "main_loop_restarts": getattr(self, '_main_loop_restart_count', 0),
            "_started_modes": list(self._started_modes),
            "_user_stopped_modes": list(self._user_stopped_modes),
            "block_counts": getattr(self, '_block_counts', {}),
            "oanda": self._oanda.status,
        }

    def request_tick(self):
        """リクエスト駆動tick: バックグラウンドスレッドが死んでいる場合のフォールバック。
        APIリクエスト時に呼ばれ、各モードのtickを実行する。
        スレッドが生きている場合はスキップ（二重実行防止）。"""
        if self._health_thread and self._health_thread.is_alive():
            return  # メインループが生きていれば不要
        # _started_modesが空なら全モードをターゲット
        if not self._started_modes:
            for m in MODE_CONFIG.keys():
                if m not in self._user_stopped_modes:
                    self._started_modes.add(m)
                    self._runners[m] = {"running": True, "thread": None}
            print(f"[RequestTick] Force-started all modes: {list(self._started_modes)}", flush=True)
        now = time.time()
        ticked = []
        for mode in list(self._started_modes):
            if mode in self._user_stopped_modes:
                continue
            runner = self._runners.get(mode, {})
            if not runner.get("running", False):
                continue
            cfg = MODE_CONFIG[mode]
            interval = cfg["interval_sec"]
            last = self._last_request_tick.get(mode, 0)
            if now - last < interval:
                continue
            try:
                self._tick(mode)
                self._last_request_tick[mode] = time.time()
                _tc = getattr(self, '_tick_counts', {})
                _tc[mode] = _tc.get(mode, 0) + 1
                self._tick_counts = _tc
                ticked.append(mode)
            except Exception as e:
                print(f"[RequestTick/{mode}] Error: {e}", flush=True)
                self._last_request_tick[mode] = time.time()
        if ticked:
            print(f"[RequestTick] Executed: {ticked}", flush=True)

        # SL/TPチェックも実行（SLTPスレッドが死んでいる場合）
        if not (self._sltp_thread and self._sltp_thread.is_alive()):
            try:
                self._check_sltp_realtime()
            except Exception:
                pass

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
        """SL/TPリアルタイムチェッカーを起動（未起動またはスレッド死亡時に再起動）"""
        if self._sltp_thread and self._sltp_thread.is_alive():
            return  # スレッドが生きていれば何もしない
        self._sltp_running = True
        self._sltp_thread = threading.Thread(
            target=self._sltp_loop, daemon=True,
            name="DemoTrader-SLTP-Checker"
        )
        self._sltp_thread.start()
        print(f"[EnsureSLTP] Thread started: {self._sltp_thread.is_alive()}", flush=True)

    def _ensure_main_loop(self):
        """メインループスレッドを起動（未起動の場合のみ）"""
        if self._health_thread and self._health_thread.is_alive():
            return
        try:
            self._health_thread = threading.Thread(
                target=self._main_loop, daemon=True,
                name="DemoTrader-MainLoop"
            )
            self._health_thread.start()
            print(f"[EnsureMainLoop] Thread started: {self._health_thread.is_alive()}", flush=True)
        except Exception as e:
            print(f"[EnsureMainLoop] FAILED to start thread: {e}", flush=True)
            import traceback; traceback.print_exc()

    def _ensure_watchdog(self):
        """独立ウォッチドッグスレッドを起動（メインループとは別スレッド）"""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True,
            name="DemoTrader-Watchdog"
        )
        self._watchdog_thread.start()

    def _watchdog_loop(self):
        """独立ウォッチドッグ: 30秒毎にモード生存確認・自動復旧"""
        print("[Watchdog] Independent watchdog thread started", flush=True)
        time.sleep(30)  # 初回は30秒待機（auto_start完了を待つ）
        _check_count = 0
        _restart_count = 0  # 自身のリスタート回数
        while True:
            try:
                _check_count += 1
                restored = []

                # 全4モードを強制チェック（_started_modesに依存しない）
                _all_modes = ["scalp", "daytrade", "daytrade_1h", "swing"]
                for m in _all_modes:
                    if m in self._user_stopped_modes:
                        continue  # ユーザーが明示的に停止したモードはスキップ
                    if m not in self._started_modes:
                        continue  # 一度もstart()されていないモードはスキップ
                    runner = self._runners.get(m)
                    if runner is None or not runner.get("running", False):
                        print(f"[Watchdog] {m} found stopped — auto-restarting", flush=True)
                        self._runners[m] = {"running": True, "thread": None}
                        restored.append(m)

                # メインループスレッドが死んでいたら再起動
                if self._started_modes and not (self._health_thread and self._health_thread.is_alive()):
                    print("[Watchdog] MainLoop thread dead — restarting", flush=True)
                    self._ensure_main_loop()
                    restored.append("MainLoop")

                # SL/TPチェッカーが死んでいたら再起動
                if self._started_modes and not (self._sltp_thread and self._sltp_thread.is_alive()):
                    print("[Watchdog] SLTP thread dead — restarting", flush=True)
                    self._ensure_sltp_checker()
                    restored.append("SLTP")

                if restored:
                    try:
                        labels = [MODE_CONFIG.get(m, {}).get('label', m) for m in restored]
                        self._add_log(f"🔄 ウォッチドッグ自動復旧: {', '.join(labels)}")
                    except Exception:
                        pass

                # 10回毎（5分毎）にヘルスビート出力
                if _check_count % 10 == 0:
                    _running = [m for m in _all_modes
                                if self._runners.get(m, {}).get("running", False)]
                    _stopped = [m for m in _all_modes
                                if m in self._started_modes and not self._runners.get(m, {}).get("running", False)]
                    _ml = "alive" if (self._health_thread and self._health_thread.is_alive()) else "DEAD"
                    _tc = getattr(self, '_tick_counts', {})
                    print(f"[Watchdog/HB] #{_check_count} running={_running} stopped={_stopped} "
                          f"started={list(self._started_modes)} user_stopped={list(self._user_stopped_modes)} "
                          f"mainloop={_ml} ticks={_tc} restarts={_restart_count}", flush=True)
            except BaseException as e:
                # SystemExit, KeyboardInterruptも含め全例外をcatch（スレッド死亡防止）
                _restart_count += 1
                print(f"[Watchdog] BaseException caught (restart #{_restart_count}): "
                      f"{type(e).__name__}: {e}", flush=True)
                import traceback; traceback.print_exc()
                # SystemExitの場合でも30秒待って再試行（スレッドを殺さない）
                time.sleep(30)
                continue

            time.sleep(30)  # 30秒間隔でチェック

    def _sltp_loop(self):
        """高頻度でリアルタイム価格を取得してSL/TPチェック"""
        print("[SLTP-Checker] Thread started", flush=True)
        _no_price_count = 0
        try:
            while self._sltp_running:
                try:
                    self._check_sltp_realtime()
                    _no_price_count = 0
                except _NoPriceError:
                    _no_price_count += 1
                    if _no_price_count == 30:
                        self._add_log("⚠️ [SLTP] 価格取得不可が15秒継続 — API障害の可能性")
                    if _no_price_count % 120 == 0:
                        print(f"[SLTP-Checker] No price for {_no_price_count * SLTP_CHECK_INTERVAL:.0f}s", flush=True)
                except Exception as e:
                    print(f"[SLTP-Checker] Error: {e}", flush=True)
                time.sleep(SLTP_CHECK_INTERVAL)
            print("[SLTP-Checker] Thread terminated cleanly (sltp_running=False)", flush=True)
        except BaseException as e:
            print(f"[SLTP-Checker] BaseException: {type(e).__name__}: {e}", flush=True)
            import traceback; traceback.print_exc()

    def _get_realtime_price(self) -> float:
        """
        リアルタイム価格を最速で取得:
        1. _price_cache（TwelveData/yfinance）が10秒以内なら使用
        2. OANDA v20 pricing API
        3. フォールバック: 1m足の最新Close
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

        # OANDA v20 リアルタイム価格
        try:
            from modules.data import fetch_oanda_price
            p = fetch_oanda_price()
            if p > 0:
                return p
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

        # 最大保持時間（秒）: scalp=30分, daytrade=8時間, daytrade_1h=18時間, swing=72時間
        MAX_HOLD_SEC = {"scalp": 1800, "daytrade": 28800, "daytrade_1h": 64800, "swing": 259200}

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
            entry_price = trade["entry_price"]

            # ══════════════════════════════════════════════════════════════
            # ── ブレイクイーブン + 連続トレーリングストップ ──
            # 50% TP到達 → SLをエントリー価格に移動（BE）
            # BE後 → SLをTP距離の30%幅でトレーリング（≒0.8-0.9 ATR）
            # BT 1H Zone: +26→+45 pip/day の主因
            # ══════════════════════════════════════════════════════════════
            tp_dist = abs(tp - entry_price)
            if direction == "BUY":
                favorable_move = price - entry_price
            else:
                favorable_move = entry_price - price

            _original_sl = sl  # OANDA SL変更検出用
            if favorable_move > 0 and tp_dist > 0:
                progress = favorable_move / tp_dist  # 0.0 ~ 1.0+

                if progress >= 0.50:
                    # 50%到達: BE + トレーリング開始
                    _trail_dist = tp_dist * 0.30  # TP距離の30% ≒ 0.8-0.9 ATR
                    if direction == "BUY":
                        # まずBE
                        new_sl = max(entry_price, price - _trail_dist)
                        new_sl = round(new_sl, 3)
                        if new_sl > sl:
                            sl = new_sl
                    else:
                        new_sl = min(entry_price, price + _trail_dist)
                        new_sl = round(new_sl, 3)
                        if new_sl < sl:
                            sl = new_sl

            # ── OANDA連携: トレーリングSL変更をミラー ──
            if sl != _original_sl:
                self._oanda.modify_sl(trade_id, sl)

            close_reason = None

            # ── シナリオ崩壊撤退（1H Zone用）──
            # エントリー時のシナリオ根拠が崩れたら即撤退（SL到達前に損切り）
            _inv = None
            _trade_reasons = trade.get("reasons", [])
            if isinstance(_trade_reasons, str):
                import json as _json
                try:
                    _trade_reasons = _json.loads(_trade_reasons)
                except Exception:
                    _trade_reasons = []
            for _r in _trade_reasons:
                if isinstance(_r, str) and _r.startswith("__INV__:"):
                    try:
                        _inv = float(_r.split(":")[1])
                    except Exception:
                        pass
                    break
            if _inv is not None and not close_reason:
                if direction == "BUY" and price < _inv:
                    close_reason = "SCENARIO_INVALID"
                elif direction == "SELL" and price > _inv:
                    close_reason = "SCENARIO_INVALID"

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
                if "error" in result:
                    continue  # 別スレッドで既にクローズ済み → スキップ

                # ── OANDA連携: ポジションクローズ ──
                self._oanda.close_trade(trade_id, reason=close_reason)

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
                    # ── 全方向連敗ウィンドウに記録 ──
                    self._total_losses_window.append(
                        (datetime.now(timezone.utc), mode, pnl))
                    # 古い記録を削除（最大4時間保持）
                    _cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
                    self._total_losses_window = [
                        t for t in self._total_losses_window if t[0] > _cutoff]

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
        import sys
        # ステータスを即座に設定（"unknown"状態を最小化）
        self._main_loop_status = "starting"
        self._main_loop_error = None
        print("[DemoTrader] MainLoop started", flush=True)
        sys.stdout.flush()
        _last_tick = {}
        _consecutive_errors = {}
        _restart_count = getattr(self, '_main_loop_restart_count', 0)
        self._main_loop_restart_count = _restart_count + 1

        self._main_loop_status = "running"
        _loop_iter = 0

        try:
            while True:
                if not self._started_modes:
                    time.sleep(2)
                    continue

                try:
                    now = time.time()
                    _loop_iter += 1
                    if _loop_iter <= 5 or _loop_iter % 30 == 0:
                        _modes_list = list(self._started_modes)
                        _running_modes = [m for m in _modes_list if self._runners.get(m, {}).get("running", False)]
                        _tc = getattr(self, '_tick_counts', {})
                        print(f"[MainLoop] iter={_loop_iter} started={_modes_list} "
                              f"running={_running_modes} ticks={_tc} restart#{_restart_count}", flush=True)
                    for mode in list(self._started_modes):
                        runner = self._runners.get(mode, {})
                        if not runner.get("running", False):
                            continue

                        cfg = MODE_CONFIG[mode]
                        interval = cfg["interval_sec"]
                        last = _last_tick.get(mode, 0)

                        if now - last < interval:
                            continue

                        # ── このモードのtickを実行 ──
                        try:
                            _tick_start = time.time()
                            self._tick(mode)
                            _tick_dur = time.time() - _tick_start
                            _consecutive_errors[mode] = 0
                            _last_tick[mode] = time.time()
                            _tick_count = getattr(self, '_tick_counts', {})
                            _tick_count[mode] = _tick_count.get(mode, 0) + 1
                            self._tick_counts = _tick_count
                            if _tick_count[mode] <= 3 or _tick_count[mode] % 10 == 0 or _tick_dur > 30:
                                print(f"[MainLoop/{mode}] tick #{_tick_count[mode]} ok ({_tick_dur:.1f}s)", flush=True)
                        except Exception as e:
                            errs = _consecutive_errors.get(mode, 0) + 1
                            _consecutive_errors[mode] = errs
                            try:
                                self._add_log(f"❌ [{cfg['label']}] エラー({errs}): {e}")
                            except Exception:
                                pass
                            print(f"[MainLoop/{mode}] Error #{errs}: {e}", flush=True)
                            import traceback; traceback.print_exc()
                            _last_tick[mode] = time.time()

                            # 10回連続エラーでバックオフ（API制限等）
                            if errs >= 10:
                                print(f"[MainLoop/{mode}] Too many errors, backing off 60s", flush=True)
                                time.sleep(60)

                        time.sleep(1)

                except Exception as e:
                    print(f"[MainLoop] Outer error: {e}", flush=True)
                    import traceback; traceback.print_exc()

                time.sleep(2)

        except BaseException as fatal:
            # SystemExit, KeyboardInterrupt等も含む全致命的エラーをキャッチ
            self._main_loop_status = "DEAD"
            self._main_loop_error = f"{type(fatal).__name__}: {fatal}"
            print(f"[MainLoop] FATAL: {type(fatal).__name__}: {fatal}", flush=True)
            import traceback; traceback.print_exc()
            try:
                self._add_log(f"💀 メインループ致命的エラー: {type(fatal).__name__}: {fatal}")
            except Exception:
                pass
            # 自動リスタート（30秒待ってから）
            print("[MainLoop] Will auto-restart in 30s...", flush=True)
            time.sleep(30)
            try:
                self._ensure_main_loop()
            except Exception:
                pass

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
        elif mode == "daytrade_1h":
            from app import compute_1h_zone_signal as compute_fn
        else:
            from app import compute_scalp_signal as compute_fn

        tf = cfg["tf"]
        period = cfg["period"]
        print(f"[DemoTrader/{mode}] _tick start: tf={tf}, period={period}", flush=True)

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
                print(f"[DemoTrader/{mode}] Insufficient data: {len(df)} bars (need 50)")
                return

            sr = find_sr_levels(df)

            # ── 1H Zone mode: ゾーン計算 + 専用シグナル呼び出し ──
            if mode == "daytrade_1h":
                import numpy as _np
                # 前日のOHLCからゾーン計算
                _1h_dates = {}
                for idx in df.index:
                    _d = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
                    if _d not in _1h_dates:
                        _1h_dates[_d] = {"H": float(df.loc[idx, "High"]),
                                         "L": float(df.loc[idx, "Low"]),
                                         "C": float(df.loc[idx, "Close"]),
                                         "atr": float(df.loc[idx].get("atr", 0.10))}
                    else:
                        _1h_dates[_d]["H"] = max(_1h_dates[_d]["H"], float(df.loc[idx, "High"]))
                        _1h_dates[_d]["L"] = min(_1h_dates[_d]["L"], float(df.loc[idx, "Low"]))
                        _1h_dates[_d]["C"] = float(df.loc[idx, "Close"])
                        _1h_dates[_d]["atr"] = float(df.loc[idx].get("atr", 0.10))

                _sorted_dates = sorted(_1h_dates.keys())
                if len(_sorted_dates) >= 2:
                    _prev_day = _1h_dates[_sorted_dates[-2]]
                    _pivot = (_prev_day["H"] + _prev_day["L"] + _prev_day["C"]) / 3.0
                    _daily_atr = _prev_day["atr"] * _np.sqrt(24)
                    _buy_zone = (_prev_day["L"] - _daily_atr * 0.2, _pivot)
                    _sell_zone = (_pivot, _prev_day["H"] + _daily_atr * 0.2)
                    sig = compute_fn(df, buy_zone=_buy_zone, sell_zone=_sell_zone,
                                     sr_levels=sr, backtest_mode=False)
                else:
                    return  # ゾーン計算不可（データ不足）
            else:
                sig = compute_fn(df, tf, sr, "USDJPY=X")

            # ── 5m補完: sr_channel_reversal / macdh_reversal は5mの方が高EV ──
            # 1m: WR=48.5%/-0.162, WR=46.7%/-0.023
            # 5m: WR=63.6%/+0.318, WR=78.4%/+0.722
            _5M_ONLY_STRATEGIES = {"macdh_reversal", "fib_reversal"}  # sr_channel_reversal除外(7d BTで赤字)
            if mode == "scalp" and sig.get("signal") == "WAIT":
                try:
                    df_5m = fetch_ohlcv("USDJPY=X", period="5d", interval="5m")
                    df_5m = add_indicators(df_5m)
                    _5m_cols = [c for c in ["close", "ema9", "ema21", "rsi", "adx", "atr"]
                                if c in {x.lower() for x in df_5m.columns}]
                    _5m_actual = [c for c in df_5m.columns if c.lower() in _5m_cols]
                    if _5m_actual:
                        df_5m = df_5m.dropna(subset=_5m_actual)
                    if len(df_5m) >= 50:
                        sr_5m = find_sr_levels(df_5m)
                        sig_5m = compute_fn(df_5m, "5m", sr_5m, "USDJPY=X")
                        if (sig_5m.get("signal") != "WAIT"
                                and sig_5m.get("entry_type") in _5M_ONLY_STRATEGIES):
                            sig = sig_5m
                            sig["_tf_override"] = "5m"
                            print(f"[DemoTrader/scalp] 5m補完: {sig_5m.get('entry_type')} {sig_5m.get('signal')}")
                except Exception as _e5:
                    print(f"[DemoTrader/scalp] 5m補完エラー: {_e5}")
        except Exception as e:
            self._add_log(f"⚠️ [{cfg['label']}] シグナル取得失敗: {e}")
            import traceback; traceback.print_exc()
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

        # ══════════════════════════════════════════════════════════════
        # ── MTF連携: 15m DT シグナル → 1m Scalp バイアス更新 ──
        # DT/DT1hの構造的パターン（三尊/逆三尊/SR等）を記録し、
        # スキャルプが順方向エントリーを強化 / 逆方向を抑制する
        # ══════════════════════════════════════════════════════════════
        if mode in ("daytrade", "daytrade_1h") and signal != "WAIT":
            _dt_etype = sig.get("entry_type", "")
            # 構造的パターン（強いバイアス）とトレンドシグナル（軽いバイアス）
            _strong_patterns = {"hs_neckbreak", "ihs_neckbreak", "dual_sr_bounce",
                                "dual_sr_breakout", "sr_fib_confluence"}
            _trend_patterns = {"ema_cross", "mtf_momentum", "pivot_breakout", "h1_breakout_retest"}
            if _dt_etype in _strong_patterns or _dt_etype in _trend_patterns:
                _bias_strength = "strong" if _dt_etype in _strong_patterns else "trend"
                with self._lock:
                    self._15m_tactical_bias = {
                        "direction": signal,
                        "entry_type": _dt_etype,
                        "confidence": sig.get("confidence", 0),
                        "updated_at": datetime.now(timezone.utc),
                        "signal_price": current_price,
                        "strength": _bias_strength,
                    }

        # ── 価格ヒストリー記録（ベロシティ計算用）──
        _now_rec = datetime.now(timezone.utc)
        self._price_history.append((_now_rec, current_price))
        # 古いデータを削除（最大4時間保持）
        _cutoff = _now_rec - timedelta(hours=4)
        self._price_history = [(t, p) for t, p in self._price_history if t > _cutoff]
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

        # ── エントリーフィルター（ブロック理由カウント付き） ──
        if not hasattr(self, '_block_counts'):
            self._block_counts = {}
        def _block(reason):
            k = f"{mode}:{reason}"
            self._block_counts[k] = self._block_counts.get(k, 0) + 1
            return

        # 全モード合計ポジション上限
        if len(open_trades) >= self._params["max_open_trades"]:
            _block("max_open"); return
        if signal == "WAIT":
            return  # WAITはカウントしない（大半がWAIT）
        if self._check_drawdown():
            _block("drawdown"); return
        if confidence < self._params["confidence_threshold"]:
            _block(f"conf<{self._params['confidence_threshold']}(was:{confidence})"); return

        # ── 重複エントリー防止 ──
        # (A) 同価格帯ブロック（モード別: scalp=1.0pip, DT=5pip, other=3pip）
        # scalp: 1.5→1.0pip (エントリー機会増), DT: 1.5→5pip (マシンガン防止)
        _same_price_dist = {"scalp": 0.010, "daytrade": 0.050}.get(mode, 0.03)
        for t in mode_trades:
            if abs(t["entry_price"] - current_price) < _same_price_dist:
                _block(f"same_price_{_same_price_dist*100:.0f}pip"); return
        # (B) 同方向ポジション上限（モード別）
        # scalp: 2→3 (好調なので増), DT: 5→2 (マシンガン防止)
        _dir_limits = {"scalp": 3, "daytrade": 3, "daytrade_1h": 2, "swing": 2}  # DT: 2→3(HTFフィルター済み)
        _max_same_dir = _dir_limits.get(mode, 2)
        _same_dir_count = sum(1 for t in mode_trades if t.get("direction") == signal)
        if _same_dir_count >= _max_same_dir:
            _block("same_dir_limit"); return

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
            "macdh_reversal",        # 5m補完経由のみ（1m赤字→5m WR=78.4% EV=+0.722）
            # "engulfing_bb",        # DISABLED: EV=+0.042 @0.8pip spread → 薄利すぎ
            # "three_bar_reversal",  # DISABLED: 1m BT WR=33.3% EV=-1.042
            "trend_rebound",         # 強トレンド時リバウンド
            "v_reversal",            # V字リバウンドキャプチャ（急落/急騰後の反転）
            # "hs_neckbreak",        # DISABLED: EV=-0.346 @0.8pip spread → マイナス
            "ihs_neckbreak",         # 逆三尊ネックライン突破
            "sr_touch_bounce",       # 水平線タッチ反発
            # スキャルプ v1互換
            "tokyo_bb", "sr_bounce", "ob_retest", "bb_bounce",
            "donchian", "reg_channel", "ema_pullback",
            # スキャルプ v2.3: リバーサル戦略
            # "sr_channel_reversal",     # DISABLED: 1m/7d BT WR=48.8% EV=-0.204
            "fib_reversal",              # フィボナッチリトレースメント反発 (1m+5m補完)

            "mtf_reversal_confluence",   # MTF RSI+MACD一致
            # デイトレ: 構造的なセットアップ
            # "dual_sr_bounce",  # DISABLED: 不調日WR=12-43%, BT EV=-0.072
            "dual_sr_breakout",  # 強いSRブレイクアウト
            "sr_fib_confluence", # SR + フィボナッチ合流
            "ema_cross",         # EMAクロス (BT 147t WR=72.8%)
            "dt_fib_reversal",           # DT フィボリバーサル
            # "dt_sr_channel_reversal",  # DISABLED: BT WR=25% EV=-0.659
            # "ema200_trend_reversal",   # DISABLED: BT WR=50% EV=-0.037
            # 1H Zone v4: SR強度ベース戦略
            # "h1_sr_reversal",      # DISABLED: WR=25% EV=-0.718
            "h1_breakout_retest",    # 強壁ブレイク後リテスト → トレンドフォロー
            # 旧戦略（互換維持）
            "h1_fib_reversal",           # 1H フィボリバーサル
            "h1_ema200_trend_reversal",  # 1H EMA200トレンド転換
        }

        # 弱い理由のエントリータイプ（追加条件が必要）
        # ema_cross: BT 147t WR=72.8% → QUALIFIED に昇格（ADX+EMA整合はapp.py側で制御済み）
        CONDITIONAL_TYPES = set()

        # 完全ブロック（理由なしエントリー）
        BLOCKED_TYPES = {
            "unknown",        # 理由不明
            "momentum",       # スコアのみ、具体的根拠なし
            "wait",           # WAITシグナル
        }

        if entry_type in BLOCKED_TYPES:
            _block(f"blocked_type:{entry_type}"); return

        if entry_type in CONDITIONAL_TYPES:
            sig_adx = sig.get("indicators", {}).get("adx", 0)
            confirmed_count = sum(1 for r in reasons if "✅" in r)
            if not sig_adx or sig_adx < 20:
                _block(f"cond_adx<20:{entry_type}"); return
            if confirmed_count < 2:
                _block(f"cond_reasons<2:{entry_type}"); return

        if entry_type in QUALIFIED_TYPES:
            confirmed_count = sum(1 for r in reasons if "✅" in r)
            if confirmed_count < 1:
                _block(f"no_confirm:{entry_type}"); return

        if entry_type not in QUALIFIED_TYPES and entry_type not in CONDITIONAL_TYPES:
            _block(f"unknown_type:{entry_type}"); return

        if entry_type in self._params["entry_type_blacklist"]:
            _block(f"blacklisted:{entry_type}"); return

        # ── SL後クールダウン ──
        last_ex = self._last_exit.get(mode)
        if last_ex:
            _cooldown_sec = {"scalp": 60, "daytrade": 300, "daytrade_1h": 1800, "swing": 7200}.get(mode, 120)  # DT: 600→300s(HTFフィルター済みで頻度増)
            _ex_age = (datetime.now(timezone.utc) - last_ex["time"]).total_seconds()
            if _ex_age < _cooldown_sec:
                if last_ex["direction"] == signal:
                    _block(f"cooldown_same_dir({int(_ex_age)}s)"); return
                if abs(last_ex["price"] - current_price) < 0.05:
                    _block(f"cooldown_same_zone({int(_ex_age)}s)"); return
            # LOSS後の同価格帯再エントリー防止（DT: 同価格帯で10pip以内 + 30分間）
            if last_ex.get("outcome") == "LOSS" and mode == "daytrade":
                _loss_cooldown = 1800  # 30分
                if _ex_age < _loss_cooldown and abs(last_ex["price"] - current_price) < 0.10:
                    _block(f"loss_zone_cooldown({int(_ex_age)}s)"); return

        # ── 時間帯×モード別フィルター ──
        # アジア(00-07): レンジ → DT禁止（スキャルプのみ）
        # ロンドン(07-12): トレンド → 全モードOK
        # NY重複(12-16): 高ボラ+反転 → DT bounce系注意（ADXで制御済み）
        # NY後半(16-21): ボラ低下 → スキャルプ中心
        # クローズ(21-00): スプレッド拡大 → 全モード非推奨
        try:
            hour_now = datetime.now(timezone.utc).hour
            # モード別時間帯制限
            if mode == "daytrade":
                if hour_now < 5 or hour_now >= 22:  # UTC5-22: 頻度維持（フィルターはHTF側で制御）
                    _block(f"session_block(h={hour_now})"); return
            elif mode == "daytrade_1h":
                if hour_now < 3 or hour_now >= 22:
                    _block(f"session_block(h={hour_now})"); return
            # scalp/swingは時間帯制限なし（デモモード: データ蓄積優先）
        except Exception:
            pass

        # ── 連敗制御: 同方向N連敗で一時停止 ──
        max_cl = self._params.get("max_consecutive_losses", 3)
        mode_cl = self._consec_losses.get(mode, {})
        if mode_cl.get(signal, 0) >= max_cl:
            _block(f"consec_loss({mode_cl.get(signal,0)})"); return

        # ── 全方向サーキットブレーカー: 30分以内にN回負けでモード一時停止 ──
        # 本番実績: DT 12連敗(-101pip)を防止するための安全装置
        _cb_limits = {"scalp": 4, "daytrade": 3, "daytrade_1h": 2, "swing": 2}
        _cb_max = _cb_limits.get(mode, 3)
        _cb_window = timedelta(minutes=30)
        _cb_cutoff = datetime.now(timezone.utc) - _cb_window
        _cb_recent = [t for t in self._total_losses_window
                      if t[0] > _cb_cutoff and t[1] == mode]
        if len(_cb_recent) >= _cb_max:
            _cb_total_loss = sum(t[2] for t in _cb_recent)
            _block(f"circuit_breaker({len(_cb_recent)}losses/{_cb_max}max_in_30min, total={_cb_total_loss:+.1f}pip)")
            return

        # ══════════════════════════════════════════════════════════════
        # ── ベロシティフィルター ──
        # 本番で急騰中のSELL連敗(-36pip)の原因 → 急動時の逆行エントリーをブロック
        # ══════════════════════════════════════════════════════════════
        _now_vel = datetime.now(timezone.utc)
        _vel_window_min = {"scalp": 10, "daytrade": 30, "daytrade_1h": 60}.get(mode, 10)
        _vel_threshold_pip = {"scalp": 15.0, "daytrade": 15.0, "daytrade_1h": 20.0}.get(mode, 8.0)  # scalp: 8→15pip（調整局面のカウンタートレード許可）
        _vel_cutoff = _now_vel - timedelta(minutes=_vel_window_min)
        _recent_prices = [(t, p) for t, p in self._price_history if t > _vel_cutoff]
        if len(_recent_prices) >= 2:
            _oldest_price = _recent_prices[0][1]
            _price_move = current_price - _oldest_price
            _move_pips = abs(_price_move) * 100
            if _move_pips >= _vel_threshold_pip:
                if _price_move > 0 and signal == "SELL":
                    _block(f"velocity_up({_move_pips:.0f}pip)_vs_SELL"); return
                if _price_move < 0 and signal == "BUY":
                    _block(f"velocity_down({_move_pips:.0f}pip)_vs_BUY"); return

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
        # ── MTF連携: 15m DT バイアス ──
        # v6: スキャルプは方向不問（1m足=短期の波を両方向で取る）
        #     15mバイアスでスキャルプを制御するのは時間軸が粗すぎる
        #     → スキャルプのMTFバイアスを無効化
        #     DT/1H: 引き続き有効（同じ時間軸レベルの制御）
        # ══════════════════════════════════════════════════════════════
        _mtf_tp_bonus = 1.0
        # スキャルプはMTFバイアス不要（両方向で調整局面も取る）
        # DT/1H/swingのみMTFバイアス適用
        if mode != "scalp":
            with self._lock:
                _bias_snapshot = dict(self._15m_tactical_bias)
            if _bias_snapshot.get("direction"):
                _bias = _bias_snapshot
                _bias_age = (datetime.now(timezone.utc) - _bias["updated_at"]).total_seconds() if _bias["updated_at"] else 99999
                _bias_valid = _bias_age < 3600

                if _bias_valid:
                    _bias_dir = _bias["direction"]
                    _bias_strength = _bias.get("strength", "trend")

                    if _bias_strength == "strong":
                        if signal != _bias_dir:
                            if entry_type != "trend_rebound":
                                return
                        else:
                            _mtf_tp_bonus = 1.3

                    elif _bias_strength == "trend":
                        if signal != _bias_dir:
                            confidence = int(confidence * 0.8)
                            if confidence < self._params["confidence_threshold"]:
                                return

        # ══════════════════════════════════════════════════════════════
        # ── TP固定 / SLエントリーから逆算 ──
        # TPは技術的ターゲット（SR/Fib/BB等）で固定。
        # SLはエントリー価格からRR比で逆算（TPが遠ければSLも余裕あり）。
        # ══════════════════════════════════════════════════════════════
        tp = sig.get("tp", 0)  # シグナル関数が算出した技術的ターゲット（固定）

        tp_dist = abs(tp - current_price) * _mtf_tp_bonus  # MTF順方向時にTP拡大
        if tp_dist <= 0:
            return  # TPが無効（0または現在価格と同一）→ エントリー見送り
        if _mtf_tp_bonus > 1.0:
            # TP価格を再計算
            if signal == "BUY":
                tp = current_price + tp_dist
            else:
                tp = current_price - tp_dist
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

        # シナリオ崩壊撤退レベル（1H Zoneシグナルに付随）
        _invalidation = sig.get("invalidation")
        _reasons_with_inv = sig.get("reasons", [])
        if _invalidation is not None:
            _reasons_with_inv = list(_reasons_with_inv) + [f"__INV__:{_invalidation:.3f}"]

        trade_id = self._db.open_trade(
            direction=signal,
            entry_price=current_price,
            sl=sl, tp=tp,
            entry_type=entry_type,
            confidence=confidence,
            tf=tf,
            reasons=_reasons_with_inv,
            regime=regime,
            layer1_dir=layer1_dir,
            score=sig.get("score", 0),
            ema_conf=ema_conf,
            sr_basis=sr_basis,
            mode=mode,
        )

        # ── OANDA連携: デモトレードをミラーリング ──
        self._oanda.open_trade(
            demo_trade_id=trade_id,
            direction=signal,
            sl=sl, tp=tp,
            mode=mode,
            callback=lambda did, oid: self._db.set_oanda_trade_id(did, oid),
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
        min_hold_sec = {"scalp": 180, "daytrade": 600, "daytrade_1h": 1800, "swing": 3600}.get(mode, 180)
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
            if "error" in result:
                return  # 別スレッドで既にクローズ済み → スキップ

            # ── OANDA連携: ポジションクローズ ──
            self._oanda.close_trade(trade_id, reason=close_reason)

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
                # ── 全方向連敗ウィンドウに記録 ──
                self._total_losses_window.append(
                    (datetime.now(timezone.utc), mode, pnl))
                _cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
                self._total_losses_window = [
                    t for t in self._total_losses_window if t[0] > _cutoff]

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
