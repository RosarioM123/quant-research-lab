"""Signal families. Each family: hypothesis docstring + pure feature functions."""
from . import momentum, mean_reversion, xsectional, volatility, volume, regime

__all__ = ["momentum", "mean_reversion", "xsectional", "volatility",
           "volume", "regime"]
