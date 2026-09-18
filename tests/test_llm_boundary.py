"""LLM boundary: research only. Orders and positions are forbidden."""
import pytest

from llm.research import (LLMBoundaryViolation, classify_research,
                          control_position, emit_order, extract_features_research,
                          propose_hypothesis)


def test_emit_order_always_raises():
    with pytest.raises(LLMBoundaryViolation):
        emit_order("AAPL", "BUY", 1.0)


def test_control_position_always_raises():
    with pytest.raises(LLMBoundaryViolation):
        control_position({"AAPL": 0.5})


def test_research_helpers_never_shape_like_orders():
    c = classify_research("Acme beats EPS estimates")
    assert "side" not in c and "qty" not in c
    assert c["role"] == "research"
    f = extract_features_research("Revenue up 8% to $10B")
    assert f["role"] == "research"
    h = propose_hypothesis("surprise x momentum might interact")
    assert h["status"] == "proposed"
