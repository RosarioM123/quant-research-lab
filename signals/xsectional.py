"""Cross-sectional (relative-strength) signals.

HYPOTHESIS: idiosyncratic strength vs. peers/market reflects real information;
relative moves are cleaner than absolute moves.

Candidates: return vs SPY over 20/60 bars; volatility-adjusted relative
strength (excess return / tracking error). Sector-relative momentum would need
a sector mapping (free-tier limitation — see experiment-design.md §11);
SPY-relative is the implemented fallback.
"""
from __future__ import annotations

import pandas as pd


def excess_vs_benchmark(prices: pd.DataFrame, benchmark: str = "SPY",
                        n: int = 20) -> pd.DataFrame:
    """n-bar return minus the benchmark's n-bar return."""
    rets = prices.pct_change(n)
    bench = rets[benchmark]
    return rets.sub(bench, axis=0).drop(columns=[benchmark])


def vol_adjusted_strength(prices: pd.DataFrame, benchmark: str = "SPY",
                          n: int = 60) -> pd.DataFrame:
    """Excess return over n bars divided by tracking error (excess-return vol)."""
    rets = prices.pct_change().drop(columns=[benchmark])
    bench_rets = prices[benchmark].pct_change()
    excess = rets.sub(bench_rets, axis=0)
    cum_excess = (1 + excess).rolling(n, min_periods=n).apply(
        lambda x: x.prod() - 1, raw=True)
    tracking_err = excess.rolling(n, min_periods=n).std()
    return cum_excess / tracking_err.replace(0, float("nan"))


def xsectional_features(prices: pd.DataFrame) -> pd.DataFrame:
    feats = {
        "xs_excess20": excess_vs_benchmark(prices, "SPY", 20),
        "xs_excess60": excess_vs_benchmark(prices, "SPY", 60),
        "xs_voladj60": vol_adjusted_strength(prices, "SPY", 60),
    }
    return pd.concat(feats, axis=1)
