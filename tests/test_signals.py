"""Signals: shapes, determinism, and the volatility-direction rule."""
import numpy as np
import pandas as pd

from signals import momentum, mean_reversion, xsectional, volatility, volume, regime


def test_momentum_shapes(prices, volumes):
    feats = momentum.momentum_features(prices, volumes)
    assert set(feats.columns.get_level_values(0)) == {
        "momentum_roc20", "momentum_roc60", "momentum_ma50",
        "momentum_breakout20"}
    assert feats.shape[1] == 4 * 3


def test_momentum_roc_spot(prices, volumes):
    r = momentum.roc(prices, 20)
    expect = prices["AAPL"].iloc[30] / prices["AAPL"].iloc[10] - 1
    assert r["AAPL"].iloc[30] == expect


def test_mean_reversion_sign(prices, volumes):
    # After a big up day, reversal should be negative.
    rev = mean_reversion.reversal(prices, 5)
    assert rev["AAPL"].iloc[60] == -(prices["AAPL"].iloc[60]
                                    / prices["AAPL"].iloc[55] - 1)


def test_xsectional_drops_benchmark(prices):
    xs = xsectional.excess_vs_benchmark(prices, "SPY", 20)
    assert "SPY" not in xs.columns
    expect = (prices["AAPL"].iloc[40] / prices["AAPL"].iloc[20] - 1) - (
        prices["SPY"].iloc[40] / prices["SPY"].iloc[20] - 1)
    assert xs["AAPL"].iloc[40] == expect


def test_volatility_features_nonnegative(prices):
    feats = volatility.volatility_features(prices)
    rv = feats["vol_realized20"]  # MultiIndex slice: DataFrame of symbols
    assert ((rv >= 0) | rv.isna()).all().all()
    pct = feats["vol_percentile252"]
    assert (((pct >= 0) & (pct <= 1)) | pct.isna()).all().all()


def test_volume_zscore(prices, volumes):
    z = volume.volume_zscore(volumes, 20)
    assert z.shape == prices.shape


def test_regime_outputs(prices):
    reg = regime.regime_features(prices)
    assert set(reg.columns) == {"regime_spy_trend", "regime_vol_percentile",
                                "regime_breadth", "regime_risk_on"}
    assert set(reg["regime_spy_trend"].dropna().unique()) <= {-1.0, 0.0, 1.0}
    assert set(reg["regime_risk_on"].dropna().unique()) <= {0.0, 1.0}
