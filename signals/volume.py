"""Volume / market-activity signals.

HYPOTHESIS: abnormal volume marks informed or urgent trading; price moves on
high volume are more meaningful than moves on low volume.

Candidates: volume z-score vs 20-bar; volume x return interaction;
unusual-activity flags.

CONSTRAINT (binding): we do NOT have institutional order-flow data and will
not pretend otherwise. Volume features are public-tape only.
"""
from __future__ import annotations

import pandas as pd


def volume_zscore(volumes: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Volume z-score vs its n-bar history."""
    ma = volumes.rolling(n, min_periods=n).mean()
    sd = volumes.rolling(n, min_periods=n).std()
    return (volumes - ma) / sd.replace(0, float("nan"))


def volume_return_interaction(prices: pd.DataFrame, volumes: pd.DataFrame,
                              n: int = 20) -> pd.DataFrame:
    """Signed volume abnormality: z-scored volume x sign of return.

    Large up-move on huge volume -> large positive; same move on thin
    volume -> near zero.
    """
    z = volume_zscore(volumes, n).fillna(0.0)
    sign = (prices.pct_change().gt(0).astype(float)
            - prices.pct_change().lt(0).astype(float))
    return z * sign


def unusual_activity(volumes: pd.DataFrame, n: int = 20,
                     threshold: float = 3.0) -> pd.DataFrame:
    """Binary flag: volume z-score beyond threshold."""
    return (volume_zscore(volumes, n).abs() > threshold).astype(float)


def volume_features(prices: pd.DataFrame,
                    volumes: pd.DataFrame) -> pd.DataFrame:
    feats = {
        "volume_z20": volume_zscore(volumes, 20),
        "volume_x_ret20": volume_return_interaction(prices, volumes, 20),
        "volume_unusual": unusual_activity(volumes, 20),
    }
    return pd.concat(feats, axis=1)
