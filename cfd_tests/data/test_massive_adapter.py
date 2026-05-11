from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from cfd_trader.data.massive_adapter import (
    MassiveAdapter,
    IndicesProbeReport,
)


@patch("cfd_trader.data.massive_adapter.requests.get")
def test_probe_indices_returns_structured_report(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"symbols": [
        {"symbol": "SPX500", "type": "index"},
        {"symbol": "EURUSD", "type": "fx"},
    ]}
    mock_get.return_value = mock_resp

    a = MassiveAdapter(api_key="x")
    report = a.probe_indices(target="SPX500")
    assert isinstance(report, IndicesProbeReport)
    assert report.target == "SPX500"
    assert report.target_available is True
    assert "SPX500" in report.discovered_index_symbols


@patch("cfd_trader.data.massive_adapter.requests.get")
def test_probe_indices_handles_missing(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"symbols": [
        {"symbol": "EURUSD", "type": "fx"},
    ]}
    mock_get.return_value = mock_resp

    a = MassiveAdapter(api_key="x")
    report = a.probe_indices(target="SPX500")
    assert report.target_available is False
    assert report.discovered_index_symbols == []


@pytest.mark.live_api
def test_live_massive_probe_returns_real_report() -> None:
    key = os.environ.get("MASSIVE_API_KEY")
    if not key:
        pytest.skip("MASSIVE_API_KEY not configured")
    a = MassiveAdapter(api_key=key)
    report = a.probe_indices(target="SPX500")
    assert report.endpoint_url
    assert isinstance(report.target_available, bool)
