"""MT5RemoteBroker — HMAC-signed HTTP client for the Windows VPS shim.

Why a shim and not direct MT5?
- The ``MetaTrader5`` Python package is Windows-only. cfd-trader runs
  on macOS / Render (Linux). Direct integration is not possible.
- We run a thin Flask service on a Windows VPS that has MT5 + the
  Python package installed and signed-in to the OANDA CFD account.
- This module is the client side: turns place_market_order into a
  signed POST to that shim, parses the response, returns
  BrokerOrderResult.

Wire protocol — see ``cfd_trader/broker/SHIM_SPEC.md`` for the full
spec. Summary:

  POST {base_url}/v1/orders/market
  Headers:
    Content-Type: application/json
    X-Timestamp: <unix epoch seconds, integer string>
    X-Signature: hex(hmac_sha256(secret, timestamp + "." + body))
  Body (JSON):
    {"instrument": "US500", "side": "long", "units": 1,
     "signal_price": 5000.0, "client_order_id": "<uuid4>"}
  Response 200 (filled):
    {"status": "filled", "broker_trade_id": "84212391",
     "fill_price": 5000.25, "raw": {...}}
  Response 200 (rejected):
    {"status": "rejected", "broker_trade_id": null,
     "fill_price": null, "reject_reason": "...", "raw": {...}}
  Response 5xx / timeout / signature mismatch:
    treated as rejected (network_error / signature_error).

The shim is responsible for the broker-name translation
(SPX500_USD → US500), MT5 deal_id extraction, etc. cfd-trader stays
broker-agnostic.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any

import requests

from cfd_trader.broker.protocol import BrokerOrderResult


class MT5RemoteBroker:
    """HMAC-signed HTTP client for the Windows VPS MT5 shim.

    Configuration is passed at construction time so unit tests can
    substitute a tiny fake server. Production wiring reads the values
    from env vars (CFD_MT5_SHIM_URL, CFD_MT5_SHIM_SECRET) — see
    cfd_trader/broker/factory.py.
    """

    # Conservative defaults — shim is on a VPS, not localhost.
    DEFAULT_TIMEOUT_S = 8.0

    def __init__(
        self,
        *,
        base_url: str,
        secret: str,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        session: requests.Session | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if not secret:
            raise ValueError("secret is required (no anonymous mode)")
        self._base_url = base_url.rstrip("/")
        self._secret = secret.encode("utf-8")
        self._timeout_s = float(timeout_s)
        self._session = session or requests.Session()

    def place_market_order(
        self,
        *,
        instrument: str,
        side: str,
        units: int,
        signal_price: float,
    ) -> BrokerOrderResult:
        body = {
            "instrument": instrument,
            "side": side,
            "units": int(units),
            "signal_price": float(signal_price),
            "client_order_id": uuid.uuid4().hex,
        }
        body_bytes = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ts = str(int(time.time()))
        sig = self._sign(ts, body_bytes)

        url = f"{self._base_url}/v1/orders/market"
        try:
            resp = self._session.post(
                url,
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Timestamp": ts,
                    "X-Signature": sig,
                },
                timeout=self._timeout_s,
            )
        except requests.RequestException as exc:
            return BrokerOrderResult(
                status="rejected",
                broker_trade_id=None,
                fill_price=None,
                reject_reason=f"network_error: {type(exc).__name__}: {exc}",
                raw={"request_body": body, "error": str(exc)},
            )

        return self._parse_response(resp, request_body=body)

    def _sign(self, ts: str, body_bytes: bytes) -> str:
        msg = ts.encode("utf-8") + b"." + body_bytes
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def _parse_response(
        self, resp: requests.Response, *, request_body: dict[str, Any]
    ) -> BrokerOrderResult:
        if resp.status_code != 200:
            return BrokerOrderResult(
                status="rejected",
                broker_trade_id=None,
                fill_price=None,
                reject_reason=f"http_{resp.status_code}",
                raw={
                    "request_body": request_body,
                    "response_status": resp.status_code,
                    "response_body_head": resp.text[:512],
                },
            )
        try:
            payload = resp.json()
        except ValueError:
            return BrokerOrderResult(
                status="rejected",
                broker_trade_id=None,
                fill_price=None,
                reject_reason="invalid_json_response",
                raw={
                    "request_body": request_body,
                    "response_body_head": resp.text[:512],
                },
            )

        status = payload.get("status")
        if status == "filled":
            broker_trade_id = payload.get("broker_trade_id")
            fill_price = payload.get("fill_price")
            # Defensive: shim swore filled but didn't return a ticket.
            # Demote to rejected so we don't lie to the LIVE bucket.
            if not broker_trade_id or fill_price is None:
                return BrokerOrderResult(
                    status="rejected",
                    broker_trade_id=None,
                    fill_price=None,
                    reject_reason="shim_filled_without_ticket_or_price",
                    raw={"request_body": request_body, "response": payload},
                )
            return BrokerOrderResult(
                status="filled",
                broker_trade_id=str(broker_trade_id),
                fill_price=float(fill_price),
                reject_reason=None,
                raw={"request_body": request_body, "response": payload},
            )
        # Anything else → rejected. We deliberately collapse "sent"
        # from the shim into rejected at the runner boundary: cfd-trader
        # currently has no async-fill reconciliation pipeline, so
        # treating "sent" as not-live keeps the LIVE bucket strictly
        # truthful. The full response stays in raw for debugging.
        return BrokerOrderResult(
            status="rejected",
            broker_trade_id=None,
            fill_price=None,
            reject_reason=payload.get("reject_reason") or f"non_filled:{status}",
            raw={"request_body": request_body, "response": payload},
        )
