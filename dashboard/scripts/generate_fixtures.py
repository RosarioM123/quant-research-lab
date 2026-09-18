"""Generate dashboard fixtures from the real replay pipeline.

Everything here is SYNTHETIC (seeded RNG prices) — fixtures for the React
dashboard only. No real market data, no performance claims. Regenerate with:
    ../.venv/bin/python scripts/generate_fixtures.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # signal-build/
sys.path.insert(0, str(ROOT))

from backtest.replay import replay
from execution.ledger import Ledger

OUT = ROOT / "dashboard" / "src" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)
idx = pd.date_range("2026-06-01", periods=90, freq="B")
symbols = ["SPY", "AAPL", "MSFT"]
rets = rng.normal(0.0008, 0.012, size=(len(idx), len(symbols)))
prices = pd.DataFrame(120 * np.exp(np.cumsum(rets, axis=0)),
                      index=idx, columns=symbols)
volumes = pd.DataFrame(rng.integers(1_000_000, 6_000_000,
                                    size=prices.shape),
                       index=idx, columns=symbols)
adv = prices * 0 + 2e9
ann_vol = prices * 0 + 0.25


def strat(t, px, vol):
    # Toy momentum tilt: positive 20d ROC -> small positive expected return.
    roc = px.pct_change(20).iloc[-1]
    return {s: float(0.3 * r) for s, r in roc.items() if s != "SPY"}


risk_cfg = {
    "portfolio": {"long_only": True, "leverage_allowed": False,
                  "margin_allowed": False, "derivatives_allowed": False,
                  "max_position_pct": 0.25, "max_gross_exposure_pct": 0.95,
                  "min_trade_notional": 5.0},
    "liquidity": {"min_price": 5.0, "min_avg_daily_dollar_volume": 10_000_000},
    "volatility": {"max_annualized_vol": 1.0},
    "orders": {"types_allowed": ["market", "limit"], "tif_allowed": ["day"],
               "fractional_allowed": True},
    "loss_limits": {"max_daily_loss_pct": 0.05, "max_trades_per_day": 10},
}
costs = {"slippage_bps_one_way": 2.0}
ledger_path = "/tmp/signal-fixture-ledger.jsonl"

res = replay(prices, volumes, adv, ann_vol, strat, risk_cfg, symbols, costs,
             ledger_path=ledger_path, flag_file="/nonexistent/KILL")

led = Ledger(ledger_path)
records = led.tail(10_000)

meta = {"fixture": True, "simulated": True,
        "note": "Synthetic seeded prices (seed 42). Illustrates dashboard "
                "layout only — NOT real trading or real performance."}

(OUT / "meta.json").write_text(json.dumps(meta, indent=2))
(OUT / "equity.json").write_text(json.dumps({
    **meta,
    "strategy": [{"t": t.isoformat(), "equity": round(e, 4)}
                 for t, e in res["equity"]],
    "benchmark_spy": [{"t": t.isoformat(), "equity": round(e, 4)}
                      for t, e in res["benchmark"]],
}))
(OUT / "positions.json").write_text(json.dumps({
    **meta,
    "cash": round(res["cash"], 4),
    "positions": {s: round(q, 6) for s, q in res["positions"].items()},
    "last_prices": {s: round(float(prices[s].iloc[-1]), 2) for s in symbols},
}))
(OUT / "ledger_tail.json").write_text(json.dumps({
    **meta,
    "records": records[-40:],
}))
decisions = [r for r in records if r["type"] == "risk_decision"]
(OUT / "risk_decisions.json").write_text(json.dumps({
    **meta,
    "decisions": decisions[-25:],
    "summary": {
        "allowed": sum(1 for r in decisions if r["data"]["allow"]),
        "rejected": sum(1 for r in decisions if not r["data"]["allow"]),
    },
}))
print("fixtures written to", OUT)
