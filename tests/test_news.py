"""News pipeline: normalize, dedupe (revision retention), stub-classify."""
import pytest

from news.classify import (Classification, classify_stub,
                           validate_classification)
from news.dedup import deduplicate
from news.features import event_features, news_to_feature_frame
from news.normalize import normalize_batch


def _events(news_raw):
    return normalize_batch(news_raw, "2026-09-10T15:00:00Z", "alpaca-news-rest",
                           ["AAPL", "SPY"])


def _classified(event, decision_time="2026-09-10T15:00:00+00:00"):
    c = classify_stub(event)
    return dict(event, event_type=c.event_type,
                event_direction=c.event_direction,
                confidence=c.confidence, surprise=c.surprise), c


def test_normalize_shapes(news_raw):
    events = _events(news_raw)
    e = events[0]
    assert e["event_id"] == "n1"
    assert e["version"] == 1
    assert e["received_at"] == "2026-09-10T15:00:00+00:00"  # honest T0
    assert "AAPL" in e["symbols"]
    assert e["created_at"] <= e["updated_at"]
    # symbols outside the universe are dropped
    assert _events([dict(news_raw[0], symbols=["FAKE"])])[0]["symbols"] == []


def test_dedup_retains_every_revision(news_raw):
    """Every revision must be retained, not just the newest."""
    deduped = deduplicate(_events(news_raw))
    n1 = sorted((e for e in deduped if e["event_id"] == "n1"),
                key=lambda e: e["version"])
    assert [e["version"] for e in n1] == [1, 2]
    assert n1[1]["supersedes"] == "n1"
    assert n1[0]["superseded_by"] is not None
    # Original text is replayable for backtests:
    assert "update" not in n1[0]["headline"]
    assert "update" in n1[1]["headline"]


def test_dedup_clusters_same_headline_different_id(news_raw):
    """Same story, different outlet/ID -> one cluster, both retained."""
    deduped = deduplicate(_events(news_raw))
    n1 = [e for e in deduped if e["event_id"] == "n1"][0]
    n2 = [e for e in deduped if e["event_id"] == "n2"][0]
    assert n2["cluster_id"] == n1["cluster_id"] == "n1"
    assert n1["event_id"] != n2["event_id"]  # distinct records retained


def test_classify_stub_is_deterministic(news_raw):
    event = _events(news_raw)[0]
    c1 = classify_stub(event)
    c2 = classify_stub(event)
    assert isinstance(c1, Classification)
    assert c1 == c2  # deterministic stub
    assert c1.event_type == "eps_surprise"
    assert c1.event_direction == "positive"
    assert 0.0 <= c1.confidence <= 1.0


def test_classify_stub_unknown_for_garbage():
    c = classify_stub({"event_id": "x", "headline": "xyzzy unrelated",
                       "summary": ""})
    assert c.event_type == "unknown"
    assert c.event_direction == "unknown"


def test_surprise_requires_expectation_source():
    bad = {"event_id": "x", "event_type": "eps_surprise",
           "event_direction": "positive", "confidence": 0.8,
           "surprise": {"metric": "eps", "expected": 1.0, "actual": 1.08,
                        "surprise_pct": 8.0, "expectation_source": None}}
    with pytest.raises(ValueError):
        validate_classification(bad)
    good = dict(bad, surprise=dict(bad["surprise"],
                                   expectation_source="article_text"))
    validate_classification(good)  # must not raise


def test_event_features_one_hot_and_decay(news_raw):
    classified, c = _classified(_events(news_raw)[0])
    feats = event_features(classified, "2026-09-10T15:00:00+00:00", novelty=1.0)
    assert feats["type_eps_surprise"] == 1.0
    assert feats["type_unknown"] == 0.0
    assert feats["direction"] == 1.0
    assert feats["confidence"] == c.confidence
    assert feats["novelty"] == 1.0
    assert feats["minutes_since_event"] == 0.0
    assert feats["decay_tau_30m"] == 1.0  # age 0 -> full weight


def test_event_features_decay_with_time(news_raw):
    classified, _ = _classified(_events(news_raw)[0])
    feats = event_features(classified, "2026-09-10T16:00:00+00:00")
    assert feats["minutes_since_event"] == 60.0
    assert feats["decay_tau_30m"] < feats["decay_tau_2h"] < feats["decay_tau_1d"]


def test_news_to_feature_frame_pit(news_raw):
    # At 13:45Z: the 14:00Z revision must NOT be visible (future data).
    frame = news_to_feature_frame(news_raw, ["AAPL", "SPY"],
                                  "2026-09-10T13:45:00Z")
    n1_rows = frame[frame["event_id"] == "n1"]
    assert n1_rows.iloc[0]["version"] == 1
    # At 14:30Z: revision 2 (updated 14:00Z) is the visible version.
    frame2 = news_to_feature_frame(news_raw, ["AAPL", "SPY"],
                                   "2026-09-10T14:30:00Z")
    assert frame2[frame2["event_id"] == "n1"].iloc[0]["version"] == 2
    # source_max_ts <= as_of invariant holds on every row.
    assert (frame2["source_max_ts"] <= frame2["as_of"]).all()
