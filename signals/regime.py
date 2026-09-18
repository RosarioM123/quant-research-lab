"""Market-regime signals.

HYPOTHESIS: the same signal behaves differently across regimes; conditioning
on regime reduces false signals.

Candidates: SPY trend (close vs MA(50/200)); volatility environment (SPY
realized-vol percentile as VIX proxy — free tier has no VIX feed, documented
limitation); breadth proxy (fraction of universe above MA(50)); risk-on /
risk-off flag.

USE: regime gates or interacts with signals (e.g. momentum weight up in
trending regimes, mean-reversion weight up in choppy regimes). The interaction
itself must be tested, not assumed.
"""
from __future__ import annotations

import pandas as pd

from .volatility import realized_vol, vol_percentile


def spy_trend(prices: pd.DataFrame) -> pd.DataFrame:
    """SPY close vs MA(50) and MA(200): +1 uptrend, -1 downtrend, 0 mixed."""
    spy = prices["SPY"]
    ma50 = spy.rolling(50, min_periods=50).mean()
    ma200 = spy.rolling(200, min_periods=200).mean()
    trend = ((spy > ma50).astype(float) + (spy > ma200).astype(float)) - 1.0
    return trend.to_frame("regime_spy_trend")


def vol_environment(prices: pd.DataFrame) -> pd.DataFrame:
    """SPY vol percentile as the VIX proxy (documented free-tier limitation)."""
    rv = realized_vol(prices[["SPY"]], 20)
    return vol_percentile(rv, 252).rename(
        columns={"SPY": "regime_vol_percentile"})


def breadth(prices: pd.DataFrame) -> pd.DataFrame:
    """Fraction of universe (ex-SPY) above its own MA(50)."""
    ex_spy = prices.drop(columns=["SPY"])
    ma50 = ex_spy.rolling(50, min_periods=50).mean()
    frac = (ex_spy > ma50).mean(axis=1)
    return frac.to_frame("regime_breadth")


def risk_on_flag(prices: pd.DataFrame) -> pd.DataFrame:
    """1 when SPY uptrend AND vol environment calm; else 0."""
    trend = spy_trend(prices)["regime_spy_trend"]
    volp = vol_environment(prices)["regime_vol_percentile"]
    flag = ((trend > 0) & (volp < 0.7)).astype(float)
    return flag.to_frame("regime_risk_on")


def regime_features(prices: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(
        [spy_trend(prices), vol_environment(prices), breadth(prices),
         risk_on_flag(prices)], axis=1)
