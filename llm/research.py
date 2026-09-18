"""LLM boundary: research and features ONLY. Never orders. Never positions.

Architecture (docs/architecture.md §1)::
    LLM      -> research / feature layer (classify, extract, hypothesize)
    QUANT    -> prediction
    PORTFOLIO-> allocation
    RISK     -> authority
    EXECUTION-> orders (paper only)

This module is the executable form of that separation. Research helpers may
classify news, extract structured fields, and propose hypotheses. The moment
anything in the LLM layer is asked to emit an order, size a position, or
override risk, it raises ``LLMBoundaryViolation``.

Tests assert the boundary holds: ``emit_order`` always raises, and the
research helpers never return anything shaped like an order.
"""
from __future__ import annotations


class LLMBoundaryViolation(Exception):
    """The LLM layer was asked to do something outside research/features."""


def classify_research(headline: str, summary: str = "") -> dict:
    """Research-only classification helper (offline stub).

    Returns a taxonomy-shaped dict, never a trading instruction.
    """
    from news.classify import classify_stub
    event = {"event_id": "research-only", "headline": headline,
             "summary": summary}
    c = classify_stub(event)
    return {"event_type": c.event_type, "event_direction": c.event_direction,
            "confidence": c.confidence, "role": "research"}


def extract_features_research(text: str) -> dict:
    """Research-only structured extraction (figures, direction words)."""
    import re
    numbers = re.findall(r"[-+]?\d*\.?\d+\s*%", text)
    return {"mentioned_percentages": numbers, "role": "research"}


def propose_hypothesis(observation: str) -> dict:
    """Record a hypothesis proposal for the research journal."""
    return {"hypothesis": observation, "status": "proposed",
            "role": "research"}


def emit_order(*args, **kwargs):
    """FORBIDDEN. The LLM layer can never emit an order."""
    raise LLMBoundaryViolation(
        "LLM layer may not emit orders: orders come only from "
        "portfolio.construct -> risk.engine -> execution.paper"
    )


def control_position(*args, **kwargs):
    """FORBIDDEN. The LLM layer can never control a position."""
    raise LLMBoundaryViolation(
        "LLM layer may not control positions: allocation is the portfolio "
        "module's job under the risk engine's authority"
    )
