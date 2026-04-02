"""
OANDA v20 REST API Client — Thin wrapper for OANDA Japan live trading.
Handles authentication, request formatting, and error handling.
All methods return (success: bool, data: dict) tuples.
"""
import os
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

# OANDA v20 API base URL (本番環境)
BASE_URL = "https://api-fxtrade.oanda.com"


class OandaClient:
    def __init__(self, token: str = None, account_id: str = None):
        self._token = token or os.environ.get("OANDA_TOKEN", "")
        self._account_id = account_id or os.environ.get("OANDA_ACCOUNT_ID", "")

    @property
    def configured(self) -> bool:
        return bool(self._token and self._account_id)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "fx-ai-trader/1.0",
        }

    def _request(self, method: str, path: str, data: dict = None,
                 timeout: int = 10) -> tuple:
        """Execute HTTP request. Returns (success, response_dict)."""
        url = f"{BASE_URL}{path}"
        body = None
        if data:
            body = json.dumps(data).encode("utf-8")

        req = Request(url, data=body, headers=self._headers(), method=method)

        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return True, json.loads(raw) if raw else {}
        except HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.error(f"OANDA API {method} {path} → {e.code}: {err_body}")
            return False, {"error": e.code, "message": err_body}
        except URLError as e:
            logger.error(f"OANDA API {method} {path} → URLError: {e.reason}")
            return False, {"error": "network", "message": str(e.reason)}
        except Exception as e:
            logger.error(f"OANDA API {method} {path} → {type(e).__name__}: {e}")
            return False, {"error": "unknown", "message": str(e)}

    # ── Market Order (v20) ────────────────────────────

    def market_order(self, side: str, units: int,
                     instrument: str = "USD_JPY",
                     stop_loss: float = None,
                     take_profit: float = None) -> tuple:
        """Place a market order via v20 API.
        side: "buy" or "sell" — v20 uses positive/negative units
        Returns (success, data) where data contains orderFillTransaction.tradeOpened.tradeID
        """
        path = f"/v3/accounts/{self._account_id}/orders"
        # v20: positive units = buy, negative units = sell
        signed_units = str(units) if side.lower() == "buy" else str(-units)

        order = {
            "type": "MARKET",
            "instrument": instrument,
            "units": signed_units,
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
        }
        if stop_loss is not None:
            order["stopLossOnFill"] = {
                "price": f"{stop_loss:.3f}",
                "timeInForce": "GTC",
            }
        if take_profit is not None:
            order["takeProfitOnFill"] = {
                "price": f"{take_profit:.3f}",
                "timeInForce": "GTC",
            }

        return self._request("POST", path, {"order": order})

    # ── Close Trade (v20) ─────────────────────────────

    def close_trade(self, trade_id: str) -> tuple:
        """Close an open trade by OANDA trade ID.
        PUT /v3/accounts/:id/trades/:trade_id/close
        """
        path = f"/v3/accounts/{self._account_id}/trades/{trade_id}/close"
        return self._request("PUT", path, {"units": "ALL"})

    # ── Modify Trade SL/TP (v20) ──────────────────────

    def modify_trade(self, trade_id: str,
                     stop_loss: float = None,
                     take_profit: float = None) -> tuple:
        """Modify SL/TP on an existing trade.
        PUT /v3/accounts/:id/trades/:trade_id/orders
        """
        path = f"/v3/accounts/{self._account_id}/trades/{trade_id}/orders"
        params = {}
        if stop_loss is not None:
            params["stopLoss"] = {
                "price": f"{stop_loss:.3f}",
                "timeInForce": "GTC",
            }
        if take_profit is not None:
            params["takeProfit"] = {
                "price": f"{take_profit:.3f}",
                "timeInForce": "GTC",
            }
        if not params:
            return False, {"error": "no_params", "message": "Nothing to modify"}

        return self._request("PUT", path, params)

    # ── Get Open Trades (v20) ─────────────────────────

    def get_open_trades(self) -> tuple:
        """List all open trades for the account.
        GET /v3/accounts/:id/openTrades
        """
        path = f"/v3/accounts/{self._account_id}/openTrades"
        return self._request("GET", path)

    # ── Get Account Info (v20) ────────────────────────

    def get_account(self) -> tuple:
        """Get account summary (balance, margin, etc).
        GET /v3/accounts/:id/summary
        """
        path = f"/v3/accounts/{self._account_id}/summary"
        return self._request("GET", path)

    # ── Get Current Price (v20) ───────────────────────

    def get_price(self, instrument: str = "USD_JPY") -> tuple:
        """Get current bid/ask price.
        GET /v3/accounts/:id/pricing?instruments=USD_JPY
        """
        path = f"/v3/accounts/{self._account_id}/pricing?instruments={instrument}"
        return self._request("GET", path)
