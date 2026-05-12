"""HMAC verification + timestamp-replay window for incoming requests.

The shim's only auth control is HMAC-SHA256 over (timestamp + "." + body).
Both sides must agree on the secret; cfd-trader's MT5RemoteBroker
produces the signature, this module verifies it.

Spec: ../../cfd_trader/broker/SHIM_SPEC.md
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

# How far the request's X-Timestamp may drift from the server clock
# before we reject. 60s leaves no useful room for clock skew, but a
# legitimate request will normally arrive in well under one second.
# Both ends MUST be NTP-synced.
MAX_TIMESTAMP_SKEW_S = 60


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    reason: str | None  # populated on rejection so 401s say why


def verify(
    *,
    secret: bytes,
    timestamp_header: str | None,
    signature_header: str | None,
    body_bytes: bytes,
    now_unix: int | None = None,
) -> AuthResult:
    """Return AuthResult; never raises for a malformed request.

    ``now_unix`` exists for tests to pin time; production passes None
    and we read the real clock.
    """
    if not timestamp_header:
        return AuthResult(False, "missing_X_Timestamp")
    if not signature_header:
        return AuthResult(False, "missing_X_Signature")

    try:
        ts = int(timestamp_header)
    except ValueError:
        return AuthResult(False, "X_Timestamp_not_int")

    now = now_unix if now_unix is not None else int(time.time())
    if abs(now - ts) > MAX_TIMESTAMP_SKEW_S:
        return AuthResult(False, "stale_timestamp")

    expected = hmac.new(
        secret,
        timestamp_header.encode("utf-8") + b"." + body_bytes,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        return AuthResult(False, "bad_signature")

    return AuthResult(True, None)
