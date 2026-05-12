# cfd-trader MT5 shim

Thin Flask service that runs on a Windows VPS, has MetaTrader 5 + the
`MetaTrader5` Python package installed, and is signed in to the OANDA
CFD account. cfd-trader on macOS/Render talks to it via the HTTP
protocol defined in [`../../cfd_trader/broker/SHIM_SPEC.md`](../../cfd_trader/broker/SHIM_SPEC.md).

## Provisioning

1. **VPS**: any Windows Server 2019 / 2022 instance. Minimum spec is
   small — MT5 + Python + this shim fit comfortably in 2 GB RAM. The
   VPS exists to host MT5; nothing else.
2. **MT5**: install from <https://www.oanda.jp/lab-education/mt5/> and
   log in to the OANDA CFD account (the same one identified by
   account_id `900190542`). Enable Algo Trading in the Tools menu.
3. **Python**: install Python 3.11+. Then:

   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Secret**: generate a random 32-byte secret (the same value cfd-trader
   sees as `CFD_MT5_SHIM_SECRET`). Set it for the service:

   ```cmd
   set CFD_MT5_SHIM_SECRET=<the-secret>
   ```

5. **Run** (development):

   ```cmd
   set FLASK_APP=services.mt5_shim.app:create_app
   flask run --host 0.0.0.0 --port 8443
   ```

   Run (production, with Waitress):

   ```cmd
   waitress-serve --listen=0.0.0.0:8443 "services.mt5_shim.app:create_app()"
   ```

6. **TLS termination**: do NOT expose plain HTTP to the public internet.
   Either:
   - Run behind Cloudflare Tunnel / Tailscale (recommended — easiest),
     or
   - Front with `caddy` / `nginx` for an HTTPS cert.

7. **cfd-trader side**: on Render / locally, set:

   ```bash
   export CFD_MT5_SHIM_URL=https://<vps-hostname-or-tunnel>
   export CFD_MT5_SHIM_SECRET=<same-secret>
   ```

   On next runner cycle, the broker factory picks up MT5RemoteBroker
   automatically (see `cfd_trader/broker/factory.py`).

## Health check

```
GET /v1/health
→ 200 {"ok": true}
```

Use this from cfd-trader / monitoring to verify the shim is alive
without firing an order.

## Order endpoint

See [SHIM_SPEC.md](../../cfd_trader/broker/SHIM_SPEC.md) for the wire
protocol; this README only covers running the service.

## Idempotency

The shim caches the last 4096 `client_order_id` → result mappings
in-memory. A duplicate POST returns the original result. The cache
is lost on restart — that's intentional, the runner's retry window is
short and a restart breaks idempotency only across multi-second gaps.

## Operational notes

- MT5 occasionally drops the connection. The adapter retries once on
  `order_send → None`. If that fails the order is reported as
  `mt5_reinit_failed`.
- The Windows machine must be NTP-synced. The shim rejects requests
  whose `X-Timestamp` is more than 60 seconds off.
- Algo Trading must remain enabled in MT5. Disabling it will cause
  every order to fail with `retcode_10027` (TRADE_DISABLED).
- Magic number 270512 tags shim orders. Manually-placed orders use a
  different magic and the shim ignores them.
