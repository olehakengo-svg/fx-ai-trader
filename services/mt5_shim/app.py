"""Flask app — POST /v1/orders/market → MT5 order_send.

Auth: HMAC-SHA256 over (timestamp + "." + raw_body). Spec:
../../cfd_trader/broker/SHIM_SPEC.md.

Idempotency: identical ``client_order_id`` returns the original
result. Cache is in-memory and small (last 4096 ids); restart loses it
but that's acceptable — duplicate requests within a few seconds is
the only realistic case.
"""
from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import asdict
from typing import Any

from flask import Flask, jsonify, request

from services.mt5_shim.auth import verify
from services.mt5_shim.mt5_adapter import FillResponse, MT5Adapter


ENV_SECRET = "CFD_MT5_SHIM_SECRET"

# Idempotency cache size. 4096 is enough to dedupe a burst of retries
# without bounding memory growth — the runner reruns at minute-scale.
IDEMPOTENCY_CACHE_LIMIT = 4096


def create_app(*, adapter: Any | None = None, secret: bytes | None = None) -> Flask:
    """Construct a Flask app.

    The adapter and secret are injectable so tests can substitute a
    FakeMT5Adapter and a known secret. Production calls
    ``create_app()`` with no args and reads from the environment.
    """
    app = Flask(__name__)
    if adapter is None:
        adapter = MT5Adapter()
    if secret is None:
        secret_str = os.environ.get(ENV_SECRET, "")
        if not secret_str:
            raise RuntimeError(f"{ENV_SECRET} not set; refuse to start unauthenticated")
        secret = secret_str.encode("utf-8")

    app.config["MT5_ADAPTER"] = adapter
    app.config["SHIM_SECRET"] = secret
    app.config["IDEMPOTENCY"] = OrderedDict()  # type: OrderedDict[str, FillResponse]

    @app.get("/v1/health")
    def health():
        return jsonify({"ok": True}), 200

    @app.post("/v1/orders/market")
    def post_market_order():
        body_bytes = request.get_data() or b""
        auth = verify(
            secret=app.config["SHIM_SECRET"],
            timestamp_header=request.headers.get("X-Timestamp"),
            signature_header=request.headers.get("X-Signature"),
            body_bytes=body_bytes,
        )
        if not auth.ok:
            return jsonify({
                "status": "rejected",
                "broker_trade_id": None,
                "fill_price": None,
                "reject_reason": f"auth:{auth.reason}",
                "raw": {},
            }), 401

        try:
            payload = request.get_json(force=True, silent=False)
        except Exception:
            return jsonify({
                "status": "rejected", "broker_trade_id": None, "fill_price": None,
                "reject_reason": "invalid_json_body", "raw": {},
            }), 400

        missing = _missing_required_fields(payload)
        if missing:
            return jsonify({
                "status": "rejected", "broker_trade_id": None, "fill_price": None,
                "reject_reason": f"missing_fields:{','.join(missing)}", "raw": {},
            }), 400

        client_order_id = str(payload["client_order_id"])
        idem: OrderedDict[str, FillResponse] = app.config["IDEMPOTENCY"]
        if client_order_id in idem:
            return jsonify(_fill_to_dict(idem[client_order_id])), 200

        adapter_local = app.config["MT5_ADAPTER"]
        try:
            fill = adapter_local.place_market(
                instrument=str(payload["instrument"]),
                side=str(payload["side"]),
                units=int(payload["units"]),
                signal_price=float(payload["signal_price"]),
                client_order_id=client_order_id,
            )
        except Exception as exc:
            # Surface adapter crashes as a rejection rather than a 5xx
            # so the client logs a consistent reject_reason. The shim's
            # local logs still have the full traceback for forensics.
            app.logger.exception("MT5 adapter raised")
            return jsonify({
                "status": "rejected", "broker_trade_id": None, "fill_price": None,
                "reject_reason": f"adapter_exception:{type(exc).__name__}",
                "raw": {},
            }), 200

        # Cache successful AND rejected outcomes — both are deterministic
        # for the given client_order_id and we want retries to be safe.
        idem[client_order_id] = fill
        while len(idem) > IDEMPOTENCY_CACHE_LIMIT:
            idem.popitem(last=False)

        return jsonify(_fill_to_dict(fill)), 200

    return app


_REQUIRED = ("instrument", "side", "units", "signal_price", "client_order_id")


def _missing_required_fields(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return list(_REQUIRED)
    return [k for k in _REQUIRED if k not in payload]


def _fill_to_dict(fill: FillResponse) -> dict[str, Any]:
    return asdict(fill)
