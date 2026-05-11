"""catalog: register/get/duplicate protection."""
from __future__ import annotations

import pandas as pd
import pytest

from cfd_trader.strategies import catalog


@pytest.fixture(autouse=True)
def _reset_registry():
    saved = dict(catalog.STRATEGIES)
    catalog.STRATEGIES.clear()
    yield
    catalog.STRATEGIES.clear()
    catalog.STRATEGIES.update(saved)


def test_register_and_get_roundtrip() -> None:
    def f(c: pd.DataFrame, p: dict) -> pd.DataFrame:
        return pd.DataFrame()
    catalog.register("noop", f)
    assert catalog.get("noop") is f


def test_register_rejects_duplicates() -> None:
    def f(c: pd.DataFrame, p: dict) -> pd.DataFrame:
        return pd.DataFrame()
    catalog.register("noop", f)
    with pytest.raises(ValueError):
        catalog.register("noop", f)


def test_get_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        catalog.get("missing")
