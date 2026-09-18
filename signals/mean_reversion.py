"""Mean-reversion signals.

HYPOTHESIS: short-term price moves overreact to noise/liquidity shocks and
partially revert; deviations from equilibrium are arbitraged away.

Candidates: 5-day reversal; z-score of price vs 20-day MA scaled by 20-day
sigma; distance from VWAP-like anchors; cross-sectional reversal.

To test: horizon of reversion, volatility normalization, interaction with
regime (reversion fails in strong trends — see regime.py).
"""
from __future__ import annotations

import pandas as pd


def reversal(prices: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Negative of the n-bar return: up-moves -> negative (expect reversion)."""
    return -prices.pct_change(n)


def zscore(prices: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Negative z-score vs n-bar MA: stretched-up -> negative (expect reversion)."""
    ma = prices.rolling(n, min_periods=n).mean()
    sd = prices.rolling(n, min_periods=n).std()
    return -((prices - ma) / sd.replace(0, float("nan")))


def dist_vwap_proxy(prices: pd.DataFrame, volumes: pd.DataFrame,
                    n: int = 20) -> pd.DataFrame:
    """Negative distance from a volume-weighted anchor (session VWAP proxy).

    True VWAP needs intraday data; this is a daily-bar proxy and is labeled
    as such. Negative sign: above-anchor -> expect reversion down.
    """
    typical = prices  # daily close as typical-price proxy (documented)
    vwap = (typical * volumes).rolling(n, min_periods=n).sum() / volumes.rolling(
        n, min_periods=n).sum().replace(0, float("nan"))
    return -(prices / vwap - 1.0)


def mean_reversion_features(prices: pd.DataFrame,
                            volumes: pd.DataFrame) -> pd.DataFrame:
    feats = {
        "mr_reversal5": reversal(prices, 5),
        "mr_zscore20": zscore(prices, 20),
        "mr_dist_vwap20": dist_vwap_proxy(prices, volumes, 20),
    }
    return pd.concat(feats, axis=1)
