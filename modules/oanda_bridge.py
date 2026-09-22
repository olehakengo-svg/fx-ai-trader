from __future__ import annotations

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
import math
import threading
import time as _time
from decimal import Decimal
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
    "USD_CAD": "USD_CAD",
    "USD_CHF": "USD_CHF",
    "AUD_JPY": "AUD_JPY",
    "NZD_JPY": "NZD_JPY",
    "AUD_USD": "AUD_USD",
    "NZD_USD": "NZD_USD",
    "EUR_AUD": "EUR_AUD",
}

OANDA_EXECUTION_ENABLED = {
    "USD_CAD": True,
    "USD_CHF": True,
    "AUD_JPY": True,
    "NZD_JPY": True,
    "AUD_USD": True,
    "NZD_USD": True,
    "EUR_AUD": True,
}


# weekend_gap 執行契約(B) §4.4 (AMENDMENT 2026-09-10, rule:R1 user 承認):
# tradeable 確認後の FOK が MARKET_HALTED cancel で返った場合 (解除直後 race)
# の限定再送までの待機秒。凍結値 30s — tests は monkeypatch で短縮する。
HALT_RACE_RESEND_DELAY_SEC = 30.0


# ── SL replacement storm guard (rule:R3 構造バグ、2026-09-22) ─────────────
# 根拠: storm 4 (#859468 kalman_d7, 2026-09-11) = SL replacement 16,837 回 /
# 33,675 tx / 2h51m @3.28 tx/s、SL 価格が 0.001 (1/10 pip) 刻みで振動
# (154.349⇄154.350) し、さらに BUY 建玉で 154.350→154.270 と 8 pip 不利側へ
# 移動 (単調性違反)。#893161 (carry_dip) では 3 回目の replacement が
# SL を 1.2 pip 不利側に置いて同一秒で自己約定。
# ⇒ 等値 idempotency 単独では止まらない。直交 4 点 (KB kalman-d7 09-16 訂正版):
#   (1) 累積 tx breaker (窓あたり累積、瞬間レートではない — 平常 trail も
#       ~1.5–3 cycle/s で storm と同帯)  (2) 冪等 (同値再送 skip)
#   (3) 単調性 (BUY で SL↓ / SELL で SL↑ を reject)  (4) 1 pip dead-band
# 既定は検知のみ (カウンタ + ログ)。STORM_GUARD_ENFORCE=1 で guard 本体が
# 有効になる。設計/CF pin 一覧: wiki/analyses/storm-guard-design-2026-09-22.md
STORM_GUARD_DEFAULTS = {
    "deadband_pips": 1.0,      # STORM_GUARD_DEADBAND_PIPS
    "max_tx_per_hour": 50,     # STORM_GUARD_MAX_TX_PER_HOUR (0 = 無効)
    "max_tx_per_day": 200,     # STORM_GUARD_MAX_TX_PER_DAY  (0 = 無効)
}
# 検知ログの抑制: trade × reason ごとに最初の N 件、以後は every M 件目のみ
# (ログ storm で tx storm を置き換えないため)
STORM_GUARD_LOG_FIRST_N = 3
STORM_GUARD_LOG_EVERY_M = 100
_TRUTHY = ("1", "true", "yes", "on")
# check に「baseline を自分で計算せよ」を伝える sentinel (None は「baseline なし」の実値)
_UNSET = object()


def _storm_pip_size(instrument: str) -> float:
    """pip 単位 — demo_trader の `100 if JPY/XAU else 10000` 換算と同一規約。"""
    inst = (instrument or "").upper()
    return 0.01 if ("JPY" in inst or "XAU" in inst) else 0.0001


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
        # ── SL replacement storm guard (R3, 2026-09-22) ──
        # per-trade in-memory state: {demo_trade_id: {"direction", "confirmed_sl", "pending",
        #   "sent_ts": [monotonic...], "sent_total", "tripped", "warned",
        #   "counts": {reason: n}}}. 永続化なし (storm 自体が process 内の
        # trail 状態に依存し、再起動で消える — 再起動後は DB 行から direction /
        # sl を lazy seed する)。
        self._storm_state: dict = {}
        # RLock: gate は「評価 → 予約 (pending / sent_ts 更新)」を 1 つの
        # critical section で行い、fire-and-forget 経路の同時到達で同じ古い
        # baseline を見て全部通る競合 (PR #287 review P2) を塞ぐ。check 内の
        # counter 更新も同 lock を取るため再入可能が必要。
        self._storm_lock = threading.RLock()
        self._storm_enforce = (
            os.environ.get("STORM_GUARD_ENFORCE", "").strip().lower() in _TRUTHY
        )
        # 単調性の明示 opt-out (BE/trail は有利側にしか動かさない契約。例外が
        # 必要なら env で明示)。既定 = reject。
        self._storm_allow_loosen = (
            os.environ.get("STORM_GUARD_ALLOW_SL_LOOSEN", "").strip().lower() in _TRUTHY
        )
        self._storm_cfg = dict(STORM_GUARD_DEFAULTS)
        for _k, _env in (("deadband_pips", "STORM_GUARD_DEADBAND_PIPS"),
                         ("max_tx_per_hour", "STORM_GUARD_MAX_TX_PER_HOUR"),
                         ("max_tx_per_day", "STORM_GUARD_MAX_TX_PER_DAY")):
            _raw = os.environ.get(_env)
            if _raw is None or _raw == "":
                continue
            try:
                self._storm_cfg[_k] = float(_raw) if _k == "deadband_pips" else int(float(_raw))
            except (TypeError, ValueError):
                logger.warning(f"[OandaBridge][STORM_GUARD] bad {_env}={_raw!r}, using default")
        # 集計 (API/status 露出用): 検知 = would_skip (検知のみモードで送信された
        # もの) / skipped = enforce で実際に止めたもの
        self._storm_totals: dict = {
            "evaluated": 0, "sent": 0,
            # serialize = 送信直列化 (detected: 検知のみモードで「待つはずだった」件数 /
            # skipped: enforce で順番待ち timeout により drop した件数)
            "detected": {"breaker": 0, "idempotent": 0, "monotonic": 0, "deadband": 0, "serialize": 0},
            "skipped": {"breaker": 0, "idempotent": 0, "monotonic": 0, "deadband": 0, "serialize": 0},
            "unknown_direction": 0, "breaker_trips": 0, "failed": 0,
            # ambiguous_failures = 応答曖昧な失敗 / reconciled = broker 照会で解消 / unresolved = 未解消のまま
            "ambiguous_failures": 0, "reconciled": 0, "unresolved": 0, "reconcile_discarded": 0,
            # observed_changed = 曖昧中に第三の値を観測 (confirmed_sl は更新、曖昧さは維持)
            # coalesced = enforce の fire-and-forget で queue 末尾に畳み込んだ要求数
            # local_backoff = client のローカル 429 backoff 中で送らなかった要求数 (窓に入れない)
            "observed_changed": 0, "coalesced": 0, "local_backoff": 0,
            # deferred = enforce で baseline が未確認だったため送信順到来まで判定を保留した件数
            "deferred": 0,
        }

    # デフォルト全モード — MODE_CONFIGと同期（UI表示用）
    # v9.0: is_mode_allowed()は常にTrue。_ALL_MODESはUI状態表示のみに使用
    _ALL_MODES = {"scalp", "daytrade", "daytrade_1h", "scalp_eur", "daytrade_eur", "daytrade_1h_eur", "scalp_eurjpy",
                   "scalp_xau", "rnb_usdjpy", "daytrade_gbpusd", "daytrade_eurgbp", "daytrade_xau",
                   "daytrade_1h_usdcad", "daytrade_1h_usdchf",
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

    @staticmethod
    def _audit_json_safe(value):
        """Normalize audit values so Flask jsonify cannot fail on SQLite drift."""
        if isinstance(value, dict):
            return {str(k): OandaBridge._audit_json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [OandaBridge._audit_json_safe(v) for v in value]
        if isinstance(value, tuple):
            return [OandaBridge._audit_json_safe(v) for v in value]
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, Decimal):
            return float(value) if value.is_finite() else None
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    @classmethod
    def _normalize_audit_rows(cls, rows):
        return [cls._audit_json_safe(dict(row)) for row in (rows or [])]

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
                return self._normalize_audit_rows(self._db.get_oanda_audit(limit=limit))
            except Exception as e:
                logger.warning(f"[OandaBridge] Audit DB read failed: {e}")
        return self._normalize_audit_rows(self._execution_audit[-limit:])

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
            "storm_guard": self.get_storm_guard_status(),
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
                   signal_price: float = 0.0,
                   entry_type: str | None = None,
                   skip_sent_audit: bool = False,
                   max_attempts: int = 3,
                   record_fill_slippage: bool = False,
                   halt_race_resend: bool = False):
        """Place OANDA market order mirroring a demo trade.
        callback(demo_trade_id, oanda_trade_id) called on success for DB persistence.
        units: override lot size (0 = use default self._units).
        log_callback: fn(msg) for 🔗 OANDA log output (runs in background thread).
        lot_label: display label for lot multiplier (e.g. "🚀1.3x").
        entry_type: optional strategy label for the 'sent' audit row.
        skip_sent_audit: when True, do NOT write the 'sent' audit row here
            (caller has already written it with full sr_meta). Used by the
            demo_trader main-entry path to avoid duplicate 'sent' rows.
        max_attempts: total broker attempts for transient errors (429/503/
            timeout/network). Default 3 preserves the historical behavior.
            weekend_gap_fade passes 1 — pre-reg §2.2 forbids ANY retry
            (a timeout retry can double-fill; single market attempt only).
        record_fill_slippage: when True, persist the real fill-vs-signal_price
            slippage (pips, adverse-positive) onto the demo trade row
            (demo_trades.slippage_pips). Used by weekend_gap_fade whose G1
            R2 gate consumes measured live slippage.
        halt_race_resend: weekend_gap 執行契約(B) §4.4 (AMENDMENT 2026-09-10,
            rule:R1 user 承認)。True のとき、送信した FOK が response 内の
            orderCancelTransaction reason=MARKET_HALTED で cancel された場合
            (tradeable 確認後の解除直後 race) に限り、30 秒後に 1 回だけ FOK
            を再送する (最大計 2 送信)。他の cancel/エラー reason は従来どおり
            再送しない。G1 semantics (§4.5): fill slippage の基準 quote は
            「実際に fill した送信 attempt の直前 quote」— 再送時は直前 quote
            を再取得して基準を差し替える (初回 quote に固定すると繰下げ
            ドリフトが G1 に混入し N=6 で恒久誤停止する — packet §3 が
            案 A を棄却した理由)。

        Returns True when the order passed all bridge gates and the
        background send was fired; False when transmission was refused
        (inactive bridge / unsupported instrument / mode excluded /
        daily-loss halt). Callers that own the 'sent' audit row
        (skip_sent_audit=True) MUST NOT write it unless this returns True
        — the bridge gate verdict is the single source of truth
        (2026-07-02 gate-asymmetry fix, rule:R3).
        """
        if not self.active:
            return False
        try:
            instrument = resolve_instrument(instrument)
        except KeyError as e:
            logger.error(f"[OandaBridge] {e}")
            if log_callback:
                log_callback(f"🔗 OANDA: [BLOCKED] unsupported instrument — {instrument}")
            return False
        if not self.is_mode_allowed(mode):
            logger.debug(f"[OandaBridge] mode={mode} not in allowed_modes, skip")
            return False
        _audit_entry_type = entry_type if entry_type is not None else mode

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
                    demo_trade_id=demo_trade_id, entry_type=_audit_entry_type,
                    is_live=False, bridge_status="blocked",
                    block_reason=_reason,
                    direction=direction, instrument=instrument,
                    units=(units if units > 0 else self._units),
                )
            except Exception as e:
                logger.warning(f"[OandaBridge] audit write failed during daily-loss block: {e}")
            if log_callback:
                log_callback(f"🔗 OANDA: [HALT] {_reason} — {direction} {instrument} not transmitted")
            return False

        if entry_type is not None and not skip_sent_audit:
            try:
                self._add_audit(
                    demo_trade_id=demo_trade_id, entry_type=_audit_entry_type,
                    is_live=True, bridge_status="sent",
                    block_reason="",
                    direction=direction, instrument=instrument,
                    units=(units if units > 0 else self._units),
                )
            except Exception as e:
                logger.warning(f"[OandaBridge] audit write failed during send: {e}")

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
            _max_att = max(1, int(max_attempts))
            for _attempt in range(_max_att):
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
                # Transient errors: retry with backoff (max_attempts total;
                # weekend_gap_fade passes max_attempts=1 = no retry, pre-reg §2.2)
                _err_code = data.get("error")
                if (_err_code in (429, 503, "timeout", "network")
                        and _attempt < _max_att - 1):
                    _time.sleep(1 * (_attempt + 1))
                    logger.warning(f"[OandaBridge] OPEN retry {_attempt+1}/{_max_att-1} "
                                   f"{side} {instrument} ({_err_code})")
                    continue
                break  # Non-retryable error, stop immediately
            # ── weekend_gap 執行契約(B) §4.4: halt-race 限定再送 (最大計 2 送信) ──
            # tradeable 確認済み送信の FOK が MARKET_HALTED cancel で返った場合
            # のみ (= response 内で orderCancelTransaction を確認できた場合のみ)、
            # 30 秒後に 1 回だけ FOK を再送する。他の cancel/エラー reason は
            # 従来どおり再送禁止 (pre-reg §2.2 max_attempts=1 は不変 — 本再送は
            # AMENDMENT §4.4 の限定条項で、二重約定構造なし: 初回注文の cancel
            # transaction が確認済みの場合に限る)。
            # G1 semantics (§4.5): fill slippage 基準は「実際に fill した送信
            # attempt の直前 quote」— 再送前に同サイド quote を再取得して基準を
            # 差し替える (初回 quote 固定は繰下げドリフトを G1 に混入させる)。
            _fill_basis_price = float(signal_price or 0.0)
            if halt_race_resend and ok:
                _cxl0 = data.get("orderCancelTransaction", {}) or {}
                _filled0 = bool((data.get("orderFillTransaction", {}) or {})
                                .get("tradeOpened", {}).get("tradeID"))
                if not _filled0 and str(_cxl0.get("reason", "")) == "MARKET_HALTED":
                    logger.warning(
                        f"[OandaBridge] OPEN {side} {instrument} FOK cancelled "
                        f"(MARKET_HALTED, halt-race) — single resend in "
                        f"{HALT_RACE_RESEND_DELAY_SEC:.0f}s (§4.4, max 2 sends)")
                    if log_callback:
                        log_callback(
                            f"🔗 OANDA: [HALT_RACE] {instrument} FOK cancelled "
                            f"(MARKET_HALTED) → {HALT_RACE_RESEND_DELAY_SEC:.0f}s "
                            f"後に 1 回だけ再送 (執行契約 B §4.4)")
                    _time.sleep(HALT_RACE_RESEND_DELAY_SEC)
                    # 再送 attempt 直前 quote を slippage 基準に差し替え (§4.5)
                    try:
                        _q_ok, _q = self._client.get_price(instrument)
                        if _q_ok:
                            _p0 = (_q.get("prices") or [{}])[0]
                            _side_key = "asks" if side == "buy" else "bids"
                            _q_px = float(
                                ((_p0.get(_side_key) or [{}])[0]).get("price", 0)
                                or 0)
                            if _q_px > 0:
                                _fill_basis_price = _q_px
                    except Exception as _q_err:
                        logger.warning(
                            f"[OandaBridge] halt-race basis-quote refresh "
                            f"failed ({instrument}): {_q_err}")
                    _t0 = _time.monotonic()
                    ok, data = self._client.market_order(
                        side=side,
                        units=_lot,
                        instrument=instrument,
                        stop_loss=sl,
                        take_profit=tp,
                    )
                    _latency_ms = round((_time.monotonic() - _t0) * 1000)
                    _attempts_made += 1
            if ok:
                # v20: orderFillTransaction.tradeOpened.tradeID
                _fill = data.get("orderFillTransaction", {})
                oanda_id = str(_fill.get("tradeOpened", {}).get("tradeID", ""))
                _price = _fill.get("price", "")
                if oanda_id:
                    with self._lock:
                        self._trade_map[demo_trade_id] = oanda_id
                    self._storm_register_trade(demo_trade_id, direction, sl)
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
                    # ── Real fill slippage persistence (weekend_gap_fade G1 input) ──
                    # Signed adverse-positive pips: BUY fill above signal / SELL
                    # fill below signal = positive (worse). Overwrites the
                    # demo-side quote-vs-mid estimate with the broker truth.
                    # 基準 quote = _fill_basis_price = 「実際に fill した送信
                    # attempt の直前 quote」(§4.5) — halt-race 再送なしの場合は
                    # caller の signal_price (送信時 quote) と同一値。
                    if record_fill_slippage and _fill_basis_price and _price and self._db is not None:
                        try:
                            _fill_px_rs = float(_price)
                            _pip_m_rs = 100 if ("JPY" in instrument or "XAU" in instrument) else 10000
                            if side == "buy":
                                _slip_rs = (_fill_px_rs - float(_fill_basis_price)) * _pip_m_rs
                            else:
                                _slip_rs = (float(_fill_basis_price) - _fill_px_rs) * _pip_m_rs
                            self._db.update_trade_slippage(
                                demo_trade_id, round(_slip_rs, 2))
                            if log_callback:
                                log_callback(
                                    f"[WEEKEND_GAP] fill slippage persisted: "
                                    f"{_slip_rs:+.2f}p (trade={demo_trade_id})")
                        except Exception as _rs_err:
                            logger.warning(
                                f"[OandaBridge] fill-slippage persist failed "
                                f"(demo={demo_trade_id}): {_rs_err}")
                    # Filled rows intentionally keep the OANDA-side mode label.
                    # `sent` rows carry the strategy name; downstream joins rely
                    # on that twin meaning to avoid counting PYR mode labels as
                    # strategies.
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
        return True

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
                    self._storm_forget(demo_trade_id)
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
                    self._storm_forget(demo_trade_id)
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

    # ── SL replacement storm guard (R3, 2026-09-22) ───
    # 4 点直交 guard。各 check は reason 文字列 (skip 理由) か None を返す。
    # CF pin (tests/test_oanda_bridge_storm_guard.py) は各 check を個別に
    # monkeypatch で殺すと storm fixture が素通りすることを固定する。

    def _storm_register_trade(self, demo_trade_id: str, direction: str | None,
                              sl: float | None):
        """open_trade 成功時に baseline (方向 / 初期 SL) を登録する。"""
        with self._storm_lock:
            st = self._storm_state.get(demo_trade_id)
            if st is None:
                st = self._storm_new_state()
                self._storm_state[demo_trade_id] = st
            if direction:
                st["direction"] = str(direction).upper()
            if sl is not None:
                try:
                    st["confirmed_sl"] = float(sl)
                except (TypeError, ValueError):
                    pass

    def _storm_forget(self, demo_trade_id: str):
        with self._storm_lock:
            self._storm_state.pop(demo_trade_id, None)

    def _storm_new_state(self) -> dict:
        return {
            # 送信直列化 (review 3 巡目 P1): pending[0] の token だけが broker へ送れる。
            # confirm/rollback が pending から外して notify_all する。
            "cond": threading.Condition(self._storm_lock),
            # network (seed / 再照会) の single-flight lock (review 13 巡目 P2: 未 seed の
            # restored trade への burst が worker ごとに GET を撃たないように) + 再照会の最短間隔
            "net_lock": threading.RLock(), "last_reconcile_ts": None,   # None = 未照会 (monotonic は 0 近傍から始まり得るので 0.0 を sentinel にしない)
            "direction": None,
            # confirmed_sl = broker が受理した最後の SL (seed / open / 成功確認のみ更新)
            # pending     = 送信中 (未確認) の予約 token 列 (発行順)
            # baseline (= 各 check が比較する値) は pending[-1].new_sl or confirmed_sl
            "confirmed_sl": None, "confirmed_seq": 0, "pending": [], "seq": 0,
            # unresolved_sl = 送信したが応答が曖昧 (timeout/network/5xx) で broker が適用したか
            # 不明な SL。broker 照会で解消するまで単調性は保守的 baseline (BUY: max / SELL: min)
            "unresolved_sl": None, "unresolved_prev": None,
            "sent_ts": [], "sent_total": 0, "failed_total": 0,
            "tripped": False, "warned": False,
            "counts": {}, "seeded": False, "seed_source": None,
        }

    @staticmethod
    def _storm_baseline(st: dict, before_seq: int | None = None) -> float | None:
        """check が比較する SL — 直近の未確認予約があればそれ (burst 抑止、review P2-1)、
        なければ broker 確認済み値。未確認値を確認済みとは**扱わない** (review P1-3)。
        before_seq を与えると、その seq より前の予約だけを見る (送信直前の再評価: 自分が
        pending[0] なら先行予約はゼロ = 確認済み値そのもの、review 5 巡目 P2)。"""
        pend = st.get("pending") or []
        if before_seq is not None:
            pend = [t for t in pend if t["seq"] < before_seq]
        if pend:
            return pend[-1]["new_sl"]
        return st.get("confirmed_sl")

    def _storm_seed_restored(self, demo_trade_id: str, st: dict):
        """再起動後 (restore_mappings 経由、open_trade を経ていない) trade の
        baseline を lazy seed する。PR #287 review P1 ×2 の修正:

        - **SL baseline は broker (OANDA openTrades の stopLossOrder.price) から
          のみ取る。** demo_trades.sl は LIVE 経路では trail 後も更新されない
          (demo_trader.py L3188–3199: LIVE 分岐は update_sl_tp を呼ばない) ので
          stale — それを単調性の基準にすると「broker 154.350 / DB 154.115 で
          154.270 を有利側と誤判定して 8 pip 緩める」= guard が守るべき形状を
          素通しする。broker が取れなければ confirmed_sl は None のまま
          (最初の成功送信で baseline 確立 = fail-open)。
        - direction は broker (currentUnits 符号) を第一、DB 行を fallback。
          DB 行の識別子は `trade_id` (demo_trades.id は INTEGER PK で別物)。
        失敗しても guard は fail-open (検知は継続)。"""
        seeded_from = None
        oanda_id = self._trade_map.get(demo_trade_id)
        # (1) broker — authoritative for both direction and current SL
        if oanda_id and self._client is not None:
            try:
                ok, data = self._client.get_open_trades()
            except Exception as e:
                ok, data = False, {"error": str(e)}
            if ok and isinstance(data, dict):
                for ot in data.get("trades", []) or []:
                    if str(ot.get("id", "")) != str(oanda_id):
                        continue
                    try:
                        units = float(ot.get("currentUnits", ot.get("initialUnits", 0)) or 0)
                    except (TypeError, ValueError):
                        units = 0.0
                    if st["direction"] is None and units != 0.0:
                        st["direction"] = "BUY" if units > 0 else "SELL"
                    sl_order = ot.get("stopLossOrder") or {}
                    if st["confirmed_sl"] is None and sl_order.get("price") not in (None, "", 0):
                        try:
                            st["confirmed_sl"] = float(sl_order["price"])
                        except (TypeError, ValueError):
                            pass
                    seeded_from = "broker"
                    break
            else:
                logger.warning(f"[OandaBridge][STORM_GUARD] broker seed failed demo={demo_trade_id}: "
                               f"{(data or {}).get('error', data) if isinstance(data, dict) else data}")
        # (2) DB fallback — direction only (sl は stale なので使わない)
        if st["direction"] is None and self._db is not None:
            try:
                rows = self._db.get_open_trades()
            except Exception as e:
                logger.warning(f"[OandaBridge][STORM_GUARD] db seed failed: {e}")
                rows = []
            for row in rows or []:
                if str(row.get("trade_id")) == str(demo_trade_id):
                    if row.get("direction"):
                        st["direction"] = str(row["direction"]).upper()
                        seeded_from = seeded_from or "db_direction_only"
                    break
        st["seed_source"] = seeded_from
        st["seeded"] = True
        if seeded_from != "broker":
            logger.warning(
                f"[OandaBridge][STORM_GUARD] restored trade demo={demo_trade_id} seeded "
                f"from {seeded_from or 'nothing'}: direction={st['direction']} "
                f"confirmed_sl={st['confirmed_sl']} (broker SL unavailable → baseline = first confirmed SL)"
            )

    # ── 4 checks (order = KB 09-16 訂正版: breaker → 冪等 → 単調性 → dead-band)

    def _storm_check_breaker(self, st: dict, now: float) -> str | None:
        """(1) 累積 tx breaker — 窓あたり累積送信数。tripped は trade 消滅まで保持。"""
        if st["tripped"]:
            return "breaker"
        max_h = int(self._storm_cfg.get("max_tx_per_hour") or 0)
        max_d = int(self._storm_cfg.get("max_tx_per_day") or 0)
        ts = st["sent_ts"]
        # prune > 24h
        cutoff_d = now - 86400.0
        while ts and ts[0] < cutoff_d:
            ts.pop(0)
        n_day = len(ts)
        n_hour = sum(1 for t in ts if t >= now - 3600.0)
        if (max_h > 0 and n_hour >= max_h) or (max_d > 0 and n_day >= max_d):
            st["tripped"] = True
            st["trip_detail"] = f"n_hour={n_hour}/{max_h} n_day={n_day}/{max_d}"
            with self._storm_lock:
                self._storm_totals["breaker_trips"] += 1
            return "breaker"
        return None

    def _storm_check_idempotent(self, st: dict, new_sl: float, pip: float,
                                last=_UNSET) -> str | None:
        """(2) 冪等 — 直前に送った SL と同値なら skip (family A: same-price loop)。"""
        if last is _UNSET:
            last = self._storm_baseline(st)
        if last is None:
            return None
        if round(abs(float(new_sl) - float(last)) / pip, 3) == 0.0:
            return "idempotent"
        return None

    def _storm_check_monotonic(self, st: dict, new_sl: float, pip: float,
                               last=_UNSET, count_unknown: bool = True) -> str | None:
        """(3) 単調性 — BUY で SL↓ / SELL で SL↑ は契約違反 (risk-increasing)。
        方向不明なら判定不能 (検知カウンタのみ; 送信直前の再評価では二重計数しない)。"""
        if last is _UNSET:
            last = self._storm_baseline(st)
        direction = st.get("direction")
        if last is None:
            return None
        if direction not in ("BUY", "SELL"):
            if count_unknown:
                with self._storm_lock:
                    self._storm_totals["unknown_direction"] += 1
            return None
        delta_pips = round((float(new_sl) - float(last)) / pip, 3)
        if direction == "BUY" and delta_pips < 0:
            return "monotonic"
        if direction == "SELL" and delta_pips > 0:
            return "monotonic"
        return None

    def _storm_check_deadband(self, st: dict, new_sl: float, pip: float,
                              last=_UNSET) -> str | None:
        """(4) dead-band — |new − last| < deadband_pips (既定 1.0 pip) は skip
        (family B: 0.001 刻み振動。等値では止まらない)。ちょうど 1.0 pip は通す。"""
        if last is _UNSET:
            last = self._storm_baseline(st)
        if last is None:
            return None
        band = float(self._storm_cfg.get("deadband_pips") or 0.0)
        if band <= 0:
            return None
        delta_pips = round(abs(float(new_sl) - float(last)) / pip, 3)
        if delta_pips < band:
            return "deadband"
        return None

    def _storm_get_state(self, demo_trade_id: str, network: bool = True) -> dict:
        """state を取得/生成し、network=True なら未 seed の restored trade の seed と
        unresolved の broker 再照会を行う (lock 外; 二重 seed は None 埋めのみで無害)。
        fire-and-forget 経路の caller は network=False で呼び、network は worker 側で行う
        (review 12 巡目 P2: broker timeout 10 s で高頻度 SL ループを塞がない)。"""
        with self._storm_lock:
            st = self._storm_state.get(demo_trade_id)
            if st is None:
                st = self._storm_new_state()
                self._storm_state[demo_trade_id] = st
        if network:
            self._storm_network_refresh(demo_trade_id, st)
        return st

    # unresolved の再照会を打つ最短間隔 (burst 中に gate ごとに GET を撃たない)
    STORM_RECONCILE_MIN_INTERVAL_SEC = 1.0

    def _storm_network_refresh(self, demo_trade_id: str, st: dict):
        """seed / 再照会を trade ごとに single-flight で行う (review 13 巡目 P2)。
        後続は lock 取得後に seeded / unresolved を見て不要なら何もしない。"""
        with st["net_lock"]:
            if not st["seeded"] and (st["direction"] is None or st["confirmed_sl"] is None):
                self._storm_seed_restored(demo_trade_id, st)
            if st.get("unresolved_sl") is not None:
                now = _time.monotonic()
                last = st.get("last_reconcile_ts")
                if last is None or now - last >= self.STORM_RECONCILE_MIN_INTERVAL_SEC:
                    st["last_reconcile_ts"] = now
                    self._storm_try_reconcile(demo_trade_id, st)

    def _storm_evaluate(self, demo_trade_id: str, st: dict, new_sl: float,
                        instrument: str, before_seq: int | None = None,
                        skip_breaker: bool = False, observe: bool = True) -> str | None:
        """4 check を順に評価し reason|None を返す。caller が _storm_lock を保持する。
        before_seq は送信直前の再評価用 (先行予約を除いた baseline = confirmed_sl)。
        observe=False (送信直前の再評価) では観測カウンタ (unknown_direction / allow_loosen
        の detected) を二重計数しない。"""
        pip = _storm_pip_size(instrument)
        now = _time.monotonic()
        last = self._storm_baseline(st, before_seq)
        # 冪等 / dead-band は確認済み (or pending) の値と比較 — unresolved 値と同値の再送は
        # 「再適用」なので skip しない。単調性だけは保守的 baseline (§2.10)。
        last_mono = self._storm_conservative(st, last)
        reason = None if skip_breaker else self._storm_check_breaker(st, now)
        if reason is None:
            reason = self._storm_check_idempotent(st, new_sl, pip, last)
        if reason is None:
            reason = self._storm_check_monotonic(st, new_sl, pip, last_mono, count_unknown=observe)
            if reason == "monotonic" and self._storm_allow_loosen:
                # 明示 opt-in: 検知は数えるが reject しない
                if observe:
                    self._storm_record(demo_trade_id, st, "monotonic", new_sl,
                                       enforced=False, note="allow_loosen")
                reason = None
        if reason is None:
            reason = self._storm_check_deadband(st, new_sl, pip, last)
        return reason

    def _storm_record(self, demo_trade_id: str, st: dict, reason: str,
                      new_sl: float, enforced: bool, note: str = ""):
        """検知器本体 — カウンタ + 抑制付きログ。CF pin: これを殺すとカウンタが
        動かず test が落ちる。"""
        with self._storm_lock:
            n = st["counts"].get(reason, 0) + 1
            st["counts"][reason] = n
            bucket = "skipped" if enforced else "detected"
            self._storm_totals[bucket][reason] = self._storm_totals[bucket].get(reason, 0) + 1
        if n <= STORM_GUARD_LOG_FIRST_N or n % STORM_GUARD_LOG_EVERY_M == 0:
            _act = "SKIP" if enforced else "DETECT(would_skip)"
            logger.warning(
                f"[OandaBridge][STORM_GUARD] {_act} reason={reason} demo={demo_trade_id} "
                f"dir={st.get('direction')} baseline={self._storm_baseline(st)} "
                f"confirmed={st.get('confirmed_sl')} pending={len(st.get('pending') or [])} new_sl={new_sl} "
                f"n={n} sent_total={st['sent_total']}{(' ' + note) if note else ''}"
            )
        if reason == "breaker" and not st["warned"]:
            st["warned"] = True
            logger.warning(
                f"[OandaBridge][STORM_GUARD] BREAKER TRIPPED demo={demo_trade_id} "
                f"{st.get('trip_detail', '')} enforce={self._storm_enforce} "
                f"— SL replacement storm signature (cf. storm 4 #859468 16,837 repl)"
            )

    def _storm_reserve(self, st: dict, new_sl: float) -> dict:
        """送信予約 — gate 通過と同じ critical section で pending に token を積む
        (PR #287 review P2-1)。fire-and-forget 経路で worker 完了前に次の modify_sl が
        来ても、次は pending 末尾を baseline に見る。
        **confirmed_sl は触らない** (未確認値を確認済みと混ぜない、review P1-3)。
        **breaker 窓 (sent_ts) にもここでは入れない** — 窓に入るのは broker へ実際に
        送信する直前 (`_storm_send_decision` → `_storm_count_tx`) だけ (review 7/8 巡目
        P1: 未送信予約が窓を埋めると偽 trip / 偽 breaker reject が出る)。
        Returns token {seq, new_sl, ts: None, done: Event, ok: None|bool, reeval}."""
        with self._storm_lock:
            st["seq"] += 1
            token = {"seq": st["seq"], "new_sl": float(new_sl), "ts": None,
                     "done": threading.Event(), "ok": None, "reeval": False}
            st["pending"].append(token)
        return token

    def _storm_count_tx(self, st: dict, token: dict, ts: float | None = None):
        """token を breaker 窓 (broker への要求数) に入れる。caller が lock 保持。"""
        ts = _time.monotonic() if ts is None else ts
        token["ts"] = ts
        st["sent_ts"].append(ts)
        st["sent_total"] += 1
        self._storm_totals["sent"] += 1

    def _storm_uncount_tx(self, st: dict, token: dict):
        """窓に入れた要求が実際には送信されなかった (client のローカル 429 backoff) 場合に外す。"""
        with self._storm_lock:
            if token.get("ts") is not None:
                try:
                    st["sent_ts"].remove(token["ts"])
                    st["sent_total"] -= 1
                    self._storm_totals["sent"] -= 1
                except ValueError:
                    pass
                token["ts"] = None

    def _storm_client_backoff_active(self) -> bool:
        """OandaClient がローカル 429 backoff 中 (= 次の _request は HTTP を出さずに 429 を返す)。"""
        until = getattr(self._client, "_rate_limit_until", 0.0) or 0.0
        try:
            return _time.time() < float(until)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _storm_is_local_backoff_reply(data) -> bool:
        """_request のローカル backoff 応答の形 {"error": 429, "message": "Rate limited, retry in Ns"}。
        HTTP を出していないので breaker 窓に数えない (15 巡目 P1)。"""
        return (isinstance(data, dict) and data.get("error") == 429
                and str(data.get("message", "")).startswith("Rate limited, retry in"))

    def _storm_precheck_send(self, demo_trade_id: str, st: dict, token: dict) -> bool:
        """送信直前: client がローカル backoff 中なら送らず (HTTP も出ないので) 窓から外して取り消す。"""
        if not self._storm_client_backoff_active():
            return True
        with self._storm_lock:
            self._storm_totals["local_backoff"] += 1
        self._storm_uncount_tx(st, token)
        self._storm_unreserve(st, token, demo_trade_id)
        logger.warning(f"[OandaBridge][STORM_GUARD] SL replacement not sent: client in local 429 backoff "
                       f"demo={demo_trade_id} sl={token['new_sl']} (not counted toward breaker)")
        return False

    def _storm_unreserve(self, st: dict, token: dict, demo_trade_id: str = ""):
        """送信直前に reject / drop された予約を取り消す — broker には一切届いておらず
        窓にも入っていない (窓入りは送信直前のみ) ので pending から外すだけ
        (失敗 rollback とは違い failed に数えない)。"""
        if not token:
            return
        with self._storm_lock:
            token["ok"] = False
            try:
                st["pending"].remove(token)
            except ValueError:
                pass
            st["cond"].notify_all()
        token["done"].set()

    def _storm_confirm(self, demo_trade_id: str, st: dict, token: dict | None):
        """broker 成功: token を pending から外し confirmed_sl を更新する。
        非同期 worker の完了順は発行順と一致しないので、confirmed_seq より新しい
        token だけが confirmed_sl を進める (古い成功で新しい確認を上書きしない)。"""
        if not token:
            return
        with self._storm_lock:
            token["ok"] = True
            try:
                st["pending"].remove(token)
            except ValueError:
                pass
            if token["seq"] > st["confirmed_seq"]:
                st["confirmed_seq"] = token["seq"]
                st["confirmed_sl"] = token["new_sl"]
                st["unresolved_sl"] = None      # より新しい確認済み値で曖昧さは消える (authoritative)
                st["unresolved_prev"] = None
            st["cond"].notify_all()
        token["done"].set()

    def _storm_rollback(self, demo_trade_id: str, st: dict, token: dict | None,
                        ambiguous: bool = False):
        """broker 失敗 (ok=False / 例外): token を pending から外すだけ。
        confirmed_sl は未確認値を一度も取り込んでいないので「戻す」操作は不要 —
        連鎖失敗 (A,B 予約 → A,B 失敗) でも baseline は自然に confirmed_sl へ戻る
        (review P2-2: 直前予約の prev_sl 復元だと B の rollback が未確認の A を
        残していた)。要求数は戻さない。"""
        if not token:
            return
        if ambiguous:
            # 応答曖昧 (review 10 巡目 P1): broker は PUT を適用済みかもしれない。旧 confirmed_sl
            # へ戻して後続を起こすと、適用済み 154.400 に対して 154.350 が「tightening」と
            # 判定され live stop を緩め得る。→ token を pending に残したまま (後続は待つ)
            # broker の現 SL を照会し、取れれば confirmed_sl をそれに合わせる。取れなければ
            # unresolved_sl に記録し、以後の gate で再照会 + 単調性は保守的 baseline。
            with self._storm_lock:
                self._storm_totals["ambiguous_failures"] += 1
                gen = st["confirmed_seq"]          # 照会開始時点の版 (review 11 巡目 P1)
            broker_sl = self._storm_query_broker_sl(demo_trade_id)
            with self._storm_lock:
                if st["confirmed_seq"] != gen:
                    # 照会中に別の確認が進んだ → snapshot は古い可能性があり捨てる。
                    # その確認が A より新しければ A の曖昧さは上書きされて消える。
                    self._storm_totals["reconcile_discarded"] += 1
                    if st["confirmed_seq"] < token["seq"]:
                        st["unresolved_sl"] = token["new_sl"]
                        self._storm_totals["unresolved"] += 1
                    logger.warning(f"[OandaBridge][STORM_GUARD] ambiguous failure: broker snapshot discarded "
                                   f"(state advanced during query) demo={demo_trade_id} sent={token['new_sl']} "
                                   f"unresolved={st['unresolved_sl']}")
                else:
                    prev = st["confirmed_sl"]
                    st["unresolved_prev"] = prev
                    verdict = self._storm_reconcile_verdict(st, token["new_sl"], prev, broker_sl)
                    if verdict == "changed":
                        # 第三の値 = 別 actor が動かした現値。confirmed_sl はそれに合わせるが、
                        # timeout した PUT がまだ着地し得る以上、曖昧さは消さない (15 巡目 P1)
                        st["confirmed_sl"] = broker_sl
                        st["unresolved_prev"] = broker_sl
                        st["unresolved_sl"] = token["new_sl"]
                        self._storm_totals["observed_changed"] += 1
                        self._storm_totals["unresolved"] += 1
                        logger.warning(f"[OandaBridge][STORM_GUARD] ambiguous failure: third value observed "
                                       f"(confirmed_sl={broker_sl}, sent={token['new_sl']} still unresolved) "
                                       f"demo={demo_trade_id}")
                    elif verdict == "applied":
                        st["confirmed_sl"] = broker_sl
                        st["confirmed_seq"] = max(st["confirmed_seq"], token["seq"])
                        st["unresolved_sl"] = None
                        st["unresolved_prev"] = None
                        self._storm_totals["reconciled"] += 1
                        logger.warning(f"[OandaBridge][STORM_GUARD] ambiguous failure reconciled ({verdict}) "
                                       f"demo={demo_trade_id} sent={token['new_sl']} broker_sl={broker_sl}")
                    else:
                        # unknown (照会不能) / inconclusive (broker はまだ旧値 = PUT が処理中かも)
                        st["unresolved_sl"] = token["new_sl"]
                        self._storm_totals["unresolved"] += 1
                        logger.warning(f"[OandaBridge][STORM_GUARD] ambiguous failure UNRESOLVED ({verdict}) "
                                       f"demo={demo_trade_id} sent={token['new_sl']} broker_sl={broker_sl} — "
                                       f"monotonic baseline stays conservative until authoritative")
        with self._storm_lock:
            token["ok"] = False
            try:
                st["pending"].remove(token)
            except ValueError:
                pass
            st["failed_total"] += 1
            self._storm_totals["failed"] += 1
            st["cond"].notify_all()
        token["done"].set()

    @staticmethod
    def _storm_failure_is_ambiguous(data, exc: BaseException | None = None) -> bool:
        """失敗が「broker が拒否した (適用されていない)」と確定できるか。
        OandaClient._request: HTTP 4xx → {"error": <int 4xx>} (broker 応答あり = 未適用、
        429 のローカル backoff も未送信) = 確定。timeout / network / unknown / 5xx / 例外 =
        PUT が届いて適用された可能性が残る = 曖昧。"""
        if exc is not None:
            return True
        if not isinstance(data, dict):
            return True
        err = data.get("error")
        if isinstance(err, bool):
            return True
        if isinstance(err, int) and 400 <= err < 500:
            return False
        return True

    def _storm_query_broker_sl(self, demo_trade_id: str) -> float | None:
        """broker の現 SL (openTrades.stopLossOrder.price)。取れなければ None。lock 外で呼ぶ。"""
        oanda_id = self._trade_map.get(demo_trade_id)
        if not oanda_id or self._client is None:
            return None
        try:
            ok, data = self._client.get_open_trades()
        except Exception as e:
            ok, data = False, {"error": str(e)}
        if not ok or not isinstance(data, dict):
            return None
        for ot in data.get("trades", []) or []:
            if str(ot.get("id", "")) != str(oanda_id):
                continue
            sl_order = ot.get("stopLossOrder") or {}
            price = sl_order.get("price")
            if price in (None, "", 0):
                return None
            try:
                return float(price)
            except (TypeError, ValueError):
                return None
        return None

    def _storm_try_reconcile(self, demo_trade_id: str, st: dict):
        """unresolved_sl が残っていれば broker を再照会して解消を試みる (gate ごと、lock 外)。
        **版チェック** (review 11 巡目 P1): 照会中に別の確認 (confirmed_seq 前進) が入ったら
        snapshot は古い可能性があるので捨てる — 古い stop で新しい confirmed_sl を上書きすると
        その間の BUY 更新が単調性を通って live stop を緩める。"""
        with self._storm_lock:
            if st.get("unresolved_sl") is None:
                return
            gen = st["confirmed_seq"]
        broker_sl = self._storm_query_broker_sl(demo_trade_id)
        if broker_sl is None:
            return
        self._storm_apply_reconcile(demo_trade_id, st, gen, broker_sl)

    def _storm_apply_reconcile(self, demo_trade_id: str, st: dict, gen: int, broker_sl: float) -> bool:
        """照会結果を「照会開始時点から状態が進んでいない」場合のみ適用する。"""
        with self._storm_lock:
            if st["confirmed_seq"] != gen:
                # 照会中に確認が進んだ (その確認で unresolved は既に消えていることが多い)
                self._storm_totals["reconcile_discarded"] += 1
                logger.warning(f"[OandaBridge][STORM_GUARD] broker snapshot discarded (state advanced "
                               f"during query) demo={demo_trade_id} snapshot={broker_sl} "
                               f"confirmed_sl={st['confirmed_sl']}")
                return False
            if st.get("unresolved_sl") is None:
                return False                   # 既に解消済み (別経路)
            verdict = self._storm_reconcile_verdict(st, st["unresolved_sl"], st.get("unresolved_prev"),
                                                    broker_sl)
            if verdict == "changed":
                # 第三の値: 現値は更新するが曖昧さは維持 (15 巡目 P1)
                st["confirmed_sl"] = broker_sl
                st["unresolved_prev"] = broker_sl
                self._storm_totals["observed_changed"] += 1
                logger.warning(f"[OandaBridge][STORM_GUARD] third value observed while unresolved "
                               f"demo={demo_trade_id} confirmed_sl={broker_sl} unresolved={st['unresolved_sl']}")
                return False
            if verdict != "applied":
                return False                   # inconclusive: 旧値の観測は何度でも非決定 (次の gate で再観測)
            st["confirmed_sl"] = broker_sl
            st["unresolved_sl"] = None
            st["unresolved_prev"] = None
            self._storm_totals["reconciled"] += 1
            logger.warning(f"[OandaBridge][STORM_GUARD] unresolved SL reconciled ({verdict}) from broker "
                           f"demo={demo_trade_id} broker_sl={broker_sl}")
            return True

    def _storm_reconcile_verdict(self, st: dict, sent_sl: float, prev_sl: float | None,
                                 broker_sl: float | None) -> str:
        """曖昧な PUT の帰結を broker 観測から判定する (review 12/14 巡目 P1):
          applied      = broker が送った値を持つ (PUT 適用済み) — authoritative
          changed      = broker が送った値でも直前の値でもない (別 actor が動かした; 現値は真だが
                         timeout した PUT の帰結は不明のまま → confirmed_sl は更新、unresolved は維持;
                         15 巡目 P1)
          inconclusive = broker が直前の値のまま。timeout した PUT の server 側完了には上限が
                         ないので、**旧値を何度・何秒観測しても「未適用」の証拠にはならない**
                         (14 巡目 P1: 5 s 安定観測で not_applied にすると、最後の GET の後に A が
                         着地し B が stop を緩め得た)。unresolved は authoritative な事象
                         (applied / 自分のより新しい確認済み replacement) まで維持し、
                         その間は緩め得る replacement を保守的 baseline でブロックし続ける
          unknown      = 照会不能
        caller が lock 保持。"""
        def _eq(a, b):
            return a is not None and b is not None and abs(float(a) - float(b)) < 1e-7
        if broker_sl is None:
            return "unknown"
        if _eq(broker_sl, sent_sl):
            return "applied"
        if prev_sl is None or not _eq(broker_sl, prev_sl):
            return "changed"
        return "inconclusive"

    def _storm_conservative(self, st: dict, base: float | None) -> float | None:
        """unresolved_sl がある間の単調性 baseline: 適用済みかもしれない値と base のうち
        より保護的な方 (BUY: max / SELL: min)。方向不明なら base。"""
        unres = st.get("unresolved_sl")
        if unres is None:
            return base
        if base is None:
            return unres
        d = st.get("direction")
        if d == "BUY":
            return max(base, unres)
        if d == "SELL":
            return min(base, unres)
        return base

    # 送信順番待ちの上限 — **先頭 token 1 件あたり** (先頭が入れ替わるたびにリセット)。
    # 先頭の決着 = PUT の HTTP timeout (10 s) + 曖昧時の broker 照会 GET (10 s) + 余裕。
    STORM_TURN_WAIT_SEC = 25.0
    # enforce の fire-and-forget で待機 token へ畳み込む (queue = 先頭 + 待機 1 件、thread ≤ 2/trade)
    STORM_COALESCE_ASYNC = True

    def _storm_wait_turn(self, demo_trade_id: str, st: dict, token: dict | None) -> bool:
        """trade ごとに SL replacement を**発行順に直列化**する (review 3 巡目 P1)。
        pending[0] が自分になるまで待つ = 前の要求が broker 応答 (confirm/rollback) を
        返すまで次を送らない。これで (a) 「B 確認済みなのに pending A が baseline」が
        起きない (A は B 送信前に決着する)、(b) broker 側で A が B の後に処理される
        発行順逆転も起きない (同時飛行が 1 件)。timeout = 前の worker 不応答 →
        False (caller は token を rollback して送らない: 順序不明のまま送る方が危険)。

        **検知のみモード (既定) では待たない・落とさない** (review 4 巡目 P2): 直列化も
        guard 本体の一部で、既定の契約は「送信は従来通り、観測だけ」。待つはずだった
        件数を `detected.serialize` に数えるのみ。"""
        if not token:
            return True
        if not self._storm_enforce:
            with self._storm_lock:
                if st["pending"] and st["pending"][0] is not token:
                    self._storm_totals["detected"]["serialize"] += 1
                    n = st["counts"].get("serialize", 0) + 1
                    st["counts"]["serialize"] = n
                    if n <= STORM_GUARD_LOG_FIRST_N or n % STORM_GUARD_LOG_EVERY_M == 0:
                        logger.warning(
                            f"[OandaBridge][STORM_GUARD] DETECT(would_wait) reason=serialize "
                            f"demo={demo_trade_id} sl={token['new_sl']} ahead={len(st['pending']) - 1} n={n}")
            return True
        # 予算は「先頭 token ごと」(review 13 巡目 P1): 先頭が入れ替わる (= 前が決着した) たびに
        # リセットする。先頭 1 件の決着には PUT timeout (10 s) + 曖昧時の照会 GET (10 s) が
        # かかり得るので STORM_TURN_WAIT_SEC はその合計 + 余裕。複数の先行がいても、各先行が
        # 進捗している限り one-shot の保護更新は落とさない。停滞 (先頭が変わらない) だけが drop。
        with self._storm_lock:
            head = st["pending"][0] if st["pending"] else None
            deadline = _time.monotonic() + self.STORM_TURN_WAIT_SEC
            while st["pending"] and st["pending"][0] is not token:
                if st["pending"][0] is not head:
                    head = st["pending"][0]
                    deadline = _time.monotonic() + self.STORM_TURN_WAIT_SEC   # 進捗 → リセット
                remaining = deadline - _time.monotonic()
                if remaining <= 0:
                    self._storm_totals["skipped"]["serialize"] += 1
                    st["counts"]["serialize"] = st["counts"].get("serialize", 0) + 1
                    logger.warning(f"[OandaBridge][STORM_GUARD] SKIP reason=serialize (turn wait timeout) "
                                   f"demo={demo_trade_id} sl={token['new_sl']} ahead={len(st['pending']) - 1} → drop")
                    return False
                st["cond"].wait(remaining)
        return True

    def _storm_gate(self, demo_trade_id: str, new_sl: float,
                    instrument: str, network: bool = True) -> tuple[bool, object, dict | None]:
        """modify_sl / modify_sl_sync 共通入口。
        Returns (proceed, sync_return, reserve_token):
          proceed=True  → broker へ送信する (sync_return は無視)。送信は既に
            予約済み (pending / sent_ts 更新) — 成功で _storm_confirm(token)、
            失敗で _storm_rollback(token)。
          proceed=False → 送信しない。sync_return は modify_sl_sync の戻り値:
            True  = 冪等 skip で broker が**確認済み**にその SL を持つ
            False = それ以外 (dead-band / 単調性 / breaker: broker SL 未変更)
          **暫定 (token["reeval"]=True)**: enforce で reject 理由が出たが baseline が
            **未確認の飛行中予約**だった場合、その場で最終判定しない (review 2 巡目 P1 /
            5 巡目 P2: 未確認値に対する最終 reject は、先行が失敗すると正当な保護更新を
            永久に落とす)。暫定予約として pending に積み、送信順が来た時 (先行が全て
            決着 = baseline が確認済み値) に `_storm_send_decision` で再評価する。
        breaker は計数ベースで baseline に依存しないので暫定にしない (最終)。
        検知のみモード (既定) では常に proceed=True で、検知はカウンタ + ログ。
        評価と予約は 1 つの lock 区間 (同時到達 N 件が同じ古い baseline を見ない)。"""
        st = self._storm_get_state(demo_trade_id, network=network)
        with self._storm_lock:
            self._storm_totals["evaluated"] += 1
            reason = self._storm_evaluate(demo_trade_id, st, new_sl, instrument)
            if reason is None:
                return True, None, self._storm_reserve(st, new_sl)
            if not self._storm_enforce:
                self._storm_record(demo_trade_id, st, reason, new_sl, enforced=False)
                return True, None, self._storm_reserve(st, new_sl)
            if reason != "breaker" and st["pending"]:
                # baseline は未確認 → 暫定予約、送信順到来時に確認済み値で再評価
                token = self._storm_reserve(st, new_sl)
                token["reeval"] = True
                token["provisional_reason"] = reason
                self._storm_totals["deferred"] += 1
                return True, None, token
            self._storm_record(demo_trade_id, st, reason, new_sl, enforced=True)
            return False, (reason == "idempotent"), None

    def _storm_send_decision(self, demo_trade_id: str, st: dict, token: dict | None,
                             new_sl: float, instrument: str) -> tuple[bool, bool]:
        """送信順到来後 (先行予約は全て決着済み) の最終判定 + **breaker 窓入り**。
        Returns (send, sync_return_if_not_send)。
        - 検知のみモード: 判定せず窓に入れて送る (検知は gate で済んでいる)。
        - enforce: **全 token を確認済み baseline で 4 check 再評価する** (breaker 含む)。
          gate 時点の評価は未確認の pending 値に対する pre-filter でしかない — gate を
          「暫定でなく」通った要求も、その baseline が暫定 (後で reject され得る) なら
          送信時に無効になり得る (review 9 巡目 P1: 確認済み 154.115 / P=154.350 /
          暫定 A=154.270 / B=154.280 は A 基準で通るが、P 確認 → A reject の後 B を
          送ると確認済み 154.350 を 154.280 に緩める)。送信直前の再評価が唯一の
          最終判定で、そこでの baseline は先行が全て決着済み = `confirmed_sl`。
          breaker も同じ場所で評価 — 窓に入るのは**実際に送信した要求**だけなので
          未送信予約が原因の偽 reject は起きない (review 8 巡目 P1)。
        通れば `_storm_count_tx` で窓に入れて送る。reject なら予約を取り消し (窓には
        入っていない) skipped に計数、sync は冪等なら True。"""
        if not token:
            return True, False
        with self._storm_lock:
            if not self._storm_enforce:
                self._storm_count_tx(st, token)
                return True, False
            reason = self._storm_evaluate(demo_trade_id, st, new_sl, instrument,
                                          before_seq=token["seq"], skip_breaker=False,
                                          observe=False)
            note = ("reevaluated_at_send"
                    + (f" (provisional={token.get('provisional_reason')})" if token.get("reeval") else ""))
            if reason is None:
                token["reeval"] = False
                self._storm_count_tx(st, token)
                return True, False
            self._storm_record(demo_trade_id, st, reason, new_sl, enforced=True, note=note)
            self._storm_unreserve(st, token, demo_trade_id)
            return False, (reason == "idempotent")

    def get_storm_guard_status(self) -> dict:
        with self._storm_lock:
            per_trade = {
                k: {"direction": v.get("direction"), "last_sl": self._storm_baseline(v),
                    "confirmed_sl": v.get("confirmed_sl"), "unresolved_sl": v.get("unresolved_sl"),
                    "pending": [t["new_sl"] for t in (v.get("pending") or [])],
                    "sent_total": v.get("sent_total", 0), "failed_total": v.get("failed_total", 0),
                    "tripped": v.get("tripped", False), "seed_source": v.get("seed_source"),
                    "counts": dict(v.get("counts", {}))}
                for k, v in self._storm_state.items()
            }
            totals = json.loads(json.dumps(self._storm_totals))
        return {
            "enforce": self._storm_enforce,
            "allow_loosen": self._storm_allow_loosen,
            "config": dict(self._storm_cfg),
            "totals": totals,
            "trades": per_trade,
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

        # 予約は gate 内 (worker 起動前) — 同時到達分は更新済み baseline を見る
        # enforce の fire-and-forget: 先頭 (飛行中) + 待機 1 件で queue を有界化 (15 巡目 P1)。
        # 待機中の async token があれば新しい値をそこへ畳み込む (trail は最新値だけが意味を持つ;
        # 送信直前の再評価が確認済み baseline で判定する)。thread は trade ごと最大 2 本。
        if self._storm_enforce and self.STORM_COALESCE_ASYNC:
            with self._storm_lock:
                st0 = self._storm_state.get(demo_trade_id)
                if st0 is not None and len(st0["pending"]) >= 2:
                    tail = st0["pending"][-1]
                    if tail.get("async") and tail["ok"] is None and not tail.get("sending"):
                        tail["new_sl"] = float(new_sl)
                        tail["reeval"] = True
                        tail["provisional_reason"] = "coalesced"
                        self._storm_totals["coalesced"] += 1
                        return
        # caller (SL ループ) では network を触らない — seed / 再照会は worker で (12 巡目 P2)
        proceed, _, token = self._storm_gate(demo_trade_id, new_sl, instrument, network=False)
        if not proceed:
            return
        if token is not None:
            token["async"] = True
        st = self._storm_state.get(demo_trade_id)

        def _do():
            if st is not None and not self._storm_wait_turn(demo_trade_id, st, token):
                # broker 未到達の drop → unreserve (要求数を戻す)。rollback (要求数保持 /
                # failed 計数) にすると停滞 1 件の後ろに並んだ burst が未送信のまま
                # breaker 窓を埋めて trip する (review 6 巡目 P2)
                self._storm_unreserve(st, token, demo_trade_id)
                logger.error(f"[OandaBridge] MODIFY SL dropped (turn timeout) #{oanda_id} "
                             f"sl={token['new_sl'] if token else new_sl} (demo={demo_trade_id})")
                return
            # 送る値は token から (待機中に畳み込まれている可能性がある)
            with self._storm_lock:
                sl_to_send = float(token["new_sl"]) if token else float(new_sl)
                if token is not None:
                    token["sending"] = True
            if st is not None:
                # 先頭になってから seed / 再照会 (single-flight、送信直前の再評価が使う)
                self._storm_get_state(demo_trade_id, network=True)
                send, _ = self._storm_send_decision(demo_trade_id, st, token, sl_to_send, instrument)
                if not send:
                    return
                if not self._storm_precheck_send(demo_trade_id, st, token):
                    return
            try:
                ok, data = self._client.modify_trade(oanda_id, stop_loss=sl_to_send,
                                                      instrument=instrument)
            except Exception as e:
                if st is not None:
                    self._storm_rollback(demo_trade_id, st, token, ambiguous=True)
                raise
            if ok:
                if st is not None:
                    self._storm_confirm(demo_trade_id, st, token)
                logger.info(f"[OandaBridge] MODIFY SL → {sl_to_send:.3f} "
                            f"OANDA #{oanda_id} (demo={demo_trade_id})")
            else:
                if st is not None:
                    if self._storm_is_local_backoff_reply(data):
                        self._storm_uncount_tx(st, token)       # HTTP を出していない
                        with self._storm_lock:
                            self._storm_totals["local_backoff"] += 1
                    self._storm_rollback(demo_trade_id, st, token,
                                         ambiguous=self._storm_failure_is_ambiguous(data))
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
        proceed, sync_ret, token = self._storm_gate(demo_trade_id, new_sl, instrument)
        if not proceed:
            return bool(sync_ret)
        st = self._storm_state.get(demo_trade_id)
        if st is not None and not self._storm_wait_turn(demo_trade_id, st, token):
            self._storm_unreserve(st, token, demo_trade_id)   # broker 未到達 → 要求数を戻す (6 巡目 P2)
            logger.error(f"[OandaBridge] MODIFY SL (sync) dropped (turn timeout) #{oanda_id} "
                         f"sl={new_sl} (demo={demo_trade_id})")
            return False
        if st is not None:
            if token is not None:
                with self._storm_lock:
                    token["sending"] = True
            send, sync_ret2 = self._storm_send_decision(demo_trade_id, st, token, new_sl, instrument)
            if not send:
                return bool(sync_ret2)
            if not self._storm_precheck_send(demo_trade_id, st, token):
                return False
        try:
            ok, data = self._client.modify_trade(oanda_id, stop_loss=new_sl,
                                                  instrument=instrument)
            if ok:
                if st is not None:
                    self._storm_confirm(demo_trade_id, st, token)
                logger.info(f"[OandaBridge] MODIFY SL (sync) → {new_sl:.3f} "
                            f"OANDA #{oanda_id} (demo={demo_trade_id})")
                return True
            else:
                if st is not None:
                    if self._storm_is_local_backoff_reply(data):
                        self._storm_uncount_tx(st, token)       # HTTP を出していない
                        with self._storm_lock:
                            self._storm_totals["local_backoff"] += 1
                    self._storm_rollback(demo_trade_id, st, token,
                                         ambiguous=self._storm_failure_is_ambiguous(data))
                logger.error(f"[OandaBridge] MODIFY SL (sync) failed #{oanda_id}: {data}")
                return False
        except Exception as e:
            if st is not None:
                self._storm_rollback(demo_trade_id, st, token, ambiguous=True)
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
