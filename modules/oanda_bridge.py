"""
OANDA Bridge — Business logic layer between demo trader and OANDA API.
Fire-and-forget: OANDA failures never block demo trading logic.
Enabled by OANDA_LIVE=true environment variable.

Strategy-level transfer control:
  - _strategy_overrides: per-strategy oanda_transfer_enabled flag (DB persistent)
  - Manual promotion: _FORCE_DEMOTED strategies can be re-enabled via override
  - Heartbeat: periodic OANDA account details check for health monitoring
"""
import os
import json
import logging
import threading
import time as _time
from modules.oanda_client import OandaClient

logger = logging.getLogger(__name__)

SUPPORTED_INSTRUMENTS = {
    "USD_JPY": "USD_JPY",
    "EUR_USD": "EUR_USD",
    "EUR_JPY": "EUR_JPY",
    "GBP_JPY": "GBP_JPY",
    "GBP_USD": "GBP_USD",
    "EUR_GBP": "EUR_GBP",
    "XAU_USD": "XAU_USD",
    "AUD_JPY": "AUD_JPY",
    "NZD_JPY": "NZD_JPY",
    "AUD_USD": "AUD_USD",
    "NZD_USD": "NZD_USD",
    "EUR_AUD": "EUR_AUD",
}

OANDA_EXECUTION_ENABLED = {
    "AUD_JPY": True,
    "NZD_JPY": True,
    "AUD_USD": True,
    "NZD_USD": True,
    "EUR_AUD": True,
}


def resolve_instrument(instrument: str) -> str:
    """Return the OANDA v20 instrument code for a supported FX pair."""
    if instrument not in SUPPORTED_INSTRUMENTS:
        raise KeyError(f"Unsupported OANDA instrument: {instrument}")
    return SUPPORTED_INSTRUMENTS[instrument]


class OandaBridge:
    def __init__(self, db=None):
        self._client = OandaClient()
        self._db = db  # DemoDB instance for settings persistence
        self._enabled = os.environ.get("OANDA_LIVE", "").lower() in ("true", "1", "yes")
        self._units = int(os.environ.get("OANDA_UNITS", "1000"))  # 1000 = 0.01 lot
        # OANDA連携対象モード — DB永続 > 環境変数 > 空(全許可)
        self._allowed_modes = self._load_allowed_modes()
        # demo_trade_id -> oanda_trade_id mapping (in-memory, also persisted in DB)
        self._trade_map = {}  # {demo_trade_id: oanda_trade_id}
        self._lock = threading.Lock()
        # エラーログ（直近20件保持、デバッグ用）
        self._recent_errors = []
        self._max_errors = 20
        # ── 戦略別OANDA転送フラグ (DB永続) ──
        # {"strategy_name": True/False} — Trueで _FORCE_DEMOTED を手動昇格
        self._strategy_overrides = self._load_strategy_overrides()
        # ── Heartbeat: OANDA APIヘルスチェック ──
        self._heartbeat = {
            "last_check": None,       # ISO timestamp
            "latency_ms": None,       # API response latency
            "balance": None,          # Account balance
            "nav": None,              # Net asset value
            "unrealized_pl": None,    # Unrealized P/L
            "margin_used": None,
            "margin_available": None,
            "open_trade_count": 0,
            "status": "unknown",      # "ok" / "error" / "unknown"
            "error": None,
        }
        self._heartbeat_lock = threading.Lock()
        # ── Execution Audit: トレードごとの実行記録 ──
        self._execution_audit = []    # 直近50件
        self._max_audit = 50
        # ── Daily Loss Gate (audit 2026-05-01 P0-2) ──
        # CLAUDE.md / roadmap-v2.1 に明記の "Scalp 1日損失 -2% で OANDA 転送停止"
        # を Live transmit-only halt として実装。demo_trader.MODE_CONFIG 側の
        # daily_loss_limit_pips=-99999 (実質無効) をブリッジレベルで補完する。
        # 既定値: -20 pip ≒ 1000pip ベース資本の -2%。env 上書き可。
        # 0 以下 / 設定なし → ゲート無効化 (後方互換)。
        try:
            self._daily_loss_limit_pips = float(
                os.environ.get("DAILY_LOSS_LIMIT_PIPS", "20")
            )
        except (TypeError, ValueError):
            self._daily_loss_limit_pips = 20.0
        self._daily_loss_cache_ts = 0.0
        self._daily_loss_cache_blocked = False
        self._daily_loss_cache_pnl = 0.0
        self._daily_loss_cache_ttl_s = 30.0  # 短めキャッシュ (DBヒット抑止)
        self._daily_loss_halt_day = ""  # once tripped, stay halted through UTC day
        self._daily_loss_lock = threading.Lock()

    # デフォルト全モード — MODE_CONFIGと同期（UI表示用）
    # v9.0: is_mode_allowed()は常にTrue。_ALL_MODESはUI状態表示のみに使用
    _ALL_MODES = {"scalp", "daytrade", "daytrade_1h", "scalp_eur", "daytrade_eur", "daytrade_1h_eur", "scalp_eurjpy",
                   "scalp_xau", "rnb_usdjpy", "daytrade_gbpusd", "daytrade_eurgbp", "daytrade_xau",
                   "daytrade_1h_audjpy", "daytrade_1h_nzdjpy", "daytrade_1h_audusd",
                   "daytrade_1h_nzdusd", "daytrade_1h_euraud",
                   "scalp_5m", "scalp_5m_eur", "scalp_5m_gbp",
                   "daytrade_eurjpy", "daytrade_gbpjpy"}  # v9.0: 全モード追加

    def _load_allowed_modes(self) -> set:
        """DB永続 > 環境変数 > 全モード許可 の優先順で読み込み.
        _ALL_MODES に新モードが追加された場合、DB保存済みリストに自動マージする。"""
        # 1. DBに保存済みの設定を優先
        if self._db:
            try:
                saved = self._db.get_oanda_setting("allowed_modes", "")
                if saved:
                    modes = set(m.strip() for m in saved.split(",") if m.strip())
                    # 新モード自動マージ: _ALL_MODES にあるがDBに無いモードを追加
                    new_modes = self._ALL_MODES - modes
                    if new_modes:
                        modes |= new_modes
                        logger.info(f"[OandaBridge] Auto-merged new modes: {sorted(new_modes)}")
                    logger.info(f"[OandaBridge] Loaded modes from DB: {sorted(modes)}")
                    return modes
            except Exception as e:
                logger.warning(f"[OandaBridge] DB mode load failed: {e}")
        # 2. 環境変数
        _modes_env = os.environ.get("OANDA_MODES", "")
        if _modes_env:
            return set(m.strip() for m in _modes_env.split(",") if m.strip())
        # 3. デフォルト全モード許可
        return set(self._ALL_MODES)

    def _save_allowed_modes(self):
        """現在のallowed_modesをDBに永続化."""
        if not self._db:
            return
        try:
            val = ",".join(sorted(self._allowed_modes)) if self._allowed_modes else ""
            self._db.set_oanda_setting("allowed_modes", val)
        except Exception as e:
            logger.warning(f"[OandaBridge] DB mode save failed: {e}")

    # ── Strategy-level OANDA transfer overrides ─────

    def _load_strategy_overrides(self) -> dict:
        """DB永続された戦略別OANDA転送フラグを読み込み."""
        if not self._db:
            return {}
        try:
            saved = self._db.get_oanda_setting("strategy_overrides", "")
            if saved:
                return json.loads(saved)
        except Exception as e:
            logger.warning(f"[OandaBridge] Strategy overrides load failed: {e}")
        return {}

    def _save_strategy_overrides(self):
        """戦略別OANDA転送フラグをDBに永続化."""
        if not self._db:
            return
        try:
            val = json.dumps(self._strategy_overrides)
            self._db.set_oanda_setting("strategy_overrides", val)
        except Exception as e:
            logger.warning(f"[OandaBridge] Strategy overrides save failed: {e}")

    # ── Tri-state: "live" / "sentinel" / "off" ──────────
    # Legacy compat: True → "live", False → "off"

    def _normalize_mode(self, val) -> str:
        """内部値を正規化: True→"live", False→"off", str→そのまま."""
        if val is True:
            return "live"
        if val is False:
            return "off"
        if isinstance(val, str) and val in ("live", "sentinel", "off"):
            return val
        return "auto"  # None / 不明 → 自動判定

    def get_strategy_mode(self, entry_type: str) -> str:
        """戦略のOANDA転送モードを返す。
        "live"     — フルロット転送
        "sentinel" — 0.01lot固定（データ収集モード）
        "off"      — OANDA転送停止
        "auto"     — 未設定（自動昇降格判定に委ねる）
        """
        raw = self._strategy_overrides.get(entry_type)
        return self._normalize_mode(raw)

    def is_strategy_enabled(self, entry_type: str) -> bool:
        """戦略のOANDA転送が有効か判定（"live"/"sentinel"でTrue）。
        明示的な"off"/Falseの場合のみブロック。
        "live"/True は _FORCE_DEMOTED を上書きして手動昇格を許可。
        """
        mode = self.get_strategy_mode(entry_type)
        if mode == "off":
            return False
        if mode in ("live", "sentinel"):
            return True
        return True  # "auto" → デフォルト許可（_is_promotedで最終判定）

    def is_strategy_sentinel(self, entry_type: str) -> bool:
        """戦略がSENTINELモード（0.01lot固定）か判定。"""
        return self.get_strategy_mode(entry_type) == "sentinel"

    def set_strategy_mode(self, entry_type: str, mode: str):
        """戦略のOANDA転送モードを設定・永続化。
        mode: "live" / "sentinel" / "off" / "auto"(=削除)
        """
        if mode == "auto":
            self._strategy_overrides.pop(entry_type, None)
        else:
            self._strategy_overrides[entry_type] = mode
        self._save_strategy_overrides()
        _labels = {"live": "LIVE（実弾）", "sentinel": "SENTINEL（0.01lot観測）",
                    "off": "OFF（停止）", "auto": "AUTO（自動判定）"}
        logger.info(f"[OandaBridge] Strategy mode: {entry_type} → {_labels.get(mode, mode)}")

    def set_strategy_enabled(self, entry_type: str, enabled: bool):
        """後方互換: ON/OFFトグル → live/off."""
        self.set_strategy_mode(entry_type, "live" if enabled else "off")

    def get_strategy_overrides(self) -> dict:
        """現在の戦略別転送フラグを返す（正規化済み）."""
        return {k: self._normalize_mode(v) for k, v in self._strategy_overrides.items()}

    # ── Execution Audit ───────────────────────────────

    def _add_audit(self, demo_trade_id: str, entry_type: str,
                   is_live: bool, bridge_status: str, block_reason: str,
                   direction: str = "", instrument: str = "",
                   units: int = 0, oanda_trade_id: str = "",
                   sr_meta=None):
        """トレード実行時のOANDA連携監査記録を追加 (インメモリ + DB永続化)."""
        from datetime import datetime, timezone
        _sr = sr_meta or {}
        _sr_is_strong = _sr.get("is_strong")
        if _sr_is_strong is not None:
            _sr_is_strong = int(bool(_sr_is_strong))
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "demo_trade_id": demo_trade_id,
            "entry_type": entry_type,
            "direction": direction,
            "instrument": instrument,
            "units": units,
            "is_live": is_live,
            "bridge_status": bridge_status,
            "block_reason": block_reason,
            "oanda_trade_id": oanda_trade_id,
            "sr_strength": _sr.get("strength"),
            "sr_touches": _sr.get("touches"),
            "sr_days_span": _sr.get("days_span"),
            "sr_is_strong": _sr_is_strong,
            "sr_distance_atr": _sr.get("distance_atr"),
        }
        # インメモリキャッシュ (後方互換)
        self._execution_audit.append(entry)
        if len(self._execution_audit) > self._max_audit:
            self._execution_audit = self._execution_audit[-self._max_audit:]
        # DB永続化 (fire-and-forget — DB障害でもトレードを止めない)
        if self._db:
            try:
                self._db.save_oanda_audit(entry)
            except Exception as e:
                logger.warning(f"[OandaBridge] Audit DB write failed: {e}")
        return entry

    def get_execution_audit(self, limit: int = 20) -> list:
        """直近の実行監査記録を返す (DB優先、フォールバック: インメモリ)."""
        if self._db:
            try:
                return self._db.get_oanda_audit(limit=limit)
            except Exception as e:
                logger.warning(f"[OandaBridge] Audit DB read failed: {e}")
        return self._execution_audit[-limit:]

    def get_execution_audit_count(self) -> int:
        """監査記録の総件数を返す (DB優先)."""
        if self._db:
            try:
                return self._db.get_oanda_audit_count()
            except Exception:
                pass
        return len(self._execution_audit)

    # ── Heartbeat: OANDA API Health Check ─────────────

    def run_heartbeat(self):
        """OANDA APIへのヘルスチェック (Account Details取得 + レイテンシ計測)。
        60秒間隔で外部から呼び出される想定。"""
        from datetime import datetime, timezone
        with self._heartbeat_lock:
            if not self.active:
                self._heartbeat.update({
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "status": "inactive",
                    "error": "OANDA not active (enabled={}, configured={})".format(
                        self._enabled, self._client.configured),
                    "latency_ms": None,
                })
                return self._heartbeat

            _start = _time.monotonic()
            try:
                ok, data = self._client.get_account()
                _elapsed = (_time.monotonic() - _start) * 1000  # ms

                if ok:
                    acct = data.get("account", data)
                    self._heartbeat.update({
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "latency_ms": round(_elapsed, 1),
                        "balance": acct.get("balance"),
                        "nav": acct.get("NAV"),
                        "unrealized_pl": acct.get("unrealizedPL"),
                        "margin_used": acct.get("marginUsed"),
                        "margin_available": acct.get("marginAvailable"),
                        "open_trade_count": acct.get("openTradeCount", 0),
                        "status": "ok",
                        "error": None,
                    })
                    logger.debug(
                        f"[OandaBridge] Heartbeat OK: latency={_elapsed:.0f}ms "
                        f"balance={acct.get('balance')} NAV={acct.get('NAV')}"
                    )
                else:
                    _elapsed = (_time.monotonic() - _start) * 1000
                    _err = str(data.get("message", data))[:200]
                    self._heartbeat.update({
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "latency_ms": round(_elapsed, 1),
                        "status": "error",
                        "error": _err,
                    })
                    self._log_error(f"Heartbeat error: {_err}")
            except Exception as e:
                _elapsed = (_time.monotonic() - _start) * 1000
                self._heartbeat.update({
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": round(_elapsed, 1),
                    "status": "error",
                    "error": str(e)[:200],
                })
                self._log_error(f"Heartbeat exception: {e}")

        return self._heartbeat

    def get_heartbeat(self) -> dict:
        """最新のハートビート情報を返す（display付き）."""
        with self._heartbeat_lock:
            hb = dict(self._heartbeat)
        # ── フォーマット済みディスプレイ文字列 ──
        _status = hb.get("status", "unknown").upper()
        _latency = hb.get("latency_ms")
        _nav = hb.get("nav")
        _balance = hb.get("balance")
        if _status == "OK" and _latency is not None:
            _nav_disp = f"¥{float(_nav):,.0f}" if _nav else "N/A"
            hb["display"] = (
                f"OANDA: CONNECTED / LATENCY: {_latency:.0f}ms / NAV: {_nav_disp}"
            )
        elif _status == "INACTIVE":
            hb["display"] = "OANDA: INACTIVE (not configured)"
        elif _status == "ERROR":
            hb["display"] = f"OANDA: ERROR / {hb.get('error', 'unknown')[:60]}"
        else:
            hb["display"] = "OANDA: UNKNOWN (awaiting first heartbeat)"
        return hb

    # ── Core Properties ───────────────────────────────

    @property
    def active(self) -> bool:
        """True if OANDA integration is enabled and configured."""
        return self._enabled and self._client.configured

    def is_mode_allowed(self, mode: str) -> bool:
        """v9.0: 常にTrue — OANDA転送可否はKelly Gate/MC Ruin/3層Tierで制御。
        モード単位の手動ON/OFFはN蓄積を阻害するため廃止。
        UIボタンは監視用に残すが、転送判定には影響しない。"""
        return True

    def _log_error(self, msg: str):
        from datetime import datetime, timezone
        entry = {"time": datetime.now(timezone.utc).isoformat(), "msg": msg}
        self._recent_errors.append(entry)
        if len(self._recent_errors) > self._max_errors:
            self._recent_errors = self._recent_errors[-self._max_errors:]

    @property
    def status(self) -> dict:
        return {
            "enabled": self._enabled,
            "configured": self._client.configured,
            "active": self.active,
            "units": self._units,
            "allowed_modes": sorted(self._allowed_modes) if self._allowed_modes else "all",
            "open_trades": len(self._trade_map),
            "recent_errors": self._recent_errors[-5:],
            "heartbeat": self.get_heartbeat(),
            "strategy_overrides": self.get_strategy_overrides(),
            "execution_audit_count": self.get_execution_audit_count(),
        }

    def set_trade_mapping(self, demo_id: str, oanda_id: str):
        """Restore mapping from DB (e.g. after deploy restart)."""
        with self._lock:
            self._trade_map[demo_id] = oanda_id

    # ── Fire-and-Forget Wrappers ──────────────────────

    def _fire(self, fn, *args, **kwargs):
        """Run OANDA operation in background thread. Never blocks caller."""
        def _run():
            try:
                fn(*args, **kwargs)
            except Exception as e:
                _msg = f"fire-and-forget error: {e}"
                logger.error(f"[OandaBridge] {_msg}")
                self._log_error(_msg)  # APIからも見えるように
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ── Daily Loss Gate (audit 2026-05-01 P0-2) ───────

    def _check_daily_loss_gate(self) -> tuple[bool, float]:
        """Return (blocked, today_pnl_pip).

        Transmit-only halt: when today's Live `total_pnl` (is_shadow=0,
        exclude_xau, exclude_seed) drops below -DAILY_LOSS_LIMIT_PIPS, OANDA
        transmits are blocked for the rest of the UTC day. demo_trader keeps
        running so the day's data continues to accumulate (per audit
        Pillar 4.2 user-confirmed default).

        Cached for `_daily_loss_cache_ttl_s` to keep the hot path cheap.
        Errors are non-fatal: the gate fails OPEN (transmit allowed) so a
        DB hiccup never silently kills live trading. The audit log records
        the block at the call site.
        """
        if self._daily_loss_limit_pips <= 0 or self._db is None:
            return False, 0.0
        import time as _time
        from datetime import datetime, timezone
        now = _time.time()
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._daily_loss_lock:
            if self._daily_loss_halt_day == today_iso:
                return True, self._daily_loss_cache_pnl
            if (now - self._daily_loss_cache_ts) < self._daily_loss_cache_ttl_s:
                return self._daily_loss_cache_blocked, self._daily_loss_cache_pnl
        # Compute outside the lock — DB call may take >1s under contention.
        try:
            stats = self._db.get_stats(
                date_from=today_iso,
                exclude_shadow=True,
                exclude_xau=True,
                exclude_seed=True,
                date_field="exit_time",
            )
            pnl = float(stats.get("total_pnl", 0.0) or 0.0)
        except Exception as e:
            logger.warning(f"[OandaBridge] daily-loss-gate DB read failed: {e}")
            return False, 0.0
        blocked = pnl <= -float(self._daily_loss_limit_pips)
        with self._daily_loss_lock:
            self._daily_loss_cache_ts = now
            self._daily_loss_cache_blocked = blocked
            self._daily_loss_cache_pnl = pnl
            if blocked:
                self._daily_loss_halt_day = today_iso
        return blocked, pnl

    # ── Open Trade ────────────────────────────────────

    def open_trade(self, demo_trade_id: str, direction: str,
                   sl: float, tp: float,
                   mode: str = "",
                   instrument: str = "USD_JPY",
                   callback=None,
                   units: int = 0,
                   log_callback=None,
                   lot_label: str = "",
                   signal_price: float = 0.0):
        """Place OANDA market order mirroring a demo trade.
        callback(demo_trade_id, oanda_trade_id) called on success for DB persistence.
        units: override lot size (0 = use default self._units).
        log_callback: fn(msg) for 🔗 OANDA log output (runs in background thread).
        lot_label: display label for lot multiplier (e.g. "🚀1.3x").
        """
        if not self.active:
            return
        try:
            instrument = resolve_instrument(instrument)
        except KeyError as e:
            logger.error(f"[OandaBridge] {e}")
            if log_callback:
                log_callback(f"🔗 OANDA: [BLOCKED] unsupported instrument — {instrument}")
            return
        if not self.is_mode_allowed(mode):
            logger.debug(f"[OandaBridge] mode={mode} not in allowed_modes, skip")
            return

        # Daily loss gate (audit 2026-05-01 P0-2). Transmit-only halt: the
        # demo trade is still recorded by the caller; we only refuse to
        # forward to OANDA. demo_trader continues to accumulate today's
        # data so the close of the day is not blinded.
        try:
            _dl_blocked, _dl_pnl = self._check_daily_loss_gate()
        except Exception:
            _dl_blocked, _dl_pnl = False, 0.0
        if _dl_blocked:
            _reason = (
                f"daily_loss_limit({_dl_pnl:.1f}pip<=-{self._daily_loss_limit_pips:.1f}pip)"
            )
            logger.warning(f"[OandaBridge] OPEN BLOCKED ({_reason}) "
                           f"demo={demo_trade_id} mode={mode} {direction} {instrument}")
            try:
                self._add_audit(
                    demo_trade_id=demo_trade_id, entry_type=mode,
                    is_live=False, bridge_status="blocked",
                    block_reason=_reason,
                    direction=direction, instrument=instrument,
                    units=(units if units > 0 else self._units),
                )
            except Exception as e:
                logger.warning(f"[OandaBridge] audit write failed during daily-loss block: {e}")
            if log_callback:
                log_callback(f"🔗 OANDA: [HALT] {_reason} — {direction} {instrument} not transmitted")
            return

        # Persist a pending row BEFORE the broker call (audit P0-6).
        # The row stays 'pending' until either pending_op_mark_done or
        # pending_op_mark_failed is called below; restart-recovery
        # surfaces any 'pending' rows that survived a crash.
        _pending_id = None
        if self._db is not None:
            try:
                _pending_id = self._db.pending_op_create(
                    "open", demo_trade_id,
                    instrument=instrument, direction=direction,
                    units=(units if units > 0 else self._units),
                    sl=sl, tp=tp,
                )
            except Exception as e:
                logger.warning(f"[OandaBridge] pending_op_create failed: {e}")

        def _do():
            import time as _time
            side = "buy" if direction == "BUY" else "sell"
            _lot = units if units > 0 else self._units
            _lot_disp = f"{_lot}u({_lot/10000:.2f}lot)"
            _latency_ms = 0
            ok, data = None, {}
            _attempts_made = 0
            for _attempt in range(3):
                _attempts_made = _attempt + 1
                _t0 = _time.monotonic()
                ok, data = self._client.market_order(
                    side=side,
                    units=_lot,
                    instrument=instrument,
                    stop_loss=sl,
                    take_profit=tp,
                )
                _latency_ms = round((_time.monotonic() - _t0) * 1000)
                if ok:
                    break
                # Transient errors: retry with backoff (max 2 retries)
                _err_code = data.get("error")
                if _err_code in (429, 503, "timeout", "network") and _attempt < 2:
                    _time.sleep(1 * (_attempt + 1))
                    logger.warning(f"[OandaBridge] OPEN retry {_attempt+1}/2 "
                                   f"{side} {instrument} ({_err_code})")
                    continue
                break  # Non-retryable error, stop immediately
            if ok:
                # v20: orderFillTransaction.tradeOpened.tradeID
                _fill = data.get("orderFillTransaction", {})
                oanda_id = str(_fill.get("tradeOpened", {}).get("tradeID", ""))
                _price = _fill.get("price", "")
                if oanda_id:
                    with self._lock:
                        self._trade_map[demo_trade_id] = oanda_id
                    logger.info(f"[OandaBridge] OPEN {side} → OANDA #{oanda_id} "
                                f"(demo={demo_trade_id})")
                    if callback:
                        callback(demo_trade_id, oanda_id)
                    # ── 🔗 OANDA 連携ラベル: 約定成功 ──
                    if log_callback:
                        log_callback(
                            f"🔗 OANDA: [FILLED] #{oanda_id} {side.upper()} {instrument} "
                            f"@ {_price} | {_lot_disp} {lot_label}"
                        )
                    # ── v6.4 TELEMETRY: 期待価格 vs 約定価格 + レイテンシ ──
                    if log_callback and signal_price and _price:
                        try:
                            _fill_px = float(_price)
                            _slip_raw = abs(_fill_px - signal_price)
                            _is_jpy_xau = "JPY" in instrument or "XAU" in instrument
                            _pip_m = 100 if _is_jpy_xau else 10000
                            _slip_pips = _slip_raw * _pip_m
                            log_callback(
                                f"[TELEMETRY] signal={signal_price:.5g} "
                                f"fill={_fill_px:.5g} "
                                f"slip={_slip_pips:.1f}pip "
                                f"latency={_latency_ms}ms"
                            )
                        except (ValueError, TypeError):
                            pass
                    elif log_callback:
                        log_callback(f"[TELEMETRY] latency={_latency_ms}ms")
                    # Update audit with OrderID
                    self._add_audit(
                        demo_trade_id=demo_trade_id, entry_type=mode,
                        is_live=True, bridge_status="filled",
                        block_reason="",
                        direction=direction, instrument=instrument,
                        units=_lot, oanda_trade_id=oanda_id,
                    )
                    if _pending_id is not None and self._db is not None:
                        try:
                            self._db.pending_op_mark_done(_pending_id, oanda_id)
                        except Exception as e:
                            logger.warning(f"[OandaBridge] pending_op_mark_done failed: {e}")
                else:
                    # 注文は成功したがtradeIDが取れない
                    _msg = f"OPEN {side} ok but no tradeID: {json.dumps(data)[:300]}"
                    logger.warning(f"[OandaBridge] {_msg}")
                    self._log_error(_msg)
                    if log_callback:
                        log_callback(f"🔗 OANDA: [WARN] Order ok but no tradeID — {instrument}")
                    if _pending_id is not None and self._db is not None:
                        try:
                            self._db.pending_op_mark_failed(
                                _pending_id, _msg, attempts=_attempts_made)
                        except Exception as e:
                            logger.warning(f"[OandaBridge] pending_op_mark_failed failed: {e}")
            else:
                _err = str(data.get("message", data))[:120]
                _msg = f"OPEN {side} FAILED (demo={demo_trade_id}, mode={mode}, sl={sl}, tp={tp}): {json.dumps(data)[:300]}"
                logger.error(f"[OandaBridge] {_msg}")
                self._log_error(_msg)
                # ── 🔗 OANDA 連携ラベル: 約定失敗 ──
                if log_callback:
                    log_callback(
                        f"🔗 OANDA: [FAILED] {side.upper()} {instrument} "
                        f"{_lot_disp} — {_err}"
                    )
                if _pending_id is not None and self._db is not None:
                    try:
                        self._db.pending_op_mark_failed(
                            _pending_id, _err, attempts=_attempts_made)
                    except Exception as e:
                        logger.warning(f"[OandaBridge] pending_op_mark_failed failed: {e}")

        self._fire(_do)

    # ── Close Trade ───────────────────────────────────

    def close_trade(self, demo_trade_id: str, reason: str = ""):
        """Close OANDA trade corresponding to demo trade."""
        if not self.active:
            return

        oanda_id = self._trade_map.get(demo_trade_id)
        if not oanda_id:
            logger.debug(f"[OandaBridge] No OANDA mapping for demo={demo_trade_id}, skip close")
            return

        # P0-6: pending row for the close as well.
        _pending_id = None
        if self._db is not None:
            try:
                _pending_id = self._db.pending_op_create(
                    "close", demo_trade_id, direction="", units=0,
                )
            except Exception as e:
                logger.warning(f"[OandaBridge] pending_op_create(close) failed: {e}")

        def _do():
            _attempts_made = 0
            for attempt in range(3):
                _attempts_made = attempt + 1
                ok, data = self._client.close_trade(oanda_id)
                if ok:
                    with self._lock:
                        self._trade_map.pop(demo_trade_id, None)
                    logger.info(f"[OandaBridge] CLOSE OANDA #{oanda_id} "
                                f"(demo={demo_trade_id}, reason={reason})")
                    if _pending_id is not None and self._db is not None:
                        try:
                            self._db.pending_op_mark_done(_pending_id, oanda_id)
                        except Exception as e:
                            logger.warning(f"[OandaBridge] pending_op_mark_done(close) failed: {e}")
                    return
                # OANDA側で既にクローズ済みならマッピング削除
                err_code = data.get("error")
                if err_code == 404:
                    with self._lock:
                        self._trade_map.pop(demo_trade_id, None)
                    logger.info(f"[OandaBridge] CLOSE #{oanda_id} already closed (404), mapping removed")
                    if _pending_id is not None and self._db is not None:
                        try:
                            self._db.pending_op_mark_done(_pending_id, oanda_id)
                        except Exception as e:
                            logger.warning(f"[OandaBridge] pending_op_mark_done(close-404) failed: {e}")
                    return
                # Transient errors: retry after backoff
                if err_code in (429, 503, "timeout", "network") and attempt < 2:
                    import time
                    time.sleep(2 * (attempt + 1))
                    logger.warning(f"[OandaBridge] CLOSE retry {attempt+1}/2 #{oanda_id} ({err_code})")
                    continue
                # Non-retryable error
                _msg = f"CLOSE failed #{oanda_id} (demo={demo_trade_id}): {json.dumps(data)[:200]}"
                logger.error(f"[OandaBridge] {_msg}")
                self._log_error(_msg)
                if _pending_id is not None and self._db is not None:
                    try:
                        self._db.pending_op_mark_failed(
                            _pending_id, _msg, attempts=_attempts_made)
                    except Exception as e:
                        logger.warning(f"[OandaBridge] pending_op_mark_failed(close) failed: {e}")
                return

        self._fire(_do)

    # ── Pending ops recovery (audit P0-6) ─────────────

    def recover_pending_ops(self) -> dict:
        """Surface pending_oanda_ops rows that did not reach a terminal state.

        Called once from app.py startup. Returns a summary dict. Side effects:
          - 'pending' rows older than 5 minutes at startup are flagged 'failed'
            with a 'startup_orphan' marker so they don't keep the queue dirty.
          - 'failed' rows are NOT auto-replayed (a stale signal could be
            economically wrong); we just emit a warning so an operator can
            triage via the API.
        Returns: {"pending": N, "stale_marked_failed": M, "failed": K}
        """
        if self._db is None:
            return {"pending": 0, "stale_marked_failed": 0, "failed": 0}
        try:
            pending = self._db.pending_op_list("pending", limit=500)
            failed = self._db.pending_op_list("failed", limit=500)
        except Exception as e:
            logger.warning(f"[OandaBridge] recover_pending_ops list failed: {e}")
            return {"pending": 0, "stale_marked_failed": 0, "failed": 0}
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(minutes=5)
        stale_marked = 0
        for row in pending:
            try:
                created = datetime.fromisoformat(
                    str(row.get("created_at", "")).replace("Z", "+00:00")
                )
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if created < stale_cutoff:
                try:
                    self._db.pending_op_mark_failed(
                        int(row["id"]),
                        "startup_orphan: in-flight when previous process died",
                        attempts=int(row.get("attempts", 0) or 0),
                    )
                    stale_marked += 1
                except Exception as e:
                    logger.warning(f"[OandaBridge] mark stale orphan failed: {e}")
        if failed:
            logger.warning(
                f"[OandaBridge] {len(failed)} pending_oanda_ops rows are still "
                f"in 'failed' state — operator reconciliation required"
            )
        if pending:
            logger.warning(
                f"[OandaBridge] {len(pending)} pending_oanda_ops rows survived "
                f"restart ({stale_marked} marked failed as startup_orphan)"
            )
        return {
            "pending": len(pending),
            "stale_marked_failed": stale_marked,
            "failed": len(failed),
        }

    # ── Modify SL ─────────────────────────────────────

    def modify_sl(self, demo_trade_id: str, new_sl: float,
                  instrument: str = "USD_JPY"):
        """Update stop loss on OANDA trade (for trailing stop / BE moves)."""
        if not self.active:
            return

        oanda_id = self._trade_map.get(demo_trade_id)
        if not oanda_id:
            return

        def _do():
            ok, data = self._client.modify_trade(oanda_id, stop_loss=new_sl,
                                                  instrument=instrument)
            if ok:
                logger.info(f"[OandaBridge] MODIFY SL → {new_sl:.3f} "
                            f"OANDA #{oanda_id} (demo={demo_trade_id})")
            else:
                logger.error(f"[OandaBridge] MODIFY SL failed #{oanda_id}: {data}")

        self._fire(_do)

    def modify_sl_sync(self, demo_trade_id: str, new_sl: float,
                       instrument: str = "USD_JPY") -> bool:
        """Synchronous SL modification — returns True on success.
        v6.4: Pyramiding用。SL変更成功を確認してから追加ポジションを開設するため同期版。
        """
        if not self.active:
            return False
        with self._lock:
            oanda_id = self._trade_map.get(demo_trade_id)
        if not oanda_id:
            return False
        try:
            ok, data = self._client.modify_trade(oanda_id, stop_loss=new_sl,
                                                  instrument=instrument)
            if ok:
                logger.info(f"[OandaBridge] MODIFY SL (sync) → {new_sl:.3f} "
                            f"OANDA #{oanda_id} (demo={demo_trade_id})")
                return True
            else:
                logger.error(f"[OandaBridge] MODIFY SL (sync) failed #{oanda_id}: {data}")
                return False
        except Exception as e:
            logger.error(f"[OandaBridge] MODIFY SL (sync) error: {e}")
            return False

    # ── Get Account Info ──────────────────────────────

    def get_account_info(self) -> dict:
        """Get OANDA account info (balance, margin, etc.)."""
        if not self.active:
            return {"error": "OANDA not active"}
        ok, data = self._client.get_account()
        if ok:
            return data
        return {"error": data.get("message", "unknown")}

    # ── Sync trade map from DB on startup ─────────────

    def restore_mappings(self, mappings: list):
        """Restore demo->OANDA trade mappings from DB.
        mappings: list of (demo_trade_id, oanda_trade_id) tuples
        """
        with self._lock:
            for demo_id, oanda_id in mappings:
                if oanda_id:
                    self._trade_map[demo_id] = oanda_id
        if self._trade_map:
            logger.info(f"[OandaBridge] Restored {len(self._trade_map)} trade mappings")
