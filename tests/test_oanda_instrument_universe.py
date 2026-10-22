# -*- coding: utf-8 -*-
"""tools/oanda_instrument_universe.py — summarize は純関数で、トークン等を記録せず、
貴金属の有無と型別件数を正しく数える (2026-10-22 R3)。"""
from tools import oanda_instrument_universe as oiu


def _inst(name, typ="CURRENCY", prec=5, pip=-4, margin="0.04"):
    return {"name": name, "type": typ, "displayName": name.replace("_", "/"),
            "displayPrecision": prec, "pipLocation": pip, "tradeUnitsPrecision": 0,
            "minimumTradeSize": "1", "maximumOrderUnits": "100000000",
            "maximumPositionSize": "0", "marginRate": margin,
            "guaranteedStopLossOrderMode": "DISABLED",
            "financing": {"longRate": "0.01", "shortRate": "-0.02"},
            "tags": [{"type": "ASSET_CLASS", "name": "CURRENCY"}]}


def test_summarize_counts_types_and_detects_metals():
    payload = {"instruments": [_inst("USD_JPY", prec=3, pip=-2), _inst("EUR_USD"),
                               _inst("XAU_USD", typ="METAL", prec=3, pip=-2)]}
    s = oiu.summarize(payload)
    assert s["n_instruments"] == 3
    assert s["by_type"] == {"CURRENCY": 2, "METAL": 1}
    assert s["metals_present"] == ["XAU_USD"]
    assert s["jpy_quote"] == ["USD_JPY"]
    usd = [r for r in s["instruments"] if r["name"] == "USD_JPY"][0]
    assert usd["displayPrecision"] == 3 and usd["pipLocation"] == -2
    assert usd["financing"] == {"longRate": "0.01", "shortRate": "-0.02"}
    assert usd["tags"] == ["CURRENCY"]


def test_summarize_empty_payload_is_zero_not_error():
    s = oiu.summarize({})
    assert s["n_instruments"] == 0 and s["by_type"] == {} and s["metals_present"] == []


def test_summarize_never_records_credentials(monkeypatch):
    # 環境にある資格情報の **値** が出力に漏れないこと (語としての "token" は note に含まれてよい)
    monkeypatch.setenv("OANDA_TOKEN", "sentinel-token-value-xyz")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "001-sentinel-account")
    s = oiu.summarize({"instruments": [_inst("USD_JPY")]})
    text = str(s)
    assert "sentinel-token-value-xyz" not in text and "001-sentinel-account" not in text
    assert not ({"token", "account_id", "OANDA_TOKEN"} & set(s.keys()))
