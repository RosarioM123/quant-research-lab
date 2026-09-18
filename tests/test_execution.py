"""Execution: the paper endpoint gate refuses everything else."""
import os

import pytest

from execution.paper import PaperBroker, PaperEndpointRefused
from risk.engine import PAPER_URL, PaperModeError


def test_paper_broker_accepts_exactly_paper_url():
    b = PaperBroker(PAPER_URL)
    assert b.base_url == PAPER_URL


def test_paper_broker_refuses_live_url():
    with pytest.raises(PaperEndpointRefused):
        PaperBroker("https://api.alpaca.markets")


def test_paper_broker_refuses_empty_url(monkeypatch):
    monkeypatch.delenv("APCA_API_BASE_URL", raising=False)
    with pytest.raises((PaperEndpointRefused, PaperModeError, ValueError)):
        PaperBroker("")


def test_paper_broker_refuses_typo_url():
    with pytest.raises(PaperEndpointRefused):
        PaperBroker("https://paper-api.alpaca.market")


def test_paper_broker_reads_env(monkeypatch):
    monkeypatch.setenv("APCA_API_BASE_URL", PAPER_URL)
    b = PaperBroker()
    assert b.base_url == PAPER_URL


def test_paper_broker_env_live_refused(monkeypatch):
    monkeypatch.setenv("APCA_API_BASE_URL", "https://api.alpaca.markets")
    monkeypatch.setenv("PAPER_TRADING", "true")
    with pytest.raises((PaperEndpointRefused, PaperModeError)):
        PaperBroker()


def test_fill_is_simulated_and_auditable():
    b = PaperBroker(PAPER_URL)
    fill = b.submit_order("AAPL", "BUY", 0.1, reference_price=200.0)
    assert fill["simulated"] is True
    assert fill["endpoint"] == PAPER_URL
    assert fill["status"] == "FILLED"


def test_fill_requires_reference_price():
    b = PaperBroker(PAPER_URL)
    with pytest.raises(ValueError):
        b.submit_order("AAPL", "BUY", 0.1)
