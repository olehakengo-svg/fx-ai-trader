from strategies.hourly.price_shock_reversion_base import PriceShockRevConfig, PriceShockReversionBase


class PriceShockRevAudJpyH1Long(PriceShockReversionBase):
    cfg = PriceShockRevConfig(
        name="price_shock_rev_aud_jpy_h1_long",
        pair="AUD_JPY",
        percentile=0.01,
        horizon_bars=12,
        vol_q="ALL",
    )
