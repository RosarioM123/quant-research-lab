"""Shared fixtures: synthetic panels, configs, news samples.

All market data here is SYNTHETIC (seeded RNG). No real prices, no fabricated
performance claims. Fixtures exist to test mechanics: rejections, chains,
leakage guards, replay ordering.
"""
import os

import numpy as np
import pandas as pd
import pytest

SEED = 7


@pytest.fixture()
def prices():
    rng = np.random.default_rng(SEED)
    idx = pd.date_range("2026-01-02", periods=120, freq="B")
    symbols = ["SPY", "AAPL", "MSFT"]
    rets = rng.normal(0.0005, 0.01, size=(len(idx), len(symbols)))
    px = 100 * np.exp(np.cumsum(rets, axis=0))
    return pd.DataFrame(px, index=idx, columns=symbols)


@pytest.fixture()
def volumes(prices):
    rng = np.random.default_rng(SEED + 1)
    return pd.DataFrame(
        rng.integers(1_000_000, 5_000_000, size=prices.shape),
        index=prices.index, columns=prices.columns)


@pytest.fixture()
def risk_cfg():
    return {
        "portfolio": {
            "long_only": True, "leverage_allowed": False,
            "margin_allowed": False, "derivatives_allowed": False,
            "max_position_pct": 0.25, "max_gross_exposure_pct": 0.95,
            "min_trade_notional": 5.0,
        },
        "liquidity": {"min_price": 5.0, "min_avg_daily_dollar_volume": 10_000_000},
        "volatility": {"max_annualized_vol": 1.0},
        "orders": {"types_allowed": ["market", "limit"], "tif_allowed": ["day"],
                   "fractional_allowed": True},
        "loss_limits": {"max_daily_loss_pct": 0.05, "max_trades_per_day": 10},
    }


@pytest.fixture()
def universe():
    return ["SPY", "AAPL", "MSFT"]


@pytest.fixture()
def market_state():
    return {
        "SPY": {"price": 500.0, "adv_dollar_volume": 5e9, "ann_vol": 0.15},
        "AAPL": {"price": 200.0, "adv_dollar_volume": 3e9, "ann_vol": 0.25},
        "MSFT": {"price": 400.0, "adv_dollar_volume": 2e9, "ann_vol": 0.22},
    }


@pytest.fixture()
def portfolio_state():
    return {"equity": 100.0, "cash": 100.0, "positions": {},
            "day_start_equity": 100.0, "day_pnl": 0.0, "trades_today": 0}


@pytest.fixture()
def news_raw():
    return [
        {"id": "n1", "headline": "Acme beats EPS estimates by 8%",
         "summary": "Acme reported EPS above estimates.", "author": "Wire",
         "created_at": "2026-09-10T13:30:00Z", "updated_at": "2026-09-10T13:30:00Z",
         "url": "https://example.com/n1", "symbols": ["AAPL"]},
        {"id": "n1", "headline": "Acme beats EPS estimates by 8% (update)",
         "summary": "Acme reported EPS above estimates. Updated.",
         "author": "Wire", "created_at": "2026-09-10T13:30:00Z",
         "updated_at": "2026-09-10T14:00:00Z",
         "url": "https://example.com/n1", "symbols": ["AAPL"]},
        {"id": "n2", "headline": "Acme beats EPS estimates by 8%",
         "summary": "Another outlet, same story.", "author": "Other",
         "created_at": "2026-09-10T13:45:00Z", "updated_at": "2026-09-10T13:45:00Z",
         "url": "https://example.com/n2", "symbols": ["AAPL"]},
    ]


@pytest.fixture(autouse=True)
def _paper_env(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
