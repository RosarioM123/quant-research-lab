"""Portfolio construction: rank -> expected return -> risk -> cost -> allocation.

Pipeline (experiment-design.md §3):
    rank by expected return -> size by ER vs risk vs cost -> constrained
    allocation under the hard rules ($100 capital, long-only, no leverage,
    25% position cap, 95% gross cap, $5 min trade, no penny stocks).

Long-only construction:
    - Only symbols with expected return above the trade threshold are bought.
    - Existing positions not in the target set are sold down (never below 0).
    - Sells can never exceed held quantity: shorting is structurally impossible.
    - Fractional shares allowed.

This module SIZES; the risk engine (risk/engine.py) has final AUTHORITY.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Proposal:
    symbol: str
    side: str            # "BUY" or "SELL" (SELL only reduces/closes longs)
    qty: float           # fractional allowed
    order_type: str = "market"
    tif: str = "day"
    reason: str = ""


def construct(expected_returns: dict[str, float],
              prices: dict[str, float],
              equity: float,
              positions: dict[str, float],
              risk_cfg: dict,
              min_er_bps: float = 20.0) -> list[Proposal]:
    """Build order proposals for one rebalance.

    expected_returns: symbol -> expected return (decimal, e.g. 0.01 = 1%).
    prices: symbol -> current price. positions: symbol -> held qty (>= 0).
    """
    pf = risk_cfg["portfolio"]
    max_pos_pct = pf["max_position_pct"]
    max_gross_pct = pf["max_gross_exposure_pct"]
    min_notional = pf["min_trade_notional"]
    min_price = risk_cfg["liquidity"]["min_price"]

    # Rank: positive expected return above threshold, best first.
    ranked = sorted(
        ((s, er) for s, er in expected_returns.items()
         if er >= min_er_bps / 10000.0 and prices.get(s, 0) >= min_price),
        key=lambda kv: kv[1], reverse=True,
    )
    if not ranked:
        # No buys: still emit sells to close anything no longer wanted? No:
        # without a target we hold. (De-risking is a strategy decision.)
        return []

    # Size: weight proportional to expected return, capped per position.
    total_er = sum(er for _, er in ranked)
    targets: dict[str, float] = {}
    gross = 0.0
    for symbol, er in ranked:
        w = (er / total_er) * max_gross_pct
        w = min(w, max_pos_pct)
        if gross + w > max_gross_pct:
            w = max(0.0, max_gross_pct - gross)
        if w * equity < min_notional:
            continue
        targets[symbol] = w
        gross += w

    proposals: list[Proposal] = []
    # Buys: move toward target weights.
    for symbol, w in targets.items():
        target_qty = (w * equity) / prices[symbol]
        held = positions.get(symbol, 0.0)
        delta = target_qty - held
        if delta * prices[symbol] >= min_notional:
            proposals.append(Proposal(symbol, "BUY", round(delta, 6),
                                      reason=f"target_weight={w:.3f}"))
    # Sells: close positions with no target (long-only: qty <= held).
    for symbol, held in positions.items():
        if held > 0 and symbol not in targets:
            proposals.append(Proposal(symbol, "SELL", round(held, 6),
                                      reason="no_longer_in_target"))
    return proposals
