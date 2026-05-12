"""Probe: does the configured OANDA account expose CFD instruments via v20 REST?

Usage:
  python3 scripts/cfd_check_oanda_rest_cfd_support.py --token <TOKEN> --account <ACCOUNT_ID> [--env live|practice]
  OR
  OANDA_CFD_TOKEN=... OANDA_CFD_ACCOUNT=... python3 scripts/cfd_check_oanda_rest_cfd_support.py

Hits `/v3/accounts/{id}/instruments` against the international (api-fxtrade.oanda.com)
endpoint AND OANDA Japan (api-fxtrade.oanda.jp) and reports per host:
  - HTTP status
  - total tradeable instrument count
  - whether SPX500_USD / NAS100_USD / US30_USD are present
  - sample of CFD-looking instruments (those NOT formatted as ISO_ISO forex pairs)

Does NOT print tokens, account_id, or any other secret material. Only
prints the *answer* you need to decide REST-direct vs MT5-bridge.
"""
from __future__ import annotations

import argparse
import os
import sys
import json

import requests


ENV_BASE = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}

# Probe a few JP-specific hosts too — OANDA Japan historically had its own
# stack. If the international endpoint refuses but a JP host accepts, we
# learn which entity the account belongs to.
JP_PROBE_HOSTS = [
    "https://api-fxtrade.oanda.jp",
]


def probe_accounts_list(base: str, token: str) -> dict:
    """List which account_ids this token can access on this endpoint.

    Returns {host, status, accounts: [{id, tags...}]} or {host, error: ...}.
    Account IDs are returned because they are needed to call the per-account
    endpoints — not secret on their own (token is the secret).
    """
    url = f"{base}/v3/accounts"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as e:
        return {"host": base, "error": f"network: {e}"}
    out: dict = {"host": base, "status": r.status_code}
    if r.status_code != 200:
        out["body_head"] = r.text[:200]
        return out
    payload = r.json()
    accts = payload.get("accounts", [])
    out["account_count"] = len(accts)
    out["accounts"] = [
        {"id": a.get("id"), "tags": a.get("tags", [])} for a in accts
    ]
    return out


def probe(base: str, token: str, account: str) -> dict:
    url = f"{base}/v3/accounts/{account}/instruments"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as e:
        return {"host": base, "error": f"network: {e}"}
    out: dict = {"host": base, "status": r.status_code}
    if r.status_code != 200:
        out["body_head"] = r.text[:200]
        return out
    payload = r.json()
    insts = payload.get("instruments", [])
    names = sorted(i.get("name", "") for i in insts)
    out["instrument_count"] = len(names)
    out["has_SPX500_USD"] = "SPX500_USD" in names
    out["has_NAS100_USD"] = "NAS100_USD" in names
    out["has_US30_USD"] = "US30_USD" in names
    cfd_like = [
        n for n in names
        if n and "_" in n and not (
            len(n.split("_")[0]) == 3 and len(n.split("_")[1]) == 3
            and n.split("_")[0].isalpha() and n.split("_")[1].isalpha()
        )
    ]
    out["cfd_like_count"] = len(cfd_like)
    out["cfd_like_all"] = cfd_like
    # Also dump every instrument so we can see exactly what this account
    # has access to — definitive answer.
    out["all_instruments"] = names
    # Group by type tag from the OANDA response (CURRENCY / CFD / METAL)
    by_type: dict[str, list[str]] = {}
    for i in insts:
        t = i.get("type", "?")
        by_type.setdefault(t, []).append(i.get("name", ""))
    out["by_type_count"] = {k: len(v) for k, v in by_type.items()}
    out["by_type_sample"] = {k: sorted(v)[:5] for k, v in by_type.items()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("OANDA_CFD_TOKEN", ""))
    ap.add_argument("--account", default=os.environ.get("OANDA_CFD_ACCOUNT", ""))
    ap.add_argument("--env", default="live", choices=["live", "practice"])
    args = ap.parse_args()

    if not args.token or not args.account:
        print(
            "MISSING_INPUT: pass --token / --account or set "
            "OANDA_CFD_TOKEN / OANDA_CFD_ACCOUNT",
            file=sys.stderr,
        )
        return 2

    primary = ENV_BASE[args.env]
    print(f"== STEP 1: list accounts visible to this token on {primary}")
    accts_resp = probe_accounts_list(primary, args.token)
    print(json.dumps(accts_resp, indent=2, ensure_ascii=False))

    # STEP 2: probe instruments for the supplied account AND every other
    # account this token can see (to find which one — if any — exposes CFDs).
    candidates: list[str] = [args.account]
    for a in accts_resp.get("accounts", []) or []:
        if a.get("id") and a["id"] not in candidates:
            candidates.append(a["id"])

    for acc in candidates:
        print()
        print(f"== STEP 2: probe instruments for account={acc} on {primary}")
        print(json.dumps(probe(primary, args.token, acc), indent=2, ensure_ascii=False))

    print()
    print("== STEP 3: also try practice endpoint (token may be live-only)")
    practice = ENV_BASE["practice"]
    print(json.dumps(probe_accounts_list(practice, args.token), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
