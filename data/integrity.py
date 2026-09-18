"""Point-in-time integrity checks (leakage guards).

These are the executable form of docs/research/experiment-design.md §9 and
the forthcoming data-integrity doc. Every check raises ``LeakageError`` on
violation — leakage fails loudly, never silently.
"""
from __future__ import annotations

import pandas as pd


class LeakageError(Exception):
    """A feature, signal, or decision used information from the future."""


def check_feature_rows(df: pd.DataFrame, decision_time: str) -> None:
    """Assert every feature row was knowable at ``decision_time``.

    ISO-8601 strings compare chronologically, so string comparison is exact.
    """
    if df.empty:
        return
    for col in ("as_of", "source_max_ts"):
        if col not in df.columns:
            raise LeakageError(f"feature table missing required column: {col}")
    future_asof = df[df["as_of"] > decision_time]
    if not future_asof.empty:
        raise LeakageError(
            f"{len(future_asof)} feature rows have as_of > decision_time "
            f"{decision_time}"
        )
    leaked = df[df["source_max_ts"] > df["as_of"]]
    if not leaked.empty:
        raise LeakageError(
            f"{len(leaked)} feature rows consumed source data newer than "
            "their own as_of timestamp"
        )
    leaked2 = df[df["source_max_ts"] > decision_time]
    if not leaked2.empty:
        raise LeakageError(
            f"{len(leaked2)} feature rows used source data newer than "
            f"decision_time {decision_time}"
        )


def check_no_future_columns(prices: pd.DataFrame, decision_time) -> None:
    """Assert a price panel contains no bar dated after ``decision_time``."""
    if not prices.empty and prices.index.max() > decision_time:
        raise LeakageError(
            f"price panel contains bars after decision_time {decision_time}"
        )


def assert_chronological(timestamps: list) -> None:
    """Replay order must be non-decreasing; time may not run backwards."""
    for a, b in zip(timestamps, timestamps[1:]):
        if b < a:
            raise LeakageError(f"non-chronological replay: {a} -> {b}")
