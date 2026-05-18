from modules.demo_trader import DemoTrader


def test_trend_rebound_in_force_demoted():
    assert "trend_rebound" in DemoTrader._FORCE_DEMOTED


def test_trend_rebound_not_in_pair_promoted():
    assert ("trend_rebound", "USD_JPY") not in DemoTrader._PAIR_PROMOTED


def test_trend_rebound_not_in_pair_demoted():
    assert ("trend_rebound", "EUR_USD") not in DemoTrader._PAIR_DEMOTED
