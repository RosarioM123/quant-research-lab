"""Chronological replay harness: the paper loop driven by historical bars.

Rules (experiment-design.md §9):
- Chronological ONLY. Never shuffle.
- Every feature uses data with timestamps <= decision time (no look-ahead).
- Decisions computed on bar t's CLOSE execute at bar t+1's OPEN.
- Same universe rules, cost assumptions, and risk constraints as paper.
- Embargo: the first ``embargo_bars`` of the test window are not traded
  (gap against label leakage).

``strategy_fn`` signature: ``(t, prices_up_to_t, volumes_up_to_t) ->
dict[symbol, expected_return]``. It receives ONLY data up to and including
bar t — enforced by slicing before the call.
"""
from __future__ import annotations

import pandas as pd

from data.integrity import (assert_chronological, check_no_future_columns,
                            LeakageError)
from execution.ledger import Ledger
from portfolio.construct import construct
from risk.engine import evaluate


def replay(prices: pd.DataFrame, volumes: pd.DataFrame, adv: pd.DataFrame,
           ann_vol: pd.DataFrame, strategy_fn, risk_cfg: dict,
           universe: list[str], costs_cfg: dict, start_cash: float = 100.0,
           embargo_bars: int = 5, ledger_path: str = "data/ledger.jsonl",
           min_er_bps: float = 20.0, flag_file: str = "KILL") -> dict:
    """Run the chronological replay. Returns equity curve, ledger, benchmark."""
    assert_chronological(list(prices.index))
    assert start_cash == 100.0, "replay capital is exactly $100"

    ledger = Ledger(ledger_path)
    cash = start_cash
    positions: dict[str, float] = {}
    equity_curve: list[tuple] = []
    bench_curve: list[tuple] = []
    # Frozen benchmark: buy-and-hold SPY, $100 at first open, never traded.
    spy_shares = start_cash / prices["SPY"].iloc[0]
    trades_today = 0
    last_day = None
    day_start_equity = start_cash

    slippage = costs_cfg["slippage_bps_one_way"] / 10000.0

    closes = prices
    opens = prices  # daily bars: execution at next bar's open == next close here
    for i in range(len(prices) - 1):
        t = prices.index[i]
        t_next = prices.index[i + 1]
        day = t.date()
        if day != last_day:
            day_start_equity = cash + sum(
                positions.get(s, 0.0) * closes[s].iloc[i] for s in positions)
            trades_today = 0
            last_day = day

        # --- No look-ahead: slice strictly up to and including bar i ---------
        px = closes.iloc[: i + 1]
        vol = volumes.iloc[: i + 1]
        check_no_future_columns(px, t)

        equity = cash + sum(positions.get(s, 0.0) * closes[s].iloc[i]
                            for s in positions)
        day_pnl = equity - day_start_equity

        if i >= embargo_bars:
            expected = strategy_fn(t, px, vol)  # dict symbol -> ER
            if not isinstance(expected, dict):
                raise LeakageError("strategy_fn must return a dict")
            # Strategy must not reference symbols outside the panel it got.
            for s in expected:
                if s not in px.columns:
                    raise LeakageError(f"strategy referenced {s} outside its panel")

            live_prices = {s: float(closes[s].iloc[i]) for s in universe
                           if s in closes.columns}
            proposals = construct(expected, live_prices, equity, positions,
                                  risk_cfg, min_er_bps)
            market_state = {
                s: {"price": float(closes[s].iloc[i]),
                    "adv_dollar_volume": float(adv[s].iloc[i]),
                    "ann_vol": float(ann_vol[s].iloc[i])}
                for s in universe if s in closes.columns
            }
            pf_state = {"equity": equity, "cash": cash, "positions": dict(positions),
                        "day_start_equity": day_start_equity, "day_pnl": day_pnl,
                        "trades_today": trades_today}
            for p in proposals:
                ledger.append("proposal", {"symbol": p.symbol, "side": p.side,
                                           "qty": p.qty, "as_of": t.isoformat()})
                dec = evaluate(p, pf_state, market_state, risk_cfg, universe,
                               flag_file=flag_file)
                ledger.append("risk_decision",
                              {"symbol": p.symbol, "allow": dec.allow,
                               "code": dec.code.value, "reason": dec.reason,
                               "as_of": t.isoformat()})
                if not dec.allow:
                    continue
                # Execute at NEXT bar's open with slippage applied.
                exec_price = float(opens[p.symbol].iloc[i + 1])
                fill_price = exec_price * (1 + slippage)  # buys pay up
                if p.side == "BUY":
                    cost = p.qty * fill_price
                    cash -= cost
                    positions[p.symbol] = positions.get(p.symbol, 0.0) + p.qty
                else:
                    fill_price = exec_price * (1 - slippage)
                    cash += p.qty * fill_price
                    positions[p.symbol] = positions.get(p.symbol, 0.0) - p.qty
                    if positions[p.symbol] <= 1e-9:
                        del positions[p.symbol]
                trades_today += 1
                pf_state["cash"] = cash
                pf_state["positions"] = dict(positions)
                pf_state["trades_today"] = trades_today
                ledger.append("fill", {"symbol": p.symbol, "side": p.side,
                                       "qty": p.qty, "fill_price": fill_price,
                                       "as_of": t_next.isoformat()})

        equity = cash + sum(positions.get(s, 0.0) * closes[s].iloc[i + 1]
                            for s in positions)
        equity_curve.append((t_next, equity))
        bench_curve.append((t_next, spy_shares * closes["SPY"].iloc[i + 1]))
        ledger.append("position", {"cash": cash,
                                   "positions": dict(positions),
                                   "equity": equity,
                                   "as_of": t_next.isoformat()})

    ok, bad = ledger.verify()
    return {"equity": equity_curve, "benchmark": bench_curve,
            "positions": positions, "cash": cash,
            "ledger_path": ledger_path, "ledger_ok": ok, "ledger_bad_seq": bad}
