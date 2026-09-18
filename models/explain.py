"""Explainability: feature contributions per prediction.

Explainability requirement (experiment-design.md §7): for every prediction
above the trade threshold, record feature contributions. "Why did the model
produce this?" must be answerable from the log. A prediction that cannot be
explained cannot be traded.

For the linear ridge baseline: contribution_i = coef_std_i * x_std_i.
"""
from __future__ import annotations

import pandas as pd

from .combine import RidgeCombiner


def explain(combiner: RidgeCombiner, x_row: pd.Series,
            top_n: int | None = None) -> list[tuple[str, float]]:
    """Return [(feature, contribution)] sorted by |contribution| desc."""
    coefs = combiner.standardized_coefs()
    x_std = (x_row[coefs.index] - combiner.mean_) / combiner.scale_
    x_std = pd.Series(x_std, index=coefs.index).fillna(0.0)
    contrib = (coefs * x_std).sort_values(key=abs, ascending=False)
    items = list(contrib.items())
    return items[:top_n] if top_n else items


def explain_prediction(combiner: RidgeCombiner, x_row: pd.Series,
                       symbol: str) -> dict:
    """Full explanation record for the ledger."""
    expected = float(combiner.predict(x_row.to_frame().T).iloc[0])
    contributions = explain(combiner, x_row)
    return {
        "symbol": symbol,
        "expected_return": expected,
        "intercept": float(combiner.intercept_),
        "contributions": [
            {"feature": name, "contribution": float(val)}
            for name, val in contributions
        ],
    }
