"""Unit tests for production_fetcher error handling.

These tests do NOT hit the live Render API; they mock urlopen.
"""
from __future__ import annotations
import io
import json
from unittest import mock

import pytest

from research.edge_discovery import production_fetcher as pf


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestSafeGetJson:
    def test_valid_json(self):
        payload = {"trades": [{"id": 1}]}
        with mock.patch.object(pf, "urlopen",
                               return_value=_FakeResp(json.dumps(payload).encode())):
            data = pf._safe_get_json("http://x", timeout_sec=10)
        assert data == payload

    def test_non_json_raises_with_snippet(self):
        """Render cold-start HTML must not crash — must raise ProductionFetchError."""
        html = b"<!DOCTYPE html><html><body>Render is booting up...</body></html>"
        with mock.patch.object(pf, "urlopen",
                               return_value=_FakeResp(html)):
            with pytest.raises(pf.ProductionFetchError) as exc:
                pf._safe_get_json("http://x", timeout_sec=10)
        assert "Non-JSON" in str(exc.value)
        assert "Render" in str(exc.value)  # snippet should contain payload

    def test_http_500_raises(self):
        from urllib.error import HTTPError
        err = HTTPError("http://x", 500, "Internal Server Error", hdrs=None, fp=None)
        with mock.patch.object(pf, "urlopen", side_effect=err):
            with pytest.raises(pf.ProductionFetchError) as exc:
                pf._safe_get_json("http://x", timeout_sec=10)
        assert "500" in str(exc.value)

    def test_network_error_raises(self):
        from urllib.error import URLError
        with mock.patch.object(pf, "urlopen", side_effect=URLError("connection refused")):
            with pytest.raises(pf.ProductionFetchError) as exc:
                pf._safe_get_json("http://x", timeout_sec=10)
        assert "Network" in str(exc.value)

    def test_status_400_raises(self):
        """Server returns 400 body but no HTTPError (edge case)."""
        with mock.patch.object(pf, "urlopen",
                               return_value=_FakeResp(b"{}", status=400)):
            with pytest.raises(pf.ProductionFetchError) as exc:
                pf._safe_get_json("http://x", timeout_sec=10)
        assert "400" in str(exc.value)


class TestFetchClosedTradesErrorPropagation:
    def test_fetcher_surfaces_api_errors(self):
        """Analysis callers must see a ProductionFetchError, not silent empty DF."""
        from urllib.error import URLError
        with mock.patch.object(pf, "urlopen", side_effect=URLError("down")):
            with pytest.raises(pf.ProductionFetchError):
                pf.fetch_closed_trades(date_from="2026-04-08")

    def test_fetcher_empty_trades_list_returns_empty_df(self):
        """Legitimate empty response should still return empty DataFrame."""
        with mock.patch.object(pf, "urlopen",
                               return_value=_FakeResp(json.dumps({"trades": []}).encode())):
            df = pf.fetch_closed_trades(date_from="2026-04-08")
        assert df.empty
