"""Momentum signals.

HYPOTHESIS: information diffuses gradually; investors underreact initially and
herding extends moves. Short-horizon continuation exists in liquid equities.

Candidates: ROC(20), ROC(60); moving-average trend (close vs MA(50));
breakout = close at N-day high with volume confirmation; cross-sectional
12-1 month return rank (see xsectional.py).

To test: which horizon, whether volume confirmation adds value, decay.
Parameters below are starting points for backtesting, not choices.
"""
from __future__ import annotations

import pandas as pd


def roc(prices: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Rate of change over n bars."""
    return prices.pct_change(n)


def ma_trend(prices: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    """Close relative to n-bar moving average (positive = uptrend)."""
    ma = prices.rolling(n, min_periods=n).mean()
    return prices / ma - 1.0


def breakout(prices: pd.DataFrame, volumes: pd.DataFrame,
             n: int = 20) -> pd.DataFrame:
    """Close at n-bar high AND volume > 1.5x its n-bar average."""
    roll_max = prices.rolling(n, min_periods=n).max()
    vol_ma = volumes.rolling(n, min_periods=n).mean()
    at_high = prices >= roll_max * 0.999  # tolerance for float noise
    vol_confirm = volumes > 1.5 * vol_ma
    return (at_high & vol_confirm).astype(float)


def momentum_features(prices: pd.DataFrame,
                      volumes: pd.DataFrame) -> pd.DataFrame:
    """Stacked momentum feature panel (MultiIndex columns: feature x symbol)."""
    feats = {
        "momentum_roc20": roc(prices, 20),
        "momentum_roc60": roc(prices, 60),
        "momentum_ma50": ma_trend(prices, 50),
        "momentum_breakout20": breakout(prices, volumes, 20),
    }
    return pd.concat(feats, axis=1)
