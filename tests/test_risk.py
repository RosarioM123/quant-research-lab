"""Risk engine: every rejection path is unit-tested. No judgment, only rules."""
import pytest

from portfolio.construct import Proposal
from risk.engine import (Decision, ReasonCode, evaluate, kill_switch_active,
                         paper_mode_gate, PaperModeError, PAPER_URL)


def prop(**kw):
    base = {"symbol": "AAPL", "side": "BUY", "qty": 0.1,
            "order_type": "market", "tif": "day"}
    base.update(kw)
    return Proposal(**base)


def test_allow_clean_proposal(risk_cfg, universe, market_state, portfolio_state):
    d = evaluate(prop(), portfolio_state, market_state, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")
    assert d.allow and d.code == ReasonCode.ALLOW


def test_reject_kill_switch(risk_cfg, universe, market_state, portfolio_state, tmp_path):
    kill = tmp_path / "KILL"
    kill.write_text("halt")
    d = evaluate(prop(), portfolio_state, market_state, risk_cfg, universe,
                 flag_file=str(kill))
    assert not d.allow and d.code == ReasonCode.KILL_SWITCH


def test_reject_unknown_symbol(risk_cfg, market_state, portfolio_state):
    d = evaluate(prop(symbol="FAKE"), portfolio_state, market_state,
                 risk_cfg, ["SPY", "AAPL"], flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.UNKNOWN_SYMBOL and not d.allow


def test_reject_short_attempt(risk_cfg, universe, market_state, portfolio_state):
    d = evaluate(prop(side="SELL", qty=0.1), portfolio_state, market_state,
                 risk_cfg, universe, flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.SHORT_ATTEMPT


def test_reject_oversell(risk_cfg, universe, market_state):
    pf = {"equity": 100.0, "cash": 50.0, "positions": {"AAPL": 0.1},
          "day_start_equity": 100.0, "day_pnl": 0.0, "trades_today": 0}
    d = evaluate(prop(side="SELL", qty=0.5), pf, market_state, risk_cfg,
                 universe, flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.OVERSELL


def test_allow_closing_sell(risk_cfg, universe, market_state):
    pf = {"equity": 100.0, "cash": 50.0, "positions": {"AAPL": 0.1},
          "day_start_equity": 100.0, "day_pnl": 0.0, "trades_today": 0}
    d = evaluate(prop(side="SELL", qty=0.1), pf, market_state, risk_cfg,
                 universe, flag_file="/nonexistent/KILL")
    assert d.allow


def test_reject_nonpositive_qty(risk_cfg, universe, market_state, portfolio_state):
    d = evaluate(prop(qty=0.0), portfolio_state, market_state, risk_cfg,
                 universe, flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.NONPOSITIVE_QTY


def test_reject_bad_order_type(risk_cfg, universe, market_state, portfolio_state):
    d = evaluate(prop(order_type="stop"), portfolio_state, market_state,
                 risk_cfg, universe, flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.BAD_ORDER_TYPE


def test_reject_penny_stock(risk_cfg, universe, portfolio_state):
    ms = {"AAPL": {"price": 4.99, "adv_dollar_volume": 3e9, "ann_vol": 0.2}}
    d = evaluate(prop(), portfolio_state, ms, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.PENNY_STOCK


def test_reject_illiquid(risk_cfg, universe, portfolio_state):
    ms = {"AAPL": {"price": 200.0, "adv_dollar_volume": 1e6, "ann_vol": 0.2}}
    d = evaluate(prop(), portfolio_state, ms, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.ILLIQUID


def test_reject_excess_volatility(risk_cfg, universe, portfolio_state):
    ms = {"AAPL": {"price": 200.0, "adv_dollar_volume": 3e9, "ann_vol": 1.5}}
    d = evaluate(prop(), portfolio_state, ms, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.EXCESS_VOLATILITY


def test_reject_over_concentration(risk_cfg, universe, market_state, portfolio_state):
    # 25% of $100 at $200 = 0.125 shares max; ask for far more.
    d = evaluate(prop(qty=10.0), portfolio_state, market_state, risk_cfg,
                 universe, flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.OVER_CONCENTRATION


def test_reject_insufficient_capital(risk_cfg, universe, market_state):
    pf = {"equity": 100.0, "cash": 1.0, "positions": {},
          "day_start_equity": 100.0, "day_pnl": 0.0, "trades_today": 0}
    d = evaluate(prop(qty=0.1), pf, market_state, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")  # $20 notional > $1 cash
    assert d.code == ReasonCode.INSUFFICIENT_CAPITAL


def test_reject_daily_loss_halt(risk_cfg, universe, market_state):
    pf = {"equity": 94.0, "cash": 94.0, "positions": {},
          "day_start_equity": 100.0, "day_pnl": -6.0, "trades_today": 0}
    d = evaluate(prop(), pf, market_state, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.DAILY_LOSS_HALT


def test_reject_max_trades(risk_cfg, universe, market_state):
    pf = {"equity": 100.0, "cash": 100.0, "positions": {},
          "day_start_equity": 100.0, "day_pnl": 0.0, "trades_today": 10}
    d = evaluate(prop(), pf, market_state, risk_cfg, universe,
                 flag_file="/nonexistent/KILL")
    assert d.code == ReasonCode.MAX_TRADES


def test_no_leverage_possible(risk_cfg, universe, market_state, portfolio_state):
    """Gross exposure can never exceed 95%: leverage is structurally blocked."""
    d = evaluate(prop(qty=0.12), portfolio_state, market_state, risk_cfg,
                 universe, flag_file="/nonexistent/KILL")  # $24 < 25% ok
    assert d.allow
    d2 = evaluate(prop(qty=0.5), portfolio_state, market_state, risk_cfg,
                  universe, flag_file="/nonexistent/KILL")  # $100 notional
    assert not d2.allow and d2.code in (ReasonCode.OVER_CONCENTRATION,
                                        ReasonCode.OVER_EXPOSURE,
                                        ReasonCode.INSUFFICIENT_CAPITAL)


def test_paper_mode_gate_ok(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("APCA_API_BASE_URL", PAPER_URL)
    paper_mode_gate()  # must not raise


def test_paper_mode_gate_rejects_live(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.setenv("APCA_API_BASE_URL", "https://api.alpaca.markets")
    with pytest.raises(PaperModeError):
        paper_mode_gate()


def test_paper_mode_gate_requires_flag(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING", "false")
    monkeypatch.setenv("APCA_API_BASE_URL", PAPER_URL)
    with pytest.raises(PaperModeError):
        paper_mode_gate()
