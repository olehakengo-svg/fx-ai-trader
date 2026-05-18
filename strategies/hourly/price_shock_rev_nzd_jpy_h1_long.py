from strategies.hourly.price_shock_reversion_base import PriceShockRevConfig, PriceShockReversionBase


class PriceShockRevNzdJpyH1Long(PriceShockReversionBase):
    cfg = PriceShockRevConfig(
        name="price_shock_rev_nzd_jpy_h1_long",
        pair="NZD_JPY",
        percentile=0.01,
        horizon_bars=12,
        vol_q="Q5",
    )
