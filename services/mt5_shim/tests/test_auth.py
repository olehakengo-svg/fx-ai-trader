"""HMAC + timestamp window verification."""
from __future__ import annotations

import hashlib
import hmac

from services.mt5_shim.auth import MAX_TIMESTAMP_SKEW_S, verify


SECRET = b"test-secret"


def _sig(ts: str, body: bytes, secret: bytes = SECRET) -> str:
    return hmac.new(secret, ts.encode() + b"." + body, hashlib.sha256).hexdigest()


def test_good_signature_accepted() -> None:
    body = b'{"x":1}'
    r = verify(
        secret=SECRET,
        timestamp_header="1000000",
        signature_header=_sig("1000000", body),
        body_bytes=body,
        now_unix=1000000,
    )
    assert r.ok is True
    assert r.reason is None


def test_bad_signature_rejected() -> None:
    body = b'{"x":1}'
    r = verify(
        secret=SECRET, timestamp_header="1000000",
        signature_header="deadbeef" * 8,  # 64-char hex but wrong
        body_bytes=body, now_unix=1000000,
    )
    assert r.ok is False
    assert r.reason == "bad_signature"


def test_signature_over_wrong_body_rejected() -> None:
    """Signing one body and sending another must fail."""
    body_sent = b'{"x":2}'
    sig_for_other = _sig("1000000", b'{"x":1}')
    r = verify(
        secret=SECRET, timestamp_header="1000000",
        signature_header=sig_for_other, body_bytes=body_sent,
        now_unix=1000000,
    )
    assert r.ok is False
    assert r.reason == "bad_signature"


def test_missing_timestamp_rejected() -> None:
    r = verify(
        secret=SECRET, timestamp_header=None,
        signature_header="ab" * 32, body_bytes=b"{}",
    )
    assert r.ok is False and r.reason == "missing_X_Timestamp"


def test_missing_signature_rejected() -> None:
    r = verify(
        secret=SECRET, timestamp_header="1000000",
        signature_header=None, body_bytes=b"{}",
    )
    assert r.ok is False and r.reason == "missing_X_Signature"


def test_non_int_timestamp_rejected() -> None:
    r = verify(
        secret=SECRET, timestamp_header="not-a-number",
        signature_header="ab" * 32, body_bytes=b"{}",
    )
    assert r.ok is False and r.reason == "X_Timestamp_not_int"


def test_stale_timestamp_rejected() -> None:
    body = b"{}"
    ts = "1000000"
    # Move "now" beyond the window
    now = 1000000 + MAX_TIMESTAMP_SKEW_S + 1
    r = verify(
        secret=SECRET, timestamp_header=ts,
        signature_header=_sig(ts, body), body_bytes=body, now_unix=now,
    )
    assert r.ok is False and r.reason == "stale_timestamp"


def test_future_timestamp_also_rejected_outside_window() -> None:
    body = b"{}"
    ts_future = str(1000000 + MAX_TIMESTAMP_SKEW_S + 1)
    r = verify(
        secret=SECRET, timestamp_header=ts_future,
        signature_header=_sig(ts_future, body),
        body_bytes=body, now_unix=1000000,
    )
    assert r.ok is False and r.reason == "stale_timestamp"


def test_wrong_secret_rejected() -> None:
    body = b"{}"
    sig_other = _sig("1000000", body, secret=b"different-secret")
    r = verify(
        secret=SECRET, timestamp_header="1000000",
        signature_header=sig_other, body_bytes=body, now_unix=1000000,
    )
    assert r.ok is False and r.reason == "bad_signature"
