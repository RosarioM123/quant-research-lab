"""Risk engine: deterministic ALLOW / REJECT with reason codes.

The risk engine never uses judgment. Every check is a pure function of
(proposal, portfolio_state, market_state, config). Violations are REJECTED,
never warned about. No overrides exist.

Check order is deliberate: structural impossibilities (kill switch, shorting)
first, then sanity, then liquidity/volatility, then concentration/exposure,
then loss/turnover halts, then capital.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class ReasonCode(str, Enum):
    ALLOW = "ALLOW"
    KILL_SWITCH = "KILL_SWITCH"
    UNKNOWN_SYMBOL = "UNKNOWN_SYMBOL"
    SHORT_ATTEMPT = "SHORT_ATTEMPT"
    OVERSELL = "OVERSELL"
    NONPOSITIVE_QTY = "NONPOSITIVE_QTY"
    BAD_ORDER_TYPE = "BAD_ORDER_TYPE"
    BAD_TIF = "BAD_TIF"
    PENNY_STOCK = "PENNY_STOCK"
    ILLIQUID = "ILLIQUID"
    EXCESS_VOLATILITY = "EXCESS_VOLATILITY"
    OVER_CONCENTRATION = "OVER_CONCENTRATION"
    OVER_EXPOSURE = "OVER_EXPOSURE"
    DAILY_LOSS_HALT = "DAILY_LOSS_HALT"
    MAX_TRADES = "MAX_TRADES"
    INSUFFICIENT_CAPITAL = "INSUFFICIENT_CAPITAL"


@dataclass(frozen=True)
class Decision:
    allow: bool
    code: ReasonCode
    reason: str

    @staticmethod
    def allow_() -> "Decision":
        return Decision(True, ReasonCode.ALLOW, "all checks passed")

    @staticmethod
    def reject(code: ReasonCode, reason: str) -> "Decision":
        return Decision(False, code, reason)


class PaperModeError(Exception):
    """Paper-mode gate failed: refuse to start."""


PAPER_URL = "https://paper-api.alpaca.markets"


def paper_mode_gate() -> None:
    """Hard gate: refuse to start unless paper mode is exactly configured."""
    if os.environ.get("PAPER_TRADING", "").lower() != "true":
        raise PaperModeError("PAPER_TRADING != true: refusing to start")
    base_url = os.environ.get("APCA_API_BASE_URL", "")
    if base_url != PAPER_URL:
        raise PaperModeError(
            f"trading base URL is not the paper endpoint: {base_url!r} "
            f"(must be exactly {PAPER_URL})"
        )


def kill_switch_active(flag_file: str = "KILL") -> bool:
    return os.path.exists(flag_file)


def evaluate(proposal, portfolio_state: dict, market_state: dict,
             risk_cfg: dict, universe: list[str],
             flag_file: str = "KILL") -> Decision:
    """Deterministic risk check.

    proposal: has .symbol, .side ("BUY"/"SELL"), .qty, .order_type, .tif.
    portfolio_state: {equity, cash, positions: {sym: qty}, day_start_equity,
                      day_pnl, trades_today}.
    market_state: {symbol: {price, adv_dollar_volume, ann_vol}}.
    """
    liq = risk_cfg["liquidity"]
    pf = risk_cfg["portfolio"]
    orders_cfg = risk_cfg["orders"]

    if kill_switch_active(flag_file):
        return Decision.reject(ReasonCode.KILL_SWITCH,
                               "kill-switch flag file present: all trading halted")

    if proposal.symbol not in universe:
        return Decision.reject(ReasonCode.UNKNOWN_SYMBOL,
                               f"{proposal.symbol} not in frozen universe")

    # --- Long-only structure -------------------------------------------------
    held = portfolio_state.get("positions", {}).get(proposal.symbol, 0.0)
    if proposal.side == "SELL":
        if held <= 0:
            return Decision.reject(ReasonCode.SHORT_ATTEMPT,
                                   f"SELL with no long position in {proposal.symbol}")
        if proposal.qty > held + 1e-9:
            return Decision.reject(ReasonCode.OVERSELL,
                                   f"SELL qty {proposal.qty} exceeds held {held}")
    elif proposal.side != "BUY":
        return Decision.reject(ReasonCode.SHORT_ATTEMPT,
                               f"unknown side {proposal.side!r}: long-only system")

    # --- Order sanity ---------------------------------------------------------
    if proposal.qty <= 0:
        return Decision.reject(ReasonCode.NONPOSITIVE_QTY,
                               f"qty must be positive, got {proposal.qty}")
    if proposal.order_type not in orders_cfg["types_allowed"]:
        return Decision.reject(ReasonCode.BAD_ORDER_TYPE,
                               f"order type {proposal.order_type!r} not allowed")
    if proposal.tif not in orders_cfg["tif_allowed"]:
        return Decision.reject(ReasonCode.BAD_TIF,
                               f"TIF {proposal.tif!r} not allowed")

    # --- Liquidity / volatility ----------------------------------------------
    m = market_state.get(proposal.symbol, {})
    price = m.get("price", 0.0)
    if price < liq["min_price"]:
        return Decision.reject(ReasonCode.PENNY_STOCK,
                               f"{proposal.symbol} price ${price:.2f} < "
                               f"${liq['min_price']:.2f} floor")
    if m.get("adv_dollar_volume", 0.0) < liq["min_avg_daily_dollar_volume"]:
        return Decision.reject(ReasonCode.ILLIQUID,
                               f"{proposal.symbol} ADV dollar volume below minimum")
    if m.get("ann_vol", 0.0) > risk_cfg["volatility"]["max_annualized_vol"]:
        return Decision.reject(ReasonCode.EXCESS_VOLATILITY,
                               f"{proposal.symbol} 20d ann. vol "
                               f"{m['ann_vol']:.0%} > 100%")

    # --- Concentration / exposure (long-only: no leverage by construction) -----
    equity = portfolio_state["equity"]
    positions = portfolio_state.get("positions", {})
    if proposal.side == "BUY":
        new_pos_value = (held + proposal.qty) * price
        if new_pos_value > pf["max_position_pct"] * equity + 1e-9:
            return Decision.reject(
                ReasonCode.OVER_CONCENTRATION,
                f"{proposal.symbol} position ${new_pos_value:.2f} > "
                f"{pf['max_position_pct']:.0%} of equity")
        gross = sum(q * market_state.get(s, {}).get("price", 0.0)
                    for s, q in positions.items()) + proposal.qty * price
        if gross > pf["max_gross_exposure_pct"] * equity + 1e-9:
            return Decision.reject(
                ReasonCode.OVER_EXPOSURE,
                f"gross exposure ${gross:.2f} > "
                f"{pf['max_gross_exposure_pct']:.0%} of equity")

    # --- Loss / turnover halts --------------------------------------------------
    day_start = portfolio_state.get("day_start_equity", equity)
    day_pnl = portfolio_state.get("day_pnl", 0.0)
    if day_pnl <= -risk_cfg["loss_limits"]["max_daily_loss_pct"] * day_start:
        return Decision.reject(ReasonCode.DAILY_LOSS_HALT,
                               f"day P&L ${day_pnl:.2f} breached "
                               "-5% halt: no new orders today")
    if portfolio_state.get("trades_today", 0) >= risk_cfg["loss_limits"]["max_trades_per_day"]:
        return Decision.reject(ReasonCode.MAX_TRADES,
                               "max 10 trades/day reached")

    # --- Capital -----------------------------------------------------------------
    if proposal.side == "BUY":
        notional = proposal.qty * price
        if notional > portfolio_state.get("cash", 0.0) + 1e-9:
            return Decision.reject(ReasonCode.INSUFFICIENT_CAPITAL,
                                   f"notional ${notional:.2f} exceeds cash "
                                   f"${portfolio_state.get('cash', 0.0):.2f}")

    return Decision.allow_()
