"""OANDA REST candle fetcher for cfd-trader.

Section 5.H: indices use point units. This module returns raw OHLC values;
unit conversion happens downstream in engine/.

Reference: https://developer.oanda.com/rest-live-v20/instrument-ep/
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import requests

ENV_BASE_URLS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live":     "https://api-fxtrade.oanda.com",
}


class CandleFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class OandaClient:
    token: str
    account_id: str
    env: Literal["practice", "live"] = "practice"
    timeout_s: float = 10.0

    def _base(self) -> str:
        if self.env not in ENV_BASE_URLS:
            raise ValueError(f"unknown OANDA_ENV: {self.env}")
        return ENV_BASE_URLS[self.env]

    def get_candles(
        self,
        instrument: str,
        granularity: str,
        count: int = 500,
        price: str = "M",
        from_iso: str | None = None,
        to_iso: str | None = None,
    ) -> pd.DataFrame:
        """Fetch candles for `instrument` at `granularity`.

        If `from_iso` and/or `to_iso` are supplied, they take precedence over
        `count` and are passed as `from=` / `to=` query params (OANDA v20
        windowed fetch). When both are None (the existing default), `count` is
        used unchanged — all existing callers remain compatible.

        Returns a DataFrame with columns:
            time (datetime64[ns, UTC]), open, high, low, close, volume, complete
        """
        url = f"{self._base()}/v3/instruments/{instrument}/candles"
        headers = {"Authorization": f"Bearer {self.token}"}
        params: dict[str, object] = {"granularity": granularity, "price": price}
        if from_iso is not None or to_iso is not None:
            if from_iso is not None:
                params["from"] = from_iso
            if to_iso is not None:
                params["to"] = to_iso
        else:
            params["count"] = count
        resp = requests.get(url, headers=headers, params=params, timeout=self.timeout_s)
        if resp.status_code != 200:
            raise CandleFetchError(
                f"OANDA candles {instrument} {granularity} failed "
                f"status={resp.status_code} body={resp.text[:300]}"
            )
        payload = resp.json()
        candles = payload.get("candles", [])
        rows = []
        for c in candles:
            mid = c.get("mid", {})
            rows.append(
                {
                    "time": c["time"],
                    "open": float(mid["o"]),
                    "high": float(mid["h"]),
                    "low":  float(mid["l"]),
                    "close": float(mid["c"]),
                    "volume": int(c.get("volume", 0)),
                    "complete": bool(c.get("complete", False)),
                }
            )
        df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume", "complete"])
        df["time"] = pd.to_datetime(df["time"], utc=True)
        # Preserve native Python bool so identity checks (is True / is False) work
        df["complete"] = df["complete"].astype(object)
        return df

# ---------------------------------------------------------------------------
# Instrument specifications (Section 5.H mandate: no magic numbers downstream).
# Values for SPX500_USD / US500 sourced from Phase 0 report Section 3b
# (https://www.oanda.jp/cfd/lineup as of 2026-05-11).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InstrumentSpec:
    """Canonical per-instrument specification, broker-agnostic.

    Names diverge across data sources:
    - `oanda_v20_name` is what the v20 REST API expects (e.g. SPX500_USD).
    - `mt5_name` is what the MT5 order layer (Phase 4) sees (e.g. US500).
    """
    oanda_v20_name: str
    mt5_name: str
    display_precision: int        # decimal places of price
    point_unit: float             # 10^(-display_precision)
    minimum_trade_size: int       # smallest unit count tradeable
    trade_units_precision: int    # 0 = integer units
    margin_rate: float            # e.g. 0.10 = 10%
    leverage: int                 # 1 / margin_rate
    max_single_order_units: int
    max_position_units: int


SPX500_USD_SPEC = InstrumentSpec(
    oanda_v20_name="SPX500_USD",
    mt5_name="US500",
    display_precision=1,
    point_unit=0.1,
    minimum_trade_size=1,
    trade_units_precision=0,
    margin_rate=0.10,
    leverage=10,
    max_single_order_units=2000,
    max_position_units=2500,
)
