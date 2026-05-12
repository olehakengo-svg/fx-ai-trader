"""Pick the right BrokerClient implementation based on env config.

This is the single place that env-var → implementation mapping happens.
Tests construct concrete brokers directly; production wiring (runner /
flask app boot) calls ``build_broker_from_env()``.
"""
from __future__ import annotations

import os

from cfd_trader.broker.protocol import BrokerClient
from cfd_trader.broker.null import NullBroker
from cfd_trader.broker.mt5_remote import MT5RemoteBroker


# Env var names — keep here, not scattered.
ENV_SHIM_URL = "CFD_MT5_SHIM_URL"
ENV_SHIM_SECRET = "CFD_MT5_SHIM_SECRET"
ENV_TIMEOUT_S = "CFD_MT5_SHIM_TIMEOUT_S"


def build_broker_from_env(env: dict[str, str] | None = None) -> BrokerClient:
    """Return MT5RemoteBroker if shim is fully configured, else NullBroker.

    Both URL and secret must be present and non-empty. A partial
    configuration (URL but no secret, etc.) falls back to NullBroker —
    fail-closed rather than silently sending unsigned requests.
    """
    e = env if env is not None else os.environ
    url = (e.get(ENV_SHIM_URL) or "").strip()
    secret = (e.get(ENV_SHIM_SECRET) or "").strip()
    if not url or not secret:
        return NullBroker()
    timeout_raw = (e.get(ENV_TIMEOUT_S) or "").strip()
    try:
        timeout_s = float(timeout_raw) if timeout_raw else MT5RemoteBroker.DEFAULT_TIMEOUT_S
    except ValueError:
        timeout_s = MT5RemoteBroker.DEFAULT_TIMEOUT_S
    return MT5RemoteBroker(base_url=url, secret=secret, timeout_s=timeout_s)


def broker_status_from_env(env: dict[str, str] | None = None) -> dict[str, object]:
    """Return a small dict describing broker config for the UI.

    Never leaks the secret. The URL is shown verbatim because it is
    not a credential — the secret is what authorizes calls.
    """
    e = env if env is not None else os.environ
    url = (e.get(ENV_SHIM_URL) or "").strip()
    secret = (e.get(ENV_SHIM_SECRET) or "").strip()
    if url and secret:
        secret_tail = secret[-4:] if len(secret) >= 4 else "****"
        return {
            "configured": True,
            "kind": "mt5_remote",
            "shim_url": url,
            "secret_tail": f"…{secret_tail}",
        }
    return {
        "configured": False,
        "kind": "null",
        "reason": _missing_reason(url, secret),
    }


def _missing_reason(url: str, secret: str) -> str:
    if not url and not secret:
        return f"{ENV_SHIM_URL} and {ENV_SHIM_SECRET} not set"
    if not url:
        return f"{ENV_SHIM_URL} not set"
    return f"{ENV_SHIM_SECRET} not set"
