"""Event classification: schema-validated taxonomy assignment.

Production design: an LLM assigns the taxonomy label (docs/research/news-engine.md
§5, §10). This module defines the SCHEMA and a deterministic keyword STUB so the
full pipeline runs offline with zero LLM calls. The stub is deliberately
low-confidence outside obvious cases — when it cannot classify reliably it
emits ``unknown`` (an honest null, never a guess).

Every classification — LLM or stub — must pass ``validate_classification``.
Validation failures are logged and quarantined, never silently coerced.
"""
from __future__ import annotations

from dataclasses import dataclass, field

EVENT_TYPES = [
    "eps_surprise", "revenue_surprise", "guidance_change", "margin_change",
    "management_commentary", "acquisition", "divestiture", "buyback",
    "offering", "leadership_change", "regulatory_approval", "investigation",
    "lawsuit", "policy_change", "product_launch", "major_contract",
    "partnership", "technical_breakthrough", "fed", "cpi_inflation", "jobs",
    "rates", "geopolitical", "upgrade", "downgrade", "price_target_change",
    "unknown",
]

DIRECTIONS = ["positive", "negative", "neutral", "unknown"]

SURPRISE_SOURCES = ["article_text", "company_guidance", None]


@dataclass
class Classification:
    event_id: str
    event_type: str
    event_direction: str
    confidence: float  # 0..1
    surprise: dict | None = None
    classifier: str = "stub"

    def validate(self) -> "Classification":
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"invalid event_type: {self.event_type}")
        if self.event_direction not in DIRECTIONS:
            raise ValueError(f"invalid event_direction: {self.event_direction}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence out of range: {self.confidence}")
        if self.surprise is not None:
            req = ("metric", "expected", "actual", "surprise_pct",
                   "expectation_source")
            missing = [k for k in req if k not in self.surprise]
            if missing:
                raise ValueError(f"surprise missing keys: {missing}")
            # Never fabricate expectations: source is mandatory.
            if self.surprise["expectation_source"] not in ("article_text",
                                                           "company_guidance"):
                raise ValueError(
                    "surprise.expectation_source must be article_text or "
                    "company_guidance — never fabricated"
                )
        return self


def validate_classification(d: dict) -> Classification:
    """Schema-validate a classification dict (e.g. from an LLM)."""
    c = Classification(
        event_id=str(d["event_id"]),
        event_type=d["event_type"],
        event_direction=d["event_direction"],
        confidence=float(d["confidence"]),
        surprise=d.get("surprise"),
        classifier=d.get("classifier", "llm"),
    )
    return c.validate()


# --- Deterministic stub (offline use; NOT a production classifier) --------

_KEYWORDS: list[tuple[str, list[str], str]] = [
    ("eps_surprise", ["eps", "earnings per share", "beat estimates"], "positive"),
    ("revenue_surprise", ["revenue", "sales beat", "top line"], "positive"),
    ("guidance_change", ["guidance", "outlook raised", "outlook cut"], "neutral"),
    ("acquisition", ["acquire", "acquisition", "takeover", "merger"], "neutral"),
    ("leadership_change", ["ceo", "resigns", "appointed chief"], "neutral"),
    ("lawsuit", ["lawsuit", "sued", "settlement"], "negative"),
    ("investigation", ["investigation", "subpoena", "probe"], "negative"),
    ("product_launch", ["launches", "unveils", "new product"], "positive"),
    ("upgrade", ["upgraded", "overweight", "buy rating"], "positive"),
    ("downgrade", ["downgraded", "underweight", "sell rating"], "negative"),
    ("buyback", ["buyback", "share repurchase"], "positive"),
    ("offering", ["secondary offering", "share offering"], "negative"),
]


def classify_stub(event: dict) -> Classification:
    """Keyword stub. Low confidence by design; unknown when unsure."""
    text = (event.get("headline", "") + " " + event.get("summary", "")).lower()
    for event_type, keywords, direction in _KEYWORDS:
        if any(k in text for k in keywords):
            return Classification(
                event_id=event["event_id"],
                event_type=event_type,
                event_direction=direction,
                confidence=0.55,
                classifier="stub",
            ).validate()
    return Classification(
        event_id=event["event_id"],
        event_type="unknown",
        event_direction="unknown",
        confidence=0.0,
        classifier="stub",
    ).validate()
