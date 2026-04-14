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
import os as _os
from datetime import datetime, timezone, timedelta

from modules.demo_db import DemoDB
from modules.learning_engine import LearningEngine
from modules.daily_review import DailyReviewEngine
from modules.oanda_bridge import OandaBridge
from modules.exposure_manager import ExposureManager
from modules.alert_manager import AlertManager
from modules.risk_analytics import get_dd_lot_multiplier, DD_LOT_TIERS

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
        "active_hours_utc": (7, 17),  # v7.0: London+NY (07-09 London WR=60%+, 13-15 NY peak volume). Asia除外(WR<20%). Spread/SL Gate(v7.0)でFast Exit防止
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
        "auto_start": False,  # v8.6: 停止 — BT friction/ATR=43.6%, PF=0.649 構造的に不可能
        "base_sl_pips": 3.5,
        "active_hours_utc": (0, 15),
    },
    # ── USD/JPY Scalp 5m — v6.8 Sentinel A/Bテスト ──
    # 1mスキャルプと並行稼働。5m足のノイズ削減(49.8%→3.4%)とSpread/ATR改善(13.8%→5.2%)を本番検証
    # BT: 164t WR=65.9% EV=+0.195 Sharpe=+0.138 (30d, 1m比 EV +0.347 改善)
    # OANDA遮断 (Sentinel) → N≥50後に1m vs 5m本番データ比較で移行判断
    "scalp_5m": {
        "interval_sec": 30,       # 5m足に合わせた間隔 (1mの10sから緩和)
        "tf": "5m",
        "period": "5d",           # EMA200確保 (200本×5m=16.7h → 5d十分)
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルプ5m",
        "icon": "⚡5️⃣",
        "symbol": "USDJPY=X",
        "instrument": "USD_JPY",
        "auto_start": True,
        "base_sl_pips": 5.0,      # 5m ATR≈5.8pip → SL余裕確保
    },
    # ── v8.6: EUR_USD Scalp 5m — 1m→5m移行（摩擦/ATR 30.6%→10-12%に改善）──
    # BT根拠: 5m USD_JPY 164t WR=65.9% EV=+0.195 (1m比 +0.347改善)
    # EUR_USDは1m bb_rsi EV=+0.943の唯一の正EVペア → 5m移行で摩擦改善しつつエッジ維持
    "scalp_5m_eur": {
        "interval_sec": 30,
        "tf": "5m",
        "period": "5d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルプ5m EUR",
        "icon": "⚡5️⃣🇪🇺",
        "symbol": "EURUSD=X",
        "instrument": "EUR_USD",
        "auto_start": True,
        "base_sl_pips": 3.5,
    },
    # ── v8.6: GBP_USD Scalp 5m — 1mのPF=0.447を5mで改善（摩擦/ATR 48.7%→15-18%）──
    "scalp_5m_gbp": {
        "interval_sec": 30,
        "tf": "5m",
        "period": "5d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルプ5m GBP",
        "icon": "⚡5️⃣🇬🇧",
        "symbol": "GBPUSD=X",
        "instrument": "GBP_USD",
        "auto_start": True,
        "base_sl_pips": 5.0,
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
    # ── EUR/GBP Daytrade (15m) — eurgbp_daily_mr 専用 ──
    # v6.6 全停止 → v6.7 日足MR戦略のみ再有効化 (Sentinel, 0.01lot)
    # 15m足で20日レンジ極値フェード (発火頻度: 2-4回/月)
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
    # ── XAU/USD Scalp (1m) — gold_pips_hunter + vol_momentum + ema_ribbon ──
    # pip=0.01 (JPYスケール), OANDA XAU_USD
    # 稼働時間: UTC 0-12 (Tokyo+London, gold_pips_hunter のセッションフィルター準拠)
    "scalp_xau": {
        "interval_sec": 10,
        "tf": "1m",
        "period": "1d",
        "signal_fn": "compute_scalp_signal",
        "label": "スキャルプXAU",
        "icon": "⚡🥇",
        "symbol": "XAUUSD=X",
        "instrument": "XAU_USD",
        "auto_start": False,       # v8.4: XAU停止 — post-cutoff損失の102%がXAU由来。FXのみで+96.8pip黒字
        "base_sl_pips": 50,        # Gold 1m ATR ≈ 30-80 pips (0.01 scale)
        "active_hours_utc": (0, 16),  # UTC 0-15 (Tokyo+London+NY_Overlap)
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
        "auto_start": False,       # v8.4: XAU停止 — post-cutoff XAU損失 -2,280pip (FXは+96.8pip黒字)
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
        # v6.2 fix: N-cache を _evaluate_promotions() の前に復元
        # → _evaluate_promotions() が DB集計で権威あるデータに上書き
        try:
            _n_str = self._db.get_system_kv("strategy_n_cache", "{}")
            self._strategy_n_cache = json.loads(_n_str)
            if self._strategy_n_cache:
                print(f"[v6.2] N-cache warm-start: {len(self._strategy_n_cache)} strategies", flush=True)
        except Exception:
            self._strategy_n_cache = {}
        self._evaluate_promotions()  # 起動時に評価 → _strategy_n_cache を DB集計で上書き

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
        self._last_learning_ts = 0.0  # epoch — dedup guard for _trigger_learning
        self._last_signals = {}   # mode -> last signal dict
        # 連敗トラッカー: mode -> {"direction": str, "count": int}
        self._consec_losses = {}  # mode -> {dir -> consecutive_loss_count}
        # SL後クールダウン: mode -> {"price": float, "time": datetime, "direction": str}
        self._last_exit = {}      # mode -> last exit info
        # ── リバウンド対策: 全方向連敗トラッカー + 価格ベロシティ ──
        self._total_losses_window = []  # [(timestamp, mode, pips)] 直近の全損失記録
        self._price_history = {}        # {instrument: [(timestamp, price)]} 通貨ペア別価格推移

        # ── Equity Curve Protector: 段階的DDロット縮小 v7.0 ──
        # v7.0: binary ON/OFF -> graduated reduction (risk_analytics.DD_LOT_TIERS)
        #   DD >= 2%: lot * 0.80 | DD >= 4%: lot * 0.60
        #   DD >= 6%: lot * 0.40 | DD >= 8%: lot * 0.20
        #   Recovery uses same thresholds (no instant full-open)
        self._EQ_BASE_CAPITAL_PIPS = 1000.0  # 基準資本 (pips換算、DDパーセント計算用)

        # ── v8.9: Equity Reset — クリーンデータ起点 ──
        # v8.4以前のXAU損失(-2,280pip)+pre-cutoffバグデータが永久にDDを汚染していた。
        # v8.4(XAU停止+Shadow除去)以降のFX-onlyデータからequityを再計算する。
        # v8.9c: 毒性ブロック+is_shadow修正デプロイ後のクリーンデータ起点
        # 4/10-4/13 15:00: FORCE_DEMOTED戦略がshadow=0で走りDD計算を汚染
        # 4/13 15:00以降: 毒性ブロック5件+is_shadow修正+EUR_USD SELLブロック適用済み
        _EQ_RESET_CUTOFF = "2026-04-13T15:00:00"
        _eq_reset_flag = "eq_reset_v89c"
        _eq_reset_done = self._db.get_system_kv(_eq_reset_flag, "0")
        if _eq_reset_done != "1":
            try:
                _all_trades = self._db.get_all_closed()
                _eq_r = 0.0
                _eq_r_peak = 0.0
                for _t in _all_trades:
                    _et = _t.get("entry_time", "") or _t.get("created_at", "") or ""
                    if _et < _EQ_RESET_CUTOFF:
                        continue
                    if _t.get("is_shadow", 0) == 1:
                        continue
                    _inst = _t.get("instrument", "")
                    if "XAU" in _inst:
                        continue
                    _pnl = float(_t.get("pnl_pips", 0) or 0)
                    _eq_r += _pnl
                    if _eq_r > _eq_r_peak:
                        _eq_r_peak = _eq_r
                _dd_r = _eq_r_peak - _eq_r
                _dd_r_pct = _dd_r / max(self._EQ_BASE_CAPITAL_PIPS, 1.0)
                _new_mult = get_dd_lot_multiplier(_dd_r_pct)
                self._eq_peak = _eq_r_peak
                self._eq_current = _eq_r
                self._dd_lot_mult = _new_mult
                self._defensive_mode = _new_mult < 1.0
                self._db.set_system_kv("eq_peak", str(round(self._eq_peak, 2)))
                self._db.set_system_kv("eq_current", str(round(self._eq_current, 2)))
                self._db.set_system_kv("dd_lot_mult", str(round(self._dd_lot_mult, 2)))
                self._db.set_system_kv("defensive_mode", "1" if self._defensive_mode else "0")
                self._db.set_system_kv(_eq_reset_flag, "1")
                print(f"[v8.9b] EquityReset: Recalculated from {_EQ_RESET_CUTOFF} "
                      f"(FX-only, non-shadow). peak={self._eq_peak:.1f} "
                      f"current={self._eq_current:.1f} DD={_dd_r_pct:.1%} "
                      f"lot_mult={self._dd_lot_mult}", flush=True)
            except Exception as e:
                print(f"[v8.9] EquityReset failed, falling back to DB restore: {e}",
                      flush=True)
                self._eq_peak = 0.0
                self._eq_current = 0.0
                self._defensive_mode = False
                self._dd_lot_mult = 1.0
        else:
            # Normal restore path (post-reset)
            try:
                self._eq_peak = float(self._db.get_system_kv("eq_peak", "0.0"))
                self._eq_current = float(self._db.get_system_kv("eq_current", "0.0"))
                self._defensive_mode = self._db.get_system_kv("defensive_mode", "0") == "1"
                self._dd_lot_mult = float(self._db.get_system_kv("dd_lot_mult", "1.0"))
                if self._eq_peak != 0 or self._eq_current != 0:
                    _dd = self._eq_peak - self._eq_current
                    _dd_pct = _dd / max(self._EQ_BASE_CAPITAL_PIPS, 1.0)
                    print(f"[v7.0] EquityProtector restored: peak={self._eq_peak:.1f} "
                          f"current={self._eq_current:.1f} DD={_dd_pct:.1%} "
                          f"lot_mult={self._dd_lot_mult}", flush=True)
            except Exception as e:
                self._eq_peak = 0.0
                self._eq_current = 0.0
                self._defensive_mode = False
                self._dd_lot_mult = 1.0
                print(f"[v7.0] EquityProtector DB restore failed, defaults: {e}",
                      flush=True)
        self._trade_high_water = {}     # trade_id -> max favorable price（BE/トレーリング用）
        # ── MAFE (Max Adverse / Favorable Excursion) ──
        self._mafe_tracker = {}         # {trade_id: {"max_high": float, "min_low": float}}
        # ── 建値ガード用: エントリー時ATR保存 ──
        self._entry_atr = {}            # {trade_id: atr_value (raw price units)}
        # ── SL狩り対策: クロス戦略カスケード防御 + Fast-SL検出 ──
        self._sl_hit_history = []       # [(timestamp, instrument, entry_type, hold_sec)] SL_HIT履歴
        # ── MTF連携: 15m DT → 1m Scalp 戦略バイアス（通貨ペア別）──
        self._15m_tactical_bias = {}  # {instrument: {direction, entry_type, ...}}
        # ── Confluence Scalp v2: MSS追跡 + Profit Extender ──
        self._mss_tracker = {}        # {trade_id: {"choch": dict|None, "msb": bool, "adx": float, "updated": datetime}}
        self._profit_extended = set() # Set of trade_ids that have been profit-extended (TP延伸済み)
        self._pyramided_trades = set()  # v6.4: 追加ポジション済みtrade_ids
        self._entry_adx = {}            # v6.4: {trade_id: adx at entry}
        # ── v6.5: Cross-pair Exposure Manager ──
        self._exposure_mgr = ExposureManager()
        # ── v6.5: External Alerting (Discord Webhook) ──
        self._alert_mgr = AlertManager()
        if self._alert_mgr.is_enabled:
            print("[v6.5] AlertManager: Discord Webhook enabled", flush=True)
        # ── v6.5: DD Phase Tagging (デモDDブレーカー代替) ──
        self._dd_phase_at_entry = {}  # {trade_id: bool} DD期間中のエントリーか
        self._pending_limits = {}     # {key: {signal, sl, tp, entry_type, sig, limit_price, created, mode, cfg, ...}}
        # v6.2: N-cache は L244 の _evaluate_promotions() で DB集計から構築済み
        # (warm-start復元は L244 の前で実行、_evaluate_promotions() が上書き)
        # v6.1: GBP_USD Strict Friction Guard — 指値失効後クールダウン
        self._limit_expired_cd = {}   # {f"{inst}_{direction}": expiry_datetime}
        # 起動済みモード追跡（ヘルスチェッカー用）
        self._started_modes = set()
        self._user_stopped_modes = set()  # 明示的にstop()されたモード（ウォッチドッグ対象外）
        self._health_thread = None
        self._watchdog_thread = None
        self._last_request_tick = {}  # mode -> timestamp (リクエスト駆動tick用)
        # ── OANDA専用サーキットブレーカー (デモは制限なし) ──
        self._oanda_was_active = False  # 前回のOANDA active状態 (再開検出用)
        self._oanda_resume_ts = None    # OANDA最終再開時刻 (リミットリセット基準)
        # ── Emergency Kill Switch (persistent, survives watchdog/deploy) ──
        self._emergency_killed = self._db.get_system_kv("emergency_killed", "0") == "1"
        if self._emergency_killed:
            print("[EMERGENCY_KILL] System is in KILLED state — all trading suspended. "
                  "Use emergency_resume() to restart.", flush=True)

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
        if self._emergency_killed:
            return {"status": "blocked", "message": "Emergency kill is active. Use emergency_resume() first."}
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

    # ── Emergency Kill Switch ─────────────────────────

    def emergency_kill(self, reason: str = "Manual kill switch") -> dict:
        """Emergency full stop: stops ALL modes + closes ALL OANDA positions.

        Sets a persistent flag that prevents auto-restart by watchdog, self-healing,
        and auto-start. Requires explicit emergency_resume() to restart.
        """
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[EMERGENCY_KILL] ACTIVATED at {ts}: {reason}", flush=True)

        # 1. Set persistent kill flag (survives deploy/restart)
        self._emergency_killed = True
        self._db.set_system_kv("emergency_killed", "1")
        self._db.set_system_kv("emergency_kill_time", ts)
        self._db.set_system_kv("emergency_kill_reason", reason[:500])

        # 2. Stop ALL demo modes
        modes_stopped = []
        with self._lock:
            for m in list(self._runners.keys()):
                runner = self._runners.get(m, {})
                if runner.get("running"):
                    runner["running"] = False
                    self._user_stopped_modes.add(m)
                    modes_stopped.append(m)
            self._sltp_running = False

        # 3. Close ALL open OANDA positions
        oanda_closed = 0
        oanda_errors = 0
        if self._oanda.active:
            # Close via trade_map (known OANDA positions)
            trade_ids = list(self._oanda._trade_map.keys())
            for demo_id in trade_ids:
                try:
                    oanda_id = self._oanda._trade_map.get(demo_id)
                    if oanda_id:
                        ok, _ = self._oanda._client.close_trade(oanda_id)
                        if ok:
                            oanda_closed += 1
                            with self._oanda._lock:
                                self._oanda._trade_map.pop(demo_id, None)
                        else:
                            oanda_errors += 1
                except Exception as e:
                    oanda_errors += 1
                    print(f"[EMERGENCY_KILL] OANDA close error for {demo_id}: {e}", flush=True)

            # Also kill OANDA allowed modes
            self._oanda._allowed_modes = set()
            self._oanda._save_allowed_modes()

        # 4. Log the event
        self._add_log(
            f"🚨 [EMERGENCY_KILL] 全停止発動: {reason} | "
            f"モード停止: {len(modes_stopped)}件 | "
            f"OANDA決済: {oanda_closed}件 (エラー: {oanda_errors}件)")

        # 5. Discord alert
        self._alert_mgr.alert_custom(
            "EMERGENCY KILL ACTIVATED",
            f"Reason: {reason}\n"
            f"Modes stopped: {len(modes_stopped)}\n"
            f"OANDA closed: {oanda_closed} (errors: {oanda_errors})")

        return {
            "status": "killed",
            "timestamp": ts,
            "reason": reason,
            "modes_stopped": modes_stopped,
            "oanda_closed": oanda_closed,
            "oanda_errors": oanda_errors,
        }

    def emergency_resume(self, confirm: bool = False) -> dict:
        """Resume from emergency kill state. Requires confirm=True as safety check."""
        if not self._emergency_killed:
            return {"status": "not_killed", "message": "System is not in emergency kill state"}

        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Pass confirm=true to resume trading. "
                           "Kill reason: " + self._db.get_system_kv("emergency_kill_reason", "unknown"),
                "killed_at": self._db.get_system_kv("emergency_kill_time", "unknown"),
            }

        ts = datetime.now(timezone.utc).isoformat()
        print(f"[EMERGENCY_KILL] RESUMED at {ts}", flush=True)

        # Clear persistent kill flag
        self._emergency_killed = False
        self._db.set_system_kv("emergency_killed", "0")
        self._db.set_system_kv("emergency_resume_time", ts)

        # Clear user_stopped_modes so watchdog can restart
        self._user_stopped_modes.clear()

        # Restart all auto-start modes
        restarted = []
        for m, cfg in MODE_CONFIG.items():
            if cfg.get("auto_start", True):
                try:
                    result = self.start(mode=m)
                    if result.get("status") in ("started", "already_running"):
                        restarted.append(m)
                except Exception as e:
                    print(f"[EMERGENCY_KILL] Resume start {m} failed: {e}", flush=True)

        self._add_log(
            f"🟢 [EMERGENCY_KILL] 復旧完了: {len(restarted)}モード再起動 | "
            f"resume_time={ts}")

        self._alert_mgr.alert_custom(
            "EMERGENCY KILL RESUMED",
            f"Modes restarted: {len(restarted)} ({', '.join(restarted)})")

        return {
            "status": "resumed",
            "timestamp": ts,
            "modes_restarted": restarted,
        }

    def emergency_status(self) -> dict:
        """Return current emergency kill state."""
        return {
            "killed": self._emergency_killed,
            "kill_time": self._db.get_system_kv("emergency_kill_time", ""),
            "kill_reason": self._db.get_system_kv("emergency_kill_reason", ""),
            "resume_time": self._db.get_system_kv("emergency_resume_time", ""),
        }

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

            # ── Emergency Kill: skip ALL self-healing when killed ──
            if self._emergency_killed:
                pass  # No healing — system intentionally stopped
            else:
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
                    _pip_mult = 100 if (_inst in ("USD_JPY", "EUR_JPY", "GBP_JPY") or "XAU" in _inst) else 10000
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
            # ── ブロック理由カウント (2026-04-07: 発火拒否の可視化) ──
            "block_counts": dict(sorted(
                getattr(self, '_block_counts', {}).items(),
                key=lambda x: x[1], reverse=True
            )[:30]),  # 上位30件のみ (キー爆発防止)
            # ── Emergency Kill Switch status ──
            "emergency_killed": self._emergency_killed,
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

        # v8.9: 含み益検知は SLTPチェッカー(0.5秒)内に統合済み
        # 別スレッドの5分監視は不要 — 削除

    _PROFIT_MONITOR_INTERVAL = 300  # 5分
    _PROFIT_ALERT_THRESHOLD = 15.0  # pip
    _SHADOW_PROFIT_THRESHOLD = 8.0  # pip
    _last_profit_alert_ts = 0.0

    def _profit_monitor_loop(self):
        """v8.9: オープンポジションの含み益を5分毎に監視。
        大幅含み益やShadow含み益を検知してログ+Discord通知。"""
        import time
        time.sleep(60)  # 起動直後はスキップ
        while True:
            try:
                open_trades = self._db.get_open_trades()
                if not open_trades:
                    time.sleep(self._PROFIT_MONITOR_INTERVAL)
                    continue

                total_unreal = 0.0
                shadow_unreal = 0.0
                best_trade = None
                best_pnl = 0.0

                for t in open_trades:
                    pnl = float(t.get("unrealized_pips", 0) or 0)
                    total_unreal += pnl
                    if t.get("is_shadow", 0):
                        shadow_unreal += max(pnl, 0)
                    if pnl > best_pnl:
                        best_pnl = pnl
                        best_trade = t

                now = time.time()
                # 30分に1回以上は通知しない（スパム防止）
                if now - self._last_profit_alert_ts < 1800:
                    time.sleep(self._PROFIT_MONITOR_INTERVAL)
                    continue

                alerts = []
                if total_unreal > self._PROFIT_ALERT_THRESHOLD:
                    bt = best_trade or {}
                    alerts.append(
                        f"💰 含み益+{total_unreal:.1f}pip "
                        f"(Top: {bt.get('entry_type','?')}×{bt.get('instrument','?')} "
                        f"+{best_pnl:.1f}pip)"
                    )
                if shadow_unreal > self._SHADOW_PROFIT_THRESHOLD:
                    alerts.append(
                        f"⚠️ Shadow含み益+{shadow_unreal:.1f}pip — OANDA未送信"
                    )

                if alerts:
                    self._last_profit_alert_ts = now
                    for a in alerts:
                        self._add_log(f"[PROFIT-MONITOR] {a}")
                    # Discord送信（webhook設定がある場合）
                    try:
                        import os, urllib.request, json as _json
                        webhook = os.environ.get("DISCORD_WEBHOOK_URL")
                        if webhook:
                            msg = "📊 **ポジション監視**\n" + "\n".join(alerts)
                            data = _json.dumps({"content": msg}).encode()
                            req = urllib.request.Request(
                                webhook, data=data,
                                headers={"Content-Type": "application/json",
                                         "User-Agent": "FX-AI-Trader/1.0"})
                            urllib.request.urlopen(req, timeout=10)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[ProfitMonitor] error: {e}", flush=True)
            time.sleep(self._PROFIT_MONITOR_INTERVAL)

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

                # Emergency kill: skip all auto-restart
                if self._emergency_killed:
                    time.sleep(60)
                    continue

                # 全モードを強制チェック（EUR含む）
                _all_modes = ["scalp", "scalp_5m", "daytrade", "daytrade_1h", "swing",
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
        _heartbeat_counter = 0
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

                # ── OANDA Heartbeat: 60秒ごと（120回に1回）──
                # Account Details取得 + レイテンシ計測 → ヘルスチェック
                _heartbeat_counter += 1
                if _heartbeat_counter >= 120:
                    _heartbeat_counter = 0
                    try:
                        hb = self._oanda.run_heartbeat()
                        if hb.get("status") == "error":
                            self._add_log(
                                f"💓 OANDA Heartbeat ERROR: {hb.get('error', 'unknown')}"
                            )
                    except Exception as e:
                        print(f"[SLTP-Checker] Heartbeat error: {e}", flush=True)

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
                    # ── MAFE計算 (OANDA_SL_TP決済パス) ──
                    _mafe_adv_oa = 0.0
                    _mafe_fav_oa = 0.0
                    _dir_oa = demo_trade.get("direction", "")
                    _inst_oa = demo_trade.get("instrument", "USD_JPY")
                    _pip_m_oa = 100 if ("JPY" in _inst_oa or "XAU" in _inst_oa) else 10000
                    _ep_oa = demo_trade.get("entry_price", 0)
                    _mt_oa = self._mafe_tracker.pop(trade_id, None)
                    self._entry_atr.pop(trade_id, None)
                    self._entry_adx.pop(trade_id, None)
                    self._pyramided_trades.discard(trade_id)
                    self._dd_phase_at_entry.pop(trade_id, None)
                    self._exposure_mgr.remove_position(trade_id)
                    if _mt_oa and _ep_oa:
                        if _dir_oa == "BUY":
                            _mafe_adv_oa = round((_ep_oa - _mt_oa["min_low"]) * _pip_m_oa, 1)
                            _mafe_fav_oa = round((_mt_oa["max_high"] - _ep_oa) * _pip_m_oa, 1)
                        else:
                            _mafe_adv_oa = round((_mt_oa["max_high"] - _ep_oa) * _pip_m_oa, 1)
                            _mafe_fav_oa = round((_ep_oa - _mt_oa["min_low"]) * _pip_m_oa, 1)
                        _mafe_adv_oa = max(_mafe_adv_oa, 0.0)
                        _mafe_fav_oa = max(_mafe_fav_oa, 0.0)
                    # v6.3: spread_at_exit をOANDA決済パスにも追加
                    _spread_exit_oa = 0.0
                    try:
                        from modules.data import fetch_oanda_bid_ask as _fab_oa
                        _ba_oa_exit = _fab_oa(_inst_oa)
                        if _ba_oa_exit:
                            _pip_m_exit_oa = 100 if ("JPY" in _inst_oa or "XAU" in _inst_oa) else 10000
                            _spread_exit_oa = round((_ba_oa_exit["ask"] - _ba_oa_exit["bid"]) * _pip_m_exit_oa, 2)
                    except Exception:
                        pass
                    result = self._db.close_trade(trade_id, close_price, "OANDA_SL_TP",
                                                  spread_at_exit=_spread_exit_oa,
                                                  mafe_adverse_pips=_mafe_adv_oa,
                                                  mafe_favorable_pips=_mafe_fav_oa)
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
        MAX_HOLD_SEC["scalp_5m"] = 3600     # 5m足: max 1h hold (12バー)
        MAX_HOLD_SEC["scalp_eur"] = 1800
        MAX_HOLD_SEC["scalp_eurjpy"] = 1800
        MAX_HOLD_SEC["daytrade_eur"] = 28800
        MAX_HOLD_SEC["daytrade_1h_eur"] = 64800
        MAX_HOLD_SEC["rnb_usdjpy"] = 7200   # RNB: max 2h hold

        for trade in open_trades:
          try:
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
            # ── MAFE追跡: Max Adverse / Favorable Excursion ──
            # 各バーの価格でmax_high/min_lowを更新し、決済時にMAE/MFEをDB保存
            # ══════════════════════════════════════════════════════════════
            if trade_id not in self._mafe_tracker:
                self._mafe_tracker[trade_id] = {"max_high": price, "min_low": price}
            else:
                _mt = self._mafe_tracker[trade_id]
                if price > _mt["max_high"]:
                    _mt["max_high"] = price
                if price < _mt["min_low"]:
                    _mt["min_low"] = price

            # ══════════════════════════════════════════════════════════════
            # ── ブレイクイーブン (共通建値ガード) ──
            # 通常: ATR*0.8 到達でBE (建値+スプレッド)
            # SMC戦略(inducement_ob, turtle_soup): 3pips含み益でBE+0.1pip
            # ══════════════════════════════════════════════════════════════
            tp_dist = abs(tp - entry_price)
            if direction == "BUY":
                favorable_move = price - entry_price
            else:
                favorable_move = entry_price - price

            _original_sl = sl  # OANDA SL変更検出用
            _entry_type_t = trade.get("entry_type", "")
            _SMC_TYPES = {"inducement_ob", "turtle_soup", "trendline_sweep"}
            _is_smc = _entry_type_t in _SMC_TYPES

            if _ba_rt:
                _spread_amt = _ba_rt["ask"] - _ba_rt["bid"]
            else:
                _spread_amt = 0.008 if "JPY" in _inst else 0.00008

            _is_jpy_or_xau_be = "JPY" in _inst or "XAU" in _inst
            _pip_val_be = 0.01 if _is_jpy_or_xau_be else 0.0001

            if favorable_move > 0 and tp_dist > 0:
                # ── 共通建値ガード: ATR*0.8 到達で SL→建値 ──
                # SMC戦略: FX=3pip即BE / XAU=10pip(ノイズ回避)
                # 通常戦略: ATR*0.8 到達でBE
                _entry_atr_be = self._entry_atr.get(trade_id,
                    0.07 if _is_jpy_or_xau_be else 0.00070)
                # ATR=0/NaN防御: 最低ATRフロア (3pip相当) → TS即死を防止
                _min_atr_floor = 0.03 if _is_jpy_or_xau_be else 0.00030
                if not _entry_atr_be or _entry_atr_be != _entry_atr_be:  # 0, None, NaN
                    _entry_atr_be = _min_atr_floor
                _entry_atr_be = max(_entry_atr_be, _min_atr_floor)
                _be_threshold = _entry_atr_be * 0.8  # raw price units

                # XAU 3pip BE → ノイズで建値撤退連発("BE貧乏")のため10pipに拡大
                _is_xau_be = "XAU" in _inst
                _smc_be_pips = 10.0 if _is_xau_be else 3.0

                if _is_smc and favorable_move >= _smc_be_pips * _pip_val_be:
                    # SMC専用: BE+0.1pip (負けを物理消去)
                    _be_buffer = 0.1 * _pip_val_be
                    if direction == "BUY":
                        new_sl = round(entry_price + _spread_amt + _be_buffer, _pip_decimals)
                        if new_sl > sl:
                            sl = new_sl
                    else:
                        new_sl = round(entry_price - _spread_amt - _be_buffer, _pip_decimals)
                        if new_sl < sl:
                            sl = new_sl

                elif favorable_move >= _be_threshold:
                    # ── Tier2: ATRトレイリングストップ ──
                    # ATR*1.5到達で動的TS: SL = price - ATR*0.5 (利益ロックイン)
                    # MFE>0→LOSSの25.5%を救済 (推定+64.7p)
                    _ts_threshold = _entry_atr_be * 1.5
                    if favorable_move >= _ts_threshold:
                        _ts_trail = _entry_atr_be * 0.5  # ATR*0.5幅でトレイル
                        if direction == "BUY":
                            new_sl = round(price - _ts_trail, _pip_decimals)
                            if new_sl > sl:
                                sl = new_sl
                        else:
                            new_sl = round(price + _ts_trail, _pip_decimals)
                            if new_sl < sl:
                                sl = new_sl
                    else:
                        # Tier1: 共通建値ガード: ATR*0.8到達でBE (建値+スプレッド)
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
                if not self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
                    sl = _original_sl  # OANDA失敗時はSLを元に戻す

            # ── v8.9: 含み益リアルタイム検知 (0.5秒ループ内) ──
            # 大幅含み益のDiscord通知 + Shadow含み益警告
            if favorable_move > 0 and hasattr(self, '_rt_profit_cache'):
                _key = f"{trade_id}"
                _prev = self._rt_profit_cache.get(_key, 0)
                _fav_pips = favorable_move * (100 if "JPY" in _inst else 10000)
                # 含み益が+10pip超えかつ前回通知から5pip以上増加した場合
                if _fav_pips > 10 and _fav_pips - _prev > 5:
                    self._rt_profit_cache[_key] = _fav_pips
                    _is_sh = trade.get("is_shadow", 0)
                    self._add_log(
                        f"💰 [{_entry_type_t}×{_inst}] 含み益+{_fav_pips:.1f}pip"
                        f"{' (SHADOW⚠️)' if _is_sh else ''}"
                    )
            if not hasattr(self, '_rt_profit_cache'):
                self._rt_profit_cache = {}

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

            # ══════════════════════════════════════════════════════════════
            # ── v6.4: Generalized 50% TP Profit Extender ──
            # トレンドフォロー戦略がTP距離の50%到達 + ADX>30 → TP200%延伸
            # ══════════════════════════════════════════════════════════════
            _entry_type_pe = trade.get("entry_type", "")
            _tp_hit_buy = (direction == "BUY" and price >= tp)
            _tp_hit_sell = (direction == "SELL" and price <= tp)
            _should_extend_tp = False

            if (_entry_type_pe in self._PE_50PCT_ELIGIBLE
                    and trade_id not in self._profit_extended):
                _tp_dist_pe = abs(tp - entry_price)
                if _tp_dist_pe > 0:  # guard: TP距離0はスキップ
                    _50pct_dist = _tp_dist_pe * 0.5
                    _reached_50 = (
                        (direction == "BUY" and price >= entry_price + _50pct_dist) or
                        (direction == "SELL" and price <= entry_price - _50pct_dist)
                    )
                    _pe_adx_entry = self._entry_adx.get(trade_id, 0)
                else:
                    _reached_50 = False
                    _pe_adx_entry = 0
                if _reached_50 and _pe_adx_entry > 30:
                    # TP → 200% of original distance
                    if direction == "BUY":
                        tp = round(entry_price + _tp_dist_pe * 2.0, _pip_decimals)
                    else:
                        tp = round(entry_price - _tp_dist_pe * 2.0, _pip_decimals)
                    self._profit_extended.add(trade_id)
                    # Trailing stop: ATR×0.5
                    _pe_atr_50 = self._entry_atr.get(
                        trade_id, 0.07 if "JPY" in _inst or "XAU" in _inst else 0.00070
                    )
                    _pe_trail_50 = _pe_atr_50 * 0.5
                    if direction == "BUY":
                        new_sl = round(price - _pe_trail_50, _pip_decimals)
                        if new_sl > sl:
                            sl = new_sl
                    else:
                        new_sl = round(price + _pe_trail_50, _pip_decimals)
                        if new_sl < sl:
                            sl = new_sl
                    if self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
                        self._db.update_sl_tp(trade_id, sl, tp)
                        self._add_log(
                            f"🚀 [v6.4] 50% TP Extender: {trade_id} ({_entry_type_pe}) "
                            f"ADX={_pe_adx_entry:.1f}>30 → TP200%={tp:.{_pip_decimals}f} "
                            f"Trail={_pe_trail_50*(100 if 'JPY' in _inst or 'XAU' in _inst else 10000):.1f}pip"
                        )
                        _should_extend_tp = True

            # ══════════════════════════════════════════════════════════════
            # ── v6.4: Risk-Free Pyramiding ──
            # 1.0 ATR有利方向移動 + OANDA昇格済み → 追加ポジション + SL→BE
            # ══════════════════════════════════════════════════════════════
            # v6.5 fix: OANDA trade IDがないトレードはPYRAMID対象外
            # (OANDA停止中に開設されたデモ専用トレードのmodify_sl_sync無限失敗を防止)
            _has_oanda_id = bool(trade.get("oanda_trade_id"))
            if (trade_id not in self._pyramided_trades
                    and _has_oanda_id
                    and _entry_type_pe in self._PE_50PCT_ELIGIBLE):
                _pyr_atr = self._entry_atr.get(
                    trade_id, 0.07 if "JPY" in _inst or "XAU" in _inst else 0.00070
                )
                _pyr_favorable = (
                    (direction == "BUY" and price >= entry_price + _pyr_atr) or
                    (direction == "SELL" and price <= entry_price - _pyr_atr)
                )
                if _pyr_favorable and self._is_promoted(_entry_type_pe, _inst):
                    # SL → BE for original trade (同期版: 成功確認後のみpyramid)
                    _pyr_spread = _ba_rt["ask"] - _ba_rt["bid"] if _ba_rt else (
                        0.008 if "JPY" in _inst else 0.00008
                    )
                    if direction == "BUY":
                        _be_sl = round(entry_price + _pyr_spread, _pip_decimals)
                        if _be_sl > sl:
                            sl = _be_sl
                    else:
                        _be_sl = round(entry_price - _pyr_spread, _pip_decimals)
                        if _be_sl < sl:
                            sl = _be_sl
                    # 同期SL変更: 失敗時はpyramid中止 (2.0lotフルリスク防止)
                    _sl_ok = self._oanda.modify_sl_sync(
                        trade_id, sl, instrument=_inst
                    )
                    if not _sl_ok:
                        self._add_log(
                            f"⚠️ [PYRAMID] SL→BE変更失敗、ピラミッド中止 "
                            f"({trade_id})"
                        )
                        self._pyramided_trades.add(trade_id)  # 再試行防止
                    else:
                        self._db.update_sl_tp(trade_id, sl, tp)
                        # Open pyramid OANDA position
                        _pyr_id = f"PYR_{trade_id}"
                        _pyr_units = min(10000, self._OANDA_LOT_CAP)
                        _pyr_tp = tp
                        _pyr_sl_price = entry_price  # risk-free: SL at original entry
                        self._oanda.open_trade(
                            demo_trade_id=_pyr_id,
                            direction=direction,
                            sl=_pyr_sl_price, tp=_pyr_tp,
                            mode=mode,
                            instrument=_inst,
                            units=_pyr_units,
                            log_callback=self._add_log,
                            lot_label="(🔺PYR)",
                        )
                        self._pyramided_trades.add(trade_id)
                        self._add_log(
                            f"🔺 [PYRAMID] {trade_id}: +{_pyr_units}u {direction} "
                            f"SL=BE({_be_sl:.{_pip_decimals}f}) "
                            f"TP={_pyr_tp:.{_pip_decimals}f}"
                        )

            # ── Profit Extender (Confluence Scalp v2 + DT) ──
            # TP到達時にMSS継続+ADX>30なら → TP延伸+トレイリング
            # クライマックス検出時は即利確

            # v6.1: DT Profit Extender (orb_trap, london_ny_swing × EUR)
            # EUR/USDの緩やかトレンドに合わせADX閾値緩和 + TP50%延伸
            if _entry_type_pe in self._PE_DT_ELIGIBLE and (_tp_hit_buy or _tp_hit_sell):
                if trade_id not in self._profit_extended:
                    _pe_adx_dt = self._PE_ADX_THRESHOLD.get(_inst, 30)
                    _pe_atr_dt = self._entry_atr.get(trade_id, 0.07 if "JPY" in _inst or "XAU" in _inst else 0.00070)
                    # ADX確認 (DF不要: 最新sigのadxを使用)
                    _pe_adx_val = sig.get("adx", 0) if sig else 0
                    if _pe_adx_val > _pe_adx_dt:
                        _ext_dist_dt = abs(tp - entry_price) * 0.5  # 50%延伸 (CSv2の2x より控えめ)
                        if direction == "BUY":
                            tp = round(tp + _ext_dist_dt, _pip_decimals)
                        else:
                            tp = round(tp - _ext_dist_dt, _pip_decimals)
                        self._profit_extended.add(trade_id)
                        _pe_trail_dt = _pe_atr_dt * 0.5  # 標準トレイリング幅
                        if direction == "BUY":
                            new_sl = round(price - _pe_trail_dt, _pip_decimals)
                            if new_sl > sl:
                                sl = new_sl
                        else:
                            new_sl = round(price + _pe_trail_dt, _pip_decimals)
                            if new_sl < sl:
                                sl = new_sl
                        if self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
                            self._db.update_sl_tp(trade_id, sl, tp)
                            self._add_log(
                                f"🚀 DT Profit Extender: {trade_id} ({_entry_type_pe}) "
                                f"TP+50% (ADX={_pe_adx_val:.1f}>{_pe_adx_dt}) → "
                                f"新TP={tp:.{_pip_decimals}f}"
                            )
                            _should_extend_tp = True

            if _entry_type_pe == "confluence_scalp" and (_tp_hit_buy or _tp_hit_sell):
                _mss = self._mss_tracker.get(trade_id)
                _pe_adx_cs = self._PE_ADX_THRESHOLD.get(_inst, 30)
                if _mss and _mss.get("msb") and _mss.get("adx", 0) > _pe_adx_cs:
                    if trade_id not in self._profit_extended:
                        # ── TP延伸: 現在TPの2倍距離に拡大 ──
                        _ext_dist = abs(tp - entry_price)
                        if direction == "BUY":
                            tp = round(tp + _ext_dist, _pip_decimals)
                        else:
                            tp = round(tp - _ext_dist, _pip_decimals)
                        self._profit_extended.add(trade_id)
                        # ── 強化トレイリング: ATR*0.4幅 (通常0.5より狭く利益ロック) ──
                        _pe_atr = self._entry_atr.get(trade_id, 0.07 if "JPY" in _inst or "XAU" in _inst else 0.00070)
                        _pe_trail = _pe_atr * 0.4
                        if direction == "BUY":
                            new_sl = round(price - _pe_trail, _pip_decimals)
                            if new_sl > sl:
                                sl = new_sl
                        else:
                            new_sl = round(price + _pe_trail, _pip_decimals)
                            if new_sl < sl:
                                sl = new_sl
                        # SL/TP変更をDBに反映 (OANDA成功時のみ)
                        if self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
                            self._db.update_sl_tp(trade_id, sl, tp)
                            self._add_log(
                                f"🚀 Profit Extender: {trade_id} TP延伸 "
                                f"(MSB+ADX={_mss.get('adx', 0):.1f}>{_pe_adx_cs}) → "
                                f"新TP={tp:.{_pip_decimals}f} Trail={_pe_trail*(100 if 'JPY' in _inst or 'XAU' in _inst else 10000):.1f}pip"
                            )
                            _should_extend_tp = True
                elif trade_id in self._profit_extended:
                    # 既にTP延伸済み → トレイリング継続 (Tier2と同じだが狭い)
                    _pe_atr = self._entry_atr.get(trade_id, 0.07 if "JPY" in _inst or "XAU" in _inst else 0.00070)
                    _pe_trail = _pe_atr * 0.4
                    if direction == "BUY":
                        new_sl = round(price - _pe_trail, _pip_decimals)
                        if new_sl > sl:
                            if self._oanda.modify_sl_sync(trade_id, new_sl, instrument=_inst):
                                sl = new_sl
                    else:
                        new_sl = round(price + _pe_trail, _pip_decimals)
                        if new_sl < sl:
                            if self._oanda.modify_sl_sync(trade_id, new_sl, instrument=_inst):
                                sl = new_sl

            # ── Climax Exit (Confluence Scalp v2) ──
            # TP延伸中にクライマックス検出 → 即利確
            if _entry_type_pe == "confluence_scalp" and trade_id in self._profit_extended:
                # 簡易クライマックス検出: 大ウィック判定 (price-based)
                # _sltp_loopにはDFがないため、MFE/current priceの乖離で代替
                _mss_c = self._mss_tracker.get(trade_id)
                if _mss_c and _mss_c.get("climax"):
                    close_reason = "CLIMAX_EXIT"
                    self._add_log(
                        f"🎯 Climax Exit: {trade_id} トレンド疲弊検出 → 利確"
                    )

            if not close_reason and not _should_extend_tp:
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
                _is_jpy_or_xau_exit = "JPY" in _inst or "XAU" in _inst
                _pip_m_exit = 100 if _is_jpy_or_xau_exit else 10000
                if _ba_rt:
                    _spread_exit = round((_ba_rt["ask"] - _ba_rt["bid"]) * _pip_m_exit, 2)

                # ── MAFE計算: 保持中のmax/min → MAE/MFE (pips) ──
                _mafe_adverse = 0.0
                _mafe_favorable = 0.0
                _mt = self._mafe_tracker.pop(trade_id, None)
                self._entry_atr.pop(trade_id, None)
                self._entry_adx.pop(trade_id, None)
                self._pyramided_trades.discard(trade_id)
                if _mt:
                    if direction == "BUY":
                        _mafe_adverse = round((entry_price - _mt["min_low"]) * _pip_m_exit, 1)
                        _mafe_favorable = round((_mt["max_high"] - entry_price) * _pip_m_exit, 1)
                    else:
                        _mafe_adverse = round((_mt["max_high"] - entry_price) * _pip_m_exit, 1)
                        _mafe_favorable = round((entry_price - _mt["min_low"]) * _pip_m_exit, 1)
                    # MAE/MFE は常に正値
                    _mafe_adverse = max(_mafe_adverse, 0.0)
                    _mafe_favorable = max(_mafe_favorable, 0.0)

                result = self._db.close_trade(trade_id, price, close_reason,
                                              spread_at_exit=_spread_exit,
                                              mafe_adverse_pips=_mafe_adverse,
                                              mafe_favorable_pips=_mafe_favorable)
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

                # ── Friction Ratio: 摩擦純度 (P2監視タグ) ──
                _spread_at_entry = trade.get("spread_at_entry", 0)
                _slippage_entry = abs(trade.get("slippage_pips", 0))
                _total_friction = _spread_at_entry + _spread_exit + _slippage_entry
                _fr_str = ""
                if abs(pnl) > 0.01:
                    _friction_ratio = _total_friction / abs(pnl)
                    _fr_str = f" FR={_friction_ratio:.0%}"
                    if _friction_ratio > 1.0:
                        _fr_str += "⚠️"  # 摩擦がPnL超過

                # ── Equity Curve Protector: 段階的DDロット縮小 v7.0 ──
                # v8.9: Shadow trades と XAU trades はエクイティ曲線に含めない
                _is_eq_eligible = (
                    not trade.get("is_shadow", 0)
                    and "XAU" not in (trade.get("instrument", "") or "")
                )
                if _is_eq_eligible:
                    self._eq_current += pnl
                    if self._eq_current > self._eq_peak:
                        self._eq_peak = self._eq_current
                    _eq_dd = self._eq_peak - self._eq_current
                    _eq_dd_pct = _eq_dd / max(self._EQ_BASE_CAPITAL_PIPS, 1.0)
                    _prev_dd_mult = self._dd_lot_mult
                    _new_dd_mult = get_dd_lot_multiplier(_eq_dd_pct)
                    self._dd_lot_mult = _new_dd_mult
                    # v7.0: backward compat flag (True if any DD reduction active)
                    self._defensive_mode = _new_dd_mult < 1.0

                    if _new_dd_mult < _prev_dd_mult:
                        self._add_log(
                            f"🛡️ DD REDUCTION: DD={_eq_dd:.1f}pip ({_eq_dd_pct:.1%}) "
                            f"lot_mult={_prev_dd_mult:.2f}->{_new_dd_mult:.2f}"
                        )
                    elif _new_dd_mult > _prev_dd_mult:
                        self._add_log(
                            f"🟢 DD RECOVERY: DD={_eq_dd:.1f}pip ({_eq_dd_pct:.1%}) "
                            f"lot_mult={_prev_dd_mult:.2f}->{_new_dd_mult:.2f}"
                        )

                    # ── v7.0: Equity state DB永続化 (deploy survive) ──
                    try:
                        self._db.set_system_kv("eq_peak", str(round(self._eq_peak, 2)))
                        self._db.set_system_kv("eq_current", str(round(self._eq_current, 2)))
                        self._db.set_system_kv("defensive_mode", "1" if self._defensive_mode else "0")
                        self._db.set_system_kv("dd_lot_mult", str(round(self._dd_lot_mult, 2)))
                    except Exception:
                        pass  # DB書き込み失敗は決済処理をブロックしない

                self._add_log(
                    f"{cfg.get('icon','')} 📤 OUT [{cfg.get('label','?')}]: {icon} {outcome} | "
                    f"{direction} @ {trade['entry_price']:.3f} → {price:.3f} | "
                    f"PnL: {pnl:+.1f} pips | "
                    f"Reason: {close_reason} | spread={_spread_exit:.1f}p{_fr_str} | ID: {trade_id}"
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
                    with self._lock:
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

          except Exception as _per_trade_err:
            # 1トレードの例外で他トレードのSL/TP/MAX_HOLDチェックを止めない
            _tid = trade.get("trade_id", "?") if isinstance(trade, dict) else "?"
            print(f"[SLTP-Checker] Trade {_tid} error: {_per_trade_err}", flush=True)
            continue

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
        # v6.5: 外部アラート (CB発動は最重要イベント)
        self._alert_mgr.alert_oanda_kill(
            f"{reason} ({pnl:+.1f}pip / limit {limit}pip) modes={modes_before}")

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
        # v7.0: Shadow Tracking — 時間帯外でもシグナル計算を実行しデータ収集
        _active_hours = cfg.get("active_hours_utc")
        _outside_active_hours = False
        if _active_hours is not None:
            _now_utc = datetime.now(timezone.utc)
            if not (_active_hours[0] <= _now_utc.hour <= _active_hours[1]):
                _outside_active_hours = True  # 下流でshadow判定に使用

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
            if mode in ("scalp", "scalp_eur", "scalp_eurjpy") and mode != "scalp_5m" and sig.get("signal") == "WAIT":
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

        # ── Confluence Scalp v2: MSS状態追跡 (Profit Extender用) ──
        # スキャルプモードで毎tick (10s間隔) に open confluence_scalp トレードの
        # MSS状態を更新 → _check_sltp_realtime でTP延伸判定に使用
        if _base_mode_fn == "scalp":
            try:
                _open_trades_mss = self._db.get_open_trades()
                for _ot_mss in _open_trades_mss:
                    if _ot_mss.get("entry_type") != "confluence_scalp":
                        continue
                    _tid_mss = _ot_mss["trade_id"]
                    try:
                        from strategies.scalp.confluence_scalp import (
                            detect_mss_state, detect_climax
                        )
                        _mss_result = detect_mss_state(df, lookback=30)
                        _adx_mss = float(df.iloc[-1].get("adx", 25.0)) if "adx" in df.columns else 25.0
                        _dir_mss = _ot_mss.get("direction", "BUY")
                        _climax = detect_climax(df, _dir_mss, lookback=10)
                        self._mss_tracker[_tid_mss] = {
                            "choch": _mss_result.get("choch"),
                            "msb": _mss_result.get("msb", False),
                            "direction": _mss_result.get("direction"),
                            "adx": _adx_mss,
                            "climax": _climax,
                            "updated": datetime.now(timezone.utc),
                        }
                    except Exception as _mss_err:
                        print(f"[MSS] tracker error for {_tid_mss}: {_mss_err}")
                # Cleanup: 閉じたトレードのMSSデータを削除
                _open_ids = {t["trade_id"] for t in _open_trades_mss}
                for _stale_id in list(self._mss_tracker.keys()):
                    if _stale_id not in _open_ids:
                        self._mss_tracker.pop(_stale_id, None)
                        self._profit_extended.discard(_stale_id)
                        self._pyramided_trades.discard(_stale_id)
                        self._entry_adx.pop(_stale_id, None)
            except Exception as _mss_outer:
                print(f"[MSS] outer error: {_mss_outer}")

        # ── Friction Minimizer: pending limit order check ──
        # 保留中の指値注文の価格到達チェック (10s間隔)
        if self._pending_limits:
            _now_lm = datetime.now(timezone.utc)
            _expired = []
            for _lm_key, _lm in list(self._pending_limits.items()):
                _lm_mode = _lm.get("mode", "")
                if _lm_mode != mode:
                    continue
                # 5分 (300秒) で期限切れ
                _lm_age = (_now_lm - _lm["created"]).total_seconds()
                if _lm_age > 300:
                    _expired.append(_lm_key)
                    # v6.1: Strict Friction Guard — GBP_USD指値失効時クールダウン
                    _lm_inst = _lm.get("instrument", "")
                    if _lm_inst in self._LIMIT_ONLY_SCALP:
                        _cd_key = f"{_lm_inst}_{_lm.get('signal', '')}"
                        self._limit_expired_cd[_cd_key] = _now_lm
                        self._add_log(
                            f"🛑 Friction Guard: {_lm_inst} 指値失効 → "
                            f"{self._LIMIT_EXPIRE_CD_SEC}s 追っかけ禁止 "
                            f"({_lm.get('signal', '')})"
                        )
                    continue
                # 価格チェック: 指値に到達したか
                _lm_price = sig.get("entry", 0)
                _lm_limit = _lm["limit_price"]
                _lm_signal = _lm["signal"]
                _filled = False
                if _lm_signal == "BUY" and _lm_price <= _lm_limit:
                    _filled = True
                elif _lm_signal == "SELL" and _lm_price >= _lm_limit:
                    _filled = True
                if _filled:
                    # 指値約定 → エントリー実行
                    self._add_log(
                        f"📍 Limit Fill: {_lm_signal} @ {_lm_price:.5f} "
                        f"(limit={_lm_limit:.5f}, waited={_lm_age:.0f}s)"
                    )
                    # ── 🔗 OANDA: 指値到達ログ ──
                    self._add_log(
                        f"🔗 OANDA: [LIMIT_FILL] {_lm_signal} {_lm.get('instrument', '')} "
                        f"@ {_lm_price:.5f} (limit={_lm_limit:.5f}, "
                        f"waited={_lm_age:.0f}s) → OANDA order dispatching"
                    )
                    # sig を limit order の保存時シグナルで上書きしてエントリー
                    _lm_sig = _lm["sig"]
                    _lm_sig["entry"] = _lm_price  # 現在価格で約定
                    try:
                        self._tick_entry(mode, cfg, _lm_sig, tf, instrument)
                    except Exception as _le:
                        print(f"[LimitEntry] error: {_le}")
                    _expired.append(_lm_key)
            for _ek in _expired:
                self._pending_limits.pop(_ek, None)

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
                pass
            # フォールバック: bid/ask取得失敗時はrealtime価格を使用
            if current_price <= 0:
                _fb = self._get_realtime_price(instrument, cfg.get("symbol", "USDJPY=X"))
                if _fb and _fb > 0:
                    current_price = _fb

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
        with self._lock:
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
            self._check_signal_reverse(trade, current_price, signal, confidence, mode, sig)

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

        # ══════════════════════════════════════════════════════════════
        # ── v7.0/v8.9: Shadow Tracking — 観測データ最大化 ──
        # FORCE_DEMOTED/Sentinel戦略は OANDA送信されない → フィルター緩和して
        # デモデータを収集。is_shadow=True でマークし学習エンジンから除外。
        # OANDA送信ロジック (_is_promoted) は一切変更しない。
        #
        # v8.9: _is_shadow_eligible を2段階に分離
        #   _is_shadow_eligible_full: 全フィルター(active_hours,regime等)のバイパス対象
        #   _is_slot_shadow_eligible: スロット制約(max_per_mode_pair,hedge,max_open)のみバイパス
        #     → 全戦略がスロット制約をバイパスしてshadow入り可能
        #     → スロットが空いていればnormal(OANDA送信可)、埋まっていればshadowで入る
        # ══════════════════════════════════════════════════════════════
        _is_shadow_eligible_full = (
            entry_type in self._FORCE_DEMOTED
            or entry_type in self._SCALP_SENTINEL
            or entry_type in self._UNIVERSAL_SENTINEL
        )
        _is_shadow_eligible = _is_shadow_eligible_full  # 後方互換 (他のbypassはこれを参照)
        _is_slot_shadow_eligible = True  # v8.9: 全戦略がスロットbypass可能
        _is_shadow = False  # 実際にフィルターをバイパスした場合にTrueになる

        # ── 通貨ペア×モードクラス別ポジション制限 ──
        # scalp/DT/1H/swingが独立してポジションを持てる
        # scalp: 高頻度のため2本まで（シグナル方向転換に対応）
        # DT/1H/swing: 1本ずつ
        _base_mode = _get_base_mode(mode)
        _mode_limits = {"scalp": 2, "daytrade": 1, "daytrade_1h": 1, "swing": 1}
        _mode_limit = _mode_limits.get(_base_mode, 1)
        # v8.9: Shadow trades は non-shadow のみカウント（スロット占有しない）
        _mode_inst_trades = [t for t in open_trades
                            if t.get("instrument", "USD_JPY") == instrument
                            and _get_base_mode(t.get("mode", "")) == _base_mode
                            and not t.get("is_shadow", False)]
        if len(_mode_inst_trades) >= _mode_limit:
            if _is_slot_shadow_eligible:
                _is_shadow = True
                self._add_log(
                    f"[SHADOW] Slot bypass: {entry_type} {mode}/{instrument} "
                    f"({len(_mode_inst_trades)}/{_mode_limit} → shadow)"
                )
            else:
                _block(f"max_per_mode_pair({_base_mode}/{instrument}:{len(_mode_inst_trades)}/{_mode_limit})"); return
        # ── 同一ペア逆方向ヘッジ防止 (2026-04-06 audit fix) ──
        # scalp limit=2 でもBUY+SELL同時保有はスプレッド二重消費 → ブロック
        # v8.9: Shadow trades はヘッジブロックも免除（デモデータ収集目的）
        _hedge_blocked = False
        for _ot in _mode_inst_trades:
            if _ot.get("direction") and _ot["direction"] != signal:
                _hedge_blocked = True; break
        if _hedge_blocked:
            if _is_slot_shadow_eligible:
                _is_shadow = True
                self._add_log(
                    f"[SHADOW] Hedge bypass: {entry_type} {mode}/{instrument} → shadow"
                )
            else:
                _block(f"hedge_block({_base_mode}/{instrument}:{signal})"); return
        # グローバル安全上限（全通貨ペア・全モード合計）
        # v8.9: Shadow trades は別上限 (max_open + 8) — N蓄積を優先しつつメモリ保護
        _max_open = self._params["max_open_trades"]
        _shadow_max = _max_open + 8
        _n_open = len(open_trades)
        if _n_open >= _max_open:
            if _is_slot_shadow_eligible and _n_open < _shadow_max:
                _is_shadow = True
            else:
                _block(f"max_open({_n_open}/{_max_open})"); return
        if signal == "WAIT":
            return  # WAITはカウントしない（大半がWAIT）
        if self._check_drawdown():
            _block("drawdown"); return

        # ── v7.0: Shadow Tracking — active_hours_utc バイパス ──
        # NOTE: _outside_active_hours は _tick() のローカル変数のため
        #       _tick_entry() 内で再計算が必要 (スコープ分離)
        _active_hours_cfg = cfg.get("active_hours_utc")
        _outside_active_hours = False
        if _active_hours_cfg is not None:
            _now_ah = datetime.now(timezone.utc)
            if not (_active_hours_cfg[0] <= _now_ah.hour <= _active_hours_cfg[1]):
                _outside_active_hours = True
        if _outside_active_hours:
            if _is_shadow_eligible:
                _is_shadow = True
                self._add_log(
                    f"[SHADOW] Session bypass: {entry_type} {mode} (outside active_hours → shadow)"
                )
            else:
                _block(f"session_hours(outside_active)"); return

        # ── v6.5: MARKET_CLOSE Entry Prevention (セッション終了30分前の新規エントリー禁止) ──
        # MARKET_CLOSE損失の構造対策: 保有中にセッション終了 → 含み損確定を防止
        _now_mc = datetime.now(timezone.utc)
        _active_hrs = cfg.get("active_hours_utc")
        if _active_hrs is not None:
            _session_end_hour = _active_hrs[1]
            _minutes_to_end = (_session_end_hour - _now_mc.hour) * 60 - _now_mc.minute
            if 0 < _minutes_to_end <= 30:
                _block(f"market_close_30min(end={_session_end_hour}:00UTC)"); return

        # ── v6.5: Cross-pair Exposure Check (通貨集中リスク防止) ──
        import os as _os_exp
        _exp_units_est = int(_os_exp.environ.get("OANDA_UNITS", "10000"))
        _exp_ok, _exp_reason = self._exposure_mgr.check_new_trade(
            instrument, signal, _exp_units_est)
        if not _exp_ok:
            self._alert_mgr.alert_exposure_blocked(instrument, signal, _exp_reason)
            _block(f"exposure:{_exp_reason}"); return

        # ══════════════════════════════════════════════════════════════
        # ── v6.5 Phase 2: Range Sub-classification & MR Score Control ──
        # RANGE → SQUEEZE / WIDE_RANGE / TRANSITION サブ分類
        # MR戦略: SQUEEZE=ブロック, WIDE_RANGE=ブースト, TRANSITION=通過
        # ══════════════════════════════════════════════════════════════
        _RANGE_MR_STRATEGIES = {
            "bb_rsi_reversion", "macdh_reversal", "fib_reversal", "vol_surge_detector",
            "eurgbp_daily_mr",  # EUR/GBP 日足MR: レンジ極値フェード
            "dt_bb_rsi_mr",              # DT BB RSI MR: 15m BB%B+RSI14+Stoch 平均回帰 (Bollinger 1992)
            "dt_sr_channel_reversal",    # v8.1: DT SR Channel Reversal — TREND_BULL MR免除対象
        }
        _sig_regime_r = sig.get("regime", {})
        _regime_type_r = _sig_regime_r.get("regime", "") if isinstance(_sig_regime_r, dict) else ""
        _range_sub = _sig_regime_r.get("range_sub") if isinstance(_sig_regime_r, dict) else None
        _is_mr_entry = entry_type in _RANGE_MR_STRATEGIES

        # ── v6.5 Phase 0: vol_surge_detector momentum/climax 二面性解決 ──
        # vol_surge_detector は climax(MR) と momentum(TF) の2モードを持つ。
        # momentum モードはトレンド初動であり MR ではない →
        # SQUEEZE ブロック・BB_mid TP・SL widening 等の MR 専用調整から免除。
        # climax モードは MR → 従来通り全 MR ロジック適用。
        _is_vol_surge_momentum = False
        if _is_mr_entry and entry_type == "vol_surge_detector":
            _vs_reasons = sig.get("reasons", [])
            _is_vol_surge_momentum = any(
                "モメンタム初動" in str(r) for r in _vs_reasons
            )
            if _is_vol_surge_momentum:
                _is_mr_entry = False  # MR分類から除外 → 全MR専用調整をバイパス

        if _regime_type_r == "RANGE" and _is_mr_entry and _range_sub:
            if _range_sub == "SQUEEZE":
                self._add_log(
                    f"[REGIME] SQUEEZE detected — MR Blocked | "
                    f"{entry_type} {signal} {instrument} | "
                    f"bb_width_pct={_sig_regime_r.get('bb_width_pct', '?')}"
                )
                _block("regime_squeeze_mr"); return
            elif _range_sub == "WIDE_RANGE":
                _orig_conf_wr = confidence
                confidence = min(confidence + 5, 100)
                _orig_score_wr = sig.get("score", 0)
                sig["score"] = _orig_score_wr + 1.0
                self._add_log(
                    f"[REGIME] WIDE_RANGE detected — MR Score Boosted | "
                    f"{entry_type} {signal} {instrument} | "
                    f"Conf: {_orig_conf_wr}→{confidence} "
                    f"Score: {_orig_score_wr:+.1f}→{sig['score']:+.1f}"
                )
            # TRANSITION: no adjustment — standard evaluation continues

        # v6.5 Phase 0: vol_surge momentum が SQUEEZE を通過した場合のテレメトリ
        if _is_vol_surge_momentum and _range_sub == "SQUEEZE":
            self._add_log(
                f"[REGIME] SQUEEZE — vol_surge MOMENTUM bypassed MR block | "
                f"{signal} {instrument} | "
                f"bb_width_pct={_sig_regime_r.get('bb_width_pct', '?')} "
                f"squeeze_bars={_sig_regime_r.get('squeeze_bars', '?')}"
            )

        # ══════════════════════════════════════════════════════════════
        # ── v6.7: DT Trend-Following RANGE Regime Block ──
        # 本番実績: DT RANGE 74%発火 WR=25.7% (構造的負EV)
        # TREND_BULL WR=35.7% が唯一の収益レジーム
        # TF戦略はRANGEで構造的に失敗 → DT(15m)のみブロック
        # MR戦略 (orb_trap, htf_false_breakout, gbp_deep_pullback,
        #         squeeze_release_momentum) はブロック対象外
        # ══════════════════════════════════════════════════════════════
        _DT_TREND_STRATEGIES = {
            "sr_fib_confluence", "ema_cross", "sr_break_retest",
            "adx_trend_continuation", "lin_reg_channel", "trendline_sweep",
            "london_ny_swing", "turtle_soup", "jpy_basket_trend",
        }
        if (_base_mode == "daytrade"
                and _regime_type_r == "RANGE"
                and entry_type in _DT_TREND_STRATEGIES):
            if _is_shadow_eligible:
                _is_shadow = True
                self._add_log(
                    f"[SHADOW] DT RANGE bypass: {entry_type} (TF in RANGE → shadow) | "
                    f"{signal} {instrument}"
                )
            else:
                self._add_log(
                    f"[REGIME] DT RANGE blocked: {entry_type} (TF strategy in RANGE) | "
                    f"{signal} {instrument} | "
                    f"range_sub={_range_sub}"
                )
                _block(f"regime_range_dt_tf({entry_type})")
                return

        # ── v8.0→v8.1: DT TREND_BULL TF戦略遮断（MR免除）──
        # TF戦略: N=17 WR=0% (ema_cross/sr_fib/sr_break — トレンド末期追っかけ)
        # MR戦略: N=3 WR=100% (dt_bb_rsi_mr/dt_sr_channel_reversal — 逆張り成功)
        # v8.0は全遮断→v8.1でMR免除。_is_mr_entryは上流Phase2で定義済み
        if (_base_mode == "daytrade" and _regime_type_r == "TREND_BULL"
                and not _is_mr_entry):
            if _is_shadow_eligible:
                _is_shadow = True
                self._add_log(
                    f"[SHADOW] DT TREND_BULL TF bypass: {entry_type} "
                    f"(TF in TREND_BULL WR=0% → shadow) | {signal} {instrument}"
                )
            else:
                _block(f"regime_trend_bull_dt_tf({entry_type})")
                return

        # ── v8.6: GBPアジアセッション除外 — フラッシュクラッシュ対策 ──
        # BIS 2017: 2016/10/7 GBP 9%暴落(アジア早朝)。2022/9にも4.5%急落
        # アジア時間帯(UTC 21-06)はGBPの流動性が極端に低い
        # Spread/SL Gateでは防げないテールリスク → 静的ブロック（原則#3の例外）
        _now_h = datetime.now(timezone.utc).hour
        if "GBP" in instrument and (_now_h >= 21 or _now_h < 6):
            if not _is_shadow_eligible:
                _block(f"gbp_asia_flash_crash(UTC{_now_h})")
                return
            else:
                _is_shadow = True
                self._add_log(
                    f"[SHADOW] GBP Asia bypass: {entry_type} (flash crash zone → shadow)"
                )

        if confidence < self._params["confidence_threshold"]:
            _block(f"conf<{self._params['confidence_threshold']}(was:{confidence})"); return

        # ── 重複エントリー防止 ──
        # (A) 同価格帯ブロック（モード別: scalp=1.0pip, DT=5pip, other=3pip）
        # scalp: 1.5→1.0pip (エントリー機会増), DT: 1.5→5pip (マシンガン防止)
        _is_jpy = "JPY" in instrument
        _is_jpy_or_xau = _is_jpy or "XAU" in instrument
        if _is_jpy_or_xau:
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
            "vol_momentum_scalp",    # VolMomスキャルプ: ADX+OBV+VWAP順張り (2026-04-07)
            "ema_ribbon_ride",       # EMAリボンライド: EMA9/21/50リボン順張り (2026-04-07)
            "gold_pips_hunter",      # ゴールドPipsハンター: XAU専用スキャルプ (2026-04-07)
            "london_shrapnel",       # LDN異常ヒゲ反転 EUR/GBP専用 (2026-04-07)
            "vol_surge_detector",    # 出来高急増ブレイクアウト (2026-04-07)
            "confluence_scalp",      # Triple Confluence + MSS (UTC 12-17, HTF Hard Block) (2026-04-07)
            # v7.0 Sentinel再有効化 — デモデータ蓄積で再検証 (2026-04-09)
            "v_reversal",            # V字反転 — Sentinel蓄積中
            "trend_rebound",         # トレンドリバウンド — Sentinel蓄積中
            "sr_channel_reversal",   # SRチャネル反転 — Sentinel蓄積中
            "engulfing_bb",          # 包み足+BB — Sentinel蓄積中
            "three_bar_reversal",    # 三本足反転 — Sentinel蓄積中
            "ema_trend_scalp",       # EMAトレンドスキャルプ — Sentinel蓄積中
            # DISABLED (FXアナリストレビュー 2026-04-03):
            # "ihs_neckbreak",       # 廃止: 1m足でパターン認識不適
            # "sr_touch_bounce",     # 廃止: BT結果なし, sr_fib(15m)と重複
            # "rsi_divergence_sr",   # 廃止: EV=-0.607
            # v1互換6種:            # 全廃止: BT結果なし, v2と機能重複
            # "sr_bounce", "ob_retest", "bb_bounce",
            # "donchian", "reg_channel",

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
            "dual_sr_bounce",                # SR Bounce: legacy compute_signal SR回帰 (2026-04-07)
            "london_ny_swing",               # LDN-NYスイング: クロスセッション順張り (2026-04-07)
            "jpy_basket_trend",              # JPYバスケットトレンド: 円通貨連動 (2026-04-07)
            "gold_vol_break",                # ゴールド出来高ブレイク: XAU DT専用 (2026-04-07)
            "gold_trend_momentum",           # ゴールドトレンドモメンタム: XAU EMA21 PB 順張り (Baur 2010) — Sentinel蓄積中
            "liquidity_sweep",               # v8.2: 流動性スイープ: ウィック構造ストップ狩りリバーサル (Osler 2003) — Sentinel蓄積中
            # v8.5: 学術文献リサーチ6新エッジ (2026-04-12)
            "session_time_bias",             # セッション時刻バイアス: 自国時間帯通貨減価 (Breedon & Ranaldo 2013)
            "gotobi_fix",                    # 五十日仲値Fix: USD/JPY BUY (Bessho 2023, Ito & Yamada 2017)
            "london_fix_reversal",           # ロンドンFixリバーサル: Fix前→Fix後反転 (Krohn 2024)
            "vix_carry_unwind",              # VIXキャリー巻戻し: VIX急騰→JPY long (Brunnermeier 2009)
            "xs_momentum",                   # クロスセクション通貨モメンタム (Menkhoff 2012, Eriksen 2019)
            "hmm_regime_filter",             # HMMレジームフィルター: 防御オーバーレイ (Nystrup 2024)
            # v8.8: 生データアルファマイニング (2026-04-12)
            "vol_spike_mr",                  # Vol Spike MR: 3x range spike → fade (BT JPY PF=1.92)
            "doji_breakout",                 # Doji Breakout: 3連続doji → breakout follow
            # v7.0 Sentinel再有効化 — デモデータ蓄積で再検証 (2026-04-09)
            "post_news_vol",                 # PNV: 指標後ボラ — Sentinel蓄積中
            "dt_fib_reversal",               # DTフィボ反転 — Sentinel蓄積中
            "dt_sr_channel_reversal",        # DT SR/チャネル反転 — Sentinel蓄積中
            "ema200_trend_reversal",         # EMA200トレンド反転 — Sentinel蓄積中
            "squeeze_release_momentum",      # SRM v3: BBスクイーズ解放 — Sentinel蓄積中
            "eurgbp_daily_mr",               # EUR/GBP 日足MR — Sentinel蓄積中
            "dt_bb_rsi_mr",                  # DT BB RSI MR: 15m平均回帰 — Sentinel蓄積中
            # DISABLED (FXアナリストレビュー):
            # "ihs_neckbreak",       # 廃止: 2t EV≒0, 低頻度
            # "dual_sr_breakout",    # 廃止: 未評価

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
            _cooldown_sec = {"scalp": 60, "scalp_5m": 300, "daytrade": 900, "daytrade_1h": 3600, "swing": 14400}.get(_base_mode, 60)
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
        _cascade_cd = {"scalp": 45, "scalp_5m": 300, "daytrade": 90, "daytrade_1h": 300, "swing": 600}.get(_base_mode, 60)  # v7.0: scalp 90→45s (1min足1本分未満、SL_HIT後の再攻撃を加速)
        _cascade_cutoff = datetime.now(timezone.utc) - timedelta(seconds=_cascade_cd)
        _recent_sl_same_inst = [h for h in self._sl_hit_history
                                if h[0] > _cascade_cutoff and h[1] == instrument]
        if _recent_sl_same_inst:
            _last_sl = _recent_sl_same_inst[-1]
            _sl_age = (datetime.now(timezone.utc) - _last_sl[0]).total_seconds()
            _block(f"cascade_cd({instrument},{_last_sl[2]},SL {int(_sl_age)}s ago/{_cascade_cd}s)")
            return

        # ══════════════════════════════════════════════════════════════
        # ── セッション×ペア除外フィルター (461t監査) ──
        # 統計的にエッジ消滅を確認したセグメントをOANDA連携・デモ共にブロック
        # EUR_GBP全セッション: WR=11.1%(N=9), 全損-29.9p
        # EUR_USD_Tokyo(UTC0-7): WR=20.4%(N=54), -62.9p
        # EUR_USD_Late_NY(UTC17+): WR=9.5%(N=21), -25.8p
        # コントラリアン検証済み: spread二重控除後 -1.1p → 逆張りもエッジなし
        # ══════════════════════════════════════════════════════════════
        _utc_hour = datetime.now(timezone.utc).hour
        # v6.7: eurgbp_daily_mr は日足MR戦略 → EUR_GBP全停止をバイパス (Sentinel)
        _EURGBP_DAILY_MR_WHITELIST = {"eurgbp_daily_mr"}
        if instrument == "EUR_GBP" and entry_type not in _EURGBP_DAILY_MR_WHITELIST:
            _block(f"session_pair(EUR_GBP全停止,WR=11%)")
            return
        if instrument == "EUR_USD":
            if _utc_hour < 7:  # Tokyo
                _block(f"session_pair(EUR_USD_Tokyo,WR=20%)")
                return
            if _utc_hour >= 17:  # Late NY
                _block(f"session_pair(EUR_USD_Late_NY,WR=10%)")
                return
            # v8.9: EUR_USD SELL全面ブロック — Alpha Scan N=43 WR=11.6% EV=-2.714 PnL=-116.7pip
            # 最大のアルファ破壊源。BUYのみ許可。
            if signal == "SELL":
                if _is_slot_shadow_eligible:
                    _is_shadow = True
                    self._add_log(f"[SHADOW] EUR_USD SELL block: {entry_type} → shadow (EV=-2.714)")
                else:
                    _block(f"alpha_scan(EUR_USD_SELL,N=43,EV=-2.714)")
                    return
        # v7.0 撤去: USD/JPY scalp UTC 11-12 デスゾーン
        # 静的時間ブロック → Spread/SL Gate(動的)に委譲。
        # マーケット開いてる間は攻める。スプレッド異常時のみ動的に防御。
        # v7.0 撤去: UTC 05 デスゾーン — N=5は統計的に無意味、
        # offending戦略(fib/macdh)は全てFORCE_DEMOTED済み。
        # bb_rsi Gold Hours(UTC 05) +0.8ボーナスと矛盾していた。
        # Spread/SL Gate(v7.0)がFast Exit防止として残存。

        # ══════════════════════════════════════════════════════════════
        # ── v8.9: RANGE SELL 制限 — Alpha Scan N=89 WR=27.0% EV=-1.636 PnL=-145.6pip ──
        # 最大毒性源。RANGE中のSELLをconfidence要件引上げで制限
        # 完全ブロックではなくconf>=65で通過（高確信SELLは許可）
        # ══════════════════════════════════════════════════════════════
        if (_regime_type_r == "RANGE" and signal == "SELL"
                and conf < 65):
            if _is_slot_shadow_eligible:
                _is_shadow = True
                self._add_log(f"[SHADOW] RANGE SELL gate: {entry_type} conf={conf}<65 → shadow")
            else:
                _block(f"alpha_scan(RANGE_SELL,conf={conf}<65,EV=-1.636)")
                return

        # ══════════════════════════════════════════════════════════════
        # ── v8.9: BUY × TREND_BULL ブロック — Alpha Scan N=70 WR=31.4% EV=-0.776 PnL=-54.3pip ──
        # トレンド追従BUYは高値掴み。MR戦略(押し目買い)は免除。
        # conf>=65 の高確信シグナルは通過許可。
        # ══════════════════════════════════════════════════════════════
        _TREND_BULL_MR_EXEMPT = {
            "bb_rsi_reversion", "fib_reversal", "orb_trap",
            "gbp_deep_pullback", "vol_spike_mr",
        }
        if (_regime_type_r == "TREND_BULL" and signal == "BUY"
                and entry_type not in _TREND_BULL_MR_EXEMPT
                and conf < 65):
            if _is_slot_shadow_eligible:
                _is_shadow = True
                self._add_log(f"[SHADOW] TREND_BULL BUY block: {entry_type} conf={conf}<65 → shadow (EV=-0.776)")
            else:
                _block(f"alpha_scan(TREND_BULL_BUY,{entry_type},conf={conf}<65,EV=-0.776)")
                return

        # ══════════════════════════════════════════════════════════════
        # ── v8.9: H11 × EUR_USD ブロック — Alpha Scan N=9 WR=22.2% EV=-4.489 PnL=-40.4pip ──
        # London mid-session: EUR_USDが叩かれるデスゾーン
        # ══════════════════════════════════════════════════════════════
        if _utc_hour == 11 and instrument == "EUR_USD":
            if _is_slot_shadow_eligible:
                _is_shadow = True
                self._add_log(f"[SHADOW] H11 EUR_USD block: {entry_type} → shadow (EV=-4.489)")
            else:
                _block(f"alpha_scan(H11_EUR_USD,N=9,EV=-4.489)")
                return

        # ══════════════════════════════════════════════════════════════
        # ── v8.9: H13 × USD_JPY ブロック — Alpha Scan N=14 WR=28.6% EV=-2.486 PnL=-34.8pip ──
        # Pre-NY dead zone: JPYの流動性枯渇帯
        # ══════════════════════════════════════════════════════════════
        if _utc_hour == 13 and instrument == "USD_JPY":
            if _is_slot_shadow_eligible:
                _is_shadow = True
                self._add_log(f"[SHADOW] H13 USD_JPY block: {entry_type} → shadow (EV=-2.486)")
            else:
                _block(f"alpha_scan(H13_USD_JPY,N=14,EV=-2.486)")
                return

        # ══════════════════════════════════════════════════════════════
        # ── v7.0: DT Power Session — USD/JPY のみ UTC 7-8, 13-14 限定 ──
        # 本番112t分析(USD/JPY): UTC 13-14 WR=65.2% +122.7pip (z=4.02)
        #                        UTC 7-8   WR=38%  +18.0pip  (London Open)
        #                        他時間帯  WR=19%  -415.7pip (全出血源)
        # Bonferroni多重比較補正後も有意 (z>2.63)
        # v7.0: USD/JPYのみ適用。他ペア(EUR,GBP,XAU,EUR/GBP)は
        #       compute_daytrade_signal 内の独自セッションフィルターで制御
        # v7.0: tokyo_nakane_momentum (UTC 00:45-01:15) は仲値リバーサル
        #       戦略のため Power Session から除外 (Andersen 2003)
        # ══════════════════════════════════════════════════════════════
        # v7.0: DT Power Session 撤去 — 原則#3「静的時間ブロック禁止」準拠
        # BT 30d検証: Power Session(WR=56.6% -5.53ATR) vs Non-Power(WR=66.1% +24.02ATR)
        # → 利益を出している時間帯をブロックし赤字時間帯のみ許可していた。Spread/SL Gateに委ねる
        # _DT_POWER_HOURS = {1, 2, 7, 8, 13, 14}  # REMOVED
        pass

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
            _is_jpy_scale = _is_jpy or "XAU" in instrument
            _spread_pips = (_ba_entry["ask"] - _ba_entry["bid"]) * (100 if _is_jpy_scale else 10000)
            # ── 通貨ペア別スプレッド閾値 (pips) — 本番乖離解消 ──
            _SPREAD_LIMITS = {
                "USD_JPY": 1.0,
                "EUR_USD": 1.2,
                "GBP_USD": 1.5,     # v7.0: 1.2→1.5 (OANDA実測0.8-1.8pip)
                "EUR_GBP": 1.5,     # v7.0: 1.2→1.5
                "EUR_JPY": 2.5,     # v7.0: 1.2→2.5 (OANDA実測1.5-2.5pip常態)
                "XAU_USD": 6.0,     # v6.4: 4.0→6.0 (OANDA実測4-5pip、Asia 5pip常態)
            }
            _spread_limit = _SPREAD_LIMITS.get(instrument, 1.2 if _is_jpy else 1.5)
            # v7.0: Sentinel戦略はspread_wideバイパス — 0.01lotのリスク<データ価値
            # NOTE: _is_shadowは立てない。PAIR_PROMOTED戦略がshadow化されOANDA遮断されるのを防止
            # spread過大エントリーはSpread/SL Gate(line 3212)で最終防御される
            if _spread_pips > _spread_limit and not _is_shadow_eligible:
                _block(f"spread_wide({_spread_pips:.1f}pip>{_spread_limit})")
                return

            # ══════════════════════════════════════════════════════════════
            # ── 動的スプレッドガード: spread_cost / expected_profit ──
            # スプレッドコスト（往復）が期待利益の閾値を超えるとedge不足で見送り
            # DT最適化: 20% (v2摩擦監査), scalp: 30%
            # ══════════════════════════════════════════════════════════════
            _sig_tp = sig.get("tp", 0)
            _sig_entry = sig.get("entry", current_price)
            _is_jpy_or_xau_sg = _is_jpy or "XAU" in instrument
            _expected_profit_pips = abs(_sig_tp - _sig_entry) * (100 if _is_jpy_or_xau_sg else 10000) if _sig_tp else 0
            if _expected_profit_pips > 0:
                _spread_cost_ratio = (_spread_pips * 2) / _expected_profit_pips  # 往復スプレッド
                # DT/1H: 20%閾値 (エリート戦略のエッジ防御), scalp: 30%
                _base_mode_sg = _get_base_mode(mode)
                _sg_threshold = 0.20 if _base_mode_sg in ("daytrade", "daytrade_1h") else 0.30
                # v7.2: XAU専用閾値 — スプレッド構造がFXと異なる(4-5pip常態)がATRも10x
                if "XAU" in instrument:
                    _sg_threshold = 0.40 if _base_mode_sg in ("daytrade", "daytrade_1h") else 0.45
                if _spread_cost_ratio > _sg_threshold:
                    _block(f"spread_guard(cost={_spread_pips*2:.1f}pip/profit={_expected_profit_pips:.1f}pip={_spread_cost_ratio:.0%}>{_sg_threshold:.0%})")
                    return

        # ══════════════════════════════════════════════════════════════
        # ── SL狩り対策A1: 価格スパイク検出 ──
        # 直近60秒で価格が急変動(>ATR×1.0)→ SL狩りスパイク中のため見送り
        # v7.0: 0.5→1.0 (1m ATR=0.8pipで0.4pip動がスパイク判定は過敏)
        # v7.0: Sentinel戦略はバイパス — データ蓄積優先
        # ══════════════════════════════════════════════════════════════
        _atr_spike = sig.get("atr", 0.07 if (_is_jpy or "XAU" in instrument) else 0.00070)
        _spike_cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        _inst_history = self._price_history.get(instrument, [])
        _spike_prices = [p for t, p in _inst_history if t > _spike_cutoff]
        if len(_spike_prices) >= 3:
            _spike_range = max(_spike_prices) - min(_spike_prices)
            # v7.2: XAU 1.0→2.0 (gold moves 1ATR/min routinely, 2ATR is genuine spike)
            _spike_mult = 2.0 if "XAU" in instrument else 1.0
            if _spike_range > _atr_spike * _spike_mult and not _is_shadow_eligible:
                _spike_m = 100 if (_is_jpy or "XAU" in instrument) else 10000
                _block(f"spike({_spike_range*_spike_m:.1f}pip/60s)")
                return

        # ══════════════════════════════════════════════════════════════
        # ── ベロシティフィルター ──
        # 本番で急騰中のSELL連敗(-36pip)の原因 → 急動時の逆行エントリーをブロック
        # ══════════════════════════════════════════════════════════════
        _now_vel = datetime.now(timezone.utc)
        _vel_window_min = {"scalp": 10, "daytrade": 30, "daytrade_1h": 60}.get(_base_mode, 10)
        # v7.2: XAU ATR is ~10x FX → velocity thresholds scaled accordingly
        if "XAU" in instrument:
            _vel_threshold_pip = {"scalp": 80.0, "daytrade": 120.0, "daytrade_1h": 200.0}.get(_base_mode, 80.0)
        else:
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
            _block(f"layer_trade_not_ok({entry_type})"); return

        # ── Layer1（COT/機関バイアス）方向チェック — スイングのみ ──
        if mode == "swing":
            _l1 = layer_status.get("layer1", {})
            _l1_dir = _l1.get("direction", "neutral") if isinstance(_l1, dict) else "neutral"
            if _l1_dir == "bull" and signal == "SELL":
                _block(f"l1_bull_vs_sell({entry_type})"); return
            if _l1_dir == "bear" and signal == "BUY":
                _block(f"l1_bear_vs_buy({entry_type})"); return

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
                                _block(f"mtf_strong_bias({_bias_dir}_vs_{signal},{entry_type})"); return
                        else:
                            _mtf_tp_bonus = 1.3

                    elif _bias_strength == "trend":
                        if signal != _bias_dir:
                            confidence = int(confidence * 0.8)
                            if confidence < self._params["confidence_threshold"]:
                                _block(f"mtf_trend_conf_decay({confidence}<{self._params['confidence_threshold']},{entry_type})"); return

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
            _block(f"tp_invalid(tp={tp},price={current_price},{entry_type})"); return
        if _mtf_tp_bonus > 1.0:
            if signal == "BUY":
                tp = current_price + tp_dist
            else:
                tp = current_price - tp_dist

        _base_mode = _get_base_mode(mode)  # scalp_eur/scalp_eurjpy -> scalp
        _is_jpy = "JPY" in instrument
        _is_jpy_or_xau = _is_jpy or "XAU" in instrument
        _price_dec = 3 if _is_jpy else 5
        _atr = sig.get("atr", 0.07 if _is_jpy_or_xau else 0.00070)
        _sl_margin = _atr * 0.3  # SR外側バッファ

        # ══════════════════════════════════════════════════════════════
        # ── v6.5 Phase 1: Range Exit Optimization — BB_mid TP Targeting ──
        # RANGE regime × MR strategy → TP = BB_mid (自然な吸引点)
        # BB_midが遠すぎる場合はATR×1.2でキャップ
        # トレンドフォロー戦略(orb_trap等)には一切影響なし (safeguarded)
        # _RANGE_MR_STRATEGIES / _regime_type_r / _is_mr_entry は Phase 2 ブロックで定義済み
        # ══════════════════════════════════════════════════════════════
        _is_range_mr = (_regime_type_r == "RANGE" and _is_mr_entry)

        if _is_range_mr:
            _bb_mid_val = sig.get("indicators", {}).get("bb_mid", 0)
            _range_tp_cap = 1.2  # ATR×1.2 TP upper cap
            if _bb_mid_val > 0:
                _original_tp = tp
                _tp_overridden = False
                if signal == "BUY" and _bb_mid_val > current_price:
                    _cap_tp = current_price + _atr * _range_tp_cap
                    tp = round(min(_bb_mid_val, _cap_tp), _price_dec)
                    tp_dist = abs(tp - current_price)
                    _tp_overridden = True
                elif signal == "SELL" and _bb_mid_val < current_price:
                    _cap_tp = current_price - _atr * _range_tp_cap
                    tp = round(max(_bb_mid_val, _cap_tp), _price_dec)
                    tp_dist = abs(tp - current_price)
                    _tp_overridden = True

                if _tp_overridden:
                    self._add_log(
                        f"[RANGE_EXIT] {signal} {instrument} | "
                        f"TP: {_original_tp:.{_price_dec}f}→{tp:.{_price_dec}f} "
                        f"(BB_mid={_bb_mid_val:.{_price_dec}f}, "
                        f"cap={round(_atr * _range_tp_cap, _price_dec)}) | "
                        f"Regime={_regime_type_r} | Type={entry_type}"
                    )
                if tp_dist <= 0:
                    _block(f"range_exit_tp_invalid(bb_mid,{entry_type})"); return

        # ── 1H Breakout SL/TP完全保存 ──
        # KSB/DMBはスクイーズ中swing HL / ドンチアン中央から精密にSLを算出済み
        # SR/ATRベース再計算では戦略の意図が破壊されるため、直接使用
        if entry_type in _1H_PRESERVE_SLTP:
            _sig_sl = sig.get("sl", 0)
            if _sig_sl > 0:
                sl = round(_sig_sl, _price_dec)
                sl_dist = abs(current_price - sl)
                if sl_dist <= 0:
                    _block(f"1h_sl_invalid(sl={sl},price={current_price},{entry_type})"); return
                # RR検証
                if tp_dist / sl_dist < 1.2:
                    _block(f"1h_rr_low({tp_dist/sl_dist:.2f}<1.2,{entry_type})"); return
                # SL狩り対策は適用（セッション遷移ワイドニング等）
                # → 下の SL狩り対策②セクションに進む
            else:
                _block(f"1h_no_sl({entry_type})"); return

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
            # v6.5: RANGE MR SL widening — ノイズ許容バッファ (BB反対バンド方向)
            if _is_range_mr:
                _orig_atr_mult = _atr_mult
                _atr_mult = max(_atr_mult, 1.0)  # scalp: 0.8→1.0
                if _atr_mult != _orig_atr_mult:
                    self._add_log(
                        f"[RANGE_EXIT] SL widened: ATR mult {_orig_atr_mult}→{_atr_mult} "
                        f"({entry_type} in RANGE)"
                    )
            if signal == "BUY":
                _atr_sl = current_price - _atr * _atr_mult
            else:
                _atr_sl = current_price + _atr * _atr_mult

            # ── SL選択: SR優先、RR >= 1.0 保証 (v6.5: RANGE MR → 0.8) ──
            _sr_rr_floor = 0.8 if _is_range_mr else 1.0
            if _sr_sl is not None:
                _sr_sl_dist = abs(current_price - _sr_sl)
                _sr_rr = tp_dist / max(_sr_sl_dist, 1e-8)
                if _sr_rr >= _sr_rr_floor:
                    sl = round(_sr_sl, _price_dec)
                    sl_dist = _sr_sl_dist
                else:
                    sl = round(_atr_sl, _price_dec)
                    sl_dist = abs(current_price - _atr_sl)
            else:
                sl = round(_atr_sl, _price_dec)
                sl_dist = abs(current_price - _atr_sl)

            # 最低SL距離保証 (XAU uses same pip scale as JPY)
            if _is_jpy_or_xau:
                MIN_SL_DIST = {"scalp": 0.030, "daytrade": 0.050, "swing": 0.100}.get(_base_mode, 0.030)
            else:
                MIN_SL_DIST = {"scalp": 0.00030, "daytrade": 0.00050, "swing": 0.00100}.get(_base_mode, 0.00030)
            if sl_dist < MIN_SL_DIST:
                sl_dist = MIN_SL_DIST
                if signal == "BUY":
                    sl = round(current_price - sl_dist, _price_dec)
                else:
                    sl = round(current_price + sl_dist, _price_dec)

            # v6.7: DT SL最大距離キャップ (外れ値防止)
            # 本番データ: 4外れ値(299.8pip等)がLOSS SL平均を1.8倍に膨張
            # SRベースSLに上限がないため、15m DTで日足SR距離のSLが発生
            # v7.5: XAU専用キャップ追加 (JPY共有の0.200=$0.20はXAU価格帯($4800)に不適)
            # XAU DT ATR≈$12, SL=ATR*1.2≈$14 → 100で外れ値のみキャップ
            _is_xau_inst = "XAU" in instrument.upper() if instrument else False
            if _is_xau_inst:
                MAX_SL_DIST = {"scalp": 50.0, "daytrade": 100.0, "daytrade_1h": 200.0}.get(_base_mode, 100.0)
            elif _is_jpy_or_xau:
                MAX_SL_DIST = {"scalp": 0.080, "daytrade": 0.200, "daytrade_1h": 0.500}.get(_base_mode, 0.200)
            else:
                MAX_SL_DIST = {"scalp": 0.00080, "daytrade": 0.00200, "daytrade_1h": 0.00500}.get(_base_mode, 0.00200)
            if sl_dist > MAX_SL_DIST:
                _old_sl_dist = sl_dist
                sl_dist = MAX_SL_DIST
                if signal == "BUY":
                    sl = round(current_price - sl_dist, _price_dec)
                else:
                    sl = round(current_price + sl_dist, _price_dec)
                self._add_log(
                    f"⚠️ [SL_CAP] {entry_type}: SL距離 {_old_sl_dist:.{_price_dec}f}"
                    f"→{sl_dist:.{_price_dec}f} (MAX_SL_DIST適用)"
                )

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
        if _is_jpy_or_xau:
            # JPY: 50銭刻み, XAU: $0.50刻み — 同じpip scale
            _sl_frac = sl % 0.500
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
        _is_jpy_or_xau_cl = _is_jpy or "XAU" in instrument
        _sl_cluster_thresh = 0.020 if _is_jpy_or_xau_cl else 0.00020  # 2pip
        _open_for_cluster = self._db.get_open_trades()
        _sl_clustered = False
        for _ot in _open_for_cluster:
            _ot_sl = _ot.get("sl", 0)
            _ot_inst = _ot.get("instrument", "USD_JPY")
            if _ot_inst == instrument and abs(sl - _ot_sl) < _sl_cluster_thresh:
                _block(f"sl_cluster(new={sl:.3f},exist={_ot_sl:.3f})")
                return

        # RR不足チェック（SL調整後に再判定）
        # v7.0: 全戦略0.8統一 — bb_rsi SELL等がSL調整後RR不足で死亡していた
        # Sentinel(0.01lot)のリスク << データ価値。RR 0.8でも収集価値あり
        _final_rr_floor = 0.8
        if tp_dist < sl_dist * _final_rr_floor:
            _block(f"rr_floor({tp_dist/sl_dist:.2f}<{_final_rr_floor},{entry_type})"); return

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
        # ── 高摩擦ペア指値強制: 成行エントリー禁止 (RT摩擦>3pip) ──
        # ══════════════════════════════════════════════════════════════
        _base_mode_limit = _get_base_mode(mode)
        if _base_mode_limit == "scalp" and instrument in self._LIMIT_ONLY_SCALP:
            # v6.1: Strict Friction Guard — 指値失効後クールダウン中はブロック
            _fg_cd_key = f"{instrument}_{signal}"
            _fg_cd_ts = self._limit_expired_cd.get(_fg_cd_key)
            if _fg_cd_ts:
                _fg_age = (datetime.now(timezone.utc) - _fg_cd_ts).total_seconds()
                if _fg_age < self._LIMIT_EXPIRE_CD_SEC:
                    _block(f"friction_guard_cd({instrument},{_fg_age:.0f}s/{self._LIMIT_EXPIRE_CD_SEC}s)")
                    return
                else:
                    self._limit_expired_cd.pop(_fg_cd_key, None)

            _has_limit = any(isinstance(_r, str) and "__LIMIT_ENTRY__" in _r for _r in reasons)
            if not _has_limit:
                _block(f"limit_only({instrument},{entry_type})")
                return

        # ══════════════════════════════════════════════════════════════
        # ── Friction Minimizer: 指値遅延エントリー (Confluence Scalp v2) ──
        # confluence_scalp が __LIMIT_ENTRY__ マーカーを含む場合:
        #   現在価格が指値より不利 → pending_limits に保存して即時エントリー見送り
        #   現在価格が指値以下(BUY)/以上(SELL) → そのままエントリー (自然な良フィル)
        # ══════════════════════════════════════════════════════════════
        if entry_type == "confluence_scalp":
            _limit_price_entry = None
            for _r in reasons:
                if isinstance(_r, str) and _r.startswith("__LIMIT_ENTRY__:"):
                    try:
                        _limit_price_entry = float(_r.split(":")[1])
                    except Exception:
                        pass
                    break
            if _limit_price_entry is not None:
                _should_defer = False
                if signal == "BUY" and current_price > _limit_price_entry:
                    _should_defer = True
                elif signal == "SELL" and current_price < _limit_price_entry:
                    _should_defer = True
                if _should_defer:
                    _lm_key = f"{instrument}_{signal}_{entry_type}"
                    if _lm_key not in self._pending_limits:
                        self._pending_limits[_lm_key] = {
                            "signal": signal,
                            "limit_price": _limit_price_entry,
                            "sig": dict(sig),  # copy
                            "created": datetime.now(timezone.utc),
                            "mode": mode,
                            "sl": sl,
                            "tp": tp,
                            "instrument": instrument,
                        }
                        self._add_log(
                            f"📍 Limit Deferred: {signal} {instrument} "
                            f"limit={_limit_price_entry:.5f} "
                            f"(current={current_price:.5f}, waiting)"
                        )
                        # ── 🔗 OANDA: 指値設置ログ ──
                        self._add_log(
                            f"🔗 OANDA: [LIMIT_PLACED] {signal} {instrument} "
                            f"limit={_limit_price_entry:.5f} | "
                            f"SL={sl:.5f} TP={tp:.5f} (5min expiry)"
                        )
                    return  # 指値待ち → 即時エントリーしない

        # ══════════════════════════════════════════════════════════════
        # ── P0監視: スリッページ・スプレッド・COOLDOWN記録 ──
        # ══════════════════════════════════════════════════════════════
        _signal_price = sig.get("entry", 0)  # シグナル関数のmid価格
        _pip_m_mon = 100 if (_is_jpy or "XAU" in instrument) else 10000
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

        # ══════════════════════════════════════════════════════════════
        # ── v7.0: Spread/SL Gate — Fast Exit 根本対策 ──
        # スプレッドがSL距離の35%超 → エッジ不足で即死リスク
        # 本番データ: Fast Exit(<2min) N=11 PnL=-30.7pip の主因
        # v7.2: XAU専用閾値 45% — ATRベースSLが広く設計上4.2%程度だが安全網として緩和
        # ══════════════════════════════════════════════════════════════
        _sl_dist_pips = abs(current_price - sl) * _pip_m_mon
        if _sl_dist_pips > 0 and _spread_entry > 0:
            _spread_sl_ratio = _spread_entry / _sl_dist_pips
            _ssl_threshold = 0.45 if "XAU" in instrument else 0.35
            if _spread_sl_ratio > _ssl_threshold:
                _block(f"spread_sl_gate({_spread_entry:.1f}/{_sl_dist_pips:.1f}pip={_spread_sl_ratio:.0%}>{_ssl_threshold:.0%})")
                return

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
            is_shadow=_is_shadow,
        )

        # ── 建値ガード用: ATR保存 ──
        # XAU uses same pip scale as JPY (100), fallback ATR must match
        # ATR=0/NaN防御: 最低3pipフロア (TS即死防止, v5.6監査)
        _is_jpy_or_xau_atr = _is_jpy or "XAU" in instrument
        _atr_raw = sig.get("atr", 0.07 if _is_jpy_or_xau_atr else 0.00070)
        _atr_floor = 0.03 if _is_jpy_or_xau_atr else 0.00030
        if not _atr_raw or _atr_raw != _atr_raw:  # 0, None, NaN
            _atr_raw = 0.07 if _is_jpy_or_xau_atr else 0.00070
        self._entry_atr[trade_id] = max(_atr_raw, _atr_floor)
        # v6.4: ADX保存 (Profit Extender 50%TP判定用)
        self._entry_adx[trade_id] = sig.get("adx", 0)
        # v6.5: DD Phase Tagging — エントリー時のDD状態を記録 (データ打ち切り回避)
        self._dd_phase_at_entry[trade_id] = self._defensive_mode
        # v6.5: Exposure tracking — ポジション追加
        self._exposure_mgr.add_position(trade_id, instrument, signal,
                                        int(_os.environ.get("OANDA_UNITS", "10000")))

        # ══════════════════════════════════════════════════════
        # ── 動的ロットサイジング v6.2: 3-Factor Model ──────
        # Factor 1: Risk    = SL距離正規化 (0.5 - 1.5)
        # Factor 2: Edge    = ATR/Spread品質 (0.5 - 1.5)
        # Factor 3: Boost   = 戦略ブースト × N制限 × DD防御
        # ══════════════════════════════════════════════════════
        _cfg_lot = MODE_CONFIG.get(mode, {})
        _base_sl_pips = _cfg_lot.get("base_sl_pips", 3.5)
        _is_jpy_or_xau_lot = _is_jpy or "XAU" in instrument
        _pip_m_d1 = 100 if _is_jpy_or_xau_lot else 10000
        _actual_sl_pips = sl_dist * _pip_m_d1

        # ── Factor 1: Risk (SL距離連動 — リスク額正規化) ──
        _risk_factor = min(_base_sl_pips / max(_actual_sl_pips, 0.5), 1.5)
        _risk_factor = max(_risk_factor, 0.5)

        # ── Factor 2: Edge (ATR/Spread比 — エッジ品質) ──
        _atr_val = sig.get("atr", 0.07 if _is_jpy_or_xau_lot else 0.00070)
        _atr_pips = _atr_val * _pip_m_d1
        _spread_pips = _spread_entry if _spread_entry > 0 else 0.4
        _edge_ratio = _atr_pips / max(_spread_pips, 0.1)

        if _edge_ratio >= 15:
            _edge_factor = 1.5
        elif _edge_ratio >= 10:
            _edge_factor = 1.3
        elif _edge_ratio >= 6:
            _edge_factor = 1.0
        elif _edge_ratio >= 3:
            _edge_factor = 0.7
        else:
            _edge_factor = 0.5

        # ── Factor 3: Boost (戦略 × N制限 × DD防御) ──
        _strat_boost = self._PAIR_LOT_BOOST.get(
            (entry_type, instrument),
            self._STRATEGY_LOT_BOOST.get(entry_type, 1.0)
        )
        _n_trades = self._strategy_n_cache.get(entry_type, 0)
        _n_cap = 1.0
        for _n_threshold, _n_max in self._N_LOT_TIERS:
            if _n_trades >= _n_threshold:
                _n_cap = _n_max
                break
        _strat_boost = min(_strat_boost, _n_cap)
        # v7.0: graduated DD lot multiplier (replaces binary 0.5)
        _eq_mult = self._dd_lot_mult
        _boost_factor = _strat_boost * _eq_mult

        # ── Combined lot ratio ──
        _lot_ratio = _risk_factor * _edge_factor * _boost_factor

        # ── v7.0: Kelly cap -- half-Kelly from learning engine stats ──
        _kelly_cap_applied = False
        _kelly = self._get_strategy_kelly(entry_type, instrument)
        if _kelly is not None and _kelly > 0:
            # Normalize Kelly fraction to lot_ratio scale:
            # half-Kelly fraction (e.g. 0.05) / base_lot_ratio (0.1) = max lot_ratio
            _kelly_lot_cap = _kelly * 0.5 / 0.1
            if _lot_ratio > _kelly_lot_cap:
                _lot_ratio = _kelly_lot_cap
                _kelly_cap_applied = True

        # ── Sentinel判定 v6.2: PAIR_PROMOTED/PAIR_LOT_BOOST はバイパス ──
        _is_sentinel = False
        _sentinel_reason = ""
        _base_mode_lot = _get_base_mode(mode)
        _pair_key = (entry_type, instrument)
        _is_pair_boosted = (_pair_key in self._PAIR_LOT_BOOST or
                            _pair_key in self._PAIR_PROMOTED)

        # v6.2 Safety: N<10の未検証戦略は原則Sentinel (PAIR指定免除)
        if _n_trades < 10 and not _is_pair_boosted:
            _is_sentinel = True
            _lot_ratio = 0.1
            _sentinel_reason = f"N={_n_trades}<10"
        elif _base_mode_lot == "scalp" and entry_type in self._SCALP_SENTINEL and not _is_pair_boosted:
            _is_sentinel = True
            _lot_ratio = 0.1
            _sentinel_reason = "SCALP_SEN"
        elif entry_type in self._UNIVERSAL_SENTINEL and not _is_pair_boosted:
            _is_sentinel = True
            _lot_ratio = 0.1
            _sentinel_reason = "UNI_SEN"

        _lot_ratio = max(0.3, min(_lot_ratio, 2.5))

        _base_units = int(_os.environ.get("OANDA_UNITS", "10000"))
        _adjusted_units = int(_base_units * _lot_ratio)
        if _is_sentinel:
            # v7.6: XAU専用Sentinel単位数 — 1unit=1troy oz≈$4800
            # FX 0.01lot=1000u相当をXAUに適用すると 1000oz×$4800=$4.8M → margin拒絶
            # XAU Sentinel=1unit(1oz), FX Sentinel=1000u(0.01lot)
            _adjusted_units = 1 if _is_xau_inst else 1000
        # XAU: 1unit単位で注文可能、1000u丸め不要
        # FX: 最小1000u, 1000u単位丸め
        if _is_xau_inst:
            _adjusted_units = max(1, _adjusted_units)
        else:
            _adjusted_units = max(1000, (_adjusted_units // 1000) * 1000)

        # ── v7.0 LOT内訳ログ (透明化 + Kelly cap) ──
        _lot_breakdown = (
            f"📐 {_risk_factor:.2f}R×{_edge_factor:.1f}E×{_boost_factor:.2f}B"
            f"{'(K)' if _kelly_cap_applied else ''}"
            f"={'SEN' if _is_sentinel else f'{_lot_ratio:.2f}'}"
            f" → {_adjusted_units}u"
            f" [N={_n_trades} edge={_edge_ratio:.0f}"
            f"{f' DD{self._dd_lot_mult:.0%}' if self._defensive_mode else ''}"
            f"{f' {_sentinel_reason}' if _sentinel_reason else ''}]"
        )

        # ── OANDA連携: 昇格済み戦略のみミラーリング + 実行監査 + 🔗ラベルログ ──
        _is_promoted = self._is_promoted(entry_type, instrument)
        # ── v7.0: Shadow Tracking — OANDAには絶対に送信しない ──
        if _is_shadow:
            _is_promoted = False
        # ── v8.9: FORCE_DEMOTED/PAIR_DEMOTED がフィルターを全通過した場合も
        #    is_shadow=True にする。OANDAに送信されないトレードはshadowとしてマーク
        #    → エクイティ曲線から除外、統計から除外される
        if not _is_promoted and not _is_shadow:
            _is_shadow = True
        # ── v6.4 SHIELD: EUR_USD DT/1H OANDA遮断 (scalp継続) ──
        # v7.0: ホワイトリスト戦略はSHIELD免除 (MR系高EV, N<10 Safety で自動Sentinel)
        if _is_promoted and mode in self._OANDA_MODE_BLOCKED:
            if entry_type in self._SHIELD_EUR_DT_WHITELIST:
                self._add_log(
                    f"[SHIELD] EUR DT whitelist bypass: {entry_type} mode={mode} "
                    f"(N<10→Sentinel自動適用)"
                )
            else:
                self._add_log(f"[SHIELD] OANDA blocked: mode={mode}")
                _is_promoted = False
        _bridge_active = self._oanda.active
        _mode_allowed = self._oanda.is_mode_allowed(mode)
        _strat_mode = self._oanda.get_strategy_mode(entry_type)

        # ── ロットタグ生成（OANDA送信ログ用）──
        _lot_tag = ""
        if _is_sentinel:
            _lot_tag = "(🔬SEN)"
        elif self._defensive_mode:
            _lot_tag = f"(🛡️DD{self._dd_lot_mult:.0%} {_strat_boost}x)"
        elif _strat_boost > 1.0:
            _lot_tag = f"(🚀{_strat_boost}x)"

        # ── SENTINEL判定: コントロールパネルの "sentinel" モードなら0.01lot固定 ──
        if _strat_mode == "sentinel":
            # v7.6: XAU=1unit(1oz), FX=1000u(0.01lot) — 同上
            _adjusted_units = 1 if _is_xau_inst else 1000
            _lot_tag = "(🔬SEN/CMD)"

        # ── v6.4 SHIELD: OANDA lot hard cap ──
        if _adjusted_units > self._OANDA_LOT_CAP:
            self._add_log(
                f"[SHIELD] Lot capped {_adjusted_units}u → {self._OANDA_LOT_CAP}u"
            )
            _adjusted_units = self._OANDA_LOT_CAP

        if _is_promoted:
            if _bridge_active and _mode_allowed:
                # ── v6.4 SHIELD: Quick-Harvest TP (OANDA専用) ──
                # v6.5: RANGE MR は BB_mid TP で既に短縮済み → 二重Harvest禁止
                #        ×0.70 重ね掛け → 実効RR≈0.56 → 損益分岐WR=64% (無理ゲー)
                _tp_oanda = tp
                if ((entry_type, instrument) not in self._QUICK_HARVEST_EXEMPT
                        and not _is_range_mr
                        and _signal_price and _signal_price > 0
                        and abs(tp - _signal_price) > 0):
                    _tp_oanda = _signal_price + (tp - _signal_price) * self._QUICK_HARVEST_MULT
                    self._add_log(
                        f"[SHIELD] Quick-Harvest TP: {tp:.{_price_dec}f} → "
                        f"{_tp_oanda:.{_price_dec}f} (×{self._QUICK_HARVEST_MULT})"
                    )
                elif _is_range_mr:
                    self._add_log(
                        f"[RANGE_EXIT] Quick-Harvest bypassed — "
                        f"BB_mid TP preserved ×1.0 | TP={tp:.{_price_dec}f}"
                    )
                # ── 実弾実行パス ──
                _lot_disp_sent = (f"{_adjusted_units}oz" if _is_xau_inst
                                  else f"{_adjusted_units}u({_adjusted_units/10000:.2f}lot)")
                self._add_log(
                    f"🔗 OANDA: [SENT] {signal} {instrument} "
                    f"{_lot_disp_sent} {_lot_tag} "
                    f"SL={sl:.{_price_dec}f} TP={_tp_oanda:.{_price_dec}f}"
                )
                self._oanda.open_trade(
                    demo_trade_id=trade_id,
                    direction=signal,
                    sl=sl, tp=_tp_oanda,
                    mode=mode,
                    instrument=instrument,
                    callback=lambda did, oid: self._db.set_oanda_trade_id(did, oid),
                    units=_adjusted_units,
                    log_callback=self._add_log,
                    lot_label=_lot_tag,
                    signal_price=_signal_price,
                )
                self._oanda._add_audit(
                    demo_trade_id=trade_id, entry_type=entry_type,
                    is_live=True, bridge_status="sent",
                    block_reason="",
                    direction=signal, instrument=instrument,
                    units=_adjusted_units,
                )
            else:
                # ── Bridge非アクティブまたはモード除外 ──
                _br = "bridge_inactive" if not _bridge_active else f"mode_{mode}_not_allowed"
                self._add_log(
                    f"🔗 OANDA: [BLOCKED] {signal} {instrument} — "
                    f"Reason: {_br}"
                )
                self._oanda._add_audit(
                    demo_trade_id=trade_id, entry_type=entry_type,
                    is_live=False, bridge_status="blocked",
                    block_reason=_br,
                    direction=signal, instrument=instrument,
                    units=_adjusted_units,
                )
        else:
            # ── OANDA未連携: 理由を詳細記録 + 🔗ラベル ──
            _promo = self._promoted_types.get(entry_type, {})
            _promo_n = _promo.get("n", 0)
            _promo_status = _promo.get("status", "pending")
            _block_reason = ""
            if _is_shadow:
                _block_reason = "shadow_tracking"
            elif _strat_mode == "off":
                _block_reason = "手動停止"
            elif mode in self._OANDA_MODE_BLOCKED:
                _block_reason = f"shield_mode_blocked({mode})"
            elif (entry_type, instrument) in self._PAIR_DEMOTED:
                _block_reason = f"pair_demoted({instrument})"
            elif entry_type in self._FORCE_DEMOTED:
                _block_reason = "force_demoted"
            elif _promo_status == "demoted":
                _block_reason = f"auto_demoted(N={_promo_n},EV={_promo.get('ev', 0):+.2f})"
            else:
                _block_reason = f"pending(N={_promo_n}/30)"

            self._oanda._add_audit(
                demo_trade_id=trade_id, entry_type=entry_type,
                is_live=False, bridge_status="skipped",
                block_reason=_block_reason,
                direction=signal, instrument=instrument,
                units=_adjusted_units,
            )
            self._add_log(
                f"🔗 OANDA: [SKIP] {entry_type} — Reason: {_block_reason}"
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
            f"📊 slip={_slippage:+.2f}p spread={_spread_entry:.1f}p {_lot_breakdown} CD={_cd_elapsed:.0f}s"
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
                _pip_m = 100 if ("JPY" in instrument or "XAU" in instrument) else 10000
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

    # ── SR決済ノイズフィルター閾値 (2026-04-07) ──
    _SR_SCORE_THRESHOLD = 2.0   # 逆転シグナルスコア最低閾値
    _SR_ADX_MIN = 20            # ADX>20のトレンド相場のみSR許可

    def _check_signal_reverse(self, trade: dict, current_price: float,
                               new_signal: str, new_conf: int, mode: str,
                               sig: dict = None):
        """シグナル反転によるクローズ判定（SL/TPは _sltp_loop が処理）
        v2: Score閾値(>=2.0) + ADXフィルター(>20) + 詳細ログ
        """
        if sig is None:
            sig = {}
        cfg = MODE_CONFIG.get(mode, {})
        direction = trade["direction"]
        trade_id = trade["trade_id"]
        _instrument_sr = cfg.get("instrument", "USD_JPY")
        _price_fmt = ".3f" if "JPY" in _instrument_sr else ".5f"

        # 最低保持時間チェック（scalp:3分, daytrade:10分, swing:1時間）
        _base_mode_sr = _get_base_mode(mode)
        # scalp: 180→300s (461t監査: <5m SIGNAL_REVERSE 72件PnL≈0のノイズ循環を断切)
        min_hold_sec = {"scalp": 300, "daytrade": 600, "daytrade_1h": 1800, "swing": 3600}.get(_base_mode_sr, 300)
        try:
            entry_time = datetime.fromisoformat(trade["entry_time"])
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - entry_time).total_seconds()
            if age < min_hold_sec:
                return  # 最低保持時間未達 → SIGNAL_REVERSE しない
        except Exception:
            pass

        # ── v6.8: DT含み益保護 — 含み益 > ATR×0.3 のWINトレードをSR切断から保護 ──
        # 本番データ: DT SIGNAL_REVERSE WIN N=4 avg +2.5pip → TP_HIT想定 +15.3pip = 51.4pip逃し
        # MFEトラッカーを参照して含み益を推定
        _base_mode_sr2 = _get_base_mode(mode)
        if _base_mode_sr2 in ("daytrade", "daytrade_1h"):
            _entry_price_sr = trade.get("entry_price", 0) or 0
            _mt_sr = self._mafe_tracker.get(trade_id)
            if _mt_sr and _entry_price_sr > 0:
                if direction == "BUY":
                    _current_favorable = current_price - _entry_price_sr
                else:
                    _current_favorable = _entry_price_sr - current_price
                # ATR推定: entry_atrがあれば使用、なければMAFEから推定
                _sr_atr = self._entry_atr.get(trade_id, 0)
                _profit_threshold = _sr_atr * 0.3 if _sr_atr > 0 else 0.0003  # fallback: 3pip
                if _current_favorable > _profit_threshold:
                    self._add_log(
                        f"[HOLD] DT含み益保護: {direction} {trade_id[:8]} "
                        f"profit={_current_favorable:.5f} > threshold={_profit_threshold:.5f} "
                        f"→ SIGNAL_REVERSE無効化"
                    )
                    return  # 含み益トレードを保護 — TP/SLに委ねる

        # ── v8.2: Scalp MFE-SRガード — 含み益>ATR×0.5 でSR無効化 ──
        # 監査レポート: SR+Quick-Harvest=76.6pip/期間の利益漏出
        # scalp TP=ATR×2.2 に対し MFE>ATR×0.5 = 23%進捗 → この水準で切るとRR≈0.5
        # DT(ATR×0.3)より高い閾値: scalpは素早く利確するためTP/SLに委ねる余地が大きい
        if _base_mode_sr2 == "scalp":
            _entry_price_sr_s = trade.get("entry_price", 0) or 0
            if _entry_price_sr_s > 0:
                if direction == "BUY":
                    _current_fav_s = current_price - _entry_price_sr_s
                else:
                    _current_fav_s = _entry_price_sr_s - current_price
                _sr_atr_s = self._entry_atr.get(trade_id, 0)
                _is_jpy_or_xau_s = "JPY" in _instrument_sr or "XAU" in _instrument_sr
                _profit_thr_s = _sr_atr_s * 0.5 if _sr_atr_s > 0 else (0.025 if _is_jpy_or_xau_s else 0.00025)
                if _current_fav_s > _profit_thr_s:
                    self._add_log(
                        f"[HOLD] Scalp MFEガード: {direction} {trade_id[:8]} "
                        f"profit={_current_fav_s:.5f} > ATR×0.5={_profit_thr_s:.5f} "
                        f"→ SIGNAL_REVERSE無効化"
                    )
                    return  # 含み益トレードを保護 — TP/SLに委ねる

        close_reason = None

        # ── SR判定: 方向反転 + confidence閾値 ──
        reverse_threshold = max(self._params["confidence_threshold"] + 10, 50)
        _is_reverse = False
        if (direction == "BUY" and new_signal == "SELL" and
                new_conf >= reverse_threshold):
            _is_reverse = True
        elif (direction == "SELL" and new_signal == "BUY" and
              new_conf >= reverse_threshold):
            _is_reverse = True

        if not _is_reverse:
            return  # 方向反転なし or confidence不足 → スキップ

        # ── SR ノイズフィルター (2026-04-07) ──
        _sig_score = abs(sig.get("score", 0))
        _sig_adx = sig.get("indicators", {}).get("adx", 0)
        _layer1 = sig.get("layer_status", {}).get("layer1", {})
        _l1_dir = _layer1.get("direction", "neutral")
        # Trend Mismatch: 反転方向がLayer1トレンドと一致するか
        _trend_mismatch = False
        if _l1_dir == "bull" and new_signal == "SELL":
            _trend_mismatch = True
        elif _l1_dir == "bear" and new_signal == "BUY":
            _trend_mismatch = True

        _sr_detail = (
            f"[SR] Score: {sig.get('score', 0):+.2f} | "
            f"ADX: {_sig_adx:.1f} | "
            f"Conf: {new_conf} | "
            f"Trend_Mismatch: {_trend_mismatch} | "
            f"L1: {_l1_dir} | "
            f"Type: {sig.get('entry_type', '?')}"
        )

        # ── フィルター1: スコア閾値 (ペア別感度: USD_JPY=1.5, 他=2.0) ──
        # 弱い逆転シグナルではSR発動しない（ノイズ防止）
        _sr_threshold = self._PAIR_SR_THRESHOLD.get(_instrument_sr, self._SR_SCORE_THRESHOLD)
        if _sig_score < _sr_threshold:
            # スコア不足はtick毎に発生する正常状態 → ログ出力しない（ログ汚染防止）
            return

        # ── フィルター2: ADXレンジ制限 (ADX > 20) ──
        # レンジ相場(ADX<=20)ではSR禁止 → SL/TPに委ねる（往復ビンタ防止）
        if _sig_adx <= self._SR_ADX_MIN:
            self._add_log(
                f"   🚫 SR抑制（レンジ相場）: {direction}→{new_signal} {_sr_detail}"
            )
            return

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

            # ── MAFE計算 (SIGNAL_REVERSE決済パス) ──
            _mafe_adverse_sr = 0.0
            _mafe_favorable_sr = 0.0
            _is_jpy_or_xau_sr = "JPY" in _instrument_sr or "XAU" in _instrument_sr
            _pip_m_sr = 100 if _is_jpy_or_xau_sr else 10000
            entry_price_sr = trade.get("entry_price", 0)
            _mt_sr = self._mafe_tracker.pop(trade_id, None)
            self._entry_atr.pop(trade_id, None)
            self._entry_adx.pop(trade_id, None)
            self._pyramided_trades.discard(trade_id)
            if _mt_sr and entry_price_sr:
                if direction == "BUY":
                    _mafe_adverse_sr = round((entry_price_sr - _mt_sr["min_low"]) * _pip_m_sr, 1)
                    _mafe_favorable_sr = round((_mt_sr["max_high"] - entry_price_sr) * _pip_m_sr, 1)
                else:
                    _mafe_adverse_sr = round((_mt_sr["max_high"] - entry_price_sr) * _pip_m_sr, 1)
                    _mafe_favorable_sr = round((entry_price_sr - _mt_sr["min_low"]) * _pip_m_sr, 1)
                _mafe_adverse_sr = max(_mafe_adverse_sr, 0.0)
                _mafe_favorable_sr = max(_mafe_favorable_sr, 0.0)

            # v6.3: spread_at_exit をSR決済パスにも追加
            _spread_exit_sr = 0.0
            if _ba_sr:
                try:
                    _spread_exit_sr = round((_ba_sr["ask"] - _ba_sr["bid"]) * _pip_m_sr, 2)
                except Exception:
                    pass
            result = self._db.close_trade(trade_id, _close_price, close_reason,
                                          spread_at_exit=_spread_exit_sr,
                                          mafe_adverse_pips=_mafe_adverse_sr,
                                          mafe_favorable_pips=_mafe_favorable_sr)
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
            # ── SR詳細ログ: スコア・ADX・トレンド整合性 ──
            self._add_log(f"   {_sr_detail}")

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

    # Minimum seconds between learning evaluations (prevents duplicate
    # adjustments when multiple trades close in the same SLTP-checker tick)
    _LEARNING_DEDUP_SEC = 60

    def _trigger_learning(self, current_mode: str = None):
        self._trade_count_since_learn = 0

        # ── Idempotency guard: skip if learning ran within dedup window ──
        _now = time.time()
        if _now - self._last_learning_ts < self._LEARNING_DEDUP_SEC:
            return
        self._last_learning_ts = _now

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

    # BT/本番コスト補正: 1トレードあたり1.0pipのコストを考慮
    # EV > _BT_COST_PER_TRADE であれば、コスト差引後もEV正
    _BT_COST_PER_TRADE = 1.0  # pips (spread + slippage)

    def _evaluate_promotions(self):
        """デモ実績に基づいて戦略をOANDA昇格/降格判定
        ファストトラック: N≥20 かつ WR≥60% かつ EV≥1.0 → 昇格
        通常トラック:    N≥30 かつ EV≥1.0 → 昇格 (コスト補正: 1pip差引後にEV正)
        降格(グローバル):  N≥20 かつ EV<-0.5 → 降格 (v8.9: N≥30→N≥20に緩和)
        降格(ペア別):    N≥15 かつ EV<-0.5 → ペア別降格 (v8.9: 新規追加)
        復帰:           N≥30 かつ EV>0 → pending復帰 (v8.9: 新規追加)
        NOTE: トレード回数は減らさない — 降格はOANDA停止のみ、Shadowは継続
        """
        from modules.learning_engine import SMC_PROTECTED
        try:
            data = self._db.get_trades_for_learning(
                min_trades=1, after_date=self._FIDELITY_CUTOFF
            )
            if not data.get("ready"):
                if self._FIDELITY_CUTOFF and self._promoted_types:
                    _reset_count = len(self._promoted_types)
                    self._promoted_types.clear()
                    # リセットすると全戦略がSentinel(0.01lot)化してしまう
                    # N cache は次回の全データ集計で自然に更新される
                    self._add_log(
                        f"🔄 [FIDELITY] 昇格ステータスリセット: "
                        f"{_reset_count}戦略 → pending (cutoff={self._FIDELITY_CUTOFF})"
                    )
                return
            by_type = data.get("by_type", {})
            changes = []
            for et, stats in by_type.items():
                n = stats.get("n", 0)
                ev = stats.get("ev", 0)
                wr = stats.get("wr", 0)
                # v6.1: N cache更新 (Confidence-based Lot Scaling 用)
                self._strategy_n_cache[et] = n
                old = self._promoted_types.get(et, {}).get("status", "pending")
                # ファストトラック: 十分なサンプル+高WR+高EV
                if n >= 20 and wr >= 60.0 and ev >= self._BT_COST_PER_TRADE:
                    status = "promoted"
                # 通常トラック: コスト補正後にEV正 (EV≥1.0pip)
                elif n >= 30 and ev >= self._BT_COST_PER_TRADE:
                    status = "promoted"
                # v8.9: 降格閾値緩和 N≥30→N≥20 (今日のEV分解で十分な根拠)
                elif n >= 20 and ev < -0.5 and et not in SMC_PROTECTED:
                    status = "demoted"
                # v8.9: 自動復帰パス — demotedでもShadowデータが改善すればpending復帰
                elif old == "demoted" and n >= 30 and ev > 0:
                    status = "pending"
                else:
                    status = old if old in ("promoted", "demoted") else "pending"
                self._promoted_types[et] = {"status": status, "n": n, "wr": wr, "ev": ev}
                if old != status:
                    changes.append(f"{et}: {old}→{status} (N={n} WR={wr}% EV={ev:+.2f})")

            # ── v8.9: ペア別降格 — グローバルEVが正でもペア別で負の組み合わせを検出 ──
            by_type_pair = data.get("by_type_pair", {})
            for key, stats in by_type_pair.items():
                _et = stats.get("entry_type", "")
                _inst = stats.get("instrument", "")
                _n = stats.get("n", 0)
                _ev = stats.get("ev", 0)
                _wr = stats.get("wr", 0)
                if _n >= 15 and _ev < -0.5 and _et not in SMC_PROTECTED:
                    _pair_key = (_et, _inst)
                    if _pair_key not in self._PAIR_DEMOTED and _pair_key not in self._PAIR_PROMOTED:
                        # 動的ペア降格: _runtime_pair_demoted に追加
                        if not hasattr(self, '_runtime_pair_demoted'):
                            self._runtime_pair_demoted = set()
                        if _pair_key not in self._runtime_pair_demoted:
                            self._runtime_pair_demoted.add(_pair_key)
                            changes.append(
                                f"🔻 {_et}×{_inst}: auto-PAIR_DEMOTED "
                                f"(N={_n} WR={_wr}% EV={_ev:+.2f})"
                            )

            if changes:
                self._add_log(f"🎯 戦略昇格更新: {', '.join(changes[:5])}")
            # ── v6.2: N cache DB永続化 (deploy survive) ──
            try:
                self._db.set_system_kv("strategy_n_cache", json.dumps(self._strategy_n_cache))
            except Exception:
                pass
            # ── v6.3: Rolling EV Monitor (直近20トレードの滑走EV) ──
            self._check_rolling_ev(by_type)
        except Exception as e:
            print(f"[Promotion] error: {e}", flush=True)

    def _check_rolling_ev(self, by_type: dict):
        """v6.3: 各戦略の直近20トレードのRolling EVを計算し、
        急激なEV低下をアラートする環境適応型モニター。
        """
        try:
            _rolling_alerts = []
            for et, stats in by_type.items():
                n = stats.get("n", 0)
                if n < 10:
                    continue  # N不足は無視
                ev = stats.get("ev", 0)
                # Rolling EV = 直近の全体EVを使用 (DBから直近20件取得は高コストなため全体EVで代替)
                _prev_ev = getattr(self, '_rolling_ev_cache', {}).get(et, None)
                if _prev_ev is not None and ev < -0.3 and ev < _prev_ev - 0.2:
                    _rolling_alerts.append(
                        f"{et}: EV={ev:+.2f}(prev={_prev_ev:+.2f}, drop={ev-_prev_ev:+.2f})"
                    )
                if not hasattr(self, '_rolling_ev_cache'):
                    self._rolling_ev_cache = {}
                self._rolling_ev_cache[et] = ev
            if _rolling_alerts:
                self._add_log(f"⚠️ [v6.3 Rolling EV] 急落検出: {', '.join(_rolling_alerts[:3])}")
                # v6.5: EV急落を外部アラート
                for _ra in _rolling_alerts[:2]:
                    _ra_parts = _ra.split(":")
                    _ra_name = _ra_parts[0].strip() if _ra_parts else "unknown"
                    _prev = self._rolling_ev_cache.get(_ra_name, 0)
                    _cur = by_type.get(_ra_name, {}).get("ev", 0)
                    self._alert_mgr.alert_ev_drop(_ra_name, _prev, _cur)
        except Exception:
            pass

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

    # 本番EV負 → OANDA停止（デモ継続）の強制降格リスト
    # Phase1: sr_fib_confluence, ema_cross, inducement_ob (2026-04-05)
    # Phase2: ema_ribbon_ride(EV=-2.75), h1_fib_reversal(EV=-4.18), pivot_breakout(EV=-8.56) (2026-04-07, 448t監査)
    # Phase3: ema_pullback(WR=19%, EV=-0.77, EMA系3戦略全滅) (2026-04-07, 461t構造分析)
    # Phase4 (v6.8 Quant Audit — 556t本番データ): N≥30で負PF確定の4戦略を停止
    # bb_rsi_reversion のみ正PF(1.13) → 他全てOANDA停止、Demo Sentinel継続
    _FORCE_DEMOTED = {
        "sr_fib_confluence", "ema_cross", "inducement_ob",
        "ema_ribbon_ride", "h1_fib_reversal", "pivot_breakout",
        "ema_pullback",
        "lin_reg_channel", "trendline_sweep", "dual_sr_bounce",
        "fib_reversal",      # v6.8: N=117 WR=39.6% PnL=-18.0 PF<1 → OANDA停止
        #   ↑ v8.2 復活パス: Post-cut N=20 WR=55.0% +35.6pip (v6.3改善効果確認)
        #   N≥30 & WR≥50% 到達時 → FORCE_DEMOTED削除 → SCALP_SENTINEL (自動Sentinel)
        #   N≥50 & WR≥52% & PF>1.1 → PAIR_PROMOTED候補として再審査
        "macdh_reversal",    # v6.8: N=86 WR=34.7% PnL=-40.6 PF<1 → OANDA停止
        "sr_break_retest",   # v7.0: N=2 EV=-21.4 PnL=-42.8 → 1件で全利益消失クラス
        "engulfing_bb",      # v8.0: 本番N=7 WR=14.3% PnL=-$353.5 — 壊滅的、即時停止
        "bb_squeeze_breakout",  # v8.2: BT EV=-0.799 ATR, ブレイクアウト直後の最大スプレッドと重なり構造的赤字
        "sr_channel_reversal",  # v8.9: Post-cut N=17 WR=11.8% 即死率87.5% — BEV下回り確定(p=0.009)
        # v8.9: EV分解で確定的負EV — UNIVERSAL_SENTINEL→FORCE_DEMOTED格上げ
        "stoch_trend_pullback",  # Post-cut N=19 WR=31.6% EV=-0.97 PnL=-18.5 全ペアで負
        "dt_bb_rsi_mr",          # Post-cut N=7(EUR) WR=14.3% EV=-4.09 PnL=-28.6
    }

    # ── Elite Track: 摩擦モデルv2 BT + v5.95統合BT監査 ──
    # 摩擦込みEV > 0.25 AND N >= 20 → ロットブースト
    _STRATEGY_LOT_BOOST = {
        # === Elite Track (Phase A-D BT verified + v5.95 統合監査) ===
        "gbp_deep_pullback": 1.3,          # 本番N<10 → 1.3x暫定 (N≥15で2.0x復帰)
        "turtle_soup": 1.5,                # GBP: EV=1.039, WR=79.3%, N=29
        "orb_trap": 1.5,                   # 全ペア: EUR WR=83% EV=+1.035 / GBP WR=83% EV=+1.117
        "htf_false_breakout": 1.5,         # EUR: EV=0.614 / GBP: EV=0.034 (14d)
        # REMOVED: trendline_sweep → FORCE_DEMOTED (本番WR=0% N=2 -29.8pip)
        "london_ny_swing": 1.5,            # EUR: EV=2.251, WR=100%, N=2
        # REMOVED: fib_reversal → FORCE_DEMOTED (本番N=117 WR=39.6% PnL=-18.0, BT乖離)
        # === Legacy ===
        "sr_break_retest": 1.3,            # GBP WR=80% EV=+0.705 (14d)
        "mtf_reversal_confluence": 1.3,    # EV +1.49 (448t監査)
        "bb_rsi_reversion": 1.5,           # v8.9: 2.0→1.5(保守的) post-cut WR=37.2%でv8.3 OOS未完了。確認後2.0x
        "vol_momentum_scalp": 1.0,        # v8.2: 2.0x→1.0x 摩擦後EV境界的(+1.61-2.14=≈0), N=11でデータ蓄積優先
        "ema_trend_scalp": 1.0,            # v8.9: 1.5x→1.0x (Post-cut N=11 WR=27.3% EV=-0.70, BEV以下)
        # v8.6: 学術リサーチ新エッジ — BT正EV確認済み
        "session_time_bias": 1.3,          # v8.6: 全3ペアBT正EV (JPY+0.427, EUR+0.650, GBP+0.266) — Breedon 2013
        "london_fix_reversal": 1.3,        # v8.6: GBP BT WR=75% EV=+0.318 — Krohn 2024
        # REMOVED: stoch_trend_pullback → _UNIVERSAL_SENTINEL降格 (全ペアEVマイナス)
    }

    # ── Scalp Sentinel: 摩擦込みEV<0 → 最小ロットでデータ収集のみ ──
    # v6.3: bb_rsi_reversion はUSD_JPYのみPAIR_PROMOTED (Sentinel bypass)
    _SCALP_SENTINEL = {
        "bb_rsi_reversion",       # v6.3: USD_JPY PAIR_PROMOTED (Sentinel bypass), 他ペアは維持
        # REMOVED: fib_reversal → FORCE_DEMOTED (重複削除、PAIR_PROMOTED×JPYで復活パスあり)
        # REMOVED: macdh_reversal → FORCE_DEMOTED (重複削除)
        # v8.0: vol_momentum_scalp → _STRATEGY_LOT_BOOST 2.0x昇格 (Kelly H=23.5%, WR=72.7%, Edge=+0.50)
        "vol_surge_detector",     # v6.3: 発火率改善(閾値緩和), Sentinel継続
        # REMOVED: ema_ribbon_ride → FORCE_DEMOTED (重複削除)
        # v8.2: bb_squeeze_breakout → FORCE_DEMOTED (BT EV=-0.799, 構造的赤字)
    }

    # ══════════════════════════════════════════════════════════════
    # ── ペア別戦略ライフサイクル管理 (v5.95 統合BT監査 2026-04-07) ──
    # ══════════════════════════════════════════════════════════════

    # ペア別降格: 特定ペアでのみEVマイナスの組み合わせを狙い撃ちで実弾除外
    _PAIR_DEMOTED = {
        ("bb_rsi_reversion", "EUR_USD"),    # WR=20% EV=-1.500 (14d BT)
        ("macdh_reversal", "GBP_USD"),      # WR=40% EV=-0.818 (14d BT)
        ("ema_cross", "USD_JPY"),           # 本番N=41 WR=34.1% -67.4pip
        ("bb_rsi_reversion", "GBP_USD"),    # v7.0: BT 7d WR=33.3% -32.1pip (PF=0.48)
        ("bb_rsi_reversion", "EUR_JPY"),    # v7.0: BT 7d WR=50.0% -21.9pip (PF=0.41)
        ("vol_surge_detector", "EUR_JPY"),  # v7.0: BT 7d WR=25.0% -36.5pip
        # v8.6: BT負EVペアの明示的降格
        ("london_fix_reversal", "USD_JPY"),  # v8.6: BT WR=28.6% EV=-0.752 — Fix効果がJPYで弱い
        ("xs_momentum", "USD_JPY"),          # v8.6: BT EV=-0.129 — 単一ペアモメンタムはJPYで機能せず
        ("post_news_vol", "USD_JPY"),        # v8.8: 120d BT WR=0% EV=-3.706 — JPYで壊滅的
        ("ema200_trend_reversal", "USD_JPY"),# v8.8: 120d BT WR=0% EV=-1.887 — JPYで全敗
        # v8.9: EV分解で確定的負EV
        ("bb_rsi_reversion", "USD_JPY"),    # Post-cut N=76 WR=38.2% EV=-0.28 Kelly=-5.5% — Tier1→降格
        # v8.9: alpha scan 2026-04-14 — Kelly<0確定セルのペア降格
        # ("ema_trend_scalp", "USD_JPY"),     # v8.9解除: SELL PB境界バグ修正済み → 再蓄積
        ("ema_trend_scalp", "EUR_USD"),     # N=8 WR=25.0% EV=-0.94 Kelly=-16.3%
        ("engulfing_bb", "EUR_USD"),        # N=9 WR=11.1% EV=-1.42 Kelly=-28.4%
        ("trend_rebound", "EUR_USD"),       # N=6 WR=16.7% EV=-1.85 Kelly=-43.0%
        # v8.9: alpha scan #2 2026-04-14 — 追加毒性セル
        ("dt_bb_rsi_mr", "EUR_USD"),         # N=8 WR=25.0% EV=-2.83 Kelly=-50.0%
        ("bb_rsi_reversion", "EUR_USD"),     # N=21 WR=33.3% EV=-0.76 Kelly=-20.2%
        ("stoch_trend_pullback", "USD_JPY"), # N=23 WR=30.4% EV=-0.69 Kelly=-15.1%
        # v8.9: レジーム別分析 2026-04-14 — 全条件負けの確定毒性セル
        ("engulfing_bb", "USD_JPY"),         # N=14 WR=28.6% Kelly=-14.7% — RANGE SELL 0/5全敗, 全レジームEV<0
    }

    # ペア別復活: グローバルFORCE_DEMOTEDだが特定ペアではEV+の戦略を復活
    # v6.8: sr_fib_confluence PAIR_PROMOTED全削除 (本番N=40 WR=28.9% -92.8pip, BT乖離確定)
    _PAIR_PROMOTED = {
        # REMOVED: bb_rsi_reversion×USD_JPY → PAIR_DEMOTED (v8.9: Post-cut N=76 WR=38.2% EV=-0.28 Kelly=-5.5%)
        # v8.2: orb_trap 全3ペア PAIR_PROMOTED — BT最強根拠 (N<10 Sentinel免除)
        # BT: JPY WR=79.3% EV=+0.617 / EUR WR=71.4% EV=+0.482 / GBP WR=64.3% EV=+0.245
        # margin +40-50pp over BEV_WR — 全戦略中最大の摩擦マージン
        # N_LOT_TIERS: N<10→max 1.0x, N≥10→1.5x で段階的増資
        ("orb_trap", "USD_JPY"),
        ("orb_trap", "EUR_USD"),
        ("orb_trap", "GBP_USD"),
        # v8.6: session_time_bias — BT全3ペア正EV確認 (学術根拠: Breedon & Ranaldo 2013 JF)
        # JPY: WR=73.1% EV=+0.427 / EUR: WR=76.9% EV=+0.650 / GBP: WR=69.4% EV=+0.266
        ("session_time_bias", "USD_JPY"),
        ("session_time_bias", "EUR_USD"),
        ("session_time_bias", "GBP_USD"),
        # v8.6: london_fix_reversal GBP_USD — BT WR=75% EV=+0.318 (Krohn 2024 JF)
        ("london_fix_reversal", "GBP_USD"),
        # v8.9: ema_pullback×JPY — Post-cut N=14 WR=42.9% EV=+1.09 (FORCE_DEMOTEDからペア復活)
        # Sentinel lotで実弾データ蓄積、N≥30でフル昇格判断
        ("ema_pullback", "USD_JPY"),
        # v8.9: xs_momentum×GBP/EUR — リアルタイム含み益+48.9pip (London-NY GBP BUY)
        # JPYはPAIR_DEMOTED。GBP/EURはBT正EV (GBP +0.134, EUR +0.192)
        # shadow全敗→TP縮小(3.0→2.0)+London-NY限定で改善済み。実弾でQH適用開始
        ("xs_momentum", "GBP_USD"),
        ("xs_momentum", "EUR_USD"),
    }

    # ペア別ロットブースト: PAIR_LOT_BOOST > _STRATEGY_LOT_BOOST (優先)
    # v8.9: Kelly Half適用 — alpha scan正EVセルにロットブースト
    _PAIR_LOT_BOOST = {
        # Kelly Half: ライブalpha scan N≥10 & Kelly>10% のセル
        ("fib_reversal", "USD_JPY"): 2.0,         # N=26 EV=+0.79 Kelly=11.1% → Half=5.6%
        ("ema_pullback", "USD_JPY"): 2.0,         # N=14 EV=+1.09 Kelly=14.9% → Half=7.5%
        ("vol_momentum_scalp", "USD_JPY"): 2.0,   # N=13 EV=+0.92 Kelly=23.7% → Half=11.9%
        ("vol_surge_detector", "EUR_USD"): 1.8,   # N=7 EV=+1.20 Kelly=32.7% → Half=16.4% (N小→控えめ)
        ("ema_pullback", "EUR_USD"): 1.5,         # N=5 EV=+0.94 Kelly=16.6% → Half=8.3% (N最小→最控えめ)
    }

    # 全モードSentinel: scalp以外にも適用される戦略Sentinel
    _UNIVERSAL_SENTINEL = {
        # REMOVED: stoch_trend_pullback → FORCE_DEMOTED (v8.9: Post-cut N=19 WR=31.6% EV=-0.97)
        "squeeze_release_momentum",    # SRM v3: BT N=24 WR=66.7% OOS未確定 → Sentinel蓄積 (2026-04-08)
        "eurgbp_daily_mr",             # EUR/GBP Daily MR: 日足レンジ極値フェード — BT未実施, Sentinel蓄積
        # REMOVED: dt_bb_rsi_mr → FORCE_DEMOTED (v8.9: Post-cut N=7 WR=14.3% EV=-4.09)
        # v8.0: ema_trend_scalp → _STRATEGY_LOT_BOOST 1.5x昇格 (当日最高PnL +$179.6, WR=44.4%)
        "gold_trend_momentum",         # XAU Trend Momentum: 15m EMA21 PB trend-follow — 新規, Sentinel蓄積
        "liquidity_sweep",             # v8.2: Liquidity Sweep: ウィック構造ストップ狩りリバーサル (Osler 2003) — Sentinel蓄積
        # v8.5: 学術文献リサーチ6新エッジ
        # REMOVED: session_time_bias → PAIR_PROMOTED済み、SENTINEL矛盾のためshadow化が発生していた (v8.9)
        # REMOVED: london_fix_reversal → PAIR_PROMOTED済み、同上 (v8.9)
        "gotobi_fix",                  # 五十日仲値Fix (Bessho 2023)
        "vix_carry_unwind",            # VIXキャリー巻戻し (Brunnermeier 2009)
        # REMOVED: xs_momentum → PAIR_PROMOTED済み(GBP/EUR)、SENTINEL矛盾のためshadow化が発生していた (v8.9)
        "hmm_regime_filter",           # HMMレジームフィルター (Nystrup 2024)
        # v8.8: 生データアルファマイニング
        "vol_spike_mr",                # Vol Spike MR: JPY PF=1.92 (BT最高PF)
        "doji_breakout",               # Doji Breakout: 3連続doji→breakout follow
        # v7.0: 全disabled戦略をSentinel再有効化 — デモデータ蓄積優先 (4原則#4)
        "v_reversal",                  # 急落/急騰反転 — BT未検証, Sentinel蓄積
        # REMOVED: ema_pullback → FORCE_DEMOTED (重複削除、PAIR_PROMOTED×JPYで復活済み)
        "trend_rebound",               # 強トレンド逆張り — 学術的エッジ疑義, Sentinel検証
        # REMOVED: sr_channel_reversal → FORCE_DEMOTED (重複削除)
        # v8.0: engulfing_bb → FORCE_DEMOTED昇格 (WR=14.3% -$353.5)
        "three_bar_reversal",          # 3本足反転 — BT未検証, Sentinel蓄積
        "london_close_reversal",       # ロンドンクローズ反転 — EV≈0, Sentinel再検証
        "dt_fib_reversal",             # DT Fib反発 — 未検証, Sentinel蓄積
        "dt_sr_channel_reversal",      # DT SR/チャネル反発 — 未検証, Sentinel蓄積
        "ema200_trend_reversal",       # EMA200ブレイクリテスト — 未検証, Sentinel蓄積
        "post_news_vol",               # ニュース後ボラ — WR=42.4%, Sentinel再検証
    }

    # ペア別SR感度: SAR高ペアに早逃げ余地
    _PAIR_SR_THRESHOLD = {
        "USD_JPY": 1.5,   # SAR=3.58 → 閾値緩和 (他ペア: デフォルト2.0)
    }

    # 高摩擦ペア指値強制: scalp成行エントリー禁止 (RT摩擦>3pip)
    _LIMIT_ONLY_SCALP = {"GBP_USD"}   # SAR=0.80 → 指値のみ許可

    # v6.1: Confidence-based Lot Scaling — サンプル数N段階制御
    # N不足の戦略への過剰集中を自動抑制 (過適合リスク管理)
    _N_LOT_TIERS = [
        (30, 2.5),   # N>=30: Proven Elite — フルブースト許可
        (10, 1.5),   # N>=10: Elite Candidate — 1.5x上限
        (0,  1.0),   # N<10:  Standard — ブースト無効 (1.0x上限)
    ]

    # v6.1: EUR/USD Profit Extender — ADX閾値ペア別
    _PE_ADX_THRESHOLD = {
        "EUR_USD": 25,  # EUR緩やかトレンド → 閾値緩和 (default 30)
    }
    _PE_DT_ELIGIBLE = {"orb_trap", "london_ny_swing"}  # DT利確延伸対象

    # v6.1: Strict Friction Guard — 指値失効後の追っかけブロック秒数
    _LIMIT_EXPIRE_CD_SEC = 180  # 3分間同方向再エントリー禁止

    # ══════════════════════════════════════════════════════════════
    # ── v6.4 SHIELD + 非対称攻撃 ──────────────────────────────
    # ══════════════════════════════════════════════════════════════
    _OANDA_LOT_CAP = 10000          # 絶対上限 (19000u災害防止)
    _OANDA_MODE_BLOCKED = frozenset({
        "daytrade_eur",              # EUR_USD DT 15m: OANDA WR=29.2%
        "daytrade_1h_eur",           # EUR_USD 1H: 未検証
        "daytrade_eurgbp",           # EUR_GBP DT: OANDA遮断
        "scalp_5m",                  # v6.8: Sentinel A/Bテスト (N≥50後に判断)
    })
    # v7.0: EUR DT SHIELD ホワイトリスト — MR系高EV戦略はモード遮断を免除
    # 根拠: orb_trap EUR BT 42t WR=71.4% EV=+0.482, htf_fbk EUR BT 32t WR=65.6% EV=+0.507
    # 安全: N<10 Safety で自動 Sentinel (0.01lot), auto_demotion + Kelly Cap 健在
    _SHIELD_EUR_DT_WHITELIST = frozenset({
        "orb_trap",                  # ORB Fakeout Reversal (MR, 独自タイミング窓)
        "htf_false_breakout",        # 1H SR False Breakout Fade (MR, MTFフィルター)
        "dt_bb_rsi_mr",              # BB+RSI MR (RANGE専用, EUR 74%がRANGE → 最適環境)
    })
    _QUICK_HARVEST_MULT = 0.85      # v6.8: 0.70→0.85 (DT WIN 7件の19.2pip利益漏出修復)
    _QUICK_HARVEST_EXEMPT = frozenset({
        ("gbp_deep_pullback", "GBP_USD"),   # 高WR戦略は全TP許可
        # v8.9: 方向性DT戦略はTP短縮不要（4-6h保有、BT WR=65-77%でTP到達率が高い）
        ("session_time_bias", "USD_JPY"),
        ("session_time_bias", "EUR_USD"),
        ("session_time_bias", "GBP_USD"),
        ("london_fix_reversal", "GBP_USD"),
        ("vix_carry_unwind", "USD_JPY"),    # イベント戦略、TP到達が前提
    })
    _FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"  # v6.3後のみ評価 (UTC明示)
    # v6.4: 50% TP到達時のTP延伸対象 (トレンドフォロー戦略のみ)
    _PE_50PCT_ELIGIBLE = frozenset({
        "vol_momentum_scalp", "confluence_scalp",
        "orb_trap", "london_ny_swing",
        "sr_fib_confluence", "htf_false_breakout",
        "gbp_deep_pullback", "turtle_soup",
        "trendline_sweep", "sr_break_retest",
        "adx_trend_continuation", "ema_cross",
        "squeeze_release_momentum",
        # v8.9: 新戦略追加
        "session_time_bias",         # セッションドリフト — トレンド継続時のTP延伸が有効
        "vol_spike_mr",              # スパイク回帰 — 回帰幅が大きい場合のTP延伸
        "london_fix_reversal",       # Fix後リバーサル — Fix効果の持続時に延伸
        "vix_carry_unwind",          # キャリー巻戻し — イベント駆動で大幅延伸が有効
        "xs_momentum",               # モメンタム — トレンド継続時の利益最大化
    })

    def _is_promoted(self, entry_type: str, instrument: str = "") -> bool:
        """戦略がOANDA実行可能か判定 (v6.2: ペア別ライフサイクル + N<10安全策)

        優先順位:
        1. Bridge戦略モード: "off"でブロック、"live"/"sentinel"で手動昇格
        2. _PAIR_DEMOTED: 特定ペアでのみ降格（ピンポイント敗兵淘汰）
        3. _PAIR_PROMOTED: 特定ペアで復活（グローバルFORCE_DEMOTED解除）
        4. _FORCE_DEMOTED: グローバル降格（手動モードで昇格可能）
        5. 自動降格判定: demoted ステータスでブロック
        6. デフォルト: OANDA送信許可（ただしN<10はSentinel lotで保護 → ロット計算側で実施）
        """
        _mode = self._oanda.get_strategy_mode(entry_type)

        # ── 明示的にOFFなら強制ブロック ──
        if _mode == "off":
            return False  # 手動停止

        # ── LIVE/SENTINELの明示指定: 手動昇格パス ──
        if _mode in ("live", "sentinel"):
            return True  # 全降格を上書き

        # ── ペア別降格: 特定ペアでのみEVマイナスの組み合わせ ──
        if instrument and (entry_type, instrument) in self._PAIR_DEMOTED:
            return False  # ペア限定降格 (静的)
        # v8.9: ランタイム自動ペア降格 (_evaluate_promotions で動的追加)
        _rt_pd = getattr(self, '_runtime_pair_demoted', set())
        if instrument and (entry_type, instrument) in _rt_pd:
            return False  # ペア限定降格 (動的)

        # ── ペア別復活: FORCE_DEMOTEDでもペア限定で復活 ──
        if instrument and (entry_type, instrument) in self._PAIR_PROMOTED:
            return True  # ペア限定昇格

        # ── _FORCE_DEMOTED: 明示的モード指定がない場合はブロック ──
        if entry_type in self._FORCE_DEMOTED:
            return False  # デモ継続・OANDA停止

        # ── 自動降格判定で demoted になった戦略もブロック ──
        info = self._promoted_types.get(entry_type)
        if info and info.get("status") == "demoted":
            return False

        # v6.2: OANDA送信は許可。N<10の未検証戦略はSentinel lotで保護
        # (ロット計算側の _is_sentinel 判定で 0.01lot 化される)
        return True

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

    def _get_strategy_kelly(self, entry_type: str, instrument: str) -> float:
        """
        Query learning engine stats for the strategy's Kelly fraction.
        Returns full_kelly value or None if insufficient data.
        v7.0: Used for Kelly-based lot cap in 3-Factor Model.
        """
        try:
            from modules.stats_utils import kelly_criterion
            # Fetch closed trades for this strategy
            closed = self._db.get_all_closed()
            strat_trades = [t for t in closed
                            if t.get("entry_type") == entry_type
                            and t.get("status") == "CLOSED"]
            if len(strat_trades) < 10:
                return None
            pnls = [float(t.get("pnl_pips", 0) or 0) for t in strat_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            if not wins or not losses:
                return None
            wr = len(wins) / len(pnls)
            avg_win = sum(wins) / len(wins)
            avg_loss = abs(sum(losses) / len(losses))
            result = kelly_criterion(wr, avg_win, avg_loss)
            return result.get("full_kelly", 0.0)
        except Exception:
            return None

    def _add_log(self, msg: str):
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")
        try:
            self._db.add_log(ts, msg)
        except Exception:
            pass
        print(f"[DemoTrader] {msg}")
