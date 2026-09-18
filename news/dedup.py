"""Deduplication: by article id, near-duplicates, and revision tracking.

- Primary key: Alpaca article ``id``.
- Revisions: same id with newer ``updated_at`` -> NEW VERSION ROW. Every
  revision is RETAINED (never overwritten); rows link via ``supersedes``.
  Backtests replay the newest revision whose ``updated_at`` <= decision time.
- Near-duplicates: same normalized URL, or headline token-Jaccard >= 0.85
  within a 24h window -> clustered under one cluster_id, variants kept.
"""
from __future__ import annotations

import re
from datetime import datetime


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _norm_url(url: str) -> str:
    return re.sub(r"[?#].*$", "", (url or "").lower().rstrip("/"))


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def deduplicate(events: list[dict], jaccard_threshold: float = 0.85) -> list[dict]:
    """Return deduplicated events. Same-ID revisions become version rows.

    Every revision is retained: the first occurrence is version 1, later
    occurrences with newer ``updated_at`` are versions 2, 3, ... linked via
    ``supersedes``. Backtests replay the original version when the decision
    time precedes the revision (leakage-critical).
    """
    deduped: list[dict] = []
    by_id: dict[str, dict] = {}
    for ev in events:
        eid = ev["event_id"]
        if eid not in by_id:
            ev = dict(ev)
            ev["version"] = 1
            ev["supersedes"] = None
            by_id[eid] = ev
            deduped.append(ev)
            continue
        existing = by_id[eid]
        if _parse(ev["updated_at"]) > _parse(existing["updated_at"]):
            ev = dict(ev)
            ev["version"] = existing["version"] + 1
            ev["supersedes"] = existing["event_id"]
            ev["superseded_by"] = None
            existing["superseded_by"] = ev["event_id"] + f"#v{ev['version']}"
            by_id[eid] = ev
            deduped.append(ev)
        # Older/duplicate rows for the same id: ignored (not new information).

    # Near-duplicate clustering (24h window, headline similarity or same URL).
    clusters: list[dict] = []
    for ev in sorted(deduped, key=lambda e: e["received_at"]):
        placed = False
        for cl in clusters:
            head = cl["head"]
            dt_hours = abs((_parse(ev["received_at"])
                            - _parse(head["received_at"])).total_seconds()) / 3600
            if dt_hours > 24:
                continue
            if (_norm_url(ev["url"]) and _norm_url(ev["url"]) == _norm_url(head["url"])) \
                    or jaccard(ev["headline"], head["headline"]) >= jaccard_threshold:
                cl["variants"].append(ev)
                ev["cluster_id"] = head["event_id"]
                placed = True
                break
        if not placed:
            clusters.append({"head": ev, "variants": []})
            ev["cluster_id"] = ev["event_id"]
    return deduped
