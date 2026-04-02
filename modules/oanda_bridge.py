"""
OANDA Bridge — Business logic layer between demo trader and OANDA API.
Fire-and-forget: OANDA failures never block demo trading logic.
Enabled by OANDA_LIVE=true environment variable.
"""
import os
import logging
import threading
from modules.oanda_client import OandaClient

logger = logging.getLogger(__name__)


class OandaBridge:
    def __init__(self):
        self._client = OandaClient()
        self._enabled = os.environ.get("OANDA_LIVE", "").lower() in ("true", "1", "yes")
        self._units = int(os.environ.get("OANDA_UNITS", "1000"))  # 1000 = 0.01 lot
        # demo_trade_id -> oanda_trade_id mapping (in-memory, also persisted in DB)
        self._trade_map = {}  # {demo_trade_id: oanda_trade_id}
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        """True if OANDA integration is enabled and configured."""
        return self._enabled and self._client.configured

    @property
    def status(self) -> dict:
        return {
            "enabled": self._enabled,
            "configured": self._client.configured,
            "active": self.active,
            "units": self._units,
            "open_trades": len(self._trade_map),
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
                logger.error(f"[OandaBridge] fire-and-forget error: {e}")
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ── Open Trade ────────────────────────────────────

    def open_trade(self, demo_trade_id: str, direction: str,
                   sl: float, tp: float,
                   callback=None):
        """Place OANDA market order mirroring a demo trade.
        callback(demo_trade_id, oanda_trade_id) called on success for DB persistence.
        """
        if not self.active:
            return

        def _do():
            side = "buy" if direction == "BUY" else "sell"
            ok, data = self._client.market_order(
                side=side,
                units=self._units,
                stop_loss=sl,
                take_profit=tp,
            )
            if ok:
                # v20: orderFillTransaction.tradeOpened.tradeID
                _fill = data.get("orderFillTransaction", {})
                oanda_id = str(_fill.get("tradeOpened", {}).get("tradeID", ""))
                if oanda_id:
                    with self._lock:
                        self._trade_map[demo_trade_id] = oanda_id
                    logger.info(f"[OandaBridge] OPEN {side} → OANDA #{oanda_id} "
                                f"(demo={demo_trade_id})")
                    if callback:
                        callback(demo_trade_id, oanda_id)
                else:
                    logger.warning(f"[OandaBridge] Order placed but no tradeOpened.id: {data}")
            else:
                logger.error(f"[OandaBridge] OPEN failed: {data}")

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

        def _do():
            ok, data = self._client.close_trade(oanda_id)
            if ok:
                with self._lock:
                    self._trade_map.pop(demo_trade_id, None)
                logger.info(f"[OandaBridge] CLOSE OANDA #{oanda_id} "
                            f"(demo={demo_trade_id}, reason={reason})")
            else:
                logger.error(f"[OandaBridge] CLOSE failed #{oanda_id}: {data}")

        self._fire(_do)

    # ── Modify SL ─────────────────────────────────────

    def modify_sl(self, demo_trade_id: str, new_sl: float):
        """Update stop loss on OANDA trade (for trailing stop / BE moves)."""
        if not self.active:
            return

        oanda_id = self._trade_map.get(demo_trade_id)
        if not oanda_id:
            return

        def _do():
            ok, data = self._client.modify_trade(oanda_id, stop_loss=new_sl)
            if ok:
                logger.info(f"[OandaBridge] MODIFY SL → {new_sl:.3f} "
                            f"OANDA #{oanda_id} (demo={demo_trade_id})")
            else:
                logger.error(f"[OandaBridge] MODIFY SL failed #{oanda_id}: {data}")

        self._fire(_do)

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
