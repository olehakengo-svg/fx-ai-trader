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
        "symbol": "USDJPY=X",
        "instrument": "USD_JPY",
        "base_sl_pips": 15,
    },
    "scalp": {
        "interval_sec": 10,       # 10秒ごとにシグナルチェック
        "tf": "1m",
        "period": "1d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルピング",
        "icon": "⚡",
        "symbol": "USDJPY=X",
        "instrument": "USD_JPY",
        "base_sl_pips": 3.5,
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
    #     "symbol": "USDJPY=X",
    #     "instrument": "USD_JPY",
    # },
    "daytrade_1h": {
        "interval_sec": 60,
        "tf": "1h",
        "period": "60d",
        "signal_fn": "compute_hourly_signal",
        "label": "1Hブレイクアウト(KSB+DMB)",
        "icon": "🕐",
        "symbol": "USDJPY=X",
        "instrument": "USD_JPY",
        "auto_start": True,
        "base_sl_pips": 30,
    },
    # ── EUR/USD modes ──
    "scalp_eur": {
        "interval_sec": 10,
        "tf": "1m",
        "period": "1d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルプEUR",
        "icon": "⚡🇪🇺",
        "symbol": "EURUSD=X",
        "instrument": "EUR_USD",
        "auto_start": True,
        "base_sl_pips": 3.5,
    },
    "daytrade_eur": {
        "interval_sec": 30,
        "tf": "15m",
        "period": "5d",
        "signal_fn": "compute_daytrade_signal",
        "label": "デイトレEUR",
        "icon": "📊🇪🇺",
        "symbol": "EURUSD=X",
        "instrument": "EUR_USD",
        "auto_start": True,
        "base_sl_pips": 15,
    },
    "daytrade_1h_eur": {
        "interval_sec": 60,
        "tf": "1h",
        "period": "60d",
        "signal_fn": "compute_hourly_signal",
        "label": "1Hブレイクアウト EUR(KSB+DMB)",
        "icon": "🕐🇪🇺",
        "symbol": "EURUSD=X",
        "instrument": "EUR_USD",
        "auto_start": True,
        "base_sl_pips": 30,
    },
    "scalp_eurjpy": {
        "interval_sec": 10,
        "tf": "1m",
        "period": "1d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルプEUR/JPY",
        "icon": "⚡💶",
        "symbol": "EURJPY=X",
        "instrument": "EUR_JPY",
        "auto_start": True,
        "base_sl_pips": 3.5,
        "active_hours_utc": (12, 15),  # UTC 12-15 only (London/NY overlap)
    },
    # ── GBP/USD Daytrade (15m) — Phase3 水平展開 ──
    "daytrade_gbpusd": {
        "interval_sec": 30,
        "tf": "15m",
        "period": "60d",
        "signal_fn": "compute_daytrade_signal",
        "label": "DT GBP/USD",
        "icon": "📊🇬🇧",
        "symbol": "GBPUSD=X",
        "instrument": "GBP_USD",
        "auto_start": True,
        "base_sl_pips": 15,
    },
    # ── EUR/GBP Daytrade (15m) — Phase3 水平展開 ──
    "daytrade_eurgbp": {
        "interval_sec": 30,
        "tf": "15m",
        "period": "60d",
        "signal_fn": "compute_daytrade_signal",
        "label": "DT EUR/GBP",
        "icon": "📊🇪🇺🇬🇧",
        "symbol": "EURGBP=X",
        "instrument": "EUR_GBP",
        "auto_start": True,
        "base_sl_pips": 15,
    },
    # ── XAU/USD Daytrade (15m) — Phase5 SMC戦略展開 ──
    # SMC 3/4戦略(turtle_soup, trendline_sweep, inducement_ob)+LRC が XAUUSD 対応済み
    # pip=0.01 (JPYスケール), OANDA XAU_USD
    "daytrade_xau": {
        "interval_sec": 30,
        "tf": "15m",
        "period": "60d",
        "signal_fn": "compute_daytrade_signal",
        "label": "DT XAU/USD",
        "icon": "📊🥇",
        "symbol": "XAUUSD=X",
        "instrument": "XAU_USD",
        "auto_start": True,
        "base_sl_pips": 200,       # Gold ATR(15m)≈100-300pips(0.01 scale)
    },
    # ── LCR: FROZEN (Phase2 BT全ペア負EV) ──
    # ── EUR/JPY, GBP/JPY RNB: REMOVED (spread負け) ──
    # ── Round Number Barrier (RNB) — USD/JPY 15m BUY-only ──
    "rnb_usdjpy": {
        "interval_sec": 30,
        "tf": "15m",
        "period": "60d",
        "signal_fn": "compute_rnb_signal",
        "label": "RNB USD/JPY",
        "icon": "🎯",
        "symbol": "USDJPY=X",
        "instrument": "USD_JPY",
        "auto_start": True,
        "base_sl_pips": 15,
        "active_hours_utc": (7, 20),
        "direction_filter": "BUY",  # BUY-only (SELL EV=-0.7, BUY EV=+7.7)
    },
}

# ── ベースモード抽出ヘルパー ──
# scalp_eur -> scalp, scalp_eurjpy -> scalp, lcr_gbpjpy -> lcr, daytrade_1h_eur -> daytrade_1h
def _get_base_mode(mode: str) -> str:
    for suffix in ("_usdjpy", "_gbpjpy", "_eurjpy", "_gbpusd", "_eurgbp", "_eur", "_xau"):  # longest first
        if mode.endswith(suffix):
            return mode[:-len(suffix)]
    return mode

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
        self._oanda = OandaBridge(db=self._db)
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

        # デプロイ中にOANDA未連携のOPENトレードを補完送信
        self._resend_pending_oanda_trades()

        # ── 戦略自動昇格: デモで実績を積んだ戦略のみOANDA実行 ──
        # 昇格条件: N >= 30 かつ EV > 0（デモ実績ベース）
        # 降格条件: N >= 30 かつ EV < -0.5
        # 未評価（N < 30）: デモのみ（OANDA連携しない）
        self._promoted_types: dict = {}  # {entry_type: {"status": "promoted"|"demoted"|"pending", "n": N, "wr": WR, "ev": EV}}
        self._evaluate_promotions()  # 起動時に評価

        # チューナブルパラメータ（学習エンジンが調整、全モード共通）
        # NOTE: sl_adjust / tp_adjust / session_blacklist は廃止
        #   SMC戦略(turtle_soup, trendline_sweep)の精密SL/TPを
        #   グローバル乗数で破壊するリスクがあるため完全パージ
        #   (2026-04-05 learning engine audit)
        self._params = {
            "confidence_threshold": 30,  # デモ: 30%（学習データ蓄積優先、本番は40推奨）
            "max_open_trades": 8,  # グローバル安全上限（実際の制御は通貨ペア×モードクラス別）
            "entry_type_blacklist": [],
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
        self._price_history = {}        # {instrument: [(timestamp, price)]} 通貨ペア別価格推移
        self._trade_high_water = {}     # trade_id -> max favorable price（BE/トレーリング用）
        # ── SL狩り対策: クロス戦略カスケード防御 + Fast-SL検出 ──
        self._sl_hit_history = []       # [(timestamp, instrument, entry_type, hold_sec)] SL_HIT履歴
        # ── MTF連携: 15m DT → 1m Scalp 戦略バイアス（通貨ペア別）──
        self._15m_tactical_bias = {}  # {instrument: {direction, entry_type, ...}}
        # 起動済みモード追跡（ヘルスチェッカー用）
        self._started_modes = set()
        self._user_stopped_modes = set()  # 明示的にstop()されたモード（ウォッチドッグ対象外）
        self._health_thread = None
        self._watchdog_thread = None
        self._last_request_tick = {}  # mode -> timestamp (リクエスト駆動tick用)
        # ── OANDA専用サーキットブレーカー (デモは制限なし) ──
        self._oanda_was_active = False  # 前回のOANDA active状態 (再開検出用)
        self._oanda_resume_ts = None    # OANDA最終再開時刻 (リミットリセット基準)

    def _resend_pending_oanda_trades(self):
        """デプロイ中にOANDA未連携だったOPENトレードを補完送信.
        5分以上前のトレードはスキップ（価格乖離が大きいため）."""
        if not self._oanda.active:
            return
        try:
            pending = self._db.get_open_trades_without_oanda()
            if not pending:
                return
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
            sent = 0
            skipped = 0
            for t in pending:
                mode = t.get("mode", "")
                if not self._oanda.is_mode_allowed(mode):
                    skipped += 1
                    continue
                # 古いトレードはスキップ（エントリー価格と現在価格の乖離が大きい）
                entry_time = t.get("entry_time", "")
                if entry_time:
                    try:
                        et = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                        if et < cutoff:
                            skipped += 1
                            continue
                    except Exception:
                        pass
                instrument = t.get("instrument", "USD_JPY")
                self._oanda.open_trade(
                    demo_trade_id=t["trade_id"],
                    direction=t["direction"],
                    sl=t["sl"],
                    tp=t["tp"],
                    mode=mode,
                    instrument=instrument,
                    callback=lambda tid, oid: self._db.set_oanda_trade_id(tid, oid),
                )
                sent += 1
            if sent or skipped:
                self._add_log(f"🔗 OANDA補完: {sent}件送信, {skipped}件スキップ（古い/モード外）")
                print(f"[OandaBridge] Resend: {sent} sent, {skipped} skipped", flush=True)
        except Exception as e:
            print(f"[OandaBridge] Resend pending failed: {e}", flush=True)

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
        # ── Self-healing: 30秒ごとに死んだスレッドを自動復旧（毎回実行は帯域浪費） ──
        _now = time.time()
        _last_heal = getattr(self, '_last_heal_time', 0)
        _healed = []
        if _now - _last_heal >= 30:
            self._last_heal_time = _now

            # _started_modesが空でも自動起動対象モードを起動（デプロイ直後のauto_start未完了対策）
            _auto_modes = [m for m, c in MODE_CONFIG.items() if c.get("auto_start", True)]
            _target_modes = list(self._started_modes) if self._started_modes else _auto_modes

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
        modes_status = {}
        _loop_alive = self._health_thread and self._health_thread.is_alive()
        for m, cfg in MODE_CONFIG.items():
            runner = self._runners.get(m, {})
            _actually_running = runner.get("running", False) and _loop_alive
            modes_status[m] = {
                "running": _actually_running,
                "label": cfg["label"],
                "icon": cfg["icon"],
                "tf": cfg["tf"],
                "interval": cfg["interval_sec"],
                "instrument": cfg.get("instrument", "USD_JPY"),
                "symbol": cfg.get("symbol", "USDJPY=X"),
                "last_signal": self._last_signals.get(m),
            }

        # ── オープンポジションに現在価格・含み損益を付与 ──
        _status_price_cache = {}
        for t in open_trades:
            try:
                _inst = t.get("instrument") or "USD_JPY"
                _mode = t.get("mode", "")
                _sym = MODE_CONFIG.get(_mode, {}).get("symbol", "USDJPY=X")
                if _inst not in _status_price_cache:
                    # _price_history から最新価格を取得（API呼び出し不要）
                    _ph = self._price_history.get(_inst, [])
                    if _ph:
                        _status_price_cache[_inst] = _ph[-1][1]
                    else:
                        _status_price_cache[_inst] = 0
                _cp = _status_price_cache[_inst]
                t["current_price"] = _cp
                _ep = t.get("entry_price", 0) or 0
                if _cp and _ep:
                    _pip_mult = 100 if _inst in ("USD_JPY", "EUR_JPY", "GBP_JPY") else 10000
                    if t.get("direction") == "BUY":
                        t["unrealized_pips"] = round((_cp - _ep) * _pip_mult, 1)
                    else:
                        t["unrealized_pips"] = round((_ep - _cp) * _pip_mult, 1)
                else:
                    t["unrealized_pips"] = 0
            except Exception:
                t["current_price"] = 0
                t["unrealized_pips"] = 0

        # log_count: 5秒キャッシュ（SELECT COUNT(*)を毎回回避）
        if _now - getattr(self, '_log_count_cache_ts', 0) >= 5:
            try:
                self._log_count_cache = self._db.get_log_count()
            except Exception:
                self._log_count_cache = getattr(self, '_log_count_cache', 0)
            self._log_count_cache_ts = _now

        return {
            "running": self.is_running(),
            "modes": modes_status,
            "open_trades": open_trades,
            "log_count": getattr(self, '_log_count_cache', 0),
            "oanda": self._oanda.status,
            "strategy_status": self._get_strategy_status_cached(),
            # healthz用（軽量フィールドのみ残す）
            "main_loop_alive": bool(_loop_alive),
            "watchdog_alive": bool(self._watchdog_thread and self._watchdog_thread.is_alive()),
            "sltp_checker_active": bool(self._sltp_thread and self._sltp_thread.is_alive()),
            "tick_counts": getattr(self, '_tick_counts', None),
            "main_loop_restarts": getattr(self, '_main_loop_restart_count', 0),
        }

    def request_tick(self):
        """リクエスト駆動tick: バックグラウンドスレッドが死んでいる場合のフォールバック。
        APIリクエスト時に呼ばれ、各モードのtickを実行する。
        スレッドが生きている場合はスキップ（二重実行防止）。"""
        if self._health_thread and self._health_thread.is_alive():
            return  # メインループが生きていれば不要
        # _started_modesが空なら自動起動対象モードをターゲット
        if not self._started_modes:
            for m, c in MODE_CONFIG.items():
                if m not in self._user_stopped_modes and c.get("auto_start", True):
                    self._started_modes.add(m)
                    self._runners[m] = {"running": True, "thread": None}
            print(f"[RequestTick] Force-started auto modes: {list(self._started_modes)}", flush=True)
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
        """DBから最新30件を古い順(時系列)で取得"""
        try:
            db_logs = self._db.get_logs(30)   # 最新30件 (newest first)
            return list(reversed(db_logs))     # oldest first → 時系列表示用
        except Exception:
            return []

    def get_params(self) -> dict:
        return self._params.copy()

    def set_params(self, updates: dict) -> dict:
        allowed = {"confidence_threshold", "max_open_trades", "learn_every_n"}
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

                # 全モードを強制チェック（EUR含む）
                _all_modes = ["scalp", "daytrade", "daytrade_1h", "swing",
                              "scalp_eur", "daytrade_eur", "daytrade_1h_eur",
                              "scalp_eurjpy", "rnb_usdjpy",
                              "daytrade_gbpusd", "daytrade_eurgbp"]
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
        """高頻度でリアルタイム価格を取得してSL/TPチェック
        BaseException耐性: キャッチして継続（スレッド不死化） (2026-04-05 audit fix)
        """
        print("[SLTP-Checker] Thread started", flush=True)
        _no_price_count = 0
        _oanda_sync_counter = 0
        _demo2oanda_counter = 0
        while self._sltp_running:
            try:
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

                # ── OANDA決済同期: 10秒ごと（SLTPループは0.5秒間隔 → 20回に1回）──
                _oanda_sync_counter += 1
                if _oanda_sync_counter >= 20:
                    _oanda_sync_counter = 0
                    try:
                        self._sync_oanda_closures()
                    except Exception as e:
                        print(f"[SLTP-Checker] OANDA sync error: {e}", flush=True)

                # ── Demo→OANDA同期: 5秒ごと（10回に1回）──
                # デモCloseだがOANDA Openの孤児ポジションを検出・クローズ
                _demo2oanda_counter += 1
                if _demo2oanda_counter >= 10:
                    _demo2oanda_counter = 0
                    try:
                        self._sync_demo_to_oanda()
                    except Exception as e:
                        print(f"[SLTP-Checker] Demo→OANDA sync error: {e}", flush=True)

                time.sleep(SLTP_CHECK_INTERVAL)
            except BaseException as e:
                # SystemExit/KeyboardInterruptでもスレッドを殺さない
                print(f"[SLTP-Checker] BaseException caught, continuing: {type(e).__name__}: {e}", flush=True)
                import traceback; traceback.print_exc()
                time.sleep(1)
                continue
        print("[SLTP-Checker] Thread terminated cleanly (sltp_running=False)", flush=True)

    def _get_realtime_price(self, instrument: str = "USD_JPY",
                            symbol: str = "USDJPY=X") -> float:
        """
        リアルタイム価格を最速で取得:
        1. _price_cache（TwelveData/yfinance）が10秒以内なら使用（USD_JPYのみ）
        2. OANDA v20 pricing API
        3. フォールバック: 1m足の最新Close
        """
        # (1) USD_JPYのみ: 既存のprice_cacheを確認
        if instrument == "USD_JPY":
            try:
                from modules.data import _price_cache, _cache_lock
                with _cache_lock:
                    pc = dict(_price_cache)
                if pc.get("ts"):
                    ts = pc["ts"]
                    now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
                    age = (now - ts).total_seconds()
                    if age < 15:
                        return float(pc["data"]["price"])
            except Exception:
                pass

        # (2) OANDA v20 リアルタイム価格
        try:
            from modules.data import fetch_oanda_price
            p = fetch_oanda_price(instrument)
            if p > 0:
                return p
        except Exception:
            pass

        # (3) フォールバック: 1m足の最新Close
        try:
            from app import fetch_ohlcv
            df = fetch_ohlcv(symbol, period="1d", interval="1m")
            if df is not None and len(df) > 0:
                return float(df.iloc[-1]["Close"])
        except Exception:
            pass

        return 0

    def _sync_oanda_closures(self):
        """OANDA側で決済済みだがデモ側OPENのトレードを同期クローズ"""
        if not self._oanda.active:
            return
        open_trades = self._db.get_open_trades()
        oanda_ids = {t.get("oanda_trade_id"): t for t in open_trades
                     if t.get("oanda_trade_id")}
        if not oanda_ids:
            return
        try:
            ok, data = self._oanda._client.get_trades(state="CLOSED", count=50)
            if not ok:
                return
            closed_oanda = {str(t["id"]): t for t in data.get("trades", [])}
            for oid, demo_trade in oanda_ids.items():
                if oid in closed_oanda:
                    ot = closed_oanda[oid]
                    close_price = float(ot.get("averageClosePrice", 0))
                    if close_price <= 0:
                        continue
                    trade_id = demo_trade["trade_id"]
                    mode = demo_trade.get("mode", "")
                    cfg = MODE_CONFIG.get(mode, {})
                    result = self._db.close_trade(trade_id, close_price, "OANDA_SL_TP")
                    if "error" not in result:
                        pnl = result.get("pnl_pips", 0)
                        outcome = result.get("outcome", "?")
                        icon = "✅" if outcome == "WIN" else "❌"
                        self._add_log(
                            f"{cfg.get('icon','')} 📤 OUT [{cfg.get('label','?')}]: {icon} {outcome} | "
                            f"{demo_trade['direction']} @ {demo_trade['entry_price']:.3f} → {close_price:.3f} | "
                            f"PnL: {pnl:+.1f} pips | "
                            f"Reason: OANDA_BROKER_CLOSE | ID: {trade_id}"
                        )
                        # Remove from bridge mapping
                        self._oanda._trade_map.pop(trade_id, None)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"oanda sync check error: {e}")

    def _sync_demo_to_oanda(self):
        """デモ側でクローズ済みだがOANDA側でまだオープンのトレードを強制クローズ。
        デモを正として、OANDA孤児ポジションを解消する。
        """
        if not self._oanda.active:
            return
        try:
            # 1. OANDA側のオープントレードを取得
            ok, data = self._oanda._client.get_open_trades()
            if not ok:
                return
            oanda_open = data.get("trades", [])
            if not oanda_open:
                return

            # 2. デモ側のオープントレードを取得
            demo_open = self._db.get_open_trades()
            demo_oanda_ids = set()
            for t in demo_open:
                oid = t.get("oanda_trade_id")
                if oid:
                    demo_oanda_ids.add(str(oid))

            # 3. bridge内のマッピングも考慮（まだDB書き込み前の可能性）
            with self._oanda._lock:
                for oid in self._oanda._trade_map.values():
                    demo_oanda_ids.add(str(oid))

            # 4. OANDA側にあるがデモ側にないトレードをクローズ
            for ot in oanda_open:
                oid = str(ot.get("id", ""))
                if oid and oid not in demo_oanda_ids:
                    # デモ側にマッピングがない → 孤児ポジション → クローズ
                    _inst = ot.get("instrument", "?")
                    _units = ot.get("currentUnits", "?")
                    self._add_log(
                        f"🔄 OANDA孤児クローズ: #{oid} {_inst} {_units}units "
                        f"(デモ側にマッピングなし)"
                    )
                    ok2, _ = self._oanda._client.close_trade(oid)
                    if ok2:
                        print(f"[DemoToOanda] Closed orphan OANDA #{oid} ({_inst})", flush=True)
                    else:
                        print(f"[DemoToOanda] Failed to close orphan #{oid}", flush=True)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"demo-to-oanda sync error: {e}")

    def _check_sltp_realtime(self):
        """全オープントレードをリアルタイム価格でSL/TPチェック + 最大保持時間 + 週末クローズ"""
        open_trades = self._db.get_open_trades()
        if not open_trades:
            return

        # 通貨ペア別にリアルタイム価格を取得（キャッシュ）— bid/ask対応
        _price_cache_rt = {}
        _bidask_cache_rt = {}  # {instrument: {"bid":, "ask":, "mid":}}
        def _get_price_for_instrument(inst, sym):
            if inst not in _price_cache_rt:
                # まずbid/askを取得（スプレッド反映の決済価格に使用）
                try:
                    from modules.data import fetch_oanda_bid_ask
                    _ba = fetch_oanda_bid_ask(inst)
                    if _ba:
                        _bidask_cache_rt[inst] = _ba
                        _price_cache_rt[inst] = _ba["mid"]
                        return _price_cache_rt[inst]
                except Exception:
                    pass
                _price_cache_rt[inst] = self._get_realtime_price(inst, sym)
            return _price_cache_rt[inst]

        # 少なくとも1つの通貨の価格が取れないとエラー
        _default_inst = "USD_JPY"
        _default_sym = "USDJPY=X"
        # 最初のトレードの通貨で価格チェック
        _first_trade = open_trades[0]
        _first_mode = _first_trade.get("mode", "")
        _first_cfg = MODE_CONFIG.get(_first_mode, {})
        _first_inst = _first_cfg.get("instrument", _default_inst)
        _first_sym = _first_cfg.get("symbol", _default_sym)
        price = _get_price_for_instrument(_first_inst, _first_sym)
        if price <= 0:
            raise _NoPriceError("realtime price unavailable")

        # 最大保持時間（秒）: scalp=30分, daytrade=8時間, daytrade_1h=18時間, swing=72時間
        MAX_HOLD_SEC = {"scalp": 1800, "daytrade": 28800, "daytrade_1h": 64800, "swing": 259200}

        # 週末クローズ判定（金曜21:45 UTC以降 = 閉場15分前に全ポジクローズ）
        _now_utc = datetime.now(timezone.utc)
        # 金曜21:45 UTC以降 = 閉場15分前に全ポジクローズ (2026-04-05 audit fix)
        _is_pre_weekend = (
            _now_utc.weekday() == 4
            and (_now_utc.hour > 21 or (_now_utc.hour == 21 and _now_utc.minute >= 45))
        )

        # EUR/USD用MAX_HOLD追加
        MAX_HOLD_SEC["scalp_eur"] = 1800
        MAX_HOLD_SEC["scalp_eurjpy"] = 1800
        MAX_HOLD_SEC["daytrade_eur"] = 28800
        MAX_HOLD_SEC["daytrade_1h_eur"] = 64800
        MAX_HOLD_SEC["rnb_usdjpy"] = 7200   # RNB: max 2h hold

        for trade in open_trades:
            direction = trade["direction"]
            sl = trade["sl"]
            tp = trade["tp"]
            trade_id = trade["trade_id"]
            tf = trade.get("tf", "")
            mode = trade.get("mode", "")
            entry_price = trade["entry_price"]

            # 通貨ペア別価格取得
            _mode_cfg = MODE_CONFIG.get(mode, {})
            _inst = _mode_cfg.get("instrument", _default_inst)
            _sym = _mode_cfg.get("symbol", _default_sym)
            price = _get_price_for_instrument(_inst, _sym)
            if price <= 0:
                continue  # この通貨の価格が取れない場合はスキップ
            # pip計算用桁数
            _pip_decimals = 3 if "JPY" in _inst else 5

            # ── OANDAスプレッド反映: SL/TP判定もbid/askベース ──
            # BUYポジの決済=売り(bid), SELLポジの決済=買い(ask)
            _ba_rt = _bidask_cache_rt.get(_inst)
            if _ba_rt:
                if direction == "BUY":
                    price = _ba_rt["bid"]   # BUY決済 → bid
                else:
                    price = _ba_rt["ask"]   # SELL決済 → ask

            # ══════════════════════════════════════════════════════════════
            # ── ブレイクイーブン（BT統一: 60% TP到達でBE、トレーリングなし）──
            # BTと同一ロジック: 60%到達でSL→エントリー価格に移動のみ
            # ══════════════════════════════════════════════════════════════
            tp_dist = abs(tp - entry_price)
            if direction == "BUY":
                favorable_move = price - entry_price
            else:
                favorable_move = entry_price - price

            _original_sl = sl  # OANDA SL変更検出用
            if favorable_move > 0 and tp_dist > 0:
                progress = favorable_move / tp_dist  # 0.0 ~ 1.0+

                if progress >= 0.60:
                    # 60%到達: BEのみ（トレーリングなし = BT統一）
                    # スプレッド考慮: BUYはbidで決済されるのでentry+spread、SELLはaskで決済されるのでentry-spread
                    if _ba_rt:
                        _spread_amt = _ba_rt["ask"] - _ba_rt["bid"]
                    else:
                        _spread_amt = 0.008 if "JPY" in _inst else 0.00008
                    if direction == "BUY":
                        new_sl = round(entry_price + _spread_amt, _pip_decimals)
                        if new_sl > sl:
                            sl = new_sl
                    else:
                        new_sl = round(entry_price - _spread_amt, _pip_decimals)
                        if new_sl < sl:
                            sl = new_sl

            # ── OANDA連携: トレーリングSL変更をミラー ──
            if sl != _original_sl:
                self._oanda.modify_sl(trade_id, sl, instrument=_inst)

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
                    max_hold = MAX_HOLD_SEC.get(_mode, MAX_HOLD_SEC.get(_get_base_mode(_mode), 259200))
                    if hold_sec > max_hold:
                        close_reason = "MAX_HOLD_TIME"
                except Exception:
                    pass

            # ── SL狩り対策C1: 時間ベース撤退 ──
            # 保持時間50%経過で含み損 → SL到達前に早期損切り（損失額を削減）
            if not close_reason:
                try:
                    entry_time_c1 = datetime.fromisoformat(trade.get("entry_time", ""))
                    if entry_time_c1.tzinfo is None:
                        entry_time_c1 = entry_time_c1.replace(tzinfo=timezone.utc)
                    _hold_c1 = (datetime.now(timezone.utc) - entry_time_c1).total_seconds()
                    _mode_c1 = mode or {"1m": "scalp", "15m": "daytrade", "4h": "swing"}.get(tf, "")
                    _max_c1 = MAX_HOLD_SEC.get(_mode_c1, MAX_HOLD_SEC.get(_get_base_mode(_mode_c1), 1800))
                    _half_hold = _max_c1 * 0.5
                    if _hold_c1 > _half_hold:
                        _in_loss = (direction == "BUY" and price < entry_price) or \
                                   (direction == "SELL" and price > entry_price)
                        if _in_loss:
                            close_reason = "TIME_DECAY_EXIT"
                except Exception:
                    pass

            if close_reason:
                # モード判定
                if not mode:
                    mode = {"1m": "scalp", "15m": "daytrade", "4h": "swing"}.get(tf, "")
                cfg = MODE_CONFIG.get(mode, {})

                # ── P0監視: 決済時スプレッド記録 ──
                _spread_exit = 0.0
                _is_jpy_exit = "JPY" in _inst
                _pip_m_exit = 100 if _is_jpy_exit else 10000
                if _ba_rt:
                    _spread_exit = round((_ba_rt["ask"] - _ba_rt["bid"]) * _pip_m_exit, 2)

                result = self._db.close_trade(trade_id, price, close_reason,
                                              spread_at_exit=_spread_exit)
                if "error" in result:
                    continue  # 別スレッドで既にクローズ済み → スキップ

                # ── 決済分析生成・保存 ──
                try:
                    _ca = self._generate_close_analysis(
                        trade, close_reason,
                        result.get("pnl_pips", 0), result.get("outcome", ""))
                    self._db.update_close_analysis(trade_id, _ca)
                except Exception:
                    pass

                # ── OANDA連携: ポジションクローズ ──
                self._oanda.close_trade(trade_id, reason=close_reason)

                pnl = result.get("pnl_pips", 0)
                outcome = result.get("outcome", "?")
                icon = "✅" if outcome == "WIN" else "❌"

                self._add_log(
                    f"{cfg.get('icon','')} 📤 OUT [{cfg.get('label','?')}]: {icon} {outcome} | "
                    f"{direction} @ {trade['entry_price']:.3f} → {price:.3f} | "
                    f"PnL: {pnl:+.1f} pips | "
                    f"Reason: {close_reason} | spread={_spread_exit:.1f}p | ID: {trade_id}"
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

                # ── SL狩り対策: SL_HIT履歴記録（カスケード防御 + Fast-SL検出用）──
                if close_reason == "SL_HIT":
                    _hold_s = 9999
                    try:
                        _et = datetime.fromisoformat(trade.get("entry_time", ""))
                        if _et.tzinfo is None:
                            _et = _et.replace(tzinfo=timezone.utc)
                        _hold_s = (datetime.now(timezone.utc) - _et).total_seconds()
                    except Exception:
                        pass
                    self._sl_hit_history.append((
                        datetime.now(timezone.utc), _inst,
                        trade.get("entry_type", ""), _hold_s))
                    # 古い記録を削除（最大2時間保持）
                    _sl_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
                    self._sl_hit_history = [
                        h for h in self._sl_hit_history if h[0] > _sl_cutoff]

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
        """全モードを順次処理するメインループ（タイムアウト最適化版）。
        scalp=10s, daytrade=30s, 1h=60s の間隔で各モードをtick。
        (2026-04-06 perf: tick timeout 60s→30s, sleep 0.5→1s, 初回stagger)"""
        import sys
        self._main_loop_status = "starting"
        self._main_loop_error = None
        print("[DemoTrader] MainLoop started (serial, timeout=30s)", flush=True)
        sys.stdout.flush()
        _last_tick = {}
        _consecutive_errors = {}
        _restart_count = getattr(self, '_main_loop_restart_count', 0)
        self._main_loop_restart_count = _restart_count + 1

        self._main_loop_status = "running"
        self._main_loop_start_ts = time.time()
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

                        # 初回tick分散: 起動直後は mode index × 3秒ずらし
                        if last == 0:
                            _idx = list(MODE_CONFIG.keys()).index(mode) if mode in MODE_CONFIG else 0
                            _stagger = _idx * 3
                            if now - self._main_loop_start_ts < _stagger:
                                continue

                        if now - last < interval:
                            continue

                        # ── このモードのtickを実行（30秒タイムアウト）──
                        try:
                            _tick_start = time.time()
                            _tick_result = [None]
                            _tick_thread = threading.Thread(
                                target=self._tick_with_catch, args=(mode, _tick_result), daemon=True)
                            _tick_thread.start()
                            _tick_thread.join(timeout=30)  # 60s→30sに短縮
                            if _tick_thread.is_alive():
                                print(f"[MainLoop/{mode}] TIMEOUT after 30s — skipping", flush=True)
                                _last_tick[mode] = time.time()
                                errs = _consecutive_errors.get(mode, 0) + 1
                                _consecutive_errors[mode] = errs
                                continue
                            if _tick_result[0] is not None:
                                raise _tick_result[0]
                            _tick_dur = time.time() - _tick_start
                            _consecutive_errors[mode] = 0
                            _last_tick[mode] = time.time()
                            _tick_count = getattr(self, '_tick_counts', {})
                            _tick_count[mode] = _tick_count.get(mode, 0) + 1
                            self._tick_counts = _tick_count
                            if _tick_count[mode] <= 3 or _tick_count[mode] % 10 == 0 or _tick_dur > 15:
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
                            if errs >= 10:
                                print(f"[MainLoop/{mode}] Too many errors, backing off 60s", flush=True)
                                time.sleep(60)

                except Exception as e:
                    print(f"[MainLoop] Outer error: {e}", flush=True)
                    import traceback; traceback.print_exc()

                # GIL yield + 1s間隔でdue判定（API応答性確保）
                time.sleep(1.0)

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
            # watchdogが30秒以内に検出して再起動する (2026-04-05 audit fix M4)
            # NOTE: ここで _ensure_main_loop() を呼ぶと、自スレッドが
            #       まだ alive なため is_alive() チェックを通過し再起動が失敗する
            print("[MainLoop] Thread exiting — watchdog will restart", flush=True)

    def _check_drawdown(self) -> bool:
        """OANDA専用サーキットブレーカー: 日次 -30pip / DD -100pip。
        制限到達 → OANDA全モード自動停止（デモは常に継続 = 常にFalse返却）。
        OANDA非稼働時は何もしない（データ蓄積優先）。
        ユーザーがOAモードを再ON → リミット自動リセット。"""
        _DAILY_LIMIT = -30   # 日次損失リミット (pip)
        _DD_LIMIT = -100     # 最大DD リミット (pip, OANDA再開以降の累計)
        try:
            # ── OANDA再開検出 → リミットリセット ──
            _oa_active = self._oanda.active and bool(self._oanda._allowed_modes)
            if _oa_active and not self._oanda_was_active:
                self._oanda_resume_ts = datetime.now(timezone.utc)
                self._add_log(
                    f"🟢 OANDA再開: 日次({_DAILY_LIMIT}pip)/DD({_DD_LIMIT}pip)リミット適用開始")
                print(f"[CB] OANDA resumed — limits reset at "
                      f"{self._oanda_resume_ts.isoformat()}", flush=True)
            self._oanda_was_active = _oa_active

            if not _oa_active or not self._oanda_resume_ts:
                return False  # OANDA非稼働 → 制限なし、デモ継続

            # ── 再開以降のクローズ済みトレードの PnL を集計 ──
            closed = self._db.get_closed_trades(limit=200)
            resume_iso = self._oanda_resume_ts.isoformat()
            recent = [t for t in closed
                      if (t.get("exit_time") or "") >= resume_iso]

            # DD制限: 再開以降の累計 PnL
            pnl_since_resume = sum(t.get("pnl_pips", 0) for t in recent)
            if pnl_since_resume <= _DD_LIMIT:
                self._oanda_kill("DD制限到達", pnl_since_resume, _DD_LIMIT)
                return False  # デモ継続

            # 日次制限: 今日の再開以降 PnL
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            daily_pnl = sum(
                t.get("pnl_pips", 0) for t in recent
                if (t.get("exit_time") or "").startswith(today))
            if daily_pnl <= _DAILY_LIMIT:
                self._oanda_kill("日次損失制限到達", daily_pnl, _DAILY_LIMIT)
                return False  # デモ継続

            return False  # デモは常に継続
        except Exception:
            return False

    def _oanda_kill(self, reason: str, pnl: float, limit: float):
        """OANDA全モード自動停止（デモは継続）。
        ユーザーがダッシュボードからOAモードを再ONすればリセット＆再適用。"""
        modes_before = sorted(self._oanda._allowed_modes) if self._oanda._allowed_modes else []
        self._oanda._allowed_modes = set()
        self._oanda._save_allowed_modes()
        self._add_log(
            f"🔴 OANDA CB発動: {reason} ({pnl:+.1f}pip / limit {limit}pip) "
            f"— OANDA全モード停止 [{','.join(modes_before)}]、デモ継続")
        print(f"[CB] OANDA killed: {reason} ({pnl:+.1f}pip / {limit}pip) "
              f"modes={modes_before}", flush=True)

    def _tick_with_catch(self, mode: str, result: list):
        """_tickを実行して例外をresult[0]に格納。タイムアウト用ワーカー。"""
        try:
            self._tick(mode)
        except Exception as e:
            result[0] = e

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

        # ── 時間帯フィルター (EUR/JPY等の限定稼働) ──
        # NOTE: datetime/timezone はモジュールレベルで import 済み (L12)
        _active_hours = cfg.get("active_hours_utc")
        if _active_hours is not None:
            _now_utc = datetime.now(timezone.utc)
            if not (_active_hours[0] <= _now_utc.hour <= _active_hours[1]):
                return  # 稼働時間外はスキップ

        # Import here to avoid circular imports
        from app import fetch_ohlcv, add_indicators, find_sr_levels

        _base_mode_fn = _get_base_mode(mode)
        if _base_mode_fn == "daytrade":
            from app import compute_daytrade_signal as compute_fn
        elif _base_mode_fn == "swing":
            from app import compute_swing_signal as compute_fn
        elif _base_mode_fn == "daytrade_1h":
            from app import compute_hourly_signal as compute_fn
        elif _base_mode_fn == "rnb":
            from app import compute_rnb_signal as compute_fn
        else:
            from app import compute_scalp_signal as compute_fn

        tf = cfg["tf"]
        period = cfg["period"]
        symbol = cfg.get("symbol", "USDJPY=X")
        instrument = cfg.get("instrument", "USD_JPY")
        # (2026-04-05 perf) 毎tick printを抑制 → 10tick毎 or 遅延時のみ出力
        _tc = getattr(self, '_tick_counts', {}).get(mode, 0)
        _verbose = (_tc <= 3 or _tc % 50 == 0)
        if _verbose:
            print(f"[DemoTrader/{mode}] _tick start: tf={tf}, period={period}, symbol={symbol}", flush=True)

        # 1. データ取得 + シグナル計算
        try:
            # scalp(1m)はperiod拡大でEMA200を確保
            fetch_period = "5d" if tf == "1m" else period
            df = fetch_ohlcv(symbol, period=fetch_period, interval=tf)
            if _verbose:
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

            # ── 1H Breakout mode: HourlyEngine (KSB+DMB) ──
            if _base_mode_fn == "daytrade_1h":
                sig = compute_fn(df, tf, sr, symbol)
            else:
                sig = compute_fn(df, tf, sr, symbol)

            # ── 5m補完: sr_channel_reversal / macdh_reversal は5mの方が高EV ──
            # 1m: WR=48.5%/-0.162, WR=46.7%/-0.023
            # 5m: WR=63.6%/+0.318, WR=78.4%/+0.722
            _5M_ONLY_STRATEGIES = {"macdh_reversal", "fib_reversal", "ema_pullback"}  # sr_channel_reversal除外(7d BTで赤字)
            if mode in ("scalp", "scalp_eur", "scalp_eurjpy") and sig.get("signal") == "WAIT":
                try:
                    df_5m = fetch_ohlcv(symbol, period="5d", interval="5m")
                    df_5m = add_indicators(df_5m)
                    _5m_cols = [c for c in ["close", "ema9", "ema21", "rsi", "adx", "atr"]
                                if c in {x.lower() for x in df_5m.columns}]
                    _5m_actual = [c for c in df_5m.columns if c.lower() in _5m_cols]
                    if _5m_actual:
                        df_5m = df_5m.dropna(subset=_5m_actual)
                    if len(df_5m) >= 50:
                        sr_5m = find_sr_levels(df_5m)
                        sig_5m = compute_fn(df_5m, "5m", sr_5m, symbol)
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

        # ── 後半処理: エントリー判定（例外でスレッドハングを防止）──
        try:
            self._tick_entry(mode, cfg, sig, tf, instrument)
        except Exception as _entry_err:
            print(f"[DemoTrader/{mode}] _tick_entry error: {_entry_err}", flush=True)
            import traceback; traceback.print_exc()

    def _tick_entry(self, mode: str, cfg: dict, sig: dict,
                    tf: str, instrument: str):
        """_tickの後半: エントリー判定・実行。例外は呼び出し元でキャッチ。"""
        current_price = sig.get("entry", 0)
        signal = sig.get("signal", "WAIT")
        _base_mode = _get_base_mode(mode)  # scalp_eur/scalp_eurjpy -> scalp

        # ── OANDAスプレッド反映: bid/askで実際のエントリー価格を使用 ──
        # BUY → ask価格, SELL → bid価格（OANDAと同じ約定価格）
        _ba = None  # P0監視用にスコープ拡張
        if signal in ("BUY", "SELL"):
            try:
                from modules.data import fetch_oanda_bid_ask
                _ba = fetch_oanda_bid_ask(instrument)
                if _ba:
                    if signal == "BUY":
                        current_price = _ba["ask"]
                    else:
                        current_price = _ba["bid"]
            except Exception:
                pass  # フォールバック: シグナルのmid価格をそのまま使用

        # ══════════════════════════════════════════════════════════════
        # ── MTF連携: 15m DT シグナル → 1m Scalp バイアス更新 ──
        # DT/DT1hの構造的パターン（三尊/逆三尊/SR等）を記録し、
        # スキャルプが順方向エントリーを強化 / 逆方向を抑制する
        # ══════════════════════════════════════════════════════════════
        if _base_mode in ("daytrade", "daytrade_1h") and signal != "WAIT":
            _dt_etype = sig.get("entry_type", "")
            # 構造的パターン（強いバイアス）とトレンドシグナル（軽いバイアス）
            _strong_patterns = {"hs_neckbreak", "ihs_neckbreak", "dual_sr_bounce",
                                "dual_sr_breakout", "sr_fib_confluence"}
            _trend_patterns = {"ema_cross", "mtf_momentum", "pivot_breakout",
                                "keltner_squeeze_breakout", "donchian_momentum_breakout"}
            if _dt_etype in _strong_patterns or _dt_etype in _trend_patterns:
                _bias_strength = "strong" if _dt_etype in _strong_patterns else "trend"
                with self._lock:
                    self._15m_tactical_bias[instrument] = {
                        "direction": signal,
                        "entry_type": _dt_etype,
                        "confidence": sig.get("confidence", 0),
                        "updated_at": datetime.now(timezone.utc),
                        "signal_price": current_price,
                        "strength": _bias_strength,
                    }

        # ── 価格ヒストリー記録（ベロシティ計算用・通貨ペア別）──
        _now_rec = datetime.now(timezone.utc)
        _inst = instrument
        if _inst not in self._price_history:
            self._price_history[_inst] = []
        self._price_history[_inst].append((_now_rec, current_price))
        # 古いデータを削除（最大4時間保持）
        _cutoff = _now_rec - timedelta(hours=4)
        self._price_history[_inst] = [(t, p) for t, p in self._price_history[_inst] if t > _cutoff]
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
            # 動的値(秒数,pip数等)を除去してキー爆発を防止 (2026-04-05 audit fix)
            k = f"{mode}:{reason.split('(')[0]}"
            self._block_counts[k] = self._block_counts.get(k, 0) + 1
            return

        # ── 方向フィルター (RNB BUY-only等) ── (2026-04-05 audit fix)
        _dir_filter = cfg.get("direction_filter")
        if _dir_filter and signal != _dir_filter:
            _block(f"direction_filter"); return

        # ── 通貨ペア×モードクラス別ポジション制限 ──
        # scalp/DT/1H/swingが独立してポジションを持てる
        # scalp: 高頻度のため2本まで（シグナル方向転換に対応）
        # DT/1H/swing: 1本ずつ
        _base_mode = _get_base_mode(mode)
        _mode_limits = {"scalp": 2, "daytrade": 1, "daytrade_1h": 1, "swing": 1}
        _mode_limit = _mode_limits.get(_base_mode, 1)
        _mode_inst_trades = [t for t in open_trades
                            if t.get("instrument", "USD_JPY") == instrument
                            and _get_base_mode(t.get("mode", "")) == _base_mode]
        if len(_mode_inst_trades) >= _mode_limit:
            _block(f"max_per_mode_pair({_base_mode}/{instrument}:{len(_mode_inst_trades)}/{_mode_limit})"); return
        # グローバル安全上限（全通貨ペア・全モード合計）
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
        _is_jpy = "JPY" in instrument
        if _is_jpy:
            _same_price_dist = {"scalp": 0.010, "daytrade": 0.050}.get(_base_mode, 0.03)
        else:
            _same_price_dist = {"scalp": 0.00010, "daytrade": 0.00050}.get(_base_mode, 0.00030)
        for t in mode_trades:
            if abs(t["entry_price"] - current_price) < _same_price_dist:
                _block(f"same_price_{_same_price_dist*100:.0f}pip"); return
        # (B) 同方向ポジション上限 — モードクラス×通貨ペア別制限で暗黙制御
        # scalp:2本/DT:1本なので、同価格帯チェックで十分

        # ══════════════════════════════════════════════════════════════
        # ── エントリー理由の品質ゲート ──
        # 「なぜここでエントリーするのか」が明確な場合のみ通す
        # ══════════════════════════════════════════════════════════════
        reasons = sig.get("reasons", [])

        # 明確な技術的根拠を持つエントリータイプ
        # 2026-04-03 FXアナリストレビューで33→9戦略に統廃合
        QUALIFIED_TYPES = {
            # ═══ スキャルプ (9戦略) ═══
            "bb_rsi_reversion",      # BB+RSI平均回帰 — 主力 (318t WR59% EV+0.26)
            "macdh_reversal",        # MACD-H方向転換 — ライブEV正 (171t WR59% EV+0.21)
            "stoch_trend_pullback",  # Stochトレンドプルバック — 最高効率 (85t WR64% EV+0.59)
            "bb_squeeze_breakout",   # BBスクイーズブレイクアウト (5t WR60% EV+1.08)
            "london_breakout",       # ロンドン開場ブレイクアウト 07-09UTC
            "tokyo_bb",              # 東京BB（金曜ブロック）
            "mtf_reversal_confluence",  # MTF RSI+MACD一致（ライブ専用）
            "fib_reversal",          # フィボ38.2-61.8%反発 — BB中央補完 (BT 61t WR57% EV+0.29)
            "ema_pullback",          # EMAプルバック反発 — BB中央帯でも発火 (FXアナリスト推奨新戦略)
            "session_vol_expansion",  # SVE: EUR/USD ロンドンオープン圧縮ブレイク (2026-04-04)
            # DISABLED (FXアナリストレビュー 2026-04-03):
            # "v_reversal",          # → bb_rsi統合予定 (サンプル5t)
            # "trend_rebound",       # 廃止: 1t EV=-1.22, 実質未発火
            # "ihs_neckbreak",       # 廃止: 1m足でパターン認識不適
            # "sr_touch_bounce",     # 廃止: BT結果なし, sr_fib(15m)と重複
            # "rsi_divergence_sr",   # 廃止: EV=-0.607
            # v1互換6種:            # 全廃止: BT結果なし, v2と機能重複
            # "sr_bounce", "ob_retest", "bb_bounce",
            # "donchian", "reg_channel", "ema_pullback",

            # ═══ デイトレ (2戦略) ═══
            "sr_fib_confluence",     # SR+フィボ合流 — DT主力 (229t WR73% EV+0.50)
            "ema_cross",             # EMAクロスリテスト (39t WR77% EV+0.64)
            "htf_false_breakout",    # FBF: 1H SR False Breakout Fade (2026-04-04)
            "london_session_breakout",  # LSB: アジア→ロンドンブレイクアウト (2026-04-04)
            "tokyo_nakane_momentum",  # TNM: 仲値リバーサル BUY専用 (2026-04-04)
            "adx_trend_continuation",  # ADX TC: トレンド押し目/戻り目 (2026-04-04)
            "sr_break_retest",           # SBR: SR Break & Retest (2026-04-05)
            "lin_reg_channel",           # LRC: Linear Regression Channel (2026-04-05)
            "orb_trap",                      # ORB Trap: Opening Range Fakeout Reversal (2026-04-05)
            "london_close_reversal",         # LCR: London Close Wick Reversal (DISABLED)
            "gbp_deep_pullback",             # GBP Deep PB: BB-2σ/EMA50 deep pullback (2026-04-05)
            "turtle_soup",                   # Turtle Soup: Liquidity Grab Reversal (Phase 5, 2026-04-05)
            "trendline_sweep",               # TL Sweep: Trendline Sweep Trap (Phase 5, 2026-04-05)
            "inducement_ob",                 # IOB: Inducement & Order Block Trap (Phase 5, 2026-04-05)
            # "post_news_vol",               # PNV: DISABLED — WR=42% EV=-0.07, needs calendar API
            # DISABLED (FXアナリストレビュー):
            # "ihs_neckbreak",       # 廃止: 2t EV≒0, 低頻度
            # "dual_sr_breakout",    # 廃止: 未評価
            # "dt_fib_reversal",     # 廃止: フォールバック未発火
            # "dt_sr_channel_reversal",  # 廃止: フォールバック未発火
            # "ema200_trend_reversal",   # 廃止: フォールバック未発火

            # ═══ 1H Breakout — HourlyEngine (v5.0) ═══
            "keltner_squeeze_breakout",      # KSB: EUR専用, WR=50% RR=2.0
            "donchian_momentum_breakout",    # DMB: 両ペア, EUR WR=50% / JPY WR=35%
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

        # ── bb_rsi / macdh 排他制御 ──
        # 相関0.65: 同一環境で同時発火→SLカスケードの原因
        # 同方向で直近3分以内にどちらかがエントリー済みなら他方をブロック
        _mutual_excl = {"bb_rsi_reversion", "macdh_reversal"}
        if entry_type in _mutual_excl:
            _other = _mutual_excl - {entry_type}
            _me_cutoff = datetime.now(timezone.utc) - timedelta(seconds=180)
            for _ot in open_trades:
                if (_ot.get("entry_type") in _other
                    and _ot.get("instrument", "USD_JPY") == instrument
                    and _ot.get("direction") == signal):
                    try:
                        _ot_time = datetime.fromisoformat(_ot.get("entry_time", ""))
                        if _ot_time.tzinfo is None:
                            _ot_time = _ot_time.replace(tzinfo=timezone.utc)
                        if _ot_time > _me_cutoff:
                            _block(f"mutual_excl({entry_type}_vs_{_ot.get('entry_type')})")
                            return
                    except Exception:
                        pass

        if entry_type not in QUALIFIED_TYPES and entry_type not in CONDITIONAL_TYPES:
            _block(f"unknown_type:{entry_type}"); return

        from modules.learning_engine import SMC_PROTECTED
        if entry_type in self._params["entry_type_blacklist"] and entry_type not in SMC_PROTECTED:
            _block(f"blacklisted:{entry_type}"); return

        # ── クールダウン（BT統一: 前ポジ決済後1バー分）──
        # BT: COOLDOWN=1バー。本番もBTと同一の1バー分に統一
        # 根拠: BT COOLDOWN=1bar → DT 15m=900s, 1H=3600s
        # 旧設定(DT=30s)ではBT比30倍速で再エントリー → WR 62.2%→40% の乖離原因
        last_ex = self._last_exit.get(mode)
        if last_ex:
            _ex_age = (datetime.now(timezone.utc) - last_ex["time"]).total_seconds()
            _cooldown_sec = {"scalp": 60, "daytrade": 900, "daytrade_1h": 3600, "swing": 14400}.get(_base_mode, 60)
            if _ex_age < _cooldown_sec:
                _block(f"cooldown({int(_ex_age)}s/{_cooldown_sec}s)"); return

        # ── 時間帯フィルター: BT統一 = 制限なし ──
        # BTは時間帯制限なしで WR=56.2%。1本逐次処理なら時間帯問わず利益出る
        # (シグナル関数側のセッションフィルターは維持)

        # ── 連敗制御: 同方向N連敗で一時停止 ──
        max_cl = self._params.get("max_consecutive_losses", 3)
        mode_cl = self._consec_losses.get(mode, {})
        if mode_cl.get(signal, 0) >= max_cl:
            _block(f"consec_loss({mode_cl.get(signal,0)})"); return

        # ── 全方向サーキットブレーカー: 30分以内にN回負けでモード一時停止 ──
        # 本番実績: DT 12連敗(-101pip)を防止するための安全装置
        _cb_limits = {"scalp": 4, "daytrade": 3, "daytrade_1h": 2, "swing": 2}
        _cb_max = _cb_limits.get(_base_mode, 3)
        _cb_window = timedelta(minutes=30)
        _cb_cutoff = datetime.now(timezone.utc) - _cb_window
        _cb_recent = [t for t in self._total_losses_window
                      if t[0] > _cb_cutoff and t[1] == mode]
        if len(_cb_recent) >= _cb_max:
            _cb_total_loss = sum(t[2] for t in _cb_recent)
            _block(f"circuit_breaker({len(_cb_recent)}losses/{_cb_max}max_in_30min, total={_cb_total_loss:+.1f}pip)")
            return

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策①: クロス戦略カスケードクールダウン ──
        # 本番実績: 同価格帯で4戦略同時発火→全滅(-17.1pip/11分)
        # 同一通貨ペアでSL_HITが発生した場合、全戦略に短期クールダウン適用
        # scalp: 90s, DT: 180s（同価格帯の反復エントリーを防止）
        # ══════════════════════════════════════════════════════════════
        _cascade_cd = {"scalp": 90, "daytrade": 180, "daytrade_1h": 300, "swing": 600}.get(_base_mode, 90)
        _cascade_cutoff = datetime.now(timezone.utc) - timedelta(seconds=_cascade_cd)
        _recent_sl_same_inst = [h for h in self._sl_hit_history
                                if h[0] > _cascade_cutoff and h[1] == instrument]
        if _recent_sl_same_inst:
            _last_sl = _recent_sl_same_inst[-1]
            _sl_age = (datetime.now(timezone.utc) - _last_sl[0]).total_seconds()
            _block(f"cascade_cd({instrument},{_last_sl[2]},SL {int(_sl_age)}s ago/{_cascade_cd}s)")
            return

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策E1: スプレッドフィルター ──
        # 異常スプレッド時はSL狩りの前兆 → エントリー見送り
        # USD/JPY通常0.2-0.4pip, 閾値1.2pip(3倍)
        # ══════════════════════════════════════════════════════════════
        try:
            from modules.data import fetch_oanda_bid_ask
            _ba_entry = fetch_oanda_bid_ask(instrument)
        except Exception:
            _ba_entry = None
        if _ba_entry:
            _spread_pips = (_ba_entry["ask"] - _ba_entry["bid"]) * (100 if _is_jpy else 10000)
            _spread_limit = 1.2 if _is_jpy else 1.5  # pips
            if _spread_pips > _spread_limit:
                _block(f"spread_wide({_spread_pips:.1f}pip>{_spread_limit})")
                return

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策A1: 価格スパイク検出 ──
        # 直近60秒で価格が急変動(>ATR×0.5)→ SL狩りスパイク中のため見送り
        # ══════════════════════════════════════════════════════════════
        _atr_spike = sig.get("atr", 0.07 if _is_jpy else 0.00070)
        _spike_cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        _inst_history = self._price_history.get(instrument, [])
        _spike_prices = [p for t, p in _inst_history if t > _spike_cutoff]
        if len(_spike_prices) >= 3:
            _spike_range = max(_spike_prices) - min(_spike_prices)
            if _spike_range > _atr_spike * 0.5:
                _block(f"spike({_spike_range*100 if _is_jpy else _spike_range*10000:.1f}pip/60s)")
                return

        # ══════════════════════════════════════════════════════════════
        # ── ベロシティフィルター ──
        # 本番で急騰中のSELL連敗(-36pip)の原因 → 急動時の逆行エントリーをブロック
        # ══════════════════════════════════════════════════════════════
        _now_vel = datetime.now(timezone.utc)
        _vel_window_min = {"scalp": 10, "daytrade": 30, "daytrade_1h": 60}.get(_base_mode, 10)
        _vel_threshold_pip = {"scalp": 15.0, "daytrade": 15.0, "daytrade_1h": 20.0}.get(_base_mode, 8.0)  # scalp: 8→15pip（調整局面のカウンタートレード許可）
        _vel_cutoff = _now_vel - timedelta(minutes=_vel_window_min)
        _recent_prices = [(t, p) for t, p in self._price_history.get(instrument, []) if t > _vel_cutoff]
        if len(_recent_prices) >= 2:
            _oldest_price = _recent_prices[0][1]
            _price_move = current_price - _oldest_price
            from modules.demo_db import pip_multiplier as _pip_mult_fn
            _pip_m = _pip_mult_fn(cfg.get("instrument", "USD_JPY"))
            _move_pips = abs(_price_move) * _pip_m
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
        if _base_mode != "scalp":
            with self._lock:
                _bias_snapshot = dict(self._15m_tactical_bias.get(instrument, {}))
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
        # ── TP固定 / SL技術的位置ベース ──
        # TPは技術的ターゲット（SR/Fib/BB等）で固定。
        # SLは①SR外側 ②ATRベース の優先順で決定。
        # 技術的に意味のある位置にSLを置くことでノイズ耐性向上。
        # ── 例外: 1H Breakout (KSB/DMB) は戦略SL/TPを完全保存 ──
        # ══════════════════════════════════════════════════════════════
        _1H_PRESERVE_SLTP = {"keltner_squeeze_breakout", "donchian_momentum_breakout", "rnb_support_bounce"}

        tp = sig.get("tp", 0)  # シグナル関数が算出した技術的ターゲット（固定）

        tp_dist = abs(tp - current_price) * _mtf_tp_bonus  # MTF順方向時にTP拡大
        if tp_dist <= 0:
            return  # TPが無効（0または現在価格と同一）→ エントリー見送り
        if _mtf_tp_bonus > 1.0:
            if signal == "BUY":
                tp = current_price + tp_dist
            else:
                tp = current_price - tp_dist

        _base_mode = _get_base_mode(mode)  # scalp_eur/scalp_eurjpy -> scalp
        _is_jpy = "JPY" in instrument
        _price_dec = 3 if _is_jpy else 5
        _atr = sig.get("atr", 0.07 if _is_jpy else 0.00070)
        _sl_margin = _atr * 0.3  # SR外側バッファ

        # ── 1H Breakout SL/TP完全保存 ──
        # KSB/DMBはスクイーズ中swing HL / ドンチアン中央から精密にSLを算出済み
        # SR/ATRベース再計算では戦略の意図が破壊されるため、直接使用
        if entry_type in _1H_PRESERVE_SLTP:
            _sig_sl = sig.get("sl", 0)
            if _sig_sl > 0:
                sl = round(_sig_sl, _price_dec)
                sl_dist = abs(current_price - sl)
                if sl_dist <= 0:
                    return  # SL無効
                # RR検証
                if tp_dist / sl_dist < 1.2:
                    return  # RR不足
                # SL狩り対策は適用（セッション遷移ワイドニング等）
                # → 下の SL狩り対策②セクションに進む
            else:
                return  # SLが算出されていない

        # ── SL候補①②: SR/ATRベース（非1H Breakoutモード用）──
        if entry_type not in _1H_PRESERVE_SLTP:
            sr_map = sig.get("sr_entry_map", {})
            _sr_sl = None
            if signal == "BUY":
                _ns = sr_map.get("nearest_support")
                if _ns and _ns.get("price", 0) > 0:
                    _sr_sl = _ns["price"] - _sl_margin
            else:
                _nr = sr_map.get("nearest_resistance")
                if _nr and _nr.get("price", 0) > 0:
                    _sr_sl = _nr["price"] + _sl_margin

            # ── SL候補②: ATRベース（SRがない場合のフォールバック）──
            _atr_mult = {"scalp": 0.8, "daytrade": 1.0, "swing": 1.5}.get(_base_mode, 0.8)
            if signal == "BUY":
                _atr_sl = current_price - _atr * _atr_mult
            else:
                _atr_sl = current_price + _atr * _atr_mult

            # ── SL選択: SR優先、RR >= 1.0 保証 ──
            if _sr_sl is not None:
                _sr_sl_dist = abs(current_price - _sr_sl)
                _sr_rr = tp_dist / max(_sr_sl_dist, 1e-8)
                if _sr_rr >= 1.0:
                    sl = round(_sr_sl, _price_dec)
                    sl_dist = _sr_sl_dist
                else:
                    sl = round(_atr_sl, _price_dec)
                    sl_dist = abs(current_price - _atr_sl)
            else:
                sl = round(_atr_sl, _price_dec)
                sl_dist = abs(current_price - _atr_sl)

            # 最低SL距離保証
            if _is_jpy:
                MIN_SL_DIST = {"scalp": 0.030, "daytrade": 0.050, "swing": 0.100}.get(_base_mode, 0.030)
            else:
                MIN_SL_DIST = {"scalp": 0.00030, "daytrade": 0.00050, "swing": 0.00100}.get(_base_mode, 0.00030)
            if sl_dist < MIN_SL_DIST:
                sl_dist = MIN_SL_DIST
                if signal == "BUY":
                    sl = round(current_price - sl_dist, _price_dec)
                else:
                    sl = round(current_price + sl_dist, _price_dec)

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策②: セッション遷移時SLワイドニング ──
        # 本番実績: UTC 18-20h(NY Close), 0-1h(東京早朝)にSL集中(48%)
        # 低流動性時間帯はスプレッド拡大+機関スパイクが多いためSLを拡大
        # ══════════════════════════════════════════════════════════════
        _utc_h = datetime.now(timezone.utc).hour
        _low_liq_hours = {0, 1, 18, 19, 20, 21}  # NY Close + 東京早朝
        if _utc_h in _low_liq_hours:
            _liq_buffer = _atr * 0.2  # ATR×0.2追加バッファ
            sl_dist += _liq_buffer
            if signal == "BUY":
                sl = round(current_price - sl_dist, _price_dec)
            else:
                sl = round(current_price + sl_dist, _price_dec)

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策③: Fast-SL適応防御 ──
        # 本番実績: 33%のSLが2分以内に到達（典型的SL狩りパターン）
        # 直近5分以内に同通貨ペアでfast SL(<120s)が発生 → SLを拡大
        # ══════════════════════════════════════════════════════════════
        _fast_sl_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        _recent_fast_sl = [h for h in self._sl_hit_history
                          if h[0] > _fast_sl_cutoff
                          and h[1] == instrument
                          and h[3] < 120]  # hold_sec < 120s = fast SL
        if _recent_fast_sl:
            _hunt_buffer = _atr * 0.3  # ATR×0.3追加（SL狩りスパイク回避）
            sl_dist += _hunt_buffer
            if signal == "BUY":
                sl = round(current_price - sl_dist, _price_dec)
            else:
                sl = round(current_price + sl_dist, _price_dec)

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策④: 平均回帰戦略のカウンタートレンドSLバッファ ──
        # 本番実績: bb_rsi SELL in bull l1 → 10/15 SL (67%)
        # 平均回帰がトレンド逆行する場合、SLを拡大して一時的逆行を吸収
        # ══════════════════════════════════════════════════════════════
        _mean_rev_types = {"bb_rsi_reversion", "macdh_reversal", "v_reversal",
                          "trend_rebound", "fib_reversal"}
        layer1_dir_pre = sig.get("layer_status", {}).get("layer1", {})
        _l1_dir = layer1_dir_pre.get("direction", "neutral") if isinstance(layer1_dir_pre, dict) else "neutral"
        _is_counter_trend = (
            entry_type in _mean_rev_types
            and ((_l1_dir == "bull" and signal == "SELL")
                 or (_l1_dir == "bear" and signal == "BUY"))
        )
        if _is_counter_trend:
            _ct_buffer = _atr * 0.25  # ATR×0.25追加（カウンタートレンド吸収）
            sl_dist += _ct_buffer
            if signal == "BUY":
                sl = round(current_price - sl_dist, _price_dec)
            else:
                sl = round(current_price + sl_dist, _price_dec)

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策B1: ラウンドナンバー回避 ──
        # 機関はXX.000, XX.500, XX.050等のSLクラスターを狙う
        # SLがラウンドナンバー近傍(2pip以内)なら外側にずらす
        # ══════════════════════════════════════════════════════════════
        if _is_jpy:
            _sl_frac = sl % 0.500  # 50銭刻みからの距離
            if _sl_frac < 0.020 or _sl_frac > 0.480:  # 2pip以内
                _nudge = 0.025  # 2.5pip外側
                if signal == "BUY":
                    sl = round(sl - _nudge, _price_dec)
                else:
                    sl = round(sl + _nudge, _price_dec)
                sl_dist = abs(current_price - sl)
        else:
            _sl_frac_5 = round((sl * 10000) % 50, 1)  # 50pips刻みからの距離
            if _sl_frac_5 < 2 or _sl_frac_5 > 48:  # 2pip以内
                _nudge = 0.00025  # 2.5pip外側
                if signal == "BUY":
                    sl = round(sl - _nudge, _price_dec)
                else:
                    sl = round(sl + _nudge, _price_dec)
                sl_dist = abs(current_price - sl)

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策F1: SLクラスタ回避 ──
        # 新規SLが既存オープンポジションのSLと2pip以内 → カスケードリスク
        # ══════════════════════════════════════════════════════════════
        _sl_cluster_thresh = 0.020 if _is_jpy else 0.00020  # 2pip
        _open_for_cluster = self._db.get_open_trades()
        _sl_clustered = False
        for _ot in _open_for_cluster:
            _ot_sl = _ot.get("sl", 0)
            _ot_inst = _ot.get("instrument", "USD_JPY")
            if _ot_inst == instrument and abs(sl - _ot_sl) < _sl_cluster_thresh:
                _block(f"sl_cluster(new={sl:.3f},exist={_ot_sl:.3f})")
                return

        # RR不足チェック（SL調整後に再判定）
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

        # ══════════════════════════════════════════════════════════════
        # ── P0監視: スリッページ・スプレッド・COOLDOWN記録 ──
        # ══════════════════════════════════════════════════════════════
        _signal_price = sig.get("entry", 0)  # シグナル関数のmid価格
        _pip_m_mon = 100 if _is_jpy else 10000
        _slippage = round((current_price - _signal_price) * _pip_m_mon, 2) if _signal_price else 0
        if signal == "SELL":
            _slippage = -_slippage  # SELL: bid<mid → 負のスリッページが正常
        # スプレッド（既にfetch済みの_ba変数を再利用）
        _spread_entry = 0.0
        try:
            if _ba:
                _spread_entry = round((_ba["ask"] - _ba["bid"]) * _pip_m_mon, 2)
        except Exception:
            pass
        # COOLDOWN経過時間
        _cd_elapsed = 0.0
        _last_ex = self._last_exit.get(mode)
        if _last_ex:
            _cd_elapsed = round((datetime.now(timezone.utc) - _last_ex["time"]).total_seconds(), 1)

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
            instrument=instrument,
            signal_price=_signal_price,
            spread_at_entry=_spread_entry,
            slippage_pips=_slippage,
            cooldown_elapsed=_cd_elapsed,
        )

        # ── 動的ロットサイジング: 2軸制御 (SL距離 + ATR/Spread) ──
        # Axis 1: SL距離連動 — リスク額正規化 (既存)
        # Axis 2: ATR/Spread比 — エッジ品質に応じた加速/減速 (新規)
        import os as _os
        _cfg_lot = MODE_CONFIG.get(mode, {})
        _base_sl_pips = _cfg_lot.get("base_sl_pips", 3.5)
        _pip_m_d1 = 100 if _is_jpy else 10000
        _actual_sl_pips = sl_dist * _pip_m_d1

        # Axis 1: SL距離連動
        _sl_ratio = min(_base_sl_pips / max(_actual_sl_pips, 0.5), 1.5)
        _sl_ratio = max(_sl_ratio, 0.5)

        # Axis 2: ATR/Spread比 (Edge Quality)
        _atr_val = sig.get("atr", 0.07 if _is_jpy else 0.00070)
        _atr_pips = _atr_val * _pip_m_d1
        _spread_pips = _spread_entry if _spread_entry > 0 else (0.4 if _is_jpy else 0.4)  # already in pips
        _edge_ratio = _atr_pips / max(_spread_pips, 0.1)

        if _edge_ratio >= 15:
            _vol_mult = 1.5    # 最強エッジ (USD/JPY scalp typical)
        elif _edge_ratio >= 10:
            _vol_mult = 1.3
        elif _edge_ratio >= 6:
            _vol_mult = 1.0    # 中立
        elif _edge_ratio >= 3:
            _vol_mult = 0.7
        else:
            _vol_mult = 0.5    # 最弱 (スプレッド負けリスク)

        _lot_ratio = _sl_ratio * _vol_mult
        _lot_ratio = max(0.3, min(_lot_ratio, 2.0))

        _base_units = int(_os.environ.get("OANDA_UNITS", "10000"))
        _adjusted_units = int(_base_units * _lot_ratio)
        _adjusted_units = max(1000, (_adjusted_units // 1000) * 1000)

        # ── OANDA連携: 昇格済み戦略のみミラーリング ──
        if self._is_promoted(entry_type):
            self._oanda.open_trade(
                demo_trade_id=trade_id,
                direction=signal,
                sl=sl, tp=tp,
                mode=mode,
                instrument=instrument,
                callback=lambda did, oid: self._db.set_oanda_trade_id(did, oid),
                units=_adjusted_units,
            )
        else:
            _promo = self._promoted_types.get(entry_type, {})
            _promo_n = _promo.get("n", 0)
            self._add_log(
                f"   ⏳ OANDA未連携（{entry_type}: N={_promo_n}/30, "
                f"status={_promo.get('status', 'pending')}）"
            )

        # エントリー理由の要約（✅マーク付きの理由を抽出）
        _confirmed_reasons = [r for r in reasons if "✅" in r]
        _reason_summary = " / ".join(_confirmed_reasons[:3]) if _confirmed_reasons else entry_type

        from modules.demo_db import pip_multiplier as _pm
        _pip_m = _pm(instrument)
        rr_actual = round(tp_dist / sl_dist, 1) if sl_dist > 0 else 0
        self._add_log(
            f"{cfg['icon']} 📥 IN [{cfg['label']}]: {signal} @ {current_price:.{_price_dec}f} | "
            f"SL {sl:.{_price_dec}f}({sl_dist*_pip_m:.1f}p) TP {tp:.{_price_dec}f}({tp_dist*_pip_m:.1f}p) RR1:{rr_actual} | "
            f"Type: {entry_type} | Conf: {confidence}% | "
            f"理由: {_reason_summary} | ID: {trade_id} | "
            f"📊 slip={_slippage:+.2f}p spread={_spread_entry:.1f}p CD={_cd_elapsed:.0f}s"
        )

    def _generate_close_analysis(self, trade: dict, close_reason: str,
                                  pnl_pips: float, outcome: str) -> str:
        """Generate concise win/loss analysis text for trade close."""
        parts = []
        entry_type = trade.get("entry_type", "")
        direction = trade.get("direction", "")
        instrument = trade.get("instrument", "USD_JPY")
        spread_entry = trade.get("spread_at_entry", 0) or 0
        sl = trade.get("sl", 0) or 0
        entry_price = trade.get("entry_price", 0) or 0

        _reasons_raw = trade.get("reasons", [])
        if isinstance(_reasons_raw, str):
            try:
                _reasons_raw = json.loads(_reasons_raw)
            except Exception:
                _reasons_raw = []
        _clean = [r.replace("✅ ", "").replace("✅", "")
                  for r in _reasons_raw
                  if isinstance(r, str) and not r.startswith("__")]

        _smc = entry_type in {"turtle_soup", "trendline_sweep",
                               "inducement_ob", "post_news_vol"}

        if outcome == "WIN":
            if close_reason == "TP_HIT":
                parts.append("TP到達")
            elif close_reason == "SIGNAL_REVERSE":
                parts.append("反転利確")
            elif close_reason == "TIME_DECAY_EXIT":
                parts.append("時間利確")
            else:
                parts.append(close_reason)
            if _smc:
                parts.append("SMC完全反発")
            if _clean:
                parts.append(",".join(_clean[:3]))
        elif outcome == "LOSS":
            if close_reason == "SL_HIT":
                _pip_m = 100 if "JPY" in instrument else 10000
                _sl_dist = abs(entry_price - sl) * _pip_m if sl and entry_price else 999
                if spread_entry > 0 and _sl_dist > 0 and spread_entry / _sl_dist > 0.3:
                    parts.append(f"spread負け({spread_entry:.1f}p)")
                else:
                    parts.append("逆行SL")
            elif close_reason == "SIGNAL_REVERSE":
                parts.append("反転損切")
            elif close_reason == "TIME_DECAY_EXIT":
                parts.append("時間減衰")
            elif close_reason == "SCENARIO_INVALID":
                parts.append("シナリオ崩壊")
            elif close_reason == "WEEKEND_CLOSE":
                parts.append("週末CL")
            elif close_reason == "MAX_HOLD_TIME":
                parts.append("MAX保持")
            else:
                parts.append(close_reason)
            if _clean:
                parts.append(",".join(_clean[:2]))
        else:
            parts.append(f"BE({close_reason})")

        return " | ".join(parts)

    def _check_signal_reverse(self, trade: dict, current_price: float,
                               new_signal: str, new_conf: int, mode: str):
        """シグナル反転によるクローズ判定のみ（SL/TPは _sltp_loop が処理）"""
        cfg = MODE_CONFIG.get(mode, {})
        direction = trade["direction"]
        trade_id = trade["trade_id"]
        _instrument_sr = cfg.get("instrument", "USD_JPY")
        _price_fmt = ".3f" if "JPY" in _instrument_sr else ".5f"

        # 最低保持時間チェック（scalp:3分, daytrade:10分, swing:1時間）
        _base_mode_sr = _get_base_mode(mode)
        min_hold_sec = {"scalp": 180, "daytrade": 600, "daytrade_1h": 1800, "swing": 3600}.get(_base_mode_sr, 180)
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
            # ── 決済価格もbid/ask反映 ──
            # BUYポジ決済=売り(bid), SELLポジ決済=買い(ask)
            _close_price = current_price
            try:
                from modules.data import fetch_oanda_bid_ask
                _inst_sr = cfg.get("instrument", "USD_JPY")
                _ba_sr = fetch_oanda_bid_ask(_inst_sr)
                if _ba_sr:
                    _close_price = _ba_sr["bid"] if direction == "BUY" else _ba_sr["ask"]
            except Exception:
                pass

            result = self._db.close_trade(trade_id, _close_price, close_reason)
            if "error" in result:
                return  # 別スレッドで既にクローズ済み → スキップ

            # ── 決済分析生成・保存 ──
            try:
                _ca = self._generate_close_analysis(
                    trade, close_reason,
                    result.get("pnl_pips", 0), result.get("outcome", ""))
                self._db.update_close_analysis(trade_id, _ca)
            except Exception:
                pass

            # ── OANDA連携: ポジションクローズ ──
            self._oanda.close_trade(trade_id, reason=close_reason)

            pnl = result.get("pnl_pips", 0)
            outcome = result.get("outcome", "?")
            icon = "✅" if outcome == "WIN" else "❌"

            self._add_log(
                f"{cfg.get('icon','')} 📤 OUT [{cfg.get('label','?')}]: {icon} {outcome} | "
                f"{direction} @ {trade['entry_price']:{_price_fmt}} → {_close_price:{_price_fmt}} | "
                f"PnL: {pnl:+.1f} pips | "
                f"Reason: {close_reason} | ID: {trade_id}"
            )

            # ── クールダウン記録（WINは除外）──
            if outcome != "WIN":
                self._last_exit[mode] = {
                    "price": trade["entry_price"],
                    "exit_price": _close_price,
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

        # 学習完了後に戦略昇格を再評価
        self._evaluate_promotions()

    def _evaluate_promotions(self):
        """デモ実績に基づいて戦略をOANDA昇格/降格判定
        ファストトラック: N≥20 かつ WR≥60% かつ EV≥1.0 → 昇格
        通常トラック:    N≥30 かつ EV>0 → 昇格
        降格:           N≥30 かつ EV<-0.5 → 降格
        NOTE: 旧エリートトラック(N≥3)は統計的に不十分なため廃止
              (2026-04-05 audit fix: N=3で本番昇格は危険)
        """
        from modules.learning_engine import SMC_PROTECTED
        try:
            data = self._db.get_trades_for_learning(min_trades=1)
            if not data.get("ready"):
                return
            by_type = data.get("by_type", {})
            changes = []
            for et, stats in by_type.items():
                n = stats.get("n", 0)
                ev = stats.get("ev", 0)
                wr = stats.get("wr", 0)
                old = self._promoted_types.get(et, {}).get("status", "pending")
                # ファストトラック: 十分なサンプル+高WR+高EV
                if n >= 20 and wr >= 60.0 and ev >= 1.0:
                    status = "promoted"
                # 通常トラック: 十分なサンプルでEVプラス
                elif n >= 30 and ev >= 0.0:
                    status = "promoted"
                # 降格: 十分なサンプルでEV大幅マイナス (SMC保護戦略は降格禁止)
                elif n >= 30 and ev < -0.5 and et not in SMC_PROTECTED:
                    status = "demoted"
                else:
                    status = "pending"
                self._promoted_types[et] = {"status": status, "n": n, "wr": wr, "ev": ev}
                if old != status:
                    changes.append(f"{et}: {old}→{status} (N={n} WR={wr}% EV={ev:+.2f})")
            if changes:
                self._add_log(f"🎯 戦略昇格更新: {', '.join(changes[:5])}")
        except Exception as e:
            print(f"[Promotion] error: {e}", flush=True)

    def _get_strategy_status_cached(self) -> list:
        """キャッシュ付き戦略ステータス（60秒TTL）。
        Engine instantiationが重いため毎秒呼び出しを回避。"""
        _now = time.time()
        _cache = getattr(self, '_strategy_status_cache', None)
        _cache_ts = getattr(self, '_strategy_status_cache_ts', 0)
        if _cache is not None and (_now - _cache_ts) < 60:
            return _cache
        result = self._get_strategy_status()
        self._strategy_status_cache = result
        self._strategy_status_cache_ts = _now
        return result

    def _get_strategy_status(self) -> list:
        """全戦略の稼働状況・SMC保護状態・昇格状態を返す。
        フロントエンドの戦略ダッシュボード表示用。
        """
        from modules.learning_engine import SMC_PROTECTED
        from strategies.daytrade import DaytradeEngine
        from strategies.scalp import ScalperEngine

        status_list = []

        # DayTrade strategies
        try:
            dt_engine = DaytradeEngine()
            for s in dt_engine.strategies:
                promo = self._promoted_types.get(s.name, {})
                blacklisted = (s.name in self._params.get("entry_type_blacklist", []))
                status_list.append({
                    "name": s.name,
                    "category": "daytrade",
                    "enabled": s.enabled,
                    "smc_protected": s.name in SMC_PROTECTED,
                    "promotion": promo.get("status", "pending"),
                    "promo_n": promo.get("n", 0),
                    "promo_wr": promo.get("wr", 0),
                    "promo_ev": promo.get("ev", 0),
                    "blacklisted": blacklisted,
                })
        except Exception as e:
            print(f"[StrategyStatus] DT error: {e}", flush=True)

        # Scalp strategies
        try:
            sc_engine = ScalperEngine()
            for s in sc_engine.strategies:
                promo = self._promoted_types.get(s.name, {})
                blacklisted = (s.name in self._params.get("entry_type_blacklist", []))
                status_list.append({
                    "name": s.name,
                    "category": "scalp",
                    "enabled": s.enabled,
                    "smc_protected": s.name in SMC_PROTECTED,
                    "promotion": promo.get("status", "pending"),
                    "promo_n": promo.get("n", 0),
                    "promo_wr": promo.get("wr", 0),
                    "promo_ev": promo.get("ev", 0),
                    "blacklisted": blacklisted,
                })
        except Exception as e:
            print(f"[StrategyStatus] Scalp error: {e}", flush=True)

        # 1H strategies (HourlyEngine)
        try:
            from strategies.hourly import HourlyEngine
            h_engine = HourlyEngine()
            for s in h_engine.strategies:
                promo = self._promoted_types.get(s.name, {})
                status_list.append({
                    "name": s.name,
                    "category": "1h",
                    "enabled": s.enabled,
                    "smc_protected": s.name in SMC_PROTECTED,
                    "promotion": promo.get("status", "pending"),
                    "promo_n": promo.get("n", 0),
                    "promo_wr": promo.get("wr", 0),
                    "promo_ev": promo.get("ev", 0),
                    "blacklisted": False,
                })
        except Exception as e:
            print(f"[StrategyStatus] 1H error: {e}", flush=True)

        return status_list

    def _is_promoted(self, entry_type: str) -> bool:
        """戦略がOANDA実行可能か判定
        NOTE: 一時的に全戦略をOANDA送信（フィルター解除中）
        """
        return True  # 一時的に全戦略をOANDA送信
        # --- 元のロジック（復元時にコメント解除）---
        # info = self._promoted_types.get(entry_type)
        # if not info:
        #     return False  # 未評価 = デモのみ
        # return info["status"] == "promoted"

    def _apply_adjustments(self, adjustments: list):
        """学習エンジンの調整を適用。
        NOTE: sl_adjust/tp_adjust/session_blacklist は廃止済み (2026-04-05 audit)
              SMC戦略はSMC_PROTECTEDで保護されブラックリスト化不可。
        """
        for adj in adjustments:
            p = adj["param"]
            if p == "confidence_threshold":
                self._params["confidence_threshold"] = int(adj["new"])
            elif p == "entry_type_blacklist_add":
                et = adj["reason"].split(":")[0].strip()
                if et not in self._params["entry_type_blacklist"]:
                    self._params["entry_type_blacklist"].append(et)
            elif p == "entry_type_blacklist_remove":
                et = adj["reason"].split(":")[0].strip()
                if et in self._params["entry_type_blacklist"]:
                    self._params["entry_type_blacklist"].remove(et)

    def _add_log(self, msg: str):
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")
        try:
            self._db.add_log(ts, msg)
        except Exception:
            pass
        print(f"[DemoTrader] {msg}")
