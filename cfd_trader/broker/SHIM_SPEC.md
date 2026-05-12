# cfd-trader MT5 shim — wire protocol

The shim is a tiny Flask service that runs on a Windows VPS, has
MetaTrader 5 + the `MetaTrader5` Python package installed, and is
signed in to the OANDA CFD account. cfd-trader speaks to it via the
HTTP protocol defined here.

The shim is **broker-aware** (knows MT5 deal/order semantics, knows
that `SPX500_USD` → `US500`); cfd-trader is **broker-agnostic** (only
knows `BrokerOrderResult`).

## Authentication

Every request is HMAC-SHA256 signed. There is no token / no IP allowlist
as primary control — the shared secret is the auth boundary.

Headers on every request:

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `X-Timestamp` | Unix epoch seconds, integer string |
| `X-Signature` | `hex(hmac_sha256(secret, timestamp + "." + raw_body))` |

The body is canonicalized as `json.dumps(payload, separators=(",", ":"), sort_keys=True)` on the client. The shim MUST sign the raw bytes it received, NOT a re-serialized version, to keep the signature stable.

Rejected on the shim side:
- `X-Timestamp` older than 60s → `401 stale_timestamp`
- `X-Signature` mismatch → `401 bad_signature`
- Missing headers → `400 missing_auth_header`

## Endpoint: `POST /v1/orders/market`

### Request

```json
{
  "instrument": "US500",
  "side": "long",
  "units": 1,
  "signal_price": 5000.0,
  "client_order_id": "8c1d2f3a4b5e6789..."
}
```

`instrument` is the MT5 symbol (the shim does the mapping back to
display names if needed — cfd-trader uses MT5-side names so the wire
is unambiguous).

`client_order_id` is a UUID4 hex chosen by cfd-trader. The shim MUST
treat duplicate IDs as idempotent (return the original result) — this
protects against retries crossing with a successful first call.

### Response — filled

HTTP 200:

```json
{
  "status": "filled",
  "broker_trade_id": "84212391",
  "fill_price": 5000.25,
  "raw": {
    "deal": 84212391,
    "order": 84212390,
    "retcode": 10009,
    "request_id": 1234567
  }
}
```

`broker_trade_id` is whatever ticket is most useful for reconciliation.
For MT5 this is the deal ticket as a string. cfd-trader stores it
verbatim in `oanda_audit.broker_trade_id` and uses presence-or-absence
as the LIVE bucket predicate (see `cfd_trader/audit/oanda_audit.py`).

### Response — rejected

HTTP 200 (yes 200 — rejection is a normal business outcome, not an
HTTP error):

```json
{
  "status": "rejected",
  "broker_trade_id": null,
  "fill_price": null,
  "reject_reason": "TRADE_RETCODE_REJECT",
  "raw": {"retcode": 10006, ...}
}
```

cfd-trader collapses any non-`filled` status into `rejected`. The shim
should still send the canonical retcode in `raw` for forensics.

### Response — error

5xx is reserved for "shim itself broke" (MT5 disconnected, Python
crashed). cfd-trader treats every non-200 as rejected with
`reject_reason="http_<code>"`.

## Out of scope (intentional)

- **Close position / modify SL**: cfd-trader's Phase 2 strategies are
  bar-exit (`orb_ny_open_short` closes at session end via a separate
  signal). Adding `/v1/positions/{ticket}/close` is a future task —
  do NOT add it speculatively.
- **Streaming prices**: cfd-trader pulls candles from OANDA's REST API
  directly. The shim is only an order ingress.
- **Account info / margin**: also pulled from OANDA REST directly on
  the FX side. CFD-side margin needs are deferred until we have an
  actual sizing routine using them.

## Operational notes

- The VPS must run on UTC or NTP-synced local time. The 60s timestamp
  window leaves no room for clock skew.
- The shim should log every request body + signature verify result to
  a rolling file for audit. cfd-trader trusts the shim's logs as the
  source of truth for "what we asked the broker to do".
- Restart policy: MT5 occasionally drops the connection. The shim
  should detect (`mt5.last_error()` after a failed call), reconnect,
  and retry once. If that fails, return `status=rejected, reject_reason="mt5_disconnected"`.
