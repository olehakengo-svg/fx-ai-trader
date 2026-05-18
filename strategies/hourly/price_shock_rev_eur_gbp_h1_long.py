from strategies.hourly.price_shock_reversion_base import PriceShockRevConfig, PriceShockReversionBase


class PriceShockRevEurGbpH1Long(PriceShockReversionBase):
    cfg = PriceShockRevConfig(
        name="price_shock_rev_eur_gbp_h1_long",
        pair="EUR_GBP",
        percentile=0.01,
        horizon_bars=3,
        vol_q="Q5",
    )
