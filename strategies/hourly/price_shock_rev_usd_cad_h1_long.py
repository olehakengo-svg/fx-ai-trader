from strategies.hourly.price_shock_reversion_base import PriceShockRevConfig, PriceShockReversionBase


class PriceShockRevUsdCadH1Long(PriceShockReversionBase):
    cfg = PriceShockRevConfig(
        name="price_shock_rev_usd_cad_h1_long",
        pair="USD_CAD",
        percentile=0.01,
        horizon_bars=3,
        vol_q="Q5",
    )
