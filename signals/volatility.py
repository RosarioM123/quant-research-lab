"""Volatility signals.

HYPOTHESIS: volatility regimes are persistent; expansions/contractions carry
information about future opportunity and risk.

RULE (binding): volatility is a FEATURE, not a direction. Never
"high vol = buy/sell". Volatility scales positions and gates signals.

Candidates: 20-bar realized volatility (annualized); vol regime (current vol
vs 1-year percentile); ATR-style range measures; expansion/contraction flags.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BARS_PER_YEAR = 252


def realized_vol(prices: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """n-bar realized volatility, annualized."""
    log_rets = np.log(prices / prices.shift(1))
    return log_rets.rolling(n, min_periods=n).std() * np.sqrt(BARS_PER_YEAR)


def vol_percentile(realized_vol_: pd.DataFrame, lookback: int = 252) -> pd.DataFrame:
    """Current vol as a percentile of its own lookback history (0..1)."""
    return realized_vol_.rolling(lookback, min_periods=lookback).apply(
        lambda x: (x <= x[-1]).mean(), raw=True)


def expansion_flag(realized_vol_: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """1 when vol is expanding fast (current > 1.5x its n-bar median)."""
    med = realized_vol_.rolling(n, min_periods=n).median()
    return (realized_vol_ > 1.5 * med).astype(float)


def volatility_features(prices: pd.DataFrame) -> pd.DataFrame:
    rv = realized_vol(prices, 20)
    feats = {
        "vol_realized20": rv,
        "vol_percentile252": vol_percentile(rv, 252),
        "vol_expanding": expansion_flag(rv, 20),
    }
    return pd.concat(feats, axis=1)
