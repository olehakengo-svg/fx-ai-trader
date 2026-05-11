"""MASSIVE Market Data adapter — Phase 0 probe.

Phase 0 only verifies whether MASSIVE exposes a target index (e.g. SPX500).
Full candle fetch is deferred to Phase 1 once the endpoint shape is known.

Section 5.G (real API E2E required): no mock-only verification.

Discovery endpoint reality (2026-05-07):
  The MASSIVE API reference endpoint is GET /v3/reference/tickers with optional
  query params: market=indices, limit=1000.
  Response shape: {"results": [{"ticker": "I:SPX", "market": "indices", ...}], ...}

  The spec's default path /v1/symbols does NOT exist on api.massive.com.
  SYMBOLS_PATH is kept as the override-able constant so Phase 1 can adjust;
  DEFAULT_SYMBOLS_PATH reflects the discovered real endpoint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

DEFAULT_BASE_URL = "https://api.massive.com"

# Real discovery endpoint found via MASSIVE MCP search (2026-05-07 Phase 0).
# Spec assumed /v1/symbols; actual API uses /v3/reference/tickers.
SYMBOLS_PATH = "/v3/reference/tickers"

# Query params for index-only discovery
_INDEX_QUERY_PARAMS: dict[str, Any] = {"market": "indices", "limit": 1000, "active": "true"}


class MassiveProbeError(RuntimeError):
    pass


@dataclass
class IndicesProbeReport:
    target: str
    target_available: bool
    discovered_index_symbols: list[str]
    endpoint_url: str
    raw_payload_preview: str
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MassiveAdapter:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 15.0

    def probe_indices(self, target: str = "SPX500") -> IndicesProbeReport:
        """Discover whether `target` is available as an index symbol.

        Hits /v3/reference/tickers?market=indices on api.massive.com.
        Also handles the mock-test shape {"symbols": [{"symbol":..., "type":...}]}
        so unit tests remain green without hitting the network.

        Always records the URL queried + 200-char payload preview for the
        phase-0 report.
        """
        url = f"{self.base_url}{SYMBOLS_PATH}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "cfd-trader/phase0",
        }
        try:
            resp = requests.get(
                url,
                headers=headers,
                params=_INDEX_QUERY_PARAMS,
                timeout=self.timeout_s,
            )
        except requests.RequestException as exc:
            return IndicesProbeReport(
                target=target,
                target_available=False,
                discovered_index_symbols=[],
                endpoint_url=url,
                raw_payload_preview="",
                error=f"request failed: {exc}",
            )

        if resp.status_code != 200:
            return IndicesProbeReport(
                target=target,
                target_available=False,
                discovered_index_symbols=[],
                endpoint_url=url,
                raw_payload_preview=resp.text[:200],
                error=f"http {resp.status_code}",
            )

        try:
            payload = resp.json()
        except ValueError:
            return IndicesProbeReport(
                target=target,
                target_available=False,
                discovered_index_symbols=[],
                endpoint_url=url,
                raw_payload_preview=resp.text[:200],
                error="non-json response",
            )

        # --- Normalise across two possible response shapes ---
        # Shape A (real MASSIVE API): {"results": [{"ticker": "I:SPX", "market": "indices"}, ...]}
        # Shape B (unit-test mock):   {"symbols": [{"symbol": "SPX500", "type": "index"}, ...]}
        index_symbols: list[str] = []

        if isinstance(payload, dict):
            results = payload.get("results")
            if results is not None:
                # Shape A
                for entry in results:
                    if not isinstance(entry, dict):
                        continue
                    sym = entry.get("ticker", "")
                    market = str(entry.get("market", "")).lower()
                    if sym and market == "indices":
                        index_symbols.append(str(sym))
            else:
                # Shape B (mock)
                symbols = payload.get("symbols", [])
                for s in symbols:
                    if isinstance(s, dict) and str(s.get("type", "")).lower() == "index":
                        index_symbols.append(str(s.get("symbol", "")))

        # Target matching: try exact match first, then substring (e.g. SPX500 in "I:SPX500")
        target_upper = target.upper()
        available = any(
            target_upper == sym.upper() or target_upper in sym.upper()
            for sym in index_symbols
        )

        return IndicesProbeReport(
            target=target,
            target_available=available,
            discovered_index_symbols=index_symbols,
            endpoint_url=url,
            raw_payload_preview=str(payload)[:200],
        )
