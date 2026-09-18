"""Normalize raw Alpaca news articles -> canonical event records.

Canonical event record (docs/research/news-engine.md §4):
    event_id, received_at (our T0), created_at, updated_at, symbols[],
    headline, summary, author, url, content_ref, event_type, event_direction,
    surprise, features, source.

All timestamps -> UTC ISO-8601. Revisions never overwrite: a newer
``updated_at`` for a known ``event_id`` is a new version row.
"""
from __future__ import annotations

from datetime import timezone

import pandas as pd


def _to_utc_iso(ts: str) -> str:
    return pd.Timestamp(ts).tz_convert(timezone.utc).isoformat()


def normalize_article(raw: dict, received_at: str, source: str,
                      universe: list[str]) -> dict:
    """Map one raw article dict to a canonical event record (unclassified)."""
    symbols = [s for s in raw.get("symbols", []) if s in universe]
    return {
        "event_id": str(raw.get("id")),
        "received_at": _to_utc_iso(received_at),
        "created_at": _to_utc_iso(raw["created_at"]),
        "updated_at": _to_utc_iso(raw.get("updated_at") or raw["created_at"]),
        "symbols": symbols,
        "headline": raw.get("headline", ""),
        "summary": raw.get("summary", ""),
        "author": raw.get("author", ""),
        "url": raw.get("url", ""),
        "content_ref": raw.get("url", ""),  # content stored by reference
        "event_type": None,        # filled by classify
        "event_direction": None,   # filled by classify
        "surprise": None,          # filled by classify/extract
        "features": {},
        "source": source,
        "version": 1,
    }


def normalize_batch(raw_articles: list[dict], received_at: str, source: str,
                    universe: list[str]) -> list[dict]:
    events = []
    for raw in raw_articles:
        try:
            events.append(normalize_article(raw, received_at, source, universe))
        except (KeyError, ValueError, TypeError):
            # Malformed article: skip, never silently coerce.
            continue
    return events
