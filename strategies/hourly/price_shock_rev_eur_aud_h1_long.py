from strategies.hourly.price_shock_reversion_base import PriceShockRevConfig, PriceShockReversionBase


class PriceShockRevEurAudH1Long(PriceShockReversionBase):
    cfg = PriceShockRevConfig(
        name="price_shock_rev_eur_aud_h1_long",
        pair="EUR_AUD",
        percentile=0.01,
        horizon_bars=12,
        vol_q="Q5",
    )
