"""Point-in-time integrity: no future data, ever."""
import pandas as pd
import pytest

from data.features import FeatureTable
from data.integrity import (LeakageError, assert_chronological,
                            check_feature_rows, check_no_future_columns)


def test_feature_table_rejects_future_source_at_write(tmp_path):
    ft = FeatureTable("t", root=tmp_path)
    with pytest.raises(ValueError):
        ft.add_row("AAPL", as_of="2026-01-05T16:00:00+00:00",
                   features={"x": 1.0},
                   source_max_ts="2026-01-06T16:00:00+00:00")  # future!


def test_check_feature_rows_ok():
    df = pd.DataFrame([
        {"symbol": "AAPL", "as_of": "2026-01-05T16:00:00+00:00",
         "source_max_ts": "2026-01-05T15:59:00+00:00", "features": {}},
    ])
    check_feature_rows(df, "2026-01-05T16:00:00+00:00")  # no raise


def test_check_feature_rows_future_asof():
    df = pd.DataFrame([
        {"symbol": "AAPL", "as_of": "2026-01-06T16:00:00+00:00",
         "source_max_ts": "2026-01-06T15:59:00+00:00", "features": {}},
    ])
    with pytest.raises(LeakageError):
        check_feature_rows(df, "2026-01-05T16:00:00+00:00")


def test_check_feature_rows_source_newer_than_asof():
    df = pd.DataFrame([
        {"symbol": "AAPL", "as_of": "2026-01-05T16:00:00+00:00",
         "source_max_ts": "2026-01-05T16:00:01+00:00", "features": {}},
    ])
    with pytest.raises(LeakageError):
        check_feature_rows(df, "2026-01-05T16:00:00+00:00")


def test_at_or_before_slice(tmp_path):
    ft = FeatureTable("t", root=tmp_path)
    ft.add_row("AAPL", "2026-01-05T16:00:00+00:00", {"x": 1.0},
               "2026-01-05T15:00:00+00:00")
    ft.add_row("AAPL", "2026-01-06T16:00:00+00:00", {"x": 2.0},
               "2026-01-06T15:00:00+00:00")
    ft.flush()
    pit = ft.at_or_before("2026-01-05T16:00:00+00:00")
    assert len(pit) == 1
    assert pit.iloc[0]["features"] == {"x": 1.0}


def test_no_future_columns(prices):
    check_no_future_columns(prices.iloc[:50], prices.index[49])  # ok
    with pytest.raises(LeakageError):
        check_no_future_columns(prices, prices.index[10])  # panel runs past t


def test_assert_chronological():
    assert_chronological([1, 2, 2, 3])  # non-decreasing ok
    with pytest.raises(LeakageError):
        assert_chronological([1, 3, 2])


def test_news_revision_uses_original_version(news_raw):
    """Backtest must replay the ORIGINAL article version, not the revision."""
    from news.normalize import normalize_batch
    from news.dedup import deduplicate
    from news.features import news_to_feature_frame
    events = normalize_batch(news_raw, "2026-09-10T15:00:00Z",
                             "alpaca-news-rest", ["AAPL", "SPY"])
    deduped = deduplicate(events)
    n1 = sorted((e for e in deduped if e["event_id"] == "n1"),
                key=lambda e: e["version"])
    assert [e["version"] for e in n1] == [1, 2]  # every revision retained
    # A point-in-time frame at 13:45Z replays the ORIGINAL version only.
    frame = news_to_feature_frame(news_raw, ["AAPL", "SPY"],
                                  "2026-09-10T13:45:00Z")
    row = frame[frame["event_id"] == "n1"].iloc[0]
    assert row["version"] == 1
    assert row["source_max_ts"] <= row["as_of"]
