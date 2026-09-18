"""Event features + decay for the signal layer.

Per-event numeric features (docs/research/news-engine.md §8):
    event_type one-hot, direction (-1/0/+1), classifier confidence,
    surprise_pct (nullable -> 0 with a has_surprise flag; never imputed as 0
    silently), novelty, minutes_since_event, decay weight, and pre-registered
    price/volume/regime interactions (experiment-design.md §8).

Decay candidates: exponential w(t) = exp(-t/tau), tau in {30m, 2h, 1d}.
The decay parameter is ESTIMATED per event type from historical data —
here it is a parameter with competing hypotheses, not an assumption.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd

from .classify import EVENT_TYPES

DIRECTION_NUM = {"positive": 1.0, "negative": -1.0, "neutral": 0.0,
                 "unknown": 0.0}

DECAY_TAUS_MIN = {"tau_30m": 30.0, "tau_2h": 120.0, "tau_1d": 1440.0}


def minutes_since(received_at: str, decision_time: str) -> float:
    t0 = datetime.fromisoformat(received_at)
    t1 = datetime.fromisoformat(decision_time)
    return max(0.0, (t1 - t0).total_seconds() / 60.0)


def decay_weight(minutes: float, tau_min: float) -> float:
    return math.exp(-minutes / tau_min)


def event_features(classified: dict, decision_time: str,
                   novelty: float = 1.0) -> dict:
    """Numeric feature dict for one classified event at ``decision_time``.

    ``classified`` is a canonical event record with event_type / event_direction
    / surprise filled. Leakage guard: minutes_since < 0 is impossible — a
    decision cannot precede receipt.
    """
    mins = minutes_since(classified["received_at"], decision_time)
    feats: dict[str, float] = {}
    for et in EVENT_TYPES:
        feats[f"type_{et}"] = 1.0 if classified.get("event_type") == et else 0.0
    feats["direction"] = DIRECTION_NUM.get(
        classified.get("event_direction", "unknown"), 0.0)
    feats["confidence"] = float(classified.get("confidence", 0.0) or 0.0)
    surprise = classified.get("surprise") or {}
    feats["has_surprise"] = 1.0 if surprise else 0.0
    feats["surprise_pct"] = float(surprise.get("surprise_pct", 0.0))
    feats["novelty"] = float(novelty)
    feats["minutes_since_event"] = mins
    for name, tau in DECAY_TAUS_MIN.items():
        feats[f"decay_{name}"] = decay_weight(mins, tau)
    return feats


def interaction_features(event_feats: dict, price_feats: dict) -> dict:
    """Pre-registered news x price interactions (experiment-design.md §8).

    surprise x momentum, surprise x volume_z, type x vol_regime,
    direction x market_regime. Each is a hypothesis with its own backtest.
    """
    out = {}
    out["inter_surprise_x_momentum"] = (
        event_feats.get("surprise_pct", 0.0)
        * price_feats.get("momentum_roc20", 0.0))
    out["inter_surprise_x_volume_z"] = (
        event_feats.get("surprise_pct", 0.0)
        * price_feats.get("volume_z20", 0.0))
    out["inter_direction_x_regime"] = (
        event_feats.get("direction", 0.0)
        * price_feats.get("regime_risk_on", 0.0))
    return out


def news_to_feature_frame(raw_items: list[dict], symbols: list[str],
                          t_now: str) -> pd.DataFrame:
    """Point-in-time news feature frame valid at t_now.

    Revisions: keep the newest revision whose ``updated_at`` <= t_now, so a
    backtest never sees a future revision. Each row's ``as_of``/``source_max_ts``
    is its ``updated_at``: no source data newer than the row's as_of.
    """
    from .normalize import normalize_batch
    from .dedup import deduplicate
    from .classify import classify_stub
    events = normalize_batch(raw_items, received_at=t_now,
                             source="alpaca-news-rest", universe=symbols)
    deduped = deduplicate(events)  # retains every revision as a version row
    best: dict[str, dict] = {}
    for e in deduped:
        if e["updated_at"] > t_now:
            continue  # future revision: not visible yet
        cur = best.get(e["event_id"])
        if cur is None or e["version"] > cur["version"]:
            best[e["event_id"]] = e
    rows = []
    for e in best.values():
        cls = classify_stub(e)
        classified = dict(e, event_type=cls.event_type,
                          event_direction=cls.event_direction,
                          confidence=cls.confidence, surprise=cls.surprise)
        feats = event_features(classified, t_now, novelty=1.0)
        rows.append({"event_id": e["event_id"], "version": e["version"],
                     "as_of": e["updated_at"], "source_max_ts": e["updated_at"],
                     "symbols": e["symbols"], **feats})
    return pd.DataFrame(rows)
