"""Signal combination: regularized linear baseline.

Start simple; complexity must be earned (experiment-design.md §7):
1. Baseline: ridge regression on standardized signal features -> expected return.
2. If justified by validation: gradient-boosted trees with strict overfit controls.
3. No deep learning in this experiment (sample size forbids it).

Closed-form ridge via numpy (no sklearn needed): w = (X'X + aI)^-1 X'y.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class RidgeCombiner:
    """Ridge combiner: standardized features -> expected return per symbol."""

    def __init__(self, alpha: float = 1.0):
        if alpha < 0:
            raise ValueError("alpha must be >= 0")
        self.alpha = alpha
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0
        self.mean_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None
        self.feature_names: list[str] | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RidgeCombiner":
        self.feature_names = list(X.columns)
        Xa = X.to_numpy(dtype=float)
        # Standardize (store for predict/explain).
        self.mean_ = np.nanmean(Xa, axis=0)
        self.scale_ = np.nanstd(Xa, axis=0)
        self.scale_[self.scale_ == 0] = 1.0
        Xs = np.nan_to_num((Xa - self.mean_) / self.scale_)
        ya = y.to_numpy(dtype=float)
        mask = ~np.isnan(ya)
        Xs, ya = Xs[mask], ya[mask]
        n_feat = Xs.shape[1]
        A = Xs.T @ Xs + self.alpha * np.eye(n_feat)
        self.coef_ = np.linalg.solve(A, Xs.T @ ya)
        self.intercept_ = float(np.mean(ya))
        return self

    def _standardize(self, X: pd.DataFrame) -> np.ndarray:
        Xa = X.to_numpy(dtype=float)
        return np.nan_to_num((Xa - self.mean_) / self.scale_)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        if self.coef_ is None:
            raise RuntimeError("combiner not fitted")
        Xs = self._standardize(X)
        return pd.Series(self.intercept_ + Xs @ self.coef_, index=X.index)

    def standardized_coefs(self) -> pd.Series:
        """Coefficients on the standardized scale (for explainability)."""
        return pd.Series(self.coef_, index=self.feature_names)
