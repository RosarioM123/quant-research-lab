"""Backtest: chronological replay, no look-ahead, $100, frozen benchmark."""
import pandas as pd
import pytest

from backtest.replay import replay
from execution.ledger import Ledger


def _adv_ann_vol(prices):
    adv = prices * 0 + 1e9
    ann_vol = prices * 0 + 0.2
    return adv, ann_vol


def test_replay_runs_and_ledger_verifies(prices, volumes, risk_cfg, universe,
                                         tmp_path):
    adv, ann_vol = _adv_ann_vol(prices)

    def strat(t, px, vol):
        return {"AAPL": 0.005}  # constant tiny edge, above threshold

    costs = {"slippage_bps_one_way": 2.0}
    res = replay(prices, volumes, adv, ann_vol, strat, risk_cfg, universe,
                 costs, ledger_path=str(tmp_path / "ledger.jsonl"),
                 flag_file="/nonexistent/KILL")
    assert len(res["equity"]) == len(prices) - 1
    assert res["ledger_ok"], f"ledger broken at seq {res['ledger_bad_seq']}"
    # Frozen benchmark: $100 of SPY at first close, never traded.
    first, last = res["benchmark"][0][1], res["benchmark"][-1][1]
    assert first == pytest.approx(100 * prices["SPY"].iloc[1]
                                  / prices["SPY"].iloc[0])
    assert last == pytest.approx(
        100 * prices["SPY"].iloc[-1] / prices["SPY"].iloc[0])
    led = Ledger(res["ledger_path"])
    types = [r["type"] for r in led.tail(len(led.tail(10_000)))]
    assert "risk_decision" in types


def test_strategy_cannot_see_future(prices, volumes, risk_cfg, universe, tmp_path):
    adv, ann_vol = _adv_ann_vol(prices)
    seen = {}

    def strat(t, px, vol):
        seen[t] = px.index[-1]
        return {}

    costs = {"slippage_bps_one_way": 2.0}
    replay(prices, volumes, adv, ann_vol, strat, risk_cfg, universe, costs,
           ledger_path=str(tmp_path / "ledger.jsonl"),
           flag_file="/nonexistent/KILL")
    for t, last in seen.items():
        assert last <= t, "strategy received data past its decision time"


def test_embargo_skips_first_bars(prices, volumes, risk_cfg, universe, tmp_path):
    adv, ann_vol = _adv_ann_vol(prices)
    calls = []

    def strat(t, px, vol):
        calls.append(t)
        return {"AAPL": 0.01}

    costs = {"slippage_bps_one_way": 2.0}
    res = replay(prices, volumes, adv, ann_vol, strat, risk_cfg, universe,
                 costs, embargo_bars=10,
                 ledger_path=str(tmp_path / "ledger.jsonl"),
                 flag_file="/nonexistent/KILL")
    assert len(calls) == (len(prices) - 1) - 10


def test_replay_capital_is_exactly_100(prices, volumes, risk_cfg, universe, tmp_path):
    adv, ann_vol = _adv_ann_vol(prices)
    try:
        replay(prices, volumes, adv, ann_vol, lambda t, p, v: {}, risk_cfg,
               universe, {"slippage_bps_one_way": 2.0}, start_cash=1000.0,
               ledger_path=str(tmp_path / "ledger.jsonl"),
               flag_file="/nonexistent/KILL")
    except AssertionError:
        pass
    else:
        raise AssertionError("start_cash != 100 must be rejected")


def test_no_buys_when_no_edge(prices, volumes, risk_cfg, universe, tmp_path):
    adv, ann_vol = _adv_ann_vol(prices)
    costs = {"slippage_bps_one_way": 2.0}
    res = replay(prices, volumes, adv, ann_vol, lambda t, p, v: {}, risk_cfg,
                 universe, costs, ledger_path=str(tmp_path / "ledger.jsonl"),
                 flag_file="/nonexistent/KILL")
    assert res["positions"] == {}
    assert res["cash"] == 100.0
