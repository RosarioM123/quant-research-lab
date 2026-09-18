"""Models: ridge combiner fits, predicts, explains. Combiners learn, not dictate."""
import numpy as np
import pandas as pd
import pytest

from models.combine import RidgeCombiner
from models.explain import explain, explain_prediction


def _panel():
    rng = np.random.default_rng(11)
    X = pd.DataFrame(rng.normal(size=(200, 4)),
                     columns=["momentum_roc20", "mr_zscore20",
                              "xs_excess20", "volume_z20"])
    y = 0.5 * X["momentum_roc20"] - 0.3 * X["mr_zscore20"] + rng.normal(
        scale=0.1, size=200)
    return X, pd.Series(y)


def test_ridge_fits_and_predicts():
    X, y = _panel()
    m = RidgeCombiner(alpha=1.0).fit(X, y)
    pred = m.predict(X.iloc[:5])
    assert len(pred) == 5
    coefs = m.standardized_coefs()
    assert coefs["momentum_roc20"] > 0  # learned sign matches truth
    assert coefs["mr_zscore20"] < 0


def test_ridge_closed_form_matches_numpy():
    X, y = _panel()
    m = RidgeCombiner(alpha=2.0).fit(X, y)
    Xa = X.to_numpy()
    mu, sd = Xa.mean(0), Xa.std(0)
    Xs = (Xa - mu) / sd
    ref = np.linalg.solve(Xs.T @ Xs + 2.0 * np.eye(4), Xs.T @ y.to_numpy())
    assert np.allclose(m.coef_, ref)


def test_explain_sums_to_prediction():
    X, y = _panel()
    m = RidgeCombiner(alpha=1.0).fit(X, y)
    row = X.iloc[7]
    expl = explain_prediction(m, row, "AAPL")
    total = expl["intercept"] + sum(c["contribution"]
                                   for c in expl["contributions"])
    pred = m.predict(row.to_frame().T).iloc[0]
    assert total == pytest.approx(pred)
    # sorted by |contribution|
    mags = [abs(c["contribution"]) for c in expl["contributions"]]
    assert mags == sorted(mags, reverse=True)
