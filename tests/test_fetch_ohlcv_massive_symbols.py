import json

import pandas as pd

from modules.data import fetch_ohlcv_massive


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def test_fetch_ohlcv_massive_accepts_underscore_fx_symbol(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        return _FakeResponse(
            {
                "results": [
                    {
                        "t": int(pd.Timestamp("2026-05-01T00:00:00Z").timestamp() * 1000),
                        "o": 191.1,
                        "h": 191.3,
                        "l": 190.9,
                        "c": 191.2,
                        "v": 10,
                    }
                ]
            }
        )

    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    df = fetch_ohlcv_massive("GBP_JPY", "15m", days=1)

    assert "C:GBPJPY" in captured["url"]
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume", "vwap"]
    assert len(df) == 1
