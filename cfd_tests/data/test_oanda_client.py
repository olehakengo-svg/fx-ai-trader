from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from cfd_trader.data.oanda_client import (
    OandaClient,
    CandleFetchError,
)


SAMPLE_RESPONSE = {
    "instrument": "SPX500_USD",
    "granularity": "M5",
    "candles": [
        {
            "time": "2026-05-07T12:00:00.000000000Z",
            "complete": True,
            "volume": 123,
            "mid": {"o": "5000.5", "h": "5005.0", "l": "4998.0", "c": "5003.2"},
        },
        {
            "time": "2026-05-07T12:05:00.000000000Z",
            "complete": False,
            "volume": 45,
            "mid": {"o": "5003.2", "h": "5004.0", "l": "5001.0", "c": "5002.0"},
        },
    ],
}


@patch("cfd_trader.data.oanda_client.requests.get")
def test_get_candles_returns_normalized_dataframe(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_get.return_value = mock_resp

    client = OandaClient(token="x", account_id="y", env="practice")
    df = client.get_candles("SPX500_USD", "M5", count=2)

    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume", "complete"]
    assert len(df) == 2
    assert df.iloc[0]["close"] == pytest.approx(5003.2)
    assert df.iloc[0]["complete"] is True
    assert df.iloc[1]["complete"] is False
    assert df["time"].dtype.kind == "M"  # datetime64


@patch("cfd_trader.data.oanda_client.requests.get")
def test_get_candles_raises_on_http_error(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"errorMessage": "Invalid Authorization"}'
    mock_get.return_value = mock_resp

    client = OandaClient(token="x", account_id="y", env="practice")
    with pytest.raises(CandleFetchError):
        client.get_candles("SPX500_USD", "M5", count=2)


@patch("cfd_trader.data.oanda_client.requests.get")
def test_get_candles_sends_from_and_to_when_provided(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_get.return_value = mock_resp

    client = OandaClient(token="x", account_id="y", env="practice")
    _ = client.get_candles(
        "SPX500_USD", "M5",
        from_iso="2026-02-11T00:00:00Z",
        to_iso="2026-02-11T01:00:00Z",
    )
    call_kwargs = mock_get.call_args
    # requests.get is called with positional url then keyword params
    sent_params = call_kwargs.kwargs.get("params", {})
    assert sent_params.get("from") == "2026-02-11T00:00:00Z"
    assert sent_params.get("to") == "2026-02-11T01:00:00Z"
    # count should NOT be present when from/to are given
    assert "count" not in sent_params


@pytest.mark.live_api
def test_live_oanda_returns_spx500_candles() -> None:
    token = os.environ.get("OANDA_API_TOKEN")
    account = os.environ.get("OANDA_ACCOUNT_ID")
    env = os.environ.get("OANDA_ENV", "practice")
    if not token or not account:
        pytest.skip("OANDA credentials not configured")
    client = OandaClient(token=token, account_id=account, env=env)
    df = client.get_candles("SPX500_USD", "M5", count=10)
    assert len(df) == 10
    assert (df["close"] > 0).all()
    assert {"open", "high", "low", "close", "volume", "complete"}.issubset(set(df.columns))
