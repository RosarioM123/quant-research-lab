# Experiment Design — the $100, 30-day paper-trading study

**Date:** 2026-09-17 · **Status:** Mission 1 (design only — no code, no trades, no credentials)

## 1. Research question

> Can a small, systematic, multi-signal trading system combining quantitative market signals,
> event/news information, and disciplined portfolio construction generate **useful predictive
> signals** over a 30-day paper-trading experiment?

This is a question about **signal value**, not about getting rich. The experiment is designed to
produce *measured evidence about specific signals* — which requires the possibility of a negative
answer. A design that cannot fail is not an experiment.

## 2. Honest expectations (read this first)

The owner has expressed the goal of doubling or tripling the $100 while minimizing risk. That goal
is recorded here, and this section is the honest response it requires:

- Doubling $100 in 30 days requires ≈ **2.3% compounded daily**; tripling requires ≈ **3.7% daily**.
  Sustained daily returns at that level, with low risk, do not exist in public markets. Any strategy
  *capable* of those returns in 30 days is, by construction, taking enormous risk of large losses.
  "2–3× with minimal risk" is not a feasible point on any risk/return frontier.
- With $100 of capital, fixed frictions dominate: spreads, slippage assumptions, and the
  indivisibility of attention. Realistic gross edges at this scale are measured in **basis points
  per trade**, and net edges after conservative costs may be zero or negative.
- A 30-day window (≈21 trading days) is a **small sample**. Even a genuinely positive-expectancy
  system can lose over 21 days by chance; even a worthless system can win. Conclusions must be
  stated with that uncertainty, not hidden from it.

**Therefore the experiment's success criteria are:**

1. **Primary:** Did any signal family or strategy sleeve show *positive, risk-adjusted, out-of-sample*
   predictive value versus the frozen benchmark, net of conservative costs? (Measured, not claimed.)
2. **Attribution:** Which components contributed — price signals, news, regime, combination? (Ablation.)
3. **Process:** Was the research pipeline executed without data leakage, p-hacking, or benchmark-moving?
4. **Negative results count.** A clean "no signal found" is a successful experiment; a lucky 2× with
   no attributable signal is not.

## 3. The research pipeline

Every idea flows through the same stages. No stage may be skipped; no stage may reach backward in time.

```text
DATA → FEATURES → SIGNALS → SIGNAL COMBINATION → PORTFOLIO CONSTRUCTION
     → RISK → EXECUTION → PERFORMANCE → RESEARCH FEEDBACK
```

- **DATA:** versioned, timestamped snapshots. Raw data is never mutated; features are derived.
- **FEATURES:** point-in-time correct. Every feature carries an `as_of` timestamp; a feature used for a decision at time T may only use information available at T.
- **SIGNALS:** one predictive view per family, each with a written hypothesis (see §5).
- **SIGNAL COMBINATION:** a simple, regularized model (start: ridge / logistic). No single indicator may dominate; contributions must be explainable.
- **PORTFOLIO CONSTRUCTION:** rank → expected return → risk → cost → constrained allocation. Long-only, no leverage, no shorting, no options, no margin, no penny stocks. Fractional shares allowed.
- **RISK:** deterministic code, not judgment. Hard constraints; violations are rejected, not warned about.
- **EXECUTION:** paper only, via Alpaca paper endpoint. Every step recorded: signal → proposal → risk check → order → fill → portfolio update.
- **PERFORMANCE:** tracked against the frozen benchmark with the full metric set (§10).
- **RESEARCH FEEDBACK:** results flow back into the journal as KEEP / MODIFY / REJECT verdicts — never into silent parameter tweaks.

**The LLM boundary:** the LLM may classify news, extract structured event features, propose hypotheses,
and summarize — it may never directly emit an order. Architecture: LLM = research/feature layer;
quant model = prediction; portfolio engine = allocation; risk engine = authority; execution = orders.

## 4. The $100 experiment — mechanics

- **Capital:** exactly $100 in a dedicated Alpaca **paper** account (paper accounts can be reset to an arbitrary balance; default is $100k — reset to $100 before Day 1).
- **Benchmark (frozen before trading begins, never changed):** buy-and-hold SPY with the same $100, bought at the same starting timestamp. The benchmark is computed, not traded.
- **Duration:** 30 calendar days (≈21 trading days). Start/end dates recorded in the journal before Day 1.
- **Universe:** liquid US equities, ≤30 symbols (free-tier websocket limit). Selection criteria (frozen before Day 1): price > $5, average daily dollar volume > $10M, listed on NYSE/Nasdaq. Final list recorded in `config/universe.yaml` (later mission). SPY is always included (benchmark + regime input).
- **Trading window:** US market hours only. No overnight orders except deliberate multi-day holds with a recorded horizon.
- **Costs (conservative, explicit, frozen):** documented slippage assumption per trade (e.g., half-spread estimate or fixed bps — value frozen in config before Day 1); no commissions (Alpaca: $0). Paper fills are simulated — see §11 for why this matters.

## 5. Signal families and hypotheses

Each family ships with a **hypothesis** (the economic/behavioral reason it might work), **candidate
features**, and **candidate parameterizations**. Parameters are *starting points for backtesting*,
not choices — the user's rule stands: no textbook parameters adopted blindly; every parameter must
be documented and backtested, and sensitivity to the parameter must be reported.

### A. Momentum
- *Hypothesis:* information diffuses gradually; investors underreact initially and herding extends moves. Short-horizon continuation exists in liquid equities.
- *Candidates:* ROC(20), ROC(60); moving-average trend (e.g., close vs MA(50)); breakout = close at N-day high with volume confirmation; cross-sectional 12–1 month return rank.
- *To test:* which horizon, whether volume confirmation adds value, decay of the signal.

### B. Mean reversion
- *Hypothesis:* short-term price moves overreact to noise/liquidity shocks and partially revert; deviations from equilibrium are arbitraged.
- *Candidates:* 5-day reversal; z-score of price vs 20-day MA scaled by 20-day σ; distance from VWAP-like anchors; cross-sectional reversal (yesterday's losers vs winners).
- *To test:* horizon of reversion, volatility normalization, interaction with regime (reversion fails in strong trends).

### C. Cross-sectional relative strength
- *Hypothesis:* idiosyncratic strength vs. peers/market reflects real information; relative moves are cleaner than absolute moves.
- *Candidates:* return vs. SPY over 20/60 days; volatility-adjusted relative strength (excess return / tracking error); sector-relative momentum (sector mapping is a data limitation — see §11; SPY-relative is the fallback).

### D. Volatility
- *Hypothesis:* volatility regimes are persistent; expansions/contractions carry information about future opportunity and risk. Volatility is a *feature*, not a direction.
- *Candidates:* 20-day realized volatility; vol regime (current vol vs 1-year percentile); ATR-style range measures; vol expansion/contraction flags.
- *Rule:* never "high vol = buy/sell." Vol scales positions and gates signals.

### E. Volume / market activity
- *Hypothesis:* abnormal volume marks informed or urgent trading; price moves on high volume are more meaningful than moves on low volume.
- *Candidates:* volume z-score vs 20-day; volume × return interaction; unusual-activity flags.
- *Constraint:* we do **not** have institutional order-flow data and will not pretend otherwise.

### F. Market regime
- *Hypothesis:* the same signal behaves differently across regimes; conditioning on regime reduces false signals.
- *Candidates:* SPY trend (close vs MA(50/200)); volatility environment (SPY realized-vol percentile as VIX proxy — free tier has no VIX feed; documented limitation); breadth proxy (fraction of universe above MA(50)); risk-on/risk-off flag.
- *Use:* regime gates or interacts with signals (e.g., momentum weight ↑ in trending regimes, mean-reversion weight ↑ in choppy regimes) — the interaction itself must be tested, not assumed.

## 6. Strategy sleeves (independent, attributed)

Instead of one "AI strategy," five independent sleeves run on the same capital-allocation framework:

- **Strategy A — Momentum** (families A + C)
- **Strategy B — Mean reversion** (family B)
- **Strategy C — News/event reaction** (news engine outputs + §8 interactions)
- **Strategy D — Market-regime** (family F conditioning; mostly a gating/tilt sleeve)
- **Strategy E — Multi-signal ensemble** (combines A–D via the §7 model)

Each sleeve gets its own paper P&L attribution. **The ensemble may not hide bad sleeves**: if E
outperforms only because of A, the journal records that A works and E adds nothing.

## 7. Multi-signal combination model

Start simple; complexity must be earned:

1. **Baseline:** regularized linear model (ridge) on standardized signal features → expected return; or logistic → P(up).
2. **If justified by validation:** gradient-boosted trees, with strict overfitting controls.
3. No deep learning in this experiment. (Sample size forbids it; say so explicitly.)

Model output per symbol:
```text
symbol, expected_return, confidence, signal_components{...}, holding_horizon
```

**Explainability requirement:** for every prediction above the trade threshold, record feature
contributions (coefficients × feature values for linear models; SHAP/gain for trees). "Why did the
model produce this?" must be answerable from the log. A prediction that cannot be explained cannot
be traded.

## 8. News × price interaction studies

More interesting than standalone sentiment. Pre-registered interaction hypotheses to test:

- `news_surprise × momentum` — does positive surprise + existing momentum predict continuation?
- `news_surprise × volume_abnormality` — does surprise on abnormal volume predict continuation?
- `news_type × volatility_regime` — do certain event types work only in certain regimes?
- `event_direction × market_regime` — e.g., does positive news after an extended rally predict *reversal* (buy-the-rumor-sell-the-news)?

Each interaction is a hypothesis with its own backtest and its own KEEP/MODIFY/REJECT verdict.

## 9. Walk-forward backtesting (mandatory)

- **Chronological splits only.** Never shuffle. Structure: TRAIN → VALIDATION → TEST, then walk forward (re-train on expanding or rolling window, test on the next block).
- **Embargo:** a gap between train and test blocks to prevent leakage from overlapping labels/horizons.
- **Point-in-time correctness:** every feature uses only data with timestamps ≤ decision time. News features use the article version that existed at decision time — never a later `updated_at` revision.
- **The backtest must match the paper implementation:** same universe rules, same cost assumptions, same risk constraints, same execution timing (e.g., decisions on close data execute at next open — document the choice and keep it).
- **Backtest vs paper tracking** is its own metric: divergence between backtested and paper-traded performance is investigated, not shrugged at.

## 10. Performance metrics

Return, excess return vs benchmark, volatility, Sharpe, Sortino, max drawdown, hit rate, average
win/loss, turnover, exposure, concentration, transaction-cost drag, slippage assumption audit,
signal decay, calibration (predicted vs realized), and breakdowns by: strategy sleeve, market regime,
news category. Plus **paper-vs-backtest divergence**.

## 11. Data limitations (free tier — binding constraints on conclusions)

Researched 2026-09-17 against Alpaca's public docs:

- **IEX-only feed on free tier** (not the consolidated tape; no NBBO). Signals estimated on IEX data may not transfer to full-market execution. Algo Trader Plus ($99/mo) adds full SIP — not purchased for this experiment (owner's constraint).
- **30-symbol websocket limit.** Universe capped at 30 symbols for streaming; everything else via REST polling.
- **Historical REST excludes the most recent 15 minutes** on free tier. Near-real-time features must come from the websocket, not REST.
- **200 REST calls/minute.** Polling cadence must be budgeted.
- **No expectations data** (EPS/revenue consensus, guidance consensus) in the free tier. Event *surprise* can only be computed where expectations are publicly stated in the article text itself (e.g., "beat estimates by 5%" — parsed, flagged as text-derived, never fabricated). Most events will have direction/type but no quantified surprise — the schema supports surprise; the data usually won't.
- **No sector/industry feed** in the free tier. Sector-relative features need a static mapping file (documented, frozen) or fall back to SPY-relative.
- **No VIX feed** confirmed on free tier. Volatility regime uses SPY realized-vol percentiles as proxy.
- **News is REST-polled** (`GET data.alpaca.markets/v1beta1/news`), not a true push stream on the free path; a websocket news channel exists on the production data endpoint. Polling cadence (e.g., every 60s during market hours) bounds news latency — the news-speed experiment (§12) measures against *our* T0 (receipt time), honestly labeled as receipt latency, not wire latency.
- **No institutional order flow.** Stated plainly; volume features are public-tape only.
- **Paper fills are simulated.** Alpaca paper does not simulate dividends; fill prices/liquidity are idealized. Slippage assumptions must be conservative and are frozen before Day 1.
- **Survivorship bias** in historical universes; delisted symbols are absent from history.

## 12. News-speed experiment

On each news event arrival, record `T0 = receipt time` and capture the symbol's price at T0, +1, +5,
+15, +30, +60 minutes (websocket where subscribed; REST bars otherwise, noting the 15-min REST gap).
Research question: *is the signal still present after the news becomes widely observable?* Report
decay curves per event type. Do not present this as HFT — our latency stack is retail polling, and
the experiment measures the phenomenon at *our* resolution, honestly labeled.

## 13. Event studies

For major event types (earnings surprise, upgrades/downgrades, M&A, guidance changes), run
historical event studies on the backtest window: average/median return, volatility, win rate, return
distribution, decay profile, and conditional behavior (by regime, by prior momentum). Event studies
may prove more informative than trading every headline — that is itself a possible finding.

## 14. Ablation tests (mandatory at the end)

- **Model 1:** price/technical signals only
- **Model 2:** news only
- **Model 3:** price + news
- **Model 4:** full multi-signal system

Questions answered: does the news engine add information? Does combining signals improve on the
parts? Each ablation is backtested walk-forward with identical costs and constraints.

## 15. No-p-hacking rules

- Every material strategy change creates a new version (`strategy_v1`, `strategy_v2`, …) with a dated entry recording *why* it changed.
- Parameters are chosen on train/validation, evaluated once on test. Re-running with tweaked parameters after seeing test results = a new version, disclosed as such.
- If 100 experiments are run and one works, the journal records all 100 and the multiple-comparison problem is stated explicitly.
- The benchmark is frozen before Day 1 and never moved.

## 16. Research journal

Append-only. Every hypothesis gets one record:

```text
Hypothesis: ...
Dataset: ...
Features: ...
Training period: ...  Validation period: ...  Test period: ...
Result: ...  Sharpe: ...  Max drawdown: ...  Hit rate: ...
Costs assumed: ...
Conclusion: ...
Status: KEEP / MODIFY / REJECT
```

Failed hypotheses are never deleted. The failures are the research record.

## 17. Biggest experimental risks

1. **Small sample.** 21 trading days cannot separate skill from luck; any "2×" outcome is more likely noise than signal. Mitigation: pre-registered hypotheses, statistical humility in reporting.
2. **Overfitting the backtest.** With few symbols and short history, almost anything can be fit. Mitigation: walk-forward, embargo, parsimony, economic rationale required, ablation.
3. **Data leakage through timestamps.** News `updated_at` revisions, REST 15-min gaps, revised bars. Mitigation: `docs/research/data-integrity.md` (next mission) with explicit leakage tests.
4. **Paper-vs-reality gap.** Simulated fills flatter all results. Mitigation: conservative frozen slippage, paper-vs-backtest divergence metric.
5. **Regime specificity.** A 30-day window is one regime draw. Mitigation: report performance *by regime*; do not generalize beyond the observed regime.
6. **News latency illusion.** REST polling means we are slow; any "news alpha" found is alpha *at our latency*, which may not survive real conditions. Mitigation: the news-speed experiment measures decay honestly.
7. **Narrative capture.** The LLM is good at telling stories about why a trade worked. Mitigation: the LLM never touches orders; only versioned, backtested rules trade.

## 18. Mission map (what comes next — not this mission)

- Mission 2: `docs/research/data-integrity.md` + data layer scaffolding (leakage tests first).
- Mission 3: news engine scaffolding (`news/` ingestion, normalization, dedup, schema).
- Mission 4: backtest harness (walk-forward, embargo, cost model).
- Mission 5: signal family v1 features + hypotheses.
- Later: paper credentials via secure vault, universe freeze, benchmark freeze, Day 1.

---
*Design frozen as v1 on 2026-09-17. Changes require a new version entry, not an edit.*
