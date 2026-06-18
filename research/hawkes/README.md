# Hawkes News-to-Price Microstructure

Research module: models how macro news events excite price jumps using a
bivariate Hawkes process with exponential kernels (via `tick`).

## Files

- `hawkes_fit.py` — Simulates a 2-D Hawkes process (news, price jumps), grid-searches
  the decay parameter, and extracts microstructure metrics: news-to-price impact
  (alpha_10), information absorption half-life, and the endogeneity (branching) ratio.
  Validates the fit with an Exp(1) residual test (time-change theorem, KS test).
- `hawkes_data_prep.py` — Builds `tick`-ready timestamp streams from real news/price
  DataFrames: timezone localization, regular-trading-hours filtering, price-jump
  extraction, common-epoch re-zeroing, and duplicate-timestamp resolution.
- `hawkes_rolling.py` — Rolling-window Hawkes fits across the trading day to track
  how news impact and endogeneity evolve; plots parameter stability.
- `hawkes_plots.py` — Diagnostics: Exp(1) Q-Q plot of compensator residuals and the
  conditional-intensity impulse response around a news event.

## Notes

- `hawkes_fit.py` runs on synthetic data (seeded) as a correctness harness;
  `hawkes_data_prep.py` is the adapter for real CSV/tick data.
- Requires: `numpy`, `pandas`, `matplotlib`, `scipy`, `tick`.
- Research code, not wired into the live signal pipeline.
